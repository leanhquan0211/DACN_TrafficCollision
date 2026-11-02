# Chuẩn bị mẫu CADP 1407 và UA-DETRAC — 19/10/2026

> **Tài liệu chi tiết/lịch sử:** ưu tiên [mục lục hiện hành](README.md), [policy nhãn B0](b0_label_protocol.md) và [trạng thái dữ liệu mới nhất](b0_pilot_audit.md). Các số liệu/chỉ dẫn cũ bên dưới giữ bối cảnh lúc tạo, không thay hướng public đã chọn.

> **Cập nhật mới nhất trong ngày:** người dùng xác nhận CADP đúng xe và **Colliding 96–130 theo frame**, ba DETRAC đầy đủ âm tính. [Nhãn ứng viên B0 và chỉ mục âm đã chuẩn bị](b0_label_protocol.md), [kết quả tìm VATIC bổ sung](cadp_pilot_sources.md), [nhật ký ngày](../progress/2026-10-19.md). Không yêu cầu rà lại 001407. [Hướng dẫn ảnh/video sạch đã có](cadp_001407_clean.md). Các audit trước xác nhận giữ nguyên như snapshot lịch sử.

## Dữ liệu thực sự có trong project

Đã tìm thấy **`1407.mp4` và `1407.txt`**, không có file `1047`. Không đổi tên hoặc ghép file gần giống. Ngoài mẫu này, đã kiểm tra PDF README/paper CADP, JSON stage 1, `duration_segments.txt`, `fps.pdf`, ZIP mã tham chiếu, ZIP ảnh DETRAC và **hai ZIP XML DETRAC**. Lượt sau đã tìm thấy riêng ZIP frames 001407; không có căn cứ coi đã tải toàn bộ extracted_frames hoặc các gói CADP khác.

```text
data_raw/
├── cadp/
│   ├── pilot_1407/1407.mp4, 1407.txt
│   ├── frames/001407-20261019T121452Z-1-001.zip
│   │          001407/0.jpg … 220.jpg
│   ├── documentation/CADP_Dataset_Release_ReadMe.pdf
│   │                  CADP_IEEE_Camera_Ready_Final.pdf
│   ├── annotations_stage1/annotations_1531762138.1303267.json
│   ├── metadata/duration_segments.txt, fps.pdf
│   └── reference_code/CarCrash_forecasting_and_detection-master.zip
└── ua_detrac/
    ├── DETRAC-Images.zip
    ├── DETRAC-Images/
    │   ├── MVI_20011/img00001.jpg … img00664.jpg
    │   ├── MVI_20012/img00001.jpg … img00936.jpg
    │   └── MVI_20032/img00001.jpg … img00437.jpg
    └── annotations/DETRAC-Train-Annotations-XML.zip
                   DETRAC-Test-Annotations-XML.zip
```

Ảnh đã lấy giữ nguyên `DETRAC-Images/MVI_*/img*.jpg` như trong ZIP. Không di chuyển hoặc nhân đôi cả bộ. `outputs/<tên-video>/` cũ được giữ nguyên; kết quả lượt này dùng các thư mục theo loại `outputs/annotation_preview/`, `outputs/detection/`, `outputs/tracking/`, `outputs/audits/`. Hai quy ước đối chiếu bằng tên video, không tạo bản sao dữ liệu nguồn.

`.gitignore` đã có `data_raw/**`, `data_samples/**`, `outputs/**`; bổ sung `*.zip`, `*.mp4`, `/DETRAC-Images/` để tránh thêm nhầm archive/video ngoài các thư mục đó. Workspace hiện **chưa có `.git/`**, nên đây là kiểm tra quy tắc ignore, chưa phải xác nhận trạng thái Git index. Code, config, manifest và docs có thể đưa vào Git sau này; media lớn và audit đầu ra bị ignore.

## CADP: format và căn chỉnh đã kiểm tra

`prepare_cadp_pilot.py` đối chiếu với hàm `read_vatic` trong ZIP mã tác giả. Một dòng TXT có dạng:

```text
track_id x1 y1 x2 y2 frame outside occluded generated "label" ["attribute" ...]
```

Bbox là `xyxy`, frame bắt đầu từ **0**. `outside=1` không được vẽ; `occluded` và `generated` vẫn được giữ trong báo cáo, không tự tạo nội suy mới. Đọc token bằng `shlex` để không tách sai nhãn/thuộc tính có khoảng trắng. `FarRegion` là vùng loại trừ của tác giả, không phải xe.

Kết quả: **4.641 dòng, 21 ID**, mỗi ID có đủ frame 0–220. Gồm 1 Bus, 11 Car, 8 Person, 1 FarRegion. Có 70 dòng mang `Colliding`:

| ID tác giả | Lớp | Khoảng frame Colliding, gồm cả hai đầu | Số frame |
| --- | --- | --- | ---: |
| 0 | Bus | 96–130 | 35 |
| 2 | Car | 96–130 | 35 |

Bảng lượt đầu: `outputs/audits/cadp_1407/objects.csv` và `colliding_intervals.csv`. Có annotation gốc/chuẩn hóa tại `outputs/audits/cadp_001407_clean_2/`, công cụ chuẩn hóa B0 mới tại `data/processed/b0_proposals/001407/`. Nhãn tác giả giữ nguyên; [phiếu rà mới](../data/reviews/2026-10-19-cadp-001407-frame-confirmation.json) xác nhận xe/96–130 theo frame. Không tự điền giây hoặc dùng làm dự đoán model.

Video đọc đủ **221 frame, 2400×1200, 25 FPS, 8,84 giây**. Nó đã có bbox/ID và viền trắng in sẵn. Cả MP4 và TXT đều **trùng byte** với `data/1407.mp4` và `data/1407.txt` trong ZIP tham chiếu tác giả. `data/draw_1407.py` tạo ảnh Matplotlib 8×4 inch, DPI 300; script `makevideo_1407.sh` ghép ảnh này thành video.

Vì vậy không áp tọa độ TXT trực tiếp lên toàn ảnh 2400×1200. [Config kiểm chứng](../configs/cadp_1407_preview.json) lưu hash hai file, canvas annotation 1280×720 và phép ánh xạ vào vùng ảnh render. Kích thước này ban đầu suy từ bố cục render/miền tọa độ; lượt có ảnh sạch đã xác nhận độc lập cả 221 JPG là 1280×720. Công thức dưới chỉ dùng với demo, không áp lên ảnh sạch:

```text
x_video = 1.2833333333 × x_annotation + 409.3083333333
y_video = 1.2833333333 × y_annotation + 144.6416666667
```

Đã đối chiếu các hộp ID 0/2 với hộp in sẵn ở frame 0, 96, 130, 220. Script kiểm tra hash, canvas, phạm vi tọa độ và tất cả frame trước khi dùng mapping. **Mapping chỉ dành cho đúng demo này**; không suy rộng sang video khác. Bản preview giữ nguyên khung hình gốc, vẽ đỏ cho `Colliding`, xanh cho đối tượng nhìn thấy khác và xám cho FarRegion, có banner “AUTHOR ANNOTATIONS — NOT MODEL PREDICTION”. Vì bbox/ID cũ đã nằm trong pixel, **cả nguồn demo và preview không phải ảnh sạch để train/evaluate detector**.

`duration_segments.txt` có dòng `001407.mp4 11.959000`, khác thời lượng 8,84 giây của demo. `fps.pdf` là biểu đồ, không cung cấp bảng FPS riêng của 1407. Do đó 25 FPS chỉ xác nhận thời gian phát của **bản render**; chưa xác minh timing của frames gốc. Có thể tua preview tới khoảng 3,84–5,20 giây để xem màu đỏ, nhưng không báo các giây này là onset/end của tai nạn trong video gốc.

README CADP địa phương nói JSON stage 1 đánh dấu biên đoạn trong video YouTube, các bbox trong JSON đó là dummy. Không dùng bbox JSON stage 1 để thay VATIC hoặc làm bbox accident. Điều kiện sử dụng/trích dẫn đọc từ PDF README được giữ ở `data_raw/cadp/documentation/`.

## DETRAC: kiểm kê ZIP và tạo video

Central directory của `DETRAC-Images.zip` có **100 chuỗi, 140.131 JPG**, 9.849.591.986 byte ZIP, 9.842.424.283 byte ảnh khi giải nén. Không có README/FPS trong ZIP ảnh. Trước giải nén, ổ còn 28.438.917.120 byte. Chọn ba chuỗi, lấy **2.037 ảnh / 152.824.125 byte**, kiểm CRC từng ảnh với ZIP; không giải nén toàn bộ 9,8 GB. Danh mục 100 chuỗi nằm trong `outputs/audits/detrac_preparation/archive_sequences.csv`.

| Chuỗi | Ảnh đầu/cuối | Số ảnh = frame đọc lại | Kích thước | FPS | Thời lượng |
| --- | --- | ---: | --- | ---: | ---: |
| MVI_20011 | img00001–img00664.jpg | 664 | 960×540 | 25 | 26,56 s |
| MVI_20012 | img00001–img00936.jpg | 936 | 960×540 | 25 | 37,44 s |
| MVI_20032 | img00001–img00437.jpg | 437 | 960×540 | 25 | 17,48 s |

Đã kiểm toàn bộ ảnh được chọn: không thiếu số, không trùng số, không lỗi giải mã, kích thước nhất quán. Sắp bằng **số trong tên ảnh**, không sắp chuỗi ký tự. FPS **25** được xác minh từ mục 2 của [bài báo UA-DETRAC do tác giả công bố](https://arxiv.org/html/1511.04136#S2), cùng kích thước JPEG 960×540. Script vẫn cho phép `--fps-status assumed` khi chuẩn bị nguồn khác chưa có căn cứ, và lưu trạng thái này trong audit; không dùng video FPS giả định để báo thời gian/vận tốc.

Hai ZIP XML thực sự có tại `annotations/` chứa lần lượt 60 và 40 XML. Đã đọc riêng XML của ba chuỗi được chọn **ngay trong ZIP**, không giải nén cả gói: tên sequence và frame 1–664, 1–936, 1–437 khớp ảnh. Đây là nhãn bbox/ID/thuộc tính phương tiện; chưa vẽ hoặc đánh giá bbox XML với ảnh, chưa phải nhãn tai nạn. XML của cả ba ghi `camera_state="unstable"`, `sence_weather="sunny"` (giữ nguyên tên trường tác giả). Ban đầu nhãn dự án unknown/pending; **sau xác nhận người dùng đã xem toàn bộ**, ba chuỗi được ghi `negative`, có [phiếu rà](../data/reviews/2026-10-19-user-confirmations.json). Không suy nhãn từ XML. Tên archive có Train/Test là tên gói nguồn, không tạo split của project.

Clip `MVI_20011_first_10s.mp4` lấy từ MP4 đã ghép, gồm 250 frame đầu. Frame 0 của clip ứng với `img00001.jpg`; frame cuối ứng với `img00250.jpg`. Đã chạy detection và ByteTrack với **model cũ `yolov8n.pt`, device auto, imgsz 640**. Hai đầu ra mở/đọc lại được đủ 250 frame, 960×540, 25 FPS. Đây là thử phát hiện/theo dõi phương tiện; chưa đo accuracy hoặc kết luận có/không có tai nạn.

## Video cần mở trong VS Code

| Mục đích | Đường dẫn từ thư mục project |
| --- | --- |
| Xem annotation tác giả, đỏ khi Colliding | `outputs/annotation_preview/cadp_1407_author_annotations.mp4` |
| Xem toàn bộ ba chuỗi DETRAC đã lấy | `data_samples/ua_detrac/MVI_20011.mp4`, `MVI_20012.mp4`, `MVI_20032.mp4` |
| Video nguồn dùng thử model | `data_samples/ua_detrac/MVI_20011_first_10s.mp4` |
| Kết quả detection | `outputs/detection/MVI_20011_first_10s/MVI_20011_first_10s_detection.mp4` |
| Kết quả tracking | `outputs/tracking/MVI_20011_first_10s/MVI_20011_first_10s_tracking.mp4` |

## Script nào tạo file gì?

Chạy PowerShell tại thư mục gốc, dùng Python `.venv`:

```powershell
.\.venv\Scripts\python.exe scripts/prepare_cadp_pilot.py --preview-config configs/cadp_1407_preview.json
.\.venv\Scripts\python.exe scripts/prepare_detrac.py --sequences MVI_20011 MVI_20012 MVI_20032 --fps 25 --fps-status verified_source --fps-source 'https://arxiv.org/html/1511.04136#S2' --smoke-seconds 10
.\.venv\Scripts\python.exe scripts/run_detection.py data_samples/ua_detrac/MVI_20011_first_10s.mp4 --device auto --imgsz 640 --output-dir outputs/detection
.\.venv\Scripts\python.exe scripts/run_tracking.py data_samples/ua_detrac/MVI_20011_first_10s.mp4 --device auto --imgsz 640 --output-dir outputs/tracking
```

- `prepare_cadp_pilot.py`: CSV đối tượng/khoảng Colliding, JSON kiểm tra và ảnh đối chiếu ở `outputs/audits/cadp_1407/`; MP4 ở `outputs/annotation_preview/`. Bỏ `--preview-config` thì chỉ audit, không tự đoán tọa độ.
- `prepare_detrac.py`: kiểm kê ZIP, tái dùng ảnh đã có khi CRC khớp hoặc lấy ảnh còn thiếu; tạo ba MP4 đầy đủ, một clip ngắn và audit tại `outputs/audits/detrac_preparation/`. Gặp file khác CRC sẽ dừng và giữ file đó.
- `src/data_preparation.py`: hàm chung đọc hết video, hash, ghi H.264 qua FFmpeg và cắt clip. Không chạy trực tiếp.
- `register_prepared_manifest.py`: đọc hai report để cập nhật manifest, giữ bản trước sửa tại `outputs/audits/manifest_registration/manifest_before.csv`.

Lệnh đã dùng đăng ký lần này:

```powershell
.\.venv\Scripts\python.exe scripts/maintenance/register_prepared_manifest.py --cadp-report outputs/audits/cadp_1407/report.json --detrac-report outputs/audits/detrac_preparation/report.json
```

**Không cần chạy lại các lệnh để xem kết quả.** Script chuẩn bị tự thêm hậu tố `_2` nếu output đã tồn tại; ảnh gốc không bị ghi đè. Script đăng ký từ chối ID đã có để không đè nhãn/ghi chú được rà sau đó. Khi chạy lại, dùng report/tên output mới thực tế, không đoán hậu tố.

## Manifest và việc cần làm tiếp

[Manifest](../data/manifest.csv) lượt đầu có 9 dòng; hiện có **12 asset** sau khi thêm chuỗi ảnh sạch, MP4 sạch và preview từ ảnh sạch. Ba mẫu cũ giữ nguyên giá trị. Chuẩn hóa khoảng trắng CSV để công cụ đọc đúng, có backup nguyên byte trước mỗi lượt sửa. Schema hiện vẫn 36 cột, không thêm cột ở lượt có ảnh sạch. 23 cột gốc và các cột truy nguồn gồm:

- `asset_role`, `source_sequence`, `derived_from`, `source_archive`, `source_frame_range`: phân biệt nguồn/demo/MP4 ghép/clip, giữ quan hệ với chuỗi gốc. Frame range gồm hai đầu; CADP bắt đầu 0, ảnh DETRAC bắt đầu 1.
- `annotation_path`: file TXT hoặc `đường-dẫn-ZIP!thành-viên-XML`; `annotation_origin` chỉ nguồn tác giả. `author_colliding_frames` giữ sự kiện tác giả mà không ghi vào `onset_s/end_s` dự án.
- `user_review_status`: phân biệt chưa xem, xem toàn chuỗi, kế thừa từ parent đã xem và CADP xác nhận đúng xe **cùng interval theo frame**. `fps_status`, `fps_source`, `verification_status`, `notes` ghi căn cứ và giới hạn kiểm chứng. Ghi chú pending cũ được giữ như lịch sử và có ghi chú superseding review; không hỏi lại mẫu đã duyệt. Cột mới trống ở ba dòng cũ nghĩa chưa có ghi nhận bổ sung.

Ba DETRAC đầy đủ có `collision_label=negative`, clip con kế thừa từ parent; CADP 001407 `positive` sau xác nhận frame, ba mẫu cũ vẫn `unknown`. Mọi `split=unassigned`. JPG không có FPS/duration nguồn nếu chưa xác minh; MP4 CADP ghi FPS trình chiếu 20 và trạng thái giới hạn. Backup cập nhật review mới tại `outputs/audits/cadp_frame_review/`. Không tải thêm dataset, không train, không tạo split.

Thao tác tiếp theo cho người thực hiện:

1. CADP 001407 đúng xe và interval 96–130 đã được xác nhận, không yêu cầu rà lại. Chốt [quy tắc vùng accident đề xuất](b0_label_protocol.md) cho B0, tách khỏi xác nhận event đã hoàn tất; không dùng FPS trình chiếu làm FPS nguồn.
2. Ba DETRAC đã được người dùng xem toàn bộ; chưa cần yêu cầu xem lại để xác nhận âm. Khi mở rộng chuỗi khác vẫn phải rà riêng, kiểm tra rung camera và miền CCTV mục tiêu; không tự lan nhãn sang chuỗi chưa xem.
3. Frames sạch 001407 và mapping đã có; còn thiếu timing gốc và quy tắc/nhãn vùng accident cho B0. Không biến bbox xe Colliding thành bbox tai nạn. [Điều kiện B0](../data/b0_readiness.json).
4. [Đã kiểm các nguồn VATIC tác giả](cadp_pilot_sources.md), chưa xác minh thêm cặp ngoài 001407. Lấy export/mapping trước, sau đó chọn thêm chuỗi có nhãn và rà pilot ít nhất 10 ví dụ đa sự kiện/âm/hard negatives. Không yêu cầu gán lại bbox xe bằng tay hoặc tải toàn CADP. Split là công việc riêng sau xác minh nhóm và chốt nhãn.

<a id="kiem-ke-ba-video-ban-dau"></a>

## Kiểm kê ba video ban đầu — 19/10/2026

> Hợp nhất từ `docs/data_audit.md` ngày 25/10 để giảm file hướng dẫn. Nội dung dưới đây giữ kết quả và giới hạn lịch sử, không phải inventory hiện hành.

> **Tài liệu chi tiết/lịch sử:** ưu tiên [mục lục hiện hành](README.md), [policy nhãn B0](b0_label_protocol.md) và [trạng thái dữ liệu mới nhất](b0_pilot_audit.md). Các số liệu/chỉ dẫn cũ bên dưới giữ bối cảnh lúc tạo, không thay hướng public đã chọn.

Đây là mốc kiểm kê **trước khi thêm CADP 1407 và DETRAC**. Kết quả và giới hạn của dữ liệu mới ở [hướng dẫn chuẩn bị CADP/DETRAC](dataset_preparation.md); manifest hiện tại đã bổ sung các asset mới.

**Lượt mới nhất cùng ngày:** đã có riêng 221 ảnh sạch CADP 001407, mapping TXT/demo được kiểm ở nhiều mốc, và ba DETRAC đầy đủ được người dùng xác nhận âm. [Bằng chứng, video và giới hạn timing/B0](cadp_001407_clean.md). Xác nhận mới không thay nhãn hoặc nguồn của ba video cũ trong bảng dưới.

### Phương pháp và kết quả đo được

Chỉ đọc file trong `data_samples/`; không tải thêm dữ liệu. Dùng OpenCV đọc toàn bộ từng MP4 và lấy metadata, dùng SHA-256 trên byte của file để kiểm tra trùng chính xác. Xem frame ở khoảng 0%, 25%, 50%, 75%, 98% mỗi clip để nhận diện sơ bộ góc quay; việc này **không thay thế xem toàn clip để gán nhãn**.

| Video | Kích thước | FPS OpenCV | Frame metadata/đọc được | Thời lượng xấp xỉ | Nhãn, nguồn, split |
| --- | --- | ---: | ---: | ---: | --- |
| `YSGhwU9XxuY.mp4` | 450×360 | 25 | 279/279 | 11,160 s | Chưa xác minh |
| `ZCQcKnFSJvg.mp4` | 480×270 | 29,97003 | 717/717 | 23,924 s | Chưa xác minh |
| `zVzXEht1aME.mp4` | 480×360 | 20 | 794/794 | 39,700 s | Chưa xác minh |

Ba SHA-256 trong [manifest](../data/manifest.csv) khác nhau, nên **không trùng chính xác ở mức file**. Điều đó chưa loại trừ hai bản cắt/chuyển mã của cùng camera hoặc sự kiện. Các frame lấy mẫu cho thấy mỗi clip có góc nhìn có vẻ cố định; chưa xác nhận nguồn CADP, camera ID hay loại sự kiện. Tại thời điểm kiểm kê ban đầu, `data_raw/` chỉ có `.gitkeep`; các gói CADP/DETRAC được kiểm kê trong buổi sau, không thay đổi kết luận nhãn của ba video này.

Trang [CADP của nhóm tác giả](https://ankitshah009.github.io/accident_forecasting_traffic_camera.html) mô tả 1.416 đoạn video, 205 đoạn có nhãn không gian–thời gian đầy đủ và dẫn tới README, annotation và guideline. Trang nêu điều kiện sử dụng phi thương mại cho nghiên cứu, cần xin phép tác giả cho mục đích khác. **Chưa đối chiếu ba MP4 địa phương với danh mục/annotation chính thức**, nên không ghi `source_dataset=CADP` chỉ dựa vào tên file hay bối cảnh hình ảnh. Chưa có bản README phát hành tại project để kiểm tra thêm điều kiện chi tiết.

### Điều kiện còn thiếu để hoàn thành giai đoạn 1

1. Nguồn và annotation gốc của video, quyền sử dụng/trích dẫn; xác định clip có đủ thời gian trước/sau va chạm và nhãn pair/onset thực tế hay không.
2. Video **không tai nạn** được xem toàn đoạn, gồm hard negatives và đoạn âm dài để đánh giá false alarms/hour.
3. Rà ít nhất 10 trường hợp pilot theo [quy tắc nhãn bản nháp](annotation_protocol.md), chốt phạm vi/ranh giới `end_s` và trường hợp không chắc chắn.
4. Xác định camera/source event, loại trùng/gần trùng, sau đó mới tạo split manifest cố định. Với ba clip chưa biết nhóm và nhãn, một split ngẫu nhiên sẽ không có ý nghĩa đánh giá.

**Kết luận tại mốc ban đầu:** kiểm kê kỹ thuật video hoàn tất cho ba file mẫu; giai đoạn định nghĩa và dữ liệu **chưa đạt điều kiện chuyển sang B0**. Xem bản chuẩn bị mới để biết tài liệu/nhãn tác giả hiện đã tìm thấy.
