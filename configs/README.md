# Cấu hình

Giai đoạn này dùng tham số dòng lệnh của các script. Chưa có cấu hình huấn luyện hoặc quy tắc kết luận va chạm.

`cadp_1407_preview.json` chỉ lưu căn chỉnh của **demo đã render** 1407: hash MP4/TXT, canvas và phép biến đổi từ tọa độ VATIC vào vùng ảnh Matplotlib. `prepare_cadp_pilot.py` kiểm hash và ZIP tham chiếu trước khi áp mapping; không dùng config này cho video sạch hoặc mẫu khác.

`b0_region_proposal.json` là **quy tắc vùng accident đề xuất**, chưa được duyệt thành GT hoặc config train. `prepare_b0_candidates.py` chỉ xuất hộp bao participant theo từng event đã rà, không padding, giữ cờ ignore/unknown và `training_eligible=false`. [Định nghĩa và giới hạn](../docs/b0_label_protocol.md). Không đổi status config để tự coi đề xuất là GT: cần quyết định quy tắc và bước rà vùng riêng trước khi viết công cụ export nhãn đã duyệt.
