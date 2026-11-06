# Frontend DACN_TrafficCollision — thiết kế và phạm vi triển khai

**Trạng thái 02/11/2026 sau phê duyệt:** đã dựng app React/TS/Vite, API FastAPI read-only và sáu khu vực đọc artifact thật; có biểu đồ epoch/so sánh, kiểm kê nguồn/split, histogram bbox val theo ảnh PNG gốc khi có, gallery/overlay, video B1 và tài liệu nguồn. Đã kiểm snapshot Kaggle Version 11 COMPLETE/50 epoch qua API, có nút đọc/lặp theo yêu cầu; chưa mở run đang train mới để kiểm live đang chạy. Môi trường web tách `.venv-dashboard`, package frontend có lockfile. Không đổi model/recipe/dataset/split hoặc mở thí nghiệm. Cách chạy/kiểm và hạn chế thực tế tại [README](README.md).

**Điều chỉnh giao diện 04/11/2026 theo ảnh người dùng gửi:** toàn dashboard dùng nền hồng phấn nhẹ, chữ tím than, điểm nhấn hồng và thẻ viền sáng; bản tối dùng nền xanh tím rất đậm, cùng hệ điểm nhấn. Giữ Be Vietnam Pro + Geist làm mặc định. Bộ chọn font có Be Vietnam Pro toàn bộ, Inter toàn bộ, hoặc Lora tiêu đề + Inter nội dung; font đóng gói cùng frontend bằng Fontsource và có subset tiếng Việt. Đây chỉ là thay đổi trình bày, không đổi số liệu hay giao thức đánh giá. Ảnh tham chiếu chỉ dùng bố cục, nhịp chữ, màu và thẻ; không sao chép nội dung học tập hoặc đồ họa quả cam.

## 1. Mục tiêu và phạm vi

Giao diện tiếng Việt phục vụ **đọc kết quả, hiểu quá trình huấn luyện và kiểm tra lỗi**, rồi mở rộng theo dõi những lần train tiếp theo. Người dùng chính là người làm đồ án và người xem báo cáo. Hiện B0 có detector ảnh và B1 có chẩn đoán; UI phải giữ đúng phạm vi ấy, không biến bbox hoặc đoạn ON thành sự kiện va chạm đã được kiểm chứng.

Ưu tiên dữ liệu thật: `experiment.json`, `results.csv`, config, các file trong `metrics_val/`/`cases_val/`, provenance và kết quả temporal hiện có. Không dựng số epoch, trạng thái GPU, độ trễ, FAR/hour hoặc kết quả baseline chưa có. File thiếu hiển thị chưa có dữ liệu, không thay bằng số 0. Các thông tin demo/fixture nếu cần phát triển phải có nhãn riêng và không lẫn với kết quả thật.

## 2. Sáu khu vực chính

| Khu vực | Nội dung và tương tác | Nguồn/điều kiện |
| --- | --- | --- |
| **Tổng quan** | Tên/mục tiêu đồ án, pipeline, B0/B1/B2/T0/B3, run đang chọn, metric snapshot, train/val theo nguồn, lịch sử mốc chính, việc kế tiếp | Bảng baseline là nguồn trạng thái duy nhất; đọc config/experiment và evidence, không tạo bảng tiến độ viết tay thứ hai |
| **Huấn luyện** | Danh sách run; biểu đồ mAP/P/R theo epoch, best/last, epoch thực/tối đa, optimizer/LR/batch/imgsz/seed, early stopping, môi trường; log một dòng/epoch; tab loss nâng cao | CSV là metric theo epoch; đánh giá lại best là nguồn khác. Tốc độ/thời gian/VRAM chỉ hiển thị nếu log có căn cứ; không suy GPU hiện tại từ máy của run cũ |
| **So sánh** | Chọn 2–3 run, cột/đường mAP50/95, P/R/F1 cố định, TP/FP/FN, bảng thay đổi config và dữ liệu; mở PNG gốc cạnh biểu đồ tương tác | Mặc định nhóm cùng split/provenance/protocol; khác dữ liệu phải có nhãn khác protocol, không xếp chung thành bảng thắng/thua. Giữ phân biệt ảnh/bbox/event |
| **Dữ liệu** | Sơ đồ nguồn → release → split, số ảnh/clip/nhóm nguồn, dương/âm/unknown, kích thước bbox, ảnh nhỏ và review/mapping; lọc theo nguồn/split | Registry/provenance/review hiện có; metadata có trên Git không chứng minh media local đã có. Không biến số frame thành số sự kiện/camera độc lập |
| **Kiểm tra ảnh/video** | Gallery TP/FP/FN; phóng to ảnh, bật/tắt GT và prediction khi đủ tọa độ, confidence/IoU, tìm theo source/frame; video + timeline score/B0/EMA/3-of-5 | Dùng prediction/case/clip có sẵn. Video GT và dự đoán tách rõ; ID tracker khác ID tác giả. Thời gian không xác minh được thì dùng frame; các thay đổi ngưỡng chỉ là xem trước, không sửa metric/run lịch sử |
| **Tra cứu & báo cáo** | Metric glossary có ví dụ, paper/vai trò, README baseline/ngày, PDF slide/báo cáo, ảnh curve gốc, xuất bảng/biểu đồ đang xem | Tái dùng reference/docs/progress hiện có. Bản vẽ lại ghi nguồn; PNG gốc giữ nguyên. Chưa có metric thì không tạo biểu đồ để lấp khoảng trống |

Trong màn hình Huấn luyện, thao tác cần có: chọn metric, bật/tắt từng đường, tooltip theo epoch, chọn khoảng epoch, đánh dấu best và epoch cuối. Làm mượt là tùy chọn có nhãn, đường raw luôn truy cập được; không dùng đường làm mượt để chọn checkpoint. Loss đưa vào mục thu gọn để hỗ trợ chẩn đoán khi cần, không chiếm khu vực chính.

Các thẻ metric có nút giải thích: precision liên quan báo sai, recall liên quan bỏ sót, F1 cân bằng, IoU là yêu cầu khớp hộp, AP/mAP tổng hợp đường PR. P/R do Ultralytics chọn điểm trên đường PR không được trộn với P/R/F1 đếm lại tại confidence 0,25/IoU 0,5. 70,64% mAP50 của V11 chưa phải accuracy sự kiện hay tiêu chí hoàn tất hệ thống.

## 3. Bố cục và phong cách

Tham khảo có chọn lọc `frontend/` workshop: component dùng lại, `tokens.css`, layout theo route, services tách khỏi màn hình, trạng thái loading/error/empty, theme và appearance preferences. Không sao chép nghiệp vụ vé/sự kiện, phiên đăng nhập, credential, dữ liệu người dùng hay toàn bộ node_modules từ project cũ.

- **Bố cục ứng dụng:** thanh điều hướng ngang có nhãn, bộ chọn run và thời điểm dữ liệu cập nhật; mobile có drawer. Trên mỗi trang, phần chính dành cho biểu đồ/ảnh, phần phụ cho cấu hình/ghi chú. Tổng quan có minh họa nhỏ; các trang phân tích dùng bố cục workbench, không lặp hero lớn hoặc một lưới card giống nhau trên mọi trang.
- **Màu và chữ:** quyết định ban đầu là kem–đào/san hô, Be Vietnam Pro + Geist. Ảnh tham chiếu và yêu cầu mới ngày 04/11 thay hệ màu hiển thị sang hồng phấn/tím than; dữ liệu, chart và nội dung giữ nguyên. Font mặc định không đổi; ba tổ hợp bổ sung đều có glyph tiếng Việt và lưu lựa chọn local. Màu, font, khoảng cách và radius dùng semantic tokens; bản tối giữ tương phản đọc bảng/biểu đồ.
- **Kính và tùy chỉnh:** kính nhẹ ở header/control, bề mặt biểu đồ đủ đặc để đọc số; chữ/control không giảm opacity. Giữ tùy chọn nền phẳng/gradient, neon, chuyển động, bo góc và độ trong suốt theo rule; giá trị 0 hợp lệ, lưu localStorage với khóa riêng project. Màu series/nhãn TP–FP–FN ổn định giữa các màn hình, không đổi ngẫu nhiên theo run hoặc thanh sắc màu.
- **Hình và chuyển động:** SVG camera, khung ảnh/bbox, giao lộ, làn đường hoặc quỹ đạo; không quạt/cánh hoa. Đồ họa trang trí ghi đúng vai trò minh họa, không giả là kết quả model. Chuyển động nhẹ chỉ transform/opacity; không làm số liệu nhấp nháy hoặc đường metric thay đổi giả. Reduced motion luôn được ưu tiên.
- **Độ dễ đọc:** body khoảng 16px, nhịp 4px, giới hạn dòng hợp lý; bảng/chart có legend và đơn vị. Góc vuông/bo nhẹ cho bảng/plot, không bắt buộc mọi khối thành pill. Focus rõ, thao tác bàn phím được; trạng thái có chữ/icon, không chỉ màu. Có bảng số thay thế biểu đồ và thông tin tooltip tiếp cận được khi không dùng chuột.

## 4. Xem lịch sử và theo dõi trực tiếp là hai chế độ

| Chế độ | Cách lấy dữ liệu đề xuất | Điều cần thể hiện |
| --- | --- | --- |
| **Lịch sử thật — làm trước** | Một adapter Python chỉ đọc các artifact đã lưu, chuẩn hóa thành JSON cho frontend và cung cấp media theo ID nằm trong danh mục cho phép | Run hoàn tất/thất bại theo bằng chứng, đường epoch đã lưu, best revalidation, nguồn file và thời điểm đọc |
| **Local đang train — làm tiếp** | Backend đọc phần CSV/log đã ghi xong, frontend cập nhật định kỳ; bỏ qua dòng CSV đang ghi dở | Epoch cuối nhận được, dữ liệu cập nhật lúc nào, trạng thái chưa rõ nếu thiếu heartbeat; không dùng timer giả làm tiến độ |
| **Kaggle đang train — tích hợp sau** | Adapter phía Python xác thực bằng credential local, đọc API/log rồi chuẩn hóa epoch như local; polling có khoảng nghỉ và backoff | Trạng thái cloud độc lập trạng thái kết nối. Mất quyền/mất log không đồng nghĩa train đã dừng; không bảo đảm live nếu API chưa trả log |

Trình duyệt không tự đọc toàn bộ thư mục `outputs/` hoặc giữ Kaggle token. Không mở API trả tùy ý đường dẫn file; media phải nằm trong các nguồn được đăng ký. Khi triển khai bản đầu, backend phục vụ read-only trên máy người dùng, không cần database hoặc tài khoản web. Chưa có yêu cầu điều khiển train: không đưa nút Train/Resume/Stop vào giai đoạn đầu, tránh thao tác xem kết quả làm thay đổi run.

Các tính năng replay có thể phát lại epoch đã lưu để trình bày, nhưng phải ghi **phát lại lịch sử**, không gọi là live. FPS/VRAM log train không phải benchmark FPS/VRAM toàn pipeline cảnh báo; bbox FP không đổi thành cảnh báo sai/giờ.

## 5. Công cụ đề xuất và lý do

| Công cụ | Nhu cầu/lý do | Phương án khác và giới hạn |
| --- | --- | --- |
| React + TypeScript + Vite | Theo cách tổ chức component/types/services người dùng đã có; phù hợp dashboard nhiều tương tác, chạy local và build riêng frontend | Streamlit nhanh hơn cho prototype Python nhưng không thuận lợi giữ UI kiểu workshop. Phiên bản thực tế khóa tại package-lock.json; không copy node_modules |
| Tailwind + component nguồn kiểu shadcn/Radix + Lucide | Tái sử dụng tư duy token, form/dialog/focus và icon quen thuộc; không cần viết lại mọi tương tác | Không copy nguyên dependency/code nghiệp vụ cũ. Chỉ cài component dùng thật, đối chiếu tương thích và pin lockfile lúc triển khai |
| Recharts | Thư viện biểu đồ theo component React/SVG, phù hợp đường epoch, cột và tooltip; có thể đồng bộ token | ECharts/Plotly là lựa chọn nếu sau này số điểm/biểu đồ vượt nhu cầu hiện tại; chưa cần thêm nhiều thư viện chart. Giữ PNG gốc song song và kiểm chart với CSV |
| FastAPI read-only adapter | Tái dùng Python để đọc CSV/JSON/log/media hiện có và làm cầu nối snapshot Kaggle; không sửa trainer chỉ để vẽ chart | Export JSON tĩnh đơn giản hơn cho offline nhưng không tự theo dõi file mới. API local đã có, cloud đọc theo yêu cầu/định kỳ; chưa kiểm streaming một run đang train mới |

Nguồn sơ cấp đã kiểm ngày 02/11: [React](https://react.dev/learn), [Vite](https://vite.dev/guide/), [Recharts](https://recharts.github.io/en-US/), [FastAPI](https://fastapi.tiangolo.com/). Quyết định trên là đề xuất theo nhu cầu UI và code tham khảo, không thay phương pháp nghiên cứu hoặc công thức train.

## 6. Thứ tự thực hiện và mức đã kiểm

1. **Bản đầu dùng được:** khung giao diện/token, danh sách run, tổng quan, chi tiết train và so sánh, đọc dữ liệu thật của các run đã hoàn tất. Có ảnh curve gốc, giải thích metric và empty/error state, không chỉ dựng màn hình số mẫu.
2. **Đọc lỗi và nguồn:** bổ sung data explorer, ảnh case/overlay, video/timeline B1 và liên kết báo cáo/reference. Chỉ cung cấp media đã có; artifact thiếu được ghi đúng.
3. **Theo dõi các run tiếp theo:** nối local/Kaggle live sau khi đường đọc artifact ổn; kiểm mất kết nối, API 401/403, log chậm, run chưa có epoch và run thất bại. Không tự mở thêm thí nghiệm để test UI.

Đã dùng `frontend/` cho app, `src/dashboard_data.py`/`dashboard_cloud.py` và `scripts/serve_dashboard.py` cho adapter/server; không thêm hệ thống backend/exports/mocks riêng. Kiểm/render đặt trong `.tmp/`, artifact nghiên cứu vẫn tại `outputs/`; không copy dataset vào `frontend/public/` hoặc đưa trọng số/cache lên Git. Ba mục trên là thứ tự thiết kế; lịch sử/ảnh/video đã kiểm với file thật, cloud snapshot đã đọc COMPLETE. Theo dõi file local có kiểm CSV ghi dở bằng fixture; chưa mở train mới để thử heartbeat/live của run mới.

## 7. Điều kiện kiểm trước khi gọi là hoàn thành giao diện

- Metric hiển thị khớp CSV/experiment/cases; số V11 fixed TP/FP/FN = 64/40/27 và mAP50/95 = 70,64/56,80% theo đúng nguồn, không ghép hai operating point.
- Bản đồ các run/split cho biết phép so nào cùng protocol; best epoch không bị đổi thành epoch cuối. Thiếu dữ liệu không hiện 0 hoặc trạng thái giả.
- Biểu đồ có raw/nguồn/scope, ảnh gốc mở được; test/reserve không bị suy luận hoặc dùng tune bởi thao tác UI.
- Chạy build/lint và kiểm browser 320/375/414/768px cùng desktop; kiểm bàn phím, tooltip/legend, dark nếu bổ sung, appearance mức 0, reduced motion và lỗi media/API.
- Phân biệt rõ đã xem lịch sử, đã đọc snapshot cloud và đã điều khiển train; chỉ báo mức thực sự đã kiểm. Đã build/lint, kiểm API/fixture và kiểm sáu route trên browser ở desktop/320/375/414/768px cùng các tương tác chính. Không có endpoint điều khiển train.
