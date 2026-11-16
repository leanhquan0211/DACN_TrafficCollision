# Chạy và trình diễn Traffic Lab

> **Xem trực tuyến:** <https://minhquan0500.github.io/DACN_TrafficCollision/>. Bản GitHub Pages phát lại hai clip mẫu đã xử lý, xem từng frame/ID và ảnh/clip cảnh báo. Không cần máy phát triển bật; không phân tích upload mới trên web tĩnh. [Chi tiết và cách cập nhật](GITHUB_PAGES.md). Phần bên dưới hướng dẫn bản Python chạy suy luận thật.

> **Bản hiện tại cuối16/11:** chế độ **Phát hiện va chạm · Thử nghiệm** mặc định, có ảnh/clip/Events JSON và chạy trên MP4 upload. CADP local mới nhất cảnh báo108 sau thayNMS (snapshot cũ109). Nhãn xe có lịch sử ID/“chưa rõ loại”, vẫn giữ dự đoán YOLO thô; [cách xem và giới hạn](VEHICLE_LABEL_FIX.md). [Cấu hình/lịch sử cảnh báo](COLLISION_DETECTION.md). Pages và bộ Word/PDF/ZIP đã tạo trước lượt nhận dạng mới giữ là snapshot lịch sử, chưa tái xuất.

## Chạy trên máy hiện tại

Từ thư mục gốc, chạy:

```bash
bash demo.sh
```

Mở <http://127.0.0.1:8765>. Muốn tự mở trình duyệt/cổng khác:

```bash
.venv/bin/python -B scripts/run_demo.py --port 8766
```

Máy chủ chỉ lắng nghe 127.0.0.1. Giữ terminal chạy; Ctrl+C để dừng. Nếu cổng bận, dùng `--port 8766`. Bản demo chạy cục bộ, không cần đăng ký dịch vụ hoặc Internet sau khi cài thư viện và có các asset.

## Dựng trên máy khác

Gói `delivery/TrafficLab_demo_2026-11-14.zip` là snapshot gồm source, trọng số, hai video sạch và bốn bộ output đã kiểm. Không chuyển `.venv` giữa máy. Gói không bao gồm toàn bộ dữ liệu nghiên cứu hoặc bộ cài offline Python/PyTorch.

Linux/macOS có Python 3.12:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
# Lệnh CPU dưới đây đã dùng trên Linux x86_64; hệ khác xem GETTING_STARTED.
.venv/bin/python -m pip install torch==2.11.0 torchvision==0.26.0 --index-url https://download.pytorch.org/whl/cpu
.venv/bin/python -m pip install -r requirements.txt -r requirements-data.txt
bash demo.sh
```

Windows (PowerShell, chưa kiểm thực tế trên Windows):

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install torch==2.11.0 torchvision==0.26.0 --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-data.txt
.\.venv\Scripts\python.exe -B scripts/run_demo.py --open
```

`run_demo.py` tìm FFmpeg hệ thống; nếu thiếu, dùng executable từ `imageio-ffmpeg` (symlink trên Linux, copy executable trên Windows). Nhánh Linux đã kiểm; Windows chưa kiểm trên máy thật. Nếu không tìm được encoder, cài FFmpeg vào PATH. Muốn chỉ xem kết quả, mở trực tiếp MP4 trong `outputs/` của gói, không cần cài Python.

Kiểm file gói trước khi chạy:

```bash
python3 scripts/verify_delivery.py .
```

Gói giữ nguyên report lịch sử với đường dẫn máy cũ. Dashboard tìm artifact qua catalog/đường dẫn cạnh report rồi **kiểm lại cùng hash**, không sửa report gốc và không bỏ qua mismatch. `check_project_assets.py` ở repo đầy đủ vẫn dùng để kiểm dữ liệu nghiên cứu, không dùng gói demo để tuyên bố đã có cả dataset.

## Chức năng sử dụng

**Cảnh báo tự động:** chọn chế độ collision, mở CADP và bấm **Xem thời điểm cảnh báo**. Khung đỏ và event do luật tạo, tách khỏi ô nhận xét thủ công. Mở ảnh/clip để kiểm; Events JSON có frame, ID tạm, dấu hiệu và trạng thái cần review. Chuyển DETRAC thấy không có cảnh báo trên mẫu đó. Dùng **Chạy lại trên CPU** hoặc upload MP4 để chạy mới. Luật chỉ xét xe đủ chất lượng/kích thước; chưa có cảnh báo không có nghĩa video chắc chắn không va chạm.

**Bổ sung 16/11 — tải video khác:** chọn MP4 H.264 trong mục “Hoặc tải video từ máy”, chọn detection/tracking và bấm “Tải lên & phân tích”. Giới hạn100MiB/2phút/FullHD, nên720p. Đã thử video cao tốc mới đủ250frame; [hướng dẫn, nguồn và số đo](EXTERNAL_VIDEO_DEMO.md). Video tải lên/kết quả được giữ cục bộ sau restart, không tự thành dữ liệu huấn luyện hoặc nhãn tai nạn. Gói ZIP ngày14/11 chưa chứa tính năng này.

1. Chọn CADP hoặc DETRAC, chế độ detection/tracking. Kết quả sẵn chỉ hiện khi đã kiểm input/weights/MP4/JSONL/hash và giải mã đủ frame.
2. Bấm Phát để xem hai video cùng nhau; thanh timeline và nút ‹/› để rà frame. Điểm bảng quan sát là **confidence của phương tiện**, không là xác suất tai nạn. ID là mã tạm trong lượt chạy.
3. “Chạy lại trên CPU” chạy YOLO thật trong tiến trình riêng; mỗi lần tạo thư mục riêng ở `outputs/demo_app/runs/<job_id>/`. Một job mỗi lúc. Có trạng thái xử lý/kiểm/hoàn tất hoặc lỗi; giữ log khi lỗi.
4. Tạm dừng, nhập nhận xét và “Lưu mốc & ảnh frame”. Ghi JSON + ảnh **đầu vào sạch** tại `outputs/demo_app/reviews/<run_id>/`. Không thay nhãn, không tự thêm vào tập train, không tạo cảnh báo tự động. Review gắn hash của input/report/ảnh.
5. Tải MP4, JSONL, report; mở Review JSON và ảnh để kiểm bằng chứng. Sau khi khởi động lại, app nhận lại các run mẫu mới đã kiểm và review đã lưu.

## Kịch bản bảo vệ 5 phút

- 0:00–0:30: giới thiệu bài toán CCTV xe–xe và phạm vi bản hiện tại.
- 0:30–1:30: CADP đầu vào/kết quả, đi từng frame, trình bày ID/class. Interval 96–130 là **nhãn người rà**, không đầu ra thuật toán tai nạn.
- 1:30–2:30: chạy lại CPU, chỉ report lượt mới và giải thích tốc độ offline.
- 2:30–3:30: DETRAC cảnh âm, giải thích nhiều xe/chồng bbox chưa đủ kết luận tai nạn.
- 3:30–5:00: lưu nhận xét/ảnh, tải report, nêu lỗi xe buýt đổi class và các thực nghiệm còn thiếu.

## Giới hạn phải nói rõ

Dashboard có **B2 luật/FSM thử nghiệm**, chưa tích hợp model B0 hoặc verifier MLP/GRU. [B0 STTAD](B0_FEASIBILITY.md) bỏ sót12/12 vùng validation tại conf0,25 nên chưa dùng cho cảnh báo. CADP/DETRAC đã dùng phát triển rule, chưa event precision/recall/F1/FAR/hour trên test độc lập, IDF1 hoặc benchmark streaming/GPU. CADP dùng20FPS **trình chiếu**: alert109=5,45giây video, chưa biết giây nguồn. Không suy tốc độ vật lý từ đó. Pilot nhỏ, lọc bbox xa có thể bỏ sót; không chia frame ngẫu nhiên làm train/test và không gọi một case đúng là accuracy100%.

## Kiểm thử và tái tạo gói

```bash
.venv/bin/python -B -m unittest discover -s tests -v
# Khi server đang chạy; tùy chọn hai flag sau thực sự tạo output/review kiểm thử:
.venv/bin/python -B scripts/check_demo.py --run-inference --save-review --output /tmp/demo-check.json
# Tạo Word/slide cần requirements-delivery; dashboard không cần chúng.
.venv/bin/python -m pip install -r requirements-delivery.txt
.venv/bin/python -B scripts/build_delivery_docs.py
.venv/bin/python -B scripts/package_delivery.py
```

Ảnh chụp màn hình và kiểm HTTP của lần bàn giao ở `outputs/audits/delivery_2026-11-14/`. Gói source không chứa hồ sơ trình duyệt, `.venv`, token phiên hoặc toàn bộ outputs.
