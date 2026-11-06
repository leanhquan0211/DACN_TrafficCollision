"""Chạy thử YOLO xe → ByteTrack → đặc trưng cặp và luật B2 trên video sạch.

Đầu vào là video và config; đầu ra là JSONL theo frame cùng metadata/hash.
Chỉ chạy khi cần cache mới. Điểm luật dùng để kiểm luồng, chưa kết luận va chạm.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.motion_features import MotionFeatures
from src.video_pipeline import VEHICLE_NAMES
from src.storage_paths import output_path, require_output_path


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for part in iter(lambda: f.read(1024*1024), b''):
            h.update(part)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('video', type=Path)
    p.add_argument('--output-dir', type=Path, default=output_path(ROOT, 'baseline', 'v003_motion_replay', baseline='B2'))
    p.add_argument('--embedded-system-evidence', action='store_true', help=argparse.SUPPRESS)
    p.add_argument('--config', type=Path, default=ROOT/'configs/b2_motion_v1.json')
    p.add_argument('--max-frames', type=int, default=150)
    p.add_argument('--device', default='auto')
    args = p.parse_args()
    args.output_dir = require_output_path(ROOT, args.output_dir, 'system_evidence' if args.embedded_system_evidence else 'baseline', baseline=None if args.embedded_system_evidence else 'B2')
    if not args.video.is_file() or args.max_frames <= 0:
        p.error('Video must exist and max-frames must be positive')
    cfg = json.loads(args.config.read_text(encoding='utf-8'))
    model_path = ROOT / cfg['model']
    if not model_path.is_file():
        raise FileNotFoundError('Vehicle weights missing; no implicit download')
    args.output_dir.mkdir(parents=True, exist_ok=False)
    os.environ.setdefault('YOLO_CONFIG_DIR', str(ROOT/'configs/ultralytics'))
    import cv2
    import torch
    from ultralytics import YOLO
    import ultralytics

    device = ('0' if torch.cuda.is_available() else 'cpu') if args.device == 'auto' else args.device
    model = YOLO(str(model_path))  # Model mới cho mỗi video: không chia sẻ ID tracker.
    classes = [int(k) for k, v in model.names.items() if str(v).lower() in VEHICLE_NAMES]
    cap = cv2.VideoCapture(str(args.video))
    if not cap.isOpened():
        raise RuntimeError('Cannot open video')
    features = MotionFeatures(cfg)
    advertised_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_count = pair_count = invalid = 0
    termination = 'frame_limit'
    start = time.perf_counter()
    frame_path = args.output_dir/'frames.jsonl'
    with frame_path.open('x', encoding='utf-8') as out:
        while frame_count < args.max_frames:
            ok, frame = cap.read()
            if not ok:
                termination = 'decoder_end_or_error'
                break
            height, width = frame.shape[:2]
            result = model.track(frame, persist=True, tracker=cfg['tracker'], device=device,
                                 imgsz=cfg['imgsz'], classes=classes, verbose=False)[0]
            observations = []
            boxes = result.boxes
            detections_without_id = len(boxes) if boxes is not None and boxes.id is None else 0
            if boxes is not None and boxes.id is not None:
                for xyxy, ident, cls, conf in zip(boxes.xyxy.cpu().tolist(), boxes.id.cpu().tolist(), boxes.cls.cpu().tolist(), boxes.conf.cpu().tolist()):
                    x1, y1, x2, y2 = xyxy
                    box = [max(0., min(1., x1/width)), max(0., min(1., y1/height)),
                           max(0., min(1., x2/width)), max(0., min(1., y2/height))]
                    if box[0] >= box[2] or box[1] >= box[3]:
                        invalid += 1
                        continue
                    observations.append(dict(track_id=int(ident), class_name=str(model.names[int(cls)]), confidence=conf, bbox_norm=box))
            item = features.step(frame_count, observations)
            # FPS container chỉ mô tả file; không suy timing gốc nếu chưa xác minh.
            item.update(video_id=args.video.stem, camera_id=None, timestamp_s=None, timebase='frame_index_only',
                        detections_without_id=detections_without_id)
            pair_count += len(item['candidates'])
            out.write(json.dumps(item, ensure_ascii=False, allow_nan=False)+'\n')
            frame_count += 1
    cap.release()
    source_complete = advertised_frames > 0 and frame_count == advertised_frames
    status = ('completed' if source_complete else
              'partial_frame_limit' if termination == 'frame_limit' and frame_count > 0 else 'incomplete_decode')
    meta = dict(status=status, source_complete=source_complete, video=str(args.video), video_sha256=sha(args.video),
                weights=str(model_path), weights_sha256=sha(model_path), config=cfg,
                config_sha256=sha(args.config), torch_version=torch.__version__,
                ultralytics_version=ultralytics.__version__, opencv_version=cv2.__version__,
                device=device, frames=frame_count, advertised_frames=advertised_frames,
                termination=termination, candidate_rows=pair_count, invalid_boxes=invalid,
                elapsed_seconds=time.perf_counter()-start, timing='frame index only, original timing unverified',
                scope='exploratory motion features and heuristic score; not collision predictions or benchmark')
    (args.output_dir/'metadata.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
