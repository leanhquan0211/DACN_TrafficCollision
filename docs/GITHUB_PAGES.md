# Web demo GitHub Pages

URL được GitHub trả về: <https://minhquan0500.github.io/DACN_TrafficCollision/>.

**Đã triển khai và kiểm live16/11:** build `built`, commit `87e8e18afa6b7743afa5affeac3cc2468565501c`, HTTPS trả200. Đã tải đối chiếu36payload +manifest, tất cảsize/SHA-256 đúng; Firefox7nhóm thao tác đạt trên chính URL công khai. Đây là bản xem kết quả đã lưu, không có backend suy luận trên Pages.

## Phạm vi

Theo yêu cầu mới16/11, xuất bản một trang tĩnh để xem demo kể cả khi máy phát triển tắt. GitHub Pages phục vụ HTML/JavaScript/MP4/JSON; không chạy Python/PyTorch. Trang ghi rõ kết quả đã xử lý, không có nút giả chạy mô hình hay upload video để phân tích. Bản Python cục bộ vẫn hỗ trợ các chức năng đó theo [DEMO_GUIDE.md](DEMO_GUIDE.md).

Có hai clip mẫu được chọn trong `configs/demo_catalog.json`, mỗi clip đủ detection/tracking/collision. Người xem phát đồng bộ video gốc và kết quả, tua từng frame, xem bbox/ID, chuyển chế độ, mở ảnh/clip cảnh báo và tải MP4/cache/tóm tắt JSON/Events JSON/báo cáo PDF. CADP có một cảnh báo ở frame109; DETRAC10giây không cảnh báo. Đây là cảnh phát triển, chưa test độc lập. Giây video/FPS offline và giới hạn chất lượng được ghi rõ.

## Mã nguồn và tái tạo

- `demo/pages/index.html`, `demo/pages/app.js`: giao diện tĩnh, mọi đường dẫn tài nguyên tương đối để chạy dưới tên repo GitHub Pages.
- `demo/style.css`: dùng lại giao diện Traffic Lab của bản cục bộ.
- `scripts/build_pages_demo.py`: chỉ đọc hai mẫu trong catalog, kiểm report/hash/giải mã bằng checker hiện có trước khi xuất. Không đọc thư mục upload/job/review cá nhân. Chỉ ghi vào thư mục mới dưới `outputs/`; từ chối ghi đè.
- Nhánh `gh-pages` trên fork `minhquan0500/DACN_TrafficCollision` chỉ chứa37tệp web/media đã chọn, khoảng30MB. Các clip mẫu minh họa được công khai theo yêu cầu; không gồm toàn dataset, trọng số, mã Python, môi trường hay credential. Không thay `main`.

Cần phục hồi đúng video/kết quả/checkpoint theo hướng dẫn project hoặc dùng máy phát triển có các file thực tế. Không coi metadata trên Git là đã có media trên máy mới.

```bash
.venv/bin/python -B scripts/build_pages_demo.py --output outputs/pages_demo_NEW
```

Gói có `PUBLIC_MANIFEST.json` với size/SHA-256 từng tệp và hash các report gốc. JSON public là bản tóm tắt có `artifact_type=public_demo_summary`, không phải report gốc bị sửa hash. Không đưa đường dẫn riêng của máy vào trang; giữ hash gốc để đối chiếu. Nhãn/model/config nghiên cứu không thay đổi.

## Cấu hình hosting

GitHub trả về source `gh-pages`, path `/`, `build_type=legacy`, HTTPS bật. Push nhánh kích hoạt build. Sau push đầu GitHub đã tự bật Pages; yêu cầu tạo site trả409 (đã có), sau đó GET xác nhận đúng cấu hình và build đang chạy. Tiếp tục lần build hiện có thay vì tạo site khác.

Khi cập nhật: tạo export mới → kiểm file/hash và trình duyệt → cập nhật đúng nhánh `gh-pages` → xác minh build + URL. Không đăng `.cache/github-auth`, file máy cá nhân hoặc output chưa được chọn. Không yêu cầu GitHub Actions tùy chỉnh hoặc máy chủ tính phí.

## Kiểm chứng trước xuất bản

- `outputs/audits/pages_2026-11-16/static_check.json`:37tệp,2mẫu/6run, frame/observation/event nhất quán, hash media/bằng chứng đúng, không có upload/path riêng/model/credential.
- `local_browser/browser_check.json`:7nhóm kiểm Firefox dưới project subpath, giải mã đủ6video kết quả, play/pause/step/seek/sync, alert109 và DETRAC không alert cũ, không gọi backend/API/upload, điều hướng,390px không tràn ngang, refresh.
- Ảnh desktop/mobile đã được xem. Có cảnh báo quyền dọn Selenium/Snap sau khi lưu bằng chứng; không thay kết quả kiểm.
- Trạng thái build/ref/cấu hình được lưu tại `outputs/audits/pages_2026-11-16/deployment.json`; `live_artifacts.json` kiểm hash toàn bộ payload trên web; `live_browser/browser_check.json` kiểm7nhóm Firefox trực tiếp HTTPS đạt. Không suy kiểm live từ kết quả localhost.

Nguồn giới hạn hosting: [GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages); [Pages REST API](https://docs.github.com/en/rest/pages/pages).
