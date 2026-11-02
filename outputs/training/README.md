# Hướng dẫn đọc kết quả huấn luyện B0

**Run Kaggle Version 10 đã có kết quả:** mở [b0_s960_adamw_kaggle_v2](b0_s960_adamw_kaggle_v2/) để xem `weights/best.pt`, `weights/last.pt`, `results.csv`, `training_summary/results.png`, `metrics_val/` và `cases_val/`. Đã chạy 60 epoch, best khớp CSV epoch 52; `last.pt` đã strip optimizer và không dùng để resume đầy đủ. Đọc [báo cáo so với Version 9](../../docs/b0_pilot_audit.md#kết-quả-version-10--adamw-kaggle-30102026) trước khi kết luận model tốt hơn. Trạng thái “đang chuẩn bị 29/10” bên dưới là lịch sử.

**Kaggle đang chuẩn bị29/10:** chưa có`b0_s960_full_kaggle_v1/` trong mục này, chưa có model/metriccloud. Gói/notebook và trạng thái thiếuđăngnhập ở`outputs/kaggle/b0_s960_full_kaggle_v1/`; xem [hướng dẫn](../../docs/kaggle_training.md). Sau khi runcloud hoàn tất,`kaggle_b0.py fetch` kiểmZIP/hash rồi mới tạo thư mục run mới tại đây; không ghi đè hardneg hoặc thay checkpoint đang khóa. `prepared`, `uploaded`, `submitted` đều không phải `training_completed`.

**Mới nhất29/10 — hardneg đã train xong:** `b0_s960_hardneg_v1/` có15epoch, bestCSV5, patience10. Val307mAP50 **68,48%**, mAP50–95 **55,43%**, F1cố định **62,07%**; [báo cáo so cùng tập](../../docs/b0_pilot_audit.md#kết-quả-s960-hardneg-hoàn-tất--29102026). Mở `b0_s960_hardneg_v1/diagnostics/index.html` xem bảng/curve/FP/FN. Model mới là `b0_s960_hardneg_v1/weights/best.pt`; checkpoint cũ ở `b0_s960_v1/weights/best.pt` giữ nguyên. Cảbest/last mới đã strip optimizer, không mặc định resume được và không chạy lại `--train` vào output đã có.

`outputs/audits/b0_hard_negative_sources_v1/reference_val/` vẫn là model **cũ** đo trên cùng307val, không phải model fine-tune mới. Mốc này dùng so sánh sau train; preflight và snapshot chuẩn bị giữ trạng thái lịch sử. CSVepoch2 từng cómAP50>70% nhưng checkpoint được chọn theo mAP50–95 ởepoch5; không dùng đỉnh một metric thay kết quả best đã đánh giá lại.

`b0_s960_v1/temporal_diagnostics_v1/` là12video/CSV/JSONL so B0 với3-of-5/EMA, không huấn luyện B1 và không tạo trọng số. Ít đoạn ON hơn không tự đồng nghĩa ít frame sai hay eventF1 tốt hơn. [Phép đo và giới hạn](../../docs/b0_pilot_audit.md#đo-b0b1-trên-video-sạch--29102026).

File này giải thích kết quả trên máy phát triển, cập nhật 28/10/2026. Dataset, ảnh, checkpoint và log trong `outputs/` bị Git bỏ qua; sau khi clone, riêng README này vẫn có nhưng các kết quả lớn cần được phục hồi hoặc chạy lại. Tiến độ chung xem [progress/README](../../progress/README.md). Dataset normal mở rộng đã train đủ 60 epoch và đo validation; kết quả mới ở cuối file.

## Ba tên pilot khác nhau thế nào?

| Tên | Ý nghĩa và trạng thái | Có nên dùng checkpoint? |
| --- | --- | --- |
| `b0_basic_pilot_v1` | Pilot đầu với **47 ảnh**, gồm 17 frame impact và 30 frame âm đã rà. Train chỉ có 11 ảnh dương. Mục đích ban đầu là kiểm tra luồng train và đo. | Giữ để đối chiếu lịch sử; chất lượng kém. |
| `b0_accident_scaled_v1` và `b0_accident_scaled_v2` | Các lần thử mở rộng ACCIDENT trước khi sửa nhãn. V1 lỗi lưu sau epoch 1; V2 dừng ở epoch 15 vì dùng frame trước impact chưa rà làm âm toàn ảnh. Release đã thu hồi. | **Không dùng làm kết quả B0 hiện hành.** Giữ log/checkpoint để truy nguyên. |
| `b0_verified_pilot_v1` | Run hiện hành: **1.750 ảnh**, nhãn dương từ impact tác giả, ảnh âm có review hoặc nhãn normal tác giả; đã train 60 epoch và đo trên test đã khóa. | `weights/best.pt` là checkpoint B0 nên dùng cho thí nghiệm tiếp theo, nhưng còn nhiều báo nhầm trên probe âm. |

`scaled` và `verified` là tên các lần thử trong project, không phải tên kiến trúc YOLO khác nhau. Cả hai bắt đầu từ `yolov8n.pt`; khác nhau ở dữ liệu, trạng thái nhãn và lần chạy. Checkpoint B0 học class **vùng `accident`**; `yolov8n.pt` gốc phát hiện các class COCO như xe, không tự kết luận tai nạn.

## Mở thư mục nào trước?

```text
outputs/training/
├── README.md                         Hướng dẫn đang đọc
├── b0_basic_pilot_v1/                Pilot 47 ảnh, lịch sử
├── b0_accident_scaled_v1/            Lần thử bị lỗi lưu, lịch sử
├── b0_accident_scaled_v2/            Lần thử âm chưa rà, đã dừng
└── b0_verified_pilot_v1/             Run B0 hiện hành
    ├── weights/                      best.pt, last.pt
    ├── train_batches/                Ảnh các batch train đã được gom lại
    ├── training_summary/             results.png và labels.jpg
    ├── validation_during_training/   batches/ và curves/ sinh khi train
    ├── metrics_val/                 Biểu đồ và ảnh validation chạy lại
    ├── metrics_test/                Biểu đồ và ảnh test chạy lại
    ├── cases_val/                   Từng ảnh, dự đoán và TP/FP/FN của val
    ├── cases_test/                  Từng ảnh, dự đoán và TP/FP/FN của test
    ├── clean_test/                  So hai checkpoint, thêm probe TAD normal
    ├── results.csv                  Số liệu theo epoch, code cần đường dẫn này
    ├── args.yaml                    Toàn bộ tham số Ultralytics thực chạy
    ├── requested_config.json        Bản sao config project khi bắt đầu
    ├── experiment.json              Kết quả tổng hợp, hash, môi trường
    └── console.log                  Log của lượt train
```

Đây là **ảnh đầu ra**, không phải dữ liệu train sạch. Sáu ảnh `train_batch*.jpg` nằm trong `train_batches/`; ảnh validation gốc nằm trong `validation_during_training/batches/`, curve và confusion matrix gốc trong `validation_during_training/curves/`. `results.png`/`labels.jpg` được gom vào `training_summary/`. Các file cùng tên ở `metrics_val/`, `metrics_test/` là ảnh của những lượt đánh giá lại riêng; chúng có thể khác nội dung và được giữ riêng. `val_batch*_labels.jpg` vẽ nhãn tham chiếu; `val_batch*_pred.jpg` vẽ dự đoán. Trong `metrics_test/`, tên `val_batch...` do Ultralytics đặt nhưng nội dung là split **test**.

- `weights/best.pt`: checkpoint được Ultralytics chọn theo **fitness validation**, ở phiên bản 8.4.178 hiện dùng là mAP50–95. Dùng file này cho phép đo và suy luận B0.
- `weights/last.pt`: checkpoint tại epoch cuối. Sau khi run đã kết thúc Ultralytics có thể đã loại trạng thái optimizer; không mặc định file này còn resume được.
- `cases_val/`, `cases_test/`: `cases.csv` ghi mỗi frame có bao nhiêu TP/FP/FN; `predictions.json` giữ bbox, confidence, IoU và kết quả ghép; `metrics.json` tổng hợp tại ngưỡng cố định. Ảnh JPG tương ứng có **GT xanh, dự đoán đỏ**.
- `metrics_val/`, `metrics_test/`: đầu ra đánh giá lại bằng Ultralytics. Chúng khác `cases_*`: một bên tính metric/đường cong của thư viện, một bên là bảng ghép bbox tại ngưỡng cố định của project.
- `clean_test/report.json`: kết quả test 112 ảnh, so checkpoint cũ trên **cùng ảnh**, và probe 100 frame normal. `cases/`/`reference_cases/` là case test của hai model; `normal_cases/`/`normal_reference_cases/` là case probe âm; `ultralytics/` và `reference_ultralytics/` chứa biểu đồ thư viện. `images.txt` và `dataset.yaml` là danh sách/cấu hình cho lần đánh giá sạch, không phải bản sao dataset.
- `args.yaml` và `requested_config.json`: lần lượt là tham số Ultralytics thực chạy, bao gồm mặc định, và config project yêu cầu. [Config nguồn](../../configs/b0_verified_pilot_v1.json) giải thích recipe và nguồn tham khảo.
- `experiment.json`: config, phiên bản thư viện, thiết bị, hash checkpoint/dataset và metric val/test. Những đường dẫn trong file là dấu vết run đã thực hiện; ảnh batch train được sắp lại sau khi run kết thúc.

## Đọc `results.csv` và `results.png`

Mỗi dòng CSV tương ứng **một epoch**: model đã đi qua tập train một lượt. `results.png` vẽ các cột chính của CSV theo epoch; biểu đồ dùng validation trong lúc train, không phải kết quả test. Trong run này có 60 dòng, một dòng cho mỗi epoch; `time` là thời gian cộng dồn tính bằng giây từ lúc bắt đầu train, không phải thời gian xử lý một ảnh.

| Cột | Ý nghĩa dễ hiểu |
| --- | --- |
| `epoch`, `time` | Số lượt train và thời gian cộng dồn. |
| `train/box_loss`, `val/box_loss` | Sai số liên quan đến vị trí/kích thước bbox trên train và validation; thường muốn giảm. |
| `train/cls_loss`, `val/cls_loss` | Sai số học class `accident`; thường muốn giảm. |
| `train/dfl_loss`, `val/dfl_loss` | **Distribution Focal Loss**: thành phần hỗ trợ hồi quy tọa độ biên bbox; thường muốn giảm. |
| `metrics/precision(B)` | Precision bbox trên validation tại điểm vận hành thư viện chọn để tóm tắt đường P/R: trong các bbox model dự đoán, bao nhiêu bbox ghép đúng GT. |
| `metrics/recall(B)` | Recall bbox trên validation ở điểm đó: trong các bbox GT, bao nhiêu bbox được phát hiện và ghép đúng. |
| `metrics/mAP50(B)` | mAP bbox khi IoU ≥ 0,50; càng cao càng tốt. Vì chỉ có một class, mAP là AP của class đó. |
| `metrics/mAP50-95(B)` | Trung bình AP qua các ngưỡng IoU từ 0,50 đến 0,95, bước 0,05; đòi bbox chính xác hơn nên thường thấp hơn mAP50. |
| `lr/pg0`, `lr/pg1`, `lr/pg2` | Learning rate của ba nhóm tham số trong optimizer; tăng ở giai đoạn warmup rồi giảm theo lịch train. Không phải độ chính xác. |

Chữ `(B)` là **box**, tức metric bbox. Không cần mọi loss giảm đều ở từng epoch; đọc xu hướng nhiều epoch và đối chiếu validation. Loss train giảm nhưng validation xấu đi kéo dài có thể gợi ý overfitting, cần xem thêm dữ liệu và case lỗi. Dòng `mAP50-95` validation cao nhất trong CSV là **epoch 45: 0,46559**. Đánh giá lại `best.pt` cho validation mAP50–95 **0,46033**; đó là hai phép ghi/đánh giá khác thời điểm, không gộp thành cùng một số.

## Các số in trong terminal

Dòng train thường có dạng `Epoch | GPU_mem | box_loss | cls_loss | dfl_loss | Instances | Size`:

- `45/60`: đang ở epoch 45 trong tối đa 60; `GPU_mem` là bộ nhớ GPU mà thư viện ghi tại thời điểm đó, không phải dung lượng file model.
- Ba cột `box_loss`, `cls_loss`, `dfl_loss` là loss train trung bình đang cập nhật trong epoch. `Instances` là số bbox trong batch hiện tại, không phải tổng số ảnh của dataset; `Size` là kích thước đầu vào model, ở đây 640.
- `193/193` là số batch đã xử lý trong epoch. `it/s` là số **iteration/batch mỗi giây**, không trực tiếp là FPS video; thời gian sau dấu `<` là ước tính còn lại.
- Sau epoch, bảng `Class | Images | Instances | Box(P R mAP50 mAP50-95)` là đánh giá **validation**. `all` gộp class đang đánh giá; `Images` là số ảnh và `Instances` là số bbox GT. Với validation ở đây là 97 ảnh và 91 bbox, vì 6 ảnh âm không có bbox.
- Dòng `Speed: preprocess / inference / loss / postprocess ... ms per image` tách các bước của phép đánh giá ảnh. Đây không phải FPS end-to-end của hệ thống video: chưa tính đầy đủ đọc video, tracking, cảnh báo và các thành phần khác.

Log gốc của lượt train đã được giữ ở `b0_verified_pilot_v1/console.log`; kết quả so sánh bổ sung có log riêng trong `clean_test/console.log`.

## Các curve và ma trận

- `BoxPR_curve.png`: trục ngang **recall**, trục dọc **precision** khi thay đổi confidence. AP là diện tích dưới đường PR theo cách tính của thư viện. Đường càng gần phía trên bên phải càng tốt, trong phạm vi dữ liệu đánh giá.
- `BoxP_curve.png` và `BoxR_curve.png`: precision hoặc recall thay đổi theo **confidence threshold**. Tăng ngưỡng thường giảm bbox dự đoán; precision có thể tăng và recall có thể giảm, nhưng không bắt buộc mọi đoạn đều đơn điệu.
- `BoxF1_curve.png`: **F1 = 2 × precision × recall / (precision + recall)** theo confidence. Chọn ngưỡng triển khai phải dùng validation và khóa trước test; không lấy đỉnh trên test để chỉnh model.
- `confusion_matrix.png`: số lượng ghép/nhầm giữa dự đoán và nhãn theo quy tắc confusion matrix của Ultralytics. `confusion_matrix_normalized.png` chuẩn hóa từng cột để nhìn tỉ lệ; xem nhãn các trục trên ảnh. Hàng/cột `background` biểu diễn dự đoán thừa hoặc GT bỏ sót, không phải tập hợp mọi pixel nền.
- `validation_during_training/curves/` chứa đồ thị do lần train/validation sinh; `metrics_val/`, `metrics_test/` và `clean_test/ultralytics/` thuộc các lượt đánh giá được chỉ rõ. Đọc tên thư mục để tránh lấy nhầm val thành test.

## Accuracy ở đâu?

**Accuracy** trong phân loại thường là `(TP + TN) / (TP + TN + FP + FN)`. Với object detection, một ảnh có thể có nhiều bbox, còn số vùng nền đúng (**TN**) không có một cách đếm tự nhiên duy nhất. Vì vậy Ultralytics thường báo **precision, recall, mAP và IoU** cho detector thay vì một accuracy chung. Vẫn có thể định nghĩa accuracy cấp ảnh nếu khóa rõ quy tắc “ảnh có ít nhất một dự đoán” và có nhãn đầy đủ, nhưng đó là bài toán khác với bbox và không nên lấy số đó thay cho chất lượng định vị. Không có cột `accuracy` trong `results.csv` của run này.

**IoU** là diện tích giao chia cho diện tích hợp của bbox dự đoán và bbox GT; IoU 0,5 nghĩa là chúng chồng lấp đủ theo ngưỡng 0,5, không có nghĩa model chắc chắn 50%. **Confidence** là điểm model gán cho bbox; nó không tự là xác suất tai nạn đã được hiệu chuẩn.

## Đọc kết quả run hiện tại

| Phép đo | Pilot 47 ảnh cũ | Pilot 1.750 ảnh mới |
| --- | ---: | ---: |
| mAP50 bbox trên **cùng 112 ảnh test** | 0,0119 | **0,6968** |
| mAP50–95 bbox trên cùng 112 ảnh | 0,0066 | **0,5223** |
| Bbox TP / FP / FN tại confidence 0,25 và IoU 0,5 | 14 / 598 / 93 | **67 / 46 / 40** |
| Frame normal TAD bị dự đoán nhầm trên 100 frame/5 clip | 76 | **41** |

Trên test chính, run mới có precision **0,5929**, recall **0,6262**, F1 **0,6091** ở confidence 0,25/IoU 0,5. Các số này khác P/R Ultralytics **0,8473/0,5607** vì thư viện tóm tắt đường cong tại điểm F1 được chọn, còn bảng TP/FP/FN của project dùng ngưỡng confidence 0,25 cố định. Chúng trả lời các câu hỏi khác nhau và không nên ghép chéo để tính F1.

Test chính có 107 ảnh dương và chỉ 5 ảnh âm; model mới không dự đoán trên cả 5 ảnh âm đó. Trên probe khác gồm 100 frame từ **5 clip TAD normal**, model dự đoán ở **41 frame**, tổng **46 bbox**, thuộc **4/5 clip**. Đây là nhãn normal cấp clip do tác giả phát hành; 100 frame không phải 100 camera hay 100 sự kiện độc lập, và tỉ lệ 41% không là số cảnh báo sai/giờ. Năm clip được chọn theo kích thước nhỏ nhất, không phải mẫu ngẫu nhiên. [Bảng và chi tiết](b0_verified_pilot_v1/clean_test/report.json).

Checkpoint mới tốt hơn rõ trên phép so ảnh đã làm, nhưng chưa đủ tin cậy để báo động thực tế: còn bỏ sót 40/107 bbox test ở ngưỡng đã khóa và còn báo nhầm trên cảnh bình thường. Hai lần train đổi đồng thời dữ liệu và optimizer/batch, nên chưa thể kết luận yếu tố nào gây ra cải thiện.

## Dữ liệu và căn cứ train

| Tập | Dương | Âm | Nguồn âm |
| --- | ---: | ---: | --- |
| Train | 1.122 | 419 | 19 frame ACCIDENT đã rà, 300 frame từ ba chuỗi DETRAC bạn đã xác nhận, 100 frame từ hai clip TAD normal của tác giả |
| Validation | 91 | 6 | Frame ACCIDENT đã rà |
| Test | 107 | 5 | Frame ACCIDENT đã rà |
| **Tổng** | **1.320** | **430** | **1.750 ảnh** |

Ảnh dương là đúng frame impact và bbox tác giả ACCIDENT sau kiểm kỹ thuật. Frame âm chưa rà không được dùng. 400 frame DETRAC/TAD train chỉ từ năm clip thuộc ba nhóm nguồn bảo thủ; nhiều frame liền kề không phải nhiều tình huống độc lập. Chia theo nhóm nguồn và đã rà một số trường hợp gần trùng; camera và mọi bản gần trùng chưa được chứng minh độc lập. 1.750 ảnh đủ cho pilot này, không có ngưỡng 1.000 nào tự bảo đảm model học tốt.

Recipe được đối chiếu [ACCIDENT](https://arxiv.org/html/2604.09819v1), [TP-YOLOv8](https://zhangtianze.com/mypublications/Thesis/TPYOLOv8.pdf) và [Ultralytics](https://docs.ultralytics.com/guides/yolo-performance-metrics/). TP-YOLOv8 dùng SGD, learning rate 0,01, momentum 0,937, ảnh 640 và batch 16, train từ đầu trên A40; project áp dụng SGD/lr/momentum/640 nhưng dùng `yolov8n.pt` pretrained, batch 8, tối đa 60 epoch trên RTX 3050 Ti và nhãn khác. ACCIDENT dùng định vị điểm và metric riêng, còn B0 chuyển bbox impact công khai thành bài toán detector ảnh. Đây là **áp dụng có điều chỉnh**, chưa phải tái lập kết quả các paper. [Literature review chi tiết](../../reference/LITERATURE_REVIEW.md).

## Lần thử tiếp theo: giảm learning rate, chỉ so validation

Đã chuẩn bị [config thử nghiệm](../../configs/b0_verified_lr001_val_v1.json): giữ nguyên data/split, seed, model pretrained, SGD, batch 8, 640 px, 60 epoch tối đa và patience 18; chỉ đổi `lr0` từ **0,01 xuống 0,001**. Đây là một giả thuyết thăm dò về độ ổn định fine-tune, dựa trên [hướng dẫn fine-tuning Ultralytics](https://docs.ultralytics.com/guides/finetuning-guide/) (tài liệu hiện nói về YOLO mới hơn) và quan sát validation dao động sau warmup ở run trước. Chưa có bằng chứng giảm LR sẽ tăng metric hay giảm false positives; thay đổi LR không thay thế việc thêm âm đa dạng.

Paper gốc dùng SGD `0,01`; hướng dẫn Ultralytics nêu learning rate thấp hơn trong một số tình huống fine-tune và minh họa cả AdamW. Việc kết hợp **SGD + 0,001** ở đây là ablation của project, chưa phải công thức SGD được nguồn chứng minh sẽ tốt hơn. `warmup_bias_lr` vẫn là mặc định của Ultralytics; chỉ trường `lr0` được đổi trong config.

**Lệnh chạy trên Windows PowerShell trong thư mục project:**

```powershell
.\.venv\Scripts\python.exe -X utf8 -B scripts/train_b0.py --config configs/b0_verified_lr001_val_v1.json --check
.\.venv\Scripts\python.exe -X utf8 -B scripts/train_b0.py --config configs/b0_verified_lr001_val_v1.json --train
```

`--check` kiểm file/nhãn/hash và split, chưa train. `--train` tạo run mới `outputs/training/b0_verified_lr001_val_v1/`, không ghi đè run cũ. File code train là [scripts/train_b0.py](../../scripts/train_b0.py); tham số cụ thể và tên output nằm trong config JSON, đường dẫn/nhãn nằm trong dataset YAML/provenance, còn phiên bản thư viện nằm trong môi trường. Sửa riêng code train không đủ để thay đổi mọi phần đó; thay tham số trong một config mới và chỉ sửa code khi cần thay chức năng.

Run này bắt đầu lại từ `yolov8n.pt` gốc để so công bằng ảnh hưởng LR, không tiếp tục trọng số `best.pt`. `--resume` chỉ nối **cùng run đang dở** từ `last.pt` còn optimizer; run hiện tại đã kết thúc và `last.pt` đã strip optimizer, không dùng nó để resume. Script kiểm config/split/hash và không ghi đè run đã có. `evaluation_splits=["val"]` làm run thử chỉ đánh giá validation; **test 112 ảnh và probe 100 frame đã xem không được dùng để chọn tham số**. Validation đã dùng nhiều lần và chỉ có 6 ảnh âm, nên cần một test mới độc lập trước khi kết luận tổng quát. Chưa chạy thử nghiệm này; sau khi bạn chạy xong, gửi mình `experiment.json`/nói kết thúc để mình phân tích.

### Khôi phục run LR 0,001 sau lỗi bộ nhớ (27/10/2026)

Run `b0_verified_lr001_val_v1` đã hoàn thành epoch 1/60, rồi dừng khi OpenCV trong DataLoader worker không cấp phát được 2.332.800 byte để giải mã ảnh ở epoch 2. `weights/last.pt` hiện có optimizer và epoch index 0; `results.csv` có đúng một dòng epoch. Đây là lỗi tài nguyên lúc đọc ảnh, chưa phải kết quả đánh giá model và chưa xác định chính xác nguồn chiếm RAM. Không chạy lại `--train` trên cùng output.

```powershell
.\.venv\Scripts\python.exe -X utf8 -B scripts/train_b0.py --config configs/b0_verified_lr001_val_v1.json --resume --resume-workers 0
```

`--resume-workers 0` đọc ảnh trong tiến trình train thay vì hai worker riêng. Đây là thay đổi cách nạp dữ liệu để giảm áp lực RAM, giữ config thí nghiệm và trạng thái optimizer từ checkpoint. Tốc độ có thể chậm hơn; epoch 2 chạy lại từ đầu vì checkpoint lưu sau epoch 1. Nếu vẫn lỗi, kiểm tra RAM/page file và đóng ứng dụng nặng; không tự giảm `batch` trong cùng run vì như vậy đổi điều kiện so sánh. Sau khi chạy xong mới so validation, không dùng lại test/probe đã xem để chọn learning rate.

### Kiểm tra giả thuyết cần đủ 60 epoch

Run LR 0,001 `b0_verified_lr001_val_v1` **đã dừng sớm sau epoch 48**, không phải 47: kiểm `results.csv` có 48 hàng; mAP50–95 tốt nhất trong CSV ở epoch 30. `weights/last.pt` có `epoch=-1` và không còn optimizer sau khi Ultralytics hoàn tất, vì vậy `--resume` không thể tiếp tục đúng lịch học ở epoch 49. Loss train cuối dao động (epoch 46–48), nên chưa thể suy ra chắc chắn epoch 50–60 sẽ tốt hơn.

Để kiểm tra giả thuyết, [config full60](../../configs/b0_verified_lr001_full60_v1.json) tạo **run mới từ `yolov8n.pt` gốc**, cùng release, LR 0,001, SGD, batch 8 và seed. `patience=0` tắt early stopping theo mã Ultralytics 8.4.178; `workers=0` giảm áp lực RAM khi đọc ảnh (cách nạp có thể ảnh hưởng thứ tự/ngẫu nhiên, không cam kết kết quả giống hệt 48 epoch đầu). Output riêng `outputs/training/b0_verified_lr001_full60_v1/`, chỉ đo val; không đánh giá test/probe đã dùng. `best.pt` vẫn chọn epoch tốt nhất trên val, còn `last.pt` là epoch 60 nếu run hoàn tất.

```powershell
.\.venv\Scripts\python.exe -X utf8 -B scripts/train_b0.py --config configs/b0_verified_lr001_full60_v1.json --check
.\.venv\Scripts\python.exe -X utf8 -B scripts/train_b0.py --config configs/b0_verified_lr001_full60_v1.json --train
```

Đây là **chạy lại 60 epoch**, không phải nối chính xác từ epoch 48. Kiểm tra `train/box_loss`, `train/cls_loss`, `train/dfl_loss` theo epoch 49–60 và so mAP50–95/precision/recall trên validation. Loss train giảm mà metric val không tăng có thể là học quá khớp. Nếu gặp lỗi giữa chừng và `last.pt` còn optimizer, dùng `--resume --resume-workers 0` với cùng config. Nguồn hành vi `patience=0`/resume: [Ultralytics EarlyStopping](https://docs.ultralytics.com/reference/utils/torch_utils/#ultralytics.utils.torch_utils.EarlyStopping), [hướng dẫn train](https://docs.ultralytics.com/modes/train/).

### Kết quả run LR 0,001 đủ 60 epoch — 27/10/2026

[Run full60](b0_verified_lr001_full60_v1/experiment.json) đã hoàn tất **60/60 epoch** từ `yolov8n.pt`, không phải nối chính xác run cũ dừng tại 48. Các đoạn trên ghi trạng thái trước khi train; số liệu hiện hành: train box loss epoch 50→60 **0,8480→0,76241**, cls loss **0,7412→0,58679**. Val mAP50–95 CSV cao nhất **0,49563 ở epoch 47**, tốt nhất trong epoch 50–60 **0,49229 ở epoch 52** và tại epoch 60 **0,48419**. `best.pt` được chọn từ epoch 47, `last.pt` từ epoch 60. Đánh giá lại `best.pt` trên val có mAP50–95 **0,49412**; run LR 0,001 dừng sớm **0,50643**, run LR 0,01 ban đầu **0,46033**. Tại confidence 0,25/IoU 0,5, full60 **56 TP/65 FP/35 FN**, run 48 epoch **60/49/31**. Loss train giảm không đồng nghĩa validation tăng. Val chỉ có sáu ảnh âm và đã dùng nhiều lần; test/probe cũ không chạy lại để chọn model. [Snapshot đo và hash](../../docs/evidence/2026-10-27-b0-full60-validation.json).

## Xem B0 chạy trên video sau train

Mở `b0_verified_pilot_v1/diagnostics/index.html` bằng trình duyệt. Trang gom ảnh FP/FN, chín video có bbox accident và link CSV/JSONL/report; không cần đi tìm từng file. `scripts/analyze_b0.py --check` kiểm lại nguồn/hash, `--run` đã thực hiện xong và sẽ từ chối ghi đè kết quả này. [Cách chạy và kết quả đầy đủ](../../docs/b0_pilot_audit.md#chẩn-đoán-lỗi-ảnh-và-video-b0--27102026).

Checkpoint mốc trên chín chuỗi sạch, 3.857 frame: ba DETRAC từng dùng train không có bbox; năm normal TAD có bbox ở 812/1.599 frame; CADP có bbox trong 35/35 frame Colliding đã xác nhận nhưng chưa phải recall vùng/sự kiện. Video CADP chỉ trình chiếu 20 FPS. Kết quả dự đoán mới này khác preview annotation tác giả trong `outputs/annotation_preview/`.

## Dataset normal mở rộng đã sẵn sàng — 28/10/2026

Mở `../audits/b0_normal_expansion_v1/index.html` từ thư mục training hoặc xem [hướng dẫn đầy đủ](../../docs/b0_pilot_audit.md#b0-normal-mở-rộng--28102026). Dataset mới 2.170 ảnh (train 1.841, val 217, test cũ 112) đã xuất/kiểm; có thêm reserve âm 120 frame ngoài dataset, chưa suy luận. Ba checkpoint cũ đã được đo trên cùng 217 ảnh val để làm mốc; **model mới đã train đủ 60 epoch và đánh giá val**.

```powershell
.\.venv\Scripts\python.exe -X utf8 -B scripts/train_b0.py --config configs/b0_normal_expanded_v1.json --check
.\.venv\Scripts\python.exe -X utf8 -B scripts/train_b0.py --config configs/b0_normal_expanded_v1.json --train
```

Giữ recipe LR 0,001/SGD/batch8/640/60epoch/patience0/workers0, bắt đầu từ pretrained gốc. Kết quả sẽ nằm trong `outputs/training/b0_normal_expanded_v1/`, chỉ đo val. Không so trực tiếp với metric val cũ 97 ảnh; dùng `outputs/audits/b0_normal_expansion_v1/reference_val/report.json` trên cùng 217 ảnh. Không dùng test đã xem hoặc reserve mới để chọn model.

## Kết quả run normal-expanded hoàn tất — 28/10/2026

Run `b0_normal_expanded_v1` hoàn tất 60 epoch, khoảng 92,29 phút gồm đánh giá. Dataset 2.170 ảnh: train 1.841, val 217, test cũ 112. Lượt này chỉ đánh giá val; test cũ và reserve âm 120 frame không suy luận.

Các checkpoint dưới đây được đo trên **cùng 217 ảnh val (91 dương, 126 âm)**:

| Run | mAP50 | mAP50–95 | TP / FP / FN | Precision / Recall / F1 cố định | Ảnh âm có bbox / 126 |
| --- | --- | --- | --- | --- | --- |
| verified_pilot | 0,56721 | 0,43480 | 52 / 83 / 39 | 0,3852 / 0,5714 / 0,4602 | 36 |
| lr001_val | 0,61759 | 0,47000 | 60 / 88 / 31 | 0,4054 / 0,6593 / 0,5021 | 38 |
| lr001_full60 | 0,60367 | 0,46194 | 56 / 95 / 35 | 0,3709 / 0,6154 / 0,4628 | 29 |
| normal_expanded | 0,64685 | 0,49031 | 54 / 35 / 37 | 0,6067 / 0,5934 / 0,6000 | 6 |

TP/FP/FN dùng confidence 0,25, matching IoU 0,5. Precision/recall do Ultralytics in ra ở điểm vận hành của nó khác cột ngưỡng cố định này. Đây là bbox/frame metric, không phải event metric hoặc false alerts/hour.

CSV trong train đạt mAP50–95 cao nhất 0,50458 tại epoch 40; epoch cuối là 0,48843. Lần đánh giá riêng `best.pt` sau train cho 0,49031; giữ nguyên cả hai phép đo và không thay số này bằng số CSV. `close_mosaic=10` trong args: mosaic đóng từ epoch 51. Best CSV trong epoch 51–60 là 0,49215. Chênh lệch giữa CSV và lần đánh giá riêng chưa được cô lập nguyên nhân.

Đường dẫn kết quả: `outputs/training/b0_normal_expanded_v1/experiment.json`, `weights/best.pt`, `weights/last.pt`, `results.csv`, `metrics_val/`, `cases_val/`. Snapshot nhỏ: `docs/evidence/2026-10-28-b0-normal-training.json`. Hash config/checkpoint/provenance và tổng 217 case đã kiểm khớp. Giới hạn: validation dương đã được dùng trước, nhóm camera chưa chứng minh độc lập; chưa đánh giá sự kiện và chưa hoàn tất toàn B0. Kết luận/hướng đi tiếp theo chỉ trình bày trong chat theo yêu cầu.

## Hồ sơ chuẩn bị s960 — lịch sử trước run đã hoàn tất

[Giải thích nguồn, dữ liệu, công thức và lệnh chạy](../../docs/b0_pilot_audit.md#chuẩn-bị-b0-s960--28102026). Config `configs/b0_s960_v1.json`: YOLOv8s pretrained,960,batch2,SGD0,001,100epoch,workers0,mosaic0,5/scale0,3. Mục tiêu kiểm **mAP50 val >70%**, không có bảo đảm đạt. Dataset/split2.170ảnh giữ nguyên, không tải thêm data hoặc suy luận test/reserve.

```powershell
.\.venv\Scripts\python.exe -X utf8 -B scripts/train_b0.py --config configs/b0_s960_v1.json --train
```

**Đoạn hướng dẫn chuẩn bị lịch sử:** người dùng sau đó đã chạy xong s960; không gọi lại lệnh `--train` vào output này. Kết quả mới ở cuối file. Các lệnh trên chỉ dùng tái lập với config/output mới. Trọng số chuẩn bị `yolov8s.pt` là COCO, chưa là model accident mới. Sau train mới có `b0_s960_v1/weights/best.pt`. Các bằng chứng chuẩn bị hiện gom trong [diagnostics của run nguồn](b0_normal_expanded_v1/diagnostics/), không tạo thêm hệ thống kết quả song song. Forward preflight đã đạt, chưa kiểm bộ nhớ backward hoặc đo thời lượng train.

### Bật early stopping khi s960 đang chạy — cập nhật sau khi người dùng bắt đầu train

Config gốc có `patience=0`, tức tắt early stopping. Không sửa config/hash của run đang chạy: tiến trình không đọc lại JSON, và resume cần giữ snapshot khớp. Theo yêu cầu mới của người dùng, script hỗ trợ bật **patience15** khi resume, giữ giới hạn tối đa100 epoch và lịch LR ban đầu.

1. Đợi epoch hiện tại hoàn tất và bắt đầu epoch kế tiếp, rồi nhấn **Ctrl+C một lần** trong terminal train. Tránh ngắt đúng lúc ghi checkpoint. Phần epoch chưa lưu sẽ chạy lại từ checkpoint gần nhất.
2. Khi terminal đã trả prompt, chạy:

```powershell
.\.venv\Scripts\python.exe -X utf8 -B scripts/train_b0.py --config configs/b0_s960_v1.json --resume --resume-workers 0 --resume-patience 15
```

Không dùng `--train`, không xóa run, không thay `epochs` thành số đã chạy. `last.pt` cần còn optimizer và run chưa hoàn tất. Script chặn nếu tiến trình cũ còn chạy; resume giữ weights/optimizer/EMA/epoch/lịch LR, chỉ thay điều kiện dừng. Thông báo `Resume early stopping: patience=15; retained best epoch=...` xác nhận override đã áp dụng. Nếu không có dòng này, chưa coi là bật thành công.

Patience15 là dừng sau15 epoch liên tiếp không có fitness validation tốt hơn, tính từ mốc best được khôi phục; không phải dừng ở epoch15 hay luôn chạy thêm15. Fitness của bản cài là mAP50–95. `100` vẫn là trần, không còn bắt buộc chạy tới đó. Sau dừng sớm, pipeline tiếp tục đánh giá best.pt.

Ultralytics8.4.178 khôi phục cả `stopper` từ checkpoint. Callback `on_train_start` của wrapper đặt lại patience **sau bước khôi phục**, giữ best_epoch/best_fitness, tránh patience vô hạn từ checkpoint cũ ghi đè. Run sẽ giữ `args_before_resume_patience.yaml` và `resume_events.json`; `experiment.json` sau hoàn tất ghi `effective_patience`. Công cụ đã được kiểm bằng fixture; AI không tự ngắt hoặc khởi động lại run của người dùng.

## Kết quả B0 s960 hoàn tất — 28/10/2026

**Đã train/đánh giá xong, không còn tiến trình train.** Run s960 dừng tại45/100epoch, best CSV tại30; `effective_patience=15`, khoảng không cải thiện15epoch khớp điều kiện dừng sớm. Người dùng resume sau10epoch; `resume_events.json` giữ lịch sử, config gốc/requested_config vẫn khớp và giữ patience0. `best.pt`/`last.pt` đọc được trên CPU, một class `accident`, mỗi file22.583.729byte; optimizer đã strip nên không resume tiếp như checkpoint dở.

So sánh **cùng217ảnh val,91bbox dương và126ảnh âm**, dataset/provenance/GT từng case khớp:

| Chỉ số | n640 normal-expanded | s960 mới | Thay đổi |
| --- | --- | --- | --- |
| mAP50 sau train | 64,68% | 68,60% | +3,91 điểm phần trăm |
| mAP50–95 sau train | 49,03% | 53,94% | +4,91 điểm phần trăm |
| Precision cố định | 60,67% | 59,81% | −0,86 điểm phần trăm |
| Recall cố định | 59,34% | 70,33% | +10,99 điểm phần trăm |
| F1 cố định | 60,00% | 64,65% | +4,65 điểm phần trăm |
| TP / FP / FN | 54 / 35 / 37 | 64 / 43 / 27 | +10 / +8 / −10 |
| Ảnh âm có dự đoán /126 | 6 | 7 | +1 ảnh |

Ngưỡng cố định: confidence0,25, matchingIoU0,5; dùng để so P/R/F1 trong bảng. Số P/R Ultralytics của s960 là84,66%/59,34% tại điểm vận hành riêng của evaluator, không thay cho hàng cố định.7ảnh âm có tổng10bbox sai, phân biệt số ảnh với số hộp. Mục tiêu **mAP50 >70% chưa đạt**; recall70,33% không thay cho mAP50.

CSV best tại30 có mAP50 **68,546%**, mAP50–95 **53,868%**; đánh giá riêng best.pt sau train cho68,598%/53,940%. Giữ cả hai phép đo, không trộn với epoch cuối45: mAP50 **60,182%**, mAP50–95 **46,741%**. Train box loss từ0,77409 ở30 xuống0,66303 ở45 trong khi mAP cuối thấp hơn best. Mosaic vẫn chưa đóng ở45 vì `close_mosaic=10` với trần100 chỉ đóng từ91.

Thời gian `experiment.json` khoảng141,09phút **chỉ tính lượt resume gồm đánh giá**, không phải cả run. Cộng42,02phút ghi trong CSV trước resume được khoảng **183,11phút (~3giờ03phút)**, chưa gồm phần khởi tạo/công việc không log và thời gian tạm dừng; cột time của CSV reset sau resume.

Phân tích217prediction đã lưu:13case giảmFN,3case cóFN mới; tổng FN37→27. FP hình học gồm30bbox rời vùng annotation,1bbox IoU0,1–<0,5,2trùng/xung đột và10bbox trên ảnh âm. Đây là phân loại hình học, không tự gán nhãn âm cho mọi vùng ngoài GT. Dùng cùng mốc resize640 để so kích thước GT: FN cạnh ngắn<32px giảm21→16; đây là chuẩn hóa kích thước hộp, không phải suy luận lại s960 ở640. Đã xem contact sheet FP/FN và đồ thị loss/mAP, giữ nguyên nhãn/case khó.

Đầu ra nằm chung trong `outputs/training/b0_s960_v1/`: `weights/best.pt`, `weights/last.pt`, `experiment.json`, `resume_events.json`, `results.csv`, `training_summary/results.png`, `metrics_val/`, `cases_val/`, `diagnostics/image_errors/`. Snapshot nhỏ trên Git: `docs/evidence/2026-10-28-b0-s960-validation.json`.

Kiểm đã đạt: SHA config/checkpoint/pretrained, dataset/provenance chung model trước;45epoch liên tục;217case/91GT/126âm và tổng TP/FP/FN khớp; hai checkpoint đọc được, class đúng; holdout hash giữ nguyên. Không train thêm hoặc chạy suy luận mới lên test cũ/reserve120frame. Nhiều yếu tố thay cùng lúc (model/resolution/batch/augmentation/horizon/stop policy), không quy cải thiện riêng cho một yếu tố. Validation đã dùng nhiều lần, chưa là test độc lập hoặc metric sự kiện; toàn B0 chưa hoàn thành. Kết luận và hướng đi tiếp theo trao đổi trong chat.

## Chọn ngưỡng và đánh giá holdout âm — 29/10/2026

**Đã hoàn thành bước chọn điểm vận hành và một lần đo holdout âm, không train thêm.** [Trang tổng hợp tại máy có output](b0_s960_v1/operating_point_v1/index.html), [khóa sử dụng](../../configs/b0_s960_v1_operating_point_v1.json), [snapshot nhỏ](../../docs/evidence/2026-10-29-b0-operating-point.json). Tất cả kết quả gom trong run s960 hiện có, không copy dataset.

Đã đọc workbook09/11/15 và [căn cứ phương pháp](../../reference/LITERATURE_REVIEW.md#10-chọn-điểm-vận-hành-và-đo-holdout-âm--29102026). Quy tắc ghi trước khi quét: **recall val≥70%, tối đa F1**, tie ít ảnh âm có hộp, precision cao, ngưỡng cao. Cache hai checkpoint trên đúng217ảnh val tại confidence0,01; quét91ngưỡng0,05–0,95, giữ IoU ghép0,5/NMS0,7/max_det100. Kết quả ở0,25 khớp chính xác các tổng đã báo cáo, train/test/split/nhãn không đổi.

| Model/điểm vận hành trên validation | Confidence | TP / FP / FN | Precision | Recall | F1 | Ảnh âm có hộp /126 |
| --- | --- | --- | --- | --- | --- | --- |
| s960 trước chọn ngưỡng | 0,25 | 64 / 43 / 27 | 59,81% | 70,33% | 64,65% | 7 |
| **s960 đã khóa** | **0,27** | **64 / 39 / 27** | **62,14%** | **70,33%** | **65,98%** | **7** |
| n640, cùng sàn recall70% | 0,09 | 65 / 85 / 26 | 43,33% | 71,43% | 53,94% | 19 |

Recall thực tế hai model khác1bbox, không gọi là khớp recall tuyệt đối. Ngưỡng s960 tối đaF1 nếu bỏ ràng buộc là0,59: F1 **70,51%**, nhưng recall chỉ **60,44%**, nên không chọn. Điểm0,27 chỉ đổi quyết định sử dụng; mAP50 **68,60%** và mAP50–95 **53,94%** từ đánh giá sau train giữ nguyên, mục tiêu mAP50>70% vẫn chưa đạt.

### Một lần đo holdout âm bằng khóa0,27

Model/confidence và hash selection đã ghi trước inference. Chỉ chạy s960 ở0,27 trên120ảnh lấy thưa từ4clip normal tác giả, không chạy model đối chứng hoặc quét ngưỡng trên holdout:

| Chuỗi gốc | Ảnh đã lấy | Ảnh có dự đoán | Tổng bbox dự đoán |
| --- | --- | --- | --- |
| 20220518_acci-bg28 | 30 | 24 | 24 |
| 20220518_acci-bg56 | 30 | 1 | 1 |
| 20220620_acci-bg37 | 30 | 1 | 1 |
| 20230818_acci-bg_129 | 30 | 8 | 9 |
| **Tổng** | **120** | **34 (28,33%)** | **35** |

Validation âm tại0,27 là7/126ảnh có hộp (5,56%); holdout là34/120 (28,33%). Nhãn là **normal cấp clip do tác giả**, không biến thành người dùng xác nhận. Chỉ có âm nên recall/F1/mAP tai nạn không xác định; không có độ đo cảnh báo/giờ, kết quả toàn video hoặc camera-held-out được chứng minh. Các frame cùng clip tương quan; chỉ bốn nhóm.

Đã xem ảnh đối chiếu: một số hộp ở nhóm bg28 nằm trên vùng sáng cố định sát rìa trái ảnh; nhóm bg_129 có hộp ở cảnh đêm/đèn xe. Đây là quan sát trên ví dụ, không sửa nhãn hoặc suy nguyên nhân chung đã được kiểm chứng. Không điều chỉnh confidence/ROI/training dựa trên holdout này trong lượt hiện tại.

Manifest `data/registries/b0_normal_expanded_v1_holdout.json` hiện **model_predictions_seen=true**, evaluation_status=complete, dẫn tới khóa/report và hash. Backup nguyên bản ở `operating_point_v1/holdout_manifest_before_evaluation.json`; clips/samples/hash ảnh/nhãn/user_review giữ nguyên. Snapshot trước29/10 nói “chưa mở” là trạng thái lịch sử, không còn là trạng thái hiện tại. Không tái sử dụng tập này như test mù cho lần tune sau.

Mở `index.html`, `validation_curves.png`, `s960_thresholds.csv`, `n640_thresholds.csv`, `holdout_false_positives.jpg`, `holdout_cases.csv` và `holdout_report.json` trong thư mục kết quả.61unit test đạt; --help/import/cú pháp, hash, tổng case và liên kết HTML đạt; lệnh đo holdout lần hai bị chặn trước nạp model. Không tải thêm dataset, đổi model hoặc train. B0 sự kiện và B1 chưa hoàn thành; kết luận/hướng tiếp theo trao đổi trong chat.
# Version 11 — SGD Kaggle

Run `b0_s960_sgd_kaggle_v3` hoàn tất tại epoch 50, best theo fitness ở epoch 3. Validation best mAP50 70,64%, mAP50–95 56,80%; đánh đổi recall và false positives so với Version 10. [Báo cáo, giới hạn và bảng so sánh](../../docs/b0_pilot_audit.md#kết-quả-version-11--sgd-kaggle-30102026). Gói ZIP và toàn bộ thành viên đã kiểm SHA; mở `b0_s960_sgd_kaggle_v3/weights/best.pt`, `last.pt`, `results.csv`, `training_summary/results.png`.

