# Pilot B0 — hồ sơ dữ liệu, huấn luyện và chẩn đoán

## Kết quả Version 10 — AdamW Kaggle, 30/10/2026

**Kết luận:** thí nghiệm mới đã hoàn thành, F1 tại ngưỡng cố định nhích lên so với Version 9, nhưng mAP và recall cố định giảm. Đây là đánh đổi trên validation đã dùng nhiều lần; chưa đủ cơ sở thay checkpoint/điểm vận hành B0 đang khóa hoặc kết luận model tổng quát tốt hơn.

### Dữ liệu và cách so sánh

Hai run đều dùng cùng 2.681 ảnh train, 307 ảnh val (91 dương, 216 âm), cùng YOLOv8s/960 và cùng SHA checkpoint khởi tạo `c1fdd6dc...019302`. Provenance toàn bộ train/val có cùng SHA `b7c0bc11...a61e`; đã đối chiếu riêng 307 danh tính frame và SHA ảnh/nhãn với nguồn hardneg trước mở rộng. Val gồm 97 ảnh ACCIDENT và 210 ảnh TAD; 216 ảnh âm thuộc 8 nhóm nguồn, không coi 216 frame là 216 camera/sự kiện độc lập. Test/reserve không được suy luận.

Version 10 dùng AdamW, batch yêu cầu 8, AMP, nbs32, cosine, augmentation nhẹ hơn và policy dừng sau epoch25/patience25. Thay đổi nhiều yếu tố cùng lúc nên không tách được phần đóng góp của optimizer, batch, AMP, lịch LR hay augmentation. Recipe không tái lập paper và không chứng minh mAP tổng quát.

### Kết quả trên cùng validation

| Metric | Version 9 — SGD | Version 10 — AdamW | Chênh lệch V10 − V9 |
| --- | ---: | ---: | ---: |
| mAP50 | 69,79% | 67,85% | −1,94 điểm % |
| mAP50–95 | 55,87% | 52,63% | −3,24 điểm % |
| Precision tại confidence 0,25/IoU 0,5 | 65,59% | 72,15% | +6,56 điểm % |
| Recall tại confidence 0,25/IoU 0,5 | 67,03% | 62,64% | −4,40 điểm % |
| F1 tại confidence 0,25/IoU 0,5 | 66,30% | 67,06% | +0,75 điểm % |
| TP / FP / FN tại ngưỡng cố định | 61 / 32 / 30 | 57 / 22 / 34 | −4 / −10 / +4 |
| Ảnh âm có dự đoán / 216 ảnh âm | 5 | 2 | −3 ảnh |

Đây là bbox/frame, không phải accuracy phân loại, recall sự kiện hay số báo sai/giờ. P/R chính thức của Ultralytics được chọn tại điểm trên đường cong và có thể khác P/R tại confidence 0,25; không trộn hai cách đo. P/R chính thức V9 là **83,55%/58,24%**, V10 **75,90%/63,74%**. mAP so qua nhiều ngưỡng confidence, F1 trên chỉ tại một ngưỡng cố định; vì vậy mAP giảm và F1 tăng có thể cùng xảy ra.

So Version 9, trong 91 ảnh dương: **53** đều được khớp bbox, **8** từ khớp sang bỏ sót, **4** từ bỏ sót sang khớp, **26** đều bỏ sót. Trong 216 ảnh âm: 4 ảnh hết dự đoán sai, 1 ảnh vẫn sai, 1 ảnh phát sinh dự đoán sai, 210 ảnh đều không có hộp. Tổng FP giảm 32→22 gồm FP trong ảnh dương 26→19 và ảnh âm 6→3; số hộp FP khác số ảnh âm có FP. Đây là các ảnh tương quan theo nguồn, không suy ra ý nghĩa thống kê hoặc hiệu quả ngoài thực tế.

### Quá trình train và checkpoint

- Chạy đủ **60 epoch**, không dừng sớm. `results.csv` đạt fitness/mAP50–95 cao nhất tại **epoch 52**: mAP50 67,868%, mAP50–95 52,856%. `best.pt` có `train_metrics` khớp hàng này; epoch trong file đã strip là −1, nên mốc 52 được xác định bằng metrics/CSV. Đánh giá lại `best.pt` cho **67,853% / 52,626%**; dùng giá trị đánh giá lại trong bảng. Sự chênh lệch nhỏ giữa hai lần đo chưa được xác định nguyên nhân.
- Epoch 5 mAP50 33,91%, epoch 7 47,11%, epoch 25 67,37%, epoch 52 67,87%, epoch 60 66,56%. Run đã phục hồi sau giai đoạn đầu giảm sâu; đánh giá epoch 7 là trung gian. Sau epoch52, mAP50–95 cuối 51,02%, thấp hơn best.
- Log xác nhận AMP checks passed, AdamW lr0=0,0003, probe backward batch8 AMP thành công và không tìm thấy cảnh báo OOM/giảm batch. `args.yaml` ghi batch8; không suy thêm rằng bộ nhớ của mọi batch khác đều giống probe. `last.pt` đã strip optimizer, không phải checkpoint resume đầy đủ.
- Python3.12.10, Torch2.11.0+cu128, Ultralytics8.4.178, GPU0 Tesla T4. Thời gian trainer bao gồm đánh giá khoảng **79,1 phút**, không tính toàn bộ thời gian chuẩn bị session Kaggle.

Mở [đồ thị loss và metric](../outputs/training/b0_s960_adamw_kaggle_v2/training_summary/results.png), [PR curve](../outputs/training/b0_s960_adamw_kaggle_v2/metrics_val/BoxPR_curve.png), [bảng epoch](../outputs/training/b0_s960_adamw_kaggle_v2/results.csv), hoặc [cases validation](../outputs/training/b0_s960_adamw_kaggle_v2/cases_val/cases.csv). Ví dụ: [một ảnh dương V9 khớp nhưng V10 bỏ sót](../outputs/training/b0_s960_adamw_kaggle_v2/cases_val/04O2SOGSG_U_00_f000017.jpg) và [một ảnh âm phát sinh FP](../outputs/training/b0_s960_adamw_kaggle_v2/cases_val/20230818_acci-bg_7_f000197.jpg). Hộp xanh là nhãn, đỏ là dự đoán; quan sát một ảnh không chứng minh nguyên nhân gây lỗi.

Trọng số: [best.pt](../outputs/training/b0_s960_adamw_kaggle_v2/weights/best.pt) SHA `adff35a1da7656908edbea2eb31c60aaf184166bc222e8ae55044b4a12ac7995`; [last.pt](../outputs/training/b0_s960_adamw_kaggle_v2/weights/last.pt) SHA `01633aa4c4a3c1b7388a8390dd896863249cefb203103c77b97a172cc0a43960`. ZIP Version10, từng member, config và best checkpoint đã kiểm hash. Metadata/CSV Version9 lấy chọn lọc **67.159 bytes** qua HTTPS Range, từng file khớp manifest, không tải checkpoint hoặc kiểm lại hash toàn ZIP cũ. [Bằng chứng so sánh](evidence/2026-10-30-b0-adamw-validation.json).

**Bước kế tiếp:** rà các ca mất/khôi phục phát hiện và FP ở cùng validation, cân nhắc trade-off recall với FP trước khi thiết kế thêm thí nghiệm. Chưa tự train lại, chọn lại ngưỡng bằng holdout, mở test/reserve hay thay model đã khóa trong lượt báo cáo này.

**Mới nhất29/10:** người dùng đã train xong `b0_s960_hardneg_v1`,15epoch/bestCSV5. Val307ảnh: mAP50 **68,48%**, mAP50–95 **55,43%**, F1 tại0,25/IoU0,5 **62,07%**. [Mở phần kết quả mới](#kết-quả-s960-hardneg-hoàn-tất--29102026). Các mục chuẩn bị và những bảng theo ngày bên dưới giữ trạng thái lịch sử; không lấy số từ các tập đánh giá khác nhau để so trực tiếp.

**Mốc lịch sử 28/10:** dataset normal mở rộng **2.170 ảnh đã train đủ 60 epoch và đánh giá val**; có 120 frame normal giữ riêng và mốc ba checkpoint cũ trên 217 ảnh val mới. [Mở phần hiện hành và lệnh train](#b0-normal-mở-rộng--28102026). Các mục dưới giữ kết quả/hạn chế lịch sử của model mốc đã train trên 1.750 ảnh.

## B0 mở rộng ACCIDENT v9 — 26/10/2026

**Trạng thái 27/10: pilot ảnh 1.750 mẫu đã train xong và đo; B0 sự kiện đầy đủ chưa hoàn thành.** Test 112 ảnh: mAP50 **0,6968**, mAP50–95 **0,5223**; ở confidence 0,25 và IoU 0,5 có **67 TP / 46 FP / 40 FN**. So cùng ảnh, checkpoint pilot cũ mAP50 **0,0119**, 14 TP / 598 FP / 93 FN. Trên probe 100 frame TAD normal, model mới dự đoán nhầm ở **41 frame / 4 clip**, tổng 46 bbox; model cũ dự đoán nhầm 76 frame / 5 clip, 225 bbox. Đây là so sánh ảnh thưa, không phải false alerts/giờ; 100 frame chỉ từ 5 clip chọn theo kích thước. [Report](../outputs/training/b0_verified_pilot_v1/clean_test/report.json), [hướng dẫn đọc biểu đồ](../outputs/training/README.md), [nhật ký](../progress/2026-10-27.md).

Run trước trên 2.436 ảnh đã dừng và release bị thu hồi vì dùng 1.084 frame âm suy ra chưa được rà toàn ảnh. Không dùng checkpoint/validation run đó làm kết quả B0. Phần lịch sử bên dưới ghi release đã thu hồi. Đã đọc workbook 05/08/09/11/15, toàn văn ACCIDENT và recipe TP-YOLOv8, tài liệu fine-tune Ultralytics. [Đối chiếu phương pháp](../reference/LITERATURE_REVIEW.md#8-đối-chiếu-recipe-huấn-luyện-b0-mở-rộng--26102026), [policy hiện hành](../configs/b0_verified_label_policy.json).

**Release thay thế đã train 60 epoch:** 1.750 ảnh: train 1.122 impact + 419 âm, val 91 impact + 6 âm, test sạch 107 impact + 5 âm. Âm gồm 30 frame ACCIDENT đã rà, 300 ảnh lấy đều từ ba chuỗi DETRAC người dùng xác nhận và 100 frame lấy đều từ hai clip TAD có nhãn normal tác giả. 400 frame mới chỉ thuộc năm clip/ba nhóm cảnh; nguy cơ model nhận diện khác biệt nguồn còn tồn tại. `--check` kiểm 1.750 ảnh/hash; rà pHash ≤5/dHash ≤8 trên mọi cặp split không tìm thêm cặp theo ngưỡng này. [Split](../data/processed/b0_verified_pilot_v1/split_report.json), [config](../configs/b0_verified_pilot_v1.json), [policy](../configs/b0_verified_label_policy.json). Release cũ bên dưới được giữ để truy nguyên, không dùng train lại.

Probe âm bổ sung đã cố định trước khi xem dự đoán: **100 frame từ 5 clip TAD test/normal** công khai, 20 frame đều/clip; [manifest nguồn/hash](../data/registries/b0_tad_normal_test_v1.json). Năm clip được chọn theo kích thước nhỏ nhất để giới hạn lượt tải, không lấy ngẫu nhiên nên có thể thiên lệch. Tác giả gắn nhãn normal cấp clip, người dùng chưa rà. Đo xong **41/100 frame có bbox nhầm, 46 bbox tại confidence 0,25**; không quy đổi thành số báo sai/giờ, camera độc lập chưa xác minh. Ví dụ đã xem: frame 0 clip F9 là đường hầm trống nhưng model đặt hộp đỏ gần mép đường, confidence 0,34. Kiểm pHash ≤5/dHash ≤8 giữa probe và mọi split không tìm cặp qua ngưỡng; báo cáo `outputs/audits/b0_exported_similarity_2/report.json`. Probe không thay test 112 ảnh chính.

Đã tải đủ **1.346 clip thật xe–xe** có metadata frame/bbox hợp lệ từ Kaggle v9, khoảng **3,04 GiB**. Raw nằm ở `data_raw/accident/public_selected/real_videos/`; URL/SHA/size ở `download_receipts.json` cạnh thư mục này. Kiểm giải mã, kích thước, số frame và PTS: **1.335 đạt, 11 reject**; tiếp tục loại **9** trường hợp đã bị rà loại ở hai ngày 25–26/10 và **4 clip có impact trùng pixel nhưng bbox khác nhau**, còn **1.322 impact** để dùng. Journal lý do từng clip ở `outputs/audits/accident_scale/clips.jsonl`; báo cáo tải ở `outputs/audits/accident_scaled_download/report.json`. Bản release ứng viên trước kiểm trùng được giữ trong `.tmp/`; không có epoch huấn luyện nào từ bản đó.

| Tập | Dương impact tác giả | Âm | Tổng ảnh |
| --- | ---: | ---: | ---: |
| Train | 1.122 | 1.103 | 2.225 |
| Validation | 91 | 6 | 97 |
| Test | 109 | 5 | 114 |

Tổng **2.436 ảnh / 1.284 nhóm nguồn tạm**; số nhóm nguồn chưa chứng minh số camera hay sự kiện độc lập. Âm gồm **1.084 nhãn yếu suy từ first-visible-contact, chỉ train**, và **30 frame đã rà** từ pilot cũ. Không lan nhãn impact sang frame khác. Nhãn yếu chọn một frame trước nửa chỉ số impact, cách impact ít nhất một giây theo PTS file; đây là giả định phục vụ train, có thể còn nhiễu vì chưa rà toàn cảnh từng frame. Val/test không chứa loại nhãn yếu này. Bảng xem mẫu ở `outputs/audits/accident_scale/spotcheck_author_boxes.jpg` và `spotcheck_early_candidates.jpg`, chỉ là spot check minh họa.

Kiểm lại provenance của dataset đã xuất: **0 nhóm nguồn** và **0 hash PNG giống hệt** xuyên split; kiểm này chưa chứng minh ảnh gần trùng hoặc camera độc lập. Trong 1.322 bbox impact, 505 hộp có diện tích nhỏ hơn 1% ảnh nguồn; trung vị 1,62%. Đây là lý do cần phân tích lỗi vùng nhỏ sau train, phù hợp vấn đề được paper TP-YOLOv8 nêu nhưng chưa phải bằng chứng model của project giải quyết được. Thống kê ở `outputs/audits/accident_scale/label_statistics.json`.

**Điều chỉnh tập đánh giá trước khi xem test (27/10):** hash cảm nhận và đối chiếu ảnh cho thấy hai sự kiện xuất hiện ở train lẫn test dưới tên nguồn khác, nên test 114 ảnh ban đầu bị nhiễm trùng. [Phiếu loại hai nhóm](../data/reviews/2026-10-27-b0-near-duplicate-review.json) khóa test sạch **112 ảnh = 107 dương + 5 âm**, trước khi đo test; train/validation giữ nguyên. Run v2 bị dừng trước bước đo test; release verified sau đó xuất thẳng test sạch và đã đánh giá trên 112 ảnh. Heuristic chưa thể khẳng định phát hiện hết video gần trùng hay độc lập camera.

**Split:** tuỳ biến theo nhóm video gốc, giữ nhóm pilot cũ. Nhóm mới thuộc author-IID train được giữ train để giảm rủi ro giao CADP/TAD; phần còn lại chia bằng hash nhóm, nên cùng nguồn không qua hai tập. Một nhóm test cũ thuộc author-train; metadata không nêu ID giao CADP/TAD riêng. Không nhận split này là benchmark IID/geo-aware của ACCIDENT. [Index/split/report](../data/processed/b0_accident_scaled_v1/split_report.json), [policy](../configs/b0_scaled_label_policy.json).

**Recipe có căn cứ:** TP-YOLOv8 công bố SGD lr 0,01, momentum 0,937, ảnh 640, batch 16, train từ đầu tối đa 300 epoch/patience 50 trên A40 48 GB. B0 giữ YOLOv8n pretrained theo hướng dẫn fine-tune Ultralytics, dùng SGD/lr/momentum trên, batch 16 và hai luồng nạp dữ liệu trên RTX 3050 Ti 4 GB, tối đa 60 epoch/patience 18. Batch 4 ban đầu chỉ dùng ~1,02 GiB VRAM và loader chậm; sau đo phần cứng chuyển batch 16, thực tế ~3,82 GiB VRAM và nhanh hơn. Lượt batch 4 bị dừng, giữ `.tmp/b0_scaled_batch4_incomplete/`, không là kết quả so sánh. Khác dataset, nhãn, kiến trúc và tài nguyên nên đây là thí nghiệm thích ứng, chưa phải tái lập paper. [Config đầy đủ](../configs/b0_accident_scaled_v1.json); không kết luận riêng optimizer hay riêng dữ liệu gây cải thiện khi hai yếu tố cùng thay đổi.

Sau epoch 1, run batch 16 lỗi trong serialize checkpoint và không có `best.pt`; log được giữ. Lượt 27/10 dùng [config v2 batch 8](../configs/b0_accident_scaled_v2.json), giữ cùng split/seed/lr/optimizer, chạy lại từ pretrained. Chưa xác định nguyên nhân lỗi gốc; script đã sửa để không che lỗi serialize ban đầu nếu tái diễn.

**Vì sao tăng ảnh:** 47 ảnh/17 nhóm chỉ đủ thử luồng kỹ thuật; train trước chỉ có 11 impact nên độ đa dạng rất thấp. Mục tiêu hơn 1.000 impact của lượt này không phải ngưỡng khoa học bảo đảm “đủ học”. Cần xem learning curve, chất lượng bbox trên nhóm giữ riêng, độ đa dạng camera/sự kiện và lỗi thực tế; nhân nhiều frame gần nhau hoặc augmentation từ một tai nạn không tạo thêm sự kiện độc lập.

Lệnh tái tạo (chỉ xuất vào thư mục mới; máy này đã có dữ liệu):

```powershell
.\.venv\Scripts\python.exe -X utf8 -B scripts/download_accident_real.py
.\.venv\Scripts\python.exe -X utf8 -B scripts/prepare_accident_scale.py --workers 4
.\.venv\Scripts\python.exe -X utf8 -B scripts/prepare_b0_scaled_release.py --verified
.\.venv\Scripts\python.exe -X utf8 -B scripts/prepare_b0_pilot_index.py --pool-index data/processed/b0_verified_pilot_v1/index.csv --export-split data/processed/b0_verified_pilot_v1/split.csv --release-kind pilot --release-key verified_pilot_release --policy-path configs/b0_verified_label_policy.json --output data/processed/b0_verified_pilot_v1/dataset
.\.venv\Scripts\python.exe -X utf8 -B scripts/train_b0.py --config configs/b0_verified_pilot_v1.json --check
.\.venv\Scripts\python.exe -X utf8 -B scripts/train_b0.py --config configs/b0_verified_pilot_v1.json --train
# Chỉ chạy sau khi train kết thúc; so hai checkpoint trên cùng 112 ảnh test sạch
.\.venv\Scripts\python.exe -X utf8 -B scripts/evaluate_b0_clean.py --reference-experiment outputs/training/b0_basic_pilot_v1/experiment.json --normal-manifest data/registries/b0_tad_normal_test_v1.json
```

Máy mới cần phục hồi metadata ACCIDENT và hồ sơ pilot cũ theo GETTING_STARTED trước khi lập release; không sửa SHA để vượt qua dữ liệu thiếu. Manifest asset lớn của release nằm local trong `data/processed/`, readiness trên Git chỉ giữ đường dẫn/hash để tránh phình metadata gốc.

## Pilot B0 ảnh 26/10/2026

**Đã hoàn thành một vòng split → export → train → đánh giá thật. Chất lượng detector pilot chưa đạt để sử dụng.** Theo quyết định mới của người dùng, hard negatives/video âm dài và benchmark sự kiện được để sau; không chặn thí nghiệm ảnh cơ bản. Không thay mô hình hoặc định nghĩa nhãn B0.

Pilot đầu chọn **47 ảnh của 17 nhóm nguồn ACCIDENT** đã có cả impact tác giả và frame trước impact được rà. Việc dùng cùng nguồn giúp tránh thí nghiệm đầu chỉ phân biệt STTAD dương với DETRAC âm. Pool v3 đầy đủ vẫn giữ nguyên 2.423 tham chiếu để mở rộng sau; không nhân bản toàn bộ dataset.

| Tập | Nhóm nguồn | Ảnh dương | Ảnh âm | Tổng ảnh |
| --- | ---: | ---: | ---: | ---: |
| Train | 11 | 11 | 19 | 30 |
| Validation | 3 | 3 | 6 | 9 |
| Test | 3 | 3 | 5 | 8 |

Split tạo trước train bằng seed **20261026**, theo nhóm nguồn, giữ segment cùng original; hai nguồn Seattle cùng train theo cách bảo thủ. Head-on/sideswipe hiếm chỉ ở train; val/test có rear-end và t-bone. Đây là split pilot của project, chưa chứng minh camera-held-out hoặc tái lập benchmark tác giả. Không điều chỉnh split/ngưỡng theo điểm test. [Split/report local](../data/processed/b0_basic_pilot_v1/split_report.json), [snapshot đọc sau clone](evidence/2026-10-26-b0-basic-pilot.json).

**Nhãn:** một bbox `accident` bao vùng các bên tham gia theo annotation impact đã kiểm; ảnh âm có TXT rỗng chỉ khi đúng frame đã có phiếu rà. Frame thiếu nhãn không được đưa vào làm âm. Bbox nguồn không bị sửa hoặc lan sang frame lân cận; CADP envelope và track ID không tham gia GT pilot này.

**Train:** [config](../configs/b0_pilot.json), YOLOv8n khởi tạo từ `yolov8n.pt` local, Ultralytics 8.4.178, torch 2.11.0+cu128, RTX 3050 Ti 4 GB; ảnh 640, batch 4, workers 0, AMP tắt. Tối đa 40 epoch, patience 15; thực tế **16 epoch rồi early stop**, best theo validation nằm ở epoch đầu. Tổng vòng train/đo khoảng 107 giây, không tính import/khởi tạo. Một lần thử trong sandbox dừng trước epoch đầu do Windows pipe `WinError 5`; đã giữ cấu hình dở ở `.tmp/b0_basic_pilot_v1_failed_sandbox/`, chạy lại được ngoài sandbox mà không thay code thư viện.

| Phép đo | Validation | Test |
| --- | ---: | ---: |
| mAP50 bbox, Ultralytics | 0,030930 | 0,001611 |
| mAP50–95 bbox, Ultralytics | 0,017802 | 0,000466 |
| TP / FP / FN tại confidence 0,25; IoU 0,5 | 2 / 60 / 1 | 0 / 45 / 3 |
| Precision / recall tại ngưỡng cố định | 3,23% / 66,67% | 0% / 0% |
| Frame âm có dự đoán | 6/6 | 5/5 |

AP là phép quét confidence của evaluator Ultralytics. Bảng TP/FP/FN riêng chạy inference từng ảnh tại ngưỡng đã khóa; không trộn operating point hay quy trình tiền xử lý với metric AP. Chúng đều là **bbox/frame**, chưa phải event recall, delay hoặc false alerts/hour. Test chỉ ba impact nên không đủ kết luận về độ tổng quát.

**Lỗi đã xem:** `0jk4tWwDKqc_00` frame 156 có GT gọn quanh hai xe, nhưng model trả hộp rất rộng gần toàn cảnh, không đạt IoU 0,5. Nhiều ảnh âm cũng có hộp đỏ. Kết quả cho thấy lần train hiện tại chưa học được vùng cần tìm; riêng phép đo này chưa xác định được tỷ trọng lỗi do ít mẫu, tối ưu hóa hay độ đa dạng ảnh. Không gọi checkpoint là model tai nạn đã dùng được, không chuyển thẳng sang B1 để che lỗi B0.

Mở các đầu ra sau:

- [experiment.json](../outputs/training/b0_basic_pilot_v1/experiment.json): config/version/hash/checkpoint và metric.
- [results.png](../outputs/training/b0_basic_pilot_v1/results.png), [results.csv](../outputs/training/b0_basic_pilot_v1/results.csv): diễn biến train/validation.
- [Ảnh test có GT xanh/dự đoán đỏ](../outputs/training/b0_basic_pilot_v1/cases_test/0jk4tWwDKqc_00_f000156.jpg); [bảng mọi case test](../outputs/training/b0_basic_pilot_v1/cases_test/cases.csv); toàn bộ 8 ảnh đều được xuất, không chọn riêng ảnh đẹp.
- [Checkpoint](../outputs/training/b0_basic_pilot_v1/weights/best.pt), [provenance](../data/processed/b0_basic_pilot_v1/dataset/provenance.csv). Media/checkpoint local ngoài Git.

**Bước tiếp theo cụ thể:** giữ ba nhóm test cố định; mở rộng ví dụ train bằng bbox impact public ACCIDENT và STTAD đã chuẩn hóa, kiểm nguồn/ảnh/nhãn; so cấu hình trên validation và ghi thí nghiệm mới. Không cần xin annotation riêng hoặc hoàn tất âm khó trước vòng train kế tiếp. Chỉ lấy thêm member cần dùng, không tải archive toàn bộ. Có hơn 26 clip ở nguồn public: paper ACCIDENT công bố 2.027 clip thật; project mới kiểm mẫu chọn lọc, không tuyên bố đã tải tất cả.

Kiểm bộ hiện có mà không train lại:

```powershell
.\.venv\Scripts\python.exe -X utf8 -B scripts/train_b0.py --check
.\.venv\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -q
```

Máy mới cần khôi phục media/audit đúng hash theo GETTING_STARTED trước. Các lệnh sau chỉ dùng khi output tương ứng chưa tồn tại; script từ chối ghi đè:

```powershell
.\.venv\Scripts\python.exe -X utf8 -B scripts/prepare_b0_pilot_index.py --make-pilot-split data/processed/b0_public_pilot_v3/index.csv --output data/processed/b0_basic_pilot_v1 --seed 20261026
.\.venv\Scripts\python.exe -X utf8 -B scripts/prepare_b0_pilot_index.py --pool-index data/processed/b0_basic_pilot_v1/index.csv --export-split data/processed/b0_basic_pilot_v1/split.csv --release-kind pilot --output data/processed/b0_basic_pilot_v1/dataset
.\.venv\Scripts\python.exe -X utf8 -B scripts/train_b0.py --train
```

Readiness trên Git là hồ sơ release máy phát triển, không tự cấp phép bỏ qua mismatch khi tái tạo. Đường dẫn tuyệt đối YAML thuộc máy hiện tại; máy mới export lại YAML đúng vị trí và lưu hash lần chạy mới. Cache nằm `.tmp/`; config train và checkpoint mới cần output mới, không sửa thí nghiệm đã đo.

## Batch mở rộng 26/10/2026 — đã hoàn thành

**Mốc lịch sử trước vòng pilot ở trên.** Các câu chưa split/train trong mục này mô tả lúc vừa hoàn tất batch mở rộng.

**Hoàn thành một vòng mở rộng dữ liệu B0:** lấy chọn lọc → kiểm toàn video/nhãn/PTS → rà phạm vi → bổ sung âm cùng cảnh → so nguồn → đăng ký → dựng pool v3 → kiểm đầu ra. B0 chưa train và chưa hoàn thành đánh giá.

| Hạng mục | Kết quả thực tế |
| --- | --- |
| Tải mới | 20 MP4 ACCIDENT v9, **52.790.420 byte**, trần 64 MiB; giải mã **8.334 frame**; không tải archive |
| Impact mới | 20/20 khớp PTS OpenCV và FFprobe; PNG trùng pixel decode, nhãn giữ bbox tác giả |
| Phạm vi vùng | **13 giữ, 7 loại**: 5 khó xác minh hình học/che/nhòe/cắt biên, 2 cảnh xe tải chạm hầm ngoài phạm vi xe–xe |
| Âm cùng cảnh | Sinh 73 ứng viên UNKNOWN từ 26 clip; kiểm lại pixel/PTS đủ 73; sau xem ảnh chọn **30 frame âm thuộc 17 chuỗi** có dương tương ứng |
| So nguồn | 36 chuỗi, **12.521 frame**, 630 cặp nhóm; không pixel hash trùng xuyên nhóm; một gợi ý gần vẫn DETRAC 20011/20012 |
| Pool v3 | **2.423 tham chiếu = 48 dương + 2.375 âm**; 26 chuỗi trong pool, 24 nhóm chống rò rỉ, 17 nhóm có cả hai nhãn |
| Tái lập | Manifest 44 asset; 24 dòng cũ giữ nguyên, schema giữ nguyên, backup trước sửa; 27 asset ACCIDENT (CSV + 26 MP4) khớp SHA |
| Kiểm code/media | 33 test đạt cuối lượt, gồm exporter; audit pool đọc đủ 2.115 ảnh + 308 frame video, không lỗi kỹ thuật; chưa split/train |

**Cách chọn:** chỉ trang đầu 100 file đã kiểm; ưu tiên metadata Good/Fine, bbox diện tích chuẩn hóa >=0,008 và file <=6,5 MB, rồi bổ sung mẫu nhỏ đủ phạm vi. Đây là pilot thiên về ảnh dễ rà, **không phải tập benchmark đại diện**. Việc bỏ ảnh khó được ghi rõ; không gọi 21 nhóm nguồn dương là 21 camera độc lập.

**Nhãn âm mới có căn cứ gì?** [Paper ACCIDENT mục 3.1](https://arxiv.org/html/2604.09819v1#S3.SS1) mô tả impact là lần tiếp xúc nhìn thấy đầu tiên. Công cụ chọn tối đa ba frame ở nửa đầu trước impact, cách impact >=1 giây **PTS file phát hành**, sau đó AI xem toàn ảnh và chọn thưa các frame đủ rõ. Không tự dùng phần bù của bbox/nhãn thiếu làm âm. 30 frame được nhập bằng `derived_author_preimpact_assistant_frame_review`; 43 ứng viên khác không nhập pool. Phiếu chỉ có hiệu lực cho frame cụ thể, không xác nhận cả đoạn hoặc toàn video; cũng không xác minh capture FPS. Nhiều cảnh âm mới có xe đang đi, hàng chờ hoặc qua giao lộ, nhưng **chưa là benchmark near-miss/phanh gấp đã rà diễn biến đầy đủ**.

Không còn quan hệ tuyệt đối “ACCIDENT là dương”, nhưng mất cân bằng và lệch nguồn vẫn rõ: quy tắc nhãn đa số theo dataset khớp 99,30% trên chính pool, trong khi chỉ đoán âm cũng khớp 98,02%. Hai con số mô tả dữ liệu, không phải metric model/test. B0 vẫn thiếu độ phủ dương (17 ACCIDENT chỉ một impact/clip + 31 frame từ 4 STTAD), âm dài/hard negatives và split có căn cứ. Không tăng số mẫu bằng copy ảnh hoặc lan bbox sang các frame không được gán nhãn.

### Những file cần mở

- [Pool v3](../data/processed/b0_public_pilot_v3/index.csv): từng ảnh/frame và nguồn nhãn; [report](../data/processed/b0_public_pilot_v3/report.json).
- [Phiếu 20 impact](../data/reviews/2026-10-26-accident-source-review.json): tên clip, giữ/loại và lý do; giữ nguyên bbox nguồn.
- [Phiếu 30 frame âm](../data/reviews/2026-10-26-preimpact-frame-review.json): trạng thái từng ứng viên, ràng buộc hash/mapping.
- [Minh họa impact trang 1](../outputs/audits/accident_expansion/impact_review_01.jpg), các trang `02`–`05` cùng thư mục; [ảnh trước impact trang 1](../outputs/audits/accident_expansion/preimpact/review_01.jpg). Chữ PENDING trên montage ghi trạng thái lúc tạo ứng viên; quyết định cuối ở phiếu JSON, không sửa bằng chứng ban đầu.
- [Kiểm pool](../outputs/audits/accident_expansion/pool_validation/report.json), [nhóm](../outputs/audits/accident_expansion/pool_validation/groups.csv), [kiểm toàn nguồn](../outputs/audits/pilot_groups_3/report.json).
- [Snapshot nhỏ sau clone](evidence/2026-10-26-b0-expansion.json); media gốc ở `data_raw/accident/public_selected/real_videos/`, mọi output vẫn ngoài Git.

### Tái tạo batch trên máy mới

Danh sách **đúng 20 file** ở `clips[].source_sequence` trong phiếu impact; URL tải từng file và SHA trong `data/download_catalog.json`. Máy hiện tại đã có output: mở xem, không chạy lại vào thư mục tồn tại. Máy mới phục hồi các batch trước theo GETTING_STARTED rồi:

```powershell
$review = Get-Content -Raw -Encoding UTF8 data/reviews/2026-10-26-accident-source-review.json | ConvertFrom-Json
$members = @($review.clips | ForEach-Object { "real_videos/$($_.source_sequence).mp4" })
.\.venv\Scripts\python.exe -X utf8 -B scripts/audit_accident_public.py --fetch-selected --max-mib 64 --output outputs/audits/accident_expansion --members $members
.\.venv\Scripts\python.exe -X utf8 -B scripts/audit_accident_public.py --verify-report outputs/audits/accident_expansion/report.json
.\.venv\Scripts\python.exe -X utf8 -B scripts/audit_accident_public.py --prepare-preimpact outputs/audits/accident_expansion/report.json --output outputs/audits/accident_expansion/preimpact
.\.venv\Scripts\python.exe -X utf8 -B scripts/audit_accident_public.py --verify-preimpact outputs/audits/accident_expansion/preimpact/report.json
# Âm từ batch sáu clip cũ cũng có trong phiếu; phục hồi tương tự:
.\.venv\Scripts\python.exe -X utf8 -B scripts/audit_accident_public.py --prepare-preimpact outputs/audits/accident_public/report.json --output outputs/audits/accident_expansion/preimpact_previous
.\.venv\Scripts\python.exe -X utf8 -B scripts/audit_accident_public.py --verify-preimpact outputs/audits/accident_expansion/preimpact_previous/report.json
```

Report tái chạy có thể khác ngày/phiên bản decoder/hash PNG. **Không sửa hash phiếu để bỏ mismatch.** Phải đối chiếu lại các fingerprint/mapping và lập phiếu tái xác minh khi khác; xác nhận người dùng về dữ liệu cũ vẫn được giữ nếu dữ liệu gốc khớp. Khi bằng chứng đã khớp, dựng pool bằng:

```powershell
.\.venv\Scripts\python.exe -X utf8 -B scripts/prepare_b0_pilot_index.py --sttad-report outputs/audits/sttad_public_6/report.json --accident-report outputs/audits/accident_public/report.json --accident-review data/reviews/2026-10-25-accident-source-review.json --extra-accident outputs/audits/accident_expansion/report.json data/reviews/2026-10-26-accident-source-review.json --preimpact-review data/reviews/2026-10-26-preimpact-frame-review.json --group-review data/reviews/2026-10-26-accident-source-review.json --output data/processed/b0_public_pilot_v3
.\.venv\Scripts\python.exe -X utf8 -B scripts/prepare_b0_pilot_index.py --audit-index data/processed/b0_public_pilot_v3/index.csv --output outputs/audits/accident_expansion/pool_validation
```

**Bước kế tiếp:** mở rộng nhãn vùng trên nhiều thời điểm/sự kiện và âm khó có diễn biến rõ; rà nhóm camera/nguồn trước quyết định split. Batch 20 clip này đã xong, không cần tạo thêm preview cho cùng mẫu hay xin lại xác nhận CADP/DETRAC. Điều kiện mở train vẫn theo [readiness](../data/b0_readiness.json) và [bảng B0](../progress/README.md).

## Kết quả lịch sử 25/10 — thêm nhãn vùng public từ ACCIDENT


Đã đọc [paper tác giả](https://arxiv.org/abs/2604.09819), repo và metadata Kaggle phiên bản 9. Paper mô tả bbox quanh các bên va chạm tại impact. API public cho lấy từng member không cần tải archive khoảng 20 GB. Đã lấy **sáu MP4, 1.445 frame giải mã**, CSV 2.027 dòng khoảng 487 KB và danh mục trang đầu; không giả là đã tải/kiểm toàn bộ 2.027 clip. Sáu video tổng khoảng 5,4 MB, giữ cấu trúc `data_raw/accident/public_selected/real_videos/`.

| Chuỗi gốc | Frame impact (decode 0-based) | Kiểm vùng B0 của AI |
| --- | --- | --- |
| `0NixrF6Mt00_0_00` | 27 | Giữ bbox tác giả cho pool chưa chia tập |
| `04O2SOGSG_U_00` | 17 | Giữ bbox tác giả cho pool chưa chia tập |
| `1_F0r7KVJ1k_00` | 160 | Giữ bbox tác giả cho pool chưa chia tập |
| `0PrAtifCwjg_00` | 137 | Giữ bbox tác giả cho pool chưa chia tập |
| `2QZf8MiIRK0_00` | 11 | Loại: tương tác xa/nhỏ, phạm vi các bên trong bbox chưa rõ |
| `-FQxK6HdxNU_00` | 48 | Loại: hộp chủ yếu bao xe bên phải, xe liên quan bên trái vượt ngoài vùng |

Đây là nhãn tác giả và quyết định lọc chất lượng của AI, **không phải người dùng xác nhận thêm**, không phải nhãn do YOLO dự đoán. Không mở rộng hai bbox bị loại cho vừa quy tắc. Mỗi clip chỉ có **một nhãn vùng tại impact**; những frame khác không đưa vào supervision, không tự gán âm.

**Đánh số và timing:** cả sáu video có số frame decode bằng `no_frames` trong CSV cộng 1. Giữ nguyên trường nguồn, không coi nó là số frame decode chính xác rồi tự dịch nhãn. Kiểm PTS bằng cả OpenCV và FFprobe cho thấy `accident_frame` 0-based khớp `accident_time` tác giả, sai số lớn nhất khoảng **0,000334 giây của file phát hành**. Có khoảng PTS không đều; phép `frame / FPS_trung_bình` cho kết quả sai. Đây chưa xác minh FPS/timing ghi hình gốc và không thay trạng thái timing CADP.

Ảnh PNG sạch được lấy đúng frame, kiểm lại trùng pixel với decode; nhãn YOLO giữ nguyên bbox chuẩn hóa, sai số chuyển số dưới 1e-9. SHA ghi nhận từ endpoint public có phiên bản là fingerprint cục bộ, không giả làm checksum do tác giả công bố. [Phiếu kiểm](../data/reviews/2026-10-25-accident-source-review.json) gắn hash báo cáo/verification; mọi split vẫn unassigned.

**Pool hiện hành:** [v2/index.csv](../data/processed/b0_public_pilot_v2/index.csv), **2.380 dòng = 35 dương + 2.345 âm**, 13 nhóm nguồn/11 nhóm cảnh tạm thời. Chỉ thêm bốn frame được giữ; v1 và các review CADP/DETRAC giữ nguyên. B0 chưa train: 35 frame dương chỉ thuộc 8 nhóm nguồn có vùng, lệch nguồn dương/âm vẫn còn; tên nguồn khác nhau không chứng minh camera/sự kiện độc lập.

### File cần mở và lệnh dùng lại

- `outputs/audits/accident_public/impact_comparisons.jpg`: trái/phải là context sạch; giữa là bbox tác giả tại impact, không phải dự đoán tai nạn.
- `outputs/audits/accident_public/verification.json`: SHA, so pixel PNG, nhãn và hai phép kiểm PTS đều đạt.
- `outputs/audits/accident_public/impact_frames.csv`: liên kết clip → frame → PNG → TXT gốc/chuyển đổi.
- `data/reviews/2026-10-25-accident-source-review.json`: lý do giữ bốn/loại hai.
- `data/processed/b0_public_pilot_v2/index.csv`: pool đang dùng; không nhập raw cả clip vào train như thể tất cả frame đã có bbox.

```powershell
# Máy mới: chỉ lấy đúng sáu member, trần 16 MiB; không tải archive
.\.venv\Scripts\python.exe -X utf8 -B scripts/audit_accident_public.py --fetch-selected --max-mib 16
# Kiểm lại output đã có, không tải/sinh thêm preview
.\.venv\Scripts\python.exe -X utf8 -B scripts/audit_accident_public.py --verify-report outputs/audits/accident_public/report.json
# Verification đã có thì đọc file; lệnh cố ý từ chối ghi đè bằng chứng.
```

Khi tái tạo pool mới, chạy `prepare_b0_pilot_index.py` với `--sttad-report`, thêm `--accident-report outputs/audits/accident_public/report.json --accident-review data/reviews/2026-10-25-accident-source-review.json` và một `--output` chưa tồn tại. SHA của report/review là bằng chứng máy hiện tại; máy mới cần kiểm lại chính dữ liệu, không thay hash để bỏ chốt.

SO-TAD đã kiểm được danh mục 2.188 member và `Appendix.txt` qua Range: chỉ có video và tên clip + một số, không có bbox trong gói này. TU-DAT có JSON chuyển động/`moving_object`, không đủ làm GT vùng accident. Giữ bằng chứng ở `outputs/audits/accident_public/source_checks/`, nguồn/diễn giải trong [reference](../reference/2026-10-24-public-data-review.md); không đưa hai dạng nhãn này vào pool B0.

## Kiểm pool trước chia tập — 26/10/2026

Đã mở rộng `prepare_b0_pilot_index.py` bằng `--audit-index`. Pool v2 có **2.072 ảnh và 308 tham chiếu frame video đọc được**, tổng 2.380, không lỗi kỹ thuật được công cụ phát hiện. Kiểm ID/frame trùng, file/provenance tồn tại, trạng thái chưa split, số bbox, class accident và mép hộp chuẩn hóa. Video decode tuần tự. Kiểm này không thay thế SHA nguồn trong audit trước hoặc chứng minh độ phủ annotation toàn ảnh.

STTAD có 31 dương/0 âm; ACCIDENT 4/0; DETRAC 0/2.037; TAD 0/308. **Không nhóm nào trong 11 nhóm chống rò rỉ có cả hai nhãn.** Gán nhãn đa số theo tên dataset khớp 100% trên chính pool: đây là thống kê tương quan nguồn–nhãn, không phải accuracy model/test hay bằng chứng model chắc chắn học shortcut. Cần thêm âm cùng miền, hard negatives và sự kiện dương độc lập; chưa chia tập/train.

Đầu ra: [report.json](../outputs/audits/b0_pool_readiness/report.json), [groups.csv](../outputs/audits/b0_pool_readiness/groups.csv). 24 test và CLI `--help` đạt. Không thêm media/nhãn/preview. Chạy lại bằng lệnh dưới với output mới; công cụ từ chối ghi đè và không tự cấp quyền train:

```powershell
.\.venv\Scripts\python.exe -X utf8 -B scripts/prepare_b0_pilot_index.py --audit-index data/processed/b0_public_pilot_v2/index.csv --output outputs/audits/b0_pool_readiness
```

## Kết quả lịch sử 24/10 — giữ nguyên để đối chiếu

## Đầu ra thực tế

| Phần | Kết quả |
| --- | --- |
| STTAD public | 4 chuỗi; 178 file đuôi ảnh, 176 đọc được, **31 frame có bbox vùng tác giả** |
| T-T_crash_2 mới | 50 ảnh 1278×534, 10 frame có bbox (15–24), 40 frame thiếu TXT giữ unknown |
| TAD normal mới | 2 clip public lấy riêng qua HTTP Range, **99 + 209 = 308 frame**, CRC member và SHA-256 khớp |
| So nguồn/cảnh | 10 nhóm nguồn, giải mã 2.742 frame; so 45 đôi nhóm, không có hash pixel trùng hệt xuyên nhóm; 1 cặp gần được kiểm trực quan |
| Pool B0 tham chiếu | **2.376 dòng** = 31 frame dương STTAD + 2.037 ảnh âm DETRAC + 308 frame âm TAD |

Đây là chuẩn bị dữ liệu và chỉ mục, chưa là tập train. 31 frame không phải 31 sự kiện độc lập. 145 frame STTAD thiếu TXT và 2 file ảnh lỗi nằm ngoài pool. CADP envelope dẫn xuất cũng không được trộn vào GT vùng STTAD.

## Phát hiện quan trọng: ba DETRAC không phải ba camera độc lập

`MVI_20011/img00664.jpg` và `MVI_20012/img00001.jpg` gần như cùng cảnh/thời điểm theo ảnh: pHash ảnh đầy đủ cách 0 bit, crop cách 2 bit, RMSE ảnh xám chuẩn hóa 0,01192. Không có pixel hash trùng hệt nên không gọi là hai file ảnh giống byte/pixel. So trực quan thấy vị trí xe, trạm xe buýt, cầu thang và hàng rào tương ứng.

MVI_20032 có cùng các mốc đường/trạm xe buýt với khung nhìn khác. Quyết định bảo thủ: **gom cả ba vào `UA_DETRAC_bus_stop_road_scene`**, bắt buộc cùng split sau này. Đây là nhóm chống rò rỉ theo cảnh, không phải camera ID vật lý đã xác minh. Các nguồn khác giữ nhóm theo chuỗi tạm thời; việc không thấy hash gần không chứng minh độc lập camera/sự kiện.

Quyết định và phạm vi kiểm của AI: [phiếu kiểm nguồn/cảnh](../data/reviews/2026-10-24-pilot-source-review.json). Thêm hai cột `leakage_group_id`, `grouping_evidence` trong inventory, không đổi schema manifest hoặc review cũ. Pool có 9 nhóm nguồn nhưng chỉ **7 nhóm cảnh bảo thủ**, chưa chia train/val/test.

## Nhãn âm TAD có căn cứ gì?

Nguồn phát hành tác giả gắn hai video trong `TAD-benchmark/train/normal/`. Đã đọc danh mục ZIP từ nguồn public, lấy đúng member, đối chiếu CRC, tính SHA và giải mã đủ video. Đây là **nhãn clip normal từ nguồn**, không phải người dùng đã xem/xác nhận, không phải nhãn mới do YOLO dự đoán. AI chỉ xem mẫu đầu/giữa/cuối để kiểm bối cảnh và chất lượng, không ghi thành rà ngữ nghĩa đầy đủ từng frame.

- `data_raw/tad/public_selected/TAD-benchmark/train/normal/20220518_acci-bg34.mp4`: CCTV ban đêm, 1920×1080, 99 frame.
- `data_raw/tad/public_selected/TAD-benchmark/train/normal/20230818_acci-bg_83.mp4`: CCTV đường cao tốc ban ngày, 640×480, 209 frame.

Hai file tổng 3.819.587 byte; tải qua Range dùng 3.838.682 byte mạng kể cả danh mục/header ZIP. Không tải archive 4,54 GB. Container báo 25 FPS nhưng **chưa xác minh capture FPS**, không dùng để kết luận vận tốc/giây nguồn. Việc thêm CCTV ngày/đêm tăng độ phủ âm, chưa tạo được cặp camera dương/âm cùng miền hoàn toàn hoặc giải quyết shortcut theo dataset/watermark.

## Mở file nào để hiểu?

1. [So cảnh đầu/giữa/cuối 10 nguồn](../outputs/audits/pilot_groups/scene_overview.jpg).
2. [T-T_crash_2: ảnh sạch bên trái, bbox tác giả bên phải](../outputs/audits/sttad_public_5/author_region_examples.jpg).
3. [Pool CSV](../data/processed/b0_public_pilot_v1/index.csv) và [report](../data/processed/b0_public_pilot_v1/report.json).

Trong CSV:

- `label_origin` tách `author_sttad_region`, `user_full_sequence_review`, `author_normal_folder_clip_label`.
- `asset_kind=image`: ảnh thật với số frame từ tên nguồn. `asset_kind=video_frame_reference`: đường dẫn video cộng `source_frame` decode **0-based**, chưa có JPG riêng. Không đưa đường dẫn MP4 vào dataloader ảnh như thể đó là JPG.
- `converted_label` chỉ có ở ảnh dương, trỏ tới TXT YOLO đã kiểm; nhãn âm có bbox_count=0 theo căn cứ nguồn, **chưa tạo empty TXT**.
- `leakage_group` dùng khi chia tập về sau. `split=unassigned`, `training_release_allowed=False`.

## Công cụ và cách chạy lại

```powershell
# Tải chọn lọc bốn STTAD nếu máy mới; máy hiện tại đã có, chỉ dùng --offline
.\.venv\Scripts\python.exe -X utf8 -B scripts/audit_sttad_public.py --fetch-selected --max-mib 96
.\.venv\Scripts\python.exe -X utf8 -B scripts/audit_sttad_public.py --offline

# Hai member normal, không tải toàn ZIP
.\.venv\Scripts\python.exe -X utf8 -B scripts/inspect_public_zip.py --max-mib 8 --fetch-members TAD-benchmark/train/normal/20230818_acci-bg_83.mp4 TAD-benchmark/train/normal/20220518_acci-bg34.mp4

# Dùng đường dẫn report STTAD thực tế vừa in; ở máy này là _6
.\.venv\Scripts\python.exe -X utf8 -B scripts/audit_pilot_groups.py --sttad-report outputs/audits/sttad_public_6/report.json

# Chỉ chạy khi muốn tạo phiên bản pool mới; không ghi đè output đã có
.\.venv\Scripts\python.exe -X utf8 -B scripts/prepare_b0_pilot_index.py --sttad-report outputs/audits/sttad_public_6/report.json --output data/processed/b0_public_pilot_v2
```

Audit mới có hậu tố khác. Phần `groups` tạo cặp gợi ý bằng hash, còn quyết định gom cảnh được giữ trong phiếu kiểm đã có; không tự đổi review/split theo ngưỡng hash. `prepare_b0_pilot_index.py` kiểm lại hash ảnh dương/DETRAC và SHA/CRC video TAD, join đúng path/frame, không tạo nhãn từ file thiếu.

## Mức sẵn sàng và bước tiếp theo

Công cụ kiểm/chuyển nhãn/nhóm/pool đã chạy được. Tính đến 25/10, có 35 frame dương thuộc tám nhóm nguồn có vùng (bốn STTAD + bốn ACCIDENT), độ phủ vẫn thưa; dữ liệu dương/âm còn tương quan với dataset gốc và chưa có split nguồn/camera độc lập đủ căn cứ. FPS nguồn chưa rõ không cản chuẩn hóa B0 ảnh, nhưng cản đánh giá theo giây nguồn. Riêng PTS file ACCIDENT đã đối chiếu, không đồng nghĩa FPS ghi hình gốc được xác minh.

Bước tiếp theo của AI: chọn tiếp member nhỏ trong metadata ACCIDENT public đã xác minh, lọc phạm vi vùng và nhóm như sáu mẫu vừa làm; bổ sung nguồn âm cùng miền có căn cứ, kiểm hard negatives và source bias trước khi chốt split. Không tải cả gói lớn hoặc lấy frame chưa nhãn làm âm. Không cần người dùng xác nhận lại CADP/DETRAC, xin tác giả hoặc chờ giảng viên. [Readiness hiện tại](../data/b0_readiness.json), [reference](../reference/2026-10-24-public-data-review.md).

Để lấy mẫu khác mà không sửa source, công cụ ACCIDENT có `--members real_videos/<tên-gốc>.mp4 ...`; chỉ chấp nhận member trong CSV và trang danh mục đã kiểm, áp cùng trần `--max-mib` và cần output mới. Bbox mới vẫn phải qua kiểm PTS/phạm vi và phiếu rà trước khi join pool; tham số tải không tự cấp trạng thái nhãn hợp lệ.


## Export YOLO — trạng thái lịch sử trước release pilot

`prepare_b0_pilot_index.py --pool-index <index.csv> --export-split <split.csv> --output <thư-mục-mới>` nhận split đã chốt, không tự chia tập. CSV split có bốn cột `source_dataset,source_sequence,source_frame,split`; split thuộc `train/val/test`. Có thể chọn một subset pool nhưng mỗi tập phải có cả dương và âm. Mọi frame của cùng chuỗi/nhóm chống leakage phải ở cùng tập; tên ảnh xuất là hash identity để tránh trùng tên giữa nguồn.

Ở mốc trước pilot, gate benchmark còn đóng: readiness cần `can_train=true`, `split_created=true`, policy cần `training_release_allowed=true` **sau khi điều kiện dữ liệu đầy đủ đạt**. Bản release ghi `export_pool_sha256`, `export_split_sha256`, `export_policy_sha256` và bảng `export_asset_sha256` của media/TXT/evidence được chọn. Vòng sau đã khóa các hash và mở gate **pilot** riêng, như mục đầu file; gate benchmark vẫn đóng.

Khi gate hợp lệ, exporter decode tuần tự các video reference, xuất PNG sạch vào `images/<split>/`, TXT vào `labels/<split>/`, giữ bbox accident và chỉ tạo TXT rỗng cho âm có căn cứ. Có `provenance.csv` và report/hash; `dataset.yaml` chỉ được ghi sau khi hoàn tất. Lỗi decode để lại `failure.json` và không phát hành YAML. Output tồn tại bị từ chối ghi đè.

Đã kiểm fixture sáu mẫu (ba dương/ba âm, có một frame lấy từ video) qua toàn bộ export, đọc lại pixel/nhãn/provenance. Kiểm trường hợp gate đóng, media đổi hash, nhóm lọt hai split, thiếu class và ảnh không decode. Fixture nằm tạm trong `.tmp/` và được dọn đúng thư mục thử; không tính thành dữ liệu/thí nghiệm đồ án. Toàn suite cuối lượt: **33 test đạt**. Thử trên pool thật bị chặn đúng readiness/policy trước khi ghi thư mục; không có split hoặc dataset thật mới.

### Đối chiếu run LR 0,001 đủ 60 epoch (27/10/2026)

[Run mới](../outputs/training/b0_verified_lr001_full60_v1/experiment.json) đã train đủ 60 epoch từ pretrained trên cùng release 1.750 ảnh; đây không phải resume từ epoch 48. Train box loss epoch 50→60 giảm **0,8480→0,76241**, cls loss **0,7412→0,58679**. Val mAP50–95 CSV tốt nhất **0,49563 ở epoch 47**, cao nhất từ 50–60 **0,49229**. Đánh giá lại `best.pt`: full60 **0,49412**, run LR 0,001 dừng 48 epoch **0,50643**, run LR 0,01 **0,46033** trên cùng 97 ảnh val. Ở confidence 0,25/IoU 0,5: full60 **56 TP/65 FP/35 FN**; run 48 epoch **60/49/31**. [Snapshot đối chiếu](evidence/2026-10-27-b0-full60-validation.json). Không dùng lại test/probe cũ để chọn model, chưa có căn cứ đổi checkpoint hiện hành hay kết luận tổng quát.

## Chẩn đoán lỗi ảnh và video B0 — 27/10/2026

**Phần này đã thực hiện xong:** phân tích prediction đã lưu của checkpoint B0 mốc, chạy cùng checkpoint/ngưỡng trên chín chuỗi sạch, ghi từng frame và đọc lại toàn bộ MP4 đầu ra. Mở `outputs/training/b0_verified_pilot_v1/diagnostics/index.html` bằng trình duyệt để xem bảng, ảnh lỗi, video và log cùng một chỗ. Kết quả tập trung trong thư mục run hiện hành, không tạo thêm hệ thống dataset hay thay release đã train. Không tải thêm dữ liệu và không train trong lượt này.

### Công cụ và tính tái lập

`scripts/analyze_b0.py` nhận `configs/b0_diagnostics_v1.json`. Trước khi suy luận, script kiểm checkpoint/config/release và hash các nguồn review/ảnh/video; chỉ nhận normal theo nhãn tác giả hoặc full-sequence review khớp hash. CADP nhận ảnh JPEG sạch gốc, kiểm đủ 221 hash từ index đã đối chiếu và giữ frame 0–220. `src/b0_diagnostics.py` xử lý thống kê hình học và đoạn frame liên tiếp. Vòng video đọc tuần tự một frame, dự đoán bbox class accident tại confidence **0,25**, NMS IoU **0,7**, ảnh **640**, max_det **100**, ghi JSONL/CSV và H.264. Đây là đúng tham số suy luận ảnh đã dùng; không tìm threshold theo video test. Tất cả MP4 đầu ra đã được giải mã lại đủ frame.

Lệnh kiểm: `python scripts/analyze_b0.py --check`; lệnh xử lý: `python scripts/analyze_b0.py --run` trong `.venv`. Lần xử lý đã chạy xong; gọi `--run` lần nữa trên cùng output sẽ bị từ chối để bảo toàn bằng chứng. Muốn tái chạy phải dùng config/output mới. `predictions.jsonl` giữ bbox/confidence và chỉ số frame, `frames.csv` giữ số hộp/score cao nhất/độ trễ mỗi frame, `report.json` giữ các đoạn liên tiếp và phạm vi nhãn. DETRAC có `original_source_frame = source_frame + 1`; CADP giữ chỉ số gốc 0-based. Cả frame không có bbox cũng có dòng log, không bỏ frame.

### Lỗi trên ảnh đã đo

Trên 112 ảnh test đã sử dụng: **67 TP, 46 FP, 40 FN** đúng với báo cáo trước. Trong 46 FP theo phép ghép với vùng tham chiếu tác giả: **38** có IoU tối đa <0,1 với mọi GT, **5** có IoU 0,1–<0,5, **3** trùng/xung đột với GT đã ghép. Đây là phân loại hình học, không tự kết luận nội dung của mọi hộp chưa khớp là không tai nạn; annotation impact không mô tả đầy đủ mọi đối tượng khác trong cảnh.

Diện tích GT trung vị ở 40 FN là **0,321% ảnh**, còn 67 TP là **3,216% ảnh**. Các vùng nhỏ/xa là một lỗi cần xử lý có bằng chứng; chưa chứng minh riêng độ phân giải hoặc thiếu dữ liệu là nguyên nhân. Đã xem contact sheet: nhiều FN ở vùng xe nhỏ trên cao tốc, còn sample FP normal phủ xe tải, cụm xe hoặc đèn xe bình thường. Phần review bằng mắt của AI là nhận xét theo mẫu, không đổi nhãn tác giả và không là xác nhận mới của người dùng. CSV/JSON giữ toàn bộ 309 ảnh (112 test + 100 normal sparse + 97 val); contact sheet chỉ chọn tối đa 12 case theo quy tắc ghi trong trang.

### Video sạch đã chạy

| Chuỗi | Frame đọc đủ | Frame có bbox accident | Đoạn frame liên tiếp có bbox |
| --- | ---: | ---: | ---: |
| MVI_20011 | 664 | 0 | 0 |
| MVI_20012 | 936 | 0 | 0 |
| MVI_20032 | 437 | 0 | 0 |
| TAD F10 | 249 | 3 | 2 |
| TAD F11 | 275 | 98 | 24 |
| TAD F3 | 249 | 94 | 10 |
| TAD F4 | 299 | 140 | 40 |
| TAD F9 | 527 | 477 | 9 |
| CADP 001407 | 221 | 158 | 7 |

Tổng **3.857 frame / 9 chuỗi**, không coi là chín camera hay chín sự kiện độc lập. Ba DETRAC là nguồn đã dùng train, chỉ chứng minh kiểm vận hành trên các video đó. Năm TAD là normal do tác giả gắn nhãn, probe đã xem: **812/1.599 frame (50,78%)**, 864 bbox, 85 đoạn thô, 5/5 clip có dự đoán. F9 có một đoạn sai liên tục **215 frame**; đây không chỉ là chớp tắt một vài frame. Chưa có phép đo cho thấy B1 sẽ sửa được lỗi kéo dài này.

CADP có bất kỳ bbox ở **35/35 frame 96–130**, và ảnh mẫu frame 110 cho thấy bbox phủ tương tác bus/car. Đây chỉ là chẩn đoán hiện diện theo thời gian: chưa có GT vùng accident cùng định nghĩa để đo spatial recall, chưa có event matching để gọi là phát hiện đúng sự kiện. Các frame ngoài 96–130 vẫn là unknown, không tính negative/FP theo frame. Dự đoán đã xuất hiện từ frame 4 và cả trước/sau khoảng Colliding, nên không gọi offset trong interval là độ trễ cảnh báo bằng 0. MP4 trình chiếu CADP 20 FPS không là FPS camera; không báo onset/end/độ trễ theo giây nguồn.

PTS container được ghi riêng cho video, source timestamp chỉ điền với DETRAC có FPS corpus đã xác minh. Đo tốc độ offline có cả đọc frame, predict, vẽ, mã hóa và chờ encoder hoàn tất; không bao gồm nạp model, warmup, hashing hay đọc lại đầu ra. Trong lượt này khoảng **47–94 frame/s** (CADP khoảng 51), không suy ra hệ thống streaming hoàn chỉnh real-time hoặc false alerts/giờ. Đoạn liên tiếp có bbox là log B0 thô, không phải alert đã xác nhận hay bộ lọc B1.

### Quyết định sau khi xem lỗi

Giữ checkpoint mốc đã đo test, không đổi model/ngưỡng từ kết quả test đã xem. Trước lần train dữ liệu mới, ưu tiên video **normal tác giả từ train/normal còn chưa dùng**, đa dạng cảnh xe tải, đường ướt/đèn, đường hầm và cụm xe; chia theo nguồn/cảnh, dành validation/test mới trước khi xem prediction. Năm clip test normal đã đo không chuyển sang train. Rà nhãn và kích thước vùng dương nhỏ hiện có trước khi quyết định một thử nghiệm độ phân giải riêng trên validation. B1 có thể bắt đầu từ log binary confidence 0,25, nhưng cần protocol/split video phù hợp và không kỳ vọng lọc thời gian tự xóa mọi FP kéo dài. B0 chẩn đoán ảnh/video đã xong; benchmark sự kiện và RQ1/RQ2 chưa xong.

[Snapshot nhỏ có hash](evidence/2026-10-27-b0-diagnostics.json), [config](../configs/b0_diagnostics_v1.json), [trang xem cục bộ](../outputs/training/b0_verified_pilot_v1/diagnostics/index.html).

## B0 normal mở rộng — 28/10/2026

**Trạng thái chuẩn bị ban đầu (trước run): đã hoàn thành dữ liệu. Cập nhật sau run: đã train đủ 60 epoch và đánh giá val, xem mục kết quả cuối file.** Mở `outputs/audits/b0_normal_expansion_v1/index.html` bằng trình duyệt: trang có nguồn từng clip, ba mốc cảnh, crop GT nhỏ, split và kết quả ba checkpoint cũ trên validation mới. Dữ liệu lớn và đầu ra tiếp tục ở bố cục cũ; chỉ mở rộng công cụ có sẵn, không thêm hệ thống thư mục hay file tiến độ riêng theo baseline.

### Đã tải và kiểm gì?

Từ [TAD tác giả](https://github.com/UnicomAI/UnicomBenchmark/tree/main/TADBench), đã kiểm lại central directory của ZIP 4.543.580.572 byte bằng HTTP Range. Thấy 111 MP4 trong `train/normal`; chọn 18 clip chưa dùng với trần mạng 256 MiB, cân ba họ tên ngày 5/5/8 để lấy ứng viên. Đây là quy tắc giới hạn dung lượng của đồ án, không phải khuyến nghị số lượng mẫu từ paper hay chứng minh đa dạng camera. Danh sách chính xác, size và CRC nằm trong [plan tải](../configs/b0_normal_expansion_v1.json). Raw giữ nguyên member tại `data_raw/tad/public_selected/TAD-benchmark/train/normal/`.

Đã tải khoảng **122,75 MiB raw**, dùng **126.299.496 byte mạng** cho lượt tải chọn lọc. Cả 18 clip đạt CRC/size/SHA, đọc đủ **5.650 frame**, kích thước không đổi, không có clip bị reject. Lấy **30 frame đều/clip = 540 PNG sạch** trước khi xem prediction. Nhãn âm là normal cấp clip tác giả, không phải xác nhận mới của người dùng. FPS container lưu để truy nguyên, không xác nhận FPS ghi hình hoặc suy onset/end theo giây.

### Cảnh, nhãn và chia tập

Đã xem ảnh đầu/giữa/cuối của cả 18 clip, ba trang cặp gần nhất với dữ liệu cũ/probe, và kiểm fingerprint của 540 ảnh mới với 1.750 ảnh dataset cũ cùng 100 ảnh probe đã xem. Không có pixel trùng khác chuỗi và không có candidate theo bộ ngưỡng pHash/crop/dHash đã ghi; kiểm cuối trên dataset xuất cộng reserve **2.290 ảnh** cũng không có candidate xuyên split ở ngưỡng pHash≤5/dHash≤8. Các điều này không chứng minh camera độc lập hoàn toàn. [Phiếu review và assignment](../data/reviews/2026-10-28-b0-normal-expansion-review.json) ghi nhóm cảnh tạm, khóa **trước prediction**: 10 nhóm train, 4 nhóm validation, 4 nhóm giữ riêng. Các cảnh gồm xe tải, hàng xe chậm, đèn chói ban đêm, đơn sắc, đường mờ, cầu/portal; chưa tuyên bố đã phủ đủ lỗi bên trong đường hầm.

| Phần | Dương | Âm | Tổng |
| --- | ---: | ---: | ---: |
| Train mới | 1.122 | 719 | **1.841** |
| Validation mới | 91 | 126 | **217** |
| Test cũ đã tiêu thụ, giữ nguyên để truy nguồn | 107 | 5 | **112** |
| Giữ riêng ngoài dataset | 0 | 120 | **120** |

Dataset có **2.170 ảnh = 1.320 dương + 850 âm**, thêm 300 normal vào train và 120 vào val. Holdout âm 120 frame/4 nhóm không vào train/val và chưa chạy model; nó chỉ là holdout **âm**, chưa phải benchmark dương/âm mới. Test 112 ảnh và năm clip TAD test/normal đã đo trước đó không được chuyển sang train. Toàn bộ **1.750 ảnh/nhãn/split cũ đều giữ nguyên hash và assignment**. Split tùy biến của đồ án không phải split benchmark chính thức TAD.

Đã kiểm đủ 1.320 bbox impact cũ: class, giá trị hữu hạn, biên tọa độ, kích thước, link ảnh/frame và hash đều đạt. Có **152 bbox** cạnh ngắn sau resize640 dưới 16 pixel, trong đó **18** dưới 8 pixel (15 train, 2 val, 1 test). Đã nhìn 15 crop GT train dưới 8 pixel bằng phóng nearest-neighbor: nhiều vùng chỉ có ít pixel và mờ, chưa đủ căn cứ bác nhãn tác giả. Giữ nguyên nhãn, không tạo crop thành mẫu train độc lập và không loại tự động vì nhỏ. Cờ khó và crop kiểm nằm trong audit, không là nhãn dương mới.

### Mốc trước train trên cùng validation mới

Đã chạy ba checkpoint cũ trên đúng 217 ảnh val, không chạy test cũ hoặc holdout mới. Ngưỡng TP/FP/FN dưới đây là confidence 0,25 và IoU ghép 0,5; mAP quét ngưỡng riêng theo Ultralytics.

| Checkpoint cũ | mAP50–95 val mới | TP/FP/FN | Frame âm có bbox /126 | F1 tại ngưỡng cố định |
| --- | ---: | --- | ---: | ---: |
| LR 0,01 mốc | 0,43480 | 52/83/39 | 36/126 | 0,46018 |
| LR 0,001 dừng 48 | 0,47000 | 60/88/31 | 38/126 | 0,50209 |
| LR 0,001 đủ 60 | 0,46194 | 56/95/35 | 29/126 | 0,46281 |

Đây là mốc đánh giá **model cũ trên tập val lớn hơn**, chưa phải kết quả train dataset mới. Không so trực tiếp với mAP trên 97 ảnh val cũ để nói model đã tốt lên/xấu đi. Positive val vẫn là nhóm đã được xem; 120 normal val mới chỉ từ bốn cảnh, nên không suy hiệu năng tổng quát từ tỷ lệ frame. [Report mốc](../outputs/audits/b0_normal_expansion_v1/reference_val/report.json).

### Chạy train tiếp như thế nào?

[Config mới](../configs/b0_normal_expanded_v1.json) giữ recipe run LR 0,001 đủ 60: YOLOv8n COCO pretrained gốc, SGD, `lr0=0.001`, batch 8, ảnh 640, workers 0, seed 20261026, không AMP, 60 epoch và `patience=0`. Thay dữ liệu normal là thay đổi chính của thí nghiệm này. Bắt đầu từ pretrained gốc để so với mốc cùng recipe, không warm-start từ best.pt cũ; chưa đổi model hoặc độ phân giải. Gate `normal_expanded_pilot_release.can_train=true` đã khóa metadata/hash/policy và exporter đã tạo YAML hoàn tất. `can_train=false` ở gốc readiness vẫn nói về benchmark đầy đủ, không chặn pilot đã cấp riêng.

Mở PowerShell ở gốc project:

```powershell
.\.venv\Scripts\python.exe -X utf8 -B scripts/train_b0.py --config configs/b0_normal_expanded_v1.json --check
.\.venv\Scripts\python.exe -X utf8 -B scripts/train_b0.py --config configs/b0_normal_expanded_v1.json --train
```

Tại mốc chuẩn bị đã chạy `--check` đạt **2.170 ảnh**, chưa chạy `--train`. Sau đó run đã hoàn tất tại `outputs/training/b0_normal_expanded_v1/`; số liệu được bổ sung ở cuối file. Đoạn hướng dẫn sau giữ để tái lập: Khi train, kết quả sẽ vào đường dẫn đó; chỉ đánh giá val sau train. So model mới với bảng mốc trên cùng 217 ảnh, xem cả mAP, P/R/F1, FP/FN và frame normal có bbox. Không mở holdout để chọn tham số. Nếu bị ngắt giữa chừng còn checkpoint optimizer, dùng cùng config với `--resume --resume-workers 0`. Khi hoàn tất, best.pt là checkpoint theo val tốt nhất, last.pt là epoch cuối.

### Công cụ và kiểm tra

Đã mở rộng các script hiện có: `inspect_public_zip.py --fetch-plan/--prepare-normal-batch`; `audit_pilot_groups.py --normal-batch/--split-report`; `prepare_b0_scaled_release.py --normal-expansion-review`; `analyze_b0.py --validation-reference`. `train_b0.py` và exporter nhận release key mới và vẫn kiểm nguồn nhãn verified. Không cần chỉnh lại code cho lần train này, dùng đúng config mới.

**52 unit test đạt**, bao gồm giữ split cũ, không đưa reserve vào train, chặn một cảnh qua hai tập, thiếu review, source frame trùng và nguồn âm chưa được xác minh. CLI/import/cú pháp đạt; nguồn thật đã CRC/decode đầy đủ; PNG/label/hash/split đã kiểm qua exporter và train `--check`. Manifest có 62 asset, đã sao lưu trước khi thêm 18 raw clip; catalog tải cập nhật nguồn/hash. [Snapshot nhỏ trên Git](evidence/2026-10-28-b0-normal-expansion.json), [nhật ký ngày](../progress/2026-10-28.md). Benchmark sự kiện B0/B1 và RQ1/RQ2 vẫn chưa hoàn thành.

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

## Chuẩn bị B0 s960 — 28/10/2026

**Mốc lịch sử trước train:** đã chuẩn bị/kiểm và dừng để người dùng tự chạy. **Hiện run đã hoàn tất**, xem phần kết quả cuối file; các lệnh chuẩn bị dưới đây chỉ để tái lập với run mới, không chạy lại vào output đã có. [Đối chiếu paper/metric/nguồn public](../reference/LITERATURE_REVIEW.md#9-đọc-lại-kết-quả-và-chuẩn-bị-b0-s960--28102026), [config](../configs/b0_s960_v1.json), [snapshot](evidence/2026-10-28-b0-s960-preparation.json).

### Vì sao chọn công thức này?

Phân tích đủ217 case val đã lưu, không đo lại test/reserve:

| Cạnh ngắn GT sau resize640 | Đúng TP | Bỏ sót FN |
| --- | --- | --- |
| <16px | 2 | 10 |
| 16 đến <32px | 11 | 11 |
| 32 đến <64px | 21 | 11 |
| ≥64px | 20 | 5 |

21/37 FN dưới32px; median cạnh ngắn TP52,99px, FN23,64px. Trong35 FP có24 hộp rời vùng được gán nhãn,4 hộp IoU từ0,1 đến<0,5,1 hộp trùng/xung đột và6 hộp trên ảnh âm. Phân loại này là **hình học so với annotation**, không tự xác nhận mọi hộp ngoài vùng GT là xe bình thường hoặc biết đủ mọi sự kiện trong ảnh. Đã xem hai contact sheet FP/FN: nhiều FN là vùng xa camera; các case lớn/đêm vẫn cần xem sau train. Không loại case khó hay sửa nhãn theo dự đoán để tăng điểm.

Recipe mới: **YOLOv8s COCO pretrained → fine-tune một class accident**, ảnh960 thay640 để giảm mất chi tiết, mosaic0,5/scale0,3 thay1,0/0,5. Batch2/workers0/FP32 cho laptop4GB, nbs64; SGD0,001/momentum0,937 giữ lại. Chạy100epoch,patience0; best vẫn chọn theo fitness mAP50–95 của bản8.4.178. Đây là thử công thức gộp model/resolution/augmentation/horizon; nếu tăng điểm chưa thể nói riêng yếu tố nào tạo cải thiện. Chưa đổi loss/head riêng, chưa dùng GRU/STFN/VLM.

### Dữ liệu dùng và mục tiêu kiểm chứng

Giữ nguyên dataset `data/processed/b0_normal_expanded_v1/dataset/dataset.yaml`:

- Train1.841: **1.122 impact ACCIDENT**, 400normal TAD,300DETRAC,19âm trước impact đã rà. Có1.085 nhóm nguồn dương, không phải1.122 camera độc lập.
- Val217:91impact ACCIDENT và126âm (120TAD,6ACCIDENT); 90nhóm dương,94nhóm tổng. Giữ cách nhóm bảo thủ và hạn chế độc lập camera như release cũ.
- Test cũ112ảnh tiếp tục ngoài chọn tham số; reserve âm120frame ngoài YAML không suy luận. Không tăng dữ liệu bằng copy/crop/oversample, không coi thiếu TXT là âm.

Dữ liệu này phù hợp để kiểm công thức B0 pilot trên **cùng validation**. Chưa đủ để hứa tổng quát hóa, đánh giá event, hoặc xác nhận70% trên test độc lập. Lượt này không cần tải thêm dataset: nguồn công khai có nhãn đang dùng đã có1.320impact; TAT/fullSTTAD chưa lấy được bản đầy đủ tương ứng, không dùng nhãn không kiểm được để thay thế.

Mục tiêu chốt **mAP50 val >0,70**, không phải accuracy hay mAP50–95. Đồng thời đối chiếu mAP50–95 với0,49031, F1 với0,60, recall với0,5934 và6/126ảnh âm báo nhầm tại ngưỡng0,25/IoU0,5. Đạt mAP50 mà recall/F1 giảm thì phải báo trade-off, không tự công nhận toàn bộ tốt hơn. Không giảm IoU hoặc bỏ ảnh khó để đạt70%; model mới chưa có số đo.

### Đã kiểm và bạn chạy thế nào?

- `train_b0.py --preflight`: đọc đủ2.058ảnh train/val, kiểm1.213bbox, dựng head một class và forward2×3×960×960 trên RTX3050Ti. Không optimizer,backward,train hoặc lưu checkpoint mới. Peak tensor allocated khoảng268MiB/reserved330MiB **chỉ cho forward**, không bảo đảm RAM/VRAM train.
- `yolov8s.pt` ở thư mục gốc,22.588.772byte; khớp SHA công bố trong GitHub releasev8.4.0. Đây là checkpoint COCO, chưa phải detector accident mới. Không sửa/yêu cầu tải lại yolov8n.pt.
- 55unit test đạt; `--help`, import/cú pháp, kiểm hash/split và tương thích config/API đã kiểm. Mọi đầu ra chuẩn bị gom tại `outputs/training/b0_normal_expanded_v1/diagnostics/`; thư mục run mới chưa tạo.

Trong terminal VS Code, tại thư mục gốc:

```powershell
# Có thể kiểm lại file/hash mà không train
.\.venv\Scripts\python.exe -X utf8 -B scripts/train_b0.py --config configs/b0_s960_v1.json --check

# Chỉ bạn thực hiện lệnh này để bắt đầu run mới
.\.venv\Scripts\python.exe -X utf8 -B scripts/train_b0.py --config configs/b0_s960_v1.json --train
```

Đây là run mới từ COCO, **không resume** model n cũ sang s. Kết quả sau train sẽ ở `outputs/training/b0_s960_v1/`; `weights/best.pt` là checkpoint chọn bằng val, `last.pt` là epoch cuối. Validation và cases chỉ dùngval, không tự mở test/reserve. Độ phân giải/model lớn hơn có thể chậm đáng kể; chưa đo tốc độ train. Nếu bị ngắt giữa chừng và còn optimizer, dùng cùng config với `--resume --resume-workers 0`. Nếu OOM, giữ traceback/run dở để chọn cấu hình phần cứng có phiên bản; không tự thay file config đã khởi chạy. Giữ terminal/máy chạy, không sleep; đóng chat không làm lệnh terminal của bạn tự dừng.

Mở xem trước: `outputs/training/b0_normal_expanded_v1/diagnostics/image_errors/false_negatives.jpg`, `false_positives.jpg`, `report.json` và `diagnostics/s960_preflight.json`. Ảnh minh họa lấy từ prediction đã đo, không phải kết quả model s960.

**Cập nhật khi người dùng đã bắt đầu train:** đã quan sát run s960 hoàn thành ít nhất9 epoch; yêu cầu mới là bật early stopping thay vì chạy bắt buộc100. Đã chuẩn bị `--resume-patience 15` và kiểm wrapper, **chưa áp dụng vào tiến trình đang sống**. [Thao tác dừng/resume và cơ chế lưu lịch sử](../outputs/training/README.md#bật-early-stopping-khi-s960-đang-chạy--cập-nhật-sau-khi-người-dùng-bắt-đầu-train). Giữ config gốc/hash/split và lịch LR; thay chính sách dừng được ghi riêng khi người dùng resume. Không tự dừng hoặc chạy train thay người dùng.

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

**Đã hoàn thành bước chọn điểm vận hành và một lần đo holdout âm, không train thêm.** [Trang tổng hợp tại máy có output](../outputs/training/b0_s960_v1/operating_point_v1/index.html), [khóa sử dụng](../configs/b0_s960_v1_operating_point_v1.json), [snapshot nhỏ](evidence/2026-10-29-b0-operating-point.json). Tất cả kết quả gom trong run s960 hiện có, không copy dataset.

Đã đọc workbook09/11/15 và [căn cứ phương pháp](../reference/LITERATURE_REVIEW.md#10-chọn-điểm-vận-hành-và-đo-holdout-âm--29102026). Quy tắc ghi trước khi quét: **recall val≥70%, tối đa F1**, tie ít ảnh âm có hộp, precision cao, ngưỡng cao. Cache hai checkpoint trên đúng217ảnh val tại confidence0,01; quét91ngưỡng0,05–0,95, giữ IoU ghép0,5/NMS0,7/max_det100. Kết quả ở0,25 khớp chính xác các tổng đã báo cáo, train/test/split/nhãn không đổi.

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

Mở `index.html`, `validation_curves.png`, `s960_thresholds.csv`, `n640_thresholds.csv`, `holdout_false_positives.jpg`, `holdout_cases.csv` và `holdout_report.json` trong thư mục kết quả.61unit test đạt ở bước chọn ngưỡng; --help/import/cú pháp, hash, tổng case và liên kết HTML đạt; lệnh đo holdout lần hai bị chặn trước nạp model. Bước này không tải dataset hoặc train. Các phần sau ghi kết quả công việc tiếp theo, không sửa phép đo lịch sử.

## Đo B0/B1 trên video sạch — 29/10/2026

“Đo” ở đây là chạy **cùng checkpoint, cùng thứ tự frame** rồi đếm tín hiệu của B0 và bộ lọc, không cập nhật trọng số. Config [b1_causal_diagnostics_v1](../configs/b1_causal_diagnostics_v1.json) khóa trước khi chạy: B0s960/conf0,27, score cảnh là confidence accident lớn nhất sau NMS; score dưới0,01 không có trong cache và coi bằng0. B1 gồm3-of-5, đợi đủ5frame; hoặc EMAalpha0,3, khởi tạo0. Reset khi đổi video/mất frame, không đọc frame tương lai. Đây là lựa chọn chẩn đoán của đồ án, không phải tham số tối ưu từ paper. [Nguồn và đối chiếu](../reference/LITERATURE_REVIEW.md#11-đo-b1-và-chuẩn-bị-dữ-liệu-âm-khó-trước-train--29102026).

Đã xử lý **12chuỗi/4.845frame**, xuất12MP4 và đọc lại đủ, không mất frame. Kết quả trong `outputs/training/b0_s960_v1/temporal_diagnostics_v1/`; mở `index.html`, `report.json`, hoặc `videos/<chuỗi>/frames.csv` và `b0_accident.mp4`. Video vẽ bbox B0 cùng trạng thái từng bộ lọc; EMA/k-of-N là trạng thái cảnh, không có bbox riêng.

| Phạm vi nguồn normal | Frame | B0: frame ON / đoạn ON | 3-of-5 | EMA |
| --- | ---: | ---: | ---: | ---: |
| 4clip validation normal | 1.296 | 99 /31 | 92 /11 | 90 /13 |
| 4clip holdout **đã mở trước**, chẩn đoán hậu nghiệm | 1.291 | 300 /40 | 293 /17 | 302 /16 |
| 3DETRAC từng dùng train, kiểm vận hành | 2.037 | 0 /0 | 0 /0 | 0 /0 |

ON frame là frame bộ lọc bật; ON bout là đoạn bật liên tục, **chưa phải cảnh báo sự kiện**. Không so tổng các nhóm thành một test độc lập. Không chọn lại alpha/k/conf theo bốn holdout đã consumed. Khoảng CADP221frame còn lại chỉ dùng chẩn đoán: cả ba có35/35frame ON trong khoảng96–130, nhưng **đều đã ON trước96**; ngoài khoảng là unknown, không tính FP hoặc event recall. FPS nguồn CADP chưa xác minh,20FPS chỉ phục vụ trình chiếu, không xuất delay giây.

Tốc độ offline toàn lượt đọc→suy luận→vẽ→mã hóa khoảng33,60frame/giây, loại trừ nạp model, warm-up, hash và đọc lại đầu ra; không phải chứng minh real-time. Report giữ thời gian suy luận median/p95 và peak VRAM theo clip. Đây là chẩn đoán B1 đã chạy; benchmark sự kiện và RQ1/RQ2 vẫn chưa hoàn thành.

## Chuẩn bị s960 hardneg v1 — 29/10/2026

**Chỉ chuẩn bị trước train; người dùng tự chạy.** Giữ cùng YOLOv8s960 và nhãn bbox impact; không tạo bbox mới, không lấy dự đoán làm nhãn, không đưa CADP envelope vào GT. [SSD mục2.2](https://arxiv.org/html/1512.02325v5) mining negative anchors bằng loss trong train; đây chỉ là cách **điều chỉnh ý tưởng chọn frame offline**, không thay loss YOLO hay nhận là tái lập SSD. Nguồn nhãn normal là [TAD tác giả](https://github.com/UnicomAI/UnicomBenchmark/tree/main/TADBench); [Ultralytics fine-tuning](https://docs.ultralytics.com/guides/finetuning-guide/) làm căn cứ warm-start với LR nhỏ hơn, đối chiếu bản cài8.4.178.

**Dữ liệu đã tải/xuất:**24MP4 mới,259,67MiB raw,8.992frame giải mã đủ. Chỉ đọc các ZIP range, không tải toàn4,54GB. Giữ đường dẫn `data_raw/tad/public_selected/TAD-benchmark/train/normal/`. Audit gom **một thư mục** `outputs/audits/b0_hard_negative_sources_v1/`: receipt/ledger,1.440PNG ứng viên, cảnh đầu/giữa/cuối, nearest-base, phiếu nhóm trước mining, scores, selected manifest, dataset checks và trang HTML. Ngân sách384MiB, ledger bảo thủ290,75MiB tính cả dự phòng lỗi trước khi có ledger; không gọi số này là bytes thực nhận chính xác. ZIP gốc không tải nguyên, dữ liệu cũ giữ nguyên.

Rà14train/3val/4reserve/3exclude **trước prediction**. Hai clip`_1`/`_119` cùng cảnh trạm thu phí nên cùng nhóm reserve; hai cảnh núi`_99`/`_103` cùng nhóm reserve bảo thủ. `_7` và`_47` có thể liên quan val cũ nên giữ cùng nhóm val tương ứng, chưa nhận là cùng camera chắc chắn. `_107`/`_15`/`_59` có thể liên quan holdout/probe đã xem nên loại khỏi release. Không dùng “hash khác” làm chứng minh độc lập camera. [Review và các lý do](../data/reviews/2026-10-29-b0-hard-negative-review.json); bản khóa trước mining và SHA ở audit.

Model cũ chỉ suy luận **840ứng viên train**. Mỗi clip lấy20frame đều +10frame score cao từ10bin thời gian, tổng420frame train mới; val90 và reserve120 lấy đều, không chọn bằng score. Có90/840ứng viên vượtconf0,27;30/140frame chọn theo xếp hạng vượt ngưỡng đó. Vì vậy “ranked hard” là mức khó tương đối trong clip, không có nghĩa140frame đều bị dự đoán nhầm. Nhãn âm đến từ tác giả normal; người dùng chưa rà các clip mới.

| Tập trong release mới | Dương impact | Âm | Tổng |
| --- | ---: | ---: | ---: |
| Train | 1.122 | 1.139 | 2.261 |
| Validation | 91 | 216 | 307 |
| Test cũ đã tiêu thụ, chỉ giữ truy nguồn | 107 | 5 | 112 |
| **Tổng dataset** | **1.320** | **1.360** | **2.680** |

Thêm510ảnh vào dataset cũ2.170, không đổi bất kỳ nhãn dương/split cũ. **2.680ảnh không phải2.680sự kiện độc lập.** Tập reserve mới120frame/4clip/2nhóm bảo thủ ở `data/registries/b0_s960_hardneg_v1_holdout.json`, ngoài datasetYAML, chưa suy luận; reserve cũ120frame đã consumed vẫn ngoài train/val. Chưa thêm sự kiện tai nạn dương hay benchmark event mới.

**Cấu hình chuẩn bị:** [b0_s960_hardneg_v1.json](../configs/b0_s960_hardneg_v1.json), [policy](../configs/b0_hard_negative_label_policy.json). Khởi tạo từ `outputs/training/b0_s960_v1/weights/best.pt` SHA`c1fdd6dc…019302`, run mới/optimizer mới, **không resume run hoàn tất**. Giữ960,batch2,FP32,workers0,SGD/momentum0,937,mosaic0,5/scale0,3; đổi LR0,001→0,0003, trần40epoch và **patience10 ngay từ đầu**. LR/trần/patience là lựa chọn giới hạn của đồ án, không số tối ưu paper. Early stopping theo fitness mAP50–95, không theo train loss. Đây là thí nghiệm gộp dữ liệu/warm-start/lịch học, không gán cải thiện cho riêng một thay đổi.

Lệnh kiểm an toàn, có thể chạy lại:

```powershell
.\.venv\Scripts\python.exe -X utf8 -B scripts/train_b0.py --config configs/b0_s960_hardneg_v1.json --check
```

Sau khi xem bằng chứng kiểm trong mục dưới, **người dùng tự chạy**:

```powershell
.\.venv\Scripts\python.exe -X utf8 -B scripts/train_b0.py --config configs/b0_s960_hardneg_v1.json --train
```

Đầu ra run mới sẽ ở `outputs/training/b0_s960_hardneg_v1/`, checkpoint trong`weights/best.pt`/`last.pt`. Thư mục run chưa được tạo trong lượt chuẩn bị. Không sửa `train_b0.py` để đổi hyperparameter; sửa config trước khi bắt đầu run mới. Nếu run đã bắt đầu thì không sửa config bị khóa hoặc chạy chồng lệnh. Mục tiêu mAP50>70% vẫn là mục tiêu chưa được đảm bảo; so model mới với mốc cũ **cùng307val**, không so trực tiếp với68,60% trên217val khác thành phần.

### Kết quả kiểm trước train

- `--check`:2.680ảnh/hash/split/nguồn hợp lệ. Giải mã và kiểm toàn bộ2.261train+307val, bbox train1.122/val91đúng class/biên; không tự coi frame thiếu nhãn là âm.
- Preflight: forward batch`[2,3,960,960]`,11.135.987tham số, peak allocated281.309.184bytes (khoảng268,28MiB). **Không tạo optimizer, không backward, không lưu checkpoint**. Đây không đảm bảo VRAM khi backward/train thật.
- Sàng lọc2.800ảnh gồm dataset+reserve: không có cặp khác split vượt đồng thời pHash≤5/dHash≤8. Đây là heuristic, không chứng minh camera độc lập. Toàn bộ2.170ảnh/nhãn/split cũ giữ nguyên, đối chiếu bằng source tuple và SHA.
- Mốc **checkpoint s960 cũ trên307val mới**: mAP50 **68,38%**, mAP50–95 **53,82%**. Tạiconf0,25/IoU0,5:64TP/43FP/27FN, P59,81%,R70,33%,F164,65%;7/216ảnh âm có hộp. Chưa có kết quả của model fine-tune mới. [Report lớn](../outputs/audits/b0_hard_negative_sources_v1/reference_val/report.json).
- Lần validation đầu trong sandbox bị WinError5khi thư viện tạo pipe Windows; chưa có metric hoặc cập nhật model ở lần đó. Đã chạy lại đúng validation ngoài sandbox, hoàn tất; không sửa nhãn/config để vượt lỗi.
-66unit test đạt, gồm chống leakage/unknown, giữ reserve ngoài train, causal/reset, không gọi temporal presence là delay, và budget tải tiếp nối;6filePython qua cú pháp/import,5CLI`--help` đạt.12MP4B1 đã đọc lại đủ4.845frame. [Snapshot nhỏ có hash/bằng chứng](evidence/2026-10-29-b0-hard-negative-preparation.json).

Mở `outputs/audits/b0_hard_negative_sources_v1/index.html`, `mined_train_examples.jpg`, `train_preflight.json`, `final_split_screen.json` và `reference_val/report.json`. Audit giữ backup manifest/catalog/readiness trước cập nhật; manifest86asset không có nghĩa86sự kiện tai nạn hay86camera. Hướng dẫn tải/phục hồi ở [GETTING_STARTED](GETTING_STARTED.md#lượt-chuẩn-bị-tiếp2910-âm-khó-và-b1-dừng-trước-train).

## Kết quả s960 hardneg hoàn tất — 29/10/2026

**Run đã hoàn tất, không chạy lại train/resume vào output này.** Người dùng chạy đúng config đã khóa: warm-start bests960,SGD0,0003,960,batch2,FP32,workers0,trần40/patience10. Dataset2.680ảnh:2.261train/307val/112test cũ; chỉ đánh giá val. Run kết thúc ởepoch15; best fitness trong CSV tạiepoch5, sau10epoch không vượt mốc đó. Đối chiếu mã8.4.178 xác nhận fitness chọn checkpoint là mAP50–95. Thời gian train và đánh giá sau train khoảng **81,34phút**, không phải thời gian suy luận.

### So checkpoint cũ và mới trên đúng307ảnh validation

Mốc cũ là `outputs/audits/b0_hard_negative_sources_v1/reference_val/report.json`, không phải bảng217val ở ngày28/10. Cùng provenance/SHA/GT,960,confidence0,25/IoU ghép0,5 cho P/R/F1; mAP là phép đo quét confidence của thư viện.

| Metric | S960 cũ trên307val | Hardneg best mới | Thay đổi |
| --- | ---: | ---: | ---: |
| mAP50 | 68,38% | 68,48% | +0,10điểm phần trăm |
| mAP50–95 | 53,82% | 55,43% | +1,60điểm phần trăm |
| Precision cố định | 59,81% | 56,25% | −3,56điểm phần trăm |
| Recall cố định | 70,33% | 69,23% | −1,10điểm phần trăm |
| F1 cố định | 64,65% | 62,07% | −2,58điểm phần trăm |
| TP / FP / FN | 64 /43 /27 | 63 /49 /28 | −1TP,+6FP,+1FN |
| Ảnh âm có bbox /216 | 7 (3,24%) | 5 (2,31%) | −2ảnh |
| Tổng bbox sai trên ảnh âm | 10 | 7 | −3bbox |
| Bbox sai trên ảnh dương theo GT hiện có | 33 | 42 | +9bbox |

Kết quả là **trade-off**, chưa xác nhận cải thiện tổng thể: mAP50–95 tăng và bớt ảnh âm có hộp, nhưng precision/recall/F1 tại ngưỡng cố định giảm. Phần giảm ảnh âm nằm ở clipTAD `20220620_acci-bg13` (3→1ảnh); bốn ảnh âm ACCIDENT vẫn có hộp. Không gọi đây là false alerts/giờ, event F1 hoặc kiểm độc lập camera. Không suy ra âm khó hoàn toàn được giải quyết hoặc riêng mining gây thay đổi vì recipe cũng thay warm-start/lịch học.

### Curve và lý do dừng

Đã xem `training_summary/results.png`: train box/cls/dfl loss có xu hướng giảm, còn val loss dao động và fitness không vượtepoch5 tới lúc dừng. Đây là dấu hiệu cải thiện trên train không chuyển đều sang val; không đủ để kết luận một nguyên nhân duy nhất. Early stopping khớp patience10 và log15epoch; không phải lỗi loader hoặc OOM trong hồ sơ run hoàn tất.

**CSV cóepoch2 mAP50=70,645%**, nhưng checkpoint được chọn theo mAP50–95 nằm ởepoch5, không phảiepoch2. `save_period=-1` và thư mục chỉ cóbest/last, không có trọng sốepoch2 để đo lại. BestCSV5 ghi mAP50=69,211%/mAP50–95=55,437%; báo cáo đánh giá lại best đã lưu cho68,4768%/55,4264%. Giữ cả hai nguồn số; chưa xác minh riêng nguyên nhân chênh CSV/đánh giá lại. Bảng so chính dùng kết quả revalidation trong `experiment.json`, không đổi tiêu chí hoặc lấy một epoch trên70% để gọi modelbest đã đạt mục tiêu.

### Kiểm tra và đầu ra

- SHA config/requested_config, checkpoint khởi tạo, best mới, dataset YAML/provenance và từng ảnh/nhãn qua `--saved-validation` đều hợp lệ; args thực khớp recipe, `resume=false`.
- Đếm và ghép lại toàn bộ307case từ bbox đã lưu khớp CSV/JSON/report:63TP/49FP/28FN,91GT. So hai model có33frame thay đổi TP/FP/FN, GT từng frame giữ nguyên.
- Cảbest/last có class`accident`,11.135.987tham số; optimizer đã strip vàepoch metadata−1. Không mặc địnhlast có thểresume. Best metadata khớp hàngCSV5, last khớpCSV15.
- Phân loại hình học49FP:7trên ảnh âm,33không giao vùngGT,7có giao nhưngIoU<0,5,2trùng/xung đột ghép. Nhóm ngoàiGT là lỗi theo annotation hiện có, không tự kết luận nguyên nhân nội dung hoặc sửa nhãn. Đã xem contact sheetFP/FN; một số FN là vùng rất nhỏ/mờ, một số FP là hộp thêm quanh xe ngoài vùngGT. Đây là quan sát mẫu, không xác minh lại toàn bộ nhãn.
- Test cũ112ảnh không suy luận lại. Reserve mới120frame giữ nguyên hash và`model_predictions_seen=false`; checkpoint/điểm vận hành s960 cũ không bị thay thế. Không tải dữ liệu, đổi config hoặc train thêm trong lượt báo cáo này.

Mở `outputs/training/b0_s960_hardneg_v1/diagnostics/index.html` để xem so sánh, curve và ảnhFP/FN; JSON đầy đủ ở`diagnostics/comparison.json`, `experiment.json`. Model mới ở`outputs/training/b0_s960_hardneg_v1/weights/best.pt`; ảnh lỗi ở`diagnostics/image_errors/`; PR/F1/confusion matrix đánh giá lại ở`metrics_val/`. [Snapshot nhỏ sau train](evidence/2026-10-29-b0-hardneg-validation.json). Các hồ sơ chuẩn bị trước train giữ nguyên trạng thái lịch sử; B0 sự kiện/RQ1/RQ2 chưa hoàn thành.

## Nghiên cứu và thí nghiệm đối chứng SGD Version 11 — 30/10/2026

**Trạng thái:** đã gửi notebook Kaggle PRIVATE Version 11, `b0_s960_sgd_kaggle_v3`, đang chạy/khởi tạo; chưa có kết quả train. Chỉ dùng quota miễn phí. Cấu hình, dữ liệu và đối chiếu được khóa trước khi gửi; không tải lại Dataset 4 GB. [Config](../configs/b0_s960_sgd_kaggle_v3.json), [lệnh theo dõi](kaggle_training.md#version-11--đối-chứng-sgd), [thống kê](evidence/2026-10-30-b0-data-distribution.json).

### Nghiên cứu và sự khác biệt task

- [STTAD mục III, V và Table III](https://dsg.tuwien.ac.at/team/snastic/publications/ITSC25_0424_FI.pdf): định nghĩa vùng sự kiện theo video, 12 loại; STFN kết hợp YOLOv8 nhánh 2D và I3D/3D, lấy 16 frame 224, AdamW batch32 trên RTX4090, LR 1e-4/1e-5/1e-6 theo ba đoạn 20/40/40 epoch. STFN-I3D báo cáo mAP@50 **42,5%**, @75 **23,6%** trên protocol test STTAD 12 class. Không so trực tiếp với B0 một class/ảnh, metadata ACCIDENT, validation đã tái sử dụng; khác tập, target và evaluator. Repo STTAD công khai phần ví dụ; không chứng minh toàn bộ dataset đã public.
- [ACCIDENT paper](https://arxiv.org/abs/2604.09819), [repo](https://github.com/accidentbench/ACCIDENT): thời điểm, điểm impact và loại va chạm, Gaussian spatial/temporal similarity, không phải mAP bbox B0. File metadata-real phiên bản dự án lưu có `x1,y1,x2,y2` ngoài tâm impact; đã dùng vùng đúng frame impact sau đối chiếu. Paper không phát hành annotation detection/tracking thông thường; không lan bbox sang frame không có nhãn hoặc coi bbox participant là accident region. Các phương pháp optical flow/dynamics và VLM là tham khảo hướng chuỗi sau B0, không phải mAP của ta.
- [TAD repo tác giả](https://github.com/UnicomAI/UnicomBenchmark/tree/main/TADBench): có nhãn clip normal; ZIP đã kiểm trước đây có video, không thấy bbox trong danh mục. Không biến video accident thành bbox training tự động. Repo nêu 344 video nhưng liệt kê 277+127=404, nên không dùng tổng trong README làm inventory đã kiểm.
- [Ultralytics YOLOv5 tips](https://docs.ultralytics.com/yolov5/tutorials/tips-for-best-training-results/): coi sự đa dạng, đủ nhãn, độc lập split là nền tảng; khuyến nghị số lượng là hướng dẫn YOLOv5 chứ không là ngưỡng khoa học đảm bảo chất lượng, không mặc định tỷ lệ background 0–10% áp dụng cho tai nạn hiếm.
- [AdamW](https://arxiv.org/abs/1711.05101) giải thích khác biệt weight decay và so với momentum SGD trên phân loại ảnh; không chứng minh SGD tốt hơn trên dataset này. [SGDR](https://arxiv.org/abs/1608.03983) dùng cosine và warm restart; code của project dùng cosine **không restart**, không tuyên bố tái lập SGDR. [Mã trainer Ultralytics 8.4.178](https://raw.githubusercontent.com/ultralytics/ultralytics/v8.4.178/ultralytics/engine/trainer.py) là bản thực tế được pin.

### Phân tích dữ liệu và run

Provenance bundle: train 1.122 dương ACCIDENT/1.085 nhóm, âm 19 ACCIDENT/11 nhóm + 1.240 TAD/26 nhóm + 300 DETRAC/1 nhóm; val 91 dương/90 nhóm, 216 âm/8 nhóm. Nhóm chống rò rỉ không chứng minh camera độc lập. Ảnh dương train 423/1.122 bbox có diện tích dưới 1% ảnh; val 41/91. Trong 34 FN validation của AdamW ở conf .25/IoU .5, 18 thuộc nhóm dưới 1%, 13 thuộc 1–5%, 3 thuộc >=5%. Đây là bbox area tương đối, không phải định nghĩa small/medium/large của COCO. Bằng chứng [JSON](evidence/2026-10-30-b0-data-distribution.json); phép đếm không đọc test/reserve. Không khẳng định cỡ bbox là nguyên nhân duy nhất; còn khác miền nguồn/đêm/chất lượng/nhãn và sai số mẫu.

Version 9 SGD có validation mAP50/95 69,79%/55,87%, Version 10 AdamW 67,85%/52,63%; tại cùng ngưỡng recall 67,03% → 62,64%, F1 66,30% → 67,06%. Cả hai cùng train/val và checkpoint đầu; nhiều tham số khác nhau nên không quy kết do optimizer. Để rút kinh nghiệm có thể kiểm định, Version 11 **chỉ đổi optimizer AdamW → SGD** so với Version 10 trong các tham số train, giữ LR .0003, momentum .9, batch8, AMP, 960, cosine, seed, augmentation, 60 epoch, nbs32 và early-stop sau epoch25/patience25. LR cùng số không có nghĩa độ lớn bước của SGD/AdamW tương đương; đây là phép thử có kiểm soát, không đảm bảo cải thiện. Vì có OOM fallback ở thư viện, phải kiểm log batch thực tế.

**Phạm vi:** cùng 2.681 train + 307 val, không thêm dữ liệu hoặc nhãn, không đổi test/reserve hay checkpoint B0 đang khóa. Không sử dụng lại val nhiều lần như ước lượng test độc lập. Chọn mAP và phân tích recall/FP, so sánh cùng mẫu; nếu không cải thiện, không tự tăng vòng thử trên cùng val, ưu tiên mở rộng nguồn ảnh sự kiện có bbox public và benchmark video độc lập. Không cam kết đạt 70%.

Kiểm trước gửi: manifest overlay và hash 2.988 ảnh hợp lệ; `--help`, import, unit test; resource/backward probe sẽ chạy trên GPU Kaggle trước epoch. Version 11 đã được gửi, **không ghi là train hoàn tất**. Sau khi xong dùng lệnh fetch trong hướng dẫn, xác nhận status, checkpoint/hash, log, so mAP/recall/FP và mới ra quyết định.

## Kết quả Version 11 — SGD Kaggle, 30/10/2026

Kaggle `COMPLETE`; `run_status.json` trong ZIP báo `training_completed=true`, 50 epoch và không chạy test/reserve. Best theo fitness mAP50–95 ở **epoch 3**, early stopping sau epoch 25 với patience 25 kích hoạt ở epoch 50. Đánh giá lại best trên 307 validation cho **mAP50 70,64%**, **mAP50–95 56,80%**. Đây là kết quả pilot trên validation đã dùng nhiều lần, không phải kết quả test độc lập hay độ chính xác sự kiện ngoài thực tế.

| Chỉ số | V9 SGD | V10 AdamW | V11 SGD |
| --- | ---: | ---: | ---: |
| mAP50 đánh giá lại best | 69,79% | 67,85% | **70,64%** |
| mAP50–95 đánh giá lại best | 55,87% | 52,63% | **56,80%** |
| Precision chính thức Ultralytics | 83,55% | 75,90% | 81,46% |
| Recall chính thức Ultralytics | 58,24% | 63,74% | 62,77% |
| Precision cố định conf .25, IoU .5 | 65,59% | **72,15%** | 61,54% |
| Recall cố định conf .25, IoU .5 | 67,03% | 62,64% | **70,33%** |
| F1 cố định conf .25, IoU .5 | 66,30% | **67,06%** | 65,64% |
| TP / FP / FN tại ngưỡng cố định | 61 / 32 / 30 | 57 / 22 / 34 | 64 / 40 / 27 |
| Ảnh âm có ít nhất một bbox sai / 216 | 5 | **2** | 8 |

Precision/recall chính thức lấy tại điểm trên đường PR do Ultralytics tính; không so như cùng ngưỡng với dòng conf .25. FP là số bbox sai gồm cả trên ảnh dương; số ảnh âm có dự đoán là phép đếm khác. 216 ảnh âm chỉ thuộc 8 nhóm nguồn, không suy thành false alerts/giờ. Tại cùng ngưỡng, V11 phát hiện thêm 7 bbox đúng nhưng tăng 18 bbox sai so V10; recall +7,69 điểm %, F1 −1,42 điểm %. Trên cùng 91 ảnh dương: 53 cả hai đúng, 11 V10 bỏ sót/V11 đúng, 4 V10 đúng/V11 bỏ sót, 23 cả hai bỏ sót. Trên 216 ảnh âm: 207 cả hai không có FP, 7 chỉ V11 có, 1 chỉ V10 có, 1 cả hai có.

V11 và V10 cùng fingerprint provenance `b7c0bc11…aba61e`, cùng checkpoint đầu, seed, batch8, AMP, cosine, learning rate và dataset; khác optimizer. Một seed và validation đã được dùng lặp lại chỉ hỗ trợ kết luận **trong lần so này**, không chứng minh SGD luôn hơn AdamW. V9 khác nhiều tham số. Run V11: log gốc đã kiểm SHA theo manifest cho thấy probe backward 3 bước batch8 AMP thành công trên Tesla T4, AMP checks passed và optimizer SGD0,0003/momentum0,9; không có thông báo OOM hoặc giảm batch. Thời gian train và đánh giá sau train khoảng 65,16 phút, chưa tính toàn bộ thời gian chuẩn bị Kaggle. Train loss giảm từ epoch3 đến50 nhưng mAP50–95 dao động và không vượt epoch3; không suy ra loss giảm thì validation phải tăng.

**Bằng chứng:** [JSON](evidence/2026-10-30-b0-sgd-validation.json); dữ liệu: 2.681 train/307 val; không đổi dữ liệu, không train lại, không thay checkpoint/điểm vận hành B0 khóa. ZIP **124.368.049 byte** có SHA `bee2df8904e75e4e2be8c62b9bfb1f27ff94df22b3c8957cf0844362363b745d`, đã kiểm từng file và giải nén vào `outputs/training/b0_s960_sgd_kaggle_v3/`. Best `weights/best.pt` SHA `87dedc00ba63541a957abf7ee7e36201a63388ede2aed816d216cafd17ce00a6`, metric metadata khớp CSV epoch3; `last.pt` SHA `338cf4ed39718ee9907a0c264099c0e85e495f67352459aef037d338da3a4626`, metadata khớp epoch50. Cả hai đã strip optimizer, epoch metadata −1, không resume đầy đủ optimizer; có thể dùng weights cho một run fine-tune mới nếu thiết kế riêng. Metadata V9 đã kiểm hash từng thành viên nhưng toàn bộ ZIP V9 chưa tải và kiểm SHA. Tiếp theo cần rà FP/FN, đo trên nguồn/event độc lập đã khóa trước và xem xét thêm nhãn vùng công khai; không dùng validation lặp lại như test, không suy event recall hay hiệu quả triển khai chỉ từ mAP này.
## Chuẩn bị Version 12 — đối chứng learning rate 04/11/2026

**Trạng thái 04/11:** đã gửi notebook PRIVATE [Version 12](https://www.kaggle.com/code/laqun0211/dacn-b0-s960-full-v1), sau đó fetch kết quả về máy. [Retrieval receipt](../outputs/kaggle/b0_s960_sgd_low_lr_kaggle_v4/retrieval.json) xác nhận output qua SHA/manifest/config/best checkpoint và `training_completed=true`, 50 epoch. Dataset PRIVATE cũ được gắn, không upload lại (`dataset_uploaded=false`). Đây là đối chứng trên **validation đã dùng nhiều lần**, chưa là benchmark sự kiện hay kiểm chứng độc lập. [Deployment receipt](../outputs/kaggle/b0_s960_sgd_low_lr_kaggle_v4/deployment.json) chỉ lưu trạng thái khi gửi.

V11 SGD trên cùng 2.681 ảnh train và 307 ảnh val hoàn tất 50 epoch; best CSV epoch 3, mAP50 0,70643, mAP50–95 0,56800. Ở confidence 0,25/IoU 0,5: TP64/FP40/FN27, F1 0,65641; 8/216 ảnh âm có dự đoán. V10 AdamW: mAP50 0,67853, mAP50–95 0,52626; F1 0,67059, FP22 và 2/216 ảnh âm có dự đoán. V11 tăng AP nhưng giảm F1 và báo nhầm nhiều hơn, nên không gọi là tốt hơn toàn diện.

V11 có train `cls_loss` 0,53747 tại epoch 3 xuống 0,27073 tại epoch 50, trong khi validation `cls_loss` tăng 0,96912 lên 1,09844; mAP50–95 không vượt epoch 3. LR thực tại epoch 3 khoảng 0,000179 trong warmup, LR đỉnh config 0,0003 ở epoch 5. Có thể do bước học, overfit, nhiễu nhãn hoặc cấu trúc validation; không suy ra nhân quả từ hai mốc này. **Phép kiểm mới giảm duy nhất `lr0` còn 0,00015** và giữ toàn bộ `TRAIN_KEYS` khác như V11, gồm YOLOv8s/960, start checkpoint SHA `c1fdd6dc...019302`, SGD, seed, batch8, AMP, augmentation, warmup/cosine, tối đa 60 epoch, early stopping từ epoch25/patience25. Không resume V11. Gói PRIVATE SHA `b00b76e7...a51` giữ nguyên, không upload lại 4 GB; test/reserve không ở trong ZIP. Đối chiếu `TRAIN_KEYS` bằng code cho đúng một khác biệt `lr0`.

Nhu cầu: kiểm liệu bước SGD nhỏ hơn giữ được chất lượng validation tốt sau giai đoạn warmup. Căn cứ: log thực và [mã/tài liệu Ultralytics 8.4.178](https://raw.githubusercontent.com/ultralytics/ultralytics/v8.4.178/ultralytics/cfg/default.yaml), [hướng dẫn train](https://docs.ultralytics.com/usage/cfg/); [STTAD](https://github.com/ZTR02/STTAD) là phương pháp chuỗi khác nhiệm vụ, [ACCIDENT](https://github.com/accidentbench/ACCIDENT) là hướng dữ liệu bổ sung phải rà nhãn. Phương án khác gồm thêm sự kiện độc lập, sửa nhãn và mô hình temporal; chưa trộn vào một run để so LR. Con số 0,00015 là **giả thuyết của project**, không phải recipe paper hay mức bảo đảm. Chỉ đánh giá val và phân tích FP/FN/nhóm nguồn sau khi có output thật; chưa đổi checkpoint B0 khóa hoặc ngưỡng vận hành. Chi tiết nguồn và mức kiểm ở [literature review](../reference/LITERATURE_REVIEW.md#đối-chiếu-cho-một-run-b0-mới--04112026).

**Kết quả đầu ra đã kiểm:** V12 best val mAP50 0,70631 (V11 0,70643), mAP50–95 0,56101 (V11 0,56800). Tại confidence 0,25/IoU 0,5, V12 TP65/FP37/FN26, F1 0,67358; V11 TP64/FP40/FN27, F1 0,65641. Ảnh âm có dự đoán: V12 7/216, V11 8/216. V12 cải thiện điểm vận hành cố định một chút nhưng không tăng AP; chưa chọn model mới vì val đã dùng nhiều lần và chưa có test sự kiện độc lập. [Artifact V12](../outputs/training/b0_s960_sgd_low_lr_kaggle_v4/experiment.json), [artifact V11](../outputs/training/b0_s960_sgd_kaggle_v3/experiment.json).
