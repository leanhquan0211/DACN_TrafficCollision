"""Phục hồi riêng 221 ảnh CADP 001407 theo SHA-256 đã rà, có thể chạy lại.

Drive file IDs là metadata công khai; không cần tài khoản/API key để tải ảnh.
Không ghi đè ảnh khác hash, không tải chuỗi khác, không sửa review hoặc split.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data_preparation import new_audit_dir, save_json, sha256_file


def fetch_verified(url: str, destination: Path, expected_size: int, expected_sha256: str) -> str:
    """Chỉ công bố file khi đủ byte và đúng hash; bảo toàn file hiện có."""
    if destination.exists():
        if destination.stat().st_size != expected_size or sha256_file(destination) != expected_sha256:
            raise ValueError(f"Existing file differs; preserved: {destination}")
        return "reused_verified"
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Temp file cùng filesystem; link tạo đích độc quyền, không thay file do tiến trình khác tạo.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=".download-", delete=False) as stream:
            temporary = Path(stream.name)
            digest = hashlib.sha256()
            total = 0
            with urllib.request.urlopen(url, timeout=45) as response:
                while chunk := response.read(min(1024 * 1024, expected_size + 1 - total)):
                    total += len(chunk)
                    if total > expected_size:
                        raise ValueError("Download exceeds reference size; possibly HTML or a changed source")
                    digest.update(chunk)
                    stream.write(chunk)
            if total != expected_size or digest.hexdigest() != expected_sha256:
                raise ValueError(f"Downloaded fingerprint mismatch: {destination.name}")
        destination.hardlink_to(temporary)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return "downloaded_verified"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, choices=range(1, 5), default=4)
    args = parser.parse_args()
    registry_path = ROOT / "data/registries/cadp_001407_drive_files.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    inventory_path = ROOT / "data/registries/cadp_001407_images.csv"
    with inventory_path.open(encoding="utf-8", newline="") as stream:
        references = list(csv.DictReader(stream))
    remote = {item["name"]: item for item in registry["files"]}
    expected_names = {f"{i}.jpg" for i in range(221)}
    if (len(remote) != len(registry["files"]) or set(remote) != expected_names
            or len(references) != 221 or {Path(r["relative_path"]).name for r in references} != expected_names):
        raise ValueError("Expected exactly the reviewed 221 image names")
    for row in references:
        target = (ROOT / row["relative_path"]).resolve()
        if target.parent != (ROOT / "data_raw/cadp/frames/001407").resolve():
            raise ValueError("Reference path outside the selected sequence")
        if int(remote[target.name]["size"]) != int(row["size_bytes"]):
            raise ValueError(f"Remote size changed: {target.name}")
    audit = new_audit_dir(ROOT / "outputs/audits", "cadp_001407_download")
    report = dict(sequence="001407", source_folder_url=registry["source_folder_url"],
                  reference_sha256=sha256_file(inventory_path),
                  drive_registry_sha256=sha256_file(registry_path),
                  results=[], errors=[], reviews_modified=False)

    def download(row):
        target = ROOT / row["relative_path"]
        file_id = remote[target.name]["id"]
        url = "https://drive.usercontent.google.com/download?" + urllib.parse.urlencode(
            dict(id=file_id, export="download", confirm="t"))
        for attempt in range(3):
            try:
                status = fetch_verified(url, target, int(row["size_bytes"]), row["sha256"])
                return dict(source_frame=int(row["source_frame"]), path=row["relative_path"],
                            sha256=row["sha256"], drive_file_id=file_id, status=status)
            except (urllib.error.URLError, TimeoutError):
                if attempt == 2:
                    raise
                time.sleep(1 + attempt)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(download, row): row for row in references}
        for future in as_completed(futures):
            try:
                report["results"].append(future.result())
            except Exception as exc:
                report["errors"].append(dict(path=futures[future]["relative_path"], error=str(exc)))
            done = len(report["results"]) + len(report["errors"])
            if done % 20 == 0 or done == len(references):
                print(f"Checked {done}/221; verified {len(report['results'])}; errors {len(report['errors'])}", flush=True)
    report["results"].sort(key=lambda item: item["source_frame"])
    report["complete"] = len(report["results"]) == 221 and not report["errors"]
    save_json(audit / "report.json", report)
    print(f"Report: {audit / 'report.json'}", flush=True)
    return 0 if report["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
