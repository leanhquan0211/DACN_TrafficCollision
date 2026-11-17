# Phát hiện va chạm tự động thử nghiệm — 16/11/2026

Đã có luồng chạy hoàn chỉnh trong demo: **video → YOLOv8n/ByteTrack → luật chuyển động causal → xác nhận/chống lặp theo cặp → cảnh báo + khung đỏ + ảnh/clip + Events JSON**. Áp dụng được cho MP4 tải lên, không đọc nhãn hoặc tên video để quyết định. Đầu ra ghi `suspected_collision` / **NGHI VA CHẠM**, cần kiểm bằng chứng; chưa phải detector đã được kiểm định trên nhiều camera.

**Ưu tiên nghiên cứu17/11:** đã có [bảng P/R/mAP50 cho detector xe và B0accident](EXPERIMENT_RESULTS.md) trên dữ liệu có nhãn, ghi rõ train/validation và scope. Các metric bbox đó không là precision/recall của cảnh báo trong trang này. B2vẫn chưa có test sự kiện độc lập; không lấy CADP1/1 hoặc số test phần mềm làm độ chính xác hệ thống.

**Cập nhật nhận dạng xe cuối16/11:** bật NMS giữa các lớp để giảm khung trùng, thêm lớp hiển thị theo lịch sử/“chưa rõ loại”, giữ dự đoán thô và luật v5. CADP chạy lại đúng cặp tại108, candidate35/35 (trước thay NMS:109/34trên35); clip900frame vẫn0alert, ba DETRAC vẫn0alert.80test và6nhóm Firefox đạt. [Chi tiết và giới hạn](VEHICLE_LABEL_FIX.md). Số frame109 và74test của lượt dưới đây giữ là lịch sử, không phải giá trị mới nhất.

**Cập nhật v5 sau phản hồi báo nhầm:** clip người dùng900frame giảm từ1cảnh báo sai ở165 xuống0 sau chạy CPU đầy đủ; CADP chạy lại vẫn có cảnh báo109. Bộ test mới74/74đạt. [Chẩn đoán và bằng chứng trước/sau](FALSE_ALERT_FIX.md). Các ảnh/video kết quả v4 dưới đây giữ là lịch sử; web local đánh dấu kết quả cũ và dùng lượt mới nhất sau khôi phục.

## Sử dụng

Chạy `bash demo.sh`, mở <http://127.0.0.1:8765> và chọn **Phát hiện va chạm · Thử nghiệm** (mặc định). CADP local mới nhất có một cảnh báo108; bản lưu trước thay NMS là109, ID1/19. Bấm **Xem thời điểm cảnh báo**, **Ảnh bằng chứng**, **Clip bằng chứng** hoặc tải **Events JSON**. Mốc96–130 trên mô tả mẫu là nhãn người rà, không được truyền vào thuật toán. Các chế độ detection/tracking giữ riêng, không tự có cảnh báo.

Chọn MP4 H.264 từ máy và bấm **Tải lên & phân tích** để chạy trên video khác. Giới hạn như [hướng dẫn upload](EXTERNAL_VIDEO_DEMO.md). Kết quả chỉ xuất hiện sau khi xử lý và kiểm đủ MP4/cache/hash/evidence; giao diện hiện là xử lý **file offline**, không phải cảnh báo streaming tức thời. Khi xem đầu video, danh sách sự kiện đã biết của cả lượt chạy vẫn được hiển thị để tra cứu.

Ảnh giao diện thật: [collision_dashboard.png](../outputs/audits/collision_2026-11-16/collision_dashboard.png). [Video CADP có cảnh báo](../outputs/collision_2026-11-16/final/cadp_001407_clean_display20fps/cadp_001407_clean_display20fps_collision.mp4), [ảnh](../outputs/collision_2026-11-16/final/cadp_001407_clean_display20fps/cadp_001407_clean_display20fps_collision_evidence/event-0001.jpg), [clip](../outputs/collision_2026-11-16/final/cadp_001407_clean_display20fps/cadp_001407_clean_display20fps_collision_evidence/event-0001.mp4).

## Quyết định và phạm vi

Người dùng yêu cầu hoàn thiện phát hiện va chạm, cho phép chủ động chọn cách làm. [B0 khả thi](B0_FEASIBILITY.md) bỏ sót12/12 vùng validation tại conf0,25; lọc B1 trên các detection đã mất không khôi phục được chúng. Vì vậy triển khai B2 luật chuyển động/FSM **song song** theo chỉ dẫn mới, giữ B0 và gate nghiên cứu chưa hoàn thành. Không tự duyệt35 proposal CADP, không train từ proposal, không đổi review/manifest/split. Đây là thay đổi thứ tự triển khai đã ghi trong README, không phải nghiệm thu toàn bộ lộ trình.

Phân tích khoảng cách/hướng/vận tốc quỹ đạo có cơ sở tham khảo trong [Ghahremannezhad et al., IST2022](https://arxiv.org/abs/2208.06461); ByteTrack kết hợp quan sát confidence thấp với lịch sử để giảm đứt track, theo [Zhang et al., ECCV2022](https://arxiv.org/abs/2110.06864). Project giữ detector/tracker hiện có và tự triển khai luật dưới đây; **không tái lập kiến trúc, tham số hay số liệu của các paper**.

## Luật và đơn vị

Code: [collision_rules.py](../src/collision_rules.py), cấu hình hiện tại: [motion_contact_v5](../configs/collision_rules.json).

1. Lọc quan sát có ID, confidence≥0,15, median confidence lịch sử≥0,3, bbox hợp lệ/đủ lớn. Cạnh ngắn tối thiểu **32pixel tại tỷ lệ đầu vào detector**; quy đổi theo kích thước ảnh/imgsz. Xe nhỏ/xa bị bỏ khỏi phân tích cặp, không được kết luận âm. Giao diện/report ghi số quan sát bị bỏ và số frame còn ít nhất hai xe đủ chất lượng.
2. Giữ tối đa32 quan sát/ID, cần lịch sử trải≥16frame. Vận tốc là median dịch chuyển tâm bbox qua cửa sổ4frame, chuẩn hóa theo đường chéo bbox và số frame thực giữa quan sát. So cửa sổ hiện tại với cửa sổ kết thúc12frame trước. Không dùng frame tương lai.
3. Tạo cặp ứng viên nếu khoảng hở bbox≤0,25 đường chéo thân xe trung bình. Điều kiện hỗ trợ cảnh báo phải đồng thời có: overlap/tổng diện tích bbox nhỏ hơn≥0,25; **v5: chênh mép dưới bbox/chiều cao bbox nhỏ hơn≤1,0**; overlap tăng≥0,08 so mốc quá khứ chung; tâm hai xe đã tiếp cận≥0,10 đường chéo trung bình; ít nhất một xe đổi chuyển động rõ. Chốt mép dưới chỉ là heuristic trên ảnh để loại một số overlap khác độ sâu; không hiệu chuẩn mặt đường và có thể bỏ sót xe bị che khuất/lật/khác độ cao.
4. Biến đổi chuyển động: tốc độ ảnh trước≥0,025 thân/frame và tốc độ hiện tại≤45% trước, hoặc hướng đổi có cosine≤0,25 với tốc độ hiện tại đủ lớn. Đây là tín hiệu ảnh, **không phải gia tốc vật lý hoặc bằng chứng tiếp xúc chắc chắn**.
5. Xác nhận3frame hỗ trợ trong5frame gần nhất. Máy trạng thái từng cặp: `idle → suspected → confirmed_by_rule → cooldown`. Cooldown100frame theo **cặp**, không khóa sự kiện của cặp khác. Bỏ lịch sử khi mất track quá3frame, bbox đổi tỷ lệ đột ngột hoặc phát hiện cắt cảnh; không nội suy bbox bị thiếu. Đổi ID cần tích lũy lịch sử mới.

`evidence_score` là số tín hiệu đạt/4, **không là xác suất**. Sau xác nhận nó thường bằng1, không được diễn giải là “chắc chắn100%”. `confirmed_by_rule` chỉ có nghĩa đủ điều kiện luật; quyết định phát hành vẫn là `suspected_collision`, `needs_review=true`.

Với CADP chưa xác minh FPS nguồn, chỉ đo theo frame và ghi `source_time_s=null`. Frame109 ứng với5,45giây **trong video trình chiếu20FPS**, không phải giây nguồn. Khoảng từ onset người rà96 đến alert109 là13frame; chưa báo event delay bằng giây nguồn hoặc km/h. Clip bằng chứng dùng clock của video đã render; đoạn sau alert chỉ được trích **sau khi quyết định**, không tham gia suy luận.

## Kết quả đã chạy và diễn biến sửa lỗi

Tất cả dữ liệu sau là **development/chẩn đoán đã được xem để phát triển luật**, không có test khóa độc lập. Các bản code/config/report trước sửa giữ tại `outputs/audits/collision_2026-11-16/rules_v1/` đến `rules_v4/`; mỗi bản có snapshot producer và config.

| Phiên bản phát triển | CADP bắt đúng sự kiện/cặp | Cảnh báo sai ngoài interval/cặp CADP | Cảnh báo trên3DETRAC đã rà âm |
| --- | ---: | ---: | ---: |
| v1 | 0/1 | 1 | 6 |
| v2 | 0/1 | 0 | 4 |
| v3 | 1/1, frame109 | 0 | 4 |
| v4, thêm lọc độ phân giải bbox | 1/1, frame109 | 0 | 0 |
| v5, thêm tương thích mép dưới bbox | 1/1, frame109 | 0 | 0 |

v1/v2 làm rõ lỗi confidence giảm/mất quan sát ngắn ở xe buýt. v3 vẫn có FP ở xe nhỏ/xa, che khuất và bbox dao động; [bảng ảnh lỗi](../outputs/audits/collision_2026-11-16/rules_v3/alert_error_review.jpg) giữ đủ bốn FP và case CADP. v4 dùng chốt chất lượng32pixel để tránh suy chuyển động từ bbox quá ít chi tiết; **đổi lại có thể bỏ sót va chạm nhỏ/xa**. Các threshold đã chọn sau khi xem chính dữ liệu này, nên không dùng bảng để chứng minh tổng quát hoặc cải thiện trên test.

Lượt v4 [final_replay/report.json](../outputs/audits/collision_2026-11-16/final_replay/report.json), các số dưới đây được giữ khi replay v5 tại `outputs/audits/false_alert_2026-11-16/v5_replay/report.json`:

- CADP221frame: ứng viên đúng cặp xuất hiện34/35frame interval96–130, một frame thiếu xe buýt; có cảnh báo đúng cặp tại109, không cảnh báo khác. Đây là **candidate event recall1/1 và coverage34/35 ở development**, không là IDF1/recall tổng quát.
- Ba DETRAC664/936/437frame, tổng2037frame≈81,48giây có FPS nguồn đã xác minh: không cảnh báo trong lượt cuối. Video ngắn và đã dùng sửa luật, chưa chứng minh FAR/hour trên dữ liệu mới hoặc camera khác.
- Cao tốc Roboflow250frame: không cảnh báo. Clip này chưa có GT, nên không tự gọi là TN hoặc đo accuracy.
- Chạy pipeline CPU thật cho CADP/DETRAC10giây; Firefox chạy lại CADP và upload cao tốc mới ở chế độ collision, đều complete và kiểm lại output. Không dùng cache replay để giả làm benchmark end-to-end.
- Sau phản hồi người dùng: chạy CPU thật clip900frame với v5, loại cảnh báo sai v4 ở165; chạy lại CADP221frame vẫn cảnh báo109. Replay đối chứng bỏ riêng chốt mép dưới tái hiện cảnh báo165. Clip900frame dùng sửa lỗi phát triển, chưa có nhãn đầy đủ; không tự coi là video âm được duyệt hoặc test độc lập.

Không đưa F1=1/accuracy100% từ một positive đã dùng phát triển. B0/B1, B2, MLP/GRU chưa có so sánh trên cùng test độc lập. Bộ verifier học máy chưa triển khai, không cần có nó để chạy bản luật này.

## Kiểm thử và bằng chứng

**74/74 test đạt** ở lượt v5, tăng từ70 trước sửa. Ngoài9test hành vi causal và4test integrity ban đầu, thêm kiểm xe xa chồng xe gần rồi phanh, cặp xe khác chiều cao có mép dưới tương thích, cấu hình mép dưới không hợp lệ và khôi phục run mới nhất theo timestamp có múi giờ. Có kiểm: xe đứng chồng bbox; xe đi song song; phanh khi ở xa; đi xuyên qua nhau trong ảnh mà không đổi tốc; va chạm mô phỏng với dừng; mất quan sát; đổiID; cắt cảnh; cooldown độc lập theo cặp; quy đổi kích thước ảnh; prefix không đổi khi sửa tương lai; event/evidence mismatch và đường dẫn vượt thư mục.

Các test mô phỏng kiểm logic phần mềm, không thay dữ liệu thực. `scripts/check_demo.py` kiểm HTTP Events JSON/ảnh/clip/range/ID lỗi; Firefox kiểm nút xem sự kiện, CPU rerun, upload chế độ collision, không giữ card cảnh báo cũ khi chuyển mẫu và refresh. Khi dọn WebDriver có cảnh báo quyền SIGTERM của Selenium/Snap sau khi lưu ảnh/JSON; các kiểm chức năng đã hoàn tất.

Hồ sơ tại `outputs/audits/collision_2026-11-16/`: `tests.log`, `browser_check.json`, `http_check.json`, `recovery_check.json`, `final_replay/report.json`. [Snapshot nhỏ](evidence/2026-11-16-collision.json) đọc được sau clone; media/cache đầy đủ vẫn cục bộ.

Lượt sửa v5 giữ audit riêng tại `outputs/audits/false_alert_2026-11-16/`: đối chứng bỏ chốt, replay6cache, hai lượt CPU đầy đủ,74test, khôi phục và5nhóm Firefox. [Snapshot v5](evidence/2026-11-16-false-alert-fix.json) không kèm video/ảnh người dùng. Pages và gói bàn giao đã tạo trước lượt sửa giữ nguyên snapshot v4; không xem chúng là output v5.

## Tái lập

```bash
# Chạy thật, cùng pipeline model/tracker; output tự thêm hậu tố nếu trùng
PATH="$PWD/.venv/bin:$PATH" .venv/bin/python -B scripts/run_collision.py \
  data_samples/cadp/cadp_001407_clean_display20fps.mp4 \
  --device cpu --cpu-threads 4 --timing-status presentation_only \
  --output-dir outputs/collision_repeat
.venv/bin/python -B scripts/check_inference_outputs.py outputs/collision_repeat

# Chỉ replay cache đã kiểm để phân tích luật; không đo FPS toàn hệ thống
.venv/bin/python -B scripts/evaluate_collision_rules.py \
  --output outputs/audits/collision_repeat
.venv/bin/python -B -m unittest discover -s tests -v
```

Lệnh replay mặc định dùng các report phát triển và processed VATIC có trên máy này; cần phục hồi đúng dữ liệu/hashes theo hướng dẫn khi clone. Có thể truyền nhiều `--report`. Nó chỉ đọc GT trong evaluator để ghép/đếm; `CollisionRules` chỉ nhận quan sát tracker và clock. Hash source weights/input/cache/config/code và event/evidence được lưu; sửa evidence sau chạy sẽ bị từ chối khi nạp vào demo.

## Phần còn cần để nghiệm thu nghiên cứu

Cần thêm positive/near-miss/negative có nhãn đầy đủ và camera độc lập, FPS nguồn, tách development/validation/test khóa trước tinh chỉnh, đo bỏ sót xe nhỏ và ID switch, motioncamera/cắt cảnh, FAR/hour trên video dài cùng miền và event delay đúng timestamp. Quy tắc vùng CADP/B0 readiness vẫn giữ nguyên chưa duyệt; không biến một bản cảnh báo chạy được thành bằng chứng đề tài đã đủ độ chính xác.
