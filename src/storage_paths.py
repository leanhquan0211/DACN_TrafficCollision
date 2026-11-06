"""Registry và đường dẫn thống nhất cho output mới cùng artifact lịch sử.

Hàm chỉ trả Path, không tạo thư mục hoặc sửa experiment/provenance. Output mới
phải nằm trong một trong bốn nhánh canonical và có tên vNNN_short_description.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

VERSION = re.compile(r'v\d{3}_[a-z0-9_]+\Z')
RUN_ID = re.compile(r'[A-Za-z0-9_-]{1,100}\Z')
FALLBACK_LAYOUT = {'baseline': 'outputs/baselines', 'shared_evaluation': 'outputs/shared_evaluations',
                   'system_evidence': 'outputs/system_evidence', 'data_audit': 'outputs/data_audits',
                   'legacy_archive': 'outputs/_legacy'}
FALLBACK_BASELINES = {'B0': '01_b0_image_detection', 'B1': '02_b1_temporal_filter',
                      'B2': '03_b2_motion_rules', 'T0': '04_t0_mlp', 'B3': '05_b3_gru'}


def registry_data(root: Path) -> dict:
    """Portable bundle/fixture không có registry vẫn đọc được theo fallback."""
    path = root.resolve() / 'data/registries/project_explorer.json'
    if not path.is_file():
        return {'storage_layout': FALLBACK_LAYOUT, 'runs': [], 'artifacts': [], 'path_aliases': [],
                'legacy_collections': [{'path': 'outputs/training', 'category': 'baseline'},
                                       {'path': 'outputs/audits', 'category': 'data_audit'},
                                       {'path': 'outputs/kaggle', 'category': 'kaggle'}]}
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict) or value.get('schema_version') != 1:
        raise ValueError('Artifact registry schema invalid')
    return value


def inside(root: Path, reference: str | Path) -> Path:
    root = root.resolve()
    path = Path(reference)
    if '..' in path.parts:
        raise ValueError('Parent traversal is not an artifact path')
    result = (path if path.is_absolute() else root / path).resolve()
    if not result.is_relative_to(root):
        raise ValueError(f'Artifact path outside project: {reference}')
    return result


def storage_root(root: Path, category: str, baseline: str | None = None) -> Path:
    registry = registry_data(root)
    if category not in {'baseline', 'shared_evaluation', 'system_evidence', 'data_audit'}:
        raise ValueError(f'Unknown output category: {category}')
    relative = registry.get('storage_layout', FALLBACK_LAYOUT).get(category)
    if not isinstance(relative, str) or not relative.startswith('outputs/'):
        raise ValueError('Unsafe storage root in registry')
    target = inside(root, relative)
    if category == 'baseline':
        matches = [r.get('folder') or FALLBACK_BASELINES.get(baseline) for r in registry.get('baseline_folders', []) if r.get('id') == baseline]
        if not matches and baseline in FALLBACK_BASELINES:
            matches = [FALLBACK_BASELINES[baseline]]
        if len(matches) != 1 or not matches[0]:
            raise ValueError('Baseline folder missing or duplicate in registry')
        target = inside(root, target / matches[0])
    elif baseline is not None:
        raise ValueError('Shared output cannot be assigned to one baseline')
    return target


def output_path(root: Path, category: str, version: str, *, baseline: str | None = None,
                child: str | Path | None = None) -> Path:
    """Dựng đường dẫn chuẩn; version phải được khai báo, không suy từ mtime."""
    if not VERSION.fullmatch(version):
        raise ValueError('Version must be vNNN_short_description')
    target = inside(root, storage_root(root, category, baseline) / version)
    return inside(root, target / child) if child is not None else target


def require_output_path(root: Path, reference: str | Path, category: str,
                        *, baseline: str | None = None, allow_version_root: bool = True) -> Path:
    """Từ chối ghi vào outputs/training, audits, kaggle và đường dẫn ngoài project."""
    target = inside(root, reference)
    base = storage_root(root, category, baseline)
    if not target.is_relative_to(base):
        raise ValueError(f'Output must be under {base.relative_to(root.resolve()).as_posix()}')
    pieces = target.relative_to(base).parts
    if not pieces or not VERSION.fullmatch(pieces[0]) or (len(pieces) == 1 and not allow_version_root):
        raise ValueError('Output requires a vNNN_short_description directory')
    return target


def artifact_path(root: Path, reference: str | Path) -> Path:
    """Giải path trước/sau move và sau rollback; không chọn khi cả hai cùng có."""
    root = root.resolve()
    absolute = inside(root, reference)
    relative = absolute.relative_to(root)
    for pair in registry_data(root).get('path_aliases', []):
        old, new = Path(pair['old']), Path(pair['new'])
        if old.is_absolute() or new.is_absolute() or '..' in old.parts or '..' in new.parts:
            raise ValueError('Unsafe storage mapping')
        for source, target in ((old, new), (new, old)):
            if relative == source or source in relative.parents:
                alternative = inside(root, target / relative.relative_to(source))
                if absolute.exists() and alternative.exists():
                    raise ValueError('Both legacy and canonical artifact exist')
                return absolute if absolute.exists() or not alternative.exists() else alternative
    return absolute


def registered_run(root: Path, run_id: str) -> dict | None:
    if not RUN_ID.fullmatch(run_id):
        raise ValueError('Invalid run ID')
    found = [r for r in registry_data(root).get('runs', []) if r.get('run_id') == run_id]
    if len(found) > 1:
        raise ValueError('Duplicate run ID in registry')
    return found[0] if found else None


def run_folder(root: Path, run_id: str) -> Path | None:
    """Ưu tiên vị trí được đăng ký; fallback cho local run lịch sử chưa mapping."""
    entry = registered_run(root, run_id)
    paths = [artifact_path(root, entry['actual_path'])] if entry and entry.get('actual_path') else []
    paths.append(inside(root, Path('outputs/training') / run_id))
    # Quét identity kể cả khi path LEGACY còn tồn tại để không âm thầm chọn sai bản.
    paths.extend(path for _, path, identity in canonical_directories(root)
                 if identity.get('run_id') == run_id)
    existing = {p for p in paths if p.is_dir()}
    if len(existing) > 1:
        raise ValueError(f'Run exists in both canonical and legacy storage: {run_id}')
    if existing:
        return next(iter(existing))
    return None


def canonical_directories(root: Path):
    """Khám phá tối đa hai cấp canonical; identity.json gắn run ID thật."""
    root = root.resolve()
    registry = registry_data(root)
    roots = []
    for baseline in registry.get('baseline_folders') or [{'id': key} for key in FALLBACK_BASELINES]:
        roots.append(('baseline', storage_root(root, 'baseline', baseline['id'])))
    for category in ('shared_evaluation', 'system_evidence', 'data_audit'):
        roots.append((category, storage_root(root, category)))
    for category, folder in roots:
        if not folder.is_dir():
            continue
        for child in sorted(folder.iterdir()):
            if not child.is_dir() or child.is_symlink() or not VERSION.fullmatch(child.name):
                continue
            if not child.resolve().is_relative_to(root):
                continue
            identity_path = child / 'artifact_identity.json'
            try:
                identity = json.loads(identity_path.read_text(encoding='utf-8')) if identity_path.is_file() else {}
            except (OSError, ValueError):
                identity = {}
            yield category, child, identity if isinstance(identity, dict) else {}


def new_run_folder(root: Path, run_id: str, baseline: str, version: str) -> Path:
    """Run mới không được trùng ID hoặc version với kết quả cũ."""
    if not RUN_ID.fullmatch(run_id):
        raise ValueError('Invalid run ID')
    if registered_run(root, run_id) is not None or run_folder(root, run_id) is not None:
        raise FileExistsError(f'Existing run ID: {run_id}')
    target = output_path(root, 'baseline', version, baseline=baseline)
    if target.exists():
        raise FileExistsError(f'Artifact version already exists: {target}')
    return target


def artifact_catalog(root: Path) -> list[dict]:
    """Danh mục một cấp: mapping tường minh cộng thư mục LEGACY chưa phân loại."""
    root = root.resolve()
    registry = registry_data(root)
    rows, seen = [], set()
    for kind, entries in (('run', registry.get('runs', [])), ('artifact', registry.get('artifacts', []))):
        for entry in entries:
            if not isinstance(entry.get('actual_path'), str):
                continue
            path = artifact_path(root, entry['actual_path'])
            relative = path.relative_to(root).as_posix()
            if relative in seen:
                raise ValueError(f'Duplicate artifact path: {relative}')
            seen.add(relative)
            rows.append({'id': entry.get('run_id') if kind == 'run' else entry.get('id'),
                         'kind': kind, 'name': entry.get('name') or entry.get('run_id'),
                         'baseline': entry.get('baseline'), 'version': entry.get('version'),
                         'category': entry.get('category') or ('baseline' if kind == 'run' else 'unknown'),
                         'physical_path': relative, 'storage_state': entry.get('storage_state', 'LEGACY'),
                         'available': path.exists(), 'source': entry.get('source')})
    for category, path, identity in canonical_directories(root):
        relative = path.relative_to(root).as_posix()
        if relative in seen:
            continue
        seen.add(relative)
        run_id = identity.get('run_id')
        if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
            run_id = None
        rows.append({'id': run_id or 'artifact_' + hashlib.sha256(relative.encode()).hexdigest()[:12],
                     'kind': 'run' if run_id else 'artifact', 'name': identity.get('name') or path.name,
                     'baseline': identity.get('baseline'), 'version': path.name,
                     'category': category, 'physical_path': relative, 'storage_state': 'CANONICAL',
                     'available': True, 'source': 'artifact_identity.json' if identity else 'filesystem metadata'})
    for collection in registry.get('legacy_collections', []):
        folder = inside(root, collection['path'])
        if not folder.is_dir():
            continue
        for path in sorted(p for p in folder.iterdir() if (p.is_dir() or p.is_file()) and not p.is_symlink() and not p.name.startswith('.')):
            if not path.resolve().is_relative_to(root):
                continue
            relative = path.relative_to(root).as_posix()
            if relative in seen:
                continue
            seen.add(relative)
            rows.append({'id': 'legacy_' + hashlib.sha256(relative.encode()).hexdigest()[:12],
                         'kind': 'legacy_directory' if path.is_dir() else 'legacy_file', 'name': path.name, 'baseline': None,
                         'version': None, 'category': collection.get('category', 'unknown'),
                         'physical_path': relative, 'storage_state': 'LEGACY',
                         'available': True, 'source': collection['path']})
    # Một thư mục chưa đăng ký ở outputs/ vẫn hiện với trạng thái LEGACY.
    outputs = root / 'outputs'
    canonical = {'baselines', 'shared_evaluations', 'system_evidence', 'data_audits', '_legacy'}
    if outputs.is_dir():
        for path in sorted(outputs.iterdir()):
            if not path.is_dir() or path.is_symlink() or path.name in canonical:
                continue
            relative = path.relative_to(root).as_posix()
            if relative in seen:
                continue
            seen.add(relative)
            rows.append({'id': 'legacy_' + hashlib.sha256(relative.encode()).hexdigest()[:12],
                         'kind': 'legacy_directory', 'name': path.name, 'baseline': None,
                         'version': None, 'category': 'unknown', 'physical_path': relative,
                         'storage_state': 'LEGACY', 'available': True, 'source': 'unregistered outputs root'})
    return rows
