# Sửa cảnh báo nhầm do overlap khác độ sâu — 16/11/2026

**Đã sửa trường hợp người dùng báo:** clip `13275193-hd_1920_1080_60fps.mp4` chạy lại đủ900frame với `motion_contact_v5` không còn cảnh báo v4 tại165. CADP chạy lại đủ221frame vẫn phát hiện đúng cặp tại109. Đây là phân tích lỗi phát triển, chưa chứng minh độ chính xác trên camera/video độc lập.

## Nguyên nhân và thay đổi

V4 báo ở frame165, khoảng2,75giây theo clock của file, giữa track4(taxi) và233(xe máy). Xe máy xa bị chồng khung lên taxi gần; biến động tốc độ ảnh từ khoảng0,079 xuống0,024 thân/frame làm đủ cả bốn tín hiệu luật. Chồng bbox trong trường hợp này không thể hiện tiếp xúc vật lý.

Giữ nguyên YOLOv8n, ByteTrack, các ngưỡng chuyển động, xác nhận3/5frame và cooldown. V5 thêm một điều kiện vào tín hiệu `contact`:

```text
abs(ymax_A - ymax_B) / min(height_A, height_B) <= 1.0
```

Chiều cao có chặn dưới1pixel để tránh chia0. Tại cảnh báo nhầm165, tỷ lệ≈2,301; các frame hỗ trợ163–165 đều>2. Tại cặp va chạm CADP109, tỷ lệ≈0,416. Điều kiện không đọc tên file, hash input, camera, ID xe hoặc nhãn. Bốn tín hiệu vẫn tạo `evidence_score` trên thang0–1, không là xác suất.

Đối chứng trên cùng cache với chốt mép dưới tắt tái hiện cảnh báo165; bật chốt loại cảnh báo này. Evaluator có thể đọc cache tracking hoặc collision đã kiểm, bỏ quyết định collision cũ trước khi replay; chỉ giữ cờ cắt cảnh được đo từ ảnh.

Đồng thời sửa hai điểm ảnh hưởng việc xem kết quả:

- Khôi phục chọn lượt chạy mới nhất theo `checked_at` có múi giờ, thay vì thứ tự thư mục UUID. Mọi run cũ vẫn còn để đối chiếu; cảnh báo cũ không thay kết quả đã sửa sau restart.
- Web ghi **“Kết quả dùng luật cũ · Chạy lại trên CPU để cập nhật”** nếu hash cấu hình của run khác cấu hình hiện tại. Đây là kiểm phiên bản config, không kiểm tính đúng của mọi quyết định hoặc toàn bộ phiên bản producer.

## Kết quả đã kiểm

| Trường hợp phát triển | Trước / tắt chốt mép dưới | V5 |
| --- | --- | --- |
| Clip người dùng,900frame | 1cảnh báo ở165 | 0cảnh báo |
| CADP,221frame | Đúng cặp tại109 | Đúng cặp tại109, không cảnh báo khác |
| DETRAC,664+936+437frame đã rà âm | 0cảnh báo | 0cảnh báo |
| Cao tốc Roboflow,250frame chưaGT | 0cảnh báo | 0cảnh báo |

900frame của clip người dùng và221frame CADP đều được **chạy lại pipeline CPU thật**, không chỉ replay cache. Với clip người dùng, input/trọng số và quan sát detector/tracker của cả900frame giống bản cũ; khác biệt cảnh báo đến từ luật. Lượt chạy900frame dùng CPU4threads,61,824giây trong pipeline (≈14,56FPS offline), gồm decode/inference/tracking/render/cache/encode, không gồm load model và hash sau chạy; chưa là benchmark streaming hoặc real-time.

**74/74test đạt**,0skip. Bốn test mới kiểm: phanh của xe phía xa chồng xe gần; hai xe khác chiều cao có mép dưới gần nhau vẫn được xét; ngưỡng không hợp lệ; khôi phục đúng lượt mới theo thời gian có múi giờ. Fixtures chỉ kiểm hành vi phần mềm.

Firefox đạt5nhóm: CADP vẫn cảnh báo109; chọn clip người dùng không còn alert/card cũ; video kết quả giải mã/phát/tua được; v4 còn nguyên nhưng được đánh dấu cũ; refresh vẫn chọn bản sửa. Khởi tạo lại `DemoState` từ storage cũng chọn đúng run0event và không lỗi asset.

## Xem trên máy này và tái lập

Chạy `bash demo.sh`, mở <http://127.0.0.1:8765>, chọn `13275193-hd_1920_1080_60fps.mp4` và **Phát hiện va chạm · Thử nghiệm**. Kết quả mới hiển thị900frame,0cảnh báo. Có thể bấm **Chạy lại trên CPU**. Chọn CADP để đối chiếu sự kiện109. Các mẫu lịch sử chưa chạy lại có dòng nhắc dùng luật cũ.

Chạy độc lập trên bản upload đã lưu cục bộ:

```bash
PATH="$PWD/.venv/bin:$PATH" .venv/bin/python -B scripts/run_collision.py \
  outputs/demo_app/uploads/a9e495eefb3646ea909e437433925500/video.mp4 \
  --device cpu --cpu-threads 4 --timing-status unknown \
  --output-dir outputs/false_alert_repeat
.venv/bin/python -B scripts/check_inference_outputs.py outputs/false_alert_repeat
```

Sau clone không có upload này; dùng file gốc người dùng cung cấp, không tự tải lại hay thay fingerprint. SHA-256 input: `977c45debc5101c5f150a67ece8dfe12206a5dc7dd8d872f8dfc65da8b22cccb`.

Audit cục bộ: `outputs/audits/false_alert_2026-11-16/`.

- `before/`: code/config v4, đặc trưng cặp và frame hỗ trợ trước sửa.
- `gate_disabled_replay/`, `v5_replay/`: cùng6cache, config/producer/per-frame/report để đối chiếu chốt bật/tắt.
- `comparison.json`, `user_result.json`, `cadp_result.json`: hash/số đo và kết quả hai lượt CPU.
- `tests.log`, `recovery_check.json`, `browser_check.json`, `corrected_dashboard.png`: kiểm phần mềm, khôi phục và giao diện thật. Ảnh giao diện giữ cục bộ vì chứa video người dùng.

[Snapshot nhỏ trên Git](evidence/2026-11-16-false-alert-fix.json) không kèm media/ảnh người dùng. Output cũ giữ nguyên, không sửa report/hash để làm mất cảnh báo. Pages và Word/PDF/ZIP tạo trước lượt sửa vẫn là snapshot v4, chưa được tái xuất bằng v5.

## Giới hạn và bước tiếp theo

Chốt mép dưới chỉ là heuristic ảnh, không phải hiệu chuẩn mặt đường3D. Nó có thể bỏ sót xe bị che khuất, xe lật hoặc ở độ cao khác. Chốt chất lượng32pixel vẫn có thể bỏ xe nhỏ/xa; lịch sử và xác nhận vẫn theo frame, nên hành vi theo thời gian thay đổi với FPS. Tắt chốt không đồng nghĩa quyết định cũ đúng, và không có cảnh báo không chứng minh toàn video an toàn.

Clip mới là case báo nhầm do người dùng chỉ ra, chưa có nhãn đầy đủ toàn clip; không tự thêm vào train/validation/test hoặc xác nhận âm. Các cảnh dùng điều chỉnh đều là development. Không đổi model/nhãn/split/readiness, không nghiệm thu gate nghiên cứu hoặc báo F1/accuracy từ các case này. Tiếp theo cần positive/near-miss/negative có nhãn và camera độc lập, khóa đánh giá trước tinh chỉnh tiếp, đo cả giảm báo nhầm lẫn bỏ sót do chốt mới.
