"""Replay cache B0/B1 qua evaluator chung, không chạy lại detector.

Đầu vào là CSV frame và config B1 đã lưu; đầu ra JSON alert/metric theo nhóm.
Chạy từ gốc project với --output tới đường dẫn mới để không ghi đè audit cũ.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.b0_diagnostics import CausalScoreFilter
from src.event_evaluator import evaluate
from src.storage_paths import output_path, require_output_path, artifact_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=output_path(ROOT, 'shared_evaluation', 'v002_event_replay', child='report.json'))
    parser.add_argument('--input', type=Path, help='Optional canonical JSON with videos, events and samples')
    parser.add_argument('--policy', type=Path, default=ROOT / 'configs/event_policy_v1.json')
    args = parser.parse_args()
    args.output = require_output_path(ROOT, args.output, 'shared_evaluation', allow_version_root=False)
    if args.output.exists():
        raise FileExistsError(f'Output already exists: {args.output}')
    policy = json.loads(args.policy.read_text(encoding='utf-8'))
    if args.input:
        data = json.loads(args.input.read_text(encoding='utf-8'))
        result = evaluate(data, policy)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False)
        print('Saved:', args.output)
        return
    cfgpath = ROOT / 'configs/b1_causal_diagnostics_v1.json'
    cfg = json.loads(cfgpath.read_text(encoding='utf-8'))
    base = artifact_path(ROOT, cfg['output']) / 'videos'
    modes = ('b0_on', 'kofn_on', 'ema_on')
    datasets = {m: {'videos': [], 'events': [], 'samples': []} for m in modes}
    elapsed = 0.0
    checked = 0
    for seq in cfg['sequences']:
        path = base / seq['sequence'] / 'frames.csv'
        with path.open(encoding='utf-8', newline='') as f:
            rows = list(csv.DictReader(f))
        if len(rows) != seq['frames']:
            raise ValueError(f'Unexpected cached frame count: {path}')
        fcfg = cfg['temporal_policy']
        filt = CausalScoreFilter(threshold=cfg['prediction_confidence'], k=fcfg['k'], n=fcfg['n'], alpha=fcfg['ema_alpha'])
        provenance = f"{path.relative_to(ROOT).as_posix()} sha256={hashlib.sha256(path.read_bytes()).hexdigest()}"
        for mode in modes:
            video = dict(video_id=seq['sequence'], camera_id=None,
                         fully_labeled_negative=seq['label'] == 'negative',
                         first_frame=0, last_frame=len(rows)-1,
                         source_timing_verified=bool(seq['source_fps_verified']),
                         source_fps=seq.get('display_fps') if seq['source_fps_verified'] else None,
                         duration_verified=bool(seq['source_fps_verified']),
                         duration_seconds=len(rows)/seq['display_fps'] if seq['source_fps_verified'] else None,
                         role=seq['role'], label_source=seq.get('label_origin'))
            datasets[mode]['videos'].append(video)
            if seq['label'] == 'reviewed_colliding_interval':
                for interval in seq['intervals']:
                    datasets[mode]['events'].append(dict(video_id=seq['sequence'], camera_id=None,
                        event_id=interval['event_id'], onset_frame=interval['start_frame'],
                        end_frame=interval['end_frame_inclusive'], status='unknown',
                        label_source='author VATIC object Colliding, user reviewed frame interval; scene event not verified'))
        for row in rows:
            start = time.perf_counter_ns()
            values = filt.step(int(row['source_frame']), float(row['max_confidence']))
            elapsed += (time.perf_counter_ns() - start) / 1e6
            checked += 1
            for mode in modes:
                if values[mode] != (row[mode] == 'True'):
                    raise ValueError(f'Filter replay differs from cache: {path} frame {row["source_frame"]}')
                label = 'negative' if row['temporal_label'] == 'negative' else 'unknown'
                datasets[mode]['samples'].append(dict(video_id=seq['sequence'], camera_id=None,
                    frame=int(row['source_frame']), score=float(values[mode]), label=label,
                    timestamp_s=float(row['source_timestamp_s']) if row['source_timestamp_s'] else None,
                    provenance=provenance))
    # CADP Colliding là thuộc tính đối tượng, chưa xác lập nhãn event scene
    # và phạm vi camera đầy đủ; giữ unknown để không tạo metric accident giả.
    role_results = {}
    for role in sorted({v['role'] for v in datasets['b0_on']['videos']}):
        role_results[role] = {}
        for mode, dataset in datasets.items():
            videos = [v for v in dataset['videos'] if v['role'] == role]
            ids = {v['video_id'] for v in videos}
            subset = {'videos': videos, 'events': [e for e in dataset['events'] if e['video_id'] in ids],
                      'samples': [r for r in dataset['samples'] if r['video_id'] in ids]}
            role_results[role][mode] = evaluate(subset, policy)['metrics']
    result = {'scope': 'exploratory replay of existing cached predictions; no independent event benchmark',
              'config': str(cfgpath.relative_to(ROOT)), 'frames_checked': checked,
              'filter_compute_ms_total': elapsed, 'filter_compute_ms_per_frame': elapsed/checked if checked else None,
              'timing_scope': 'CPU wall-clock filter.step only, single replay; excludes detector and I/O',
              'results': {m: evaluate(datasets[m], policy) for m in modes}, 'results_by_role': role_results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False)
    for mode in modes:
        print(mode, result['results'][mode]['metrics'])
    print('Filter ms/frame:', result['filter_compute_ms_per_frame'])
    print('Saved:', args.output)


if __name__ == '__main__':
    main()
