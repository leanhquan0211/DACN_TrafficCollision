"""Báo cáo hiện trạng máy + metadata; không tải, sửa review, split hay train.

Chạy bằng Python chuẩn, không cần torch/cv2. --strict trả 1 khi còn blocker;
không có blocker tự động cũng không thay nghiệm thu nhãn/dữ liệu bằng người.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
import importlib.metadata
import json
from pathlib import Path
import platform
import shutil
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.check_project_assets import digest, inspect, within_root
from src.data_preparation import new_audit_dir, save_json
from src.manifest_audit import audit_manifest


def build_report() -> dict:
    manifest = ROOT / "data/manifest.csv"
    readiness_path = ROOT / "data/b0_readiness.json"
    catalog_path = ROOT / "data/download_catalog.json"
    rule_path = ROOT / "configs/b0_region_proposal.json"
    with manifest.open(encoding="utf-8-sig", newline="") as stream:
        metadata = audit_manifest(list(csv.DictReader(stream)))
    readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    rule = json.loads(rule_path.read_text(encoding="utf-8"))
    assets = []
    accepted = {"present", "present_count_matches", "verified_sha256", "verified_image_fingerprints"}
    for item in catalog["assets"]:
        try:
            result = inspect(item, check_hashes=True)
        except (OSError, ValueError, KeyError) as exc:
            result = dict(id=item["id"], path=item["path"], status="inspection_error", error=str(exc))
        result.update(optional=item["optional"], required_for=item["required_for"])
        assets.append(result)
    packages = {}
    for package in ("torch", "torchvision", "ultralytics", "lap", "opencv-python", "numpy"):
        try:
            packages[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            packages[package] = None
    artifacts = {}
    for key in ("annotation_csv", "technical_evidence"):
        if readiness.get(key):
            artifacts[readiness[key]] = within_root(readiness[key]).is_file()
    candidate_table = readiness.get("region_proposal", {}).get("candidate_table")
    if candidate_table:
        artifacts[candidate_table] = within_root(candidate_table).is_file()
    artifacts["data/processed/b0_reviewed_negatives/frames.csv"] = within_root(
        "data/processed/b0_reviewed_negatives/frames.csv").is_file()
    blockers = []

    def block(code, detail):
        blockers.append(dict(code=code, detail=detail))

    for asset in assets:
        # Full 9.85 GB archive is only needed for its dedicated archive audit.
        # Restoring selected extracted sequences must not demand that download.
        active_profiles = set(asset["required_for"]) - {"detrac_archive_audit"}
        if not asset["optional"] and active_profiles and asset["status"] not in accepted:
            block("local_asset_unavailable", f"{asset['id']}: {asset['status']}")
    for name, version in packages.items():
        if version is None:
            block("missing_package", name)
    if not shutil.which("ffmpeg"):
        block("missing_ffmpeg", "Required for H.264 output")
    if not metadata["metadata_consistent"]:
        block("manifest_errors", metadata["issues"])
    if metadata["unassigned_asset_count"] or metadata["assigned_asset_count"] == 0:
        block("split_incomplete", "No complete reviewed train/val/test split; do not randomly split frames")
    if metadata["known_positive_events"] < 3:
        block("insufficient_event_groups", "Fewer than 3 known events cannot populate 3 disjoint positive splits; 3 alone would not certify adequacy")
    if metadata["missing_camera_count"]:
        block("camera_grouping_unresolved", "Camera metadata incomplete; source/near-duplicate review still required")
    if rule.get("training_export_allowed") is not True:
        block("region_rule_not_approved", rule.get("status"))
    if readiness.get("can_train") is not True or readiness.get("stage_1_complete") is not True:
        block("research_gate_closed", "Recorded readiness has not passed stage 1/B0")
    for detail in readiness.get("blockers_for_image_B0", []):
        block("recorded_image_blocker", detail)
    for path, exists in artifacts.items():
        if not exists:
            block("generated_artifact_missing", path)
    return dict(
        schema_version=1,
        checked_at=datetime.now(ZoneInfo("Asia/Bangkok")).isoformat(),
        input_sha256={str(p.relative_to(ROOT)): digest(p) for p in
                      (manifest, readiness_path, catalog_path, rule_path, ROOT / "src/manifest_audit.py",
                       ROOT / "scripts/audit_project.py", ROOT / "scripts/check_project_assets.py")},
        metadata=metadata, local_assets=assets, local_generated_artifacts=artifacts,
        environment=dict(python=platform.python_version(), packages=packages,
                         ffmpeg_present=bool(shutil.which("ffmpeg")),
                         package_imports_tested=False, cuda_tested=False),
        historical_readiness=dict(updated_date=readiness.get("updated_date"),
                                  can_train=readiness.get("can_train"),
                                  counts_are_local_inventory=False),
        temporal_blockers=readiness.get("blockers_for_temporal_evaluation", []),
        blockers=blockers, status="blocked" if blockers else "requires_manual_verification",
        automatic_training_approval=False,
        limitations=["File presence/count is not fingerprint verification without a reference hash",
                     "Metadata grouping is not a visual near-duplicate or camera-independence review",
                     "No model, accuracy, source FPS or data adequacy is validated by this report"],
        downloads_performed=0, manifest_or_reviews_modified=False)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=ROOT / "outputs/audits")
    parser.add_argument("--strict", action="store_true", help="Return 1 while blockers remain")
    args = parser.parse_args()
    report = build_report()
    folder = new_audit_dir(args.output_root, "project_" + report["checked_at"][:10])
    save_json(folder / "report.json", report)
    m = report["metadata"]
    lines = ["# Kiểm tra hiện trạng project", "", f"Thời điểm: {report['checked_at']}", "",
             f"Trạng thái: **{report['status']}**. Không tự phê duyệt huấn luyện.", "",
             f"Metadata: {m['asset_count']} asset, {m['known_positive_events']} sự kiện dương, "
             f"{m['known_negative_sequences']} chuỗi âm; {m['unassigned_asset_count']} asset chưa chia split.",
             "Các số này lấy từ hồ sơ; xem bảng dưới để biết file thật trên máy.", "",
             "| Asset | Trạng thái local |", "| --- | --- |"]
    lines.extend(f"| {a['id']} | {a['status']} |" for a in report["local_assets"])
    lines.extend(["", "## Blocker", ""])
    lines.extend(f"- `{b['code']}`: {b['detail']}" for b in report["blockers"])
    lines.extend(["", "## Giới hạn", ""] + [f"- {s}" for s in report["limitations"]])
    with (folder / "report.md").open("x", encoding="utf-8") as stream:
        stream.write("\n".join(lines) + "\n")
    print(f"{report['status']}: {len(report['blockers'])} blockers; {folder / 'report.md'}")
    return 1 if args.strict and report["blockers"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
