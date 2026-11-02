"""Lập chỉ mục nguồn B0 có nhãn, giữ nhóm cảnh và tách rõ nguồn xác nhận.

Đầu vào: audit STTAD, chỉ mục âm DETRAC đã rà và phiếu kiểm nguồn TAD/cảnh;
tùy chọn thêm nhiều batch impact ACCIDENT đã đối chiếu PTS và phiếu rà các
frame âm trước impact. Chỉ nhập frame được chấp nhận rõ ràng, giữ nguồn dẫn xuất.
Chế độ pool/audit xuất CSV tham chiếu + report, không copy media hay chia tập.
--export-split chỉ xuất PNG/TXT/YAML khi có split và release đã khóa; hiện
gate dữ liệu thật đóng, mới kiểm exporter bằng fixture. Không huấn luyện.
Frame STTAD thiếu TXT và CADP envelope dẫn xuất không nhập vào pool GT này.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import zlib
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data_preparation import save_csv, save_json, sha256_file, validate_b0_verified_origins


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def leakage_group(source_key: str, review: dict) -> str:
    """Nhóm cảnh là ràng buộc chống leakage, không phải camera ID đã xác minh."""
    matches = [g["id"] for g in review["leakage_groups"] if source_key in g["members"]]
    if len(matches) > 1:
        raise ValueError(f"Conflicting leakage groups: {source_key}")
    return matches[0] if matches else source_key


def checked_path(relative: str) -> Path:
    path = (ROOT/relative).resolve()
    if not path.is_relative_to(ROOT) or not path.is_file():
        raise ValueError(f"Missing or outside-project file: {relative}")
    return path


def build_index(sttad_report: Path, negatives: Path, review_path: Path) -> tuple[list[dict], dict]:
    """Join bằng path/frame chính xác và hash, không dùng thứ tự dòng để ghép."""
    report = json.loads(sttad_report.read_text(encoding="utf-8"))
    review = json.loads(review_path.read_text(encoding="utf-8"))
    if review["training_allowed"] or review["split_created"] or report["can_train"]:
        raise ValueError("This command prepares an unsplit pilot pool only")
    fingerprints = {r["relative_path"]: r["sha256"] for r in read_csv(sttad_report.parent/"image_fingerprints.csv")}
    source_boxes = read_csv(sttad_report.parent/"boxes_normalized.csv")
    by_image = {}
    for box in source_boxes:
        by_image.setdefault(box["image"], []).append(box)
    rows = []

    def entry(dataset, sequence, frame, source, kind, label, origin, evidence, bbox_count, converted=""):
        key = dataset + ":" + sequence
        return dict(source_dataset=dataset, source_sequence=sequence, source_frame=frame,
                    source_path=source, asset_kind=kind, collision_label=label, label_origin=origin,
                    label_evidence=evidence, accident_bbox_count=bbox_count, converted_label=converted,
                    leakage_group=leakage_group(key, review), camera_id_verified=False,
                    split="unassigned", training_release_allowed=False)

    for image, boxes in sorted(by_image.items()):
        if sha256_file(checked_path(image)) != fingerprints[image]:
            raise ValueError(f"STTAD image changed: {image}")
        first = boxes[0]
        label = sttad_report.parent/"labels_yolo"/first["sequence"]/f"{int(first['source_frame']):05d}.txt"
        tokens = [line.split() for line in label.read_text(encoding="utf-8").splitlines()]
        if len(tokens) != len(boxes) or any(len(t) != 5 or t[0] != "0" for t in tokens):
            raise ValueError(f"Converted label mismatch: {label}")
        for tokens_row, box in zip(tokens, boxes):
            for value, key in zip(tokens_row[1:], ("cx_norm", "cy_norm", "w_norm", "h_norm")):
                converted, expected = float(value), float(box[key])
                if not (0 <= converted <= 1 and abs(converted-expected) <= 1e-7):
                    raise ValueError(f"Converted coordinates differ from audited bbox: {label}")
        # Không tự thêm bbox cho frame chưa có annotation tác giả.
        rows.append(entry("STTAD", first["sequence"], first["source_frame"], image, "image",
                          "positive", "author_sttad_region", first["annotation"], len(boxes),
                          label.resolve().relative_to(ROOT).as_posix()))

    for item in read_csv(negatives):
        image = checked_path(item["source_image"])
        if item["collision_label"] != "negative" or sha256_file(image) != item["image_sha256"]:
            raise ValueError(f"Reviewed DETRAC reference changed: {image}")
        rows.append(entry("UA-DETRAC", item["source_sequence"], item["source_frame"],
                          item["source_image"], "image", "negative", item["label_origin"],
                          item["review_path"], 0))

    for clip in review["normal_clips"]:
        path = checked_path(clip["path"])
        if clip["annotation_origin"] != "author_normal_folder_clip_label" or clip["collision_label"] != "negative":
            raise ValueError("Missing author normal-clip evidence")
        if sha256_file(path) != clip["sha256"] or f"{zlib.crc32(path.read_bytes())&0xffffffff:08x}" != clip["crc32"]:
            raise ValueError(f"TAD video differs from audited ZIP member: {path}")
        # Đây là tham chiếu video + chỉ số decode 0-based, KHÔNG phải file JPG.
        # Materialize ảnh sau này phải đọc đúng frame; không nhân đôi clip ở đây.
        for frame in range(clip["decoded_frames"]):
            rows.append(entry("TAD", clip["sequence"], frame, clip["path"], "video_frame_reference",
                              "negative", "author_normal_folder_clip_label", review_path.as_posix(), 0))
    identities = {(r["source_dataset"], r["source_sequence"], int(r["source_frame"])) for r in rows}
    if len(identities) != len(rows):
        raise ValueError("Duplicate source frame in pilot pool")
    summary = dict(frame_references=len(rows), label_counts=dict(Counter(r["collision_label"] for r in rows)),
                   source_counts=dict(Counter(r["source_dataset"] for r in rows)),
                   nominal_source_groups=len({(r["source_dataset"], r["source_sequence"]) for r in rows}),
                   conservative_leakage_groups=len({r["leakage_group"] for r in rows}),
                   unknown_sttad_frames_excluded=report["unknown_frames"],
                   corrupt_sttad_files_excluded=len(report["decode_failures"]),
                   cadp_derived_boxes_included=0, images_copied=0, empty_labels_created=0,
                   split_created=False, can_train=False,
                   blockers=["Few positive source groups and sparse public region coverage",
                             "Dataset identity remains correlated with labels; TAD negatives add domain variety, not proof of matched cameras",
                             "No verified source/camera-independent split or sufficient hard-negative evaluation"],
                   frame_index_note="STTAD/DETRAC use source filename numbers; TAD video references use 0-based decode indices, not source seconds",
                   sttad_report=sttad_report.as_posix(), negative_index=negatives.as_posix(), source_review=review_path.as_posix())
    return rows, summary


def accident_entries(report_path: Path, review_path: Path) -> list[dict]:
    """Chỉ nhận impact đã kiểm PTS và được rà phù hợp nghĩa vùng B0.

    Bbox thiếu/chưa rõ phạm vi vẫn ở raw/audit. Không lan bbox impact sang
    frame lân cận. Frame âm cần phiếu rà riêng qua preimpact_entries().
    """
    report = json.loads(report_path.read_text(encoding="utf-8"))
    review = json.loads(review_path.read_text(encoding="utf-8"))
    if sha256_file(report_path) != review["source_report_sha256"]:
        raise ValueError("ACCIDENT source report changed since geometry review")
    verification = checked_path(review["verification_path"])
    if sha256_file(verification) != review["verification_sha256"]:
        raise ValueError("ACCIDENT verification changed since geometry review")
    verified = {x["source_sequence"]: x for x in json.loads(verification.read_text(encoding="utf-8"))["clips"]}
    if review["training_allowed"] or review["split_created"]:
        raise ValueError("Unsplit reference pool only")
    decisions = {x["source_sequence"]: x for x in review["clips"]}
    rows = []
    for clip in report["selected_clips"]:
        decision = decisions[clip["source_sequence"]]
        if decision["b0_region_status"] != "accepted_for_unsplit_pool":
            continue
        if not verified[clip["source_sequence"]]["technical_checks_passed"]:
            raise ValueError("ACCIDENT impact mapping failed")
        for key, hash_key in (("clean_image", "image_sha256"), ("source_video", "video_sha256"),
                              ("source_metadata", "metadata_sha256"), ("converted_label", "label_sha256")):
            if sha256_file(checked_path(clip[key])) != clip[hash_key]:
                raise ValueError(f"ACCIDENT source changed: {clip[key]}")
        tokens = checked_path(clip["converted_label"]).read_text(encoding="utf-8").split()
        x1,y1,x2,y2 = clip["xyxy_norm"]
        expected = ((x1+x2)/2, (y1+y2)/2, x2-x1, y2-y1)
        if len(tokens) != 5 or tokens[0] != "0" or any(abs(float(a)-b) > 1e-9 for a,b in zip(tokens[1:],expected)):
            raise ValueError("ACCIDENT converted label differs from author corners")
        rows.append(dict(source_dataset="ACCIDENT", source_sequence=clip["source_sequence"],
                         source_frame=clip["source_frame"], source_path=clip["clean_image"], asset_kind="image",
                         collision_label="positive", label_origin="author_accident_impact_region",
                         label_evidence=clip["source_metadata"], accident_bbox_count=1,
                         converted_label=clip["converted_label"], leakage_group=clip["source_group"],
                         camera_id_verified=False, split="unassigned", training_release_allowed=False))
    accepted = {x["source_sequence"] for x in review["clips"] if x["b0_region_status"] == "accepted_for_unsplit_pool"}
    if {x["source_sequence"] for x in rows} != accepted:
        raise ValueError("Review references absent ACCIDENT source")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare labeled B0 pilot reference pool, no media copies/splits/training")
    parser.add_argument("--sttad-report", type=Path)
    parser.add_argument("--audit-index", type=Path, help="Kiểm pool có sẵn, không chia tập hoặc xuất nhãn train")
    parser.add_argument("--reviewed-negatives", type=Path, default=Path("data/processed/b0_reviewed_negatives/frames.csv"))
    parser.add_argument("--source-review", type=Path, default=Path("data/reviews/2026-10-24-pilot-source-review.json"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/b0_public_pilot_v1"))
    parser.add_argument("--accident-report", type=Path)
    parser.add_argument("--accident-review", type=Path)
    parser.add_argument("--extra-accident", nargs=2, type=Path, action="append", default=[],
                        metavar=("REPORT", "REVIEW"), help="Thêm batch impact đã rà; có thể lặp lại")
    parser.add_argument("--preimpact-review", type=Path, help="Phiếu rà từng ảnh âm cùng cảnh, không nhãn clip")
    parser.add_argument("--group-review", type=Path, help="Áp nhóm cảnh bảo thủ từ phiếu rà, không đổi nhãn")
    parser.add_argument("--export-split", type=Path, help="CSV split đã khóa; chỉ export khi readiness/policy cho phép")
    parser.add_argument("--pool-index", type=Path, help="Pool đầu vào cho --export-split")
    parser.add_argument("--release-kind", choices=("benchmark", "pilot"), default="benchmark",
                        help="Pilot có gate riêng; không tự mở release benchmark")
    parser.add_argument("--release-key", default="pilot_release", help="Khóa readiness cho pilot đã fingerprint; mặc định giữ release cũ")
    parser.add_argument("--policy-path", type=Path, default=Path("configs/b0_public_label_policy.json"))
    parser.add_argument("--make-pilot-split", type=Path, help="Tạo pilot ảnh ACCIDENT đã rà, chia theo nhóm nguồn")
    parser.add_argument("--seed", type=int, default=20261026)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT) or output.exists():
        parser.error("Output must be a NEW directory inside project")
    if args.make_pilot_split:
        if args.pool_index or args.export_split or args.audit_index or args.sttad_report:
            parser.error("Pilot split mode takes --make-pilot-split INDEX --output NEW_DIR")
        make_pilot_split(args.make_pilot_split, output, args.seed)
        return 0
    if args.export_split:
        if not args.pool_index or args.audit_index or args.sttad_report or args.accident_report or args.accident_review or args.extra_accident or args.preimpact_review or args.group_review:
            parser.error("Export mode needs --pool-index and --export-split only")
        export_dataset(args.pool_index, args.export_split, output, args.release_kind, args.release_key, args.policy_path)
        return 0
    if args.pool_index:
        parser.error("--pool-index requires --export-split")
    if args.audit_index:
        if args.sttad_report or args.accident_report or args.accident_review or args.extra_accident or args.preimpact_review or args.group_review:
            parser.error("Audit mode takes an existing index only")
        report, groups = audit_index(args.audit_index)
        output.mkdir(parents=True, exist_ok=False)
        save_json(output/"report.json", report)
        save_csv(output/"groups.csv", groups, list(groups[0]) if groups else ["leakage_group"])
        print(json.dumps(report, ensure_ascii=False))
        return 0 if report["technical_checks_passed"] else 1
    if not args.sttad_report:
        parser.error("Supply --sttad-report or --audit-index")
    rows, report = build_index(args.sttad_report, args.reviewed_negatives, args.source_review)
    if bool(args.accident_report) != bool(args.accident_review):
        parser.error("--accident-report and --accident-review must be supplied together")
    if args.accident_report:
        extra = accident_entries(args.accident_report, args.accident_review)
        rows.extend(extra)
        if len({(r["source_dataset"], r["source_sequence"], int(r["source_frame"])) for r in rows}) != len(rows):
            raise ValueError("Duplicate source frame after ACCIDENT join")
        report.update(frame_references=len(rows), label_counts=dict(Counter(r["collision_label"] for r in rows)),
                      source_counts=dict(Counter(r["source_dataset"] for r in rows)),
                      nominal_source_groups=len({(r["source_dataset"],r["source_sequence"]) for r in rows}),
                      conservative_leakage_groups=len({r["leakage_group"] for r in rows}),
                      accident_report=args.accident_report.as_posix(), accident_review=args.accident_review.as_posix(),
                      accident_impact_frames_added=len(extra),
                      accident_other_frames_included=0,
                      frame_index_note="STTAD/DETRAC: filename numbers; TAD/ACCIDENT: 0-based decode. ACCIDENT impact joined by verified presentation timestamp; original capture timing remains unverified")
    for source_report, review in args.extra_accident:
        rows.extend(accident_entries(source_report, review))
    if args.preimpact_review:
        rows.extend(preimpact_entries(args.preimpact_review))
    if args.group_review:
        grouping = json.loads(args.group_review.read_text(encoding="utf-8"))
        for row in rows:
            key = row["source_dataset"]+":"+row["source_sequence"]
            if any(key in group["members"] for group in grouping["leakage_groups"]):
                row["leakage_group"] = leakage_group(key, grouping)
    identities = {(r["source_dataset"],r["source_sequence"],int(r["source_frame"])) for r in rows}
    if len(identities) != len(rows):
        raise ValueError("Duplicate frame across batches/reviews")
    # Một chuỗi không được tách nhóm chỉ vì một frame âm và frame khác dương.
    assignments = {}
    for row in rows:
        key = (row["source_dataset"],row["source_sequence"])
        if key in assignments and assignments[key] != row["leakage_group"]:
            raise ValueError("One sequence assigned to multiple leakage groups")
        assignments[key] = row["leakage_group"]
    report.update(frame_references=len(rows), label_counts=dict(Counter(r["collision_label"] for r in rows)),
                  source_counts=dict(Counter(r["source_dataset"] for r in rows)),
                  nominal_source_groups=len(assignments),
                  conservative_leakage_groups=len({r["leakage_group"] for r in rows}),
                  accident_impact_frames_added=sum(r["source_dataset"]=="ACCIDENT" and r["collision_label"]=="positive" for r in rows),
                  accident_other_frames_included=sum(r["source_dataset"]=="ACCIDENT" and r["collision_label"]=="negative" for r in rows),
                  extra_accident_batches=[[p.as_posix() for p in pair] for pair in args.extra_accident],
                  preimpact_review=args.preimpact_review.as_posix() if args.preimpact_review else None,
                  group_review=args.group_review.as_posix() if args.group_review else None)
    output.mkdir(parents=True, exist_ok=False)
    save_csv(output/"index.csv", rows, list(rows[0]))
    save_json(output/"report.json", report)
    print(json.dumps(report))
    print(f"Report: {(output/'report.json').relative_to(ROOT).as_posix()}")
    return 0


def make_pilot_split(index: Path, output: Path, seed: int) -> None:
    """Lập thí nghiệm nhỏ từ ảnh impact và âm cùng cảnh đã có bằng chứng.

    Không đợi âm khó để thử B0 cơ bản. Chỉ dùng ACCIDENT để cả hai nhãn cùng
    nguồn dữ liệu; giữ scene/segment cùng tập. Test ít chỉ là phép đo pilot,
    không chứng minh khả năng tổng quát ngoài camera hoặc phát hiện sự kiện.
    """
    import hashlib
    ready = json.loads((ROOT/"data/b0_readiness.json").read_text(encoding="utf-8"))
    validation = json.loads(checked_path(ready["pool_validation"]).read_text(encoding="utf-8"))
    if sha256_file(index) != validation["index_sha256"] or not validation["technical_checks_passed"]:
        raise ValueError("Pilot pool differs from audited input")
    pool_report = json.loads(checked_path(ready["prepared_pool"]).read_text(encoding="utf-8"))
    evidence = accident_entries(checked_path(pool_report["accident_report"]),checked_path(pool_report["accident_review"]))
    for report,review in pool_report.get("extra_accident_batches",[]):
        evidence.extend(accident_entries(checked_path(report),checked_path(review)))
    evidence.extend(preimpact_entries(checked_path(pool_report["preimpact_review"])))
    def identity(row):
        return (row["source_dataset"],row["source_sequence"],int(row["source_frame"]))
    verified = {identity(r):r for r in evidence}
    selected = [r for r in read_csv(index) if identity(r) in verified]
    for row in selected:
        original = verified[identity(row)]
        for field in ("source_path","collision_label","converted_label","leakage_group"):
            if row[field] != original[field]:
                raise ValueError("Audited row differs from scoped source review")
    groups = {}
    for row in selected:
        groups.setdefault(row["leakage_group"],[]).append(row)
    if any({r["collision_label"] for r in rows} != {"positive","negative"} for rows in groups.values()):
        raise ValueError("Pilot needs reviewed positives and negatives in every source group")
    metadata = read_csv(checked_path("data_raw/accident/public_selected/metadata-real.csv"))
    by_sequence = {Path(r["path"]).stem:r for r in metadata}
    # Gom bảo thủ các mẫu cùng thành phố Seattle ở train. Đây là phòng rủi
    # ro camera gần nhau, không tuyên bố đã xác minh camera vật lý giống nhau.
    assignments = {group:"train" for group,rows in groups.items()
                   if by_sequence[rows[0]["source_sequence"]]["region"] == "Seattle"}
    by_type = {}
    for group,rows in groups.items():
        by_type.setdefault(by_sequence[rows[0]["source_sequence"]]["type"],[]).append(group)
    def rank(group):
        return hashlib.sha256(f"{seed}:{group}".encode()).hexdigest()
    # Loại chỉ có 1–2 sự kiện để ở train, không tạo một test thiếu hỗ trợ
    # chỉ để đạt tỷ lệ đẹp. Với loại >=3 nhóm, giữ tối thiểu một val và test.
    for kind,source_groups in sorted(by_type.items()):
        available = sorted((g for g in source_groups if g not in assignments),key=rank)
        if len(source_groups) < 3:
            assignments.update({g:"train" for g in available})
        elif len(available) >= 3:
            assignments[available[0]]="val";assignments[available[1]]="test"
    for split in ("val","test"):
        available=sorted((g for g in groups if g not in assignments),key=rank)
        for group in available[:max(0,3-sum(v==split for v in assignments.values()))]:
            assignments[group]=split
    assignments.update({g:"train" for g in groups if g not in assignments})
    splits = [dict(source_dataset=r["source_dataset"],source_sequence=r["source_sequence"],
                   source_frame=r["source_frame"],split=assignments[r["leakage_group"]]) for r in selected]
    plan=export_plan(selected,splits)
    output.mkdir(parents=True,exist_ok=False)
    save_csv(output/"index.csv",selected,list(selected[0]))
    save_csv(output/"split.csv",splits,list(splits[0]))
    save_json(output/"split_report.json",dict(seed=seed,scope="basic accident-region image pilot; hard negatives deferred",
              source_pool=index.as_posix(),source_pool_sha256=sha256_file(index),
              samples=len(plan),labels=dict(Counter(r["collision_label"] for r in plan)),
              split_samples=dict(Counter(r["split"] for r in plan)),
              split_positive=dict(Counter(r["split"] for r in plan if r["collision_label"]=="positive")),
              group_assignments=assignments,group_counts=dict(Counter(assignments.values())),
              camera_independence_verified=False,source_group_disjoint=True,
              sampling="All verified ACCIDENT impact boxes and exact reviewed preimpact negatives; no model-based selection",
              type_stratification=by_type,conservative_seattle_groups=[g for g in assignments
                  if by_sequence[groups[g][0]["source_sequence"]]["region"]=="Seattle"],
              note="Rare types retained in train; 3 source groups each for val/test. Not author benchmark split or temporal event evaluation."))
    print(f"Pilot split prepared: {output/'split_report.json'}")


def export_plan(rows: list[dict], splits: list[dict]) -> list[dict]:
    """Ghép split bằng ID nguồn, chặn một cảnh/chuỗi xuất hiện ở hai tập.

    Chỉ số frame gốc được giữ, không ghép theo số thứ tự dòng. Hàm không tự
    chia tập; manifest split phải được lập từ quyết định nhóm đã có căn cứ.
    """
    def key(row):
        return (row["source_dataset"],row["source_sequence"],int(row["source_frame"]))
    pool = {key(row):row for row in rows}
    if len(pool) != len(rows):
        raise ValueError("Duplicate pool identity")
    seen, groups, sequences, result = set(), {}, {}, []
    counts = {name:Counter() for name in ("train","val","test")}
    for assignment in splits:
        identity = key(assignment)
        if identity in seen or identity not in pool:
            raise ValueError("Duplicate or unknown split identity")
        seen.add(identity)
        split = assignment["split"]
        if split not in counts:
            raise ValueError("Split must be train, val or test")
        row = pool[identity]
        if row["collision_label"] not in ("positive","negative") or not row["label_origin"] or not row["label_evidence"]:
            raise ValueError("Unreviewed/unknown sample cannot be exported")
        group = row["leakage_group"]
        if not group:
            raise ValueError("Missing leakage group")
        for mapping, item in ((groups,group),(sequences,identity[:2])):
            if item in mapping and mapping[item] != split:
                raise ValueError("Source sequence/leakage group crosses splits")
            mapping[item] = split
        counts[split][row["collision_label"]] += 1
        result.append(dict(row,split=split))
    if any(not count["positive"] or not count["negative"] for count in counts.values()):
        raise ValueError("Each evaluation/training split needs both labeled classes")
    return sorted(result,key=lambda row:(row["split"],key(row)))


def export_dataset(index: Path, split_path: Path, output: Path, release_kind: str = "benchmark",
                   release_key: str = "pilot_release", policy_path: Path = Path("configs/b0_public_label_policy.json")) -> None:
    """Xuất ảnh PNG/TXT và YAML YOLO sau khi gate dữ liệu đã mở.

    Pool giữ tham chiếu để tiết kiệm chỗ; chỉ lúc phát hành mới materialize
    đúng các ảnh đã chọn. Âm có căn cứ nhận TXT rỗng; không đọc nhãn từ sự
    vắng mặt của TXT. Lưu provenance/hash để lần train sau truy lại được.
    """
    import hashlib
    import shutil
    ready = json.loads((ROOT/"data/b0_readiness.json").read_text(encoding="utf-8"))
    policy_file = checked_path(policy_path.as_posix())
    policy = json.loads(policy_file.read_text(encoding="utf-8"))
    if release_kind not in ("benchmark", "pilot"):
        raise ValueError("Invalid release scope")
    if release_kind == "pilot":
        ready = ready.get(release_key, {})
        policy_allowed = policy.get("pilot_training_release_allowed", False)
    else:
        policy_allowed = policy["training_release_allowed"]
    # Kiểm đúng gate pilot/benchmark TRƯỚC mở split hoặc ghi thư mục;
    # release pilot không tự mở benchmark đầy đủ.
    if not ready.get("can_train", False) or not ready.get("split_created", False) or not policy_allowed:
        raise ValueError("B0 data release is blocked by readiness/policy; no dataset written")
    if sha256_file(index) != ready["export_pool_sha256"] or sha256_file(split_path) != ready["export_split_sha256"]:
        raise ValueError("Pool/split differs from locked release fingerprints")
    if sha256_file(policy_file) != ready["export_policy_sha256"]:
        raise ValueError("Policy differs from locked release")
    asset_hashes = ready.get("export_asset_sha256")
    if asset_hashes is None:
        asset_manifest = checked_path(ready["export_asset_manifest"])
        if sha256_file(asset_manifest) != ready["export_asset_manifest_sha256"]:
            raise ValueError("Scaled asset manifest changed after release")
        asset_hashes = json.loads(asset_manifest.read_text(encoding="utf-8"))
    output = output.resolve()
    if not output.is_relative_to(ROOT) or output.exists():
        raise ValueError("Export requires a NEW workspace directory")
    plan = export_plan(read_csv(index),read_csv(split_path))
    if release_key == "expanded_pilot_release" and any(
        r["label_origin"] == "derived_author_first_visible_contact_candidate" and r["split"] != "train"
        for r in plan
    ):
        raise ValueError("Unreviewed preimpact candidates may only supervise expanded-pilot train")
    if release_key in ("verified_pilot_release","normal_expanded_pilot_release","hard_negative_pilot_release"):
        validate_b0_verified_origins(plan)
    # Preflight mọi path/label trước khi ghi. Lỗi decode về sau để lại report
    # failed và KHÔNG sinh dataset.yaml, tránh dùng nhầm export dở dang.
    physical = set()
    for row in plan:
        checked_path(row["source_path"])
        checked_path(row["label_evidence"])
        identity = (checked_path(row["source_path"]),int(row["source_frame"]) if row["asset_kind"]=="video_frame_reference" else None)
        if identity in physical:
            raise ValueError("One physical frame has multiple source identities")
        physical.add(identity)
        # Pool hash khóa metadata, chưa khóa byte media. Release cần cả bảng
        # SHA nguồn/nhãn/evidence để không export dữ liệu bị sửa sau audit.
        for name in (row["source_path"],row["label_evidence"],row["converted_label"]):
            if name and sha256_file(checked_path(name)) != asset_hashes.get(name):
                raise ValueError("Source asset differs from locked release fingerprint")
        if row["collision_label"] == "positive":
            validate_yolo(checked_path(row["converted_label"]).read_text(encoding="utf-8"),int(row["accident_bbox_count"]))
        elif int(row["accident_bbox_count"]) != 0 or row["converted_label"]:
            raise ValueError("Negative provenance contradicts bbox data")
        if row["asset_kind"] not in ("image","video_frame_reference") or int(row["source_frame"]) < 0:
            raise ValueError("Invalid media reference")
    required = sum(checked_path(r["source_path"]).stat().st_size for r in plan if r["asset_kind"]=="image")
    if shutil.disk_usage(ROOT).free < max(required*5,512*1024**2):
        raise OSError("Insufficient disk reserve for lossless dataset export")
    output.mkdir(parents=True)
    records=[]
    def materialize(row, picture):
        if picture is None:
            raise ValueError("Cannot decode selected export frame")
        # Tên hash từ identity tránh ký tự đường dẫn nguồn và trùng stem giữa dataset.
        identity=json.dumps([row["source_dataset"],row["source_sequence"],int(row["source_frame"])],ensure_ascii=False)
        stem=hashlib.sha256(identity.encode()).hexdigest()
        image=output/"images"/row["split"]/(stem+".png")
        label=output/"labels"/row["split"]/(stem+".txt")
        image.parent.mkdir(parents=True,exist_ok=True);label.parent.mkdir(parents=True,exist_ok=True)
        ok,body=cv2.imencode(".png",picture)
        if not ok:
            raise ValueError("PNG encoding failed")
        image.write_bytes(body.tobytes())
        text=checked_path(row["converted_label"]).read_text(encoding="utf-8") if row["collision_label"]=="positive" else ""
        label.write_text(text,encoding="utf-8",newline="\n")
        records.append(dict(**row,export_image=image.relative_to(output).as_posix(),
                            export_label=label.relative_to(output).as_posix(),
                            image_sha256=sha256_file(image),label_sha256=sha256_file(label)))
    try:
        videos={}
        for row in plan:
            if row["asset_kind"]=="image":
                picture=cv2.imdecode(np.frombuffer(checked_path(row["source_path"]).read_bytes(),np.uint8),1)
                materialize(row,picture)
            else:
                videos.setdefault(row["source_path"],{})[int(row["source_frame"])]=row
        for video,wanted in videos.items():
            cap=cv2.VideoCapture(str(checked_path(video)))
            try:
                for frame in range(max(wanted)+1):
                    ok,picture=cap.read()
                    if not ok:
                        raise ValueError("Missing source video frame during export")
                    if frame in wanted:
                        materialize(wanted[frame],picture)
            finally:
                cap.release()
        # YAML chỉ phát hành sau khi mọi ảnh/label/provenance đã ghi thành công.
        yaml="path: "+json.dumps(output.as_posix(),ensure_ascii=False)+"\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n  0: accident\n"
        save_csv(output/"provenance.csv",records,list(records[0]))
        save_json(output/"report.json",dict(status="complete",samples=len(records), release_kind=release_kind,
                  release_key=release_key, policy_path=policy_file.relative_to(ROOT).as_posix(),
                  label_counts=dict(Counter(r["collision_label"] for r in records)),
                  pool_sha256=sha256_file(index),split_sha256=sha256_file(split_path),
                  provenance_sha256=sha256_file(output/"provenance.csv"),
                  dataset_yaml_sha256=hashlib.sha256(yaml.encode("utf-8")).hexdigest(),model_trained=False))
        (output/"dataset.yaml").write_text(yaml,encoding="utf-8",newline="\n")
    except Exception as exc:
        save_json(output/"failure.json",dict(status="incomplete_do_not_train",error=str(exc)))
        raise
    print(f"Exported {len(records)} samples: {output/'dataset.yaml'}")


def preimpact_entries(review_path: Path) -> list[dict]:
    """Nhập đúng các frame âm đã rà; frame chưa rà/không rõ tiếp tục ở ngoài pool.

    Nhãn dẫn xuất dựa vào thời điểm tác giả và quan sát toàn ảnh của AI, không
    phải nhãn âm do tác giả cung cấp hay xác nhận mới của người dùng.
    """
    review = json.loads(review_path.read_text(encoding="utf-8"))
    if review["training_allowed"] or review["split_created"]:
        raise ValueError("Only an unsplit frame review is accepted")
    candidates = {}
    for source in review["candidate_reports"]:
        path = checked_path(source["path"])
        if sha256_file(path) != source["sha256"]:
            raise ValueError("Candidate report changed after review")
        report = json.loads(path.read_text(encoding="utf-8"))
        verification_path = path.parent/"verification.json"
        if sha256_file(verification_path) != source["verification_sha256"]:
            raise ValueError("Preimpact pixel verification changed after review")
        verified = json.loads(verification_path.read_text(encoding="utf-8"))
        if not verified["all_technical_checks_passed"] or verified["candidate_report_sha256"] != source["sha256"]:
            raise ValueError("Preimpact verification failed or references another report")
        impact = checked_path(report["source_report"])
        if sha256_file(impact) != report["source_report_sha256"] or sha256_file(impact.parent/"verification.json") != report["verification_sha256"]:
            raise ValueError("Impact evidence changed")
        for row in report["candidates"]:
            key = (row["source_sequence"], row["source_frame"])
            if key in candidates:
                raise ValueError("Duplicate preimpact candidate")
            candidates[key] = row
    rows, seen = [], set()
    for decision in review["frames"]:
        key = (decision["source_sequence"], decision["source_frame"])
        if key in seen or key not in candidates:
            raise ValueError("Duplicate or absent reviewed frame")
        seen.add(key)
        if decision["status"] != "accepted_negative_frame":
            continue
        row = candidates[key]
        if not decision.get("reason") or row["source_frame"] >= row["impact_frame"] or row["margin_seconds"] < 1:
            raise ValueError("Missing review reason or inadequate preimpact margin")
        if not math.isclose(row["impact_pts_seconds"]-row["pts_seconds"],row["margin_seconds"],abs_tol=1e-6):
            raise ValueError("Inconsistent preimpact timing")
        for field, digest in (("image","image_sha256"),("source_video","video_sha256")):
            if sha256_file(checked_path(row[field])) != row[digest]:
                raise ValueError("Reviewed preimpact asset changed")
        rows.append(dict(source_dataset="ACCIDENT", source_sequence=key[0], source_frame=key[1],
                         source_path=row["image"], asset_kind="image", collision_label="negative",
                         label_origin="derived_author_preimpact_assistant_frame_review",
                         label_evidence=review_path.resolve().relative_to(ROOT).as_posix(), accident_bbox_count=0,
                         converted_label="", leakage_group=row["source_group"], camera_id_verified=False,
                         split="unassigned", training_release_allowed=False))
    return rows


def validate_yolo(text: str, expected_count: int) -> None:
    """Kiểm cả mép hộp: tâm/kích thước hợp lệ chưa đảm bảo hộp nằm trong ảnh."""
    lines = [line.split() for line in text.splitlines() if line.strip()]
    if len(lines) != expected_count or expected_count < 1:
        raise ValueError("Positive bbox count mismatch")
    for line in lines:
        if len(line) != 5 or line[0] != "0":
            raise ValueError("Expected accident class 0 and four coordinates")
        x, y, w, h = map(float, line[1:])
        if not all(math.isfinite(v) for v in (x,y,w,h)) or w <= 0 or h <= 0:
            raise ValueError("Nonfinite or nonpositive bbox")
        if min(x-w/2, y-h/2) < -1e-7 or max(x+w/2, y+h/2) > 1+1e-7:
            raise ValueError("BBox outside normalized image bounds")


def audit_index(index: Path) -> tuple[dict, list[dict]]:
    """Đọc pool và media thật; xuất kiểm kỹ thuật và độ phủ, không duyệt ngữ nghĩa.

    Ảnh âm chỉ được kiểm theo căn cứ đã ghi trong pool; không suy nhãn từ
    việc thiếu TXT. Video được decode tuần tự để tránh seek lệch frame.
    """
    rows = read_csv(index)
    errors, seen, sources, groups, videos = [], set(), {}, {}, {}
    decoded_images = decoded_video_frames = 0
    for number, row in enumerate(rows, 2):
        try:
            identity = (row["source_dataset"], row["source_sequence"], int(row["source_frame"]))
            if identity in seen or identity[2] < 0:
                raise ValueError("Duplicate or negative source frame")
            seen.add(identity)
            label = row["collision_label"]
            if label not in ("positive", "negative"):
                raise ValueError("Unknown label cannot enter supervised pool")
            if row["split"] != "unassigned" or row["training_release_allowed"].lower() != "false":
                raise ValueError("Expected unreleased, unsplit pool")
            if not row["label_origin"] or not row["label_evidence"] or not row["leakage_group"]:
                raise ValueError("Missing provenance or leakage group")
            checked_path(row["label_evidence"])
            path = checked_path(row["source_path"])
            count = int(row["accident_bbox_count"])
            if label == "positive":
                validate_yolo(checked_path(row["converted_label"]).read_text(encoding="utf-8"), count)
            elif count != 0 or row["converted_label"]:
                raise ValueError("Negative row has a bbox or unexpected label file")
            if row["asset_kind"] == "image":
                frame = cv2.imdecode(np.frombuffer(path.read_bytes(), dtype=np.uint8), cv2.IMREAD_COLOR)
                if frame is None:
                    raise ValueError("Image decode failed")
                decoded_images += 1
            elif row["asset_kind"] == "video_frame_reference":
                videos.setdefault(path, set()).add(identity[2])
            else:
                raise ValueError("Unsupported asset kind")
            sources.setdefault(identity[0], Counter())[label] += 1
            group = groups.setdefault(row["leakage_group"], {"counts": Counter(), "sources": set(), "sequences": set()})
            group["counts"][label] += 1
            group["sources"].add(identity[0])
            group["sequences"].add(identity[:2])
        except (ValueError, KeyError, OSError) as exc:
            errors.append({"csv_line": number, "error": str(exc)})
    # Decode một lần mỗi video, chỉ đếm các chỉ số được pool tham chiếu.
    for path, wanted in videos.items():
        cap = cv2.VideoCapture(str(path))
        found, i = set(), 0
        try:
            while cap.isOpened():
                ok, frame = cap.read()
                if not ok:
                    break
                if i in wanted:
                    found.add(i)
                i += 1
        finally:
            cap.release()
        decoded_video_frames += len(found)
        if wanted-found:
            errors.append({"video": str(path.relative_to(ROOT)), "missing_frames": sorted(wanted-found)})
    table = [dict(leakage_group=key, datasets=";".join(sorted(g["sources"])),
                  source_sequences=len(g["sequences"]), positive=g["counts"]["positive"],
                  negative=g["counts"]["negative"]) for key,g in sorted(groups.items())]
    # Thống kê mô tả trên chính pool, KHÔNG phải accuracy model/held-out test.
    source_majority = sum(max(c.values()) for c in sources.values())
    report = dict(index_path=index.as_posix(), index_sha256=sha256_file(index),
                  frame_references=len(rows), decoded_images=decoded_images,
                  decoded_video_references=decoded_video_frames, errors=errors,
                  technical_checks_passed=bool(rows) and not errors,
                  source_label_counts={k:dict(v) for k,v in sorted(sources.items())},
                  groups_with_both_labels=sum(g["positive"]>0 and g["negative"]>0 for g in table),
                  source_majority_agreement_on_same_pool=source_majority/len(rows) if rows else None,
                  interpretation="Descriptive source-label association, not model accuracy or an independence test",
                  semantic_coverage_verified_by_this_audit=False,
                  split_created=False, training_release_allowed=False,
                  remaining_checks=["Expand independent positive events and matched-domain negatives",
                                    "Review annotation completeness and hard-negative coverage",
                                    "Justify group split before any training release"])
    return report, table


if __name__ == "__main__":
    raise SystemExit(main())
