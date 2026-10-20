# Bằng chứng nhỏ đọc được ngay sau clone

Hai JSON ngày 19/10 là snapshot kiểm tra từ máy phát triển, sao từ `outputs/audits/` trước khi đưa code lên Git. Chúng ghi số frame/hash/kiểm tra đã chạy, không chứa video, ảnh hoặc annotation gốc. Không coi chúng là kết quả chạy trên máy mới.

- `2026-10-19-clean-video-validation.json`: đọc lại video sạch, GT preview, detection và tracking, mỗi file 221 frame; timing nguồn vẫn chưa xác minh.
- `2026-10-19-b0-validation.json`: thống kê/kiểm nhãn ứng viên và index âm; nhãn vùng chưa duyệt GT.

Các file/hash code trong snapshot phản ánh **phiên bản tại thời điểm kiểm**, có thể khác sau chỉnh sửa tài liệu/công cụ. Muốn kiểm trạng thái hiện tại, chạy test/chuẩn bị dữ liệu theo [hướng dẫn mới](../GETTING_STARTED.md). Media, audit đầy đủ và backup manifest vẫn nằm cục bộ trong `outputs/` và bị ignore.
