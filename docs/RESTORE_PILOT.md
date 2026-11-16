# Phục hồi pilot từ các link đã tìm được

Ngày kiểm: **12/11/2026, Asia/Bangkok**. Lệnh chỉ lấy CADP 001407 và ba chuỗi DETRAC đã có trong hồ sơ. Đây là phục hồi dữ liệu, chưa tạo thêm sự kiện độc lập hoặc tập train.

## CADP: link trực tiếp đã xác minh

- Kho cha trong tài liệu: [manual/extracted_frames](https://drive.google.com/drive/folders/1BRIv9h4c_zbqJ6Ye4rVyFSo3K20BQt_v).
- Đã tìm được [thư mục 001407](https://drive.google.com/drive/folders/16vpAatZkuLguVMT4n4SMtrf3zu9VR3uE), có đủ `0.jpg` đến `220.jpg`.
- [Registry Drive](../data/registries/cadp_001407_drive_files.json) lưu ID công khai của từng ảnh; [fingerprint gốc](../data/registries/cadp_001407_images.csv) giữ nguyên từ máy phát triển.

```bash
python3 -B scripts/download_cadp_frames.py
python3 -B scripts/check_project_assets.py --profile cadp --check-hashes --strict
```

Ảnh chỉ được ghi vào `data_raw/cadp/frames/001407/` sau khi đúng cả số byte và SHA-256. Chạy lại sẽ kiểm rồi dùng ảnh đúng hash đã có; file khác nội dung được giữ nguyên và báo lỗi. Không cần tài khoản Drive để tải các file công khai này. Các input MP4/TXT/ZIP mã tác giả khác vẫn theo [GETTING_STARTED](GETTING_STARTED.md).

**Kết quả CADP đã chạy:** 221/221 ảnh khớp fingerprint và đọc được ở 1280×720; đối chiếu demo/VATIC đạt, giữ 4.641 dòng annotation, tái tạo 35 vùng đề xuất. 186 frame ngoài đề xuất vẫn chưa có chứng nhận âm toàn cảnh. Xác nhận xe và interval 96–130 được mang theo bằng `--review`; không suy source FPS hoặc giây từ video trình chiếu.

## DETRAC: nguồn chính thức bị giới hạn tải

[Trang tác giả](https://sites.google.com/view/daweidu/projects/ua-detrac) trỏ tới ZIP Drive 9.849.591.986 byte. Ngày 12/11 đọc được các HTTP Range đầu tiên và một phần central directory, đủ lấy kích thước/CRC của **toàn bộ 2.037 ảnh cần dùng**. Sau đó Drive trả `downloadQuotaExceeded`; endpoint API cũng xác nhận lỗi này. Nguồn cũ tại Albany trả HTTP 403. Không tải toàn ZIP.

Đã tìm được [bản sao công khai](https://huggingface.co/datasets/kalyan1729/sentineledgedataset) với đúng ba chuỗi. Dùng revision cố định **`de18d2110ac93e94f9955029ee20341e4cd5ea61`** làm kênh vận chuyển. Điều kiện đưa ảnh vào thư mục chuẩn:

1. Kích thước và SHA-256 khớp file ở revision mirror.
2. CRC và kích thước khớp member trong **ZIP chính thức**, không chỉ cùng tên.

[Nguồn và hash bằng chứng](../data/registries/detrac_subset_sources.json), [registry so nguồn/mirror](../data/registries/detrac_selected_images.csv). Tuyên bố license của mirror không thay điều kiện sử dụng/trích dẫn nguồn tác giả. Dữ liệu tải về để phục hồi pilot cục bộ.

```bash
python3 -B scripts/download_detrac_mirror.py --workers 6
python3 -B scripts/check_project_assets.py --profile detrac --check-hashes --strict
```

Đích: `data_raw/ua_detrac/DETRAC-Images/MVI_20011`, `MVI_20012`, `MVI_20032`, tương ứng 664/936/437 ảnh. Tổng byte ảnh dự kiến từ registry: 152.824.125. Script xuất report mới mỗi lượt; xem `complete`, `images`, `errors` để biết trạng thái thực. File sai CRC nằm ngoài thư mục chuẩn, không được dùng để train.

`scripts/download_detrac_subset.py` là phương án đọc trực tiếp từng phần ZIP nguồn, có trần 512 MiB và kiểm HTTP 206/Content-Range. Hiện đường tải này bị quota; không chạy lặp liên tục để cố vượt lỗi. Các Range và lỗi đã giữ trong audit.

## Môi trường xử lý ảnh và video trên Linux

Đã dựng `.venv` Python 3.12, numpy 2.5.2, OpenCV package 5.0.0.93. Máy chưa có FFmpeg hệ thống nên dùng binary FFmpeg 7.0.2 từ `imageio-ffmpeg==0.6.0` trong môi trường riêng. [requirements-data.txt](../requirements-data.txt) ghim môi trường này; chưa bao gồm PyTorch/Ultralytics.

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-data.txt
# Nếu FFmpeg hệ thống chưa có, tạo link cục bộ một lần:
.venv/bin/python -c 'from pathlib import Path; import imageio_ffmpeg; p=Path(".venv/bin/ffmpeg"); p.exists() or p.symlink_to(imageio_ffmpeg.get_ffmpeg_exe())'
export PATH="$PWD/.venv/bin:$PATH"
```

Khi CADP fingerprint đúng, dùng lại review đã có và chạy:

```bash
.venv/bin/python -B scripts/prepare_cadp_frames.py --review data/reviews/2026-10-19-cadp-001407-frame-confirmation.json
# Xem contact sheet / mapping_checks ở audit vừa in; khi mapping đạt:
.venv/bin/python -B scripts/prepare_cadp_frames.py --visual-check-confirmed --review data/reviews/2026-10-19-cadp-001407-frame-confirmation.json
```

Dùng đúng `audit_directory` được in làm `--mapping-report` cho `prepare_b0_candidates.py` theo hướng dẫn gốc. Công cụ xuất đề xuất từ chối ghi đè thư mục đã có. Nhãn vùng vẫn chờ duyệt, khác với review xe/interval đã xác nhận.

## Video tái mã hóa và xác nhận cũ

MP4 ghép bằng FFmpeg mới có thể khác SHA-256 với MP4 trên máy phát triển, dù cùng ảnh nguồn. Không sửa hash trong manifest/review để làm chúng khớp. Báo cáo ghép mới ghi hash thật; xem chúng như asset dẫn xuất của lượt phục hồi. Xác nhận âm của ba chuỗi cũ vẫn được giữ, nhưng công cụ index âm cũ yêu cầu **đúng MP4 đã rà + ZIP đầy đủ**, nên chưa tự coi video mới đáp ứng chốt kiểm đó.

Sau khi có các chuỗi ảnh, kiểm giải mã và ghép video bằng `prepare_detrac.py`. Để phân biệt với MP4 lịch sử, dùng `--video-root data_samples/ua_detrac/restored_2026-11-12`. Bước đăng ký dẫn xuất phải ghi fingerprint ảnh, nguồn tải, MP4 mới và liên hệ với phiếu rà cũ. Không đếm video ghép, clip con hoặc preview thành sự kiện độc lập mới.

**Tiếp theo để train B0:** duyệt quy tắc/35 vùng đề xuất, bổ sung nhiều sự kiện dương có VATIC/mapping, hoàn thiện camera/near-duplicate/hard negatives và split. ZIP mã tác giả tải lại vẫn chỉ có `data/1407.txt` là annotation mẫu; chưa có VATIC cho sự kiện mới.
