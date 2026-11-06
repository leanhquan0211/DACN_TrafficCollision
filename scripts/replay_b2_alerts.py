"""Replay B2 frames.jsonl qua FSM theo cặp; lưu alert và evidence metadata.

Chạy sau run_b2_motion.py, không gọi lại detector. Kết quả là demo kỹ thuật,
không phải các sự kiện va chạm đã xác nhận hoặc ảnh/clip evidence.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.alert_fsm import AlertFSM
from src.storage_paths import output_path, require_output_path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('frames', type=Path)
    p.add_argument('--output', type=Path, default=output_path(ROOT, 'shared_evaluation', 'v003_b2_alert_replay', child='events.json'))
    p.add_argument('--config', type=Path, default=ROOT/'configs/alert_fsm_v1.json')
    a = p.parse_args()
    a.output = require_output_path(ROOT, a.output, 'shared_evaluation', allow_version_root=False)
    if a.output.exists():
        raise FileExistsError(a.output)
    config = json.loads(a.config.read_text(encoding='utf-8'))
    fsm = AlertFSM(config)
    events = []
    frame_count = 0
    with a.frames.open(encoding='utf-8') as f:
        for line in f:
            row = json.loads(line)
            pairs = [dict(track_ids=c['track_ids'], score=c['rule_score']) for c in row['candidates']]
            events.extend(fsm.step(row['video_id'], row['frame'], pairs)['completed'])
            frame_count += 1
    events.extend(fsm.finish())
    result = {'scope': 'unvalidated heuristic alert demo; evidence contains metadata only',
              'input': str(a.frames), 'input_sha256': hashlib.sha256(a.frames.read_bytes()).hexdigest(),
              'config': config, 'frames': frame_count, 'events': events}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open('x', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False)
    print(f'{frame_count} frames, {len(events)} heuristic alerts; {a.output}')


if __name__ == '__main__':
    main()
