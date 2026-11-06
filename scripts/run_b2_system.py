"""Chạy video → YOLO/ByteTrack → motion → FSM → ảnh và clip evidence.

Thực hiện hai lượt offline: cache track/feature rồi đọc lại video để dựng
evidence có giới hạn RAM. Không diễn giải tốc độ offline thành streaming FPS.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.storage_paths import output_path, require_output_path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('video', type=Path)
    p.add_argument('--output-dir', type=Path, default=output_path(ROOT, 'system_evidence', 'v003_b2_alerts'))
    p.add_argument('--device', default='cpu')
    p.add_argument('--motion-config', type=Path, default=ROOT/'configs/b2_motion_v2.json')
    p.add_argument('--fsm-config', type=Path, default=ROOT/'configs/alert_fsm_v2.json')
    a = p.parse_args()
    a.output_dir = require_output_path(ROOT, a.output_dir, 'system_evidence')
    if not a.video.is_file():
        p.error('Video not found')
    a.output_dir.mkdir(parents=True, exist_ok=False)
    track = a.output_dir/'tracking'
    evidence = a.output_dir/'evidence'
    stages = []
    commands = [
        [sys.executable, '-X', 'utf8', '-B', str(ROOT/'scripts/run_b2_motion.py'), str(a.video), '--output-dir', str(track), '--embedded-system-evidence', '--config', str(a.motion_config), '--max-frames', '1000000000', '--device', a.device],
        [sys.executable, '-X', 'utf8', '-B', str(ROOT/'scripts/render_b2_evidence.py'), '--video', str(a.video), '--frames', str(track/'frames.jsonl'), '--track-metadata', str(track/'metadata.json'), '--output-dir', str(evidence), '--config', str(a.fsm_config)]
    ]
    for label, cmd in zip(('tracking_motion', 'evidence_replay'), commands):
        start = time.perf_counter()
        subprocess.run(cmd, cwd=ROOT, check=True)
        stages.append({'stage': label, 'seconds': time.perf_counter()-start})
        if label == 'tracking_motion':
            meta = json.loads((track/'metadata.json').read_text(encoding='utf-8'))
            if not meta.get('source_complete'):
                raise RuntimeError('Video completeness could not be established; evidence not generated')
    events = json.loads((evidence/'events.json').read_text(encoding='utf-8'))
    elapsed = sum(s['seconds'] for s in stages)
    summary = {'status': 'completed', 'mode': 'offline two-pass', 'frames': meta['frames'],
               'heuristic_alerts': len(events['alerts']), 'stages': stages,
               'offline_total_seconds': elapsed, 'offline_fps_including_second_pass_and_startup': meta['frames']/elapsed,
               'limitations': 'not real-time streaming; no model accuracy/event benchmark; GPU synchronization and VRAM not measured'}
    (a.output_dir/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
