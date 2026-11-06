# Đầu ra chạy cục bộ — không đưa lên Git

## Nơi lưu hiện hành từ 06/11/2026

```text
baselines/
  01_b0_image_detection/   # B0 mới
  02_b1_temporal_filter/   # B1 mới
  03_b2_motion_rules/      # B2 mới và hai run đã migration
  04_t0_mlp/               # T0 mới
  05_b3_gru/               # B3/T1 mới
shared_evaluations/        # so sánh và benchmark dùng chung
system_evidence/           # ảnh, clip và metadata của pipeline
data_audits/               # kiểm dữ liệu, nhãn và nguồn
```

Mỗi output mới nằm trong một thư mục `vNNN_short_description`. Xem [kiến trúc lưu trữ](../docs/STORAGE_ARCHITECTURE.md), [registry](../data/registries/project_explorer.json) và trang **Explore → Tìm artifact** trên dashboard để biết vị trí thật. Không tạo thủ công output mới trong `training/`, `audits/`, `detection/`, `tracking/` hoặc `annotation_preview/`. Chúng là vị trí của kết quả lịch sử được đăng ký `LEGACY`; `_legacy/` chỉ xuất hiện sau migration có plan, SHA, verify và rollback. Dữ liệu nguồn/release nằm ở `data_raw/`, `data_samples/`, `data/processed/`, không ở đây.

## Kết quả lịch sử còn tại chỗ

Đọc [training/README.md](training/README.md) để hiểu các run, biểu đồ, chỉ số và ảnh kiểm tra. Riêng README này được giữ trên Git; checkpoint, ảnh và log train nằm cục bộ.

```text
annotation_preview/  # video vẽ annotation tác giả
detection/           # bbox phương tiện do YOLO dự đoán
tracking/            # bbox + ID tạm của ByteTrack
audits/              # metadata, hash, CSV, ảnh đối chiếu, backup, kết quả kiểm tra
  archive/           # audit thử cũ không còn được workflow hiện tại tham chiếu
```

Nhiều liên kết trong tài liệu cũ trỏ tới các đường dẫn này như bằng chứng trên máy phát triển. Sau clone chúng chưa tồn tại; làm theo [hướng dẫn phục hồi](../docs/GETTING_STARTED.md). Các script lịch sử từng tránh ghi đè bằng hậu tố `_2`, `_3`; output mới dùng version `vNNN_short_description` và từ chối ghi đè. Luôn dùng tên report thực tế được in ra.

Một số snapshot metadata nhỏ có trong `docs/evidence/` để đọc được trạng thái nghiên cứu ngay sau clone. Chúng là kết quả lịch sử, không chứng minh đã chạy trên máy mới; không chứa ảnh/video/raw annotation.

## Mốc đang dùng

| Muốn xem | Đường dẫn local |
| --- | --- |
| STTAD bốn chuỗi, bbox nguồn và chuyển YOLO | `audits/sttad_public_6/` |
| Các cảnh và cặp gần giống | `audits/pilot_groups/scene_overview.jpg` |
| Chất lượng CADP dẫn xuất | `audits/cadp_b0_quality/` |
| Pool B0 (ở data, không phải outputs) | `../data/processed/b0_public_pilot_v1/` |

Đã gom ba audit thử `sttad_public`, `sttad_public_2`, `sttad_public_3` vào `audits/archive/`, sau kiểm không có tham chiếu trong code/docs/metadata đang dùng. Không xóa file hay sửa nội dung bằng chứng; đường dẫn được ghi bên trong các report lưu trữ là đường dẫn tại lúc chạy. Các audit có tham chiếu khác giữ nguyên vị trí. Không chọn report chỉ theo hậu tố lớn nhất: ưu tiên đường dẫn trong readiness/báo cáo hiện hành.
