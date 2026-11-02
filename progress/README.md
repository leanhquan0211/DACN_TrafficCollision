**Mới nhất 31/10 — báo cáo và bản trình bày:** [PDF 14 slide ngang](../docs/SLIDE_TIEN_DO_DACN.pdf) dùng Times New Roman, nền kem/cam san hô và góc vuông/bo nhẹ. Slide 6–7 giải thích IoU, P/R/F1 và AP/mAP; slide 8/10 đưa ảnh biểu đồ gốc local/Kaggle trước các slide so sánh vẽ lại. Giữ nội dung/số liệu 10 slide trước, chỉ đổi số thứ tự; [chú thích và lời trình bày](../docs/CHU_THICH_SLIDE_DACN.md) đã đồng bộ đủ 14 mục. [Báo cáo Markdown](../docs/BAO_CAO_TIEN_DO_DACN.md) / [PDF đầy đủ](../docs/BAO_CAO_TIEN_DO_DACN.pdf) giữ giải thích và bằng chứng. API xác nhận Version11 COMPLETE trong lượt kiểm trước; local kết quả/hashes khớp. Dừng triển khai/thí nghiệm mới theo yêu cầu; [nhật ký31/10](2026-10-31.md). Kết quả V11 vẫn là pilot trên validation: mAP50 **70,64%**, mAP50–95 **56,80%**, fixed F1 **65,64%**/recall **70,33%**; chưa benchmark sự kiện hoặc thay model khóa.

**02/11 — rà soát trước push:** kiểm `.gitignore`, file tracked/untracked, kích thước và khả năng phục hồi sau clone; chưa commit/push hoặc train. Source/config/metadata/tài liệu phù hợp đưa lên Git; dataset/checkpoint/bundle vẫn ngoài Git. Clone chưa train ngay: thiếu tài sản và quyền Dataset Kaggle PRIVATE. [Hướng dẫn máy mới](../docs/GETTING_STARTED.md), [nhật ký02/11](2026-11-02.md). Trạng thái thực nghiệm B0/B1 giữ nguyên.

# Tiến độ từng baseline và nhật ký đồ án

**Lịch sử — Kaggle Version 10 đã hoàn tất:** đủ 60 epoch, best theo CSV/train_metrics tại epoch 52. Đánh giá lại best trên 307 val: mAP50 **67,85%**, mAP50–95 **52,63%**; F1 tại confidence0,25/IoU0,5 **67,06%**, Recall **62,64%**. So Version 9 cùng dữ liệu: mAP50 giảm 1,94 điểm %, F1 tăng 0,75 điểm %, recall cố định giảm 4,40 điểm %. Đã tải và kiểm hash kết quả; không dùng test/reserve hoặc thay model khóa. [Báo cáo](../docs/b0_pilot_audit.md#kết-quả-version-10--adamw-kaggle-30102026), [bằng chứng](../docs/evidence/2026-10-30-b0-adamw-validation.json), [nhật ký](2026-10-30.md).

**Đây là file tổng hợp duy nhất cho tất cả baseline.** Cập nhật lần cuối: **02/11/2026**, múi giờ Asia/Bangkok. Muốn biết mỗi baseline còn thiếu gì, đọc file này; muốn xem chi tiết một lần làm việc, theo liên kết nhật ký bên dưới. Không tạo file tiến độ riêng cho B0/B1/B2/T0/B3.

Kế hoạch và điều kiện chuyển bước: [README gốc](../README.md), sheet `05_Cac_buoc`/`08_Du_lieu`/`09_Danh_gia` trong [XLSX](../YOLO_Lo_trinh_DACN.xlsx). Thuật ngữ tra ở [GLOSSARY](../reference/GLOSSARY.md). **B3 và T1 là hai ký hiệu của cùng phương án GRU**, không phải hai baseline độc lập.

Trước mỗi lần triển khai hoặc train, đối chiếu [literature review](../reference/LITERATURE_REVIEW.md), paper/mã nguồn chính thức và workbook; ghi khác biệt của thí nghiệm với recipe tác giả vào config/báo cáo. Chỉ cập nhật trạng thái bằng đầu ra đã kiểm, không coi số ảnh nhiều là bằng chứng chất lượng model.

## Nhìn nhanh: đang ở đâu?

**Kaggle29/10 — đã chuẩn bị, chưa gửi train:** gói3,78GiB chứa2.988ảnh(train2.681/val307), thêm420normal tác giả trong14nhómtrain cũ; không thêm sự kiện độc lập. 75test đạt, kiểm5996fileZIP/hash, decode2988ảnh và trainer đổi root đạt. CLI2.2.5 riêng đã cài, publish báo`authentication_required`: **Dataset/Notebook chưa tạo, runcloud chưa khởi chạy**. [Hướng dẫn đăng nhập/gửi/nhận](../docs/kaggle_training.md), [snapshot](../docs/evidence/2026-10-29-b0-kaggle-preparation.json). Người dùng cho phép một runPRIVATE; AI không theo dõi liên tục và không train nặng laptop. Kết quả hardneg local phía dưới vẫn giữ nguyên.

Đã bổ sung hướngdẫn vòngđời`publish→status→fetch`, trường hợpDatasetprocessing/chốnggửi trùng, cấu trúc`training_summary`/weights/curves và điều kiện tạo thínghiệm kếtiếp. Lượt giải thích không gọipublish/status/fetch và không đổi trạngtháiAPI.

**Mới nhất29/10 — hardneg đã hoàn tất:**15epoch, bestCSV5, early stop10. Cùng307val, mAP50 **68,48%**, mAP50–95 **55,43%**, F1 tại0,25/IoU0,5 **62,07%**;63TP/49FP/28FN,5/216ảnh âm có hộp. So mốc cùng tập: mAP50–95 tăng1,60điểm phần trăm nhưng F1 giảm2,58; chưa nhận cải thiện tổng thể hoặc modelbest đạt70%mAP50. [Bằng chứng](../docs/evidence/2026-10-29-b0-hardneg-validation.json), [trang xem](../outputs/training/b0_s960_hardneg_v1/diagnostics/index.html), [nhật ký cùng ngày](2026-10-29.md). Không train thêm hoặc mở reserve; các mục chuẩn bị phía dưới là lịch sử.

**Mốc trước khi train29/10:** chạy lại `--check` cho `b0_s960_hardneg_v1` đạt:2.680ảnh, split2.261/307/112. Preflight đã đạt; tại mốc đó output chưa tồn tại. Run hiện đã hoàn tất theo cập nhật phía trên; không chạy lại train/resume vào output cũ.

**Làm rõ quy mô nguồn29/10:**2.261ảnh train đến từ1.151clip/chuỗi, không chỉ vài chục:1.122clip dương ACCIDENT,26TAD normal,3DETRAC;11clip âm ACCIDENT trùng nguồn dương.1.112nhóm nguồn tạm chưa chứng minh camera độc lập. Đã đối chiếu Kaggle GPU như lựa chọn tài nguyên cho tương lai, chưa chuyển nền tảng/config; [nhật ký cùng ngày](2026-10-29.md).

**Mốc chuẩn bị tiếp29/10:** đã triển khai/đo B1 causal trên12chuỗi/4.845frame và xuất release mới2.680ảnh; thêm510normal vào train/val, giữ riêng120normal mới, loại3clip nghi liên quan nguồn consumed. [Hồ sơ chuẩn bị](../docs/b0_pilot_audit.md#chuẩn-bị-s960-hardneg-v1--29102026), [B1](../docs/b0_pilot_audit.md#đo-b0b1-trên-video-sạch--29102026), [snapshot lúc chưa train](../docs/evidence/2026-10-29-b0-hard-negative-preparation.json). Nhật ký cùng ngày tiếp tục ở file29/10 phía dưới.

**29/10:** đã hoàn thành chọn điểm vận hành s960/conf0,27 (valF1 65,98%, recall70,33%), khóa trước khi đo holdout âm. Holdout **34/120ảnh có hộp**, đã consumed; không dùng để chọn lại ngưỡng. [Snapshot](../docs/evidence/2026-10-29-b0-operating-point.json), [nhật ký29/10](2026-10-29.md).

**Run s960 đã hoàn tất:**45epoch, best CSV30, early stopping patience15 đã áp dụng. Val mAP50 **68,60%**, mAP50–95 **53,94%**, F1 cố định **64,65%**; chưa đạt mAP50>70%. [Bằng chứng](../docs/evidence/2026-10-28-b0-s960-validation.json), [nhật ký28/10](2026-10-28.md).

**Giải thích AP/mAP chi tiết 28/10:** đã đối chiếu hàm tính thực tế bằng ví dụ nhỏ; không thay metric/config.

**Giải thích metric 28/10:** mục tiêu run s960 vẫn là mAP50 val >70%; best.pt chọn theo mAP50–95 của bản cài. Đã đối chiếu precision/recall/F1 cố định với số Ultralytics và phân biệt bbox/frame với event; không đổi config, dữ liệu hoặc điều kiện run đang chạy.

**Trạng thái dữ liệu28/10:** dataset2.170ảnh đã được dùng cho cả n640 và s960; reserve âm120frame khi đó vẫn giữ riêng/chưa suy luận; đã được đo một lần ở bước29/10. Ba checkpoint cũ và hai run mới đã có metric trên cùng217val. Trạng thái chuẩn bị/chờ chạy trong nhật ký trước là lịch sử.

**Lượt mở rộng 26–27/10:** release **1.750 ảnh** dùng âm đã rà hoặc nhãn normal tác giả, đã train xong 60 epoch và đo trên [test sạch 112 ảnh](../data/reviews/2026-10-27-b0-near-duplicate-review.json). mAP50 **0,6968**; tại confidence 0,25/IoU 0,5 có **67 TP, 46 FP, 40 FN**. Trên probe TAD normal, **41/100 frame** bị dự đoán nhầm. Pilot ảnh hoàn thành vòng train/đo; B0 sự kiện đầy đủ chưa xong. [Báo cáo](../docs/b0_pilot_audit.md#b0-mở-rộng-accident-v9--26102026), [nhật ký 27/10](2026-10-27.md).

| Baseline | Làm gì? | Trạng thái thực tế | Việc cần hoàn thành tiếp |
| --- | --- | --- | --- |
| [B0](#b0--detector-ảnh-vùng-tai-nạn) | YOLO học bbox vùng accident trên từng ảnh | **Version 11 hoàn tất: mAP50 70,64%, F1 cố định 65,64%; recall tăng nhưng FP tăng so Version 10** | Rà ca bỏ sót và FP, quyết định trade-off trên val; chưa thay model khóa, chưa benchmark sự kiện |
| [B1](#b1--b0-cộng-lọc-theo-thời-gian) | Làm mượt điểm B0 bằng EMA hoặc k-of-N causal | **Đã triển khai và đo chẩn đoán, chưa benchmark sự kiện** | Cần nguồn dương temporal/độc lập và protocol event/matched recall; không gọi bout ON là cảnh báo |
| [B2](#b2--tracking-phương-tiện-và-luật-chuyển-động) | YOLO xe + ByteTrack + đặc trưng/luật va chạm | **Mới có phần detection/tracking chạy thử** | Chưa có tracks cache phục vụ motion, candidate, features và luật quyết định |
| [T0](#t0--mlp-trên-đặc-trưng-hiện-tại) | MLP học từ đặc trưng cặp xe tại thời điểm hiện tại | **Chưa triển khai** | Cần candidate/features/nhãn và đối chứng B2 |
| [B3/T1](#b3t1--gru-trên-chuỗi-quá-khứ) | GRU một chiều học diễn biến của cùng candidate/features | **Chưa triển khai** | Chỉ thực hiện sau dữ liệu chuỗi và các đối chứng phù hợp |

**Chưa baseline nào hoàn thành.** B0 đã có metric bbox trên ảnh pilot, nhưng chưa có metric sự kiện/cảnh báo tai nạn. YOLOv8n pretrained ban đầu tìm xe; checkpoint B0 pilot riêng đã fine-tune class `accident`. Video bbox/track ID cũ chỉ kiểm chức năng B2. Không dùng phần trăm hoàn thành khi các đầu việc có độ lớn khác nhau.

## Điều kiện chung trước thí nghiệm

| Phần dùng chung | Đã có | Còn thiếu / điều kiện đạt |
| --- | --- | --- |
| Mục tiêu và nhãn | CCTV cố định, va chạm xe–xe; policy vùng B0 có phiên bản; phân biệt nhãn tác giả/rà của AI/xác nhận người dùng | Tiếp tục giữ nhãn nhất quán, phạm vi gán nhãn rõ và loại trường hợp mơ hồ |
| Dữ liệu B0 | S960 dùng2.170ảnh; release chuẩn bị mới **2.680 =1.320impact+1.360âm**, thêm420train+90val,120reserve mới | Chưa thêm sự kiện dương; nhóm cảnh bảo thủ, chưa chứng minh camera độc lập; source bias và vùng dương nhỏ còn tồn tại |
| Truy nguồn và kiểm trùng | Manifest86asset; batch mới24clip/8.992frame, kiểmCRC/SHA/decode. Nhóm khóa trước mining;3clip nghi nguồn consumed bị loại | Không có pixel/hash gần không chứng minh camera/sự kiện độc lập; không dùng probe/holdout đã xem để train |
| Split train/validation/test | Release mới **2.261train /307val /112test cũ**, ngoài ra120reserve mới/4clip/2nhóm bảo thủ | Test/holdout cũ đã tiêu thụ; reserve mới chỉ có âm, chưa benchmark dương/âm độc lập; positive val vẫn là nhóm đã xem |
| Timing và nhãn temporal | CADP 001407 đã xác nhận Colliding 96–130 theo frame; PTS impact sáu file ACCIDENT đã đối chiếu | Chưa xác minh FPS ghi hình gốc; chưa có nhãn cửa sổ/cặp xe và protocol event-delay hoàn chỉnh |
| Đánh giá và tái lập | Pilot mới có config/seed, checkpoint, prediction log, bảng TP/FP/FN, so model cũ và probe âm | Chưa có evaluator sự kiện chung, benchmark toàn pipeline; probe còn 41/100 frame bị dự đoán nhầm |

Chi tiết dữ liệu, pilot và mẫu bị loại: [báo cáo B0](../docs/b0_pilot_audit.md). Nhãn âm/dương: [giải thích và điều kiện hợp lệ](../docs/b0_label_protocol.md#mẫu-dương-mẫu-âm-và-mẫu-chưa-biết). [Readiness](../data/b0_readiness.json) tách gate pilot đã mở khỏi gate benchmark đầy đủ vẫn đóng (`can_train=false`).

## B0 — Detector ảnh vùng tai nạn

**Cập nhật 27/10/2026:** pilot 47 ảnh lịch sử kém; run dùng âm chưa rà đã thu hồi. Release 1.750 ảnh đã train 60 epoch, đo test và probe âm. Trên cùng 112 ảnh test, mAP50 mới **0,6968**, cũ **0,0119**; probe TAD normal bị dự đoán nhầm 41/100 frame mới so với 76/100 cũ. [Báo cáo](../docs/b0_pilot_audit.md), [hướng dẫn đọc train](../outputs/training/README.md), [nhật ký 27/10](2026-10-27.md).

**Mục tiêu:** nhận ảnh sạch, trả bbox vùng `accident`, class và confidence. Model khởi đầu theo kế hoạch là YOLOv8n fine-tune; trọng số xe pretrained đang có chưa làm được nhiệm vụ này.

| Phần cần làm | Trạng thái | Bằng chứng / đầu ra cần đạt |
| --- | --- | --- |
| Định nghĩa vùng và chuẩn hóa nhãn | **Đã có công cụ/policy v4** | [Policy](../configs/b0_public_label_policy.json), [quy tắc nhãn](../docs/b0_label_protocol.md); giữ bbox nguồn, không dùng envelope CADP như GT tác giả |
| Ảnh dương, âm và trường hợp khó | **Release dùng âm đã rà hoặc nhãn normal tác giả** | 1.320 impact, 30 âm ACCIDENT đã rà, 300 DETRAC user xem và 100 TAD normal tác giả; val/test chỉ 6/5 âm |
| Kiểm chất lượng, trùng/cảnh và nhóm nguồn | **Kiểm kỹ thuật; bbox mới chưa rà toàn bộ** | 11 clip reject kỹ thuật, 9 clip loại theo review cũ, 4 clip impact trùng loại; [report](../data/processed/b0_accident_scaled_v1/split_report.json). Độc lập camera chưa được chứng minh |
| Split và export dataset huấn luyện | **Đã xuất release có âm đã xác minh** | [Split/report](../data/processed/b0_verified_pilot_v1/split_report.json), [phiếu loại hai nhóm](../data/reviews/2026-10-27-b0-near-duplicate-review.json); benchmark gate vẫn đóng |
| Fine-tune và lưu lần chạy | **Hoàn thành 60 epoch pilot ảnh** | [Config](../configs/b0_verified_pilot_v1.json), [checkpoint và experiment](../outputs/training/b0_verified_pilot_v1/experiment.json); run v2 bị thu hồi |
| Thí nghiệm normal mở rộng | **Đã train 60 epoch và đánh giá val** | [Config](../configs/b0_normal_expanded_v1.json), [dataset](../data/processed/b0_normal_expanded_v1/dataset/dataset.yaml), [mốc ba model trên val](../outputs/audits/b0_normal_expansion_v1/reference_val/report.json); [Kết quả run mới](../docs/evidence/2026-10-28-b0-normal-training.json): mAP50 0,64685; mAP50–95 0,49031; TP/FP/FN 54/35/37 |
| Điểm vận hành / holdout âm | **Đã chọn/khóa và đo một lần** | [Khóa](../configs/b0_s960_v1_operating_point_v1.json), [trang xem](../outputs/training/b0_s960_v1/operating_point_v1/index.html), [snapshot29/10](../docs/evidence/2026-10-29-b0-operating-point.json). ValTP/FP/FN64/39/27; holdout34/120ảnh có35hộp, không phải event metric |
| Công thức s960 sau đọc lại paper | **Hoàn tất45epoch, early stop15; best30** | [Kết quả](../docs/evidence/2026-10-28-b0-s960-validation.json), [checkpoint](../outputs/training/b0_s960_v1/weights/best.pt), [đồ thị](../outputs/training/b0_s960_v1/training_summary/results.png); mAP50 68,60%, mAP50–95 53,94%, TP/FP/FN64/43/27; chưa đạt mục tiêu70% |
| Fine-tune với âm khó | **Hoàn tất15epoch, early stop10; bestCSV5** | [Config](../configs/b0_s960_hardneg_v1.json), [snapshot sau train](../docs/evidence/2026-10-29-b0-hardneg-validation.json), [so sánh/ảnh lỗi](../outputs/training/b0_s960_hardneg_v1/diagnostics/index.html). Val307mAP50/95=68,48/55,43%;F162,07%;ảnh âm sai7→5 nhưng tổngFP43→49. Snapshot chuẩn bị vẫn giữ lịch sử; reserve mới chưa mở |
| Chuyển train sang KagglePRIVATE | **Đã có Dataset/NotebookPRIVATE và các run V9–V11 hoàn tất** | [Hướng dẫn](../docs/kaggle_training.md), [báo cáo tổng hợp](../docs/BAO_CAO_TIEN_DO_DACN.md#e9-chuyển-sang-kaggle-và-version-9). Gói2681train/307val; test/reserve ngoàiZIP; V10/V11 đã tải/kiểmhash, V9 giữ metadata chọn lọc. Mốc chặn đăng nhập29/10 chỉ là lịch sử. |
| Suy luận, đánh giá và phân loại FP/FN | **Đã phân tích lỗi và chạy 9 chuỗi đủ 3.857 frame; chưa benchmark event** | [Trang kết quả](../outputs/training/b0_verified_pilot_v1/diagnostics/index.html), [báo cáo](../outputs/training/b0_verified_pilot_v1/diagnostics/report.json); TAD normal 812/1.599 frame có bbox, CADP 35/35 frame Colliding có bbox nhưng chưa ghép vùng GT |

**Điều kiện hoàn thành:** có detector accident được huấn luyện và đo trên split đã khóa; lưu checkpoint/config, prediction và các lỗi FP/FN để biết vấn đề nào cần B1/B2 giải quyết. Không đặt số accuracy hay FPS giả làm mốc đã đạt.

**Cập nhật sau train 28/10:** run normal-expanded đã hoàn tất; F1 cố định 0,6000, 6/126 ảnh âm có dự đoán. [Snapshot kết quả](../docs/evidence/2026-10-28-b0-normal-training.json), [nhật ký](2026-10-28.md). Test cũ và holdout mới không được chạy trong lượt này. Kết luận và hướng đi tiếp theo được trao đổi trong chat theo yêu cầu người dùng.

**Thử nghiệm LR đã hoàn thành sớm ở epoch 48/60:** [config](../configs/b0_verified_lr001_val_v1.json) giữ nguyên dataset, split, SGD, seed, batch và checkpoint pretrained; thay `lr0=0,01` thành `0,001` để khảo sát ổn định fine-tune theo [hướng dẫn Ultralytics](https://docs.ultralytics.com/guides/finetuning-guide/). Dùng **validation duy nhất** để so hai run; validation đã dùng nhiều lần và chỉ có sáu ảnh âm. Test/probe đã xem không dùng chọn tham số; cần tập test mới độc lập để kết luận. Sau lỗi RAM ở epoch 2 đã resume và kết thúc sớm tại epoch 48; `last.pt` đã strip optimizer. Để xem epoch 49–60, đã chuẩn bị [config run mới](../configs/b0_verified_lr001_full60_v1.json) với `patience=0`, `workers=0`; **đã chạy xong; xem kết quả mới ngay dưới**. Đây không phải resume chính xác; chỉ dùng val để so, chưa có bằng chứng LR mới giảm báo nhầm. [Lệnh và giải thích](../outputs/training/README.md#lần-thử-tiếp-theo-giảm-learning-rate-chỉ-so-validation).

**Quá trình:** [19/10 — chuẩn hóa CADP và ảnh âm](2026-10-19.md) → [24/10 — chọn STTAD và pool v1](2026-10-24.md) → [25/10 — thêm impact ACCIDENT, pool v2](2026-10-25.md) → [26/10 — pilot và mở rộng](2026-10-26.md) → [27/10 — khôi phục train mở rộng](2026-10-27.md).

## Cập nhật sau khi run LR 0,001 đủ 60 epoch hoàn tất (27/10/2026)

Run `b0_verified_lr001_full60_v1` đã hoàn tất **60/60 epoch** trên cùng 97 ảnh validation. Các đoạn phía trên ghi trạng thái lúc chuẩn bị, nay được thay bằng số liệu thực tế ở đây. Train box loss giảm từ **0,8480** (epoch 50) xuống **0,76241** (epoch 60); cls loss **0,7412 → 0,58679**. Val mAP50–95 tốt nhất trong CSV của run mới là **0,49563 tại epoch 47**. Trong epoch 50–60, cao nhất chỉ **0,49229 ở epoch 52**; epoch 60 **0,48419**. Vì vậy nhận xét loss train giảm là đúng, nhưng validation không vượt checkpoint tốt nhất của run.

Đánh giá lại `best.pt` cùng split val: mAP50–95 **0,49412** ở run đủ 60, so **0,50643** ở run LR 0,001 dừng epoch 48 và **0,46033** ở run LR 0,01 ban đầu. Ngưỡng confidence 0,25/IoU 0,5: run đủ 60 có **56 TP / 65 FP / 35 FN**, run 48 epoch **60 / 49 / 31**. [Snapshot chỉ số và hash](../docs/evidence/2026-10-27-b0-full60-validation.json). Hai run LR 0,001 khác cách nạp ảnh (`workers=0` so với 2, run cũ từng resume), nên không quy chênh lệch chỉ cho early stopping. Chưa dùng test/probe cũ để chọn model; chưa đổi checkpoint B0 hiện hành. B0 sự kiện chưa hoàn thành.

### Vòng chẩn đoán ảnh và video đã hoàn tất

309 ảnh đã đo được thống kê lại từ prediction gốc, giữ đúng test **67 TP/46 FP/40 FN**. GT bị bỏ sót có diện tích trung vị **0,321% ảnh**, GT bắt đúng **3,216%**. Đã xử lý và đọc lại đủ **3.857 frame của 9 chuỗi** bằng checkpoint mốc/ngưỡng 0,25. Ba DETRAC từng dùng train: **0/2.037 frame có bbox**. Năm TAD normal đã xem: **812/1.599 frame có bbox**, có đoạn sai liên tục 215 frame. CADP: **35/35 frame 96–130 có bbox**, chỉ là temporal presence diagnostic, ngoài khoảng vẫn unknown và chưa có spatial/event recall. [Trang xem](../outputs/training/b0_verified_pilot_v1/diagnostics/index.html), [snapshot/hash](../docs/evidence/2026-10-27-b0-diagnostics.json), [nhật ký](2026-10-27.md). Code mới kiểm an toàn nhãn/frame; **47 test đạt**. Đã xong phần chẩn đoán B0; chưa benchmark sự kiện hoặc triển khai B1.

## B1 — B0 cộng lọc theo thời gian

**Mục tiêu:** nhận điểm accident của B0 qua nhiều frame, lọc bằng EMA hoặc k-of-N chỉ dùng hiện tại/quá khứ để giảm cảnh báo chập chờn. B1 không bắt buộc ByteTrack.

| Phần cần làm | Trạng thái | Đầu ra cần đạt |
| --- | --- | --- |
| Score B0, thứ tự frame/timestamp và GT temporal | **12chuỗi/4.845frame mới đã đo** | Cache score≥0,01, PTS media và source frame; CADP96–130 theo frame. Nguồn FPS CADP chưa biết; ngoài interval unknown |
| Lọc EMA/k-of-N và reset khi đổi video | **Đã triển khai/kiểm causal, warmup và gap** | [Code](../src/b0_diagnostics.py), [config](../configs/b1_causal_diagnostics_v1.json):3-of-5 đủ cửa sổ,EMAalpha0,3 init0; reset nguồn/gap |
| Chọn cửa sổ/ngưỡng trên validation | **Config cố định trước chẩn đoán; chưa tune cửa sổ** | conf0,27 từ val cũ; không tối ưu theo holdout đã mở. k/N/alpha là giả thuyết đồ án |
| Replay/đánh giá cùng B0 | **Đã đo tín hiệu, chưa event benchmark** | [HTML/report](../outputs/training/b0_s960_v1/temporal_diagnostics_v1/index.html): valnormal99→92/90frameON; consumednormal300→293/302; bout giảm nhưng sai kéo dài còn tồn tại. EventF1/delay/matchedrecall chưa có |

**Điều kiện hoàn thành:** đo được B0 so với B1 trên cùng split/protocol, nêu thay đổi báo sai và độ trễ tại recall tương đương. Không bắt buộc B1 phải thắng; kết quả âm vẫn phải được ghi đúng.

**Phụ thuộc tiếp theo:** cần nguồn temporal dương/âm và evaluator sự kiện; không suy timing CADP. **Quá trình:** đã chạy phép chẩn đoán29/10,12MP4 đọc lại đủ; [nhật ký cùng ngày](2026-10-29.md), [report và giới hạn](../docs/b0_pilot_audit.md#đo-b0b1-trên-video-sạch--29102026). Chưa đạt điều kiện hoàn thành B1 đầy đủ.

## B2 — Tracking phương tiện và luật chuyển động

**Mục tiêu:** nhận video sạch, phát hiện/theo dõi xe, chọn cặp nghi vấn và dùng luật chuyển động để tạo score/alert va chạm. Hai bbox chồng nhau hoặc hai track gần nhau chưa đủ ra quyết định.

| Phần cần làm | Trạng thái | Bằng chứng / đầu ra cần đạt |
| --- | --- | --- |
| Đọc video → YOLO xe → ByteTrack → vẽ/lưu | **Đã chạy thử phần kỹ thuật** | [Pipeline hiện có](../src/video_pipeline.py); đã đọc lại đủ 250 frame DETRAC và 221 frame CADP sạch. Đây chưa là metric tracking hoặc accident |
| Xuất tracks có bbox/ID/time/confidence và trạng thái thiếu | **Chưa triển khai cho motion** | Cache dữ liệu quỹ đạo; tách GT ID với track ID, ghi mất/đổi ID và reset giữa video |
| Chọn cặp trong ROI | **Chưa triển khai** | Candidate log và candidate recall; bộ tạo cặp vận hành khác với nhãn vùng đề xuất CADP |
| Tính đặc trưng chuyển động | **Chưa triển khai** | Vị trí/khoảng cách/biến thiên hướng, chất lượng/missing mask; dùng timing có căn cứ, không gọi chuyển vị ảnh là km/h |
| Luật quyết định và chính sách alert | **Chưa triển khai** | Luật/ngưỡng chọn bằng validation, score và event log; xác nhận/chống lặp không che sự kiện mới |
| Đánh giá và phân tích lỗi | **Chưa triển khai** | Cùng split/evaluator; đo báo sai, recall, delay và chi phí toàn pipeline; tách lỗi detector/tracker/luật |

**Điều kiện hoàn thành:** có bộ luật chuyển động chạy được trên candidate/features đã kiểm, phát alert và được đánh giá công bằng. Video có bbox/ID đơn thuần không đáp ứng điều kiện này.

**Phụ thuộc tiếp theo:** theo lộ trình, hoàn thành/hiểu B0 trước; sau đó cần timing, tracks và nhãn event/pair hoặc scene đúng phạm vi. **Quá trình phần nền:** [17/10 — đọc pipeline và thử video](2026-10-17.md), [19/10 — thử CADP/DETRAC sạch](2026-10-19.md). Chưa có lần đo luật B2.

## T0 — MLP trên đặc trưng hiện tại

**Mục tiêu:** dùng Multi-Layer Perceptron để học score của cùng candidate/features như B2/B3, từ đặc trưng hiện tại. Đây là đối chứng kiểm xem có cần học cả chuỗi hay không.

| Phần cần làm | Trạng thái | Đầu ra cần đạt |
| --- | --- | --- |
| Candidate/features và nhãn phù hợp | **Chưa có** | Tái dùng cùng bộ tạo cặp/đặc trưng, giữ split và phạm vi nhãn nhất quán |
| Chuẩn hóa và dataloader | **Chưa triển khai** | Fit scaler trên train, lưu scaler/mask/schema; không lấy thống kê từ val/test |
| MLP, train và chọn cấu hình | **Chưa triển khai** | Code PyTorch, config/seed/log, checkpoint và ngưỡng chọn trên validation |
| So B2/T0 và chuẩn bị so B3 | **Chưa triển khai** | Cùng evaluator/alert policy và đầu vào; bảng lỗi, event metrics và chi phí |

**Điều kiện hoàn thành:** có T0 tái lập được và phép so công bằng trên candidate/features chung; không thay detector khi muốn đo riêng tác dụng verifier.

**Phụ thuộc tiếp theo:** cần dữ liệu features/nhãn và B2 có thể kiểm chứng. **Quá trình:** chưa có lần triển khai/huấn luyện/thí nghiệm T0.

## B3/T1 — GRU trên chuỗi quá khứ

**Mục tiêu:** dùng Gated Recurrent Unit một chiều để đọc lịch sử đặc trưng của cặp xe và xác minh va chạm. Không dùng BiGRU hoặc frame tương lai khi tuyên bố xử lý online.

| Phần cần làm | Trạng thái | Đầu ra cần đạt |
| --- | --- | --- |
| Chuỗi `[T,F]`, sampling, mask và nhãn cửa sổ | **Chưa có** | Cửa sổ chỉ đến thời điểm hiện tại, giữ thứ tự/timing; nhãn dựa vào thời điểm cuối cửa sổ, không gán mọi frame của clip tai nạn là dương |
| GRU nhỏ và dataloader chuỗi | **Chưa triển khai** | Code/config; hidden 32/64, một layer chỉ là gợi ý trong XLSX, chưa là cấu hình tối ưu |
| Train, scaler và checkpoint | **Chưa triển khai** | Cùng split/features như T0; lưu seed/log/model/scaler, chọn cấu hình trên validation |
| So với B1/B2/T0 và ablation | **Chưa triển khai** | Phân biệt so hệ thống với ablation; tách đóng góp temporal/features/policy, báo cả recall, FP và delay |
| Benchmark và quyết định có dùng GRU không | **Chưa triển khai** | FPS/latency/VRAM toàn pipeline; nếu không hơn đối chứng thì phân tích nguyên nhân và chọn phương án phù hợp |

**Điều kiện hoàn thành:** có phép so tái lập chứng minh hoặc bác bỏ lợi ích học diễn biến theo thời gian, kèm chi phí; không coi chỉ ghép YOLO + GRU là có cải thiện hay tính mới.

**Phụ thuộc tiếp theo:** cần B2/T0, nhãn temporal và chuỗi đủ chất lượng. **Quá trình:** chưa có lần triển khai/huấn luyện/thí nghiệm B3/T1.

## Đầu ra hệ thống dùng chung sau các baseline

FSM `idle → suspected → confirmed → cooldown`, event matching/chống trùng, ảnh/clip bằng chứng, dashboard và báo cáo hiện **chưa triển khai**. Đây là các thành phần hệ thống, không tách thành baseline mới. Theo kế hoạch cần event precision/recall/F1, false alerts/hour trên âm dài, delay có GT timing, FPS end-to-end, p50/p95 latency và peak VRAM; hiện chưa có các số đo đó. Thiếu timing thì ghi giới hạn, không tự suy số giây nguồn.

## Quá trình cập nhật và nhật ký theo ngày

Mốc mới nhất: **31/10 — báo cáo tổng hợp và đối chiếu bằng chứng:** [nhật ký31/10](2026-10-31.md). Các runKaggle hoàn tất30/10 ở [nhật ký30/10](2026-10-30.md); không có train mới trong lượt báo cáo. Mốc29/10 điểm vận hành/B1 và28/10 s960 giữ vai trò lịch sử riêng.

Bảng này là lịch sử các thay đổi có ý nghĩa đối với baseline, dẫn tới **nhật ký cùng ngày**. Không sao toàn bộ log/audit vào đây.

| Ngày | Baseline/phần liên quan | Thay đổi thực sự đã làm | Nhật ký |
| --- | --- | --- | --- |
| 16/10/2026 | Nền chung | Lập mốc, quy tắc tiến độ; prototype xe/tracking chưa là baseline tai nạn hoàn chỉnh | [16/10](2026-10-16.md) |
| 17/10/2026 | Nền B2 | Giải thích code, kiểm luồng video và chạy thử chức năng | [17/10](2026-10-17.md) |
| 19/10/2026 | Dữ liệu B0, nền B2 | CADP 001407 sạch/mapping/review 96–130; DETRAC âm; chuẩn hóa nhãn và envelope dẫn xuất riêng | [19/10](2026-10-19.md) |
| 20/10/2026 | Tái lập chung | Hướng dẫn clone/tải/kiểm asset, Git ignore và bàn giao source; không phải run train | [20/10](2026-10-20.md) |
| 24/10/2026 | B0 dữ liệu | Chọn STTAD public, 31 frame vùng; TAD normal, kiểm nhóm DETRAC và pool v1 | [24/10](2026-10-24.md) |
| 25/10/2026 | B0 dữ liệu | Sáu ACCIDENT, bốn bbox impact phù hợp vào pool v2; 22 test đạt, chưa split/train | [25/10](2026-10-25.md) |
| 25/10/2026 | Theo dõi toàn bộ baseline | Nâng cấp chính file này thành bảng từng baseline; gom lịch sử kiểm kê, giải thích âm/dương. Không có thí nghiệm model mới | [25/10 — cập nhật tài liệu](2026-10-25.md#củng-cố-bảng-tiến-độ-baseline-và-tài-liệu) |
| 26/10/2026 | B0 dữ liệu và pilot ảnh | Mở rộng 20 ACCIDENT → pool v3; split/export 47 ảnh; train/đo pilot, test 0 TP/45 FP/3 FN ở ngưỡng cố định | [26/10](2026-10-26.md) |
| 27/10/2026 | B0 dữ liệu, train và đo | Thu hồi run âm chưa rà; train 60 epoch trên 1.750 ảnh, test mAP50 0,6968; probe normal 41/100 frame báo nhầm | [27/10](2026-10-27.md) |
| 28/10/2026 | B0 normal mở rộng và s960 | Dataset2.170ảnh, reserve120; n640 đủ60 và s960 early stop45 đã đo cùng217val; s960 mAP50 68,60% | [28/10](2026-10-28.md) |
| 29/10/2026 | Điểm vận hành, B1diagnostic, fine-tune và kiểm kết quả | Conf0,27/holdoutconsumed;12chuỗiB1/4.845frame; release2.680ảnh; hardneg15epoch/best5, valmAP50/95=68,48/55,43%,F162,07% | [29/10](2026-10-29.md) |
| 30/10/2026 | B0 Kaggle và vận hành | Khôi phục upload/GPU/môi trường; V9/V10/V11 hoàn tất; V11valmAP50/95=70,64/56,80%, fixedF165,64%, chưa event benchmark | [30/10](2026-10-30.md) |
| 31/10/2026 | Tổng hợp/hướng trình bày | Đối chiếu lịch sử/config/log/cases/checkpoint và nguồn; báo cáo MD/PDF, căn cứ mọi lựa chọn; không train hoặc mở dữ liệu mới | [31/10](2026-10-31.md) |
| 02/11/2026 | Bàn giao source | Kiểm Git ignore/file/kích thước, phân biệt clone code với phục hồi train; cập nhật giới hạn hướng dẫn, chưa commit/push hoặc train | [02/11](2026-11-02.md) |

## Quy tắc cập nhật từ lần làm việc sau

1. **Trước khi làm:** đọc bảng nhìn nhanh, mục baseline liên quan, README và phần kế hoạch/XLSX cần thiết. Kiểm media thật trên máy; trạng thái ở đây là hồ sơ đã kiểm, không chứng minh một máy clone đã có dữ liệu.
2. **Trước khi kết thúc:** cập nhật đúng hàng/hạng mục baseline trong **file này**, bằng chứng, đầu ra còn thiếu và việc tiếp theo. Nếu có mốc mới thì thêm dòng vào bảng quá trình; các việc cùng ngày cùng một mục nhật ký.
3. **Nhật ký:** mỗi ngày Asia/Bangkok chỉ có **một `progress/YYYY-MM-DD.md`**. Mọi task/lần chạy thêm mục trong file ngày đó; không tạo `B0.md`, file hậu tố theo task hoặc một progress file khác cho cùng ngày.
4. **Phân vai tài liệu:** file này giữ trạng thái baseline; nhật ký giữ diễn biến/quyết định theo ngày; `docs/` giữ hướng dẫn/báo cáo kỹ thuật; `outputs/audits/` giữ bằng chứng chạy đầy đủ. Dữ liệu/policy có thể đọc bằng máy ở `data/`/`configs/` được đồng bộ khi thực sự thay đổi, không sửa chỉ để làm đẹp bảng.
5. **Cách đánh dấu:** “đã có công cụ”, “đã chạy mẫu”, “đã train” và “đã đánh giá” là các trạng thái khác nhau. Chỉ ghi hoàn thành khi đạt đầu ra/điều kiện của baseline; không dùng số paper/mục tiêu kế hoạch làm kết quả thực nghiệm.

Các file 19/10 và 17/10 từng được hợp nhất theo quy ước một ngày/một file; bằng chứng bảo toàn vẫn ở `outputs/audits/progress_consolidation/`. Không chỉnh audit cũ để thay trạng thái hiện tại.

### Mẫu mục trong nhật ký ngày

```markdown
## Công việc / baseline liên quan

### Mục tiêu
- Baseline/hạng mục và đầu ra cần có.

### Đã làm và bằng chứng
- Lệnh/file/kết quả thật; phân biệt kiểm chức năng với đánh giá model.

### Quyết định và thay đổi trạng thái
- Hạng mục nào trong progress/README.md đã được cập nhật, vì sao.

### Còn thiếu và bước tiếp theo
- Việc cụ thể, điều kiện đạt; ghi giới hạn còn tồn tại.
```
