"""Tạo video có bbox phương tiện và ID theo dõi của ByteTrack.

Đầu vào: video và tùy chọn dòng lệnh; mặc định dùng yolov8n.pt pretrained.
Đầu ra: MP4 tracking trong --output-dir/<tên-video>/ (mặc định outputs/).
Chạy riêng khi cần xem cùng một xe được nối qua các frame như thế nào.
"""

import sys
import traceback
from pathlib import Path

# Cho phép chạy trực tiếp từ scripts/ nhưng vẫn import được phần xử lý chung ở src/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.video_pipeline import arguments, run


if __name__ == "__main__":
    sys.stdout.reconfigure(errors="backslashreplace")
    sys.stderr.reconfigure(errors="backslashreplace")
    try:
        args = arguments("tracking").parse_args()
        print(f"Starting tracking: {args.video} -> output dir: {args.output_dir}", flush=True)
        # tracking=True chọn model.track với bytetrack.yaml trong run().
        # ID chỉ là mã tạm trong video, không phải biển số hay danh tính thật.
        output = run(args, tracking=True)
        print(f"Tracking complete. Saved: {output}", flush=True)
    except (OSError, RuntimeError, ValueError) as exc:
        traceback.print_exc()
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
