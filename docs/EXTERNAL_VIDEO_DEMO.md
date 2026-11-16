# Thử tải và phân tích video mới — 16/11/2026

Theo yêu cầu người dùng, đã tìm một video giao thông ngoài CADP/DETRAC, tải qua giao diện và chạy YOLOv8n/ByteTrack thật. Không huấn luyện lại model hoặc thay dữ liệu nghiên cứu.

## Xem và thử trên máy hiện tại

Mở <http://127.0.0.1:8765>; nếu server chưa chạy, dùng `bash demo.sh`. Trong danh sách video, chọn `roboflow_vehicles_10s.mp4` để xem kết quả đã lưu. Có thể tải trực tiếp [MP4 kết quả của lượt kiểm](../outputs/demo_app/runs/6113376e6e85471f9a16fe0daf0d6a74/video/video_tracking.mp4) hoặc xem [ảnh giao diện](../outputs/audits/external_video_2026-11-16/uploaded_video_dashboard.png).

Muốn thử video của mình:

1. Bấm chọn file ở **Hoặc tải video từ máy**.
2. Chọn phương pháp detection hoặc tracking, bấm **Tải lên & phân tích**.
3. Chờ xử lý và kiểm MP4/cache/hash; sau đó phát hai video, rà từng frame, tải kết quả hoặc lưu nhận xét như các mẫu cũ.

Ưu tiên video gốc chưa có khung/ID vẽ sẵn. Nếu tải bản đã được detector khác vẽ, các chữ/khung cũ vẫn nằm trên ảnh đầu vào; không dùng bản đó để đo độ chính xác.

Hỗ trợ **MP4 H.264**, không rỗng, tối đa **100 MiB, 2 phút, Full HD** (cạnh dài ≤1920, tối đa 1920×1080 pixel, FPS≤120); nên dùng 720p cho CPU. File không đọc được/không đúng codec được báo lỗi; không tự đổi nhãn, không tự coi là cảnh âm. Dữ liệu tải lên lưu trên máy tại `outputs/demo_app/uploads/<uuid>/`; kết quả ở `outputs/demo_app/runs/<job_id>/`. Mỗi lượt có model/tracker mới; các clip không dùng chung ID. App khôi phục video/kết quả đã kiểm khi khởi động lại; hash khác thì từ chối.

## Nguồn và phép thử

Nguồn video là ví dụ `vehicles.mp4` được giới thiệu trong [tài liệu Supervision của Roboflow](https://supervision.roboflow.com/0.27.0/notebooks/count-objects-crossing-the-line/), tải từ `https://media.roboflow.com/supervision/video-examples/vehicles.mp4` (35.345.757 byte). SHA-256 nguồn: `ac81100d9310bd4e9c02bc0b13b6492781d009742ced347766b2601be3c44ad4`.

Lấy 10 giây đầu và giảm xuống 1280×720 bằng FFmpeg, H.264 CRF22, bỏ audio để thử cục bộ. SHA-256 clip: `5ee70b88101502198e8b1e2ba1f1276cd309add4537425f0ddf1f3571048a270`. [Registry và lệnh dẫn xuất](../data/registries/external_demo_vehicles.json) ghi nguồn/byte/hash/tham số; clip không nằm trong train/validation/test và chưa có nhãn tai nạn. Thời gian container được dùng để phát; `source_seconds_verified=false`.

## Kết quả thật

| Đo trên lượt tracking qua trình duyệt | Kết quả |
| --- | ---: |
| Frame xử lý/kiểm lại | 250/250 |
| Tổng lượt quan sát bbox phương tiện | 837 |
| Số ID theo dõi tạm đã xuất hiện | 17 |
| Thời gian pipeline offline | 10,254 giây |
| FPS pipeline offline | 24,38 |

837 là tổng bbox qua các frame; 17 ID không chứng minh có 17 xe thực tế vì tracker có thể mất/đổi ID. Chưa có GT phương tiện/identity để đo precision, recall hoặc IDF1. FPS gồm giải mã, inference, tracking, render/cache/encode; không gồm nạp model/hash sau chạy và không là benchmark streaming. Đây là kiểm tra ứng dụng xử lý được video mới, không phải xác nhận độ chính xác trên mọi camera.

Bằng chứng đầy đủ tại `outputs/audits/external_video_2026-11-16/`: `download.json`, `derivation.json`, `browser_upload_check.json`, `result.json`, `http_check.json`, `tests.log`. Firefox đã chọn file thật qua input, gửi upload, đợi CPU hoàn tất, tua frame125 và tải lại trang; kết quả còn. Tạo `DemoState` mới cũng khôi phục đúng mẫu/run/hash. Có cảnh báo quyền SIGTERM của Selenium/Snap khi dọn tiến trình sau kiểm; ảnh và JSON đã lưu trước cảnh báo này.

Bộ test hiện có **57/57 đạt**, thêm bốn test upload dùng video H.264 thật và các trường hợp file rỗng/quá cỡ/sai đuôi, giả media, tải ngắt, quá dài/quá lớn/sai codec, tên file không được dùng làm đường dẫn, nguồn bị sửa sau lưu. Kiểm HTTP còn bao gồm video gốc/kết quả/range/last frame của mẫu mới.

**Chưa có cảnh báo va chạm tự động.** Model trong tính năng này nhận diện phương tiện; B0 accident thử riêng vẫn có lỗi validation đã ghi trong [báo cáo B0](B0_FEASIBILITY.md). Thử upload không thay điều kiện hoàn thành dữ liệu/B0 nghiên cứu và không cập nhật gói bàn giao ngày14/11.
