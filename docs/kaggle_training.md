# Chạy B0 trên Kaggle

**Cập nhật kết quả Version 10:** phiên đã hoàn tất 60 epoch và đã fetch/kiểm hash về `outputs/training/b0_s960_adamw_kaggle_v2/`. Best theo CSV/train_metrics ở epoch 52; đánh giá lại best trên 307 val: mAP50 67,85%, mAP50–95 52,63%, F1 cố định 67,06%, Recall cố định 62,64%. So Version 9 cùng tập, mAP và recall cố định giảm, F1 nhích lên; chưa thay model B0 khóa. [Báo cáo đầy đủ](b0_pilot_audit.md#kết-quả-version-10--adamw-kaggle-30102026), [bằng chứng](evidence/2026-10-30-b0-adamw-validation.json). Các mục đang chạy bên dưới là lịch sử; không chạy fetch lại vào output đã có.

## Hiện hành: Version 10 — AdamW, AMP và early stopping muộn

Version 9 hoàn tất 11 epoch, best epoch 1; đánh giá lại best trên 307 val cho khoảng **mAP50 69,8%, mAP50–95 55,9%, Recall 58,2%**. Epoch 11 thực tế khoảng mAP50 63,5%/mAP50–95 50,8%; dòng đánh giá lại best sau train không phải kết quả epoch 11. Đã đọc log, giữ kết quả trên Kaggle Version 9 và không tải bộ checkpoint cũ về laptop. Mức tăng nhẹ chưa đủ để thay model B0 khóa.

Theo yêu cầu điều chỉnh lớn, đã gửi **Version 10**, run `b0_s960_adamw_kaggle_v2`, PRIVATE; API trả RUNNING lúc gửi. Phép kiểm backward 3 bước đã đạt; lúc đọc log đã đến epoch 7 với mAP50 47,11%, thấp hơn best run cũ. **Đây là kết quả trung gian, chưa kết luận chất lượng cuối.** Dùng cùng 2.988 ảnh (2.681 train/307 val), cùng checkpoint s960 cũ và YOLOv8s/960. Dataset đã có, không upload lại; test/reserve ngoài luồng train và đánh giá tự động.

| Thành phần | Version 9 | Version 10 |
| --- | --- | --- |
| Optimizer | SGD | AdamW, lr0=0,0003, beta1=0,9 |
| Batch/kiểu số | 2/FP32 | 8/AMP FP16+FP32, GPU0 |
| nbs | 64 | 32, thường tích lũy 4 batch sau warmup |
| Lịch LR | tuyến tính | cosine, lrf=0,05, warmup 5 epoch, bias LR 0 |
| Mosaic/scale | 0,5/0,3 | 0,2/0,15, tắt mosaic 15 epoch cuối |
| Epoch/dừng sớm | tối đa 40, patience 10, dừng ở 11 | tối đa 60, chỉ đếm chờ sau 25, patience 25; plateau sớm nhất epoch 50 |
| Workers | 0 | 2, cache=False |

Đây là thử nghiệm gộp nhiều thay đổi, không phải ablation hoặc bảo đảm vượt 70%. AdamW/cosine tham khảo paper và mã Ultralytics 8.4.178; giảm augmentation là điều chỉnh theo các bbox nhỏ đã đo, không sao tham số paper khác bài toán. AMP chủ yếu cải thiện hiệu quả tính toán, không tự bảo đảm tăng accuracy. Ultralytics có thể tải checkpoint YOLO26n nhỏ chỉ để kiểm AMP; model được train vẫn YOLOv8s.

Trước epoch đầu, callback đo 3 bước forward/backward/AdamW trên **bản sao** với ảnh và nhãn train thật, kiểm finite loss/gradient và VRAM. Không lưu trọng số probe hoặc sửa trọng số thực/val/test. Nếu probe không phù hợp sẽ báo lỗi. Báo cáo `backward_preflight.json` xuất khi kiểm thành công; đây không phải metric chất lượng và không bảo đảm mọi batch đều vừa VRAM.

**Đính chính về batch:** config yêu cầu batch 8, nhưng kiểm lại mã Ultralytics 8.4.178 cho thấy trainer có cơ chế tự giảm batch nếu OOM ở epoch đầu; config Version 10 ghi “no automatic batch fallback” nhưng chưa vô hiệu hóa cơ chế thư viện. Log lọc trên laptop sẽ hiện cảnh báo giảm batch; sau train phải kiểm `live_console.log` trước khi kết luận batch thực tế, vì `args.yaml` có thể vẫn ghi batch được yêu cầu ban đầu. Điều này không thay chính sách early stopping đã đặt.

AMP đã được bật và vượt 3 bước kiểm trên bản sao; trainer Ultralytics còn có phép kiểm AMP riêng và có thể tắt AMP nếu phép kiểm của nó thất bại. `runtime_environment.json` ghi giá trị yêu cầu, vì vậy phải xem `live_console.log` để xác nhận AMP thực tế trước báo cáo cuối.

Notebook chỉ thêm code/config có hash vào `runtime/` và module phụ trợ; bundle 4 GB và manifest cũ giữ nguyên. Checker kiểm release gốc trước khi chấp nhận recipe mới đã khóa. Đã kiểm input thật trên view hardlink: 2.988 mẫu, không copy media hoặc train laptop; 92 unittest đạt.

Theo dõi **chỉ theo epoch**, không hiện tiến độ từng batch:

```powershell
.\.venv\Scripts\python.exe -X utf8 -B scripts/kaggle_b0.py logs --follow --epochs-only --version 10
```

Mỗi dòng có Epoch, box/cls/dfl loss, P/R/mAP50/mAP50–95. Trước train có thể chưa có dòng epoch; dùng logs không `--epochs-only` khi cần chẩn đoán cài đặt. Ctrl+C chỉ ngắt xem. Log raw đầy đủ vẫn giữ trên cloud trong `live_console.log`.

Sau khi Version 10 train thực sự hoàn tất, nhận đúng run mới bằng:

```powershell
.\.venv\Scripts\python.exe -X utf8 -B scripts/kaggle_b0.py fetch --experiment adamw-v2 --version 10
```

Đầu ra khi nhận sẽ vào `outputs/training/b0_s960_adamw_kaggle_v2/`; chuẩn bị/notebook/manifest ở `outputs/kaggle/b0_s960_adamw_kaggle_v2/`. Chưa chạy fetch. `prepare-recipe`/`publish-recipe` đã dùng; không gọi lại để gửi run trùng. Hướng dẫn Version 9 trở xuống là lịch sử. Căn cứ và khác biệt recipe được lưu trong [literature review](../reference/LITERATURE_REVIEW.md).

## Hiện hành: Version 9 sửa lỗi vẽ biểu đồ trước epoch

Version 8 đã qua GPU/data/forward, nhưng trainer dừng trước epoch vì kế thừa `MPLBACKEND=module://matplotlib_inline.backend_inline` từ kernel Kaggle vào venv không có inline backend. Không phải lỗi bbox/dataset hoặc thiếu VRAM. Chuyển `MPLBACKEND=Agg` trước khi tạo Python con; Agg vẫn xuất PNG curves/confusion matrix. Notebook mới kiểm xuất PNG bằng Python đã pin trước `execute`. Không sửa ZIP, nhãn/split/model/batch/recipe. 17 test bundle đạt, gồm xuất PNG thật khi môi trường cha mang backend inline lỗi. Căn cứ [Matplotlib backends](https://matplotlib.org/stable/users/explain/figure/backends.html).

Đã gửi Version 9 PRIVATE qua API để thử lại từ checkpoint khởi tạo đã khóa, không resume phiên lỗi vì chưa chạy epoch nào. Chưa xác nhận phiên mới đến epoch hoặc hoàn tất. Theo dõi đúng phiên:

```powershell
.\.venv\Scripts\python.exe -X utf8 -B scripts/kaggle_b0.py logs --follow --version 9
```

Log sẽ có `Plot backend Agg: passed` trước kiểm/train. Không upload dữ liệu hoặc gọi publish thêm. Các hướng dẫn Version 8 dưới đây là lịch sử; dùng Version 9 hiện tại.

## Hiện hành: đã chạy qua API sau xác minh — Version 8

Người dùng báo đã xác minh điện thoại; kiểm lại bằng API ở Version 7 xác nhận **2 Tesla T4, mỗi GPU 15.360 MiB, driver580.178.04, torch2.11.0+cu128, CUDA12.8, phép tính tensor GPU đạt và truy cập PyPI đạt**. Không cần tìm/chọn Accelerator trên giao diện cho lượt này. Kaggle CLI/API hỗ trợ yêu cầu GPU và Save & Run All trực tiếp; xác nhận bằng phần cứng quan sát được thay vì chỉ metadata. Không khẳng định một tài khoản khác có quyền gì khi chưa kiểm.

Đã gửi notebook train chính **Version 8** qua API, PRIVATE; API trả RUNNING lúc gửi. Giữ recipe/GPU0/batch2/FP32, không dùng đa GPU hoặc mở vòng tối ưu. Dùng lại Dataset; không upload ZIP. **Chưa xác nhận đã tới epoch hay hoàn tất train.** Không chạy publish/Run All/Save Version thêm. Mở [Logs](https://www.kaggle.com/code/laqun0211/dacn-b0-s960-full-v1) chọn Version 8, hoặc dùng `status`/`logs` bên dưới. Khi có kết quả train hoàn tất mới fetch.

Trạng thái Version 6 chờ thao tác UI và các bước hướng dẫn giao diện dưới đây là lịch sử/phương án dự phòng, không phải việc người dùng còn phải làm hiện tại. Chỉ dùng quota miễn phí; không billing.

**Chỉ dùng miễn phí theo yêu cầu người dùng:** không mua tài nguyên, bật AI Models trả phí hoặc kết nối billing Google Cloud. Các số Private Datasets/GPU/TPU trên trang quota là hạn mức tài khoản; không phải nơi chọn GPU. Hết quota thì dừng/chờ, không chuyển sang dịch vụ có phí.

**Notebook chính đã sửa được lưu ở Version 6 bằng Quick Save, chưa chạy.** Version 4 kiểm môi trường CPU riêng, không train: toàn bộ 2.988 ảnh qua kiểm hash và chuẩn bị, nhưng pip gặp DNS không phân giải pypi.org, chưa cài xong môi trường. Version 6 kiểm cả GPU và truy cập PyPI trước khi đọc/copy gói lớn. Để chọn GPU: mở link notebook → Edit → bảng bên phải Settings → Session options (có thể hiển thị Notebook options) → Accelerator → GPU T4 ×2; bật Internet On. Nếu bảng bị ẩn, mở lại sidebar hoặc tab Settings; giao diện hẹp có thể xếp các mục thành tab phía trên editor. Đây là vị trí trong notebook editor theo tài liệu Kaggle, khác Settings ở avatar tài khoản.

## Trạng thái và nguyên nhân đã kiểm — 30/10/2026

Dataset [dacn-b0-full-trainval-v1](https://www.kaggle.com/datasets/laqun0211/dacn-b0-full-trainval-v1) đã có, PRIVATE, ready và receipt khớp. **Không upload lại, không chạy prepare hay publish --allow-reupload.**

- Version 1 lỗi trước train: Kaggle tự giải nén ZIP thành thư mục `b0_full_bundle/`; đã sửa notebook nhận cả hai dạng và kiểm toàn bộ hash.
- Version 2 lỗi trước train: `nvidia-smi` không tồn tại, giao diện ghi Accelerator None. Metadata T4 không chứng minh đã được cấp GPU.
- Version 3 là **chẩn đoán, không train**: đã yêu cầu T4, image GPU chính thức có digest và Save & Run All rõ ràng, nhưng kết quả vẫn là `torch 2.11.0+cpu`, CUDA false, 0 GPU, không có `/dev/nvidia*`. Version này COMPLETE chỉ có nghĩa chẩn đoán xong. Không kết luận người dùng chưa xác minh tài khoản nếu chưa xem giao diện.
- Version 4 chỉ kiểm dữ liệu/cài môi trường/`--check` trên CPU cloud, **không gọi execute, --preflight hoặc --train**. Phần dữ liệu đã qua; phần cài môi trường bị chặn DNS PyPI nên chưa tới `--check`. Không phải kết quả huấn luyện.

Các lỗi license/403 trước đó đã vượt qua; lịch sử đầy đủ ở [nhật ký ngày](../progress/2026-10-30.md). Không cài nvidia-smi hoặc torch CUDA để giả lập một GPU chưa được Kaggle cấp. AI không tiếp tục gửi train khi chưa có bằng chứng GPU thật.

## Bước người dùng thực hiện trên giao diện

1. Mở [Notebook](https://www.kaggle.com/code/laqun0211/dacn-b0-s960-full-v1), xem phiên bản và mục đích của phiên. Chỉ bản có tiêu đề nội dung **B0 PRIVATE — train đầy đủ** mới là notebook chính; bản chẩn đoán không train.
2. Khi notebook chính đã được lưu trở lại, chọn **Edit**, mở **Settings/Notebook options → Accelerator → GPU T4 ×2**. Bật Internet; giữ PRIVATE. Chỉ dùng GPU0 theo recipe, không chuyển sang train đa GPU.
3. Nếu GPU bị khóa hoặc xuất hiện yêu cầu xác minh/điều khoản, hoàn thành trên tài khoản Kaggle tại https://www.kaggle.com/settings . Không gửi token/mật khẩu/mã xác minh vào chat. Nếu chọn T4 được, kiểm tra session thực sự báo GPU, không chỉ metadata. Đây là phần chưa thể thay bằng sửa code.
4. Kiểm tra Input đã có Dataset `laqun0211/dacn-b0-full-trainval-v1`; giữ nguyên dữ liệu hiện có, không tạo Dataset khác.
5. Chọn **Save Version → Save & Run All** đúng một lần. Không chạy Run All rồi đồng thời Save & Run All vì sẽ tạo hai phiên. Phiên lưu chạy trên cloud, có thể tắt laptop sau khi gửi xong.

Nếu cell đầu vẫn báo không có GPU, mở Output lấy `gpu_check.json`; không upload dữ liệu lại. Cell sẽ lưu trạng thái bị chặn và không cài môi trường hoặc train CPU.

## Theo dõi đúng bước

**Xem trực tiếp từng epoch của Version 8 trong terminal VS Code:**

```powershell
.\.venv\Scripts\python.exe -X utf8 -B scripts/kaggle_b0.py logs --follow --version 8
```

Lệnh kết nối luồng log trực tiếp (SSE) của Kaggle, chỉ đọc, không upload hoặc gửi lại notebook. Có thể phát lại lịch sử kiểm file/cài thư viện trước khi tới log mới; chờ tới cuối log hoặc kéo xuống cuối terminal. Khi tới train sẽ thấy Epoch, GPU_mem, box_loss/cls_loss/dfl_loss và metric validation sau mỗi epoch. Lúc đang kiểm file/cài môi trường sẽ chưa có bảng epoch. SDK tự nối lại và bỏ phần trùng khi mất kết nối tạm; nếu thoát kết nối thì chạy lại cùng lệnh, không chạy publish.

**Ctrl+C hoặc đóng terminal chỉ ngừng xem log, không dừng train trên Kaggle.** Tắt laptop thì mất kết nối xem; cloud vẫn tiếp tục. `logs` không có `--follow` chỉ đọc bản log đã lưu một lần, có thể chưa đầy đủ khi phiên đang chạy. `--version 8` chọn đúng phiên chính; những lần sau dùng số version tương ứng. Có thể đọc trạng thái đúng phiên bằng `status --version 8`.

Mở phiên mới nhất của notebook chính → **Logs**. Thứ tự: GPU được cấp → kiểm hash/copy input → cài Python/thư viện → `--check` → `--preflight` → bảng Epoch/loss/mAP. **RUNNING bao gồm cả chuẩn bị; chỉ thấy Epoch mới biết model đang train.** `COMPLETE` của phiên chẩn đoán không phải train thành công.

Từ terminal có thể đọc một lần, không tự train hoặc upload:

```powershell
.\.venv\Scripts\python.exe -X utf8 -B scripts/kaggle_b0.py status
.\.venv\Scripts\python.exe -X utf8 -B scripts/kaggle_b0.py logs
```

Lệnh logs lưu bản đọc tại `outputs/kaggle/b0_s960_full_kaggle_v1/latest_remote_logs.txt`. Giữ `deployment.json` và các version; không xóa state để vượt chống gửi trùng. API vẫn có thể lưu yêu cầu GPU mà thực tế chạy CPU; đây là lý do cần gate trong notebook.

## Dữ liệu, môi trường và recipe giữ nguyên

Gói **2.988 ảnh**: train **2.681 = 1.122 dương + 1.559 âm**, val **307 = 91 dương + 216 âm**. Giữ 2.568 train/val cũ, thêm 420 frame normal có nhãn tác giả từ 14 clip đã khóa train, dùng đủ 60 thay 30 mốc/clip. Không tăng số sự kiện độc lập, không tạo pseudo-label. **112 test cũ và 120 reserve mới không có media trong gói**, không dùng để chọn tham số.

Config `configs/b0_s960_full_kaggle_v1.json` giữ recipe nguồn: YOLOv8s, 960, batch2, FP32, workers0, SGD lr0.0003, tối đa40/patience10 và seed/augmentation/nbs đã chốt. Khởi tạo best s960 cũ SHA `c1fdd6dcbb09d8d2c3dae4c2c90dfcf4189fac88980c045c3eff095dba019302`, không dùng best hardneg mới. Đây là thí nghiệm đổi lựa chọn frame và nền tảng, không hứa tăng metric.

Trainer chung vẫn là `scripts/train_b0.py`. Input và venv ở `/tmp`; output ở `/kaggle/working`. Bootstrap tạo Python3.12.10 riêng, pin torch2.11.0+cu128, torchvision0.26.0+cu128, Ultralytics8.4.178 và closure trong `requirements-kaggle.lock`. Không nâng Ultralytics, thay batch/AMP hoặc fallback train CPU. Hash manifest đã chốt trong notebook bảo vệ gói sau khi Kaggle giải nén ZIP.

## Lấy kết quả khi train hoàn tất

Chỉ kết luận hoàn tất khi `run_status.json`/receipt báo `training_completed=true`, có experiment hợp lệ và checkpoint khớp. Output cần có `b0_results.zip`, `results_receipt.json`, log và environment. Sau đó:

```powershell
.\.venv\Scripts\python.exe -X utf8 -B scripts/kaggle_b0.py fetch
```

Lệnh kiểm SHA/allowlist/config/checkpoint rồi nhập vào `outputs/training/b0_s960_full_kaggle_v1/`, từ chối ghi đè. Download gốc giữ ở `outputs/kaggle/b0_s960_full_kaggle_v1/download/`. Một phiên chẩn đoán không tạo ZIP train này. Không tự chạy test/reserve hoặc thay checkpoint B0 đang khóa.

```text
outputs/training/b0_s960_full_kaggle_v1/
├── weights/                         # best.pt, last.pt nếu có
├── training_summary/                # results.png, labels.jpg
├── train_batches/
├── validation_during_training/
│   ├── batches/
│   └── curves/
├── metrics_val/
├── cases_val/
├── results.csv
└── experiment.json                  # cùng config/environment/log thực tế
```

## Máy mới và các lần chạy sau

CLI2.2.5 nằm riêng tại `.tmp/kaggle_cli_env`; nếu cần đăng nhập lại:

```powershell
.\.tmp\kaggle_cli_env\Scripts\kaggle.exe auth login
```

Chọn đúng `laqun0211`; credential chỉ nằm trong hồ sơ tài khoản. Không gọi lệnh in token hoặc đưa bí mật vào Git/notebook. Gói hiện có tại `outputs/kaggle/b0_s960_full_kaggle_v1/dataset/`: ZIP, receipt, metadata; notebook chính ở `notebook/train_b0.ipynb`. Không cần tải raw hay cả repo lên Kaggle.

`publish` có thể gửi chạy notebook khi chưa submit; sau submit thì chống gửi trùng. Công cụ khóa một config/bundle/run, không phải lệnh mở tùy ý nhiều vòng tối ưu. Lần nghiên cứu mới cần config/tên run và bằng chứng riêng; Dataset có thể tái sử dụng nếu bytes/nhãn/split không đổi. Không xóa state, resume hardneg đã hoàn tất hoặc ghi đè run cũ.

Nguồn: [Kaggle kernels/API](https://github.com/Kaggle/kaggle-cli/blob/main/docs/kernels.md), [Kaggle CPU/GPU images](https://github.com/Kaggle/docker-python), [metadata](https://github.com/Kaggle/kaggle-cli/blob/main/docs/kernels_metadata.md), [uv Python](https://docs.astral.sh/uv/guides/install-python/). Bằng chứng chạy thực nằm trong staging, tiến độ ở [bảng baseline](../progress/README.md).

## Version 11 — đối chứng SGD

**Nếu log/status báo HTTP 401 hoặc 403:** API hiện không xác thực hoặc không có quyền truy cập notebook PRIVATE; có thể phiên đăng nhập hết hạn hoặc đang dùng sai tài khoản, chưa thể kết luận nguyên nhân cụ thể. Chạy `.\.tmp\kaggle_cli_env\Scripts\kaggle.exe auth login`, chọn `laqun0211`, sau đó chạy lại `status --version 11` và `logs --follow --epochs-only --version 11`. Không gửi token vào chat, không cần publish lại; chỉ lỗi xem log không tự dừng train. Nếu vẫn bị từ chối, mở notebook trong trình duyệt với đúng tài khoản để kiểm quyền. Lần kiểm tra ngày 30/10, cả status và log bị từ chối nên chưa xác minh trạng thái run thực tế.

Đã gửi `b0_s960_sgd_kaggle_v3` lên [notebook PRIVATE](https://www.kaggle.com/code/laqun0211/dacn-b0-s960-full-v1), **Version 11**, dùng Dataset hiện hữu, không upload lại 4 GB. `RUNNING` chỉ là phiên đang khởi tạo/chạy, chưa chứng minh đã train; xem dòng epoch và `B0_RESOURCE`. Tối đa 60 epoch; theo dõi best từ đầu, đếm patience25 sau epoch25, dừng sớm nhất epoch50 nếu không cải thiện. Máy chỉ dùng GPU miễn phí; có thể bị quota ngắt trước khi đủ 60. Không thay model B0 đang khóa.

```powershell
.\.venv\Scripts\python.exe -X utf8 -B scripts/kaggle_b0.py logs --follow --epochs-only --version 11
.\.venv\Scripts\python.exe -X utf8 -B scripts/kaggle_b0.py status --version 11
```

Ctrl+C chỉ dừng xem log. Khi hoàn tất thật (`COMPLETE` và `run_status.json` có `training_completed=true`), lấy kết quả về mà không submit lại:

```powershell
.\.venv\Scripts\python.exe -X utf8 -B scripts/kaggle_b0.py fetch --experiment sgd-v3 --version 11
```

Nếu việc tải bị ngắt và thư mục `download` đã tồn tại, chỉ sau khi lệnh tải cũ đã dừng, tiếp tục bằng `fetch --experiment sgd-v3 --version 11 --resume-download`. Lệnh kiểm SHA và không ghi đè kết quả đã nhập. Không chạy hai lệnh tải đồng thời.

Kết quả dự kiến `outputs/training/b0_s960_sgd_kaggle_v3/`; thất bại hoặc hết quota không được báo là hoàn tất. [Phân tích, protocol và nguồn](b0_pilot_audit.md#nghiên-cứu-và-thí-nghiệm-đối-chứng-sgd-version-11--30102026).

### Kết quả Version 11

Kaggle COMPLETE và run_status báo train hoàn tất ở epoch50 do early stopping; best epoch3. mAP50 val 70,64%, mAP50–95 56,80%, recall cố định .25/.5 70,33% nhưng FP tăng. [Báo cáo so sánh](b0_pilot_audit.md#kết-quả-version-11--sgd-kaggle-30102026). Thông báo 401 phía trên là lịch sử; API đã truy cập trở lại. Không gửi thêm notebook hoặc train lại.
