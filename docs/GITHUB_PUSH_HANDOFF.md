# Trạng thái xuất bản nhánh demo

## Cập nhật25/11 — Pages phân tích video mới

Nhánh `gh-pages` của repo gốc và fork đã cập nhật tới `cff376d6c8149a5d7ff005051c95d278a3a432b6`; bản fork build và kiểm trực tiếp HTTPS đạt54tệp. [Chọn video để chạy YOLO ngay trên thiết bị](https://minhquan0500.github.io/DACN_TrafficCollision/upload.html), có JSON/PNG và cảnh báo thử nghiệm. [Cách triển khai/giới hạn](BROWSER_VIDEO_UPLOAD.md), [snapshot](evidence/2026-11-25-browser-upload.json). Source browser/export/check/documentation được đồng bộ vào nhánh mã nguồn hiện có; không đổi main hoặc merge PR. Model chỉ phân phối trên `gh-pages`, source giữ script dựng và fingerprint; video người dùng không được gửi hoặc công khai.

## Cập nhật 19–21/11/2026

Đã upload trực tiếp vào **repo người dùng yêu cầu**:

- [Nhánh mã nguồn `feat/collision-demo-2026-11-16`](https://github.com/leanhquan0211/DACN_TrafficCollision/tree/feat/collision-demo-2026-11-16), gồm các sửa demo và kết quả đánh giá có nhãn. Lần tạo nhánh dùng commit `e7b2c991364a5b759f31300bfd40415ed06555eb`; các cập nhật Pages tiếp tục trên cùng nhánh.
- [Nhánh web `gh-pages`](https://github.com/leanhquan0211/DACN_TrafficCollision/tree/gh-pages) ở commit `985e1fc3c055f3d86207a5d61622f21ca4f4e975`: 40 tệp, khoảng 30 MB; hai clip/ba chế độ và bảng train/validation/P/R/mAP.
- Quyền tài khoản hiện tại: `push=true`, `admin=false`, `maintain=false`. GitHub connector chặn tạo nhánh bằng lỗi `Resource not accessible by integration`; dùng GitHub CLI đã đăng nhập để push thành công. Đây không còn là trạng thái thiếu quyền ghi mã ngày 16/11.
- Repo gốc chưa bật Pages (`has_pages=false`). GET/POST Pages trả HTTP 404 với tài khoản này. Chủ repo cần vào **Settings → Pages → Deploy from a branch → gh-pages → /(root) → Save**. Quyền ghi mã chưa đủ để quản lý cấu hình Pages. [Hướng dẫn hosting](GITHUB_PAGES.md).
- Giữ `main` và PR cũ; không tự merge các dòng phát triển có xung đột. Không đưa dataset, trọng số, video tải lên cá nhân hoặc credential vào nhánh mã nguồn. Nhánh Pages chỉ chứa media mẫu đã chọn và hồ sơ công khai.

Bằng chứng quyền/ref và kiểm tra web: `outputs/audits/pages_2026-11-19/`. Audit giữ tên ngày bắt đầu; nhật ký tiếp tục trong `progress/2026-11-21.md`.

## Kết quả lịch sử — 16/11/2026

Đã đăng nhập GitHub qua luồng browser/device của GitHub CLI chính thức, tài khoản `minhquan0500`. API repo gốc xác nhận `push=false`, nên dùng fork thuộc tài khoản này để công bố nhánh và tạo draft pull request về repo được người dùng chỉ định.

- [Nhánh đã upload: feat/collision-demo-2026-11-16](https://github.com/minhquan0500/DACN_TrafficCollision/tree/feat/collision-demo-2026-11-16).
- [Draft PR #1 về leanhquan0211/DACN_TrafficCollision](https://github.com/leanhquan0211/DACN_TrafficCollision/pull/1).
- Commit nguồn đã đối chiếu remote: `8211918cac66fe9c32c1e92bc3b4e4395cc1bf0b`; commit tài liệu sau đó ghi kết quả xuất bản. SHA cuối được ghi trong audit local `outputs/audits/github_publish_2026-11-16/publication.json`.
- Đã xác minh PR là `open`, `draft=true`, head đúng fork/nhánh và base là `main` của repo gốc. API báo **mergeable=false / dirty**: hai dòng phát triển có xung đột cần xử lý trước tích hợp.
- Không push trực tiếp vào repo gốc, không sửa hoặc merge `main`. Muốn tạo nhánh trực tiếp trong repo gốc cần tài khoản được chủ repo cấp quyền ghi.

## Phạm vi bản nguồn

Nhánh từ `79d7af9` ngày20/10 tương ứng bản ZIP đang phát triển. `main` gốc đã có dòng dashboard/training khác ở `0f223f7`; không coi snapshot demo là bản đã tích hợp tương thích với dòng mới. Chủ repo cần đối chiếu và giải quyết xung đột trước khi nhận thay đổi. PR giữ draft để thể hiện điều này.

Có source/config/metadata/review/registry, hướng dẫn, nhật ký, Word/PDF/slide và bằng chứng nhỏ. Không có dataset, model weights, video upload cá nhân, ZIP hoặc môi trường Python. `.gitattributes` giữ nguyên byte CSV registry để bảo toàn fingerprint.

Kiểm tra trước xuất bản: 70/70 test trên máy có dữ liệu; source tách riêng68đạt/2skip tích hợp thiếu pilot. 148 file của snapshot đã kiểm round-trip Git giống byte. Chỉ thêm tài liệu/trạng thái xuất bản sau đó, không đổi mã suy luận. Chưa kiểm cài dependencies sạch hoặc nghiệm thu chất lượng trên camera độc lập.

## Vị trí để tiếp tục

- Thư mục source gốc `/home/minh-quan/Downloads/DACN_TrafficCollision-main` là bản ZIP, `.git` rỗng. Không git init/ghi đè môi trường này.
- Worktree Git: `.cache/github-publish/collision-demo`.
- Remote `origin`: repo gốc `leanhquan0211/DACN_TrafficCollision`; remote `fork`: `minhquan0500/DACN_TrafficCollision`.
- GitHub CLI được kiểm checksum tại `.cache/github-tools/gh`. Config đăng nhập ở `.cache/github-auth` bị Git ignore; không đọc/in token, không copy vào source/bundle.
- Bằng chứng local: `outputs/audits/github_publish_2026-11-16/`. Bản bundle trước đăng nhập giữ snapshot8211918; source GitHub là bản cập nhật tiếp theo.

Người dùng đã cho phép upload nhánh này. Không hỏi lại quyền push cùng phạm vi. Việc cài GitHub plugin trước đó đã thành công nhưng công cụ chưa được nạp vào phiên đang chạy; GitHub CLI/browser đã giải quyết đăng nhập mà không cần người dùng chuyển chat. Các ghi nhận thiếu đăng nhập trong nhật ký là lịch sử, không còn là trạng thái hiện tại. Hosting24/7 đã bị người dùng hủy.
