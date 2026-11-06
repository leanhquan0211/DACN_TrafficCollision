"""Kiểm kê ZIP DETRAC, lấy chọn lọc chuỗi ảnh và ghép thành MP4 để xem thử.

Đầu vào: ZIP ảnh hoặc thư mục chuỗi đã giải nén, tên chuỗi và FPS có nguồn.
Đầu ra: ảnh giữ nguyên đường dẫn tương đối, MP4 đầy đủ/clip ngắn và audit JSON/CSV.
Chạy trước detection/tracking; không gán nhãn tai nạn hoặc tạo split dữ liệu.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import zipfile
import zlib
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.data_preparation import H264Writer, clip_video, probe_video, save_csv, save_json, unique_path


IMAGE_NAME = re.compile(r"img(\d+)\.(jpg|jpeg|png)", re.IGNORECASE)


def numbered_images(folder: Path) -> list[tuple[int, Path]]:
    """Sắp theo số frame: img2 đứng trước img10, không theo thứ tự chữ."""
    result = []
    for path in folder.iterdir():
        if path.is_file() and path.suffix.lower() in (".jpg", ".jpeg", ".png"):
            match = IMAGE_NAME.fullmatch(path.name)
            if match is None:
                raise ValueError(f"Unrecognized image filename: {path}")
            result.append((int(match[1]), path))
    result.sort(key=lambda item: item[0])
    numbers = [number for number, _ in result]
    if not numbers or len(set(numbers)) != len(numbers):
        raise ValueError(f"Empty sequence or duplicate frame numbers: {folder}")
    missing = sorted(set(range(1, numbers[-1] + 1)) - set(numbers))
    if missing:
        raise ValueError(f"Missing frame numbers in {folder}: {missing[:30]}")
    return result


def read_image(path: Path):
    """Đọc qua byte để đường dẫn tiếng Việt trên Windows vẫn hoạt động."""
    import cv2
    import numpy as np

    image = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Corrupt/unreadable image: {path}")
    return image


def safe_destination(root: Path, member: str) -> Path:
    """Chặn đường dẫn ZIP vượt ra khỏi thư mục dữ liệu được chỉ định."""
    parts = PurePosixPath(member.replace("\\", "/"))
    if parts.is_absolute() or ".." in parts.parts or any(":" in part for part in parts.parts):
        raise ValueError(f"Unsafe ZIP member: {member}")
    resolved_root = root.resolve()
    result = resolved_root.joinpath(*parts.parts).resolve()
    if not result.is_relative_to(resolved_root):
        raise ValueError(f"ZIP member escapes destination: {member}")
    return result


def file_crc32(path: Path) -> int:
    crc = 0
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            crc = zlib.crc32(data, crc)
    return crc & 0xFFFFFFFF


def extract_selected(archive: zipfile.ZipFile, root: Path, selected: list[zipfile.ZipInfo]) -> dict:
    """Tái dùng ảnh đã có nếu CRC khớp; chỉ giải nén file còn thiếu, không ghi đè."""
    root.mkdir(parents=True, exist_ok=True)
    missing_bytes, reused = 0, 0
    for info in selected:
        target = safe_destination(root, info.filename)
        if target.exists():
            if not target.is_file() or target.stat().st_size != info.file_size or file_crc32(target) != info.CRC:
                raise ValueError(f"Existing file differs from ZIP; preserved: {target}")
            reused += 1
        else:
            missing_bytes += info.file_size
    free = shutil.disk_usage(root.resolve()).free
    # Chừa 1 GiB cho video và hoạt động hệ thống, ngoài lượng ảnh cần lấy.
    if free < missing_bytes + 1024**3:
        raise OSError(f"Insufficient free space: need {missing_bytes} bytes + 1 GiB, have {free}")
    extracted = 0
    for info in selected:
        target = safe_destination(root, info.filename)
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        created = False
        try:
            with archive.open(info) as source, target.open("xb") as dest:
                created = True
                shutil.copyfileobj(source, dest, 1024 * 1024)
            if target.stat().st_size != info.file_size or file_crc32(target) != info.CRC:
                raise ValueError(f"Extracted CRC mismatch: {target}")
        except Exception:
            # File này vừa được tạo bằng xb; không đụng tới ảnh có sẵn trước lượt chạy.
            if created and target.exists():
                target.unlink()
            raise
        extracted += 1
    return dict(free_bytes_before=free, new_image_bytes=missing_bytes,
                extracted_files=extracted, reused_matching_files=reused)


def annotation_metadata(root: Path, sequence: str) -> list[dict]:
    """Chỉ kiểm tra XML thật có trong ZIP địa phương; đây là nhãn xe, không nhãn tai nạn."""
    results = []
    for path in sorted(root.glob("annotations/*.zip")):
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                if PurePosixPath(name).name != sequence + ".xml":
                    continue
                xml = ET.fromstring(archive.read(name))
                if xml.attrib.get("name") != sequence:
                    raise ValueError(f"XML sequence name mismatch: {path}!{name}")
                frames = [int(frame.attrib["num"]) for frame in xml.findall("frame")]
                types = sorted({a.attrib.get("vehicle_type", "") for a in xml.findall(".//attribute")})
                targets = xml.findall(".//target")
                sequence_attributes = xml.find("sequence_attribute")
                results.append(dict(archive=str(path), member=name, sequence_name=xml.attrib.get("name"),
                                    frame_count=len(frames), first_frame=min(frames) if frames else None,
                                    last_frame=max(frames) if frames else None, boxes=len(targets),
                                    frame_numbers_contiguous=bool(frames) and sorted(frames) == list(range(1, max(frames)+1)),
                                    sequence_attributes=dict(sequence_attributes.attrib) if sequence_attributes is not None else {},
                                    vehicle_types=types, collision_label="unknown", user_review_status="pending"))
    return results


def prepare_sequence(folder: Path, output: Path, fps: float) -> dict:
    images = numbered_images(folder)
    width, height = None, None
    # Kiểm tra toàn bộ ảnh và kích thước trước khi ghi MP4: gặp ảnh thiếu/lỗi
    # sẽ dừng, không lấp bằng frame giả và không âm thầm đổi nhịp video.
    for _, path in images:
        image = read_image(path)
        h, w = image.shape[:2]
        if width is None:
            width, height = w, h
        if (w, h) != (width, height):
            raise ValueError(f"Inconsistent image dimensions: {path}")
    with H264Writer(output, width, height, fps) as writer:
        for _, path in images:
            writer.write(read_image(path))
    info = probe_video(output)
    if info["decoded_frames"] != len(images) or abs(info["fps"] - fps) > .001:
        raise ValueError("Encoded video differs from image count/FPS")
    return dict(sequence=folder.name, image_directory=str(folder),
                first_image=images[0][1].name, last_image=images[-1][1].name,
                first_image_number=images[0][0], last_image_number=images[-1][0],
                missing_images=[], corrupt_images=[], output=str(output), video_info=info)


def main() -> int:
    parser = argparse.ArgumentParser(description="Selectively extract DETRAC image sequences and create verified MP4 previews")
    parser.add_argument("--archive", type=Path, default=Path("data_raw/ua_detrac/DETRAC-Images.zip"))
    parser.add_argument("--raw-root", type=Path, default=Path("data_raw/ua_detrac"))
    parser.add_argument("--sequences", nargs="+", required=True, help="Exact sequence names, e.g. MVI_20011 MVI_20012")
    parser.add_argument("--fps", type=float, required=True)
    parser.add_argument("--fps-status", choices=("verified_source", "assumed"), default="assumed")
    parser.add_argument("--fps-source", default="", help="Document/official paper supporting FPS")
    parser.add_argument("--video-root", type=Path, default=Path("data_samples/ua_detrac"))
    parser.add_argument("--audit-root", type=Path, default=Path("outputs/data_audits"))
    parser.add_argument("--audit-name", default="v002_detrac_preparation", help="Tên mới dạng vNNN_mo_ta; không ghi đè audit cũ")
    parser.add_argument("--smoke-seconds", type=float, default=10, help="First sequence clip, maximum 30 seconds")
    args = parser.parse_args()
    if len(set(args.sequences)) != len(args.sequences) or any(re.fullmatch(r"MVI_\d+", s) is None for s in args.sequences):
        parser.error("Use distinct exact MVI_<number> sequence names")
    if not 0 < args.fps < 1000 or not 0 < args.smoke_seconds <= 30:
        parser.error("Invalid FPS or smoke duration")
    if args.fps_status == "verified_source" and not args.fps_source.strip():
        parser.error("--fps-source is required for verified_source")
    if not re.fullmatch(r"v\d{3}_[a-z0-9_]+", args.audit_name):
        parser.error("--audit-name phải có dạng vNNN_mo_ta")
    audit = args.audit_root / args.audit_name
    audit.mkdir(parents=True, exist_ok=False)
    report = dict(archive=str(args.archive), selected_sequences=args.sequences,
                  fps=args.fps, fps_status=args.fps_status, fps_source=args.fps_source,
                  collision_label="unknown", user_review_status="pending", sequences=[])
    try:
        if args.archive.is_file():
            with zipfile.ZipFile(args.archive) as archive:
                # Đọc central directory trước; không extractall và không đổi tên
                # thư mục DETRAC-Images/MVI_*/img00001.jpg của bộ gốc.
                groups = defaultdict(list)
                files = [i for i in archive.infolist() if not i.is_dir()]
                if len({i.filename for i in files}) != len(files):
                    raise ValueError("Duplicate ZIP member names; inspect before extracting")
                for info in files:
                    parts = PurePosixPath(info.filename.replace("\\", "/"))
                    if len(parts.parts) == 3 and parts.parts[0] == "DETRAC-Images" and IMAGE_NAME.fullmatch(parts.name):
                        groups[parts.parts[1]].append(info)
                if sum(map(len, groups.values())) != len(files):
                    raise ValueError("ZIP has unexpected members; inspect manually before extracting")
                inventory = []
                for sequence, members in sorted(groups.items()):
                    members.sort(key=lambda i: int(IMAGE_NAME.fullmatch(PurePosixPath(i.filename).name)[1]))
                    inventory.append(dict(sequence=sequence, image_count=len(members),
                                          uncompressed_bytes=sum(i.file_size for i in members),
                                          first_member=members[0].filename, last_member=members[-1].filename,
                                          selected=sequence in args.sequences))
                save_csv(audit / "archive_sequences.csv", inventory, list(inventory[0]))
                report["archive_inventory"] = dict(file_count=len(files), sequence_count=len(groups),
                                                   compressed_bytes=args.archive.stat().st_size,
                                                   uncompressed_bytes=sum(i.file_size for i in files))
                for sequence in args.sequences:
                    if sequence not in groups:
                        raise ValueError(f"Sequence not in ZIP: {sequence}")
                selected = [i for sequence in args.sequences for i in groups[sequence]]
                report["extraction"] = extract_selected(archive, args.raw_root, selected)
        else:
            report["extraction"] = dict(status="using_existing_directories_archive_not_present")
        args.video_root.mkdir(parents=True, exist_ok=True)
        for sequence in args.sequences:
            folder = args.raw_root / "DETRAC-Images" / sequence
            output = unique_path(args.video_root / f"{sequence}.mp4")
            result = prepare_sequence(folder, output, args.fps)
            result["author_vehicle_annotations"] = annotation_metadata(args.raw_root, sequence)
            for metadata in result["author_vehicle_annotations"]:
                if (metadata["first_frame"] != result["first_image_number"] or
                    metadata["last_frame"] != result["last_image_number"] or
                    metadata["frame_count"] != result["video_info"]["decoded_frames"] or
                    not metadata["frame_numbers_contiguous"]):
                    raise ValueError(f"XML/image frame range mismatch: {sequence}")
            report["sequences"].append(result)
            print(f"SEQUENCE_OK {sequence}: {result['video_info']['decoded_frames']} frames -> {output}", flush=True)
        first = report["sequences"][0]
        clip = unique_path(args.video_root / f"{first['sequence']}_first_{args.smoke_seconds:g}s.mp4")
        info = clip_video(Path(first["output"]), clip, args.smoke_seconds)
        report["smoke_clip"] = dict(output=str(clip), parent_video=first["output"],
                                    source_sequence=first["sequence"], source_start_frame=1,
                                    source_end_frame=info["decoded_frames"], video_info=info,
                                    collision_label="unknown", user_review_status="pending")
    except Exception as exc:
        report["error"] = str(exc)
        save_json(audit / "report.json", report)
        raise
    save_json(audit / "report.json", report)
    print(f"AUDIT {audit}; SMOKE_CLIP {report['smoke_clip']['output']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
