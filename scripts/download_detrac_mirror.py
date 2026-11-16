"""Phục hồi ba chuỗi DETRAC qua bản sao, kiểm SHA mirror và CRC ZIP nguồn.

Metadata ghim revision ở data/registries/detrac_subset_sources.json. Chỉ công
bố ảnh sau cả hai phép kiểm; không xác nhận nhãn hoặc thay review MP4 cũ.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import json
from pathlib import Path
import sys
import time
import urllib.error
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.download_cadp_frames import fetch_verified
from scripts.download_detrac_subset import EXPECTED
from src.data_preparation import new_audit_dir, save_json, sha256_file


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, choices=range(1, 9), default=4)
    args = parser.parse_args()
    source_path = ROOT / "data/registries/detrac_subset_sources.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    inventory_path = ROOT / source["inventory"]
    if sha256_file(inventory_path) != source["inventory_sha256"]:
        raise ValueError("Inventory fingerprint changed")
    with inventory_path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    for sequence, count in EXPECTED.items():
        names = [r["filename"] for r in rows if r["sequence"] == sequence]
        if len(names) != count or set(names) != {f"img{i:05d}.jpg" for i in range(1, count+1)}:
            raise ValueError(f"Unexpected reference names: {sequence}")
    if len(rows) != sum(EXPECTED.values()):
        raise ValueError("Unexpected sequences in inventory")
    audit = new_audit_dir(ROOT / "outputs/audits", "detrac_mirror_download")
    report = dict(source_metadata=source, source_metadata_sha256=sha256_file(source_path),
                  images=[], errors=[], complete=False, reviews_modified=False,
                  full_archive_downloaded=False, original_reviewed_mp4_restored=False)

    def download(row):
        target = ROOT / "data_raw/ua_detrac/DETRAC-Images" / row["sequence"] / row["filename"]
        staged = audit / "staging" / row["sequence"] / row["filename"]
        location = target if target.exists() else staged
        url = source["mirror_resolve_prefix"] + row["mirror_path"]
        for attempt in range(3):
            try:
                status = fetch_verified(url, location, int(row["size_bytes"]), row["mirror_sha256"])
                break
            except (urllib.error.URLError, TimeoutError) as exc:
                if attempt == 2:
                    raise
                delay = 2 + attempt
                if isinstance(exc, urllib.error.HTTPError) and exc.code == 429:
                    retry = exc.headers.get("Retry-After", "10")
                    delay = min(45, int(retry)) if retry.isdigit() else 10
                time.sleep(delay)
        crc = f"{zlib.crc32(location.read_bytes()):08x}"
        if crc != row["source_crc32"]:
            raise ValueError("Mirror image differs from official ZIP CRC; quarantined in staging")
        if location == staged:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.hardlink_to(staged)
            staged.unlink()
        return dict(sequence=row["sequence"], filename=row["filename"], path=str(target.relative_to(ROOT)),
                    size_bytes=int(row["size_bytes"]), sha256=row["mirror_sha256"], source_crc32=crc, status=status)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(download, row): row for row in rows}
        for future in as_completed(futures):
            row = futures[future]
            try:
                report["images"].append(future.result())
            except Exception as exc:
                report["errors"].append(dict(sequence=row["sequence"], filename=row["filename"], error=str(exc)))
            done = len(report["images"]) + len(report["errors"])
            if done % 100 == 0 or done == len(rows):
                print(f"Checked {done}/{len(rows)}; verified {len(report['images'])}; errors {len(report['errors'])}", flush=True)
    report["images"].sort(key=lambda row: (row["sequence"], row["filename"]))
    report["complete"] = len(report["images"]) == len(rows) and not report["errors"]
    save_json(audit / "report.json", report)
    print(f"Report: {audit / 'report.json'}", flush=True)
    return 0 if report["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
