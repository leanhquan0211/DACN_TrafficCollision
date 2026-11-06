"""Di chuyển output đã đối chiếu theo từng nhóm và kiểm hash/rollback.

Đầu vào là artifact local và registry mapping; đầu ra là manifest metadata dưới
outputs/audits/storage_migration_v1. Chỉ chạy khi chủ động gọi --apply; không
đọc dataset raw, không copy cross-volume hoặc sửa snapshot thí nghiệm.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / 'outputs/audits/storage_migration_v1/manifest.json'
GROUPS = {
    'b2_v1': ('outputs/audits/b2_motion_v1', 'outputs/baselines/03_b2_motion_rules/v001_motion_pilot'),
    'b2_v2': ('outputs/audits/b2_motion_v2', 'outputs/baselines/03_b2_motion_rules/v002_overlap_fix'),
    'shared_events': ('outputs/audits/event_evaluator_v1', 'outputs/shared_evaluations/v001_event_evaluator'),
    'system_evidence': ('outputs/audits/b2_system_v2', 'outputs/system_evidence/v001_b2_alerts'),
    'detrac_audit': ('outputs/audits/detrac_preparation', 'outputs/data_audits/v001_detrac_preparation'),
}
PLACEHOLDER_FLAGS = 0x1000 | 0x40000 | 0x400000  # offline / recall on open / recall on data access


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for part in iter(lambda: f.read(1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()


def safe(root: Path, relative: str) -> Path:
    """Chỉ thao tác dưới outputs trong project thật; không theo junction/symlink."""
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts or path.parts[0] != 'outputs':
        raise ValueError(f'Unsafe path: {relative}')
    candidate = root / path
    if not candidate.resolve().is_relative_to(root.resolve()):
        raise ValueError(f'Path escaped project: {relative}')
    return candidate


def scan(root: Path, source: str) -> dict:
    folder = safe(root, source)
    if not folder.is_dir() or folder.is_symlink():
        raise FileNotFoundError(source)
    records = []
    stack = [folder]
    while stack:
        current = stack.pop()
        if current.is_symlink() or (hasattr(current, 'is_junction') and current.is_junction()):
            raise RuntimeError(f'Link/junction trong source: {current}')
        for item in current.iterdir():
            if item.is_symlink() or (hasattr(item, 'is_junction') and item.is_junction()):
                raise RuntimeError(f'Link/junction trong source: {item}')
            if len(str(item.resolve())) > 240:
                raise RuntimeError(f'Đường dẫn quá dài: {item}')
            if item.is_dir():
                stack.append(item)
            elif item.is_file():
                st = item.stat()
                if getattr(st, 'st_file_attributes', 0) & PLACEHOLDER_FLAGS:
                    raise RuntimeError(f'File OneDrive chưa có đủ trên máy: {item}')
                records.append({'path': item.relative_to(folder).as_posix(), 'bytes': st.st_size,
                                'sha256': digest(item)})
            else:
                raise RuntimeError(f'Mục không phải file/thư mục thường: {item}')
    records.sort(key=lambda x: x['path'])
    return {'files': records, 'file_count': len(records), 'bytes': sum(x['bytes'] for x in records)}


def exclusive_read(path: Path):
    """Trên Windows, thử mở không chia sẻ để phát hiện file đang được giữ."""
    if os.name != 'nt':
        with path.open('rb'):
            return
    import ctypes
    kernel = ctypes.windll.kernel32
    kernel.CreateFileW.restype = ctypes.c_void_p
    handle = kernel.CreateFileW(str(path), 0x80000000, 0, None, 3, 0, None)
    if handle == ctypes.c_void_p(-1).value:
        raise OSError(f'File đang bị khóa hoặc không mở được: {path}')
    kernel.CloseHandle(ctypes.c_void_p(handle))


def preflight(root: Path, name: str, item: dict):
    source, dest = safe(root, item['source']), safe(root, item['destination'])
    if source.exists() and dest.exists():
        raise FileExistsError(f'Cả source và destination tồn tại: {name}')
    if not source.is_dir() or dest.exists():
        raise RuntimeError(f'Không ở trạng thái trước move: {name}')
    existing_parent = dest.parent
    while not existing_parent.exists():
        existing_parent = existing_parent.parent
    if source.stat().st_dev != existing_parent.stat().st_dev:
        raise RuntimeError('Khác filesystem; công cụ không copy')
    for record in item['files']:
        path = source / record['path']
        exclusive_read(path)
        if path.stat().st_size != record['bytes'] or digest(path) != record['sha256']:
            raise RuntimeError(f'Source đổi từ khi tạo manifest: {path}')


def verify_one(root: Path, item: dict, where: str) -> dict:
    folder = safe(root, item[where])
    other = safe(root, item['source' if where == 'destination' else 'destination'])
    if not folder.is_dir() or other.exists():
        raise RuntimeError(f'Sai vị trí sau move/rollback: {folder}')
    actual = scan(root, item[where])
    if actual['files'] != item['files']:
        raise RuntimeError(f'Fingerprint không khớp: {folder}')
    return {'path': item[where], 'files': actual['file_count'], 'bytes': actual['bytes'], 'verified': True}


def save(manifest: dict):
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    temp = MANIFEST.with_suffix('.json.tmp')
    temp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(MANIFEST)


def load_or_create() -> dict:
    registry = ROOT / 'data/registries/project_explorer.json'
    if registry.is_file():
        mapping = json.loads(registry.read_text(encoding='utf-8'))
        aliases = {(row['old'], row['new']) for row in mapping.get('path_aliases', [])}
        if not set(GROUPS.values()).issubset(aliases):
            raise RuntimeError('Registry path_aliases không khớp kế hoạch move')
        protected = [Path(row['path']) for row in mapping.get('protected_paths', [])]
        for old, new in GROUPS.values():
            if any(Path(old) == p or p in Path(old).parents or Path(new) == p or p in Path(new).parents for p in protected):
                raise RuntimeError(f'Kế hoạch chạm đường dẫn PROTECT: {old} → {new}')
    if MANIFEST.exists():
        data = json.loads(MANIFEST.read_text(encoding='utf-8'))
        if data.get('schema_version') != 1 or {k: (v['source'], v['destination']) for k, v in data['groups'].items()} != GROUPS:
            raise RuntimeError('Manifest không khớp mapping khóa; dừng để kiểm tra')
        return data
    groups = {}
    for name, (old, new) in GROUPS.items():
        if safe(ROOT, new).exists():
            raise FileExistsError(new)
        details = scan(ROOT, old)
        groups[name] = {'source': old, 'destination': new, **details, 'state': 'planned'}
    data = {'schema_version': 1, 'created_at': datetime.now(timezone(timedelta(hours=7))).isoformat(),
            'mode': 'same_filesystem_rename_only', 'groups': groups}
    save(data)
    return data


def main():
    p = argparse.ArgumentParser(description=__doc__)
    actions = p.add_mutually_exclusive_group(required=True)
    for action in ('plan', 'apply', 'verify', 'rollback'):
        actions.add_argument('--' + action, action='store_true')
    p.add_argument('--group', choices=GROUPS, help='Bắt buộc cho apply/rollback để kiểm từng giai đoạn')
    args = p.parse_args()
    if (args.apply or args.rollback) and not args.group:
        p.error('--apply/--rollback yêu cầu --group')
    if args.plan:
        rows = []
        for name, (old, new) in GROUPS.items():
            source, dest = safe(ROOT, old), safe(ROOT, new)
            size = scan(ROOT, old) if source.is_dir() else None
            rows.append({'group': name, 'source': old, 'destination': new, 'source_exists': source.is_dir(),
                         'destination_exists': dest.exists(), 'file_count': size['file_count'] if size else None,
                         'bytes': size['bytes'] if size else None})
        print(json.dumps(rows, ensure_ascii=False, indent=2)); return
    manifest = load_or_create()
    selected = [args.group] if args.group else list(GROUPS)
    for name in selected:
        item = manifest['groups'][name]
        source, dest = safe(ROOT, item['source']), safe(ROOT, item['destination'])
        if args.apply:
            if not source.exists() and dest.exists():
                verify_one(ROOT, item, 'destination')  # phục hồi state sau crash giữa rename/save
            elif item['state'] == 'applied':
                verify_one(ROOT, item, 'destination')
            else:
                preflight(ROOT, name, item)
                dest.parent.mkdir(parents=True, exist_ok=True)
                source.rename(dest)  # atomic same-volume; không copy hay xóa nội dung
                try:
                    verify_one(ROOT, item, 'destination')
                except Exception:
                    if not source.exists() and dest.exists():
                        dest.rename(source)
                    raise
            item['state'] = 'applied'; save(manifest)
            print(json.dumps({'group': name, **verify_one(ROOT, item, 'destination')}, ensure_ascii=False))
        elif args.verify:
            where = 'destination' if dest.exists() and not source.exists() else 'source'
            print(json.dumps({'group': name, 'state': item['state'], **verify_one(ROOT, item, where)}, ensure_ascii=False))
        else:
            verify_one(ROOT, item, 'destination')
            if source.exists():
                raise FileExistsError(source)
            dest.rename(source)
            verify_one(ROOT, item, 'source')
            item['state'] = 'rolled_back'; save(manifest)
            print(json.dumps({'group': name, 'rolled_back': True, 'source': item['source']}, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError) as exc:
        print(f'BLOCKED: {exc}', file=sys.stderr)
        raise SystemExit(1)
