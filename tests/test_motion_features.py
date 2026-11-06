"""Kiểm đặc trưng causal, frame gap và track ID bằng dữ liệu minh họa."""
import json
import unittest
from pathlib import Path
from src.motion_features import MotionFeatures

CFG = json.loads(Path('configs/b2_motion_v1.json').read_text(encoding='utf-8'))


def obs(ident, x, y=.5):
    return {'track_id': ident, 'class_name': 'car', 'confidence': .9,
            'bbox_norm': [x-.03, y-.03, x+.03, y+.03]}


class MotionTests(unittest.TestCase):
    def test_approaching_pair_and_causal_history(self):
        motion = MotionFeatures(CFG)
        self.assertEqual(motion.step(0, [obs(1, .3), obs(2, .4)])['candidates'], [])
        row = motion.step(1, [obs(1, .31), obs(2, .39)])
        self.assertEqual(row['candidates'][0]['track_ids'], [1, 2])
        self.assertGreater(row['candidates'][0]['approach_per_frame'], 0)
        self.assertFalse(row['tracks'][0]['history_valid'])

    def test_stationary_nearby_no_overlap(self):
        m = MotionFeatures(CFG)
        m.step(0, [obs(1, .3), obs(2, .4)])
        self.assertEqual(m.step(1, [obs(1, .3), obs(2, .4)])['candidates'], [])

    def test_missing_and_gap_clear_history(self):
        m = MotionFeatures(CFG)
        m.step(0, [obs(1, .3)])
        self.assertEqual(m.step(1, [])['missing_track_ids'], [1])
        self.assertFalse(m.step(2, [obs(1, .4)])['tracks'][0]['velocity_valid'])
        self.assertEqual(m.step(5, [obs(1, .4)])['tracks'][0]['track_age'], 1)
        with self.assertRaises(ValueError):
            m.step(5, [])

    def test_invalid_bbox_duplicate_and_independent_video(self):
        m = MotionFeatures(CFG)
        with self.assertRaises(ValueError):
            m.step(0, [obs(1, .3), obs(1, .4)])
        with self.assertRaises(ValueError):
            MotionFeatures(CFG).step(0, [obs(1, 2)])
        self.assertEqual(MotionFeatures(CFG).step(0, [obs(1, .3)])['tracks'][0]['track_age'], 1)

    def test_overlap_is_only_a_signal(self):
        m = MotionFeatures(CFG)
        pair = [obs(1, .3), obs(2, .32)]
        m.step(0, pair)
        candidate = m.step(1, pair)['candidates'][0]
        self.assertEqual(candidate['rule_score'], .25)
        self.assertIn('not collision', candidate['meaning'])

    def test_large_overlapping_boxes_survive_center_distance_gate(self):
        a, b = obs(1, .3), obs(2, .46)
        a['bbox_norm'] = [.2, .3, .45, .7]
        b['bbox_norm'] = [.35, .3, .57, .7]
        old = MotionFeatures(CFG)
        old.step(0, [a, b])
        self.assertEqual(old.step(1, [a, b])['candidates'], [])
        new = MotionFeatures(dict(CFG, overlap_bypasses_distance=True))
        new.step(0, [a, b])
        result = new.step(1, [a, b])['candidates']
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['rule_score'], .25)

    def test_track_switch_and_recovery_do_not_inherit_velocity(self):
        m = MotionFeatures(dict(CFG, overlap_bypasses_distance=True))
        m.step(0, [obs(1, .3), obs(2, .4)])
        row = m.step(1, [obs(3, .31), obs(2, .39)])
        self.assertIn(1, row['missing_track_ids'])
        self.assertFalse(next(t for t in row['tracks'] if t['track_id'] == 3)['velocity_valid'])
        recovered = m.step(2, [obs(1, .32), obs(2, .38)])
        self.assertFalse(next(t for t in recovered['tracks'] if t['track_id'] == 1)['velocity_valid'])


if __name__ == '__main__':
    unittest.main()
