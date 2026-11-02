# Bắt đầu từ một máy mới hoặc một AI mới

Hướng dẫn cho Windows/PowerShell, dữ liệu cập nhật **27/10/2026, Asia/Bangkok**. Mục tiêu là clone được code, biết project đang ở đâu, tải đúng phần cần dùng và tái tạo đầu ra. Repo không chứa dataset, video, trọng số, môi trường `.venv` hoặc toàn bộ audit.

> **Kiểm khả năng bàn giao source ngày 02/11/2026:** clone chỉ lấy code/config/metadata và tài liệu, **chưa chạy train ngay**. Phần dưới có các hướng dẫn lịch sử của pilot đầu; trạng thái mới nhất đọc ở [bảng baseline](../progress/README.md) và [báo cáo tổng hợp](BAO_CAO_TIEN_DO_DACN.md). Config V11 dùng bố cục bundle (`data/kaggle_full/dataset.yaml`, `weights/initial.pt`, `data/training_bundle_manifest.json`, metadata recipe và runtime), không phải các đường dẫn mặc nhiên có sau clone. Cần phục hồi đúng gói dataset/nhãn/split/provenance, checkpoint khởi đầu và hồ sơ kiểm tương ứng; không đổi hash hoặc bỏ gate để ép chạy. Dataset/Notebook Kaggle hiện PRIVATE: clone GitHub không cấp quyền đọc chúng. Có thể nhận quyền truy cập phù hợp từ chủ tài khoản hoặc dựng lại từ nguồn công khai; không đưa token hay toàn bundle vào Git.

Trình tự kiểm trên máy mới: cài môi trường theo mục 2 → `python scripts/train_b0.py --help` → `python scripts/check_project_assets.py --json` → phục hồi tài sản theo catalog/hướng dẫn → `python scripts/train_b0.py --config <config-phù-hợp> --check`. Lệnh kiểm asset không chứng minh đã có đủ release train mới nhất vì catalog không bao phủ toàn bộ bundle/runtime. Chỉ chạy `--train` khi đầu vào/config đã được kiểm và có chỉ dẫn mở thí nghiệm mới; dùng tên output mới, không ghi đè run lịch sử. Việc `--help` chạy được không phải bằng chứng đã tái lập huấn luyện trên clone sạch.

## 1. Hiểu trạng thái trước khi chạy lệnh

Đọc lần lượt:

1. [AGENTS.md](../AGENTS.md): quy tắc làm việc và một file tiến độ/ngày.
2. [README.md](../README.md), các sheet liên quan trong [XLSX](../YOLO_Lo_trinh_DACN.xlsx): mục tiêu và điều kiện chuyển bước.
3. [progress/README.md](../progress/README.md), file nhật ký gần nhất: những gì thực sự đã làm.
4. [Literature review](../reference/LITERATURE_REVIEW.md), [thuật ngữ](../reference/GLOSSARY.md) khi gặp từ lạ.
   Trước khi AI mới đổi dữ liệu, nhãn, cách train hoặc metric, đối chiếu paper/mã tác giả/tài liệu chính thức với bốn cột review; ghi recipe gốc, điều chỉnh vì B0/phần cứng và phép kiểm trong config/báo cáo. Không lấy tham số của bài toán khác làm mặc định không giải thích.
5. [Nhãn B0 hiện hành](b0_label_protocol.md), [pool/nhóm cảnh](b0_pilot_audit.md), [metadata](../data/README.md). Chọn lệnh ở [scripts/README](../scripts/README.md).

**Hiện tại:** đã train và đo B0 pilot ảnh 1.750 mẫu; checkpoint mới tốt hơn pilot 47 ảnh trên cùng test nhưng còn báo nhầm trên cảnh bình thường. YOLOv8n pretrained/ByteTrack cũ tìm phương tiện và giữ ID tạm; checkpoint B0 riêng tìm vùng `accident`, chưa là hệ thống phát hiện sự kiện hoàn chỉnh. Xem [kết quả](b0_pilot_audit.md#b0-mở-rộng-accident-v9--26102026) và [cách đọc train](../outputs/training/README.md).

**Cập nhật mở rộng sau pilot đầu:** đã tải 1.346 clip ACCIDENT v9 xe–xe (~3,04 GiB). Release cũ 2.436 ảnh bị thu hồi vì dùng âm chưa rà; release mới 1.750 ảnh dùng impact tác giả và âm có căn cứ. [Recipe, split và trạng thái](b0_pilot_audit.md#b0-mở-rộng-accident-v9--26102026), [bảng tiến độ](../progress/README.md). Raw ở `data_raw/accident/public_selected/real_videos/`, ảnh kiểm ở `outputs/audits/accident_scale/`, dataset mới ở `data/processed/b0_verified_pilot_v1/dataset/`. Downloader `scripts/download_accident_real.py` lấy từng member public, lưu SHA/size/URL trong receipt và kiểm chỗ trống; dùng sau khi phục hồi `metadata-real.csv` theo catalog bên dưới. Dữ liệu/checkpoint không có trong Git. Các con số 26 clip/47 ảnh bên dưới mô tả pilot đầu và cách phục hồi hồ sơ cũ mà split mới vẫn tham chiếu.

Snapshot index/split/hash của release mới nằm tại `data/registries/b0_verified_pilot_v1_{index.csv,split.csv,asset_hashes.json}` (metadata khoảng 1 MB). Trên máy mới sau khi phục hồi đúng raw, ảnh audit và evidence theo các hướng dẫn bên dưới, có thể gọi exporter với `--pool-index data/registries/b0_verified_pilot_v1_index.csv --export-split data/registries/b0_verified_pilot_v1_split.csv --release-kind pilot --release-key verified_pilot_release --policy-path configs/b0_verified_label_policy.json --output data/processed/b0_verified_pilot_v1/dataset`; không cần tái tạo release âm yếu bị thu hồi. Export sẽ từ chối nếu media/audit không khớp hash. Phiếu loại gần trùng và evaluator hiện còn tham chiếu audit cục bộ lịch sử, nên phải phục hồi audit đó khi muốn tái chạy so sánh hai checkpoint; không xem snapshot Git là media đã có.

Để phục hồi probe âm 100 frame từ nguồn TAD, chạy lệnh dưới; thay `tad_public_zip_N` bằng đúng thư mục report được in ra sau lệnh đầu. Công cụ giữ nguyên 5 video trong `data_raw/tad/public_selected/TAD-benchmark/test/normal/`, ảnh kiểm ở `outputs/audits/tad_normal_test_v1/` và đối chiếu hash với registry, không tự sửa registry khi có mismatch.

```powershell
.\.venv\Scripts\python.exe -X utf8 -B scripts/inspect_public_zip.py --max-mib 80 --fetch-members TAD-benchmark/test/normal/videox_test_F11.mp4 TAD-benchmark/test/normal/videox_test_F10.mp4 TAD-benchmark/test/normal/videox_test_F9.mp4 TAD-benchmark/test/normal/videox_test_F4.mp4 TAD-benchmark/test/normal/videox_test_F3.mp4
.\.venv\Scripts\python.exe -X utf8 -B scripts/inspect_public_zip.py --prepare-normal-test outputs/audits/tad_public_zip_N/report.json --samples-per-clip 20
.\.venv\Scripts\python.exe -X utf8 -B scripts/evaluate_b0_clean.py --check --normal-manifest data/registries/b0_tad_normal_test_v1.json
```

Nếu run `b0_verified_pilot_v1` bị ngắt trong lúc train, trước hết kiểm tra không còn tiến trình train đang chạy và còn `outputs/training/b0_verified_pilot_v1/weights/last.pt`. Sau đó dùng `python scripts/train_b0.py --config configs/b0_verified_pilot_v1.json --resume`. Script kiểm config snapshot, dataset, trạng thái run, process đang chạy và optimizer trong checkpoint; nếu đã chạy vào phần đánh giá hoặc checkpoint bị strip optimizer thì không tự bắt đầu lại. Cơ chế kiểm điều kiện đã được test bằng fixture; chưa xem việc resume có thành công cho đến khi thực sự chạy một lượt resume.

- Một sự kiện CADP **001407**: 221 ảnh sạch, TXT khớp; người dùng đã xác nhận đúng xe và Colliding **frame 96–130**, gồm hai đầu, GT ID0 Bus/ID2 Car. Không yêu cầu xác nhận lại mẫu này khi phục hồi đúng dữ liệu đã kiểm. FPS nguồn chưa biết, không đổi interval thành giây bằng FPS bản render/trình chiếu.
- Ba DETRAC đầy đủ **MVI_20011/MVI_20012/MVI_20032** đã được người dùng xem và xác nhận không va chạm. Đây là review của người dùng, không suy từ nhãn xe XML.
- B0 đã chọn bbox vùng tác giả STTAD public: 4 chuỗi, 31 frame có bbox; 145 frame thiếu TXT giữ unknown, 2 file ảnh lỗi bị loại. 35 envelope CADP giữ riêng là derived auxiliary.
- Hai normal TAD có 308 frame nhãn clip của nguồn, không phải người dùng rà; ba DETRAC gom cùng cảnh bảo thủ, không là ba camera độc lập.
- ACCIDENT có 26 clip chọn lọc (6 cũ + 20 mới), 17 impact được giữ và 30 frame âm trước impact có rà riêng. Pool v3 có 2.423 tham chiếu (48 dương/2.375 âm); pilot đầu dùng 47 ảnh ACCIDENT cùng miền, chia 30/9/8 theo video nguồn rồi train/đo. **Danh sách 20 file mới, URL/nơi lưu và lệnh phục hồi:** [batch mở rộng B0](b0_pilot_audit.md#batch-mở-rộng-26102026--đã-hoàn-thành). Không tải archive 20 GB.
- Manifest có 44 asset, số frame/asset không bằng số sự kiện độc lập. `data/b0_readiness.json` tách `pilot_release.can_train=true` khỏi gate benchmark đầy đủ `can_train=false`; âm khó không chặn pilot ảnh. Ba MP4 mẫu cũ vẫn chưa rõ nguồn. Config ở `configs/b0_pilot.json`, code train/đo ở `scripts/train_b0.py`; dataset và checkpoint lớn nằm local, không nằm trên Git. Snapshot nhỏ ở [evidence](evidence/2026-10-26-b0-basic-pilot.json).

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

Hiện có 16 test: 13 fixture và 3 integration cần dữ liệu/output đã phục hồi. Integration có thể **skipped** trên clone chỉ source; skipped không có nghĩa đã kiểm media thật. Danh sách/số test có thể tăng, đọc output thực tế của lệnh.

## 3. Những gì có và không có trong repo

```text
DACN_TrafficCollision/
├── AGENTS.md, README.md, requirements.txt, YOLO_Lo_trinh_DACN.xlsx
├── docs/README.md                # mục lục hướng dẫn hiện hành/lịch sử
├── docs/GETTING_STARTED.md       # cài máy, tải dữ liệu và chạy lại
├── docs/evidence/                # vài JSON kết quả lịch sử nhỏ
├── reference/                   # LITERATURE_REVIEW.md, GLOSSARY.md, catalog nguồn
├── configs/                     # policy B0 hiện hành và config nguồn giữ riêng
├── scripts/                     # lệnh video/dữ liệu; README chỉ cách chọn
│   └── maintenance/             # bảo trì manifest/review, không chạy thường xuyên
├── src/, tests/                 # code dùng chung và kiểm tra
├── data/
│   ├── manifest.csv, reviews/    # metadata/review, có Git
│   ├── download_catalog.json    # nguồn tải + đường dẫn + hash
│   ├── registries/              # fingerprint CADP/STTAD, không chứa ảnh
│   └── processed/               # sinh cục bộ, bị ignore
├── data_raw/                    # tải thủ công, bị ignore trừ README/.gitkeep
├── data_samples/                # MP4 ghép/clip cục bộ, bị ignore
├── outputs/                     # prediction/audit/backup cục bộ, bị ignore
│   └── audits/archive/          # một số audit thử cũ không còn tham chiếu
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
- **CADP export bổ sung chưa public trong phạm vi kiểm:** giữ lịch sử ở [hồ sơ CADP](cadp_pilot_sources.md), không xin riêng. Dùng nhãn vùng STTAD public đã kiểm theo mục D bên dưới.

### D. Nhãn vùng B0 công khai STTAD — lựa chọn mới 24/10

Nguồn tác giả: [ZTR02/STTAD](https://github.com/ZTR02/STTAD), pin commit `21f3f5fea50b071f1db61186b481c2a7ccf525c9`. Chỉ lấy **bốn chuỗi** `V-V_crash_0`, `V-V_crash_1`, `T-T_crash_1`, `T-T_crash_2`, tổng khoảng 79,2 MiB; không Download ZIP toàn repo.

```powershell
# Máy mới: tự kiểm tree, budget và hash, tải đúng bốn chuỗi + nhãn gốc
.\.venv\Scripts\python.exe -X utf8 -B scripts/audit_sttad_public.py --fetch-selected --max-mib 96
# Máy hiện tại đã có dữ liệu: kiểm lại offline, không tải thêm
.\.venv\Scripts\python.exe -X utf8 -B scripts/audit_sttad_public.py --offline
.\.venv\Scripts\python.exe -X utf8 -B scripts/check_project_assets.py --profile sttad --check-hashes --strict
```

Script giữ cấu trúc nguồn ở `data_raw/sttad/public_examples/rgb-images/<category>/<sequence>/` và `labels/<category>/<sequence>/`. `source_tree.json`, README và list tác giả nằm cạnh đó. Máy hiện tại: 178 file ảnh nguồn, 176 giải mã được, 31 frame có bbox, 145 frame thiếu TXT giữ unknown; hai `00051.jpg` V-V lỗi bị loại. TXT nguồn là class + xyxy pixel, không đưa thẳng vào YOLO. Script xuất CSV/31 TXT chuẩn hóa và ảnh so sánh ở audit in ra, chưa tạo dataset.yaml/split/train. Checker fingerprint không thay kiểm decode/nhãn trong audit.

Kết quả đã có cần mở: `outputs/audits/sttad_public_6/author_region_examples.jpg`, `boxes_normalized.csv`, `frames.csv`, `labels_yolo/`. Rerun sinh audit có hậu tố khác, dùng đường dẫn script in. [Reference và quyết định](../reference/2026-10-24-public-data-review.md).

### E. Hai clip normal TAD public và pool tham chiếu

Đã lấy riêng hai member `TAD-benchmark/train/normal/20220518_acci-bg34.mp4` và `TAD-benchmark/train/normal/20230818_acci-bg_83.mp4` từ [ZIP tác giả](https://drive.google.com/file/d/14GNlNcWLzN-sbzvmrMuSbAg_rZZ5yd26/view). Chúng nằm ở `data_raw/tad/public_selected/TAD-benchmark/train/normal/`, tổng khoảng 3,64 MiB. **Không cần tải cả ZIP 4,54 GB.**

```powershell
.\.venv\Scripts\python.exe -X utf8 -B scripts/inspect_public_zip.py --max-mib 8 --fetch-members TAD-benchmark/train/normal/20230818_acci-bg_83.mp4 TAD-benchmark/train/normal/20220518_acci-bg34.mp4
.\.venv\Scripts\python.exe -X utf8 -B scripts/check_project_assets.py --profile tad --check-hashes --strict
```

Hai clip có nhãn normal từ folder tác giả, chưa được người dùng rà; giải mã đủ 308 frame. [Phiếu nguồn/cảnh](../data/reviews/2026-10-24-pilot-source-review.json) giữ hash/CRC/phạm vi kiểm. Container 25 FPS không xác minh capture timing. Pool ở `data/processed/b0_public_pilot_v1/index.csv` tham chiếu 31 ảnh STTAD dương, 2.037 ảnh DETRAC âm và 308 frame video TAD âm; `video_frame_reference` là video + chỉ số decode 0-based, chưa có JPG riêng. Không có split/train/empty TXT. [Công cụ, lệnh tạo phiên bản pool mới và giới hạn](b0_pilot_audit.md).

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

Nếu video tái mã hóa khác hash, ghi đây là asset mới, chứng minh quan hệ ảnh/chuỗi/review bằng fingerprint/CRC và lập đăng ký dẫn xuất phù hợp ở công việc tiếp theo; chưa báo đã tái tạo index đúng review cũ. Có thể nhận MP4 gốc đã rà từ người đang giữ để phục hồi chính xác. Việc này không đồng nghĩa ba chuỗi mất xác nhận âm. Không chạy mù `register_prepared_manifest.py`/`update_manifest_reviews.py` lên manifest đã có 18 asset: chúng phục vụ lượt đăng ký lịch sử và sẽ từ chối ID/asset khác hoặc trùng.

Lộ trình tại mốc 24/10 (lịch sử; trạng thái mới nhất ở mục 1 và [báo cáo B0](b0_pilot_audit.md#pilot-b0-ảnh-26102026)):

1. Đã chọn nghĩa vùng theo STTAD và policy `configs/b0_public_label_policy.json`; dùng bbox vùng tác giả có sẵn. CADP envelope giữ auxiliary riêng. Không cần xin/chờ duyệt.
2. Đã kiểm T-T_crash_2 và hai normal TAD; [pool/nhóm cảnh](b0_pilot_audit.md) đã chạy thật. Mở rộng tiếp nguồn public có bbox cùng nghĩa và cả dương/âm, giảm shortcut nguồn; không lấy frame thiếu TXT làm âm.
3. Ba DETRAC cùng nhóm cảnh bảo thủ, không coi là ba camera độc lập. Các nguồn khác vẫn cần kiểm nguồn/camera/sự kiện và hard negatives khi mở rộng đánh giá.
4. Khi đủ điều kiện, tạo split theo nhóm và huấn luyện/đo B0 → phân tích FP/FN → B1/B2/T0/GRU theo bằng chứng. Nguồn chỉ có nhãn clip không được dùng như bbox GT; thay baseline cần ghi quyết định rõ.

### Người đang có pilot hiện tại cần làm gì ngay? — 24/10/2026

- Không cần tải lại CADP/DETRAC/model. Đọc [reference mới](../reference/2026-10-24-public-data-review.md) để hiểu paper dùng tín hiệu gì và vì sao chọn nguồn STTAD.
- Nhấn `Ctrl+P` trong VS Code, nhập `outputs/audits/sttad_public_6/author_region_examples.jpg`: trái là ảnh nguồn, phải là bbox tác giả; không phải dự đoán model. Xem `outputs/audits/pilot_groups/scene_overview.jpg` để hiểu các nguồn/cảnh. Không cần xác nhận lại xe/96–130 của CADP.
- Mở `outputs/audits/cadp_b0_quality/frame_quality.csv` và `outputs/audits/sttad_public_6/frames.csv`: đọc cột status/reasons để thấy frame nào được giữ/loại, thay vì phải tự đoán thiếu nhãn.
- AI tiếp tục kiểm/chuẩn hóa cặp public và chuẩn bị dữ liệu theo policy. Người dùng không cần gửi thư xin nhãn hoặc đưa giảng viên duyệt quyết định kỹ thuật.

### Bổ sung 25/10: tải đúng mẫu ACCIDENT, không tải cả bộ

Nguồn: [Kaggle tác giả, phiên bản 9](https://www.kaggle.com/datasets/picekl/accident/versions/9), [paper](https://arxiv.org/abs/2604.09819). API từng file đã kiểm truy cập công khai, không cần xin nhãn hoặc tải archive khoảng 20 GB.

```powershell
.\.venv\Scripts\python.exe -X utf8 -B scripts/audit_accident_public.py --fetch-selected --max-mib 16
.\.venv\Scripts\python.exe -X utf8 -B scripts/check_project_assets.py --profile accident --check-hashes --strict
.\.venv\Scripts\python.exe -X utf8 -B scripts/audit_accident_public.py --verify-report outputs/audits/accident_public/report.json
```

Script lấy **`metadata-real.csv` và đúng sáu MP4** trong `real_videos/`: `0NixrF6Mt00_0_00.mp4`, `04O2SOGSG_U_00.mp4`, `2QZf8MiIRK0_00.mp4`, `1_F0r7KVJ1k_00.mp4`, `-FQxK6HdxNU_00.mp4`, `0PrAtifCwjg_00.mp4`. Video/CSV lưu tại **`data_raw/accident/public_selected/`**, giữ tên và đường dẫn nguồn. Sáu video khoảng 5,4 MB; ngân sách tổng một lần chạy 16 MiB. Không lấy các clip khác hoặc trọng số model.

Kết quả ở **`outputs/audits/accident_public/`**: `images/` là PNG impact sạch, `labels_yolo/` là bbox chuyển đổi, `impact_comparisons.jpg` dùng đối chiếu. `verification.json` kiểm lại pixel/hash/PTS; FFprobe độc lập được dùng nếu đã cài. Giữ bản ảnh sạch riêng với ảnh vẽ GT. Nếu output/verification đã có, mở kết quả; khi chủ động chạy lại phải dùng `--output` mới hoặc chế độ kiểm thích hợp, không xóa/ghi đè bằng chứng.

Mốc 25/10 đã xong bước này: bốn bbox được giữ, hai bbox loại theo [phiếu kiểm AI](../data/reviews/2026-10-25-accident-source-review.json). Pool v2 khi đó có 2.380 dòng, 35 dương/2.345 âm và chưa split/train; hiện đã có v3 và pilot ở mục 1. `no_frames` nguồn không bằng số decode ở sáu mẫu; mapping đã kiểm bằng PTS, không sửa index theo FPS trung bình. FPS ghi hình gốc vẫn chưa xác minh.

Sau clone, audit mới có thể khác hash báo cáo vì môi trường/code hoặc số byte tải, trong khi media vẫn khớp. Giữ review gốc; AI đối chiếu fingerprint và kết quả kiểm thật rồi lập phiếu kiểm có phạm vi cho bản tái tạo nếu cần. Không thay hash cũ để vượt chốt; không yêu cầu rà lại CADP/DETRAC đã xác nhận nếu fingerprint đúng.

## 7. Giao việc cho một AI mới

Có thể gửi nguyên đoạn sau sau khi mở repo trong IDE:

> Đọc AGENTS.md, README.md và **progress/README.md** trước khi làm; bảng đó tổng hợp mọi baseline và dẫn tới nhật ký mới nhất. Đọc docs/b0_pilot_audit.md, data/b0_readiness.json và policy để biết dữ liệu/gate thật; kiểm media bằng scripts/check_project_assets.py, không suy file đã có sau clone từ manifest Git. CADP 001407 và ba DETRAC đã xác nhận, không hỏi lại nếu fingerprint đúng. Chỉ dùng nguồn public; AI tự đọc/so sánh/ghi căn cứ, không giao người dùng xin tác giả hoặc chờ giảng viên. Không tự biến nhãn thiếu thành âm, bbox xe thành vùng accident hoặc timing trình chiếu thành FPS nguồn. Theo đúng baseline/điều kiện chuyển bước; không tải toàn dataset, đổi model, split hoặc train khi chưa đủ điều kiện. Trước khi kết thúc cập nhật mục baseline trong progress/README.md và đúng một nhật ký progress/YYYY-MM-DD.md theo Asia/Bangkok.

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

## 9. Lần train normal mở rộng đã chuẩn bị — 28/10/2026

**Trên máy phát triển hiện tại đã tải/kiểm/xuất xong, không cần tải lại.** Chạy `scripts/train_b0.py --config configs/b0_normal_expanded_v1.json --check` trong `.venv` để kiểm dữ liệu thật; khi đạt có thể dùng `--train`. [Nguồn, số liệu và toàn bộ lệnh train](b0_pilot_audit.md#b0-normal-mở-rộng--28102026). Model mới đã train đủ 60 epoch; kết quả tại `outputs/training/b0_normal_expanded_v1/experiment.json`. Bảng `reference_val` giữ checkpoint cũ đo trên cùng validation 217 ảnh; snapshot sau train ở `docs/evidence/2026-10-28-b0-normal-training.json`.

Nguồn là [TAD tác giả](https://github.com/UnicomAI/UnicomBenchmark/tree/main/TADBench), link ZIP public trong repo. Chỉ cần đúng **18 MP4 `train/normal`** liệt kê ở `configs/b0_normal_expansion_v1.json`; tổng khoảng 123 MiB raw. Đặt giữ nguyên đường dẫn member dưới `data_raw/tad/public_selected/TAD-benchmark/train/normal/`, không lấy các clip `test/normal` đã xem để train. `data/download_catalog.json` có size/SHA và nơi đặt từng clip, `data/reviews/2026-10-28-b0-normal-expansion-review.json` giữ nhóm/split, `docs/evidence/2026-10-28-b0-normal-expansion.json` giữ thông tin media/split và số liệu sau kiểm.

Trên máy clone **chưa có thư mục audit batch**, công cụ tải đúng member theo CRC/size, không tải toàn ZIP 4,54 GB:

```powershell
.\.venv\Scripts\python.exe -X utf8 -B scripts/inspect_public_zip.py --max-mib 256 --fetch-plan configs/b0_normal_expansion_v1.json --audit-dir outputs/audits/b0_normal_expansion_v1
.\.venv\Scripts\python.exe -X utf8 -B scripts/inspect_public_zip.py --prepare-normal-batch configs/b0_normal_expansion_v1.json
```

File raw đã có đúng CRC sẽ được dùng lại; file khác nội dung bị chặn. Không chạy lại hai lệnh này lên audit đã hoàn tất chỉ để vượt lỗi tồn tại thư mục. Công cụ trích đều 30 frame/clip, decode đủ trước chọn, lưu PNG và `normal_manifest.json` tại `outputs/audits/b0_normal_expansion_v1/`. Khôi phục release B0 cũ theo các mục trước rồi đối chiếu source fingerprint/review, không sửa hash cũ để chấp nhận một audit mới khác byte. Sau clone, metadata/evidence trên Git chưa chứng minh dataset PNG và checkpoint đã có.

Dataset cuối là `data/processed/b0_normal_expanded_v1/dataset/dataset.yaml` (2.170 ảnh); 120 frame holdout âm nằm ngoài train/val theo `data/registries/b0_normal_expanded_v1_holdout.json`. Chỉ gọi `--train` sau `--check` thành công; config giữ recipe LR0,001 đủ60, kết quả vào `outputs/training/b0_normal_expanded_v1/`. Sau train so với các mốc **cùng 217 ảnh val**, không so trực tiếp với metric val cũ97 ảnh và không dùng holdout/test để chọn model.

### Sau run normal-expanded: s960 đã hoàn tất

S960 đã dừng sớm ở45/100, patience15, best CSV epoch30. [Kết quả và file cần mở](b0_pilot_audit.md#kết-quả-b0-s960-hoàn-tất--28102026). Không chạy lại `--train` hoặc `--resume` vào run đã hoàn tất. Các hướng dẫn tải/chuẩn bị sau đây phục vụ máy clone và thí nghiệm có output mới. Dữ liệu vẫn như mục9; trên máy hiện tại đã có `yolov8s.pt` và preflight đạt. Sau clone chỉ tải checkpoint thêm từ [GitHub chính thức](https://github.com/ultralytics/assets/releases/download/v8.4.0/yolov8s.pt), đặt **`yolov8s.pt` ở thư mục gốc**, kiểm SHA theo `configs/b0_s960_v1.json`/catalog. Không thay tên checkpoint n để giả thành s. Chạy `--check` trước `--train`; kết quả mới chỉ xuất hiện khi người dùng gọi lệnh train.

### Sau train: điểm vận hành và trạng thái holdout29/10

Đã chọn s960/conf0,27 trên217val, rồi đo một lần120ảnh âm giữ riêng:34ảnh có hộp. [Kết quả và nơi mở](b0_pilot_audit.md#chọn-ngưỡng-và-đánh-giá-holdout-âm--29102026). Khóa `configs/b0_s960_v1_operating_point_v1.json` giữ checkpoint/imgsz/confidence và SHA bằng chứng; không làm thay mAP hoặc cấu hình train.

Holdout trong hồ sơ hiện đã consumed. Người clone không sửa model_predictions_seen vềfalse hoặc đổi hash để chạy lại như test chưa xem. Media vẫn phục hồi theo catalog; metadata không chứng minh file đã có trên máy mới. Report lớn/cache ở outputs, snapshot nhỏ đọc được sau clone. Trạng thái B1 sau bước chuẩn bị tiếp cùng ngày ghi ở mục dưới; các lệnh video phương tiện cũ vẫn dùng detector xe riêng.

### Lượt chuẩn bị tiếp29/10: âm khó và B1, dừng trước train

**Cập nhật sau đó29/10:** `b0_s960_hardneg_v1` đã được người dùng train xong15epoch và đo307val. [Kết quả và file cần mở](b0_pilot_audit.md#kết-quả-s960-hardneg-hoàn-tất--29102026). Mục dưới giữ cách phục hồi dữ liệu/lịch sử chuẩn bị; **không chạy lại train/resume vào output đã hoàn tất**. Checkpoint mới ở`outputs/training/b0_s960_hardneg_v1/weights/best.pt`; snapshot chuẩn bị nói chưa train là trạng thái trước đó, không ghi đè.

Trên máy phát triển đã có24MP4 TAD mới và dataset `data/processed/b0_s960_hardneg_v1/dataset/dataset.yaml`2.680ảnh; **không cần tải lại**. Các nguồn mới vẫn là author`train/normal`, đường dẫn raw `data_raw/tad/public_selected/TAD-benchmark/train/normal/`; đúng tên24file trong [fetch plan](../configs/b0_hard_negative_sources_v1.json), catalog có SHA/size. Không tải cả TAD ZIP hoặc thêm nhãn accident từ prediction.

Trên máy clone chưa có raw/audit, tải chọn lọc bằng công cụ hiện có:

```powershell
.\.venv\Scripts\python.exe -X utf8 -B scripts/inspect_public_zip.py --max-mib 384 --fetch-plan configs/b0_hard_negative_sources_v1.json --audit-dir outputs/audits/b0_hard_negative_sources_v1
.\.venv\Scripts\python.exe -X utf8 -B scripts/inspect_public_zip.py --prepare-normal-batch configs/b0_hard_negative_sources_v1.json
```

Nếu lần tải dở chưa córeport, thêm`--resume-fetch` vào lệnh tải, giữ audit và ledger; không xóa để reset budget. Nếu audit đã hoàn tất thì đọc lại, không chạy lại để ghi đè. Đợt này khoảng260MiB raw, không toàn4,54GB; nên có vàiGiB trống cho PNG/dataset/output. Không sao chép các file có tên gần giống để vượt fingerprint.

Để dựng đúng phiên bản đã khóa cần khôi phục **audit batch + review/index/split + checkpoint s960 best** đúng SHA, cùng dữ liệu cũ2.170ảnh; raw MP4 một mình chưa thay thế bằng chứng frame đã chọn. Checkpoint cần dùng là `outputs/training/b0_s960_v1/weights/best.pt`, **không phải** pretrained`yolov8s.pt`. Trọng số đã fine-tune không có URL public do project chưa phát hành; lấy bản sao từ máy đã train hoặc tái lập run trước thành thí nghiệm mới, không sửa hash cũ để giả trùng. [Quy trình và lệnh hiện hành](b0_pilot_audit.md#chuẩn-bị-s960-hardneg-v1--29102026).

Mở `outputs/audits/b0_hard_negative_sources_v1/index.html` xem nguồn/split/mốc val và trạng thái train hiện có; `train_preflight.json` chỉ ghi kiểm decode/bbox/forward trước train. Mở `outputs/training/b0_s960_v1/temporal_diagnostics_v1/index.html` xem B0/B1 cũ; kết quả hardneg mới ở`outputs/training/b0_s960_hardneg_v1/diagnostics/index.html`. Lệnh `train_b0.py --config configs/b0_s960_hardneg_v1.json --check` vẫn kiểm dữ liệu được, nhưng run hiện đã hoàn tất; không dùng `--train` hoặc `--resume` để ghi thêm vào run đó. Thí nghiệm tương lai cần config/output mới, không sửa hash của config hoàn tất.
