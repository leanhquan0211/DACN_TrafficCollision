# CADP 001407: ảnh sạch và đối chiếu nhãn — 19/10/2026

> **Cập nhật mới:** người dùng đã xác nhận đúng xe **và Colliding 96–130 theo frame**. Không cần rà lại mẫu này. [Phiếu mới](../data/reviews/2026-10-19-cadp-001407-frame-confirmation.json), [chuẩn hóa nhãn B0 đã làm](b0_label_protocol.md), [kiểm nguồn mở rộng](cadp_pilot_sources.md). Các report audit cũ bên dưới giữ trạng thái tại lúc tạo; FPS nguồn vẫn chưa biết.

## Kết quả thực tế

Ban đầu `data_raw/cadp/frames/` chỉ có **`001407-20261019T121452Z-1-001.zip`**, chưa có thư mục ảnh. ZIP chứa đúng 221 JPG dưới `001407/`; thứ tự thành viên ZIP không phải thứ tự frame. Đã kiểm CRC toàn ZIP, kiểm dung lượng trống rồi lấy riêng chuỗi này về **`data_raw/cadp/frames/001407/0.jpg … 220.jpg`**. Tên ảnh và byte nguồn được giữ nguyên, không lồng `001407/001407/`. ZIP vẫn còn nguyên SHA-256. Lần kiểm tra thứ hai tái dùng đủ 221 ảnh, không giải nén trùng.

```text
data_raw/cadp/
├── frames/
│   ├── 001407-20261019T121452Z-1-001.zip   # giữ nguyên
│   └── 001407/0.jpg … 220.jpg             # một bộ ảnh nguồn duy nhất
├── pilot_1407/1407.mp4, 1407.txt          # demo đã vẽ / VATIC tác giả
└── reference_code/CarCrash_forecasting_and_detection-master.zip
data_samples/cadp/cadp_001407_clean_display20fps.mp4
outputs/
├── annotation_preview/cadp_001407_clean_author_display20fps.mp4
├── detection/cadp_001407_clean_display20fps/
│   └── cadp_001407_clean_display20fps_detection.mp4
├── tracking/cadp_001407_clean_display20fps/
│   └── cadp_001407_clean_display20fps_tracking.mp4
└── audits/
    ├── cadp_001407_clean/                 # audit đầu, trước kiểm trực quan
    ├── cadp_001407_clean_2/               # audit đã kiểm + tạo video
    └── cadp_clean_manifest_update/manifest_before.csv
```

Ổ còn khoảng 1,17 GB trước lấy ảnh; chuỗi cần 62.140.870 byte. Script dự trù thêm 640 MiB cho đầu ra và khoảng trống. Không lấy thêm chuỗi/dataset hay sao chép cả bộ.

## Ảnh có sạch và khớp nhãn không?

- **Giải mã toàn bộ:** 221/221 ảnh đọc được, cùng 1280×720, số frame liên tục 0–220, không thiếu hoặc trùng số. [Danh mục/hash từng ảnh](../outputs/audits/cadp_001407_clean_2/images.csv).
- **Kiểm trực quan 9 mốc:** 0, 60, 95, 96, 110, 130, 131, 180, 220. Không thấy bbox, ID hay viền Matplotlib trong các ảnh nguồn đã xem; watermark nguồn “CAR CRASHES TIME”/18+ vẫn còn. Đây là kiểm tra trực quan lấy mẫu, không phải khẳng định đã xem từng pixel của cả 221 ảnh.
- **Mapping:** ảnh `i.jpg` ↔ frame `i` trong TXT ↔ frame `i` trong demo tác giả. Mã `data/draw_1407.py` trong ZIP tham chiếu sắp tên ảnh bằng số và dùng chỉ số vòng lặp cho frame TXT. Cặp demo/TXT trùng byte với bản trong ZIP tác giả. Dải frame, kích thước native, toàn bộ bbox và cảnh ở 9 mốc đều khớp; không chỉ dựa vào tên `1407`/`001407`.
- Ảnh đối chiếu gồm ba cột: **ảnh sạch → TXT vẽ trực tiếp lên ảnh sạch → vùng ảnh phục hồi từ demo**. Phép affine chỉ dùng cho việc so với demo 2400×1200; annotation trên ảnh sạch dùng nguyên tọa độ TXT 1280×720.
- [Bảng đối chiếu lân cận ±3 frame](../outputs/audits/cadp_001407_clean_2/mapping_checks.csv): cùng frame có MAE khoảng 3,60–5,70 trên vùng đã che bbox/chữ. 8/9 mốc có offset tốt nhất bằng 0; frame 130 gần hòa với ảnh 129 (chênh khoảng 0,015 mức màu/255). Không dịch mapping vì chênh lệch nhỏ này. Kết luận dựa thêm vào mã tác giả, thứ tự đầy đủ và kiểm trực quan; MAE không phải metric chất lượng model hay bằng chứng chính xác onset/end.

Mở [tổng quan 9 ảnh sạch](../outputs/audits/cadp_001407_clean_2/clean_contact_sheet.jpg), rồi các mốc [95](../outputs/audits/cadp_001407_clean_2/comparison_095.jpg), [96](../outputs/audits/cadp_001407_clean_2/comparison_096.jpg), [130](../outputs/audits/cadp_001407_clean_2/comparison_130.jpg), [131](../outputs/audits/cadp_001407_clean_2/comparison_131.jpg). Mốc đầu/cuối: [0](../outputs/audits/cadp_001407_clean_2/comparison_000.jpg), [220](../outputs/audits/cadp_001407_clean_2/comparison_220.jpg).

**FPS nguồn vẫn chưa xác minh.** `duration_segments.txt` ghi 11,959 giây cho 001407, demo render là 221 frame/25 FPS = 8,84 giây; `fps.pdf` chỉ có biểu đồ. Không suy ngược FPS nguồn bằng cách chia hai số này. Video mới chọn **20 FPS để trình chiếu**, dài 11,05 giây; đây không phải thời gian sự kiện gốc, không dùng để kết luận vận tốc/độ trễ hoặc đổi onset/end sang giây.

## Video và bảng cần mở

| File | Mục đích |
| --- | --- |
| [cadp_001407_clean_display20fps.mp4](../data_samples/cadp/cadp_001407_clean_display20fps.mp4) | Bản xem từ JPG, không thêm bbox/chữ/viền; đầu vào của model |
| [cadp_001407_clean_author_display20fps.mp4](../outputs/annotation_preview/cadp_001407_clean_author_display20fps.mp4) | Annotation **tác giả**: GT ID, loại đối tượng, `Colliding`; đỏ = Colliding, xanh = đối tượng khác, xám = FarRegion |
| [detection.mp4](../outputs/detection/cadp_001407_clean_display20fps/cadp_001407_clean_display20fps_detection.mp4) | Dự đoán bbox phương tiện của YOLOv8n pretrained trên bản sạch |
| [tracking.mp4](../outputs/tracking/cadp_001407_clean_display20fps/cadp_001407_clean_display20fps_tracking.mp4) | Dự đoán phương tiện và ID tạm của ByteTrack trên bản sạch |
| [author_annotations.csv](../outputs/audits/cadp_001407_clean_2/author_annotations.csv) | 4.641 dòng VATIC gốc kèm tọa độ chuẩn hóa; chưa phải nhãn B0 |
| [objects.csv](../outputs/audits/cadp_001407_clean_2/objects.csv) / [colliding_intervals.csv](../outputs/audits/cadp_001407_clean_2/colliding_intervals.csv) | 21 đối tượng và khoảng Colliding theo từng GT ID, chỉ ghi frame |

Bảng annotation có `source_frame`, `source_image`, `gt_id`, `xmin/ymin/xmax/ymax`, `object_type`, `outside`, `visible`, `occluded`, `generated`, `colliding`, `attributes`, `cx_norm/cy_norm/w_norm/h_norm`. `visible=1-outside` là cờ hiện diện theo VATIC, không có nghĩa không bị che khuất; xem riêng `occluded`. `generated` giữ cờ nội suy của nguồn, script không tạo thêm nội suy. Bảng giữ cả dòng outside; preview không vẽ chúng. `FarRegion` không phải class xe hoặc vùng accident.

GT ID **0 Bus** và **2 Car** có `Colliding` ở **96–130**, gồm cả hai đầu, 35 frame mỗi đối tượng. Người dùng đã xác nhận đúng xe và khoảng frame này rõ ràng/phù hợp, giữ riêng lớp rà với annotation tác giả. Chưa có timing giây. ID ByteTrack không cùng hệ ID với GT; không so trực tiếp số ID hoặc xem video model là phát hiện tai nạn.

## Xác nhận người dùng và manifest

[Phiếu xác nhận có phạm vi](../data/reviews/2026-10-19-user-confirmations.json) gắn hash đúng các video đã xem:

- Ba chuỗi DETRAC **đầy đủ** MVI_20011, MVI_20012, MVI_20032: `collision_label=negative`, `user_review_status=reviewed_full_sequence_no_collision`. Đây là xác nhận người dùng, không suy ra từ XML xe.
- Clip MVI_20011_first_10s là ảnh 1–250 của chuỗi đã xem 1–664: kế thừa âm tính từ parent, ghi `inherited_from_reviewed_full_sequence`, không coi là một lần xem độc lập.
- CADP: phiếu đầu chỉ xác nhận hộp đỏ đúng xe; **phiếu mới xác nhận cả 96–130 theo frame**, `vehicles_and_colliding_frames_confirmed`, nhãn dự án `positive`, GT ID 0 và 2. `onset_s/end_s` vẫn trống, không suy FPS nguồn. Phiếu đầu/report cũ giữ lịch sử; trạng thái hiện tại theo [phiếu mới](../data/reviews/2026-10-19-cadp-001407-frame-confirmation.json).
- Ba mẫu cũ YSGhwU9XxuY, ZCQcKnFSJvg, zVzXEht1aME giữ nguyên mọi giá trị đã có.

[Manifest](../data/manifest.csv) giữ **36 cột**, tăng 9 → **12 asset**: thêm chuỗi JPG, video sạch và preview mới. Thư mục JPG dùng `asset_role=clean_image_sequence`, không có SHA cho “cả thư mục” hoặc FPS giả; hash từng ảnh ở inventory. `duration_s/fps` trên MP4 mới chỉ là metadata trình chiếu. Mọi split vẫn `unassigned`. `source_sequence=001407` nối các alias CADP sau kiểm chứng; `derived_from` giữ đúng nguồn từng asset. Prediction video liên kết bằng đường dẫn input/output và hash trong [validation.json](../outputs/audits/cadp_001407_clean_2/validation.json).

Backup nguyên byte trước sửa: `outputs/audits/cadp_clean_manifest_update/manifest_before.csv`; [nhật ký đăng ký](../outputs/audits/cadp_clean_manifest_update/report.json). Việc chuẩn hóa khoảng trắng CSV không thay giá trị ba mẫu cũ. Báo cáo cũ là snapshot trước xác nhận mới, không sửa lịch sử.

## Tái lập và kiểm tra

```powershell
.\.venv\Scripts\python.exe -B scripts/prepare_cadp_frames.py --archive data_raw/cadp/frames/001407-20261019T121452Z-1-001.zip --presentation-fps 20
# Mở ảnh đối chiếu trước; cờ dưới đây là kiểm trực quan của người chạy, không duyệt onset/end.
.\.venv\Scripts\python.exe -B scripts/prepare_cadp_frames.py --archive data_raw/cadp/frames/001407-20261019T121452Z-1-001.zip --presentation-fps 20 --visual-check-confirmed
.\.venv\Scripts\python.exe -B scripts/run_detection.py data_samples/cadp/cadp_001407_clean_display20fps.mp4 --device auto --imgsz 640 --output-dir outputs/detection
.\.venv\Scripts\python.exe -B scripts/run_tracking.py data_samples/cadp/cadp_001407_clean_display20fps.mp4 --device auto --imgsz 640 --output-dir outputs/tracking
.\.venv\Scripts\python.exe -B scripts/update_manifest_reviews.py --cadp-report outputs/audits/cadp_001407_clean_2/report.json --review data/reviews/2026-10-19-user-confirmations.json
```

Không cần chạy lại để xem kết quả. Script chuẩn bị thêm hậu tố cho output đã có; khi chạy lại phải dùng đường dẫn report/video thực tế. Script cập nhật manifest chỉ tái dùng đăng ký giống hệt, từ chối cùng ID nhưng khác asset; không tự ghi đè review. Không sửa pipeline suy luận: vẫn `yolov8n.pt`, `bytetrack.yaml`, device auto, imgsz 640. Tracker giữ trạng thái trong video và khởi tạo mới ở lần chạy video khác; 20 FPS trình chiếu không chứng minh motion theo thời gian thực.

Đã kiểm cú pháp 13 file Python, import ba module chuẩn bị/đăng ký, `--help` năm script liên quan; kiểm từ chối ZIP traversal, file khác nội dung và mapping chưa đạt; kiểm đăng ký lại không trùng. Đã giải mã hết 221 JPG và đọc lại **cả bốn MP4 mới**, mỗi file đủ 221 frame, 1280×720, 20 FPS. [Báo cáo kỹ thuật](../outputs/audits/cadp_001407_clean_2/report.json), [kết quả kiểm tra](../outputs/audits/cadp_001407_clean_2/validation.json). Chưa đo AP, tracking accuracy hay metric va chạm.

## B0 đã sẵn sàng chưa? Việc tiếp theo

**Chưa train.** B0 là YOLO fine-tune **bbox vùng tai nạn**. Đã có [quy tắc cụ thể và 35 hộp dẫn xuất đề xuất](b0_label_protocol.md), không tự coi hộp bao các xe thành GT accident đã duyệt. Bộ chuyển đổi đã chuẩn hóa đủ cờ/vùng ignore và giữ frame ngoài phần đã rà là unknown, chưa tạo split/dataset train. [Bảng điều kiện B0](../data/b0_readiness.json).

1. Xác nhận xe/96–130 của 001407 **đã xong**, không yêu cầu mở/rà lại. Bước quyết định còn lại là chọn quy tắc hình học **vùng accident cho B0** dựa trên đề xuất cụ thể, áp dụng nhất quán cho các chuỗi sau.
2. Nếu cần đánh giá theo giây/vận tốc: bổ sung bảng FPS/timestamp **của riêng chuỗi 001407**, hoặc video nguồn sạch có quan hệ lấy mẫu frame được ghi rõ. Không đoán FPS từ thời lượng metadata.
3. Thống nhất với giảng viên quy tắc vùng accident cho B0 và rà pilot ít nhất 10 ví dụ như kế hoạch. Một sự kiện + ba chuỗi âm khác miền chưa đủ tạo split/benchmark; XML DETRAC còn ghi camera `unstable`, không mặc định cùng miền CCTV cố định.
4. [Đã kiểm nguồn tác giả trực tuyến](cadp_pilot_sources.md); hiện chưa tìm được VATIC bổ sung đủ để chọn cặp mới. Cần export/mapping trước khi chọn thêm ảnh sạch tương ứng, không tự yêu cầu gán lại bbox bằng tay hoặc tải toàn extracted_frames. Thêm nhiều sự kiện/âm/hard negatives và kiểm nhóm camera/nguồn/sự kiện trước split/train sau này.

Buổi này không tải dataset, không tạo split, không train và không thay model. Ảnh sạch đã đủ để tiếp tục rà/chuẩn hóa pilot; việc dùng làm tập huấn luyện B0 vẫn bị chặn bởi các điều kiện trên.
