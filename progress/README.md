# Tiến độ đồ án

## Quy tắc: một ngày một file

- Dùng **`progress/YYYY-MM-DD.md`**, lấy ngày theo **Asia/Bangkok**. Nếu file ngày đó đã có, cập nhật vào file đó.
- Mỗi task/lần chạy/lượt trao đổi là một mục nội dung trong ngày; **không tạo file Markdown có hậu tố theo chủ đề**.
- Mỗi mục ghi mục tiêu, việc thực sự đã làm, file/lệnh/bằng chứng, quyết định và lý do, phần còn dở, bước tiếp theo. Không ghi kế hoạch hoặc chỉ số tham khảo thành kết quả.
- Giữ lịch sử thay đổi trạng thái: ví dụ “lúc đầu pending → sau đó người dùng đã xác nhận”, không dùng yêu cầu cũ để hỏi lại nội dung đã duyệt.
- Trước khi kết thúc công việc, cập nhật file ngày và bảng dưới. Chỉ đánh dấu hoàn thành giai đoạn khi đạt điều kiện trong [README gốc](../README.md)/[XLSX](../YOLO_Lo_trinh_DACN.xlsx).
- Hướng dẫn/báo cáo kỹ thuật vẫn ở `docs/`, bằng chứng ở `outputs/audits/`; không nhập các tài liệu đó vào nhật ký hoặc xóa chúng.

Quy ước này thay quy ước cũ một file/buổi. Đã hợp nhất ba bản 19/10 vào [2026-10-19.md](2026-10-19.md), đồng bộ 16/10 và hai phần 17/10 thành file theo ngày. Bản gốc/hash và kiểm tra bảo toàn ở `outputs/audits/progress_consolidation/`; chỉ bỏ file phân mảnh sau kiểm tra nội dung/liên kết.

## Trạng thái hiện tại — 20/10/2026

**Cập nhật bàn giao/GitHub:** đã bổ sung [hướng dẫn người/AI mới](../docs/GETTING_STARTED.md), catalog tải có vị trí/hash, công cụ kiểm asset và skeleton thư mục trên Git. Dữ liệu/nhãn/model không đổi; giai đoạn nghiên cứu vẫn như kết quả 19/10 bên dưới. Trạng thái xuất bản và kiểm clone được ghi trong [nhật ký 20/10](2026-10-20.md).

**Đã xuất bản source lên [GitHub/main](https://github.com/leanhquan0211/DACN_TrafficCollision)**, xác minh SHA remote khớp commit nguồn. Bản công khai bỏ log máy cá nhân/đường dẫn riêng; media/dataset/checkpoint vẫn local. Test có dữ liệu: 5 đạt; bản source không có dataset: 3 đạt, 2 integration skip đúng lý do. Không coi kiểm bản source bằng interpreter hiện có là đã cài lại một `.venv` mới.

**Giai đoạn 1 đang làm.** CADP 001407 có 221 ảnh sạch khớp VATIC; người dùng đã xác nhận đúng xe và Colliding **96–130 theo frame**. Ba DETRAC đầy đủ đã xác nhận âm. Manifest 12 asset nhưng chỉ 4 nhóm chuỗi đã rà, gồm 1 sự kiện va chạm; không đếm preview/clip/output thành mẫu độc lập. Ba MP4 cũ vẫn chưa rõ nguồn/nhãn.

| Giai đoạn | Trạng thái | Bằng chứng và phần còn thiếu |
| --- | --- | --- |
| 1. Định nghĩa/dữ liệu | Đang làm | Có review theo frame, [inventory nhóm chuỗi](../data/pilot_inventory.csv), công cụ chuẩn hóa và chỉ mục âm; thiếu pilot đa sự kiện/nhãn vùng đã duyệt và nhóm camera/near-duplicate |
| 2. B0 ảnh accident | Chuẩn bị nhãn, chưa train | [35 bbox đề xuất](../data/processed/b0_proposals/001407/report.json), [2.037 frame âm được lập chỉ mục](../data/processed/b0_reviewed_negatives/report.json); [quy tắc vùng](../docs/b0_label_protocol.md) còn đề xuất, không phải GT |
| 3. B1/tracking | Đã thử phần kỹ thuật tracking | YOLOv8n/ByteTrack đọc đủ 250 frame DETRAC và 221 frame CADP sạch; chưa có B1/metric bbox-ID |
| 4. Ứng viên/cảnh báo | Chưa triển khai | Bbox đề xuất nhãn B0 không phải bộ tạo ứng viên cặp xe vận hành B2; chưa motion features/FSM/alert |
| 5. Verifier thời gian | Chưa triển khai | Chưa có MLP/GRU/features/nhãn cửa sổ |
| 6. Đánh giá/demo | Chưa triển khai | Chưa event metrics, FPS/VRAM toàn hệ thống hoặc dashboard |

**Kiểm tra mới:** công cụ tạo nhãn chạy thật; giữ 4.641 dòng VATIC/flags/ignore, 35 ứng viên và 186 frame chưa chứng nhận âm, không tạo empty label giả. Chỉ mục âm kiểm lại CRC/giải mã/kích thước 2.037 ảnh DETRAC và hash MP4 đã rà. Năm test nhãn đã đạt. Kiểm tra đầy đủ ở [nhật ký ngày](2026-10-19.md).

**Nguồn mở rộng:** [đã kiểm trực tuyến](../docs/cadp_pilot_sources.md), truy cập được kho ảnh nhưng chưa xác minh thêm cặp VATIC/ảnh ngoài 001407. Chưa yêu cầu gán lại bbox bằng tay hoặc tải cả dataset.

**Việc tiếp theo:** chốt quy tắc vùng B0 trên đề xuất cụ thể; lấy export VATIC/mapping từ tác giả, chọn chuỗi có nhãn rồi mới lấy ảnh tương ứng. Không cần rà lại 001407 hoặc ba DETRAC. Source FPS CADP vẫn chưa biết; thiếu này cản đánh giá theo giây, không cản chuẩn hóa nhãn ảnh B0. Chưa split/train. [Readiness](../data/b0_readiness.json).

## Nhật ký theo ngày

| Ngày | Nội dung | File |
| --- | --- | --- |
| 16/10/2026 | Lập mốc, quy tắc theo dõi và trạng thái xuất phát | [2026-10-16.md](2026-10-16.md) |
| 17/10/2026 | Rà tổng thể, giải thích code tiếng Việt, thử lại video mẫu | [2026-10-17.md](2026-10-17.md) |
| 19/10/2026 | Dữ liệu CADP/DETRAC, ảnh sạch, review frame, nhãn đề xuất B0 và tìm nguồn | [2026-10-19.md](2026-10-19.md) |
| 20/10/2026 | Hướng dẫn dựng lại cho người/AI mới, Git ignore, kiểm clone và xuất bản GitHub | [2026-10-20.md](2026-10-20.md) |

## Mẫu mục bổ sung trong file ngày

```markdown
## Công việc / kết quả cập nhật

### Mục tiêu
- Kết quả cần có và giai đoạn liên quan.

### Đã làm và bằng chứng
- Việc đã chạy, file/lệnh/log, số đo thật.

### Quyết định và thay đổi trạng thái
- Lý do; trạng thái cũ nếu cần đối chiếu.

### Còn thiếu và bước tiếp theo
- Việc cụ thể, đầu ra cần có và cách kiểm tra.
```
