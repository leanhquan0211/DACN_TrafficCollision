"""Ghi xác nhận có phạm vi của người dùng và đăng ký chuỗi CADP sạch đã kiểm tra.

Đầu vào: manifest, phiếu rà người dùng và báo cáo prepare_cadp_frames.
Đầu ra: manifest giữ schema, bản sao trước sửa và nhật ký thay đổi. Chạy sau
khi kiểm tra ảnh/mapping; không duyệt onset/end hay tạo nhãn accident từ bbox xe.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.data_preparation import new_audit_dir, save_csv, save_json, sha256_file, unique_path


def read_manifest(path: Path) -> tuple[list[str], list[dict]]:
    """Chấp nhận CSV được căn khoảng trắng, kể cả trường ghi chú có dấu phẩy."""
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, skipinitialspace=True)
        fields = [key.strip() for key in reader.fieldnames]
        rows = []
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError("Malformed manifest CSV")
            rows.append({key.strip(): value.strip() for key, value in row.items()})
    if len(fields) != len(set(fields)) or len(rows) != len({r["video_id"] for r in rows}):
        raise ValueError("Duplicate columns/video IDs")
    return fields, rows


def verify_file(path: str, expected_hash: str) -> None:
    if not expected_hash or sha256_file(Path(path)) != expected_hash:
        raise ValueError(f"Asset changed or hash missing: {path}")


def append_note(row: dict, note: str) -> None:
    if note not in row["notes"]:
        row["notes"] = (row["notes"] + " " + note).strip()


def update(rows: list[dict], fields: list[str], report: dict, review: dict,
           review_path: Path, report_path: Path, detrac: dict) -> tuple[list[dict], list[str]]:
    """Chỉ cập nhật asset có bằng chứng đúng hash; ảnh sạch dùng hash từng JPG."""
    if ("error" in report or not report["mapping_verified"] or report["source_timing_verified"]
            or report["presentation_fps"] != 20):
        raise ValueError("Expected verified mapping with explicitly unresolved source timing")
    by_id = {row["video_id"]: row for row in rows}
    review_note = f"User review: {review_path.as_posix()}."
    negatives = set()
    cadp_identity_confirmed = False
    for statement in review["statements"]:
        row = by_id[statement["video_id"]]
        verify_file(row["relative_path"], statement["sha256"])
        if row["sha256"] != statement["sha256"]:
            raise ValueError("Manifest differs from reviewed asset")
        if statement["scope"] == "full_sequence" and statement.get("collision_label") == "negative":
            if row["source_dataset"] != "UA-DETRAC" or row["asset_role"] != "sequence_video":
                raise ValueError("Review scope is not a full DETRAC sequence")
            negatives.add(row["video_id"])
            row.update(collision_label="negative", certainty="user_confirmed",
                       user_review_status="reviewed_full_sequence_no_collision",
                       annotation_status="author_vehicle_labels_user_collision_reviewed")
            for key in ("onset_s", "end_s", "involved_gt_ids"):
                row[key] = ""
            append_note(row, review_note)
        elif statement["scope"] == "red_boxes_vehicle_identity_only":
            if row["video_id"] != "CADP_1407_author_preview" or statement.get("onset_end_review") != "pending":
                raise ValueError("Unexpected CADP review target/scope")
            verify_file(report["annotation_path"], statement["annotation_sha256"])
            cadp_identity_confirmed = True
        else:
            raise ValueError("Unsupported review scope; no labels guessed")
    if not cadp_identity_confirmed:
        raise ValueError("CADP vehicle-identity review is missing; not inferred from clean mapping")

    # Clip là tập con đã biết của một chuỗi đã xem đầy đủ. Ghi trạng thái kế thừa,
    # không nói người dùng đã mở riêng clip hoặc đánh giá bbox XML.
    clip = by_id["UA_DETRAC_MVI_20011_first_10s"]
    parent = by_id["UA_DETRAC_MVI_20011"]
    provenance = detrac["smoke_clip"]
    verify_file(clip["relative_path"], provenance["video_info"]["sha256"])
    if (parent["video_id"] not in negatives or clip["derived_from"] != parent["relative_path"]
            or Path(provenance["parent_video"]).as_posix() != parent["relative_path"]
            or clip["relative_path"] != Path(provenance["output"]).as_posix()
            or clip["source_frame_range"] != "1-250"
            or parent["source_frame_range"] != "1-664"):
        raise ValueError("Short-clip provenance differs from reviewed parent")
    clip.update(collision_label="negative", certainty="inherited_user_reviewed_parent",
                user_review_status="inherited_from_reviewed_full_sequence",
                annotation_status="author_vehicle_labels_parent_collision_reviewed")
    append_note(clip, review_note + " Negative inherited only for source images 1-250 of reviewed parent 1-664.")

    # 1407 và 001407 được nối sau kiểm tra nội dung/mapping, không chỉ theo tên.
    # Giữ nhãn dự án unknown: xác nhận đúng xe chưa phải xác nhận mốc va chạm.
    for video_id in ("CADP_1407", "CADP_1407_author_preview"):
        row = by_id[video_id]
        row.update(source_sequence="001407", user_review_status="vehicles_confirmed_onset_end_pending",
                   annotation_status="author_vehicle_identity_confirmed_timing_pending")
        append_note(row, review_note + f" Clean sequence mapping: {report_path.as_posix()}.")

    folder = Path(report["frames_directory"])
    audit = Path(report["audit_directory"])
    with (audit / "images.csv").open(encoding="utf-8", newline="") as stream:
        inventory = list(csv.DictReader(stream))
    if len(inventory) != report["image_info"]["count"]:
        raise ValueError("Image inventory count changed")
    for image in inventory:
        verify_file(image["relative_path"], image["sha256"])
    verify_file(report["annotation_path"], report["annotation_sha256"])
    source_archive = report["archive_inspection"]["archive"]
    verify_file(source_archive, report["archive_inspection"]["archive_sha256"])
    common = dict(source_dataset="CADP", source_sequence="001407",
                  source_url=by_id["CADP_1407"]["source_url"], split="unassigned",
                  collision_label="unknown", annotation_status="author_vehicle_identity_confirmed_timing_pending",
                  source_archive=source_archive, source_frame_range="0-220",
                  annotation_path=report["annotation_path"], annotation_origin="author_vatic",
                  author_colliding_frames="ID0 Bus:96-130;ID2 Car:96-130",
                  user_review_status="vehicles_confirmed_onset_end_pending",
                  verification_status="all_images_decoded_crc;native_bbox_bounds;reference_code;9_frame_visual_mapping",
                  notes=f"{review_note} Audit: {report_path.as_posix()}. No accident-region labels; source timing unverified.")
    info = report["image_info"]
    entries = [dict(common, video_id="CADP_001407_clean_frames", relative_path=folder.as_posix(),
                    asset_role="clean_image_sequence", size_bytes=info["size_bytes"],
                    width_px=info["width_px"], height_px=info["height_px"], frame_count=info["count"],
                    decoded_frames=info["count"], derived_from=source_archive,
                    fps_status="original_timing_unverified", fps_source="",
                    notes=common["notes"] + f" Directory SHA left blank; per-image hashes: {audit.as_posix()}/images.csv.")]
    for role, key, video_id in (("clean_video", "clean_video", "CADP_001407_clean_display20fps"),
                                ("annotation_preview", "author_preview", "CADP_001407_clean_author_display20fps")):
        metadata = report[key + "_info"]
        verify_file(report[key], metadata["sha256"])
        entries.append(dict(common, **metadata, video_id=video_id, relative_path=report[key],
                            asset_role=role, derived_from=folder.as_posix(), fps_status=report["fps_status"],
                            fps_source="operator-selected 20 FPS for display only; not capture FPS"))
    added = []
    for entry in entries:
        candidate = {key: str(entry.get(key, "")) for key in fields}
        if entry["video_id"] in by_id:
            # Có thể chạy lại cùng audit: chỉ tái dùng dòng giống hệt, không tạo trùng.
            if by_id[entry["video_id"]] != candidate:
                raise ValueError(f"Existing registration differs; preserved: {entry['video_id']}")
            continue
        rows.append(candidate)
        added.append(entry["video_id"])
    return rows, added


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply scoped user reviews and register verified clean CADP assets")
    parser.add_argument("--manifest", type=Path, default=Path("data/manifest.csv"))
    parser.add_argument("--cadp-report", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--detrac-report", type=Path, default=Path("outputs/audits/detrac_preparation/report.json"))
    parser.add_argument("--audit-root", type=Path, default=Path("outputs/audits"))
    args = parser.parse_args()
    fields, rows = read_manifest(args.manifest)
    before = deepcopy(rows)
    rows, added = update(rows, fields, json.loads(args.cadp_report.read_text(encoding="utf-8")),
                         json.loads(args.review.read_text(encoding="utf-8")), args.review, args.cadp_report,
                         json.loads(args.detrac_report.read_text(encoding="utf-8")))
    untouched = ["YSGhwU9XxuY", "ZCQcKnFSJvg", "zVzXEht1aME"]
    if any(next(r for r in before if r["video_id"] == key) != next(r for r in rows if r["video_id"] == key) for key in untouched):
        raise ValueError("Unreviewed old sample changed")
    # Kiểm tra xong mới ghi backup nguyên byte và thay CSV bằng file tạm hoàn chỉnh.
    audit = new_audit_dir(args.audit_root, "cadp_clean_manifest_update")
    (audit / "manifest_before.csv").write_bytes(args.manifest.read_bytes())
    temporary = unique_path(args.manifest.with_suffix(".part.csv"))
    save_csv(temporary, rows, fields)
    temporary.replace(args.manifest)
    save_json(audit / "report.json", dict(row_count=len(rows), schema_unchanged=True, added=added,
              old_samples_unchanged=untouched, review=args.review.as_posix(), cadp_report=args.cadp_report.as_posix()))
    print(f"MANIFEST_OK {len(rows)} rows; backup: {audit.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
