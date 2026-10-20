# Dữ liệu gốc — chỉ lưu ở máy, không đưa lên Git

Đặt file theo [bảng nguồn tải/vị trí chính xác](../docs/GETTING_STARTED.md#4-tải-dữ-liệu-đúng-vị-trí). Giữ nguyên tên ảnh/ZIP và cấu trúc DETRAC; không đổi tên gần giống để ép ghép nhãn.

```text
cadp/
  pilot_1407/1407.mp4, 1407.txt
  frames/<ZIP tải riêng 001407 nếu có>
  frames/001407/0.jpg ... 220.jpg
  reference_code/CarCrash_forecasting_and_detection-master.zip
  documentation/<README và paper tác giả nếu đã tải>
  annotations/vatic/<TXT mới do tác giả cung cấp, hiện chưa có>
ua_detrac/
  DETRAC-Images.zip
  DETRAC-Images/MVI_20011/img00001.jpg ... img00664.jpg
  DETRAC-Images/MVI_20012/img00001.jpg ... img00936.jpg
  DETRAC-Images/MVI_20032/img00001.jpg ... img00437.jpg
  annotations/DETRAC-Train-Annotations-XML.zip
  annotations/DETRAC-Test-Annotations-XML.zip
```

Repo chỉ giữ README này và `.gitkeep`; dữ liệu gốc do người dùng tải từ nguồn. Không giải nén toàn bộ CADP/DETRAC nếu chỉ cần pilot ba chuỗi.
