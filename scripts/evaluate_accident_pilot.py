"""Kiểm scene score B2 đúng frame impact tác giả trên clip development.

Đây là probe điểm onset với tolerance 0 frame, không suy end, negative hay
thời gian camera; không phải event benchmark hoặc phép chọn ngưỡng.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.event_evaluator import evaluate
from src.storage_paths import output_path, require_output_path


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inspection', type=Path, required=True)
    p.add_argument('--frames', type=Path, required=True)
    p.add_argument('--tracking-metadata', type=Path, required=True)
    p.add_argument('--output', type=Path, default=output_path(ROOT, 'shared_evaluation', 'v005_accident_pilot', child='report.json'))
    a = p.parse_args()
    a.output = require_output_path(ROOT, a.output, 'shared_evaluation', allow_version_root=False)
    inspection = json.loads(a.inspection.read_text(encoding='utf-8'))
    meta = json.loads(a.tracking_metadata.read_text(encoding='utf-8'))
    if inspection['role'] != 'development_debug_only_not_heldout' or inspection['video_sha256'] != meta['video_sha256']:
        raise ValueError('Pilot source role or video fingerprint mismatch')
    if a.frames.resolve() != (a.tracking_metadata.parent/'frames.jsonl').resolve():
        raise ValueError('Frames must belong to specified tracking metadata directory')
    if not inspection['opencv_pts_check']['pts_mapping_verified'] or not inspection['ffprobe_pts_check']['pts_mapping_verified']:
        raise ValueError('Impact point PTS mapping is unverified')
    rows = [json.loads(x) for x in a.frames.read_text(encoding='utf-8').splitlines()]
    if len(rows) != inspection['decoded_frames'] or any(r['frame'] != i or r['video_id'] != inspection['video_id'] for i, r in enumerate(rows)):
        raise ValueError('Frame sequence/source mismatch')
    # 0 frame là phép kiểm đúng tại contact, không phải event end của tác giả.
    policy = {'version': 'impact-frame-only-development-v1', 'threshold': .5,
              'cooldown_frames': 0, 'post_onset_tolerance_frames': 0}
    onset = inspection['impact_frame']
    vid = inspection['video_id']
    frames_sha = sha(a.frames)
    data = {'videos': [{'video_id': vid, 'camera_id': None, 'source_timing_verified': False}],
            'events': [{'video_id': vid, 'camera_id': None, 'event_id': vid+':impact',
                        'onset_frame': onset, 'end_frame': None, 'status': 'verified',
                        'label_source': 'ACCIDENT v9 author impact point; PTS mapping checked'}],
            'samples': [{'video_id': vid, 'camera_id': None, 'frame': r['frame'],
                         'score': max((c['rule_score'] for c in r['candidates']), default=0.0),
                         'label': 'positive' if r['frame'] == onset else 'unknown',
                         'provenance': frames_sha} for r in rows]}
    evaluated = evaluate(data, policy)
    # Một điểm onset và vùng còn lại unknown không đủ để báo precision/F1 hay
    # recall tổng quát; giữ match gốc để truy vết, ẩn các tỷ lệ dễ hiểu nhầm.
    for key in ('precision', 'recall', 'f1'):
        evaluated['metrics'][key] = None
    result = {'scope': 'single development clip exact-impact-point probe; not event benchmark',
              'inspection_sha256': sha(a.inspection), 'tracking_sha256': frames_sha,
              'policy_note': 'zero-frame post-onset tolerance; author did not provide an event end',
              'metric_note': 'Precision/recall/F1 suppressed: one development onset with unknown coverage elsewhere.',
              'result': evaluated}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open('x', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps(result['result']['metrics'], ensure_ascii=False))


if __name__ == '__main__':
    main()
