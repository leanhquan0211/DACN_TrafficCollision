"""Xử lý chung để biến video gốc thành video có bbox hoặc bbox + track ID.

Đầu vào: args từ run_detection.py/run_tracking.py và cờ tracking.
Đầu ra: đường dẫn MP4 đã vẽ chú thích trong outputs/<tên-video>/.
Không chạy trực tiếp file này; hai script trên gọi arguments() và run().
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path


# Tên class được đối chiếu với model.names, nên chỉ giữ kết quả thuộc nhóm xe.
VEHICLE_NAMES = {"bicycle", "car", "motorcycle", "motorbike", "bus", "truck"}


def arguments(kind: str) -> argparse.ArgumentParser:
    """Tạo cùng bộ tham số dòng lệnh cho detection và tracking."""
    parser = argparse.ArgumentParser(description=f"Run YOLOv8n {kind} on one video")
    parser.add_argument("video", type=Path, help="Path to an input video")
    parser.add_argument("--device", default="auto", help="auto, cpu, or CUDA index such as 0")
    parser.add_argument("--imgsz", type=int, default=640, help="Inference image size")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"), help="Root directory; results go into a subfolder named after the video")
    parser.add_argument("--model", type=Path, default=Path("yolov8n.pt"), help="YOLOv8n weights")
    return parser


def run(args: argparse.Namespace, tracking: bool) -> Path:
    """Đọc từng frame, suy luận, vẽ và ghi MP4; trả về đường dẫn file kết quả."""
    # Kiểm tra đường dẫn và tham số trước khi nạp thư viện nặng: --help/lỗi
    # thiếu video vẫn hoạt động kể cả khi môi trường CV chưa cài đủ.
    source = args.video.expanduser().resolve()
    if not source.is_file():
        raise ValueError(f"Video does not exist: {source}")
    if args.imgsz <= 0:
        raise ValueError("--imgsz must be positive")
    # Ultralytics lưu cấu hình trong project; các import này chỉ cần khi thực sự
    # xử lý video. cv2 đọc frame, torch chọn GPU, YOLO suy luận, numpy đổi ảnh.
    os.environ.setdefault("YOLO_CONFIG_DIR", str(Path(__file__).resolve().parents[1] / "configs" / "ultralytics"))
    try:
        import cv2
        import torch
        from ultralytics import YOLO
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("Install packages in .venv before running video inference") from exc

    # args.device="auto" ưu tiên GPU đầu tiên nếu PyTorch CUDA sẵn sàng.
    # Dữ liệu sau bước này là chuỗi "0" (GPU) hoặc "cpu" đưa vào YOLO.
    device = ("0" if torch.cuda.is_available() else "cpu") if args.device == "auto" else args.device
    if device != "cpu" and not torch.cuda.is_available():
        raise RuntimeError("CUDA device requested, but PyTorch cannot use CUDA")

    # Nạp checkpoint YOLO: yolov8n.pt hiện học các class COCO như car/bus/truck,
    # chưa có class accident. Chỉ trọng số yolov8n.pt được phép tải ngầm khi thiếu.
    model_path = args.model.expanduser()
    if not model_path.is_file() and model_path.name != "yolov8n.pt":
        raise FileNotFoundError(f"Model does not exist: {model_path}")
    try:
        model = YOLO(str(model_path))
    except Exception as exc:
        raise RuntimeError(f"Cannot load YOLOv8n model: {exc}") from exc
    # model.names ánh xạ class ID -> tên. Lọc thành danh sách class ID xe để
    # YOLO chỉ trả bbox/class/conf của nhóm này, không trả mọi class COCO.
    names = model.names
    if isinstance(names, list):
        names = dict(enumerate(names))
    classes = [int(i) for i, name in names.items() if str(name).lower() in VEHICLE_NAMES]
    if not classes:
        raise RuntimeError(f"Model has no supported vehicle classes. Model classes: {names}")
    print("Vehicle classes:", ", ".join(f"{i}={names[i]}" for i in classes), flush=True)

    # VideoCapture mở luồng giải mã. Frame sẽ được lấy lần lượt, không giữ cả
    # video trong RAM; read() trả (ok, ảnh BGR dạng mảng cao x rộng x 3).
    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        raise RuntimeError(f"Cannot open video: {source}")
    encoder = None
    output = None
    try:
        # Đọc trước frame đầu để biết kích thước ảnh thật và kiểm tra video đọc
        # được. FPS nguồn sẽ được dùng lại để video kết quả chạy đúng nhịp.
        ok, frame = capture.read()
        if not ok or frame is None:
            raise RuntimeError(f"Cannot read first frame: {source}")
        height, width = frame.shape[:2]
        fps = capture.get(cv2.CAP_PROP_FPS)
        if not 0 < fps < 1000:
            raise RuntimeError("Video FPS is unavailable or invalid; cannot write timed output")
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg is None:
            raise RuntimeError("FFmpeg is required to save H.264 MP4; install it and add ffmpeg to PATH")
        # Gom hai loại kết quả theo tên video nguồn để dễ so sánh; chạy lại thì
        # dùng hậu tố _2, _3... thay vì ghi đè kết quả trước.
        out_dir = args.output_dir.expanduser().resolve() / source.stem
        out_dir.mkdir(parents=True, exist_ok=True)
        stem = f"{source.stem}_{'tracking' if tracking else 'detection'}"
        output = out_dir / f"{stem}.mp4"
        counter = 2
        while output.exists() or output == source:
            output = out_dir / f"{stem}_{counter}.mp4"
            counter += 1
        # Ghi vào file .part.mp4 trước; chỉ đổi tên thành MP4 cuối cùng khi
        # FFmpeg thành công, tránh để một video xuất dở trông như kết quả hợp lệ.
        temp_output = output.with_name(output.stem + ".part" + output.suffix)
        if temp_output.exists():
            try:
                temp_output.unlink()
            except OSError:
                pass
        # FFmpeg nhận từng ảnh BGR 24-bit qua stdin rồi mã hóa H.264/yuv420p.
        # Dữ liệu ra là MP4 mở được trong trình xem video của VS Code.
        print(f"Input: {source}", flush=True)
        print(f"Temporary output: {temp_output}", flush=True)
        print(f"Final output will be: {output}", flush=True)
        print(f"Using ffmpeg: {ffmpeg}", flush=True)
        command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-xerror", "-n",
             "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{width}x{height}",
             "-r", str(fps), "-i", "pipe:0", "-an", "-c:v", "libx264",
             "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
             "-movflags", "+faststart", "-f", "mp4", str(temp_output)]
        try:
            encoder = subprocess.Popen(command, stdin=subprocess.PIPE,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        except OSError as exc:
            raise RuntimeError(f"Cannot start FFmpeg: {exc}") from exc
        count = 0
        while ok and frame is not None:
            # Cùng ảnh frame BGR đi vào YOLO ở cả hai chế độ. predict() chỉ tìm
            # bbox xe ở frame hiện tại; track() gọi detector rồi ByteTrack theo
            # bytetrack.yaml để nối xe với frame trước và gán ID tạm.
            options = dict(device=device, imgsz=args.imgsz, classes=classes, verbose=False)
            if tracking:
                # persist=True giữ trạng thái tracker giữa các lần track(frame)
                # của CÙNG video. Mỗi lần run() tạo YOLO mới; nếu sau này tái dùng
                # cùng model cho video/camera khác, phải reset tracker hoặc tạo
                # model mới để ID/quỹ đạo cũ không lẫn sang video mới.
                results = model.track(frame, persist=True, tracker="bytetrack.yaml", **options)
            else:
                results = model.predict(frame, **options)
            # results[0].boxes chứa bbox (xyxy), class, confidence; chế độ
            # tracking có thể thêm boxes.id nếu tracker gán được ID. Code hiện
            # không tách các trường này ra: plot() tự đọc chúng và trả ảnh BGR
            # đã vẽ khung/nhãn/ID, vẫn có dạng cao x rộng x 3.
            img = results[0].plot()
            # FFmpeg cần dãy byte BGR liền mạch, không nhận trực tiếp ndarray.
            try:
                if isinstance(img, np.ndarray):
                    frame_bytes = np.ascontiguousarray(img).tobytes()
                else:
                    # Trường hợp thư viện trả ảnh dạng buffer khác ndarray.
                    frame_bytes = img.tobytes()
            except Exception as exc:
                raise RuntimeError(f"Cannot convert plotted frame to bytes: {exc}") from exc
            # Đưa byte của frame đã vẽ sang FFmpeg; lỗi encoder cần được báo
            # trước khi đọc frame kế tiếp để không tạo file đầu ra hỏng.
            if encoder.poll() is not None:
                error = encoder.stderr.read().decode(errors="replace").strip()
                raise RuntimeError(f"FFmpeg exited early (rc={encoder.poll()}): {error}")
            try:
                encoder.stdin.write(frame_bytes)
            except BrokenPipeError as exc:
                error = encoder.stderr.read().decode(errors="replace").strip()
                raise RuntimeError(f"FFmpeg could not write output: {error or exc}") from exc
            except OSError as exc:
                # Trên Windows, OSError(22) có thể là pipe lỗi; kèm stderr để chẩn đoán.
                error = encoder.stderr.read().decode(errors="replace").strip()
                raise RuntimeError(f"OS error writing to FFmpeg stdin: {exc}; stderr: {error}") from exc
            count += 1
            # Chỉ sau khi xử lý và ghi xong frame hiện tại mới đọc frame tiếp.
            # ByteTrack còn trạng thái trong model, còn ảnh cũ được thay thế.
            ok, frame = capture.read()
        # Hết frame: đóng pipe để FFmpeg nhận tín hiệu kết thúc, ghi phần cuối
        # của MP4 và trả mã lỗi/thành công trước khi đổi tên file tạm.
        encoder.stdin.close()
        encoder.stdin = None
        error = encoder.stderr.read().decode(errors="replace").strip()
        ret = encoder.wait()
        encoder.stderr.close()
        encoder = None
        if ret != 0:
            # Encoder lỗi thì bỏ file tạm chưa hoàn chỉnh.
            if temp_output.exists():
                try:
                    temp_output.unlink()
                except OSError:
                    pass
            raise RuntimeError(f"FFmpeg could not write output: {error or temp_output}")
        # Mã hóa xong mới công bố tên file MP4 cuối cùng.
        try:
            temp_output.replace(output)
        except Exception as exc:
            raise RuntimeError(f"Cannot finalize output file: {exc}") from exc
        # Báo số frame và file xuất; đây là kiểm tra luồng xử lý, không phải
        # số liệu độ chính xác phát hiện xe hay kết luận tai nạn.
        try:
            size = output.stat().st_size
        except OSError:
            size = None
        print(f"Processed {count} frames; saved: {output} (size={size})", flush=True)
        return output
    except Exception:
        if encoder is not None:
            if encoder.stdin is not None:
                try:
                    encoder.stdin.close()
                except OSError:
                    pass
            if encoder.poll() is None:
                encoder.terminate()
            encoder.wait()
            encoder.stderr.close()
        if output is not None and output.exists():
            try:
                output.unlink()
            except OSError:
                pass
        # Dọn file tạm còn sót để lần chạy sau không nhầm là kết quả.
        try:
            if 'temp_output' in locals() and temp_output.exists():
                temp_output.unlink()
        except OSError:
            pass
        raise
    finally:
        capture.release()
