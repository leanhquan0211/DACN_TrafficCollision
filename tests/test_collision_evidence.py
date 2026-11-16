"""Event integrity and evidence boundaries, independently of detector accuracy."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.check_inference_outputs import inspect_collision_events
from src.data_preparation import sha256_file


class CollisionEvidenceTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name);self.output=self.root/'result.mp4'
        self.snapshot=self.root/'event.jpg';self.snapshot.write_bytes(b'snapshot fixture')
        self.clip=self.root/'event.mp4';self.clip.write_bytes(b'clip fixture')
        self.cached=dict(event_id='event-0001',frame_index=10,automatic=True,needs_review=True,
                         decision='suspected_collision',score_is_probability=False,source_time_s=None)
        self.event=dict(**self.cached,snapshot='event.jpg',snapshot_sha256=sha256_file(self.snapshot),
                        clip='event.mp4',clip_sha256=sha256_file(self.clip))
        self.manifest=dict(method='fixture',experimental=True,score_is_probability=False,events=[self.event])
        self.report=dict(output_video=str(self.output),event_count=1,processed_frames=20,
                         collision_detection_implemented=True,collision_experimental=True,collision_method='fixture')

    def check(self):
        path=self.output.with_suffix('.events.json');path.write_text(json.dumps(self.manifest))
        self.report['events_sha256']=sha256_file(path)
        with patch('scripts.check_inference_outputs.probe_video',return_value={'decoded_frames':10}):
            return inspect_collision_events(self.report,[self.cached])

    def test_accepts_matching_causal_event_and_hashed_evidence_without_promoting_gt(self):
        result=self.check()
        self.assertTrue(result['events'][0]['needs_review'])
        self.assertIsNone(result['events'][0]['source_time_s'])
        self.assertFalse(result['score_is_probability'])

    def test_rejects_event_changed_from_frame_cache_and_probability_claim(self):
        self.event['frame_index']=11
        with self.assertRaisesRegex(ValueError,'causal'):self.check()
        self.event['frame_index']=10;self.manifest['score_is_probability']=True
        with self.assertRaisesRegex(ValueError,'scope'):self.check()

    def test_rejects_evidence_outside_run_directory_and_modified_evidence(self):
        self.event['snapshot']='../outside.jpg'
        with self.assertRaisesRegex(ValueError,'path/fingerprint'):self.check()
        self.event['snapshot']='event.jpg';self.snapshot.write_bytes(b'modified')
        with self.assertRaisesRegex(ValueError,'path/fingerprint'):self.check()

    def test_rejects_count_mismatch_and_duplicate_event_ids(self):
        self.report['event_count']=2
        with self.assertRaisesRegex(ValueError,'count'):self.check()
        self.manifest['events'].append(copy.deepcopy(self.event))
        path=self.output.with_suffix('.events.json');path.write_text(json.dumps(self.manifest))
        self.report['events_sha256']=sha256_file(path)
        with patch('scripts.check_inference_outputs.probe_video',return_value={'decoded_frames':10}):
            with self.assertRaisesRegex(ValueError,'causal'):
                inspect_collision_events(self.report,[self.cached,self.cached])


if __name__=='__main__':unittest.main()
