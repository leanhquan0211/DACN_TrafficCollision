# Metadata dữ liệu được đưa lên Git

- `manifest.csv`: danh mục **12 asset đã kiểm trên máy phát triển**, gồm đường dẫn/hash/nguồn và review. Có dòng trong manifest không có nghĩa file đã có trên máy vừa clone. Không xóa dòng lịch sử hoặc đổi nhãn chỉ vì file chưa được tải.
- `reviews/`: xác nhận của người dùng, giữ riêng annotation tác giả; 001407 đã xác nhận đúng xe/Colliding 96–130 theo frame, ba DETRAC đầy đủ âm. Không yêu cầu xác nhận lại nếu phục hồi đúng dữ liệu đã kiểm.
- `registries/cadp_001407_images.csv`: hash/kích thước/đường dẫn của 221 JPG đã kiểm; không chứa ảnh hoặc bbox. Dùng kiểm bản tải lại có đúng nội dung đã rà không.
- `download_catalog.json`: tệp cần lấy, URL, vị trí lưu, vai trò và trạng thái xác minh. Đây là chỉ dẫn tải thủ công, không phải script tải dataset.
- `pilot_inventory.csv`/`pilot_inventory_summary.json`: nhóm theo chuỗi, không đếm output/clip con là sự kiện mới.
- `b0_readiness.json`: điều kiện còn thiếu trước train; quy tắc vùng accident hiện vẫn đề xuất.
- `cadp_source_inventory.json`: kết quả tìm nguồn trước đây; link có thể đổi, cần kiểm lại khi mở rộng.
- `processed/`: kết quả sinh ra như nhãn ứng viên/chỉ mục âm, **bị ignore**, tạo lại bằng script. Nhãn đề xuất không phải GT đã duyệt.

[Hướng dẫn dựng lại từ đầu](../docs/GETTING_STARTED.md). Kiểm những file thực sự đang có bằng `python scripts/check_project_assets.py --check-hashes`; công cụ chỉ đọc dữ liệu, không ghi manifest/review hoặc tải thêm.
