> **Bản lưu lịch sử trước khi rút gọn README ngày 05/11/2026.** Nội dung bên dưới giữ ngữ cảnh và hướng dẫn cũ; khi có khác biệt, ưu tiên [README hiện hành](../README.md), [tiến độ](../progress/README.md) và các chỉ dẫn mới của người dùng. Đường dẫn tương đối đã điều chỉnh về thư mục gốc.

# ĐACN: phát hiện và cảnh báo va chạm giao thông từ video

> **05/11 — B2 và evidence:** đã sửa gate bỏ cặp bbox chồng nhau, so trước/sau trên CADP và DETRAC âm, chạy pipeline offline toàn video và lưu ảnh/clip. Số báo nghi vấn trên DETRAC vẫn cao; chưa có benchmark event độc lập. Một clip ACCIDENT thuộc split test tác giả đã bị dùng cho development trước khi phát hiện split: đã đánh dấu consumed và thêm chốt không mở source test để phát triển. [Tiến độ và bằng chứng](../progress/2026-11-05.md#b2-evaluator-và-evidence--lượt-tiếp-theo), [lệnh chạy](../scripts/README.md#b2-pipeline-và-dữ-liệu-temporal--lượt-tiếp-theo).

> **05/11/2026 — chuyển trọng tâm sang sự kiện và chuyển động:** tạm dừng các vòng train B0; đã có evaluator thử nghiệm, replay B0/B1 từ cache và lát cắt B2 YOLO xe → ByteTrack → đặc trưng/luật. MLP/GRU và FSM mới ở mức giao diện/kiểm thử, chưa có benchmark sự kiện độc lập. Xem [tiến độ từng baseline](../progress/README.md) và [cách chạy](../scripts/README.md#theo-dõi-sự-kiện-và-motion--05112026).

> **04/11/2026 — thí nghiệm B0 được cho phép riêng:** Version 12 SGD learning rate giảm một nửa đã chạy xong và fetch/kiểm về máy. mAP50 val gần ngang V11, mAP50–95 thấp hơn, F1 cố định nhích lên; [báo cáo B0](../docs/b0_pilot_audit.md#chuẩn-bị-version-12--đối-chứng-learning-rate-04112026), [hướng dẫn Kaggle](../docs/kaggle_training.md#version-12--đối-chứng-learning-rate-sgd-04112026), [dashboard](../frontend/README.md#theo-dõi-file-local-và-kaggle), [nhật ký](../progress/2026-11-04.md). Chưa thay checkpoint B0 đang khóa. Yêu cầu tạm dừng trước đây vẫn áp dụng cho các thí nghiệm khác.

> **Dashboard đã triển khai 02/11:** chạy `.\.venv-dashboard\Scripts\python.exe -X utf8 -B scripts/serve_dashboard.py`, mở **http://127.0.0.1:8765**. [Cài đặt/cách dùng](../frontend/README.md), [thiết kế/phạm vi](../frontend/DESIGN.md). Đọc artifact thật, xem train/so sánh/ảnh/video, kiểm kê dữ liệu và snapshot Kaggle chỉ đọc; không mở hoặc điều khiển train, không thay checkpoint.

> **Giao diện 04/11:** theo ảnh tham khảo hồng phấn/tím than, có lựa chọn font tiếng Việt trong phần Tùy chỉnh giao diện; Be Vietnam Pro + Geist vẫn là mặc định. [Xem cách đổi font](../frontend/README.md#mở-trên-máy-hiện-tại).

> **Báo cáo tổng hợp cập nhật 04/11/2026:** [bản đọc Markdown](../docs/BAO_CAO_TIEN_DO_DACN.md), [PDF trình bày](../docs/BAO_CAO_TIEN_DO_DACN.pdf). Báo cáo giải thích căn cứ chọn dữ liệu/model/công cụ/Kaggle, lịch sử B0, kết quả V12 và mức triển khai thật của B1/dashboard; không thay bảng baseline hoặc nhật ký ngày. Mọi lựa chọn tiếp theo cần ghi nhu cầu, nguồn/bằng chứng, phương án thay thế và giới hạn; phân biệt căn cứ lịch sử với đối chiếu sau. Ngoài run V12 đã được cho phép riêng, tiếp tục tạm dừng mở thí nghiệm hoặc chỉnh mô hình mới.

> **Mới clone hoặc bắt đầu với AI mới? Đọc [GETTING_STARTED — cài môi trường, tải gì/ở đâu/lưu đâu và tiếp tục thế nào](../docs/GETTING_STARTED.md).** Repo giữ code/config/metadata/nhật ký; dataset, trọng số, `.venv`, video và audit đầy đủ nằm cục bộ, không có sau clone. [Catalog tải](../data/download_catalog.json), [kiểm file hiện có](../scripts/check_project_assets.py), [snapshot bằng chứng nhỏ](../docs/evidence/README.md).

> **Tài liệu định hướng của project.** README này tóm tắt kế hoạch trong [YOLO_Lo_trinh_DACN.xlsx](../YOLO_Lo_trinh_DACN.xlsx) và ghi trạng thái triển khai thực tế. File XLSX là bản phác thảo ban đầu, không phải kết quả thực nghiệm hoặc yêu cầu đã được giảng viên duyệt. Các thông số, mô hình và mốc thời gian ghi là **dự kiến** cho đến khi được kiểm chứng. Khi cần chi tiết về dữ liệu, pipeline, đánh giá hoặc nguồn tham khảo, đọc các sheet `01_Huong_DACN`, `05_Cac_buoc`, `07_Pipeline`, `08_Du_lieu`, `09_Danh_gia`, `13_Ke_hoach` và `15_Nguon`.


## Bắt đầu ở đâu?

| Bạn cần gì? | File chính |
| --- | --- |
| Cài máy, tải dữ liệu đúng nơi, chạy lại | [GETTING_STARTED](../docs/GETTING_STARTED.md) |
| Đăng nhập, gửi train PRIVATE lên Kaggle và nhận kết quả | [Kaggle training](../docs/kaggle_training.md) |
| Paper, tóm tắt và hướng áp dụng | [Literature review](../reference/LITERATURE_REVIEW.md) |
| Tra thuật ngữ và ví dụ ngắn | [GLOSSARY — Ctrl+F](../reference/GLOSSARY.md) |
| Tiến độ từng baseline, phần còn thiếu và lịch sử | [Bảng baseline chung](../progress/README.md) |
| Frontend xem kết quả, train và phân tích lỗi | [Chạy dashboard local](../frontend/README.md), [thiết kế/phạm vi](../frontend/DESIGN.md); có API đọc artifact và snapshot Kaggle theo yêu cầu |
| Biết chạy script nào | [scripts/README](../scripts/README.md) |
| Đọc kết quả train, loss, mAP và các ảnh | [Hướng dẫn outputs/training](../outputs/training/README.md) |
| Dữ liệu/pool B0 đang có | [Báo cáo hiện hành](../docs/b0_pilot_audit.md) |
| Tìm hướng dẫn chi tiết/lịch sử | [docs/README](../docs/README.md) |

## Quy tắc định hướng cho mọi công việc tiếp theo

**Train mới từ 30/10:** chỉ áp dụng early stopping sau hơn 20 epoch; khóa mốc bắt đầu và patience trong config từng run. Lệnh theo dõi thông thường dùng `logs --follow --epochs-only --version <N>` để xem tóm tắt epoch. Run AdamW Kaggle mới và căn cứ ở [hướng dẫn](../docs/kaggle_training.md) và [bảng tiến độ](../progress/README.md); không thay mô hình B0 đang khóa chỉ theo điểm train.

**Kaggle chỉ dùng tài nguyên miễn phí:** không bật dịch vụ trả phí hoặc gắn tài khoản thanh toán. Nếu hết quota thì dừng/chờ; không tự chuyển sang tài nguyên tính phí. Mục chọn GPU nằm trong trình chỉnh sửa notebook (Edit → Settings/Session options → Accelerator), không phải trang quota của tài khoản. [Hướng dẫn Kaggle](../docs/kaggle_training.md).

1. Trước khi chọn việc làm, công cụ, mô hình, dữ liệu hoặc cách đánh giá, đọc README này và phần liên quan trong XLSX. Bám vào **mục tiêu phát hiện sự kiện va chạm từ CCTV cố định**, câu hỏi nghiên cứu, thứ tự baseline → phân tích lỗi → xác minh chuyển động → cảnh báo → đánh giá, cùng giới hạn máy hiện có.
   Trước khi triển khai, đọc paper/mã tác giả/tài liệu chính thức liên quan và [literature review](../reference/LITERATURE_REVIEW.md). Ghi rõ recipe gốc, nhãn/metric thật, phần nào áp dụng và phần nào phải điều chỉnh cho B0 hoặc máy hiện có trong config và báo cáo; kiểm bằng validation, không tự chọn theo cảm tính hay gọi bản điều chỉnh là tái lập paper.
2. Không thêm mô hình hay công nghệ chỉ vì mới hơn hoặc có sẵn. Nêu vấn đề quan sát được, phương án đơn giản đang dùng, điều kiện chuyển hướng và phép đo cần có. Ưu tiên hoàn thành, đo và hiểu baseline trước khi mở rộng.
3. Phân biệt rõ **đã chạy/đã đo**, **đang làm** và **dự kiến** trong code, tài liệu, demo và báo cáo. Không biến gợi ý, số liệu paper hoặc giá trị mẫu trong XLSX thành kết quả của project. Không tuyên bố `real-time`, cải thiện độ chính xác hay tính mới khi chưa có benchmark phù hợp.
4. Khi thay đổi phạm vi, dataset, nhãn, stack hoặc protocol đánh giá, ghi lý do và bằng chứng trong README/config hoặc nhật ký thí nghiệm, rồi cập nhật phần kế hoạch liên quan. Nếu README và XLSX chưa khớp, đối chiếu bản gốc và quyết định đã ghi; chỉ dẫn mới của người thực hiện và yêu cầu của giảng viên được ưu tiên, sau đó cập nhật tài liệu để lần sau dùng cùng một định hướng.
5. Mỗi bước mới phải có đầu ra có thể kiểm tra và điều kiện chuyển bước. Giữ split, nhãn, config, checkpoint, phiên bản thư viện và log đo để tái lập; không dùng test set để chọn ngưỡng hay tinh chỉnh mô hình.
6. Trước khi kết thúc công việc, cập nhật **[bảng tiến độ chung của mọi baseline](../progress/README.md)** (phần cần làm, trạng thái, bằng chứng, đầu ra/điều kiện hoàn thành và việc tiếp theo) cùng nhật ký ngày. Không tạo file tiến độ riêng cho từng baseline; README này giữ định hướng, bảng trên giữ trạng thái. Quy tắc nhật ký: **một file `progress/YYYY-MM-DD.md` cho mỗi ngày theo Asia/Bangkok**. Mọi task/lần chạy/lượt trao đổi cùng ngày thêm thành mục trong file đó, không tạo file hậu tố theo chủ đề. Ghi mục tiêu, việc đã làm, bằng chứng, quyết định và bước tiếp theo; giữ trạng thái lịch sử tách kết quả mới. Không đánh dấu giai đoạn hoàn thành nếu chưa đạt điều kiện chuyển bước.
7. **Quyết định người dùng 24/10/2026:** AI chủ động đọc, tìm, so sánh và chọn phương án từ paper/mã/dữ liệu/nhãn **công khai**. Nguồn cần xin riêng hoặc chưa truy cập được thì bỏ khỏi đường triển khai và tìm thay thế; không giao người dùng xin tác giả hoặc chờ giảng viên duyệt quyết định kỹ thuật. Kiểm sheet `11_Cong_trinh`/`15_Nguon` trước; lưu nguồn và căn cứ dùng/bỏ ở [reference/](../reference/README.md), giải thích cho người mới bằng công cụ/tiêu chí thực tế. Không bịa nhãn khi thiếu.

## Mục tiêu và phạm vi

**Đầu vào:** video có timestamp từ **một camera CCTV cố định**. **Đầu ra dự kiến:** một sự kiện va chạm xe–xe gồm `event_id`, thời điểm, camera, độ tin cậy, các ID track liên quan và ảnh/clip bằng chứng trên dashboard. Track ID chỉ là mã tạm trong video, không phải danh tính xe ngoài đời. Ban đầu có thể giới hạn ô tô; chỉ thêm xe máy nếu nhãn và detector hỗ trợ đủ tốt.

Đây là **collision detection**: nhận biết va chạm đang hoặc vừa xảy ra. Dự báo trước va chạm (*anticipation*), đa camera, graph, VLM và mô hình video lớn là các hướng mở rộng riêng, không phải yêu cầu cốt lõi của ĐACN. Triển khai theo phạm vi hiện có và bằng chứng; không đặt việc xin duyệt quyết định kỹ thuật thành điều kiện bắt đầu.

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

**Nguồn vùng B0:** nhãn STTAD public và bbox impact tác giả ACCIDENT; lần mở rộng dùng ACCIDENT real xe–xe theo [policy âm có căn cứ](../configs/b0_verified_label_policy.json), [đối chiếu paper/dữ liệu](../reference/2026-10-24-public-data-review.md) và [báo cáo B0](../docs/b0_pilot_audit.md). Bbox impact chỉ dùng ở đúng frame đã kiểm; frame sớm chưa rà không tự thành nhãn âm. Âm train lấy từ frame đã rà, chuỗi DETRAC người dùng xác nhận và clip TAD được tác giả gắn normal. Giữ CADP 001407 đã khớp để debug/đối chiếu motion. TAD có link video public nhưng ZIP đã đọc danh mục không có bbox, nên không tự thay cho nhãn vùng. Kiểm ảnh/frame, timing, khoảng trước/sau và phạm vi annotation thật của từng nguồn. Video âm dài và hard negatives là phần đánh giá mở rộng. Trạng thái và số liệu mới nhất xem [bảng baseline duy nhất](../progress/README.md).

Manifest tối thiểu: `video_id`, `camera_id`, `source_event_id`, nguồn, split, thời lượng, `onset_s`, `end_s`, loại sự kiện, xe liên quan và độ chắc chắn nhãn. Với dữ liệu âm tính, thời điểm va chạm để trống. Nhãn cửa sổ cho bài toán detection phải dựa vào thời điểm cuối cửa sổ; đoạn **trước onset** là âm tính, không gán cả clip tai nạn là dương tính. Nếu chưa có nhãn xe liên quan, chỉ làm mức scene và ghi rõ giới hạn đó.

Loại clip trùng/gần trùng; chia train/validation/test theo **camera, nguồn hoặc sự kiện** để các bản cắt của cùng tai nạn ở cùng một split. Fit chuẩn hóa và chọn đặc trưng trên train; chọn ngưỡng trên validation; chỉ đánh giá test với cấu hình đã khóa. Pilot nhỏ chỉ để kiểm tra pipeline, không tự là benchmark đáng tin cậy.

## Thứ tự thực hiện và điều kiện chuyển bước

**Điều chỉnh phạm vi theo người dùng 26/10/2026:** triển khai **B0 pilot ảnh phát hiện va chạm cơ bản** trước. Âm khó, video âm dài, kiểm camera-held-out và đánh giá sự kiện đầy đủ thuộc bước mở rộng; chúng không chặn train pilot trên nhãn public đã kiểm. Pilot giữ bbox accident, dữ liệu sạch và split theo nhóm nguồn; có cấu hình/checkpoint/metric riêng và công bố giới hạn tập nhỏ. `can_train` của benchmark đầy đủ và `pilot_release.can_train` được ghi riêng trong readiness. Không xem kết quả pilot là chứng minh RQ1/RQ2 hoặc đã hoàn thành toàn B0.

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

**Hạ tầng train29/10 — chuyển Kaggle:** đã chuẩn bị gói **2.988ảnh(train2.681/val307)**, notebookPRIVATE và luồng gửi/nhận tự động, thêm420normal train có nhãn tác giả từ các nhóm cũ theo yêu cầu dùng dữ liệu đầy đủ hơn. Giữ recipe/checkpoint khởi tạo, không lấy test/reserve hoặc đổi nhãn/split cũ. **Chưa upload/khởi chạy vì thiếu đăng nhập Kaggle**, không train laptop và không theo dõi train liên tục. [Hai lệnh người dùng cần chạy](../docs/kaggle_training.md#bạn-cần-làm-ngay), [bước triển khai](../KE_HOACH_TRIEN_KHAI.md); trạng thái API thật ở`outputs/kaggle/b0_s960_full_kaggle_v1/deployment.json`.

**Mới nhất29/10 — hardneg đã train xong:** người dùng hoàn tất `b0_s960_hardneg_v1` ở15epoch, bestCSV5, patience10. Trên **cùng307val**: mAP50 **68,48%**, mAP50–95 **55,43%**; tại confidence0,25/IoU0,5:63TP/49FP/28FN, F1 **62,07%**,5/216ảnh âm có hộp. So mốc cũ cùng tập, mAP50–95 tăng nhưng F1 giảm; chưa xác nhận cải thiện tổng thể hoặc đạt mAP50>70% ở checkpoint được chọn. [Báo cáo](../docs/b0_pilot_audit.md#kết-quả-s960-hardneg-hoàn-tất--29102026), [snapshot](../docs/evidence/2026-10-29-b0-hardneg-validation.json). Không train thêm, không mở reserve mới hoặc thay điểm vận hành cũ.

**Mốc chuẩn bị trước đó29/10:** đã đo B0/B1 causal trên12chuỗi/4.845frame; xuất release2.680ảnh với510normal mới trong train/val và120normal mới giữ riêng. Recipe warm-start s960/SGD0,0003/trần40/patience10 nằm trong [config](../configs/b0_s960_hardneg_v1.json); bằng chứng lúc chưa train giữ tại [hồ sơ chuẩn bị](../docs/b0_pilot_audit.md#chuẩn-bị-s960-hardneg-v1--29102026). Giữ bbox impact gốc, mining chỉ trong train sau khóa nhóm, không chuyển test/holdout đã xem vào train. [Phép đo B1](../docs/b0_pilot_audit.md#đo-b0b1-trên-video-sạch--29102026) là chẩn đoán, chưa benchmark event/RQ1/RQ2.

**Bước trước cùng ngày:** đã khóa s960/confidence0,27 bằng val rồi đo một lần holdout âm34/120ảnh có hộp; tập này hiện consumed. [Hồ sơ](../docs/b0_pilot_audit.md#chọn-ngưỡng-và-đánh-giá-holdout-âm--29102026). Các metric68,60%mAP50/53,94%mAP50–95 vẫn là run s960 cũ trên217val, không phải kết quả release mới307val.

**Kết quả mới 28/10:** [B0 s960](../configs/b0_s960_v1.json) đã hoàn tất ở epoch 45 với early stopping patience15; best theo CSV ở epoch30. Validation sau train: mAP50 **68,60%**, mAP50–95 **53,94%**, chưa đạt mục tiêu mAP50 >70%. [Báo cáo và bằng chứng](../docs/b0_pilot_audit.md#kết-quả-b0-s960-hoàn-tất--28102026).

**Đã hoàn thành vòng pilot ảnh B0 và chẩn đoán trên video sạch; B0 sự kiện đầy đủ chưa hoàn thành.** Checkpoint mốc đã train trên release 1.750 ảnh và đo test; release mới **2.170 ảnh đã train đủ 60 epoch và đánh giá trên 217 ảnh validation**, có 120 frame normal giữ riêng ngoài dataset. Các model cũ đã được đo trên cùng validation mở rộng để làm mốc so sánh. [Dữ liệu mới và lệnh train](../docs/b0_pilot_audit.md#b0-normal-mở-rộng--28102026). Công cụ `scripts/analyze_b0.py` còn có chẩn đoán 9 chuỗi sạch tại `outputs/training/b0_verified_pilot_v1/diagnostics/`. B1, luật B2, T0 và B3/T1 chưa hoàn thành; bảng trạng thái duy nhất nằm trong progress/README.

Quyết định nhãn 26/10: [policy v4](../configs/b0_public_label_policy.json) giữ **đúng các frame trước impact đã kiểm PTS/pixel và rà toàn ảnh**, dựa vào mốc first-visible-contact tác giả ACCIDENT. Đây là nhãn âm dẫn xuất có phiếu rà của AI, không phải nhãn âm tác giả hoặc xác nhận mới của người dùng. Không áp dụng cho cả interval/clip; giữ phần còn lại unknown, bbox impact và các xác nhận CADP/DETRAC không đổi. Policy mở release **pilot ảnh** riêng; gate benchmark đầy đủ vẫn đóng. [Bằng chứng, kết quả và lệnh tái tạo](../docs/b0_pilot_audit.md#pilot-b0-ảnh-26102026).

Xem **[một bảng tiến độ cho tất cả baseline](../progress/README.md)** để biết từng phần đã làm, còn thiếu, đầu ra cần đạt và quá trình theo ngày. Số liệu/giới hạn dữ liệu hiện hành ở [báo cáo B0](../docs/b0_pilot_audit.md), gate kỹ thuật ở [readiness](../data/b0_readiness.json). README không sao thêm các bảng số liệu/trạng thái lịch sử; các mốc đó được dẫn từ bảng baseline và nhật ký.

## Cấu trúc và cách dùng lâu dài

```text
DACN_TrafficCollision/
├── README.md, AGENTS.md, YOLO_Lo_trinh_DACN.xlsx
├── src/                         # vòng xử lý và helper dùng chung
├── scripts/                     # lệnh chạy video/chuẩn bị dữ liệu
│   └── maintenance/             # bảo trì manifest/review, ít dùng
├── tests/, configs/             # kiểm tra và policy/cấu hình
├── reference/                   # literature review + glossary + nguồn
├── docs/                        # hướng dẫn; evidence/ giữ snapshot nhỏ
├── data/                        # manifest/review/fingerprint
│   └── processed/               # pool/nhãn sinh ra, không Git
├── data_raw/, data_samples/     # raw và video ghép/thử, không Git
├── outputs/                     # prediction/audit, không Git
│   └── audits/archive/          # audit thử cũ không còn tham chiếu
├── progress/                    # lịch sử theo ngày, không phải bước chạy
└── logs/                        # snapshot môi trường
```

Dữ liệu giữ tên/path nguồn; code không cần chạy tất cả script. Chọn lệnh theo [scripts/README](../scripts/README.md), đọc metadata tại [data/README](../data/README.md), xem vai trò config ở [configs/README](../configs/README.md). Dataset/model/output và `.venv` không có sau clone. Các thư mục tạm/môi trường/cache được ẩn trong VS Code Explorer; vẫn tồn tại và dùng bình thường. Bố cục được rà 25/10; kết quả dữ liệu và công cụ mới nhất xem bảng baseline chung và nhật ký ngày, không coi chúng là thí nghiệm huấn luyện model.

## Đọc code theo thứ tự nào?

Luồng **vehicle detection/tracking ban đầu** chỉ vẽ phương tiện và ID theo dõi:

```text
Video nguồn
  → scripts/run_all.py:main() gọi tuần tự ba script, mỗi script là một tiến trình riêng
  → scripts/inspect_video.py:main() kiểm tra metadata và đọc thử frame đầu
  → scripts/run_detection.py → src/video_pipeline.py:run(tracking=False)
       đọc lại video → YOLO.predict từng frame → vẽ bbox xe → MP4 detection
  → scripts/run_tracking.py → src/video_pipeline.py:run(tracking=True)
       đọc lại video → YOLO.track + ByteTrack từng frame → vẽ bbox/ID → MP4 tracking
```

`run_all.py` **không chuyển bbox hoặc frame từ detection sang tracking**: mỗi nhánh mở lại video gốc và nạp model trong tiến trình riêng. Cả hai dùng `video_pipeline.arguments()` để nhận tham số và `video_pipeline.run()` để xử lý. Trong `run()`, `cv2.VideoCapture.read()` đưa ra từng frame là mảng ảnh BGR kích thước `(cao, rộng, 3)`; YOLO trả `Results` chứa bbox, class và confidence. Khi tracking, kết quả có thể có thêm ID. `results[0].plot()` tự lấy các thông tin đó để tạo ảnh đã vẽ; code hiện **không tách bbox/ID ra biến riêng**. Ảnh được đổi thành byte BGR, đưa qua pipe cho FFmpeg mã hóa thành MP4.

Nhánh B0 riêng hiện có: `scripts/train_b0.py` tạo checkpoint class `accident`; `scripts/analyze_b0.py` nhận checkpoint đó và video/ảnh sạch, tách bbox/confidence mỗi frame, ghi CSV/JSONL và MP4. `src/b0_diagnostics.py` phân tích lỗi hình học và gom các frame có bbox liên tiếp thành log thô. Log này chuẩn bị đầu vào B1, chưa phải cảnh báo đã xác nhận. Nên đọc nhánh B0 sau khi hiểu vòng đọc frame của pipeline vehicle.

Nhánh B1 đã có `CausalScoreFilter` trong cùng `src/b0_diagnostics.py`; `analyze_b0.py --temporal-diagnostics` so các trạng thái B0/EMA/k-of-N. Trạng thái bật hoặc đoạn bật liên tiếp chưa là sự kiện tai nạn đã xác minh; không đồng nhất bbox class`accident` với track ID của nhánh phát hiện xe.

Mở file trong VS Code theo thứ tự sau:

1. [`scripts/run_all.py`](../scripts/run_all.py): xem `main()` chọn thứ tự ba công đoạn và dừng ở bước lỗi.
2. [`scripts/inspect_video.py`](../scripts/inspect_video.py): xem `main()` mở video, đọc metadata và một frame để kiểm tra nguồn.
3. [`scripts/run_detection.py`](../scripts/run_detection.py): thấy `run(args, tracking=False)` chọn nhánh chỉ phát hiện xe.
4. [`scripts/run_tracking.py`](../scripts/run_tracking.py): thấy `run(args, tracking=True)` chọn nhánh thêm ByteTrack.
5. [`src/video_pipeline.py`](../src/video_pipeline.py): đọc `arguments()` rồi `run()`; đây là nơi cả hai nhánh thật sự nạp model, đọc frame, suy luận, vẽ và ghi MP4. Khi đọc vòng lặp, theo dõi hai nhánh `predict()` và `track()` riêng.
6. [`scripts/check_environment.py`](../scripts/check_environment.py): xem cách kiểm tra thư viện và PyTorch CUDA trước khi xử lý video; file này chạy độc lập, không nằm trong chuỗi `run_all.py`.

`yolov8n.pt` hiện là trọng số YOLO pretrained để **phát hiện phương tiện**, không có class `accident` mặc định. `bytetrack.yaml` chọn cấu hình thuật toán ByteTrack; nó không phải trọng số YOLO. Track ID là mã tạm do tracker gán trong một lần theo dõi, có thể đổi hoặc mất khi xe bị che. Trong vòng lặp một video, `persist=True` giữ trạng thái ByteTrack từ frame trước để nối ID sang frame sau. Mỗi lần gọi `run()` hiện tạo một đối tượng YOLO mới, nên hai lần chạy/video riêng không dùng chung trạng thái. Nếu sau này sửa code để dùng **cùng đối tượng model** cho nhiều video hoặc camera, phải reset tracker hoặc tạo model mới khi đổi nguồn. Bbox xe và track ID vẫn **chưa chứng minh có va chạm**.

**Ví dụ minh họa, không phải kết quả đo:** Một frame giả định có hai ô tô. YOLO trả hai bbox, class `car` và confidence cho từng bbox. Ở nhánh detection, `plot()` vẽ hai khung xe. Ở nhánh tracking, ByteTrack so hai bbox với trạng thái từ các frame trước và có thể gán ID tạm `7` và `12`; `plot()` vẽ khung kèm ID. Code biến frame đã vẽ thành byte rồi FFmpeg ghi nó vào MP4; frame kế tiếp lại đi qua các bước đó. Hai ID đứng gần nhau vẫn chưa đủ để gọi là tai nạn.

### Sau này huấn luyện bằng gì?

- **YOLO qua Ultralytics:** đã fine-tune một B0 pilot vùng `accident` bằng ảnh/nhãn public đã rà; script `train_b0.py`, split, config và checkpoint ở [báo cáo B0](../docs/b0_pilot_audit.md#pilot-b0-ảnh-26102026). Kết quả test đầu kém, cần mở rộng/kiểm dữ liệu và đo lại. Pipeline vehicle detection/tracking cũ vẫn dùng `yolov8n.pt` pretrained cho xe.
- **MLP/GRU qua PyTorch:** đã có đặc trưng B2, interface MLP/GRU causal và kiểm tensor/fixture; chưa có nhãn thời gian/cặp xe phù hợp để train hoặc báo metric. Xem [trạng thái hiện hành](../progress/README.md).
- B0 pilot đã train trên laptop RTX 3050 Ti. Các vòng sau có thể chạy laptop hoặc Colab khi dữ liệu/tài nguyên yêu cầu; mỗi run phải lưu cấu hình, nguồn nhãn và metric thực tế.

## Chạy trong PowerShell

Mở terminal ở gốc project, sau khi cài môi trường/tải đúng dữ liệu theo [GETTING_STARTED](../docs/GETTING_STARTED.md):

```powershell
.\.venv\Scripts\python.exe scripts/run_all.py "data_samples/TEN_VIDEO_GOC.mp4" --device auto --imgsz 640 --output-dir outputs
```

Đổi tên video thật. Lệnh đọc video gốc, chạy detection và tracking riêng, xuất MP4 dưới `outputs/<tên-video>/`; file nguồn không bị sửa. Dùng ảnh/video sạch, không đưa GT preview đã vẽ vào model. Các lệnh kiểm môi trường, asset, chuẩn bị B0 và bảo trì được liệt kê trong [scripts/README](../scripts/README.md); không cần chạy lại toàn bộ mỗi buổi.

Môi trường pin/CPU/CUDA xem [GETTING_STARTED](../docs/GETTING_STARTED.md#2-clone-và-tạo-môi-trường), kết quả đã kiểm xem [environment_reference](../docs/environment_reference.md). Các số đo lịch sử không chứng minh máy mới đã chạy được; test tích hợp sẽ skip nếu thiếu input.

## Lỗi thường gặp

- `Video does not exist`: kiểm tra tên và đường dẫn video, giữ dấu ngoặc kép nếu có khoảng trắng.
- `Cannot open/read video`: thử video khác hoặc kiểm tra codec và tệp hỏng bằng `inspect_video.py`.
- `Cannot write output video`: kiểm tra quyền ghi, dung lượng ổ đĩa và codec MP4.
- `CUDA device requested`: chạy `check_environment.py`; dùng `--device cpu` nếu PyTorch CUDA chưa hoạt động.
- Tải `yolov8n.pt` thất bại: kiểm tra mạng; tự đặt đúng trọng số chính thức vào thư mục dự án rồi chạy lại.
- Lỗi kích hoạt `.venv` trong PowerShell: dùng đường dẫn `.\.venv\Scripts\python.exe` như các lệnh trên, không cần đổi chính sách bảo mật.

Bước nghiên cứu tiếp theo vẫn theo [readiness B0](../data/b0_readiness.json); việc sắp xếp tài liệu không đánh dấu B0 hoàn thành hoặc thay mô hình.

## Nguồn kỹ thuật

- [PyTorch: cài đặt Windows, CUDA và kiểm tra GPU](https://pytorch.org/get-started/locally/)
- [Ultralytics: cài đặt sau PyTorch](https://docs.ultralytics.com/quickstart/)
- [Ultralytics: ByteTrack trong chế độ tracking](https://docs.ultralytics.com/modes/track/)
