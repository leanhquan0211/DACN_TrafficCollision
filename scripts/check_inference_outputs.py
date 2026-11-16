"""Kiểm cache/MP4/report trước khi dùng lại; không đánh giá accuracy/IDF1.

Chỉ nhận report complete, hash input/weights/output khớp, frame không mất,
clock tăng và source seconds đúng trạng thái timing đã khai báo.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import math
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data_preparation import new_audit_dir, probe_video, save_json, sha256_file


def inspect_report(path: Path, *, path_overrides: dict | None = None) -> dict:
    report = json.loads(path.read_text(encoding="utf-8"))
    # A copied demo bundle can relocate files without rewriting historical reports.
    # Fingerprints remain mandatory; only the four artifact locations may change.
    if path_overrides:
        allowed = {"input_video", "weights_path", "frame_cache", "output_video"}
        if set(path_overrides) - allowed:
            raise ValueError("Unsupported relocated artifact")
        report.update({key: str(value) for key, value in path_overrides.items()})
    if report.get("complete") is not True or report.get("schema_version") != 1:
        raise ValueError("Unsupported/incomplete run report")
    for path_key, hash_key in (("input_video", "input_sha256"), ("weights_path", "weights_sha256"),
                               ("frame_cache", "frame_cache_sha256"), ("output_video", "output_sha256")):
        if sha256_file(Path(report[path_key])) != report[hash_key]:
            raise ValueError(f"Fingerprint mismatch: {path_key}")
    if report["timing_evidence"]:
        if sha256_file(Path(report["timing_evidence"])) != report["timing_evidence_sha256"]:
            raise ValueError("Timing evidence changed")
    count, observations, empty, ids, previous_time = 0, 0, 0, set(), None
    cached_events = []
    with Path(report["frame_cache"]).open(encoding="utf-8") as stream:
        for line in stream:
            frame = json.loads(line)
            time_s = frame["video_time_s"]
            if (frame["frame_index"] != count or not math.isfinite(time_s) or time_s < 0
                    or (previous_time is not None and time_s <= previous_time)):
                raise ValueError(f"Frame gap or invalid clock at frame {count}")
            if frame["timing_status"] != report["timing_status"]:
                raise ValueError("Frame/report timing status differs")
            if report["timing_status"] == "verified_source":
                if frame["source_time_s"] != time_s or frame["timestamp_origin"] != "container_pts":
                    raise ValueError("Verified timing must retain container PTS")
            elif frame["source_time_s"] is not None:
                raise ValueError("Unverified source seconds exported")
            current_ids = []
            for item in frame["observations"]:
                if item["missing_mask"] != 0:
                    raise ValueError("Observed box marked missing")
                if report["mode"] == "detection" and item["track_id"] is not None:
                    raise ValueError("Detection cache must not invent track IDs")
                if item["track_id"] is not None:
                    current_ids.append(item["track_id"])
                    ids.add(item["track_id"])
            if len(set(current_ids)) != len(current_ids):
                raise ValueError("Duplicate track IDs in a frame")
            for item in frame["missing_tracks"]:
                if item["missing_mask"] != 1 or any("bbox" in key for key in item) or item["track_id"] in current_ids:
                    raise ValueError("Missing-track entry invents observations")
            count += 1
            observations += len(frame["observations"])
            empty += not frame["observations"]
            previous_time = time_s
            if report['mode'] == 'collision':
                if frame['collision']['frame_index'] != frame['frame_index']:
                    raise ValueError('Collision/cache frame mismatch')
                cached_events.extend(frame['collision']['new_events'])
    if (count != report["processed_frames"] or observations != report["observation_count"]
            or empty != report["empty_frames"] or len(ids) != report["unique_track_ids"]):
        raise ValueError("Cache/report counts differ")
    video = probe_video(Path(report["output_video"]))
    if (video["decoded_frames"] != count or video["width_px"] != report["width_px"]
            or video["height_px"] != report["height_px"] or abs(video["fps"]-report["container_fps"]) > .001):
        raise ValueError("Encoded MP4 differs from cached frames/size/FPS")
    if report['mode'] == 'collision':
        inspect_collision_events(report,cached_events)
    return dict(report=str(path), mode=report["mode"], frames=count, observations=observations,
                unique_track_ids=len(ids), timing_status=report["timing_status"],
                output_video=report["output_video"], frame_cache=report["frame_cache"],
                verified=True, accuracy_or_identity_quality_measured=False)


def inspect_collision_events(report, cached_events):
    """Validate event provenance/evidence without asserting the alerts are true."""
    output = Path(report['output_video'])
    path = output.with_suffix('.events.json')
    if sha256_file(path) != report['events_sha256']:
        raise ValueError('Collision event manifest fingerprint mismatch')
    manifest = json.loads(path.read_text())
    if (report.get('collision_detection_implemented') is not True
            or report.get('collision_experimental') is not True
            or manifest.get('experimental') is not True
            or manifest.get('score_is_probability') is not False
            or manifest['method'] != report['collision_method']
            or len(manifest['events']) != report['event_count']
            or len(cached_events) != report['event_count']):
        raise ValueError('Collision event count/method/scope mismatch')
    event_ids = set()
    for event, cached in zip(manifest['events'],cached_events):
        if (event['event_id'] in event_ids or any(event.get(k) != value for k,value in cached.items())
                or not 0 <= event['frame_index'] < report['processed_frames']
                or event.get('automatic') is not True or event.get('needs_review') is not True
                or event.get('score_is_probability') is not False
                or event['decision'] != 'suspected_collision'):
            raise ValueError('Collision event differs from causal frame cache')
        event_ids.add(event['event_id'])
        for kind in ('snapshot','clip'):
            artifact = (output.parent/event[kind]).resolve()
            if not artifact.is_relative_to(output.parent.resolve()) or sha256_file(artifact) != event[kind+'_sha256']:
                raise ValueError('Collision evidence path/fingerprint mismatch')
        clip = probe_video(output.parent/event['clip'])
        if clip['decoded_frames'] <= 0:
            raise ValueError('Empty collision evidence clip')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="Directory containing *.run.json, or one report")
    args = parser.parse_args()
    reports = [args.root] if args.root.is_file() else sorted(args.root.rglob("*.run.json"))
    if not reports:
        parser.error("No run reports found")
    results, errors = [], []
    for path in reports:
        try:
            result = inspect_report(path)
            results.append(result)
            print(f"VERIFIED {path.parent.name}: {result['mode']} {result['frames']} frames", flush=True)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append(dict(report=str(path), error=str(exc)))
            print(f"FAILED {path}: {exc}", flush=True)
    date = datetime.now(ZoneInfo("Asia/Bangkok")).date().isoformat()
    folder = new_audit_dir(ROOT / "outputs/audits", "inference_output_check_" + date)
    save_json(folder / "report.json", dict(complete=not errors, results=results, errors=errors,
                                          collision_metrics_measured=False))
    print(f"Audit: {folder / 'report.json'}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
