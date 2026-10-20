# Bắt đầu từ một máy mới hoặc một AI mới

Hướng dẫn cho Windows/PowerShell, cập nhật **20/10/2026, Asia/Bangkok**. Mục tiêu là clone được code, biết project đang ở đâu, tải đúng phần cần dùng và tái tạo đầu ra. Repo không chứa dataset, video, trọng số, môi trường `.venv` hoặc toàn bộ audit.

## 1. Hiểu trạng thái trước khi chạy lệnh

Đọc lần lượt:

1. [AGENTS.md](../AGENTS.md): quy tắc làm việc và một file tiến độ/ngày.
2. [README.md](../README.md), các sheet liên quan trong [XLSX](../YOLO_Lo_trinh_DACN.xlsx): mục tiêu và điều kiện chuyển bước.
3. [progress/README.md](../progress/README.md), file nhật ký gần nhất: những gì thực sự đã làm.
4. [Định nghĩa/đề xuất nhãn B0](b0_label_protocol.md), [nguồn dữ liệu đã kiểm](cadp_pilot_sources.md), [metadata dữ liệu](../data/README.md).

**Hiện tại:** đang ở giai đoạn 1 — định nghĩa và chuẩn bị dữ liệu. Đã chạy YOLOv8n pretrained để tìm phương tiện, ByteTrack để giữ ID tạm. Chúng **chưa phát hiện tai nạn**. B0 trong kế hoạch là YOLO fine-tune **vùng accident**, chưa train.

- Một sự kiện CADP **001407**: 221 ảnh sạch, TXT khớp; người dùng đã xác nhận đúng xe và Colliding **frame 96–130**, gồm hai đầu, GT ID0 Bus/ID2 Car. Không yêu cầu xác nhận lại mẫu này khi phục hồi đúng dữ liệu đã kiểm. FPS nguồn chưa biết, không đổi interval thành giây bằng FPS bản render/trình chiếu.
- Ba DETRAC đầy đủ **MVI_20011/MVI_20012/MVI_20032** đã được người dùng xem và xác nhận không va chạm. Đây là review của người dùng, không suy từ nhãn xe XML.
- Có 35 bbox vùng **đề xuất dẫn xuất**, chưa phải GT B0 đã duyệt; còn thiếu quyết định quy tắc vùng và pilot đa sự kiện. `data/b0_readiness.json` giữ `can_train=false`.
- Manifest có 12 asset nhưng chỉ 1 sự kiện CADP + 3 nhóm chuỗi âm; output/clip con không là mẫu độc lập. Ba MP4 mẫu cũ chưa rõ nguồn, không bắt buộc tải để dựng pilot này.

## 2. Clone và tạo môi trường

### Phần mềm

| Cần gì | Nguồn và cách đặt |
| --- | --- |
| Git cho Windows | [Trang Git](https://git-scm.com/install/windows), cài để gọi được `git` trong PowerShell |
| Python **3.12, 64-bit** | [Python Windows](https://www.python.org/downloads/windows/), chọn nhánh 3.12; kiểm `py -3.12 --version` |
| FFmpeg có `libx264` | [Trang FFmpeg](https://ffmpeg.org/download.html) → Windows builds từ gyan.dev/BtbN được trang đó dẫn; giải nén, ví dụ `C:\Tools\ffmpeg\`, thêm thư mục chứa `ffmpeg.exe` vào PATH người dùng, mở PowerShell mới |
| VS Code | Có thể dùng để mở thư mục; chọn interpreter `.venv\Scripts\python.exe` |
| GPU NVIDIA | Nếu dùng GPU cần driver phù hợp; nhánh CPU bên dưới vẫn chạy được inference, thường chậm hơn |

Không copy `.venv` từ máy cũ. Không cần cài CUDA Toolkit riêng chỉ để chạy wheel PyTorch; xác nhận bằng `check_environment.py`. Tham khảo [hướng dẫn PyTorch chính thức](https://pytorch.org/get-started/locally/) nếu máy/driver khác cấu hình đã kiểm.

```powershell
git clone https://github.com/leanhquan0211/DACN_TrafficCollision.git
Set-Location DACN_TrafficCollision
$env:PYTHONUTF8 = '1' # tránh lỗi console/pip khi đường dẫn có tiếng Việt
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
```

**Chọn một nhánh PyTorch**, rồi cài dependencies chung. Các pin dưới đây lấy từ môi trường đã dùng, không có nghĩa là phiên bản mới nhất:

```powershell
# GPU NVIDIA: nhánh từng chạy trên laptop của project
.\.venv\Scripts\python.exe -m pip install --index-url https://download.pytorch.org/whl/cu128 'torch==2.11.0+cu128' 'torchvision==0.26.0+cu128'

# HOẶC CPU nếu không dùng NVIDIA/CUDA
.\.venv\Scripts\python.exe -m pip install --index-url https://download.pytorch.org/whl/cpu 'torch==2.11.0' 'torchvision==0.26.0'

# Sau một trong hai nhánh ở trên
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
ffmpeg -version
ffmpeg -hide_banner -encoders | Select-String libx264
.\.venv\Scripts\python.exe scripts/check_environment.py
```

Nếu pin không có wheel cho máy/OS đang dùng, ghi rõ lỗi, tra nguồn PyTorch và báo thay đổi môi trường; không tự đổi model/baseline. `logs/requirements-installed.txt` là snapshot đầy đủ của máy cũ, không mặc định áp nguyên CUDA lên mọi máy. Không cài dependencies của repository CADP Python 2.7 vào `.venv` project này.

### Kiểm code ngay cả khi chưa có dataset

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/run_all.py --help
.\.venv\Scripts\python.exe scripts/check_project_assets.py --create-dirs
```

Ba test dùng fixture nhỏ chạy không cần dataset. Hai test tích hợp cần TXT/pilot thật sẽ ghi **skipped** nếu chưa phục hồi; skipped không có nghĩa đã kiểm pipeline trên dữ liệu thật. Khi phục hồi đủ pilot, cả năm test mới chạy đầy đủ.

## 3. Những gì có và không có trong repo

```text
DACN_TrafficCollision/
├── AGENTS.md, README.md, requirements.txt, YOLO_Lo_trinh_DACN.xlsx
├── docs/GETTING_STARTED.md       # điểm bắt đầu cho người/AI mới
├── docs/evidence/                # vài JSON kết quả lịch sử nhỏ
├── configs/                     # config căn chỉnh và quy tắc B0 đề xuất
├── scripts/, src/, tests/        # công cụ xử lý và kiểm tra
├── data/
│   ├── manifest.csv, reviews/    # metadata/review, có Git
│   ├── download_catalog.json    # nguồn tải + đường dẫn + hash
│   ├── registries/              # fingerprint 221 ảnh, không chứa ảnh
│   └── processed/               # sinh cục bộ, bị ignore
├── data_raw/                    # tải thủ công, bị ignore trừ README/.gitkeep
├── data_samples/                # MP4 ghép/clip cục bộ, bị ignore
├── outputs/                     # prediction/audit/backup cục bộ, bị ignore
├── progress/YYYY-MM-DD.md       # một file/ngày Asia/Bangkok
├── logs/                        # thông tin môi trường lịch sử nhỏ
├── yolov8n.pt                   # tải riêng, bị ignore
└── .venv/, .tmp/                # sinh trên máy, bị ignore
```

Đường dẫn trong hướng dẫn tính từ thư mục chứa README. Có thể clone ở thư mục khác; VS Code settings dùng `${workspaceFolder}`. Log máy cá nhân được giữ local, bản môi trường công khai tại [environment_reference.md](environment_reference.md).

**Manifest/review trên Git là hồ sơ nghiên cứu, không phải inventory máy mới.** Liên kết tài liệu tới `outputs/`/`data/processed/` chỉ mở được sau khi có dữ liệu và tái tạo đầu ra. Đọc [snapshot nhỏ](evidence/README.md) nếu chỉ muốn hiểu kết quả lịch sử, không cần tải media.

## 4. Tải dữ liệu đúng vị trí

**Không có script tự tải toàn dataset.** Catalog có URL và hash để kiểm: [data/download_catalog.json](../data/download_catalog.json). Kiểm dung lượng trống trước; môi trường GPU cũng cần dung lượng riêng, ngoài dataset.

### A. Model và mẫu CADP 001407

| File/phần cần lấy | Nguồn chính xác | Lưu tại |
| --- | --- | --- |
| `yolov8n.pt` (~6,55 MB) | [Ultralytics asset chính thức](https://github.com/ultralytics/assets/releases/download/v8.4.0/yolov8n.pt); URL đã đối chiếu release API ngày 20/10 | **Gốc project:** `yolov8n.pt` |
| `1407.txt` (VATIC tác giả) | [Raw TXT của repository tác giả](https://raw.githubusercontent.com/ankitshah009/CarCrash_forecasting_and_detection/master/data/1407.txt); tải file raw, không lưu trang HTML | `data_raw/cadp/pilot_1407/1407.txt` |
| `1407.mp4` (demo đã vẽ) | [Raw MP4 của tác giả](https://raw.githubusercontent.com/ankitshah009/CarCrash_forecasting_and_detection/master/data/1407.mp4) | `data_raw/cadp/pilot_1407/1407.mp4` |
| ZIP mã tham chiếu | [Download ZIP nhánh master](https://github.com/ankitshah009/CarCrash_forecasting_and_detection/archive/refs/heads/master.zip) của repository tác giả | `data_raw/cadp/reference_code/CarCrash_forecasting_and_detection-master.zip` |
| **Chỉ thư mục ảnh `001407`** | [extracted_frames được mã tác giả sử dụng](https://drive.google.com/drive/folders/1BRIv9h4c_zbqJ6Ye4rVyFSo3K20BQt_v), đường dẫn phát hành `Dataset/manual/extracted_frames/001407` | `data_raw/cadp/frames/001407/0.jpg … 220.jpg` |

Trong Drive chọn đúng thư mục tên **001407** để tải, không tải thư mục cha. Google có thể đóng gói thành ZIP tên có ngày/giờ khác máy cũ. Giữ ZIP đó trong `data_raw/cadp/frames/` và truyền **tên thật** vào script; không phải đổi thành tên ZIP lịch sử. Giữ tên ảnh gốc, sắp theo số, tránh `001407/001407/`.

Nếu Drive chưa cho tải, mở bằng trình duyệt để xem trạng thái quyền truy cập; đừng thay bằng video đã vẽ hoặc một chuỗi tên gần giống. Link extracted frames cũ trên trang CADP từng trả 404; dùng nguồn folder ở bảng trên. Ảnh 001407 đã có trong máy cũ khoảng 62,14 MB, không phải toàn CADP.

Trọng số YOLO dùng class phương tiện COCO, không có class accident. `bytetrack.yaml` được đóng trong Ultralytics, không cần tải trọng số tracker riêng. Pipeline cũng có thể tải **đúng `yolov8n.pt` mặc định** nếu thiếu, nhưng có thể tải thủ công theo bảng nếu mạng hạn chế.

### B. Ba chuỗi UA-DETRAC

Nguồn tác giả: [UA-DETRAC download](https://sites.google.com/view/daweidu/projects/ua-detrac).

| File/phần cần lấy | Link | Lưu tại |
| --- | --- | --- |
| `DETRAC-Images.zip` (~9,85 GB) | [Drive DETRAC-Images](https://drive.google.com/file/d/1fQC6CEWOeL9pnJ4ZdD7U2gromcnWDRgm/view) | `data_raw/ua_detrac/DETRAC-Images.zip` |
| Nhãn xe train XML, tùy chọn khi kiểm vehicle GT | [DETRAC-Train-Annotations-XML.zip](https://drive.google.com/file/d/1f22g3puG164gemY_njcPG8beuCcuMjqb/view) | `data_raw/ua_detrac/annotations/DETRAC-Train-Annotations-XML.zip` |
| Nhãn xe test XML, tùy chọn | [DETRAC-Test-Annotations-XML.zip](https://drive.google.com/file/d/1zc8KZWUa3Cw0DbcFqTCMBmUZzbfuhGKr/view) | `data_raw/ua_detrac/annotations/DETRAC-Test-Annotations-XML.zip` |

Nếu máy thiếu dung lượng, có thể nhận **ba thư mục đã lấy chọn lọc** từ người đang giữ dữ liệu, giữ đúng tên/cấu trúc sau; script ghép video chấp nhận dùng lại mà không có ZIP. Không cần tải DETRAC-Detections, MAT hoặc Toolkits cho pipeline hiện tại.

```text
data_raw/ua_detrac/DETRAC-Images/
  MVI_20011/img00001.jpg … img00664.jpg  # 664 ảnh
  MVI_20012/img00001.jpg … img00936.jpg  # 936 ảnh
  MVI_20032/img00001.jpg … img00437.jpg  # 437 ảnh
```

Không giải nén toàn ZIP chỉ để chạy ba chuỗi. Bước tạo **index âm kiểm CRC** hiện cần ZIP gốc để đối chiếu; nếu chỉ có thư mục ảnh thì vẫn ghép/chạy model được, chưa báo đã thực hiện CRC ZIP. Các archive Train/Test là tên của nguồn, không là split của project. XML là nhãn phương tiện, không phải nhãn accident.

### C. Tài liệu/metadata tùy chọn

- [README phát hành CADP](https://docs.google.com/document/d/12F7l4yxNzzUAISZufEd9WFhQKSefVVo_QsPdTsWxZh8/edit): tải PDF về `data_raw/cadp/documentation/CADP_Dataset_Release_ReadMe.pdf`.
- [Paper CADP](https://arxiv.org/abs/1809.05782): tải PDF về `data_raw/cadp/documentation/`; phiên bản có thể khác bản camera-ready máy cũ, không ép hash.
- JSON Stage 1, duration và biểu đồ FPS là tài liệu tham chiếu ở [trang tác giả](https://ankitshah009.github.io/accident_forecasting_traffic_camera.html); đặt JSON tại `data_raw/cadp/annotations_stage1/`, duration/FPS tại `data_raw/cadp/metadata/` nếu cần nghiên cứu. Chúng không bắt buộc để tạo pilot sạch; bbox Stage 1 là dummy, biểu đồ FPS không xác nhận FPS riêng 001407.
- **Chưa tìm được gói VATIC bổ sung đầy đủ**: không hứa có `000000.txt` để tải. [Phạm vi đã tìm và cách xin export](cadp_pilot_sources.md). Khi nhận được, giữ ZIP tại `data_raw/cadp/annotations/`, TXT chọn lọc tại `data_raw/cadp/annotations/vatic/`, kiểm mapping rồi mới chọn ảnh tương ứng.

## 5. Kiểm dữ liệu trước khi chạy model

```powershell
.\.venv\Scripts\python.exe scripts/check_project_assets.py --create-dirs --check-hashes
.\.venv\Scripts\python.exe scripts/check_project_assets.py --profile inference --check-hashes --strict
```

`missing` chỉ rõ vị trí cần chép và nguồn; `hash_mismatch` không được bỏ qua bằng cách tự sửa manifest/review. Catalog có fingerprint cả 221 JPG để nối đúng với xác nhận đã có, không chỉ so tên thư mục. `--strict --profile cadp` có thể dùng **sau khi giải nén** để kiểm đủ input CADP. Công cụ không tải gì, không đổi nhãn.

### CADP: audit ảnh → video sạch → suy luận

Nếu đã có thư mục ảnh đúng cấu trúc, bỏ `--archive`. Nếu chỉ có ZIP, thay `TEN_ZIP_THAT.zip` bằng tên thật trên máy:

```powershell
# Lần đầu audit-only; lấy riêng 001407 nếu cần, giữ ZIP, không ghi đè file khác nội dung
.\.venv\Scripts\python.exe -B scripts/prepare_cadp_frames.py --archive "data_raw/cadp/frames/TEN_ZIP_THAT.zip"
.\.venv\Scripts\python.exe scripts/check_project_assets.py --profile cadp --check-hashes --strict

# Khi fingerprint khớp dữ liệu đã xác nhận, dùng lại kết luận sạch/mapping đã ghi;
# cờ visual không phải xác nhận accident-region GT, không xác nhận source FPS
.\.venv\Scripts\python.exe -B scripts/prepare_cadp_frames.py --visual-check-confirmed
```

Nếu hash ảnh khác hoặc mapping kỹ thuật không đạt thì dừng nhánh dùng nhãn, giữ dữ liệu ngoài tập train và ghi điều chưa khớp; không tự dịch frame hoặc ép xác nhận cũ sang dữ liệu mới. Không cần hỏi lại người dùng xe/96–130 khi **đúng byte dữ liệu đã rà**.

Script in `audit_directory`, `clean_video`, `author_preview`. Ví dụ một máy sạch chạy đúng hai lệnh chuẩn bị ở trên thường có report `_2`; nếu tên đã có thì hậu tố khác. **Dùng đường dẫn in ra thực tế**, không đoán `_2`.

```powershell
$cadpCleanReport = 'outputs/audits/cadp_001407_clean_2/report.json' # sửa theo audit_directory vừa in
$cadpRunInfo = Get-Content -Raw $cadpCleanReport | ConvertFrom-Json
.\.venv\Scripts\python.exe scripts/run_detection.py $cadpRunInfo.clean_video --device auto --imgsz 640 --output-dir outputs/detection
.\.venv\Scripts\python.exe scripts/run_tracking.py $cadpRunInfo.clean_video --device auto --imgsz 640 --output-dir outputs/tracking
```

Mở các MP4 script báo đã lưu. Bản GT preview dùng xem nhãn tác giả; bản detection/tracking là dự đoán xe, ID tracker khác GT ID. Không đưa `1407.mp4` render hoặc GT preview vào model để đánh giá detector.

### DETRAC: lấy ba chuỗi → ghép video/clip

```powershell
.\.venv\Scripts\python.exe scripts/prepare_detrac.py --sequences MVI_20011 MVI_20012 MVI_20032 --fps 25 --fps-status verified_source --fps-source 'https://arxiv.org/html/1511.04136#S2' --smoke-seconds 10
.\.venv\Scripts\python.exe scripts/check_project_assets.py --profile detrac --strict
```

Nếu ZIP không có nhưng các thư mục ảnh đã đúng, script dùng thư mục hiện có. Ba MP4 sinh trong `data_samples/ua_detrac/`; report tại `outputs/audits/detrac_preparation*/report.json`. Chạy detection/tracking trên clip 10 giây mới in ra; vẫn model/tham số cũ. FPS 25 thuộc DETRAC, không dùng cho CADP.

## 6. Chuẩn hóa nhãn B0 và tiếp tục đúng lộ trình

Khi CADP fingerprint/mapping đã đạt, tạo đề xuất từ **TXT tác giả + phiếu rà hiện có**:

```powershell
.\.venv\Scripts\python.exe scripts/prepare_b0_candidates.py --sequence 001407 --frames-dir data_raw/cadp/frames/001407 --annotations data_raw/cadp/pilot_1407/1407.txt --mapping-report $cadpCleanReport --review data/reviews/2026-10-19-cadp-001407-frame-confirmation.json --output data/processed/b0_proposals/001407
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

Output đã tồn tại thì không chạy lại hoặc dùng đường dẫn phiên bản mới có chủ đích; công cụ từ chối ghi đè. Xem `report.json`, `objects_normalized.csv`, `frames.csv`, `ignore_and_separator_regions.csv`, `region_proposals.csv`, `proposal_examples.jpg`, `labels_proposed/`. Kỳ vọng: 35 đề xuất, 186 frame chưa chứng nhận âm toàn cảnh; **chưa duyệt GT, không có dataset.yaml/train/val/test**.

**Về index âm DETRAC và manifest:** hồ sơ trên Git gắn SHA của MP4 đã xem trên máy phát triển. Ghép lại bằng FFmpeg khác phiên bản có thể khác byte dù dùng cùng ảnh. Không tự thay hash trong review để vượt chốt kiểm. Khi có **đúng MP4 đã rà**, ZIP nguồn và report ghép khớp, chạy:

```powershell
.\.venv\Scripts\python.exe scripts/prepare_b0_negative_index.py --preparation-report outputs/audits/detrac_preparation/report.json
```

Nếu video tái mã hóa khác hash, ghi đây là asset mới, chứng minh quan hệ ảnh/chuỗi/review bằng fingerprint/CRC và lập đăng ký dẫn xuất phù hợp ở công việc tiếp theo; chưa báo đã tái tạo index đúng review cũ. Có thể nhận MP4 gốc đã rà từ người đang giữ để phục hồi chính xác. Việc này không đồng nghĩa ba chuỗi mất xác nhận âm. Không chạy mù `register_prepared_manifest.py`/`update_manifest_reviews.py` lên manifest đã có 12 asset: chúng phục vụ lượt đăng ký lịch sử và sẽ từ chối ID/asset khác hoặc trùng.

Lộ trình tiếp theo:

1. Chốt [quy tắc vùng accident đề xuất](b0_label_protocol.md) — khác với xác nhận xe/interval 001407 đã hoàn tất.
2. Lấy thêm **VATIC sẵn có và mapping** từ tác giả; chọn thêm sự kiện độc lập và âm/hard negatives gần miền camera. Không tự gán lại bbox trước khi giải quyết nguồn có sẵn.
3. Kiểm near-duplicate, nhóm camera/nguồn/sự kiện, rà pilot và nhãn vùng nhất quán. Khi đủ điều kiện mới làm công việc chia split theo nhóm.
4. Sau đó mới huấn luyện/đo B0, phân tích FP/FN và tiếp tục B1 → B2/T0 → GRU nếu lỗi/đo đạc cho thấy cần. Không train từ một chuỗi dương và ba chuỗi âm hiện tại.

## 7. Giao việc cho một AI mới

Có thể gửi nguyên đoạn sau sau khi mở repo trong IDE:

> Đọc AGENTS.md, README.md, docs/GETTING_STARTED.md, định nghĩa B0 và progress gần nhất trước khi làm. Kiểm kê file thực tế bằng scripts/check_project_assets.py; manifest và evidence trên Git là hồ sơ máy phát triển, đừng giả định dữ liệu/output đã tải trên máy này. CADP 001407 đã xác nhận xe và Colliding 96–130 theo frame, ba DETRAC đầy đủ đã xác nhận âm; không hỏi lại nếu fingerprint đúng. Source FPS CADP chưa xác minh. Nhãn vùng B0 hiện là đề xuất dẫn xuất chưa duyệt GT, can_train=false. Không tự tải cả dataset, thay model, tạo split hoặc train. Hoàn thành phần kỹ thuật đủ điều kiện và ghi giới hạn thật. Trước kết thúc cập nhật progress/README.md và đúng một file progress/YYYY-MM-DD.md theo Asia/Bangkok.

## 8. Git: đưa code lên, giữ media ở máy

- Có Git: source/test/config/docs, XLSX định hướng nhỏ, requirements, metadata/hash/review và nhật ký theo ngày.
- Không Git: `.venv`, `.tmp`, dataset/ZIP, trọng số, MP4/prediction/preview, processed labels/index sinh ra, audit/backup đầy đủ, credentials/token.
- `data_raw/`, `data_samples/`, `outputs/` chỉ giữ README/.gitkeep để người clone thấy cấu trúc. Không đổi bố cục hoặc copy cả dataset chỉ để hợp Git.

```powershell
git status --short
git check-ignore -v yolov8n.pt data_raw/cadp/pilot_1407/1407.mp4
git diff --cached --stat
```

Trước commit xem danh sách staging, không `git add -f` dataset hoặc thông tin đăng nhập. Không cần Git LFS cho bố cục hiện tại: repo giữ nguồn phục hồi và metadata, media lưu ngoài Git. Nếu nguồn tải đổi hoặc nhận export mới, cập nhật catalog/docs/nhật ký bằng kết quả kiểm thực tế.
