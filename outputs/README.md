# Đầu ra chạy cục bộ — không đưa lên Git

Đọc [training/README.md](training/README.md) để hiểu các run, biểu đồ, chỉ số và ảnh kiểm tra. Riêng README này được giữ trên Git; checkpoint, ảnh và log train nằm cục bộ.

```text
annotation_preview/  # video vẽ annotation tác giả
detection/           # bbox phương tiện do YOLO dự đoán
tracking/            # bbox + ID tạm của ByteTrack
audits/              # metadata, hash, CSV, ảnh đối chiếu, backup, kết quả kiểm tra
  archive/           # audit thử cũ không còn được workflow hiện tại tham chiếu
```

Nhiều liên kết trong tài liệu cũ trỏ tới các đường dẫn này như bằng chứng trên máy phát triển. Sau clone chúng chưa tồn tại; làm theo [hướng dẫn phục hồi](../docs/GETTING_STARTED.md). Script tránh ghi đè bằng hậu tố `_2`, `_3`; luôn dùng tên report thực tế được in ra.

Một số snapshot metadata nhỏ có trong `docs/evidence/` để đọc được trạng thái nghiên cứu ngay sau clone. Chúng là kết quả lịch sử, không chứng minh đã chạy trên máy mới; không chứa ảnh/video/raw annotation.

## Mốc đang dùng

| Muốn xem | Đường dẫn local |
| --- | --- |
| STTAD bốn chuỗi, bbox nguồn và chuyển YOLO | `audits/sttad_public_6/` |
| Các cảnh và cặp gần giống | `audits/pilot_groups/scene_overview.jpg` |
| Chất lượng CADP dẫn xuất | `audits/cadp_b0_quality/` |
| Pool B0 (ở data, không phải outputs) | `../data/processed/b0_public_pilot_v1/` |

Đã gom ba audit thử `sttad_public`, `sttad_public_2`, `sttad_public_3` vào `audits/archive/`, sau kiểm không có tham chiếu trong code/docs/metadata đang dùng. Không xóa file hay sửa nội dung bằng chứng; đường dẫn được ghi bên trong các report lưu trữ là đường dẫn tại lúc chạy. Các audit có tham chiếu khác giữ nguyên vị trí. Không chọn report chỉ theo hậu tố lớn nhất: ưu tiên đường dẫn trong readiness/báo cáo hiện hành.
