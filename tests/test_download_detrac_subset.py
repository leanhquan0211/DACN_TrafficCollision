"""HTTP Range phải đúng và không được đọc toàn dataset khi server trả HTML/200."""

from contextlib import redirect_stdout
import io
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from scripts.download_detrac_subset import RangeReader


class Response(io.BytesIO):
    def __init__(self, body, status, headers):
        super().__init__(body)
        self.status, self.headers = status, headers


class RangeReaderTests(unittest.TestCase):
    def test_zip_reads_and_cached_seeks(self):
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as z:
            z.writestr("fixture.txt", b"test data")
        payload = archive.getvalue()

        def get(request, **kwargs):
            start, end = map(int, re.fullmatch(r"bytes=(\d+)-(\d+)", request.headers["Range"]).groups())
            return Response(payload[start:end+1], 206, {"Content-Range": f"bytes {start}-{end}/{len(payload)}"})

        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(io.StringIO()), \
                patch("urllib.request.urlopen", side_effect=get):
            reader = RangeReader("https://fixture?file=1", Path(tmp)/"cache", block_size=32)
            with zipfile.ZipFile(reader) as z:
                self.assertEqual(z.read("fixture.txt"), b"test data")
            downloaded = reader.downloaded
            reader.seek(0)
            self.assertEqual(reader.read(), payload)
            self.assertEqual(reader.downloaded, downloaded)
            self.assertEqual(downloaded, len(payload) + 1)

    def test_non_range_response_body_is_never_read(self):
        response = Response(b"could be a whole dataset or a quota HTML page", 200, {})
        response.read = lambda *args: self.fail("Must stop before reading body")
        with tempfile.TemporaryDirectory() as tmp, patch("urllib.request.urlopen", return_value=response):
            with self.assertRaisesRegex(ValueError, "did not honor Range"):
                RangeReader("https://fixture?file=1", Path(tmp)/"cache")

    def test_wrong_range_is_rejected(self):
        response = Response(b"a", 206, {"Content-Range": "bytes 1-1/100"})
        with tempfile.TemporaryDirectory() as tmp, patch("urllib.request.urlopen", return_value=response):
            with self.assertRaisesRegex(ValueError, "range/size changed"):
                RangeReader("https://fixture?file=1", Path(tmp)/"cache")


if __name__ == "__main__":
    unittest.main()
