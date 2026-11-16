"""YOLO/ByteTrack → MP4 + JSONL quan sát + report input/config/runtime có hash.

Đây là pipeline phương tiện; cache không phải GT hoặc score accident.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import statistics
import time
from zoneinfo import ZoneInfo

from src.data_preparation import H264Writer, save_json, sha256_file
from src.inference_export import FrameCache, observations, reserve_outputs
from src.vehicle_labels import VehicleLabels, draw_vehicle_labels

VEHICLE_NAMES = {"bicycle", "car", "motorcycle", "motorbike", "bus", "truck"}


def arguments(kind: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=f"Run YOLOv8n {kind}; export video, frame cache and provenance")
    parser.add_argument("video", type=Path, help="Path to an input video")
    parser.add_argument("--device", default="auto", help="auto, cpu, or CUDA index such as 0")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    parser.add_argument("--model", type=Path, default=Path("yolov8n.pt"))
    parser.add_argument("--timing-status", choices=("unknown", "presentation_only", "verified_source"), default="unknown")
    parser.add_argument("--timing-evidence", type=Path, help="Required local source-timing evidence for verified_source")
    parser.add_argument("--cpu-threads", type=int, help="Optional PyTorch CPU thread count, recorded in report")
    parser.add_argument("--collision-config", type=Path, default=Path(__file__).resolve().parents[1]/'configs/collision_rules.json')
    parser.add_argument("--vehicle-config", type=Path, default=Path(__file__).resolve().parents[1]/'configs/vehicle_inference.json')
    return parser


def percentile(values, probability):
    ordered = sorted(values)
    index = (len(ordered) - 1) * probability
    low, high = math.floor(index), math.ceil(index)
    return ordered[low] + (ordered[high] - ordered[low]) * (index - low)


def run(args: argparse.Namespace, tracking: bool) -> Path:
    source = args.video.expanduser().resolve()
    vehicle_config_path = getattr(args, 'vehicle_config', Path(__file__).resolve().parents[1]/'configs/vehicle_inference.json')
    vehicle_config = json.loads(vehicle_config_path.read_text())
    vehicle_config_hash = sha256_file(vehicle_config_path)
    label_engine = VehicleLabels(vehicle_config)
    collision_mode = bool(getattr(args,'collision',False))
    rule_engine = None
    if collision_mode:
        if not tracking:
            raise ValueError('Collision analysis requires tracking')
        from src.collision_rules import CollisionRules
        from src.collision_output import draw_alerts, export_evidence
        collision_config = json.loads(args.collision_config.read_text())
        collision_config_hash = sha256_file(args.collision_config)
    if not source.is_file():
        raise ValueError(f"Video does not exist: {source}")
    if args.imgsz <= 0:
        raise ValueError("--imgsz must be positive")
    timing_status = getattr(args, "timing_status", "unknown")
    evidence = getattr(args, "timing_evidence", None)
    if timing_status == "verified_source" and (evidence is None or not evidence.is_file()):
        raise ValueError("verified_source requires an existing --timing-evidence file")
    if evidence is not None and not evidence.is_file():
        raise ValueError("Timing evidence does not exist")
    threads = getattr(args, "cpu_threads", None)
    if threads is not None and threads <= 0:
        raise ValueError("--cpu-threads must be positive")
    os.environ.setdefault("YOLO_CONFIG_DIR", str(Path(__file__).resolve().parents[1] / "configs/ultralytics"))
    try:
        import cv2
        import torch
        from ultralytics import YOLO
        from ultralytics.utils.checks import check_yaml
    except ImportError as exc:
        raise RuntimeError("Install packages in .venv before running video inference") from exc
    if threads:
        torch.set_num_threads(threads)
    device = ("0" if torch.cuda.is_available() else "cpu") if args.device == "auto" else args.device
    if device != "cpu" and not torch.cuda.is_available():
        raise RuntimeError("CUDA device requested, but PyTorch cannot use CUDA")
    model_path = args.model.expanduser()
    if not model_path.is_file() and model_path.name != "yolov8n.pt":
        raise FileNotFoundError(f"Model does not exist: {model_path}")
    model = YOLO(str(model_path))
    if threads and device == "cpu":
        # Ultralytics setup_model/select_device resets the thread count.
        # Public prediction callback restores the requested count after setup.
        model.add_callback("on_predict_start", lambda predictor: torch.set_num_threads(threads))
    names = dict(enumerate(model.names)) if isinstance(model.names, list) else model.names
    classes = [int(i) for i, name in names.items() if str(name).lower() in VEHICLE_NAMES]
    if not classes:
        raise RuntimeError(f"Model has no supported vehicle classes: {names}")
    print("Vehicle classes:", ", ".join(f"{i}={names[i]}" for i in classes), flush=True)
    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        capture.release()
        raise RuntimeError(f"Cannot open video: {source}")
    paths, completed = None, []
    try:
        fps = capture.get(cv2.CAP_PROP_FPS)
        if not 0 < fps < 1000:
            raise RuntimeError("Video container FPS unavailable or invalid")
        reported_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_started = time.perf_counter()
        ok, frame = capture.read()
        if not ok or frame is None:
            raise RuntimeError(f"Cannot read first frame: {source}")
        height, width = frame.shape[:2]
        if collision_mode:
            rule_engine = CollisionRules(collision_config,image_width=width,image_height=height,detector_imgsz=args.imgsz)
        kind = 'collision' if collision_mode else ("tracking" if tracking else "detection")
        paths = reserve_outputs(args.output_dir.expanduser().resolve() / source.stem, f"{source.stem}_{kind}")
        clock = FrameCache(fps, timing_status)
        durations, count, track_ids = [], 0, set()
        previous_thumbnail = None
        collision_quality = dict(observations=0,eligible_track_observations=0,abstained_observations=0,frames_with_two_eligible_tracks=0)
        pipeline_started = frame_started
        print(f"Input: {source}\nOutput: {paths['video']}", flush=True)
        with paths["partial"].open("x", encoding="utf-8") as cache:
            with H264Writer(paths["video"], width, height, fps) as writer:
                while ok and frame is not None:
                    if frame.shape[:2] != (height, width):
                        raise ValueError("Changing frame dimensions")
                    pts_ms = capture.get(cv2.CAP_PROP_POS_MSEC)
                    options = dict(device=device, imgsz=args.imgsz, classes=classes, verbose=False,
                                   agnostic_nms=vehicle_config['agnostic_nms'])
                    # A new YOLO object per run isolates ByteTrack state between videos.
                    results = (model.track(frame, persist=True, tracker="bytetrack.yaml", **options)
                               if tracking else model.predict(frame, **options))
                    objects = observations(results[0], names, width, height)
                    scene_difference = 0.0
                    if tracking:
                        import numpy as np
                        thumbnail = cv2.resize(frame,(64,36)).astype('float32')/255
                        if previous_thumbnail is not None:
                            scene_difference = float(np.mean(np.abs(thumbnail-previous_thumbnail)))
                        previous_thumbnail = thumbnail
                    label_cut = scene_difference >= vehicle_config['scene_cut_mean_difference']
                    objects = label_engine.update(count, objects, scene_cut=label_cut)
                    record = clock.record(count, pts_ms, objects)
                    record['vehicle_scene_cut'] = label_cut
                    if rule_engine:
                        scene_cut = scene_difference >= collision_config['scene_cut_mean_difference']
                        record['collision'] = rule_engine.update(record,scene_cut=scene_cut)
                        quality = record['collision']['quality']
                        collision_quality['observations'] += quality['observations']
                        collision_quality['eligible_track_observations'] += quality['eligible_tracks']
                        collision_quality['abstained_observations'] += quality['abstained_observations']
                        collision_quality['frames_with_two_eligible_tracks'] += quality['eligible_tracks'] >= 2
                    cache.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
                    track_ids.update(o["track_id"] for o in objects if o["track_id"] is not None)
                    rendered = draw_vehicle_labels(frame,objects)
                    if rule_engine:
                        draw_alerts(rendered,rule_engine.events,count)
                    writer.write(rendered)
                    durations.append((time.perf_counter() - frame_started) * 1000)
                    count += 1
                    frame_started = time.perf_counter()
                    ok, frame = capture.read()
                if reported_frames > 0 and count != reported_frames:
                    raise RuntimeError(f"Incomplete decode: {count}/{reported_frames}; outputs not finalized")
        completed.append(paths["video"])
        pipeline_seconds = time.perf_counter() - pipeline_started
        paths["partial"].rename(paths["frames"])
        completed.append(paths["frames"])
        collision_fields = {}
        if rule_engine:
            events_path = paths['video'].with_suffix('.events.json')
            events = export_evidence(source,paths['video'],rule_engine.events,collision_config,fps,count)
            if sha256_file(args.collision_config) != collision_config_hash:
                raise ValueError('Collision configuration changed during the run')
            save_json(events_path,dict(schema_version=1,method=collision_config['rule_id'],
                                      experimental=True,score_is_probability=False,events=events))
            completed.append(events_path)
            collision_fields = dict(collision_experimental=True,collision_method=collision_config['rule_id'],
                                    collision_config=collision_config,collision_config_sha256=collision_config_hash,
                                    events_file=str(events_path),events_sha256=sha256_file(events_path),event_count=len(events),
                                    collision_quality=collision_quality)
            pipeline_seconds = time.perf_counter()-pipeline_started
        effective = model.predictor.args
        if sha256_file(vehicle_config_path) != vehicle_config_hash:
            raise ValueError('Vehicle inference configuration changed during the run')
        tracker_config = Path(check_yaml("bytetrack.yaml")) if tracking else None
        report = dict(
            schema_version=1, complete=True, checked_at=datetime.now(ZoneInfo("Asia/Bangkok")).isoformat(),
            mode=kind, input_video=str(source), input_sha256=sha256_file(source),
            weights_path=str(model_path.resolve()), weights_sha256=sha256_file(model_path),
            output_video=str(paths["video"]), output_sha256=sha256_file(paths["video"]),
            frame_cache=str(paths["frames"]), frame_cache_sha256=sha256_file(paths["frames"]),
            processed_frames=count, reported_input_frames=reported_frames, width_px=width, height_px=height,
            container_fps=fps, timing_status=timing_status, source_seconds_verified=timing_status == "verified_source",
            timing_evidence=str(evidence) if evidence else None,
            timing_evidence_sha256=sha256_file(evidence) if evidence else None,
            device=device, cpu_threads=torch.get_num_threads(), cpu_threads_requested=threads, requested_imgsz=args.imgsz,
            vehicle_classes={str(i): names[i] for i in classes},
            vehicle_inference_config=vehicle_config, vehicle_inference_config_sha256=vehicle_config_hash,
            effective_args={k: getattr(effective, k, None) for k in ("conf", "iou", "max_det", "half", "rect", "batch", "vid_stride", "agnostic_nms")},
            tracker="bytetrack.yaml" if tracking else None,
            tracker_config_sha256=sha256_file(tracker_config) if tracker_config else None,
            tracker_config=tracker_config.read_text() if tracker_config else None,
            observation_count=clock.observation_count, empty_frames=clock.empty_frames,
            unique_track_ids=len(track_ids), fallback_video_timestamps=clock.fallback_timestamps,
            missing_track_export_max_gap_frames=clock.max_gap,
            runtime=dict(pipeline_wall_s=pipeline_seconds, offline_processing_fps=count/pipeline_seconds,
                         frame_wall_ms_p50=statistics.median(durations), frame_wall_ms_p95=percentile(durations, .95),
                         scope="offline decode+inference+tracking(if enabled)+render+cache+encode; includes cold first inference, excludes model loading and post-run hashes; not a streaming benchmark"),
            python=platform.python_version(), platform=platform.platform(),
            packages={p: importlib.metadata.version(p) for p in ("torch", "torchvision", "ultralytics", "numpy", "opencv-python", "lap")},
            code_sha256={name: sha256_file(Path(__file__).parent/name) for name in ("video_pipeline.py", "inference_export.py", "data_preparation.py", "vehicle_labels.py")},
            labels_or_splits_modified=False, collision_detection_implemented=collision_mode,**collision_fields)
        if rule_engine:
            report['runtime']['scope'] += '; collision rules and post-run evidence clip encoding included'
            report['code_sha256'].update({name:sha256_file(Path(__file__).parent/name) for name in ('collision_rules.py','collision_output.py')})
        save_json(paths["report"], report)
        print(f"Processed {count} frames; observations {clock.observation_count}; tracks {len(track_ids)}", flush=True)
        print(f"Frame cache: {paths['frames']}\nRun report: {paths['report']}", flush=True)
        return paths["video"]
    except BaseException:
        for path in completed:
            path.unlink(missing_ok=True)
        raise
    finally:
        capture.release()
        if paths:
            paths["partial"].unlink(missing_ok=True)
            paths["lock"].unlink(missing_ok=True)
