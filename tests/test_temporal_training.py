"""Kiểm gate nhãn, leakage, causal và scaler mà không huấn luyện model."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
import uuid
from src.temporal_training import make_examples, validate_records
from src.temporal_verifiers import FEATURE_NAMES


def row(split, label, group, video, camera, event):
    return {'split': split, 'label': label, 'label_status': 'verified', 'label_source': 'fixture',
            'group_id': group, 'video_id': video, 'camera_id': camera, 'source_event_id': event,
            'frame': 4, 'label_frame_interval': [3, 4], 'window_frame_indices': [None, 3, 4], 'observation_mask': [0, 1, 1],
            'features': [[0.0]*len(FEATURE_NAMES), [1.0]*13+[1.0]*7, [2.0]*13+[1.0]*7]}


def records():
    return [row('train', 0, 'ta', 'ta', 'ca', None), row('train', 1, 'tb', 'tb', 'cb', 'ea'),
            row('val', 0, 'va', 'va', 'cc', None), row('val', 1, 'vb', 'vb', 'cd', 'eb')]


class TrainingGateTests(unittest.TestCase):
    def test_valid_and_scaler_uses_train_only(self):
        items = records()
        self.assertEqual(validate_records(items, 3)['train_records'], 2)
        scaler, values = make_examples(items)
        self.assertEqual(scaler.state()['fit_split'], 'train')
        self.assertEqual(values[0]['window'][0], [0.0]*(len(FEATURE_NAMES)+1))

    def test_camera_leakage_and_unknown_label(self):
        items = records()
        items[2]['camera_id'] = 'ca'
        with self.assertRaises(ValueError):
            validate_records(items, 3)
        items = records()
        items[0]['label_status'] = 'unknown'
        with self.assertRaises(ValueError):
            validate_records(items, 3)

    def test_future_or_gap_rejected(self):
        items = records()
        items[0]['window_frame_indices'] = [None, 4, 5]
        with self.assertRaises(ValueError):
            validate_records(items, 3)
        items[0]['window_frame_indices'] = [None, 2, 4]
        with self.assertRaises(ValueError):
            validate_records(items, 3)

    def test_cli_check_passes_but_disabled_training_is_blocked(self):
        root = Path(__file__).resolve().parents[1]
        # Path.mkdir tránh ACL tạm không truy cập được của tempfile trên Windows sandbox.
        base = root/'.tmp'/('temporal_gate_'+uuid.uuid4().hex)
        base.mkdir(parents=True)
        data, release, config = base/'data.json', base/'release.json', base/'config.json'
        data.write_text(json.dumps({'records': records()}), encoding='utf-8')
        release.write_text(json.dumps({'data_sha256': hashlib.sha256(data.read_bytes()).hexdigest(),
                                       'feature_names': list(FEATURE_NAMES), 'can_train': False}), encoding='utf-8')
        config.write_text(json.dumps({'window_frames': 3, 'training_enabled': False}), encoding='utf-8')
        cmd = [sys.executable, str(root/'scripts/train_temporal_verifier.py'), '--data', str(data),
               '--release', str(release), '--config', str(config), '--kind', 'mlp']
        checked = subprocess.run(cmd+['--check'], cwd=root, capture_output=True, text=True)
        self.assertEqual(checked.returncode, 0, checked.stderr)
        blocked = subprocess.run(cmd+['--train', '--output-dir', str(base/'model')], cwd=root, capture_output=True, text=True)
        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn('Training blocked', blocked.stderr)
        self.assertFalse((base/'model').exists())


if __name__ == '__main__':
    unittest.main()
