# Phát hiện và cảnh báo va chạm giao thông từ video CCTV

## Báo cáo hiện trạng và bản demo nền tảng — 14/11/2026

Sinh viên: [điền họ tên] · MSSV: [điền] · Lớp: [điền] · Giảng viên: [điền].

Tài liệu này mô tả kết quả thực sự có ở thời điểm bàn giao. Chưa phải báo cáo nghiệm thu hoàn chỉnh của hệ thống phát hiện va chạm. Cần cập nhật kết quả cuối và mẫu trình bày của trường trước khi nộp.

## 1. Bài toán và mục tiêu

Đề tài hướng đến phát hiện sự kiện va chạm xe–xe đang hoặc vừa xảy ra trong video từ camera CCTV cố định. Đầu ra mong muốn gồm thời điểm, camera, track liên quan, mức tin cậy và ảnh/clip bằng chứng. Dự báo tai nạn trước khi xảy ra, đa camera và xác định vận tốc km/h nằm ngoài phạm vi ban đầu.

Hai câu hỏi nghiên cứu được đặt ra: thông tin chuyển động theo thời gian có giảm cảnh báo sai trên các tình huống dễ nhầm so với detector ảnh cộng lọc thời gian ở recall tương đương hay không; và chi phí xử lý có phù hợp máy đích hay không. Chưa có thực nghiệm đủ để trả lời hai câu hỏi này.

Phần đã triển khai là nền tảng nhận diện/theo dõi phương tiện, quản lý bằng chứng và giao diện đối chiếu. Pretrained vehicle detector không có class accident; thấy nhiều xe hoặc bbox chồng nhau không tự chứng minh va chạm.

## 2. Thiết kế hệ thống hiện có

Pipeline vận hành: video sạch → YOLOv8n pretrained → ByteTrack nếu chọn tracking → MP4 overlay + cache JSONL từng frame + report provenance. Giao diện HTML/CSS/JavaScript gọi máy chủ Python standard library qua HTTP loopback. Không có dịch vụ cloud hoặc CDN trong luồng demo.

Mỗi lượt suy luận tạo model/tracker riêng để tránh mang ID sang video tiếp theo. Các class được lọc theo tên phương tiện. Cache lưu bbox pixel/chuẩn hóa, class, confidence của phương tiện, ID tạm và tuổi theo số lần quan sát. Missing-track chỉ có mask/gap, không tạo bbox giả. Các output có tên riêng và không ghi đè lượt trước.

Run report lưu hash input/trọng số/output/cache, cấu hình detector/tracker, package versions, số frame và thời gian xử lý. Consumer kiểm hash, clock và số quan sát, rồi giải mã lại MP4 trước khi dùng trong demo. Khi di chuyển gói, chỉ định lại vị trí artifact và giữ nguyên phép kiểm hash; report lịch sử không bị sửa.

Giao diện cho chọn hai mẫu video, đổi detection/tracking, phát hai video cùng nhau, chọn frame, xem quan sát và tải kết quả. Nút chạy lại gọi pipeline thật trên CPU bằng tiến trình riêng. Một job chạy mỗi lúc để tránh tranh chấp CPU; lỗi hiển thị kèm vị trí log. Ghi nhận thủ công lưu note và ảnh frame gốc với hash, độc lập với nhãn nghiên cứu.

## 3. Dữ liệu và định nghĩa nhãn

Pilot phát triển có 221 ảnh CADP 001407 và 2.037 ảnh của ba chuỗi DETRAC MVI_20011/MVI_20012/MVI_20032. Tổng 2.258 ảnh đã phục hồi có đối chiếu fingerprint. Gói demo chỉ mang hai clip ngắn và các kết quả cần trình diễn.

CADP có một sự kiện độc lập được người dùng xác nhận: participant GT 0 và 2, Colliding ở frame 96–130, bao gồm hai đầu. Mốc này là nhãn tham chiếu do người rà, không được dùng để chèn cảnh báo vào chương trình. Ba chuỗi DETRAC được xác nhận âm tính trong review lịch sử. Các bản cắt/video overlay không được đếm thành sự kiện độc lập mới.

35 hộp bao participant hiện là đề xuất vùng accident, chưa phải GT vùng được duyệt. 186 frame còn lại của CADP không tự trở thành ảnh âm chỉ vì nằm ngoài proposal. Mọi split vẫn unassigned và readiness giữ can_train=false. Không chia ngẫu nhiên frame của cùng tai nạn sang train/val/test.

Source FPS CADP chưa xác minh. MP4 sạch dùng 20 FPS trình chiếu; cache có video_time_s để phát nhưng source_time_s để null. Vì vậy chưa được báo tốc độ ảnh theo giây nguồn hoặc độ trễ từ onset theo giây của chuỗi này. Quyết định này giữ khả năng phân tích theo frame mà không tạo timestamp nguồn giả.

## 4. Môi trường và kết quả chạy thực tế

Máy hiện tại chạy CPU, Python 3.12.16, torch 2.11.0+cpu, torchvision 0.26.0+cpu, ultralytics 8.4.178, lap 0.5.13, OpenCV 5.0.0.93, numpy 2.5.2. Các run dùng imgsz 640; cấu hình được ghi trong từng report. Không có CUDA khả dụng trên máy đã kiểm.

| Video / nhánh | Frame | Quan sát bbox | ID tạm |
| --- | --- | --- | --- |
| CADP 001407 / detection | 221 | 1.755 | Không áp dụng |
| CADP 001407 / tracking | 221 | 1.831 | 31 |
| DETRAC MVI_20011 đoạn 10s / detection | 250 | 4.563 | Không áp dụng |
| DETRAC MVI_20011 đoạn 10s / tracking | 250 | 4.935 | 59 |

Số liệu trên lấy từ bốn report được catalog demo chọn, không phải độ chính xác. Tổng bbox đếm cùng một xe qua nhiều frame; số ID tạm có thể tăng khi tracker mất/đổi ID và không phải số xe thật. Detection/tracking có effective confidence khác theo nhánh; không dùng chênh số bbox để kết luận nhánh nào chính xác hơn.

Tracking đầy đủ ba DETRAC cũng đã xử lý 664, 936, 437 frame, nhưng không dùng các đoạn này để nhân số mẫu độc lập. Tốc độ khoảng 20–23 FPS của một số run CPU là xử lý file offline; report nêu rõ có cold first inference và không tính model loading/post-run hashing. Chưa đo streaming queue, frame drops, GPU/VRAM hoặc event delay. Giao diện đọc FPS của từng run thay vì gán một số cố định.

Phân tích debug trên 35 frame CADP cho thấy proposal association của xe buýt có 13 frame trả class car, một frame không đạt IoU debug 0.3; ứng viên ID1 có 34/35 frame khi ghép không lọc class. Xe GT2 có ứng viên ID19 ở 35/35 frame. Mapping này chưa được rà như GT-track mapping, không là IDF1/HOTA hoặc metric va chạm. Kết quả gợi ý phải xử lý class flicker và chất lượng quan sát trước khi thiết kế features.

## 5. Kiểm chứng phần mềm và khả năng tái lập

Các test bao phủ nhãn/missing/clock, download fail-safe, fingerprint, metadata leakage, output reservation, consumer chống tampering, media Range và bằng chứng review. Kiểm HTTP riêng đọc catalog, report, frame cuối, tua MP4; từ chối request mutation thiếu token/cross-origin; gọi suy luận CPU thật và kiểm review JPEG. Xem bằng chứng tại outputs/audits/delivery_2026-11-14 và snapshot docs/evidence, không xem test pass là đạt accuracy.

Môi trường được pin trong requirements; dữ liệu/trọng số có registry/catalog. Hướng dẫn demo mô tả cách dựng lại, lỗi thường gặp và kịch bản trình diễn. Gói ZIP có manifest SHA-256 để kiểm nội dung sau chuyển máy. Không mang .venv hoặc hồ sơ/token trình duyệt vào gói.

## 6. Phần còn thiếu và đánh giá dự kiến

B0 accident detector chưa huấn luyện; B1 smoothing chưa đo; candidate generation, luật chuyển động, MLP/GRU và FSM cảnh báo chưa triển khai. Dashboard hiện tại không được gọi là hệ thống cảnh báo va chạm đã nghiệm thu. Manual review không tự tạo GT hoặc score tai nạn.

Sau khi có dữ liệu/nhãn đủ, cần group split theo camera/nguồn/sự kiện, loại near-duplicate, giữ test khóa. Train B0 trước, đo B1 rồi phân tích FP/FN. Rà tracks/timing, đo candidate recall trước motion rules B2; chỉ học verifier nếu có nhãn phù hợp. Các baseline phải dùng cùng evaluator, split và chính sách ghép event.

Đánh giá cuối dự kiến: event precision/recall/F1, PR curve, false alerts/hour trên video âm dài, event delay, FPS end-to-end, frame drops/queue lag và peak VRAM ở máy đích. Ngưỡng chọn bằng validation; test không dùng để chỉnh luật. Chưa có các số đo này trong project, vì vậy không có bảng F1 giả hoặc số paper thay cho kết quả.

## 7. Kế hoạch một tháng và điều kiện nộp

Tuần 1 ưu tiên dữ liệu/nhãn và group split; tuần 2 baseline B0/B1 cùng phân tích lỗi; tuần 3 candidates/rules/FSM nếu qua gate; tuần 4 đánh test, báo cáo và dựng lại demo. Chi tiết ngày dự kiến và điều kiện ở docs/KE_HOACH_4_TUAN.md.

Nếu không đủ dữ liệu/nhãn trong tuần đầu, cần giảng viên duyệt phạm vi hẹp sớm. Bản hiện tại có thể trình diễn nền tảng vehicle inference, nhưng chưa đáp ứng nghiệm thu chức năng tự động phát hiện/cảnh báo va chạm của đề tài ban đầu. Trước nộp phải điền thông tin tác giả/giảng viên, mẫu trường và cập nhật kết quả cuối vào báo cáo/slide.

## 8. Tài liệu và nguồn kiểm tra

- README.md và YOLO_Lo_trinh_DACN.xlsx: mục tiêu, protocol/gates và kế hoạch gốc.
- docs/INFERENCE_CACHE.md: schema cache, lệnh chạy và giới hạn runtime.
- docs/RESTORE_PILOT.md, data/download_catalog.json, data/registries/: nguồn và fingerprint.
- data/reviews/2026-10-19-cadp-001407-frame-confirmation.json: xác nhận interval theo frame.
- outputs/demo_2026-11-14/ và outputs/inference_2026-11-14/: bốn report/cache/MP4 dùng trong bảng.
- outputs/audits/inference_2026-11-14/cadp_participant_class_diagnostics.json: case study class flicker; không phải GT association.
- https://github.com/ultralytics/ultralytics: thư viện YOLO; tuân thủ giấy phép của phần mềm/trọng số.
- docs/cadp_pilot_sources.md và docs/dataset_preparation.md: nguồn CADP/DETRAC, điều kiện/giới hạn đã rà. Không suy quyền công bố lại toàn bộ dataset từ việc tải được sample.
