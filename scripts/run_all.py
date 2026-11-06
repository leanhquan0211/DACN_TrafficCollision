"""Chạy toàn bộ bước thử video từ một lệnh.

Đầu vào: đường dẫn video và các tùy chọn model, thiết bị, kích thước ảnh, thư mục xuất.
Đầu ra: thông tin video trên terminal và hai MP4 trong --output-dir
(mặc định là outputs/).
Chạy file này khi muốn kiểm tra video rồi tạo cả hai kết quả để so sánh.
"""

import argparse
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.storage_paths import output_path


def main() -> int:
    sys.stdout.reconfigure(errors="backslashreplace")
    sys.stderr.reconfigure(errors="backslashreplace")
    parser = argparse.ArgumentParser(description="Inspect, detect and track one video with YOLOv8n")
    parser.add_argument("video", type=Path, help="Path to an input video")
    parser.add_argument("--device", default="auto", help="auto, cpu, or CUDA index such as 0")
    parser.add_argument("--imgsz", type=int, default=640, help="Inference image size")
    parser.add_argument("--output-dir", type=Path, default=output_path(Path(__file__).resolve().parents[1], 'system_evidence', 'v002_vehicle_preview'), help="Canonical run directory for per-video result folders")
    parser.add_argument("--model", type=Path, default=Path("yolov8n.pt"), help="YOLOv8n weights")
    args = parser.parse_args()

    # Chuyển đường dẫn đầu vào thành đường dẫn tuyệt đối để cả ba tiến trình con
    # cùng đọc đúng một video, dù chúng chạy từ vị trí nào.
    video = args.video.expanduser().resolve()
    scripts_dir = Path(__file__).resolve().parent
    # Mỗi script chạy tuần tự trong một Python riêng: inspect chỉ đọc metadata,
    # detection và tracking đều đọc lại video gốc, không nhận frame từ bước trước.
    steps = ("inspect_video.py", "run_detection.py", "run_tracking.py")
    for name in steps:
        command = [sys.executable, str(scripts_dir / name), str(video)]
        if name != "inspect_video.py":
            command.extend(("--device", args.device, "--imgsz", str(args.imgsz),
                            "--output-dir", str(args.output_dir), "--model", str(args.model)))
        print(f"\n=== {name} ===", flush=True)
        # Dừng ngay nếu một bước lỗi để không coi hai MP4 chưa đủ là kết quả hoàn chỉnh.
        try:
            result = subprocess.run(command, check=False)
        except OSError as exc:
            print(f"Error: cannot start {name}: {exc}", file=sys.stderr)
            return 1
        if result.returncode != 0:
            print(f"Stopped: {name} failed (exit {result.returncode})", file=sys.stderr)
            return result.returncode
    print(f"\nResults: {args.output_dir.expanduser().resolve() / video.stem}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
