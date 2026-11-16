"""Regression cho clock, missing-mask và bảo toàn output của cache suy luận."""

from pathlib import Path
import json
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from src.inference_export import FrameCache, observations, reserve_outputs
from src.data_preparation import sha256_file
from scripts.check_inference_outputs import inspect_report


def item(track_id):
    return dict(track_id=track_id, bbox_xyxy=[0, 0, 10, 10], missing_mask=0)


class FrameCacheTests(unittest.TestCase):
    def test_presentation_fps_does_not_become_source_seconds(self):
        for status in ("unknown", "presentation_only"):
            clock = FrameCache(20, status)
            a = clock.record(0, 0, [])
            b = clock.record(1, 50, [])
            self.assertEqual(a["video_time_s"], 0)
            self.assertEqual(b["video_time_s"], .05)
            self.assertIsNone(b["source_time_s"])
            self.assertEqual(clock.empty_frames, 2)

    def test_valid_source_pts_preserved_and_bad_pts_rejected(self):
        clock = FrameCache(25, "verified_source")
        clock.record(0, 0, [])
        self.assertEqual(clock.record(1, 37, [])["source_time_s"], .037)
        with self.assertRaisesRegex(ValueError, "nonmonotonic"):
            clock.record(2, 37, [])
        with self.assertRaises(ValueError):
            clock.record(2, float("nan"), [])

    def test_unknown_clock_fallback_is_explicit(self):
        clock = FrameCache(25)
        clock.record(0, 0, [])
        row = clock.record(1, 0, [])
        self.assertEqual(row["timestamp_origin"], "frame_index_over_container_fps")
        self.assertEqual(row["video_time_s"], .04)
        self.assertIsNone(row["source_time_s"])

    def test_missing_track_never_creates_box_and_ages_observations_only(self):
        clock = FrameCache(25, max_gap_frames=2)
        original = item(7)
        self.assertEqual(clock.record(0, 0, [original])["observations"][0]["track_age_observations"], 1)
        missing = clock.record(1, 40, [])
        self.assertEqual(missing["observations"], [])
        self.assertEqual(missing["missing_tracks"][0]["missing_mask"], 1)
        self.assertNotIn("bbox_xyxy", missing["missing_tracks"][0])
        self.assertEqual(clock.record(2, 80, [item(7)])["observations"][0]["track_age_observations"], 2)
        self.assertNotIn("track_age_observations", original)
        clock.record(3, 120, [])
        clock.record(4, 160, [])
        self.assertEqual(clock.record(5, 200, [])["expired_track_ids"], [7])

    def test_new_run_resets_state_and_untracked_detection_stays_null(self):
        a, b = FrameCache(25), FrameCache(25)
        a.record(0, 0, [item(7)])
        self.assertEqual(b.record(0, 0, [item(7)])["observations"][0]["track_age_observations"], 1)
        row = b.record(1, 40, [item(None)])["observations"][0]
        self.assertIsNone(row["track_id"])
        self.assertIsNone(row["track_age_observations"])

    def test_duplicate_ids_and_frame_jumps_rejected(self):
        clock = FrameCache(25)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            clock.record(0, 0, [item(7), item(7)])
        with self.assertRaisesRegex(ValueError, "consecutive"):
            clock.record(1, 40, [])


class OutputSafetyTests(unittest.TestCase):
    def test_sidecar_or_reservation_prevents_name_reuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "run.frames.jsonl").write_text("old cache")
            a = reserve_outputs(folder, "run")
            b = reserve_outputs(folder, "run")
            try:
                self.assertEqual(a["video"].name, "run_2.mp4")
                self.assertEqual(b["video"].name, "run_3.mp4")
                self.assertEqual((folder / "run.frames.jsonl").read_text(), "old cache")
            finally:
                a["lock"].unlink()
                b["lock"].unlink()

    def test_box_normalization_and_absent_track_id(self):
        class Tensor:
            def __init__(self, values): self.values = values
            def cpu(self): return self
            def tolist(self): return self.values
        boxes = SimpleNamespace(xyxy=Tensor([[10, 20, 30, 60]]), cls=Tensor([2]), conf=Tensor([.9]), id=None)
        result = SimpleNamespace(boxes=boxes)
        row = observations(result, {2: "car"}, 100, 100)[0]
        self.assertEqual(row["bbox_cxcywh_norm"], [.2, .4, .2, .4])
        self.assertIsNone(row["track_id"])
        boxes.xyxy = Tensor([[-1, 20, 30, 60]])
        with self.assertRaisesRegex(ValueError, "outside"):
            observations(result, {2: "car"}, 100, 100)


class CacheConsumerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.report_path = root/"run.json"
        self.report = dict(complete=True, schema_version=1, timing_evidence=None, timing_status="presentation_only",
                           processed_frames=2, observation_count=0, empty_frames=2, unique_track_ids=0,
                           width_px=100, height_px=100, container_fps=25, mode="tracking")
        for path_key, hash_key in (("input_video", "input_sha256"), ("weights_path", "weights_sha256"),
                                   ("frame_cache", "frame_cache_sha256"), ("output_video", "output_sha256")):
            path = root/path_key
            path.write_bytes(b"fixture")
            self.report[path_key], self.report[hash_key] = str(path), sha256_file(path)
        clock = FrameCache(25, "presentation_only")
        self.frames = [clock.record(0, 0, []), clock.record(1, 40, [])]

    def save(self):
        path = Path(self.report["frame_cache"])
        path.write_text("".join(json.dumps(f)+"\n" for f in self.frames))
        self.report["frame_cache_sha256"] = sha256_file(path)
        self.report_path.write_text(json.dumps(self.report))

    def test_valid_cache_rejected_after_content_tampering(self):
        self.save()
        with patch("scripts.check_inference_outputs.probe_video", return_value=dict(
                decoded_frames=2, width_px=100, height_px=100, fps=25)):
            self.assertTrue(inspect_report(self.report_path)["verified"])
        Path(self.report["frame_cache"]).write_text("corrupt content")
        with self.assertRaisesRegex(ValueError, "Fingerprint mismatch"):
            inspect_report(self.report_path)

    def test_presentation_seconds_cannot_be_promoted_in_cache(self):
        self.frames[0]["source_time_s"] = 0
        self.save()
        with self.assertRaisesRegex(ValueError, "Unverified source seconds"):
            inspect_report(self.report_path)

    def test_truncated_cache_rejected_even_if_hash_updated(self):
        self.frames.pop()
        self.save()
        with self.assertRaisesRegex(ValueError, "counts differ"):
            inspect_report(self.report_path)


if __name__ == "__main__":
    unittest.main()
