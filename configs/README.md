# Cấu hình

Các script đọc cấu hình có phiên bản và ghi hash trong output; README gốc phân biệt nhánh khả thi/demo với gate nghiên cứu chưa hoàn thành.

- `vehicle_inference.json`: NMS giữa lớp và chính sách nhãn hiển thị causal theo ID, có trạng thái chưa rõ loại. Không thay class/confidence thô hoặc tạo nhãn GT. [Bằng chứng/giới hạn](../docs/VEHICLE_LABEL_FIX.md).
- `collision_rules.json`: luật va chạm thử nghiệm `motion_contact_v5`, không là classifier đã kiểm định độc lập. [Ngưỡng/lịch sử lỗi](../docs/COLLISION_DETECTION.md).
- `demo_catalog.json`: allowlist mẫu và report đã lưu; không đại diện toàn dataset hoặc upload cá nhân.
- `vehicle_evaluation.json`: protocol cố định trước đo hai profileNMS trên2037ảnh DETRAC cóXML, checkpoint COCO giữ nguyên; localization1lớp vàcar/bus2lớp, P/Rởngưỡng đã khai báo. Không test độc lập, không tự train hoặc thay GT/split. [Kết quả/tái lập](../docs/EXPERIMENT_RESULTS.md).

`cadp_1407_preview.json` chỉ lưu căn chỉnh của **demo đã render** 1407: hash MP4/TXT, canvas và phép biến đổi từ tọa độ VATIC vào vùng ảnh Matplotlib. `prepare_cadp_pilot.py` kiểm hash và ZIP tham chiếu trước khi áp mapping; không dùng config này cho video sạch hoặc mẫu khác.

`b0_region_proposal.json` là **quy tắc vùng accident đề xuất**, chưa được duyệt thành GT hoặc config train. `prepare_b0_candidates.py` chỉ xuất hộp bao participant theo từng event đã rà, không padding, giữ cờ ignore/unknown và `training_eligible=false`. [Định nghĩa và giới hạn](../docs/b0_label_protocol.md). Không đổi status config để tự coi đề xuất là GT: cần quyết định quy tắc và bước rà vùng riêng trước khi viết công cụ export nhãn đã duyệt.
