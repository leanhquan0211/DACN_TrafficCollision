"""Áp xác nhận CADP theo frame, giữ nhãn tác giả và timing nguồn chưa biết.

Đầu vào: phiếu rà có hash TXT, manifest và VATIC gốc. Đầu ra: manifest cập
nhật riêng chuỗi đã rà, kèm backup/audit. Chạy khi có xác nhận mới; không
đổi FPS, suy thời gian giây, tạo split hoặc đổi nhãn chuỗi khác.
"""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.prepare_cadp_pilot import read_vatic
from scripts.update_manifest_reviews import read_manifest, append_note, verify_file
from src.data_preparation import new_audit_dir, save_csv, save_json, unique_path


def apply_review(rows: list[dict], review: dict, review_path: Path) -> list[str]:
    """Đối chiếu toàn khoảng và GT ID trước khi gắn lớp người dùng đã rà."""
    if review["review_status"] != "vehicles_and_colliding_frames_confirmed" or review["source_fps_verified"]:
        raise ValueError("Expected a source-frame review with unresolved source FPS")
    verify_file(review["annotation_path"],review["annotation_sha256"])
    original = read_vatic(Path(review["annotation_path"]))
    for event in review["events"]:
        expected = set(range(event["start_frame"],event["end_frame_inclusive"]+1))
        for gt_id in event["participant_gt_ids"]:
            actual = {r["frame"] for r in original if r["track_id"]==gt_id and "Colliding" in r["attributes"]}
            if actual != expected:
                raise ValueError("Reviewed interval differs from original Colliding rows; no author annotation changed")
    targets = [r for r in rows if r["source_dataset"]=="CADP" and r["source_sequence"]==review["sequence"]]
    if not targets:
        raise ValueError("No manifest assets belong to reviewed sequence")
    for row in targets:
        if row["annotation_path"] != review["annotation_path"] or row["annotation_origin"] != "author_vatic":
            raise ValueError("Manifest annotation source differs from reviewed TXT")
        if row["onset_s"] or row["end_s"]:
            raise ValueError("Existing second-based labels need separate review; not overwritten")
        row.update(collision_label="positive", certainty="user_confirmed_source_frames",
                   involved_gt_ids=";".join(map(str,sorted({i for e in review['events'] for i in e['participant_gt_ids']}))),
                   event_type="vehicle_vehicle", annotation_status="author_objects_and_colliding_frames_user_reviewed",
                   user_review_status=review["review_status"])
        if len(review["events"])==1:
            row["source_event_id"]=review["events"][0]["event_id"]
        ranges = ";".join(f"{e['start_frame']}-{e['end_frame_inclusive']}" for e in review["events"])
        append_note(row, f"Superseding frame review: {review_path.as_posix()}; source frames {ranges} inclusive confirmed, source FPS unknown, no seconds inferred. Earlier pending notes are historical.")
    return [r["video_id"] for r in targets]


def main() -> int:
    parser=argparse.ArgumentParser(description="Apply reviewed CADP object identities and frame intervals without inventing source timing")
    parser.add_argument("--manifest",type=Path,default=Path("data/manifest.csv"))
    parser.add_argument("--review",type=Path,required=True)
    args=parser.parse_args()
    fields,rows=read_manifest(args.manifest)
    before=deepcopy(rows)
    review=json.loads(args.review.read_text(encoding="utf-8"))
    targets=apply_review(rows,review,args.review)
    # So sánh tất cả chuỗi ngoài scope, không chỉ ba clip mẫu cũ.
    assert all(old==new for old,new in zip(before,rows) if old["video_id"] not in targets)
    audit=new_audit_dir(Path("outputs/audits"),"cadp_frame_review")
    (audit/"manifest_before.csv").write_bytes(args.manifest.read_bytes())
    temporary=unique_path(args.manifest.with_suffix(".part.csv"))
    save_csv(temporary,rows,fields)
    temporary.replace(args.manifest)
    save_json(audit/"report.json",dict(updated=targets,review=args.review.as_posix(),schema_unchanged=True,
              other_rows_unchanged=True,source_fps_inferred=False,seconds_inferred=False))
    print(f"REVIEW_OK {len(targets)} CADP assets; backup: {audit.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
