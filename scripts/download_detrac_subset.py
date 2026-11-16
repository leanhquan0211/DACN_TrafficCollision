"""Lấy riêng ba chuỗi DETRAC qua HTTP Range, không tải toàn ZIP ~9.85 GB.

Kiểm Content-Range mỗi lần đọc, giới hạn byte, kiểm CRC từng member và giữ
central directory/fingerprint làm provenance. Không sửa review hay manifest.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile
import urllib.request
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data_preparation import new_audit_dir, save_json, save_csv, sha256_file

URL = "https://drive.usercontent.google.com/download?id=1fQC6CEWOeL9pnJ4ZdD7U2gromcnWDRgm&export=download&confirm=t"
EXPECTED = {"MVI_20011": 664, "MVI_20012": 936, "MVI_20032": 437}


class RangeReader(io.RawIOBase):
    """Seekable reader with bounded on-disk blocks; rejects non-range replies."""

    def __init__(self, url, cache, budget=512 * 1024**2, block_size=4 * 1024**2):
        self.url, self.cache, self.budget, self.block_size = url, cache, budget, block_size
        self.position, self.downloaded, self.size = 0, 0, None
        self.ranges = []
        cache.mkdir(parents=True, exist_ok=False)
        self._request(0, 0)

    def _request(self, start, end):
        length = end - start + 1
        if self.downloaded + length > self.budget:
            raise ValueError("Selective download byte budget exceeded; no full archive download")
        # Separate cache keys: some intermediaries cache a Drive HTML response
        # under the URL without varying on the Range header.
        url = self.url + f"&range_start={start}&range_end={end}"
        req = urllib.request.Request(url, headers={"Range": f"bytes={start}-{end}", "Cache-Control": "no-cache"})
        with urllib.request.urlopen(req, timeout=60) as response:
            content_range = response.headers.get("Content-Range", "")
            match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", content_range)
            if response.status != 206 or not match:
                raise ValueError(f"Server did not honor Range (HTTP {response.status}, {response.headers.get('Content-Type')}); stopped before downloading full ZIP")
            actual_start, actual_end, size = map(int, match.groups())
            if (actual_start, actual_end) != (start, end) or (self.size is not None and size != self.size):
                raise ValueError("Remote archive range/size changed")
            data = response.read(length + 1)
            if len(data) != length:
                raise ValueError("Incomplete or oversized HTTP range")
            self.size = size
        self.downloaded += len(data)
        self.ranges.append(dict(start=start, end=end, bytes=len(data)))
        print(f"Range {start}-{end}; downloaded {self.downloaded / 1024**2:.1f} MiB", flush=True)
        return data

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        base = {0: 0, 1: self.position, 2: self.size}.get(whence)
        if base is None or base + offset < 0:
            raise ValueError("Invalid seek")
        self.position = base + offset
        return self.position

    def read(self, size=-1):
        if size < 0:
            size = self.size - self.position
        end = min(self.size, self.position + size)
        result = bytearray()
        while self.position < end:
            block = self.position // self.block_size
            start = block * self.block_size
            stop = min(start + self.block_size, self.size)
            path = self.cache / f"{start}-{stop-1}.bin"
            if not path.exists():
                with path.open("xb") as stream:
                    stream.write(self._request(start, stop - 1))
            count = min(end, stop) - self.position
            with path.open("rb") as stream:
                stream.seek(self.position - start)
                result.extend(stream.read(count))
            self.position += count
        return bytes(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-mib", type=int, default=512, help="Maximum network bytes for selected data and ZIP directory")
    args = parser.parse_args()
    if not 32 <= args.max_mib <= 1024:
        parser.error("--max-mib must be between 32 and 1024; full archive download is not supported")
    audit = new_audit_dir(ROOT / "outputs/audits", "detrac_subset_download")
    report = dict(source_url=URL, selected_sequences=EXPECTED, full_archive_downloaded=False,
                  reviews_modified=False, complete=False, images=[], audit_directory=str(audit.relative_to(ROOT)))
    remote = None
    try:
        remote = RangeReader(URL, audit / "range_cache", budget=args.max_mib * 1024**2)
        with zipfile.ZipFile(remote) as archive:
            selected = []
            for item in archive.infolist():
                path = PurePosixPath(item.filename.replace("\\", "/"))
                if len(path.parts) >= 2 and path.parts[-2] in EXPECTED and not item.is_dir():
                    if path.is_absolute() or ".." in path.parts or not re.fullmatch(r"img\d{5}\.jpg", path.name):
                        raise ValueError(f"Unexpected selected member: {item.filename}")
                    selected.append(item)
            for sequence, expected_count in EXPECTED.items():
                names = [PurePosixPath(item.filename).name for item in selected
                         if PurePosixPath(item.filename).parent.name == sequence]
                if len(names) != expected_count or set(names) != {f"img{i:05d}.jpg" for i in range(1, expected_count+1)}:
                    raise ValueError(f"Source sequence inventory differs: {sequence}")
            report["archive_member_count"] = len(archive.infolist())
            report["selected_compressed_bytes"] = sum(i.compress_size for i in selected)
            print(f"Selected {len(selected)} images, compressed {report['selected_compressed_bytes']} bytes", flush=True)
            # Keep source ZIP central directory separately, not as a fake complete ZIP.
            remote.seek(archive.start_dir)
            central = remote.read(remote.size - archive.start_dir)
            (audit / "central_directory.bin").write_bytes(central)
            report["central_directory_sha256"] = sha256_file(audit / "central_directory.bin")
            for item in sorted(selected, key=lambda i: i.header_offset):
                member = PurePosixPath(item.filename)
                target = ROOT / "data_raw/ua_detrac/DETRAC-Images" / member.parent.name / member.name
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    existing = target.read_bytes()
                    if len(existing) != item.file_size or zlib.crc32(existing) != item.CRC:
                        raise ValueError(f"Existing image differs; preserved: {target}")
                    status = "reused_crc_verified"
                else:
                    data = archive.read(item)  # ZipFile checks decompression and CRC.
                    temporary = None
                    try:
                        with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".download-", delete=False) as stream:
                            temporary = Path(stream.name)
                            stream.write(data)
                        target.hardlink_to(temporary)
                    finally:
                        if temporary:
                            temporary.unlink(missing_ok=True)
                    status = "downloaded_crc_verified"
                report["images"].append(dict(sequence=member.parent.name, filename=member.name,
                    path=str(target.relative_to(ROOT)), source_member=item.filename, size_bytes=item.file_size,
                    source_crc32=f"{item.CRC:08x}", sha256=sha256_file(target), status=status))
                if len(report["images"]) % 200 == 0:
                    print(f"Verified {len(report['images'])}/{len(selected)} images", flush=True)
            report["complete"] = True
            save_csv(audit / "images.csv", report["images"], list(report["images"][0]))
    except Exception as exc:
        report["error"] = str(exc)
        raise
    finally:
        if remote:
            report.update(source_archive_size_bytes=remote.size, network_bytes=remote.downloaded, ranges=remote.ranges)
            remote.close()
        save_json(audit / "report.json", report)
        print(f"Report: {audit / 'report.json'}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
