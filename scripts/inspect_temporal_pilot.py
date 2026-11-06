"""Kiểm một clip ACCIDENT làm development: hash, giải mã và frame impact.

Metadata chỉ cung cấp mốc tiếp xúc; tool không tự tạo event end hoặc negative.
Đầu ra là bảng/bằng chứng hình tại ba frame, không gán clip làm held-out.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.audit_accident_public import inspect_video, check_timestamps
from src.storage_paths import output_path, require_output_path
METADATA_SHA256 = 'a3d06073353a7fedff140b652d025135f017860a240cad693990f5288c6c0ec9'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_is_development_eligible(row):
    """Chỉ chấp nhận clip tác giả xếp train ở cả hai split công bố."""
    return row.get('split_in_distribution') == 'train' and row.get('split_geo_aware') == 'train'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--video-id', required=True)
    p.add_argument('--inventory', type=Path, required=True)
    p.add_argument('--output-dir', type=Path, default=output_path(ROOT,'data_audit','v008_temporal_pilot_inspection'))
    a = p.parse_args()
    a.output_dir = require_output_path(ROOT,a.output_dir,'data_audit')
    inv = json.loads(a.inventory.read_text(encoding='utf-8'))
    if a.video_id not in inv.get('source_train_only_development_candidates', []):
        raise ValueError('ID must be in screened source-train development candidates; source test is reserved')
    raw = ROOT/'data_raw/accident/public_selected'
    metadata, receipts = raw/'metadata-real.csv', raw/'download_receipts.json'
    if digest(metadata) != METADATA_SHA256:
        raise ValueError('Metadata fingerprint differs from pinned ACCIDENT v9')
    with metadata.open(encoding='utf-8-sig', newline='') as f:
        found = [r for r in csv.DictReader(f) if Path(r['path']).stem == a.video_id]
    if len(found) != 1:
        raise ValueError('Clip must have one matching metadata row')
    item = found[0]
    if not source_is_development_eligible(item):
        raise ValueError('Source test split cannot be opened for development')
    video = raw/item['path']
    if not video.resolve().is_relative_to(raw.resolve()) or not video.is_file():
        raise ValueError('Unsafe or missing video')
    receipt = json.loads(receipts.read_text(encoding='utf-8')).get(item['path'])
    if not receipt or receipt['sha256'] != digest(video) or receipt['size_bytes'] != video.stat().st_size:
        raise ValueError('Video does not match recorded receipt')
    import cv2
    import numpy as np
    onset, total = int(item['accident_frame']), int(item['no_frames'])
    coords = [float(item[k]) for k in ('x1', 'y1', 'x2', 'y2')]
    if not (0 <= onset < total and 0 <= coords[0] < coords[2] <= 1 and 0 <= coords[1] < coords[3] <= 1):
        raise ValueError('Invalid author frame/bbox metadata')
    a.output_dir.mkdir(parents=True, exist_ok=False)
    # Tái dùng audit gốc: lưu sai lệch no_frames, rồi kiểm mapping PTS bằng
    # OpenCV và ffprobe; không tự coi metadata là số frame thực.
    info, samples = inspect_video(video, item)
    count = info['decoded_frames']
    probe = shutil.which('ffprobe')
    if not probe:
        raise RuntimeError('ffprobe required for independent PTS mapping check')
    proc = subprocess.run([probe, '-v', 'error', '-select_streams', 'v:0', '-show_frames',
                           '-show_entries', 'frame=best_effort_timestamp_time', '-of', 'json', str(video)],
                          check=True, capture_output=True, text=True, timeout=60)
    points = [float(v['best_effort_timestamp_time']) for v in json.loads(proc.stdout)['frames']]
    independent = check_timestamps(points, onset, float(item['accident_time']))
    if len(points) != count or not info['pts_mapping_verified'] or not independent['pts_mapping_verified']:
        raise ValueError('Impact frame mapping could not be verified across PTS decoders')
    selected = {i: samples[i] for i in (max(0, onset-1), onset, min(count-1, onset+1)) if i in samples}
    presentation_fps = info['container_fps']
    width, height = int(item['width']), int(item['height'])
    if any(f.shape[:2] != (height, width) for f in selected.values()):
        raise ValueError('Dimensions disagree with author metadata')
    panels = []
    for index, frame in sorted(selected.items()):
        if index == onset:
            x1,y1,x2,y2 = coords
            cv2.rectangle(frame, (int(x1*width),int(y1*height)), (int(x2*width),int(y2*height)), (0,0,255), 4)
        cv2.putText(frame, f'frame {index}'+(' author impact bbox' if index == onset else ' unlabelled'),
                    (15,35), cv2.FONT_HERSHEY_SIMPLEX, .8, (0,255,255), 2)
        panels.append(cv2.resize(frame, (640, int(height*640/width))))
    ok, png = cv2.imencode('.png', np.concatenate(panels, axis=1))
    if not ok:
        raise RuntimeError('Cannot encode inspection image')
    (a.output_dir/'impact_comparison.png').write_bytes(png.tobytes())
    result = {'role': 'development_debug_only_not_heldout', 'dataset': 'ACCIDENT v9',
              'video_id': a.video_id, 'video': str(video.relative_to(ROOT)), 'video_sha256': digest(video),
              'metadata_sha256': digest(metadata), 'source_metadata': item, 'decoded_frames': count,
              'metadata_no_frames': total, 'frame_count_delta': count-total,
              'opencv_pts_check': info, 'ffprobe_pts_check': independent,
              'impact_frame': onset, 'author_bbox_norm': coords, 'event_end': None,
              'frame_timebase': 'zero-based frame index; source camera FPS unverified',
              'container_presentation_fps': presentation_fps, 'timing_verified': False,
              'duplicate_status': 'not in checked registry name/group; byte and perceptual duplicate screening incomplete',
              'label_scope': 'author impact frame/bbox only; other frames unknown',
              'image': 'impact_comparison.png'}
    (a.output_dir/'inspection.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'video_id': a.video_id, 'frames': count, 'impact_frame': onset, 'output': str(a.output_dir)}))


if __name__ == '__main__':
    main()
