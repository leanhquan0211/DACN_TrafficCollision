"""Strict STTAD sample ingestion. Published accident boxes, not vehicle GT.

Raw labels inspected in the pinned repository are class + pixel xyxy, despite
the paper's high-level description of boxes by center/size. No silent guessing,
missing-label negatives, frame-time inference, or repair of broken source paths.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path, PurePosixPath
import re
import tempfile
from urllib.request import Request, urlopen

SOURCE = "https://raw.githubusercontent.com/ZTR02/STTAD/"


def blob_id(body: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest()


def safe_path(path: str) -> PurePosixPath:
    result = PurePosixPath(path)
    if result.is_absolute() or ".." in result.parts or "\\" in path or not result.parts:
        raise ValueError("Unsafe source path")
    return result


def parse_tree(text: str) -> dict[str, str]:
    tree = {}
    for line in text.splitlines():
        metadata, path = line.split("\t", 1)
        mode, kind, identity = metadata.split()
        safe_path(path)
        if mode != "100644" or kind != "blob" or not re.fullmatch(r"[0-9a-f]{40}", identity):
            raise ValueError("Unsupported Git entry")
        if path in tree:
            raise ValueError("Duplicate Git path")
        tree[path] = identity
    return tree


def parse_pixel_boxes(body: bytes, width: int, height: int, expected_class: int) -> list[dict]:
    if body.startswith(b"\xff\xd8"):
        raise ValueError("Label is JPEG bytes, not text")
    try:
        lines = body.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise ValueError("Label is not UTF-8 text") from exc
    if not lines or not body.strip():
        raise ValueError("Empty source label is unreviewed, not a certified negative")
    boxes = []
    for line in lines:
        fields = line.split()
        if len(fields) != 5:
            raise ValueError("Expected class_id xmin_px ymin_px xmax_px ymax_px")
        values = [float(value) for value in fields]
        if not all(math.isfinite(value) for value in values):
            raise ValueError("Non-finite box")
        class_id, x1, y1, x2, y2 = values
        if class_id != expected_class:
            raise ValueError(f"Class/category mismatch: {class_id} != {expected_class}")
        if not 0 <= x1 < x2 <= width or not 0 <= y1 < y2 <= height:
            raise ValueError("Pixel xyxy box outside image; do not auto-clip or guess format")
        boxes.append(dict(source_class_id=int(class_id), bbox_xyxy=[x1,y1,x2,y2],
                          bbox_cxcywh_norm=[(x1+x2)/(2*width),(y1+y2)/(2*height),(x2-x1)/width,(y2-y1)/height]))
    return boxes


def fetch_blob(commit: str, remote_path: str, destination: Path, expected: str,
               max_bytes: int = 4*1024*1024) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}",commit) or not re.fullmatch(r"[0-9a-f]{40}",expected):
        raise ValueError("An immutable commit and Git blob ID are required")
    safe_path(remote_path)
    if destination.exists():
        if destination.stat().st_size > max_bytes or blob_id(destination.read_bytes()) != expected:
            raise ValueError(f"Existing fingerprint mismatch; preserved: {destination}")
        return "reused_verified"
    request = Request(SOURCE+commit+"/"+remote_path, headers={"User-Agent":"TrafficCollision-research-pilot/1.0"})
    with urlopen(request,timeout=40) as response:
        body = response.read(max_bytes+1)
    if len(body)>max_bytes or blob_id(body)!=expected:
        raise ValueError(f"Downloaded Git blob mismatch or size cap: {remote_path}")
    destination.parent.mkdir(parents=True,exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent,prefix=".sttad-",delete=False) as stream:
            temporary=Path(stream.name);stream.write(body)
        destination.hardlink_to(temporary)
    finally:
        if temporary is not None:temporary.unlink(missing_ok=True)
    return "downloaded_verified"


def sequence_key(path: str, prefix: str) -> str:
    parts=safe_path(path).parts
    if len(parts)!=4 or parts[0]!=prefix:
        raise ValueError("Expected category/sequence/frame path")
    return "/".join(parts[1:3])


def validate_registry(registry: dict):
    if registry.get("repository")!="https://github.com/ZTR02/STTAD" or not re.fullmatch(r"[0-9a-f]{40}",registry.get("commit","")):
        raise ValueError("Unsupported source registry")
    sequences=registry["sequences"]
    allowed={s["key"] for s in sequences}
    if len(allowed)!=len(sequences) or not 1<=len(allowed)<=6:
        raise ValueError("Pilot must select 1–6 unique sequences")
    seen=set()
    grouped={key:{"rgb-images":set(),"labels":set()} for key in allowed}
    for item in registry["files"]:
        path=item["path"]
        if not re.fullmatch(r"[0-9a-f]{40}",item.get("git_blob_sha1","")):
            raise ValueError("Missing pinned Git blob ID")
        if path in seen:raise ValueError("Duplicate registry path")
        seen.add(path)
        if path in {"README.md","trainlist.txt","testlist.txt"}:continue
        prefix=path.split("/")[0]
        if prefix not in {"rgb-images","labels"} or sequence_key(path,prefix) not in allowed:
            raise ValueError("File belongs to an unselected sequence")
        if not re.fullmatch(r"\d{5}\.(jpg|txt)",PurePosixPath(path).name):
            raise ValueError("Unexpected frame filename")
        if (prefix=="rgb-images")!=(path.endswith(".jpg")):
            raise ValueError("Mismatched image/label suffix")
        grouped[sequence_key(path,prefix)][prefix].add(PurePosixPath(path).stem)
    if len(seen)>700:
        raise ValueError("Pilot file cap exceeded")
    for key,kinds in grouped.items():
        if not kinds["rgb-images"] or not kinds["labels"] or kinds["labels"]-kinds["rgb-images"]:
            raise ValueError(f"Sequence requires matching image/label paths: {key}")
