"""Kiểm cửa sổ causal và chống rò nhóm cho giao diện T0/B3."""
import unittest
from src.motion_features import MotionFeatures
from src.temporal_verifiers import CausalWindows, FEATURE_NAMES, TrainScaler, validate_group_split
from tests.test_motion_features import CFG, obs


class WindowTests(unittest.TestCase):
    def test_causal_padding_video_and_gap(self):
        motion = MotionFeatures(CFG)
        window = CausalWindows(3)
        motion.step(0, [obs(1, .3), obs(2, .4)])
        row = motion.step(1, [obs(1, .31), obs(2, .39)])
        row['video_id'] = 'v1'
        one = window.step(row)[0]
        self.assertEqual(one['observation_mask'], [0, 0, 1])
        self.assertEqual(one['window_frame_indices'], [None, None, 1])
        self.assertEqual(len(one['features'][-1]), len(FEATURE_NAMES))
        row2 = motion.step(2, [obs(1, .32), obs(2, .38)])
        row2['video_id'] = 'v1'
        self.assertEqual(window.step(row2)[0]['observation_mask'], [0, 1, 1])
        row2['video_id'] = 'v2'
        self.assertEqual(window.step(row2)[0]['observation_mask'], [0, 0, 1])

    def test_group_leakage(self):
        validate_group_split({'train': ['a'], 'val': ['b']})
        with self.assertRaises(ValueError):
            validate_group_split({'train': ['a'], 'val': ['a']})

    def test_scaler_train_only_and_mask(self):
        v = [1.0]*len(FEATURE_NAMES)
        s = TrainScaler()
        with self.assertRaises(ValueError):
            s.fit([v], split='val')
        s.fit([v], split='train')
        self.assertEqual(s.transform(v)[-7:], [1.]*7)
        self.assertEqual(s.state()['fit_split'], 'train')
        self.assertEqual(TrainScaler.from_state(s.state()).transform(v), s.transform(v))


class TorchWindowTests(unittest.TestCase):
    def test_gru_padding_and_serialization(self):
        import io
        import torch
        from src.temporal_verifiers import make_model
        torch.manual_seed(1)
        n = len(FEATURE_NAMES)+1
        model = make_model('gru').eval()
        actual = torch.randn(1, 2, n)
        actual[:, :, -1] = 1
        padded = torch.cat([torch.zeros(1, 3, n), actual], dim=1)
        batch = torch.cat([padded, torch.ones(1, 5, n)], dim=0)
        with torch.no_grad():
            direct = model(actual)
            self.assertTrue(torch.allclose(direct, model(padded), atol=1e-6))
            self.assertEqual(tuple(model(batch).shape), (2, 1))
            buf = io.BytesIO()
            torch.save(model.state_dict(), buf)
            buf.seek(0)
            restored = make_model('gru').eval()
            restored.load_state_dict(torch.load(buf, weights_only=True))
            self.assertTrue(torch.allclose(direct, restored(actual), atol=1e-6))
            with self.assertRaises(ValueError):
                model(torch.zeros(1, 2, n))


if __name__ == '__main__':
    unittest.main()
