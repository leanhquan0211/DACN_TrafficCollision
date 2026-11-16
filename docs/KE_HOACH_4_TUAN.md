# Kế hoạch hoàn thiện trong một tháng

Người dùng cho biết còn một tháng từ trao đổi 14/11/2026. Mốc dưới đây là kế hoạch, không là kết quả hoặc cam kết đã được giảng viên duyệt. Giữ đề tài phát hiện va chạm CCTV; giao diện hiện tại là bản nền trình diễn.

| Thời gian dự kiến | Việc phải làm | Đầu ra / điều kiện kiểm |
| --- | --- | --- |
| 14–20/11 | Chốt yêu cầu giảng viên; duyệt định nghĩa/vùng accident; tìm thêm cặp ảnh sạch–annotation CADP; rà camera/sự kiện/near-duplicate; chọn pilot dương/âm đa dạng | Nhiều sự kiện độc lập có provenance, nhãn rõ, split theo nhóm. Không có đủ dữ liệu thì thu hẹp phạm vi với giảng viên sớm. Số 20–30 positives trong XLSX chỉ là gợi ý, không phải tiêu chuẩn đủ mẫu. |
| 21–27/11 | Sau gate dữ liệu mới train B0; lưu seed/config/model/curve; B1 causal; khóa val và phân tích FP/FN. Rà association GT↔track, class flicker, missing, timing | Có baseline thật và các lỗi cần giải quyết; không lấy pretrained vehicle model làm accident baseline. |
| 28/11–04/12 | Nếu đạt gate: candidates/ROI, đo candidate recall, features có quality mask, luật B2 và FSM/evidence. Chỉ học MLP/GRU khi đủ nhãn cặp/window và baseline phù hợp | Cảnh báo phát sinh từ thuật toán có log causal; tách khỏi manual review. Mỗi bước có test trên dữ liệu thật. Không chèn mốc GT vào luật để “demo trúng”. |
| 05–11/12 | Khóa protocol/ngưỡng từ val; đánh test; video âm dài; đo event precision/recall/F1, FAR/hour, delay và runtime; hoàn thiện báo cáo/slide | Bảng số khớp log, có FP/FN và giới hạn; không tuyên bố real-time chỉ từ FPS offline. |
| 12–14/12 (dự phòng) | Dựng lại máy sạch, luyện demo, kiểm gói nộp và định dạng trường | Người khác chạy được; giảng viên xác nhận phạm vi được nghiệm thu. |

## Ưu tiên và tiêu chí dừng

Phần trọng tâm tiếp theo là **dữ liệu + nhãn/split**, không đổi detector chỉ vì phiên bản mới. Không vừa tăng model vừa đổi features khi muốn so sánh đóng góp. Nếu một tuần đầu chưa có đủ sự kiện/nhãn, cần xin giảng viên duyệt phạm vi hẹp, ví dụ nguyên mẫu detection/tracking và phân tích dữ liệu. Không tự ghi đó là đề tài collision đã hoàn thành.

Nếu hết thời gian mà GRU chưa được kiểm chứng, trình bày B0/B1/B2 đã đo nếu có và giới hạn, chỉ bỏ GRU khi phạm vi nộp được giảng viên chấp nhận. Bản hiện tại chưa có kết quả các baseline đó.

## Checklist trước nộp

- [ ] Tên đề tài/phạm vi, tên sinh viên, MSSV, lớp, giảng viên và mẫu báo cáo được xác nhận.
- [ ] Manifest, nhãn đã duyệt, group split và kiểm leakage/media được lưu.
- [ ] Checkpoint accident/baseline, cấu hình, seed, dependency và log chạy được bàn giao.
- [ ] Chức năng cảnh báo đúng phạm vi đã duyệt; không nhầm review thủ công với auto.
- [ ] Kết quả test, FP/FN, protocol và hạn chế khớp bằng chứng.
- [ ] Word/PDF/slide cập nhật **kết quả cuối**, không để báo cáo hiện trạng thay cho kết quả chưa làm.
- [ ] Demo trên máy nộp, có clip dự phòng và hướng dẫn dựng môi trường.

Các ô này chưa được đánh dấu hoàn thành chỉ vì đã tạo bộ tài liệu/giao diện.
