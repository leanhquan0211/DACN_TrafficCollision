# Quy tắc nhãn va chạm — bản nháp 19/10/2026

> **Tài liệu chi tiết/lịch sử:** ưu tiên [mục lục hiện hành](README.md), [policy nhãn B0](b0_label_protocol.md) và [trạng thái dữ liệu mới nhất](b0_pilot_audit.md). Các số liệu/chỉ dẫn cũ bên dưới giữ bối cảnh lúc tạo, không thay hướng public đã chọn.

**Trạng thái: bản nháp để rà với dữ liệu thật và giảng viên; chưa phải nhãn GT đã duyệt.** Tài liệu này cụ thể hóa bước 01 của sheet `05_Cac_buoc` và phần nhãn/split của sheet `08_Du_lieu` trong `YOLO_Lo_trinh_DACN.xlsx`. Không suy ra nhãn từ tên video, bbox YOLO, ID ByteTrack hoặc một vài frame lấy mẫu.

## Phạm vi đề xuất

- Nguồn đầu vào: video giao thông từ **một góc CCTV cố định** cho mỗi clip. Một sự kiện là va chạm vật lý **giữa hai hoặc nhiều phương tiện nhìn thấy được**. Phạm vi class cụ thể (chỉ ô tô hay thêm xe máy) phải chốt sau khi kiểm tra nhãn và độ phủ dữ liệu.
- Đây là **detection**: xác nhận sự kiện đang/vừa xảy ra. Near miss, phanh gấp, xe đỗ sát, kẹt xe hoặc bbox chồng lên nhau trong ảnh **không tự là va chạm**. Va chạm với người hoặc vật thể không phải phương tiện để ngoài phạm vi ban đầu và ghi rõ khi gặp.
- Chỉ gán `positive` khi xem toàn clip và có bằng chứng trực quan đủ rõ về tiếp xúc giữa phương tiện. Nếu điểm tiếp xúc bị che, clip bắt đầu sau va chạm, video bị cắt hoặc góc quay không đủ để phân biệt contact với near miss, gán `uncertain` để rà tiếp; không ép thành `negative`.

## Mốc thời gian và đối tượng

- Với `positive`, `onset_s` là thời điểm **frame đầu tiên thấy tiếp xúc** trong clip đang xét. Ghi thêm frame index trong phiếu rà nhãn nếu có để kiểm tra lại; không dùng thời điểm model phát cảnh báo thay onset GT.
- `end_s` là thời điểm tương tác va chạm trực tiếp kết thúc theo quy tắc đã chốt trên pilot; không mặc định là cuối clip. Nếu ranh giới không xác định được, giữ trống và đánh dấu cần phân xử. Thời điểm trước onset là âm tính cho tác vụ detection; chỉ đoạn contact/diễn biến hậu va chạm được định nghĩa trước mới có thể là dương tính.
- `involved_gt_ids` là mã do người gán cho các phương tiện liên quan **trong chính video đó**. Không dùng track ID của ByteTrack làm GT; khi tracker đổi ID cần ánh xạ riêng. Nếu chỉ đủ nhãn mức cảnh, để trường này trống và ghi giới hạn scene-level.
- `negative` chỉ được dùng sau khi xem đủ toàn clip và xác nhận không có va chạm trong phạm vi. Để `onset_s`, `end_s`, `involved_gt_ids` trống. Có thể thêm `hard_negative_type` như `parked_close`, `congestion`, `sudden_stop`, `near_miss`, `crossing_paths`, `occlusion_id_switch`; video âm bình thường để trống.

## Ghi vào manifest và rà nhãn

File [data/manifest.csv](../data/manifest.csv) có **một dòng cho mỗi asset video hoặc chuỗi ảnh**, gồm nguồn và MP4/clip sinh ra. `video_id`, đường dẫn, SHA-256, kích thước, FPS và số frame là thông tin kỹ thuật đo từ file; chuỗi ảnh dùng `asset_role=clean_image_sequence`, hash từng ảnh qua inventory, để trống hash thư mục/FPS/duration chưa biết. `duration_s` trên MP4 tính bằng `frame_count/fps` để kiểm kê, có thể chỉ là thời gian trình chiếu; khi gán onset/end cần timestamp của dữ liệu gốc. Các trường nguồn/nhãn/split phải có căn cứ riêng. Schema được giải thích tại [hướng dẫn chuẩn bị dữ liệu](dataset_preparation.md): `annotation_origin`/`author_colliding_frames` lưu nhãn tác giả, còn `user_review_status` ghi việc người dùng rà. Có annotation tác giả chưa tự đồng nghĩa nhãn va chạm dự án đã duyệt. `unknown`, `not_reviewed`, `pending`, `unassigned` **không mang nghĩa âm tính**. Không chuyển frame Colliding sang giây video gốc bằng FPS demo/trình chiếu khi timing chưa khớp.

**Xác nhận mới nhất 19/10:** [phiếu rà CADP theo frame](../data/reviews/2026-10-19-cadp-001407-frame-confirmation.json) xác nhận đúng xe và Colliding 96–130; không yêu cầu rà lại 001407. Manifest ghi positive, GT ID 0 và 2, nhưng `onset_s/end_s` trống vì source FPS chưa xác minh; annotation tác giả và lớp reviewer vẫn riêng. [Phiếu trước](../data/reviews/2026-10-19-user-confirmations.json) giữ xác nhận âm toàn bộ ba DETRAC. Clip con chỉ kế thừa khi đã chứng minh parent/range, ghi `inherited_from_reviewed_full_sequence`, không coi là lần xem độc lập hoặc lan sang chuỗi khác. `visible=1-outside` chỉ là hiện diện, xem riêng `occluded`; `generated` là cờ nguồn. [Quy tắc vùng B0 đề xuất](b0_label_protocol.md) chưa được duyệt thành GT; xác nhận event theo frame không tự duyệt bbox vùng này. Frame thiếu annotation hoặc không có Colliding không tự là negative toàn cảnh.

Quy trình dự kiến cho mỗi clip:

1. Mở video gốc, kiểm tra FPS, độ dài và đủ diễn biến trước/sau điểm nghi vấn; ghi nguồn/điều kiện sử dụng. Nếu là bản cắt hoặc chuyển mã, giữ quan hệ với video gốc trong `source_event_id`.
2. Xem **toàn clip** ở tốc độ thường và chậm tại đoạn nghi vấn. Ghi nhãn `positive`/`negative`/`uncertain`, mốc thời gian và xe liên quan theo quy tắc trên; ghi lý do khi mơ hồ.
3. Rà lại ít nhất 10 trường hợp pilot gồm va chạm rõ, near miss/xe sát nhau và trường hợp khó. Chốt cách xử lý bất đồng với giảng viên/người rà thứ hai trước khi tạo bộ nhãn chính thức. Hiện **chưa có 10 ví dụ đã rà**.
4. Chỉ sau khi biết `camera_id`, `source_event_id`, nguồn và clip trùng/gần trùng mới chia train/validation/test theo **nhóm camera/nguồn/sự kiện**. Các bản cắt của một sự kiện ở cùng split. Không chia ngẫu nhiên frame hoặc cửa sổ; không gán split cho ba video hiện có khi chưa biết chúng có cùng nguồn/sự kiện không.

## Nhãn cho các bước sau

- **B0 YOLO accident:** cần định nghĩa riêng vùng bbox tai nạn theo cùng quy tắc, gán ảnh dương và ảnh âm có file nhãn rỗng đúng định dạng; bbox xe pretrained không tự thành bbox tai nạn.
- **Verifier cặp xe/chuỗi:** cần nhãn xe liên quan và cửa sổ theo thời gian. Cửa sổ chỉ dùng frame đã đến; đoạn trước onset không được gán dương tính vì clip sau đó có tai nạn. Nếu chỉ có nhãn mức cảnh, phải thiết kế và báo cáo bài toán scene-level thay vì giả có nhãn cặp.

**Điều kiện duyệt quy tắc:** pilot có ví dụ và bất đồng được giải quyết; nhãn trong manifest truy ngược được video gốc; phạm vi class và định nghĩa `end_s` được chốt. Trước đó không dùng manifest này để train hoặc báo metric.
