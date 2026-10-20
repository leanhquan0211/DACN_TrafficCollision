# Nhãn B0: phần đã chuẩn hóa và quy tắc vùng tai nạn đề xuất

## B0 trong kế hoạch thật

Theo README và sheet `05_Cac_buoc` bước 05, `08_Du_lieu` mục D3, `09_Danh_gia` mục B0:

- **Đầu vào:** ảnh/frame sạch, truy được video/chuỗi/sự kiện gốc; train về sau cần cả ảnh dương có bbox và ảnh âm được rà đủ.
- **Đầu ra model:** bbox vùng `accident`, class và confidence trên từng frame; không phải bbox xe pretrained hoặc ID tracker. Quyết định/cảnh báo theo thời gian là các bước B1/B2 về sau.
- **Nhãn cần:** quy tắc nhất quán xác định một vùng accident là gì, khoảng frame hợp lệ và các vùng/frame chưa đủ căn cứ. Định dạng YOLO dự kiến `0 cx cy w h`, chuẩn hóa theo kích thước ảnh; chưa tạo bộ train/val/test trong lượt này.

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

**Các điểm cần chốt trước khi dùng làm GT:** có chọn vùng bao participant như trên không; với nhiều xe/che khuất/ảnh bị cắt có giữ/bỏ/mask thế nào; quy tắc hình học và xử lý vùng ignore có nhất quán cho các nguồn khác không. Không cần gán lại bbox xe đã có để trả lời câu hỏi này. Nếu chọn một định nghĩa khác, giữ đề xuất này làm lịch sử và đổi config/công cụ có phiên bản sau khi quyết định.

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
.\.venv\Scripts\python.exe -B scripts/apply_cadp_frame_review.py --review data/reviews/2026-10-19-cadp-001407-frame-confirmation.json
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

[B0 readiness](../data/b0_readiness.json) giữ `can_train=false`. Bước tiếp theo là quyết định quy tắc vùng accident dựa trên đề xuất cụ thể và lấy thêm **VATIC sẵn có của tác giả**, rồi mới chọn ảnh sạch cùng ID; [kết quả tìm nguồn và thao tác lấy dữ liệu](cadp_pilot_sources.md). Không yêu cầu gán lại bbox bằng tay khi chưa giải quyết nguồn export.
