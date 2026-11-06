"""Chụp metadata dung lượng cho dashboard; không đọc nội dung, di chuyển hay xóa.

Chỉ quét các thư mục cho phép trong project, không theo symlink/junction.
Chạy thủ công khi cần làm mới; API chỉ đọc snapshot, không quét mỗi request.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.storage_paths import output_path, require_output_path
PATHS = [*(f'data_raw/{name}' for name in ('accident', 'tad', 'ua_detrac', 'cadp', 'sttad')),
         *(f'data_samples/{name}' for name in ('ua_detrac', 'cadp')),
         'data/processed', 'outputs/training', 'outputs/audits', 'outputs/kaggle',
         'outputs/baselines', 'outputs/shared_evaluations', 'outputs/system_evidence', 'outputs/data_audits']
VIDEO = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
IMAGE = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
ARCHIVE = {'.zip', '.7z', '.tar', '.gz'}


def scan(relative):
    root = ROOT/relative
    result = {'path': relative, 'exists': root.is_dir(), 'bytes': 0, 'files': 0,
              'video_files': 0, 'image_files': 0, 'archives': 0, 'errors': 0}
    if not result['exists']:
        return result
    stack = [root]
    while stack:
        folder = stack.pop()
        try:
            with os.scandir(folder) as entries:
                for entry in entries:
                    try:
                        if entry.is_symlink() or (hasattr(entry, 'is_junction') and entry.is_junction()):
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(Path(entry.path))
                        elif entry.is_file(follow_symlinks=False):
                            result['bytes'] += entry.stat(follow_symlinks=False).st_size
                            result['files'] += 1
                            ext = Path(entry.name).suffix.lower()
                            result['video_files'] += ext in VIDEO
                            result['image_files'] += ext in IMAGE
                            result['archives'] += ext in ARCHIVE
                    except OSError:
                        result['errors'] += 1
        except OSError:
            result['errors'] += 1
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=output_path(ROOT, 'data_audit', 'v002_project_inventory', child='project_explorer_inventory.json'))
    a = p.parse_args()
    output = a.output.resolve()
    require_output_path(ROOT, output, 'data_audit', allow_version_root=False)
    if output.exists():
        p.error('Output already exists; choose a new vNNN directory')
    snapshot = {'schema_version': 1, 'recorded_at': datetime.now(timezone.utc).isoformat(),
                'scope': 'filesystem metadata; file counts are not unique videos or independent events',
                'entries': [scan(path) for path in PATHS]}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)
    print(f"Đã kiểm kê {len(snapshot['entries'])} khu vực; {output}")


if __name__ == '__main__':
    main()
