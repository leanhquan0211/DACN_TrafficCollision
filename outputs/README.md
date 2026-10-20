# Đầu ra chạy cục bộ — không đưa lên Git

```text
annotation_preview/  # video vẽ annotation tác giả
detection/           # bbox phương tiện do YOLO dự đoán
tracking/            # bbox + ID tạm của ByteTrack
audits/              # metadata, hash, CSV, ảnh đối chiếu, backup, kết quả kiểm tra
```

Nhiều liên kết trong tài liệu cũ trỏ tới các đường dẫn này như bằng chứng trên máy phát triển. Sau clone chúng chưa tồn tại; làm theo [hướng dẫn phục hồi](../docs/GETTING_STARTED.md). Script tránh ghi đè bằng hậu tố `_2`, `_3`; luôn dùng tên report thực tế được in ra.

Một số snapshot metadata nhỏ có trong `docs/evidence/` để đọc được trạng thái nghiên cứu ngay sau clone. Chúng là kết quả lịch sử, không chứng minh đã chạy trên máy mới; không chứa ảnh/video/raw annotation.
