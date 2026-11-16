"""Boundaries of demo reviews, relocated artifacts and media seeking."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.demo_server import DemoState, byte_range, rooted
from src.data_preparation import sha256_file
from src.inference_export import FrameCache
from scripts.check_inference_outputs import inspect_report


class MediaTests(unittest.TestCase):
    def test_ranges_allow_browser_seeking_and_reject_invalid_requests(self):
        for header, expected in ((None,(0,99)),("bytes=10-19",(10,19)),("bytes=95-",(95,99)),
                                 ("bytes=-8",(92,99)),("bytes=90-999",(90,99))):
            self.assertEqual(byte_range(header,100),expected)
        for header in ("bytes=100-", "bytes=20-10", "bytes=-0", "bytes=0-1,3-4", "bytes=-", "anything"):
            with self.assertRaises(ValueError):
                byte_range(header,100)

    def test_catalog_cannot_escape_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            self.assertEqual(rooted(root,"video.mp4"),root/"video.mp4")
            with self.assertRaises(ValueError):
                rooted(root,"../outside.mp4")
            (root/"link").symlink_to("/tmp")
            with self.assertRaises(ValueError):
                rooted(root,"link/outside.mp4")


class RelocationTests(unittest.TestCase):
    def test_relocation_keeps_original_report_and_requires_original_fingerprints(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=root/"old.run.json";overrides={}
            report=dict(complete=True,schema_version=1,timing_evidence=None,timing_status="presentation_only",
                        processed_frames=2,observation_count=0,empty_frames=2,unique_track_ids=0,
                        width_px=100,height_px=100,container_fps=25,mode="tracking")
            for key,hash_key in (("input_video","input_sha256"),("weights_path","weights_sha256"),
                                 ("frame_cache","frame_cache_sha256"),("output_video","output_sha256")):
                target=root/key;target.write_bytes(b"test")
                overrides[key]=target;report[key]="/old-machine/"+key
                report[hash_key]=sha256_file(target)
            clock=FrameCache(25,"presentation_only")
            overrides["frame_cache"].write_text("".join(json.dumps(clock.record(i,i*40,[]))+"\n" for i in range(2)))
            report["frame_cache_sha256"]=sha256_file(overrides["frame_cache"])
            path.write_text(json.dumps(report));original=path.read_bytes()
            with patch("scripts.check_inference_outputs.probe_video",return_value=dict(decoded_frames=2,width_px=100,height_px=100,fps=25)):
                self.assertTrue(inspect_report(path,path_overrides=overrides)["verified"])
            self.assertEqual(path.read_bytes(),original)
            overrides["input_video"].write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError,"Fingerprint"):
                inspect_report(path,path_overrides=overrides)
            with self.assertRaisesRegex(ValueError,"Unsupported relocated"):
                inspect_report(path,path_overrides={"input_sha256":"fake"})


class ManualReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.state=DemoState.__new__(DemoState)
        self.state.storage=self.root/"storage"
        self.source=self.root/"input.mp4";self.report=self.root/"run.json"
        self.report.write_text('{"historical_report":true}')
        # Real frame retrieval is tested instead of mocking evidence creation.
        import cv2
        import numpy as np
        writer=cv2.VideoWriter(str(self.source),cv2.VideoWriter_fourcc(*"mp4v"),25,(32,24))
        for i in range(3):
            writer.write(np.full((24,32,3),i*70,dtype=np.uint8))
        writer.release()
        clock=FrameCache(25,"presentation_only")
        frames=[clock.record(i,i*40,[]) for i in range(3)]
        self.entry=dict(id="fixture",sample_id="sample",frames=frames,report_path=self.report,
                        paths={"input_video":self.source},report={"input_sha256":sha256_file(self.source)})
        self.state.get_run=lambda identity:self.entry if identity=="fixture" else (_ for _ in ()).throw(ValueError("Unknown run"))

    def test_manual_review_writes_real_evidence_but_never_promotes_ground_truth_or_source_seconds(self):
        record=self.state.save_review(dict(run_id="fixture",frame_index=1,note="Check ID"))
        self.assertEqual(record["method"],"manual_review")
        self.assertFalse(record["automatic_collision_alert"])
        self.assertFalse(record["training_ground_truth"])
        self.assertIsNone(record["source_time_s"])
        self.assertEqual(record["frame_index"],1)
        snapshot=self.state.storage/"reviews/fixture"/(record["id"]+".jpg")
        self.assertEqual(sha256_file(snapshot),record["snapshot_sha256"])
        import cv2
        self.assertTrue(60<float(cv2.imread(str(snapshot)).mean())<80)
        self.assertEqual(self.state.reviews("fixture"),[record])
        second=self.state.save_review(dict(run_id="fixture",frame_index=1,note="Another review"))
        self.assertNotEqual(record["id"],second["id"])
        self.assertEqual(len(self.state.reviews("fixture")),2)

    def test_invalid_frame_and_empty_note_do_not_create_evidence(self):
        for index in (-1,3,True,"1"):
            with self.assertRaises(ValueError):
                self.state.save_review(dict(run_id="fixture",frame_index=index,note="check"))
        for note in ("", " ", "x"*1001,None):
            with self.assertRaises(ValueError):
                self.state.save_review(dict(run_id="fixture",frame_index=0,note=note))
        self.assertFalse(self.state.storage.exists())


if __name__=="__main__":
    unittest.main()
