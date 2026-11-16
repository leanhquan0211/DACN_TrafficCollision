"""Real media upload, persistence, and rejection of incomplete/unsafe input."""
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from src.demo_server import DemoState, MAX_UPLOAD_BYTES, inspect_upload


class UploadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        executable = shutil.which("ffmpeg")
        if not executable:
            try:
                import imageio_ffmpeg
                executable = imageio_ffmpeg.get_ffmpeg_exe()
            except ImportError:
                raise unittest.SkipTest("H.264 fixture requires FFmpeg")
        cls.media_tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.media_tmp.cleanup)
        path = Path(cls.media_tmp.name) / "fixture.mp4"
        subprocess.run([executable, "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                        "color=c=blue:s=96x64:r=10:d=0.3", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)], check=True)
        cls.video = path.read_bytes()

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / "configs").mkdir()
        (self.root / "configs/demo_catalog.json").write_text('{"samples":[]}')
        self.state = DemoState(self.root)

    def test_real_upload_uses_generated_path_preserves_bytes_and_stays_outside_research(self):
        result = self.state.upload(io.BytesIO(self.video), len(self.video), "../../Cảnh mới.mp4")
        item = self.state.samples[result["sample_id"]]
        self.assertEqual(item["title"], "Cảnh mới.mp4")
        path = self.root / item["source"]
        self.assertTrue(path.is_relative_to(self.state.storage / "uploads"))
        self.assertEqual(path.read_bytes(), self.video)
        self.assertFalse(item["training_ground_truth"])
        self.assertEqual(item["timing_status"], "unknown")
        self.assertEqual(item["media"]["reported_frames"], 3)
        self.assertFalse((self.root / "data/manifest.csv").exists())
        self.assertEqual(DemoState(self.root).samples[item["id"]]["input_sha256"], item["input_sha256"])
        path.write_bytes(b"tampered")
        restarted = DemoState(self.root)
        self.assertNotIn(item["id"], restarted.samples)
        self.assertTrue(restarted.errors)

    def test_rejects_oversize_empty_wrong_extension_before_reading(self):
        for length, name in [(0,"test.mp4"),(MAX_UPLOAD_BYTES+1,"test.mp4"),(2,"test.html")]:
            with self.assertRaises(ValueError):
                self.state.upload(io.BytesIO(b"xx"), length, name)
        self.assertFalse((self.state.storage / "uploads").exists())

    def test_truncated_or_fake_media_is_removed_without_registering_sample(self):
        for payload, length in [(self.video[:10], len(self.video)), (b"not a video",11)]:
            with self.assertRaises(ValueError):
                self.state.upload(io.BytesIO(payload), length, "test.mp4")
            self.assertFalse(self.state.samples)
            self.assertEqual(list((self.state.storage / "uploads").iterdir()), [])

    def test_rejects_long_large_or_non_browser_codec_video(self):
        from unittest.mock import patch
        import numpy as np
        capture = unittest.mock.MagicMock()
        import cv2
        values = {cv2.CAP_PROP_FPS:10, cv2.CAP_PROP_FRAME_COUNT:3,
                  cv2.CAP_PROP_FOURCC:cv2.VideoWriter_fourcc(*"avc1")}
        capture.get.side_effect = lambda prop: values[prop]
        capture.read.return_value = (True,np.zeros((64,96,3),dtype=np.uint8))
        with patch("cv2.VideoCapture", return_value=capture):
            values[cv2.CAP_PROP_FRAME_COUNT]=1201
            with self.assertRaisesRegex(ValueError,"2 phút"):
                inspect_upload(Path("video.mp4"))
            values[cv2.CAP_PROP_FRAME_COUNT]=3
            capture.read.return_value=(True,np.zeros((1100,1920,3),dtype=np.uint8))
            with self.assertRaisesRegex(ValueError,"Full HD"):
                inspect_upload(Path("video.mp4"))
            capture.read.return_value=(True,np.zeros((64,96,3),dtype=np.uint8))
            values[cv2.CAP_PROP_FOURCC]=cv2.VideoWriter_fourcc(*"mp4v")
            with self.assertRaisesRegex(ValueError,"H.264"):
                inspect_upload(Path("video.mp4"))
        self.assertTrue(capture.release.called)


if __name__ == "__main__":
    unittest.main()
