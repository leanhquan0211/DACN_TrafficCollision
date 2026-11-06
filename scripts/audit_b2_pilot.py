"""Đối chiếu cặp track B2 với hai bbox tác giả CADP ở các frame đã rà.

Đầu vào: JSONL B2 và CSV annotation tác giả; đầu ra: JSON từng frame và tổng
hợp pilot theo IoU được chỉ định. Đo kỹ thuật trên một ca, không tuning.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.motion_features import _iou
from src.storage_paths import output_path, require_output_path, artifact_path


def audit(frame_records, annotations, ids, first, last, threshold, width, height):
    """Gán tối đa hai GT bằng IoU, bắt buộc hai track khác nhau."""
    records = {r['frame']: r for r in frame_records}
    source = {}
    for row in annotations:
        frame, ident = int(row['source_frame']), int(row['gt_id'])
        if first <= frame <= last and ident in ids and row['visible'] == '1' and row['outside'] == '0' and row['colliding'] == '1':
            key = (frame, ident)
            if key in source:
                raise ValueError('Duplicate GT frame/ID')
            source[key] = [float(row['xmin'])/width, float(row['ymin'])/height,
                           float(row['xmax'])/width, float(row['ymax'])/height]
    output = []
    for frame in range(first, last+1):
        if frame not in records:
            raise ValueError(f'Missing prediction frame {frame}')
        if any((frame, i) not in source for i in ids):
            output.append({'frame': frame, 'status': 'gt_not_visible_or_unavailable'})
            continue
        candidates = []
        for a in records[frame]['tracks']:
            for b in records[frame]['tracks']:
                if a['track_id'] == b['track_id']:
                    continue
                ia, ib = _iou(source[(frame, ids[0])], a['bbox_norm']), _iou(source[(frame, ids[1])], b['bbox_norm'])
                if ia >= threshold and ib >= threshold:
                    candidates.append((ia+ib, ia, ib, a['track_id'], b['track_id']))
        if not candidates:
            output.append({'frame': frame, 'status': 'pair_not_both_matched'})
            continue
        _, ia, ib, a_id, b_id = sorted(candidates, key=lambda x: (-x[0], x[3], x[4]))[0]
        proposed = any(set(pair['track_ids']) == {a_id, b_id} for pair in records[frame]['candidates'])
        output.append({'frame': frame, 'status': 'candidate_present' if proposed else 'candidate_missing',
                       'gt_ids': list(ids), 'track_ids': [a_id, b_id], 'iou': [ia, ib]})
    return output


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--frames', type=Path, required=True)
    p.add_argument('--annotations', type=Path, default=artifact_path(ROOT,'outputs/audits/cadp_001407_clean_2/author_annotations.csv'))
    p.add_argument('--output', type=Path, default=output_path(ROOT,'data_audit','v006_b2_pair_audit',child='pair_audit.json'))
    p.add_argument('--iou', type=float, default=.5)
    args = p.parse_args()
    args.output = require_output_path(ROOT,args.output,'data_audit',allow_version_root=False)
    if not 0 < args.iou <= 1 or args.output.exists():
        p.error('IoU must be in (0,1] and output must be new')
    rows = [json.loads(line) for line in args.frames.read_text(encoding='utf-8').splitlines()]
    with args.annotations.open(encoding='utf-8', newline='') as f:
        annotations = list(csv.DictReader(f))
    per_frame = audit(rows, annotations, (0, 2), 96, 130, args.iou, 1280, 720)
    counts = {s: sum(r['status'] == s for r in per_frame) for s in ('candidate_present', 'candidate_missing', 'pair_not_both_matched', 'gt_not_visible_or_unavailable')}
    result = dict(scope='one reviewed CADP pilot; framewise IoU match, not independent benchmark',
                  frames=str(args.frames), frames_sha256=hashlib.sha256(args.frames.read_bytes()).hexdigest(),
                  annotations=str(args.annotations), annotations_sha256=hashlib.sha256(args.annotations.read_bytes()).hexdigest(),
                  source_gt_ids=[0, 2], interval=[96, 130], iou_threshold=args.iou,
                  counts=counts, per_frame=per_frame,
                  limitations='IoU assignment is an automatic proxy, not reviewed identity mapping; occlusion, annotation interpolation and IoU affect counts. No threshold tuning.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps(counts))


if __name__ == '__main__':
    main()
