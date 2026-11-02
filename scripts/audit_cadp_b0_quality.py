"""Biến cờ chất lượng CADP thành bảng giữ/loại có lý do, không sửa nhãn gốc.

Đầu vào: frames.csv và region_proposals.csv đã chuẩn hóa từ 001407. Đầu ra:
CSV một dòng/frame và thống kê các cờ thiếu nhãn/che khuất/vùng ignore. Chạy
khi kiểm tập dẫn xuất; frame unknown không thành negative, bbox hợp lệ về
hình học vẫn không tự thành annotation vùng accident của tác giả.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data_preparation import new_audit_dir, save_csv, save_json


def classify(frame: dict, proposal: dict | None) -> dict:
    """Quyết định bảo thủ cho nhãn dẫn xuất: thiếu thông tin thì loại, không đoán."""
    reasons = []
    if proposal is None:
        reasons.append(frame.get("skip_reasons") or "no_region_annotation_unknown_not_negative")
    else:
        if proposal["any_occluded"] == "1":
            reasons.append("excluded_occluded_derived_participant")
        if proposal["overlaps_ignore_region"] == "1":
            reasons.append("excluded_overlapping_unlabeled_region")
        if frame["missing_known_track_rows"] != "[]":
            reasons.append("excluded_incomplete_track_rows")
    return dict(sequence=frame["sequence"], source_frame=frame["source_frame"], source_image=frame["source_image"],
                derived_geometry_quality="exclude" if reasons else "passes_explicit_source_flags",
                reasons=";".join(reasons), generated_source_flag=proposal["any_generated"] if proposal else "",
                use="auxiliary_derived_only_not_author_region_gt", training_eligible=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit CADP derived label quality; never approve GT or create negatives")
    parser.add_argument("--input", type=Path, default=Path("data/processed/b0_proposals/001407"))
    args = parser.parse_args()
    with (args.input/"frames.csv").open(encoding="utf-8", newline="") as stream:
        frames = list(csv.DictReader(stream))
    with (args.input/"region_proposals.csv").open(encoding="utf-8", newline="") as stream:
        proposals = list(csv.DictReader(stream))
    by_frame = {r["source_frame"]: r for r in proposals}
    if len(by_frame) != len(proposals):
        raise ValueError("This pilot audit expects one event region per frame")
    records = [classify(f, by_frame.get(f["source_frame"])) for f in frames]
    audit = new_audit_dir(ROOT/"outputs/audits", "cadp_b0_quality")
    save_csv(audit/"frame_quality.csv", records, list(records[0]))
    report = dict(source=args.input.as_posix(), frame_count=len(records),
                  status_counts=dict(Counter(r["derived_geometry_quality"] for r in records)),
                  occluded_proposals=sum(r["any_occluded"] == "1" for r in proposals),
                  ignore_overlapping_proposals=sum(r["overlaps_ignore_region"] == "1" for r in proposals),
                  source_generated_proposals=sum(r["any_generated"] == "1" for r in proposals),
                  policy="Conservative derived CADP filter; retain generated flag as provenance, no interpolation or approval",
                  negative_labels_created=0, approved_gt_created=0, can_train=False)
    save_json(audit/"report.json", report)
    print(f"Report: {(audit/'report.json').relative_to(ROOT).as_posix()}")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
