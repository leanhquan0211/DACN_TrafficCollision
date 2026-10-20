# Quy tắc làm việc trong project

- Trước khi đề xuất hoặc thực hiện thay đổi về hướng đi, công cụ, mô hình, dữ liệu, nhãn hay đánh giá, đọc `README.md` ở thư mục gốc và các sheet liên quan trong `YOLO_Lo_trinh_DACN.xlsx`.
- Theo mục tiêu, phạm vi, thứ tự thực hiện và điều kiện chuyển bước trong README. Phân biệt rõ phần đã kiểm chứng với kế hoạch; không trình bày mục tiêu hoặc số liệu tham khảo như kết quả thực nghiệm.
- Khi có lý do để đổi hướng, ghi quyết định và bằng chứng vào README/config/nhật ký thí nghiệm, rồi cập nhật tài liệu liên quan. Chỉ dẫn mới của người dùng và yêu cầu của giảng viên được ưu tiên; đồng bộ README sau khi đổi.
- Giữ dữ liệu, split, nhãn, config và đánh giá có thể tái lập. Chọn mô hình hoặc công cụ mới theo lỗi thực tế và phép đo, không theo tên phiên bản.
- Trước khi kết thúc công việc, cập nhật `progress/README.md` và file nhật ký cùng ngày: mục tiêu, việc đã làm, bằng chứng, việc còn dở và bước tiếp theo. Chỉ đánh dấu hoàn thành khi đạt điều kiện chuyển bước trong README gốc.
- **Quy ước mới của người dùng:** mỗi ngày theo múi giờ `Asia/Bangkok` chỉ có một file `progress/YYYY-MM-DD.md`. Mọi task/lần chạy/lượt trao đổi cùng ngày thêm vào các mục trong file đó, không tạo hậu tố theo chủ đề. Ghi rõ trạng thái lịch sử và kết quả mới; giữ bằng chứng kỹ thuật trong `docs/` và `outputs/audits/` riêng.
- Sau clone hoặc trên máy mới, đọc `docs/GETTING_STARTED.md` và `data/download_catalog.json`, kiểm file thực tế bằng `scripts/check_project_assets.py`. Manifest/review/evidence trên Git là hồ sơ máy phát triển, không chứng minh media đã có trên máy hiện tại. Không tự tải toàn dataset hoặc sửa hash/review để bỏ qua mismatch; giữ các xác nhận đã có nếu fingerprint dữ liệu khớp.
