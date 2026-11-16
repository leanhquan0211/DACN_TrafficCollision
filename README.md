# ĐACN: phát hiện và cảnh báo va chạm giao thông từ video

> **Mới clone hoặc bắt đầu với AI mới? Đọc [GETTING_STARTED — cài môi trường, tải gì/ở đâu/lưu đâu và tiếp tục thế nào](docs/GETTING_STARTED.md).** Repo giữ code/config/metadata/nhật ký; dataset, trọng số, `.venv`, video và audit đầy đủ nằm cục bộ, không có sau clone. [Catalog tải](data/download_catalog.json), [kiểm file hiện có](scripts/check_project_assets.py), [snapshot bằng chứng nhỏ](docs/evidence/README.md).

> **Chạy demo:** `bash demo.sh` → <http://127.0.0.1:8765>. Mặc định **Phát hiện va chạm · Thử nghiệm**: tự tạo cảnh báo, khung đỏ, ảnh/clip và Events JSON bằng luật chuyển động sau YOLO/ByteTrack. Hỗ trợ MP4 tải lên. [Kết quả/giới hạn/cách chạy](docs/COLLISION_DETECTION.md), [hướng dẫn demo](docs/DEMO_GUIDE.md). Bản thử đã chạy được, chưa thay nghiệm thu độ chính xác trên camera độc lập.

> **Web demo công khai:** <https://minhquan0500.github.io/DACN_TrafficCollision/> — GitHub Pages phát lại hai clip mẫu, đủ ba chế độ, quan sát từng frame và ảnh/clip cảnh báo. Chạy được khi máy phát triển tắt. Đây là **bản xem kết quả đã lưu**, không chạy Python hoặc phân tích video tải lên. [Phạm vi, mã nguồn và cách cập nhật](docs/GITHUB_PAGES.md). Hosting backend24/7 trước đó vẫn chưa triển khai; trang tĩnh này được tạo theo yêu cầu GitHub Pages mới.

> **Mã nguồn demo 16/11:** đã upload nhánh [`feat/collision-demo-2026-11-16` trên fork minhquan0500](https://github.com/minhquan0500/DACN_TrafficCollision/tree/feat/collision-demo-2026-11-16) và tạo [draft PR #1 về repo gốc](https://github.com/leanhquan0211/DACN_TrafficCollision/pull/1). Tài khoản đăng nhập không có quyền ghi repo gốc; `main` giữ nguyên. Nhánh từ bản nguồn20/10; cần đối chiếu với dòng dashboard/training hiện có trước khi tích hợp. [Trạng thái xuất bản](docs/GITHUB_PUSH_HANDOFF.md).

> **Tài liệu định hướng của project.** README này tóm tắt kế hoạch trong [YOLO_Lo_trinh_DACN.xlsx](YOLO_Lo_trinh_DACN.xlsx) và ghi trạng thái triển khai thực tế. File XLSX là bản phác thảo ban đầu, không phải kết quả thực nghiệm hoặc yêu cầu đã được giảng viên duyệt. Các thông số, mô hình và mốc thời gian ghi là **dự kiến** cho đến khi được kiểm chứng. Khi cần chi tiết về dữ liệu, pipeline, đánh giá hoặc nguồn tham khảo, đọc các sheet `01_Huong_DACN`, `05_Cac_buoc`, `07_Pipeline`, `08_Du_lieu`, `09_Danh_gia`, `13_Ke_hoach` và `15_Nguon`.

## Quy tắc định hướng cho mọi công việc tiếp theo

1. Trước khi chọn việc làm, công cụ, mô hình, dữ liệu hoặc cách đánh giá, đọc README này và phần liên quan trong XLSX. Bám vào **mục tiêu phát hiện sự kiện va chạm từ CCTV cố định**, câu hỏi nghiên cứu, thứ tự baseline → phân tích lỗi → xác minh chuyển động → cảnh báo → đánh giá, cùng giới hạn máy hiện có.
2. Không thêm mô hình hay công nghệ chỉ vì mới hơn hoặc có sẵn. Nêu vấn đề quan sát được, phương án đơn giản đang dùng, điều kiện chuyển hướng và phép đo cần có. Ưu tiên hoàn thành, đo và hiểu baseline trước khi mở rộng.
3. Phân biệt rõ **đã chạy/đã đo**, **đang làm** và **dự kiến** trong code, tài liệu, demo và báo cáo. Không biến gợi ý, số liệu paper hoặc giá trị mẫu trong XLSX thành kết quả của project. Không tuyên bố `real-time`, cải thiện độ chính xác hay tính mới khi chưa có benchmark phù hợp.
4. Khi thay đổi phạm vi, dataset, nhãn, stack hoặc protocol đánh giá, ghi lý do và bằng chứng trong README/config hoặc nhật ký thí nghiệm, rồi cập nhật phần kế hoạch liên quan. Nếu README và XLSX chưa khớp, đối chiếu bản gốc và quyết định đã ghi; chỉ dẫn mới của người thực hiện và yêu cầu của giảng viên được ưu tiên, sau đó cập nhật tài liệu để lần sau dùng cùng một định hướng.
5. Mỗi bước mới phải có đầu ra có thể kiểm tra và điều kiện chuyển bước. Giữ split, nhãn, config, checkpoint, phiên bản thư viện và log đo để tái lập; không dùng test set để chọn ngưỡng hay tinh chỉnh mô hình.
6. Trước khi kết thúc công việc, cập nhật [nhật ký tiến độ](progress/README.md) và bảng trạng thái: **một file `progress/YYYY-MM-DD.md` cho mỗi ngày theo Asia/Bangkok**. Mọi task/lần chạy/lượt trao đổi cùng ngày thêm thành mục trong file đó, không tạo file hậu tố theo chủ đề. Ghi mục tiêu, việc đã làm, bằng chứng, quyết định và bước tiếp theo; giữ trạng thái lịch sử tách kết quả mới. Không đánh dấu giai đoạn hoàn thành nếu chưa đạt điều kiện chuyển bước.

## Mục tiêu và phạm vi

**Đầu vào:** video có timestamp từ **một camera CCTV cố định**. **Đầu ra dự kiến:** một sự kiện va chạm xe–xe gồm `event_id`, thời điểm, camera, độ tin cậy, các ID track liên quan và ảnh/clip bằng chứng trên dashboard. Track ID chỉ là mã tạm trong video, không phải danh tính xe ngoài đời. Ban đầu có thể giới hạn ô tô; chỉ thêm xe máy nếu nhãn và detector hỗ trợ đủ tốt.

Đây là **collision detection**: nhận biết va chạm đang hoặc vừa xảy ra. Dự báo trước va chạm (*anticipation*), đa camera, graph, VLM và mô hình video lớn là các hướng mở rộng riêng, không phải yêu cầu cốt lõi của ĐACN. Phạm vi mức 3 trong sheet `04_Bon_muc` là đề xuất cần giảng viên duyệt.

Hai câu hỏi cần trả lời bằng thực nghiệm:

- **RQ1:** Quỹ đạo và diễn biến theo thời gian có giảm cảnh báo sai trên các cảnh dễ nhầm (*hard negatives*) so với detector ảnh cộng lọc thời gian đơn giản, tại mức recall tương đương không?
- **RQ2:** Nếu giảm được cảnh báo sai, chi phí FPS, độ trễ và VRAM trên laptop RTX 3050 Ti có chấp nhận được không?

Sản phẩm hướng tới gồm code/config có phiên bản, quy tắc nhãn và data manifest, checkpoint, bảng thí nghiệm, phân tích lỗi, dashboard xem cảnh báo/bằng chứng, demo và báo cáo. Việc công bố clip/dữ liệu phụ thuộc điều kiện sử dụng của nguồn.

## Hướng kỹ thuật dự kiến

```text
Video CCTV + timestamp
  → YOLO phát hiện phương tiện → ByteTrack giữ ID và quỹ đạo
  → chọn cặp xe nghi vấn trong ROI → đặc trưng chuyển động cặp xe
  → luật / MLP / GRU một chiều dùng dữ liệu quá khứ để xác minh
  → máy trạng thái cảnh báo → event log + clip bằng chứng + dashboard
```

- **YOLOv8n pretrained** là điểm bắt đầu cho *vehicle detection*. Nó có class phương tiện, **không có class `accident` mặc định**. Baseline ảnh tai nạn B0 cần nhãn vùng tai nạn và fine-tune một detector riêng; nếu chạy đồng thời hai detector thì phải tính chi phí của cả hai.
- **ByteTrack** là tracker khởi đầu cho camera cố định. Nếu lỗi mất/đổi ID ảnh hưởng kết quả, mới so BoT-SORT hoặc cách association khác trên cùng detector và dữ liệu. Bounding box chồng nhau hay hai xe ở gần nhau chưa đủ xác nhận va chạm.
- Đặc trưng dự kiến: vị trí/kích thước bbox chuẩn hóa, vận tốc ảnh, đổi hướng hoặc dừng đột ngột, khoảng cách/tốc độ tiếp cận tương đối, tuổi và độ tin cậy track, mask khi thiếu quan sát. Tính theo timestamp thật; không gọi tốc độ ảnh là km/h khi chưa hiệu chuẩn camera.
- Bắt đầu bằng **luật chuyển động**, rồi **MLP** làm đối chứng. Chỉ thử **GRU causal nhỏ** (gợi ý 1 layer, hidden 32/64) khi có nhãn thời gian/cặp xe và baseline đã được đo. Cache tracks/features để huấn luyện verifier tách detector; khi benchmark vận hành vẫn tính toàn bộ chi phí detector.
- Cảnh báo cần chính sách xác nhận và chống lặp: `idle → suspected → confirmed → cooldown`. Lưu vài giây video trước/sau cảnh báo bằng ring buffer; cooldown không được che sự kiện mới ở cặp xe hoặc vị trí khác. Dashboard chọn stack Python quen thuộc như FastAPI hoặc Streamlit sau khi lõi suy luận ổn.

## Dữ liệu và nhãn cần chuẩn bị

Ưu tiên **kiểm tra CADP** cho bối cảnh CCTV: video gốc có đọc được không, FPS/timestamp và khoảng trước/sau va chạm có đủ không, nhãn bbox/onset/cặp xe có thực sự tồn tại cho subset dùng hay không, điều kiện sử dụng/trích dẫn là gì. Không mặc định toàn bộ CADP có nhãn cặp xe hoặc nhãn thời gian đầy đủ. Bổ sung video âm tính dài, cùng miền camera, để đo cảnh báo sai trên giờ video; thêm các nhóm xe đỗ sát, kẹt xe, phanh gấp, near miss, giao quỹ đạo, che khuất và đổi ID. Cảnh mơ hồ cần cờ `uncertain` và rà bằng video gốc.

Manifest tối thiểu: `video_id`, `camera_id`, `source_event_id`, nguồn, split, thời lượng, `onset_s`, `end_s`, loại sự kiện, xe liên quan và độ chắc chắn nhãn. Với dữ liệu âm tính, thời điểm va chạm để trống. Nhãn cửa sổ cho bài toán detection phải dựa vào thời điểm cuối cửa sổ; đoạn **trước onset** là âm tính, không gán cả clip tai nạn là dương tính. Nếu chưa có nhãn xe liên quan, chỉ làm mức scene và ghi rõ giới hạn đó.

Loại clip trùng/gần trùng; chia train/validation/test theo **camera, nguồn hoặc sự kiện** để các bản cắt của cùng tai nạn ở cùng một split. Fit chuẩn hóa và chọn đặc trưng trên train; chọn ngưỡng trên validation; chỉ đánh giá test với cấu hình đã khóa. Pilot nhỏ chỉ để kiểm tra pipeline, không tự là benchmark đáng tin cậy.

## Thứ tự thực hiện và điều kiện chuyển bước

| Giai đoạn | Việc làm và đầu ra cần có | Điều kiện chuyển tiếp |
| --- | --- | --- |
| 1. Định nghĩa và dữ liệu | Chốt quy tắc va chạm, onset/end, trường hợp mơ hồ; rà video và nhãn; manifest, split cố định. | Có cả sự kiện dương, video âm và nhãn nhất quán, không rò rỉ giữa split. |
| 2. Baseline ảnh B0 | Gán bbox tai nạn theo cùng quy tắc, fine-tune YOLOv8n; thử `s` nếu `n` bỏ sót có hệ thống; lưu model/config và FP/FN. | Xác định lỗi thật cần giải quyết, nhất là hard negatives. |
| 3. B1 và tracking | Lọc score B0 bằng EMA hoặc k-of-N causal; chạy YOLO vehicle + ByteTrack, rà ID trên clip mẫu. | Có B1 được đo trên cùng test và tracks đủ tin cậy để tính chuyển động. |
| 4. Ứng viên và cảnh báo | Chọn cặp trong ROI, đo *candidate recall*, tính features; làm luật B2, event log/FSM và clip bằng chứng. | Bước tạo ứng viên không bỏ sót nhiều sự kiện thật; timestamps và nhãn cặp/scene khớp. |
| 5. Xác minh theo thời gian | Gán nhãn cửa sổ; huấn luyện MLP T0 rồi GRU causal B3/T1 trên cùng candidate/features; lưu scaler, seed và checkpoint. | Có so sánh công bằng với B1/B2/T0; nếu GRU không hơn, phân tích lỗi và dùng phương án phù hợp hơn. |
| 6. Đánh giá và demo | Ablation từng nhóm feature/window/policy; đo video dài, FPS/độ trễ/VRAM; hoàn thiện dashboard và báo cáo. | Có kết quả thật, case FP/FN, hướng dẫn tái lập và demo chạy được. |

Sheet `13_Ke_hoach` chia các bước thành **10 tuần dự kiến**, không phải lịch đã cam kết hoặc trạng thái thực hiện hiện nay. Chỉ cân nhắc một hướng KLTN sau khi có lỗi đo được và câu hỏi mở rộng riêng.

## Đối chứng và cách đánh giá

| Ký hiệu trong XLSX | Phương án |
| --- | --- |
| B0 | YOLO fine-tune để phát hiện vùng tai nạn trên ảnh/video. |
| B1 | B0 cộng lọc điểm theo thời gian bằng EMA hoặc k-of-N causal. |
| B2 | Detector phương tiện + tracking + luật chuyển động. |
| T0 | Cùng candidate/features như B3, dùng MLP trên đặc trưng hiện tại. |
| B3/T1 | Cùng candidate/features như T0, dùng GRU một chiều trên chuỗi quá khứ. |

Các phương án dùng cùng split, định nghĩa sự kiện, quy tắc ghép alert với GT và chính sách chống trùng khi so hệ thống. Một alert ghép tối đa một event; alert thừa là FP, event không được ghép là FN. Báo **event precision/recall/F1**, đường precision–recall, **false alerts/hour** trên video âm tính dài, tỷ lệ clip âm có cảnh báo sai theo từng hard-negative group, **event delay** từ onset đến alert, FPS end-to-end, p50/p95 thời gian xử lý, peak VRAM, số frame bỏ và queue lag. So số cảnh báo sai ở **recall tương đương**; chọn ngưỡng trên validation và báo recall thực tế trên test. FPS chỉ của YOLO không đại diện pipeline. `10 Hz` trong XLSX chỉ là ví dụ mục tiêu, cần đo khả năng xử lý ổn định trên máy thật. Không so F1 detection trực tiếp với AP/mTTA của bài toán anticipation.

## Trạng thái hiện tại

**Cập nhật nhận dạng lớp xe16/11:** đã xử lý trường hợp ô tô/SUV bị hiện `truck`0,23 trong clip140frame. Giữ YOLOv8n640, bật NMS không phân lớp để giảm khung trùng và thêm nhãn hiển thị causal theo lịch sử ID; bằng chứng yếu/mâu thuẫn hiện **“chưa rõ loại”**, không tự đổi mọi truck thành car. Xe người dùng chỉ có dự đoán thô truck0,23 nhưng thiếu bằng chứng nên hiển thị `vehicle?`/chưa rõ loại; **chưa sửa được lớp thô của model thành car**. Trên clip này, cặp khung khác lớp IoU≥0,8 giảm141→0, ID tạm65→50. Chạy lại7clip/3548frame thực: CADP đúng cặp tại108 (trước109, candidate35/35); clip900frame0alert; ba DETRAC2037frame0alert; cao tốc250frame chưaGT0alert; clip140frame vẫn1alert tại52 chưa có GT. **80/80test,6nhóm Firefox đạt.** [Cấu hình, bằng chứng và giới hạn](docs/VEHICLE_LABEL_FIX.md). NMS có thể loại xe thật chồng nhau mạnh; lịch sử ID vẫn có thể nhận nhầm lớp. Không đổi luật va chạm/nhãn/split, không gọi số khung trùng là accuracy. Các lượt v4/v5 trước đây giữ là lịch sử; Pages/Word/PDF/ZIP chưa tái xuất bằng cấu hình mới.

**Đã sửa trường hợp báo nhầm người dùng gửi16/11:** bản `motion_contact_v5` thêm điều kiện tương thích mép dưới bbox để hạn chế overlap do khác độ sâu. Chạy lại đầy đủ900frame của `13275193-hd_1920_1080_60fps.mp4` trên CPU: **1cảnh báo sai ở frame165 → 0cảnh báo**; input/trọng số và quan sát detector của cả900frame giống trước sửa. Chạy lại CADP221frame vẫn bắt đúng cặp tại109; replay ba DETRAC2037frame và cao tốc250frame không phát cảnh báo. **74/74test đạt**, Firefox5nhóm đạt; khôi phục web chọn đúng lượt mới nhất, kết quả dùng cấu hình cũ được ghi rõ. [Chẩn đoán, số đo và cách xem](docs/FALSE_ALERT_FIX.md), [snapshot](docs/evidence/2026-11-16-false-alert-fix.json). Đây là chẩn đoán phát triển, chưa là test độc lập hoặc xác nhận âm toàn clip; không đổi nhãn/split/model hay công khai video cá nhân. Điều kiện hình học có thể bỏ sót xe che khuất, lật hoặc khác độ cao; không là hiệu chuẩn3D. Pages và bộ Word/PDF/ZIP trước lượt sửa giữ là snapshot v4.

**Cảnh báo tự động thử nghiệm — lượt v4 trước sửa:** chế độ collision chạy causal trên tracker, xác nhận3/5frame, cooldown theo cặp, đánh dấu và xuất ảnh/clip/Events JSON; hỗ trợ upload và khôi phục kết quả sau restart. Rulev4 bắt đúng cặp CADP tại frame109; candidatecoverage34/35frame interval. Không báo trên2037frame/≈81,48giây ba DETRAC đã rà âm và clip cao tốc250frame chưa có GT. **Các cảnh đã dùng phát triển luật**, chưa phải test độc lập; lọc bbox nhỏ giúp giảm báo nhầm nhưng có thể bỏ sót va chạm ở xa. Bộ test khi đó70/70đạt, HTTP/Firefox đã kiểm CPU rerun/upload/evidence. [Báo cáo và lịch sử lỗi v1–v5](docs/COLLISION_DETECTION.md), [nhật ký](progress/2026-11-16.md). Các trạng thái “chưa cảnh báo” bên dưới phản ánh các lượt trước trong ngày; gate nghiên cứu/B0 vẫn chưa hoàn thành.

**Quyết định theo chỉ dẫn mới 16/11 — triển khai cảnh báo tự động thử nghiệm:** người dùng yêu cầu hoàn thiện phát hiện va chạm và cho phép chủ động chọn phương tiện thực hiện. Do B0 khả thi bỏ sót12/12 vùng validation ở conf0,25, lọc B1 không thể khôi phục tín hiệu đã mất; triển khai nhánh B2 luật chuyển động/FSM song song để có luồng cảnh báo vận hành và đo lỗi. Giữ YOLOv8n/ByteTrack, không đổi sang model lớn hoặc dùng nhãn/frame va chạm làm điều kiện runtime. Luật kết hợp tiếp cận + tương tác không gian + biến đổi chuyển động + xác nhận causal; overlap đơn lẻ không xác nhận. CADP là **development**, ba DETRAC rà âm dùng chẩn đoán; không gọi là test độc lập hoặc nghiệm thu nghiên cứu. Với nguồn chưa rõ FPS, chuyển động đo theo frame/độ lớn bbox, thời gian cảnh báo là thời gian video; không suy source seconds/km/h. Không tự duyệt proposal CADP, sửa review/hash hay đánh hoàn thành gate nghiên cứu. Đây là thay đổi thứ tự triển khai theo yêu cầu mới, cần báo đủ lỗi, config, hạn chế và bằng chứng trước khi kết luận chất lượng.

**Tải video mới 16/11:** theo yêu cầu người dùng, dashboard đã có chọn file MP4 H.264 từ máy và tự chạy detection/tracking. Đã thử qua trình duyệt với clip cao tốc Roboflow 10 giây ngoài CADP/DETRAC: 250 frame, 837 lượt bbox, 17 ID tạm; kết quả giữ sau refresh và khôi phục state. **57/57 test đạt**. [Cách dùng/nguồn/giới hạn](docs/EXTERNAL_VIDEO_DEMO.md). Video mới chỉ phục vụ demo suy luận, không tự vào tập nghiên cứu hoặc có nhãn tai nạn; giữ model/gate nghiên cứu và các review cũ.

**Kết quả 16/11/2026:** đã chạy lượt B0 khả thi 12 epoch, có checkpoint một lớp `accident`, 25 ảnh train/18 validation và **53/53 test đạt**. Tại conf 0,25/IoU 0,5: train bắt 17/19 vùng nhưng báo nhầm trên 3/6 ảnh âm; validation **TP=0, FP=0, FN=12**, mAP50 0,01208. Model học được cảnh train nhưng chưa tổng quát sang cảnh khác; chưa đủ tin cậy để bật cảnh báo trong demo. [Báo cáo/cách chạy lại](docs/B0_FEASIBILITY.md), [snapshot bằng chứng](docs/evidence/2026-11-16-b0-feasibility.json), [nhật ký](progress/2026-11-16.md). Gate nghiên cứu dữ liệu/B0 chưa hoàn thành; Word/slide/ZIP ngày 14/11 giữ là snapshot trước lượt này.

**Quyết định 16/11/2026 — thử huấn luyện B0 ở mức khả thi phần mềm:** nhãn vùng STTAD của tác giả đã kiểm byte/bounds; thực hiện một thí nghiệm riêng trên bốn cảnh để xác minh data loader, backprop, checkpoint và đầu ra lớp `accident`. Dùng 31 frame có bbox nguồn; frame âm chỉ lấy từ các frame đầu được agent rà riêng, không tự đổi 145 frame thiếu nhãn thành âm. Tách trọn T-T_crash_1/V-V_crash_0 cho train và T-T_crash_2/V-V_crash_1 cho validation chẩn đoán; không có test khóa. Đây là split **development** theo cảnh quan sát được, chưa chứng nhận camera/sự kiện gốc. Giữ YOLOv8n và cấu hình cố định trước chạy; không lấy kết quả này làm benchmark sự kiện hoặc nghiệm thu. Không dùng proposal CADP chưa duyệt; `data/b0_readiness.json` vẫn chặn huấn luyện nghiên cứu chính thức. Thí nghiệm phải ghi rõ nhãn âm do agent rà, giới hạn mẫu, hash/config và lỗi thực tế; không tự chuyển sang B1/verifier/FSM khi gate nghiên cứu còn thiếu.

**Quyết định nghiên cứu bổ sung 14/11:** theo yêu cầu tự tìm hiểu/làm tiếp, kiểm nguồn chính thức CADP và các nguồn CCTV có nhãn vùng. CADP hiện chưa tìm được export bổ sung; STTAD công bố mẫu ảnh/nhãn vùng phù hợp B0. Đã lấy **chọn lọc bốn chuỗi V–V/T–T** ở commit `21f3f5fea50b071f1db61186b481c2a7ccf525c9`: 212 tệp khớp Git blob, **176 ảnh giải mã được, 31 frame có bbox nguồn, 145 frame chưa có nhãn**, hai tệp JPG chứa văn bản được loại khỏi index và giữ nguyên nguồn. Không tải toàn dataset, không thay CADP/split nghiên cứu. Nhóm V–T trong cây nguồn có ảnh `.jpg` nằm dưới `labels/` và không khớp tên chuỗi; không tự đổi tên để ép ghép. Bbox V–V/T–T diễn giải `class xmin_px ymin_px xmax_px ymax_px` đã kiểm bounds/overlay, không mặc định định dạng YOLO. [Ghi nhận nghiên cứu và nguồn](docs/RESEARCH_NOTES.md), [registry chọn lọc](data/registries/sttad_selected_sources.json). `training_eligible=false`; chưa có nhãn temporal đầy đủ, FPS nguồn hoặc group split. Giữ YOLOv8n/ByteTrack và gate B0.

**Quyết định bàn giao 14/11:** người dùng yêu cầu bản có thể nộp/demo và cho biết còn một tháng. Triển khai trước giao diện **cục bộ** cho pipeline đã kiểm chứng, chạy lại video, xuất bằng chứng và tài liệu trình diễn. Phần ghi mốc sự kiện trong giao diện là **review thủ công**, không phải dự đoán va chạm. Đây là công việc đóng gói song song, không thay gate dữ liệu/nhãn, không coi giai đoạn nghiên cứu 6 đã hoàn thành. Giữ YOLOv8n/ByteTrack; giao diện HTML/JS + Python standard library để không thêm framework hoặc dịch vụ mạng cho bản demo CPU.

**Đã hoàn thiện môi trường suy luận CPU và cache theo frame:** YOLOv8n/ByteTrack chạy đủ CADP 221 frame và ba DETRAC 664/936/437 frame; có MP4, JSONL bbox/ID/missing-mask và report hash/config thực tế. Đã đọc lại output, kiểm clock và tách source seconds chưa xác minh khỏi FPS trình chiếu CADP. [Kết quả/cách chạy](docs/INFERENCE_CACHE.md), [nhật ký 14/11](progress/2026-11-14.md).

**Có lỗi thực tế để phân tích:** trong interval 96–130, đề xuất track của xe buýt có 13 frame bị trả class `car`; một frame không đạt ngưỡng overlap debug. Liên kết GT↔track còn là ứng viên, chưa báo IDF1 hoặc metric va chạm. Giai đoạn 1/B0 nghiên cứu vẫn chưa hoàn thành: thiếu pilot đa sự kiện, nhãn vùng nhất quán và split được xác minh; lượt khả thi STTAD ở trên không thay các điều kiện này. Máy hiện tại chạy CPU, không có GPU NVIDIA khả dụng qua `/dev/nvidia*`/`nvidia-smi`; các lượt offline không đại diện benchmark RTX 3050 Ti.

### Phục hồi dữ liệu ngày 12/11/2026

**Đã phục hồi 2.258 ảnh:** CADP 221 ảnh khớp SHA-256 cũ; DETRAC 2.037 ảnh từ mirror ghim revision, đều khớp SHA-256 mirror và CRC/kích thước ZIP chính thức. Có video sạch/preview, 35 vùng B0 đề xuất và registry video tái mã hóa. Google Drive DETRAC bị quota nên dùng mirror làm kênh tải. [Bằng chứng 12/11](docs/evidence/2026-11-12-restoration.json), [hướng dẫn phục hồi](docs/RESTORE_PILOT.md). Metadata/review và điều kiện train giữ nguyên.

### Kết quả kiểm máy ngày 09/11/2026

**Rà trên máy Linux hiện tại:** đồ án vẫn ở giai đoạn 1, chưa đủ điều kiện train B0. Đã tìm và phục hồi `1407.mp4` từ Downloads, tải riêng TXT tác giả `1407.txt`; cả hai SHA-256 khớp catalog. Ảnh sạch CADP, DETRAC, trọng số, output nhãn và môi trường suy luận chưa được phục hồi. Các số lượng ảnh/kết quả tháng 10 dưới đây là **lịch sử máy phát triển**, không phải file đã có trên máy này.

**Hoàn thiện kỹ thuật mới:** [audit hiện trạng](scripts/audit_project.py) xuất JSON/Markdown có hash đầu vào, kiểm metadata và rò rỉ split qua chuỗi/camera/sự kiện/hash/quan hệ dẫn xuất; sửa kiểm fingerprint ảnh và mã lỗi kiểm môi trường. 17 test: **16 đạt, 1 skip** do thiếu pilot ảnh sạch/output. Test đối chiếu TXT/review 96–130 đã chạy đạt. Không đổi nhãn, review, model hoặc tự chia split; `can_train=false` giữ nguyên. [Báo cáo phần còn thiếu và thứ tự hoàn thiện](docs/completion_audit.md), [nhật ký 09/11](progress/2026-11-09.md).

```bash
python3 -B scripts/audit_project.py --strict
python3 -B -m unittest discover -s tests -v
```

Audit trả mã **1** khi còn blocker, lưu báo cáo mới dưới `outputs/audits/project_YYYY-MM-DD*/`. Mã 0 không thay nghiệm thu dữ liệu/nhãn. Kiểm metadata không thay rà near-duplicate bằng media và không chứng minh đủ điều kiện huấn luyện. Không yêu cầu tải toàn ZIP DETRAC chỉ để phục hồi các chuỗi đã trích.

### Hồ sơ đến 20/10/2026 — không phải inventory máy hiện tại

Ngày 20/10 bổ sung hướng dẫn dựng lại, catalog/fingerprint, kiểm file sau clone và xuất bản source lên [GitHub/main](https://github.com/leanhquan0211/DACN_TrafficCollision). Bản công khai giữ metadata nhỏ và loại log máy cá nhân; dữ liệu/mô hình/định nghĩa nhãn không đổi. Các kết quả nghiên cứu dưới đây được thực hiện đến 19/10, không phải run huấn luyện mới. Nhật ký hiện tại: [2026-10-20](progress/2026-10-20.md).

**Đã có:** môi trường `.venv` Python 3.12, PyTorch CUDA và Ultralytics; pipeline YOLOv8n/ByteTrack, ba video mẫu cũ và [manifest](data/manifest.csv). Đã xác minh cặp **1407.mp4/1407.txt** trùng mẫu tác giả; lấy chọn lọc 3 chuỗi DETRAC (2.037 ảnh), ghép MP4 và thử detection/tracking trên clip 10 giây. Lượt tiếp theo cùng ngày đã kiểm ZIP **001407**, lấy 221 ảnh sạch 1280×720, đối chiếu mapping với TXT/demo ở 9 mốc, xuất annotation gốc/chuẩn hóa, video sạch, preview tác giả và chạy YOLO/ByteTrack trên đầu vào sạch. Cả bốn MP4 CADP mới đọc đủ 221 frame. Manifest có **12 asset**, gồm một chuỗi ảnh và các video liên quan; giữ schema và backup trước sửa.

**Xác nhận mới của người dùng:** CADP 001407 **đúng xe và Colliding frame 96–130 rõ ràng/phù hợp** → positive mức chuỗi/sự kiện, GT ID 0 và 2; [phiếu rà theo frame](data/reviews/2026-10-19-cadp-001407-frame-confirmation.json) tách khỏi annotation tác giả. Không cần yêu cầu xác nhận lại mẫu này. FPS nguồn vẫn chưa xác minh, `onset_s/end_s` trống. Ba DETRAC đầy đủ MVI_20011/MVI_20012/MVI_20032 vẫn `negative`; clip con kế thừa từ parent, không đổi ba mẫu cũ. [Phiếu đầu](data/reviews/2026-10-19-user-confirmations.json) giữ làm lịch sử.

**Chuẩn bị nhãn B0 đã làm:** [công cụ và quy tắc vùng đề xuất](docs/b0_label_protocol.md) đã chạy trên 001407: giữ 4.641 dòng object/flags/ignore, tạo **35 bbox ứng viên** trong `data/processed/b0_proposals/001407/`, đánh dấu dẫn xuất/chưa duyệt GT. 186 frame ngoài ứng viên không tự thành negative. Có [chỉ mục 2.037 ảnh âm](data/processed/b0_reviewed_negatives/frames.csv) dựa xác nhận toàn DETRAC, không sao chép ảnh. Đây chưa là tập train. [Inventory](data/pilot_inventory.csv) đếm **1 sự kiện CADP + 3 chuỗi âm**, không đếm 12 asset hoặc video output thành mẫu độc lập.

**Chưa hoàn tất giai đoạn 1/B0:** cần chốt quy tắc vùng accident và rà vùng, mở rộng pilot có nhãn sẵn, kiểm nhóm camera/nguồn/sự kiện. Hộp bao participant hiện chỉ là **đề xuất**, không coi hợp bbox xe thành GT accident đã duyệt. [Readiness](data/b0_readiness.json) giữ `can_train=false`, mọi split `unassigned`. FPS nguồn CADP chưa biết; 25 FPS demo/20 FPS trình chiếu không là nguồn timing. Thiếu này cản giây/chuyển động, không ngăn chuẩn hóa nhãn ảnh B0 theo frame. Chưa fine-tune, chưa verifier/alert/dashboard hoặc benchmark va chạm.

### Mở dữ liệu mới ở đâu?

**Mới nhất:** [nhãn B0 và minh họa đề xuất](docs/b0_label_protocol.md), [kết quả kiểm nguồn VATIC bổ sung](docs/cadp_pilot_sources.md), [nhật ký trong ngày](progress/2026-10-19.md). Các video sạch/GT/model đã có từ lượt trước tại [hướng dẫn ảnh sạch](docs/cadp_001407_clean.md); không tạo thêm MP4 tương tự trong lượt chuẩn hóa nhãn này. Format VATIC/căn chỉnh demo/FPS DETRAC/schema: [Chuẩn bị CADP/DETRAC](docs/dataset_preparation.md).

- Ảnh sạch gốc: `data_raw/cadp/frames/001407/0.jpg … 220.jpg`; ZIP bên cạnh được giữ nguyên.
- Video sạch dùng cho model: `data_samples/cadp/cadp_001407_clean_display20fps.mp4`.
- Preview tác giả trên ảnh sạch: `outputs/annotation_preview/cadp_001407_clean_author_display20fps.mp4`.
- YOLO/ByteTrack trên CADP sạch: `outputs/detection/cadp_001407_clean_display20fps/` và `outputs/tracking/cadp_001407_clean_display20fps/`.
- Bảng annotation và ảnh đối chiếu trước/trong/sau Colliding: `outputs/audits/cadp_001407_clean_2/`.

- Annotation tác giả CADP (đỏ = `Colliding`, không phải dự đoán model): `outputs/annotation_preview/cadp_1407_author_annotations.mp4`.
- Video DETRAC đầy đủ: `data_samples/ua_detrac/MVI_20011.mp4`, `MVI_20012.mp4`, `MVI_20032.mp4`.
- Clip nguồn 10 giây: `data_samples/ua_detrac/MVI_20011_first_10s.mp4`.
- Detection: `outputs/detection/MVI_20011_first_10s/MVI_20011_first_10s_detection.mp4`.
- Tracking: `outputs/tracking/MVI_20011_first_10s/MVI_20011_first_10s_tracking.mp4`.

DETRAC được ghép ở 25 FPS theo [bài báo gốc](https://arxiv.org/html/1511.04136#S2); XML ba chuỗi ghi camera `unstable`. YOLO/ByteTrack chỉ phát hiện/theo dõi phương tiện; xác nhận âm đến từ người dùng. Bước tiếp theo: chốt quy tắc vùng B0 trên đề xuất và lấy VATIC tương ứng từ tác giả để chọn thêm chuỗi sạch. Đã kiểm kho Drive/README/GitHub trực tuyến nhưng **chưa xác minh cặp VATIC bổ sung** ngoài 001407; chưa yêu cầu tải toàn bộ ảnh hoặc gán lại nhãn tay. Không yêu cầu rà lại 001407.

## Vị trí và cấu trúc

Dự án: thư mục `DACN_TrafficCollision` bạn vừa clone; các đường dẫn hướng dẫn tính từ thư mục này.

Dữ liệu CADP gốc đặt trong `data_raw/cadp/`, ảnh sạch đã chuẩn bị ở `data_raw/cadp/frames/001407/`; video ghép để xem/chạy thử đặt ở `data_samples/cadp/`. Giữ nguyên tên tệp nguồn để đối chiếu nhãn. Các mẫu cũ tại gốc `data_samples/` được giữ nguyên. **Không có dataset hoặc video được tải tự động.**

| Thư mục/tệp | Vai trò |
| --- | --- |
| `YOLO_Lo_trinh_DACN.xlsx` | Bản định hướng gốc và kế hoạch thực nghiệm chi tiết; các đề xuất cần kiểm chứng |
| `AGENTS.md` | Chỉ dẫn ngắn để các phiên coding agent sau đọc README và XLSX trước khi làm việc |
| `progress/` | Trạng thái và một file YYYY-MM-DD.md/ngày Asia/Bangkok; mọi task trong ngày cập nhật cùng file |
| `data/manifest.csv` | Hồ sơ 12 asset đã kiểm trên máy phát triển; không có nghĩa file đã tồn tại trên máy vừa clone |
| `docs/GETTING_STARTED.md`, `data/download_catalog.json` | Onboarding cho người/AI mới; nguồn tải chính xác, vị trí lưu, khôi phục đầu ra và lộ trình |
| `data/registries/`, `docs/evidence/` | Fingerprint ảnh và snapshot JSON nhỏ, không chứa dataset/media/annotation gốc |
| `data/reviews/`, `data/b0_readiness.json` | Xác nhận có phạm vi/hash của người dùng và các điều kiện còn thiếu trước B0 |
| `docs/` | Quy tắc nhãn bản nháp, kiểm kê ban đầu và hướng dẫn chuẩn bị CADP/DETRAC |
| `data_raw/` | Gói CADP/UA-DETRAC bạn tải và chuỗi ảnh giữ nguyên cấu trúc gốc |
| `data_samples/` | Một vài video để chạy thử |
| `src/video_pipeline.py` | Vòng xử lý từng frame, lọc class phương tiện, xuất MP4 |
| `scripts/check_environment.py` | Phiên bản Python, thư viện, CUDA và phép tính tensor |
| `scripts/check_project_assets.py` | Kiểm file thực tế/hash theo catalog, tạo khung thư mục khi được chỉ định; không tải/sửa nhãn |
| `scripts/inspect_video.py` | Mở video, đọc frame đầu và metadata |
| `scripts/run_all.py` | Một lệnh kiểm tra video, chạy detection rồi tracking |
| `scripts/run_detection.py` | Phát hiện phương tiện, vẽ bounding box |
| `scripts/run_tracking.py` | Phát hiện và theo dõi bằng ByteTrack, vẽ ID |
| `scripts/prepare_cadp_pilot.py` | Đọc VATIC, xuất bảng ID/Colliding và preview khi có căn cứ căn chỉnh |
| `scripts/prepare_cadp_frames.py` | Lấy riêng 001407 an toàn, kiểm toàn ảnh, so với demo và tạo MP4 sạch/GT riêng |
| `scripts/prepare_detrac.py` | Kiểm kê ZIP, lấy chọn lọc chuỗi, kiểm ảnh, ghép MP4 và clip ngắn |
| `scripts/register_prepared_manifest.py` | Đưa báo cáo chuẩn bị vào manifest, giữ backup và từ chối ID trùng |
| `scripts/update_manifest_reviews.py` | Áp xác nhận người dùng đúng phạm vi/hash và đăng ký CADP sạch, giữ schema/backup |
| `scripts/apply_cadp_frame_review.py` | Áp xác nhận frame/xe mới vào đúng chuỗi, giữ timing nguồn và nhãn các chuỗi khác |
| `scripts/prepare_b0_candidates.py` | Chuẩn hóa VATIC/ignore/frame coverage và xuất bbox vùng đề xuất, chưa duyệt GT |
| `scripts/prepare_b0_negative_index.py` | Lập chỉ mục ảnh âm từ full-sequence review, kiểm CRC/giải mã/hash, không copy dataset |
| `data/processed/`, `data/pilot_inventory.csv` | Nhãn ứng viên/chỉ mục sinh ra và bảng nhóm chuỗi, không phải split huấn luyện |
| `src/data_preparation.py` | Ghi H.264, kiểm tra video, hash và tiện ích chuẩn bị dữ liệu |
| `configs/` | Config căn chỉnh riêng demo CADP 1407; chưa có cấu hình huấn luyện |
| `outputs/` | Kết quả cũ theo tên video; lượt mới dùng annotation_preview/detection/tracking/audits, giữ nguyên kết quả cũ |
| `logs/` | Danh sách phiên bản package; log máy cá nhân giữ local và bị ignore. Bản công khai: docs/environment_reference.md |

## Đọc code theo thứ tự nào?

Luồng video có detection/tracking riêng và chế độ collision thử nghiệm. Nhánh fine-tune B0 chạy riêng theo [hướng dẫn](docs/B0_FEASIBILITY.md); nhánh cảnh báo dùng [run_collision.py](scripts/run_collision.py) → cùng `video_pipeline.run()` → [CollisionRules](src/collision_rules.py) → [ảnh/clip](src/collision_output.py). Không truyền GT vào runtime. Hai chế độ phương tiện giữ luồng sau:

```text
Video nguồn
  → scripts/run_all.py:main() gọi tuần tự ba script, mỗi script là một tiến trình riêng
  → scripts/inspect_video.py:main() kiểm tra metadata và đọc thử frame đầu
  → scripts/run_detection.py → src/video_pipeline.py:run(tracking=False)
       đọc lại video → YOLO.predict từng frame → vẽ bbox xe → MP4 detection
  → scripts/run_tracking.py → src/video_pipeline.py:run(tracking=True)
       đọc lại video → YOLO.track + ByteTrack từng frame → vẽ bbox/ID → MP4 tracking
```

`run_all.py` chạy hai nhánh độc lập: mỗi nhánh mở lại video và nạp model riêng. `cv2.VideoCapture.read()` đưa ra ảnh BGR; YOLO trả `Results`. `inference_export.observations()` tách bbox/class/confidence/ID ra số Python; `FrameCache` ghi JSONL theo frame, giữ clock/missing-mask. `results[0].plot()` tạo ảnh đã vẽ; `H264Writer` trong `src/data_preparation.py` đưa ảnh qua FFmpeg thành MP4. `*.run.json` công bố lượt complete cùng hash và config. [Schema/cách kiểm cache](docs/INFERENCE_CACHE.md).

Mở file trong VS Code theo thứ tự sau:

1. [`scripts/run_all.py`](scripts/run_all.py): xem `main()` chọn thứ tự ba công đoạn và dừng ở bước lỗi.
2. [`scripts/inspect_video.py`](scripts/inspect_video.py): xem `main()` mở video, đọc metadata và một frame để kiểm tra nguồn.
3. [`scripts/run_detection.py`](scripts/run_detection.py): thấy `run(args, tracking=False)` chọn nhánh chỉ phát hiện xe.
4. [`scripts/run_tracking.py`](scripts/run_tracking.py): thấy `run(args, tracking=True)` chọn nhánh thêm ByteTrack.
5. [`src/video_pipeline.py`](src/video_pipeline.py): đọc `arguments()` rồi `run()`; đây là nơi cả hai nhánh thật sự nạp model, đọc frame, suy luận, vẽ và ghi MP4. Khi đọc vòng lặp, theo dõi hai nhánh `predict()` và `track()` riêng.
6. [`scripts/check_environment.py`](scripts/check_environment.py): xem cách kiểm tra thư viện và PyTorch CUDA trước khi xử lý video; file này chạy độc lập, không nằm trong chuỗi `run_all.py`.
7. [`src/inference_export.py`](src/inference_export.py), [`scripts/check_inference_outputs.py`](scripts/check_inference_outputs.py): cache quan sát/clock và kiểm lại MP4, hash, frame count trước khi dùng cho bước sau.

`yolov8n.pt` hiện là trọng số YOLO pretrained để **phát hiện phương tiện**, không có class `accident` mặc định. `bytetrack.yaml` chọn cấu hình thuật toán ByteTrack; nó không phải trọng số YOLO. Track ID là mã tạm do tracker gán trong một lần theo dõi, có thể đổi hoặc mất khi xe bị che. Trong vòng lặp một video, `persist=True` giữ trạng thái ByteTrack từ frame trước để nối ID sang frame sau. Mỗi lần gọi `run()` hiện tạo một đối tượng YOLO mới, nên hai lần chạy/video riêng không dùng chung trạng thái. Nếu sau này sửa code để dùng **cùng đối tượng model** cho nhiều video hoặc camera, phải reset tracker hoặc tạo model mới khi đổi nguồn. Bbox xe và track ID vẫn **chưa chứng minh có va chạm**.

**Ví dụ minh họa, không phải kết quả đo:** Một frame giả định có hai ô tô. YOLO trả hai bbox, class `car` và confidence cho từng bbox. Ở nhánh detection, `plot()` vẽ hai khung xe. Ở nhánh tracking, ByteTrack so hai bbox với trạng thái từ các frame trước và có thể gán ID tạm `7` và `12`; `plot()` vẽ khung kèm ID. Code biến frame đã vẽ thành byte rồi FFmpeg ghi nó vào MP4; frame kế tiếp lại đi qua các bước đó. Hai ID đứng gần nhau vẫn chưa đủ để gọi là tai nạn.

### Huấn luyện bằng gì?

- **YOLO qua Ultralytics:** đã có script chuẩn bị dữ liệu, fine-tune và chẩn đoán B0 khả thi một lớp `accident` trên nhãn nguồn STTAD. [Lượt chạy 16/11](docs/B0_FEASIBILITY.md) lưu config/checkpoint/hash và kết quả yếu; chưa đủ benchmark nghiên cứu. Video/demo vẫn dùng `yolov8n.pt` pretrained cho xe.
- **MLP/GRU qua PyTorch:** khi có quỹ đạo, đặc trưng chuỗi và nhãn thời gian/cặp xe phù hợp, có thể huấn luyện bộ xác minh va chạm. Code hiện chưa tạo các đặc trưng đó và chưa có MLP/GRU.
- Lượt B0 khả thi đã chạy CPU trên máy hiện tại; chưa đo benchmark trên GPU. Việc chuyển máy/Colab chỉ cân nhắc theo nhu cầu dữ liệu và tài nguyên thực tế, giữ cùng config/split khi so sánh.

## Chạy trong PowerShell

Mở PowerShell tại thư mục dự án. Các lệnh dưới đây gọi trực tiếp Python trong `.venv`, nên không phụ thuộc chính sách kích hoạt PowerShell. Nếu muốn kích hoạt thủ công và máy cho phép: `.\.venv\Scripts\Activate.ps1`.

**Thông thường chỉ cần một lệnh** sau khi chép video vào `data_samples`:

```powershell
$env:PYTHONUTF8 = '1'
.\.venv\Scripts\python.exe scripts\run_all.py "data_samples\TEN_VIDEO_GOC.mp4" --device auto --imgsz 640 --output-dir outputs
```

Lệnh này chạy `inspect_video.py`, rồi `run_detection.py`, rồi `run_tracking.py` **lần lượt**. Nếu một bước lỗi, chương trình dừng và báo bước đó. Detection và tracking có thể chạy riêng khi bạn chỉ cần một loại kết quả:

```powershell
.\.venv\Scripts\python.exe scripts\check_environment.py
.\.venv\Scripts\python.exe scripts\inspect_video.py "data_samples\TEN_VIDEO_GOC.mp4"
.\.venv\Scripts\python.exe scripts\run_detection.py "data_samples\TEN_VIDEO_GOC.mp4" --device auto --imgsz 640 --output-dir outputs
.\.venv\Scripts\python.exe scripts\run_tracking.py "data_samples\TEN_VIDEO_GOC.mp4" --device auto --imgsz 640 --output-dir outputs
```

Đổi `TEN_VIDEO_GOC.mp4` thành tên thật. Có thể dùng đường dẫn tuyệt đối trong dấu ngoặc kép. `--device cpu` ép CPU, `--device 0` chọn GPU NVIDIA đầu tiên. `--model` nhận đường dẫn trọng số khác, nhưng mặc định luôn là `yolov8n.pt`. Nếu tệp mặc định chưa có, Ultralytics sẽ thử tải trọng số YOLOv8n chính thức. Không dùng model khác thay thế khi tải thất bại. Script in ra tên và số thứ tự class phương tiện lấy trực tiếp từ model.

Mở cả hai MP4 trong `outputs/<tên-video-không-gồm-đuôi>/`, ví dụ `outputs/YSGhwU9XxuY/YSGhwU9XxuY_detection.mp4` và `..._tracking.mp4`. `--output-dir` chọn thư mục gốc, các script tự tạo thư mục con theo tên video. Kết quả mới nhận hậu tố `_2`, `_3`... nếu tên cũ đã có. Video nguồn không bị sửa. Vòng lặp chỉ giữ frame hiện tại trong RAM; video quá lớn vẫn cần đủ dung lượng trống cho file xuất.

Từ 14/11, mỗi MP4 có thêm `*.frames.jsonl` và `*.run.json`. Mặc định timing là `unknown`; dùng `presentation_only` cho CADP sạch và chỉ dùng `verified_source` kèm file `--timing-evidence` khi có căn cứ nguồn. `run_all.py` truyền các tùy chọn này cho cả hai nhánh. [Lệnh Linux và kết quả hiện tại](docs/INFERENCE_CACHE.md).

## Tái lập môi trường

Máy mới làm theo [hướng dẫn đầy đủ](docs/GETTING_STARTED.md#2-clone-và-tạo-môi-trường): chọn CPU/CUDA trước rồi cài `requirements.txt`. Test tích hợp phụ thuộc dataset sẽ skip nếu input chưa phục hồi, không mặc định năm test đã chạy trên một clone rỗng dữ liệu.

`logs/requirements-installed.txt` lưu toàn bộ phiên bản đã cài. Nếu cần tạo lại `.venv` trên máy có GPU/driver tương thích, cài PyTorch CUDA trước, rồi Ultralytics và phụ thuộc ByteTrack:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --index-url https://download.pytorch.org/whl/cu128 'torch==2.11.0+cu128' 'torchvision==0.26.0+cu128'
.\.venv\Scripts\python.exe -m pip install 'ultralytics==8.4.178' 'lap==0.5.13'
```

Các phiên bản trong tệp freeze là bản ghi thực tế; hai lệnh cài trên dùng đúng nguồn tải cho PyTorch CUDA. Trên máy khác cần chọn bản CUDA phù hợp với GPU và driver theo hướng dẫn PyTorch.

## Kết quả hiện tại

Xem [báo cáo môi trường](docs/environment_reference.md) để biết cấu hình và kiểm tra ban đầu. Ba MP4 ở gốc `data_samples/` là mẫu cũ; các MP4 CADP/DETRAC mới nằm trong thư mục con. Lần thử `run_all.py` với `YSGhwU9XxuY.mp4` (450×360, 25 FPS, 279 frame) đã đọc lại hai MP4 đủ frame. Các lượt dữ liệu/nhãn tiếp theo ở [nhật ký 19/10](progress/2026-10-19.md). Chưa đánh giá accuracy bbox/ID hoặc va chạm.

Python chạy chương trình. PyTorch thực hiện tính toán tensor trên CPU hoặc GPU. CUDA là nền tảng tính toán GPU NVIDIA; driver, CUDA runtime đóng trong bản PyTorch, và CUDA Toolkit cài riêng là ba thứ khác nhau. YOLOv8n tìm đối tượng trong từng frame; ByteTrack liên kết các khung qua thời gian để gán ID. Việc nhìn thấy xe và giữ ID **không tự xác nhận va chạm**.

Tài liệu phát hành/paper CADP đã có trong `data_raw/cadp/documentation/`; nguồn và căn cứ kiểm dữ liệu tại [hướng dẫn](docs/dataset_preparation.md). Giữ tài liệu gốc để tra điều kiện sử dụng/trích dẫn. Ảnh sạch 001407 đã khớp annotation, event đã xác nhận theo frame; FPS nguồn chưa xác minh. Quy tắc vùng accident và dữ liệu pilot đủ đa dạng vẫn là điều kiện trước B0.

## Lỗi thường gặp

- `Video does not exist`: kiểm tra tên và đường dẫn video, giữ dấu ngoặc kép nếu có khoảng trắng.
- `Cannot open/read video`: thử video khác hoặc kiểm tra codec và tệp hỏng bằng `inspect_video.py`.
- `Cannot write output video`: kiểm tra quyền ghi, dung lượng ổ đĩa và codec MP4.
- `CUDA device requested`: chạy `check_environment.py`; dùng `--device cpu` nếu PyTorch CUDA chưa hoạt động.
- Tải `yolov8n.pt` thất bại: kiểm tra mạng; tự đặt đúng trọng số chính thức vào thư mục dự án rồi chạy lại.
- Lỗi kích hoạt `.venv` trong PowerShell: dùng đường dẫn `.\.venv\Scripts\python.exe` như các lệnh trên, không cần đổi chính sách bảo mật.

Với video tiếp theo, chạy `run_all.py` một lần rồi đối chiếu hai video kết quả với video gốc và nhãn CADP trước khi thiết kế bước huấn luyện hay suy luận va chạm.

## Nguồn kỹ thuật

- [PyTorch: cài đặt Windows, CUDA và kiểm tra GPU](https://pytorch.org/get-started/locally/)
- [Ultralytics: cài đặt sau PyTorch](https://docs.ultralytics.com/quickstart/)
- [Ultralytics: ByteTrack trong chế độ tracking](https://docs.ultralytics.com/modes/track/)
