**TỪ ĐIỂN THUẬT NGỮ CỦA PROJECT**

# AdamW — Adam với weight decay tách riêng

AdamW là thuật toán tối ưu dùng gradient để điều chỉnh trọng số mạng, đồng thời áp dụng weight decay riêng với phép cập nhật của Adam. So với SGD, nó dùng thông tin trung bình gradient và độ lớn gradient để điều chỉnh bước đi theo từng tham số. Ví dụ Version 10 dùng AdamW với learning rate ban đầu 0,0003; không thể kết luận nó tốt hơn SGD nếu chưa so kết quả trên cùng validation.

# Cosine learning-rate schedule — Lịch giảm tốc độ học theo đường cosine

Đây là cách giảm dần learning rate theo một đường cong giống nửa chu kỳ cosine. Learning rate thường thay đổi mạnh hơn ở giữa và giảm chậm hơn gần cuối. Version 10 dùng `cos_lr=True`, tối đa 60 epoch; đây là cosine một lượt, không áp dụng warm restart như toàn bộ phương pháp SGDR trong paper.

# NBS — Nominal Batch Size, kích thước batch danh nghĩa

Trong Ultralytics, NBS là mốc dùng để tính số batch cần tích lũy gradient và điều chỉnh weight decay. Nó không nhất thiết là số ảnh cùng lúc nằm trong GPU. Ví dụ batch thực 8 với `nbs=32` thường tích lũy khoảng 4 batch trước một lần cập nhật sau warmup; trong warmup hoặc do làm tròn, số bước có thể khác.

Dùng **Ctrl+F** để tìm tên tiếng Anh hoặc viết tắt; VS Code Outline liệt kê từng header cấp 1. Mỗi mục ghi tên, nghĩa tiếng Việt, giải thích và ví dụ. Các ký hiệu B0/B1/B2/T0/B3 là quy ước của project; tên sản phẩm/dataset không được tự mở rộng khi nguồn không quy định. Gặp từ mới thì bổ sung vào file chung này.

Ví dụ là minh họa, không phải kết quả đo. Quy tắc hiện hành xem [README](../README.md), nội dung công trình xem [literature review](LITERATURE_REVIEW.md). Tên dataset/công cụ đối chiếu thêm với [CADP](https://ankitshah009.github.io/accident_forecasting_traffic_camera.html), [UA-DETRAC](https://arxiv.org/abs/1511.04136), [VATIC](https://github.com/cvondrick/vatic) và [A3D](https://arxiv.org/abs/1903.00618).

# CV — Computer Vision (Thị giác máy tính)

Computer Vision là lĩnh vực giúp máy tính trích thông tin từ ảnh và video. Các nhiệm vụ có thể là nhận biết ảnh có gì, xác định vị trí đối tượng hoặc phân tích thay đổi qua thời gian; chúng không phải cùng một bài toán.

**Ví dụ:** Trong đồ án, tìm xe bằng YOLO là một nhiệm vụ CV; xác định xe có va chạm hay không cần thêm nhãn và cách ra quyết định phù hợp.

# CCTV — Closed-Circuit Television (Camera giám sát)

CCTV là hệ thống camera truyền hình giám sát. Project chủ yếu hướng tới fixed camera, nghĩa là góc quan sát được đặt tương đối cố định; điều này khác với camera gắn trên xe đang chạy.

**Ví dụ:** Camera trên cột nhìn xuống giao lộ thuộc bối cảnh mục tiêu. Một video có rung hoặc thay góc vẫn cần được kiểm, không chỉ dựa vào tên CCTV.

# Dashcam và ego view — Camera trên xe và góc nhìn từ xe

Dashcam là camera lắp trên phương tiện. Ego view nhấn mạnh góc nhìn của chính phương tiện đang di chuyển, nên nền cảnh và chuyển động ảnh phụ thuộc cả camera lẫn các xe xung quanh.

**Ví dụ:** Kết quả tốt trên DAD/CCD không tự chứng minh phương pháp hoạt động tương đương với camera CCTV đứng yên.

# Object detection — Phát hiện đối tượng

Object detection tìm vị trí và loại đối tượng trong ảnh, thường trả bbox, class và confidence. Nó mô tả những gì nhìn thấy, chưa mặc định hiểu quan hệ hoặc sự kiện giữa các đối tượng.

**Ví dụ:** YOLO trả hai bbox car chỉ chứng minh model dự đoán có hai ô tô, chưa kết luận chúng va chạm.

# Collision detection — Phát hiện va chạm

Collision detection trong project là nhận biết va chạm đang hoặc vừa xảy ra. Nhãn, khoảng sự kiện và cách ghép cảnh báo phải được định nghĩa; hai xe gần nhau hoặc phanh gấp chưa đủ tạo một sự kiện positive.

**Ví dụ:** Một cảnh giao bbox do phối cảnh có thể là hard negative, dù detector xe vẫn dự đoán đúng.

# Accident anticipation — Dự báo trước tai nạn

Anticipation dự đoán nguy cơ trước khi sự kiện xảy ra. Nó khác detection ở thời điểm cần ra quyết định và cách đánh giá; cảnh trước onset có thể là đầu vào dự báo nhưng không tự là nhãn positive cho detection.

**Ví dụ:** RARE nghiên cứu anticipation; không lấy metric dự báo của nó thay metric phát hiện va chạm của đồ án.

# Classification — Phân loại

Classification gán một hoặc nhiều nhãn cho đơn vị đầu vào, chẳng hạn một ảnh hoặc cả clip. Nhãn này thường không chỉ ra vị trí bbox hay ranh giới thời gian nếu bài toán không yêu cầu những đầu ra đó.

**Ví dụ:** Folder normal của TAD cho nhãn clip âm; folder accident không tự cho bbox accident ở từng frame.

# Localization — Định vị

Localization xác định sự kiện hay đối tượng nằm ở đâu trong ảnh hoặc ở khoảng nào trong video. Spatial localization nói về vị trí không gian; temporal localization nói về mốc hoặc khoảng thời gian.

**Ví dụ:** Bbox accident là định vị trong ảnh; onset/end là định vị sự kiện theo thời gian.

# Anomaly — Bất thường

Anomaly là hành vi hoặc quan sát khác thường so với bối cảnh bình thường. Khái niệm này rộng hơn collision: xe dừng sai chỗ, người đi vào đường cao tốc hoặc vật rơi có thể bất thường nhưng không phải va chạm xe–xe.

**Ví dụ:** Không gộp tất cả nhãn anomaly của một dataset thành positive accident cho B0.

# Near miss — Tình huống suýt va chạm

Near miss là tương tác nguy hiểm nhưng không xảy ra tiếp xúc va chạm trong phạm vi được quan sát rõ. Nó rất hữu ích để kiểm báo sai vì có thể mang nhiều dấu hiệu giống tai nạn, như phanh gấp hoặc đổi hướng.

**Ví dụ:** Một xe đánh lái tránh xe khác thành công có thể là hard negative cho collision detection.

# Baseline — Phương án đối chứng

Baseline là cách giải bài toán được dùng làm mốc so sánh. Nó phải có đầu vào, đầu ra, cấu hình và phép đánh giá cụ thể; không nhất thiết là mô hình cũ hoặc yếu nhất.

**Ví dụ:** Nếu GRU giảm báo sai thì cần biết nó hơn một bộ luật hoặc cách làm mượt đơn giản ở mức recall nào.

# B0 — Ký hiệu baseline ảnh của project

B0 là nhãn định danh trong kế hoạch, không phải tên chuẩn của một thuật toán. Nó chỉ YOLO được fine-tune để phát hiện bbox vùng accident trên từng ảnh/frame; hiện chưa có run train B0.

**Ví dụ:** Chạy yolov8n.pt pretrained tìm phương tiện chưa tạo ra B0 accident.

# B1 — Baseline ảnh có lọc thời gian

B1 là B0 cộng bước lọc score bằng thông tin hiện tại/quá khứ, như EMA hoặc k-of-N. Mục đích là hạn chế dự đoán chập chờn; mức giảm báo sai cần so cùng recall và độ trễ.

**Ví dụ:** Một frame score cao đơn lẻ có thể chưa đủ làm B1 phát cảnh báo.

# B2 — Baseline luật chuyển động

B2 là detector phương tiện, tracker, bước chọn cặp và bộ luật kiểm diễn biến chuyển động. Luật cần được mô tả và chọn ngưỡng có kiểm soát; không phải cứ chạy tracking thì đã có B2.

**Ví dụ:** Tính khoảng cách tương đối và đổi hướng là chuẩn bị feature, chưa tự có kết luận va chạm.

# T0 — Baseline MLP trên đặc trưng hiện tại

T0 là ký hiệu đối chứng dùng Multi-Layer Perceptron, tức mạng perceptron nhiều lớp, trên feature tại thời điểm xét. Nó giúp tách lợi ích của mô hình chuỗi khỏi lợi ích của bản thân bộ feature.

**Ví dụ:** T0 và GRU phải dùng candidate, split và feature tương thích để so được vai trò thời gian.

# B3 hoặc T1 — Verifier GRU theo quá khứ

B3/T1 trong kế hoạch là mô hình Gated Recurrent Unit một chiều học chuỗi feature quá khứ. Đây là phương án dự kiến; chỉ thử sau khi dữ liệu, nhãn chuỗi và baseline đã đủ căn cứ.

**Ví dụ:** Không đổi thành BiGRU nhìn cả clip rồi vẫn tuyên bố cảnh báo online không cần đợi.

# Pilot — Bộ mẫu thử quy trình

Pilot là tập nhỏ dùng kiểm dữ liệu, định dạng nhãn, đường chạy và các lỗi dễ gặp. Nhiều frame từ cùng một chuỗi vẫn có tương quan cao, nên số frame lớn chưa đồng nghĩa bộ đánh giá đáng tin cậy.

**Ví dụ:** 31 frame có bbox thuộc bốn STTAD chưa phải 31 sự kiện độc lập.

# Smoke test — Kiểm tra chạy cơ bản

Smoke test là lần thử ngắn để phát hiện lỗi lớn như không mở được video, không nạp được model hoặc không ghi được output. Nó không thay cho đánh giá accuracy, khả năng tổng quát hay tính real-time.

**Ví dụ:** MP4 đầu ra đọc đủ frame cho biết pipeline chạy được, chưa cho biết model nhận tai nạn đúng.

# Frame — Khung hình

Frame là một ảnh trong chuỗi video. Khi giải mã, mỗi frame trở thành một mảng pixel để code xử lý; cần biết frame đó thuộc nguồn nào và có số thứ tự theo quy ước nào.

**Ví dụ:** Một lần cap.read() thành công thường đưa ra một frame BGR cho YOLO.

# Frame index, 0-based và 1-based — Chỉ số khung hình

Frame index là số thứ tự quan sát. 0-based bắt đầu từ 0, còn 1-based bắt đầu từ 1; số tên file và thứ tự decoder không được tự coi là giống nhau khi chưa đối chiếu.

**Ví dụ:** CADP có 0.jpg; pool TAD dùng chỉ số decode bắt đầu 0. Giữ đúng convention khi join nhãn.

# Resolution và dimensions — Độ phân giải, kích thước ảnh

Kích thước ảnh thường ghi width × height, đơn vị pixel. Nó khác số frame và ảnh hưởng tới cách chuẩn hóa bbox; thay kích thước ảnh phải giữ phép đổi tọa độ nhất quán.

**Ví dụ:** Ảnh 1280×720 có chiều rộng 1280, chiều cao 720; không phải video có 1280 frame.

# Pixel — Điểm ảnh

Pixel là một vị trí lấy mẫu màu trong ảnh số. Tọa độ ảnh thường lấy gốc ở góc trên trái, x tăng sang phải và y tăng xuống dưới; khoảng cách pixel không tự là khoảng cách ngoài đường.

**Ví dụ:** Xe dịch 10 pixel chưa thể đổi thành mét nếu chưa có hiệu chuẩn phù hợp.

# FPS — Frames Per Second (Số khung hình mỗi giây)

FPS biểu thị một tốc độ frame nhưng phải nói rõ tốc độ ghi hình, trình chiếu hay xử lý. Một con số FPS đứng riêng không cho biết timing nguồn đã được xác minh hay hệ thống chạy đủ nhanh.

**Ví dụ:** 25 FPS trong metadata MP4 khác kết quả đo chương trình xử lý được 25 frame mỗi giây.

# Source FPS — FPS ghi hình của nguồn

Source FPS chỉ tốc độ lấy frame của nguồn khi có căn cứ thích hợp. Để tính thời gian, vận tốc hoặc độ trễ của sự kiện gốc, còn cần biết chuỗi có bị lấy mẫu, cắt hoặc đổi tốc độ không.

**Ví dụ:** Không dùng 20 FPS của video ghép CADP để suy thời gian capture của 001407.

# Container FPS và display FPS — FPS khai báo và trình chiếu

Container FPS là thông tin trong file video; display FPS là tốc độ chọn để phát hoặc ghép ảnh. Cả hai có thể khác tốc độ nguồn, nhất là khi video đã render hoặc tái mã hóa.

**Ví dụ:** Ghép 100 ảnh thành MP4 20 FPS tạo 5 giây trình chiếu, chưa chứng minh sự kiện gốc kéo dài 5 giây.

# Processing FPS — Tốc độ xử lý frame

Processing FPS là số frame thực sự xử lý chia cho thời gian chạy được đo. Phải nêu có tính decode, tracking, vẽ, ghi evidence và các bước khác hay chỉ đo model forward.

**Ví dụ:** FPS riêng YOLO cao chưa bảo đảm toàn hệ thống không bị tăng hàng đợi.

# Timestamp — Dấu thời gian

Timestamp gắn một quan sát với mốc thời gian trong nguồn hoặc hệ thống. Cần phân biệt thời gian sự kiện gốc, thời gian phát video và thời gian chương trình nhận/xử lý frame.

**Ví dụ:** Tính event delay phải ghép alert và onset trong cùng hệ thời gian.

# Decode — Giải mã

Decode chuyển dữ liệu ảnh/video nén thành pixel mà chương trình đọc được. Đuôi file hoặc metadata không bảo đảm nội dung hợp lệ; phải thực sự thử đọc và kiểm số frame/kích thước.

**Ví dụ:** Hai file STTAD đuôi JPG không decode được được giữ nguyên raw nhưng loại khỏi pool ảnh.

# Codec và H.264 — Cách mã hóa media

Codec là cơ chế mã hóa/giải mã ảnh hoặc video; H.264 là một chuẩn mã hóa video. MP4 là định dạng chứa dữ liệu, không đồng nghĩa mọi MP4 dùng cùng codec hoặc giải mã được như nhau.

**Ví dụ:** FFmpeg có thể ghi video H.264 vào container MP4 để mở lại bằng trình phát thông dụng.

# RGB và BGR — Red Green Blue và Blue Green Red

RGB là thứ tự kênh đỏ–lục–lam, BGR là lam–lục–đỏ. Hai mảng cùng kích thước nhưng khác thứ tự kênh có thể cho màu sai nếu đọc hoặc hiển thị bằng thư viện khác quy ước.

**Ví dụ:** OpenCV thường trả BGR; cần kiểm khi chuyển sang công cụ đòi RGB.

# NumPy array và shape — Mảng số và kích thước mảng

NumPy là thư viện mảng số trong Python; shape mô tả số phần tử theo từng chiều. Ảnh màu thường có chiều cao, chiều rộng và số kênh, khác thứ tự width × height ghi trong metadata.

**Ví dụ:** Frame shape (720,1280,3) tương ứng ảnh rộng 1280 và cao 720.

# Bbox — Bounding Box (Hộp bao)

Bounding box là hộp chữ nhật mô tả vị trí/kích thước đối tượng hoặc vùng trong ảnh. Hộp có ý nghĩa gì phụ thuộc nhiệm vụ và nhãn, không chỉ phụ thuộc hình dạng tọa độ.

**Ví dụ:** Bbox car của detector xe không được tự coi là bbox accident-region của B0.

# xyxy — Tọa độ hai góc của hộp

xyxy thường chỉ xmin, ymin, xmax, ymax. Với quy ước đang dùng trong công cụ nguồn, chiều rộng là xmax−xmin và chiều cao là ymax−ymin; không tự thêm hiệu chỉnh một pixel khi chưa có căn cứ.

**Ví dụ:** Hộp (100,50,300,150) rộng 200 và cao 100 pixel.

# xywh và cxcywh — Góc hoặc tâm kèm kích thước hộp

xywh thường gồm góc x,y và width,height; cxcywh dùng tâm hộp thay góc. Tên cột/API quyết định ý nghĩa chính xác, nên cùng bốn số không được đọc tùy ý theo một định dạng khác.

**Ví dụ:** Hộp xyxy (100,50,300,150) có cxcywh pixel là (200,100,200,100).

# Normalized coordinates — Tọa độ chuẩn hóa

Tọa độ chuẩn hóa chia các đại lượng theo chiều rộng/chiều cao ảnh để biểu diễn tỷ lệ. Phải dùng đúng kích thước ảnh gắn với nhãn; chuẩn hóa không sửa bbox sai hoặc thiếu nhãn.

**Ví dụ:** Ảnh 400×200, hộp trên có cxcywh chuẩn hóa 0.5,0.5,0.5,0.5.

# YOLO label format — Định dạng nhãn YOLO

Một dòng detection label YOLO thường là class_id cx cy w h, với tọa độ tâm và kích thước chuẩn hóa. File TXT có năm số chưa chắc là định dạng này, vì nguồn khác có thể ghi class và xyxy pixel.

**Ví dụ:** TXT STTAD phải chuyển đổi trước; không đưa nguyên dòng class xmin ymin xmax ymax vào train YOLO.

# ROI — Region of Interest (Vùng quan tâm)

ROI là vùng ảnh được chọn để phân tích hoặc giới hạn tìm kiếm. Nó có thể giúp tập trung vào mặt đường nhưng phải có lý do và áp dụng nhất quán khi so các phương án.

**Ví dụ:** Bỏ vùng trời khỏi bước chọn cặp không có nghĩa mọi đối tượng ngoài ROI đã được gán nhãn âm.

# Crop và padding — Cắt ảnh và thêm viền

Crop lấy một vùng con; padding thêm phần viền vào ảnh hoặc vùng. Hai thao tác làm thay đổi hệ tọa độ hay ngữ cảnh, nên phải lưu phép biến đổi khi dùng với bbox.

**Ví dụ:** Không cắt ảnh rồi giữ nguyên tọa độ nhãn toàn ảnh, cũng không tự nới nhãn gốc bằng padding.

# Overlay, preview và render — Hình chú thích và bản dựng để xem

Overlay là phần vẽ thêm lên ảnh; preview là bản xem; render là quá trình dựng đầu ra. Đây có thể là nhãn tác giả hoặc dự đoán model và cần ghi rõ loại nào.

**Ví dụ:** Video đã vẽ bbox GT chỉ dùng kiểm nhãn, không dùng làm ảnh sạch đầu vào đánh giá detector.

# Dataset, sequence và clip — Bộ dữ liệu, chuỗi và đoạn video

Dataset là tập dữ liệu; sequence là một chuỗi nguồn; clip là một đoạn video. Bản cắt, bản ghép hoặc preview từ cùng nguồn không tự tạo một sự kiện độc lập mới.

**Ví dụ:** MVI_20011 và clip 10 giây của nó phải giữ cùng nhóm nguồn khi chia tập.

# CADP — Car Accident Detection and Prediction

CADP là bộ dữ liệu phục vụ phát hiện/dự báo tai nạn từ CCTV, giới thiệu trong paper về phân tích tai nạn bằng camera giao thông. Phạm vi nhãn thật sự có sẵn phải kiểm theo từng subset và file tải được.

**Ví dụ:** Project đã đối chiếu 001407 với 1407.txt; điều đó không xác nhận toàn bộ CADP đã có nhãn tương ứng trên máy.

# STTAD — Bộ dữ liệu sự kiện tai nạn theo không gian và thời gian

STTAD là tên bộ dữ liệu trong công trình Surveillance-based Spatial Temporal Traffic Accident Detection: A novel Dataset and tailored Algorithm. Nó mô tả vùng sự kiện theo frame; tên công trình đầy đủ được giữ thay vì tự suy diễn cách mở từng chữ ngoài nguồn.

**Ví dụ:** Phần public examples đang cung cấp bbox vùng B0, không đồng nghĩa toàn bộ dataset paper đã được phát hành.

# TAD — Traffic Accident Detection (Phát hiện tai nạn giao thông)

TAD vừa là cách viết tắt tên nhiệm vụ vừa là tên benchmark trong paper của Xu et al. Khi đọc tài liệu cần xem nó đang chỉ bài toán chung hay bộ dữ liệu cụ thể, tránh nhầm với STTAD.

**Ví dụ:** ZIP TAD đã kiểm trong project có clip accident/normal nhưng không có bbox TXT đi kèm.

# UA-DETRAC — University at Albany DETection and tRACking

UA-DETRAC là benchmark phát hiện và theo dõi nhiều đối tượng, chủ yếu phương tiện giao thông. Annotation xe của nó phục vụ detection/tracking, không tự gán nhãn collision cho video.

**Ví dụ:** Ba chuỗi DETRAC đang được coi là âm nhờ review người dùng, không vì XML không có class accident.

# DAD, CCD và A3D — Các bộ dữ liệu camera trên xe

DAD là Dashcam Accident Dataset; CCD là Car Crash Dataset; A3D là AnAn Accident Detection. Đây là tên dữ liệu xuất hiện trong literature detection/anticipation, với protocol riêng cần đọc ở từng paper.

**Ví dụ:** Không chuyển nguyên kết quả của DAD/CCD sang kết luận camera CCTV cố định của project.

# Annotation và label — Thông tin gán nhãn

Annotation là thông tin gắn với dữ liệu như bbox, ID và khoảng frame; label có thể chỉ một lớp hoặc giá trị cụ thể trong đó. Phải biết nhãn thuộc mức object, frame, clip hay event.

**Ví dụ:** Clip normal là nhãn toàn đoạn, còn bbox accident cần vị trí tại frame cụ thể.

# GT — Ground Truth (Nhãn tham chiếu)

Ground truth là nhãn được chọn làm chuẩn để học/đánh giá, có nguồn và quy tắc xác định. Nó không đồng nghĩa mọi dòng nguồn đều đầy đủ hoặc không có lỗi; cần lưu chất lượng và phạm vi.

**Ví dụ:** Bbox model tự dự đoán không trở thành GT chỉ vì trông hợp lý.

# Author annotation — Nhãn do tác giả hoặc nguồn cung cấp

Author annotation là thông tin được phát hành cùng nguồn dữ liệu. Cần giữ nguyên raw và phân biệt nó với mọi chuyển đổi, rà soát hoặc nhãn dẫn xuất của project.

**Ví dụ:** Đổi bbox STTAD sang YOLO giữ origin tác giả; không đổi thành user review.

# User review — Xác nhận của người dùng

User review ghi điều người dùng thực sự đã kiểm, gắn đúng dữ liệu và phạm vi. Một xác nhận không tự mở rộng sang nguồn khác, loại nhãn khác hoặc thời gian theo giây chưa được đối chiếu.

**Ví dụ:** Xác nhận CADP đúng xe và frame 96–130 không xác nhận FPS nguồn hay mọi bbox region dẫn xuất.

# Derived label và proposal — Nhãn dẫn xuất và đề xuất

Derived label được tính từ dữ liệu/nhãn khác theo quy tắc project; proposal nhấn mạnh trạng thái ứng viên. Cả hai cần provenance và không được trình bày như annotation nguyên bản của tác giả.

**Ví dụ:** Hộp bao hai bbox xe Colliding của CADP được giữ auxiliary, không nhập lẫn GT region STTAD.

# Accident region và envelope — Vùng sự kiện và hộp bao tổng

Accident region mô tả vùng tai nạn theo định nghĩa nhiệm vụ. Envelope là hộp trục song song nhỏ nhất bao các hộp được chọn; phép tính hình học này không tự chứng minh vùng đó là GT.

**Ví dụ:** STTAD có nhãn sự kiện nguồn; envelope CADP là kết quả project tính riêng.

# Class và class ID — Loại nhãn và mã lớp

Class là loại đối tượng/sự kiện; class ID là số đại diện trong một hệ nhãn cụ thể. Cùng số có thể mang nghĩa khác ở dataset/model khác; cần bảng ánh xạ và giữ mã nguồn.

**Ví dụ:** Source class 11 của STTAD có thể ánh xạ về project accident class 0, không liên quan track ID 11.

# Positive và negative — Nhãn có và không có sự kiện

Positive là mẫu dương, tức có điều đang cần tìm; negative là mẫu âm, tức có căn cứ không có điều đó trong phạm vi được gán nhãn. Với B0, cần tìm vùng tai nạn trên một frame: dương cần bbox accident hợp lệ, âm vẫn có thể chứa nhiều xe. Thiếu file nhãn hoặc chưa nhìn rõ không tự là âm; nhãn của cả clip không tự áp cho mọi frame/bbox.

**Ví dụ:** Hai xe đang va chạm, có bbox vùng đã kiểm là mẫu dương. Hai xe chạy sát nhưng không va chạm, đã có căn cứ nhãn là mẫu âm. Trong TXT YOLO `0 cx cy w h`, số 0 là class accident, không có nghĩa mẫu âm. Xem [điều kiện mẫu hợp lệ](../docs/b0_label_protocol.md#mẫu-dương-mẫu-âm-và-mẫu-chưa-biết).

# Unknown và uncertain — Chưa biết và chưa đủ chắc chắn

Unknown thường dùng khi thiếu thông tin/nhãn; uncertain dùng khi quan sát còn mơ hồ hoặc không đủ căn cứ. Cả hai cần giữ riêng với positive/negative thay vì ép nhãn để tăng số mẫu.

**Ví dụ:** Frame STTAD không có TXT được giữ unknown, không sinh empty label.

# Hard negative — Mẫu âm dễ nhầm

Hard negative là cảnh thật sự không có sự kiện mục tiêu nhưng có tín hiệu dễ làm hệ thống báo sai. Nó giúp kiểm model có phân biệt được va chạm với các tương tác thường gặp hay không.

**Ví dụ:** Xe đỗ sát, kẹt xe, near miss và bbox chồng do phối cảnh là các nhóm cần xem xét.

# VATIC — Video Annotation Tool from Irvine, California

VATIC là công cụ gán nhãn video; file export có thể chứa track ID, tọa độ, frame và các flags. Phải đọc cấu trúc thực tế của export, không coi mọi TXT annotation là YOLO label.

**Ví dụ:** 1407.txt được bộ đọc riêng giải thích outside/occluded/generated và thuộc tính Colliding.

# Colliding — Thuộc tính đang va chạm

Colliding là thuộc tính trong annotation nguồn của CADP, gắn với đối tượng theo frame. Cần đọc cùng ID, bbox và flags để biết nó mô tả xe nào và khoảng nào.

**Ví dụ:** ID0 và ID2 có Colliding 96–130; đây không phải class accident mặc định trong YOLO COCO.

# Outside và visible — Ngoài ảnh và còn hiện diện

Theo quy ước công cụ CADP, outside đánh dấu đối tượng ngoài vùng ảnh; visible được tính là 1−outside. Visible ở đây chỉ nói còn hiện diện, không bảo đảm đối tượng nhìn thấy đầy đủ.

**Ví dụ:** Một xe visible vẫn có thể có occluded=1 và cần xử lý khác khi tạo nhãn dẫn xuất.

# Occluded — Bị che khuất

Occluded mô tả tình trạng đối tượng bị vật khác che theo annotation nguồn. Nó khác ngoài ảnh và khác model bỏ sót; nếu nguồn không có flag thì phải ghi không được cung cấp.

**Ví dụ:** Không suy hình dạng xe bị khuất rồi tự vẽ bù bbox làm GT.

# Generated trong VATIC — Cờ do công cụ nguồn sinh

Generated cho biết dòng annotation được hệ thống nguồn sinh/nội suy theo quy ước export. Nó không mặc định nghĩa nhãn sai, nhãn do AI project tạo hoặc có thể xóa đi mà không mất thông tin.

**Ví dụ:** 35 proposal CADP có generated nguồn vẫn giữ cờ này trong bảng chuẩn hóa.

# Ignore region, FarRegion và CrowdRegion — Vùng cần xử lý riêng

Ignore region là khu vực không gán nhãn đầy đủ hoặc được nguồn dành cho cách xử lý riêng. FarRegion/CrowdRegion là tên vùng trong dữ liệu; không phải class xe hay accident.

**Ví dụ:** Không biến các xe chưa được gán nhãn trong vùng đông/xa thành background negative một cách mặc định.

# Separator — Dấu phân cảnh

Separator trong annotation nguồn dùng phân tách cảnh theo quy ước công cụ. Nó cần giữ trong audit để nhận ra thay cảnh nhưng không đưa vào danh sách object class của detector.

**Ví dụ:** Một dấu Separator không trở thành bbox accident hoặc một phương tiện tham gia.

# Onset, end và inclusive interval — Mốc đầu, cuối và khoảng gồm hai đầu

Onset/end là ranh giới sự kiện theo quy tắc nhãn. Inclusive interval tính cả frame đầu và cuối; khi chỉ xác minh theo frame thì không tự đổi thành giây của nguồn.

**Ví dụ:** 96–130 inclusive gồm 130−96+1=35 frame, không tự biết tương ứng bao nhiêu giây capture.

# Empty label — File nhãn rỗng

Empty label là file annotation không có bbox cho task đang train, chỉ đúng khi frame được coi là âm có căn cứ. Nó khác việc không tồn tại nhãn, file lỗi hoặc chưa được gán nhãn.

**Ví dụ:** Không tạo TXT rỗng cho 145 frame STTAD unknown chỉ để đủ cấu trúc dataset.

# Label scope và coverage — Phạm vi và độ phủ nhãn

Scope nói nhãn có ý nghĩa ở mức nào; coverage nói dữ liệu đã được gán nhãn đầy đủ đến đâu. Nhãn đúng cho một đối tượng không chứng minh mọi vùng khác trong ảnh đều được rà.

**Ví dụ:** Có một bbox sự kiện không tự xác nhận toàn bộ clip hoặc mọi frame chưa có TXT.

# Manifest và inventory — Danh mục asset và kiểm kê nhóm nguồn

Manifest ghi từng asset cùng đường dẫn, hash và provenance. Inventory nhóm theo chuỗi/nguồn để nhìn số mẫu gốc; hai bảng có mục đích khác nhau và không được đếm cùng đơn vị.

**Ví dụ:** 18 asset gồm cả bản dẫn xuất, không có nghĩa 18 tai nạn hoặc camera độc lập.

# Asset và provenance — Đơn vị dữ liệu và nguồn gốc

Asset là file hoặc chuỗi được đăng ký. Provenance lưu nó đến từ đâu, tạo bằng bước nào và liên hệ với nguồn gốc; nhờ đó phân biệt raw, bản cắt, preview và dự đoán.

**Ví dụ:** Một MP4 ghép từ ảnh DETRAC phải nối lại được về đúng thư mục chuỗi.

# Fingerprint, SHA-256 và CRC — Dấu nhận diện và kiểm toàn vẹn

Fingerprint là dấu nhận diện nội dung. SHA-256 là Secure Hash Algorithm 256-bit; CRC là Cyclic Redundancy Check. Chúng hỗ trợ kiểm nội dung hoặc lỗi dữ liệu, không chứng minh nhãn đúng về ngữ nghĩa.

**Ví dụ:** CRC member ZIP và SHA video giúp biết đúng file đã lấy; review vẫn cần phạm vi riêng.

# pHash và Hamming distance — Perceptual Hash và khoảng cách bit

Perceptual hash tạo dấu tóm tắt bố cục ảnh để tìm mẫu tương tự; Hamming distance đếm số bit khác nhau. Ảnh gần hash là ứng viên kiểm lại, không tự chứng minh cùng camera hoặc cùng sự kiện.

**Ví dụ:** Cặp biên DETRAC được xem trực quan thêm sau khi hash gợi ý rất gần.

# HTTP Range và ZIP central directory — Đọc từng phần và danh mục ZIP

HTTP là Hypertext Transfer Protocol; Range yêu cầu một đoạn byte thay vì cả file. ZIP central directory chứa danh mục member, giúp biết gói có gì trước khi tải hoặc giải nén.

**Ví dụ:** Đọc danh mục TAD không đồng nghĩa đã tải/giải mã toàn bộ video hoặc kiểm CRC toàn archive.

# Pool và reference index — Tập tham chiếu chuẩn bị

Pool/reference index là danh sách mẫu ứng viên có nguồn và nhãn để tổ chức bước sau. Nó có thể trỏ tới ảnh hoặc frame trong video, chưa là bộ train đã materialize và chia tập.

**Ví dụ:** TAD video_frame_reference cần decode đúng chỉ số, không được đưa MP4 vào dataloader như một JPG.

# Audit, evidence và snapshot — Kiểm tra, bằng chứng và bản ghi thời điểm

Audit là quá trình kiểm có báo cáo; evidence là bằng chứng hỗ trợ kết luận; snapshot là bản lưu trạng thái tại một thời điểm. Phải đọc cùng ngày, nguồn và phạm vi kiểm.

**Ví dụ:** JSON trên Git mô tả máy phát triển trước đây, không chứng minh media đã có sau clone.

# Model, weights và checkpoint — Mô hình, trọng số và bản lưu

Model là cấu trúc tính toán; weights là tham số đã học; checkpoint là bản lưu để dùng hoặc tiếp tục quá trình học, có thể kèm trạng thái optimizer. File model không tự xác định task nếu chưa xem class/config.

**Ví dụ:** yolov8n.pt đang dùng có class phương tiện COCO, không tự có class accident.

# Pretrained, fine-tune và inference — Học trước, học tiếp và suy luận

Pretrained nghĩa tham số đã được học trước; fine-tune là học tiếp trên dữ liệu mục tiêu; inference là chạy dự đoán bằng tham số hiện có. Ba việc có đầu ra và cách kiểm khác nhau.

**Ví dụ:** Chạy video qua pretrained YOLO là inference, chưa phải một lượt train B0.

# YOLO — You Only Look Once

YOLO là họ mô hình phát hiện đối tượng. YOLOv8n là biến thể nhỏ đang dùng; chữ n chỉ mức nano trong họ biến thể, không mô tả khả năng nhận tai nạn có sẵn.

**Ví dụ:** Muốn detector accident phải có class, nhãn vùng và bước fine-tune phù hợp, không chỉ đổi tên file weights.

# Ultralytics và PyTorch — Thư viện triển khai và nền tảng học sâu

Ultralytics cung cấp API để nạp, chạy và huấn luyện các model YOLO. PyTorch là nền tảng tensor/học sâu phía dưới; khả năng chạy GPU còn phụ thuộc bản cài và môi trường.

**Ví dụ:** Gọi model.track() dùng YOLO/tracker qua API, còn phép tính neural network chạy bằng PyTorch.

# CNN — Convolutional Neural Network (Mạng neural tích chập)

CNN là mạng học các mẫu không gian trong ảnh bằng các lớp tích chập và thành phần liên quan. Backbone là phần trích biểu diễn; feature là những giá trị số mô tả thông tin đã học.

**Ví dụ:** Feature ảnh không đồng nghĩa tọa độ bbox, và hai loại biểu diễn có chi phí/ý nghĩa khác nhau.

# Confidence và threshold — Điểm tin cậy và ngưỡng quyết định

Confidence là score do model trả theo định nghĩa của nó; threshold là ngưỡng dùng lọc hoặc ra quyết định. Score cao không tự là xác suất đã hiệu chuẩn hoặc bằng chứng vật lý chắc chắn.

**Ví dụ:** Tăng ngưỡng có thể giảm báo sai nhưng cũng làm tăng bỏ sót; phải xem cả recall.

# NMS — Non-Maximum Suppression (Loại bớt dự đoán chồng lặp)

NMS là bước hậu xử lý giữ lại các bbox phù hợp và bỏ bớt hộp trùng cho cùng đối tượng theo score/overlap. Nó hoạt động trên dự đoán, không phải thuật toán giữ danh tính qua video.

**Ví dụ:** Hai hộp cùng một xe có thể được NMS lọc, còn nối xe sang frame sau là việc của tracker.

# IoU — Intersection over Union (Tỷ lệ giao trên hợp)

IoU là diện tích phần giao chia cho diện tích phần hợp của hai vùng. Nó thường dùng so bbox dự đoán với nhãn hoặc hỗ trợ ghép quan sát; giá trị từ 0 đến 1 theo vùng hợp lệ.

**Ví dụ:** IoU cao giữa hai bbox xe có thể do phối cảnh, không đủ xác nhận chúng tiếp xúc ngoài đường.

# Tracking và association — Theo dõi và liên kết quan sát

Tracking duy trì trạng thái đối tượng qua frame; association là bước ghép detection hiện tại vào các track. Sai ở bước này có thể tạo quỹ đạo nhảy dù detector từng frame vẫn tìm thấy xe.

**Ví dụ:** Một xe đổi ID giữa clip cần được xem là lỗi/mất liên kết, không phải xe mới va chạm.

# ByteTrack và bytetrack.yaml — Tracker và file cấu hình

ByteTrack là tên thuật toán theo dõi bằng liên kết detection; không phải từ viết tắt cần tự mở rộng. bytetrack.yaml chọn các tham số/thuật toán tracker trong Ultralytics, không phải trọng số detector.

**Ví dụ:** YOLO tìm bbox; ByteTrack nối bbox theo thời gian để cấp ID tạm.

# Track ID và GT ID — Mã theo dõi và mã nhãn nguồn

ID là Identifier, nghĩa mã định danh trong một phạm vi. Track ID do tracker gán; GT ID do annotation nguồn quy định. Hai hệ mã không tự đồng bộ và có thể đổi theo video.

**Ví dụ:** Không lấy tracker ID 2 để khẳng định đó chính là CADP GT ID2 nếu chưa ánh xạ.

# Persist và reset — Giữ và xóa trạng thái

Persist giữ trạng thái giữa các lần xử lý liên tiếp để nối track; reset bắt đầu trạng thái mới. Phạm vi nên là cùng nguồn/video liên tục, tránh nối nhầm giữa camera độc lập.

**Ví dụ:** Code tạo model mới mỗi run hiện tại; nếu tái dùng cùng model cho video khác phải kiểm reset tracker.

# ID switch và lost track — Đổi mã sai và mất dấu

ID switch xảy ra khi danh tính theo dõi bị tráo hoặc đổi không đúng; lost track là mất quan sát/track. Chúng ảnh hưởng tới feature chuyển động, không chỉ làm chữ ID trên video kém đẹp.

**Ví dụ:** Một bước nhảy tâm bbox do đổi ID có thể bị nhầm thành đổi hướng hoặc gia tốc lớn.

# Kalman filter và Hungarian algorithm — Ước lượng trạng thái và ghép cặp

Kalman filter hỗ trợ dự đoán/cập nhật trạng thái từ quan sát có nhiễu. Hungarian giải bài toán gán cặp theo ma trận chi phí; hai thành phần thường phối hợp trong tracking nhưng làm việc khác nhau.

**Ví dụ:** Dự đoán vị trí không tự quyết định detection nào thuộc xe đó; còn cần association.

# ReID, GMC và BoT-SORT — Ngoại hình, bù chuyển động và tracker khác

ReID là Re-Identification, tái nhận dạng bằng biểu diễn ngoại hình; GMC là Global Motion Compensation, bù chuyển động camera. BoT-SORT là tên tracker trong paper Robust Associations Multi-Pedestrian Tracking, không tự chứng minh mọi cấu hình đều bật ReID.

**Ví dụ:** Chỉ cân nhắc tracker khác khi lỗi association đã được quan sát và đo trong setup của project.

# Centroid và trajectory — Tâm và quỹ đạo

Centroid là tâm đại diện của vùng/đối tượng; với bbox thường dùng trung điểm hộp. Trajectory là chuỗi vị trí theo thời gian hoặc frame, cần gắn đúng ID và chất lượng quan sát.

**Ví dụ:** Tâm bbox dao động khi xe bị che có thể tạo quỹ đạo nhiễu dù xe không đổi hướng thật.

# Velocity, acceleration và heading — Vận tốc, gia tốc và hướng

Velocity mô tả biến đổi vị trí có hướng theo thời gian; acceleration là biến đổi vận tốc; heading là hướng chuyển động được xét. Với ảnh, đây có thể chỉ là đại lượng chiếu và phụ thuộc phối cảnh.

**Ví dụ:** Chưa biết timing/hiệu chuẩn thì báo chuyển vị theo frame, không tự gọi là km/h hoặc gia tốc vật lý.

# Homography và camera calibration — Ánh xạ mặt phẳng và hiệu chuẩn camera

Homography mô tả phép biến đổi giữa các mặt phẳng ảnh trong điều kiện phù hợp. Camera calibration xác định thông tin hình học cần thiết; không thể đổi pixel sang mét chỉ bằng kích thước video.

**Ví dụ:** Mặt đường có thể được ánh xạ sang tọa độ tham chiếu khi có các điểm tương ứng đáng tin cậy.

# Optical flow — Luồng chuyển động điểm ảnh

Optical flow ước lượng sự dịch chuyển của các vị trí ảnh giữa quan sát liên tiếp. Nó chứa thông tin chuyển động rộng hơn tâm bbox nhưng cũng chịu tác động camera, nền và nhiễu.

**Ví dụ:** Chuyển động điểm ảnh trên cả cảnh không tự là quỹ đạo hoặc vận tốc thật của từng xe.

# Candidate, pair và candidate recall — Ứng viên, cặp và độ giữ sự kiện

Candidate là trường hợp được chọn để kiểm sâu; pair là cặp xe; candidate recall đo bước chọn có giữ lại các trường hợp GT cần xét không. Verifier không thể cứu một event bị loại trước khi tới nó.

**Ví dụ:** Chỉ chọn cặp có IoU rất cao có thể bỏ sót va chạm xa camera; phải kiểm bằng dữ liệu nhãn.

# Missing mask — Cờ thiếu quan sát

Missing mask cho biết quan sát/feature nào bị thiếu hoặc không hợp lệ. Nó giúp phân biệt không có phép đo với một giá trị đo thật bằng 0, nhất là khi tracker mất dấu.

**Ví dụ:** Không điền vận tốc 0 cho xe vừa mất track như thể đã xác nhận xe dừng.

# Verifier — Bộ kiểm thêm bằng chứng

Verifier nhận ứng viên và thông tin bổ sung để đánh giá có đủ căn cứ sự kiện không. Nó có thể là luật, MLP hoặc model chuỗi; tên gọi không bảo đảm nó chính xác nếu chưa được đo.

**Ví dụ:** GRU dự kiến là một verifier, không thay cho detector phải tìm được xe đầu vào.

# MLP — Multi-Layer Perceptron (Mạng perceptron nhiều lớp)

MLP là mạng feed-forward gồm các lớp biến đổi feature, thường dùng phân loại hoặc hồi quy. Nó không tự có bộ nhớ chuỗi như mạng hồi tiếp, dù có thể nhận feature tổng hợp của một cửa sổ.

**Ví dụ:** T0 xét feature hiện tại để so với lợi ích của việc mô hình hóa chuỗi bằng GRU.

# GRU — Gated Recurrent Unit (Đơn vị hồi tiếp có cổng)

GRU là thành phần mạng xử lý chuỗi, dùng trạng thái ẩn và các cổng để điều chỉnh thông tin giữ lại/cập nhật. GRU một chiều có thể nhận feature theo thứ tự quá khứ đến hiện tại.

**Ví dụ:** Đầu vào B3 dự kiến là chuỗi chuyển động, không phải chỉ một frame có hai bbox.

# LSTM — Long Short-Term Memory (Bộ nhớ dài–ngắn hạn)

LSTM là một kiểu mạng hồi tiếp có cơ chế cổng và trạng thái nhớ để học phụ thuộc trong chuỗi. Nó là kiến trúc khác với GRU; không mặc định tốt hơn chỉ vì tên nhấn mạnh bộ nhớ.

**Ví dụ:** Muốn so LSTM với GRU phải kiểm cùng dữ liệu, feature, protocol và ngân sách tính toán.

# BiGRU — Bidirectional Gated Recurrent Unit (GRU hai chiều)

BiGRU xử lý chuỗi theo hai hướng. Cần xem chuỗi được đưa vào là buffer quá khứ hay toàn clip; chỉ tên model chưa đủ để biết cảnh báo có dùng thông tin tương lai hay phải chờ bao lâu.

**Ví dụ:** Nhìn toàn clip để phân loại rồi so độ trễ với model online là không cùng protocol.

# GCN và graph — Graph Convolutional Network và đồ thị

Graph là biểu diễn bằng nút và cạnh quan hệ. GCN, mạng tích chập đồ thị, học cách kết hợp thông tin qua những quan hệ đó; cách tạo nút/cạnh là một phần thiết kế quan trọng.

**Ví dụ:** Xe có thể là nút, tương tác là cạnh; thêm graph chưa tự làm phương pháp có tính mới.

# Attention và Transformer — Cơ chế chú ý và kiến trúc xử lý biểu diễn

Attention điều chỉnh mức đóng góp của các thông tin khi tạo biểu diễn. Transformer là họ kiến trúc dùng attention cùng các thành phần khác; nó không tự bảo đảm dùng đúng thứ tự thời gian hoặc không nhìn tương lai.

**Ví dụ:** Một Transformer phân loại cả clip khác một verifier ra quyết định tại frame hiện tại.

# Temporal, spatial và spatiotemporal — Thời gian, không gian và kết hợp

Spatial nói về bố cục/vị trí trong ảnh; temporal nói về quan hệ giữa các quan sát theo thời gian. Spatiotemporal kết hợp cả hai để mô tả diễn biến tại những vị trí cụ thể.

**Ví dụ:** Một bbox là spatial; theo dõi vùng sự kiện qua frame mang thông tin spatiotemporal.

# Causal processing — Xử lý chỉ dùng hiện tại và quá khứ

Trong hệ thống online, causal nghĩa quyết định tại thời điểm t không dùng quan sát sau t. Từ này trong ngữ cảnh xử lý chuỗi không đồng nghĩa đã chứng minh quan hệ nhân quả giữa hành vi và tai nạn.

**Ví dụ:** Luật dùng 15 frame sau overlap phải ghi độ chờ, không gọi là quyết định tức thời tại overlap.

# EMA và k-of-N — Làm mượt và bỏ phiếu theo cửa sổ

EMA là Exponential Moving Average, trung bình trượt hàm mũ để làm mượt score. k-of-N yêu cầu ít nhất k trong N quan sát thỏa điều kiện. Hai cách có tham số ảnh hưởng recall, báo sai và độ chờ.

**Ví dụ:** B1 có thể dùng một trong các cách này, chọn cấu hình trên validation thay vì test.

Trong phép kiểm 29/10, **EMA — Exponential Moving Average**, trung bình trượt hàm mũ, cập nhật `e[t] = 0,3 × score[t] + 0,7 × e[t−1]`, bắt đầu từ0. Bộ đếm **3-of-5** bật khi ít nhất3 trong5frame vừa qua vượt ngưỡng; đợi đủ5frame trước lần bật đầu. Cả hai reset khi đổi video hoặc thiếu frame. Chúng làm giảm chập chờn nhưng không sửa được vùng bị dự đoán nhầm liên tục; EMA còn có thể kéo dài trạng thái ON sau khi score giảm.

# Hard-negative mining — Chọn mẫu âm model dễ nhầm

Là cách ưu tiên những mẫu đã biết là âm nhưng model vẫn cho điểm dương cao. Nhãn âm phải có căn cứ độc lập với dự đoán; một ảnh chưa có annotation không tự trở thành mẫu âm. Trong SSD, tác giả chọn negative anchors theo loss ngay lúc train. Project này chỉ mượn ý tưởng để chọn **frame offline trong nhóm train**, giữ20mốc đều và10frame điểm cao ở10khoảng thời gian mỗi clip. Validation và reserve lấy đều, không được chọn theo score.

**Ví dụ:** Clip do tác giả gắn nhãn normal có xe công vụ và đèn nháy. B0 cũ nhầm đèn là accident; một số frame đó được chọn để fine-tune, với nhãn rỗng do clip normal. Đây không phải dùng dự đoán làm nhãn mới.

# Warm start — Khởi tạo từ trọng số đã học

Warm start dùng checkpoint đã học làm điểm bắt đầu cho một run mới. Khác với **resume**, tiếp tục đúng run đang dở cùng optimizer/lịch học, fine-tune mới thường tạo optimizer và lịch học mới. Run chuẩn bị `b0_s960_hardneg_v1` lấy `b0_s960_v1/weights/best.pt`, giảm learning rate và bật dừng sớm ngay từ đầu; không sửa checkpoint gốc và chưa train trong lượt chuẩn bị.

# Active frame và ON bout — Frame bật và đoạn bật liên tiếp

Active frame là frame mà trạng thái lọc vượt ngưỡng. ON bout là một đoạn các active frame liên tiếp, kết thúc khi trạng thái tắt hoặc thiếu frame. Đây chỉ là thống kê tín hiệu, chưa có chính sách gộp/cooldown để trở thành cảnh báo sự kiện. Một cảnh sáng bị nhầm suốt100frame có thể tạo1bout nhưng vẫn sai100frame; vì vậy ít bout hơn chưa có nghĩa ít thời gian báo sai hơn.

# Window và sampling — Cửa sổ và lấy mẫu

Window là tập quan sát liên tiếp được dùng trong một lần xử lý; sampling là quy tắc/tần suất chọn quan sát. Phải biết đơn vị frame hay giây nguồn và có dùng tương lai không.

**Ví dụ:** Cửa sổ 20 frame không luôn tương ứng 1 giây khi timing nguồn chưa xác minh.

# FSM, cooldown và ring buffer — Máy trạng thái và bộ nhớ cuộn

FSM là Finite-State Machine, máy trạng thái hữu hạn điều khiển chuyển bước cảnh báo. Cooldown hạn chế lặp cảnh báo; ring buffer giữ một đoạn dữ liệu gần nhất để trích evidence mà không giữ cả video trong RAM.

**Ví dụ:** Trạng thái suspected/confirmed không được tự sinh GT, và cooldown không nên che một event mới.

# Train, validation và test — Học, chọn cấu hình và đánh giá cuối

Train dùng học tham số; validation dùng chọn cấu hình/ngưỡng; test dùng đánh giá với lựa chọn đã khóa. Dữ liệu giữa các tập phải độc lập theo nhóm phù hợp, không chỉ khác tên ảnh.

**Ví dụ:** Chỉnh threshold sau khi thấy kết quả test làm đánh giá cuối bị rò thông tin.

# Group split và leakage group — Chia theo nhóm và nhóm chống rò rỉ

Group split giữ mẫu cùng nguồn/camera/sự kiện trong một tập. Leakage group là ràng buộc bảo thủ về các nguồn phải ở cùng nhau; nó không nhất thiết là camera ID vật lý đã xác minh.

**Ví dụ:** Ba DETRAC cùng cảnh được gom để không lọt nền gần giống sang các split khác nhau.

# Data leakage và near duplicate — Rò dữ liệu và mẫu gần trùng

Data leakage xảy ra khi thông tin đáng ra chưa biết lại ảnh hưởng việc học/chọn cấu hình/đánh giá. Near duplicate là bản gần giống do cắt, đổi nén hoặc lấy frame gần nhau, có thể gây rò giữa tập.

**Ví dụ:** Hai đoạn của cùng tai nạn ở train và test có thể làm điểm số đẹp giả.

# Domain và domain shift — Miền dữ liệu và thay đổi miền

Domain gồm các đặc điểm phân phối như camera, thời tiết, ánh sáng và bối cảnh. Domain shift là thay đổi giữa nguồn học và nguồn sử dụng, có thể làm model yếu đi dù task cùng tên.

**Ví dụ:** Model học CCTV ban ngày chưa được bảo đảm làm tốt camera đêm hoặc dashcam.

# Source bias và shortcut — Thiên lệch nguồn và lối tắt

Source bias là ảnh hưởng của nguồn thu thập tới dữ liệu/nhãn. Shortcut là tín hiệu dễ khai thác nhưng không đúng bản chất mục tiêu, khiến model làm tốt trong tập hiện có và kém trên nguồn mới.

**Ví dụ:** Nếu chỉ ảnh có watermark nhất định là positive, model có thể học watermark thay vì va chạm.

# Overfitting và generalization — Học quá khớp và tổng quát hóa

Overfitting là học quá sát dữ liệu đã gặp mà không giữ được hiệu quả trên dữ liệu độc lập. Generalization là khả năng làm tốt trên các quan sát chưa gặp theo điều kiện đánh giá xác định.

**Ví dụ:** Nhiều frame gần nhau từ một camera không thay thế được sự đa dạng nguồn/sự kiện.

# Epoch, batch và learning rate — Lượt dữ liệu, nhóm mẫu và tốc độ học

Epoch thường là một lượt qua dữ liệu train; batch là nhóm mẫu dùng cho một bước tính; learning rate điều khiển mức cập nhật tham số. Đây là hyperparameters, tức lựa chọn cấu hình học cần kiểm.

**Ví dụ:** Batch lớn hoặc số epoch từ paper khác không tự là cấu hình tối ưu cho máy project.

# Loss, optimizer và gradient — Hàm lỗi, bộ tối ưu và đạo hàm cập nhật

Loss lượng hóa mục tiêu cần tối ưu; gradient mô tả cách loss thay đổi theo tham số; optimizer dùng thông tin đó để cập nhật. Loss train tốt không thay cho phép đánh giá task cuối.

**Ví dụ:** Loss giảm chưa chứng minh hệ thống giảm false alerts/hour trên camera chưa gặp.

# imgsz, augmentation, freeze và AMP — Các tùy chọn tính toán/huấn luyện

imgsz là kích thước ảnh xử lý; augmentation biến đổi mẫu có kiểm soát; freeze khóa một phần tham số. AMP là Automatic Mixed Precision, tự phối hợp độ chính xác số để hỗ trợ hiệu quả tính toán khi phù hợp.

**Ví dụ:** Đổi kích thước ảnh có thể ảnh hưởng xe nhỏ; không thay tham số đang chạy tốt chỉ để thử tên tùy chọn.

# Seed, config và run ID — Tái lập cấu hình một lần chạy

Seed là giá trị khởi tạo phần ngẫu nhiên; config lưu lựa chọn xử lý; run ID là mã nhận diện lần chạy. Có đủ những thứ này giúp đối chiếu thay đổi nhưng không bảo đảm tuyệt đối mọi phép tính đều deterministic.

**Ví dụ:** So hai model cần biết chúng dùng cùng split, ngưỡng, feature và điều kiện chạy nào.

# dataset.yaml và best.pt — Cấu hình dữ liệu và checkpoint chọn khi train

dataset.yaml thường khai báo đường dẫn split và các class cho Ultralytics. best.pt thường là weights được chọn theo tiêu chí validation trong quá trình train; tên file không tự chứng minh một model tốt cho task nào.

**Ví dụ:** Project chưa có dataset chia tập hoặc best.pt của B0 accident; yolov8n.pt hiện tại là pretrained.

# TP, FP, FN và TN — Bốn kết quả đối chiếu nhãn

TP là True Positive, phát hiện đúng; FP là False Positive, báo nhầm; FN là False Negative, bỏ sót; TN là True Negative, nhận đúng âm. Cách đếm phụ thuộc đơn vị frame, clip hoặc event và quy tắc matching.

**Ví dụ:** Một event có nhiều alert không nhất thiết tạo nhiều TP; alert lặp có thể là FP.

# Precision — Độ chính xác trong các báo dương

Precision bằng TP/(TP+FP), trả lời trong những lần hệ thống báo dương có bao nhiêu lần đúng. Nó phải đi cùng recall vì model có thể đạt precision cao chỉ bằng cách ít khi báo.

**Ví dụ:** Giả sử 10 alert có 8 đúng thì precision=0,8; đây là ví dụ, không phải số đo project.

# Recall — Độ bao phủ các trường hợp dương

Recall bằng TP/(TP+FN), trả lời trong những trường hợp thật sự cần tìm đã phát hiện được bao nhiêu. Recall thấp nghĩa bỏ sót nhiều dù một số cảnh báo nhìn có vẻ chính xác.

**Ví dụ:** Nếu có 10 event thật và tìm được 8 thì recall=0,8, chỉ là ví dụ minh họa.

# F1 và PR curve — Cân bằng precision–recall và đường đổi ngưỡng

F1 là trung bình điều hòa của precision và recall, thường viết 2PR/(P+R). PR curve là Precision–Recall curve, biểu diễn sự đánh đổi khi thay ngưỡng hoặc operating point theo protocol.

**Ví dụ:** Không chọn một ngưỡng làm giảm FP bằng cách bỏ sót nhiều rồi gọi là cải thiện toàn diện.

# AP và mAP — Average Precision và mean Average Precision

AP tổng hợp chất lượng đường precision–recall theo quy tắc đánh giá; mAP là trung bình các AP theo class/ngưỡng được protocol quy định. Với detection, còn phải nói IoU và cách ghép hộp.

**Ví dụ:** mAP bbox không đổi trực tiếp thành event F1 hoặc mean time-to-accident của anticipation.

# Frame-level và event-level — Mức khung hình và mức sự kiện

Frame-level lấy từng ảnh làm đơn vị; event-level lấy sự kiện làm đơn vị, cần tổng hợp diễn biến và chống đếm lặp. Kết quả hai mức trả lời những câu hỏi khác nhau.

**Ví dụ:** 35 frame có Colliding trong một chuỗi vẫn có thể thuộc cùng một va chạm.

# Event matching và dedup — Ghép cảnh báo và chống đếm lặp

Event matching quy định alert nào được tính khớp GT nào theo thời gian/vị trí hoặc đối tượng. Dedup loại hoặc xử lý cảnh báo lặp, cần giữ chính sách nhất quán giữa các model.

**Ví dụ:** Một alert ghép tối đa một event; alert thừa không được đếm thêm TP tùy ý.

# FAR — False Alarm Rate (Tần suất báo sai)

Trong kế hoạch này, FAR/hour là số cảnh báo sai chia cho số giờ video âm, sau cùng chính sách ghép/chống lặp. Cần đủ thời lượng và điều kiện đa dạng để diễn giải ổn định.

**Ví dụ:** Hai clip âm vài giây không đủ để ước lượng chắc tần suất báo sai trên một giờ vận hành.

# Negative-clip FPR — False Positive Rate ở mức clip âm

Negative-clip FPR là số clip âm có ít nhất một cảnh báo sai chia cho tổng clip âm. Nó khác tần suất alert theo giờ vì mỗi clip chỉ tính một lần dù có nhiều alert.

**Ví dụ:** Một clip có năm báo sai vẫn đóng góp một clip dương giả vào tỷ lệ này.

# Event delay, latency và p95 — Độ chậm, thời gian xử lý và phân vị

Event delay so mốc alert với onset GT; latency là thời gian xử lý/đợi theo phạm vi đo. p95 là 95th percentile, mức mà khoảng 95% quan sát không vượt qua trong tập phép đo.

**Ví dụ:** Latency riêng forward YOLO không phải event delay hoặc độ trễ toàn pipeline có buffer/ghi evidence.

# Benchmark và ablation — Bài đánh giá và phép tách đóng góp

Benchmark là tập dữ liệu/protocol cho phép so sánh; ablation thay hoặc bỏ thành phần để hiểu nó đóng góp gì. Chỉ so được khi giữ các điều kiện khác cần thiết nhất quán.

**Ví dụ:** So MLP với GRU cần giữ candidate/features/split phù hợp, không đổi đồng thời detector rồi quy hết lợi ích cho GRU.

# Pipeline, entry point và CLI — Luồng xử lý và điểm chạy

Pipeline là chuỗi bước dữ liệu đi qua; entry point là nơi bắt đầu chạy; CLI là Command-Line Interface, giao diện lệnh terminal. Một lệnh có thể gọi nhiều tiến trình chứ không tự chia sẻ mọi trạng thái.

**Ví dụ:** run_all.py gọi inspect, detection và tracking riêng; vòng đọc frame chính nằm ở src/video_pipeline.py.

# Import, module và docstring — Nạp mã, đơn vị mã và mô tả

Import đưa định nghĩa từ module khác vào phạm vi sử dụng; module thường là một file Python; docstring là chuỗi mô tả ở đầu module/hàm/class. Đọc input/output trước giúp tránh chạy nhầm công cụ.

**Ví dụ:** Script maintenance cập nhật metadata khác script chỉ đọc video để kiểm thông tin.

# FFmpeg và pipe — Công cụ media và luồng byte giữa tiến trình

FFmpeg là tên công cụ xử lý media, không cần tự mở rộng thành một thuật ngữ khác. Pipe cho phép truyền dữ liệu giữa tiến trình; code có thể gửi frame dạng byte sang chương trình ghi video.

**Ví dụ:** Ảnh BGR đã plot được đưa qua pipe để FFmpeg mã hóa MP4.

# CPU, GPU, CUDA và VRAM — Các thành phần tính toán

CPU là Central Processing Unit, bộ xử lý trung tâm; GPU là Graphics Processing Unit, bộ xử lý đồ họa. CUDA là Compute Unified Device Architecture, nền tảng tính toán NVIDIA; VRAM là Video Random Access Memory, bộ nhớ GPU.

**Ví dụ:** Có GPU không bảo đảm PyTorch đã nhận CUDA; cần kiểm bản cài và driver, không chỉ nhìn tên máy.

# venv và requirements — Môi trường ảo và danh sách phụ thuộc

venv là cơ chế virtual environment của Python, giúp tách package cho project. requirements ghi dependencies/phiên bản cần cài; snapshot môi trường cũ không mặc định phù hợp mọi máy.

**Ví dụ:** Clone source không có .venv; dựng lại môi trường theo hướng dẫn CPU hoặc GPU tương ứng.

# Git, gitignore và repository — Quản lý phiên bản và kho mã

Git theo dõi lịch sử các file được quản lý; repository là kho đó; gitignore chỉ ra file không nên tự thêm vào tracking. Ignore không xóa file trên máy và không thay một hệ thống backup dataset.

**Ví dụ:** Dataset/model/video giữ local; source, policy, fingerprint và tài liệu nhỏ có thể đưa lên Git.

# Maintenance và archive — Bảo trì và lưu trữ lịch sử

Maintenance chứa công cụ ít dùng để cập nhật metadata có kiểm soát. Archive giữ kết quả cũ không còn là đầu ra hiện hành; lưu trữ không có nghĩa sửa hoặc xóa bằng chứng trong đó.

**Ví dụ:** scripts/maintenance tách khỏi lệnh thường dùng; outputs/audits/archive không là nơi chọn report mới nhất.

# Literature review và reference — Tổng quan công trình và tài liệu tham khảo

Literature review tổng hợp vấn đề, phương pháp, giới hạn và quan hệ giữa các công trình. Reference là nguồn để tra đối chiếu; chỉ có danh sách URL chưa đủ thay một bản phân tích vai trò của từng bài.

**Ví dụ:** Cột vai trò trong review là phân tích cho project, không phải kết luận tác giả đã chứng minh trong setup này.

# Abstract, preprint, peer review và DOI — Thông tin công bố khoa học

Abstract là tóm tắt bài; preprint là bản thảo công khai có thể chưa phản biện; peer review là quá trình phản biện. DOI là Digital Object Identifier, định danh tài liệu, không bảo đảm link dữ liệu hoặc code đang tải được.

**Ví dụ:** Có abstract hoặc DOI chưa có nghĩa đã đọc full text, có annotation public hoặc đã tái lập paper.

# Reproduction, novelty và SOTA — Tái lập, tính mới và mức tiên tiến

Reproduction là tái lập thí nghiệm theo điều kiện được mô tả; novelty là đóng góp mới có căn cứ. SOTA là State of the Art, mức tiên tiến trong benchmark/protocol cụ thể, không phải nhãn chất lượng cho mọi bối cảnh.

**Ví dụ:** Chạy YOLO cùng GRU hoặc dùng model mới hơn không tự chứng minh novelty hay cải thiện so với baseline.

# PTS — Presentation Timestamp (Dấu thời gian trình chiếu)

PTS cho biết một frame được trình chiếu tại thời điểm nào trong file video. Nó có thể khác phép lấy chỉ số frame chia FPS trung bình, nhất là khi video có khoảng thời gian giữa các frame không đều. PTS của file phát hành chưa tự chứng minh thời điểm hay FPS ghi hình gốc.

**Ví dụ:** ACCIDENT `2QZf8MiIRK0_00` có frame decode 11 ở PTS 1,134467 giây, khớp CSV tác giả; chia 11 cho FPS trung bình lại không cho mốc đó.

# VFR — Variable Frame Rate (Tốc độ khung hình biến đổi)

VFR là video có khoảng thời gian trình chiếu giữa các frame thay đổi. CFR là Constant Frame Rate, tốc độ khung hình cố định. Với VFR, FPS hiển thị trong metadata thường chỉ là một giá trị tổng hợp; khi ghép nhãn thời gian với frame nên đọc PTS thay vì mặc định mọi frame cách đều nhau.

**Ví dụ:** Hai frame liên tiếp có thể cách 0,04 giây, rồi cặp tiếp theo cách 0,12 giây. Chỉ số decode vẫn tăng một, nhưng thời gian không tăng đều.

# ACCIDENT — Tên benchmark tai nạn từ CCTV

ACCIDENT là tên riêng của benchmark do Picek và cộng sự công bố, không phải từ viết tắt cần tự mở rộng. Phần dữ liệu thực phát hành có mốc impact, bbox và loại va chạm. Trong project, chỉ các bbox impact đã kiểm mapping và phạm vi vùng mới được thêm vào pool B0; một nhãn tại impact không làm cho toàn bộ clip có nhãn bbox đầy đủ.

# Pre-impact frame — Khung hình trước va chạm

Là ảnh nằm trước mốc tiếp xúc của sự kiện đang xét. Với collision detection, ảnh này có thể làm mẫu âm nếu đã xác minh chưa có va chạm trong toàn phạm vi ảnh; không chỉ dựa vào việc thiếu bbox. Project chọn frame cách impact ít nhất một giây PTS của file, kiểm lại mapping và xem toàn ảnh. Ví dụ một frame xe còn đi tách nhau được giữ âm; frame sát lúc tiếp xúc hoặc không thấy rõ vẫn chưa xác định. Điều này không biến cả video tai nạn thành video âm.

# Derived label — Nhãn dẫn xuất

Là nhãn suy ra từ thông tin nguồn và một quy tắc được ghi rõ, thay vì nhãn tác giả cung cấp trực tiếp. Phải lưu quy tắc, bằng chứng, phạm vi và người/công cụ rà để tránh nhầm nguồn. Ví dụ 30 frame âm trước impact trong pool v3 dựa vào mốc tác giả cộng rà ảnh của AI; chúng không phải nhãn âm tác giả hoặc xác nhận mới của người dùng.

# Dataset release — Bản dữ liệu được phát hành cho huấn luyện

Là phiên bản ảnh, nhãn và split đã qua các điều kiện kiểm dữ liệu, được khóa bằng hash và truy nguồn. Một pool tham chiếu chưa tự là dataset release. Công cụ export của project chỉ tạo cấu trúc ảnh/TXT/YAML khi readiness và policy cho phép; có YAML từ fixture thử không có nghĩa dữ liệu thật đã sẵn sàng train.

**Ví dụ:** Đã tải sáu clip nhỏ nhưng chỉ giữ bốn ảnh impact phù hợp; không đếm 1.445 frame video thành 1.445 nhãn vùng accident.

# Raw positive run — Đoạn dự đoán dương liên tiếp

Là một nhóm frame liền nhau mà model đều trả ít nhất một bbox accident tại ngưỡng đang dùng. Ví dụ frame 10, 11, 12 có hộp, frame 13 không có hộp thì đoạn này là 10–12; nếu frame 14 có hộp sẽ bắt đầu đoạn mới. Trong log B0 đây là cách gom kết quả để xem chúng chớp tắt hay kéo dài, chưa phải một cảnh báo tai nạn đã xác nhận. Một va chạm thật có thể tạo nhiều đoạn, còn một lỗi nhầm background có thể tạo một đoạn rất dài. Vì vậy không lấy số đoạn này thay cho số tai nạn, false alerts/giờ hoặc precision sự kiện khi chưa chốt quy tắc cảnh báo và ghép sự kiện.

# Post-hoc diagnostic — Phân tích chẩn đoán sau khi đã xem kết quả

Là việc xem prediction và lỗi của một model đã chạy để hiểu nó đang nhầm ở đâu. Chẳng hạn thống kê thấy vùng GT bị bỏ sót thường nhỏ hơn vùng bắt đúng, hoặc model đặt hộp nhiều lần trên đường hầm không có va chạm. Phân tích này giúp đề xuất phép thử và dữ liệu cho bước sau, nhưng không tự chứng minh nguyên nhân hay chất lượng trên dữ liệu mới. Nếu đã xem test để tìm lỗi thì phải ghi nhận test đã được sử dụng; khi cải thiện dựa trên các lỗi đó, cần đánh giá trên nguồn độc lập mới trước khi tuyên bố khả năng khái quát.

# Negative-only holdout — Tập âm giữ riêng

Là một nhóm video/ảnh được biết là không có tai nạn và được dành riêng trước khi train hoặc chọn tham số. Model không được học các mẫu này; cũng không xem kết quả trên chúng để liên tục sửa ngưỡng. Sau khi chốt model, tập này giúp kiểm model có đặt hộp/cảnh báo nhầm trên cảnh normal mới hay không. Ví dụ pilot hiện giữ riêng 120 frame từ bốn clip normal tác giả, ngoài train và validation. Vì chỉ có âm, tập này không đo được khả năng bắt tai nạn thật hay recall dương; nó không thay thế một test đầy đủ có cả hai loại và nhiều nguồn độc lập.

# Operating point — Điểm vận hành

Là cách chọn một ngưỡng quyết định cụ thể để sử dụng model, ví dụ chỉ giữ hộp có confidence lớn hơn0,27. Khi nâng ngưỡng, thường ít báo sai hơn nhưng dễ bỏ sót hơn. Vì vậy phải chọn theo mục tiêu và validation, không chỉ chọn ngưỡng có precision cao nhất. Trong pilot B0, điểm0,27 được chọn bằng F1 cao nhất trong các ngưỡng còn giữ recall ít nhất70%; thay ngưỡng không làm model học thêm, không tăng mAP đã báo cáo và không biến confidence thành xác suất va chạm đã hiệu chuẩn. Sau khi khóa, giữ nguyên khi đánh giá holdout; nếu sửa dựa trên lỗi holdout thì tập đó đã tham gia phát triển, không còn là phép kiểm độc lập mới.

# OAuth — Cơ chế cấp quyền qua trang đăng nhập

OAuth là tên cơ chế ủy quyền: công cụ mở trang của dịch vụ để bạn đăng nhập và cho phép truy cập, sau đó lưu credential phù hợp trên máy. Trong project, `kaggle auth login` giúp KaggleCLI sử dụng tài khoản của bạn; bạn không cần gửi mật khẩu hoặc token vào cuộc trò chuyện. Đăng nhập thành công chưa đồng nghĩa Dataset đã upload hoặc notebook đã train; các bước đó có trạng thái riêng.

# Portable bundle — Gói chạy có thể chuyển máy

Là gói chứa đúng ảnh/nhãn, split, config, code và checkpoint cần thiết, kèm hash để kiểm trước khi chạy ở máy khác. Gói B0 có train/validation nhưng không có media test/reserve, raw hoặc credential. Đường dẫn tuyệt đối Windows được thay bằng YAML tạo tại máy chạy; nội dung ảnh/nhãn và split nguồn vẫn giữ nguyên. Có gói hợp lệ mới là chuẩn bị xong, chưa phải đã train xong.

# Hard link — Liên kết cứng tới cùng nội dung file

Hai đường dẫn hard link trỏ tới cùng dữ liệu trên cùng ổ đĩa, thay vì sao chép thêm một file lớn. Project dùng chúng trong thư mục tạm để kiểm trainer sau khi đổi root mà không nhân đôi hàngGiB ảnh. Đây không phải hai mẫu dữ liệu độc lập; cũng không nên chỉnh file qua đường dẫn thử vì nội dung được dùng chung. Lượt kiểm chỉ đọc/hash/decode và không train.

# GPU quota — Hạn mức sử dụng GPU

Là giới hạn tài nguyên mà nền tảng cấp cho tài khoản, chẳng hạn thời gian GPU còn dùng được. Hạn mức, GPU được cấp và khả năng bậtGPU cần xem trong tài khoản Kaggle thật; không suy từ máy của người khác. Gửi notebook thành công vẫn có thể phải chờ hoặc lỗi quota. Project không chuyển sang trainCPU/laptop khi Kaggle không cấpGPU.
