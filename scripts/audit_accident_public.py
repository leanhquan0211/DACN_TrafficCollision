"""Lấy mẫu nhỏ ACCIDENT công khai và kiểm bbox tại frame impact của tác giả.

Đầu vào: metadata/video Kaggle phiên bản cố định hoặc cache đã có tại máy.
Đầu ra: video gốc, ảnh PNG sạch tại impact, nhãn YOLO và báo cáo chất lượng.
Chạy --fetch-selected để lấy mặc định sáu clip nhỏ; --members chọn member
khác trong danh mục đã kiểm, còn --offline không truy cập mạng.
--prepare-preimpact tạo ứng viên UNKNOWN để rà theo frame; --verify-preimpact
đọc lại pixel/PTS. Không tự gán âm, lan bbox, chia tập hoặc huấn luyện model.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
import zipfile
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data_preparation import save_csv, save_json, sha256_file
from src.storage_paths import output_path, require_output_path

DATASET = "picekl/accident"
VERSION = 9
METADATA_SHA256 = "a3d06073353a7fedff140b652d025135f017860a240cad693990f5288c6c0ec9"
SELECTED = (
    "real_videos/0NixrF6Mt00_0_00.mp4",
    "real_videos/04O2SOGSG_U_00.mp4",
    "real_videos/2QZf8MiIRK0_00.mp4",
    "real_videos/1_F0r7KVJ1k_00.mp4",
    "real_videos/-FQxK6HdxNU_00.mp4",
    "real_videos/0PrAtifCwjg_00.mp4",
)
MULTI_VEHICLE_TYPES = {"t-bone", "rear-end", "sideswipe", "head-on"}


def inside(path: Path) -> Path:
    result = path.resolve()
    if not result.is_relative_to(ROOT):
        raise ValueError(f"Path must stay inside project: {path}")
    return result


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def save_image(path: Path, picture) -> None:
    """Mã hóa trong RAM rồi ghi byte, hỗ trợ đường dẫn Windows có dấu tiếng Việt."""
    import cv2
    ok, encoded = cv2.imencode(path.suffix, picture)
    if not ok:
        raise OSError(f"Cannot encode image: {path}")
    with path.open("xb") as stream:
        stream.write(encoded.tobytes())


class BudgetDownload:
    """Giới hạn tổng byte phản hồi; không dùng endpoint tải cả dataset."""

    def __init__(self, budget: int):
        self.budget, self.transferred = budget, 0

    def get(self, url: str, limit: int) -> bytes:
        allowance = min(limit, self.budget - self.transferred)
        if allowance <= 0:
            raise ValueError("Network byte budget exhausted")
        request = urllib.request.Request(url, headers={"User-Agent": "DACN-public-source-audit"})
        with urllib.request.urlopen(request, timeout=30) as response:
            if int(response.headers.get("Content-Length", "0")) > allowance:
                raise ValueError("Response exceeds per-file/total budget; refusing full dataset")
            body = response.read(allowance + 1)
        self.transferred += len(body)
        if len(body) > allowance:
            raise ValueError("Response without valid length exceeds budget")
        return body


def member_url(name: str) -> str:
    # Tên member đi nguyên vào URL, không thay ký tự '-' đầu tên thành option.
    return (f"https://www.kaggle.com/api/v1/datasets/download/{DATASET}/"
            f"{urllib.parse.quote(name, safe='')}?datasetVersionNumber={VERSION}")


def validate_row(row: dict) -> dict:
    """Kiểm tọa độ chuẩn hóa nguồn; không clip/đổi frame để chữa nhãn lỗi."""
    path = PurePosixPath(row["path"])
    if path.is_absolute() or ".." in path.parts or "\\" in row["path"] or ":" in row["path"]:
        raise ValueError("Unsafe source path")
    if len(path.parts) != 2 or path.parts[0] != "real_videos" or path.suffix != ".mp4":
        raise ValueError("Not a real video member")
    values = {k: float(row[k]) for k in ("x1", "y1", "x2", "y2", "center_x", "center_y",
                                        "width", "height", "accident_frame", "no_frames")}
    if not all(math.isfinite(v) for v in values.values()):
        raise ValueError("Nonfinite metadata")
    for key in ("width", "height", "accident_frame", "no_frames"):
        if not values[key].is_integer():
            raise ValueError(f"Noninteger {key}")
    if values["width"] <= 0 or values["height"] <= 0:
        raise ValueError("Invalid dimensions")
    if not 0 <= values["accident_frame"] < values["no_frames"]:
        raise ValueError("Impact frame outside decoded index range; do not subtract one automatically")
    x1, y1, x2, y2 = (values[k] for k in ("x1", "y1", "x2", "y2"))
    if not (0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1):
        raise ValueError("Invalid normalized bbox")
    if abs((x1+x2)/2-values["center_x"]) > 1e-6 or abs((y1+y2)/2-values["center_y"]) > 1e-6:
        raise ValueError("Center does not match source corners")
    return dict(frame=int(values["accident_frame"]), width=int(values["width"]),
                height=int(values["height"]), declared_frames=int(values["no_frames"]),
                xyxy_norm=(x1, y1, x2, y2),
                yolo=(0, (x1+x2)/2, (y1+y2)/2, x2-x1, y2-y1))


def check_timestamps(points: list[float], frame: int, source_time: float) -> dict:
    """Đối chiếu bằng PTS thực, không lấy frame chia FPS trung bình của video VFR."""
    if not points or not all(math.isfinite(x) for x in points) or not 0 <= frame < len(points):
        raise ValueError("Invalid presentation timestamps/frame")
    nearest = min(range(len(points)), key=lambda i: abs(points[i]-source_time))
    ordered = all(b > a for a, b in zip(points, points[1:]))
    residual = points[frame]-source_time
    return dict(impact_pts_seconds=points[frame], source_reported_accident_time=source_time,
                impact_pts_residual_seconds=residual, nearest_pts_frame=nearest,
                timestamps_strictly_increasing=ordered,
                pts_mapping_verified=ordered and nearest == frame and abs(residual) <= .001,
                timing_scope="presentation timestamps of released file; original capture FPS unverified")


def ensure_file(raw: Path, name: str, network: BudgetDownload, offline: bool,
                receipts: dict, expected_size: int | None = None) -> Path:
    target = inside(raw / name)
    if target.exists():
        digest = sha256_file(target)
        expected_hash = METADATA_SHA256 if name == "metadata-real.csv" else receipts.get(name, {}).get("sha256")
        if expected_hash is not None and digest != expected_hash:
            raise ValueError(f"Existing unverified/changed file preserved: {target}")
        if expected_size is not None and target.stat().st_size != expected_size:
            raise ValueError(f"Existing member size differs from listing: {target}")
        if expected_hash is not None:
            return target
    if offline:
        raise FileNotFoundError(target)
    body = network.get(member_url(name), (expected_size or 1_000_000) + 65536)
    if body.startswith(b"PK"):
        # Một số API trả ZIP cho đúng một member; kiểm tên, kích thước và CRC
        # trước khi đọc, không giải nén hàng loạt hoặc tin đường dẫn trong ZIP.
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            members = [x for x in archive.infolist() if not x.is_dir()]
            if len(members) != 1 or members[0].filename not in (name, PurePosixPath(name).name):
                raise ValueError("Unexpected single-file archive")
            if members[0].file_size > (expected_size or 1_000_000):
                raise ValueError("Uncompressed member exceeds expected size")
            body = archive.read(members[0])
    digest = hashlib.sha256(body).hexdigest()
    if (expected_size is not None and len(body) != expected_size) or (name == "metadata-real.csv" and digest != METADATA_SHA256):
        raise ValueError(f"Pinned metadata/member size mismatch: {name}")
    if target.exists():
        # Khôi phục lần tải bị ngắt trước khi ghi receipt: so lại toàn byte
        # qua hash của phản hồi mới, tuyệt đối không ghi đè media khác nội dung.
        if sha256_file(target) != digest:
            raise ValueError(f"Unrecorded local media differs from public member: {target}")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(body)
    receipts[name] = dict(url=member_url(name), size_bytes=len(body), sha256=digest,
                          identity_status="observed_local_sha256_from_versioned_public_endpoint")
    # Receipt là sổ tải đang cập nhật, còn save_json dùng cho audit bất biến
    # và cố ý chỉ tạo file mới. Không sửa helper chung để bỏ kiểm ghi đè audit.
    (raw/"download_receipts.json").write_text(json.dumps(receipts, indent=2)+"\n", encoding="utf-8")
    return target


def inspect_video(path: Path, row: dict) -> tuple[dict, dict]:
    """Đọc tuần tự toàn clip để không nhầm seek/keyframe với chỉ số decode.

    Sau bước này có số frame thật, kích thước và các frame sạch quanh impact.
    Bbox nguồn chỉ có ở impact; ảnh lân cận dùng đối chiếu, không nhận GT mới.
    """
    import cv2
    checked = validate_row(row)
    cap = cv2.VideoCapture(str(path))
    samples, count, sizes, timestamps = {}, 0, Counter(), []
    requested = {checked["frame"] + d for d in (-3, -1, 0, 1, 3)} | {0}
    last_image = None
    try:
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {path}")
        container_fps = cap.get(cv2.CAP_PROP_FPS)
        while True:
            ok, image = cap.read()
            if not ok:
                break
            sizes[image.shape[1], image.shape[0]] += 1
            timestamps.append(cap.get(cv2.CAP_PROP_POS_MSEC)/1000)
            if count in requested:
                samples[count] = image.copy()
            last_image = image
            count += 1
    finally:
        cap.release()
    if set(sizes) != {(checked["width"], checked["height"])}:
        raise ValueError(f"Metadata/decoded video mismatch: {path}; {count}, {sizes}")
    if checked["frame"] not in samples:
        raise ValueError("Impact frame was not decoded")
    # Khi impact sát đầu/cuối clip, dùng frame biên thật làm context;
    # không giả sinh một frame ngoài phạm vi hoặc đổi chỉ số GT impact.
    samples[count-1] = last_image.copy()
    return dict(decoded_frames=count, width=checked["width"], height=checked["height"],
                container_fps=container_fps, source_fps_verified=False,
                metadata_no_frames=checked["declared_frames"],
                metadata_frame_count_matches=count == checked["declared_frames"],
                frame_count_delta=count-checked["declared_frames"],
                source_frame=checked["frame"], source_frame_index_basis="0-based decode; source metadata retained",
                xyxy_norm=checked["xyxy_norm"],
                **check_timestamps(timestamps, checked["frame"], float(row["accident_time"]))), samples


def verify_report(report_path: Path) -> None:
    """Kiểm lại SHA/ảnh/nhãn và PTS bằng hai decoder, không sinh thêm preview.

    Báo cáo tải ban đầu giữ nguyên. Verification riêng lưu sai lệch số frame
    và kết quả ffprobe/OpenCV, không coi container timing là timing ghi hình.
    """
    import cv2
    import numpy as np
    report_path = inside(report_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    destination = report_path.parent/"verification.json"
    if destination.exists():
        raise FileExistsError(destination)
    probe = shutil.which("ffprobe")
    results = []
    for clip in report["selected_clips"]:
        for path_key, hash_key in (("source_video", "video_sha256"), ("clean_image", "image_sha256"),
                                   ("converted_label", "label_sha256"), ("source_metadata", "metadata_sha256")):
            if sha256_file(inside(ROOT/clip[path_key])) != clip[hash_key]:
                raise ValueError(f"Audited input changed: {clip[path_key]}")
        with (ROOT/clip["source_metadata"]).open(encoding="utf-8-sig", newline="") as stream:
            source = next(r for r in csv.DictReader(stream) if r["path"] == "real_videos/"+clip["source_sequence"]+".mp4")
        info, samples = inspect_video(ROOT/clip["source_video"], source)
        clean = cv2.imdecode(np.frombuffer((ROOT/clip["clean_image"]).read_bytes(), dtype=np.uint8), cv2.IMREAD_COLOR)
        image_matches = clean is not None and np.array_equal(clean, samples[info["source_frame"]])
        tokens = (ROOT/clip["converted_label"]).read_text(encoding="utf-8").split()
        expected = validate_row(source)["yolo"]
        label_matches = len(tokens) == 5 and tokens[0] == "0" and all(abs(float(a)-b) < 1e-9 for a,b in zip(tokens[1:], expected[1:]))
        independent = None
        if probe:
            decoded = subprocess.run([probe, "-v", "error", "-select_streams", "v:0", "-show_frames",
                                      "-show_entries", "frame=best_effort_timestamp_time", "-of", "json",
                                      str(ROOT/clip["source_video"])], check=True, capture_output=True, text=True, timeout=60)
            points = [float(x["best_effort_timestamp_time"]) for x in json.loads(decoded.stdout)["frames"]]
            independent = check_timestamps(points, info["source_frame"], float(source["accident_time"]))
            independent["decoded_frames"] = len(points)
        passed = image_matches and label_matches and info["pts_mapping_verified"] and (
            independent is None or independent["pts_mapping_verified"] and independent["decoded_frames"] == info["decoded_frames"])
        results.append(dict(source_sequence=clip["source_sequence"], **info,
                            clean_png_pixel_exact=image_matches, yolo_matches_source=label_matches,
                            ffprobe_check=independent, technical_checks_passed=passed))
    save_json(destination, dict(source_report=relative(report_path), clips=results,
                               all_technical_checks_passed=all(x["technical_checks_passed"] for x in results),
                               independent_decoder_available=bool(probe), split_created=False, can_train=False))
    print(f"Verification: {relative(destination)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit public ACCIDENT impact boxes (default six clips), no full download/split/train")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--fetch-selected", action="store_true")
    mode.add_argument("--offline", action="store_true")
    mode.add_argument("--verify-report", type=Path, help="Verify existing output without new media or network")
    mode.add_argument("--prepare-preimpact", type=Path,
                      help="Tạo ảnh ứng viên trước impact từ report đã verify; chưa gán nhãn âm")
    mode.add_argument("--verify-preimpact", type=Path, help="Decode lại để so pixel/PTS/hash các ảnh ứng viên")
    parser.add_argument("--max-mib", type=int, default=16)
    parser.add_argument("--raw-root", type=Path, default=Path("data_raw/accident/public_selected"))
    parser.add_argument("--output", type=Path, help="New canonical data audit directory")
    parser.add_argument("--members", nargs="+", default=list(SELECTED),
                        help="Exact video member paths from inspected first-page listing; default six selected clips")
    args = parser.parse_args()
    if args.verify_preimpact:
        verify_preimpact(args.verify_preimpact)
        return 0
    if args.prepare_preimpact:
        output = require_output_path(ROOT, args.output or output_path(ROOT,'data_audit','v013_accident_preimpact'), 'data_audit')
        prepare_preimpact(args.prepare_preimpact, output)
        return 0
    if args.verify_report:
        verify_report(args.verify_report)
        return 0
    raw, output = inside(args.raw_root), require_output_path(ROOT, args.output or output_path(ROOT,'data_audit','v005_accident_public'), 'data_audit')
    if args.max_mib <= 0 or output.exists():
        parser.error("Positive budget and a NEW output directory are required")
    if len(set(args.members)) != len(args.members):
        parser.error("Duplicate member paths are not independent samples")
    if shutil.disk_usage(ROOT).free < args.max_mib*1024**2 + 512*1024**2:
        raise OSError("Insufficient free space including 512 MiB reserve")
    raw.mkdir(parents=True, exist_ok=True)
    receipt_path = raw/"download_receipts.json"
    receipts = json.loads(receipt_path.read_text(encoding="utf-8")) if receipt_path.exists() else {}
    network = BudgetDownload(args.max_mib*1024**2)
    metadata = ensure_file(raw, "metadata-real.csv", network, args.offline, receipts)
    with metadata.open(encoding="utf-8-sig", newline="") as stream:
        source_rows = list(csv.DictReader(stream))
    by_path = {r["path"]: r for r in source_rows}
    if len(by_path) != len(source_rows):
        raise ValueError("Duplicate source metadata paths")
    rejected = []
    for row in source_rows:
        try:
            validate_row(row)
        except ValueError as error:
            rejected.append(dict(path=row["path"], reason=str(error)))
    # Chỉ danh mục trang đầu dùng chọn sáu clip, không giả là đã kiểm toàn media.
    listing_path = raw/"source_file_listing.json"
    if not listing_path.exists():
        if args.offline:
            raise FileNotFoundError(listing_path)
        body = network.get(f"https://www.kaggle.com/api/v1/datasets/list/{DATASET}?datasetVersionNumber={VERSION}&pageSize=100", 500_000)
        listing_path.write_bytes(body)
    listing = json.loads(listing_path.read_bytes())
    sizes = {x["name"]: int(x["totalBytes"]) for x in listing["datasetFiles"]}
    if any(p not in sizes or p not in by_path for p in args.members):
        raise ValueError("Selected member not in pinned metadata/inspected first listing page")
    results, panels = [], []
    import cv2
    import numpy as np
    output.mkdir(parents=True, exist_ok=False)
    (output/"images").mkdir()
    (output/"labels_yolo").mkdir()
    for name in args.members:
        row = by_path[name]
        if row["type"] not in MULTI_VEHICLE_TYPES:
            raise ValueError("Selected event outside vehicle-vehicle scope")
        video = ensure_file(raw, name, network, args.offline, receipts, sizes[name])
        info, samples = inspect_video(video, row)
        frame, stem = info["source_frame"], PurePosixPath(name).stem
        image_path = output/"images"/f"{stem}_f{frame:06d}.png"
        save_image(image_path, samples[frame])
        label_path = output/"labels_yolo"/f"{image_path.stem}.txt"
        label = validate_row(row)["yolo"]
        label_path.write_text("0 " + " ".join(f"{v:.10f}" for v in label[1:]) + "\n", encoding="utf-8")
        # Chỉ panel ở đúng impact có bbox tác giả. Không vẽ nhãn lên PNG sạch
        # dùng về sau; ID video/source group cũng không là ID tracker.
        strip = []
        for f in (max(0, frame-3), frame, min(info["decoded_frames"]-1, frame+3)):
            picture = samples[f].copy()
            if f == frame:
                x1, y1, x2, y2 = info["xyxy_norm"]
                cv2.rectangle(picture, (round(x1*info["width"]), round(y1*info["height"])),
                              (round(x2*info["width"]), round(y2*info["height"])), (0, 0, 255), 2)
            picture = cv2.resize(picture, (480, 270))
            cv2.rectangle(picture, (0, 0), (480, 37), (0, 0, 0), -1)
            caption = f"{stem} f={f}" + (" AUTHOR IMPACT BOX" if f == frame else " CLEAN CONTEXT")
            cv2.putText(picture, caption, (5, 23), cv2.FONT_HERSHEY_SIMPLEX, .42, (255,255,255), 1)
            strip.append(picture)
        panels.append(np.hstack(strip))
        group = stem.rsplit("_", 1)[0]
        results.append(dict(source_dataset="ACCIDENT", source_sequence=stem, source_group=f"ACCIDENT:{group}",
                            source_video=relative(video), video_sha256=sha256_file(video), video_size_bytes=video.stat().st_size,
                            source_metadata=relative(metadata), metadata_sha256=METADATA_SHA256,
                            source_type=row["type"], quality=row["quality"], region=row["region"],
                            **info,
                            clean_image=relative(image_path), image_sha256=sha256_file(image_path),
                            converted_label=relative(label_path), label_sha256=sha256_file(label_path),
                            label_origin="author_accident_impact_region", label_scope="impact_frame_only",
                            other_frames="unknown_for_bbox_supervision", user_review_status="not_requested_not_user_reviewed",
                            ai_visual_review="pending", split="unassigned", training_release_allowed=False))
        print(f"Checked: {name}, {info['decoded_frames']} decoded, impact {frame}", flush=True)
    save_image(output/"impact_comparisons.jpg", np.vstack(panels))
    save_csv(output/"impact_frames.csv", results, list(results[0]))
    report = dict(dataset=DATASET, version=VERSION, source_url="https://www.kaggle.com/datasets/picekl/accident/versions/9",
                  paper="https://arxiv.org/abs/2604.09819",
                  date=datetime.now(timezone(timedelta(hours=7))).date().isoformat(),
                  metadata_rows=len(source_rows), metadata_sha256=METADATA_SHA256,
                  metadata_invalid_rows=rejected, listed_files_this_page=len(sizes),
                  selected_clips=results, total_decoded_frames=sum(x["decoded_frames"] for x in results),
                  author_region_frames=len(results), network_bytes_this_run=network.transferred,
                  full_dataset_downloaded=False, split_created=False, can_train=False,
                  label_scope="one author box at source impact frame; NOT a box for every video frame",
                  frame_index_caveat="0-based decode interpretation checked visually; source CSV kept unchanged; no auto-fix for out-of-range rows",
                  license="CC BY-NC-SA 4.0 per Kaggle metadata; media not redistributed on Git")
    save_json(output/"report.json", report)
    print(f"Report: {relative(output/'report.json')}")
    return 0


def verify_preimpact(path: Path) -> None:
    """Đọc lại video và PNG để kiểm mapping từng ứng viên, không duyệt nhãn âm."""
    import cv2
    import numpy as np
    path = inside(path)
    report = json.loads(path.read_text(encoding="utf-8"))
    grouped = {}
    for row in report["candidates"]:
        grouped.setdefault(row["source_video"], []).append(row)
    verified = []
    for video, candidates in grouped.items():
        source = inside(ROOT/video)
        if any(sha256_file(source) != r["video_sha256"] for r in candidates):
            raise ValueError("Candidate source video changed")
        wanted = {r["source_frame"]:r for r in candidates}
        cap = cv2.VideoCapture(str(source))
        try:
            for index in range(max(wanted)+1):
                ok, frame = cap.read()
                if not ok:
                    raise ValueError("Candidate frame missing")
                if index not in wanted:
                    continue
                row = wanted[index]
                image = inside(ROOT/row["image"])
                png = cv2.imdecode(np.frombuffer(image.read_bytes(),np.uint8),1)
                if sha256_file(image) != row["image_sha256"] or not np.array_equal(frame,png):
                    raise ValueError("Candidate PNG differs from decoded source")
                if abs(cap.get(cv2.CAP_PROP_POS_MSEC)/1000-row["pts_seconds"]) > 1e-6:
                    raise ValueError("Candidate PTS mismatch")
                verified.append(dict(source_sequence=row["source_sequence"], source_frame=index,
                                     pixel_exact=True, pts_matches=True))
        finally:
            cap.release()
    save_json(path.parent/"verification.json",dict(candidate_report_sha256=sha256_file(path),
              frames=verified, all_technical_checks_passed=True, semantic_labels_verified=False))
    print(f"Verified {len(verified)} preimpact images")


def preimpact_indices(points: list[float], impact: int, margin: float = 1.0) -> list[int]:
    """Chọn tối đa ba ảnh ở nửa đầu trước impact, cách impact ít nhất một giây PTS.

    Khoảng đệm chỉ dùng sàng lọc; không chứng minh cả cảnh không có va chạm.
    Giây ở đây thuộc file phát hành, không phải FPS camera gốc.
    """
    if not 0 <= impact < len(points) or margin <= 0:
        raise ValueError("Invalid impact or margin")
    if not all(math.isfinite(p) for p in points) or any(b <= a for a,b in zip(points,points[1:])):
        raise ValueError("Invalid/nonmonotonic PTS")
    eligible = [i for i in range((impact+1)//2) if points[impact]-points[i] >= margin]
    return sorted({eligible[i] for i in (0, len(eligible)//2, len(eligible)-1)}) if eligible else []


def prepare_preimpact(report_path: Path, output: Path) -> None:
    """Xuất ứng viên sạch và phiếu truy nguồn để rà âm cùng cảnh trước khi nhập pool.

    Chỉ chạy sau verify. Không tạo TXT rỗng, không tự coi mọi frame trước
    impact là âm. Người rà phải ghi quyết định cho từng ảnh, tách nguồn tác giả.
    """
    import cv2
    import numpy as np
    report_path, output = inside(report_path), inside(output)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    verification_path = report_path.parent/"verification.json"
    verification = json.loads(verification_path.read_text(encoding="utf-8"))
    verified = {r["source_sequence"]:r for r in verification["clips"]}
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    rows, panels, skipped = [], [], []
    for clip in report["selected_clips"]:
        if not verified[clip["source_sequence"]]["technical_checks_passed"]:
            skipped.append(clip["source_sequence"])
            continue
        video = inside(ROOT/clip["source_video"])
        if sha256_file(video) != clip["video_sha256"]:
            raise ValueError("Video changed since impact audit")
        # Lượt đầu chỉ giữ PTS; lượt sau giữ tối đa ba ảnh, tránh tích video HD
        # trong RAM. Cả hai lượt đều decode tuần tự, không seek theo FPS.
        cap = cv2.VideoCapture(str(video))
        frames, points = {}, []
        try:
            for _ in range(clip["source_frame"]+1):
                ok, frame = cap.read()
                if not ok:
                    raise ValueError("Missing preimpact frame")
                points.append(cap.get(cv2.CAP_PROP_POS_MSEC)/1000)
        finally:
            cap.release()
        chosen = preimpact_indices(points, clip["source_frame"])
        cap = cv2.VideoCapture(str(video))
        try:
            for index in range(max(chosen, default=-1)+1):
                ok, frame = cap.read()
                if not ok:
                    raise ValueError("Missing frame during candidate materialization")
                if index in chosen:
                    frames[index] = frame
        finally:
            cap.release()
        strip = []
        for index in chosen:
            path = output/f"{clip['source_sequence']}_f{index:06d}.png"
            save_image(path, frames[index])
            rows.append(dict(source_sequence=clip["source_sequence"], source_frame=index,
                             source_group=clip["source_group"], source_video=clip["source_video"],
                             video_sha256=clip["video_sha256"], image=relative(path), image_sha256=sha256_file(path),
                             pts_seconds=points[index], impact_frame=clip["source_frame"],
                             impact_pts_seconds=points[-1], margin_seconds=points[-1]-points[index],
                             collision_label="unknown", review_status="pending_frame_scope_review"))
            panel = cv2.resize(frames[index], (480,270))
            cv2.putText(panel, f"f={index} gap={points[-1]-points[index]:.2f}s PENDING", (8,25),
                        cv2.FONT_HERSHEY_SIMPLEX,.5,(0,255,255),1)
            strip.append(panel)
        if strip:
            while len(strip)<3:
                strip.append(np.zeros((270,480,3),np.uint8))
            header = np.zeros((30,1440,3),np.uint8)
            cv2.putText(header,clip["source_sequence"],(8,22),cv2.FONT_HERSHEY_SIMPLEX,.6,(255,255,255),1)
            panels.append(np.vstack([header,np.hstack(strip)]))
        else:
            skipped.append(clip["source_sequence"])
    for start in range(0,len(panels),4):
        save_image(output/f"review_{start//4+1:02d}.jpg",np.vstack(panels[start:start+4]))
    save_json(output/"report.json",dict(source_report=relative(report_path),
              source_report_sha256=sha256_file(report_path), verification_sha256=sha256_file(verification_path),
              candidates=rows, skipped_sequences=skipped, margin_seconds=1.0,
              selection="up to 3 first-half preimpact frames with >=1s released-file PTS margin",
              label_status="ALL UNKNOWN pending scoped visual review", training_release_allowed=False))
    print(f"Prepared {len(rows)} UNKNOWN candidates: {relative(output/'report.json')}")


if __name__ == "__main__":
    raise SystemExit(main())
