"""Kiểm tra môi trường Python trước khi chạy video hoặc huấn luyện sau này.

Đầu vào: không cần video; đọc Python, gói đã cài và GPU của máy hiện tại.
Đầu ra: phiên bản và kết quả phép tính CUDA nhỏ trên terminal, không tạo MP4.
Chạy khi mới cài môi trường hoặc khi nghi ngờ PyTorch không dùng được GPU.
"""

import argparse
import importlib
import os
import platform
import struct
import sys
from pathlib import Path


def main() -> int:
    argparse.ArgumentParser(description="Check Python packages and run a small CUDA tensor calculation").parse_args()
    sys.stdout.reconfigure(errors="backslashreplace")
    # Ultralytics ghi cấu hình vào thư mục project để dễ chạy trong môi trường này.
    os.environ.setdefault("YOLO_CONFIG_DIR", str(Path(__file__).resolve().parents[1] / "configs" / "ultralytics"))
    print(f"Python: {sys.version.split()[0]} ({struct.calcsize('P') * 8}-bit)")
    print(f"Interpreter: {sys.executable}")
    print(f"OS: {platform.platform()}")
    # Thử import các gói mà pipeline dùng; tên phiên bản cho biết interpreter
    # hiện tại có đúng môi trường .venv đã cài phụ thuộc hay không.
    for name in ("torch", "torchvision", "ultralytics", "cv2"):
        try:
            module = importlib.import_module(name)
            print(f"{name}: {getattr(module, '__version__', 'installed')}")
        except ImportError as exc:
            print(f"{name}: MISSING ({exc})")
    try:
        import torch
    except ImportError:
        return 1
    print(f"PyTorch CUDA runtime: {torch.version.cuda or 'none (CPU build)'}")
    available = torch.cuda.is_available()
    print(f"torch.cuda.is_available(): {available}")
    if available:
        # Phép tính thật trên GPU xác nhận PyTorch CUDA hoạt động, không chỉ
        # xác nhận máy có tên GPU; đây chưa phải benchmark tốc độ YOLO.
        print(f"PyTorch GPU: {torch.cuda.get_device_name(0)}")
        tensor = torch.tensor([1.0, 2.0], device="cuda")
        print(f"CUDA tensor test: {(tensor * 2).sum().item()} (expected 6.0)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
