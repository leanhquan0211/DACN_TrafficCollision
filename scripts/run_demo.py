"""Launch the local, offline demonstration dashboard."""
import argparse
import os
from pathlib import Path
import shutil
import sys
import threading
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.demo_server import DemoHTTPServer, DemoState


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--open", action="store_true", help="Open the local dashboard in the default browser")
    args = parser.parse_args()
    if not shutil.which("ffmpeg"):
        try:
            import imageio_ffmpeg
            folder = ROOT / ".cache/demo-bin"
            folder.mkdir(parents=True, exist_ok=True)
            executable = folder / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
            if not executable.exists():
                if os.name == "nt":
                    shutil.copy2(imageio_ffmpeg.get_ffmpeg_exe(), executable)
                else:
                    executable.symlink_to(imageio_ffmpeg.get_ffmpeg_exe())
            os.environ["PATH"] = str(folder) + os.pathsep + os.environ.get("PATH", "")
        except (ImportError, OSError):
            print("FFmpeg chưa có: xem docs/DEMO_GUIDE.md. Vẫn có thể xem kết quả đã lưu.", flush=True)
    print("Đang kiểm hash, cache và giải mã các video demo…", flush=True)
    state = DemoState(ROOT)
    try:
        server = DemoHTTPServer(("127.0.0.1", args.port), state)
    except OSError as exc:
        raise SystemExit(f"Không mở được cổng {args.port}: {exc}. Thử --port 8766.")
    url = f"http://127.0.0.1:{args.port}"
    print(f"Traffic Lab: {url}\nCtrl+C để dừng. Có chế độ cảnh báo va chạm bằng luật chuyển động thử nghiệm; cần rà bằng chứng.", flush=True)
    if args.open:
        threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        state.stop()
        server.server_close()


if __name__ == "__main__":
    main()
