# Tiến độ đồ án

## Quy tắc: một ngày một file

- Dùng **`progress/YYYY-MM-DD.md`**, lấy ngày theo **Asia/Bangkok**. Nếu file ngày đó đã có, cập nhật vào file đó.
- Mỗi task/lần chạy/lượt trao đổi là một mục nội dung trong ngày; **không tạo file Markdown có hậu tố theo chủ đề**.
- Mỗi mục ghi mục tiêu, việc thực sự đã làm, file/lệnh/bằng chứng, quyết định và lý do, phần còn dở, bước tiếp theo. Không ghi kế hoạch hoặc chỉ số tham khảo thành kết quả.
- Giữ lịch sử thay đổi trạng thái: ví dụ “lúc đầu pending → sau đó người dùng đã xác nhận”, không dùng yêu cầu cũ để hỏi lại nội dung đã duyệt.
- Trước khi kết thúc công việc, cập nhật file ngày và bảng dưới. Chỉ đánh dấu hoàn thành giai đoạn khi đạt điều kiện trong [README gốc](../README.md)/[XLSX](../YOLO_Lo_trinh_DACN.xlsx).
- Hướng dẫn/báo cáo kỹ thuật vẫn ở `docs/`, bằng chứng ở `outputs/audits/`; không nhập các tài liệu đó vào nhật ký hoặc xóa chúng.

Quy ước này thay quy ước cũ một file/buổi. Đã hợp nhất ba bản 19/10 vào [2026-10-19.md](2026-10-19.md), đồng bộ 16/10 và hai phần 17/10 thành file theo ngày. Bản gốc/hash và kiểm tra bảo toàn ở `outputs/audits/progress_consolidation/`; chỉ bỏ file phân mảnh sau kiểm tra nội dung/liên kết.

## Trạng thái hiện tại — 16/11/2026

**Web demo GitHub Pages đã hoạt động:** <https://minhquan0500.github.io/DACN_TrafficCollision/>. Hai clip/ba chế độ, video gốc/kết quả, từng frame/ID, cảnh báo và ảnh/clip, tải JSON/MP4/PDF; bản **phát lại kết quả**, không phân tích upload mới.37tệp≈30MB, không dữ liệu cá nhân/model/credential;36payload+manifest trên web khớp hash. Firefox7nhóm đạt cả local và HTTPS,390px không tràn; build/ref đã xác minh. [Cách cập nhật và giới hạn](../docs/GITHUB_PAGES.md), [nhật ký](2026-11-16.md). Đây là yêu cầu Pages mới, không triển khai backend tính phí24/7.

**Đã upload nhánh demo lên GitHub:** đăng nhập thành công `minhquan0500`, nhưng repo gốc chưa cấp quyền push. Đã tạo fork, đẩy [`feat/collision-demo-2026-11-16`](https://github.com/minhquan0500/DACN_TrafficCollision/tree/feat/collision-demo-2026-11-16) và mở [draft PR #1 về repo gốc](https://github.com/leanhquan0211/DACN_TrafficCollision/pull/1). Giữ nguyên main; hai dòng phát triển cần đối chiếu trước merge. Test70/70 có dữ liệu, source sạch68đạt/2skip; dataset/model/upload/ZIP giữ local. [Trạng thái xuất bản](../docs/GITHUB_PUSH_HANDOFF.md), [diễn biến trong ngày](2026-11-16.md). Hosting24/7 đã hủy, chưa phát sinh phí.

**Cập nhật mới nhất — đã có cảnh báo va chạm tự động thử nghiệm:** B2 luật causal/FSM theo cặp, khung đỏ, eventJSON, ảnh/clip, upload/refresh/restart. Rulev4 bắt đúng cặp CADPframe109 (candidate34/35frame), không alert trên2037frame DETRAC đã rà âm và Roboflow250frame chưaGT. Đây là **development đã dùng sửa luật**, lọc xe xa có thể miss; chưa test độc lập/nghiệm thu nghiên cứu. **70/70 test đạt**, Firefox5nhóm vàHTTP19nhóm đạt; đã rerunCPU/upload thật. [Báo cáo/giới hạn](../docs/COLLISION_DETECTION.md), [ảnh demo](../outputs/audits/collision_2026-11-16/collision_dashboard.png). Các mục trước cùng ngày bên dưới ghi lịch sử, không còn là trạng thái chức năng cuối cùng.

**Bàn giao cuối lượt:** có Word/PDF mới và ZIP16/11; đã giải nén chuyển thư mục, kiểm184file và nạp đủ hai mẫu/ba chế độ, giữ ảnh/clip cảnh báo. [Bộ bàn giao](../delivery/README.md), [kiểm gói](../outputs/audits/collision_2026-11-16/bundle_verification.json). Không chứa upload cá nhân hoặc môi trường Python; chưa kiểm cài sạch/Windows.

**Đã thử tải video ngoài pilot:** dashboard có chọn MP4 từ máy và chạy detection/tracking. Clip cao tốc Roboflow10giây qua upload thật xử lý250frame,837lượt bbox,17ID tạm; giữ kết quả sau refresh và khôi phục state. **57/57 test đạt** sau bốn test upload mới. [Cách dùng/nguồn/số đo](../docs/EXTERNAL_VIDEO_DEMO.md), [ảnh kết quả](../outputs/audits/external_video_2026-11-16/uploaded_video_dashboard.png). Chỉ demo phương tiện, không tự có nhãn tai nạn hoặc thêm dữ liệu nghiên cứu.

**Đã huấn luyện B0 ở mức khả thi phần mềm:** 12 epoch YOLOv8n, lớp `accident`, 25 ảnh train/18 validation phát triển; checkpoint/hash/config được lưu. Tại conf0,25/IoU0,5, train bắt17/19 vùng và báo nhầm3/6 ảnh âm; validation **TP=0, FP=0, FN=12**, mAP50=0,01208. Model chưa tổng quát sang cảnh khác; chưa dùng cho cảnh báo. **53/53 test đạt**. [Báo cáo/lệnh tái lập](../docs/B0_FEASIBILITY.md), [nhật ký16/11](2026-11-16.md). Gate dữ liệu/B0 nghiên cứu chưa hoàn thành; không đổi proposal CADP thành GT hay sửa readiness chính thức. Các mục dưới giữ diễn biến ngày14/11 và trước đó.

**Trình diễn lại cùng ngày:** đã khởi động dashboard tại localhost:8765, kiểm bảy nhóm HTTP đạt và chụp giao diện Firefox tại frame110. [Ảnh hiện tại](../outputs/audits/showcase_2026-11-16/dashboard_frame110.png), [kiểm HTTP](../outputs/audits/showcase_2026-11-16/http_check.json). Không chạy lại huấn luyện/inference trong lượt chỉ xem này.

### Kết quả ngày 14/11/2026

**Đã phục hồi pilot và chạy suy luận trên máy hiện tại.** Có 2.258 ảnh CADP/DETRAC khớp fingerprint, video sạch, trọng số YOLOv8n và môi trường CPU đúng pin. Đã chạy detection/tracking CADP 221 frame, tracking ba DETRAC 664/936/437 frame, kiểm lại MP4/cache và ghi provenance. Đầu ngày có 34 test đạt; sau dashboard 39; bộ mới sau importer STTAD **46/46 test đạt**. [Hướng dẫn/kết quả cache](../docs/INFERENCE_CACHE.md), [nhật ký 14/11](2026-11-14.md).

**Lỗi đã quan sát:** trong 35 frame va chạm CADP, đề xuất track xe buýt có 13 frame trả class car; mapping GT↔track vẫn chưa duyệt. Giai đoạn 1/B0 tiếp tục thiếu nhãn vùng, pilot đa sự kiện và split; chưa train/verifier/cảnh báo. Không dùng số frame, clip con hoặc lượt chạy lại làm số sự kiện độc lập.

**Demo trực tiếp cùng ngày:** đã chạy lại detection/tracking CADP đủ 221 frame vào `outputs/demo_2026-11-14/`, kiểm lại output đạt và mở MP4 tracking bằng trình phát mặc định (`xdg-open` trả 0). Chi tiết bổ sung trong nhật ký 14/11; demo hiện hiển thị xe/ID.

**Bổ sung sau yêu cầu nộp/demo, hạn còn một tháng:** đã có dashboard cục bộ (`bash demo.sh`), chọn hai clip/hai chế độ, chạy CPU thật, so hai video/quan sát theo frame, tải MP4/cache/report và lưu review thủ công với ảnh/hash. Kiểm Firefox 7 nhóm thao tác đạt; HTTP 9 nhóm kiểm đạt; có Word/PDF hiện trạng, 11 slide PPTX/PDF và script gói ZIP kèm manifest. [Bộ bàn giao](../delivery/README.md), [hướng dẫn](../docs/DEMO_GUIDE.md), [kế hoạch bốn tuần](../docs/KE_HOACH_4_TUAN.md). Đây là bản trình diễn vehicle inference, **chưa đủ nghiệm thu đề tài cảnh báo va chạm tự động**; không đánh hoàn thành giai đoạn nghiên cứu 6.

**Tự nghiên cứu và áp dụng sau đó:** đã kiểm nguồn/paper tác giả, tải chọn lọc bốn chuỗi STTAD ở commit ghim:212 tệp/83.058.778 byte khớp nguồn,176 ảnh decode được,31 frame có bbox nguồn hợp lệ,145 frame unknown; loại hai text-JPG mà không sửa nguồn. Có importer, bảng rà đủ31 vùng, bảy test mới và kiểm pairing/split nguồn. Chưa hợp nhất vào manifest, chưa chứng nhận bốn sự kiện độc lập/chưa train; source train/test công khai không đủ. [Ghi nhận nghiên cứu](../docs/RESEARCH_NOTES.md), [registry](../data/registries/sttad_selected_sources.json). Bộ ZIP/Word/slide trước đó giữ là snapshot demo, chưa chứa media STTAD mới.

### Kết quả kiểm máy ngày 09/11/2026

**Rà máy Linux và hoàn thiện kiểm tra:** đã khôi phục CADP 1407 MP4/TXT khớp SHA-256, bổ sung audit metadata/split/local assets và sửa lỗi fingerprint/mã thoát môi trường. **16/17 test đạt, 1 skip** vì thiếu ảnh sạch/output B0. Metadata/review/config giữ nguyên. Máy hiện tại thiếu ảnh sạch CADP, DETRAC, trọng số và môi trường suy luận; không dùng các kết quả máy cũ bên dưới làm inventory hiện tại. [Nhật ký 09/11](2026-11-09.md), [báo cáo phần còn thiếu](../docs/completion_audit.md).

**Giai đoạn 1 vẫn đang làm**, B0 chưa train; chưa đạt điều kiện chuyển bước. Công cụ kiểm leakage metadata đã có nhưng camera/near-duplicate và split thực nghiệm vẫn chưa hoàn tất.

### Trạng thái lịch sử đến 20/10/2026

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
| 09/11/2026 | Rà phần chưa hoàn thiện, phục hồi CADP MP4/TXT, audit metadata/split, sửa kiểm fingerprint/môi trường; chưa đủ điều kiện train | [2026-11-09.md](2026-11-09.md) |
| 12/11/2026 | Tìm link trực tiếp, phục hồi 2.258 ảnh có fingerprint, video dẫn xuất và 35 vùng B0 đề xuất; 23 test đạt | [2026-11-12.md](2026-11-12.md) |
| 14/11/2026 | Môi trường CPU/cache, dashboard/Word/slide/ZIP; nghiên cứu nguồn, tải chọn lọc và kiểm nhãn STTAD, bảy test importer mới | [2026-11-14.md](2026-11-14.md) |
| 16/11/2026 | B0 khả thi, upload video mới; B2/FSM cảnh báo tự động thử nghiệm với ảnh/clip; 70test đạt, chạy CPU/Firefox/HTTP và lưu lịch sử lỗi v1–v4 | [2026-11-16.md](2026-11-16.md) |

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
