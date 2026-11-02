# Bằng chứng nhỏ đọc được ngay sau clone

Mới nhất: [26/10 — pilot B0 đã train/đo](2026-10-26-b0-basic-pilot.json): split 47 ảnh/17 nhóm, config/hash/checkpoint, metric và bảng lỗi val/test. Kết quả test kém, chưa hoàn thành B0 đầy đủ. [Batch B0 và exporter trước đó](2026-10-26-b0-expansion.json) giữ mốc lịch sử trước train. Đây là snapshot máy phát triển; media phải phục hồi/kiểm lại trên máy clone.

Hai JSON ngày 19/10 là snapshot kiểm tra từ máy phát triển, sao từ `outputs/audits/` trước khi đưa code lên Git. Chúng ghi số frame/hash/kiểm tra đã chạy, không chứa video, ảnh hoặc annotation gốc. Không coi chúng là kết quả chạy trên máy mới.

- `2026-10-19-clean-video-validation.json`: đọc lại video sạch, GT preview, detection và tracking, mỗi file 221 frame; timing nguồn vẫn chưa xác minh.
- `2026-10-19-b0-validation.json`: thống kê/kiểm nhãn ứng viên và index âm; nhãn vùng chưa duyệt GT.

Các file/hash code trong snapshot phản ánh **phiên bản tại thời điểm kiểm**, có thể khác sau chỉnh sửa tài liệu/công cụ. Muốn kiểm trạng thái hiện tại, chạy test/chuẩn bị dữ liệu theo [hướng dẫn mới](../GETTING_STARTED.md). Media, audit đầy đủ và backup manifest vẫn nằm cục bộ trong `outputs/` và bị ignore.

## Bổ sung 24/10/2026

- [STTAD public audit](2026-10-24-sttad-public-audit.json): tải chọn lọc/giải mã/nhãn/unknown; không phải benchmark.
- [TAD remote ZIP](2026-10-24-tad-range-audit.json): đọc danh mục bằng HTTP Range, không tải/CRC toàn ZIP.
- [CADP quality](2026-10-24-cadp-quality.json): cờ chất lượng dẫn xuất, không biến thành GT.

Đây là snapshot máy phát triển, không chứng minh media đã phục hồi trên máy clone.

### Mở rộng và kiểm nhóm cùng ngày

- [STTAD bốn chuỗi](2026-10-24-sttad-expanded-audit.json): 176 ảnh đọc được, 31 frame có bbox nguồn.
- [Kiểm nhóm/cảnh](2026-10-24-pilot-groups.json): 10 nhóm, 2.742 frame, hash chỉ để sàng lọc; quyết định nhóm nằm trong phiếu review.
- [Hai normal TAD](2026-10-24-tad-selected-clips.json): Range/member CRC, không tải ZIP toàn bộ.
- [Pool tham chiếu B0](2026-10-24-b0-pool.json): 2.376 dòng, chưa split/train; index/media đầy đủ ở local.

## Bổ sung 25/10/2026

[Mở rộng B0 bằng nguồn public](2026-10-25-b0-expansion.json) gộp kết quả kiểm SO-TAD/TU-DAT, sáu clip ACCIDENT/PTS/pixel/nhãn, audit 16 nhóm nguồn và pool v2 có 35 frame dương/2.345 frame âm. 22 test đạt, chưa split/train. Bốn nhãn impact được giữ và hai nhãn loại theo [phiếu rà AI](../../data/reviews/2026-10-25-accident-source-review.json); không coi đây là xác nhận mới của người dùng. Media, annotation nguồn và backup vẫn local ở `outputs/audits/accident_public/`.

## Bổ sung 27/10/2026

[Pilot B0 ảnh đã train/đo](2026-10-27-b0-verified-pilot.json) lưu số liệu tổng hợp, config/checkpoint hash và so model cũ trên cùng test; report đầy đủ, ảnh từng case và checkpoint nằm local trong `outputs/training/b0_verified_pilot_v1/`. Snapshot không chứng minh media đã có trên máy clone và không là benchmark sự kiện.

[So sánh ba run B0 trên validation](2026-10-27-b0-full60-validation.json) ghi kết quả đủ 60 epoch, epoch tốt nhất, metric và hash dataset/config/checkpoint. Đây là validation đã sử dụng nhiều lần, không thay test độc lập mới.

[Chẩn đoán B0 trên ảnh và video](2026-10-27-b0-diagnostics.json) giữ hash checkpoint/config và kết quả phân tích 309 ảnh, xử lý/đọc lại 9 chuỗi đủ 3.857 frame. Mở HTML/video/log đầy đủ tại `outputs/training/b0_verified_pilot_v1/diagnostics/` trên máy có media. TAD normal là probe đã xem, DETRAC là nguồn từng dùng train, CADP chỉ có khoảng Colliding theo frame; snapshot này không là benchmark event độc lập.

[Normal mở rộng B0 28/10](2026-10-28-b0-normal-expansion.json) ghi nguồn/CRC/SHA của 18 clip, 5.650 frame decode, 540 mẫu, release 2.170 ảnh và reserve 120 frame, kiểm bbox nhỏ và mốc ba checkpoint cũ trên validation mới. Dataset mới chưa train, camera độc lập chưa chứng minh và đây không là benchmark event. Media/ảnh/reference cases nằm cục bộ trong `outputs/audits/b0_normal_expansion_v1/` và đường dẫn raw được ghi trong snapshot/catalog.

[Run normal-expanded hoàn tất 28/10](2026-10-28-b0-normal-training.json): 60 epoch, hash checkpoint/config, 217 case val và so sánh cùng tập; không suy luận test/holdout. Snapshot chuẩn bị trước đó giữ nguyên trạng thái lịch sử.

[Chuẩn bị s960 ngày28/10](2026-10-28-b0-s960-preparation.json): đối chiếu nguồn, lỗi val, SHA trọng số chính thức, decode/bbox và forward GPU;55test đạt. **Chưa train**, chưa có metric model s960; không chạy test/reserve.

[S960 validation hoàn tất 28/10](2026-10-28-b0-s960-validation.json):45epoch, bestCSV30, patience15 đã áp dụng; hash/checkpoint/class/case/timing và so cùng217val với n640. mAP50 68,60% chưa đạt70%; test/reserve không suy luận. Snapshot chuẩn bị giữ nguyên như hồ sơ lịch sử.

[Chọn điểm vận hành và holdout âm29/10](2026-10-29-b0-operating-point.json): khóa s960/conf0,27 trên val trước đo; valF1 65,98%/recall70,33%; holdout34/120ảnh có hộp. Tập âm đã consumed, không dùng chọn lại ngưỡng; không có event metric hoặc train mới.

[Chuẩn bị trước train tiếp29/10](2026-10-29-b0-hard-negative-preparation.json): B1causal12chuỗi/4.845frame, batch24TADnormal/8.992frame, nhóm khóa trước mining, release2.680ảnh, reserve120mới chưa suy luận, preflight/referenceval/hash. **Không train**, không thay kết quả các run trước. Đây là snapshot kỹ thuật; trạng thái baseline vẫn ở progress/README chung.

[Hardneg validation hoàn tất29/10](2026-10-29-b0-hardneg-validation.json): người dùng train15epoch, bestCSV5, earlystop10; hash checkpoint/args/dataset và đếm lại307case khớp. So mốc cũ cùng307val: mAP50/95 mới68,48/55,43%, F1cố định62,07%; ảnh âm có hộp7→5 nhưng tổngFP43→49. Giữ tách sốCSV và revalidation; CSVepoch2 trên70%mAP50 chưa là modelbest được chọn/đo. Test/reserve không suy luận, không train thêm hoặc thay operating point; hồ sơ chuẩn bị giữ nguyên lịch sử.

[Chuẩn bị KagglePRIVATE29/10](2026-10-29-b0-kaggle-preparation.json): gói3,78GiB/5.996file/2.988ảnh, thêm420normal train hợp lệ, val307giữ nguyên, khôngtest/reserve media. 75test, decodeCPU/trainerđổiROOT vàwheelLinux đúngpin đạt. Đã thửpublish nhưng thiếuđăngnhập: **Dataset/Notebook/runcloud chưa tạo/gửi/chạy**, chưa cókếtquảđể tải. Snapshot cóhash/giới hạn, không cótoken hoặcmetricgiả. Hướng dẫnở`docs/kaggle_training.md`; khôngtheodõitrain liên tục.
