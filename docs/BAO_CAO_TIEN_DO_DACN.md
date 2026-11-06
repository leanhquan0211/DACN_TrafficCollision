# BÁO CÁO TỔNG HỢP TIẾN ĐỘ ĐỒ ÁN CHUYÊN NGÀNH

**Đề tài:** Phát hiện và cảnh báo va chạm giao thông từ video bằng theo dõi phương tiện và phân tích chuyển động theo thời gian.  
**Project:** DACN_TrafficCollision.  
**Ngày đối chiếu:** 04/11/2026, múi giờ Asia/Bangkok.
**Phạm vi hồ sơ:** lộ trình ban đầu và hoạt động có bằng chứng từ 16/10–04/11/2026. Các nhận định ghi mốc 31/10 được giữ như lịch sử; phần cập nhật V12/dashboard dùng artifact đã kiểm ngày 04/11. Báo cáo này bổ sung tài liệu trình bày, không thay thế nhật ký hằng ngày.

## Tổng quan ngắn

Đồ án hướng tới nhận biết va chạm xe–xe từ camera giám sát và tạo cảnh báo có thời điểm, vị trí cùng bằng chứng video. Quá trình thực hiện đã đi từ thử phát hiện/theo dõi xe, kiểm dữ liệu và nhãn, đến huấn luyện detector ảnh vùng tai nạn B0. Phần B1 lọc điểm theo thời gian đã có code và kết quả chẩn đoán; các bước luật chuyển động B2, mạng MLP T0 và GRU B3/T1 chưa được triển khai thành baseline hoàn chỉnh.

Run gần nhất, SGD learning rate giảm một nửa trên Kaggle **Version 12**, đã hoàn tất 50 epoch và được tải/kiểm về máy. Checkpoint best epoch 3 đánh giá lại trên cùng 307 ảnh validation: mAP50 **70,63%**, mAP50–95 **56,10%**. Tại confidence 0,25 và IoU ghép bbox 0,5: **65 TP, 37 FP, 26 FN**, precision **63,73%**, recall **71,43%**, F1 **67,36%**. So với Version 11, F1 tại điểm vận hành này tăng nhẹ, còn mAP50 gần ngang và mAP50–95 giảm. Đây là kết quả pilot ảnh trên validation đã dùng nhiều lần, chưa là phép đo phát hiện sự kiện trên test độc lập hoặc căn cứ tự đổi checkpoint vận hành.

Đóng góp thực tế đến thời điểm báo cáo gồm quy trình giữ nguồn gốc dữ liệu, phân biệt nhãn tác giả/nhãn dẫn xuất/xác nhận thủ công, chia tập theo nhóm nguồn, huấn luyện có config và checkpoint, phân tích lỗi ảnh/video, cùng quy trình chạy Kaggle riêng tư và tải kết quả có kiểm hash. Dashboard local đã có một lựa chọn run thống nhất: xem log/trạng thái Kaggle trước khi fetch và metric/curve/checkpoint từ artifact local sau khi fetch; giao diện chỉ đọc, không điều khiển train. Những sửa chữa đáng chú ý là loại dữ liệu trùng xuyên split, thu hồi run sử dụng nhãn âm chưa đủ căn cứ, xử lý lỗi RAM và phân biệt resume với khởi tạo thí nghiệm mới.

Ưu tiên tiếp theo được đề xuất là cố định detector phục vụ phát triển, hoàn thiện dữ liệu và evaluator sự kiện, rồi so B0/B1 trước khi xây B2/T0/GRU. Tối ưu thêm B0 chỉ nên mở khi có giả thuyết cụ thể từ lỗi hoặc có nhãn công khai phù hợp. Chưa có căn cứ xem 70% mAP50 là chuẩn nghiệm thu bắt buộc hoặc xem thêm epoch là biện pháp chắc chắn cải thiện chất lượng.

## A. Tổng quan bài toán và phạm vi

### A.1. Vấn đề cần giải quyết

Camera giám sát cung cấp chuỗi hình ảnh giao thông liên tục, nhưng việc quan sát được phương tiện chưa đồng nghĩa nhận biết được tai nạn. Hai xe có thể đứng sát nhau, bị che do phối cảnh, đi qua cùng vị trí ảnh ở thời điểm khác nhau hoặc phanh tránh nhau mà chưa tiếp xúc. Một cảnh có nhiều xe cũng không mặc định nguy hiểm. Hệ thống cần phân biệt những tình huống này với va chạm đang hoặc vừa xảy ra.

Đầu vào mục tiêu là video từ một camera CCTV, viết đầy đủ là Closed-Circuit Television, có thời gian hoặc quan hệ thứ tự frame được kiểm chứng. Phạm vi nghiên cứu tập trung va chạm xe–xe từ góc nhìn giám sát; dự báo trước tai nạn, đa camera và hiểu mọi loại bất thường giao thông là các bài toán khác. Đầu ra mục tiêu là sự kiện với mã, thời điểm cảnh báo, vị trí, độ tin cậy và ảnh/clip bằng chứng; nếu dùng tracking thì có thêm ID tạm của các xe liên quan.

Các từ “nhẹ” và “thời gian thực” trong định hướng là mục tiêu cần đo trên toàn pipeline. Tốc độ detector riêng hoặc tốc độ xử lý file offline chưa chứng minh hệ thống có thể tiếp nhận video liên tục, không tích hàng đợi và phát cảnh báo đúng thời hạn.

### A.2. Bốn nhiệm vụ cần phân biệt

| Nhiệm vụ | Đầu ra | Ý nghĩa trong đồ án |
| --- | --- | --- |
| Phát hiện phương tiện | Bbox, lớp car/bus/truck và confidence | Cung cấp quan sát xe; pretrained COCO không tự có lớp accident. |
| Theo dõi phương tiện | Bbox qua thời gian và track ID | Nối quan sát thành quỹ đạo; ID chỉ tồn tại tạm trong video. |
| Phát hiện vùng tai nạn B0 | Bbox lớp accident trên một ảnh | Học dấu hiệu thị giác của vùng sự cố; cần nhãn vùng riêng. |
| Xác định sự kiện va chạm | Một sự kiện theo thời gian và chính sách cảnh báo | Cần nhãn onset/end, ghép event, chống lặp và đo cảnh báo sai/độ trễ. |

Một video có bbox/ID chứng minh pipeline perception đọc và ghi được dữ liệu, chưa chứng minh phân loại va chạm. Tương tự, nhiều frame liên tiếp có accident score cao chưa tự trở thành nhiều tai nạn hoặc một cảnh báo đúng: còn cần quy tắc sự kiện và ground truth phù hợp.

### A.3. Câu hỏi nghiên cứu và lý do giới hạn phạm vi

RQ1 trong lộ trình đặt câu hỏi liệu quỹ đạo và diễn biến theo thời gian có giảm cảnh báo sai trên cảnh khó ở mức recall tương đương với detector ảnh cộng lọc đơn giản hay không. RQ2 xét lợi ích đó có đáng với chi phí FPS, độ trễ và VRAM trên laptop hay không. Đây là hai câu hỏi chưa được trả lời bằng thực nghiệm đầy đủ.

CCTV được chọn vì phù hợp bối cảnh giám sát đường và cho phép nghiên cứu tương tác giữa nhiều xe trong một khung nhìn. Việc giới hạn một camera và va chạm xe–xe giúp định nghĩa nhãn, nguồn dữ liệu và evaluator rõ hơn. Cách tiếp cận tuần tự từ baseline đơn giản đến motion verifier giúp kiểm tra thành phần nào tạo ra lợi ích, phù hợp ngân sách GPU/RAM ban đầu. Đây là lựa chọn thiết kế trong workbook, không phải kết luận một paper duy nhất đã chứng minh kiến trúc dự kiến là tối ưu.

## B. Cơ sở nghiên cứu và căn cứ lựa chọn

### B.1. Nguyên tắc sử dụng tài liệu

Workbook đã liệt kê các hướng YOLOv8, RARE, Graph(Graph), CRASH, Transformer, AcciDetect và CADP. Những nguồn STTAD, TAD, ACCIDENT, motion rules và tối ưu được bổ sung trong quá trình thực hiện. Thứ tự này có ý nghĩa: nguồn đã xuất hiện trong lộ trình chỉ cho thấy đã được dự kiến tham khảo; mức đã đọc, khả năng tải nhãn và mức áp dụng phải kiểm riêng.

Từ 24/10, đường triển khai được giới hạn vào paper, mã và dữ liệu công khai truy cập được. Nguồn yêu cầu xin riêng không còn được xem là điều kiện phải chờ. Từ 26/10, quyết định dữ liệu/train/metric phải ghi nguồn sơ cấp, phần kế thừa, phần điều chỉnh và phép kiểm. Những công thức được bổ sung sau khi có kết quả chỉ được dùng để đối chiếu, không được ghi hồi tố thành động cơ đã có từ đầu.

### B.2. Các nghiên cứu liên quan trực tiếp

| Nguồn và mức kiểm | Nội dung liên quan | Quyết định và giới hạn áp dụng |
| --- | --- | --- |
| Minh và cộng sự, YOLOv8 accident, 2025 [R1]; abstract publisher đọc được, PDF vẫn 403 | Khảo sát detector YOLOv8 n/s/m cho ảnh tai nạn. | Căn cứ hướng baseline ảnh trong workbook; chưa đủ toàn văn/dữ liệu để gọi là tái lập. |
| Xu và cộng sự, STTAD, 2025 [R2]; mục III/V và bảng III | Định vị vùng xảy ra sự kiện bằng kết hợp không gian–thời gian. | Làm rõ nghĩa vùng accident từ 24/10; phần ví dụ public quá thưa để thay toàn bộ dữ liệu B0. |
| Ning và cộng sự, TP-YOLOv8, 2025 [R3]; toàn văn tác giả | Detector ảnh tai nạn, sửa cấu trúc xử lý mục tiêu nhỏ; recipe SGD. | Căn cứ mở rộng dữ liệu và đối chiếu công thức từ 26/10; kiến trúc và TAT chưa được tái lập. |
| Picek và cộng sự, ACCIDENT, 2026 [R4]; paper, metadata và media đã kiểm | Benchmark CCTV thời điểm impact, vị trí và loại va chạm. | Nguồn dương chính của các release lớn; chỉ dùng vùng tại frame impact đã đối chiếu. |
| Ijjina và cộng sự, 2019 [R5]; phương pháp và kết quả | Kết hợp detection/tracking với giao quỹ đạo và biến thiên chuyển động. | Căn cứ motion rules B2; cần kiểm cửa sổ nhìn sau và ngưỡng theo camera. |
| Ghahremannezhad và cộng sự, 2022 [R6]; phương pháp/thực nghiệm | YOLOv4, tracking và xung đột quỹ đạo ở giao lộ. | Tham khảo chọn cặp, hướng và tốc độ; target có cả near-accident, khác collision thuần. |
| Song và Lee, RARE, 2025 [R7]; paper/repo | Tái dùng feature detector, attention và GRU cho anticipation DAD/CCD. | Tham khảo cách dùng chuỗi tiết kiệm; không chuyển task sang dự báo từ dashcam. |
| ByteTrack [R8]; paper và tích hợp Ultralytics | Ghép detection với tracklet, kể cả một phần detection điểm thấp. | Tracker khởi đầu vì có mã/tích hợp và pipeline đã chạy; chưa có metric GT tracking. |

STTAD mô tả vùng sự kiện, còn nhãn CADP gốc là bbox từng đối tượng cùng thuộc tính Colliding. Vì vậy, từ 24/10, việc sử dụng vùng tác giả public được ưu tiên hơn biến hộp từng xe thành ground truth tai nạn. STFN của STTAD dùng 16 frame 224, AdamW và nhánh 2D+3D; kết quả mAP@50 42,5% trên test 12 lớp không là điểm so trực tiếp cho B0 một lớp trên ảnh impact. Lựa chọn kế thừa ở đây là khái niệm/nhãn; kiến trúc STFN chưa được triển khai.

TP-YOLOv8 công bố TAT 8.392 ảnh và recipe SGD 0,01, momentum 0,937, batch 16, 640, tối đa 300 epoch, dừng sau 50 epoch không cải thiện, không pretrained, trên A40 48 GB. Đồ án tham khảo hướng detector và recipe nhưng dùng YOLOv8 pretrained với ngân sách khác; không áp nguyên batch/epoch hoặc nhận là đã tái lập. Link TAT chưa tải được ở mốc quyết định, nên ACCIDENT public được chọn để mở rộng nhãn thay vì giả định TAT đã sẵn có.

ACCIDENT cung cấp tình huống CCTV đa dạng, nhưng metric chính thức định vị điểm impact và thời gian theo dung sai. Metadata v9 thực lưu trong project có tâm cùng các cột x1/y1/x2/y2. B0 sử dụng vùng metadata tại đúng frame đã kiểm; đây là cách điều chỉnh cho detector ảnh, không phải chạy đúng benchmark tác giả hoặc có annotation tracking đầy đủ. Khả năng giao nguồn với CADP/TAD tiếp tục là lý do phải kiểm trùng và nhóm cảnh.

Các hướng motion của Ijjina và Ghahremannezhad giải thích lý do cần nhiều dấu hiệu tương tác. Độ chồng hộp chỉ là bước tạo nghi vấn. Paper thứ nhất có phép tính cần quan sát sau giao nhau; paper thứ hai dùng hiệu chuẩn homography và xét cả conflict gần tai nạn. Do chưa có hiệu chuẩn/timing đáng tin cho mọi nguồn, kế hoạch của đồ án ưu tiên đặc trưng ảnh với đơn vị rõ và xử lý causal, nghĩa là chỉ dùng thông tin hiện tại/quá khứ.

RARE và các hướng graph/Transformer trong workbook cho thấy mô hình hóa quan hệ và thời gian đã có nghiên cứu trước. Chúng hỗ trợ thiết kế đối chứng T0–GRU và nhu cầu đo toàn pipeline, chưa tạo căn cứ tuyên bố tính mới từ việc ghép YOLO với GRU. Graph(Graph), CRASH và AcciDetect được giữ trong literature review; chưa có thực nghiệm của đồ án với những kiến trúc này, không dùng số AP dashcam để đặt chuẩn cho CCTV.

### B.3. Lý do chọn dữ liệu, mô hình và công cụ

| Lựa chọn | Căn cứ và mục đích | Cách kiểm và giới hạn |
| --- | --- | --- |
| CADP 001407 | CCTV, có VATIC và một cặp ảnh/nhãn đối chiếu được; phù hợp debug mapping và interval. | Một sự kiện; FPS nguồn chưa xác minh, không làm benchmark độc lập. |
| ACCIDENT real v9 | Có clip công khai, frame impact và vùng metadata truy được; phù hợp mở rộng dương B0. | Giữ bốn nhóm loại xe–xe; loại lỗi/trùng/ngoài phạm vi; nhãn thưa một frame. |
| STTAD public examples | Có vùng sự kiện theo paper và TXT tương ứng trong một phần dữ liệu. | Kiểm cặp path/pixel/biên; thiếu TXT là unknown. Không dùng toàn paper như dữ liệu đã tải. |
| UA-DETRAC chọn lọc | Chuỗi xe rõ, có số frame nguồn, người dùng đã xem ba chuỗi không va chạm. | Dùng âm/debug; ba chuỗi gom một nhóm cảnh bảo thủ, không phải ba camera độc lập. |
| TAD normal | Có nhãn normal cấp clip public; phù hợp bổ sung âm và lỗi cảnh bình thường. | Nhãn từ tác giả, không phải xác nhận người dùng; không có bbox accident trong ZIP đã kiểm. |
| YOLOv8n rồi YOLOv8s | n là mức thử gọn trong lộ trình; lỗi vùng nhỏ tạo lý do thử s và 960. | Giữ API/version để tái lập; n→s đồng thời đổi độ phân giải/augmentation nên không tách được nguyên nhân. |
| ByteTrack | Có phương pháp public [R8], tích hợp trực tiếp và pipeline sẵn chạy. | Cần GT để đo ID switch/IDF1/HOTA; chưa có bằng chứng cần đổi sang tracker khác. |
| PyTorch và Ultralytics [R16, R18] | Huấn luyện deep learning có pretrained, loss/evaluator và tracking dùng chung. | Pin phiên bản, lưu config thực; không dùng default mới từ tài liệu thay recipe cũ. |
| OpenCV và FFmpeg/FFprobe | Đọc/ghi media, kiểm frame/kích thước và đối chiếu presentation timestamp. | PTS file phát hành không mặc định là thời gian ghi hình gốc; kiểm đọc lại video sau xuất. |
| Kaggle PRIVATE miễn phí [R17] | Giảm tải laptop sau giới hạn RAM/VRAM; tái dùng dataset và notebook có API. | Kiểm GPU/quota thật; cloud là lựa chọn tài nguyên, không tạo dữ liệu tốt hơn hay bảo đảm tăng mAP. |
| Git, JSON/CSV manifest và SHA-256 | Tách code/hồ sơ nhỏ khỏi media; truy nguồn và phát hiện file thay đổi. | Hash bằng nhau chứng minh byte bằng nhau, hash khác không chứng minh camera/sự kiện độc lập. |

Nguồn SO-TAD đã được đọc danh mục nhưng gói lớn chủ yếu cung cấp video/nhãn khác bbox, nên không tải 27 GB để giải quyết thiếu nhãn B0. Gói TU-DAT đã kiểm có hộp moving_object và phân tích tự động; chúng không được đổi thành ground truth vùng tai nạn. VLM, graph lớn hoặc mô hình mới hơn chưa được chọn vì hiện còn thiếu protocol/nhãn và phép so cần thiết. Đây là loại theo mức phù hợp/khả năng tái lập của nguồn đã kiểm, không kết luận các hướng đó kém về học thuật.

SGD/AdamW và lịch cosine được chọn như các giả thuyết tối ưu có đối chiếu log, không là “cách train theo một paper” duy nhất. AdamW [R9] và SGDR [R10] là nguồn bổ sung ngày 30/10 để giải thích optimizer/schedule; không được gán thành lý do ban đầu chọn YOLOv8 từ workbook. Cosine của các run Kaggle mới không có warm restart như toàn bộ SGDR.

## C. Phân rã mục tiêu và trạng thái từng baseline

### C.1. Bảng tổng hợp

| Baseline | Mục tiêu và đầu ra | Phụ thuộc chính | Trạng thái đã kiểm |
| --- | --- | --- | --- |
| B0 | Detector ảnh, bbox/score accident để làm đối chứng thị giác. | Ảnh sạch, vùng GT có nghĩa thống nhất, split nguồn và evaluator bbox. | Có nhiều run, checkpoint, validation và phân tích lỗi; pilot ảnh đã chạy, benchmark event còn thiếu. |
| B1 | Lọc score B0 theo thời gian bằng k-of-N/EMA. | Chuỗi frame có thứ tự, reset, nhãn temporal và evaluator sự kiện. | Code causal và chẩn đoán 12 chuỗi/4.845 frame đã có; chưa đo event F1/delay. |
| B2 | Vehicle tracking, chọn cặp và luật chuyển động để cho score va chạm. | Tracks, quality/missing mask, timing, nhãn interaction/event. | Perception/tracking đã chạy; candidate/features/rules/alert chưa hoàn chỉnh. |
| T0 | MLP trên đặc trưng hiện tại, đối chứng learned verifier đơn giản. | Cùng candidate/features và split với B3. | Chưa xây dataset feature hoặc train MLP. |
| B3/T1 | GRU một chiều học chuỗi đặc trưng quá khứ. | T0/B2, window labels, scaler train-only, evaluator chung. | Chưa triển khai/huấn luyện; B3 và T1 là cùng một phương án. |

### C.2. B0 — baseline ảnh vùng tai nạn

B0 nhận ảnh sạch và trả một hoặc nhiều bbox accident cùng confidence. Ảnh dương cần vùng phù hợp và mapping chắc chắn; ảnh âm cần căn cứ phủ đúng phạm vi được xét. Lý do bắt đầu từ B0 là có một đối chứng có thể train/đo bằng nhãn công khai trước khi thêm tracking và xác minh chuyển động. Mỗi run lưu khởi tạo, dữ liệu, seed, thông số và kết quả để biết thay đổi tác động ra sao.

Ở mức công cụ và pilot ảnh, B0 đã có đủ đường từ nhãn đến checkpoint, prediction và thống kê FP/FN. Ở mức mục tiêu cuối, score ảnh vẫn phải đi qua chính sách event và evaluator chung. Điều kiện tiếp tục không phải vượt một con số mAP tùy ý mà là có detector tái lập được, hiểu lỗi và khóa vai trò của checkpoint trong phép so B1/B2.

### C.3. B1 — đối chứng lọc đơn giản theo thời gian

B1 nhận score cảnh B0 theo frame. Với k-of-N, trạng thái bật khi đủ số frame vượt ngưỡng trong cửa sổ quá khứ; cấu hình hiện có là 3-of-5, chờ đủ năm frame. EMA là Exponential Moving Average, trung bình trượt mũ: score hiện tại được trộn với trạng thái cũ, ở đây alpha 0,3 và khởi tạo 0. Công thức tham khảo NIST [R11], còn k/N/alpha là lựa chọn chẩn đoán của đồ án.

Bộ lọc được reset khi đổi video hoặc mất frame, tránh mang trạng thái từ cảnh trước sang cảnh sau. Lý do có B1 là kiểm tra mức lợi ích đạt được bằng một phương án rẻ trước khi dùng mô hình học chuỗi. Code và replay đã có; điều kiện hoàn thành vẫn cần so cùng event matching, recall, cảnh báo sai và độ trễ. Một đoạn ON kéo dài do B0 sai có thể đi xuyên qua cả hai bộ lọc.

### C.4. B2 — quỹ đạo và luật chuyển động

B2 có nhánh perception riêng: YOLO phương tiện → ByteTrack → chọn cặp gần/tiếp cận trong vùng quan tâm ROI, tức Region of Interest → đặc trưng chuyển động → luật xác minh. Bbox accident của B0 và bbox xe trong nhánh này có ý nghĩa khác nhau. Candidate recall phải được đo vì cặp bị bỏ ngay bước lựa chọn không thể được verifier phía sau cứu lại.

Đặc trưng dự kiến gồm vị trí chuẩn hóa, chuyển vị, biến thiên hướng, khoảng cách tương đối, tuổi track và cờ thiếu quan sát. Nếu timing chưa tin cậy, chỉ được báo đơn vị theo frame hoặc đơn vị ảnh có căn cứ, không km/h. Đã chạy được tracking để xem video; chưa có cache track hoàn chỉnh cho motion, candidate generator, luật và đánh giá va chạm. Mất/đổi ID hiện là rủi ro kỹ thuật cần kiểm, chưa có thống kê GT cho phép gọi đó là nguyên nhân lỗi thực nghiệm.

### C.5. T0 — MLP làm đối chứng học đặc trưng hiện tại

MLP, viết đầy đủ Multi-Layer Perceptron, là mạng nhiều lớp kết nối đầy đủ. T0 dự kiến nhận cùng các biến của B2 tại thời điểm hiện tại và trả score cho cặp/cảnh. Nó giúp tách lợi ích của việc học trọng số đặc trưng khỏi lợi ích của bộ nhớ chuỗi. Không có T0, nếu GRU tốt hơn luật thì chưa biết cải thiện do temporal hay chỉ vì bộ phân loại có thể học.

T0 cần cache đặc trưng cùng nhãn và grouping rõ, chuẩn hóa chỉ fit trên train, ngưỡng chọn bằng validation. Hiện chưa có bộ dữ liệu đó hoặc checkpoint MLP. Điều kiện hoàn thành là có kết quả tái lập, cùng candidate, split và evaluator với B2/B3, không chỉ có mô hình chạy được trên dữ liệu minh họa.

### C.6. B3/T1 — GRU causal nhỏ

GRU, Gated Recurrent Unit, duy trì trạng thái qua chuỗi đặc trưng để biểu diễn diễn biến tương tác. B3/T1 là một phương án duy nhất trong lộ trình; cấu hình một lớp, hidden 32/64 chỉ là đề xuất ban đầu. Window kết thúc ở thời điểm cần quyết định và chỉ chứa quan sát quá khứ. Nhãn phải phản ánh collision đã xảy ra ở cuối window theo quy tắc detection, không gán toàn clip tai nạn là dương từ đầu.

Phương án này phụ thuộc chất lượng track, nhãn temporal/cặp xe và baseline T0/B2. Đánh giá cần cùng feature/candidate, nhiều seed khi khả thi và phép bỏ từng nhóm đặc trưng để tách tác động. Chưa có training hoặc bằng chứng giảm false alarm; do đó chưa thể trả lời RQ1/RQ2 hoặc tuyên bố GRU cần thiết.

## D. Chuẩn bị dữ liệu và điều chỉnh nhãn

### D.1. Từ mẫu thử đến ảnh sạch

Ban đầu project có ba MP4 để thử pipeline. Chúng chưa đủ nguồn/nhãn để tự đưa vào train. CADP [R13] sau đó có đúng cặp 1407.mp4/1407.txt; demo MP4 là bản đã vẽ bbox/ID/viền. Ảnh sạch được lấy từ ZIP chuỗi 001407, gồm 221 JPG 1280×720, số 0–220. Toàn bộ ảnh được kiểm giải mã; mapping được đối chiếu mã tác giả, khoảng frame, tọa độ và chín mốc trước/trong/sau Colliding. Không chỉ dựa vào tên 1407/001407.

VATIC có 4.641 dòng/21 ID; GT ID 0 Bus và ID 2 Car mang Colliding ở frame 96–130, gồm hai đầu. Xác nhận người dùng đã chốt đúng đối tượng và khoảng frame này. Đây là lớp review bên trên annotation tác giả, không xác nhận FPS nguồn. Video demo 25 FPS và video sạch trình chiếu 20 FPS không được dùng để suy onset/end theo giây. 35 hộp bao participant từng được xuất để minh họa vẫn là đề xuất dẫn xuất, không dùng làm GT vùng B0.

DETRAC-Images [R15] được kiểm danh mục trước khi lấy riêng ba chuỗi MVI_20011/20012/20032, tổng 2.037 ảnh. MP4 ghép giữ mapping nguồn và được đọc lại đủ frame. Người dùng xác nhận ba video đầy đủ không có va chạm; XML xe không được dùng thay xác nhận này. Hai chuỗi có dấu hiệu nối tiếp và các cảnh được gộp bảo thủ thành một nhóm; không đếm các MP4 cắt/detection/tracking là mẫu nguồn độc lập.

### D.2. Ba mức nhãn và cách dùng unknown

| Mức thông tin | Ví dụ đang có | Phạm vi được phép sử dụng |
| --- | --- | --- |
| Annotation tác giả | VATIC CADP; vùng STTAD; vùng impact ACCIDENT; normal cấp clip TAD | Giữ loại nhãn và đơn vị gốc; không chuyển nhãn clip thành bbox cho mọi frame. |
| Nhãn dẫn xuất có quy tắc | 30 frame ACCIDENT trước impact đã rà; chuyển xyxy sang YOLO; envelope CADP | Ghi quy tắc và người/mức kiểm; envelope không vào GT B0, chuyển format không tạo nhãn mới. |
| Xác nhận thủ công người dùng | CADP đúng xe/96–130; ba DETRAC âm toàn chuỗi | Gắn fingerprint và đúng phạm vi; không lan sang các clip chưa xem hoặc timing nguồn. |

Mẫu dương của B0 là ảnh có vùng accident phù hợp, mẫu âm là ảnh có căn cứ không có target trong phạm vi xét. Ảnh âm có thể có nhiều xe. Thiếu TXT không có nghĩa âm: 145 ảnh STTAD thiếu nhãn và các frame CADP ngoài phần đã xác nhận được giữ unknown. TXT YOLO rỗng chỉ xuất khi căn cứ âm đã hợp lệ; class ID 0 trong TXT dương là mã lớp accident, không là “âm”.

Chuẩn hóa gồm kiểm giải mã, kích thước, class, tọa độ hữu hạn/hợp biên, frame index và fingerprint. Với VATIC, outside/occluded/generated/ignore được giữ riêng; visible không đồng nghĩa không che khuất. Nếu nhãn chưa phủ toàn frame hoặc vùng chưa rõ, loại khỏi supervision hoặc ghi unknown. Việc kiểm format đạt không chứng minh nội dung nhãn đã được rà hết.

### D.3. Kiểm nguồn công khai và lựa chọn thực tế

STTAD public đã cung cấp bốn chuỗi phù hợp, 178 file đuôi ảnh, 176 giải mã được và 31 frame có bbox. Hai file lỗi được giữ raw và loại khỏi ảnh dùng; nhãn nguồn là xyxy pixel nên phải chuyển sang tọa độ YOLO chuẩn hóa. Đây là nguồn tham khảo/pool; **các run lớn gần đây có toàn bộ ảnh dương train từ ACCIDENT**, không phải toàn bộ STTAD hoặc dữ liệu của paper.

ACCIDENT bắt đầu bằng sáu clip kiểm mapping/PTS, rồi thêm batch nhỏ và sau đó tải 1.346 clip real phù hợp bộ lọc xe–xe. Khoảng 3,04 GiB media được lấy; 1.335 clip qua kiểm kỹ thuật, 11 bị loại. Sau các review/trùng/phạm vi, release verified giữ 1.320 ảnh impact. Một clip có một impact frame không có nghĩa mọi frame trong clip có bbox tai nạn. Bbox chuyển đổi vẫn liên kết clip/frame/metadata gốc.

TAD [R14] có nhãn normal cấp clip phù hợp nguồn âm. Danh mục ZIP đã kiểm có 404 MP4 và không thấy TXT/XML/JSON bbox; do đó không được dùng nhãn accident của thư mục để tạo bbox dương. Số 344 trong README nguồn không khớp 277+127 và danh mục 404, nên kiểm kê dựa trên member thực. SO-TAD/TU-DAT đã kiểm nhưng chưa hỗ trợ trực tiếp GT vùng B0 theo các gói tìm được; quyết định bỏ khỏi đường train hiện tại tránh tải lớn mà không giải quyết đúng nhãn còn thiếu.

### D.4. Các release có ý nghĩa

| Release hoặc mốc | Số ảnh | Train / val / test | Ý nghĩa và giới hạn |
| --- | ---: | --- | --- |
| Pilot ACCIDENT đầu | 47 | 30 / 9 / 8 | 17 impact + 30 âm cùng cảnh đã rà; 17 nhóm nguồn, rất nhỏ. |
| Scaled lịch sử, đã thu hồi | 2.436 | 2.225 / 97 / 114 lúc khóa | Có 1.084 âm trước impact chưa rà đầy đủ; không dùng checkpoint làm kết quả hợp lệ. |
| Verified pilot | 1.750 | 1.541 / 97 / 112 | 1.320 dương; 30 âm rà + 300 DETRAC + 100 TAD. |
| Normal-expanded | 2.170 | 1.841 / 217 / 112 | Thêm 300 train và 120 val normal; giữ 120 ảnh âm reserve ngoài train/val. |
| Hardneg | 2.680 | 2.261 / 307 / 112 | Thêm 420 train/90 val; có reserve âm mới 120 ảnh riêng. |
| Gói Kaggle hiện dùng | 2.988 train+val | 2.681 / 307 / không đóng gói test | Thêm 420 normal trong các nhóm train đã khóa; không thêm sự kiện độc lập. |

Các số ở các dòng là snapshot theo thời điểm, không cộng chúng để tính tổng dataset. Tập test 112 ảnh cũ đã được xem trong giai đoạn verified và không còn là test mới để chọn tham số. Các vòng về sau chỉ đánh giá validation; reserve âm nằm ngoài YAML và bundle. Reserve chỉ có âm nên dù chưa suy luận cũng không đủ tự tạo benchmark dương/âm hoàn chỉnh.

### D.5. Trùng lặp, chia nhóm và sửa sai

Split theo nguồn/sự kiện được ưu tiên thay chia ngẫu nhiên frame. Hash pixel tìm được bốn clip impact lặp với bbox khác nhau; screening gần giống tiếp tục phát hiện hai sự kiện xuyên train/test dù tên khác. Chúng được loại theo phiếu trước đánh giá test sạch. Tuy nhiên hash/pHash/dHash chỉ là phép sàng lọc: không tìm thêm cặp qua ngưỡng không chứng minh độc lập camera hoặc phát hiện hết mọi đoạn cắt từ cùng sự kiện.

Sai sót quan trọng khác là sử dụng 1.084 frame trước impact chưa rà như âm toàn ảnh. Dù từng được ghi là weak label, phạm vi nhãn chưa đáp ứng quy tắc đã chốt. Run scaled v2 được dừng trong epoch 15, gate release đóng lại và thay bằng verified pilot chỉ dùng âm có căn cứ. Hồ sơ cũ được giữ để truy xuất; báo cáo không dùng các metric tạm của run bị thu hồi như kết quả B0 hợp lệ.

### D.6. Số ảnh và số nguồn hiện tại

| Phần gói Kaggle | Ảnh | Clip/chuỗi duy nhất | Nhóm chống rò rỉ |
| --- | ---: | ---: | ---: |
| Train tổng | 2.681 | 1.151 | 1.112 |
| Train dương ACCIDENT | 1.122 | 1.122 | 1.085 |
| Train âm ACCIDENT | 19 | 11 | 11 |
| Train âm TAD | 1.240 | 26 | 26 |
| Train âm DETRAC | 300 | 3 | 1 |
| Validation tổng | 307 | 98 | 95 |
| Validation dương | 91 | 91 | 90 |
| Validation âm | 216 | 8 | 8 |

Các hàng con không cộng clip/nhóm trực tiếp vì âm ACCIDENT có thể cùng nguồn với impact dương. Train âm có 38 nhóm; số frame lớn hơn không làm tăng số camera tương ứng. 1.085 nhóm dương cũng chỉ là grouping theo nguồn đã có, chưa là 1.085 sự kiện/camera độc lập xác minh đầy đủ. Vì vậy báo cáo chưa đưa tổng số tai nạn vật lý độc lập đã kiểm như một con số chắc chắn.

## E. Quá trình xây dựng và huấn luyện B0

### E.1. Prototype perception và pilot 47 ảnh

Trong các mốc 16–19/10, YOLOv8n pretrained và ByteTrack được dùng để kiểm môi trường, đọc frame, duy trì ID trong một video, vẽ và lưu MP4. Lựa chọn n phù hợp mức smoke ban đầu và tài nguyên laptop; kiểm đọc lại frame xác nhận chức năng I/O. Chưa có phép đo chất lượng nhận biết tai nạn ở giai đoạn này.

Đến 26/10, pilot B0 dùng 47 ảnh ACCIDENT được chia theo 17 nhóm nguồn. YOLOv8n pretrained được fine-tune với lớp accident, 640, batch 4, FP32, optimizer auto, tối đa 40 epoch/patience 15. Run dừng sau 16 epoch, best CSV epoch 1. Trên test tám ảnh, 0 TP/45 FP/3 FN tại ngưỡng cố định cho thấy detector kém; mAP50 test 0,161%. Ý nghĩa thành công của mốc này là đường train/evaluate có thể kiểm chứng, không là mô hình đã đủ tốt.

### E.2. Mở rộng ACCIDENT và thu hồi run không phù hợp

Độ phủ dương quá nhỏ là lý do tải thêm clip public và đối chiếu TP-YOLOv8/Ultralytics. Batch 4 sau đo tài nguyên được thử tăng lên 16; lỗi serialize checkpoint ở epoch đầu khiến lượt này không có checkpoint dùng để resume. Run v2 khởi tạo lại từ pretrained với batch 8 để chừa tài nguyên, không gọi là tiếp tục chính xác run hỏng. Nguyên nhân gốc serialize chưa được cô lập; thử lưu tensor nhỏ thành công không đủ chứng minh lỗi VRAM.

Khi phát hiện âm chưa rà và trùng nguồn, mục tiêu không còn là cố chạy hết run. Dữ liệu không đáp ứng policy dẫn đến dừng và thu hồi kết quả scaled v2. Verified pilot được tạo lại với nguồn âm đã rõ và test sạch 112 ảnh. Quyết định này xuất phát từ độ hợp lệ nhãn/split, không từ việc lựa checkpoint điểm thấp hay cao.

### E.3. Verified pilot 1.750 ảnh

Run verified bắt đầu lại từ YOLOv8n pretrained, SGD 0,01/momentum 0,937, batch 8, FP32, 640, tối đa 60 epoch/patience 18. Dữ liệu gồm 1.541 train/97 val/112 test. Run hoàn tất 60 epoch; best CSV epoch 45. Trên test 112 ảnh, mAP50 đạt 69,68%, mAP50–95 52,23%, fixed F1 60,91%. Khi đánh giá model pilot cũ trên cùng tập này, mAP50 chỉ khoảng 1,19%; đây là phép so cùng test nhưng đã đổi đồng thời quy mô/nguồn dữ liệu và recipe.

Tập test chỉ có năm ảnh âm nên chưa đo tốt báo sai ngoài thực tế. Probe bổ sung 100 frame của năm clip TAD normal được chọn trước prediction. Model verified vẫn báo nhầm 41/100 frame và bốn trong năm clip; đây là lý do phân tích lỗi và mở rộng normal. Chọn các clip nhỏ nhất gây selection bias; probe sau khi đã xem được coi là consumed, không tái dùng như test mới hoặc nguồn để tune threshold.

### E.4. Learning rate 0,001, lỗi RAM và chạy đủ 60 epoch

Validation dao động và nhu cầu fine-tune ổn định tạo lý do thử giảm SGD lr0 từ 0,01 xuống 0,001, giữ dữ liệu, pretrained, seed và batch. Run dùng val-only để tránh đo lại test đã xem. Đầu epoch 2, OpenCV trong DataLoader không cấp phát được bộ nhớ RAM; đây không phải thông báo CUDA OOM. Checkpoint còn optimizer sau epoch 1 cho phép resume; số worker được giảm từ 2 xuống 0 để giảm áp lực nạp dữ liệu. Nhật ký ghi thao tác, còn config snapshot gốc vẫn được giữ.

Run LR thấp dừng sau **48 epoch**, không phải 47, best CSV ở epoch 30. Vì checkpoint cuối đã strip optimizer, yêu cầu chạy tiếp tới 60 được thực hiện bằng **một run mới từ pretrained**, patience 0 và workers 0; không phải resume từ epoch 49. Train loss giảm sau epoch 50 nhưng validation không vượt best của run mới hoặc run 48 epoch. Hai lượt khác loader/resume nên kết quả không tách được riêng tác động early stopping.

### E.5. Mở rộng normal lên 2.170 ảnh

Phân tích video verified cho thấy một số FP kéo dài, đặc biệt normal TAD; tăng khả năng phân biệt cảnh thường trở thành giả thuyết dữ liệu. Mười tám clip normal train công khai được lấy chọn lọc bằng ZIP Range, kiểm CRC/SHA/giải mã. Nhóm 10 train/4 val/4 reserve được chốt trước prediction; 30 frame đều mỗi clip tạo 300 train, 120 val và 120 reserve. Đây là thêm cảnh có căn cứ, không tạo pseudo-label từ prediction.

Run normal-expanded giữ YOLOv8n, SGD 0,001, batch 8, 640, workers 0 và đủ 60 epoch để so ảnh hưởng dữ liệu trên validation mới 217 ảnh. Best CSV ở epoch 40, revalidation mAP50 64,68%, mAP50–95 49,03%; 54 TP/35 FP/37 FN. Không so trực tiếp con số này với 97 val cũ như một cải thiện/giảm chất lượng có kiểm soát; model cũ phải được đo lại trên cùng 217 ảnh để làm reference.

### E.6. YOLOv8s, ảnh 960 và điều chỉnh dừng sớm

Trên 217 val, 21/37 FN có cạnh ngắn dưới 32 pixel khi resize 640; dữ liệu dương còn nhiều vùng nhỏ. Đây là bằng chứng để thử s960 thay cho việc đổi họ model theo tên phiên bản. Trọng số YOLOv8s chính thức được tải và kiểm digest, dữ liệu/split giữ nguyên. Thử nghiệm đồng thời tăng capacity n→s, ảnh 640→960 và giảm biến dạng augmentation, nên chỉ là thay recipe tổng hợp, không phải phép tách từng yếu tố.

Cấu hình đặt batch 2/FP32/workers 0 để phù hợp laptop; SGD 0,001, nbs 64, mosaic 0,5 và scale 0,3. Ban đầu trần 100 epoch/patience 0; sau yêu cầu dừng sớm, run được resume sau 10 epoch với patience 15 có receipt và giữ optimizer/best. Run kết thúc 45 epoch, best CSV30. Revalidation trên 217 val đạt mAP50 68,60%, mAP50–95 53,94%, fixed recall 70,33%; có cải thiện so n640 trên cùng tập nhưng không gán riêng cho kiến trúc hoặc độ phân giải.

### E.7. Điểm vận hành và B1 chẩn đoán

Ngưỡng confidence 0,27 cho checkpoint s960 cũ được chọn trên val với điều kiện recall tối thiểu 0,70 rồi khóa trước mở holdout âm. Ở ngưỡng này val có 64 TP/39 FP/27 FN, F1 65,98%. Holdout 120 frame normal cho 34 ảnh có dự đoán và 35 bbox sai; sau lượt này nó đã consumed. Không sửa khóa theo kết quả holdout hoặc tuyên bố 34/120 là false alerts/giờ.

Checkpoint/điểm vận hành này được dùng cho chẩn đoán B1 ngày 29/10, không tự thay bằng model Kaggle mới hơn. Điều đó giữ tính truy xuất của phép đo B0–B1 đã có. B1 đã thực thi trên video, nhưng chưa đáp ứng đầy đủ event metrics; chi tiết ở phần G.

### E.8. Hard negatives và fine-tune từ checkpoint s960

Lỗi normal kéo dài tạo căn cứ thêm dữ liệu âm khó. Ý tưởng mining tham khảo SSD [R12], nhưng SSD chọn negative anchors theo loss còn đồ án chọn frame offline theo score cũ. TAD normal cung cấp nhãn; score chỉ xếp độ khó, không tạo ground truth. Nhóm được khóa trước mining. Mỗi clip train lấy 20 frame đều và 10 frame score cao rải theo bin; val/reserve lấy đều và không chọn bằng score.

Batch 24 clip mới qua screening, trong đó 14 train/3 val/4 reserve/3 loại. Có 420 ảnh thêm train và 90 val, tạo 2.261 train/307 val/112 test cũ; 120 reserve mới nằm riêng. Khởi tạo từ best s960, tạo optimizer mới, SGD 0,0003, batch 2/960/FP32; đây là warm-start run mới. Run dừng sau 15 epoch, best CSV5; mAP50–95 tăng nhưng fixed F1 giảm so reference cùng 307 val. Không gọi riêng mining đã cải thiện tổng quát hóa.

### E.9. Chuyển sang Kaggle và Version 9

Kaggle được chọn theo yêu cầu giảm tải laptop và vì tài khoản có tài nguyên GPU miễn phí, hỗ trợ Dataset PRIVATE, Notebook và API. Bổ sung dữ liệu ở mốc này là dùng đủ 60 ứng viên normal thay 30 trong 14 clip train đã khóa, thêm 420 ảnh nhưng không thêm sự kiện độc lập. Gói chứa 2.681 train/307 val; test/reserve không có media trong luồng train. Recipe và trọng số đầu như hardneg được giữ ở Version 9, không lấy best hardneg để resume.

Các phiên trước Version 9 có lỗi tích hợp, không phải các model mới: license Dataset bị từ chối, trạng thái quyền tạm, Kaggle giải nén ZIP làm notebook không tìm được archive, yêu cầu GPU nhưng thực tế chưa được cấp GPU, DNS và backend Matplotlib inline. Probe sau đó xác nhận GPU T4/CUDA/Internet thật; backend Agg được đặt trước process con. Không suy ngược các lỗi này là dữ liệu sai hoặc thiếu VRAM.

Version 9 hoàn tất 11 epoch, best CSV1 với SGD 0,0003, batch 2 FP32, trần 40/patience 10. Same-val mAP50 69,79%, mAP50–95 55,87%. Tham số môi trường Python 3.12.10, Torch 2.11.0+cu128, Ultralytics 8.4.178 được khóa để tránh image cloud cập nhật làm lệch môi trường. GPU0 được dùng dù probe có hai T4; không nhận đây là train đa GPU.

### E.10. Version 10 AdamW và Version 11 SGD

Version 9 dừng sớm và best ngay đầu run là lý do thử recipe tối ưu khác. Version 10 giữ gói dữ liệu/khởi tạo, đổi AdamW, batch 8/AMP, nbs 32, cosine, warmup 5, mosaic 0,2/scale 0,15, tối đa60. Bộ đếm dừng chỉ bắt đầu sau epoch 25, patience 25. Run hoàn tất60, best52, mAP50 67,85% và mAP50–95 52,63%; F1 cố định tăng nhẹ nhưng recall giảm so V9. Vì thay nhiều yếu tố, không thể quy toàn bộ khác biệt cho AdamW hoặc cosine.

Version 11 được thiết kế để chỉ đổi optimizer AdamW→SGD trong các tham số train của V10. Giữ batch 8, AMP, seed, lịch học, dữ liệu và trọng số đầu; momentum là 0,9, không phải 0,937 của V9. Cùng lr0 0,0003 không có nghĩa SGD/AdamW có bước cập nhật tương đương, nên đây là đối chứng ở một điểm recipe, không chứng minh optimizer nào luôn tốt hơn. Run dừng đúng epoch 50 do best vẫn ở3 và bộ đếm sau 25 đủ 25 epoch.

Version 11 tăng mAP và recall fixed nhưng tăng FP; chưa được tự đưa thành checkpoint vận hành thay khóa cũ. Best/last đã tải đủ, kiểm hash và đọc được trên CPU; cả hai đã strip optimizer, metadata epoch −1, metric tương ứng CSV3/50. Chúng có thể dùng làm weights cho run mới được thiết kế riêng, không phục hồi chính xác optimizer của run đã kết thúc.

## F. Tổng hợp kết quả và phép so hợp lệ

### F.1. Ý nghĩa các chỉ số

TP, True Positive, là bbox dự đoán được ghép đúng một bbox GT theo class/IoU; FP, False Positive, là bbox không ghép đúng; FN, False Negative, là bbox GT còn bị bỏ sót. Precision = TP/(TP+FP); recall = TP/(TP+FN); F1 là trung bình điều hòa precision và recall. Các phép đếm bên dưới dùng confidence 0,25 và IoU ghép 0,5 trừ khi ghi rõ điểm vận hành khác.

IoU, Intersection over Union, là diện tích giao chia diện tích hợp của hai hộp. AP là diện tích dưới đường precision–recall khi quét mức confidence; mAP lấy trung bình AP theo lớp. Với một lớp, mAP50 bằng AP của lớp accident tại IoU0,5. mAP50–95 tiếp tục trung bình ở 10 ngưỡng IoU từ 0,50 đến0,95 bước0,05. Đây không phải trung bình precision thô hoặc accuracy phân loại ảnh.

Precision/recall do Ultralytics báo trên đường PR có thể dùng điểm làm việc khác confidence0,25. Báo cáo không trộn chúng với P/R/F1 đếm lại ở ngưỡng cố định. Fitness chọn best của bản Ultralytics 8.4.178 là mAP50–95, không train loss hoặc mAP50 riêng. Các bảng dùng **đánh giá lại best đã lưu**, còn peak CSV được ghi riêng khi cần.

### F.2. Pilot đầu và test đã sử dụng

| Model và tập đánh giá | mAP50 | mAP50–95 | TP / FP / FN | F1 cố định |
| --- | ---: | ---: | --- | ---: |
| Pilot47, test 8 ảnh | 0,16% | 0,05% | 0 / 45 / 3 | 0,00% |
| Verified1750, test 112 ảnh | 69,68% | 52,23% | 67 / 46 / 40 | 60,91% |

Hai dòng khác tập test nên chỉ là các mốc lịch sử, không là ablation. Phép đánh giá bổ sung cùng test 112 đã đo pilot cũ mAP50 khoảng 1,19%, verified mới 69,68%; kết quả hỗ trợ việc mở rộng/chuẩn hóa nhưng không tách riêng ảnh hưởng dữ liệu và recipe. Test 112 chỉ có năm ảnh âm, vì vậy không thể suy mức báo sai trên giao thông thực từ nó.

### F.3. Cùng validation 97 ảnh — khảo sát learning rate/thời lượng

| Run | Epoch thực / best CSV | mAP50 | mAP50–95 | P / R / F1 cố định |
| --- | --- | ---: | ---: | --- |
| Verified, SGD 0,01 | 60 / 45 | 60,63% | 46,03% | 51,49 / 57,14 / 54,17% |
| LR0,001, có resume/đổi workers | 48 / 30 | 66,86% | 50,64% | 55,05 / 65,93 / 60,00% |
| LR0,001, run mới đủ 60 | 60 / 47 | 64,94% | 49,41% | 46,28 / 61,54 / 52,83% |

TP/FP/FN lần lượt là 52/49/39,60/49/31 và56/65/35. Tập này gồm 91 ảnh dương/6 ảnh âm. Giảm LR có kết quả tốt hơn trong các run đã đo; run đủ 60 không hơn run48 dù loss train giảm. Do resume/worker khác nhau và chỉ một seed, không gọi đây là bằng chứng nhân quả riêng cho early stopping.

### F.4. Cùng validation 217 ảnh — normal-expanded và s960

| Run và thay đổi chính | Epoch thực / best CSV | mAP50 | mAP50–95 | TP / FP / FN |
| --- | --- | ---: | ---: | --- |
| n640 normal-expanded | 60 / 40 | 64,68% | 49,03% | 54 / 35 / 37 |
| s960, đổi capacity/resolution/augmentation | 45 / 30 | 68,60% | 53,94% | 64 / 43 / 27 |

P/R/F1 cố định n640 là 60,67/59,34/60,00%; s960 là 59,81/70,33/64,65%. Recall tăng và FN giảm nhưng FP cũng tăng. Đây là phép so cùng tập và dữ liệu train, còn nhiều biến recipe thay đổi. Chưa thể nói riêng YOLOv8s hoặc 960 là nguyên nhân toàn bộ mức tăng.

### F.5. Cùng validation 307 ảnh — hardneg và Kaggle

| Run, dữ liệu train | Epoch thực / best CSV | mAP50 | mAP50–95 | Đặc điểm phép so |
| --- | --- | ---: | ---: | --- |
| Hardneg local, 2.261 ảnh | 15 / 5 | 68,48% | 55,43% | Warm-start s960; dữ liệu train ít hơn cloud. |
| Kaggle V9, 2.681 ảnh | 11 / 1 | 69,79% | 55,87% | Thêm 420 normal; cùng recipe hardneg, đổi môi trường. |
| Kaggle V10, 2.681 ảnh | 60 / 52 | 67,85% | 52,63% | AdamW và nhiều thay đổi schedule/resource. |
| Kaggle V11, 2.681 ảnh | 50 / 3 | 70,64% | 56,80% | Chỉ đổi optimizer so V10 trong training arguments. |
| Kaggle V12, 2.681 ảnh | 50 / 3 | 70,63% | 56,10% | Chỉ giảm `lr0` SGD 0,0003→0,00015 so V11. |

| Run | Precision | Recall | F1 | TP / FP / FN | Ảnh âm có FP /216 |
| --- | ---: | ---: | ---: | --- | ---: |
| Hardneg | 56,25% | 69,23% | 62,07% | 63 / 49 / 28 | 5 |
| V9 | 65,59% | 67,03% | 66,30% | 61 / 32 / 30 | 5 |
| V10 | 72,15% | 62,64% | 67,06% | 57 / 22 / 34 | 2 |
| V11 | 61,54% | 70,33% | 65,64% | 64 / 40 / 27 | 8 |
| V12 | 63,73% | 71,43% | 67,36% | 65 / 37 / 26 | 7 |

Nhóm Kaggle cùng fingerprint provenance và trọng số khởi tạo, còn hardneg khác lượng train. V11 so V10 tăng 2,79 điểm phần trăm mAP50, tăng 4,17 điểm mAP50–95 và tăng 7,69 điểm recall cố định; precision giảm 10,61 điểm, F1 giảm 1,42 điểm và FP tăng 18 bbox. V11 so V9 tăng khoảng 0,85 điểm mAP50 và0,93 điểm mAP50–95; không nên diễn giải mức tăng nhỏ trên validation tái sử dụng là tổng quát hóa đã được chứng minh.

V12 là đối chứng một biến với V11: cùng 2.681 train/307 val, checkpoint đầu, seed, SGD, batch8, AMP, augmentation và lịch huấn luyện; chỉ `lr0` từ0,0003 xuống0,00015. Cả hai dừng ởepoch50 và chọn best epoch3. V12 so V11 gần như ngang mAP50 (giảm0,01 điểm phần trăm khi làm tròn), mAP50–95 giảm0,70 điểm, trong khi F1 cố định tăng1,72 điểm, FP giảm3 bbox và FN giảm1 bbox; số ảnh âm có hộp sai giảm8→7 trên216. Các thay đổi nhỏ trên một validation đã dùng nhiều lần không chứng minh LR thấp hơn tốt hơn tổng quát, đặc biệt khi mAP50–95 đi ngược F1. V10 vẫn có FP thấp hơn cả hai run SGD ở ngưỡng này. [Config V12](../configs/b0_s960_sgd_low_lr_kaggle_v4.json) ghi trước run giả thuyết và giới hạn; không thay checkpoint/operating point B0 đang khóa.

Ví dụ chính xác về khác biệt metric: Ultralytics revalidation V11 báo P81,46%/R62,77%, còn ngưỡng cố định cho P61,54%/R70,33%. Hai cặp đều hợp lệ trong protocol của chúng; không chọn precision cao của cặp đầu và recall cao của cặp sau để dựng một cấu hình không tồn tại.

### F.6. Peak CSV, checkpoint và độ tin cậy so sánh

![Đồ thị train và validation của Version 11](../outputs/training/b0_s960_sgd_kaggle_v3/training_summary/results.png)

*Hình 1. Đồ thị thực tế Version 11, lấy từ kết quả đã kiểm hash. Loss train giảm trong khi loss validation và mAP không tạo cải thiện vượt epoch 3; diễn biến này là dấu hiệu cần kiểm tổng quát hóa, chưa cô lập riêng nguyên nhân quá khớp, lệch nguồn hoặc độ phủ nhãn.*

![Đồ thị train và validation của Version 12](../outputs/training/b0_s960_sgd_low_lr_kaggle_v4/training_summary/results.png)

*Hình 2. Đồ thị thực tế Version 12 từ output đã kiểm hash. Best vẫn ở epoch 3 dù LR đỉnh thấp hơn; kéo dài đến epoch 50 không tạo checkpoint vượt best theo fitness. Đây là quan sát trên cùng validation, không là bằng chứng độc lập rằng một LR tối ưu đã được tìm thấy.*

Trong hardneg, mAP50 CSV epoch 2 từng vượt70% nhưng checkpoint best chọn ởepoch5 theo mAP50–95. Không có checkpoint epoch 2 để đánh giá lại, nên con số CSV đó không được gọi là modelbest đã đạt mục tiêu. Ở V11, bestCSV3 mAP50≈70,643% và revalidation70,643% nhất quán gần nhau; mAP50–95 CSV56,815% và revalidation56,800% được giữ là hai nguồn khác nhau. Một số run trước có chênh lớn hơn; nguyên nhân riêng chưa được cô lập, không tự quy cho random hay lỗi evaluator.

Hồ sơ V10/V11/V12 có ZIP, receipt và từng file qua hash; V12 thêm `run_status.json` xác nhận `training_completed=true`,50epoch và `best.pt` khớp hash trong experiment. V9 được đọc chọn lọc metadata bằng HTTP Range, từng member khớp manifest; toàn bộ ZIP/checkpoint V9 không được tải và kiểm lại SHA đầy đủ. Những khác biệt về mức bằng chứng này phải được giữ khi trình bày khả năng tái lập.

### F.7. Vì sao không đối chiếu các “phần trăm” paper như cùng thang đo?

Ijjina báo detection rate71% và FAR0,53% theo đơn vị cases/patterns [R5]; Ghahremannezhad báo93,10% detection rate trên 29 conflict gồm cả near-accident [R6]. RARE báo AP anticipation trên DAD/CCD và thời gian dự báo [R7]. STTAD báo mAP vùng trên test 12 lớp [R2]. Những con số này khác mAP bbox một lớp trên validation B0 về target, mẫu, đơn vị ghép và độ độc lập.

Mốc70% mAP50 từng là mục tiêu thăm dò trong các config sau 28/10, có trường không bảo đảm. Workbook đặt trọng tâm giảm false alarm tại recall tương đương và chi phí vận hành, không chốt70% là chuẩn ngành hay tiêu chí đủ để hoàn thành đồ án. Vì vậy việc V11 vượt mốc này không thay thế đánh giá event hoặc là lý do tự kết thúc nghiên cứu.

## G. Phân tích lỗi và kết quả ngoài B0

### G.1. Bằng chứng và giả thuyết nguyên nhân

| Vấn đề | Bằng chứng đã có | Cách hiểu và phần chưa kiểm chứng |
| --- | --- | --- |
| Vùng nhỏ dễ bỏ sót | Verified: diện tích GT FN trung vị0,321% ảnh, TP3,216%; normal-expanded21/37 FN cạnh ngắn<32 pixel ở640. | Liên hệ với kích cỡ là quan sát; chưa cô lập riêng tác động blur/occlusion/label/camera. |
| Báo sai normal kéo dài | Verified có 812/1.599 frame TAD normal bị dự đoán, đoạn dài215 frame. | Lọc chớp tắt có thể không đủ; chưa có giả thuyết nào được chứng minh cho mọi clip. |
| Lệch nguồn | Train dương ACCIDENT, phần lớn âm từ TAD/DETRAC; âm train chỉ38 nhóm. | Có nguy cơ học dấu hiệu nguồn; chưa đo classifier nguồn hoặc tác động nhân quả. |
| Validation tái sử dụng | Val 97→217→307 giữ nhiều nguồn dương cũ; đã dùng để nhiều lần chọn recipe. | Điểm cao có thể thích nghi validation; chưa có test mới độc lập cân cả dương/âm. |
| Timing chưa đủ | CADP interval theoframe, FPS nguồn chưa biết; nhiều TAD chỉ có PTS media. | Không báo độ trễ nguồn hoặc km/h khi thiếu căn cứ; không gán displayFPS thành cameraFPS. |
| Track ID/missing | Pipeline giữ/reset tracker và đã xuất video kiểm kỹ thuật. | Chưa có GT identity để đo ID switch; chỉ nêu rủi ro, không gán là lỗi đã đo. |

Với Version 10,41/91 vùng val có diện tích<1% ảnh và18/34 FN nằm trong nhóm đó. Đây là phân tầng theo diện tích tương đối, khác small/medium/large của COCO. Kết quả cho phép ưu tiên kiểm các case nhỏ nhưng chưa cho phép loại chúng để làm đẹp validation hoặc tự phóng bbox GT.

Các mẫu FP đã xem có vùng sáng cố định, đường hầm/đèn xe và cảnh đêm, nhưng đó là quan sát lấy mẫu. Hướng xử lý hợp lý là phân loại lỗi, giữ nhãn nguồn và kiểm nhóm; nếu mở dữ liệu mới thì cần nhãn công khai hỗ trợ đúng task, không chuyển prediction thành GT hoặc coi toàn clip accident là dương.

### G.2. B1 đã triển khai tới đâu?

Ngày 29/10, cùng checkpoint s960/conf0,27 được chạy trên 12 chuỗi/4.845 frame, lưu score, frame/time, trạng thái bộ lọc và MP4. Tất cả12 video đọc lại đủ frame; phép kiểm causal, warmup và reset/gap đã có. Đây là phần triển khai thật, vì vậy trạng thái “B1 chưa triển khai” trong một số đoạn nhật ký27/10 chỉ còn là lịch sử.

| Nhóm chẩn đoán | Frame | B0 ON / bout | B1 3-of-5 ON / bout | B1 EMA ON / bout |
| --- | ---: | --- | --- | --- |
| DETRAC từng dùng train | 2.037 | 0 / 0 | 0 / 0 | 0 / 0 |
| Normal thuộc validation | 1.296 | 99 / 31 | 92 / 11 | 90 / 13 |
| Normal holdout đã tiêu thụ | 1.291 | 300 / 40 | 293 / 17 | 302 / 16 |

Bout là đoạn trạng thái ON liên tiếp, chưa có chính sách event matching để gọi là số cảnh báo sai. B1 giảm số đoạn chớp nhưng EMA có thể kéo dài ON; nhóm consumed chỉ dùng chẩn đoán hậu nghiệm. Cả ba policy bật35/35 frame trong CADP96–130 nhưng đã bật trước96; ngoài interval là unknown. Không suy spatial recall, event recall hoặc delay từ 35/35này.

Lý do giữ B1 làm đối chứng là chi phí thấp và giúp định lượng lợi ích temporal đơn giản trước verifier. Dữ liệu hiện tại chưa đủ để xác nhận B1 hoàn thành điều kiện so matched recall và độ trễ trên test sự kiện độc lập. B2/T0/GRU không được ghi là đã có kết quả chỉ vì có video tracking hoặc mã bộ lọc.

### G.3. Quy trình tái lập và khả năng vận hành

Code hiện có kiểm input, config, model/hash và số frame đầu ra; raw, preview tác giả và prediction đặt riêng. Checkpoint `best.pt` phục vụ đánh giá theo fitness còn `last.pt` là cuối run; sau strip không còn optimizer để resume đầy đủ. Khi run đang dở và checkpoint còn optimizer, resume phải đối chiếu snapshot; khi khởi tạo lại phải ghi run mới.

Git giữ source/config/docs/metadata nhỏ; dataset, trọng số, cache và video kết quả được ignore. Hướng dẫn phục hồi/catalog chỉ ra nguồn và vị trí, vì manifest trên Git không chứng minh media đã có trên máy mới. SHA giúp tái lập byte dữ liệu nhưng không thay việc kiểm nhãn hoặc grouping camera. Các kiểm thử kỹ thuật đã đạt ở các mốc thể hiện độ an toàn của công cụ; chúng không phải accuracy của detector.

## H. Trạng thái hiện tại và kế hoạch ưu tiên

### H.1. Trạng thái đã kiểm tại ngày báo cáo

Kaggle Version 11 được kiểm/thu thập từ 31/10 và giữ nguyên như mốc lịch sử. Theo chỉ dẫn riêng ngày04/11, Version 12 được gửi trên Dataset PRIVATE cũ mà không upload lại dữ liệu, chạy 50 epoch và đã fetch về `outputs/training/b0_s960_sgd_low_lr_kaggle_v4/`. Receipt và manifest ZIP, config hash, `run_status.json` cùng SHA checkpoint best đã qua kiểm; `training_completed=true`. Không có train trên laptop, không chạy test/reserve hay thay checkpoint B0 đang khóa. Deployment receipt lúc gửi vẫn ghi `RUNNING`, vì đó là snapshot lịch sử; API sau đó báo `COMPLETE` và kết quả local mới là bằng chứng hoàn tất train.

Lỗi401/403 đọc log trước đó đã không còn tái hiện ở lần kiểm trạng thái này, nhưng nguyên nhân nội bộ hết lỗi chưa được xác minh. Trạng thái upload thành công trước đây không được dùng thay trạng thái train. Quota GPU được đọc tại từng mốc, từng có thông tin khả dụng khác con số giao diện30 giờ/tuần; không coi hạn mức đó là hằng số bảo đảm.

| Mức hoàn thành | Thành quả có bằng chứng | Phần chưa đạt |
| --- | --- | --- |
| Công cụ dữ liệu | Kiểm media/mapping/nhãn/hash, export YOLO và group split. | Độc lập camera và độ phủ ngữ nghĩa toàn dataset chưa chứng minh. |
| B0 pilot ảnh | Có checkpoint, config, curves, metric và FP/FN; V11/V12 đều quanh70,6% mAP50 val. | Chưa có test sự kiện độc lập hoặc lựa chọn model vận hành mới. |
| B1 chẩn đoán | Bộ lọc causal/replay và12 chuỗi đã chạy. | Chưa có event matching/recall/delay được kiểm đầy đủ. |
| B2/T0/B3 | Có kế hoạch, nền detection/tracking và tài liệu. | Candidate/features/labels/verifier/evaluator còn thiếu. |
| Hệ thống cuối | Luồng đọc/ghi video, evidence thí nghiệm và dashboard local chỉ đọc đã có; xem được một run từ cloud đến artifact đã fetch. | FSM cảnh báo, xử lý online/video dài và benchmark toàn pipeline chưa hoàn chỉnh. |

### H.2. Có nên tiếp tục tối ưu B0 ngay?

B0 đã có tín hiệu ảnh hữu ích và lỗi đủ rõ để phát triển bước kiểm chứng temporal. Các vòng đổi LR, tăng epoch, thêm normal, tăng model/resolution và đổi optimizer cho thấy sự đánh đổi; chưa có xu hướng cho phép bảo đảm cứ train tiếp sẽ cải thiện. V11 giữ mAP50/mAP50–95 cao hơn V12 một ít trên307 val, nhưng V12 có F1 cố định cao hơn V11; V10 vẫn có FP thấp nhất trong ba run này ở cùng ngưỡng. Không có căn cứ chọn model chỉ theo một số tối đa rồi bỏ trade-off FP/recall và validation tái sử dụng.

Phương án đề xuất là tạm khóa ứng viên và tiêu chí trước khi mở dữ liệu đánh giá mới. Checkpoint/operating point s960 đã khóa vẫn là mốc của các phép đo B1 cũ; V11 và V12 là hai ứng viên ảnh có trade-off khác nhau, chưa tự thay thế. Nếu cần chọn điểm vận hành mới thì thực hiện trên validation có ghi protocol, sau đó giữ nguyên cho phép đo độc lập. Mốc70% không là điều kiện chặn B1/B2 hoặc là bằng chứng hệ thống hoàn tất.

### H.3. Thứ tự công việc đề xuất sau báo cáo

| Ưu tiên | Mục đích và công việc cụ thể | Đầu ra kiểm chứng | Phụ thuộc/điều kiện chuyển |
| --- | --- | --- | --- |
| 1. Khóa câu hỏi và ứng viên | Chốt đơn vị cảnh báo, policy contact/unknown và checkpoint phục vụ so B0/B1; rà FP/FN đã lưu. | Config inference/version, bảng lý do chọn và phân nhóm lỗi. | Dựa trên val hiện có; không lựa bằng reserve/test đã mở. |
| 2. Hoàn thiện dữ liệu sự kiện | Kiểm nguồn public có onset/interval; lập manifest camera/nguồn, kiểm giao dữ liệu; nếu chỉ frame/clip-label thì ghi đúng giới hạn. | Danh sách event dương và video âm cùng provenance, unknown/ignore rõ. | Không gán nhãn thiếu là âm; timing theo đơn vị được kiểm. |
| 3. Evaluator sự kiện chung | Cài event matching, chống lặp, đếm miss/false alert và thời gian; kiểm các tình huống biên. | Evaluator có fixture và log ghép alert–event truy xuất được. | Protocol khóa trước test; nếu thiếu timing thì chưa báo delay giây nguồn. |
| 4. So B0/B1 | Replay cùng score, cùng bộ dữ liệu và policy; đo matched recall, FP và độ trễ. | Bảng PR/event, case lỗi và chi phí tăng thêm. | Phân biệt val/development với test mới; B1 không cần phải thắng. |
| 5. Xây B2 rồi T0 | Xuất track quality/missing; tạo cặp, đo candidate recall, xây đặc trưng và luật rồi MLP. | Track/feature cache, nhãn có phiên bản và baseline có metric. | Candidate/nhãn đủ rõ; không dùng ID tracker như GT identity. |
| 6. Thử B3/T1 có điều kiện | GRU causal cùng features/split với T0; bỏ từng nhóm feature và nhiều seed nếu ngân sách cho phép. | Bảng ablation và kết luận RQ1 có giới hạn. | Chỉ mở khi đủ temporal labels và các baseline đơn giản đã đo. |
| 7. Hệ thống/benchmark | Dashboard chỉ đọc đã có; còn FSM, cooldown, ring buffer, pipeline online và đo video dài trên laptop. | Demo, false alerts/giờ âm, FPS/VRAM/latency đầy đủ để trả lời RQ2. | Tính cả hai detector nếu dùng; không loại bỏ thời gian I/O/queue. |

Một vòng train B0 mới chỉ có căn cứ khi xác định được lỗi có thể sửa bằng dữ liệu/recipe cụ thể và có phép so kiểm soát. Phép kiểm LR V12 đã hoàn thành nhưng chưa giải quyết giới hạn validation; không mở thêm run theo quán tính. Nếu thêm dữ liệu, ưu tiên nguồn/cảnh/sự kiện độc lập và nhãn vùng phù hợp thay vì lặp dày frame. Nếu nguồn chỉ public nhãn temporal/clip, có thể phục vụ evaluator/B1 theo đơn vị đó; không tự biến thành bbox để tăng ảnh B0. Các mục evaluator và baseline còn lại trong bảng là kế hoạch, dashboard đọc kết quả là phần đã triển khai.

## I. Kết luận tiến độ

Đồ án đã hoàn thành một chuỗi công việc có thể truy xuất từ dữ liệu public đến huấn luyện và phân tích detector ảnh. Quá trình không tiến tuyến tính: đã có sai nhãn âm, trùng nguồn, lỗi RAM/serialize và tích hợp cloud; những thay đổi có căn cứ đã được ghi, run không phù hợp được thu hồi và các phép đo lịch sử được giữ phạm vi.

Thành quả mới nhất là run V12 đã tải/kiểm: mAP50 val70,63%, mAP50–95 56,10%, F1 cố định67,36%; giảm LR so V11 tạo trade-off chứ không thắng trên mọi metric. Dashboard đã gộp trạng thái Kaggle và artifact local theo một run, tự đọc lại khi đang mở nhưng không tự tải trọng số hoặc điều khiển train. Thành quả B1 hiện tại là triển khai causal và chẩn đoán có dữ liệu thật, chưa là benchmark sự kiện. Hạn chế chính nằm ở độ độc lập/độ phủ nhãn, timing và evaluator hệ thống. Ưu tiên phù hợp là hoàn thiện phép đánh giá và đối chứng temporal trên một detector được khóa, rồi mới xác định nhu cầu motion verifier hoặc train tiếp bằng bằng chứng.

## Tài liệu tham khảo

Các mã R trong báo cáo thống nhất theo danh mục dưới đây; nguồn nền được kiểm trực tuyến phục vụ báo cáo 31/10/2026, mã và tài liệu Ultralytics cho đối chứng LR được đối chiếu tiếp 04/11 trong `reference/LITERATURE_REVIEW.md`. Mã S/R lịch sử trong workbook/literature được đối chiếu tại phụ lục, không có nghĩa tất cả nguồn đều đã được tái lập.

- **[R1]** Q. N. H. Minh và cộng sự (2025). *Real-time traffic accident detection using YOLOv8*. Transportation Research Procedia85,68–75. [Publisher/abstract](https://www.sciencedirect.com/science/article/pii/S2352146525001942), [DOI](https://doi.org/10.1016/j.trpro.2025.03.135). Full PDF chưa truy cập được; không dùng chi tiết chưa đọc.
- **[R2]** S. Xu và cộng sự (2025). *Surveillance-based Spatial Temporal Traffic Accident Detection: A novel Dataset and tailored Algorithm*. [Toàn văn](https://dsg.tuwien.ac.at/team/snastic/publications/ITSC25_0424_FI.pdf), [STTAD repo](https://github.com/ZTR02/STTAD). Dùng mục nhãn và recipe/kết quả; chưa chạy STFN.
- **[R3]** Z. Ning, T. Zhang, X. Li, A. Wu, G. Shi (2025). *TP-YOLOv8: a lightweight and accurate model for traffic accident recognition*. The Journal of Supercomputing81:622. [Bản tác giả](https://zhangtianze.com/mypublications/Thesis/TPYOLOv8.pdf), [DOI](https://doi.org/10.1007/s11227-025-07129-6).
- **[R4]** L. Picek, M. Čermák, M. Hanzl, V. Čermák (2026). *ACCIDENT: A Benchmark Dataset for Vehicle Accident Detection from Traffic Surveillance Videos*. [Paper](https://arxiv.org/abs/2604.09819), [repo](https://github.com/accidentbench/ACCIDENT), [dataset v9](https://www.kaggle.com/datasets/picekl/accident/versions/9).
- **[R5]** E. P. Ijjina và cộng sự (2019). *Computer Vision-based Accident Detection in Traffic Surveillance*. [Paper](https://arxiv.org/html/1911.10037v1). Tham khảo motion rules và giới hạn điều kiện quan sát.
- **[R6]** H. Ghahremannezhad, H. Shi, C. Liu (2022). *Real-Time Accident Detection in Traffic Surveillance Using Deep Learning*. [Paper](https://arxiv.org/html/2208.06461v1), [DOI](https://doi.org/10.1109/IST55454.2022.9827736).
- **[R7]** I. Song, J. Lee (2025). *Real-time Traffic Accident Anticipation with Feature Reuse*. [Paper](https://arxiv.org/html/2505.17449v1), [RARE repo](https://github.com/Songinpyo/RARE-ICIP2025).
- **[R8]** Y. Zhang và cộng sự (2021/2022). *ByteTrack: Multi-Object Tracking by Associating Every Detection Box*. [Paper](https://arxiv.org/abs/2110.06864). Không chuyển điểm MOT thành chất lượng tracking của đồ án.
- **[R9]** I. Loshchilov, F. Hutter (ICLR2019). *Decoupled Weight Decay Regularization*. [Paper](https://arxiv.org/abs/1711.05101). Đối chiếu AdamW; không là recipe tối ưu CCTV đã chứng minh.
- **[R10]** I. Loshchilov, F. Hutter (ICLR2017). *SGDR: Stochastic Gradient Descent with Warm Restarts*. [Paper](https://arxiv.org/abs/1608.03983). Đồ án chỉ áp lịch cosine, không warm restart.
- **[R11]** NIST/SEMATECH. *EWMA Control Charts*. [Tài liệu](https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc314.htm). Tham chiếu công thức trung bình trượt mũ, không protocol tai nạn.
- **[R12]** W. Liu và cộng sự (2016). *SSD: Single Shot MultiBox Detector*. [Paper](https://arxiv.org/html/1512.02325v5). Ý tưởng chọn âm khó được điều chỉnh thành offline frame mining.
- **[R13]** A. Shah và cộng sự (2018). *CADP: A Novel Dataset for CCTV Traffic Camera based Accident Analysis*. [Trang tác giả](https://ankitshah009.github.io/accident_forecasting_traffic_camera.html), [mã tham chiếu](https://github.com/ankitshah009/CarCrash_forecasting_and_detection).
- **[R14]** Y. Xu và cộng sự (2025). *TAD: A Large-Scale Benchmark for Traffic Accidents Detection From Video Surveillance*. IEEE Access13,2018–2033. [Repo tác giả](https://github.com/UnicomAI/UnicomBenchmark/tree/main/TADBench), [DOI](https://doi.org/10.1109/ACCESS.2024.3522384).
- **[R15]** L. Wen và cộng sự. *UA-DETRAC: A New Benchmark and Protocol for Multi-Object Detection and Tracking*. [Paper](https://arxiv.org/abs/1511.04136). Vai trò video/xe và quy ước dữ liệu, không nhãn accident.
- **[R16]** Ultralytics. [YOLOv8](https://docs.ultralytics.com/models/yolov8/), [train](https://docs.ultralytics.com/modes/train/), [fine-tuning](https://docs.ultralytics.com/guides/finetuning-guide/), [trainer bản8.4.178](https://github.com/ultralytics/ultralytics/blob/v8.4.178/ultralytics/engine/trainer.py). Tài liệu web hiện cập nhật sang thế hệ khác; code/version đã khóa là căn cứ tái lập.
- **[R17]** Kaggle. [CLI kernels](https://github.com/Kaggle/kaggle-cli/blob/main/docs/kernels.md), [metadata](https://github.com/Kaggle/kaggle-cli/blob/main/docs/kernels_metadata.md), [Docker images](https://github.com/Kaggle/docker-python). Căn cứ vận hành GPU/API, không căn cứ chất lượng detector.
- **[R18]** PyTorch. [AMP2.11](https://docs.pytorch.org/docs/2.11/notes/amp_examples.html). Matplotlib. [Backends](https://matplotlib.org/stable/users/explain/figure/backends.html). uv. [Python provisioning](https://docs.astral.sh/uv/guides/install-python/). Vai trò môi trường/resource và xuất biểu đồ.

## Phụ lục 1. Đối chiếu nhận định với bằng chứng

Các đường dẫn dưới đây tính từ gốc project. Chúng phục vụ truy xuất, không thay thế phần giải thích chuyên môn. Media/checkpoint lớn lưu local; sau clone cần phục hồi theo catalog, không chỉ có file metadata là đủ.

| Mã hồ sơ | Nội dung kiểm chứng | Đường dẫn chính |
| --- | --- | --- |
| E01 | Mục tiêu, baseline và điều kiện | `README.md`; `YOLO_Lo_trinh_DACN.xlsx`, sheet01/05/07/08/09/11/13/15. |
| E02 | Lịch sử và nguồn nghiên cứu | `progress/2026-10-16.md` đến `2026-11-04.md`; `reference/LITERATURE_REVIEW.md`; `reference/workbook_sources.csv`. |
| E03 | CADP sạch và review theo frame | `docs/cadp_001407_clean.md`; `outputs/audits/cadp_001407_clean_2/report.json`; `data/reviews/2026-10-19-cadp-001407-frame-confirmation.json`. |
| E04 | Nhãn/public sources và thu hồi | `docs/b0_label_protocol.md`; `configs/b0_verified_label_policy.json`; `data/b0_readiness.json`; review26–27/10 và nhật ký27/10. |
| E05 | Dataset, split, provenance | `data/processed/b0_verified_pilot_v1/`; `b0_normal_expanded_v1/`; `b0_s960_hardneg_v1/`; mỗi release có split report và dataset/provenance.csv. |
| E06 | Các run local hợp lệ | `outputs/training/<run>/experiment.json`, `requested_config.json`, `args.yaml`, `results.csv`, `cases_val/cases.csv`; tên run ở phụ lục2. |
| E07 | Kaggle V9–V12 | `outputs/kaggle/b0_s960_full_kaggle_v1/version9_lightweight_comparison.json`; V10–V12 `outputs/training/<run>/experiment.json`, `run_status.json`, `recipe_revision.json`, `live_console.log`; V12 `outputs/kaggle/b0_s960_sgd_low_lr_kaggle_v4/retrieval.json`. |
| E08 | Kết quả/metric nhỏ trên Git | `docs/evidence/2026-10-27-b0-verified-pilot.json`; `2026-10-28-b0-s960-validation.json`; `2026-10-30-b0-adamw-validation.json`; `2026-10-30-b0-sgd-validation.json`. |
| E09 | Ngưỡng khóa và holdout đã dùng | `configs/b0_s960_v1_operating_point_v1.json`; `outputs/training/b0_s960_v1/operating_point_v1/selection.json`; `docs/evidence/2026-10-29-b0-operating-point.json`. |
| E10 | B1 causal và12 chuỗi | `src/b0_diagnostics.py`; `configs/b1_causal_diagnostics_v1.json`; `outputs/training/b0_s960_v1/temporal_diagnostics_v1/report.json`. |
| E11 | Pipeline và trainer thực tế | `src/video_pipeline.py`; `scripts/train_b0.py`; `src/kaggle_recipe.py`; `scripts/kaggle_b0.py`. |
| E12 | Phục hồi và Kaggle | `docs/GETTING_STARTED.md`; `data/download_catalog.json`; `docs/kaggle_training.md`; các deployment/retrieval receipt dưới `outputs/kaggle/`. |
| E13 | Dashboard đã triển khai 02–04/11 | `frontend/README.md`; `src/dashboard_data.py`; `src/dashboard_cloud.py`; `frontend/src/`; `tests/test_dashboard.py`; một lựa chọn run, polling local/Kaggle chỉ đọc, không tự fetch/train. |

### Những thông tin vẫn chưa đủ bằng chứng

Chưa có FPS ghi hình nguồn CADP001407; chưa có số camera/sự kiện độc lập đã xác minh cho toàn bộ grouping; chưa rà ngữ nghĩa đầy đủ từng bbox lớn; chưa có evaluator và test sự kiện độc lập đầy đủ, false alerts/giờ, event delay hoặc benchmark online toàn pipeline. Chưa đo GT tracking hay train MLP/GRU. Nguyên nhân gốc serialize checkpoint và một số chênh lệch CSV–revalidation chưa được cô lập. Toàn văn YOLOv8 accident [R1] và nhãn/mã đầy đủ của một số paper chưa truy cập được. Các giới hạn này được giữ như phần thiếu bằng chứng, không điền bằng suy đoán.

## Phụ lục 2. Tên thí nghiệm và checkpoint cần truy xuất

| Tên ngắn trong báo cáo | Tên thư mục run dưới outputs/training |
| --- | --- |
| Pilot47 | `b0_basic_pilot_v1` |
| Verified1750 | `b0_verified_pilot_v1` |
| LR0,001 có resume | `b0_verified_lr001_val_v1` |
| LR0,001 đủ 60 | `b0_verified_lr001_full60_v1` |
| Normal-expanded | `b0_normal_expanded_v1` |
| s960 | `b0_s960_v1` |
| Hardneg | `b0_s960_hardneg_v1` |
| Kaggle V9 | `b0_s960_full_kaggle_v1` — local chủ yếu giữ metadata chọn lọc, không đủ weights. |
| Kaggle V10 | `b0_s960_adamw_kaggle_v2` |
| Kaggle V11 | `b0_s960_sgd_kaggle_v3` |
| Kaggle V12 | `b0_s960_sgd_low_lr_kaggle_v4` |

SHA-256 đầy đủ của best/last V11–V12 và checkpoint s960 đang khóa nằm trong `experiment.json`, `artifacts_manifest.json` và retrieval receipt tương ứng; báo cáo giữ đường dẫn thay vì lặp chuỗi hash dài. Trên web, `K09`–`K12` là version notebook Kaggle; `L01`–`L09` là alias cho run local cũ. Không nhãn hiển thị nào đổi ID run hoặc tự thay checkpoint vận hành.
