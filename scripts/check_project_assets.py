"""Kiểm file cần phục hồi sau clone, không tải dữ liệu hoặc sửa nhãn.

Đầu vào: data/download_catalog.json và các file thực tế trên máy. Đầu ra:
trạng thái có/thiếu/sai hash, đường dẫn nguồn và nơi cần đặt. Dùng --create-dirs
để tạo khung thư mục rỗng; --check-hashes kiểm byte với mẫu đã xác minh.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIRECTORIES = (
    "data_raw/cadp/pilot_1407", "data_raw/cadp/frames", "data_raw/cadp/reference_code",
    "data_raw/cadp/documentation", "data_raw/cadp/annotations/vatic",
    "data_raw/ua_detrac/annotations", "data_samples/cadp", "data_samples/ua_detrac",
    "data/processed", "outputs/annotation_preview", "outputs/detection",
    "outputs/tracking", "outputs/audits", "data_raw/sttad/public_examples", "data_raw/tad/public_selected",
)


def within_root(relative: str) -> Path:
    """Catalog chỉ được trỏ vào project, không đọc/ghi đường dẫn bên ngoài."""
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError(f"Path outside project: {relative}")
    return path


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def inspect(asset: dict, check_hashes: bool) -> dict:
    path = within_root(asset["path"])
    result = dict(id=asset["id"], path=asset["path"], source_url=asset["source_url"], status="missing")
    if asset["kind"] == "download_directory":
        if not path.is_dir():
            return result
        images = [p for p in path.iterdir() if p.is_file() and p.suffix.lower() in (".jpg", ".jpeg", ".png")]
        result["image_count"] = len(images)
        result["status"] = "present_count_matches" if len(images) == asset["expected_image_count"] else "count_mismatch"
        if check_hashes and asset.get("image_inventory"):
            with within_root(asset["image_inventory"]).open(encoding="utf-8", newline="") as stream:
                inventory = list(csv.DictReader(stream))
            # Hash từng ảnh gốc ngăn việc cùng tên/thư mục nhưng khác nội dung.
            failures = [r["relative_path"] for r in inventory
                        if not within_root(r["relative_path"]).is_file()
                        or digest(within_root(r["relative_path"])) != r["sha256"]]
            result["mismatched_images"] = failures
            if failures or len(inventory) != len(images):
                result["status"] = "image_fingerprint_mismatch"
            else:
                result["status"] = "verified_image_fingerprints"
        return result
    if path.is_file():
        result.update(status="present", size_bytes=path.stat().st_size)
        if check_hashes and asset.get("expected_sha256"):
            result["status"] = "verified_sha256" if digest(path) == asset["expected_sha256"] else "hash_mismatch"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Report local dataset/model assets after clone; no downloads or label changes")
    parser.add_argument("--catalog", type=Path, default=ROOT / "data/download_catalog.json")
    parser.add_argument("--create-dirs", action="store_true", help="Create missing project folders only")
    parser.add_argument("--check-hashes", action="store_true", help="Compare catalog hashes and CADP image fingerprints")
    parser.add_argument("--profile", choices=("inference", "cadp", "detrac", "detrac_archive_audit", "sttad", "tad", "accident"))
    parser.add_argument("--strict", action="store_true", help="Exit 1 if a required asset in the selected profile is missing/mismatched")
    parser.add_argument("--json", action="store_true", help="Print structured inventory")
    args = parser.parse_args()
    if args.strict and not args.profile:
        parser.error("--strict requires --profile; optional documents are not mandatory setup inputs")
    if args.create_dirs:
        for folder in DIRECTORIES:
            within_root(folder).mkdir(parents=True, exist_ok=True)
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    assets = [a for a in catalog["assets"] if not args.profile or args.profile in a["required_for"]]
    results = [inspect(asset, args.check_hashes) for asset in assets]
    accepted = {"present", "present_count_matches", "verified_image_fingerprints", "verified_sha256"}
    failures = [r for a, r in zip(assets, results) if not a["optional"] and r["status"] not in accepted]
    if args.json:
        print(json.dumps(dict(assets=results, required_incomplete=len(failures), downloads_performed=0,
                              manifest_modified=False), ensure_ascii=True, indent=2))
    else:
        for result in results:
            print(f"{result['status']:30} {result['path']}")
            if result["status"] not in accepted:
                print(f"  Source: {result['source_url']}")
        print("Guide: docs/GETTING_STARTED.md; no downloads or manifest/review changes performed.")
    return 1 if args.strict and failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
