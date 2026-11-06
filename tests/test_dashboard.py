"""Kiểm việc đọc artifact, phân biệt metric và ranh giới API; không dùng GPU.

Fixture tạo trong thư mục tạm, kiểm cả CSV đang ghi dở, path traversal và
video Range. Chạy bằng .venv-dashboard; suite train thiếu FastAPI sẽ skip API.
"""
from pathlib import Path
import hashlib
import json
import tempfile
import struct
import unittest
from unittest.mock import patch

from src.dashboard_data import DashboardStore

try:
    from fastapi.testclient import TestClient
    from scripts.serve_dashboard import create_app
except ImportError:
    TestClient = None


class DashboardDataTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.folder = self.root / "outputs/training/b0_fixture"
        self.folder.mkdir(parents=True)
        self.dataset = self.root / "data/processed/fixture"
        self.dataset.mkdir(parents=True)
        self.config = {"dataset": "data/processed/fixture/dataset.yaml", "epochs": 60}
        self.experiment = {"config": self.config, "epochs_completed": 2,
                           "official_bbox_metrics": {"val": {"metrics/mAP50(B)": .7, "metrics/mAP50-95(B)": .5}},
                           "fixed_threshold_metrics": {"val": {"tp": 3, "fp": 2, "fn": 1, "precision": .6, "recall": .75, "confidence": .25, "matching_iou": .5}},
                           "provenance_sha256": "fixture"}
        (self.folder / "experiment.json").write_text(json.dumps(self.experiment))
        (self.folder / "results.csv").write_text("epoch,metrics/precision(B),metrics/recall(B),metrics/mAP50(B),metrics/mAP50-95(B)\n1,.9,.4,.65,.5\n2,.8,.5,.7,.49\n3,.8,\n")
        (self.dataset / "provenance.csv").write_text("source_dataset,source_sequence,source_frame,leakage_group,collision_label,split\nA,clip,1,g1,positive,train\nA,clip,2,g1,negative,train\nA,other,3,g2,positive,val\n")
        self.store = DashboardStore(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_partial_epoch_is_not_plotted(self):
        self.assertEqual([r["epoch"] for r in self.store.run("b0_fixture")["history"]], [1, 2])

    def test_new_b0_is_visible_but_t0_stays_in_explore(self):
        b0 = self.root/'outputs/baselines/01_b0_image_detection/v099_new_b0'
        t0 = self.root/'outputs/baselines/04_t0_mlp/v099_new_t0'
        for folder, baseline in ((b0, 'B0'), (t0, 'T0')):
            folder.mkdir(parents=True)
            (folder/'artifact_identity.json').write_text(json.dumps({
                'run_id': folder.name, 'baseline': baseline, 'name': folder.name}), encoding='utf-8')
            (folder/'experiment.json').write_text(json.dumps(self.experiment), encoding='utf-8')
        self.assertEqual(self.store.folder(b0.name), b0)
        self.assertEqual(self.store.folder(t0.name), t0)
        ids = {item['id'] for item in self.store.runs()['runs']}
        self.assertIn(b0.name, ids)
        self.assertNotIn(t0.name, ids)
        catalog = {item['id'] for item in self.store.artifacts()['artifacts']}
        self.assertIn(t0.name, catalog)

    def test_best_epoch_uses_map95_not_last_or_peak_map50(self):
        self.assertEqual(self.store.run("b0_fixture")["best_epoch"], 1)

    def test_fixed_and_official_metrics_remain_separate(self):
        run = self.store.run("b0_fixture")
        self.assertEqual(run["metrics"]["map50"], .7)
        self.assertEqual(run["fixed"]["precision"], .6)
        self.assertEqual(run["history"][0]["precision"], .9)

    def test_missing_metric_is_null_not_zero(self):
        self.assertIsNone(self.store.run("b0_fixture")["metrics"]["recall"])

    def test_images_are_not_counted_as_independent_clips(self):
        d = self.store.dataset("b0_fixture")
        self.assertEqual((d["samples"], d["clips"], d["groups"]), (3, 2, 2))
        self.assertEqual(d["sources"][0]["negative"], 1)

    def test_split_filter_does_not_include_validation(self):
        d = self.store.dataset("b0_fixture", "train")
        self.assertEqual(d["samples"], 2)
        self.assertEqual(d["splits"], {"train": 2})

    def test_run_path_cannot_escape_root(self):
        for name in ("../secrets", "x/y", "..", "x\\y", "C:\\data"):
            with self.assertRaises(ValueError):
                self.store.folder(name)

    def test_secret_extensions_not_registered_as_media(self):
        p = self.root / ".env"
        p.write_text("fixture, not a real secret")
        self.assertIsNone(self.store.asset(p))

    def test_media_outside_root_is_denied(self):
        self.assertIsNone(self.store.asset(self.root.parent / "other.png"))

    def test_only_registered_media_can_be_read(self):
        self.assertIsNone(self.store.media_path("guessed-id"))
        image = self.root / "a.png"
        image.write_bytes(b"fixture")
        url = self.store.asset(image)
        self.assertEqual(self.store.media_path(url.rsplit("/", 1)[1]), image)

    def test_unknown_run_not_reported_running(self):
        (self.folder / "experiment.json").unlink()
        run = self.store.run("b0_fixture")
        self.assertEqual(run["status"], "unknown")
        self.assertEqual(run["live_status"], "not_verified")

    def test_cloud_deployment_and_local_artifact_share_one_run_entry(self):
        run_id = "b0_s960_sgd_low_lr_kaggle_v4"
        folder = self.root / "outputs/kaggle" / run_id
        folder.mkdir(parents=True)
        (folder / "deployment.json").write_text(json.dumps({"run": run_id, "notebook_version": 12,
            "config": "configs/b0_s960_sgd_low_lr_kaggle_v4.json", "phase": "submitted_not_completed"}))
        (self.root / "configs").mkdir()
        (self.root / "configs" / (run_id + ".json")).write_text(json.dumps({"lr0": .00015}))
        cloud_only = self.store.run(run_id)
        self.assertEqual((cloud_only["title"], cloud_only["cloud_version"], cloud_only["local_available"]),
                         ("K12 · SGD LR 0,00015", 12, False))
        self.assertEqual(sum(r["id"] == run_id for r in self.store.runs()["runs"]), 1)
        local = self.root / "outputs/training" / run_id
        local.mkdir()
        (local / "experiment.json").write_text(json.dumps(self.experiment))
        merged = self.store.run(run_id)
        self.assertTrue(merged["local_available"])
        self.assertEqual(merged["cloud_version"], 12)
        self.assertEqual(sum(r["id"] == run_id for r in self.store.runs()["runs"]), 1)

    def test_reads_do_not_change_artifacts(self):
        def fingerprints():
            return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.rglob("*") if p.is_file()}
        before = fingerprints()
        self.store.runs(); self.store.dataset("b0_fixture"); self.store.cases("b0_fixture"); self.store.temporal()
        self.assertEqual(before, fingerprints())

    def test_cloud_does_not_attempt_network_without_cli_environment(self):
        with patch("src.dashboard_data.subprocess.run") as run:
            self.assertEqual(self.store.cloud(11)["reason"], "cli_environment_missing")
            run.assert_not_called()

    def test_bbox_histogram_uses_original_png_dimensions(self):
        png = self.root / "clean.png"
        png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00"*8 + struct.pack(">II", 1000, 1000))
        (self.dataset / "provenance.csv").write_text("source_dataset,source_sequence,source_frame,leakage_group,collision_label,split,source_path\nA,clip,1,g1,positive,val,clean.png\nA,other,2,g2,negative,train,\n")
        cases = self.folder / "cases_val"; cases.mkdir()
        (cases / "predictions.json").write_text(json.dumps([{"source_sequence": "clip", "source_frame": "1", "gt_xyxy": [[0,0,10,10],[0,0,100,100]]}]))
        d = self.store.dataset("b0_fixture")["bbox_sizes"]
        self.assertEqual(d["measured"], 2)
        self.assertEqual([r["count"] for r in d["histogram"]], [1,0,1,0])

    def test_cloud_snapshot_timeout_does_not_start_train(self):
        python = self.root / ".tmp/kaggle_cli_env/Scripts/python.exe"
        python.parent.mkdir(parents=True); python.touch()
        import subprocess
        with patch("src.dashboard_data.subprocess.run", side_effect=subprocess.TimeoutExpired("fixture", 35)) as run:
            self.assertFalse(self.store.cloud(11)["connected"])
            command = run.call_args.args[0]
            self.assertIn("src.dashboard_cloud", command)
            self.assertNotIn("publish", command)

    def test_explorer_maps_once_and_leaves_unknown_unclassified(self):
        registry = self.root / 'data/registries/project_explorer.json'
        registry.parent.mkdir(parents=True)
        document = {'schema_version': 1, 'baseline_folders': [{'id': name} for name in ('B0', 'B1', 'B2', 'T0', 'B3')],
                    'runs': [{'run_id': 'b0_fixture', 'baseline': 'B0', 'version': 'v001_fixture',
                              'name': 'Fixture', 'lifecycle': 'historical'}], 'structure': [], 'dataset_sources': []}
        registry.write_text(json.dumps(document), encoding='utf-8')
        data = self.store.explore()
        self.assertEqual(len(data['runs']), 1)
        self.assertEqual((data['runs'][0]['id'], data['runs'][0]['version']), ('b0_fixture', 'v001_fixture'))
        self.assertEqual(data['runs'][0]['metrics']['map50'], .7)
        self.assertIs(self.store.explore(), data)
        document['runs'] = []
        registry.write_text(json.dumps(document), encoding='utf-8')
        other = DashboardStore(self.root).explore()['runs'][0]
        self.assertIsNone(other['baseline'])
        self.assertIsNone(other['version'])

    def test_explorer_rejects_duplicate_mapping_and_unsafe_path(self):
        registry = self.root / 'data/registries/project_explorer.json'
        registry.parent.mkdir(parents=True)
        entry = {'run_id': 'b0_fixture', 'baseline': 'B0', 'version': 'v001_fixture',
                 'name': 'Fixture', 'lifecycle': 'historical'}
        doc = {'schema_version': 1, 'baseline_folders': [{'id': n} for n in ('B0','B1','B2','T0','B3')],
               'runs': [entry, dict(entry)], 'structure': [], 'dataset_sources': []}
        registry.write_text(json.dumps(doc), encoding='utf-8')
        with self.assertRaises(ValueError):
            self.store.explore()
        doc['runs'] = [dict(entry, actual_path='outputs/training/../../.env')]
        registry.write_text(json.dumps(doc), encoding='utf-8')
        with self.assertRaises(ValueError):
            self.store.explore()


@unittest.skipIf(TestClient is None, "API tests require requirements-dashboard.txt")
class DashboardApiTests(unittest.TestCase):
    def setUp(self):
        DashboardDataTests.setUp(self)
        self.client = TestClient(create_app(self.root))

    def tearDown(self):
        DashboardDataTests.tearDown(self)

    def test_api_lists_fixture(self):
        response = self.client.get("/api/runs")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["runs"][0]["id"], "b0_fixture")

    def test_artifact_catalog_shows_canonical_and_legacy_without_media_scan(self):
        canonical = self.root/'outputs/system_evidence/v001_fixture'
        canonical.mkdir(parents=True)
        response = self.client.get('/api/artifacts')
        self.assertEqual(response.status_code, 200)
        rows = response.json()['artifacts']
        self.assertTrue(any(r['physical_path']=='outputs/system_evidence/v001_fixture' and r['storage_state']=='CANONICAL' for r in rows))
        self.assertTrue(any(r['physical_path']=='outputs/training/b0_fixture' and r['storage_state']=='LEGACY' for r in rows))

    def test_no_arbitrary_file_endpoint(self):
        self.assertEqual(self.client.get("/api/media/not-registered").status_code, 404)
        self.assertEqual(self.client.get("/api/unknown").status_code, 404)
        self.assertEqual(self.client.post("/api/runs/b0_fixture/train").status_code, 405)

    def test_invalid_query_is_rejected(self):
        self.assertEqual(self.client.get("/api/runs/b0_fixture/cases?limit=1000000").status_code, 422)
        self.assertEqual(self.client.get("/api/runs/b0_fixture/cases?offset=-1").status_code, 422)
        self.assertEqual(self.client.get("/api/kaggle?version=-1").status_code, 422)

    def test_video_range_response(self):
        p = self.root / "fixture.mp4"; p.write_bytes(bytes(range(100)))
        url = self.client.app.state.store.asset(p)
        response = self.client.get(url, headers={"Range": "bytes=10-19"})
        self.assertEqual(response.status_code, 206)
        self.assertEqual(response.content, bytes(range(10, 20)))


class DashboardCloudTests(unittest.TestCase):
    def test_status_survives_log_endpoint_failure(self):
        from src.dashboard_cloud import read_snapshot
        class ProxyError(Exception):
            pass
        with patch("scripts.kaggle_b0.credentials_present", return_value=True), \
             patch("scripts.kaggle_b0.api_client") as client:
            client.return_value.kernels_status.return_value = '{"status":"COMPLETE"}'
            client.return_value.kernels_logs.side_effect = ProxyError("private URL redacted")
            snapshot = read_snapshot(12)
        self.assertTrue(snapshot["connected"])
        self.assertEqual(snapshot["status"], "COMPLETE")
        self.assertFalse(snapshot["logs_available"])
        self.assertEqual(snapshot["history"], [])
        self.assertNotIn("private URL", snapshot["message"])

    def test_proxy_status_failure_has_actionable_safe_reason(self):
        from src.dashboard_cloud import read_snapshot
        class ProxyError(Exception):
            pass
        with patch("scripts.kaggle_b0.credentials_present", return_value=True), \
             patch("scripts.kaggle_b0.api_client") as client:
            client.return_value.kernels_status.side_effect = ProxyError("private URL redacted")
            snapshot = read_snapshot(12)
        self.assertEqual(snapshot["reason"], "proxy_unreachable")
        self.assertNotIn("private URL", snapshot["message"])


if __name__ == "__main__":
    unittest.main()
