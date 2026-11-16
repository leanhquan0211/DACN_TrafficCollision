# Suy luận phương tiện và cache theo frame — 14/11/2026

Đã hoàn tất môi trường suy luận CPU và chạy YOLOv8n/ByteTrack trên pilot phục hồi. Model/config giữ theo README: torch 2.11.0+cpu, torchvision 0.26.0+cpu, Ultralytics 8.4.178, lap 0.5.13, numpy 2.5.2, OpenCV package 5.0.0.93, FFmpeg 7.0.2. Python 3.12.16. [Freeze môi trường CPU](../logs/requirements-installed-2026-11-14-cpu.txt).

## Chạy lại

```bash
export PATH="$PWD/.venv/bin:$PATH"
.venv/bin/python scripts/check_environment.py
.venv/bin/python scripts/run_all.py data_samples/cadp/cadp_001407_clean_display20fps.mp4 --device cpu --cpu-threads 4 --imgsz 640 --timing-status presentation_only --output-dir outputs/inference_new
.venv/bin/python scripts/run_tracking.py data_samples/ua_detrac/restored_2026-11-12/MVI_20011.mp4 --device cpu --cpu-threads 4 --imgsz 640 --timing-status verified_source --timing-evidence outputs/audits/detrac_preparation/report.json --output-dir outputs/inference_new
.venv/bin/python scripts/check_inference_outputs.py outputs/inference_new
```

`--timing-status verified_source` yêu cầu file bằng chứng local có hash được ghi trong report. Đây là khai báo của người vận hành dựa trên nguồn, không phải cách tự suy FPS thật từ MP4. Với CADP 001407, dùng `presentation_only`; `source_time_s` luôn để trống. Video chưa rà timing dùng mặc định `unknown`.

## Ba output cho mỗi lượt

- `*.mp4`: video bbox/class; tracking có thêm ID.
- `*.frames.jsonl`: mỗi frame một dòng, kể cả không có đối tượng. `frame_index` bắt đầu 0 trong **video đầu vào**. CADP raw cũng bắt đầu 0; DETRAC raw bắt đầu 1 và quan hệ video↔ảnh nằm trong report chuẩn bị nguồn.
- `*.run.json`: chỉ xuất `complete=true` sau khi encoder thành công và số frame đọc khớp metadata. Giữ hash video nguồn/trọng số/cache/output/code, class xe, config ByteTrack đầy đủ, tham số inference thực tế, package versions, timing evidence và thống kê runtime.

Tên đã có MP4/cache/report/file dở hoặc đang được giữ sẽ nhận hậu tố mới. `H264Writer` ghi H.264 qua stderr file tạm, tránh nghẽn pipe; lỗi decode/encoder không được công bố thành lượt complete. Chỉ dùng cache khi report complete và `check_inference_outputs.py` đạt.

Mỗi quan sát có `bbox_xyxy`, `bbox_cxcywh_norm`, class/confidence, `track_id`, `missing_mask=0` và `track_age_observations`. Nhánh detection giữ `track_id=null`. Frame thiếu track có `missing_tracks` với ID/gap/mask=1, không bịa bbox. Export chỉ giữ trạng thái missing tối đa 30 frame; đây là giới hạn bộ nhớ cache, không phải đo chất lượng tracker. Mỗi run tạo model/clock mới, không nối ID giữa camera/video.

Clock dùng PTS của container. Nếu PTS lỗi trên timing chưa xác minh, có thể dùng `frame_index/container_fps`, ghi rõ `timestamp_origin`; source seconds vẫn null. Với `verified_source`, PTS lỗi hoặc không tăng làm lượt chạy thất bại thay vì tự tạo giây nguồn.

## Kết quả đã chạy

| Video | Nhánh | Frame đọc và xuất | ID tracker khác nhau |
| --- | --- | ---: | ---: |
| MVI_20011_first_10s | detection | 250 | 0 |
| MVI_20011_first_10s | tracking | 250 | 59 |
| CADP 001407 sạch | detection | 221 | 0 |
| CADP 001407 sạch | tracking | 221 | 31 |
| MVI_20011 đầy đủ | tracking | 664 | 151 |
| MVI_20012 đầy đủ | tracking | 936 | 191 |
| MVI_20032 đầy đủ | tracking | 437 | 91 |

Đây là số đếm output, chưa là accuracy/IDF1. Các MP4 đã được giải mã lại đầy đủ, so số frame/kích thước/FPS với cache và kiểm hash input/weights/output. Clip 10 giây và video đầy đủ dùng cùng nguồn, không đếm thành mẫu độc lập. [Thư mục output](../outputs/inference_2026-11-14/).

Phát hiện khi kiểm report: Ultralytics tự đặt lại CPU threads thành 8 trong setup dù CLI yêu cầu 4. Các lượt đầu ghi **giá trị thực tế 8** trong report. Đã sửa bằng callback `on_predict_start`; chạy lại detection/tracking trên clip 250 frame để kiểm cả `cpu_threads_requested` và `cpu_threads` đều 4. Output kiểm lại nhận hậu tố `_2`, giữ lượt trước và source snapshot làm lịch sử.

Runtime trong report là **offline**, có inference đầu còn cold, decode/render/cache/encoder; không gồm tải model và hash sau chạy. Không có đo streaming, queue lag hay GPU RTX 3050 Ti trong lượt này. Detection dùng confidence hiệu lực 0.25, tracking dùng 0.1 theo mặc định Ultralytics; các con số không tạo thành so sánh accuracy công bằng.

## Lỗi quan sát được ở hai xe đã xác nhận

Đã đối chiếu bbox tác giả cho GT 0 Bus và GT 2 Car trong 35 frame 96–130. Ảnh [so track với GT ở 96/110/130](../outputs/audits/inference_2026-11-14/cadp_track_review.jpg), [bảng chẩn đoán](../outputs/audits/inference_2026-11-14/cadp_participant_class_diagnostics.csv).

Phương pháp debug: ghép hai participant với hai quan sát khác nhau bằng tổng IoU lớn nhất, không lọc class. Ngưỡng IoU 0.3 chỉ dùng lọc hiển thị debug, chưa chọn bằng validation, liên kết vẫn `association_reviewed=false`.

- GT 0 có đề xuất track ID 1 đạt ngưỡng ở 34/35 frame: 21 lần trả class `bus`, **13 lần trả class `car`**. Frame 108 không có ứng viên đạt ngưỡng.
- GT 2 có đề xuất track ID 19 ở 35/35 frame, class `car`.
- Báo cáo debug ban đầu lọc cùng class chỉ thấy bus ở 21/35 frame. Ảnh frame 110 cho thấy ID 1 vẫn tồn tại nhưng class đổi thành car; vì vậy không được diễn giải mọi lần thiếu class bus thành mất track.

Đây chưa là GT↔track mapping đã rà hoặc kết quả đánh giá tracker. Nó nêu lỗi class thay đổi cần xét khi thiết kế features/candidate. Chưa đủ bằng chứng để đổi model/tracker; không suy contact chỉ từ IoU/ID.

## Điều kiện còn thiếu

Giai đoạn 1/B0 chưa hoàn thành: một sự kiện dương, quy tắc/35 vùng B0 còn chờ quyết định cụ thể, thiếu pilot đa sự kiện, camera/near-duplicate/hard negatives và split. Source FPS CADP chưa biết. Cache hiện phục vụ rà và tái lập phần suy luận; chưa phải dữ liệu temporal đã có nhãn để train verifier.
