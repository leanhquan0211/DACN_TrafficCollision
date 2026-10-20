# Kiểm tra nguồn để mở rộng pilot CADP — 19/10/2026

## Đếm dữ liệu theo chuỗi/sự kiện

[Manifest](../data/manifest.csv) có 12 asset, nhưng chỉ có **4 nhóm chuỗi đã biết nhãn**: CADP 001407 (1 sự kiện va chạm, 5 asset ảnh/video) và 3 DETRAC âm đầy đủ. Clip con MVI_20011, preview, detection và tracking không phải sự kiện hoặc chuỗi độc lập mới. Ba MP4 cũ chưa biết nguồn/nhãn vẫn để riêng, không thêm vào số mẫu đã duyệt.

[pilot_inventory.csv](../data/pilot_inventory.csv) và [summary](../data/pilot_inventory_summary.json) ghi nhóm asset/provenance. Bốn tên chuỗi khác nhau chưa chứng minh độc lập camera hoặc không gần trùng; chưa có group split. Một sự kiện + ba chuỗi âm chưa đủ pilot đa sự kiện như kế hoạch.

## Nguồn thực sự đã kiểm tra trực tuyến

Đã GET metadata/tài liệu công khai, không tải ảnh/video hoặc cả dataset. Trình duyệt công cụ không đọc được một số Drive/Docs; đã kiểm tra lại bằng HTTPS trực tiếp và lưu [report nguồn](../outputs/audits/cadp_source_discovery/report.json). Kết quả này áp dụng tại thời điểm kiểm, không bảo đảm link còn sống về sau.

| Nguồn | Kết quả kiểm thực tế | Có thêm cặp sạch + VATIC đã xác minh? |
| --- | --- | --- |
| [Trang CADP tác giả](https://ankitshah009.github.io/accident_forecasting_traffic_camera.html) | Đọc được trang và các liên kết phát hành | Chưa có cặp bổ sung từ trang |
| [Dataset Release README](https://docs.google.com/document/d/12F7l4yxNzzUAISZufEd9WFhQKSefVVo_QsPdTsWxZh8/edit) | Export TXT HTTP 200; có đường dẫn kho Drive, mô tả object/temporal annotation; phần spatio-temporal chưa đưa tệp export cụ thể | Không |
| [Kho Drive trong README](https://drive.google.com/drive/folders/1ikepACwlFsVeaYSRWOQGDQXh1Hy5gWS6) → [Dataset](https://drive.google.com/drive/folders/1ozfZbz8wRoNqKknC59IPXP_twKgmCOaA) → [manual](https://drive.google.com/drive/folders/1296u7MPa1Fs2OtVXmprOmbgXJ9VNJ_AL) | Đọc được danh mục, HTTP 200 | Không tìm thấy gói VATIC trong các danh mục đã kiểm |
| [manual/extracted_frames](https://drive.google.com/drive/folders/1BRIv9h4c_zbqJ6Ye4rVyFSo3K20BQt_v) | HTTP 200, danh mục đầu có 50 thư mục từ 000000…; đúng folder ID trong `analysis/pydrive.py` tác giả. **Chỉ trang danh mục đầu, không phải tổng số chuỗi.** | Có ảnh được phát hành, chưa có VATIC thêm để ghép |
| [Chuỗi ảnh 000000](https://drive.google.com/drive/folders/1YAfAvFlWOL3VB9Nx-Hete9OHSMFPMG9D) | Danh mục JPG `0.jpg`, `1.jpg`… truy cập được; chưa tải pixel/kiểm sạch hay mapping | Không có TXT tương ứng đã tìm thấy |
| [manual/Lijun](https://drive.google.com/drive/folders/1baWPwG9tsbq6bBPLbDgyfmLyHgo41_LA) | Có thư mục ảnh; đã đọc danh mục 000000, không thấy export VATIC trong khu vực này | Không |
| [manual/outsource](https://drive.google.com/drive/folders/1GVORbpaQYNFfUefFE44SiNThRH1-Vfjv) | Guideline/Guide và bảng Stage 2 | Tài liệu, chưa phải dữ liệu annotation |
| [Stage 2 spreadsheet](https://docs.google.com/spreadsheets/d/1dH1iYC8CtAAXiU4pPAznN-u-iHLfe36BenxxU7IP84c/edit) | Export CSV HTTP 200; bảng công việc/URL VATIC UI, không phải bbox export. Một URL mẫu `http://35.237.143.103:8080/?id=299&hitId=offline` timeout 8 giây | Không thu được annotation; không ánh xạ job ID 299 thành sequence 000299 chỉ vì trùng số |
| [GitHub data của tác giả](https://github.com/ankitshah009/CarCrash_forecasting_and_detection/tree/master/data) | Đọc tree hiện tại qua API và ZIP địa phương; chỉ có annotation mẫu **`data/1407.txt`**, không có `data/annotations/` đầy đủ | Chỉ mẫu 001407 đang có, không phải sự kiện mới |
| [Link extracted frames cũ trên trang tác giả](https://drive.google.com/file/d/1PDsYAsOEwZTcFVVt444wvhOTfjqwqTaY/view) | HTTPS trực tiếp trả **404** | Không |
| [Annotations JSON trên trang tác giả](https://filedn.com/lQfYylUHSWEYAyORS7PdIKH/annotations_CADP.json) | Truy cập được; không xác minh đây là VATIC đầy đủ; README mô tả Stage 1 là biên clip với bbox dummy | Không dùng thay bbox xe/accident |

Đã kiểm thêm danh mục automatic/json/Web/forth_investigation/temp/References/Reports, các hướng dẫn tạo CSV/mask và phản hồi ở issue 3/4/12/18/19/41 trong repository tác giả. Không tìm được URL export VATIC bổ sung có thể xác minh. Issue 41 đóng nhưng API trả không có bình luận, nên trạng thái đóng **không chứng minh đã phát hành nhãn**. Không dùng bình luận của người ngoài nhóm tác giả như xác nhận nhãn chính thức.

Giới hạn: các thư mục ảnh lớn chỉ kiểm danh mục HTML đầu, không crawl toàn dataset hoặc từng ảnh. Kết luận là **chưa tìm thấy bộ export trong phạm vi đã kiểm**, không khẳng định toàn bộ annotation không tồn tại ở nơi khác hoặc trong tài khoản riêng.

## Hiện có cặp nào? Cần lấy chính xác gì?

**Cặp duy nhất đã kiểm chứng đầy đủ tại project:** `data_raw/cadp/frames/001407/0.jpg … 220.jpg` + `data_raw/cadp/pilot_1407/1407.txt`. Đây là một chuỗi, không tăng số mẫu độc lập khi tải lại cùng `1407.txt`.

**Chưa có tên/URL tệp VATIC bổ sung đã xác minh để bảo bạn tải ngay.** Không chỉ định tải ngẫu nhiên 000000/000001 rồi tự cho rằng có nhãn tương ứng; chưa yêu cầu tự gán lại bbox bằng tay.

Bước cụ thể để mở rộng:

1. Dùng thông tin liên hệ trong [README phát hành của tác giả](https://docs.google.com/document/d/12F7l4yxNzzUAISZufEd9WFhQKSefVVo_QsPdTsWxZh8/edit), xin **export VATIC TXT cho subset có nhãn spatio-temporal**, gồm ID/class/xyxy/frame/outside/occluded/generated/Colliding, FarRegion/CrowdRegion/Separator nếu có; kèm bảng nối **tên TXT ↔ mã thư mục ảnh 6 chữ số**, nguồn video/sự kiện và FPS/timestamp riêng chuỗi nếu có. Chưa gửi email/tin nhắn thay người dùng.
2. Khi được cung cấp, lưu ZIP export nguyên bản trong `data_raw/cadp/annotations/`; TXT đã lấy chọn lọc đặt tại **`data_raw/cadp/annotations/vatic/<tên-tác-giả>.txt`**. Thư mục đích đã được tạo; hiện còn trống. Không tự đặt tên file đang chưa biết hoặc đổi tên gần giống để ép ghép.
3. Đọc danh mục TXT trước, chọn 2–3 **chuỗi có nhãn thực sự**, rồi mới tải đúng các thư mục tương ứng từ extracted_frames về **`data_raw/cadp/frames/<sequence-6-chữ-số>/`**. Nếu Drive tạo ZIP khi tải thư mục, giữ nguyên ZIP trong `data_raw/cadp/frames/`, không cần tải toàn extracted_frames. Kiểm dung lượng trước; ổ còn khoảng 1,09 GB ở đầu lượt này.
4. Chạy lại kiểm ảnh/mapping với từng cặp mới, kiểm sự kiện/camera/clip trùng và nguồn timing. Công cụ chuẩn hóa/ứng viên đã có, nhưng xác nhận 001407 không lan sang các chuỗi mới.

Nếu tác giả chỉ cung cấp nhãn object/Colliding, có thể tận dụng cho đề xuất vùng B0 sau khi chốt quy tắc; chúng vẫn không tự là GT vùng accident. [Quy tắc đề xuất và trạng thái train](b0_label_protocol.md). Thiếu FPS nguồn không cản việc chuẩn hóa bbox ảnh, nhưng cản kết luận theo giây/vận tốc và đánh giá temporal.
