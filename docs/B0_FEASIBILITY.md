# B0 thử nghiệm khả thi — 16/11/2026

Đã fine-tune YOLOv8n thành detector một lớp `accident`, lưu checkpoint và đo trên các cảnh validation khác train. Pipeline dữ liệu/huấn luyện chạy được, **model chưa đủ tin cậy để cảnh báo**: tại confidence 0,25 và IoU 0,5, validation có TP=0, FP=0, FN=12. Đây là thử nghiệm phát triển nhỏ, không phải nghiệm thu B0 nghiên cứu hoặc kết quả trên test khóa.

## Dữ liệu và phạm vi nhãn

Nguồn là bốn chuỗi ảnh ví dụ từ [repository STTAD của tác giả](https://github.com/ZTR02/STTAD), ghim commit `21f3f5fea50b071f1db61186b481c2a7ccf525c9`. Đây không phải toàn bộ benchmark. [Registry](../data/registries/sttad_selected_sources.json) ghi 212 tệp; đã kiểm Git blob của từng tệp. Trong 176 ảnh giải mã được, 31 ảnh có nhãn vùng nguồn. Lớp nguồn 6/11 được ánh xạ về lớp 0 `accident`; tọa độ nguồn pixel xyxy được chuyển sang YOLO chuẩn hóa theo kích thước từng ảnh.

Chỉ 12 frame đầu (1, 2, 3 của từng cảnh) được thêm nhãn âm sau khi agent xem ảnh, với SHA trong [phiếu rà](../data/reviews/2026-11-16-sttad-feasibility-frame-review.json). Đây là review của agent, chưa có đối soát độc lập của người dùng/giảng viên; không phải xác nhận toàn video âm. 133 ảnh còn lại vẫn unknown và bị loại; hai tệp đuôi JPG chứa văn bản cũng bị loại, nguồn giữ nguyên.

| Split phát triển | Cảnh nguồn | Ảnh dương | Ảnh âm | Tổng |
| --- | --- | ---: | ---: | ---: |
| Train | T-T_crash_1, V-V_crash_0 | 19 | 6 | 25 |
| Validation | T-T_crash_2, V-V_crash_1 | 12 | 6 | 18 |

Split theo trọn cảnh đã cố định trước huấn luyện. Không có ảnh trùng SHA giữa hai phần; khoảng cách pHash nhỏ nhất là 24 (chốt loại ≤8). Đây chỉ là sàng lọc ảnh gần trùng, không chứng minh camera/sự kiện độc lập. ID camera gốc và timestamp/FPS chưa xác minh. Không tạo test và không báo metric sự kiện, delay hay false alerts/hour.

**Không dùng** 35 proposal CADP chưa duyệt làm GT. `data/manifest.csv`, `data/b0_readiness.json`, `configs/b0_region_proposal.json` giữ nguyên hash sau chạy. Gate nghiên cứu chính thức vẫn chưa đạt; thử nghiệm này có `purpose=software_feasibility_only`, không tự cho phép chuyển B1/verifier/FSM.

## Cấu hình và đầu ra thực tế

[Config cố định](../configs/b0_feasibility.json): YOLOv8n pretrained, 12 epoch, ảnh 640, batch 2, AdamW lr 0,001, freeze 10, seed 0, deterministic, CPU 4 thread, worker 0, AMP tắt. Các augmentation ảnh bị tắt trong lượt kiểm tra ban đầu này. Không thay model hoặc chỉnh ngưỡng sau khi thấy validation. Máy chạy Python 3.12.16, torch 2.11.0+cpu, torchvision 0.26.0+cpu, ultralytics 8.4.178. Thời gian gọi huấn luyện đo được **49,67 giây**, không phải benchmark suy luận toàn hệ thống.

Đầu ra trên máy này:

- [Checkpoint best.pt](../outputs/experiments/b0_feasibility_2026-11-16/train/weights/best.pt), 6.479.210 byte; SHA-256 `16352246565cd707b8125b836839efb5199631a02a50ab3bee608f5e4008b794`.
- [Báo cáo chạy](../outputs/experiments/b0_feasibility_2026-11-16/report.json), [metadata package/code/input](../outputs/experiments/b0_feasibility_2026-11-16/run_metadata.json), [log epoch](../outputs/experiments/b0_feasibility_2026-11-16/train/results.csv).
- [Rà đủ 18 ảnh validation](../outputs/experiments/b0_feasibility_2026-11-16/validation_cases.jpg): xanh là vùng nguồn, cam là dự đoán ở ngưỡng 0,25; không có dự đoán ở ngưỡng này.
- [Biểu đồ train/validation](../outputs/audits/b0_feasibility_2026-11-16/generalization/confidence_by_split.png), [số liệu từng ảnh](../outputs/audits/b0_feasibility_2026-11-16/generalization/frames.csv), [báo cáo chẩn đoán](../outputs/audits/b0_feasibility_2026-11-16/generalization/report.json).
- [Snapshot nhỏ đọc được sau clone](evidence/2026-11-16-b0-feasibility.json). Media/checkpoint/dataset/audit đầy đủ vẫn là tệp cục bộ, không có sau clone.

## Kết quả và phân tích lỗi

| Phép đo | Train — chỉ chẩn đoán | Validation phát triển |
| --- | ---: | ---: |
| Ảnh dương có bbox ghép IoU≥0,5 tại conf≥0,25 | 17/19 | 0/12 |
| Ảnh âm có dự đoán tại conf≥0,25 | 3/6 | 0/6 |
| Median confidence của bbox ghép IoU≥0,5, thu thập từ conf≥0,001 | 0,51019 | 0,00669 |

Ultralytics đo trên validation: mAP50 **0,01208** (khoảng 1,21%), mAP50–95 **0,00347**, precision **0,02624**, recall **0,16667**. Các giá trị AP/PR được tính theo đường điểm confidence, **khác** bộ đếm cố định tại 0,25. Không dùng recall của đường PR để tuyên bố bắt được sự kiện tại ngưỡng demo. Train không phải tập đánh giá.

Tại ngưỡng cố định validation bỏ sót cả 12 vùng; việc FP=0 không chứng minh khả năng loại cảnh báo sai vì detector không trả vùng nào. Chỉ sáu ảnh âm cũng không đo được false alerts/hour. Model bắt được nhiều vùng trên train nhưng không chuyển sang hai cảnh validation; đây là bằng chứng phù hợp với học phụ thuộc cảnh trên pilot quá nhỏ, **chưa chứng minh nguyên nhân duy nhất**. Ba ảnh âm train có dự đoán cũng là lỗi thật cần giữ lại. Tăng epoch hoặc giảm confidence để có khung trên demo chưa giải quyết được những lỗi này.

## Chạy lại

Cần khôi phục nguồn STTAD theo [ghi nhận nguồn](RESEARCH_NOTES.md)/catalog và có trọng số gốc đúng hash. Dùng `.venv` đúng pin; không tự tải toàn dataset. Các lệnh dưới dùng thư mục mới để giữ lượt đầu:

```bash
.venv/bin/python -B scripts/prepare_b0_feasibility.py --feasibility-only \
  --output data/processed/b0_feasibility_repeat
.venv/bin/python -B scripts/run_b0_feasibility.py --feasibility-only \
  --dataset data/processed/b0_feasibility_repeat \
  --output outputs/experiments/b0_feasibility_repeat
.venv/bin/python -B scripts/analyze_b0_generalization.py \
  --dataset data/processed/b0_feasibility_repeat \
  --experiment outputs/experiments/b0_feasibility_repeat \
  --output outputs/audits/b0_feasibility_repeat_generalization
```

Công cụ từ chối ghi đè thư mục và kiểm lại source/export/config/review/checkpoint. Seed/config giúp tái lập; không hứa bitwise giống khi thay hệ điều hành/phần cứng/thư viện. Bộ test ngày 16/11 có **53/53 đạt**, gồm bảy kiểm thử mới cho nhãn âm có bằng chứng, unknown không tự thành âm, chống rò rỉ/hash mismatch và phân biệt thử nghiệm với nghiên cứu.

## Việc tiếp theo

1. Rà quy tắc vùng accident nhất quán giữa các cảnh; đối soát nhãn âm bởi người thứ hai, giữ riêng nhãn mơ hồ. Chốt riêng 35 proposal CADP trước khi dùng làm GT.
2. Ưu tiên bổ sung các cảnh có nhãn nguồn và camera/sự kiện độc lập, kèm hard negatives cùng miền; ghi registry/hash trước khi chọn thêm ảnh. Nhiều frame liền nhau không thay được nhiều sự kiện.
3. Lập split theo nhóm có bằng chứng và test khóa; chạy lại B0 với ngân sách cố định, giữ lượt này làm mốc, phân tích FP/FN theo cảnh. Chỉ chuyển bước khi đạt điều kiện trong README gốc.

Dashboard hiện vẫn trình diễn vehicle detection/tracking và review thủ công. Word/slide/ZIP ngày 14/11 là snapshot trước thử nghiệm này, chưa được cập nhật thành báo cáo nghiên cứu hoàn chỉnh.
