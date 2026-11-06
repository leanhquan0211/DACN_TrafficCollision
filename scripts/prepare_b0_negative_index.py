"""Lập chỉ mục frame âm từ các chuỗi DETRAC đã được người dùng xem đầy đủ.

Đầu vào: manifest, phiếu rà gắn hash và audit ghép ảnh DETRAC. Đầu ra: CSV
tham chiếu ảnh nguồn cùng căn cứ âm tính. Chạy sau xác nhận toàn chuỗi; không
lấy thiếu bbox xe làm bằng chứng âm, không tạo split, copy ảnh hoặc train.
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.prepare_detrac import numbered_images, read_image, file_crc32
from scripts.maintenance.update_manifest_reviews import read_manifest, verify_file
from src.data_preparation import save_csv, save_json, sha256_file
from src.storage_paths import artifact_path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser=argparse.ArgumentParser(description="Index only explicitly reviewed full-sequence accident-negative frames")
    parser.add_argument("--manifest",type=Path,default=Path("data/manifest.csv"))
    parser.add_argument("--review",type=Path,default=Path("data/reviews/2026-10-19-user-confirmations.json"))
    parser.add_argument("--preparation-report",type=Path,default=artifact_path(ROOT, 'outputs/data_audits/v001_detrac_preparation/report.json'))
    parser.add_argument("--output",type=Path,default=Path("data/processed/b0_reviewed_negatives"))
    args=parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Output already exists; existing index preserved")
    _,manifest=read_manifest(args.manifest)
    review=json.loads(args.review.read_text(encoding="utf-8"))
    report=json.loads(args.preparation_report.read_text(encoding="utf-8"))
    rows=[]
    counts={}
    with zipfile.ZipFile(report["archive"]) as archive:
        # Chỉ đọc central directory + CRC ảnh đang có; không giải nén/tải thêm.
        members={}
        for info in archive.infolist():
            parts=info.filename.replace("\\","/").split("/")
            if len(parts)>=2 and not info.is_dir():
                key=(parts[-2],parts[-1])
                if key in members:
                    raise ValueError("Duplicate sequence/image member")
                members[key]=info
        for item in manifest:
            if item["asset_role"]!="sequence_video" or item["source_dataset"]!="UA-DETRAC":
                continue
            if item["collision_label"]!="negative" or item["user_review_status"]!="reviewed_full_sequence_no_collision":
                continue
            statement=next((s for s in review["statements"] if s["video_id"]==item["video_id"] and s["scope"]=="full_sequence" and s.get("collision_label")=="negative"),None)
            if not statement or statement["sha256"]!=item["sha256"]:
                raise ValueError("No matching full-sequence negative review")
            verify_file(item["relative_path"],statement["sha256"])
            source=next(s for s in report["sequences"] if s["sequence"]==item["source_sequence"])
            if source["video_info"]["sha256"]!=statement["sha256"]:
                raise ValueError("Reviewed MP4 differs from image-sequence preparation")
            folder=Path(source["image_directory"])
            images=numbered_images(folder)
            expected=list(range(source["first_image_number"],source["last_image_number"]+1))
            if [number for number,_ in images]!=expected:
                raise ValueError("Source frame list changed")
            for number,path in images:
                info=members[(source["sequence"],path.name)]
                if path.stat().st_size!=info.file_size or file_crc32(path)!=info.CRC:
                    raise ValueError(f"Image changed from source ZIP: {path}")
                height,width=read_image(path).shape[:2]
                if (width,height)!=(source["video_info"]["width_px"],source["video_info"]["height_px"]):
                    raise ValueError("Source dimensions changed")
                rows.append(dict(source_dataset="UA-DETRAC",source_sequence=source["sequence"],source_frame=number,
                                 source_image=path.as_posix(),image_sha256=sha256_file(path),width_px=width,height_px=height,
                                 parent_video=item["relative_path"],parent_video_sha256=statement["sha256"],
                                 collision_label="negative",label_origin="user_full_sequence_review",
                                 review_path=args.review.as_posix(),accident_object_count=0,
                                 yolo_empty_label_justification="explicit full-scene accident-negative review, not absence of vehicle boxes",
                                 training_dataset_ready=False,split="unassigned"))
            counts[source["sequence"]]=len(images)
    if not rows:
        raise ValueError("No eligible full-sequence negative reviews")
    args.output.mkdir(parents=True,exist_ok=False)
    save_csv(args.output/"frames.csv",rows,list(rows[0]))
    save_json(args.output/"report.json",dict(frames=len(rows),full_source_sequences=counts,
              reference_only=True,images_copied=0,empty_label_files_created=0,
              label_scope="scene accident-negative, not vehicle detection-negative",
              all_images_decoded_and_crc_checked=True,training_dataset_ready=False,split_created=False))
    print(f"NEGATIVE_INDEX_OK {len(rows)} frames from {len(counts)} reviewed full sequences")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
