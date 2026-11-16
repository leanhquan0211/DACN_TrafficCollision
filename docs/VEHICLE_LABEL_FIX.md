# Xử lý nhầm car/truck và khung trùng — 16/11/2026

Người dùng chỉ xe trắng phía trên bên phải trong clip `rearend (3).mp4`, frame139/139: hiển thị `truck`0,23 dù hình ảnh giống ô tô/SUV. Đã tìm đúng quan sát track245 của lượt cũ. **Bản mới hiện “Xe · chưa rõ loại” trong bảng, `vehicle? det:0.23` trên video**, giữ nguyên dự đoán thô trong JSON và tooltip. Chưa sửa được detector để xe này thành `car`; không dùng việc bỏ nhãn yếu làm chứng minh accuracy tăng.

## Chẩn đoán trước khi đổi

- Track245 chỉ có2quan sát:138 truck0,313;139 truck0,230. Không có lịch sử car đủ tin cậy cho ID này để tự sửa tên.
- Thử cùng YOLOv8n, CPU4threads, cùng frame137–139 với imgsz640/960/1280: cả9lần đều có dự đoán truck tại vị trí đó;1280 còn cho truck≈0,55–0,58. Vì vậy giữ imgsz640/model cũ, không khẳng định tăng resolution chữa được lỗi. Thời gian probe có cold-start/ít frame, không là benchmark tốc độ.
- 140frame cũ có141cặp khung khác lớp IoU≥0,8 trên92frame; nhiều cặp car/truck gần như cùng vị trí nhưng mang ID riêng. Đây là chỉ báo khung trùng cần xử lý, không tự là141xe hoặc141lỗi có GT.

## Thay đổi hiện tại

[Cấu hình](../configs/vehicle_inference.json), [nhãn và render](../src/vehicle_labels.py), [pipeline](../src/video_pipeline.py).

1. `agnostic_nms=true`: NMS xét chồng khung giữa các lớp, giữ cùng ngưỡng IoU hiện tại0,7, conf và model. Giảm việc cùng xe có khung car/truck đồng thời. Có thể loại nhầm xe thật khi hai bbox chồng IoU cao; chưa có đánh giá recall detector độc lập.
2. Dự đoán thô `class_id`, `class_name`, `confidence`, bbox và ID của quan sát còn lại **không bị đổi tên**. Thêm `display_class` riêng, không tạo nhãn huấn luyện/GT.
3. Mỗi ID dùng tối đa15frame quá khứ/hiện tại. Chỉ phiếu confidence≥0,5 góp vào lớp hiển thị; cần≥3quan sát đủ điểm, lớp thắng chiếm≥75% tổng trọng số confidence để hiện lớp ổn định. Nếu ít lịch sử nhưng frame hiện tại≥0,5, chỉ hiện dự đoán tạm (`car?`…); bằng chứng yếu/mâu thuẫn hiện chưa rõ loại. `vote_share` là tỷ lệ phiếu, không là xác suất đúng.
4. Tách ID/video; reset khi cắt cảnh, mất track>3frame hoặc bbox đổi kích thước vượt tỷ lệ1,6. Cửa sổ theo frame, còn phụ thuộc FPS. Không nối lại ID đã mất bằng suy đoán, không dùng frame tương lai. Detection không có ID chỉ có dự đoán tạm, không tích lũy lịch sử giả.
5. Video và bảng dùng cùng `display_class`. Cột **ĐIỂM YOLO** vẫn là điểm thô của frame hiện tại, có thể ứng với lớp khác lớp tổng hợp; tooltip nêu lớp thô. Màu/vote không phải xác suất va chạm. Config/producer/hash và `agnostic_nms` được ghi trong report; web nhắc chạy lại output dùng config cũ.

Ngưỡng confidence chỉ tác động nhãn hiển thị, không tự loại quan sát yếu khỏi cache hoặc luật va chạm. NMS thay quan sát/ID đầu vào nên phải kiểm lại cả cảnh báo. `motion_contact_v5` giữ nguyên cấu hình, không thay threshold để bù cho lỗi lớp.

## Kiểm thực tế

Đã chạy pipeline CPU thật7clip, tổng3548frame; giữ output cũ, không sửa report/hash lịch sử.

| Case phát triển | Kết quả với NMS/nhãn mới |
| --- | --- |
| Clip người dùng140frame | 2484quan sát,50ID tạm (trước2645/65); cặp khác lớp IoU≥0,8 từ141→0; xe được chỉ hiện chưa rõ loại, raw vẫn truck0,230. Cảnh báo52 vẫn còn, clip chưa có GT sự kiện đầy đủ. |
| CADP221frame | Một cảnh báo đúng cặp tại108, không cảnh báo khác; evaluator đối chiếu bbox nhãn, candidate35/35frame interval. Trước NMS mới là109/34trên35. Không suy thêm camera/sự kiện từ lượt chạy lại. |
| Clip900frame đã sửa báo nhầm | Vẫn0cảnh báo. |
| DETRAC664+936+437frame đã rà âm | 0cảnh báo trên2037frame; giữ trạng thái source timing đã kiểm. |
| Cao tốc250frame chưaGT | 0cảnh báo; không gọi là TN/đo accuracy. |

**80/80testđạt,0skip**: thêm6test về nhãn yếu/giữ raw, chống flip mà không tự đổi truck thật, xung đột cần abstain, cách ly ID/cut/gap/scale/run, cửa sổ hữu hạn và detection không bịa lịch sử.

Firefox6nhóm đạt: CADP còn cảnh báo; xe được chỉ có nhãn chưa rõ/tooltip raw truck23%; video thật giải mã/tua/phát đồng bộ; clip900frame không tái báo; output cũ được đánh dấu; refresh có đúng run mới. Đã xem ảnh dashboard và crop từ MP4 kết quả ở frame139. Cảnh báo SIGTERM Selenium/Snap xảy ra khi dọn WebDriver sau lưu bằng chứng, không làm hỏng kiểm chức năng.

## Xem và tái lập

Mở <http://127.0.0.1:8765>, tải lại trang rồi chọn **rearend (3).mp4** và **Phát hiện va chạm · Thử nghiệm**. Tua frame139, xe trắng ở trên bên phải hiện `vehicle?`. Trong bảng, tìm ID199 của lượt mới, loại **Xe · chưa rõ loại**, di chuột xem raw truck23%. ID245 cũ thành199 vì NMS thay tập quan sát; không có mapping danh tính xe ngoài đời được chứng nhận.

CLI vẫn dùng `scripts/run_collision.py`, `run_tracking.py`, `run_detection.py`; mặc định đọc config mới. Có thể truyền `--vehicle-config` để ghi rõ chính sách thử. Ví dụ clip người dùng đã lưu trên máy này:

```bash
PATH="$PWD/.venv/bin:$PATH" .venv/bin/python -B scripts/run_collision.py \
  outputs/demo_app/uploads/e3d45dd5e8314be28fa656ee1e94ed81/video.mp4 \
  --device cpu --cpu-threads 4 --timing-status unknown \
  --vehicle-config configs/vehicle_inference.json \
  --output-dir outputs/vehicle_labels_repeat
.venv/bin/python -B scripts/check_inference_outputs.py outputs/vehicle_labels_repeat
```

Audit: `outputs/audits/class_label_2026-11-16/`: ảnh gốc/crop, lịch sử245, resolution probe, cặp khung trước/sau,7report thật, evaluator CADP, tests/browser/recovery. [Snapshot nhỏ trên Git](evidence/2026-11-16-vehicle-labels.json) không chứa ảnh/video cá nhân. Sau clone cần file gốc/asset thật; không lấy snapshot làm inventory máy mới. Pages và gói Word/PDF/ZIP cũ chưa tái xuất; không công khai upload người dùng.

## Giới hạn và bước tiếp theo

Đây là giảm khung trùng và xử lý sự không chắc chắn của lớp. Detector vẫn có thể nhầm SUV/pickup/truck/bus kể cả điểm cao; lịch sử chỉ làm nhãn ổn định hơn và có thể giữ nhãn sai khi ID bị ghép sai. “Chưa rõ loại” làm ít nhãn khẳng định hơn, không đồng nghĩa recall/accuracy tốt hơn. Ngưỡng phát triển đã xem các cảnh này; chưa có test khóa.

Muốn nâng độ chính xác lớp thật cần subset xe có nhãn được rà, camera độc lập, quy tắc phân biệt SUV/pickup/truck rõ ràng và so model/cấu hình trên cùng tập đánh giá; chỉ cân nhắc model khác/fine-tune sau phép đo đó. Nhãn/split/model/gate nghiên cứu hiện tại không đổi. Không dùng class hiển thị làm GT hoặc bằng chứng một cảnh báo va chạm đúng.
