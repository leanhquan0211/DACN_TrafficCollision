"""Kiểm tra nhanh video trước khi chạy YOLO.

Đầu vào: đường dẫn một file video. Đầu ra: FPS, kích thước, số frame,
thời lượng và khả năng đọc frame đầu trên terminal; không tạo video mới.
Chạy riêng khi cần kiểm tra file nguồn, hoặc để run_all.py gọi đầu tiên.
"""

import argparse
import sys
from pathlib import Path


def main() -> int:
    sys.stdout.reconfigure(errors="backslashreplace")
    sys.stderr.reconfigure(errors="backslashreplace")
    parser = argparse.ArgumentParser(description="Inspect a video and test whether its first frame is readable")
    parser.add_argument("video", type=Path)
    args = parser.parse_args()
    path = args.video.expanduser().resolve()
    if not path.is_file():
        print(f"Error: video does not exist: {path}", file=sys.stderr)
        return 1
    try:
        import cv2
    except ImportError:
        print("Error: OpenCV is not installed in this Python environment", file=sys.stderr)
        return 1
    # VideoCapture mở luồng giải mã; chưa nạp toàn bộ video vào RAM.
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        print(f"Error: cannot open video: {path}", file=sys.stderr)
        return 1
    try:
        # Metadata cho biết nhịp và kích thước dự kiến; read() kiểm tra thực sự
        # giải mã được một frame, là mảng ảnh BGR có dạng (cao, rộng, 3).
        fps = cap.get(cv2.CAP_PROP_FPS)
        frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        ok, frame = cap.read()
        if not ok or frame is None:
            print(f"Error: cannot read first frame: {path}", file=sys.stderr)
            return 1
        print(f"Video: {path}")
        print(f"Resolution: {int(width)}x{int(height)}" if width > 0 and height > 0 else "Resolution: unknown")
        print(f"FPS: {fps:.3f}" if 0 < fps < 1000 else "FPS: unknown")
        print(f"Frames: {int(frames)}" if frames > 0 else "Frames: unknown")
        print(f"Duration: {frames/fps:.3f} seconds" if frames > 0 and 0 < fps < 1000 else "Duration: unknown")
        print("First frame: readable")
        return 0
    finally:
        # Giải phóng file video kể cả khi frame đầu bị lỗi.
        cap.release()


if __name__ == "__main__":
    raise SystemExit(main())
