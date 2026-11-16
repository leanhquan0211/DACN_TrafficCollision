"""Local dashboard around verified vehicle inference. No accident classifier.

Uses standard library HTTP, fixed artifact IDs, one CPU job, range video delivery.
Manual reviews live apart from research GT and never become automatic alerts.
"""
from __future__ import annotations

from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import threading
from urllib.parse import parse_qs, urlsplit, unquote
import uuid
from zoneinfo import ZoneInfo

from scripts.check_inference_outputs import inspect_report
from src.data_preparation import save_json, sha256_file

MAX_UPLOAD_BYTES = 100 * 1024 * 1024


def inspect_upload(path: Path) -> dict:
    """Validate a bounded MP4 input without inventing labels or source timing."""
    import cv2
    capture = cv2.VideoCapture(str(path))
    try:
        fps = capture.get(cv2.CAP_PROP_FPS)
        count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        ok, frame = capture.read()
        if not ok or frame is None or not 0 < fps <= 120 or not 0 < count <= 14400:
            raise ValueError("Không đọc được video MP4 hợp lệ hoặc FPS quá cao.")
        height, width = frame.shape[:2]
        if count / fps > 120 or max(width, height) > 1920 or width * height > 1920 * 1080:
            raise ValueError("Chọn clip tối đa 2 phút, độ phân giải tối đa Full HD; nên dùng 720p để chạy CPU.")
        fourcc = int(capture.get(cv2.CAP_PROP_FOURCC))
        codec = ''.join(chr((fourcc >> (8*i)) & 255) for i in range(4)).lower()
        if codec not in {"avc1", "h264"}:
            raise ValueError("Dùng MP4 mã hóa H.264 để cả hai video phát được trong trình duyệt.")
        return dict(container_fps=fps, reported_frames=count, width_px=width, height_px=height,
                    container_duration_s=count/fps, codec=codec)
    finally:
        capture.release()


def rooted(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Đường dẫn vượt thư mục dự án")
    return path


def byte_range(header: str | None, size: int) -> tuple[int, int]:
    if not header:
        return 0, size - 1
    match = re.fullmatch(r"bytes=(\d*)-(\d*)", header)
    if not match or not any(match.groups()):
        raise ValueError("Invalid range")
    first, last = match.groups()
    if not first:
        length = int(last)
        if length <= 0:
            raise ValueError("Invalid suffix")
        start, end = max(0, size-length), size-1
    else:
        start, end = int(first), min(int(last), size-1) if last else size-1
    if start > end or start >= size:
        raise ValueError("Range outside file")
    return start, end


class DemoState:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.token = secrets.token_urlsafe(32)
        self.lock = threading.RLock()
        self.job = None
        self.process = None
        self.closing = False
        self.runs = {}
        self.samples = {}
        self.errors = []
        self.storage = self.root / "outputs/demo_app"
        self.storage.mkdir(parents=True, exist_ok=True)
        catalog = json.loads((self.root / "configs/demo_catalog.json").read_text())
        for item in catalog["samples"]:
            item = dict(item, available=rooted(self.root, item["source"]).is_file(), runs={})
            self.samples[item["id"]] = item
            for mode, report_path in item["reports"].items():
                try:
                    entry = self.load_run(rooted(self.root, report_path), item)
                    if entry["report"]["mode"] != mode:
                        raise ValueError("Sai chế độ trong catalog")
                    self.register(entry, item)
                except (OSError, ValueError, KeyError, TypeError) as exc:
                    self.errors.append(f"{item['id']}/{mode}: {exc}")
        for record in sorted((self.storage / "uploads").glob("*/sample.json")):
            try:
                item = json.loads(record.read_text())
                folder = record.parent
                source = folder / "video.mp4"
                if (item["id"] != "upload-" + folder.name
                        or item["source"] != str(source.relative_to(self.root))
                        or sha256_file(source) != item["input_sha256"]
                        or item["timing_status"] != "unknown"
                        or item["training_ground_truth"] is not False):
                    raise ValueError("Video tải lên khác fingerprint hoặc metadata không hợp lệ")
                self.samples[item["id"]] = dict(item, available=True, runs={})
            except (OSError, ValueError, KeyError, TypeError) as exc:
                self.errors.append(f"Bỏ qua video tải lên: {record.parent.name}: {exc}")
        # Recover verified UI jobs on restart; original logs/reports remain unchanged.
        for report in sorted((self.storage / "runs").rglob("*.run.json")):
            try:
                metadata = json.loads((report.parents[1] / "sample.json").read_text())
                item = self.samples.get(metadata["id"])
                if item:
                    self.register(self.load_run(report, item), item)
            except (OSError, ValueError, KeyError, TypeError) as exc:
                self.errors.append(f"Bỏ qua output chưa kiểm được: {report.name}: {exc}")

    def load_run(self, path: Path, item: dict) -> dict:
        report = json.loads(path.read_text())
        paths = {
            "input_video": rooted(self.root, item["source"]),
            "weights_path": self.root / "yolov8n.pt",
            "output_video": path.parent / Path(report["output_video"]).name,
            "frame_cache": path.parent / Path(report["frame_cache"]).name,
        }
        inspect_report(path, path_overrides=paths)
        collision = report['mode'] == 'collision'
        if report.get('collision_detection_implemented') is not collision:
            raise ValueError('Chế độ report và trạng thái collision không khớp')
        events = json.loads(paths['output_video'].with_suffix('.events.json').read_text())['events'] if collision else []
        frames = [json.loads(line) for line in paths["frame_cache"].read_text().splitlines()]
        return dict(id=sha256_file(path)[:24], sample_id=item["id"], report=report,
                    report_path=path, paths=paths, frames=frames, events=events)

    def register(self, entry: dict, item: dict):
        with self.lock:
            checked = datetime.fromisoformat(entry['report']['checked_at'])
            if checked.tzinfo is None:
                raise ValueError('Lượt chạy thiếu múi giờ kiểm tra')
            mode = entry['report']['mode']
            previous = self.runs.get(item['runs'].get(mode))
            self.runs[entry["id"]] = entry
            # Recovery enumerates random UUID folders, not chronological jobs.
            # Preserve every report, but select the newest completed run so a
            # corrected rerun cannot be replaced by an older false alert.
            if previous is None or checked >= datetime.fromisoformat(previous['report']['checked_at']):
                item['runs'][mode] = entry['id']

    def catalog(self):
        with self.lock:
            return dict(token=self.token, samples=[{k: v for k, v in item.items() if k != "reports"}
                                                   for item in self.samples.values()],
                        errors=list(self.errors), collision_detection_implemented=True,
                        collision_experimental=True,
                        max_upload_bytes=MAX_UPLOAD_BYTES)

    def upload(self, stream, length: int, filename: str):
        if not 0 < length <= MAX_UPLOAD_BYTES:
            raise ValueError("Video phải nhỏ hơn hoặc bằng 100 MiB và không rỗng.")
        if not isinstance(filename, str) or not filename.lower().endswith(".mp4") or len(filename) > 255:
            raise ValueError("Chọn một file MP4 H.264.")
        # Original names are display-only. Never use a client filename as a path.
        display_name = filename.replace('\\', '/').rsplit('/', 1)[-1]
        folder = self.storage / "uploads" / uuid.uuid4().hex
        folder.mkdir(parents=True)
        partial = folder / "video.mp4.part"
        try:
            with partial.open("xb") as output:
                remaining = length
                while remaining:
                    chunk = stream.read(min(256*1024, remaining))
                    if not chunk:
                        raise ValueError("Tải video bị ngắt. Vui lòng thử lại.")
                    output.write(chunk)
                    remaining -= len(chunk)
            # OpenCV sniffs the container, independently of the client extension.
            info = inspect_upload(partial)
            target = folder / "video.mp4"
            partial.rename(target)
            item = dict(id="upload-"+folder.name, title=display_name,
                        description=f"Video tải lên · {info['width_px']}×{info['height_px']} · {info['reported_frames']} frame. Chưa có nhãn va chạm.",
                        source=str(target.relative_to(self.root)), timing_status="unknown",
                        input_sha256=sha256_file(target), uploaded_bytes=length,
                        uploaded_at=datetime.now(ZoneInfo("Asia/Bangkok")).isoformat(),
                        training_ground_truth=False, media=info)
            save_json(folder / "sample.json", item)
            with self.lock:
                self.samples[item["id"]] = dict(item, available=True, runs={})
            return dict(sample_id=item["id"], title=display_name, media=info)
        except BaseException:
            shutil.rmtree(folder, ignore_errors=True)
            raise

    def get_run(self, run_id: str):
        with self.lock:
            if run_id not in self.runs:
                raise ValueError("Không có lượt chạy đã kiểm này")
            return self.runs[run_id]

    def run_summary(self, run_id):
        entry = self.get_run(run_id)
        report = entry["report"]
        fields = ("mode", "processed_frames", "observation_count", "unique_track_ids", "container_fps",
                  "width_px", "height_px", "runtime", "device", "cpu_threads", "timing_status", "checked_at",
                  "input_sha256", "weights_sha256", "source_seconds_verified", "packages")
        details = {key: report[key] for key in fields}
        details.update(collision_detection_implemented=report['mode']=='collision',
                       collision_experimental=report.get('collision_experimental',False),
                       collision_method=report.get('collision_method'),event_count=report.get('event_count',0),
                       collision_quality=report.get('collision_quality'))
        vehicle_config = self.root / 'configs/vehicle_inference.json'
        details['vehicle_label_policy'] = report.get('vehicle_inference_config', {}).get('policy_id')
        details['current_vehicle_config'] = (vehicle_config.is_file()
            and report.get('vehicle_inference_config_sha256') == sha256_file(vehicle_config))
        if report['mode'] == 'collision':
            config = self.root / 'configs/collision_rules.json'
            details['current_collision_config'] = (config.is_file()
                and report.get('collision_config_sha256') == sha256_file(config))
        return dict(id=run_id, sample_id=entry["sample_id"], verified=True,
                    report=details,events=entry.get('events',[]),
                    counts=[len(f["observations"]) for f in entry["frames"]])

    def start_job(self, sample_id, mode):
        if mode not in {"detection", "tracking", "collision"} or sample_id not in self.samples:
            raise ValueError("Video/chế độ không hợp lệ")
        item = self.samples[sample_id]
        if not rooted(self.root, item["source"]).is_file() or not (self.root / "yolov8n.pt").is_file():
            raise ValueError("Thiếu video hoặc yolov8n.pt. Xem hướng dẫn cài đặt.")
        if not shutil.which("ffmpeg"):
            raise ValueError("Thiếu ffmpeg. Chạy lại bằng ./demo.sh để tự tìm FFmpeg.")
        with self.lock:
            if self.closing or (self.job and self.job["status"] in {"running", "validating"}):
                raise ValueError("CPU đang xử lý một video. Vui lòng chờ xong.")
            job_id = uuid.uuid4().hex
            folder = self.storage / "runs" / job_id
            folder.mkdir(parents=True)
            save_json(folder / "sample.json", {"id": sample_id})
            self.job = dict(id=job_id, sample_id=sample_id, mode=mode, status="running",
                            started_at=datetime.now(ZoneInfo("Asia/Bangkok")).isoformat())
            threading.Thread(target=self._worker, args=(item, mode, folder), daemon=True).start()
            return dict(self.job)

    def _worker(self, item, mode, folder):
        try:
            command = [sys.executable, "-B", str(self.root / f"scripts/run_{mode}.py"),
                       str(rooted(self.root, item["source"])), "--device", "cpu", "--cpu-threads", "4",
                       "--imgsz", "640", "--model", str(self.root / "yolov8n.pt"),
                       "--timing-status", item["timing_status"], "--output-dir", str(folder)]
            with (folder / "process.log").open("x") as log:
                with self.lock:
                    if self.closing:
                        raise RuntimeError("Ứng dụng đang dừng")
                    self.process = subprocess.Popen(command, cwd=self.root, stdout=log, stderr=subprocess.STDOUT)
                result = self.process.wait()
            if result:
                raise RuntimeError(f"Pipeline trả mã {result}. Xem outputs/demo_app/runs/{folder.name}/process.log")
            with self.lock:
                self.job["status"] = "validating"
            reports = list(folder.rglob("*.run.json"))
            if len(reports) != 1:
                raise ValueError("Pipeline không tạo đủ report")
            entry = self.load_run(reports[0], item)
            self.register(entry, item)
            with self.lock:
                self.job.update(status="complete", run_id=entry["id"])
        except Exception as exc:
            with self.lock:
                self.job.update(status="failed", error=str(exc))
        finally:
            with self.lock:
                self.process = None

    def stop(self):
        with self.lock:
            self.closing = True
            if self.process and self.process.poll() is None:
                self.process.terminate()

    def reviews(self, run_id):
        self.get_run(run_id)
        return [json.loads(p.read_text()) for p in sorted((self.storage / "reviews" / run_id).glob("*.json"))]

    def save_review(self, data):
        entry = self.get_run(data.get("run_id", ""))
        index = data.get("frame_index")
        if type(index) is not int or not 0 <= index < len(entry["frames"]):
            raise ValueError("Frame không hợp lệ")
        note = data.get("note", "")
        if not isinstance(note, str) or not note.strip() or len(note) > 1000:
            raise ValueError("Ghi nhận xét từ 1 đến 1000 ký tự")
        import cv2
        capture = cv2.VideoCapture(str(entry["paths"]["input_video"]))
        try:
            capture.set(cv2.CAP_PROP_POS_FRAMES, index)
            ok, frame = capture.read()
        finally:
            capture.release()
        if not ok or frame is None:
            raise ValueError("Không lấy được ảnh bằng chứng")
        identity = uuid.uuid4().hex
        folder = self.storage / "reviews" / entry["id"]
        folder.mkdir(parents=True, exist_ok=True)
        snapshot = folder / f"{identity}.jpg"
        if not cv2.imwrite(str(snapshot), frame):
            raise OSError("Không lưu được ảnh")
        observation = entry["frames"][index]
        record = dict(id=identity, run_id=entry["id"], sample_id=entry["sample_id"],
                      frame_index=index, video_time_s=observation["video_time_s"],
                      source_time_s=observation["source_time_s"], note=note.strip(),
                      created_at=datetime.now(ZoneInfo("Asia/Bangkok")).isoformat(),
                      method="manual_review", automatic_collision_alert=False, training_ground_truth=False,
                      input_sha256=entry["report"]["input_sha256"], run_report_sha256=sha256_file(entry["report_path"]),
                      snapshot_sha256=sha256_file(snapshot))
        save_json(folder / f"{identity}.json", record)
        return record


class DemoHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, state):
        self.state = state
        super().__init__(address, DemoHandler)


class DemoHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    @property
    def state(self):
        return self.server.state

    def log_message(self, fmt, *args):
        print(f"HTTP {self.address_string()} {fmt % args}", flush=True)

    def json(self, data, status=200):
        content = json.dumps(data, ensure_ascii=False, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(content)

    def file(self, path, download=False):
        size = path.stat().st_size
        try:
            start, end = byte_range(self.headers.get("Range"), size)
        except ValueError:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        partial = self.headers.get("Range") is not None
        self.send_response(206 if partial else 200)
        self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(end-start+1))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        if partial:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        if download:
            self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.end_headers()
        if self.command == "HEAD":
            return
        with path.open("rb") as stream:
            stream.seek(start)
            remaining = end-start+1
            while remaining > 0:
                chunk = stream.read(min(256*1024, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        try:
            if self.headers.get("Host") not in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}:
                self.json(dict(error="Chỉ dùng địa chỉ localhost của ứng dụng"), 403)
                return
            url = urlsplit(self.path)
            query = {k: v[0] for k, v in parse_qs(url.query).items()}
            if url.path == "/api/catalog":
                self.json(self.state.catalog())
            elif url.path == "/api/job":
                with self.state.lock:
                    job = dict(self.state.job) if self.state.job else None
                self.json(dict(job=job))
            elif url.path == "/api/run":
                self.json(self.state.run_summary(query["id"]))
            elif url.path == "/api/frame":
                entry = self.state.get_run(query["id"])
                index = int(query["index"])
                if not 0 <= index < len(entry["frames"]):
                    raise ValueError("Frame ngoài video")
                self.json(entry["frames"][index])
            elif url.path == "/api/reviews":
                self.json(self.state.reviews(query["id"]))
            elif url.path in {"/media", "/download"}:
                entry = self.state.get_run(query["id"])
                choices = dict(source=entry["paths"]["input_video"], output=entry["paths"]["output_video"],
                               cache=entry["paths"]["frame_cache"], report=entry["report_path"])
                if entry['report']['mode'] == 'collision':
                    choices['events'] = entry['paths']['output_video'].with_suffix('.events.json')
                self.file(choices[query["kind"]], download=url.path == "/download")
            elif url.path == '/collision-evidence':
                entry = self.state.get_run(query['run'])
                event = next((e for e in entry.get('events',[]) if e['event_id'] == query['event']),None)
                if event is None or query['kind'] not in {'snapshot','clip'}:
                    raise ValueError('Không có bằng chứng sự kiện này')
                artifact = (entry['paths']['output_video'].parent/event[query['kind']]).resolve()
                if not artifact.is_relative_to(entry['paths']['output_video'].parent.resolve()):
                    raise ValueError('Đường dẫn bằng chứng không hợp lệ')
                self.file(artifact)
            elif url.path == "/evidence":
                run_id, review_id = query["run"], query["review"]
                self.state.get_run(run_id)
                if not re.fullmatch(r"[a-f0-9]{32}", review_id):
                    raise ValueError("Mã bằng chứng không hợp lệ")
                self.file(self.state.storage / "reviews" / run_id / f"{review_id}.jpg")
            elif url.path == "/download-reviews":
                self.json(self.state.reviews(query["id"]))
            else:
                static = {"/": "index.html", "/app.js": "app.js", "/style.css": "style.css"}
                if url.path not in static:
                    self.json(dict(error="Không tìm thấy"), 404)
                    return
                self.file(self.state.root / "demo" / static[url.path])
        except (BrokenPipeError, ConnectionResetError):
            pass
        except (ValueError, KeyError, OSError) as exc:
            self.json(dict(error=str(exc)), 400)

    def do_POST(self):
        try:
            origin = self.headers.get("Origin")
            expected = f"http://{self.headers.get('Host')}"
            if (self.headers.get("Host") not in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
                    or self.headers.get("X-Demo-Token") != self.state.token or (origin and origin != expected)):
                self.close_connection = True
                self.json(dict(error="Phiên không hợp lệ. Tải lại trang."), 403)
                return
            length = int(self.headers.get("Content-Length", "0"))
            if self.path == "/api/uploads":
                self.close_connection = True
                if self.headers.get("Transfer-Encoding"):
                    raise ValueError("Yêu cầu Content-Length cho video tải lên")
                self.connection.settimeout(45)
                self.json(self.state.upload(self.rfile, length, unquote(self.headers.get("X-File-Name", ""))), 201)
                return
            if not 0 < length <= 16384:
                self.close_connection = True
                raise ValueError("Nội dung quá lớn hoặc rỗng")
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError("Nội dung phải là JSON object")
            if self.path == "/api/jobs":
                self.json(self.state.start_job(data["sample_id"], data["mode"]), 202)
            elif self.path == "/api/reviews":
                self.json(self.state.save_review(data), 201)
            else:
                self.json(dict(error="Không tìm thấy"), 404)
        except (ValueError, KeyError, OSError, TypeError) as exc:
            self.close_connection = True
            self.json(dict(error=str(exc)), 400)
