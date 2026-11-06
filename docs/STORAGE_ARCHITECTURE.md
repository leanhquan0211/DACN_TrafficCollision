# Kiến trúc lưu artifact chính thức

Áp dụng cho **output mới từ 06/11/2026**. Lịch sử giữ đường dẫn và hash gốc; vị trí cũ được hiển thị là `LEGACY` trong cùng registry. Tài liệu này nói về lưu file, không đổi baseline, dữ liệu, nhãn, split hoặc metric.

## Các lớp dữ liệu

| Lớp | Vị trí | Quy tắc |
| --- | --- | --- |
| Nguồn công bố | `data_raw/`, `data_samples/` | Chung cho mọi baseline, giữ cấu trúc/hash; không chuyển vào `outputs/` hoặc nhân bản. |
| Release huấn luyện | `data/processed/` cùng `data/registries/` | Dataset dẫn xuất và split có provenance; nhiều run đọc cùng release. Không đưa vào từng baseline. |
| Kết quả baseline | `outputs/baselines/<mã>/vNNN_short_description/` | Checkpoint, config thực tế, log, dự đoán và chẩn đoán thuộc một baseline. |
| Đánh giá chung | `outputs/shared_evaluations/vNNN_short_description/` | So B0/B1/B2 hoặc benchmark sự kiện cùng policy. |
| Bằng chứng hệ thống | `outputs/system_evidence/vNNN_short_description/` | Video inference, cảnh báo, clip/ảnh evidence và pipeline tích hợp. |
| Audit dữ liệu | `outputs/data_audits/vNNN_short_description/` | Kiểm nguồn, chất lượng, mapping, kiểm kê và chẩn đoán dữ liệu. |
| Lịch sử | Đường dẫn cũ được đánh dấu `LEGACY`; `_legacy/` chỉ dùng sau một migration có manifest/verify/rollback | Không tự tạo symlink hoặc copy checkpoint/archive để gom cây. |

Thư mục baseline cố định: `01_b0_image_detection`, `02_b1_temporal_filter`, `03_b2_motion_rules`, `04_t0_mlp`, `05_b3_gru`. Tên version dùng ba chữ số và mô tả tiếng Anh ngắn, ví dụ `v013_impact_validation`; **không dùng ngày tháng**. Run ID, alias version và Kaggle Notebook Version là ba khóa khác nhau; registry giữ ánh xạ, không đổi tên run lịch sử. Tăng `vNNN` trong đúng nhánh khi cần run mới, không ghi đè.

## Registry và resolver

`data/registries/project_explorer.json` là registry duy nhất cho baseline, run cũ, alias move, artifact đã đăng ký và bộ sưu tập legacy. `src/storage_paths.py` là API trung tâm: `output_path()` dựng path mới, `require_output_path()` từ chối write ngoài cây chuẩn, `artifact_path()` giải alias cũ/mới, `run_folder()` tìm run, `artifact_catalog()` ghép registry, discovery canonical và các thư mục legacy chưa phân loại. API chỉ đọc, không quét media/checkpoint để liệt kê. `artifact_identity.json` tùy chọn trong run mới nối run ID với thư mục version; Kaggle fetch ghi nó sau khi xác minh ZIP. Dashboard `/api/artifacts` và Explore → **Tìm artifact** dùng cùng catalog, hiện trạng thái `CANONICAL`/`LEGACY` và đường dẫn vật lý thật. `available=false` nghĩa là clone này chưa có file, không xóa hồ sơ nguồn.

Đường dẫn từ config/snapshot cũ được mở qua `artifact_path()`. Khi cả hai vị trí cùng tồn tại, resolver báo lỗi thay vì tự chọn. Mọi file `experiment.json`, checkpoint, config hash và split lịch sử vẫn giữ byte gốc. Snapshot lịch sử có path cũ là bằng chứng thời điểm đó, không sửa hồi tố.

## Kiểm kê entry point ghi output

Run B0/T0/B3 mới ghi `artifact_identity.json` ngay khi tạo thư mục version để Explore nhận diện đúng baseline; trang Huấn luyện chỉ tổng hợp B0. Kaggle fetch đã được thử bằng ZIP fixture trên Windows: manifest/SHA/checkpoint được kiểm, file nhận lại giữ nguyên byte và registry chuyển sang vị trí canonical. Không có lệnh tải từ Kaggle thật trong lượt kiểm này.

| Nhóm | Entry point | Tình trạng từ lượt này |
| --- | --- | --- |
| B0 train | `train_b0.py` | `--train`, `--preflight` và `--resume` local kiểm cây canonical; run lịch sử hoàn tất giữ bất biến. Bundle Kaggle lịch sử đã khóa vẫn chạy trong `/tmp` theo config nguyên bản. `--check` chỉ đọc. Config B0 cũ chưa được sửa để tránh đổi SHA. |
| B0 hậu phân tích | `analyze_b0.py`, `analyze_b0_training_data.py` | File phân tích train/val mới mặc định `data_audits`. `analyze_b0.py` khóa các mode ghi vào canonical theo vai trò; config cũ trỏ legacy sẽ bị từ chối, cần config mới để tái chạy. Phần tính toán/đầu ra bên trong vẫn đọc cấu trúc run lịch sử, nên **chưa chuyển hết**. |
| T0/B3 train | `train_temporal_verifier.py` | `--check` chỉ đọc; `--train` mặc định `baselines/04...` hoặc `05.../v001_supervised_pilot`, từ chối output ngoài cây. Gate readiness cũ giữ nguyên. |
| Video inference | `run_all.py`, `run_detection.py`, `run_tracking.py`, `src/video_pipeline.py` | Mặc định `system_evidence/v002_vehicle_preview/<video>/`; pipeline từ chối root legacy. |
| B2 & hệ thống | `run_b2_motion.py`, `replay_b2_candidates.py`, `run_b2_system.py`, `render_b2_evidence.py` | B2 baseline hoặc `system_evidence` theo vai trò; path được resolver kiểm trước khi ghi. |
| Event/common evaluation | `evaluate_events.py`, `replay_b2_alerts.py`, `compare_b0_b1_b2.py`, `evaluate_accident_pilot.py` | Mặc định `shared_evaluations/vNNN_...`; từ chối write legacy; nguồn lịch sử vẫn được đọc qua resolver ở chỗ có alias. |
| Audit mới | `inventory_explorer.py`, `audit_b2_pilot.py`, `diagnose_b2_pilot.py`, `inventory_temporal_sources.py`, `inspect_temporal_pilot.py`, `compare_b2_candidates.py` | Mặc định `data_audits/vNNN_...`; kiểm path trước khi ghi. `src/data_preparation.new_audit_dir()` chuyển tên audit cũ đã đăng ký trong registry sang `data_audits` và từ chối version bị chiếm. |
| CADP và ACCIDENT | `prepare_cadp_pilot.py`, `prepare_cadp_frames.py`, `prepare_accident_scale.py`, `audit_accident_public.py`, `inspect_public_zip.py`, `download_accident_real.py` | Audit mới dùng `data_audits`, preview annotation mới dùng `system_evidence`; bản video sạch dùng chung vẫn ở `data_samples`. Output chỉ định ngoài cây chuẩn bị từ chối; downloader ACCIDENT yêu cầu version audit mới cho mỗi báo cáo. Các plan/hồ sơ cũ có path legacy vẫn được đọc nhưng không ghi thêm vào đó. |
| Kaggle fetch | `kaggle_b0.py fetch` | Kết quả tải mới vào thư mục B0 version đăng ký; xác minh ZIP/manifest/checkpoint trước, extraction sang `.partial`, rename rồi cập nhật registry. Các `prepare/publish/logs` của recipe lịch sử còn dùng `outputs/kaggle` để giữ config và cache bất biến, **chưa là entry point cho thí nghiệm mới**. Không gọi `publish` trong migration này. |
| Release/maintenance lịch sử | `prepare_b0_*`, `maintenance/*`, một số `audit_*` | Release vẫn ở `data/processed`; `new_audit_dir` và các công cụ sửa manifest đã chuyển audit mới. Một số báo cáo/backup hardcode cũ còn **chưa chuyển hết**, ví dụ công cụ chuẩn bị B0 đời đầu. Dùng registry để đọc và kiểm dependency trước lần tái chạy. |

Không có train, inference GPU hay Kaggle run mới trong lượt kiến trúc. Mặc định mới có thể bị chặn khi version đã tồn tại: chỉ định version tiếp theo sau khi thêm registry/ghi quyết định, không ghi đè. Một số script lịch sử còn chưa chuyển được ghi rõ thay vì coi toàn bộ project đã migration xong.

## Lịch sử còn tại chỗ và dependency

| Đường dẫn vật lý | Vì sao giữ tại chỗ |
| --- | --- |
| `outputs/training/` (12 thư mục local B0, trong đó `b0_s960_v1/temporal_diagnostics_v1` chứa B1) | `experiment.json`/config và dashboard đọc checkpoint, cases, curve theo run ID; B1 config `configs/b1_causal_diagnostics_v1.json` có output lồng trong run B0; snapshot/hướng dẫn lịch sử dẫn path. Chuyển cần cập nhật mọi reader, kiểm SHA trước/sau và rollback nhóm. |
| `outputs/kaggle/` (4 thư mục recipe/cache) | Config SHA/receipt, ZIP 3,78 GB, deployment, download và Kaggle Notebook Version đang gắn nhau. `kaggle_b0.py` và `src/kaggle_recipe.py` còn dùng path cũ cho recipe đã phát hành. Copy archive vừa tốn chỗ vừa không bảo toàn provenance. |
| `outputs/audits/` (nhiều audit và `archive/`) | Một số report/manifest tham chiếu path cũ; backup và `storage_migration_v1/manifest.json` là rollback của năm nhóm đã move. `data/registries` và tài liệu dẫn đến chúng. Chưa có manifest hash/rollback riêng cho các nhóm còn lại. |
| `outputs/detection/`, `outputs/tracking/`, `outputs/annotation_preview/` | Video demo cũ được nhắc trong manifest/tài liệu, có thể là bản xuất từ nguồn dùng chung; chưa rà từng file và tham chiếu. Output video mới đã dùng `system_evidence`. |
| `outputs/YSGhwU9XxuY/`, `outputs/zVzXEht1aME/` | Thư mục nằm trực tiếp dưới `outputs/`, chưa xác minh vai trò/provenance. Catalog hiển thị `LEGACY/unknown`; không gộp hay đổi tên khi chưa kiểm. |

`outputs/_legacy/` hiện **chưa được tạo**: chưa có nhóm legacy nào đủ điều kiện di chuyển vào đó. Năm nhóm nhỏ đã move từ `outputs/audits` vào đích đúng loại trong lượt trước; manifest `outputs/audits/storage_migration_v1/manifest.json` ghi **175 file / 53.826.604 byte**, SHA từng file, trạng thái verify và rollback. Lệnh kiểm: `python scripts/maintenance/migrate_outputs.py --verify`; rollback chỉ chạy khi thật sự cần khôi phục và đã kiểm dependency.

Trước mọi move tiếp theo: lập nhóm và dependency, tạo plan/manifest hash, kiểm file đang mở/OneDrive placeholder/dung lượng và cùng filesystem, dry run, apply rename, verify byte và các đường đọc/API, giữ rollback có thể chạy. Không sửa JSON thực nghiệm để hợp thức hóa move.

## Mở project trong VS Code

- `DACN_Explore.code-workspace`: giữ tài liệu, code, registry và output chuẩn trước mắt; ẩn raw/processed và các nhánh legacy nặng trong Explorer. Chỉ là cấu hình hiển thị, **không xóa/di chuyển file**.
- `DACN_Full.code-workspace`: mở toàn bộ project, chỉ ẩn môi trường/cache. Dùng khi cần kiểm chính xác đường dẫn cũ hoặc dataset.

Hai workspace có thể mở bằng `code DACN_Explore.code-workspace` hoặc `code DACN_Full.code-workspace` tại gốc. Tìm artifact trong dashboard Explore hoặc dùng `src/storage_paths.py`, không đoán chỗ lưu từ tên Kaggle Version.

## Danh sách chi tiết các thư mục LEGACY

Kiểm kê chỉ đọc ngày 06/11/2026. Cột tham chiếu là file văn bản có chứa đúng đường dẫn; nó chỉ ra dependency cần kiểm trước khi move, không chứng minh mọi tham chiếu ngầm. Khi không tìm thấy tham chiếu tường minh, provenance/nội dung thư mục vẫn chưa được xác minh và chưa đủ điều kiện move.

| Thư mục còn ở vị trí cũ | Tham chiếu cần xử lý trước khi move |
| --- | --- |
| `outputs/training/b0_accident_scaled_v1/` | `configs/b0_accident_scaled_v1.json`, `data/registries/project_explorer.json`, `progress/2026-10-27.md`, `src/dashboard_data.py` (run ID động) |
| `outputs/training/b0_accident_scaled_v2/` | `configs/b0_accident_scaled_v2.json`, `data/registries/project_explorer.json`, `progress/2026-10-27.md`, `src/dashboard_data.py` (run ID động) |
| `outputs/training/b0_basic_pilot_v1/` | `configs/b0_pilot.json`, `configs/README.md`, `data/registries/project_explorer.json`, `src/dashboard_data.py` (run ID động) |
| `outputs/training/b0_normal_expanded_v1/` | `configs/b0_normal_expanded_v1.json`, `configs/b0_s960_v1.json`, `data/registries/project_explorer.json`, `src/dashboard_data.py` (run ID động) |
| `outputs/training/b0_s960_adamw_kaggle_v2/` | `configs/b0_s960_adamw_kaggle_v2.json`, `data/registries/project_explorer.json`, `docs/b0_pilot_audit.md`, `src/dashboard_data.py` (run ID động) |
| `outputs/training/b0_s960_hardneg_v1/` | `configs/b0_s960_hardneg_v1.json`, `data/registries/project_explorer.json`, `docs/b0_pilot_audit.md`, `src/dashboard_data.py` (run ID động) |
| `outputs/training/b0_s960_sgd_kaggle_v3/` | `configs/b0_s960_sgd_kaggle_v3.json`, `data/registries/project_explorer.json`, `docs/b0_pilot_audit.md`, `src/dashboard_data.py` (run ID động) |
| `outputs/training/b0_s960_sgd_low_lr_kaggle_v4/` | `configs/b0_s960_sgd_low_lr_kaggle_v4.json`, `data/registries/project_explorer.json`, `docs/b0_pilot_audit.md`, `src/dashboard_data.py` (run ID động) |
| `outputs/training/b0_s960_v1/` | `configs/b0_s960_adamw_kaggle_v2.json`, `configs/b0_s960_full_kaggle_v1.json`, `configs/b0_s960_hardneg_v1.json`, `src/dashboard_data.py` (run ID động) |
| `outputs/training/b0_verified_lr001_full60_v1/` | `configs/b0_normal_expanded_v1.json`, `configs/b0_verified_lr001_full60_v1.json`, `data/registries/project_explorer.json`, `src/dashboard_data.py` (run ID động) |
| `outputs/training/b0_verified_lr001_val_v1/` | `configs/b0_normal_expanded_v1.json`, `configs/b0_verified_lr001_val_v1.json`, `data/registries/project_explorer.json`, `src/dashboard_data.py` (run ID động) |
| `outputs/training/b0_verified_pilot_v1/` | `configs/b0_diagnostics_v1.json`, `configs/b0_normal_expanded_v1.json`, `configs/b0_verified_pilot_v1.json`, `src/dashboard_data.py` (run ID động) |
| `outputs/kaggle/b0_s960_adamw_kaggle_v2/` | `docs/kaggle_training.md`, `progress/2026-10-30.md`, `src/kaggle_recipe.py` / `scripts/kaggle_b0.py` (run ID động) |
| `outputs/kaggle/b0_s960_full_kaggle_v1/` | `data/registries/project_explorer.json`, `docs/BAO_CAO_TIEN_DO_DACN.md`, `docs/GETTING_STARTED.md`, `src/kaggle_recipe.py` / `scripts/kaggle_b0.py` (run ID động) |
| `outputs/kaggle/b0_s960_sgd_kaggle_v3/` | `src/kaggle_recipe.py` / `scripts/kaggle_b0.py` (run ID động) |
| `outputs/kaggle/b0_s960_sgd_low_lr_kaggle_v4/` | `docs/b0_pilot_audit.md`, `docs/BAO_CAO_TIEN_DO_DACN.md`, `docs/kaggle_training.md`, `src/kaggle_recipe.py` / `scripts/kaggle_b0.py` (run ID động) |
| `outputs/audits/accident_expansion/` | `data/registries/b0_normal_expanded_v1_asset_hashes.json`, `data/registries/b0_normal_expanded_v1_index.csv`, `data/registries/b0_s960_hardneg_v1_asset_hashes.json` |
| `outputs/audits/accident_full_download/` | Chưa thấy tham chiếu text; cần audit nội dung/provenance |
| `outputs/audits/accident_public/` | `docs/b0_pilot_audit.md`, `docs/GETTING_STARTED.md`, `docs/evidence/2026-10-25-b0-expansion.json` |
| `outputs/audits/accident_scale/` | `data/registries/b0_normal_expanded_v1_asset_hashes.json`, `data/registries/b0_normal_expanded_v1_index.csv`, `data/registries/b0_s960_hardneg_v1_asset_hashes.json` |
| `outputs/audits/accident_scaled_download/` | `docs/b0_pilot_audit.md`, `scripts/download_accident_real.py` |
| `outputs/audits/archive/` | `data/registries/project_explorer.json`, `reference/GLOSSARY.md` |
| `outputs/audits/b0_basic_pilot_v1/` | Chưa thấy tham chiếu text; cần audit nội dung/provenance |
| `outputs/audits/b0_exported_similarity/` | `docs/b0_pilot_audit.md`, `progress/2026-10-27.md` |
| `outputs/audits/b0_exported_similarity_2/` | `docs/b0_pilot_audit.md`, `progress/2026-10-27.md` |
| `outputs/audits/b0_hard_negative_sources_v1/` | `configs/b0_hard_negative_sources_v1.json`, `configs/b0_s960_hardneg_v1.json`, `data/registries/b0_s960_hardneg_v1_asset_hashes.json` |
| `outputs/audits/b0_label_preparation/` | `docs/evidence/2026-10-19-b0-validation.json`, `progress/2026-10-19.md` |
| `outputs/audits/b0_normal_expansion_v1/` | `configs/b0_normal_expanded_v1.json`, `configs/b0_normal_expansion_v1.json`, `configs/b1_causal_diagnostics_v1.json` |
| `outputs/audits/b0_pool_readiness/` | `docs/b0_pilot_audit.md`, `progress/2026-10-26.md` |
| `outputs/audits/cadp_001407_clean/` | `configs/b0_diagnostics_v1.json`, `configs/b1_causal_diagnostics_v1.json`, `docs/b0_label_protocol.md` |
| `outputs/audits/cadp_001407_clean_2/` | `configs/b0_diagnostics_v1.json`, `configs/b1_causal_diagnostics_v1.json`, `docs/b0_label_protocol.md` |
| `outputs/audits/cadp_1407/` | `docs/dataset_preparation.md`, `progress/2026-10-19.md` |
| `outputs/audits/cadp_b0_quality/` | `docs/GETTING_STARTED.md`, `progress/2026-10-24.md` |
| `outputs/audits/cadp_clean_manifest_update/` | `docs/cadp_001407_clean.md`, `progress/2026-10-19.md` |
| `outputs/audits/cadp_frame_review/` | `docs/dataset_preparation.md`, `progress/2026-10-19.md` |
| `outputs/audits/cadp_source_discovery/` | `docs/cadp_pilot_sources.md`, `docs/evidence/2026-10-19-b0-validation.json`, `progress/2026-10-19.md` |
| `outputs/audits/manifest_registration/` | `docs/dataset_preparation.md`, `progress/2026-10-19.md` |
| `outputs/audits/pilot_expansion_registration/` | `progress/2026-10-24.md` |
| `outputs/audits/pilot_groups/` | `docs/b0_pilot_audit.md`, `docs/GETTING_STARTED.md`, `progress/2026-10-24.md` |
| `outputs/audits/pilot_groups_2/` | `progress/2026-10-25.md` |
| `outputs/audits/pilot_groups_3/` | `docs/b0_pilot_audit.md` |
| `outputs/audits/pipeline_smoke/` | `progress/2026-10-19.md` |
| `outputs/audits/progress_consolidation/` | `progress/2026-10-19.md`, `progress/README.md` |
| `outputs/audits/public_source_decision/` | `progress/2026-10-24.md` |
| `outputs/audits/repository_handoff/` | `progress/2026-10-20.md` |
| `outputs/audits/storage_migration_v1/` | `data/registries/project_explorer.json`, `docs/STORAGE_ARCHITECTURE.md`, `progress/2026-11-06.md` |
| `outputs/audits/sttad_public_4/` | `docs/evidence/2026-10-24-sttad-public-audit.json`, `progress/2026-10-24.md`, `reference/2026-10-24-public-data-review.md` |
| `outputs/audits/sttad_public_5/` | `docs/b0_pilot_audit.md` |
| `outputs/audits/sttad_public_6/` | `docs/b0_pilot_audit.md`, `docs/cadp_pilot_sources.md`, `docs/GETTING_STARTED.md` |
| `outputs/audits/tad_normal_test_v1/` | `data/registries/b0_tad_normal_test_v1.json`, `docs/GETTING_STARTED.md`, `scripts/inspect_public_zip.py` |
| `outputs/audits/tad_public_zip/` | `configs/b0_hard_negative_sources_v1.json`, `configs/b0_normal_expansion_v1.json`, `data/registries/b0_tad_normal_test_v1.json` |
| `outputs/audits/tad_public_zip_2/` | `progress/2026-10-24.md` |
| `outputs/audits/tad_public_zip_3/` | `data/registries/b0_tad_normal_test_v1.json` |
| `outputs/audits/tad_public_zip_4/` | `configs/b0_hard_negative_sources_v1.json`, `configs/b0_normal_expansion_v1.json` |
| `outputs/detection/cadp_001407_clean_display20fps/` | `docs/cadp_001407_clean.md`, `docs/evidence/2026-10-19-clean-video-validation.json` |
| `outputs/detection/MVI_20011_first_10s/` | `docs/dataset_preparation.md` |
| `outputs/tracking/cadp_001407_clean_display20fps/` | `docs/cadp_001407_clean.md`, `docs/evidence/2026-10-19-clean-video-validation.json` |
| `outputs/tracking/MVI_20011_first_10s/` | `docs/dataset_preparation.md` |
| `outputs/YSGhwU9XxuY/` | `docs/STORAGE_ARCHITECTURE.md`, `progress/2026-10-17.md` |
| `outputs/zVzXEht1aME/` | `docs/STORAGE_ARCHITECTURE.md` |

Thư mục `outputs/annotation_preview/` có các MP4 ở cấp gốc, không có thư mục con; catalog đánh dấu các file này LEGACY. `outputs/audits/` còn có snapshot JSON ở cấp gốc, được tìm bằng cùng cơ chế. Không di chuyển chúng khi chưa kiểm tham chiếu/byte.
