"""Kiểm FSM theo cặp và phạm vi evidence trên timeline ngắn."""
import json
import unittest
from pathlib import Path
from src.alert_fsm import AlertFSM

CFG = json.loads(Path('configs/alert_fsm_v1.json').read_text(encoding='utf-8'))


def item(a, b, score=1):
    return {'track_ids': [a, b], 'score': score}


class AlertTests(unittest.TestCase):
    def test_confirm_and_pair_specific_cooldown(self):
        f = AlertFSM(CFG)
        self.assertFalse(f.step('v', 0, [item(1, 2)])['emitted'])
        self.assertEqual(len(f.step('v', 1, [item(1, 2)])['emitted']), 1)
        f.step('v', 2, [item(1, 2), item(3, 4)])
        result = f.step('v', 3, [item(1, 2), item(3, 4)])
        self.assertEqual(result['emitted'][0]['track_ids'], [3, 4])

    def test_gap_censors_post_evidence(self):
        f = AlertFSM(CFG)
        f.step('v', 0, [item(1, 2)])
        f.step('v', 1, [item(1, 2)])
        out = f.step('v', 4, [])
        self.assertFalse(out['completed'][0]['evidence_complete'])

    def test_finish_marks_incomplete(self):
        f = AlertFSM(CFG)
        f.step('v', 0, [item(1, 2)])
        f.step('v', 1, [item(1, 2)])
        self.assertFalse(f.finish()[0]['evidence_complete'])

    def test_rearm_same_pair_after_low_without_repeating_persistent_high(self):
        cfg = dict(CFG, rearm_low_frames=2, missing_expire_frames=4, post_frames=0)
        f = AlertFSM(cfg)
        emitted = []
        for i, score in enumerate([1, 1, 1, 1, .25, .25, 1, 1]):
            emitted.extend(f.step('v', i, [item(1, 2, score)])['emitted'])
        self.assertEqual([e['confirmation_frame'] for e in emitted], [1, 7])
        self.assertFalse(emitted[0]['pre_complete'])

    def test_missing_does_not_count_as_low(self):
        f = AlertFSM(dict(CFG, rearm_low_frames=2, missing_expire_frames=4))
        f.step('v', 0, [item(1, 2)])
        f.step('v', 1, [item(1, 2)])
        f.step('v', 2, [])
        f.step('v', 3, [])
        self.assertFalse(f.step('v', 4, [item(1, 2)])['emitted'])

    def test_track_switch_is_explicit_new_pair_not_silent_identity_merge(self):
        f = AlertFSM(dict(CFG, rearm_low_frames=2, missing_expire_frames=4))
        f.step('v', 0, [item(1, 2)])
        f.step('v', 1, [item(1, 2)])
        f.step('v', 2, [item(1, 3)])
        result = f.step('v', 3, [item(1, 3)])
        self.assertEqual(result['emitted'][0]['track_ids'], [1, 3])


if __name__ == '__main__':
    unittest.main()
