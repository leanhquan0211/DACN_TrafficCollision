"""Tiện ích chuẩn bị dữ liệu: đọc media, tính hash và ghi MP4 H.264.

Các script prepare_* truyền đường dẫn/frame vào đây; đầu ra là báo cáo hoặc
video mới. Không chạy trực tiếp; không sửa file nguồn hay ghi đè kết quả cũ.
"""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


def sha256_file(path: Path) -> str:
    """Đọc theo khối để nhận diện file mà không nạp cả ZIP/video vào RAM."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_b0_verified_origins(rows: list[dict]) -> None:
    """Chặn frame chưa có căn cứ âm/dương khỏi release B0 đã rà.

    Tên nguồn nhãn được khóa theo policy; việc file thiếu TXT hoặc ở trước
    impact không tự đủ để nhận empty label. Hàm này không tự xác minh nội
    dung review hoặc hash: các bước lập release và export phải kiểm riêng.
    """
    allowed={
        "positive":{"author_accident_impact_region"},
        "negative":{"derived_author_preimpact_assistant_frame_review",
                    "author_normal_folder_clip_label","user_full_sequence_review"},
    }
    for row in rows:
        if row.get("label_origin") not in allowed.get(row.get("collision_label"),set()):
            raise ValueError("Unverified B0 label origin: "+str(row.get("label_origin")))


def unique_path(path: Path) -> Path:
    """Thêm hậu tố nếu tên kết quả đã tồn tại; giữ nguyên mọi kết quả cũ."""
    candidate = path
    index = 2
    while candidate.exists():
        candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
        index += 1
    return candidate


def new_audit_dir(root: Path, name: str) -> Path:
    target = unique_path(root / name)
    target.mkdir(parents=True, exist_ok=False)
    return target


def save_json(path: Path, value: object) -> None:
    """Chỉ tạo file báo cáo mới; không vô tình ghi đè báo cáo trước."""
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def save_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def probe_video(path: Path) -> dict:
    """Giải mã hết video để so số frame thực với metadata, không đo accuracy."""
    import cv2

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        cap.release()
        raise ValueError(f"Cannot open video: {path}")
    try:
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        reported = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        count = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if frame.shape[:2] != (height, width):
                raise ValueError(f"Changing frame size: {path}")
            count += 1
        if count == 0 or (reported > 0 and count != reported):
            raise ValueError(f"Incomplete decode: {path}: {count}/{reported}")
        if not 0 < fps < 1000:
            raise ValueError(f"Invalid FPS: {path}: {fps}")
        return dict(width_px=width, height_px=height, fps=fps,
                    frame_count=reported, decoded_frames=count,
                    duration_s=count / fps, size_bytes=path.stat().st_size,
                    sha256=sha256_file(path))
    finally:
        cap.release()


class H264Writer:
    """Nhận từng ảnh BGR và đưa qua FFmpeg để MP4 xem được trong VS Code."""

    def __init__(self, output: Path, width: int, height: int, fps: float):
        if output.exists():
            raise FileExistsError(output)
        if width <= 0 or height <= 0 or width % 2 or height % 2 or not 0 < fps < 1000:
            raise ValueError("H.264/yuv420p needs positive even dimensions and valid FPS")
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg is None:
            raise RuntimeError("FFmpeg is not on PATH")
        output.parent.mkdir(parents=True, exist_ok=True)
        self.output = output
        self.width, self.height = width, height
        self.temp = unique_path(output.with_name(output.stem + ".part.mp4"))
        self.errors = tempfile.TemporaryFile()
        self.process = None
        self.count = 0
        try:
            # stderr nằm trong file tạm để encoder không bị nghẽn pipe khi báo lỗi.
            self.process = subprocess.Popen([
                ffmpeg, "-hide_banner", "-loglevel", "error", "-xerror", "-n",
                "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{width}x{height}",
                "-r", str(fps), "-i", "pipe:0", "-an", "-c:v", "libx264",
                "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
                "-movflags", "+faststart", str(self.temp)],
                stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=self.errors)
        except Exception:
            self.errors.close()
            raise

    def __enter__(self):
        return self

    def write(self, frame) -> None:
        import numpy as np

        if frame.shape != (self.height, self.width, 3) or frame.dtype != np.uint8:
            raise ValueError("Unexpected BGR frame shape/dtype")
        self.process.stdin.write(np.ascontiguousarray(frame).tobytes())
        self.count += 1

    def __exit__(self, exc_type, exc, traceback):
        try:
            try:
                self.process.stdin.close()
            except OSError:
                if exc_type is None:
                    raise
            if exc_type is not None and self.process.poll() is None:
                self.process.terminate()
            ret = self.process.wait()
            self.errors.seek(0)
            error = self.errors.read().decode(errors="replace").strip()
            if exc_type is None:
                if ret or self.count == 0:
                    raise RuntimeError(f"FFmpeg failed: {error}")
                if self.output.exists():
                    raise FileExistsError(self.output)
                self.temp.rename(self.output)
        finally:
            if self.process.poll() is None:
                self.process.terminate()
                self.process.wait()
            self.errors.close()
            if self.temp.exists():
                self.temp.unlink()


def clip_video(source: Path, output: Path, seconds: float) -> dict:
    """Cắt từ đầu MP4 đã ghép, giữ FPS và ghi số frame để truy ngược chuỗi gốc."""
    import cv2

    if not 0 < seconds <= 30:
        raise ValueError("Smoke clip must be in (0, 30] seconds")
    info = probe_video(source)
    limit = min(info["decoded_frames"], int(seconds * info["fps"]))
    if limit < 1:
        raise ValueError("Clip duration is shorter than one frame")
    cap = cv2.VideoCapture(str(source))
    try:
        with H264Writer(output, info["width_px"], info["height_px"], info["fps"]) as writer:
            for _ in range(limit):
                ok, frame = cap.read()
                if not ok:
                    raise ValueError("Cannot decode requested clip")
                writer.write(frame)
    finally:
        cap.release()
    result = probe_video(output)
    if result["decoded_frames"] != limit:
        raise ValueError("Clip frame count mismatch")
    return result
