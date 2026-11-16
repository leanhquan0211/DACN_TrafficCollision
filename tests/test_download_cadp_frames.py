"""Downloader không được công bố HTML/file lỗi hoặc thay ảnh đã có."""

import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.download_cadp_frames import fetch_verified


class VerifiedDownloadTests(unittest.TestCase):
    def test_success_then_reuse_without_network(self):
        data = b"reviewed image bytes"
        sha = hashlib.sha256(data).hexdigest()
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "0.jpg"
            with patch("urllib.request.urlopen", return_value=io.BytesIO(data)):
                self.assertEqual(fetch_verified("https://fixture", target, len(data), sha), "downloaded_verified")
            with patch("urllib.request.urlopen", side_effect=AssertionError("Unexpected network call")):
                self.assertEqual(fetch_verified("https://fixture", target, len(data), sha), "reused_verified")
            self.assertEqual(target.read_bytes(), data)
            self.assertEqual(list(Path(tmp).iterdir()), [target])

    def test_hash_size_or_html_failure_leaves_no_image_or_temp(self):
        expected = b"reviewed image bytes"
        for data in (b"short", b"x" * len(expected), b"<html>" * 100):
            with self.subTest(data=data[:12]), tempfile.TemporaryDirectory() as tmp:
                target = Path(tmp) / "0.jpg"
                with patch("urllib.request.urlopen", return_value=io.BytesIO(data)):
                    with self.assertRaises(ValueError):
                        fetch_verified("https://fixture", target, len(expected), hashlib.sha256(expected).hexdigest())
                self.assertFalse(target.exists())
                self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_existing_mismatch_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "0.jpg"
            target.write_bytes(b"original local bytes")
            with patch("urllib.request.urlopen", side_effect=AssertionError("Unexpected network call")):
                with self.assertRaisesRegex(ValueError, "preserved"):
                    fetch_verified("https://fixture", target, 5, hashlib.sha256(b"other").hexdigest())
            self.assertEqual(target.read_bytes(), b"original local bytes")


if __name__ == "__main__":
    unittest.main()
