# Tài liệu — đọc theo nhu cầu

README gốc đã rút gọn; [bản trước khi rút gọn](README_TRUOC_KHAM_PHA.md) giữ nội dung và bối cảnh lịch sử. Cách khám phá cấu trúc và đề xuất di chuyển trong tương lai nằm tại [frontend/README.md](../frontend/README.md).

## Đang dùng

| Muốn biết gì? | Đọc file này |
| --- | --- |
| Đọc hoặc trình bày toàn bộ quá trình, căn cứ chọn và kết quả thật | [Báo cáo tổng hợp Markdown](BAO_CAO_TIEN_DO_DACN.md), [PDF](BAO_CAO_TIEN_DO_DACN.pdf), cập nhật 04/11/2026; bản slide là ảnh chụp tiến độ 31/10 |
| Trình bày ngắn bằng slide, có biểu đồ so sánh | [PDF 14 slide ngang 16:9](SLIDE_TIEN_DO_DACN.pdf): giải thích metric, ảnh biểu đồ gốc rồi so sánh tổng hợp; [chú thích ngắn và lời trình bày từng slide](CHU_THICH_SLIDE_DACN.md). Font Times New Roman, nền kem/cam san hô, góc vuông/bo nhẹ |
| Mục tiêu và lộ trình project | [README gốc](../README.md) |
| Frontend trực quan: xem train, so sánh, ảnh/video và dữ liệu | [Chạy/cài dashboard](../frontend/README.md), [thiết kế và phạm vi](../frontend/DESIGN.md); một danh sách run local/Kaggle, tự đọc lại khi web đang mở, API chỉ đọc |
| Từng baseline còn gì, đã làm tới đâu, kết quả cần đạt? | [Bảng chung B0/B1/B2/T0/B3](../progress/README.md) |
| Cài máy, tải gì/ở đâu/lưu đâu, chạy lệnh nào? | [GETTING_STARTED](GETTING_STARTED.md) |
| Hai người làm chung: chia Dataset/Kaggle, nhận bundle và giảm conflict | [GETTING_STARTED — mục 10](GETTING_STARTED.md#10-làm-nhóm-hai-người-dùng-chung-dữ-liệu-và-tránh-xung-đột); một repo, nhánh/notebook riêng, dữ liệu chung |
| Chuyển train sang KagglePRIVATE, đăng nhập/gửi/nhận kết quả | [kaggle_training](kaggle_training.md), [bước triển khai hiện hành](../KE_HOACH_TRIEN_KHAI.md) |
| Có những paper nào, dùng được gì? | [Literature review](../reference/LITERATURE_REVIEW.md) |
| Thuật ngữ/code đang nói gì? | [Từ điển ngắn](../reference/GLOSSARY.md) |
| B0 dùng nhãn gì, phân biệt source/derived/unknown thế nào? | [b0_label_protocol](b0_label_protocol.md) |
| Dữ liệu hiện tại, nhóm cảnh, pool và output cần mở? | [b0_pilot_audit](b0_pilot_audit.md) |
| B0 nhầm ở đâu và chạy trên video sạch ra sao? | [Chẩn đoán ảnh/video B0](b0_pilot_audit.md#chẩn-đoán-lỗi-ảnh-và-video-b0--27102026) |
| Run mới nhất đã train ra sao, model ở đâu? | [Kaggle Version 12 và đường dẫn kết quả](b0_pilot_audit.md#chuẩn-bị-version-12--đối-chứng-learning-rate-04112026), [so sánh V10–V12](BAO_CAO_TIEN_DO_DACN.md#f-tổng-hợp-kết-quả-và-phép-so-hợp-lệ) |
| Dataset normal, nguồn/split và lịch sử lệnh train | [Chuẩn bị hardneg29/10](b0_pilot_audit.md#chuẩn-bị-s960-hardneg-v1--29102026), [normal mở rộng28/10](b0_pilot_audit.md#b0-normal-mở-rộng--28102026) |
| Mỗi script làm gì? | [scripts/README](../scripts/README.md) |
| Output mới phải lưu đâu, tìm run cũ ở đâu, migration còn chặn gì? | [Kiến trúc artifact](STORAGE_ARCHITECTURE.md), [registry](../data/registries/project_explorer.json) và hai file workspace tại gốc |
| Manifest, review và fingerprint có vai trò gì? | [data/README](../data/README.md) |
| Môi trường từng kiểm | [environment_reference](environment_reference.md) |

## Chi tiết theo nguồn và lịch sử

Các tài liệu sau giữ đường dẫn cũ để nhật ký/bằng chứng còn đọc được. Không cần đọc hết để bắt đầu; các quyết định mới trong README/policy hiện hành ưu tiên hơn chỉ dẫn cũ.

| File | Nội dung |
| --- | --- |
| [annotation_protocol](annotation_protocol.md) | Định nghĩa nhãn/sự kiện bản nháp 19/10, có phần chưa còn là quy trình hiện hành |
| [dataset_preparation](dataset_preparation.md) | Chuẩn bị CADP/DETRAC và [kiểm kê ba MP4 ban đầu](dataset_preparation.md#kiem-ke-ba-video-ban-dau) đã gộp |
| [cadp_001407_clean](cadp_001407_clean.md) | Bằng chứng ảnh sạch, mapping và các output CADP |
| [cadp_pilot_sources](cadp_pilot_sources.md) | Phạm vi tìm CADP, vì sao không chờ export chưa public |
| [evidence/](evidence/README.md) | Snapshot JSON nhỏ đọc được sau clone; không phải media đã phục hồi |

**Quy ước:** hướng dẫn thao tác ở `docs/`; paper/tóm tắt/thuật ngữ ở `reference/`; nhật ký ở `progress/`; kết quả chạy ở `outputs/`. Cập nhật tài liệu phù hợp khi có thay đổi, tránh thêm một file hướng dẫn mới cho mỗi lượt làm việc.
