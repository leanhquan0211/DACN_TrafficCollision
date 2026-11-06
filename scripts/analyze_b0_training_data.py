"""Thống kê nhãn train/val và lỗi validation đã lưu, không chạy mô hình.

Đầu vào là provenance của gói B0 và cases.csv từ run đã hoàn tất. Đầu ra
JSON giúp so sánh nhóm nguồn, diện tích bbox và số case bỏ sót theo kích cỡ;
không đọc hoặc phân tích test/reserve. Chạy khi cần đánh giá dữ liệu B0.
"""
import argparse
import collections
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.storage_paths import output_path, require_output_path


def load_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def analyze(provenance, cases, dataset_root):
    rows = [r for r in load_csv(provenance) if r['split'] in ('train', 'val')]
    case_rows = load_csv(cases)
    case_index = {(r['leakage_group'], r['source_sequence'], str(r['source_frame'])): r for r in case_rows}
    if len(case_index) != len(case_rows):
        raise ValueError('Validation cases have duplicate keys')
    counts = collections.Counter()
    groups = collections.defaultdict(set)
    sizes = collections.Counter()
    missed = collections.Counter()
    matched = 0
    for row in rows:
        split, label, source = row['split'], row['collision_label'], row['source_dataset']
        group = (split, label, source)
        counts[group] += 1
        groups[group].add(row['leakage_group'])
        key = (row['leakage_group'], row['source_sequence'], str(row['source_frame']))
        if split == 'val':
            if key not in case_index or case_index[key]['collision_label'] != label:
                raise ValueError('Validation labels/cases do not match')
            matched += 1
        if label != 'positive':
            continue
        label_path = dataset_root / row['export_label']
        lines = label_path.read_text(encoding='utf-8').splitlines()
        for line in lines:
            c, x, y, w, h = map(float, line.split())
            if c != 0 or not (0 < w <= 1 and 0 < h <= 1 and 0 <= x <= 1 and 0 <= y <= 1):
                raise ValueError('Invalid normalized label: ' + str(label_path))
            # Phân nhóm theo tỷ lệ diện tích bbox trên ảnh gốc, không gọi đây
            # là cỡ COCO (COCO dùng diện tích pixel trong hệ tọa độ riêng).
            area = w * h
            size = '<1%' if area < .01 else '1-5%' if area < .05 else '>=5%'
            sizes[(split, size)] += 1
            if split == 'val' and int(case_index[key]['fn']) > 0:
                missed[size] += 1
    if matched != len(case_index):
        raise ValueError('Some validation cases are missing from provenance')
    return {'scope': 'train/val only; existing validation predictions at conf=.25, IoU=.5',
            'sample_groups': [{'split': k[0], 'label': k[1], 'source': k[2], 'images': v,
                               'groups': len(groups[k])} for k, v in sorted(counts.items())],
            'positive_bbox_area': [{'split': k[0], 'fraction_of_image': k[1], 'boxes': v}
                                   for k, v in sorted(sizes.items())],
            'validation_fn_by_bbox_area': dict(missed), 'validation_cases_matched': matched,
            'limitations': 'Bbox areas are normalized; FN counts describe saved cases, not causes. Groups are not proven independent cameras.',
            'test_inference': False, 'reserve_inference': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset-root', type=Path, required=True)
    parser.add_argument('--cases', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=output_path(ROOT,'data_audit','v009_b0_training_analysis',child='analysis.json'))
    args = parser.parse_args()
    args.output = require_output_path(ROOT,args.output,'data_audit',allow_version_root=False)
    if args.output.exists():
        raise FileExistsError(args.output)
    result = analyze(args.dataset_root / 'provenance.csv', args.cases, args.dataset_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
