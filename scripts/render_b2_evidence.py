"""Tạo ảnh/clip evidence từ video sạch và cache B2 qua FSM theo cặp.

Chỉ giữ JPEG của cửa sổ trước/sau trong RAM; đầu ra là ảnh, MP4 ngắn và JSON.
FPS container chỉ dùng phát lại clip, không suy thời gian camera gốc.
"""
import argparse
from collections import deque
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.alert_fsm import AlertFSM
from src.storage_paths import require_output_path


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--video', type=Path, required=True)
    p.add_argument('--frames', type=Path, required=True)
    p.add_argument('--track-metadata', type=Path, required=True)
    p.add_argument('--output-dir', type=Path, required=True)
    p.add_argument('--config', type=Path, default=ROOT/'configs/alert_fsm_v2.json')
    p.add_argument('--max-pending', type=int, default=16)
    a = p.parse_args()
    a.output_dir = require_output_path(ROOT, a.output_dir, 'system_evidence')
    if not a.video.is_file() or a.max_pending < 1:
        p.error('Video must exist and max-pending must be positive')
    cfg = json.loads(a.config.read_text(encoding='utf-8'))
    source_meta = json.loads(a.track_metadata.read_text(encoding='utf-8'))
    if digest(a.video) != source_meta['video_sha256']:
        raise ValueError('Video hash differs from tracking source')
    a.output_dir.mkdir(parents=True, exist_ok=False)
    import cv2
    import numpy as np
    import shutil
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        raise RuntimeError('ffmpeg required for evidence MP4')
    cap = cv2.VideoCapture(str(a.video))
    if not cap.isOpened():
        raise RuntimeError('Cannot open evidence video')
    fps = float(cap.get(cv2.CAP_PROP_FPS))
    if not 0 < fps < 1000:
        raise ValueError('Valid presentation FPS required to encode preview')
    engine = AlertFSM(cfg)
    ring = deque(maxlen=cfg['pre_frames']+1)
    pending = {}
    completed = []
    count = 0

    def save_event(event):
        chunks = pending.pop(event['event_id'])
        name = f"event_{len(completed)+1:04d}_frame_{event['confirmation_frame']:06d}"
        image = a.output_dir/(name+'.jpg')
        clip = a.output_dir/(name+'.mp4')
        at_alert = next(data for index, data in chunks if index == event['confirmation_frame'])
        image.write_bytes(at_alert)
        cmd = [ffmpeg, '-hide_banner', '-loglevel', 'error', '-xerror', '-n', '-f', 'image2pipe',
               '-vcodec', 'mjpeg', '-r', str(fps), '-i', 'pipe:0', '-an', '-c:v', 'libx264',
               '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(clip)]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        _, err = proc.communicate(input=b''.join(data for _, data in chunks))
        if proc.returncode:
            raise RuntimeError('Evidence encoder failed: '+err.decode(errors='replace')[-1000:])
        verify = cv2.VideoCapture(str(clip))
        decoded = 0
        max_mae = 0.0
        while True:
            ok, decoded_frame = verify.read()
            if not ok:
                break
            if decoded >= len(chunks):
                raise RuntimeError('Evidence contains unexpected extra frame')
            reference = cv2.imdecode(np.frombuffer(chunks[decoded][1], dtype=np.uint8), 1)
            if reference is None or decoded_frame.shape != reference.shape:
                raise RuntimeError('Evidence frame dimensions differ')
            error = float(np.mean(np.abs(decoded_frame.astype(np.int16)-reference.astype(np.int16))))
            max_mae = max(max_mae, error)
            if error > 20:
                raise RuntimeError(f'Evidence frame mismatch at {decoded}: MAE={error:.2f}')
            decoded += 1
        verify.release()
        if decoded != len(chunks) or cv2.imdecode(np.frombuffer(at_alert, dtype=np.uint8), 1) is None:
            raise RuntimeError(f'Evidence could not be read back: {clip}, {decoded}/{len(chunks)}')
        entry = {k: v for k, v in event.items() if k != 'evidence_frames'}
        entry.update(image=image.name, clip=clip.name, evidence_first_frame=chunks[0][0],
                     evidence_last_frame=chunks[-1][0], evidence_frames_count=len(chunks), decoded_frames=decoded,
                     max_frame_mean_absolute_pixel_error=max_mae,
                     source_timestamp_s=None, source_timebase='frame index only',
                     preview_fps=fps, preview_fps_scope='source container presentation only',
                     source_video_sha256=source_meta['video_sha256'], weights_sha256=source_meta['weights_sha256'],
                     motion_config_sha256=source_meta['config_sha256'], fsm_config_sha256=digest(a.config))
        completed.append(entry)

    with a.frames.open(encoding='utf-8') as f:
        for line in f:
            row = json.loads(line)
            if row['frame'] != count:
                raise ValueError('Frame cache must be continuous and start at zero')
            ok, img = cap.read()
            if not ok or img is None:
                raise RuntimeError(f'Source cannot decode frame {count}')
            h, w = img.shape[:2]
            pairs = [dict(track_ids=c['track_ids'], score=c['rule_score']) for c in row['candidates']]
            result = engine.step(row['video_id'], count, pairs)
            alert_ids = {ident for event in result['emitted'] for ident in event['track_ids']}
            # Vẽ ID track tạm; bbox là dự đoán, không phải annotation tác giả.
            for track in row['tracks']:
                x1,y1,x2,y2 = track['bbox_norm']
                pt1, pt2 = (int(x1*w), int(y1*h)), (int(x2*w), int(y2*h))
                selected = track['track_id'] in alert_ids
                color = (0, 40, 255) if selected else (80, 200, 255)
                cv2.rectangle(img, pt1, pt2, color, 3 if selected else 1)
                cv2.putText(img, str(track['track_id']), pt1, cv2.FONT_HERSHEY_SIMPLEX, .5, color, 2 if selected else 1)
            cv2.putText(img, f'Frame {count} | heuristic only', (10, 25), cv2.FONT_HERSHEY_SIMPLEX, .6, (0, 220, 255), 2)
            ok, encoded = cv2.imencode('.jpg', img)
            if not ok:
                raise RuntimeError('Cannot encode evidence frame')
            chunk = (count, encoded.tobytes())
            for value in pending.values():
                value.append(chunk)
            ring.append(chunk)
            for event in result['emitted']:
                if len(pending) >= a.max_pending:
                    raise RuntimeError('Too many pending evidence clips; no events silently dropped')
                event['rule_features'] = next(c for c in row['candidates'] if c['track_ids'] == event['track_ids'])
                pending[event['event_id']] = list(ring)
            for event in result['completed']:
                save_event(event)
            count += 1
    cap.release()
    for event in engine.finish():
        save_event(event)
    result = {'status': 'completed', 'scope': 'offline heuristic alert demo; not collision ground truth',
              'video': str(a.video), 'frames_input': str(a.frames), 'frames_sha256': digest(a.frames),
              'source_metadata': str(a.track_metadata), 'fsm_policy': cfg, 'frames': count,
              'alerts': completed}
    (a.output_dir/'events.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    print(f'{count} frames, {len(completed)} heuristic alerts; {a.output_dir}')


if __name__ == '__main__':
    main()
