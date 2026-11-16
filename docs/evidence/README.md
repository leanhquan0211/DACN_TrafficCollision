# Bằng chứng nhỏ đọc được ngay sau clone

Hai JSON ngày 19/10 là snapshot kiểm tra từ máy phát triển, sao từ `outputs/audits/` trước khi đưa code lên Git. Chúng ghi số frame/hash/kiểm tra đã chạy, không chứa video, ảnh hoặc annotation gốc. Không coi chúng là kết quả chạy trên máy mới.

- `2026-10-19-clean-video-validation.json`: đọc lại video sạch, GT preview, detection và tracking, mỗi file 221 frame; timing nguồn vẫn chưa xác minh.
- `2026-10-19-b0-validation.json`: thống kê/kiểm nhãn ứng viên và index âm; nhãn vùng chưa duyệt GT.
- `2026-11-12-restoration.json`: phục hồi 2.258 ảnh, hash nguồn/mirror, 23 test đạt trên máy Linux.
- `2026-11-14-inference.json`: chạy YOLO/ByteTrack CPU, kiểm MP4/cache, test và chẩn đoán class/track; không phải đánh giá va chạm.
- `2026-11-14-delivery.json`: kiểm dashboard/HTTP/Firefox, Word/slide và chuyển thư mục bản demo vehicle inference.
- `2026-11-14-research.json`: tìm nguồn, tải212 tệp STTAD ghim commit, decode176 ảnh/31 vùng/145 unknown và loại source lỗi; chưa train hoặc chia test.
- `2026-11-16-b0-feasibility.json`: đã train một lớp accident 12 epoch trên pilot STTAD phát triển, có checkpoint/hash; validation FN12/12 tại conf0,25, train bắt17/19 và báo nhầm3/6 ảnh âm; 53 test đạt. Không phải test khóa/nghiệm thu cảnh báo.
- `2026-11-16-external-video.json`: thêm upload MP4 và chạy clip cao tốc ngoài pilot qua Firefox; 250frame/837bbox/17ID tạm, kiểm refresh/khôi phục state, 57test đạt. Không có GT/accuracy/nhãn hoặc cảnh báo va chạm cho video mới.
- `2026-11-16-collision.json`: B2 luật causal/FSM và ảnh/clip/Events JSON chạy trên mẫu/upload; CADPframe109, development không alert trên3DETRAC;70test đạt và kiểm HTTP/Firefox. Không có test khóa, không suy accuracy100%; qualitygate có thể bỏ sót xe nhỏ/xa.
- `2026-11-16-pages.json`: GitHub Pages đã build/HTTPS200,37tệp công khai gồm hai clip/sáu kết quả;36payload+manifest khớp hash,7nhóm Firefox đạt trên cả localhost và URL công khai. Trang chỉ phát lại kết quả, không suy luận/upload mới hoặc chứa dữ liệu cá nhân/trọng số; gate nghiên cứu giữ nguyên.

Các file/hash code trong snapshot phản ánh **phiên bản tại thời điểm kiểm**, có thể khác sau chỉnh sửa tài liệu/công cụ. Muốn kiểm trạng thái hiện tại, chạy test/chuẩn bị dữ liệu theo [hướng dẫn mới](../GETTING_STARTED.md). Media, audit đầy đủ và backup manifest vẫn nằm cục bộ trong `outputs/` và bị ignore.
