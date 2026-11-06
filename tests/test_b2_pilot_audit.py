"""Kiểm ghép hai ID annotation sang hai track khác nhau trong audit pilot."""
import unittest
from scripts.audit_b2_pilot import audit


def gt(ident, x1, x2):
    return {'source_frame': '96', 'gt_id': str(ident), 'visible': '1', 'outside': '0',
            'colliding': '1', 'xmin': str(x1), 'ymin': '0', 'xmax': str(x2), 'ymax': '10'}


class PilotAuditTests(unittest.TestCase):
    def test_two_tracks_needed_and_candidate_checked(self):
        gt_rows = [gt(0, 0, 5), gt(2, 5, 10)]
        frame = {'frame': 96, 'tracks': [{'track_id': 1, 'bbox_norm': [0, 0, .5, 1]},
                                         {'track_id': 2, 'bbox_norm': [.5, 0, 1, 1]}],
                 'candidates': [{'track_ids': [1, 2]}]}
        self.assertEqual(audit([frame], gt_rows, (0, 2), 96, 96, .5, 10, 10)[0]['status'], 'candidate_present')
        frame['candidates'] = []
        self.assertEqual(audit([frame], gt_rows, (0, 2), 96, 96, .5, 10, 10)[0]['status'], 'candidate_missing')
        frame['tracks'].pop()
        self.assertEqual(audit([frame], gt_rows, (0, 2), 96, 96, .5, 10, 10)[0]['status'], 'pair_not_both_matched')


if __name__ == '__main__':
    unittest.main()
