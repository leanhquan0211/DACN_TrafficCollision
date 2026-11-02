"""Kiểm thống kê train/val, không để lọt case test vào báo cáo."""
import csv
import uuid
import unittest
from pathlib import Path
from scripts.analyze_b0_training_data import analyze


def write_csv(path, rows):
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=rows[0].keys())
        writer.writeheader();writer.writerows(rows)


class DistributionTests(unittest.TestCase):
    def test_group_and_small_bbox_false_negative(self):
        root=Path('.tmp')/('b0_distribution_test_'+uuid.uuid4().hex);root.mkdir(parents=True)
        (root/'label.txt').write_text('0 .5 .5 .05 .1\n',encoding='utf-8')
        row=dict(split='val',collision_label='positive',source_dataset='ACCIDENT',leakage_group='a',
                 source_sequence='a_00',source_frame='4',export_label='label.txt')
        test=dict(row,split='test',leakage_group='test',export_label='does-not-exist')
        write_csv(root/'provenance.csv',[row,test])
        case=dict(leakage_group='a',source_sequence='a_00',source_frame='4',collision_label='positive',fn='1')
        write_csv(root/'cases.csv',[case])
        result=analyze(root/'provenance.csv',root/'cases.csv',root)
        self.assertEqual(result['validation_fn_by_bbox_area'],{'<1%':1})
        self.assertEqual(result['validation_cases_matched'],1)
        self.assertEqual(result['sample_groups'][0]['groups'],1)
        self.assertFalse(result['test_inference'])

    def test_mismatched_cases_rejected(self):
        root=Path('.tmp')/('b0_distribution_test_'+uuid.uuid4().hex);root.mkdir(parents=True)
        row=dict(split='val',collision_label='negative',source_dataset='TAD',leakage_group='a',
                 source_sequence='a',source_frame='0',export_label='')
        case=dict(leakage_group='b',source_sequence='b',source_frame='0',collision_label='negative',fn='0')
        write_csv(root/'provenance.csv',[row]);write_csv(root/'cases.csv',[case])
        with self.assertRaisesRegex(ValueError,'do not match'):
            analyze(root/'provenance.csv',root/'cases.csv',root)


if __name__=='__main__':unittest.main()
