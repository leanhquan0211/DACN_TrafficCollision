# Trạng thái xuất bản nhánh demo

## Kết quả đã xác minh — 16/11/2026

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
