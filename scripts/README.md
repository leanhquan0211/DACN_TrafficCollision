**B0 Version 11:** `analyze_b0_training_data.py --help` thống kê nhóm nguồn/diện tích bbox và lỗi val đã lưu; `kaggle_b0.py logs --follow --epochs-only --version 11` theo dõi, `fetch --experiment sgd-v3 --version 11` lấy sau khi hoàn tất. [Hướng dẫn](../docs/kaggle_training.md#version-11--đối-chứng-sgd).

# Chọn đúng lệnh để chạy

**Kaggle Version 10 đã hoàn tất và đã fetch:** `logs --epochs-only --version 10` đọc lại một dòng mỗi epoch; `prepare-recipe`, `publish-recipe` và `fetch --experiment adamw-v2 --version 10` đã thực hiện, không gọi lại vào cùng output. Kiểm [báo cáo](../docs/b0_pilot_audit.md#kết-quả-version-10--adamw-kaggle-30102026). Các dòng Version 8 bên dưới là lịch sử.

Chạy từ gốc project bằng `.\.venv\Scripts\python.exe`. Không cần chạy tất cả script mỗi buổi. Ý nghĩa thuật ngữ: [GLOSSARY](../reference/GLOSSARY.md). Lộ trình hiện tại: [README](../README.md).

## 1. Thường dùng

| Việc muốn làm | Điểm bắt đầu | Kết quả |
| --- | --- | --- |
| Kiểm môi trường | `check_environment.py` | Phiên bản thư viện/CUDA, không thay môi trường |
| Kiểm dữ liệu có trên máy | `check_project_assets.py --check-hashes` | Trạng thái file/hash theo catalog, không tải |
| Xem thông tin video | `inspect_video.py <video>` | Metadata và kiểm đọc frame đầu |
| Thử detection và tracking | `run_all.py <video>` | Chạy inspect → detection → tracking trên video gốc |
| Chỉ detection / chỉ tracking | `run_detection.py` / `run_tracking.py` | MP4 bbox xe / bbox + ID tạm |

```powershell
.\.venv\Scripts\python.exe scripts/run_all.py "data_samples/TEN_VIDEO.mp4" --device auto --imgsz 640 --output-dir outputs
```

Thay tên video thật. `yolov8n.pt` phát hiện phương tiện, chưa kết luận tai nạn. `run_all.py` là bộ gọi các tiến trình; vòng frame nằm trong `src/video_pipeline.py`. Các CLI có `--help`; không đổi model/tham số để thử chỉ vì sắp xếp lại thư mục.

## 2. Dữ liệu và B0 — dùng khi cần chuẩn bị/tái tạo

| Script | Mục đích | Xem hướng dẫn |
| --- | --- | --- |
| `audit_sttad_public.py` | Lấy chọn lọc bốn chuỗi public hoặc kiểm offline, chuyển nhãn nguồn | [GETTING_STARTED mục D](../docs/GETTING_STARTED.md) |
| `audit_accident_public.py` | Tải member chọn lọc; kiểm impact/PTS; `--prepare-preimpact` tạo ứng viên UNKNOWN, `--verify-preimpact` so pixel/PTS trước rà | [Nguồn và batch 20 clip](../docs/b0_pilot_audit.md) |
| `download_accident_real.py` | Tải tiếp nối phần real xe–xe ACCIDENT v9 có bbox hợp lệ, ghi SHA/receipt; không tải synthetic | [Mở rộng B0](../docs/b0_pilot_audit.md) |
| `prepare_accident_scale.py` | Giải mã và kiểm mapping tác giả; trích PNG impact, TXT YOLO và ứng viên âm trước impact, giữ nguồn nhãn | [Mở rộng B0](../docs/b0_pilot_audit.md) |
| `prepare_b0_scaled_release.py` | `--verified` khóa index/split, chỉ nhận âm có review hoặc nhãn normal tác giả; kiểm fingerprint media | [Policy hiện hành](../configs/b0_verified_label_policy.json) |
| `inspect_public_zip.py` | Đọc member ZIP qua HTTP Range; `--prepare-normal-test` kiểm CRC/giải mã và trích frame TAD test/normal | [Nguồn âm TAD](../docs/b0_pilot_audit.md) |
| `audit_pilot_groups.py` | Fingerprint frame, gợi ý cảnh gần, so nhóm nguồn; `--exported-dataset` gợi ý cặp gần giống xuyên split YOLO | [Kiểm nhóm B0](../docs/b0_pilot_audit.md) |
| `prepare_b0_pilot_index.py` | Ghép batch/review; kiểm pool; `--make-pilot-split` chia theo nhóm nguồn; `--export-split --release-kind pilot` xuất YOLO sau gate/hash | [Pilot và lệnh kiểm](../docs/b0_pilot_audit.md#pilot-b0-ảnh-26102026) |
| `train_b0.py` | Kiểm release/export; fine-tune và đo bbox; `--resume` tiếp tục run dở từ checkpoint/optimizer khi config khớp và không còn process train | [Config](../configs/b0_verified_pilot_v1.json), [kết quả](../docs/b0_pilot_audit.md) |
| `evaluate_b0_clean.py` | Đo checkpoint trên test đã khóa; có thể so checkpoint cũ và probe TAD normal cùng ngưỡng | [Phiếu loại](../data/reviews/2026-10-27-b0-near-duplicate-review.json) |
| `analyze_b0.py` | Phân tích lỗi từ prediction đã lưu; chạy checkpoint B0 hiện hành trên 9 chuỗi sạch, xuất log mỗi frame/MP4 và trang HTML | [Chẩn đoán B0](../docs/b0_pilot_audit.md#chẩn-đoán-lỗi-ảnh-và-video-b0--27102026), [config khóa nguồn](../configs/b0_diagnostics_v1.json) |
| `prepare_detrac.py` | Lấy chọn lọc chuỗi DETRAC, kiểm ảnh và ghép MP4 | [Dựng lại dữ liệu](../docs/GETTING_STARTED.md) |
| `prepare_cadp_frames.py` | Kiểm ảnh sạch CADP, mapping, ghép video/preview | [CADP chi tiết](../docs/cadp_001407_clean.md) |
| `prepare_cadp_pilot.py` | Đọc VATIC và đối chiếu demo tác giả đã vẽ | [Chuẩn bị ban đầu](../docs/dataset_preparation.md) |
| `prepare_b0_candidates.py` | Chuẩn hóa VATIC và xuất envelope đề xuất CADP, không GT vùng tác giả | [Quy tắc nhãn](../docs/b0_label_protocol.md) |
| `audit_cadp_b0_quality.py` | Ghi lý do giữ/loại frame dẫn xuất theo flags | [Kiểm chất lượng](../docs/b0_label_protocol.md) |
| `prepare_b0_negative_index.py` | Kiểm/lập chỉ mục DETRAC âm đã review | [Hướng dẫn nguồn/hash](../docs/GETTING_STARTED.md) |

Output đã có thì mở để đọc; chỉ chạy lại khi cần kiểm hoặc tái tạo một phiên bản. Công cụ xuất/train từ chối ghi đè. `train_b0.py --check` kiểm đầu vào mà không chạy GPU. Gate benchmark đầy đủ vẫn đóng; mỗi pilot có release và config riêng. Khi tái tạo trên máy khác, đọc [GETTING_STARTED](../docs/GETTING_STARTED.md) và dùng output/run name mới.

## 3. `maintenance/` — bảo trì metadata, không chạy theo thói quen

Ba script đã chuyển vào đây để tách khỏi workflow video/dữ liệu thường dùng:

| File | Khi nào dùng |
| --- | --- |
| `maintenance/register_prepared_manifest.py` | Đăng ký asset từ báo cáo CADP/DETRAC khi thực sự cần thêm vào manifest |
| `maintenance/update_manifest_reviews.py` | Áp phiếu review có phạm vi/hash và đăng ký CADP sạch theo quy trình lịch sử |
| `maintenance/apply_cadp_frame_review.py` | Áp phiếu xác nhận frame CADP phù hợp; không thay annotation nguồn |

Ví dụ xem tùy chọn, chưa thực hiện cập nhật:

```powershell
.\.venv\Scripts\python.exe scripts/maintenance/apply_cadp_frame_review.py --help
```

Nhật ký/báo cáo cũ có thể ghi `scripts/update_manifest_reviews.py` theo đường dẫn lúc chạy. Đường dẫn thực thi hiện nay là `scripts/maintenance/update_manifest_reviews.py`; lịch sử không bị sửa. Những công cụ này giữ backup và kiểm hash/ID; không dùng để đăng ký lại toàn manifest hiện có.

## Normal expansion 28/10 — các chế độ đã dùng

Công cụ hiện có được mở rộng, không có pipeline tải/split song song:

- `inspect_public_zip.py --fetch-plan configs/b0_normal_expansion_v1.json --max-mib 256 --audit-dir outputs/audits/b0_normal_expansion_v1`: lấy đúng 18 member đã khóa CRC/size, giữ raw path.
- `inspect_public_zip.py --prepare-normal-batch configs/b0_normal_expansion_v1.json`: offline, đọc đủ clip và trích frame trước prediction.
- `audit_pilot_groups.py --normal-batch <normal_manifest.json> --base-dataset <dataset-cũ> --consumed-normal-probe <probe.json>`: rà cảnh/near-duplicates, bbox nhỏ và ảnh đối chiếu; không tự chia tập theo hash.
- `prepare_b0_scaled_release.py --normal-expansion-review data/reviews/2026-10-28-b0-normal-expansion-review.json`: khóa release mới, giữ split cũ và reserve ngoài train/val, xuất dataset; chế độ này đã chạy xong, không chạy lại để ghi đè.
- `analyze_b0.py --config configs/b0_normal_expanded_v1.json --validation-reference`: đo ba checkpoint cũ trên val mới, không đo test/reserve; mốc này đã có.

[Trang kết quả và lệnh train tiếp](../docs/b0_pilot_audit.md#b0-normal-mở-rộng--28102026). `train_b0.py --config configs/b0_normal_expanded_v1.json --check` là lệnh kiểm thường dùng tiếp theo; `--train` tạo run mới, hiện chưa chạy.

**Cập nhật sau đó 28/10:** normal-expanded đã train xong. Công thức `configs/b0_s960_v1.json` **đã chạy xong45epoch và đánh giá val**; không chạy lại train/resume vào output đã hoàn tất; [lệnh hiện hành](../docs/b0_pilot_audit.md#chuẩn-bị-b0-s960--28102026). Hai chế độ kiểm có thể tái dùng:

- `analyze_b0.py --config <config-train-đã-xong> --saved-validation`: phân tích prediction val có sẵn, tạo contact sheet/thống kê trong `diagnostics/`, từ chối ghi đè.
- `train_b0.py --config <config-mới> --preflight`: kiểm ảnh/bbox và forward GPU, không tạo optimizer/backward hoặc train. Config cần `preflight_report` chưa tồn tại; hồ sơ đã có thì đọc lại, dùng `--check` để kiểm hash hiện tại.

## Chọn điểm vận hành sau train — 29/10

- `analyze_b0.py --config configs/b0_s960_v1.json --select-operating-point`: cache đúngval, quét confidence và ghi khóa; đã chạy, từ chối ghi đè.
- `analyze_b0.py --config configs/b0_s960_v1_operating_point_v1.json --evaluate-operating-holdout`: chỉ đo một lần tập âm bằng khóa sẵn. **Đã chạy xong, không chạy lại**; manifest đánh dấu consumed.
- Chỉ mở `outputs/training/b0_s960_v1/operating_point_v1/index.html` để xem lại. Việc xem report/cache không chạy model; không sửa manifest để vượt chặn.

[Phép kiểm, nguồn và kết quả](../docs/b0_pilot_audit.md#chọn-ngưỡng-và-đánh-giá-holdout-âm--29102026). Không có train hoặc video B1 mới trong bước này.

## Chuẩn bị tiếp29/10 — các chế độ mở rộng

Phần chọn ngưỡng phía trên là lịch sử; sau đó đã bổ sung:

- `analyze_b0.py --config configs/b1_causal_diagnostics_v1.json --temporal-diagnostics`: cùng một lượt inference so B0/EMA/k-of-N, lưu CSV/JSONL/MP4 và đọc lại. Đã chạy xong; xem HTML, không chạy lại để ghi đè.
- `inspect_public_zip.py --resume-fetch ...`: tiếp tục audit tải chưa hoàn tất; ledger giữ tổng budget bảo thủ qua các lần lỗi. Không dùng cho audit đã có report hoàn tất.
- `prepare_b0_scaled_release.py --mine-normal-groups outputs/audits/b0_hard_negative_sources_v1/groups_before_mining.json`: chỉ xếp hạng frame train sau khóa nhóm/split; val/reserve lấy đều, không suy luận. Đã chạy xong.
- `prepare_b0_scaled_release.py --normal-expansion-review data/reviews/2026-10-29-b0-hard-negative-review.json --output data/processed/b0_s960_hardneg_v1`: xuất phiên bản mới, giữ toàn bộ split/nhãn cũ. Không chạy lại lên output đã có.
- `train_b0.py --config configs/b0_s960_hardneg_v1.json --check`: kiểm có thể lặp lại, không train. `--preflight` và `analyze_b0.py --validation-reference` tạo bằng chứng một lần; đọc lại report nếu đã có.

Lệnh train **do người dùng tự chạy**, cùng giải thích LR/early stopping và kết quả kiểm nằm trong [báo cáo B0](../docs/b0_pilot_audit.md#chuẩn-bị-s960-hardneg-v1--29102026).

**Cập nhật sau train29/10:** hardneg đã hoàn tất15epoch, bestCSV5; không chạy lại lệnh train/resume vào output cũ. Đã dùng `analyze_b0.py --config configs/b0_s960_hardneg_v1.json --saved-validation` để kiểm/phân tích307prediction đã lưu, không suy luận mới. Kết quả ở`outputs/training/b0_s960_hardneg_v1/diagnostics/`; chế độ này từ chối ghi đè nên mở HTML/report để xem lại. [Báo cáo mới](../docs/b0_pilot_audit.md#kết-quả-s960-hardneg-hoàn-tất--29102026).

## Train KagglePRIVATE — không train laptop

`kaggle_b0.py` tái sử dụng`train_b0.py` và`src/training_bundle.py`, không có trainer YOLO song song:

- `prepare`: kiểm release cũ, thêm đủ normal ứng viên thuộctrain, đóngZIP allowlist và sinh notebook/metadataPRIVATE; **đã chạy**, không chạy lại để ghi đè.
- `verify`: kiểmCRC/hash tất cảfileZIP, không giải nén toàn raw hoặc train.
  - `publish`: tạo/gửi PRIVATE Dataset/Notebook cho run ban đầu, state chống gửi lại. Dataset đã có; run mới dùng `publish-recipe` và đã gửi Version 10. Không gọi lại để tạo run trùng; xem status/logs.
- `status`: đọc trạng thái một lần khi người dùng cần, không pollingloop.
  - `logs`: đọc log Kaggle một lần, lưu `latest_remote_logs.txt` trong staging; `logs --follow --epochs-only --version 10` xem từng epoch của phiên mới, Ctrl+C chỉ ngắt xem. `status --version 10` đọc đúng phiên. Không train/upload khi xem log; RUNNING/COMPLETE của phiên chẩn đoán không phải kết quả train.
- `fetch`: tảiZIP/receipt, kiểmhash và nhập vào runcloud mới; không tự test/reserve hoặc thay điểm vận hành B0.
- `bootstrap`/`execute`: chỉ trongKaggle; càiPython/thư viện khóa, kiểmGPU/data/forward rồi mới gọi trainer cũ. Trênlaptop bị chặn trước train.

[Hướng dẫn và lệnh cụ thể](../docs/kaggle_training.md). Gói/lầnchạy ở`outputs/kaggle/b0_s960_full_kaggle_v1/`, kết quảcloud sau khi nhận ở`outputs/training/b0_s960_full_kaggle_v1/`. Không resume hardneg15epoch đã hoàn tất; không upload`.venv`,cache,raw hoặc credential.
