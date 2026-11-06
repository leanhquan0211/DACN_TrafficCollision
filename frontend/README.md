# Traffic Observatory — dashboard đồ án

Explore → **Tìm artifact** tìm chung kết quả trong cây mới và LEGACY theo tên/ID/path, có bộ lọc loại và trạng thái. API `/api/artifacts` chỉ đọc registry và metadata thư mục. Quy ước lưu mới và bảng dependency lịch sử nằm tại [kiến trúc artifact](../docs/STORAGE_ARCHITECTURE.md); hướng dẫn migration cũ bên dưới là lịch sử trước kiến trúc này.

Giao diện local tiếng Việt đọc **artifact thật**, không train, resume, hủy run hoặc sửa dataset/nhãn/checkpoint. Gồm tổng quan, biểu đồ theo epoch, so sánh, dữ liệu, ảnh/video và tra cứu. Thiết kế và giới hạn ở [DESIGN](DESIGN.md).

## Mở trên máy hiện tại

Tại **gốc project**, chạy:

```powershell
.\.venv-dashboard\Scripts\python.exe -X utf8 -B scripts/serve_dashboard.py
```

Mở **http://127.0.0.1:8765**. Frontend cần được build như mục dưới; máy phát triển đã có bản build kiểm ngày 04/11/2026. Đóng terminal/Ctrl+C dừng web local; không ảnh hưởng train Kaggle.

Giao diện ngày 04/11/2026 dùng màu hồng phấn/tím than theo ảnh tham khảo. Bấm **biểu tượng thanh trượt ở góc phải trên → Kiểu chữ** để chọn font. Mặc định vẫn là **Be Vietnam Pro cho tiêu đề + Geist cho nội dung**; có thêm Be Vietnam Pro toàn bộ, Inter toàn bộ và Lora tiêu đề + Inter nội dung. Mẫu chữ tiếng Việt hiện ngay trong bảng tùy chỉnh; lựa chọn được nhớ trên trình duyệt này. Bấm **Khôi phục mặc định** để quay về font và các tùy chỉnh gốc. Chuyển sáng/tối bằng biểu tượng mặt trăng/mặt trời bên cạnh.

## Cài sau clone

Node đã kiểm: **26.10.0**, npm **11.19.1**. Phiên bản package frontend khóa bằng `package-lock.json`; không copy `node_modules` từ project workshop. Môi trường web Python tách riêng `.venv-dashboard`, không cài đè `.venv` train.

Font lấy từ các gói Fontsource đã khóa phiên bản và build vào frontend để xem offline, không dùng CDN. Inter/Lora có subset tiếng Việt trong package; lựa chọn font chỉ ảnh hưởng cách đọc, không ảnh hưởng kết quả. Cách dùng font hệ thống như Times New Roman không được chọn vì cách hiển thị giữa máy có thể khác nhau; thêm hai gói làm bản build lớn hơn một chút nhưng không đưa `dist/` hoặc `node_modules/` lên Git.

```powershell
# Tại gốc project
py -3.12 -m venv .venv-dashboard
.\.venv-dashboard\Scripts\python.exe -m pip install -r requirements-dashboard.txt

Set-Location frontend
npm ci
npm run build
npm run lint
Set-Location ..
.\.venv-dashboard\Scripts\python.exe -X utf8 -B scripts/serve_dashboard.py
```

Nếu muốn sửa UI với hot reload, giữ API ở terminal trên; terminal khác vào `frontend` chạy `npm run dev`, mở URL Vite in ra. Vite proxy `/api` về `127.0.0.1:8765`. Với bản build, chỉ cần một server Python, không cần Vite chạy cùng.

Clone Git không có media/dataset/checkpoint trong `outputs/`; các file hướng dẫn nhỏ có thể có. Khi chưa phục hồi artifact, giao diện hiển thị chưa có run, không tự tải hoặc tạo dữ liệu demo. Đọc [GETTING_STARTED](../docs/GETTING_STARTED.md), [kiến trúc output hiện hành](../docs/STORAGE_ARCHITECTURE.md) và [hướng dẫn run B0 lịch sử](../outputs/training/README.md). Không cần GPU hoặc cài PyTorch vào môi trường dashboard để xem kết quả đã có.

## Nguồn dữ liệu và cách đọc

| Vùng giao diện | Nguồn |
| --- | --- |
| Danh sách/config/best revalidation | Resolver/registry tìm `outputs/baselines/<baseline>/<version>/` hoặc `outputs/training/<run>/` LEGACY; đọc `experiment.json` và config snapshot |
| Đường học/log epoch | `results.csv`; bỏ dòng chưa ghi đủ, không nội suy |
| P/R/F1 tại ngưỡng cố định | `fixed_threshold_metrics.val` hoặc `cases_val/metrics.json` |
| Ảnh gốc | `training_summary/results.png`, `metrics_val/Box*curve.png` và confusion matrix |
| Dữ liệu | Provenance của release; với run cloud đọc member provenance trong ZIP bundle sẵn có, không giải nén media. Histogram bbox val dùng kích thước PNG sạch gốc nếu còn local, thiếu ảnh thì ghi skipped |
| Gallery | `cases_val/predictions.json`, ảnh so sánh và ảnh sạch local nếu còn tồn tại |
| Video/B1 | `b0_s960_v1/temporal_diagnostics_v1/report.json`, `videos/<sequence>/frames.csv` và MP4 |
| Tiến độ/tài liệu | File gốc trong `progress/`, `docs/`, `reference/`; không ghi lại qua UI |

- P/R trong đường epoch/log là điểm Ultralytics báo, có thể khác P/R/F1 fixed ở confidence 0,25/IoU 0,5. mAP không phải accuracy video; bbox FP không phải false alerts/hour.
- Best đánh dấu từ mAP50–95 raw trong CSV; các thẻ best dùng **đánh giá lại checkpoint** từ experiment, không lấy giá trị epoch cuối hoặc đường làm mượt.
- So sánh báo cùng provenance/ngưỡng hoặc khác protocol; kể cả cùng fingerprint vẫn phải đọc khác biệt config và giới hạn một seed/validation tái sử dụng. Run thu hồi không vào nhóm so sánh chất lượng.
- Kiểm kê nguồn mặc định cả release; chọn **Chỉ train** để đọc số train, không nhầm 1.213 dương train+val với 1.122 dương train. Số ảnh, clip và nhóm nguồn khác nhau.
- Ảnh gallery đã vẽ sẵn không thể bật/tắt hộp. Khi tìm được ảnh sạch, modal có hai lớp GT/prediction độc lập; GT xanh, prediction san hô nét đứt. Không tạo prediction hoặc GT mới.
- Video B1 dùng **s960 cũ/conf0,27**, không phải V11. CADP 96–130 là interval đã review theo frame; tua theo media không cung cấp timing nguồn hay độ trễ event.
- Các dấu baseline chỉ ghi nhận artifact hiện có, không tự nghiệm thu. `progress/README.md` vẫn là bảng tiến độ nguồn; B2/T0/GRU hiện chưa có kết quả đăng ký.

## Theo dõi file local và Kaggle

**Một lựa chọn run ở đầu trang:** `K09`–`K12` là **version của notebook Kaggle**; `L01`–`L09` là thứ tự hiển thị các pilot local cũ. Đây chỉ là tên dễ đọc trên web, không đổi ID/thư mục/checkpoint gốc. Ví dụ `K12 · SGD LR 0,00015` trỏ tới `outputs/training/b0_s960_sgd_low_lr_kaggle_v4/` và notebook Kaggle Version 12. Cùng một run chỉ xuất hiện **một lần**: nếu mới gửi Kaggle, web đọc trạng thái/log từ API; khi đã fetch, web dùng CSV/checkpoint/metric/ảnh local và vẫn hiện trạng thái cloud nhỏ ở cùng trang. Không còn ô chọn version Snapshot riêng hoặc biểu đồ epoch lặp lại.

**Tự cập nhật khi web đang mở:** danh sách run local + deployment Kaggle đọc lại mỗi **15 giây**; run đang chọn đọc file local mỗi **10 giây** và trạng thái/log Kaggle mỗi **30 giây** nếu có version tương ứng. Khi có deployment mới, run mới tự xuất hiện trong danh sách; web giữ run bạn đang xem, không tự chuyển sang run khác. Khi fetch xong, cùng mục đó tự chuyển sang nội dung local đầy đủ. Đóng web hoặc tắt máy thì polling dừng; Kaggle vẫn chạy độc lập. Cache cloud tối thiểu 20 giây, timeout 35 giây; log API có thể đến chậm. Dashboard **không tự tải** `best.pt`/output lớn, không train/hủy/resume, không đánh giá test/reserve. Lệnh fetch có kiểm hash theo [hướng dẫn Kaggle](../docs/kaggle_training.md).

Nếu web báo `proxy_unreachable`, server dashboard đang chạy trong môi trường không ra được Kaggle (đã gặp khi khởi chạy trong sandbox công cụ); đóng server đó và chạy lệnh mở dashboard ở đầu file bằng PowerShell của máy. Không cần gửi lại notebook hoặc cài lại Kaggle. Nếu API trạng thái đọc được nhưng endpoint log lỗi, web vẫn hiển thị trạng thái và báo riêng log chưa có. Lỗi 401/403 cần đăng nhập lại CLI đúng tài khoản. Dùng đúng Notebook `laqun0211/dacn-b0-s960-full-v1` đang có; công cụ chưa cấu hình nhiều owner.

Cần môi trường CLI và đăng nhập local theo [kaggle_training](../docs/kaggle_training.md). Trình đọc dùng `.tmp/kaggle_cli_env/Scripts/python.exe` để tách SDK khỏi web/train. Nếu chưa có môi trường hoặc không có quyền, web báo đúng giới hạn và lịch sử vẫn xem được. Không đưa token vào web, `.env` frontend hoặc Git.

Đã kiểm đọc thực tế Version 11: API trả COMPLETE và 50 epoch. Ngày 04/11, Version 12 đã được tải về bằng `fetch`, kiểm SHA/manifest/`run_status.json` có `training_completed=true`, 50 epoch và `best.pt`/`last.pt`. Web đọc bản local này và trạng thái cloud `COMPLETE` trên cùng trang. Không suy `COMPLETE` của notebook thay cho kết quả được kiểm; chỉ bản đã fetch mới cho metric best và ảnh gốc.

## Kiểm và cấu trúc

```powershell
.\.venv-dashboard\Scripts\python.exe -X utf8 -B -m unittest tests.test_dashboard -v
.\.venv-dashboard\Scripts\python.exe -m pip check
```

`src/dashboard_data.py` chuẩn hóa artifact; `src/dashboard_cloud.py` đọc cloud; `scripts/serve_dashboard.py` chỉ phục vụ API/media/front-end build. Mã UI tập trung trong `frontend/src/`, token tại `tokens.css`. Không cần database/tài khoản web cho bản local.

API chỉ đăng ký ảnh/video/tài liệu bằng media ID, chặn đường dẫn ngoài project và không có endpoint điều khiển train. Bind loopback `127.0.0.1`; chưa thiết kế để công khai Internet. Raw/output/model và `.venv-dashboard`, `node_modules`, `dist`, kiểm trình duyệt/`.hallmark` không đưa Git. Push code, package lock, requirements web và tài liệu; người clone build lại.

Hạn chế hiện tại: phần tra cứu Markdown hiển thị văn bản nguồn; chưa có công cụ sửa nhãn, tự tạo event hoặc pipeline suy luận online. Không có ảnh/metric của run thì hiển thị thiếu; không tải thêm để lấp UI.

## Khám phá đồ án và kiểm kê

Mở `http://127.0.0.1:8765/explore`. Các tab trình bày mục đích, dữ liệu, run, cấu trúc, luồng hệ thống và dung lượng. Bấm một baseline hoặc nguồn để xem chi tiết; trang Huấn luyện vẫn là nơi xem đường cong và log. So sánh nhanh chỉ hỗ trợ kết luận khi cùng provenance và ngưỡng; metric validation ảnh không phải metric sự kiện.

`data/registries/project_explorer.json` ánh xạ baseline/version và đường dẫn thật. B2 đã có hai thư mục vật lý dưới `outputs/baselines/03_b2_motion_rules/`; B0/B1 vẫn ở vị trí lịch sử. `01_b0_image_detection`, `02_b1_temporal_filter`, `04_t0_mlp`, `05_b3_gru` vẫn là nhóm logic, chưa tạo thư mục trống. B3 và T1 cùng một nhánh GRU. Alias `vNNN_mo_ta` khác run ID và Notebook Version; không suy thứ tự từ tên cũ hoặc thời gian file. Run chưa ánh xạ hiển thị chưa phân loại.

Số file được ghi trong snapshot `outputs/audits/project_explorer_inventory*.json`: có thể trùng giữa bản gốc, bản cắt, release và kết quả; không cộng chúng để suy ra số sự kiện độc lập. Số train/validation lấy từ provenance đã tải về của run K12; test/reserve không nằm trong gói train này, không suy rằng toàn dự án không có test. Quét metadata thủ công khi cần, không đọc nội dung ảnh hoặc tự xóa/ghi đè file:

```powershell
.\.venv-dashboard\Scripts\python.exe -X utf8 -B scripts/inventory_explorer.py
```

Web đọc snapshot có `recorded_at` mới nhất theo tên hợp lệ và cache tối đa 30 giây; nó không tự quét dataset mỗi khi mở trang. Nếu snapshot không có hoặc clone chưa có media, giao diện báo thiếu. Xem ngày quét và lỗi đọc trước khi sử dụng số liệu.

### Migration vật lý 05/11 và phần giữ lại

| Đường dẫn cũ | Đường dẫn hiện tại/đề xuất | Trạng thái và phụ thuộc |
| --- | --- | --- |
| `outputs/audits/b2_motion_v1/`, `b2_motion_v2/` | `outputs/baselines/03_b2_motion_rules/v001_motion_pilot/`, `v002_overlap_fix/` | Đã chuyển; 26 file, hash từng file khớp. |
| `outputs/audits/event_evaluator_v1/` | `outputs/shared_evaluations/v001_event_evaluator/` | Đã chuyển; 18 file. Snapshot bên trong giữ nguyên chuỗi path lịch sử. |
| `outputs/audits/b2_system_v2/` | `outputs/system_evidence/v001_b2_alerts/` | Đã chuyển; 129 file ảnh/clip/metadata. |
| `outputs/audits/detrac_preparation/` | `outputs/data_audits/v001_detrac_preparation/` | Đã chuyển; 2 file, script đọc report dùng resolver. |
| `outputs/training/<run>/` | Đích sau migration an toàn: `outputs/baselines/01_b0_image_detection/<alias>/` | **Chưa di chuyển run cũ**: config/snapshot, checkpoint reference và B1 lồng trong B0 còn tham chiếu đường dẫn lịch sử. Train mới và Kaggle fetch mới đã dùng cây chuẩn; move run cũ vẫn cần plan, SHA, verify và rollback riêng. |
| `outputs/kaggle/`, raw, processed release, archive và audit còn lại | Giữ nguyên | Artifact lớn, nguồn phục hồi hoặc chứa hash/review lịch sử; chưa xác minh đủ dependency để đổi. |

Công cụ [migrate_outputs.py](../scripts/maintenance/migrate_outputs.py) có `--plan`, `--apply --group`, `--verify`, `--rollback --group`; manifest thực tế tại `outputs/audits/storage_migration_v1/manifest.json` ghi SHA-256 từng file, byte và trạng thái, bị Git ignore cùng output. Di chuyển chỉ dùng rename cùng filesystem, kiểm file lock/OneDrive placeholder và từ chối destination tồn tại. Ví dụ: `python scripts/maintenance/migrate_outputs.py --verify`. Khi rollback một nhóm, resolver trong `src/storage_paths.py` tự đọc vị trí cũ; các liên kết Markdown cập nhật theo path mới phải được khôi phục riêng nếu muốn dùng giao diện tài liệu ở trạng thái rollback. Không chỉnh experiment snapshot hay provenance lịch sử.

B0/B1 chỉ nên chuyển ở một đợt riêng sau khi mọi config và công cụ train/fetch dùng chung resolver, kiểm liên kết checkpoint và B1 diagnostics, lập manifest SHA trước/sau và chạy test. Mức rủi ro cao vì có khoảng 97 file code/config/manifest/tài liệu chứa tham chiếu tới ba khu output cũ; con số này là kết quả tìm text, chưa chứng minh hết tham chiếu trong artifact hoặc notebook bên ngoài. Rollback dự kiến là rename ngược theo manifest, rồi xác minh byte/SHA; không có bước cleanup tự động. `.gitignore` bao phủ toàn bộ `outputs/**`, nên output mới không được đưa lên Git.

Chuỗi phụ thuộc B0 lịch sử là `configs/b0*.json → train_b0.py/analyze_b0.py → experiment.json/checkpoint`; các config/snapshot cũ vẫn chứa đường dẫn và hash gốc nên không sửa ngược. `kaggle_b0.py fetch` hiện xác minh ZIP rồi lưu vào B0 canonical; fixture đã kiểm byte checkpoint và cập nhật registry. `DashboardStore` dùng resolver để đọc run ở cả hai vị trí; B1 lịch sử vẫn nằm trong `b0_s960_v1/temporal_diagnostics_v1`. Các audit lớn `accident_scale` (~4 GiB), `b0_hard_negative_sources_v1` (~2,56 GiB), `b0_normal_expansion_v1` (~0,92 GiB), backup và hồ sơ test giữ **PROTECT**. Kaggle bundle và raw cũng giữ tại chỗ. Bảng phụ thuộc chi tiết, cập nhật cho từng thư mục, nằm ở [kiến trúc lưu trữ](../docs/STORAGE_ARCHITECTURE.md).
