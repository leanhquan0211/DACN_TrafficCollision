"""Tạo video có khung bao quanh phương tiện, chưa kết luận tai nạn.

Đầu vào: video và tùy chọn dòng lệnh; mặc định dùng yolov8n.pt pretrained.
Đầu ra: MP4 detection trong --output-dir/<tên-video>/ (mặc định outputs/).
Chạy riêng khi chỉ cần xem xe YOLO tìm được trên từng frame.
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
        args = arguments("detection").parse_args()
        print(f"Starting detection: {args.video} -> output dir: {args.output_dir}", flush=True)
        # tracking=False chọn model.predict: mỗi frame có bbox/class/conf,
        # không có ID liên tục giữa các frame. run() trả về đường dẫn MP4 đã lưu.
        output = run(args, tracking=False)
        print(f"Detection complete. Saved: {output}", flush=True)
    except (OSError, RuntimeError, ValueError) as exc:
        traceback.print_exc()
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
