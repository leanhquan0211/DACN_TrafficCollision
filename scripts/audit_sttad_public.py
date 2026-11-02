"""Kiểm phần STTAD công khai và lấy chọn lọc vài chuỗi có ảnh + nhãn gốc.

Đầu vào: GitHub tree tại commit cố định, danh sách chuỗi và ngân sách tải.
Đầu ra: inventory nguồn, ảnh/TXT giữ cấu trúc, CSV bbox/unknown và ảnh đối chiếu.
Chạy không cờ để kiểm metadata; --fetch-selected lấy mẫu nhỏ, --offline kiểm lại
file đã lấy. Không tải toàn bộ dataset, tạo split, suy ra FPS hoặc train model.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import sys
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data_preparation import new_audit_dir, save_csv, save_json

REPO = "ZTR02/STTAD"
COMMIT = "21f3f5fea50b071f1db61186b481c2a7ccf525c9"
DEFAULT_SEQUENCES = ("V-V_crash/V-V_crash_0", "V-V_crash/V-V_crash_1",
                     "T-T_crash/T-T_crash_1", "T-T_crash/T-T_crash_2")


def project_path(path: Path) -> Path:
    """Giữ dữ liệu và audit trong workspace, kể cả khi truyền đường dẫn khác."""
    resolved = path.resolve()
    if not resolved.is_relative_to(ROOT):
        raise ValueError(f"Path must stay inside project: {path}")
    return resolved


def get_bytes(url: str, limit: int) -> bytes:
    """Chỉ GET nguồn công khai, giới hạn cả phản hồi không có Content-Length."""
    request = urllib.request.Request(url, headers={"User-Agent": "DACN-public-source-audit"})
    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f"Response exceeds budget: {url}")
    return data


def git_blob(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def index_tree(tree: dict) -> tuple[dict, dict]:
    """Ghép bằng đúng đường dẫn tương đối; không sửa tên V-T thành V-P."""
    if tree.get("truncated"):
        raise ValueError("Incomplete GitHub tree")
    files = {r["path"]: r for r in tree["tree"] if r["type"] == "blob"}
    groups = defaultdict(lambda: {"images": [], "labels": [], "unexpected": []})
    for path in files:
        p = PurePosixPath(path)
        if len(p.parts) != 4 or p.parts[0] not in ("labels", "rgb-images"):
            continue
        if ".." in p.parts or not p.stem.isdecimal():
            raise ValueError(f"Unexpected source path: {path}")
        kind = "labels" if p.parts[0] == "labels" else "images"
        expected = ".txt" if kind == "labels" else ".jpg"
        if p.suffix.lower() != expected:
            groups["/".join(p.parts[1:3])]["unexpected"].append(path)
            continue
        groups["/".join(p.parts[1:3])][kind].append(path)
    result = {}
    for key, group in sorted(groups.items()):
        images = {PurePosixPath(p).stem for p in group["images"]}
        labels = {PurePosixPath(p).stem for p in group["labels"]}
        result[key] = dict(images=len(images), labels=len(labels), paired=len(images & labels),
                           images_without_label=len(images-labels), labels_without_image=len(labels-images),
                           unexpected_files=group["unexpected"])
    return files, result


def parse_boxes(text: str, width: int, height: int) -> list[dict]:
    """Nguồn mẫu là class + xyxy PIXEL, không phải YOLO cxcywh chuẩn hóa.

    Chỉ chuyển đổi sau khi kiểm tọa độ; không clip bbox sai vào ảnh hoặc sửa
    class nguồn. Class project 0 là phép gộp có ghi rõ, giữ source_class riêng.
    """
    if not text.strip():
        raise ValueError("Empty annotation is not certified negative")
    boxes = []
    for line in text.splitlines():
        fields = line.split()
        if len(fields) != 5:
            raise ValueError(f"Expected class xyxy pixels: {line}")
        cls, x1, y1, x2, y2 = map(float, fields)
        if not all(math.isfinite(v) for v in (cls, x1, y1, x2, y2)) or cls < 0 or not cls.is_integer():
            raise ValueError("Invalid class/coordinates")
        if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
            raise ValueError(f"BBox outside {width}x{height}: {line}")
        boxes.append(dict(source_class=int(cls), xmin=x1, ymin=y1, xmax=x2, ymax=y2,
                          cx_norm=(x1+x2)/(2*width), cy_norm=(y1+y2)/(2*height),
                          w_norm=(x2-x1)/width, h_norm=(y2-y1)/height, project_class=0))
    return boxes


def inspect_selected(raw: Path, files: dict, sequences: list[str], audit: Path) -> dict:
    """Giải mã toàn ảnh đã chọn; frame thiếu TXT luôn unknown, không sinh âm."""
    import cv2
    import numpy as np

    frames, boxes, panels, fingerprints, decode_failures = [], [], [], [], []
    for sequence in sequences:
        source = sorted((p for p in files if p.startswith(f"rgb-images/{sequence}/")),
                        key=lambda p: int(PurePosixPath(p).stem))
        labels = [p for p in files if p.startswith(f"labels/{sequence}/")]
        labeled_numbers = sorted(int(PurePosixPath(p).stem) for p in labels)
        sample = {labeled_numbers[0], labeled_numbers[len(labeled_numbers)//2], labeled_numbers[-1]}
        sizes = Counter()
        for path in source:
            image_path = raw/path
            content = image_path.read_bytes()
            if git_blob(content) != files[path]["sha"]:
                raise ValueError(f"Image differs from pinned source: {path}")
            fingerprints.append(dict(relative_path=image_path.relative_to(ROOT).as_posix(),
                                     sha256=hashlib.sha256(content).hexdigest(), source_git_blob=files[path]["sha"]))
            picture = cv2.imdecode(np.frombuffer(content, dtype=np.uint8), cv2.IMREAD_COLOR)
            if picture is None:
                # File nguồn đã khớp Git nhưng không phải ảnh đọc được: giữ
                # nguyên, ghi loại trừ và tiếp tục kiểm phần độc lập còn tốt.
                decode_failures.append(path)
                frames.append(dict(sequence=sequence, source_frame=int(PurePosixPath(path).stem),
                                   image=image_path.relative_to(ROOT).as_posix(), width=0, height=0,
                                   annotation="", status="excluded_decode_failure", fps_status="unknown",
                                   split="unassigned", training_eligible=False))
                continue
            height, width = picture.shape[:2]
            sizes[f"{width}x{height}"] += 1
            stem = PurePosixPath(path).stem
            label = f"labels/{sequence}/{stem}.txt"
            records = []
            if label in files:
                body = (raw/label).read_bytes()
                if git_blob(body) != files[label]["sha"]:
                    raise ValueError(f"Label differs from pinned source: {label}")
                records = parse_boxes(body.decode("utf-8-sig"), width, height)
            # Một CSV giữ tất cả frame, một CSV chỉ chứa bbox nguồn hợp lệ.
            # Đường dẫn và class nguồn được giữ; không biến list của tác giả thành
            # train/test project, và không giả định file thiếu nghĩa không tai nạn.
            frames.append(dict(sequence=sequence, source_frame=int(stem), image=image_path.relative_to(ROOT).as_posix(),
                               width=width, height=height, annotation=(raw/label).relative_to(ROOT).as_posix() if records else "",
                               status="author_region_present" if records else "unknown_missing_label",
                               fps_status="unknown", split="unassigned", training_eligible=False))
            for record in records:
                boxes.append(dict(sequence=sequence, source_frame=int(stem), image=frames[-1]["image"],
                                  annotation=frames[-1]["annotation"], annotation_origin="author_sttad_region",
                                  visibility_status="not_provided", split="unassigned", training_eligible=False, **record))
            if records:
                # TXT chuyển đổi dùng để kiểm định dạng; không phải dataset
                # đã phát hành để train. Không tạo file rỗng cho frame unknown.
                converted = audit/"labels_yolo"/sequence/f"{stem}.txt"
                converted.parent.mkdir(parents=True, exist_ok=True)
                with converted.open("x", encoding="utf-8") as stream:
                    for record in records:
                        stream.write("0 " + " ".join(f"{record[k]:.8f}" for k in
                                     ("cx_norm", "cy_norm", "w_norm", "h_norm")) + "\n")
            if int(stem) in sample:
                # Trái: ảnh nguồn; phải: cùng ảnh có bbox tác giả để phát hiện
                # ảnh đã vẽ sẵn hoặc bbox lệch cảnh, không phải model prediction.
                drawn = picture.copy()
                for r in records:
                    cv2.rectangle(drawn, (int(r["xmin"]), int(r["ymin"])),
                                  (int(r["xmax"]), int(r["ymax"])), (0, 180, 255), 3)
                pair = cv2.hconcat([cv2.resize(picture, (480, 270)), cv2.resize(drawn, (480, 270))])
                cv2.rectangle(pair, (0, 0), (959, 28), (0, 0, 0), -1)
                cv2.putText(pair, f"{sequence} frame {stem} | raw / author region | NOT model output", (5, 19),
                            cv2.FONT_HERSHEY_SIMPLEX, .43, (255, 255, 255), 1)
                panels.append(pair)
        if len(sizes) != 1:
            raise ValueError(f"Mixed image sizes in sequence {sequence}: {sizes}")
    save_csv(audit/"frames.csv", frames, list(frames[0]))
    save_csv(audit/"boxes_normalized.csv", boxes, list(boxes[0]))
    save_csv(audit/"image_fingerprints.csv", fingerprints, list(fingerprints[0]))
    ok, encoded = cv2.imencode(".jpg", cv2.vconcat(panels))
    if not ok:
        raise OSError("Failed to write comparison image")
    # OpenCV imwrite có thể lỗi với đường dẫn tiếng Việt trên Windows.
    with (audit/"author_region_examples.jpg").open("xb") as stream:
        stream.write(encoded.tobytes())
    return dict(source_images=len(frames), decoded_images=len(frames)-len(decode_failures),
                decode_failures=decode_failures, author_boxes=len(boxes),
                frames_with_author_region=sum(r["status"] == "author_region_present" for r in frames),
                unknown_frames=sum(r["status"] == "unknown_missing_label" for r in frames),
                dimensions=dict(Counter(f"{r['width']}x{r['height']}" for r in frames if r['width'])),
                source_classes=dict(Counter(r["source_class"] for r in boxes)),
                converted_label_files=sum(r["status"] == "author_region_present" for r in frames),
                coordinate_interpretation_status="pixel xyxy checked by bounds and paired image overlays; not documented as normalized YOLO",
                invalid_boxes=0, source_format="class xyxy pixels; validated, not source YOLO normalized",
                source_timing_verified=False, negative_labels_created=0, can_train=False,
                example_image=(audit/"author_region_examples.jpg").relative_to(ROOT).as_posix())


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit pinned public STTAD examples; bounded selective download, no training")
    parser.add_argument("--fetch-selected", action="store_true")
    parser.add_argument("--offline", action="store_true", help="Use cached tree and downloaded images/labels; no network")
    parser.add_argument("--sequences", nargs="+", default=list(DEFAULT_SEQUENCES))
    parser.add_argument("--max-mib", type=int, default=96)
    parser.add_argument("--raw-root", type=Path, default=Path("data_raw/sttad/public_examples"))
    args = parser.parse_args()
    if args.max_mib <= 0 or len(set(args.sequences)) != len(args.sequences):
        parser.error("Use a positive byte budget and unique sequences")
    raw = project_path(args.raw_root)
    raw.mkdir(parents=True, exist_ok=True)
    cache = raw/"source_tree.json"
    # Cache cố định commit: máy khác kiểm cùng nguồn, không lặng lẽ lấy main mới.
    tree_bytes = cache.read_bytes() if cache.exists() else get_bytes(
        f"https://api.github.com/repos/{REPO}/git/trees/{COMMIT}?recursive=1", 4_000_000) if not args.offline else None
    if tree_bytes is None:
        raise FileNotFoundError("Offline mode requires cached source_tree.json")
    tree = json.loads(tree_bytes)
    if tree["sha"] != COMMIT:
        raise ValueError("Tree does not match pinned commit")
    files, groups = index_tree(tree)
    for seq in args.sequences:
        if seq not in groups or not groups[seq]["paired"] or groups[seq]["labels_without_image"]:
            raise ValueError(f"No exact image/label pairing: {seq}")
    selected = [r for p, r in files.items() if p in ("README.md", "trainlist.txt", "testlist.txt") or
                any(p.startswith(f"{kind}/{seq}/") for seq in args.sequences for kind in ("labels", "rgb-images"))]
    needed = sum(r["size"] for r in selected)
    if needed > args.max_mib * 1024**2:
        raise ValueError(f"Selected source bytes {needed} exceed --max-mib {args.max_mib}")
    if not cache.exists():
        cache.write_bytes(tree_bytes)
    audit = new_audit_dir(ROOT/"outputs/audits", "sttad_public")
    save_json(audit/"groups.json", groups)
    plan = dict(repo=REPO, commit=COMMIT, files_in_public_tree=len(files),
                public_tree_bytes=sum(r["size"] for r in files.values()), groups=groups,
                selected_sequences=args.sequences, selected_bytes=needed,
                raw_root=raw.relative_to(ROOT).as_posix(), full_dataset_downloaded=False)
    print(json.dumps({k: v for k, v in plan.items() if k != "groups"}, ensure_ascii=True), flush=True)
    if args.fetch_selected and not args.offline:
        missing_bytes = sum(r["size"] for r in selected if not (raw/r["path"]).exists())
        if shutil.disk_usage(raw).free < missing_bytes + 512*1024**2:
            raise OSError("Insufficient free space including 512 MiB reserve")

        def fetch(row: dict) -> None:
            target = raw/row["path"]
            if target.exists():
                body = target.read_bytes()
            else:
                body = get_bytes(f"https://raw.githubusercontent.com/{REPO}/{COMMIT}/{row['path']}", row["size"])
            if len(body) != row["size"] or git_blob(body) != row["sha"]:
                raise ValueError(f"Source content mismatch, preserved existing file: {row['path']}")
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as stream:
                    stream.write(body)

        # Bốn GET nhỏ song song; không clone kho gần 0,5 GB hoặc tải ZIP toàn bộ.
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(fetch, selected))
    if args.fetch_selected or args.offline:
        result = inspect_selected(raw, files, args.sequences, audit)
        # List tác giả là tài liệu gốc, không tự áp split hoặc tải những file
        # được liệt kê nhưng chưa phát hành trong public tree.
        lists = {}
        for name in ("trainlist.txt", "testlist.txt"):
            lines = (raw/name).read_text(encoding="utf-8-sig").splitlines()
            lists[name] = dict(entries=len(lines), entries_missing_from_public_tree=sum(p not in files for p in lines))
        plan.update(result, original_lists=lists)
    save_json(audit/"report.json", plan)
    print(f"Report: {(audit/'report.json').relative_to(ROOT).as_posix()}")
    if "decoded_images" in plan:
        print(json.dumps({k:plan[k] for k in ("decoded_images", "author_boxes", "unknown_frames", "can_train")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
