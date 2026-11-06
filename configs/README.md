**Version 11:** [config SGD v3](b0_s960_sgd_kaggle_v3.json) chỉ đổi optimizer so với AdamW v2 trong các tham số huấn luyện; đã gửi Kaggle, chưa có kết quả. [Đối chiếu nguồn và giới hạn](../docs/b0_pilot_audit.md#nghiên-cứu-và-thí-nghiệm-đối-chứng-sgd-version-11--30102026).

# Cấu hình

**Cấu hình thí nghiệm đã hoàn tất là snapshot lịch sử:** không sửa `output` trong config cũ để chạy lại vì sẽ đổi hash/provenance. Run mới cần config mới trỏ tới `outputs/baselines/<baseline>/vNNN_short_description/` và version được cấp trước; xem [kiến trúc artifact](../docs/STORAGE_ARCHITECTURE.md). Các lệnh `--run`/`--train` với output legacy được mô tả bên dưới là lịch sử, không còn là lệnh tạo output mới.

**05/11 — bản phát triển temporal mới:** [B2 v2](b2_motion_v2.json) thêm nhánh bbox overlap vào gate, giữ ngưỡng v1; [FSM v2](alert_fsm_v2.json) rearm theo score thấp đã quan sát; [trainer T0/GRU](temporal_supervised_v1.json) đang khóa train. Cả ba là giá trị thử nghiệm, chưa hiệu chuẩn trên tập validation độc lập.

**05/11 — công cụ temporal thử nghiệm:** [event_policy_v1.json](event_policy_v1.json) khóa quy tắc cạnh cảnh báo để replay; [b2_motion_v1.json](b2_motion_v1.json) và [alert_fsm_v1.json](alert_fsm_v1.json) ghi ngưỡng khởi tạo để kiểm chức năng, chưa tuning/benchmark. [Cách chạy và schema](../scripts/README.md#theo-dõi-sự-kiện-và-motion--05112026).

**04/11 — run B0 Kaggle đối chứng LR:** [`b0_s960_sgd_low_lr_kaggle_v4.json`](b0_s960_sgd_low_lr_kaggle_v4.json) giữ data/nhãn/split/checkpoint và `TRAIN_KEYS` của SGD V11, chỉ đổi `lr0=0,0003 → 0,00015`; GPU Kaggle miễn phí, val-only, tối đa 60 epoch, bắt đầu xét early stopping epoch25/patience25. Run đã kết thúc ở epoch50, kết quả local đã qua kiểm; chưa chọn làm checkpoint B0 hiện hành. Xem [số liệu và giới hạn](../docs/b0_pilot_audit.md#chuẩn-bị-version-12--đối-chứng-learning-rate-04112026).

**Version 10 đã hoàn tất:** config AdamW bên dưới đã chạy đủ 60 epoch, best CSV epoch52; log xác nhận AMP checks passed, không ghi OOM/giảm batch. Không sửa config khóa. [Báo cáo kết quả](../docs/b0_pilot_audit.md#kết-quả-version-10--adamw-kaggle-30102026).

**Thử nghiệm hiện hành:** [b0_s960_adamw_kaggle_v2.json](b0_s960_adamw_kaggle_v2.json), được khóa trước gửi Version 10. Giữ data/split/checkpoint, đổi SGD→AdamW, batch 2→8, AMP, nbs 64→32, cosine, augmentation nhẹ và tối đa 60 epoch; chỉ tính patience 25 sau epoch 25. Không sửa config đã gửi. Sau kiểm mã thư viện phát hiện config ghi không fallback nhưng Ultralytics có thể tự giảm batch khi OOM epoch đầu; theo dõi log thực và ghi rõ batch thực tế khi báo cáo. [Hướng dẫn](../docs/kaggle_training.md).

`b0_accident_scaled_v1.json` và `b0_scaled_label_policy.json` là thí nghiệm mở rộng lịch sử ngày 26/10, dùng âm chưa rà và đã bị thu hồi; `expanded_pilot_release.can_train=false`. Không xóa file/hash để giữ lịch sử. Trạng thái chạy xem [bảng tiến độ](../progress/README.md).

`b0_accident_scaled_v2.json` là lần chạy lại lịch sử 27/10 đã dừng do phạm vi âm chưa phù hợp, không dùng checkpoint đó làm kết quả B0. `b0_verified_pilot_v1.json` và `b0_verified_label_policy.json` là run mới chỉ dùng âm có review hoặc nhãn normal tác giả; `verified_pilot_release` khóa hash riêng. Trạng thái xem [nhật ký](../progress/2026-10-27.md).

**Cấu hình đang dùng:** `b0_public_label_policy.json` v4 ghi định nghĩa vùng B0 theo STTAD và bbox impact ACCIDENT đã rà, xử lý unknown, nguồn nhãn và nhóm cảnh. Hộp impact chỉ dùng tại đúng frame đã kiểm PTS; vùng thiếu/chưa rõ phạm vi bị loại. Release pilot ảnh được tách khỏi benchmark đầy đủ; không biến bbox xe thành GT vùng tai nạn.

Trường `status`/`training_release_allowed=false` trong policy nói về benchmark đầy đủ; `pilot_training_release_allowed=true` cùng `data/b0_readiness.json/pilot_release` cấp đúng phạm vi thí nghiệm ảnh đã khóa hash. Không sửa policy sau run vì hash của bản đã train nằm trong release.

`b0_pilot.json` khóa cấu hình thí nghiệm B0 ảnh đầu tiên: YOLOv8n local, split 47 ảnh ACCIDENT, seed 20261026, 40 epoch tối đa, early stop, ảnh 640, batch 4, CUDA và ngưỡng đánh giá. Kết quả thực tế lưu ở `outputs/training/b0_basic_pilot_v1/experiment.json`; thay đổi tham số/dữ liệu cần run mới, không ghi đè checkpoint cũ.

`cadp_1407_preview.json` chỉ lưu căn chỉnh của **demo đã render** 1407: hash MP4/TXT, canvas và phép biến đổi từ tọa độ VATIC vào vùng ảnh Matplotlib. `prepare_cadp_pilot.py` kiểm hash và ZIP tham chiếu trước khi áp mapping; không dùng config này cho video sạch hoặc mẫu khác.

`b0_region_proposal.json` giữ quy tắc envelope CADP lịch sử. `prepare_b0_candidates.py` xuất hộp bao participant dẫn xuất, không phải bbox vùng tác giả hoặc config train. Giữ riêng với nhãn STTAD. [Định nghĩa và giới hạn](../docs/b0_label_protocol.md).

Các file giữ đường dẫn để code/hash/provenance còn khớp. Pilot đã có `data/processed/b0_basic_pilot_v1/{split.csv,dataset/dataset.yaml}` local; media/checkpoint lớn bị Git ignore. Bộ benchmark B0 đầy đủ chưa phát hành.

## Chẩn đoán sau train

`b0_diagnostics_v1.json` khóa checkpoint mốc, ngưỡng suy luận đã dùng, hash từng ảnh/video/review và vai trò dữ liệu trong một lượt kiểm hậu nghiệm. Không là config train. `scripts/analyze_b0.py --check` không nạp model; `--run` tạo `outputs/training/b0_verified_pilot_v1/diagnostics/`, không ghi đè lần đã có. Nhãn normal dựa trên review hoặc clip label tác giả; CADP chỉ dùng interval theo frame, không biến thành GT vùng accident hoặc suy FPS nguồn.

## Normal mở rộng B0

`b0_normal_expansion_v1.json` là plan tải 18 member **train/normal** TAD, khóa CRC/size và giữ path nguồn. `b0_normal_expanded_label_policy.json` chỉ mở pilot dùng nhãn verified, không thay policy của các release cũ. `b0_normal_expanded_v1.json` là config train cho dataset mới 2.170 ảnh; giữ recipe LR 0,001 đủ 60 epoch, chỉ đánh giá validation. Các trường `reference_experiments`/`reference_validation_output` cho `analyze_b0.py --validation-reference`, không phải checkpoint khởi tạo train. Holdout âm mới được giữ ngoài YAML train/val; test cũ vẫn là test đã tiêu thụ. [Nguồn, kết quả và lệnh](../docs/b0_pilot_audit.md#b0-normal-mở-rộng--28102026).
## Công thức B0 chuẩn bị sau normal-expanded (28/10)

`b0_s960_v1.json` giữ dataset/release/split, đổi sang YOLOv8s pretrained960, batch2,100epoch và augmentation nhẹ hơn. Có SHA trọng số riêng do GitHub công bố, không đổi SHA model n trong release. `train_b0.py` truyền các tham số augmentation tường minh và kiểm chúng khi resume. Trạng thái **đã hoàn tất45epoch; early stopping patience15 được ghi trong resume_events**, config gốc giữ patience0 để bảo toàn snapshot. [Kết quả](../docs/b0_pilot_audit.md#kết-quả-b0-s960-hoàn-tất--28102026). Mục tiêu mAP50 val>70% là giả thuyết, không phải kết quả. [Căn cứ và lệnh](../docs/b0_pilot_audit.md#chuẩn-bị-b0-s960--28102026).

`b0_s960_v1_operating_point_v1.json` khóa checkpoint s960/conf0,27 và SHA report val trước khi mở holdout. Đây là cấu hình inference B0 ảnh, không config train và không model phát hiện xe. Kết quả holdout34/120ảnh có dự đoán ở tập normal tác giả; điểm vận hành này chưa là hệ thống cảnh báo đã xác minh. Không sửa khóa theo holdout; [báo cáo](../docs/b0_pilot_audit.md#chọn-ngưỡng-và-đánh-giá-holdout-âm--29102026).

## Chuẩn bị29/10: B1 và fine-tune với âm khó

- `b1_causal_diagnostics_v1.json`: phép đo đã chạy, cùng s960/conf0,27,3-of-5 và EMAalpha0,3; không phải config train. Khóa reset/warmup, vai trò từng nguồn và giới hạn timing.
- `b0_hard_negative_sources_v1.json`: đúng24member TAD normal,259,67MiB raw,60ảnh ứng viên/clip. Công cụ tải có budget384MiB và ledger bảo thủ; `--resume-fetch` chỉ tiếp tục audit chưa hoàn tất, kiểm CRC/size của file cũ.
- `b0_hard_negative_label_policy.json`: pilot mới dùng cùng impact positives, thêm normal tác giả; nhóm/split khóa trước mining, không đổi nhãn theo score. Cảnh nghi liên quan consumed test bị loại.
- `b0_s960_hardneg_v1.json`: **đã train xong15epoch, bestCSV5, patience10**, chỉ đo307val. Khởi tạo từ `b0_s960_v1/weights/best.pt`, optimizer mới, SGD0,0003, trần40; s960/batch2/FP32/workers0 giữ nguyên. Không sửa config/requested_config sau run hoặc gọi train/resume vào output hoàn tất. `--check` vẫn kiểm hash được; preflight/reference chỉ là hồ sơ trước train. [Kết quả](../docs/b0_pilot_audit.md#kết-quả-s960-hardneg-hoàn-tất--29102026).

Nguồn, khác biệt với SSD/fine-tuning guide và giới hạn ghi ngay trong config; [chi tiết dữ liệu và lệnh](../docs/b0_pilot_audit.md#chuẩn-bị-s960-hardneg-v1--29102026). Không đảm bảo mAP50>70% trước khi có kết quả train/val mới.

## RunKaggle chuẩn bị theo yêu cầu29/10

`b0_s960_full_kaggle_v1.json` dùng trainer chung và portable bundle:2681train/307val, không cótest media/YAML. Toàn bộ`TRAIN_KEYS` giữ như hardnegv1, khởi tạo cùngSHA c1fdd6dc…019302; tênrun/path/environment mới. `b0_kaggle_full_label_policy.json` chỉ mở phần420normal ứng viên bổ sung trong nhómtrain đã khóa; không đổi nhãn/split cũ, không thêm sự kiện độc lập. Manifest bundle chứng minh mapping/hash trướctrain; không chỉnh fingerprint release cũ vì Windows/Linux khácpath. **Chưa train: hiện thiếu đăng nhập Kaggle**. [Cáchgửi/nhận](../docs/kaggle_training.md); không chạy trực tiếp configcloud trênlaptop thiếubundle hoặc gọiresume vào outputcũ.
