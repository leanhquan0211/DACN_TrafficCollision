# Kiểm kê ban đầu ba video mẫu — 19/10/2026

Đây là mốc kiểm kê **trước khi thêm CADP 1407 và DETRAC**. Kết quả và giới hạn của dữ liệu mới ở [hướng dẫn chuẩn bị CADP/DETRAC](dataset_preparation.md); manifest hiện tại đã bổ sung các asset mới.

**Lượt mới nhất cùng ngày:** đã có riêng 221 ảnh sạch CADP 001407, mapping TXT/demo được kiểm ở nhiều mốc, và ba DETRAC đầy đủ được người dùng xác nhận âm. [Bằng chứng, video và giới hạn timing/B0](cadp_001407_clean.md). Xác nhận mới không thay nhãn hoặc nguồn của ba video cũ trong bảng dưới.

## Phương pháp và kết quả đo được

Chỉ đọc file trong `data_samples/`; không tải thêm dữ liệu. Dùng OpenCV đọc toàn bộ từng MP4 và lấy metadata, dùng SHA-256 trên byte của file để kiểm tra trùng chính xác. Xem frame ở khoảng 0%, 25%, 50%, 75%, 98% mỗi clip để nhận diện sơ bộ góc quay; việc này **không thay thế xem toàn clip để gán nhãn**.

| Video | Kích thước | FPS OpenCV | Frame metadata/đọc được | Thời lượng xấp xỉ | Nhãn, nguồn, split |
| --- | --- | ---: | ---: | ---: | --- |
| `YSGhwU9XxuY.mp4` | 450×360 | 25 | 279/279 | 11,160 s | Chưa xác minh |
| `ZCQcKnFSJvg.mp4` | 480×270 | 29,97003 | 717/717 | 23,924 s | Chưa xác minh |
| `zVzXEht1aME.mp4` | 480×360 | 20 | 794/794 | 39,700 s | Chưa xác minh |

Ba SHA-256 trong [manifest](../data/manifest.csv) khác nhau, nên **không trùng chính xác ở mức file**. Điều đó chưa loại trừ hai bản cắt/chuyển mã của cùng camera hoặc sự kiện. Các frame lấy mẫu cho thấy mỗi clip có góc nhìn có vẻ cố định; chưa xác nhận nguồn CADP, camera ID hay loại sự kiện. Tại thời điểm kiểm kê ban đầu, `data_raw/` chỉ có `.gitkeep`; các gói CADP/DETRAC được kiểm kê trong buổi sau, không thay đổi kết luận nhãn của ba video này.

Trang [CADP của nhóm tác giả](https://ankitshah009.github.io/accident_forecasting_traffic_camera.html) mô tả 1.416 đoạn video, 205 đoạn có nhãn không gian–thời gian đầy đủ và dẫn tới README, annotation và guideline. Trang nêu điều kiện sử dụng phi thương mại cho nghiên cứu, cần xin phép tác giả cho mục đích khác. **Chưa đối chiếu ba MP4 địa phương với danh mục/annotation chính thức**, nên không ghi `source_dataset=CADP` chỉ dựa vào tên file hay bối cảnh hình ảnh. Chưa có bản README phát hành tại project để kiểm tra thêm điều kiện chi tiết.

## Điều kiện còn thiếu để hoàn thành giai đoạn 1

1. Nguồn và annotation gốc của video, quyền sử dụng/trích dẫn; xác định clip có đủ thời gian trước/sau va chạm và nhãn pair/onset thực tế hay không.
2. Video **không tai nạn** được xem toàn đoạn, gồm hard negatives và đoạn âm dài để đánh giá false alarms/hour.
3. Rà ít nhất 10 trường hợp pilot theo [quy tắc nhãn bản nháp](annotation_protocol.md), chốt phạm vi/ranh giới `end_s` và trường hợp không chắc chắn.
4. Xác định camera/source event, loại trùng/gần trùng, sau đó mới tạo split manifest cố định. Với ba clip chưa biết nhóm và nhãn, một split ngẫu nhiên sẽ không có ý nghĩa đánh giá.

**Kết luận tại mốc ban đầu:** kiểm kê kỹ thuật video hoàn tất cho ba file mẫu; giai đoạn định nghĩa và dữ liệu **chưa đạt điều kiện chuyển sang B0**. Xem bản chuẩn bị mới để biết tài liệu/nhãn tác giả hiện đã tìm thấy.
