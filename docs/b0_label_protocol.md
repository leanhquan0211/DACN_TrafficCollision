# Nhãn B0: phần đã chuẩn hóa và quy tắc vùng tai nạn đề xuất

## Quyết định hiện tại — 26/10/2026

Policy **v4** giữ bbox vùng tác giả, bổ sung 13 impact ACCIDENT đã rà và **30 frame âm cùng cảnh**. Âm mới là nhãn dẫn xuất từ mốc first-visible-contact tác giả, biên >=1 giây PTS file và kiểm trực quan toàn ảnh tại đúng frame; nguồn ghi `derived_author_preimpact_assistant_frame_review`. Không gọi là annotation âm tác giả hay xác nhận người dùng. Chỉ 30 frame có phiếu/hash/pixel/PTS được dùng; phần còn lại của clip vẫn unknown. [Phiếu frame](../data/reviews/2026-10-26-preimpact-frame-review.json), [pilot và giới hạn](b0_pilot_audit.md#pilot-b0-ảnh-26102026).

Pool tham chiếu v3: **48 dương/2.375 âm**, 21 nhóm nguồn dương, 17 nhóm có cả hai nhãn. Từ đó đã xuất pilot thật **17 impact ACCIDENT + 30 frame âm đã rà**, chia 30/9/8 ảnh theo nhóm nguồn và train/đo. Gate pilot được mở riêng; hard negatives và benchmark sự kiện để sau theo quyết định người dùng. Các số 35/2.345 và policy v2 bên dưới là mốc lịch sử 25/10.

### Quyết định lịch sử — 25/10/2026

Giữ định nghĩa vùng B0; policy v2 bổ sung bbox tác giả **ACCIDENT v9 tại impact**, chỉ dùng mẫu đã kiểm PTS và phạm vi hình học. Trong sáu clip đã lấy, bốn bbox vào pool v2, hai bbox thiếu/chưa rõ phạm vi bị loại, không chỉnh hộp nguồn. Không lan hộp impact sang frame khác hoặc gán các frame đó là âm. [Phiếu rà AI](../data/reviews/2026-10-25-accident-source-review.json), [kết quả hiện hành](b0_pilot_audit.md). Pool có 35 frame dương/2.345 frame âm; chưa split/train. Timing PTS của file ACCIDENT được kiểm riêng, FPS nguồn CADP vẫn chưa xác minh.

### Căn cứ STTAD từ 24/10 — tiếp tục áp dụng

Theo yêu cầu người dùng, không chờ tác giả chia sẻ riêng hoặc giảng viên duyệt. AI đã chọn **vùng sự kiện theo STTAD Table II**, bao các bên tham gia sự kiện, và dùng **nhãn vùng tác giả public** cho B0 trước mắt; không tự tạo lại bbox từ vehicle detector. [Policy](../configs/b0_public_label_policy.json), [reference/bằng chứng](../reference/2026-10-24-public-data-review.md). Sau mở rộng: **4 STTAD, 31 bbox/frame nguồn hợp biên và chuyển YOLO**, frame thiếu TXT giữ unknown. Hai TAD normal dùng nhãn clip âm nguồn, không tạo bbox dương từ nhãn clip. [Pool/nhóm cảnh](b0_pilot_audit.md) đã chuẩn bị, chưa split/train. B0 vẫn là YOLO accident-region ảnh, không đổi thành phân loại clip.

Phần CADP bên dưới là hồ sơ công cụ/đề xuất 19/10, được giữ riêng để đối chiếu, **không còn là yêu cầu người dùng xin duyệt**. Chạy `scripts/audit_cadp_b0_quality.py` để xuất từng frame giữ/loại theo flags: 35 ứng viên không occluded/không chồng ignore; 186 frame unknown loại khỏi supervision. Khi participant bị che/missing/outside hoặc vùng dẫn xuất chồng ignore, loại với lý do, không vẽ bù. STTAD không có visibility flag thì ghi `not_provided`, không tự phán không che.

## B0 trong kế hoạch thật

Theo README và sheet `05_Cac_buoc` bước 05, `08_Du_lieu` mục D3, `09_Danh_gia` mục B0:

- **Đầu vào:** ảnh/frame sạch, truy được video/chuỗi/sự kiện gốc; train về sau cần cả ảnh dương có bbox và ảnh âm được rà đủ.
- **Đầu ra model:** bbox vùng `accident`, class và confidence trên từng frame; không phải bbox xe pretrained hoặc ID tracker. Quyết định/cảnh báo theo thời gian là các bước B1/B2 về sau.
- **Nhãn cần:** quy tắc nhất quán xác định một vùng accident là gì, khoảng frame hợp lệ và các vùng/frame chưa đủ căn cứ. Định dạng YOLO `0 cx cy w h`, chuẩn hóa theo kích thước ảnh; pilot đã có train/val/test theo nhóm nguồn.

## Mẫu dương, mẫu âm và mẫu chưa biết

“Dương/âm” phải gắn với **điều cần nhận biết** và **đơn vị được gán nhãn**. Với B0, điều cần tìm là vùng tai nạn trong **một ảnh/frame**, không phải sự hiện diện của xe. Nhãn của cả clip, của một frame và của một bbox không được dùng thay thế nhau.

| Loại mẫu trong B0 | Nghĩa dễ hiểu | Ví dụ và cách xử lý |
| --- | --- | --- |
| **Mẫu dương — positive** | Frame có vùng tai nạn thuộc phạm vi project và có bbox hợp lệ cho vùng đó | Bốn ảnh impact ACCIDENT được giữ có bbox tác giả và mapping đã kiểm. Giữ nhãn ở đúng frame, không gán mọi frame trong clip là dương |
| **Mẫu âm — negative** | Frame đã có căn cứ không có tai nạn trong phạm vi ảnh được xét; ảnh vẫn có thể có rất nhiều xe | Ảnh từ ba DETRAC đã xác nhận toàn chuỗi không va chạm; hoặc frame từ clip normal TAD có nhãn nguồn. Phân biệt nguồn nhãn này với người dùng đã rà |
| **Chưa biết/chưa chắc — unknown/uncertain** | Thiếu nhãn, chưa rõ nội dung hoặc chưa đủ bằng chứng khớp ảnh/nhãn | STTAD thiếu TXT, frame CADP ngoài khoảng đã xác nhận hoặc frame ACCIDENT ngoài impact không tự được gán âm. Giữ ngoài supervision chưa đủ căn cứ |

**Mẫu âm khó — hard negative** là cảnh không có tai nạn nhưng dễ bị nhầm: hai xe đỗ sát nhau, kẹt xe, giao quỹ đạo do phối cảnh, phanh gấp hoặc near miss đã xác minh không tiếp xúc. Cần kiểm nội dung thật; tên nhóm hoặc bbox chồng nhau không đủ làm nhãn. Với đánh giá sự kiện, có thể cần cả diễn biến video, không chỉ một ảnh.

### Mẫu như thế nào mới hợp lý?

1. **Đúng nội dung và phạm vi:** dương có vùng accident theo policy; âm có căn cứ không có sự kiện trong toàn phạm vi gán nhãn. Bbox xe không tự thành bbox tai nạn. Nhãn positive mức clip không cấp bbox cho mọi ảnh trong clip.
2. **Ảnh sạch và khớp nhãn:** đọc được, đúng chuỗi/frame/kích thước, tọa độ hợp biên; không dùng GT preview đã vẽ đáp án làm đầu vào. Bbox thiếu/chưa rõ phạm vi thì loại/giữ chưa chắc chắn, không vẽ bù để tăng số mẫu.
3. **Biết độ phủ nhãn:** có một bbox không chứng minh những vùng khác hoặc frame khác đã được rà đầy đủ. Không coi phần chưa gán nhãn là negative; điều kiện supervision phải được kiểm trước khi export/train.
4. **Gần bối cảnh triển khai:** cần cả tai nạn và giao thông bình thường/khó trong bối cảnh CCTV tương đồng. Nếu dương luôn có watermark của một nguồn còn âm luôn từ nguồn khác, model có thể học dấu hiệu nguồn thay vì va chạm.
5. **Đa dạng và độc lập khi đánh giá:** hàng trăm frame gần nhau của cùng sự kiện không tương đương hàng trăm tai nạn. Giữ bản cắt/frame cùng nguồn trong một split; kiểm nhóm camera/sự kiện trước khi chia tập. Không đạt cân bằng bằng cách copy ảnh hoặc chia ngẫu nhiên frame gần nhau.

Không có yêu cầu mặc định rằng cứ **1 dương phải có đúng 1 âm** hoặc đạt một số frame cố định mới được train. Pool v3 có 48 dương/2.375 âm nhưng lệch nguồn mạnh; pilot đầu chọn 17 impact và 30 âm cùng cảnh, không dùng mọi ảnh âm DETRAC để lấn át số dương. Đây là thiết kế thăm dò với giới hạn rõ, không chứng minh 17 dương là đủ học tốt. Thực tế pilot đang thất bại trên test; vòng sau cần thêm ví dụ vùng/nguồn và kiểm tối ưu hóa, không chỉ tăng âm. Không đổi phân bố test để làm kết quả đẹp hơn.

**Định dạng đã xuất:** ảnh dương có dòng YOLO `0 cx cy w h`; số `0` là **class ID của accident**, không có nghĩa “âm tính”. 30 ảnh âm đã có căn cứ nhận TXT rỗng trong dataset pilot. Frame thiếu TXT nguồn vẫn unknown, không tự tạo empty label cho chúng.

Tiến độ thực hiện các điều kiện này xem [B0 trong bảng baseline chung](../progress/README.md#b0--detector-ảnh-vùng-tai-nạn). Phần CADP dưới đây là hồ sơ nhãn/đề xuất lịch sử, không thay định nghĩa mẫu hiện hành ở trên.

Người dùng đã xác nhận **001407 đúng đối tượng, Colliding 96–130 rõ ràng/phù hợp**. [Phiếu rà mới](../data/reviews/2026-10-19-cadp-001407-frame-confirmation.json) gắn hash TXT và GT ID0 Bus, ID2 Car, chỉ số nguồn bắt đầu 0, hai đầu interval đều tính. Không cần xác nhận lại mẫu này. Manifest ghi positive mức chuỗi/sự kiện, còn `onset_s/end_s` trống vì FPS nguồn chưa xác minh. Xác nhận frame không tự duyệt quy tắc hình học vùng accident bên dưới.

## Đề xuất cụ thể: vùng bao các phương tiện tham gia cùng sự kiện

**Trạng thái: đề xuất dẫn xuất, chưa phải annotation tác giả hoặc GT B0 đã duyệt.** Config: [b0_region_proposal.json](../configs/b0_region_proposal.json).

Một bbox đại diện **phạm vi ảnh đang chứa các phương tiện của cùng sự kiện va chạm đã xác nhận**, không đại diện điểm tiếp xúc vật lý, vùng hư hỏng, làn đường hay toàn bộ hiện trường. Đề xuất ban đầu nhằm xác định vùng ngữ cảnh tương tác cho detector ảnh; đây là lựa chọn nhãn của project cần chốt, không phải định nghĩa CADP có sẵn.

1. Lấy **danh sách GT ID của từng event đã rà**, không gộp mọi đối tượng có Colliding trong ảnh. Nếu có hai sự kiện riêng, tạo hai vùng riêng.
2. Trong khoảng frame đã xác nhận của event, chỉ tạo ứng viên khi có bbox tác giả cho **tất cả** phương tiện tham gia và không có cờ `outside`.
3. Vùng ứng viên là hộp chữ nhật trục song song nhỏ nhất bao các bbox participant trong **frame hiện tại**: `xmin=min(xmin_i)`, `ymin=min(ymin_i)`, `xmax=max(xmax_i)`, `ymax=max(ymax_i)`. Chưa thêm padding tùy ý. Bbox có thể chứa một phần nền hoặc đối tượng đi ngang nằm giữa các xe; không hiểu mọi pixel trong hộp là tai nạn.
4. Giữ nguyên cờ `occluded/generated` của nguồn, gắn cờ cần rà vùng. Không tự suy ra hình dạng phần bị che. Nếu thiếu participant/ngoài ảnh, **bỏ ứng viên và ghi lý do**, không xuất empty label hay nội suy mới.
5. Giữ `FarRegion`/`CrowdRegion` trong bảng vùng bỏ qua. `Separator` chỉ đánh dấu cắt cảnh, không phải class accident. Ghi overlap của ứng viên với vùng bỏ qua; chưa quyết định cách mask/ignore khi train. Mã tác giả cũng [giữ/xử lý vùng chưa gán nhãn](https://github.com/ankitshah009/CarCrash_forecasting_and_detection#data-preparation), nên không coi toàn ảnh đã gán nhãn đầy đủ chỉ từ số track.
6. Chỉ interval **96–130** của 001407 được dùng cho minh họa đề xuất. Frame khác không tự trở thành ảnh âm toàn cảnh. Nhãn B0 vùng còn pending dù event/participant/interval của mẫu này đã được người dùng xác nhận.

**Cách sử dụng hiện tại:** giữ 35 envelope CADP ở auxiliary derived; không đưa thành GT vùng tác giả. Chính sách B0 public ở đầu tài liệu đã được AI chọn có căn cứ paper, không cần người dùng quyết định lại mẫu này. Với nguồn khác, kiểm nghĩa nhãn trước khi gộp; annotation clip không tự thành bbox.

## Công cụ và kết quả đã tạo

`scripts/prepare_b0_candidates.py` nhận chuỗi ảnh, VATIC, báo cáo mapping đã xác minh, phiếu xác nhận theo frame và config đề xuất. Công cụ đối chiếu hash từng ảnh/TXT, kiểm tọa độ với kích thước native, giữ source sequence/frame/GT ID/visibility. Chạy không có phiếu rà vẫn chuẩn hóa bảng đối tượng, không tạo ứng viên từ giả định.

Kết quả tại [data/processed/b0_proposals/001407/](../data/processed/b0_proposals/001407/):

| File | Nội dung thực tế |
| --- | --- |
| [objects_normalized.csv](../data/processed/b0_proposals/001407/objects_normalized.csv) | 4.641 dòng nguồn; role object/ignore/separator, xyxy và tọa độ chuẩn hóa; outside/occluded/generated/Colliding giữ nguyên |
| [frames.csv](../data/processed/b0_proposals/001407/frames.csv) | 221 frame; số dòng/đối tượng/vùng ignore, missing track rows, lý do bỏ và trạng thái nhãn |
| [ignore_and_separator_regions.csv](../data/processed/b0_proposals/001407/ignore_and_separator_regions.csv) | 221 dòng FarRegion, không biến thành xe hoặc accident |
| [region_proposals.csv](../data/processed/b0_proposals/001407/region_proposals.csv) | 35 bbox ứng viên, 96–130; liên kết event, participant, ảnh và `training_eligible=False` |
| `labels_proposed/001407_000096.txt … 001407_000130.txt` | 35 TXT **đề xuất** theo cú pháp YOLO, không đặt trong tập train, không có `dataset.yaml` |
| [proposal_examples.jpg](../data/processed/b0_proposals/001407/proposal_examples.jpg) | Minh họa vùng màu cam ở frame 96/113/130; chữ “PROPOSAL ONLY”, không phải preview/dự đoán mới của model |
| [report.json](../data/processed/b0_proposals/001407/report.json) | Hash/quy tắc/phiếu rà, thống kê và gate chưa đủ điều kiện train |

Toàn nguồn có 3.770 dòng visible, 621 occluded, 4.500 generated, 70 dòng Colliding. `visible=1-outside` nghĩa còn trong ảnh, không có nghĩa không bị che. Generated là cờ nguồn, không phải nhãn do project mới tạo. Không loại cờ hoặc làm tròn bbox gốc để che sai lệch. **186 frame ngoài phần ứng viên vẫn unknown về nhãn âm toàn cảnh; không tạo nhãn rỗng.**

Ba DETRAC đầy đủ có xác nhận âm **toàn cảnh/toàn chuỗi** riêng, nên có căn cứ khác với “không thấy bbox Colliding”. `scripts/prepare_b0_negative_index.py` đã kiểm lại hash MP4 đã rà, quan hệ MP4↔ảnh, CRC/kích thước/giải mã đủ 2.037 JPG, xuất [chỉ mục frame âm](../data/processed/b0_reviewed_negatives/frames.csv) và [report](../data/processed/b0_reviewed_negatives/report.json). Đây là tham chiếu 664/936/437 ảnh nguồn, không copy ảnh, không tạo 2.037 mẫu độc lập, chưa tạo empty TXT để train và không coi chúng là ảnh “không có xe”.

```powershell
.\.venv\Scripts\python.exe -B scripts/maintenance/apply_cadp_frame_review.py --review data/reviews/2026-10-19-cadp-001407-frame-confirmation.json
.\.venv\Scripts\python.exe -B scripts/prepare_b0_candidates.py --sequence 001407 --frames-dir data_raw/cadp/frames/001407 --annotations data_raw/cadp/pilot_1407/1407.txt --mapping-report outputs/audits/cadp_001407_clean_2/report.json --review data/reviews/2026-10-19-cadp-001407-frame-confirmation.json --output data/processed/b0_proposals/001407
.\.venv\Scripts\python.exe -B scripts/prepare_b0_negative_index.py
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

Đầu ra đã có, **không cần chạy lại để xem**. Công cụ xuất nhãn từ chối ghi đè; khi chủ động chuẩn bị phiên bản mới phải dùng `--output` mới và cập nhật liên kết. Chưa có chức năng phê duyệt GT hoặc chạy train tự động.

## Sẵn sàng đến đâu?

| Phần | Tình trạng |
| --- | --- |
| Đọc VATIC, kiểm ảnh/bbox/flags, giữ provenance | Đã có và chạy thật trên 001407 |
| Xác nhận người dùng về xe/96–130 | Đã có; không còn yêu cầu rà lại mẫu này |
| Công cụ vùng ứng viên, bảng ignore/unknown và minh họa | Đã có, 35 đề xuất chưa được duyệt |
| Dữ liệu âm đã rà | 3 chuỗi DETRAC, 2.037 frame được lập chỉ mục |
| Dữ liệu pilot theo nguồn độc lập | 1 sự kiện CADP + 3 chuỗi DETRAC; [inventory](../data/pilot_inventory.csv), không đếm output thành sự kiện mới; độc lập giữa camera/near-duplicate chưa xác minh |
| Nhãn GT vùng accident nhất quán và pilot đủ nhiều nguồn/sự kiện | **Còn thiếu** |
| FPS nguồn/timestamp CADP | **Còn thiếu cho đánh giá theo giây/đặc trưng chuyển động**; không phải điều kiện bắt buộc để chuẩn hóa nhãn ảnh B0 theo frame |
| Split / huấn luyện / đánh giá accuracy | Chưa thực hiện |

[B0 readiness](../data/b0_readiness.json) giữ `can_train=false` vì độ phủ/nhóm dữ liệu chưa đủ, không vì chờ xin nhãn/duyệt. Bước tiếp theo: mở rộng cặp public STTAD hợp phạm vi, kiểm trùng/nguồn và tìm nguồn âm cùng miền; thiếu nhãn vùng thì loại khỏi B0 hoặc ghi quyết định baseline khác theo dữ liệu, không tạo GT giả. [Kết quả đối chiếu mới](../reference/2026-10-24-public-data-review.md).
