"""Kiểm metadata/split mà không tự gán nhãn hoặc chia tập dữ liệu.

Nhóm liên thông dùng nguồn chuỗi, camera, sự kiện, hash và quan hệ dẫn xuất.
Đây chỉ là kiểm leakage đã biết; không thay rà near-duplicate bằng media.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import math
from pathlib import PurePosixPath


SPLITS = {"train", "val", "test"}
REQUIRED = {"video_id", "relative_path", "sha256", "source_dataset", "source_sequence",
            "source_event_id", "camera_id", "derived_from", "collision_label", "split",
            "onset_s", "end_s", "fps_status", "asset_role"}


def normalized_path(value: str) -> str:
    return str(PurePosixPath(value.replace("\\", "/"))) if value else ""


def audit_manifest(rows: list[dict]) -> dict:
    """Trả lỗi cụ thể và nhóm chống leakage; không xác nhận tập đủ để train."""
    issues = []

    def issue(code, ids, detail):
        issues.append(dict(code=code, asset_ids=sorted(ids), detail=detail))

    if not rows:
        issue("empty_manifest", [], "Manifest has no assets")
    for i, row in enumerate(rows):
        missing = REQUIRED - row.keys()
        if missing:
            raise ValueError(f"Manifest row {i + 2} missing columns: {sorted(missing)}")
        if any(not isinstance(row[k], str) for k in REQUIRED):
            raise ValueError(f"Manifest row {i + 2} has missing/non-text cells")
    ids = [r["video_id"] for r in rows]
    for value, count in Counter(ids).items():
        if not value or count > 1:
            issue("invalid_asset_id", [value], "Asset IDs must be nonempty and unique")

    parents = list(range(len(rows)))

    def root(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i

    owners = {}
    links = []
    for i, row in enumerate(rows):
        dataset = row["source_dataset"]
        keys = []
        for field in ("source_sequence", "camera_id", "source_event_id"):
            if row[field]:
                keys.append((field, dataset, row[field]))
        if row["sha256"]:
            keys.append(("sha256", row["sha256"].lower()))
        # A parent need not have its own row: siblings still share this key.
        for field in ("relative_path", "derived_from"):
            if row[field]:
                keys.append(("path", normalized_path(row[field])))
        for key in keys:
            if key in owners:
                j = owners[key]
                parents[root(i)] = root(j)
                links.append(dict(asset_ids=[ids[j], ids[i]], basis=list(key)))
            else:
                owners[key] = i
        split = row["split"]
        if split not in SPLITS | {"unassigned", ""}:
            issue("invalid_split", [ids[i]], f"Unsupported split: {split}")
        label = row["collision_label"]
        if label not in {"positive", "negative", "unknown", "uncertain"}:
            issue("invalid_label", [ids[i]], f"Unsupported label: {label}")
        if split in SPLITS:
            if label not in {"positive", "negative"}:
                issue("unreviewed_label_in_split", [ids[i]], "Unknown/uncertain is not a training label")
            if not dataset or not row["source_sequence"]:
                issue("missing_source_group", [ids[i]], "Assigned asset needs dataset and sequence provenance")
            if row["asset_role"] in {"annotation_preview", "rendered_author_demo"}:
                issue("overlay_in_split", [ids[i]], "Author overlays must not be model input")
        onset, end = row["onset_s"], row["end_s"]
        if label == "negative" and (onset or end):
            issue("negative_has_event_time", [ids[i]], "Negative assets must have blank onset/end")
        if bool(onset) != bool(end):
            issue("incomplete_event_time", [ids[i]], "Onset and end must both be present or both blank")
        if onset and end:
            try:
                start, stop = float(onset), float(end)
                if not (math.isfinite(start) and math.isfinite(stop) and 0 <= start <= stop):
                    raise ValueError
            except ValueError:
                issue("invalid_event_time", [ids[i]], "Expected finite 0 <= onset <= end")
            if row["fps_status"] != "verified_source":
                issue("unverified_event_seconds", [ids[i]], "Render/display FPS cannot certify source timing")

    components = defaultdict(list)
    for i in range(len(rows)):
        components[root(i)].append(i)
    groups = []
    for members in components.values():
        group_ids = sorted(ids[i] for i in members)
        assigned = sorted({rows[i]["split"] for i in members} & SPLITS)
        if len(assigned) > 1:
            issue("split_leakage", group_ids, f"Connected assets cross splits: {assigned}")
        groups.append(dict(asset_ids=group_ids, assigned_splits=assigned))
    # Count source events/sequences, never previews/derivatives as new samples.
    events = {(r["source_dataset"], r["source_event_id"]) for r in rows
              if r["collision_label"] == "positive" and r["source_event_id"]}
    negatives = {(r["source_dataset"], r["source_sequence"]) for r in rows
                 if r["collision_label"] == "negative" and r["source_sequence"]}
    return dict(asset_count=len(rows), known_positive_events=len(events),
                known_negative_sequences=len(negatives),
                assigned_asset_count=sum(r["split"] in SPLITS for r in rows),
                unassigned_asset_count=sum(r["split"] in {"", "unassigned"} for r in rows),
                missing_camera_count=sum(not r["camera_id"] for r in rows),
                metadata_consistent=not issues, issues=issues,
                groups=sorted(groups, key=lambda g: g["asset_ids"]), links=links,
                near_duplicate_media_check_performed=False,
                independent_groups_verified=False)
