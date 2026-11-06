"""Đưa media đã kiểm tra từ audit CADP/DETRAC vào manifest hiện có.

Đầu vào: hai report.json và CSV manifest. Đầu ra: CSV thêm asset/provenance,
kèm bản sao manifest trước sửa trong outputs/data_audits. Giữ nhãn dự án unknown,
user review pending và split unassigned; không lấy Colliding làm nhãn tự duyệt.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.data_preparation import new_audit_dir, save_csv, save_json, sha256_file, unique_path
from src.storage_paths import storage_root


EXTRA_FIELDS = ["asset_role", "source_sequence", "derived_from", "source_archive",
                "source_frame_range", "annotation_path", "annotation_origin",
                "author_colliding_frames", "user_review_status", "fps_status",
                "fps_source", "verification_status", "notes"]


def relative(path: str) -> str:
    return Path(path).as_posix()


def candidates(cadp: dict, detrac: dict) -> list[dict]:
    if "error" in cadp or "error" in detrac:
        raise ValueError("Do not register failed preparation reports")
    results = []

    def add(video_id, path, info, **values):
        if not Path(path).is_file():
            raise FileNotFoundError(path)
        if Path(path).stat().st_size != info["size_bytes"] or sha256_file(Path(path)) != info["sha256"]:
            raise ValueError(f"Video changed since preparation report: {path}")
        results.append(dict(video_id=video_id, relative_path=relative(path), **info,
                            collision_label="unknown", split="unassigned", user_review_status="pending",
                            **values))

    cadp_sequence = Path(cadp["video"]).stem
    colliding = ";".join(f"ID{item['track_id']} {item['label']}:{item['start_frame']}-{item['end_frame']}"
                         for item in cadp["colliding_intervals"])
    cadp_shared = dict(source_dataset="CADP", source_sequence=cadp_sequence,
                       source_url="https://ankitshah009.github.io/accident_forecasting_traffic_camera.html",
                       source_archive=cadp.get("reference_archive", "data_raw/cadp/reference_code/CarCrash_forecasting_and_detection-master.zip"),
                       source_frame_range=f"0-{cadp['video_info']['decoded_frames']-1}", annotation_path=relative(cadp["annotations"]),
                       annotation_origin="author_vatic", author_colliding_frames=colliding,
                       annotation_status="author_available_user_review_pending",
                       fps_status="rendered_preview_original_timing_unverified",
                       fps_source="author makevideo_1407.sh + local MP4 metadata",
                       verification_status=cadp["alignment_status"])
    add("CADP_" + cadp_sequence, cadp["video"], cadp["video_info"], **cadp_shared,
        asset_role="rendered_author_demo", derived_from="",
        notes="Already contains author boxes/IDs and white margins; not clean training input; original capture timing unverified.")
    if cadp.get("preview"):
        add("CADP_" + cadp_sequence + "_author_preview", cadp["preview"], cadp["preview_info"], **cadp_shared,
            asset_role="annotation_preview", derived_from=relative(cadp["video"]),
            notes="Author annotation overlay, not model output; red=Colliding, green=other visible GT, gray=FarRegion.")
    for sequence in detrac["sequences"]:
        labels = sequence["author_vehicle_annotations"]
        annotation_path = ";".join(relative(a["archive"]) + "!" + a["member"] for a in labels)
        camera_states = "|".join(sorted({a.get("sequence_attributes", {}).get("camera_state", "unknown") for a in labels}))
        verification = "images_decoded_all" + (";zip_crc_checked" if "archive_inventory" in detrac else "") + (";xml_frame_range_checked" if labels else "")
        add("UA_DETRAC_" + sequence["sequence"], sequence["output"], sequence["video_info"],
            source_dataset="UA-DETRAC", source_sequence=sequence["sequence"],
            source_url="https://sites.google.com/view/daweidu/projects/ua-detrac",
            source_archive=relative(detrac["archive"]), asset_role="sequence_video",
            derived_from=relative(sequence["image_directory"]),
            source_frame_range=f"{sequence['first_image_number']}-{sequence['last_image_number']}",
            annotation_path=annotation_path, annotation_origin="author_vehicle_xml" if labels else "",
            annotation_status="author_vehicle_labels_user_review_pending" if labels else "not_reviewed",
            fps_status=detrac["fps_status"], fps_source=detrac["fps_source"],
            verification_status=verification,
            notes=f"No accident label inferred. XML camera_state={camera_states or 'not_available'}; bbox alignment not manually reviewed.")
    clip = detrac["smoke_clip"]
    parent = next(row for row in results if row["source_sequence"] == clip["source_sequence"] and row["asset_role"] == "sequence_video")
    shared = {key: parent.get(key, "") for key in ("source_dataset", "source_sequence", "source_url", "source_archive", "annotation_path", "annotation_origin", "annotation_status", "fps_status", "fps_source")}
    add("UA_DETRAC_" + Path(clip["output"]).stem, clip["output"], clip["video_info"], **shared,
        asset_role="short_clip", derived_from=relative(clip["parent_video"]),
        source_frame_range=f"{clip['source_start_frame']}-{clip['source_end_frame']}",
        verification_status="generated_clip_decoded_all",
        notes="Clip frame 0 maps to source image 1. Use for vehicle detection/tracking smoke test only.")
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Register audited CADP/DETRAC videos without assigning accident labels or splits")
    parser.add_argument("--manifest", type=Path, default=Path("data/manifest.csv"))
    parser.add_argument("--cadp-report", type=Path, required=True)
    parser.add_argument("--detrac-report", type=Path, required=True)
    parser.add_argument("--audit-root", type=Path, default=storage_root(ROOT,'data_audit'))
    args = parser.parse_args()
    with args.manifest.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, skipinitialspace=True)
        fields = [name.strip() for name in reader.fieldnames]
        if len(set(fields)) != len(fields):
            raise ValueError("Duplicate manifest columns")
        rows = []
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError("Malformed manifest CSV")
            rows.append({key.strip(): value.strip() for key, value in row.items()})
    if len({row["video_id"] for row in rows}) != len(rows):
        raise ValueError("Duplicate video_id in existing manifest")
    fields += [name for name in EXTRA_FIELDS if name not in fields]
    registered = []
    for candidate in candidates(json.loads(args.cadp_report.read_text(encoding="utf-8")), json.loads(args.detrac_report.read_text(encoding="utf-8"))):
        if any(row["video_id"] == candidate["video_id"] for row in rows):
            # Không ghi đè nhãn/ghi chú đã có; nếu muốn đăng ký lại phải rà thủ công.
            raise ValueError(f"Already registered; existing row preserved: {candidate['video_id']}")
        row = {name: str(candidate.get(name, "")) for name in fields}
        rows.append(row)
        registered.append(row["video_id"])
    audit = new_audit_dir(args.audit_root, 'v019_manifest_registration' if args.audit_root.resolve()==storage_root(ROOT,'data_audit') else 'manifest_registration')
    with (audit / "manifest_before.csv").open("xb") as backup:
        backup.write(args.manifest.read_bytes())
    temporary = unique_path(args.manifest.with_suffix(".part.csv"))
    save_csv(temporary, rows, fields)
    temporary.replace(args.manifest)
    save_json(audit / "report.json", dict(registered=registered, row_count=len(rows),
              added_fields=EXTRA_FIELDS, cadp_report=str(args.cadp_report), detrac_report=str(args.detrac_report)))
    print(f"MANIFEST_OK {args.manifest}: {len(rows)} rows; backup {audit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
