"""Kiểm luật event, nhãn chưa biết, camera và thời gian bằng fixture nhỏ."""
import unittest
from src.event_evaluator import compare_matched_recall, evaluate

POLICY = {'version': 'fixture-v1', 'threshold': .5, 'cooldown_frames': 0}


def fixture(scores, events=(), labels=None, camera='cam', fps=None):
    return {'videos': [{'video_id': 'v', 'camera_id': camera,
                        'source_timing_verified': bool(fps), 'source_fps': fps}],
            'events': list(events),
            'samples': [{'video_id': 'v', 'camera_id': camera, 'frame': f,
                         'score': s, 'label': (labels or {}).get(f, 'negative'),
                         'provenance': 'fixture'} for f, s in scores]}


def event(name, start, end, camera='cam'):
    return {'video_id': 'v', 'camera_id': camera, 'event_id': name,
            'onset_frame': start, 'end_frame': end, 'status': 'verified', 'label_source': 'fixture'}


class EventTests(unittest.TestCase):
    def test_two_events_and_repeat(self):
        data = fixture(enumerate([0, 1, 0, 1, 0, 1, 0]), [event('a', 1, 4), event('b', 5, 6)])
        out = evaluate(data, POLICY)
        self.assertEqual((out['metrics']['tp'], out['metrics']['fp'], out['metrics']['fn']), (2, 1, 0))

    def test_overlap_one_to_one_and_deterministic(self):
        data = fixture(enumerate([0, 1, 0, 1]), [event('b', 1, 3), event('a', 1, 2)])
        out = evaluate(data, POLICY)
        self.assertEqual([m['event_id'] for m in out['matches']], ['a', 'b'])

    def test_early_active_censored(self):
        data = fixture(enumerate([0, 1, 1, 1, 0]), [event('a', 2, 3)], {1: 'unknown', 2: 'positive', 3: 'positive'})
        out = evaluate(data, POLICY)
        self.assertEqual(out['metrics']['censored_events'], 1)
        self.assertEqual(out['alerts'][0]['early_for_events'], ['a'])
        self.assertEqual((out['metrics']['tp'], out['metrics']['fp'], out['metrics']['fn']), (0, 0, 0))

    def test_unknown_alert_and_missing_interval(self):
        data = fixture([(0, 1), (1, 0), (3, 0)], [event('a', 1, 3)], {0: 'unknown'})
        out = evaluate(data, POLICY)
        self.assertEqual(out['metrics']['unknown_alerts'], 1)
        self.assertEqual(out['censored'][0]['reason'], 'missing_event_frames')

    def test_camera_rejected(self):
        with self.assertRaises(ValueError):
            evaluate(fixture([(0, 0)], [event('a', 0, 0, 'other')]), POLICY)

    def test_ignore_interval_overrides_negative_label(self):
        ignored = dict(event('uncertain', 0, 1), status='ignore')
        out = evaluate(fixture([(0, 1), (1, 0)], [ignored]), POLICY)
        self.assertEqual(out['metrics']['unknown_alerts'], 1)
        self.assertEqual(out['metrics']['fp'], 0)

    def test_ignore_overlapping_verified_event_censors_instead_of_tp_or_fn(self):
        ignored = dict(event('ignored', 1, 1), status='ignore')
        data = fixture(enumerate([0, 1, 0]), [event('real', 1, 1), ignored], {1: 'ignore'})
        out = evaluate(data, POLICY)
        self.assertEqual((out['metrics']['tp'], out['metrics']['fn'], out['metrics']['censored_events']), (0, 0, 1))

    def test_matched_recall_requires_same_events(self):
        a = evaluate(fixture(enumerate([0, 1]), [event('a', 1, 1)]), POLICY)
        b = evaluate(fixture(enumerate([0, 0]), [event('a', 1, 1)]), POLICY)
        self.assertFalse(compare_matched_recall(a, b)['matched_within_tolerance'])
        with self.assertRaises(ValueError):
            compare_matched_recall(a, evaluate(fixture([(0, 0)]), POLICY))

    def test_point_onset_requires_explicit_tolerance_and_never_counts_early(self):
        point = dict(event('a', 1, 1), end_frame=None)
        data = fixture(enumerate([0, 0, 0, 1]), [point])
        with self.assertRaises(ValueError):
            evaluate(data, POLICY)
        out = evaluate(data, dict(POLICY, post_onset_tolerance_frames=2))
        self.assertEqual(out['matches'][0]['delay_frames'], 2)
        early = fixture(enumerate([1, 1, 0, 0]), [point], {0: 'unknown', 1: 'positive'})
        out = evaluate(early, dict(POLICY, post_onset_tolerance_frames=2))
        self.assertEqual(out['metrics']['tp'], 0)
        self.assertEqual(out['metrics']['censored_events'], 1)

    def test_missing_timestamp_and_verified_fps(self):
        for fps, expected in ((None, None), (10, .1)):
            out = evaluate(fixture(enumerate([0, 0, 1]), [event('a', 1, 2)], fps=fps), POLICY)
            self.assertEqual(out['matches'][0]['delay_seconds'], expected)

    def test_empty_and_boundary(self):
        out = evaluate({'videos': [], 'events': [], 'samples': []}, POLICY)
        self.assertIsNone(out['metrics']['precision'])
        self.assertIsNone(evaluate(fixture([(0, 1)]), POLICY)['metrics']['f1'])
        out = evaluate(fixture(enumerate([0, .5, 1]), [event('a', 2, 2)]), POLICY)
        self.assertEqual(out['matches'][0]['delay_frames'], 0)

    def test_cooldown_and_negative_coverage(self):
        data = fixture(enumerate([0, 1, 0, 1]))
        data['videos'][0].update(fully_labeled_negative=True, first_frame=0, last_frame=3,
                                 duration_verified=True, duration_seconds=4)
        out = evaluate(data, dict(POLICY, cooldown_frames=2))
        self.assertEqual(out['metrics']['false_alerts_per_hour'], 900)
        self.assertEqual(out['alerts'][1]['classification'], 'suppressed_cooldown')
        data['videos'][0]['last_frame'] = 4
        with self.assertRaises(ValueError):
            evaluate(data, POLICY)


if __name__ == '__main__':
    unittest.main()
