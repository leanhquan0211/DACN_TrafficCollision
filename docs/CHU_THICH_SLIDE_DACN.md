# Chú thích và lời trình bày cho 14 slide

Đọc cùng [PDF slide](SLIDE_TIEN_DO_DACN.pdf). Mỗi mục có **ghi chú ngắn** để hiểu nội dung và **lời trình bày gợi ý** có thể đọc khi thuyết trình. Số liệu là kết quả đã kiểm; các bước tiếp theo vẫn là đề xuất, chưa triển khai thêm.

## Slide 01 — Giới thiệu đề tài

### Ghi chú ngắn

- CCTV là camera giám sát; một frame là một khung hình của video.
- Mục tiêu: phát hiện va chạm xe–xe, tạo cảnh báo có thời điểm, vị trí và clip bằng chứng.
- Ảnh CADP 001407/frame 110 minh họa bối cảnh, chưa có dự đoán của model.

### Lời trình bày gợi ý

> Đề tài hướng đến phát hiện và cảnh báo va chạm giao thông từ video camera giám sát. Hướng tiếp cận là nhận biết vùng có dấu hiệu tai nạn trên ảnh, sau đó kiểm tra thêm diễn biến theo thời gian. Đầu ra mong muốn không chỉ là một hộp đánh dấu, mà còn có thời điểm, vị trí và clip để người xem kiểm tra. Ảnh bên phải là ảnh nguồn minh họa bối cảnh CCTV, chưa phải kết quả dự đoán của mô hình.

## Slide 02 — Các baseline

### Ghi chú ngắn

- **Baseline:** phương án đối chứng để biết phần bổ sung có ích hay không.
- **B0:** YOLOv8 fine-tune qua Ultralytics/PyTorch; ảnh vào → bbox vùng accident và confidence. Đã train/đo.
- **B1:** Python lọc score B0 bằng 3-of-5 hoặc EMA, tức trung bình trượt mũ; không train mạng mới. Đã chẩn đoán.
- **B2:** YOLO xe + ByteTrack → quỹ đạo/cặp xe → luật chuyển động. Nhánh tracking đã có, baseline chưa hoàn chỉnh.
- **T0:** MLP (*Multi-Layer Perceptron*, mạng nhiều lớp) dùng đặc trưng hiện tại. **B3/T1:** cùng một phương án GRU (*Gated Recurrent Unit*, mạng hồi tiếp có cổng) dùng chuỗi quá khứ. Dự kiến dùng PyTorch; chưa triển khai.
- **Cần chứng minh:** giảm báo sai mà vẫn giữ khả năng bắt tai nạn tương đương, đồng thời không tốn quá nhiều thời gian/bộ nhớ. Ít cảnh báo chỉ vì bỏ sót nhiều hơn chưa phải cải thiện.

### Lời trình bày gợi ý

> Lộ trình được chia thành các baseline từ đơn giản đến phức tạp. B0 dùng YOLO tìm vùng tai nạn trong từng ảnh. B1 kiểm tra tín hiệu qua nhiều frame để giảm chớp sai. B2 dự kiến dùng YOLO và ByteTrack để xét chuyển động giữa các xe. T0 dùng MLP làm đối chứng không có bộ nhớ; GRU sẽ dùng thêm chuỗi quá khứ. Các đối chứng giúp kiểm tra phần nào thực sự hữu ích. Mục tiêu là giảm báo sai ở mức phát hiện tương đương, chứ không mặc định mạng phức tạp hơn luôn tốt hơn.

## Slide 03 — Lý do chọn nguồn dữ liệu

### Ghi chú ngắn

- **ACCIDENT:** train có 1.122 ảnh dương từ 1.122 clip, mỗi clip lấy một frame impact có bbox; thêm 19 ảnh âm đã rà từ 11 clip có thể chung nguồn với ảnh dương.
- **TAD normal:** 1.240 ảnh âm train từ 26 video, lấy nhiều frame/video; căn cứ âm là nhãn normal cấp clip của tác giả.
- **UA-DETRAC:** 300 ảnh âm train từ ba chuỗi, 100 ảnh/chuỗi. Người dùng đã xác nhận toàn chuỗi không va chạm; gom bảo thủ một nhóm cảnh.
- **CADP:** 221 ảnh của một chuỗi, frame 0–220; đúng đối tượng và Colliding 96–130 đã xác nhận theo frame, chưa xác minh FPS nguồn.
- **STTAD:** gói ví dụ bốn chuỗi có 31 frame mang bbox; dùng tham khảo/pool, chưa vào các run lớn gần đây.
- Dương/âm xét theo target tai nạn, không theo có/không có xe. Số ảnh khác số video/sự kiện độc lập; ảnh thiếu nhãn vẫn là `unknown`.

### Lời trình bày gợi ý

> Dữ liệu được chọn theo loại nhãn thực sự có thể sử dụng. ACCIDENT là nguồn dương chính: 1.122 ảnh train lấy từ 1.122 clip, không phải từ một video duy nhất. Ngược lại, 1.240 ảnh âm TAD chỉ đến từ 26 video, nên có nhiều frame cùng nguồn. DETRAC đóng góp 300 ảnh từ ba chuỗi đã được xác nhận không va chạm. CADP dùng đối chiếu nhãn theo frame, còn STTAD hỗ trợ chuẩn hóa khái niệm vùng sự kiện. Vì vậy tăng số ảnh chưa đồng nghĩa tăng tương ứng số tình huống độc lập.

## Slide 04 — Chuẩn bị và khóa dữ liệu

### Ghi chú ngắn

- **Ảnh sạch + mapping:** ảnh chưa vẽ đáp án; mỗi ảnh khớp đúng chuỗi, frame và hệ tọa độ nhãn. Kiểm bằng OpenCV, code/annotation tác giả và ảnh đối chiếu.
- **Kiểm nhãn/loại trùng:** kiểm bbox hợp lệ và phạm vi nhãn; dùng hash, ảnh gần giống và rà cảnh để gom nguồn trước chia tập. Không coi ảnh thiếu nhãn là âm.
- **Khóa release:** lưu phiên bản dữ liệu, nguồn gốc từng mẫu (*provenance*), split, config và hash để tái lập. Train cập nhật trọng số; val chọn cách làm; test/reserve giữ ngoài luồng train.
- Gói Kaggle: **2.681 train + 307 val = 2.988 ảnh**; train có 1.151 clip/chuỗi, 1.112 nhóm nguồn. Run lịch sử dùng 1.084 âm chưa rà đã thu hồi.

### Lời trình bày gợi ý

> Trước khi train, cần bảo đảm ảnh chưa chứa hộp đáp án và mỗi nhãn khớp đúng frame nguồn. Sau đó kiểm tọa độ, phạm vi nhãn và các cảnh trùng hoặc gần giống để hạn chế rò rỉ giữa các tập. Phiên bản dữ liệu được khóa cùng nguồn gốc và cấu hình để có thể chạy lại. Gói Kaggle hiện có 2.988 ảnh train và validation; test cùng reserve không nằm trong gói. Quá trình này cũng đã sửa sai bằng việc loại các ảnh âm chưa đủ căn cứ khỏi release hợp lệ.

## Slide 05 — Quá trình B0

### Ghi chú ngắn

- **Pilot 47:** thử nhỏ với 47 ảnh, gồm 17 dương/30 âm; chia 30 train/9 val/8 test. Kiểm đường train → đo, không đủ đánh giá tổng quát.
- **Verified 1.750 → normal 2.170:** sửa nhãn/trùng, khảo sát learning rate rồi bổ sung cảnh âm có căn cứ. Đây là các phiên bản kế tiếp, không cộng số ảnh của chúng.
- **s960:** YOLOv8s, đầu vào 960; thử vì 21/37 FN có cạnh ngắn dưới 32 pixel ở 640. Đổi cả model, kích thước và augmentation, tức biến đổi ảnh khi train.
- **Hardneg 2.680:** chọn frame khó từ clip normal đã có nhãn; prediction chỉ dùng xếp hạng, không làm nhãn thật. Warm-start nghĩa là dùng trọng số đã học nhưng tạo optimizer mới.
- **Kaggle 2.988:** chỉ train+val; thêm normal trong nhóm train cũ, giảm tải laptop. Recipe là tập cấu hình train; có đối chiếu paper/Ultralytics và lỗi thực tế, không gọi là tái lập nguyên paper.

### Lời trình bày gợi ý

> B0 bắt đầu bằng pilot 47 ảnh để kiểm toàn bộ đường từ dữ liệu đến huấn luyện và đánh giá. Kết quả nhỏ này kém nên bước tiếp theo là sửa nhãn và mở rộng dữ liệu, thay vì chỉ tăng epoch. Sau đó bổ sung normal và thử YOLOv8s ở kích thước 960 khi thấy vùng nhỏ thường bị bỏ sót. Âm khó vẫn lấy từ nguồn normal có căn cứ. Cuối cùng chuyển train lên Kaggle. Các mốc có dữ liệu và split khác nhau, nên cần tách phép so để không hiểu nhầm mọi thay đổi đều làm chất lượng tăng.

## Slide 06 — IoU, precision, recall và F1

### Ghi chú ngắn

- **IoU = diện tích giao / diện tích hợp:** đo độ khớp hộp dự đoán với hộp thật. Ví dụ hình minh họa IoU 0,60 đạt yêu cầu 0,50 nhưng không đạt yêu cầu 0,75; ngưỡng cao hơn đòi khớp sát hơn.
- **TP/FP/FN:** hộp ghép đúng/hộp sai/vùng thật bị bỏ sót. Ghép cùng lớp, một–một, trong phạm vi nhãn đã kiểm; B0 đang đếm bbox, chưa đếm sự kiện.
- **Precision = TP/(TP+FP):** theo dõi báo nhầm. **Recall = TP/(TP+FN):** theo dõi bỏ sót. **F1 = 2PR/(P+R):** trung bình điều hòa, cân bằng hai phía nhưng không thay thế việc xem từng chỉ số.
- Confidence là ngưỡng giữ prediction; IoU là ngưỡng kiểm độ khớp vị trí. Hai ngưỡng có vai trò khác nhau, không thay cho nhau.

### Lời trình bày gợi ý

> Trước khi đọc kết quả, cần phân biệt các metric. IoU kiểm hộp dự đoán khớp vị trí đến đâu; cùng một hộp có IoU 0,60 sẽ qua yêu cầu 0,50 nhưng chưa qua 0,75. Sau khi ghép hộp, precision cho biết trong các hộp model báo có bao nhiêu hộp đúng; recall cho biết model tìm được bao nhiêu vùng thật. Chúng ta quan tâm recall để hạn chế bỏ sót va chạm và precision để hạn chế báo nhầm. F1 tổng hợp hai phía, nhưng vẫn cần đọc từng chỉ số thay vì chỉ nhìn một con số.

## Slide 07 — AP và mAP — đọc cả đường precision–recall

### Ghi chú ngắn

- **AP — Average Precision:** diện tích dưới đường precision–recall khi quét confidence tại một ngưỡng IoU; không phải cộng mọi precision thô rồi chia số lượng.
- **mAP — mean Average Precision:** trung bình AP các lớp. B0 có một lớp accident, nên mAP50 = AP50; mAP50–95 tiếp tục trung bình ở mười ngưỡng IoU 0,50–0,95, bước 0,05.
- Theo dõi **mAP50** để đánh giá khả năng phát hiện/định vị ở điều kiện khớp thông dụng và **mAP50–95** để xem chất lượng khi đòi bbox sát hơn. Đây không phải accuracy hay recall sự kiện.
- Ảnh trái là [PR gốc của V11](../outputs/training/b0_s960_sgd_kaggle_v3/metrics_val/BoxPR_curve.png); nhãn 0,706 là làm tròn. Code metric đã đối chiếu với Ultralytics 8.4.178 đang cài; bản này chọn best theo mAP50–95.

### Lời trình bày gợi ý

> Một ngưỡng confidence chỉ tạo một điểm precision và recall. Khi thay ngưỡng, ta được cả đường PR như ảnh gốc bên trái; AP tóm tắt đường này bằng diện tích bên dưới. mAP là trung bình AP qua các lớp, nhưng B0 chỉ có lớp accident. mAP50 xét IoU 0,50, còn mAP50–95 xét thêm những mức khớp chặt đến 0,95. Vì vậy cần xem cả hai để biết model chỉ tìm gần đúng hay còn định vị tốt. Các số này đánh giá bbox ảnh, chưa cho biết hệ thống cảnh báo đúng bao nhiêu sự kiện.

## Slide 08 — Ảnh biểu đồ gốc local

### Ghi chú ngắn

- Ảnh lấy từ `training_summary/results.png` của [n640](../outputs/training/b0_normal_expanded_v1/training_summary/results.png) và [s960](../outputs/training/b0_s960_v1/training_summary/results.png), cùng 217 ảnh val. Chỉ hiển thị hai ô mAP phía dưới bên phải; không sửa đường, số, màu hoặc trục, không đưa các loss lên slide.
- Trục ngang là epoch; đường xanh là kết quả, nét cam là đường làm mượt của công cụ. Mỗi ô tự co giãn trục dọc, nên không so độ cao/chênh lệch thị giác như cùng một thang cố định.
- Đây là diễn biến theo epoch, khác việc đánh giá lại `best.pt`. Slide sau dùng cột 0–100% từ kết quả best để so rõ hơn; panel 97 val ở slide sau là protocol khác, không phải nguồn hai ảnh này.

### Lời trình bày gợi ý

> Đây là ảnh biểu đồ thật do công cụ train xuất, trước khi tổng hợp lại thành các cột so sánh. Hai ảnh thuộc n640 và s960 trên cùng nhóm 217 ảnh validation. Chỉ hai ô mAP được đưa lên để tập trung vào chất lượng phát hiện; các đường và trục vẫn giữ nguyên. Cần lưu ý trục dọc của từng ô tự co giãn. Các ảnh cho thấy diễn biến học, còn slide tiếp theo sẽ đặt kết quả checkpoint best trên cùng thang phần trăm để đọc mức chênh dễ hơn.

## Slide 09 — Kết quả local

### Ghi chú ngắn

- **LR/epoch:** learning rate là bước cập nhật trọng số; epoch là một lượt qua tập train. Loss là sai số tối ưu khi học, không phải mAP.
- **mAP50:** AP tính từ đường precision–recall khi quét confidence, ghép bbox tại IoU ≥ 0,5; B0 có một lớp accident. Không phải accuracy theo ảnh/video.
- **Val 97:** LR 0,01/60 epoch đạt 60,63%; LR 0,001/48 đạt 66,86%; LR 0,001/60 đạt 64,94%. Run có khác loader/resume nên chưa cô lập tác động số epoch.
- **Val 217:** n640 đạt 64,68%, s960 đạt 68,60%. Đổi đồng thời nhiều yếu tố; chỉ so trong cùng panel, không so hai tập val như cùng một bài thi.

### Lời trình bày gợi ý

> Hai biểu đồ dùng hai tập validation khác nhau nên chỉ so các cột trong cùng nhóm. Ở nhóm 97 ảnh, giảm learning rate có kết quả tốt hơn, nhưng chạy đủ 60 epoch không vượt run 48 epoch. Vì hai run còn khác cách nạp dữ liệu và resume nên chưa kết luận riêng về early stopping. Ở nhóm 217 ảnh, s960 tăng mAP50 từ 64,68 lên 68,60%, nhưng đã đổi cả quy mô model, kích thước ảnh và augmentation. Điểm chính là cần đo trên cùng điều kiện và không chỉ nhìn loss train giảm.

## Slide 10 — Ảnh PR gốc Kaggle — V10 và V11

### Ghi chú ngắn

- Dùng ảnh `metrics_val/BoxPR_curve.png` thật của [V10](../outputs/training/b0_s960_adamw_kaggle_v2/metrics_val/BoxPR_curve.png) và [V11](../outputs/training/b0_s960_sgd_kaggle_v3/metrics_val/BoxPR_curve.png), xuất khi đánh giá best trên cùng 307 val, không vẽ lại hoặc đổi màu.
- Trục ngang recall, trục dọc precision; mỗi điểm ứng với confidence khác nhau, IoU ghép giữ ở 0,50. Không lấy điểm tùy ý trên đường này làm P/R tại confidence 0,25.
- Chú giải ảnh làm tròn AP50 thành 0,679 và 0,706; số chi tiết đánh giá lại là khoảng 67,85% và 70,64%. Một lớp accident nên hai đường class/all classes gần như trùng nhau.
- Ảnh PR không chứa mAP50–95; số đó ở bảng đánh giá. V9 chỉ có metadata đã lấy chọn lọc, nên không dựng ảnh gốc giả cho V9. Các slide kế tách so mAP và so P/R/F1 cố định.

### Lời trình bày gợi ý

> Đây là hai ảnh PR gốc khi đánh giá checkpoint best của V10 và V11 trên cùng validation. Chú giải cho thấy AP50 của V11 cao hơn, nhưng đây là kết quả xét cả đường khi thay confidence, chưa phải một ngưỡng vận hành duy nhất. Ảnh được giữ nguyên để có thể đối chiếu với nguồn thật. Tiếp theo, các cột sẽ tổng hợp mAP từ báo cáo đánh giá; sau đó mới so precision, recall và F1 tại cùng confidence 0,25 để thấy rõ phần được và mất của mỗi model.

## Slide 11 — So sánh Kaggle

### Ghi chú ngắn

- V9/V10/V11 là **version notebook**, vẫn dùng YOLOv8s; cùng 2.681 train/307 val và trọng số khởi đầu. Kaggle dùng GPU miễn phí, gói PRIVATE để giảm tải laptop.
- SGD/AdamW là optimizer cập nhật trọng số; batch là số ảnh mỗi mini-batch. FP32 dùng số thực 32 bit; AMP (*Automatic Mixed Precision*) phối hợp độ chính xác số để tiết kiệm tài nguyên.
- mAP50/mAP50–95: **V9 69,79/55,87%; V10 67,85/52,63%; V11 70,64/56,80%**. mAP50–95 trung bình AP ở IoU 0,50–0,95, bước 0,05, yêu cầu bbox khớp chặt hơn.
- Best ở epoch **1/52/3**, chạy thực **11/60/50**. `best.pt` chọn theo mAP50–95; `last.pt` là cuối run. V10→V11 chỉ đổi optimizer trong tham số train; vẫn một seed, val đã dùng nhiều lần.

### Lời trình bày gợi ý

> Ba version Kaggle dùng cùng dữ liệu và trọng số khởi đầu. V11 đạt mAP50 70,64% và mAP50–95 56,80%, cao nhất trong nhóm này. Chỉ số thứ hai thấp hơn vì còn kiểm các ngưỡng IoU khắt khe hơn. Best của V11 ở epoch 3, không phải epoch cuối. V10 và V11 giữ các tham số train khác để đối chứng optimizer. Đây là kết quả validation hiện có; GPU cloud giúp chạy thuận tiện hơn nhưng không tự bảo đảm khả năng tổng quát hóa hoặc chất lượng cảnh báo sự kiện.

## Slide 12 — Đánh đổi precision và recall

### Ghi chú ngắn

- Cùng 307 val, confidence 0,25, IoU ghép 0,5. **TP:** hộp ghép đúng; **FP:** hộp sai; **FN:** vùng thật bị bỏ sót.
- **Precision = TP/(TP+FP):** tỷ lệ đúng trong các hộp dự đoán. **Recall = TP/(TP+FN):** tỷ lệ vùng thật tìm được. **F1 = 2PR/(P+R):** trung bình điều hòa hai phía.
- V10→V11: TP **57→64**, FP **22→40**, FN **34→27**. P/R/F1 đổi từ **72,15/62,64/67,06%** sang **61,54/70,33/65,64%**.
- Ảnh âm có FP là **2→8/216**, khác tổng số bbox FP. mAP quét nhiều confidence, còn P/R/F1 trên slide dùng ngưỡng cố định; FP bbox chưa là cảnh báo sai/sự kiện/giờ.

### Lời trình bày gợi ý

> Dù mAP tăng, V11 chưa tốt hơn về mọi mặt. Ở cùng ngưỡng, số vùng thật tìm đúng tăng từ 57 lên 64, nhưng hộp sai cũng tăng từ 22 lên 40. Vì thế recall tăng, trong khi precision và F1 giảm so với V10. Đây là đánh đổi giữa bắt được nhiều hơn và báo nhầm nhiều hơn. Các con số đang đếm bbox trên ảnh; để biết hệ thống gây bao nhiêu cảnh báo sai trên video còn phải gộp tín hiệu theo sự kiện và đánh giá bằng cùng một protocol.

## Slide 13 — Đường học và B1

### Ghi chú ngắn

- Đường trái lấy `results.csv` V11: best epoch 3, kết thúc 50. Chính sách dừng trễ bắt đầu mốc 25, patience 25; không mặc định cộng best 3 + 25 để suy mốc dừng.
- B1 bên phải dùng **s960 cũ/conf 0,27**, không phải V11. Đã chạy 12 chuỗi/4.845 frame; biểu đồ chỉ lấy **1.296 frame normal val**.
- **3-of-5:** ít nhất ba trong năm frame gần nhất vượt ngưỡng. **EMA:** `e_t = 0,3 × score_t + 0,7 × e_(t-1)`, khởi tạo 0. Chỉ dùng hiện tại/quá khứ, reset khi đổi nguồn hoặc gặp gap.
- **Bout:** một đoạn ON liên tiếp. B0 có **31**, 3-of-5 còn **11**, EMA **13**; bớt chớp nhưng chưa đo recall/độ trễ sự kiện. Làm mượt cũng có thể bỏ tín hiệu thật ngắn hoặc giữ ON lâu.

### Lời trình bày gợi ý

> V11 có checkpoint tốt nhất khá sớm; chạy thêm chưa giúp validation vượt mốc đó. Bên phải là chẩn đoán B1 đã thực hiện với checkpoint s960 cũ. Trên nhóm normal validation, số đoạn tín hiệu bật liên tiếp giảm từ 31 xuống 11 với 3-of-5 hoặc 13 với EMA. Điều này cho thấy tín hiệu bớt chớp, nhưng chưa đủ kết luận cảnh báo sự kiện tốt hơn. Cần kiểm cả va chạm thật và độ trễ, bởi một bộ lọc quá mạnh cũng có thể làm mất tín hiệu cần phát hiện.

## Slide 14 — Trạng thái và bước tiếp theo

### Ghi chú ngắn

- **Đã có:** B0 ảnh, kết quả V11 và chẩn đoán B1. **Chưa đủ:** benchmark sự kiện, B2/T0/GRU; không coi 70% mAP là hoàn thành hệ thống.
- **Evaluator/protocol:** chương trình và quy tắc đánh giá chung; chốt onset/end, tức mốc bắt đầu/kết thúc, ghép cảnh báo với sự kiện và gộp cảnh báo lặp trước khi đo độc lập.
- **Thứ tự đề xuất:** giữ checkpoint/config mốc, rà FP/FN → hoàn thiện dữ liệu/evaluator event → so B0/B1 → B2, MLP, GRU khi đủ nhãn. V11 chưa tự thay checkpoint đang khóa.
- **RQ — Research Question:** cần trả lời lợi ích giảm báo sai ở recall tương đương và chi phí vận hành. Còn thiếu timing CADP, bằng chứng độc lập camera và test event mới; FPS trình chiếu không thay FPS nguồn.

### Lời trình bày gợi ý

> Hiện project đã có detector ảnh và một bước lọc thời gian chạy được. Phần cần ưu tiên tiếp theo là làm phép đánh giá sự kiện đáng tin: xác định thế nào là bắt đúng một va chạm, ghép và gộp cảnh báo ra sao, rồi đo cả bỏ sót, báo sai và độ trễ. Sau khi so B0 với B1 mới có cơ sở phát triển chuyển động, MLP hoặc GRU. Đây là hướng đề xuất; hiện vẫn tạm dừng mở thí nghiệm mới để rà soát. Kết quả 70,64% mAP50 là một mốc B0, chưa thay kết luận cho toàn hệ thống.

Đọc sâu và đối chiếu bằng chứng: [báo cáo tổng hợp](BAO_CAO_TIEN_DO_DACN.md). Tra thuật ngữ ở [GLOSSARY](../reference/GLOSSARY.md), nguồn ở [LITERATURE_REVIEW](../reference/LITERATURE_REVIEW.md), trạng thái ở [progress/README.md](../progress/README.md).
