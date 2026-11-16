"""Cache quan sát theo frame; không nội suy bbox hoặc tạo nhãn va chạm."""

from __future__ import annotations

import math
from pathlib import Path


def reserve_outputs(folder: Path, stem: str) -> dict[str, Path]:
    """Giữ độc quyền tên MP4/cache/report; bảo toàn output và file dở cũ."""
    folder.mkdir(parents=True, exist_ok=True)
    counter = 1
    while True:
        name = stem if counter == 1 else f"{stem}_{counter}"
        paths = dict(video=folder / f"{name}.mp4", frames=folder / f"{name}.frames.jsonl",
                     report=folder / f"{name}.run.json", partial=folder / f"{name}.frames.part.jsonl",
                     lock=folder / f".{name}.lock")
        if any(p.exists() for p in paths.values()):
            counter += 1
            continue
        try:
            with paths["lock"].open("x", encoding="utf-8") as stream:
                stream.write("inference output reservation\n")
        except FileExistsError:
            counter += 1
            continue
        if any(p.exists() for k, p in paths.items() if k != "lock"):
            paths["lock"].unlink()
            counter += 1
            continue
        return paths


def observations(result, names: dict, width: int, height: int) -> list[dict]:
    """Chuyển Results.boxes thành số Python; track ID khác GT ID."""
    boxes = result.boxes
    if boxes is None:
        return []
    xyxy, classes = boxes.xyxy.cpu().tolist(), boxes.cls.cpu().tolist()
    confidence = boxes.conf.cpu().tolist()
    ids = boxes.id.cpu().tolist() if boxes.id is not None else [None] * len(xyxy)
    if not len(xyxy) == len(classes) == len(confidence) == len(ids):
        raise ValueError("Result box arrays differ in length")
    rows = []
    for box, class_id, score, track_id in zip(xyxy, classes, confidence, ids):
        if len(box) != 4 or not all(math.isfinite(v) for v in box):
            raise ValueError("Invalid box coordinates")
        x1, y1, x2, y2 = box
        if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
            raise ValueError("Box outside image or zero area; no silent clipping")
        if not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError("Invalid observation confidence")
        if not math.isfinite(class_id) or class_id != int(class_id):
            raise ValueError("Invalid class ID")
        if track_id is not None and (not math.isfinite(track_id) or track_id < 0 or track_id != int(track_id)):
            raise ValueError("Invalid track ID")
        rows.append(dict(bbox_xyxy=box, bbox_cxcywh_norm=[(x1+x2)/(2*width), (y1+y2)/(2*height),
                         (x2-x1)/width, (y2-y1)/height], class_id=int(class_id),
                         class_name=names[int(class_id)], confidence=score,
                         track_id=int(track_id) if track_id is not None else None, missing_mask=0))
    return rows


class FrameCache:
    """Giữ video clock riêng với source seconds chưa xác minh.

    Missing entry chỉ có ID/gap/mask. Tuổi là số lần ID được trả về, không
    phải tuổi GT hoặc chứng nhận tracker giữ đúng danh tính.
    """

    def __init__(self, fps: float, timing_status="unknown", max_gap_frames=30):
        if not math.isfinite(fps) or fps <= 0 or max_gap_frames < 0:
            raise ValueError("Invalid FPS or export gap limit")
        if timing_status not in {"unknown", "presentation_only", "verified_source"}:
            raise ValueError("Invalid timing status")
        self.fps, self.timing_status, self.max_gap = fps, timing_status, max_gap_frames
        self.next_frame, self.last_time, self.tracks = 0, None, {}
        self.observation_count, self.empty_frames, self.fallback_timestamps = 0, 0, 0

    def record(self, frame_index: int, pts_ms: float, objects: list[dict]) -> dict:
        if frame_index != self.next_frame:
            raise ValueError("Frames must be consecutive and zero-based")
        time_s, origin = pts_ms / 1000, "container_pts"
        if not math.isfinite(time_s) or time_s < 0 or (self.last_time is not None and time_s <= self.last_time):
            if self.timing_status == "verified_source":
                raise ValueError("Invalid/nonmonotonic PTS on verified source; no invented seconds")
            time_s, origin = frame_index / self.fps, "frame_index_over_container_fps"
            if self.last_time is not None and time_s <= self.last_time:
                raise ValueError("Cannot construct a monotonic video clock")
            self.fallback_timestamps += 1
        current = [item["track_id"] for item in objects if item["track_id"] is not None]
        if len(set(current)) != len(current):
            raise ValueError("Duplicate track ID in one frame")
        objects = [dict(item) for item in objects]
        for item in objects:
            track_id = item["track_id"]
            if track_id is not None:
                previous = self.tracks.get(track_id)
                count = previous["observations"] + 1 if previous else 1
                self.tracks[track_id] = dict(last_frame=frame_index, observations=count)
                item["track_age_observations"] = count
            else:
                item["track_age_observations"] = None
        missing, expired = [], []
        for track_id, state in list(self.tracks.items()):
            gap = frame_index - state["last_frame"]
            if gap > self.max_gap:
                expired.append(track_id)
                del self.tracks[track_id]
            elif gap:
                missing.append(dict(track_id=track_id, missing_mask=1, gap_frames=gap,
                                    last_observed_frame=state["last_frame"]))
        self.last_time, self.next_frame = time_s, frame_index + 1
        self.observation_count += len(objects)
        self.empty_frames += not objects
        return dict(frame_index=frame_index, video_time_s=time_s, timestamp_origin=origin,
                    source_time_s=time_s if self.timing_status == "verified_source" else None,
                    timing_status=self.timing_status, observations=objects,
                    missing_tracks=sorted(missing, key=lambda r: r["track_id"]),
                    expired_track_ids=sorted(expired))
