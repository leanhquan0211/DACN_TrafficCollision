"""Đọc nhãn VATIC CADP, xuất bảng đối tượng và video xem lại annotation tác giả.

Đầu vào: cặp MP4/TXT và cấu hình căn chỉnh đã kiểm chứng. Đầu ra: CSV/JSON
trong outputs/audits và MP4 trong outputs/annotation_preview. Chạy khi có cặp
mẫu cần đối chiếu; không suy luận model, không biến Colliding thành nhãn do người dùng duyệt.
"""

from __future__ import annotations

import argparse
import json
import shlex
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.data_preparation import H264Writer, new_audit_dir, probe_video, save_csv, save_json, sha256_file, unique_path


def read_vatic(path: Path) -> list[dict]:
    """Tách token có dấu ngoặc kép, giữ đủ cờ ngoài ảnh/che khuất và thuộc tính.

    Thứ tự theo read_vatic của tác giả: ID x1 y1 x2 y2 frame outside
    occluded generated label [attributes...]. Tọa độ ở đây là xyxy, không phải xywh.
    """
    rows, seen, labels = [], set(), {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        tokens = shlex.split(line)
        if len(tokens) < 10:
            raise ValueError(f"VATIC line {line_number}: expected at least 10 columns")
        values = list(map(int, tokens[:9]))
        track_id, x1, y1, x2, y2, frame, outside, occluded, generated = values
        key = (track_id, frame)
        if key in seen or min(track_id, frame) < 0 or x2 <= x1 or y2 <= y1:
            raise ValueError(f"Invalid or duplicate VATIC row at line {line_number}")
        if any(flag not in (0, 1) for flag in (outside, occluded, generated)):
            raise ValueError(f"Invalid flags at line {line_number}")
        label = tokens[9]
        if track_id in labels and labels[track_id] != label:
            raise ValueError(f"Class changed for ID {track_id}")
        labels[track_id] = label
        seen.add(key)
        rows.append(dict(track_id=track_id, frame=frame, bbox=[x1, y1, x2, y2],
                         outside=outside, occluded=occluded, generated=generated,
                         label=label, attributes=tokens[10:]))
    if not rows:
        raise ValueError("Empty VATIC annotation")
    return rows


def frame_intervals(frames: list[int]) -> list[list[int]]:
    """Nén các frame liên tiếp thành khoảng [đầu, cuối] bao gồm cả hai đầu."""
    result = []
    for value in sorted(set(frames)):
        if result and result[-1][1] + 1 == value:
            result[-1][1] = value
        else:
            result.append([value, value])
    return result


def summarize(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    groups = defaultdict(list)
    for row in rows:
        groups[row["track_id"]].append(row)
    objects, collisions = [], []
    for track_id, track in sorted(groups.items()):
        colliding = [r["frame"] for r in track if "Colliding" in r["attributes"]]
        intervals = frame_intervals(colliding)
        objects.append(dict(track_id=track_id, label=track[0]["label"], rows=len(track),
                            first_frame=min(r["frame"] for r in track), last_frame=max(r["frame"] for r in track),
                            visible_frames=sum(not r["outside"] for r in track),
                            occluded_frames=sum(r["occluded"] for r in track),
                            generated_frames=sum(r["generated"] for r in track),
                            colliding_frames=len(colliding), colliding_intervals=json.dumps(intervals)))
        for start, end in intervals:
            collisions.append(dict(track_id=track_id, label=track[0]["label"],
                                   start_frame=start, end_frame=end, frame_count=end - start + 1,
                                   annotation_source="author_vatic", user_review_status="pending"))
    return objects, collisions


def verify_alignment(config: dict, video: Path, annotations: Path, reference: Path,
                     info: dict, rows: list[dict]) -> None:
    """Chỉ chấp nhận phép biến đổi dành cho đúng mẫu đã xác minh, không tự đoán scale.

    Mẫu 1407 là ảnh Matplotlib đã có nhãn in sẵn; hash và đối chiếu archive tác giả
    ngăn việc dùng nhầm mapping đó cho video sạch hoặc file khác cùng tên.
    """
    if video.stem != annotations.stem:
        raise ValueError("MP4/TXT stems differ; will not guess a pairing")
    if not config.get("source_is_rendered_annotation_demo"):
        raise ValueError("This preview config must describe a verified rendered author sample")
    if sha256_file(video) != config["video_sha256"] or sha256_file(annotations) != config["annotation_sha256"]:
        raise ValueError("Files do not match the verified alignment config")
    if [info["width_px"], info["height_px"]] != config["video_canvas"] or info["decoded_frames"] != config["frame_count"]:
        raise ValueError("Video dimensions/frame count do not match config")
    if config["frame_index_base"] != 0:
        raise ValueError("Only the verified 0-based mapping is supported here")
    frames = sorted({r["frame"] for r in rows})
    if frames != list(range(info["decoded_frames"])):
        raise ValueError("Annotation frame range does not match video")
    canvas_w, canvas_h = config["annotation_canvas"]
    sx, sy, tx, ty = config["bbox_transform"]
    if sx <= 0 or sy <= 0:
        raise ValueError("Invalid mapping scale")
    for row in rows:
        x1, y1, x2, y2 = row["bbox"]
        if not (0 <= x1 < x2 < canvas_w and 0 <= y1 < y2 < canvas_h):
            raise ValueError("BBox outside the verified annotation canvas")
        if not (0 <= sx * x1 + tx < sx * x2 + tx < info["width_px"] and
                0 <= sy * y1 + ty < sy * y2 + ty < info["height_px"]):
            raise ValueError("Transformed bbox outside output image")
    with zipfile.ZipFile(reference) as archive:
        for key, path in (("video", video), ("annotations", annotations)):
            if archive.read(config["reference_members"][key]) != path.read_bytes():
                raise ValueError(f"{key} differs from the author reference archive")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit CADP VATIC and optionally render verified author annotations")
    parser.add_argument("--video", type=Path, default=Path("data_raw/cadp/pilot_1407/1407.mp4"))
    parser.add_argument("--annotations", type=Path, default=Path("data_raw/cadp/pilot_1407/1407.txt"))
    parser.add_argument("--preview-config", type=Path, help="Required for overlay; no automatic coordinate scaling")
    parser.add_argument("--reference-zip", type=Path, default=Path("data_raw/cadp/reference_code/CarCrash_forecasting_and_detection-master.zip"))
    parser.add_argument("--audit-root", type=Path, default=Path("outputs/audits"))
    parser.add_argument("--preview-root", type=Path, default=Path("outputs/annotation_preview"))
    args = parser.parse_args()
    import cv2

    # Bảng nhãn xuất độc lập với preview; thiếu căn cứ khớp video vẫn xem được
    # ID/lớp/khoảng Colliding mà không áp bbox lên sai khung hình.
    rows = read_vatic(args.annotations)
    objects, collisions = summarize(rows)
    audit = new_audit_dir(args.audit_root, f"cadp_{args.annotations.stem}")
    save_csv(audit / "objects.csv", objects, list(objects[0]))
    save_csv(audit / "colliding_intervals.csv", collisions,
             ["track_id", "label", "start_frame", "end_frame", "frame_count", "annotation_source", "user_review_status"])
    report = dict(video=str(args.video), annotations=str(args.annotations),
                  reference_archive=str(args.reference_zip),
                  annotation_sha256=sha256_file(args.annotations), object_count=len(objects),
                  annotation_rows=len(rows), colliding_intervals=collisions,
                  frame_index_base=0, original_timing_verified=False,
                  user_review_status="pending", preview=None)
    try:
        info = probe_video(args.video)
        report["video_info"] = info
        report["coordinate_ranges_xyxy"] = [[min(r["bbox"][i] for r in rows), max(r["bbox"][i] for r in rows)] for i in range(4)]
        if args.preview_config is None:
            report["alignment_status"] = "not_verified_no_overlay"
        else:
            config = json.loads(args.preview_config.read_text(encoding="utf-8"))
            verify_alignment(config, args.video, args.annotations, args.reference_zip, info, rows)
            report["alignment_status"] = "verified_rendered_reference_sample_only"
            report["alignment_config"] = config
            by_frame = defaultdict(list)
            for row in rows:
                by_frame[row["frame"]].append(row)
            output = unique_path(args.preview_root / f"cadp_{args.video.stem}_author_annotations.mp4")
            sx, sy, tx, ty = config["bbox_transform"]
            capture = cv2.VideoCapture(str(args.video))
            try:
                with H264Writer(output, info["width_px"], info["height_px"], info["fps"]) as writer:
                    for index in range(info["decoded_frames"]):
                        ok, frame = capture.read()
                        if not ok:
                            raise ValueError(f"Cannot read frame {index}")
                        for row in by_frame[index]:
                            # outside=1 là không nhìn thấy: không vẽ bbox dự đoán ngoài ảnh.
                            # FarRegion là vùng bỏ qua, không coi là một phương tiện.
                            if row["outside"]:
                                continue
                            colliding = "Colliding" in row["attributes"]
                            color = (0, 0, 255) if colliding else ((128, 128, 128) if row["label"] == "FarRegion" else (0, 200, 0))
                            x1, y1, x2, y2 = row["bbox"]
                            p1, p2 = (round(sx*x1+tx), round(sy*y1+ty)), (round(sx*x2+tx), round(sy*y2+ty))
                            cv2.rectangle(frame, p1, p2, color, 3)
                            label = f"GT {row['track_id']} {row['label']}" + (" Colliding" if colliding else "")
                            cv2.putText(frame, label, (p1[0], max(25, p1[1]-8)), cv2.FONT_HERSHEY_SIMPLEX, .65, color, 2)
                        # Banner ở viền trắng nhắc đây là annotation tác giả trên demo
                        # đã vẽ sẵn, không phải dự đoán model hay ảnh train sạch.
                        cv2.putText(frame, "AUTHOR ANNOTATIONS - NOT MODEL PREDICTION - RENDERED DEMO", (35, 55), cv2.FONT_HERSHEY_SIMPLEX, .95, (0, 0, 0), 2)
                        cv2.putText(frame, f"Frame {index} | RED: Colliding | GREEN: other visible GT | original timing unverified", (35, 100), cv2.FONT_HERSHEY_SIMPLEX, .85, (0, 0, 0), 2)
                        writer.write(frame)
                        if index in (0, 96, 130, 220):
                            cv2.imwrite(str(audit / f"overlay_frame_{index:03}.jpg"), frame)
            finally:
                capture.release()
            preview_info = probe_video(output)
            if preview_info["decoded_frames"] != info["decoded_frames"]:
                raise ValueError("Preview lost frames")
            report["preview"] = str(output)
            report["preview_info"] = preview_info
    except Exception as exc:
        report["error"] = str(exc)
        save_json(audit / "report.json", report)
        raise
    save_json(audit / "report.json", report)
    print(json.dumps(dict(audit=str(audit), preview=report["preview"], objects=len(objects), colliding_intervals=collisions), ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
