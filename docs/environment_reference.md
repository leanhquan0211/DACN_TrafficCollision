# Môi trường tham chiếu của project

Tài liệu công khai chỉ ghi dependencies và cách kiểm lại. Log máy phát triển đầy đủ ở `logs/environment_check.md` được giữ cục bộ, bị ignore vì có đường dẫn/thông tin máy cá nhân.

## Dependencies đã dùng

| Thành phần | Phiên bản tham chiếu |
| --- | --- |
| Python | 3.12, 64-bit |
| PyTorch | 2.11.0; bản CUDA đã dùng có hậu tố `+cu128` |
| torchvision | 0.26.0; bản CUDA tương ứng `+cu128` |
| Ultralytics | 8.4.178 |
| lap | 0.5.13 |
| OpenCV | 5.0.0.93 |
| NumPy | 2.5.2 |

[requirements.txt](../requirements.txt) pin dependencies trực tiếp; [snapshot các package](../logs/requirements-installed.txt) chỉ chứa tên/phiên bản. Không đóng gói `.venv`, driver, CUDA Toolkit hoặc FFmpeg binary trong repo. CPU/CUDA chọn theo máy mới, rồi kiểm bằng script; không suy phần cứng của máy clone từ một log cũ.

## Kiểm lại trên máy đang dùng

Làm theo [hướng dẫn cài đặt](GETTING_STARTED.md), sau đó:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts/check_environment.py
ffmpeg -version
ffmpeg -hide_banner -encoders | Select-String libx264
```

`check_environment.py` có thể in thông tin/path thực tế của máy chạy. Giữ log thô ở local; khi cần đưa lên Git chỉ ghi kết luận liên quan và loại định danh máy/tên người dùng/đường dẫn riêng. Chưa cài thử một môi trường hoàn toàn mới không được ghi thành đã tái lập cài đặt.

## Kết quả chức năng lịch sử

Các nhật ký ghi lần thử video mẫu 279 frame và các lượt CADP/DETRAC chuẩn bị dữ liệu; [evidence nhỏ](evidence/README.md) ghi kết quả đọc lại/kiểm nhãn. Đó là kiểm chức năng, không phải benchmark độ chính xác va chạm hoặc tốc độ phần cứng. Trên máy mới phải chạy lại các kiểm tra phù hợp với dữ liệu đã phục hồi.
