# Chọn và phân tích video trên GitHub Pages

## Cách dùng

Mở <https://minhquan0500.github.io/DACN_TrafficCollision/upload.html> hoặc bấm **Phân tích video của bạn** trên trang chính. Chọn một MP4, chọn chế độ rồi bấm **Phân tích video**. Có tiến trình, thời gian ước lượng và nút **Hủy xử lý**. Khi xong, phát/tua video bên trái để xem các bbox trên mẫu hình gần nhất bên phải; các mốc nghi va chạm có nút tới thời điểm đó.

Hỗ trợ file MP4 trình duyệt giải mã được, không rỗng, tối đa **100 MiB, 120 giây, Full HD**. Ưu tiên MP4 H.264 và clip ngắn trên máy tính. Lấy mẫu **20 Hz** theo thời gian container, không suy đây là FPS nguồn. Model và runtime khoảng 25 MB ở lần tải đầu; thời gian phân tích phụ thuộc máy. Video chỉ được đọc qua blob URL trên thiết bị, không gửi tới GitHub hoặc API suy luận.

Tải **JSON** để giữ kết quả (SHA-256 file, phương pháp, mọi mẫu/bbox/ID và các event); tải **PNG** của khung đang xem. Kết quả giữ trong bộ nhớ trang, đóng/tải lại sẽ mất nếu chưa tải JSON. Bản này chưa xuất video MP4 có khung. Các clip mẫu/PDF cũ vẫn xem được ở trang chính.

## Mô hình và phạm vi thay đổi

Yêu cầu người dùng ngày 25/11 là cho Pages xử lý được video mới, trong khi chưa có máy chủ suy luận được triển khai. Chọn **ONNX Runtime Web WASM trên thiết bị** để dùng được với hosting GitHub Pages hiện có. Đây là thay đổi cách triển khai, không thay dữ liệu train hoặc mở benchmark mới.

- Dùng đúng `yolov8n.pt` COCO pretrained, SHA-256 `f59b3d833e2ff32e194b5bb8e08d211dc7c5bdf144b90d2c8412c47ccfc83b36`, không huấn luyện thêm. Export ONNX FP32, opset17, input `[1,3,640,640]`, output `[1,84,8400]`, không gắn NMS trong graph. Hồ sơ `models/model.json` và `PUBLIC_MANIFEST.json` có hash; worker kiểm SHA model trước chạy.
- Preprocess canvas RGB letterbox640, confidence0,25, NMS giữa lớp IoU0,7, tối đa100bbox; nhận bicycle/car/motorcycle/bus/truck từ80lớp COCO. Chọn lớp có score cao nhất trên đủ80lớp trước lọc phương tiện. Canvas resize/letterbox vuông khác nhánh rect của Python.
- ONNX Runtime Web **1.23.2**, WASM một thread trong Web Worker, không cần cross-origin isolation. Runtime/model cùng origin của Pages; không phụ thuộc CDN ngoài lúc người dùng phân tích. Tải có tiến trình, timeout và báo lỗi nếu model sai hash hoặc trình duyệt không hỗ trợ.
- Bộ theo dõi browser `browser_iou_velocity_v1`: greedy IoU với vị trí dự đoán từ chuyển động quá khứ, không khóa class để nối ID; gap dài và cut reset lịch sử. **Đây là bộ theo dõi khác ByteTrack**. Ghi rõ trong giao diện và JSON; không mang số IDF1/metric của Python sang.
- Port đúng logic `motion_contact_v5` sang JavaScript, cùng điều kiện chất lượng, tiếp cận/contact/motion change, xác nhận và cooldown. Chạy trên **mẫu hình20Hz**; chuyển động/camera/nhãn còn ảnh hưởng. `source_time_s=null`, không báo độ trễ nguồn hoặc tốc độ km/h. Scene cut dùng sai biệt ảnh nhỏ, không nối lịch sử xuyên cut. Mốc nghi va chạm cần người xem kiểm tra.

Đây là nhánh triển khai trình duyệt, **chưa có P/R/mAP hoặc event P/R trên test độc lập riêng**. Số đo Python ngày17/11 giữ nguyên và được ghi rõ phạm vi; không suy từ việc chạy được một clip thành accuracy. B0 accident validation thấp vẫn chưa dùng. Không đẩy video người dùng hoặc nhãn tự sinh vào train/val/test.

## Mã và tái lập export

```bash
.venv/bin/python -m pip install -r requirements-browser-export.txt
YOLO_AUTOINSTALL=false .venv/bin/python -B scripts/prepare_browser_assets.py
.venv/bin/python -B scripts/build_pages_demo.py --output outputs/pages_demo_NEW
```

`prepare_browser_assets.py` đọc checkpoint đúng hash, xuất model vào `.cache/browser-model`, tải đúng gói npm `onnxruntime-web@1.23.2` và kiểm tarball SHA-1 từ registry. Runtime assets/hồ sơ/license nằm trong `.cache/browser-runtime`; bản có sẵn sai hash bị từ chối. Source không chứa cache/model/vendor; gói `gh-pages` phân phối các binary cần chạy, có manifest và license. Tệp license MIT/third-party lấy từ distribution ONNX Runtime chính thức đã cài (version được ghi trong provenance), AGPL từ distribution Ultralytics. Model có metadata giấy phép AGPL-3.0; giữ link source triển khai trên giao diện.

Frontend: `demo/pages/upload.html`, `upload.js`, `browser-worker.js`, `browser-core.js`. Trang upload riêng giúp các kết quả mẫu được giữ nguyên nguồn/report, không biến video mới thành clip mẫu. Worker xử lý một frame mỗi lần; cancel hủy worker và vô hiệu hóa kết quả/download cũ. Tên file chỉ để hiển thị/JSON; không được dùng làm HTML hay đường dẫn máy chủ.

## Kiểm chứng

- Export ONNX đã qua checker; trên ảnh CADP110 dùng cùng input tensor với PyTorch fused, sai lệch tuyệt đối lớn nhất≈0,001373, trung bình≈0,000001803 trong đầu ra thô. Đây là kiểm chuyển đổi trên một ảnh development, không phải metric accuracy.
- So toàn bộ quyết định/features/event của JavaScript và Python trên chín chuỗi hành vi: impact, overlap tĩnh, chạy song song, phanh tách xa, giao quỹ đạo, đổi ID, confidence thấp, mất ngắn và scene cut; khớp trong sai số1e-8. Kiểm thêm NMS/letterbox và reset ID sau gap.
- `scripts/check_browser_upload.py` chọn file thật qua input, chạy mô hình WASM hết video, kiểm mọi sample timestamp/hash, JSON, replay, hủy, file lỗi, mobile và không gửi body video qua mạng. Kết quả từng lượt ở `outputs/audits/browser_upload_2026-11-25/`; báo cáo chốt và snapshot được cập nhật sau kiểm cuối.
- Kết quả CADP local ban đầu:221mẫu/1696quan sát/1mốc109 (5,45scontainer),88,677giây xử lý trên Firefox CPU. Đây là chẩn đoán chức năng trên cảnh đã dùng phát triển, không là benchmark độc lập. Không thay GT hoặc tune rule theo kết quả này.

Nguồn kỹ thuật: [ONNX Runtime Web deployment](https://onnxruntime.ai/docs/tutorials/web/deploy.html), [WASM environment flags](https://onnxruntime.ai/docs/tutorials/web/env-flags-and-session-options.html), [Ultralytics ONNX](https://docs.ultralytics.com/integrations/onnx/). Giữ YOLOv8n hiện có dù tài liệu nhà phát hành có thể minh họa bằng model khác.

## Triển khai đã xác minh ngày25/11

Gói Pages `cff376d6c8149a5d7ff005051c95d278a3a432b6` đã upload lên cả repo gốc và fork; fork build `built`. **54/54tệp trên HTTPS khớp export**, gồm model/runtime. Firefox kiểm bảy nhóm và thực sự phân tích file CADP đủ221mẫu/1696quan sát/1mốc,83,109giây trên link công khai. Clip cao tốc ngoài CADP đã kiểm local đủ200mẫu/629quan sát/0mốc,85,401giây. Các số này là chẩn đoán chức năng, không phải accuracy/FPS streaming. Trang mẫu cũ tám nhóm local đạt. [Snapshot và giới hạn](evidence/2026-11-25-browser-upload.json).
