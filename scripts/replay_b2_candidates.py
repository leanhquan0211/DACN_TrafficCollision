"""Replay candidate B2 từ cache track, không chạy lại YOLO hoặc ByteTrack.

Đầu vào JSONL từng frame và config; đầu ra JSONL cùng cấu trúc, metadata
hash và thời gian tính feature. Chỉ dùng cache liên tục của một video.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.motion_features import MotionFeatures
from src.storage_paths import output_path, require_output_path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--config', type=Path, required=True)
    p.add_argument('--output-dir', type=Path, default=output_path(ROOT, 'baseline', 'v004_candidate_replay', baseline='B2'))
    a = p.parse_args()
    a.output_dir = require_output_path(ROOT, a.output_dir, 'baseline', baseline='B2')
    config = json.loads(a.config.read_text(encoding='utf-8'))
    a.output_dir.mkdir(parents=True, exist_ok=False)
    engine = MotionFeatures(config)
    elapsed_ns = 0
    count = pairs = changed = 0
    video = None
    with a.input.open(encoding='utf-8') as src, (a.output_dir/'frames.jsonl').open('x', encoding='utf-8') as dst:
        for line in src:
            old = json.loads(line)
            if video is None:
                video = old['video_id']
            if old['video_id'] != video:
                raise ValueError('Input cache must contain exactly one video')
            observations = [{k: t[k] for k in ('track_id', 'class_name', 'confidence', 'bbox_norm')} for t in old['tracks']]
            start = time.perf_counter_ns()
            row = engine.step(old['frame'], observations)
            elapsed_ns += time.perf_counter_ns()-start
            row.update({k: old.get(k) for k in ('video_id', 'camera_id', 'timestamp_s', 'timebase', 'detections_without_id')})
            changed += row['candidates'] != old['candidates']
            pairs += len(row['candidates'])
            count += 1
            dst.write(json.dumps(row, ensure_ascii=False, allow_nan=False)+'\n')
    if not count:
        raise ValueError('Empty cache')
    meta = {'status': 'completed', 'input': str(a.input), 'input_sha256': digest(a.input),
            'config': config, 'config_sha256': digest(a.config), 'frames': count,
            'candidate_rows': pairs, 'candidates_per_frame': pairs/count,
            'frames_changed_vs_input': changed, 'feature_ms_total': elapsed_ns/1e6,
            'feature_ms_per_frame': elapsed_ns/count/1e6,
            'timing_scope': 'one CPU replay; feature/candidate calculation only, excludes decode/tracking'}
    (a.output_dir/'metadata.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
