# 24/10/2026 — Dùng nguồn công khai để tiếp tục B0 và xác minh va chạm

> **Kết quả tiếp theo cùng ngày:** đã thêm T-T_crash_2, tổng 4 STTAD/176 ảnh đọc được/31 frame nhãn; lấy hai TAD normal (308 frame), kiểm nhóm và tạo pool tham chiếu. MVI_20011/20012 gần như nối tiếp, cả ba DETRAC gom cùng cảnh bảo thủ. Xem [báo cáo mới](../docs/b0_pilot_audit.md); các số 3 chuỗi/21 bbox bên dưới là mốc lịch sử trước mở rộng.

## Quyết định và đối chiếu workbook

Yêu cầu mới: AI tự nghiên cứu, so sánh và thực hiện; bỏ đường yêu cầu xin dữ liệu riêng hoặc chờ giảng viên duyệt quyết định kỹ thuật. Việc trước đây giao người dùng gửi thư/xin duyệt không còn là bước tiếp theo.

**XLSX đã liệt kê** paper YOLOv8 (S12), Surveillance Transformer (S13), RARE (S07/08), Graph(Graph) (S09/10), CRASH (S11), AcciDetect (S14), VTAD-FL (S15), CADP (S16), ở sheet 11/15. B0/B1/B2/T0/B3 đã có ở sheet 05/09. Sai sót trước là không dùng đủ các nguồn này để chọn phương án khả thi khi CADP thiếu export. STTAD, TAD, Ijjina 2019 và Ghahremannezhad 2022 chưa có thành mục riêng trong workbook; bổ sung ở đây, không sửa âm thầm XLSX gốc.

## Các hướng đã công bố và vai trò trong project

| Nguồn sơ cấp / mức đọc | Hướng và tín hiệu | Quyết định |
| --- | --- | --- |
| S12 [Real-time traffic accident detection using YOLOv8, 2025](https://doi.org/10.1016/j.trpro.2025.03.135), abstract nhà xuất bản; full text công cụ trả 403 | Fine-tune detector ảnh accident. | Tham chiếu B0; chưa xác minh được dataset/split/code paper, không nhận là tái lập. |
| R19 [STTAD, ITSC 2025](https://dsg.tuwien.ac.at/team/snastic/publications/ITSC25_0424_FI.pdf), đọc mục III/IV và Table II | Vùng sự kiện theo frame; STFN ghép đặc trưng 2D YOLOv8 với 3D CNN. | Dùng định nghĩa vùng và annotation public; giữ YOLOv8n B0, không đổi sang STFN. |
| R20 [Ijjina et al., 2019](https://arxiv.org/html/1911.10037v1), đọc mục III | Mask R-CNN/centroid tracks; overlap, tốc độ/gia tốc, góc quỹ đạo. Có phép tính dùng 15 frame sau overlap. | Tham chiếu B2; không sao ngưỡng hoặc dùng tương lai mà gọi causal. |
| R21 [Ghahremannezhad et al., 2022](https://arxiv.org/html/2208.06461v1), đọc mục II | YOLOv4, Kalman/Hungarian, khoảng cách/tốc độ/hướng; có hiệu chuẩn homography. Target bao gồm cả near-accident. | Tham chiếu B2 và chất lượng tracks; không biến mọi conflict thành collision hoặc báo km/h khi chưa hiệu chuẩn. |
| S13 [Surveillance Transformer, 2025](https://arxiv.org/html/2512.11350v1), đọc mục 3/4 | CNN RGB/optical-flow features + Transformer phân loại clip. | So sánh hướng appearance/motion; bài mô tả tập tổng hợp nhưng chưa xác minh public đầy đủ, không chờ xin dữ liệu. |
| S07/08 [RARE, 2025](https://arxiv.org/html/2505.17449v1), abstract/phương pháp và [repo tác giả](https://github.com/Songinpyo/RARE-ICIP2025) | Tái dùng feature YOLO, attention, GRU; anticipation DAD/CCD. | Tham chiếu verifier nhẹ, không đổi sang dashcam/anticipation hoặc YOLOv10x. |
| S09/10 [Graph(Graph), WACV 2024](https://github.com/thakurnupur/Graph-Graph) | Nested object/temporal graph cho anticipation, theo workbook; CVF full text trả 403 lượt này. | Giữ tham chiếu, không coi đã đọc lại toàn văn. |
| S11 [CRASH, 2024](https://arxiv.org/html/2407.17757v1), abstract/phương pháp | Object/context attention và temporal fusion trên dashcam, anticipation. | Tham chiếu tương tác; không đổi task hoặc gọi temporal là mới. |
| S14 [AcciDetect, 2026](https://research.polsl.pl/en/publications/accidetect-a-graph-recurrent-framework-for-detecting-road-acciden/), abstract cơ quan tác giả | Object/motion GCN + BiGRU, DAD/CCD. | Đối chiếu; cần kiểm causal trước vận hành, chưa chạy code/checkpoint. |

Không hướng nào biến một phép đo đơn lẻ thành bằng chứng chắc chắn cho mọi cảnh. **Kế hoạch project:** B0 học hình ảnh vùng accident → B1 lọc score theo quá khứ → B2/MLP/GRU (khi đủ điều kiện) kiểm chuyển động cặp xe, so cảnh báo sai trên hard negatives.

## Xác minh va chạm dựa vào gì?

| Yếu tố | Dữ liệu/cách tính sẽ dùng | Giới hạn và vị trí trong lộ trình |
| --- | --- | --- |
| Dấu hiệu thị giác của sự kiện | B0 fine-tune bằng bbox accident-region của nguồn công khai | Ảnh đơn có thể nhầm xe đỗ sát/che nhau; cần nhãn cùng nghĩa và FP/FN. |
| Hai xe tương tác gần nhau | Khoảng cách tâm chuẩn hóa, IoU, độ tiến lại gần từ tracks | Chỉ tạo ứng viên; giao bbox do phối cảnh chưa đủ xác nhận. B2. |
| Biến đổi chuyển động | Tâm bbox qua quá khứ, đổi hướng, giảm chuyển vị đột ngột, biến đổi tương đối | Cần mask thiếu track; nếu chưa có timing chỉ tính theo frame, không km/h hay giây nguồn. B2/T0. |
| Bằng chứng kéo dài theo thời gian | EMA/k-of-N causal, rồi feature window causal khi có nhãn phù hợp | Không nhìn tương lai; phải đo trade-off recall/false alarms/delay. B1/B3. |
| Chất lượng quan sát | Confidence, số lần mất/đổi ID, missing mask, nhãn vùng ignore | Thiếu/che khuất → unknown hoặc bỏ cửa sổ, không tự khẳng định không va chạm. |

Các công cụ trên chưa phải collision detector đã đo được của project; hiện pipeline chạy mới dừng vehicle detection/tracking.

## Kiểm dữ liệu public thực tế

### STTAD — chọn làm nguồn vùng B0 trước mắt

[Repo tác giả](https://github.com/ZTR02/STTAD), commit `21f3f5fea50b071f1db61186b481c2a7ccf525c9`. Đọc full Git tree (không truncated): 1.693 file, tổng metadata size 483.155.196 byte; **đây là phần ví dụ công khai, không phải toàn bộ 1.189 video của paper**. Tree có 197 cặp ảnh/TXT theo đúng path; pixel các cặp chưa tải vẫn chưa kiểm. Có 200 JPG đặt trong khu vực labels, và nhánh V-T không có TXT tương ứng; không đổi tên để ép ghép.

Đã lấy chọn lọc **75.388.808 byte (~71,9 MiB)**, gồm ba chuỗi và README/list nguồn, không clone cả repo:

| Chuỗi | File ảnh nguồn / giải mã được | Frame có bbox tác giả | Còn lại |
| --- | --- | --- | --- |
| V-V_crash/V-V_crash_0 | 51 / 50, 1920×1080 | 7 | 43 unknown, 1 file lỗi |
| V-V_crash/V-V_crash_1 | 51 / 50, 1920×1080 | 2 | 48 unknown, 1 file lỗi |
| T-T_crash/T-T_crash_1 | 26 / 26, 450×358 | 12 | 14 unknown |

Hai `00051.jpg` trong V-V thực tế không giải mã được, dù byte khớp Git blob (một file đọc được như text); giữ nguyên và loại khỏi dữ liệu ảnh. 21 bbox đều trong biên. TXT thực tế là `class xmin ymin xmax ymax` **pixel**, không đưa nguyên vào Ultralytics như YOLO normalized. Đã chuyển CSV + 21 TXT sang class project 0/cxcywh chuẩn hóa, giữ class nguồn 11/6 và provenance. Không có visibility/FPS nguồn trong các TXT, không suy diễn.

Đã xem **8 cặp ảnh nguồn/overlay** (đầu/giữa/cuối các frame có nhãn, trùng thì lấy một): ảnh có nội dung CCTV, bbox cùng cảnh và bao vùng xe liên quan; không thấy bbox nguồn vẽ sẵn trong các ảnh mẫu. Đây là kiểm mẫu của AI, không xác nhận người dùng hoặc kiểm đầy đủ mọi pixel/onset/end. `trainlist.txt` có 23/35 đường dẫn không nằm trong tree public; test list 23/23 thiếu. Không áp các list này làm split project.

Nguồn ảnh/TXT: `data_raw/sttad/public_examples/{rgb-images,labels}/<category>/<sequence>/`. [Báo cáo](../outputs/audits/sttad_public_4/report.json), [CSV frame](../outputs/audits/sttad_public_4/frames.csv), [CSV bbox](../outputs/audits/sttad_public_4/boxes_normalized.csv), [ảnh đối chiếu](../outputs/audits/sttad_public_4/author_region_examples.jpg), TXT chuyển đổi ở `outputs/audits/sttad_public_4/labels_yolo/`. Media/TXT giữ local bị Git ignore; repo chỉ giữ code/hồ sơ nhỏ. Chưa thấy LICENSE riêng trong tree public, không kết luận có quyền phân phối lại media.

### TAD — public video nhưng gói đã kiểm không có bbox

[Repo phát hành](https://github.com/UnicomAI/UnicomBenchmark/tree/main/TADBench), [paper preprint](https://arxiv.org/pdf/2209.12386), [ZIP Google Drive](https://drive.google.com/file/d/14GNlNcWLzN-sbzvmrMuSbAg_rZZ5yd26/view). Paper mô tả cả phân loại và bbox; không suy ra gói tải có đủ hai dạng nhãn.

Đã đọc central directory ZIP bằng HTTP 206 Range: archive **4.543.580.572 byte**, chỉ truyền **50.792 byte** để liệt kê 414 member: **404 MP4 + 10 directory**, không có TXT/XML/JSON bbox. Folder phân loại có 277 accident/127 normal; khác tổng 344 viết trong README. Không dùng tổng sai đó làm inventory. Đây là kiểm danh mục, chưa tải/giải mã 404 video, chưa CRC toàn ZIP. Có thể dùng để nghiên cứu phân loại clip khi đối chiếu được từng nguồn; **không chọn thay GT bbox B0 và không gán mọi frame của clip accident là dương**. [Báo cáo](../outputs/audits/tad_public_zip/report.json), [member CSV](../outputs/audits/tad_public_zip/members.csv).

### Nguồn giữ tham chiếu hoặc bỏ khỏi đường chính

- CADP: giữ đúng 001407 + review đã có; export bổ sung chưa public trong phạm vi kiểm, không xin riêng, không chặn công việc tiếp tục.
- [Ghahremannezhad repo/data link](https://github.com/hadign20/AccidentDetection): source có liên kết Drive công khai, chưa kiểm được annotation trong folder; dùng phương pháp tham khảo, không tính là mẫu có GT bbox.
- Các công trình/dataset khác xuất hiện khi tìm nhưng chưa audit: [TU-DAT/paper](https://www.mdpi.com/1424-8220/25/11/3259), [TrackGuard-LTE](https://zenodo.org/records/20586797), [SynCrash](https://github.com/arkya-art/SynCrash-CVPR2026), [YOLOv9/paper](https://www.mdpi.com/2079-9292/15/10/2178), [MDTS-ADNet](https://github.com/Jasoncode0115/MDTS-ADNet). Chỉ là đầu mối, không dùng số đo/claim train-ready; nguồn đòi xin phần riêng không đưa vào kế hoạch triển khai. Những kết quả tìm chung về collision avoidance hoặc repo không gắn nguồn paper chưa được chọn làm bằng chứng va chạm.

## Thiếu nhãn hoặc bị che: làm cụ thể thế nào?

1. Dùng đúng path/frame để join ảnh và TXT. Không có TXT → `unknown_missing_label`, không empty label.
2. Kiểm giải mã, kích thước và `0 <= xmin < xmax <= W`, tương tự y; lỗi → ghi loại trừ, giữ nguyên raw.
3. CADP có `outside/occluded/generated/FarRegion`: công cụ nguồn đã giữ flags. Với **envelope dẫn xuất**, loại ứng viên có participant missing/outside/occluded hoặc chồng ignore; không vẽ bù phần khuất. `generated` là cờ nguồn, không đồng nghĩa nhãn sai hoặc nhãn project tự tạo.
4. STTAD không có visibility flag trong TXT: ghi `not_provided`; giữ bbox tác giả khi hợp lệ, không tự gọi frame không che. Frame không nhãn bị bỏ khỏi supervision. Nếu kiểm mẫu thấy bbox sai cảnh thì loại cặp/chuỗi và chuyển sang cặp public khác.
5. File `frame_quality.csv` ghi từng frame và lý do; không dùng từ “sẽ rà” mà thiếu công cụ/tiêu chí. Lần chạy CADP: **35 ứng viên qua các cờ hiện có, 0 occluded, 0 overlap ignore; 186 unknown bị loại khỏi nhãn**. Cả 35 vẫn auxiliary derived, không biến thành GT tác giả.

## Làm tiếp bằng gì?

Đã chọn policy [b0_public_label_policy.json](../configs/b0_public_label_policy.json): B0 giữ nhiệm vụ vùng accident, dùng nhãn vùng tác giả STTAD public trước; giữ CADP để debug/motion, DETRAC âm được rà. Không yêu cầu người dùng hoặc giảng viên duyệt quyết định này.

Các lệnh chạy được trong project:

```powershell
# Máy này đã có file: kiểm offline, không tải lại
.\.venv\Scripts\python.exe -X utf8 -B scripts/audit_sttad_public.py --offline
.\.venv\Scripts\python.exe -X utf8 -B scripts/audit_cadp_b0_quality.py

# Máy mới: chỉ lấy ba chuỗi đã chọn, giới hạn 96 MiB, giữ commit nguồn
.\.venv\Scripts\python.exe -X utf8 -B scripts/audit_sttad_public.py --fetch-selected --max-mib 96

# Nguồn lớn: chỉ đọc danh mục remote, không tải ZIP TAD 4,54 GB
.\.venv\Scripts\python.exe -X utf8 -B scripts/inspect_public_zip.py
```

Lần chạy mới in audit_directory khác, không ghi đè bằng chứng cũ. Bước tiếp theo của AI là chuẩn bị thêm cặp vehicle–vehicle public hợp path (trong tree còn T-T_crash_2), kiểm nguồn/camera/trùng cảnh và nguồn âm phù hợp; chỉ sau đó thiết kế split theo nhóm. Nếu nguồn chỉ có nhãn clip, chỉ dùng được cho bài toán clip hoặc phải ghi một thay đổi baseline riêng; không tự tạo bbox. Nếu không tìm đủ nhãn vùng public, báo mức hỗ trợ thực tế và chọn baseline được dữ liệu public hỗ trợ, ghi rõ quyết định thay vì chờ xin hoặc tạo GT giả. **Hiện chưa split/train, chưa có accuracy/event metric; 21 frame dương không phải 21 sự kiện độc lập.**

## Bổ sung cùng ngày — nguồn âm và phương pháp sàng lọc cảnh

- Từ [gói TAD tác giả](https://github.com/UnicomAI/UnicomBenchmark/tree/main/TADBench), đã lấy riêng hai member `train/normal/20220518_acci-bg34.mp4` và `train/normal/20230818_acci-bg_83.mp4`. Dùng nhãn âm mức clip của tác giả, giữ nguồn/review scope; không coi đó là xác nhận người dùng hoặc tạo bbox dương. Danh mục/CRC/hash và kiểm decode ở [báo cáo mới](../docs/b0_pilot_audit.md).
- Tham khảo [tài liệu image hashing OpenCV](https://docs.opencv.org/4.x/d4/d93/group__img__hash.html), kiểm 24/10: hash dùng tìm ảnh tương tự. Tool project tự dùng DCT 8×8 bỏ DC tạo 63 bit, so cả ảnh và crop giữa; không nhận là triển khai giống hệt PHash 64 bit của OpenCV hoặc metric học được. Ngưỡng Hamming ≤8 chỉ để đề xuất nhìn lại, không tự merge nguồn hay chứng minh camera độc lập.
- Quan sát trực tiếp ảnh đầu/giữa/cuối và cặp biên 20011/20012 làm căn cứ gom DETRAC bảo thủ. Không thêm paper/model mới vào pipeline suy luận; vẫn giữ mục tiêu B0/nhãn nguồn và các review cũ.

## Bổ sung 25/10/2026 — kiểm nguồn và mở rộng pool thực tế

Đã đọc lại README và các sheet 05/08/09/11/15 trước khi tìm. Phần nguồn dưới đây bổ sung R23–R25 trong [literature review](LITERATURE_REVIEW.md); không thay mục tiêu B0. Bằng chứng chi tiết tại `outputs/audits/accident_public/source_checks/sources.json` và các phản hồi metadata/danh mục giữ cùng thư mục.

| Nguồn sơ cấp | Mức public/thực sự đã kiểm | Quyết định |
| --- | --- | --- |
| [SO-TAD paper](https://doi.org/10.1016/j.neucom.2024.129061), [repo tác giả](https://github.com/cccxy-299/so-tad), [HF tác giả](https://huggingface.co/datasets/cccccxy/so-tad) | API public/HTTP Range đạt; revision `6b11c79731309da5cb39f4c18a8a86697b3f7ad5`. Archive 51 phần, 27.349.353.323 byte; đọc danh mục 2.188 member gồm 2.185 MP4, hai folder, một Appendix. Lấy riêng Appendix 3.333 byte sau giải nén, CRC `41b69f65` đạt; 281 dòng tên clip + một số, không bbox. Không tải video. | Không dùng làm GT vùng B0. Không tải 27 GB để giải quyết thiếu bbox; chỉ giữ tham khảo temporal/schema. |
| [TU-DAT paper](https://doi.org/10.3390/s25113259), [repo tác giả](https://github.com/pavana27/TU-DAT) | ZIP annotation public tại commit `9495d9506faf0d9efa1d7c1d83917dbd0e409c9b`, 2.216.074 byte, 270 member; CRC toàn ZIP đạt. Đọc 128 JSON từng video: 73.120 bbox mẫu đều mang class `moving_object`, kèm phân tích chuyển động/impact detection. Chưa tải raw video hoặc kiểm mapping. | Không biến hộp chuyển động tự động thành GT accident. Kết luận giới hạn ở gói đã kiểm, không khẳng định mọi bản TU-DAT đều thiếu nhãn. |
| [ACCIDENT paper](https://arxiv.org/abs/2604.09819), [repo](https://github.com/accidentbench/ACCIDENT), [Kaggle v9](https://www.kaggle.com/datasets/picekl/accident/versions/9) | API metadata và URL từng file truy cập không cần xác thực; CSV 486.740 byte/2.027 dòng, có frame impact và bbox. Lấy riêng sáu clip, 1.445 frame decode; đối chiếu PTS OpenCV/FFprobe, pixel PNG và nhãn chuyển đổi đạt. Chỉ liệt kê trang đầu 100 file, không kiểm toàn bộ media. Giấy phép dataset API ghi CC BY-NC-SA 4.0. | Bốn vùng phù hợp vào pool v2; hai vùng thiếu/chưa rõ phạm vi giữ ngoài. Không lan nhãn ra toàn clip. Không train/split/đổi model. |

Hai dòng CSV ACCIDENT có `accident_frame == no_frames` được công cụ đánh dấu cần kiểm quy ước biên, chưa tải video để kết luận nhãn sai. Với sáu clip đã tải, `decoded_count = no_frames + 1`; cả sáu index impact khớp PTS tác giả. Giữ nguyên metadata gốc. Không dùng FPS trung bình để dịch index hoặc suy timing ghi hình.

Đã kiểm thêm đầu mối [TUM Accid3nD](https://accident-dataset.github.io/) và [gói Thai/Zenodo](https://zenodo.org/records/20153379): trang mô tả/API truy cập được, chưa kiểm gói ảnh + nhãn vùng tương ứng. Không tính chúng thành dữ liệu B0 đã có, không tải trọng số hoặc gói lớn. TUM còn có phạm vi đa cảm biến; không tự chuyển project sang 3D. Một số endpoint publisher trả 429 hoặc trang kiểm trình duyệt; không dùng phần chưa đọc để điền phương pháp chi tiết.

Kiểm lại toàn pilot: **16 nhóm nguồn, 4.187 frame decode, 120 cặp nhóm**, 0 hash pixel trùng hệt xuyên nhóm, một cặp gợi ý vẫn là DETRAC 20011/20012. Không thấy trùng hệt không chứng minh độc lập camera/sự kiện; đặc biệt ACCIDENT có báo giao nguồn với CADP/TAD. Nhóm DETRAC giữ nguyên. Pool mới **2.380 dòng, 35 dương/2.345 âm**, 13 nhóm nguồn/11 nhóm chống rò rỉ tạm thời. [Báo cáo B0](../docs/b0_pilot_audit.md), [phiếu rà AI](../data/reviews/2026-10-25-accident-source-review.json), [nhật ký](../progress/2026-10-25.md).


## Đối chiếu bổ sung 26/10/2026 — âm trước impact và mở rộng chọn lọc

Đọc lại [repo tác giả](https://github.com/accidentbench/ACCIDENT) và [paper mục 3.1](https://arxiv.org/html/2604.09819v1#S3.SS1), cả hai truy cập được. Mốc tác giả là tiếp xúc nhìn thấy đầu tiên; thông tin này hỗ trợ chọn ứng viên trước impact nhưng không tự chứng minh toàn ảnh là âm. Project áp dụng khoảng đệm PTS file và rà từng frame; nguồn nhãn mới ghi derived, không giả annotation âm tác giả. Không thêm paper/trang review riêng.

20 URL từng MP4 v9 đã tải thực tế qua API public, tổng 52.790.420 byte. URL chính xác và SHA ở [catalog](../data/download_catalog.json); tên 20 file ở [phiếu impact](../data/reviews/2026-10-26-accident-source-review.json). 13 impact mới giữ, 7 loại có lý do; 30 âm theo frame giữ từ cả batch mới/cũ. Không tải cả dataset, không suy timing camera từ PTS, không lấy clip label làm bbox mọi frame. Quyết định ứng dụng và kết quả kỹ thuật ở [báo cáo B0](../docs/b0_pilot_audit.md). Dataset có paper/mã/media mẫu public đã kiểm; chưa kiểm mọi video trong 2.027 dòng CSV. Ở thời điểm kết thúc batch mở rộng, gate train còn đóng; vòng pilot sau trong cùng ngày đã mở release ảnh riêng. Không cần xin nguồn riêng.

### 26/10/2026 — sử dụng nguồn public cho B0 pilot thật

Đối chiếu lại [paper ACCIDENT](https://arxiv.org/html/2604.09819v1) và [repo tác giả](https://github.com/accidentbench/ACCIDENT), đều truy cập được ngày 26/10. Paper công bố **2.027 clip thật và 2.211 clip mô phỏng**, có impact time/vị trí/loại; project mới tải và kiểm 26 clip thật chọn lọc, chưa kiểm phần còn lại hoặc clip mô phỏng. Vì thế công bố của tác giả là nguồn mở rộng cụ thể, không phải bằng chứng chất lượng của 26 file đã chọn hay nhãn cho mọi frame. Các vùng impact giữ đúng nhãn public của tác giả; 30 ảnh trước impact là âm dẫn xuất có phiếu rà AI.

Đã dùng 17 cặp nguồn phù hợp để xuất 47 ảnh, split theo nguồn, fine-tune YOLOv8n và đo bbox: [config](../configs/b0_pilot.json), [metric và case](../docs/b0_pilot_audit.md#pilot-b0-ảnh-26102026). Kiểm [Ultralytics train](https://docs.ultralytics.com/modes/train/) và [val](https://docs.ultralytics.com/modes/val/) ngày 26/10 để đối chiếu API/ý nghĩa mAP, nhưng giữ phiên bản đã cài **8.4.178** và model **YOLOv8n**, không đổi theo ví dụ phiên bản mới trong trang docs. mAP bbox pilot không thay thế metric temporal/spatial/type của paper ACCIDENT. Kết quả test hiện kém; bước mở rộng train dựa vào clip/nhãn public còn lại và case FP/FN, vẫn giữ test hiện hành để đối chiếu.
## Bổ sung 26/10/2026 — kiểm nguồn cho lần train B0 mở rộng

**Cập nhật 27/10:** quyết định dùng frame trước impact chưa rà làm âm train của lượt đầu đã bị thu hồi; mốc first-visible-contact chỉ tạo ứng viên cần rà, không xác nhận âm toàn ảnh. Release hiện hành chỉ dùng âm đã rà hoặc nhãn normal công khai. Xem [nhật ký](../progress/2026-10-27.md) và [policy](../configs/b0_verified_label_policy.json).

- [ACCIDENT paper](https://arxiv.org/html/2604.09819v1) ghi **2.027 clip thật**, impact là tiếp xúc nhìn thấy đầu tiên, một bbox quanh bên tham gia, loại va chạm; dữ liệu thật không có dense detection/tracking annotation. Baseline vị trí trong paper dự đoán **điểm** và chấm bằng Gaussian, không phải YOLO accident bbox mAP. [Kaggle v9](https://www.kaggle.com/datasets/picekl/accident/versions/9) phát hành `metadata-real.csv` và video; danh mục API cho 1.346 clip bốn loại xe–xe có frame/bbox hợp lệ (327 author IID train, 1.019 author IID test). Đồ án dùng split nhóm nguồn **tuỳ biến** vì B0 cần đủ ví dụ impact cho train, tuyệt đối không nhận là kết quả benchmark IID tác giả. Mỗi clip phải qua SHA, giải mã, kích thước và PTS; trường hợp sai giữ reject. Không tải 2.211 clip synthetic hoặc nhãn dense chưa public.
- [TP-YOLOv8 paper](https://zhangtianze.com/mypublications/Thesis/TPYOLOv8.pdf) công bố 8.392 ảnh TAT và recipe train từ đầu trên A40 48 GB, nhưng [URL TAT repo trong bài](https://github.com/Ningdashuai/TAT) trả 404 khi kiểm ngày này. **Paper public không đồng nghĩa nhãn TAT public truy cập được**; không ghi 8.392 ảnh này là dữ liệu đã tải. Recipe chỉ là đối chiếu cho optimizer/kích thước ảnh, khác nhãn/task/phần cứng của B0.
- [Ultralytics fine-tune](https://docs.ultralytics.com/guides/finetuning-guide) khuyên khởi tạo từ checkpoint khi dữ liệu hạn chế. Giữ YOLOv8n pretrained hiện có và cấu hình có phiên bản; phép fine-tune vùng impact là thích ứng của project. Nguồn thật, nhãn gốc, âm đã rà và ảnh test phải có provenance riêng. Xem [literature review](LITERATURE_REVIEW.md) để hiểu phương pháp, [policy hiện hành](../configs/b0_verified_label_policy.json) để biết điều kiện dùng nhãn.

## Bổ sung 27/10 — probe âm TAD test/normal

[Repo benchmark tác giả](https://github.com/UnicomAI/UnicomBenchmark/tree/main/TADBench) dẫn tới archive công khai đã được kiểm bằng HTTP Range. Từ danh mục ZIP, chọn năm member nhỏ nhất trong `TAD-benchmark/test/normal/`: `videox_test_F11`, `F10`, `F9`, `F4`, `F3`; tải 49.593.409 byte mạng, kiểm CRC từng member và giải mã toàn bộ năm video. Ghi SHA/CRC, frame count, kích thước và 20 frame lấy đều/clip trong [manifest](../data/registries/b0_tad_normal_test_v1.json). Đây là **nhãn normal của tác giả theo thư mục clip**, không phải người dùng đã xem hoặc nhãn bbox. Chọn theo kích thước không phải mẫu ngẫu nhiên; chỉ dùng làm probe false positive trên 100 frame, không thay benchmark TAD, không đo báo động/giờ và chưa chứng minh độc lập camera. Không điều chỉnh model theo các frame này.
