"""Kiểm tra chuỗi CADP sạch, đối chiếu VATIC và tạo video trình chiếu riêng.

Đầu vào: ZIP/thư mục 001407, TXT và demo tác giả đã xác minh. Đầu ra: ảnh
nguồn giữ nguyên, CSV gốc/chuẩn hóa, ảnh đối chiếu, báo cáo và hai MP4 riêng.
FPS trình chiếu không phải FPS nguồn; chỉ tạo MP4 khi mapping kỹ thuật đạt
và người chạy đã kiểm tra trực quan các ảnh mẫu bằng --visual-check-confirmed.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import zipfile
from collections import defaultdict
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.prepare_cadp_pilot import read_vatic, summarize, verify_alignment
from scripts.prepare_detrac import file_crc32, read_image, safe_destination
from src.data_preparation import H264Writer, new_audit_dir, probe_video, save_csv, save_json, sha256_file, unique_path


SAMPLE_FRAMES = (0, 60, 95, 96, 110, 130, 131, 180, 220)


def stage_archive(path: Path, destination: Path, sequence: str) -> dict:
    """Chỉ lấy ảnh dưới thư mục đúng sequence, không tạo 001407/001407.

    Tên ảnh nguồn không đổi. File đã có chỉ được tái dùng nếu cùng size/CRC;
    không xóa ZIP và không ghi đè nội dung khác.
    """
    with zipfile.ZipFile(path) as archive:
        files = [i for i in archive.infolist() if not i.is_dir()]
        selected = []
        for info in files:
            member = PurePosixPath(info.filename.replace("\\", "/"))
            safe_destination(destination.parent, info.filename)
            if len(member.parts) >= 2 and member.parts[-2] == sequence and member.suffix.lower() in (".jpg", ".jpeg", ".png"):
                if not member.stem.isdecimal():
                    raise ValueError(f"Non-numeric frame name: {member}")
                selected.append(info)
        if not selected or len({PurePosixPath(i.filename).name for i in selected}) != len(selected):
            raise ValueError("Missing sequence or duplicate source filenames in ZIP")
        if len({int(PurePosixPath(i.filename).stem) for i in selected}) != len(selected):
            raise ValueError("Duplicate numeric frame indices in ZIP")
        bad = archive.testzip()
        if bad is not None:
            raise ValueError(f"ZIP CRC failure: {bad}")
        destination.mkdir(parents=True, exist_ok=True)
        missing = 0
        for info in selected:
            target = safe_destination(destination, PurePosixPath(info.filename).name)
            if target.exists():
                if not target.is_file() or target.stat().st_size != info.file_size or file_crc32(target) != info.CRC:
                    raise ValueError(f"Existing source differs; preserved: {target}")
            else:
                missing += info.file_size
        free = shutil.disk_usage(destination).free
        # Dự trù 128 MiB cho video/audit và chừa 512 MiB; chỉ một chuỗi nhỏ.
        reserve = (512 + 128) * 1024**2
        if free < missing + reserve:
            raise OSError(f"Need {missing + reserve} bytes including reserve; have {free}")
        extracted = 0
        for info in selected:
            target = safe_destination(destination, PurePosixPath(info.filename).name)
            if target.exists():
                continue
            created = False
            try:
                with archive.open(info) as source, target.open("xb") as output:
                    created = True
                    shutil.copyfileobj(source, output, 1024 * 1024)
                if file_crc32(target) != info.CRC:
                    raise ValueError(f"Extracted CRC mismatch: {target}")
            except Exception:
                if created and target.exists():
                    target.unlink()
                raise
            extracted += 1
        return dict(archive=path.as_posix(), archive_sha256=sha256_file(path),
                    member_count=len(files), selected_count=len(selected),
                    selected_bytes=sum(i.file_size for i in selected),
                    first_zip_members=[i.filename for i in selected[:6]],
                    free_bytes_before=free, reserve_bytes=reserve, extracted_files=extracted,
                    reused_files=len(selected)-extracted, crc_valid=True)


def inspect_frames(folder: Path) -> tuple[dict[int, Path], list[dict], tuple[int, int]]:
    """Đọc hết ảnh, kiểm tra số frame, kích thước và ghi hash từng ảnh nguồn."""
    images, records, size = {}, [], None
    for path in folder.iterdir():
        if path.suffix.lower() not in (".jpg", ".jpeg", ".png"):
            continue
        if not path.stem.isdecimal() or int(path.stem) in images:
            raise ValueError(f"Invalid/duplicate source frame: {path}")
        images[int(path.stem)] = path
    if not images:
        raise ValueError(f"No source images: {folder}")
    if sorted(images) != list(range(max(images)+1)):
        raise ValueError("Expected contiguous zero-based frame numbers; no automatic offset applied")
    for frame, path in sorted(images.items()):
        image = read_image(path)
        h, w = image.shape[:2]
        if size is None:
            size = (w, h)
        if size != (w, h):
            raise ValueError(f"Inconsistent image size: {path}")
        records.append(dict(source_frame=frame, relative_path=path.as_posix(),
                            size_bytes=path.stat().st_size, sha256=sha256_file(path),
                            width_px=w, height_px=h))
    return images, records, size


def draw_annotations(image, rows: list[dict], frame_number: int, fps: float):
    """Vẽ lên bản sao ảnh, giữ GT ID khác hoàn toàn với ID của ByteTrack."""
    import cv2

    output = image.copy()
    for row in rows:
        if row["outside"]:
            continue
        colliding = "Colliding" in row["attributes"]
        color = (0, 0, 255) if colliding else ((128, 128, 128) if row["label"] == "FarRegion" else (0, 200, 0))
        x1, y1, x2, y2 = row["bbox"]
        cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)
        label = f"GT {row['track_id']} {row['label']}" + (" Colliding" if colliding else "")
        cv2.putText(output, label, (x1, max(65, y1-6)), cv2.FONT_HERSHEY_SIMPLEX, .45, color, 1)
    cv2.rectangle(output, (0, 0), (output.shape[1]-1, 55), (0, 0, 0), -1)
    cv2.putText(output, "AUTHOR VATIC / GT IDs - NOT MODEL PREDICTION", (8, 21), cv2.FONT_HERSHEY_SIMPLEX, .55, (255, 255, 255), 1)
    cv2.putText(output, f"Source frame {frame_number} | display {fps:g} FPS only | original timing unknown", (8, 45), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 1)
    return output


def compare_reference(images: dict[int, Path], rows: list[dict], demo: Path,
                      config: dict, audit: Path, fps: float) -> tuple[list[dict], bool]:
    """So ảnh sạch với demo tác giả sau khi bỏ ảnh hưởng viền/bbox/text.

    MAE và offset lân cận chỉ là hỗ trợ kiểm tra mapping, không phải metric CV
    của model. Lưu cả trường hợp gần hòa do nén video; không đổi số frame theo MAE.
    """
    import cv2
    import numpy as np

    width, height = read_image(images[0]).shape[1::-1]
    sx, sy, tx, ty = config["bbox_transform"]
    matrix = np.array([[sx, 0, tx], [0, sy, ty]], dtype=np.float32)
    by_frame = defaultdict(list)
    for row in rows:
        by_frame[row["frame"]].append(row)
    capture = cv2.VideoCapture(str(demo))
    checks, thumbnails = [], []
    try:
        for number in SAMPLE_FRAMES:
            if number not in images:
                raise ValueError(f"Missing verification frame {number}")
            capture.set(cv2.CAP_PROP_POS_FRAMES, number)
            ok, rendered = capture.read()
            if not ok:
                raise ValueError(f"Cannot read reference frame {number}")
            back = cv2.warpAffine(rendered, matrix, (width, height), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP)
            mask = np.ones((height, width), dtype=np.uint8)
            mask[:85] = 0
            for row in by_frame[number]:
                if row["outside"]:
                    continue
                x1, y1, x2, y2 = row["bbox"]
                if row["label"] in ("FarRegion", "CrowdRegion"):
                    cv2.rectangle(mask, (x1, y1), (x2, y2), 0, -1)
                else:
                    cv2.rectangle(mask, (x1, y1), (x2, y2), 0, 12)
                cv2.rectangle(mask, (max(0, x1-10), max(0, y1-24)),
                              (min(width-1, max(x2, x1+260)), min(height-1, y1+16)), 0, -1)
            scores = {}
            for offset in range(-3, 4):
                if number+offset not in images:
                    continue
                clean = read_image(images[number+offset])
                difference = np.mean(np.abs(clean.astype(np.float32)-back.astype(np.float32)), axis=2)
                scores[offset] = float(difference[mask > 0].mean())
            best = min(scores, key=scores.get)
            checks.append(dict(source_frame=number, demo_frame=number, best_neighbor_offset=best,
                               same_frame_mae=scores[0], best_mae=scores[best],
                               excess_mae=scores[0]-scores[best], masked_pixels=int(mask.sum()),
                               neighbor_scores=json.dumps(scores)))
            clean = read_image(images[number])
            overlay = draw_annotations(clean, by_frame[number], number, fps)
            panels = []
            for title, picture in (("CLEAN SOURCE", clean), ("AUTHOR TXT ON CLEAN", overlay), ("AUTHOR DEMO / RECOVERED REGION", back)):
                panel = cv2.resize(picture, (640, 360))
                panel = cv2.copyMakeBorder(panel, 28, 0, 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255))
                cv2.putText(panel, f"{number}: {title}", (6, 20), cv2.FONT_HERSHEY_SIMPLEX, .48, (0, 0, 0), 1)
                panels.append(panel)
            cv2.imwrite(str(audit / f"comparison_{number:03}.jpg"), cv2.hconcat(panels))
            thumbnail = cv2.resize(clean, (480, 270))
            cv2.putText(thumbnail, f"Source frame {number}", (8, 26), cv2.FONT_HERSHEY_SIMPLEX, .65, (0, 255, 255), 2)
            thumbnails.append(thumbnail)
    finally:
        capture.release()
    cv2.imwrite(str(audit / "clean_contact_sheet.jpg"), cv2.vconcat([cv2.hconcat(thumbnails[i:i+3]) for i in (0, 3, 6)]))
    # Giới hạn hỗ trợ cho demo này: cùng frame gần nhất hoặc gần hòa trong
    # 0,15 mức màu/255; vẫn cần kiểm trực quan bằng cờ CLI trước khi tạo video.
    passed = all(c["same_frame_mae"] < 12 and c["excess_mae"] <= .15 for c in checks) and sum(c["best_neighbor_offset"] == 0 for c in checks) >= len(checks)-1
    return checks, passed


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit clean CADP 001407 frames and create presentation-only videos")
    parser.add_argument("--archive", type=Path, help="Optional ZIP; existing image directory is usable without ZIP")
    parser.add_argument("--frames-dir", type=Path, default=Path("data_raw/cadp/frames/001407"))
    parser.add_argument("--annotations", type=Path, default=Path("data_raw/cadp/pilot_1407/1407.txt"))
    parser.add_argument("--demo", type=Path, default=Path("data_raw/cadp/pilot_1407/1407.mp4"))
    parser.add_argument("--reference-zip", type=Path, default=Path("data_raw/cadp/reference_code/CarCrash_forecasting_and_detection-master.zip"))
    parser.add_argument("--demo-config", type=Path, default=Path("configs/cadp_1407_preview.json"))
    parser.add_argument("--presentation-fps", type=float, default=20)
    parser.add_argument("--visual-check-confirmed", action="store_true", help="Operator checked clean images/GT mapping; not user onset/end confirmation")
    parser.add_argument("--audit-root", type=Path, default=Path("outputs/audits"))
    parser.add_argument("--video-root", type=Path, default=Path("data_samples/cadp"))
    parser.add_argument("--preview-root", type=Path, default=Path("outputs/annotation_preview"))
    args = parser.parse_args()
    if not 0 < args.presentation_fps < 1000:
        parser.error("Invalid presentation FPS")
    audit = new_audit_dir(args.audit_root, "cadp_001407_clean")
    report = dict(sequence="001407", frames_directory=args.frames_dir.as_posix(),
                  annotation_path=args.annotations.as_posix(), annotation_sha256=sha256_file(args.annotations),
                  source_timing_verified=False, presentation_fps=args.presentation_fps,
                  fps_status="presentation_only_original_timing_unverified",
                  user_onset_end_review="pending", visual_check_confirmed=args.visual_check_confirmed,
                  audit_directory=audit.as_posix(), clean_video=None, author_preview=None,
                  B0_training_ready=False)
    try:
        if args.archive:
            report["archive_inspection"] = stage_archive(args.archive, args.frames_dir, "001407")
        else:
            report["archive_inspection"] = dict(status="using_existing_directory")
        images, inventory, (width, height) = inspect_frames(args.frames_dir)
        report["image_info"] = dict(count=len(images), width_px=width, height_px=height,
                                    first_frame=min(images), last_frame=max(images), missing=[], corrupt=[],
                                    size_bytes=sum(r["size_bytes"] for r in inventory))
        save_csv(audit / "images.csv", inventory, list(inventory[0]))
        rows = read_vatic(args.annotations)
        if set(images) != {r["frame"] for r in rows}:
            raise ValueError("Image numbers and annotation frame numbers differ; no offset guessed")
        for row in rows:
            x1, y1, x2, y2 = row["bbox"]
            if not (0 <= x1 < x2 < width and 0 <= y1 < y2 < height):
                raise ValueError("Native annotation coordinates do not fit clean images")
        config = json.loads(args.demo_config.read_text(encoding="utf-8"))
        demo_info = probe_video(args.demo)
        verify_alignment(config, args.demo, args.annotations, args.reference_zip, demo_info, rows)
        if [width, height] != config["annotation_canvas"] or len(images) != demo_info["decoded_frames"]:
            raise ValueError("Clean sequence differs from verified demo canvas/count")
        checks, passed = compare_reference(images, rows, args.demo, config, audit, args.presentation_fps)
        save_csv(audit / "mapping_checks.csv", checks, list(checks[0]))
        report["mapping_checks"] = checks
        report["mapping_technical_checks_passed"] = passed
        report["mapping_verified"] = passed and args.visual_check_confirmed
        report["cleanliness"] = "no_annotation_boxes_ids_or_plot_border_in_9_inspected_frames;source_watermark_retained" if args.visual_check_confirmed else "visual_review_pending"
        objects, collisions = summarize(rows)
        save_csv(audit / "objects.csv", objects, list(objects[0]))
        save_csv(audit / "colliding_intervals.csv", collisions, ["track_id", "label", "start_frame", "end_frame", "frame_count", "annotation_source", "user_review_status"])
        normalized = []
        by_frame = defaultdict(list)
        for row in rows:
            x1, y1, x2, y2 = row["bbox"]
            normalized.append(dict(source_frame=row["frame"], source_image=images[row["frame"]].as_posix(),
                                   gt_id=row["track_id"], xmin=x1, ymin=y1, xmax=x2, ymax=y2,
                                   object_type=row["label"], outside=row["outside"], visible=int(not row["outside"]),
                                   occluded=row["occluded"], generated=row["generated"],
                                   colliding=int("Colliding" in row["attributes"]), attributes=json.dumps(row["attributes"]),
                                   cx_norm=(x1+x2)/(2*width), cy_norm=(y1+y2)/(2*height),
                                   w_norm=(x2-x1)/width, h_norm=(y2-y1)/height))
            by_frame[row["frame"]].append(row)
        save_csv(audit / "author_annotations.csv", normalized, list(normalized[0]))
        report["author_colliding_intervals"] = collisions
        report["author_annotation_rows"] = len(normalized)
        report["annotation_table"] = (audit / "author_annotations.csv").as_posix()
        if args.visual_check_confirmed:
            if not passed:
                raise ValueError("Mapping checks failed; no videos/model input created")
            # Video sạch không thêm chữ/viền/bbox. Banner chỉ nằm trong preview
            # annotation riêng; model phải đọc clean_video, không đọc author_preview.
            clean_path = unique_path(args.video_root / f"cadp_001407_clean_display{args.presentation_fps:g}fps.mp4")
            preview_path = unique_path(args.preview_root / f"cadp_001407_clean_author_display{args.presentation_fps:g}fps.mp4")
            with H264Writer(clean_path, width, height, args.presentation_fps) as clean_writer:
                for number, path in sorted(images.items()):
                    clean_writer.write(read_image(path))
            with H264Writer(preview_path, width, height, args.presentation_fps) as annotation_writer:
                for number, path in sorted(images.items()):
                    annotation_writer.write(draw_annotations(read_image(path), by_frame[number], number, args.presentation_fps))
            clean_info, preview_info = probe_video(clean_path), probe_video(preview_path)
            if any(info["decoded_frames"] != len(images) for info in (clean_info, preview_info)):
                raise ValueError("Output lost frames")
            report.update(clean_video=clean_path.as_posix(), author_preview=preview_path.as_posix(),
                          clean_video_info=clean_info, author_preview_info=preview_info)
    except Exception as exc:
        report["error"] = str(exc)
        save_json(audit / "report.json", report)
        raise
    save_json(audit / "report.json", report)
    print(json.dumps({key: report[key] for key in ("audit_directory", "mapping_verified", "clean_video", "author_preview")}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
