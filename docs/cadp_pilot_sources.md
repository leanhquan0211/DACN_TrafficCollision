# Kiểm tra nguồn CADP — lịch sử và quyết định hiện tại

> **Tài liệu chi tiết/lịch sử:** ưu tiên [mục lục hiện hành](README.md), [policy nhãn B0](b0_label_protocol.md) và [trạng thái dữ liệu mới nhất](b0_pilot_audit.md). Các số liệu/chỉ dẫn cũ bên dưới giữ bối cảnh lúc tạo, không thay hướng public đã chọn.

> **Cập nhật 24/10:** giữ CADP 001407; phần export chưa public bị bỏ khỏi đường mở rộng hiện tại. Không xin tác giả hoặc chờ giảng viên duyệt. Đã có nhãn vùng STTAD công khai và công cụ kiểm thật: [reference](../reference/2026-10-24-public-data-review.md). Các số liệu/tìm nguồn dưới đây là lịch sử 19/10, trước khi thêm STTAD.

## Đếm dữ liệu theo chuỗi/sự kiện — lịch sử 19/10

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

## Quyết định 24/10 và cách tiếp tục

- Cặp CADP đã kiểm vẫn là `data_raw/cadp/frames/001407/` + `data_raw/cadp/pilot_1407/1407.txt`, review xe/96–130 giữ nguyên. Không cần tải lại hoặc xác nhận lại.
- Chưa tìm được export VATIC bổ sung public trong phạm vi kiểm: bỏ dependency này, không giao người dùng gửi thư hoặc xin nhãn riêng. Mẫu thư/hướng dẫn xin trước đó đã được rút khỏi hướng dẫn hiện hành; nhật ký giữ lịch sử quyết định.
- AI chọn nhãn vùng tác giả **STTAD public** cho B0, giữ CADP envelope riêng là auxiliary derived. [Policy](../configs/b0_public_label_policy.json), [paper/kiểm nguồn](../reference/2026-10-24-public-data-review.md), [hướng dẫn tải chọn lọc](GETTING_STARTED.md).
- Đã có 4 chuỗi STTAD ở `data_raw/sttad/public_examples/`, 176 ảnh đọc được và 31 bbox/frame nguồn; xem `outputs/audits/sttad_public_6/`. Thiếu TXT → unknown, không negative; 2 file ảnh lỗi bị loại, raw giữ nguyên. [Mở rộng/pool/nhóm cảnh](b0_pilot_audit.md).
- Nguồn TAD có ZIP public, danh mục đã kiểm chỉ 404 MP4, không có bbox export; dùng tham khảo/ứng viên clip-level, không đổi thành GT vùng B0. Không tải cả ZIP 4,54 GB.
