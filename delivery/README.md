# Bộ bàn giao demo

**Cập nhật sau lượt sửa báo nhầm16/11:** source/web local hiện dùng luật v5, đã chạy lại clip người dùng900frame (1cảnh báo nhầm→0), CADP vẫn cảnh báo109 và74testđạt. [Bằng chứng và giới hạn](../docs/FALSE_ALERT_FIX.md). Word/PDF/ZIP bên dưới đã tạo trước lượt sửa, giữ là snapshot v4; chưa tái xuất bằng v5 và không kèm video người dùng.

## Bản cảnh báo thử nghiệm — 16/11/2026

Chế độ collision đã có luật/FSM tự động, khung đỏ và bằng chứng ảnh/clip/Events JSON, chạy được trên MP4 upload. [Kết quả, cách dùng và giới hạn](../docs/COLLISION_DETECTION.md). Báo cáo phát triển mới nằm trong `collision_2026-11-16/`; không thay bằng chứng nghiên cứu hoặc mẫu báo cáo chính thức của trường. Gói mới `TrafficLab_demo_2026-11-16.zip` giữ nguồn/model/hai clip và cả kết quả cảnh báo mẫu; bỏ upload cá nhân và không chứa `.venv`/toàn dataset.

- [Báo cáo PDF mới](collision_2026-11-16/BAO_CAO_PHAT_HIEN_VA_CHAM.pdf), [Word có thể sửa](collision_2026-11-16/BAO_CAO_PHAT_HIEN_VA_CHAM.docx).
- [Gói demo ZIP16/11](TrafficLab_demo_2026-11-16.zip), kèm fileSHA256. Đã kiểm184file và chuyển thư mục/nạp hai mẫu đủ ba chế độ trên Linux hiện tại; chưa kiểm cài dependencies sạch hoặc Windows.

## Snapshot trước cảnh báo — 14/11/2026

- `TrafficLab_demo_2026-11-14.zip`: source + YOLOv8n + hai clip sạch + bốn bộ kết quả + tài liệu, kèm manifest SHA-256 bên trong. Không gồm `.venv`/bộ cài offline hoặc toàn dataset.
- `BAO_CAO_HIEN_TRANG.docx` và `.pdf`: báo cáo hiện trạng, có ảnh chạy thật và giới hạn. Cần điền thông tin sinh viên/giảng viên, mẫu trường và bổ sung kết quả cuối trước nộp.
- `SLIDE_DEMO.pptx` và `.pdf`: 11 slide để chỉnh sửa/trình bày bản hiện tại.
- `document_provenance.json`: hash nguồn nội dung và các report đã dùng.

Chạy `bash demo.sh` ở thư mục gốc; xem `docs/DEMO_GUIDE.md` và `docs/KE_HOACH_4_TUAN.md`. Đây là bản demo detection/tracking và review thủ công. Chức năng cảnh báo va chạm tự động và thực nghiệm nghiên cứu chưa hoàn thành; không coi có file ZIP/Word/slide là đã đủ nghiệm thu đề tài ban đầu.
