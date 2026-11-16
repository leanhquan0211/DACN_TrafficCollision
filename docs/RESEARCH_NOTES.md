# Tìm hiểu và áp dụng vào đồ án — 14/11/2026

> **Cập nhật sau đó, 16/11:** đã chạy [B0 khả thi phần mềm](B0_FEASIBILITY.md), có checkpoint và phân tích lỗi train/validation. Kết quả yếu, gate nghiên cứu chưa đạt. Nội dung dưới ghi trạng thái tìm nguồn ngày14/11; “chưa train/checkpoint” bên dưới là lịch sử ở thời điểm đó.

## Vấn đề cần giải quyết

Demo vehicle inference đã chạy nhưng chưa có accident detector. Trước lượt này, pilot chỉ có một sự kiện CADP đã xác nhận, nhãn vùng còn là đề xuất; thiếu export VATIC bổ sung khiến việc huấn luyện B0 bị chặn. Người dùng yêu cầu chủ động tìm hiểu và làm tiếp, hạn dự kiến còn một tháng. Giữ câu hỏi nghiên cứu/thứ tự baseline trong README và XLSX, ưu tiên dữ liệu thực dùng được.

## Đọc nguồn gốc và rút ra quyết định

| Nguồn chính | Điều đã đối chiếu | Áp dụng / giới hạn |
| --- | --- | --- |
| [CADP — trang tác giả](https://ankitshah009.github.io/accident_forecasting_traffic_camera.html), [repo tác giả](https://github.com/ankitshah009/CarCrash_forecasting_and_detection) | Định hướng CCTV, object/temporal annotations và yêu cầu annotation riêng trong code | Không dùng JSON Stage1 hoặc tên folder thay cho bbox/cặp xe. Chưa có export bổ sung mới được kiểm chứng; không đếm tải lại 001407 thành sự kiện mới. Lượt gọi REST API bị rate-limit403, không lấy đó làm bằng chứng repo hiện không có nhãn. |
| [STTAD — paper tác giả, mục III.B và Table II](https://www.dsg.tuwien.ac.at/team/snastic/publications/ITSC25_0424_FI.pdf) | Bài báo dùng bbox vùng sự kiện bao hai bên tham gia; mốc bắt đầu dựa tiếp xúc và end dựa kết thúc chuyển động tương đối/clip | Có cơ sở tham khảo cho nhãn vùng B0. Đây là định nghĩa nguồn, chưa tự duyệt các proposal CADP của project. Không lấy kiến trúc STFN hay điểm paper làm kết quả đồ án. |
| [STTAD — repo](https://github.com/ZTR02/STTAD), [phản hồi owner về phát hành](https://github.com/ZTR02/STTAD/issues/1) | Repo mô tả mẫu minh họa; cây file/nhãn đã được kiểm trực tiếp ở commit cố định | Lấy riêng bốn chuỗi xe–xe để audit. Không tuyên bố đã có cả benchmark hoặc split chính thức đủ chạy. |
| [ACCIDENT — repo tác giả](https://github.com/accidentbench/ACCIDENT), [hướng dẫn dataset](https://github.com/accidentbench/ACCIDENT/blob/main/dataset/README.md) | Có hướng CCTV temporal/spatial/type; đường tải chính thức qua Kaggle và yêu cầu xác thực trong hướng dẫn | Nguồn dự phòng cần kiểm schema/quyền truy cập; chưa tải hay đưa vào manifest. Không lẫn với dự án VLM AccidentBench có tên gần giống. |
| [TADBench chính thức](https://github.com/UnicomAI/UnicomBenchmark/tree/main/TADBench), [AccidentDet3D](https://github.com/accident-dataset/AccidentDet3D) | Có nguồn CCTV; TAD README ghi tổng mẫu không nhất quán với các thành phần; AccidentDet3D có ROS/multi-sensor stack | Chưa chọn làm thay thế; không chuyển stack chỉ vì có code/model mới. Số lượng/khả năng truy cập cần kiểm dữ liệu trước khi dùng. |

Các đường dẫn được truy cập trong lượt này. Chỉ nguồn tác giả/paper chính được dùng làm căn cứ; metadata, nguồn byte và đo trên máy phân biệt riêng. Không gửi email/issue cho tác giả thay người dùng.

## Kết quả thực tế từ STTAD

**Nguồn:** `ZTR02/STTAD`, commit `21f3f5fea50b071f1db61186b481c2a7ccf525c9`. GitHub REST API trả403, nên dùng `ls-remote` rồi partial clone `--filter=blob:none --no-checkout` để đọc cây file; `.git` metadata khoảng228KiB. Không checkout/tải toàn ảnh. Khi liệt kê dùng `git ls-tree -r --full-tree HEAD`, không dùng `-l` gây lấy blob kích thước.

[Registry chọn lọc](../data/registries/sttad_selected_sources.json) giữ Git blob của **212 tệp**, tải **83.058.778 byte** từ raw URL ghim commit. Mỗi file kiểm SHA-1 theo object Git `blob <length>\0<body>`; audit tải ghi thêm SHA-256/kích thước. Check Git blob chứng minh byte khớp nguồn, không chứng minh chất lượng nhãn hoặc giấy phép tái phân phối.

| Chuỗi | Ảnh giải mã được | Frame có bbox nguồn | Frame thiếu nhãn |
| --- | --- | --- | --- |
| T-T_crash_1 | 26 | 12 | 14 |
| T-T_crash_2 | 50 | 10 | 40 |
| V-V_crash_0 | 50 | 7 | 43 |
| V-V_crash_1 | 50 | 2 | 48 |
| Tổng | **176** | **31** | **145** |

Có31 region trong31 frame; không nhân sự kiện theo số frame. Bốn chuỗi là bốn nguồn ứng viên, **chưa cộng thành bốn sự kiện độc lập đã duyệt** trong manifest. 145 frame thiếu annotation giữ `unknown_no_label`, không xuất empty negative label. Không đổi B0 readiness, CADP review, manifest hoặc split hiện có.

Các nhãn raw được kiểm trong subset là `class_id xmin_px ymin_px xmax_px ymax_px`: T–T class6, V–V class11. Đây là **diễn giải định dạng từ dữ liệu thực**, có bounds/overlay làm bằng chứng, khác cách mô tả bbox center/size ở mức khái niệm trong paper. Parser không đoán YOLO, không tự clip bbox. Rà toàn31 bbox qua hai bảng ảnh cho thấy vùng đặt ở khu vực tương tác của xe trong các ảnh mẫu; đây là kiểm kỹ thuật bởi agent, **không phải người dùng/giảng viên duyệt temporal/cặp xe** hoặc chứng minh mọi ranh giới event đã đúng.

### Lỗi và giới hạn nguồn đã kiểm được

1. `rgb-images/V-V_crash/V-V_crash_0/00051.jpg` thực chất10 byte văn bản `0,004-049`; chuỗi V-V_crash_1 có tệp tương tự18 byte. Giữ nguyên nguồn, xuất danh sách loại trừ, không đưa thành frame. Không diễn giải tự động chúng thành onset/end vì chưa rõ schema và không khớp độ phủ label hiện có.
2. Nhóm `labels/V-T_crash/` chứa100 tệp **`.jpg`**, tên chuỗi `V-P_crash_3/4`, trong khi ảnh V–T dùng `V-T_crash_0/2`. Mẫu đã tải ở `labels/V-T_crash/V-P_crash_3/00001.jpg` đúng Git blob và là JPEG. **Đính chính nhận định ban đầu:** file gốc này không là `.txt`; chỉ tên bản lưu tạm có đuôi `.txt`. Vì thiếu ánh xạ/nhãn văn bản, không tự đổi tên/copy sang V–T.
3. Cây repo có1293 path JPG dưới `rgb-images/`; dưới `labels/` có197 TXT và200 JPG (100 JPG ở V–P,100 ở V–T). Đây là đếm file metadata, không phải1293 ảnh đã giải mã hoặc397 nhãn văn bản. Chỉ212 file đã chọn được tải/kiểm byte.
4. `trainlist.txt` có35 tham chiếu, chỉ12 tồn tại trong cây hiện có (thuộc T-T_crash_1); `testlist.txt` có23 tham chiếu và0 tồn tại. Không gán các mẫu unlisted vào test và không dùng mốc train/test của paper thay cho file thực tế.
5. Không có source FPS/timestamp đáng tin cậy cho chuỗi đã lấy. Overlay ngày/giờ là manh mối, không đủ chuyển frame index thành giây. Camera/event ID gốc và near-duplicates chưa xác minh; không có test split khóa.
6. Các ảnh có watermark/overlay từ nguồn. Cần kiểm bias camera/dataset khi bổ sung DETRAC làm âm; tránh mô hình học dấu nguồn thay vì tai nạn.

## Code và cách tái lập

```bash
# Chỉ xem giới hạn tải; chưa gọi mạng
.venv/bin/python -B scripts/download_sttad_subset.py
# Tải chọn lọc / tái dùng đúng fingerprint; không ghi đè file khác byte
.venv/bin/python -B scripts/download_sttad_subset.py --download
# Kiểm toàn file, decode, bounds, pairing, tạo CSV và bảng ảnh mới
.venv/bin/python -B scripts/prepare_sttad_pilot.py
.venv/bin/python -B -m unittest discover -s tests -p test_sttad_pilot.py -v
```

File gốc ở `data_raw/sttad/author_samples/`; nhãn/ảnh giữ nguyên đường dẫn tác giả. Script in thư mục output thực tế, tăng hậu tố khi đã tồn tại. Lượt thành công có `frames.csv`, `accident_regions.csv`, `excluded_source_files.csv`, contact sheet, `review_all_01.jpg`, `review_all_02.jpg`, `report.json` dưới `outputs/audits/sttad_pilot_2026-11-14_3/`. Lượt đầu dừng đúng vì hai JPG không decode được; lượt sau ghi exclusion rõ và chưa bật train. Audit tải ở `outputs/audits/sttad_download_2026-11-14/`; hồ sơ tìm nguồn ở `outputs/audits/research_sources_2026-11-14/`.

Module `src/sttad_pilot.py` kiểm cây nguồn, registry, Git blob, nội dung nhãn và pixel→normalized. Bảy test mới bao phủ nhãn JPEG/empty/NaN/sai class/outside, tải lỗi/giới hạn byte/bảo toàn mismatch, đường dẫn và pipeline fixture giữ frame thiếu nhãn unknown/loại text-JPG mà không sửa nguồn.

## Việc tiếp theo để có B0 thật

Chốt quy tắc vùng, xác minh diễn biến đầy đủ/onset/end và nhóm camera/sự kiện, bổ sung đủ positives/negatives cùng miền, rồi chia nhóm trước train. Mẫu công khai STTAD quá ít/sparse để gọi là benchmark nghiên cứu. Có thể dùng để kiểm importer/region convention và thiết kế phiếu review; không train trên vài frame rồi báo đã nghiệm thu collision detection. Nếu nguồn công khai không đủ, lựa chọn mở rộng phải được ghi với căn cứ và phạm vi rõ, không đổi mô hình để che vấn đề dữ liệu.

Chưa có experiment accident mới, checkpoint accident hoặc metric event. Bộ Word/slide/ZIP tạo trước lượt này vẫn là snapshot demo cũ; không tự biến dữ liệu mới thành kết quả trong báo cáo đã đóng gói.
