"""Chuẩn hóa VATIC và tạo nhãn ứng viên vùng sự kiện, chưa phải GT B0 đã duyệt.

Đầu vào: ảnh sạch, TXT gốc, báo cáo mapping và (nếu có) xác nhận theo frame.
Đầu ra: bảng đối tượng/frame/vùng bỏ qua, bbox đề xuất và TXT YOLO minh họa
ở thư mục labels_proposed. Chạy khi chuẩn bị chuỗi mới; không tạo split/train,
không tạo nhãn âm rỗng cho frame thiếu nhãn hoặc ngoài khoảng đã được rà.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.prepare_cadp_pilot import read_vatic
from scripts.prepare_cadp_frames import inspect_frames
from scripts.prepare_detrac import read_image
from src.data_preparation import save_csv, save_json, sha256_file


REGIONS = {"FarRegion", "CrowdRegion"}
NON_OBJECTS = REGIONS | {"Separator"}


def normalize(rows: list[dict], images: dict[int, Path], width: int, height: int, sequence: str) -> list[dict]:
    """Giữ mọi dòng nguồn, kể cả outside/region; không điền bbox còn thiếu."""
    records = []
    for row in rows:
        frame = row["frame"]
        if frame not in images:
            raise ValueError(f"Annotation refers to missing source frame {frame}")
        x1, y1, x2, y2 = row["bbox"]
        if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
            raise ValueError(f"Out-of-bounds bbox: ID {row['track_id']} frame {frame}; no silent clipping")
        role = "ignore_region" if row["label"] in REGIONS else ("scene_separator" if row["label"] == "Separator" else "object")
        records.append(dict(sequence=sequence, source_frame=frame, source_image=images[frame].as_posix(),
                            gt_id=row["track_id"], object_type=row["label"], annotation_role=role,
                            xmin=x1, ymin=y1, xmax=x2, ymax=y2, image_width=width, image_height=height,
                            visible=int(not row["outside"]), outside=row["outside"], occluded=row["occluded"],
                            generated=row["generated"], colliding=int("Colliding" in row["attributes"]),
                            attributes=json.dumps(row["attributes"]),
                            cx_norm=(x1+x2)/(2*width), cy_norm=(y1+y2)/(2*height),
                            w_norm=(x2-x1)/width, h_norm=(y2-y1)/height,
                            annotation_origin="author_vatic", region_gt_approved=False))
    return records


def build_candidates(rows: list[dict], images: dict[int, Path], events: list[dict],
                     sequence: str, width: int, height: int, rule: dict) -> tuple[list[dict], list[dict]]:
    """Một bbox đề xuất bao các xe thuộc cùng event đã rà; không gộp mọi Colliding.

    Bbox đại diện vùng chứa các phương tiện tham gia, không phải điểm tiếp xúc,
    vùng hư hỏng hay nhãn nguồn. Chỉ xuất khi mọi participant có dòng nhìn thấy.
    """
    by_frame = defaultdict(dict)
    for row in rows:
        by_frame[row["frame"]][row["track_id"]] = row
    candidates, frame_records = [], []
    known_ids = {r["track_id"] for r in rows}
    event_ids = set()
    for event in events:
        ids = event["participant_gt_ids"]
        start, end = event["start_frame"], event["end_frame_inclusive"]
        if (event["event_id"] in event_ids or len(set(ids)) < 2 or len(set(ids)) != len(ids)
                or start > end or not set(range(start, end+1)) <= set(images)):
            raise ValueError("Invalid/duplicate reviewed event or source interval")
        event_ids.add(event["event_id"])
    for frame, image in sorted(images.items()):
        objects = list(by_frame[frame].values())
        frame_events = [e for e in events if e["start_frame"] <= frame <= e["end_frame_inclusive"]]
        reasons = []
        frame_candidates = []
        for event in frame_events:
            participants = [by_frame[frame].get(gt_id) for gt_id in event["participant_gt_ids"]]
            if any(r is None or r["outside"] or r["label"] in NON_OBJECTS for r in participants):
                reasons.append(event["event_id"] + ":missing_or_outside_participant")
                continue
            if not all("Colliding" in r["attributes"] for r in participants):
                raise ValueError(f"Reviewed interval contradicts author attributes at frame {frame}")
            boxes = [r["bbox"] for r in participants]
            x1, y1 = min(b[0] for b in boxes), min(b[1] for b in boxes)
            x2, y2 = max(b[2] for b in boxes), max(b[3] for b in boxes)
            ignored = [r for r in objects if r["label"] in REGIONS and not r["outside"]]
            overlap = any(min(x2,r["bbox"][2]) > max(x1,r["bbox"][0]) and
                          min(y2,r["bbox"][3]) > max(y1,r["bbox"][1]) for r in ignored)
            candidate = dict(sequence=sequence, event_id=event["event_id"], source_frame=frame,
                             source_image=image.as_posix(), participant_gt_ids=json.dumps(event["participant_gt_ids"]),
                             xmin=x1, ymin=y1, xmax=x2, ymax=y2,
                             cx_norm=(x1+x2)/(2*width), cy_norm=(y1+y2)/(2*height),
                             w_norm=(x2-x1)/width, h_norm=(y2-y1)/height,
                             class_id=rule["class_id"], rule_id=rule["rule_id"],
                             label_origin="derived_proposal_not_author_annotation",
                             approval_status="pending_region_rule_and_region_review",
                             any_occluded=int(any(r["occluded"] for r in participants)),
                             any_generated=int(any(r["generated"] for r in participants)),
                             overlaps_ignore_region=int(overlap), training_eligible=False)
            candidates.append(candidate)
            frame_candidates.append(candidate)
        # Có dòng cho đủ ID vẫn chưa chứng minh mọi vùng trong ảnh đã được gán nhãn.
        # Frame ngoài interval và frame thiếu annotation đều không thành negative.
        frame_records.append(dict(sequence=sequence, source_frame=frame, source_image=image.as_posix(),
                                  annotation_rows=len(objects), visible_objects=sum(not r["outside"] and r["label"] not in NON_OBJECTS for r in objects),
                                  missing_known_track_rows=json.dumps(sorted(known_ids-set(by_frame[frame]))),
                                  visible_ignore_regions=sum(not r["outside"] and r["label"] in REGIONS for r in objects),
                                  reviewed_event_ids=json.dumps([e["event_id"] for e in frame_events]),
                                  proposal_count=len(frame_candidates), skip_reasons=";".join(reasons),
                                  frame_label_status="reviewed_event_candidate_pending_region_rule" if frame_candidates else "unknown_not_certified_negative",
                                  empty_negative_exported=False, training_eligible=False))
    return candidates, frame_records


def illustrations(images: dict[int, Path], rows: list[dict], candidates: list[dict], target: Path) -> None:
    """Lưu vài ảnh giải thích bbox đề xuất và vùng bỏ qua, không tạo thêm MP4."""
    import cv2
    by_frame = defaultdict(list)
    for row in rows:
        by_frame[row["frame"]].append(row)
    selected = sorted({c["source_frame"] for c in candidates})
    if not selected:
        return
    sample = sorted({selected[0], selected[len(selected)//2], selected[-1]})
    panels = []
    for frame in sample:
        picture = read_image(images[frame]).copy()
        for row in by_frame[frame]:
            if row["outside"]:
                continue
            if row["label"] in REGIONS or "Colliding" in row["attributes"]:
                cv2.rectangle(picture, tuple(row["bbox"][:2]), tuple(row["bbox"][2:]), (140,140,140), 1)
        for item in candidates:
            if item["source_frame"] == frame:
                cv2.rectangle(picture,(item["xmin"],item["ymin"]),(item["xmax"],item["ymax"]),(0,180,255),3)
        cv2.rectangle(picture,(0,0),(picture.shape[1]-1,70),(0,0,0),-1)
        cv2.putText(picture,"PROPOSAL ONLY: participant envelope / NOT approved accident GT",(8,25),cv2.FONT_HERSHEY_SIMPLEX,.6,(0,180,255),1)
        cv2.putText(picture,f"Source frame {frame} | gray: source boxes/ignore regions | no source timing inferred",(8,53),cv2.FONT_HERSHEY_SIMPLEX,.55,(255,255,255),1)
        cv2.imwrite(str(target/f"proposal_{frame:06d}.jpg"),picture)
        panels.append(cv2.resize(picture,(768,432)))
    cv2.imwrite(str(target/"proposal_examples.jpg"),cv2.vconcat(panels))


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize VATIC and export derived B0 region proposals, never approved training GT")
    parser.add_argument("--sequence", required=True)
    parser.add_argument("--frames-dir", type=Path, required=True)
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--mapping-report", type=Path, required=True)
    parser.add_argument("--review", type=Path)
    parser.add_argument("--rule", type=Path, default=Path("configs/b0_region_proposal.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.sequence.isdecimal() or len(args.sequence) != 6:
        parser.error("Use original six-digit CADP sequence ID")
    mapping = json.loads(args.mapping_report.read_text(encoding="utf-8"))
    rule = json.loads(args.rule.read_text(encoding="utf-8"))
    if (not mapping.get("mapping_verified") or mapping.get("sequence") != args.sequence
            or Path(mapping["frames_directory"]).resolve() != args.frames_dir.resolve()
            or mapping["annotation_sha256"] != sha256_file(args.annotations)):
        raise ValueError("Clean mapping report does not match this sequence/annotation")
    if (rule["status"] != "proposal_not_approved_ground_truth" or rule["training_export_allowed"]
            or rule["rule_id"] != "participant_envelope_v1_proposal" or rule["padding_px"] != 0):
        raise ValueError("This tool exports proposals only, not approved training labels")
    images, inventory, (width, height) = inspect_frames(args.frames_dir)
    # Đối chiếu từng hash với lần xác minh sạch; cùng tên file không đủ chứng minh.
    import csv
    with (Path(mapping["audit_directory"])/"images.csv").open(encoding="utf-8",newline="") as stream:
        verified = {int(r["source_frame"]): r["sha256"] for r in csv.DictReader(stream)}
    if {r["source_frame"]:r["sha256"] for r in inventory} != verified:
        raise ValueError("Images differ from verified clean inventory")
    rows = read_vatic(args.annotations)
    normalized = normalize(rows, images, width, height, args.sequence)
    events = []
    if args.review:
        review = json.loads(args.review.read_text(encoding="utf-8"))
        if (review["sequence"] != args.sequence or review["annotation_sha256"] != sha256_file(args.annotations)
                or review["review_status"] != "vehicles_and_colliding_frames_confirmed" or review["frame_index_base"] != 0):
            raise ValueError("Review is not a matching frame-based confirmation")
        events = review["events"]
    candidates, frames = build_candidates(rows, images, events, args.sequence, width, height, rule)
    # Output mới hoàn toàn: không sao chép ảnh, không tạo dataset.yaml/split và
    # không đặt candidate cạnh nhãn GT để công cụ train tự động lấy nhầm.
    args.output.mkdir(parents=True, exist_ok=False)
    save_csv(args.output/"objects_normalized.csv",normalized,list(normalized[0]))
    save_csv(args.output/"frames.csv",frames,list(frames[0]))
    ignores = [r for r in normalized if r["annotation_role"] != "object"]
    save_csv(args.output/"ignore_and_separator_regions.csv",ignores,list(normalized[0]))
    fields = list(candidates[0]) if candidates else ["sequence","source_frame","approval_status"]
    save_csv(args.output/"region_proposals.csv",candidates,fields)
    save_csv(args.output/"images.csv",inventory,list(inventory[0]))
    labels = args.output/"labels_proposed"
    labels.mkdir()
    grouped = defaultdict(list)
    for candidate in candidates:
        grouped[candidate["source_frame"]].append(candidate)
    for frame, objects in grouped.items():
        with (labels/f"{args.sequence}_{frame:06d}.txt").open("x",encoding="utf-8") as stream:
            for item in objects:
                stream.write(f"{item['class_id']} {item['cx_norm']:.8f} {item['cy_norm']:.8f} {item['w_norm']:.8f} {item['h_norm']:.8f}\n")
    illustrations(images,rows,candidates,args.output)
    report = dict(sequence=args.sequence,annotation_origin="author_vatic",annotation_path=args.annotations.as_posix(),
                  annotation_sha256=sha256_file(args.annotations),mapping_report=args.mapping_report.as_posix(),
                  review_path=args.review.as_posix() if args.review else None,
                  rule_path=args.rule.as_posix(),rule_sha256=sha256_file(args.rule),rule_status=rule["status"],
                  frames=len(images),width=width,height=height,annotation_rows=len(rows),
                  object_classes=dict(Counter(r["label"] for r in rows)),
                  visible_rows=sum(not r["outside"] for r in rows),occluded_rows=sum(r["occluded"] for r in rows),
                  generated_rows=sum(r["generated"] for r in rows),author_colliding_rows=sum("Colliding" in r["attributes"] for r in rows),
                  reviewed_events=events,proposal_boxes=len(candidates),proposal_frames=len(grouped),
                  ignore_rows=len(ignores),unknown_non_candidate_frames=len(images)-len(grouped),
                  empty_negative_labels_created=0,source_fps_verified=mapping.get("source_timing_verified",False),time_seconds_exported=False,
                  training_eligible=False,split_created=False,images_copied=0,
                  missing_annotation_is_not_negative=True)
    save_json(args.output/"report.json",report)
    print(json.dumps(report,ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
