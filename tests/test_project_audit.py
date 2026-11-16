"""Regression: leakage, thời gian giả và fingerprint không được báo đạt."""

import csv
import hashlib
import io
import sys
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import check_environment, check_project_assets
from src.manifest_audit import REQUIRED, audit_manifest


def asset(name, split="unassigned", **kwargs):
    row = dict.fromkeys(REQUIRED, "")
    row.update(video_id=name, relative_path=f"data/{name}.mp4", source_dataset="fixture",
               source_sequence=name, collision_label="negative", split=split,
               fps_status="verified_source", asset_role="sequence_video")
    row.update(kwargs)
    return row


class ManifestAuditTests(unittest.TestCase):
    def codes(self, rows):
        return {x["code"] for x in audit_manifest(rows)["issues"]}

    def test_transitive_camera_and_event_leakage(self):
        rows = [asset("a", "train", camera_id="cam"),
                asset("b", camera_id="cam", source_event_id="event"),
                asset("c", "test", source_event_id="event")]
        report = audit_manifest(rows)
        self.assertEqual(report["groups"][0]["asset_ids"], ["a", "b", "c"])
        self.assertIn("split_leakage", self.codes(rows))

    def test_hash_and_parent_link_even_without_matching_sequence(self):
        for other in (asset("b", "test", sha256="abcd"),
                      asset("b", "test", derived_from="data\\a.mp4")):
            self.assertIn("split_leakage", self.codes([asset("a", "train", sha256="abcd"), other]))

    def test_siblings_with_unregistered_parent_stay_together(self):
        self.assertIn("split_leakage", self.codes([
            asset("a", "train", derived_from="raw/source"),
            asset("b", "test", derived_from="raw/source")]))

    def test_missing_group_keys_do_not_merge_unrelated_assets(self):
        report = audit_manifest([asset("a", "train"), asset("b", "test")])
        self.assertEqual(len(report["groups"]), 2)
        self.assertTrue(report["metadata_consistent"])
        self.assertFalse(report["independent_groups_verified"])

    def test_preview_is_not_new_event_or_training_input(self):
        rows = [asset("a", collision_label="positive", source_event_id="event"),
                asset("preview", "train", collision_label="positive", source_event_id="event",
                      asset_role="annotation_preview")]
        self.assertEqual(audit_manifest(rows)["known_positive_events"], 1)
        self.assertIn("overlay_in_split", self.codes(rows))

    def test_unknown_and_negative_labels_are_not_invented(self):
        self.assertIn("unreviewed_label_in_split", self.codes([asset("a", "train", collision_label="unknown")]))
        self.assertIn("negative_has_event_time", self.codes([asset("a", onset_s="1", end_s="2")]))
        self.assertIn("invalid_asset_id", self.codes([asset("a"), asset("a")]))

    def test_source_seconds_must_be_finite_ordered_and_verified(self):
        for start, stop in (("nan", "2"), ("1", "inf"), ("3", "2"), ("-1", "2")):
            self.assertIn("invalid_event_time", self.codes([
                asset("a", collision_label="positive", onset_s=start, end_s=stop)]))
        self.assertIn("unverified_event_seconds", self.codes([
            asset("a", collision_label="positive", onset_s="1", end_s="2", fps_status="presentation_only")]))
        self.assertIn("incomplete_event_time", self.codes([asset("a", onset_s="1")]))

    def test_schema_error_is_explicit(self):
        with self.assertRaisesRegex(ValueError, "missing columns"):
            audit_manifest([{"video_id": "a"}])
        self.assertIn("empty_manifest", self.codes([]))


class AssetFingerprintTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        patcher = patch.object(check_project_assets, "ROOT", self.root)
        patcher.start()
        self.addCleanup(patcher.stop)
        (self.root / "frames").mkdir()
        (self.root / "frames/0.jpg").write_bytes(b"fingerprint fixture, not an image decode test")
        self.reference = dict(relative_path="frames/0.jpg", sha256=hashlib.sha256(
            (self.root / "frames/0.jpg").read_bytes()).hexdigest())
        self.asset = dict(id="fixture", path="frames", source_url="fixture", kind="download_directory",
                          expected_image_count=1, image_inventory="inventory.csv")

    def inventory(self, rows):
        with (self.root / "inventory.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=["relative_path", "sha256"])
            writer.writeheader()
            writer.writerows(rows)

    def test_matching_hash_cannot_override_expected_count(self):
        self.inventory([self.reference])
        self.assertEqual(check_project_assets.inspect(self.asset, True)["status"], "verified_image_fingerprints")
        self.asset["expected_image_count"] = 2
        self.assertEqual(check_project_assets.inspect(self.asset, True)["status"], "image_fingerprint_mismatch")

    def test_duplicate_inventory_cannot_hide_unchecked_image(self):
        (self.root / "frames/1.jpg").write_bytes(b"not verified")
        self.inventory([self.reference, self.reference])
        self.asset["expected_image_count"] = 2
        self.assertEqual(check_project_assets.inspect(self.asset, True)["status"], "image_fingerprint_mismatch")

    def test_inventory_cannot_certify_different_directory(self):
        (self.root / "elsewhere").mkdir()
        (self.root / "elsewhere/0.jpg").write_bytes((self.root / "frames/0.jpg").read_bytes())
        self.inventory([dict(self.reference, relative_path="elsewhere/0.jpg")])
        with self.assertRaisesRegex(ValueError, "outside asset directory"):
            check_project_assets.inspect(self.asset, True)
        with self.assertRaises(ValueError):
            check_project_assets.within_root("../outside")


class EnvironmentExitTests(unittest.TestCase):
    def test_missing_or_broken_dependency_returns_failure_even_with_torch(self):
        torch = SimpleNamespace(version=SimpleNamespace(cuda=None),
                                cuda=SimpleNamespace(is_available=lambda: False))
        for failure in (ImportError("missing"), RuntimeError("binary ABI mismatch")):
            def load(name):
                if name == "torchvision":
                    raise failure
                return torch if name == "torch" else SimpleNamespace(__version__="fixture")
            output = io.StringIO()
            output.reconfigure = lambda **kwargs: None
            with patch.object(check_environment.importlib, "import_module", side_effect=load), \
                    patch.dict(sys.modules, {"torch": torch}), \
                    patch.object(sys, "argv", ["check_environment.py"]), patch.object(sys, "stdout", output):
                self.assertEqual(check_environment.main(), 1)


if __name__ == "__main__":
    unittest.main()
