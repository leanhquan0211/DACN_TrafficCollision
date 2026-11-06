"""Kiểm kê metadata temporal sẵn có và dấu vết nguồn B0, không mở holdout.

Đầu vào metadata ACCIDENT, receipt và registry project; đầu ra audit tổng hợp.
Clip chưa thấy trong registry chỉ là ứng viên cần kiểm, không là test độc lập.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.storage_paths import output_path, require_output_path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def group(stem):
    # ID YouTube 11 ký tự theo sau bởi một hoặc nhiều hậu tố số của clip.
    # Đây vẫn chỉ là sàng lọc tên, không chứng minh các ID khác là độc lập.
    match = re.fullmatch(r'([A-Za-z0-9_-]{11})(?:_\d+)+', stem)
    return match.group(1) if match else stem


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=output_path(ROOT,'data_audit','v007_temporal_sources',child='inventory.json'))
    args = p.parse_args()
    args.output = require_output_path(ROOT,args.output,'data_audit',allow_version_root=False)
    raw = ROOT/'data_raw/accident/public_selected'
    metadata = raw/'metadata-real.csv'
    receipts = raw/'download_receipts.json'
    with metadata.open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    registry_paths = sorted((ROOT/'data/registries').glob('b0_*_split.csv'))
    known = set()
    for registry in registry_paths:
        with registry.open(encoding='utf-8-sig', newline='') as f:
            known.update(row['source_sequence'] for row in csv.DictReader(f) if row.get('source_dataset') == 'ACCIDENT')
    known_groups = {group(name) for name in known}
    dev_registry = ROOT/'data/registries/temporal_development_v1.json'
    dev = json.loads(dev_registry.read_text(encoding='utf-8')) if dev_registry.exists() else {'videos': []}
    consumed_groups = {group(v['video_id']) for v in dev['videos']}
    local = {p.stem: p for p in (raw/'real_videos').glob('*.mp4')}
    metadata_by_stem = {Path(r['path']).stem: r for r in rows}
    if len(metadata_by_stem) != len(rows):
        raise ValueError('Duplicate metadata clip names')
    unlisted = [stem for stem in local if stem not in known]
    group_clear = [stem for stem in unlisted if group(stem) not in known_groups]
    valid_point = []
    for stem in group_clear:
        r = metadata_by_stem.get(stem)
        try:
            if r and 0 <= int(r['accident_frame']) < int(r['no_frames']):
                valid_point.append(stem)
        except (TypeError, ValueError):
            continue
    eligible = [stem for stem in valid_point if group(stem) not in consumed_groups]
    development = [stem for stem in eligible if metadata_by_stem[stem].get('split_in_distribution') == 'train'
                   and metadata_by_stem[stem].get('split_geo_aware') == 'train']
    source_test = [stem for stem in eligible if metadata_by_stem[stem].get('split_in_distribution') == 'test'
                   or metadata_by_stem[stem].get('split_geo_aware') == 'test']
    result = {'status': 'inventory_only_no_heldout_opened', 'metadata': str(metadata.relative_to(ROOT)),
              'metadata_sha256': digest(metadata), 'receipt_sha256': digest(receipts),
              'registry_files': [dict(path=str(p.relative_to(ROOT)), sha256=digest(p)) for p in registry_paths],
              'metadata_rows': len(rows), 'local_mp4_count': len(local), 'registry_accident_sequences': len(known),
              'local_not_in_registry': len(unlisted), 'local_not_in_registry_group': len(group_clear),
              'metadata_impact_frame_in_range_among_those': len(valid_point),
              'unassigned_candidates': sorted(eligible),
              'already_consumed_development': sorted(stem for stem in valid_point if group(stem) in consumed_groups),
              'source_train_only_development_candidates': sorted(development),
              'source_test_reserved_count': len(source_test),
              'scope': 'Name/group metadata screen only; no byte/perceptual duplicate check or full prior-run provenance. No clip is declared independent or assigned heldout.',
              'label_schema': 'ACCIDENT accident_frame is author first visible contact point; no event end implied. Camera timing/source FPS not established by container.',
              'sources': {'ACCIDENT': 'https://arxiv.org/html/2604.09819v1',
                          'CADP': 'https://github.com/ankitshah009/CarCrash_forecasting_and_detection',
                          'STTAD': 'https://github.com/ZTR02/STTAD',
                          'TAD': 'https://github.com/UnicomAI/UnicomBenchmark/tree/main/TADBench'}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps({k: v for k, v in result.items() if k.endswith('count') or k.startswith('local_') or k.startswith('metadata_impact')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
