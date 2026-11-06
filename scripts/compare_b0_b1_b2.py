"""Replay B0/B1 và B2 trên cùng đoạn DETRAC âm đã dùng trước đây.

Đọc score B0/B1 và cache track B2, kiểm hash nguồn video rồi xuất metric cùng
evaluator/policy. Đây là chẩn đoán âm, không phải benchmark độc lập.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.event_evaluator import evaluate
from src.storage_paths import output_path, require_output_path, artifact_path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--b2-frames', type=Path, required=True)
    p.add_argument('--track-metadata', type=Path, required=True)
    p.add_argument('--output', type=Path, default=output_path(ROOT, 'shared_evaluation', 'v004_b0_b1_b2_comparison', child='report.json'))
    a = p.parse_args()
    a.output = require_output_path(ROOT, a.output, 'shared_evaluation', allow_version_root=False)
    if a.output.exists():
        raise FileExistsError(a.output)
    b1cfg = json.loads((ROOT/'configs/b1_causal_diagnostics_v1.json').read_text(encoding='utf-8'))
    sequence = next(s for s in b1cfg['sequences'] if s['sequence'] == 'MVI_20011')
    meta = json.loads(a.track_metadata.read_text(encoding='utf-8'))
    video_path = ROOT/sequence['path']
    if digest(video_path) != sequence['sha256'] or meta['video_sha256'] != sequence['sha256']:
        raise ValueError('Video fingerprint mismatch across B0/B1 and B2')
    replay_meta = json.loads((a.b2_frames.parent/'metadata.json').read_text(encoding='utf-8'))
    original_frames = a.track_metadata.parent/'frames.jsonl'
    if replay_meta.get('input_sha256') != digest(original_frames):
        raise ValueError('B2 replay is not linked to the specified tracking cache')
    b1path = artifact_path(ROOT,b1cfg['output'])/'videos/MVI_20011/frames.csv'
    with b1path.open(encoding='utf-8', newline='') as f:
        old = list(csv.DictReader(f))
    b2 = [json.loads(x) for x in a.b2_frames.read_text(encoding='utf-8').splitlines()]
    n = len(b2)
    if n == 0 or n > len(old) or any(r['frame'] != i or r['video_id'] != 'MVI_20011' for i, r in enumerate(b2)):
        raise ValueError('B2 frame coverage or video identity mismatch')
    if any(int(old[i]['source_frame']) != i or old[i]['temporal_label'] != 'negative' for i in range(n)):
        raise ValueError('B0/B1 cached frame coverage or label mismatch')
    if not sequence['source_fps_verified']:
        raise ValueError('Do not assume FPS source')
    fps = sequence['display_fps']
    b1_sha, b2_sha = digest(b1path), digest(a.b2_frames)
    video = {'video_id': 'MVI_20011', 'camera_id': None, 'first_frame': 0, 'last_frame': n-1,
             'fully_labeled_negative': True, 'duration_verified': True, 'duration_seconds': n/fps,
             'source_timing_verified': True, 'source_fps': fps, 'label_source': sequence['label_origin'],
             'role': 'training_source_operational_diagnostic'}
    policy = json.loads((ROOT/'configs/event_policy_v1.json').read_text(encoding='utf-8'))
    result = {}
    for mode in ('b0_on', 'kofn_on', 'ema_on', 'b2_rule'):
        samples = []
        for i in range(n):
            score = max((c['rule_score'] for c in b2[i]['candidates']), default=0.0) if mode == 'b2_rule' else float(old[i][mode] == 'True')
            samples.append({'video_id': 'MVI_20011', 'camera_id': None, 'frame': i, 'score': score,
                            'label': 'negative', 'timestamp_s': float(old[i]['source_timestamp_s']),
                            'provenance': b2_sha if mode == 'b2_rule' else b1_sha})
        result[mode] = evaluate({'videos': [video], 'events': [], 'samples': samples}, policy)
    report = {'scope': 'development negative clip; previously used for training/diagnostics, no recall or independent benchmark',
              'source_sha256': sequence['sha256'], 'b1_cache_sha256': b1_sha,
              'b2_cache_sha256': b2_sha, 'b2_tracking_metadata': str(a.track_metadata),
              'fps_source': sequence['fps_scope'], 'frames': n,
              'method_note': 'B0/B1 use locked accident detector; B2 uses separate vehicle detector/tracker and uncalibrated rule. All are converted to rising-edge scene alerts with policy event-edge-v1; scores are not equivalent probabilities.',
              'results': result}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open('x', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps({k: v['metrics'] for k, v in result.items()}, ensure_ascii=False))


if __name__ == '__main__':
    main()
