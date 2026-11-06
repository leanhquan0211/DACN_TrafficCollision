"""Chẩn đoán lý do loại cặp GT đã ghép trong audit CADP, không dùng GT inference.

Đọc audit + cache và xuất CSV mới có khoảng cách, IoU, approach, tuổi, ROI,
ranking/cap và điều kiện lọc. Chỉ sử dụng cho ca phát triển đã có mapping.
"""
import argparse
import csv
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.motion_features import _iou
from src.storage_paths import output_path, require_output_path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--audit', type=Path, required=True)
    p.add_argument('--frames', type=Path, required=True)
    p.add_argument('--config', type=Path, default=ROOT/'configs/b2_motion_v1.json')
    p.add_argument('--output', type=Path, default=output_path(ROOT, 'data_audit', 'v003_b2_pilot_diagnosis', child='diagnosis.csv'))
    a = p.parse_args()
    a.output = require_output_path(ROOT, a.output, 'data_audit', allow_version_root=False)
    cfg = json.loads(a.config.read_text(encoding='utf-8'))
    audit = json.loads(a.audit.read_text(encoding='utf-8'))
    records = {r['frame']: r for r in (json.loads(line) for line in a.frames.read_text(encoding='utf-8').splitlines())}
    rows = []
    for match in audit['per_frame']:
        if match['status'] != 'candidate_missing':
            continue
        rec = records[match['frame']]
        track = {t['track_id']: t for t in rec['tracks']}
        x, y = (track[i] for i in match['track_ids'])
        dx = y['center_norm'][0]-x['center_norm'][0]
        dy = y['center_norm'][1]-x['center_norm'][1]
        distance = math.hypot(dx, dy)
        overlap = _iou(x['bbox_norm'], y['bbox_norm'])
        approach = -(dx*(y['vx_per_frame']-x['vx_per_frame'])+dy*(y['vy_per_frame']-x['vy_per_frame']))/distance if x['velocity_valid'] and y['velocity_valid'] and distance else None
        rows.append({'frame': match['frame'], 'gt_participants': match['gt_ids'], 'matched_tracks': match['track_ids'],
                     'gt_iou': match['iou'], 'pair_before_filter': True, 'distance': round(distance, 6),
                     'distance_limit': cfg['max_normalized_distance'], 'box_iou': round(overlap, 6),
                     'approach_per_frame': None if approach is None else round(approach, 6),
                     'track_ages': [x['track_age'], y['track_age']], 'confidences': [x['confidence'], y['confidence']],
                     'candidate_cap_reached': rec['candidate_cap_reached'], 'track_cap_reached': rec['track_cap_reached'],
                     'exclusion_reason': 'center_distance_gate' if distance > cfg['max_normalized_distance'] else 'inspect_other_gate',
                     'proposed_fix': 'allow overlapping boxes before distance gate' if overlap > 0 else 'inspect separately'})
    if not rows:
        raise ValueError('No missing matched pairs')
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open('x', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f'{len(rows)} rows: {a.output}')


if __name__ == '__main__':
    main()
