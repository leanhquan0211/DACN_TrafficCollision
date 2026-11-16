# Phần còn thiếu và kết quả hoàn thiện ngày 09/11/2026

> Đây là audit lịch sử. Đến 12/11 đã phục hồi đủ 2.258 ảnh; đến 14/11 đã chạy suy luận CPU và xuất cache bbox/track. Xem [trạng thái mới](INFERENCE_CACHE.md) và [bằng chứng phục hồi](evidence/2026-11-12-restoration.json). Điều kiện train B0 vẫn chưa đạt.

**Đồ án chưa hoàn tất.** Phần đã có là chuẩn bị dữ liệu/nhãn đề xuất và suy luận phương tiện + ByteTrack. Chưa có mô hình accident đã train hay hệ thống cảnh báo va chạm được kiểm chứng. Kết luận dựa trên README, các sheet 01/05/07/08/09/13 và kiểm file/code thực tế.

## Các phần phải hoàn thiện theo thứ tự

| Bước | Phần còn thiếu | Điều kiện để tiếp tục |
| --- | --- | --- |
| 1. Dữ liệu/nhãn | Phục hồi ảnh sạch CADP, DETRAC; bổ sung nhiều sự kiện độc lập; duyệt quy tắc và bbox accident; rà camera, near-duplicate, hard negatives | Có pilot dương/âm được rà, nhãn vùng nhất quán, split theo nhóm không rò rỉ |
| 2. B0 | Script/config train, dataset đã duyệt, checkpoint, log và FP/FN | Train trên dữ liệu đủ điều kiện; chọn tham số bằng validation, đánh giá test theo protocol khóa |
| 3. B1/tracking | Lọc score causal B0, cache tracks/timestamps, đo chất lượng ID | Đo B1, rà tracking đủ tin cậy và xác minh timing |
| 4. B2/cảnh báo | Candidate pairs/recall, motion features, luật, FSM và clip bằng chứng | Candidate không bỏ sót nhiều sự kiện; nhãn/time khớp; cảnh báo chống lặp không che sự kiện mới |
| 5. T0/GRU | Nhãn cửa sổ/cặp xe, scaler train-only, MLP và GRU causal | Đối chứng công bằng cùng candidate/features; mở rộng dựa vào lỗi/đo thực tế |
| 6. Đánh giá/demo | Evaluator chung, FAR/hour, delay/FPS/VRAM, ablation, dashboard, báo cáo/demo | Kết quả thật trên dữ liệu đã khóa, case FP/FN và hướng dẫn tái lập |

Một sự kiện dương không thể tạo ba split dương độc lập. Kiểm tra tối thiểu này không có nghĩa ba sự kiện là đủ cho thí nghiệm. Source FPS CADP chưa xác minh: có thể xử lý nhãn ảnh theo frame, chưa được dùng FPS trình chiếu để suy onset/delay/vận tốc nguồn.

## Đã làm trong lượt này

- Tìm media/weights tại Downloads, Documents, Desktop, Videos, `/mnt`, `/media` và kiểm mục lục các ZIP project. Đây là phạm vi tìm kiếm cụ thể, không khẳng định đã rà mọi ổ đĩa/tài khoản.
- Tìm được `Downloads/1407.mp4`, chép vào `data_raw/cadp/pilot_1407/1407.mp4`. SHA-256 khớp `461d1fbe…6b0d91`. Đây là demo có overlay của tác giả, không dùng làm ảnh sạch train.
- Tải riêng TXT tác giả theo catalog, kiểm đủ SHA-256 trước khi ghi `data_raw/cadp/pilot_1407/1407.txt` (165.663 byte), khớp `e134b397…8c1f5ba`. Không tải toàn dataset. [Bằng chứng phục hồi](../outputs/audits/restoration_2026-11-09/report.json).
- Thêm [audit hiện trạng](../scripts/audit_project.py) và [kiểm manifest](../src/manifest_audit.py). Báo cáo JSON/Markdown ghi hash đầu vào, file local, metadata, phiên bản package và blocker. Các nhóm liên thông nhận quan hệ nguồn chuỗi/camera/sự kiện/hash/parent; phát hiện leakage gián tiếp, label unknown đưa vào split, preview có overlay đưa vào split, thời gian không hợp lệ hoặc dùng timing chưa xác minh. Không tự chia split hoặc duyệt nhãn.
- Sửa [kiểm asset](../scripts/check_project_assets.py): hash đúng không còn ghi đè lỗi số lượng; inventory trùng dòng/khác thư mục không được chứng nhận ảnh chưa kiểm.
- Sửa [kiểm môi trường](../scripts/check_environment.py): trả mã 1 khi thiếu dependency hoặc import lỗi ABI, kể cả khi riêng torch có sẵn; kiểm thêm numpy/lap.

Giữ nguyên `data/manifest.csv`, các phiếu review, registry, readiness và config. Đã so byte với ZIP source hiện có. Giữ xác nhận xe/Colliding 96–130 và ba DETRAC âm; không yêu cầu rà lại các nội dung này khi phục hồi đúng fingerprint. Không sửa XLSX vì không đổi lộ trình, nhãn hoặc phương án nghiên cứu.

## Kiểm chứng và giới hạn

[Kết quả kiểm tra](../outputs/audits/verification_2026-11-09/report.json): **17 test, 16 đạt, 1 skip**, không lỗi. Test đối chiếu review với VATIC thật đã đạt; test nhãn/ảnh/output pilot skip vì chưa có đầu vào. Các test mới dùng fixture để phát hiện sai metadata/fingerprint, không phải số đo accuracy.

[Audit cuối lượt](../outputs/audits/project_2026-11-09_2/report.md): 12 asset trong metadata, 1 event dương, 3 chuỗi âm, 12 asset `unassigned`. Không phát hiện mâu thuẫn metadata hiện tại, nhưng **chưa có split để chứng minh phân tách train/val/test**. Thiếu camera và rà near-duplicate vẫn là blocker. Tổng số thông báo blocker không phải số công việc độc lập; có các thông báo cùng nguyên nhân.

Máy hiện tại có Python 3.14.4, numpy 2.5.4; thiếu torch, torchvision, ultralytics, opencv-python, lap và FFmpeg. Chưa dựng môi trường ML tương đương máy phát triển; chưa chạy model, train hoặc đo va chạm. Không dùng kết quả lịch sử để khẳng định GPU/môi trường của máy này.

## Chạy lại

```bash
python3 -B scripts/audit_project.py --strict
python3 -B -m unittest discover -s tests -v
python3 -B scripts/check_environment.py
```

Audit luôn tạo thư mục mới, không ghi đè bằng chứng cũ. `--strict` trả 1 khi còn blocker; không có blocker tự động vẫn cần nghiệm thu dữ liệu/nhãn. Không coi `present_count_matches` là đúng fingerprint nếu nguồn không có hash tham chiếu. ZIP DETRAC đầy đủ chỉ phục vụ nhánh archive audit, không bắt buộc tải nếu đã có các chuỗi trích chọn lọc.

Bước tiếp theo: phục hồi đúng **221 ảnh sạch 001407** và **ba chuỗi DETRAC** theo [catalog](../data/download_catalog.json)/[hướng dẫn](GETTING_STARTED.md); tái tạo đề xuất để duyệt quy tắc vùng, lấy thêm export VATIC/mapping cho nhiều sự kiện rồi mới chốt split và train B0. Không thể hoàn thành các phần thực nghiệm còn lại chỉ bằng source hiện có.
