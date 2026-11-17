import json
import importlib.util
import unittest

from src.detection_evaluation import coco_truth, evaluate_coco, parse_detrac, task_predictions


def frame(objects=None, ignored=None):
    return dict(id=1,file_name='fixture.jpg',width=100,height=100,objects=objects or [
        dict(source_id=1,source_class='car',truncation=0,bbox=[10,10,20,20])],ignored_regions=ignored or [])


def prediction(category=2,score=.9,box=None):
    return dict(image_id=1,category_id=category,score=score,bbox=box or [10,10,20,20])


@unittest.skipUnless(importlib.util.find_spec('pycocotools'), 'Install requirements-eval.txt for COCO evaluation tests')
class DetectionEvaluationTests(unittest.TestCase):
    def test_duplicate_predictions_cannot_inflate_recall(self):
        truth=coco_truth([frame()],'car_bus_common_classes')
        result,_=evaluate_coco(truth,[prediction(),prediction(score=.8)],(.25,))
        point=result['operating_points'][0]
        self.assertEqual((point['tp'],point['fp'],point['fn']),(1,1,0))
        self.assertEqual((point['precision'],point['recall']),(.5,1))
        self.assertEqual(json.loads(json.dumps(result))['operating_points'][0]['tp'],1)

    def test_wrong_class_can_match_localization_but_fails_class_detection(self):
        for task,counts in [('vehicle_localization',(1,0,0)),('car_bus_common_classes',(0,1,1))]:
            result,_=evaluate_coco(coco_truth([frame()],task),task_predictions([prediction(5)],task),(.25,))
            point=result['operating_points'][0]
            self.assertEqual((point['tp'],point['fp'],point['fn']),counts)

    def test_crowd_ignore_does_not_count_as_tp_or_hide_valid_ground_truth(self):
        truth=coco_truth([frame(ignored=[[0,0,100,100]])],'vehicle_localization')
        raw=[prediction(score=.99,box=[0,0,100,100]),prediction(score=.6)]
        result,_=evaluate_coco(truth,task_predictions(raw,'vehicle_localization'),(.25,))
        p=result['operating_points'][0]
        self.assertEqual((p['tp'],p['fp'],p['fn'],p['ignored_predictions']),(1,0,0,1))
        self.assertAlmostEqual(result['mAP50'],1)

    def test_empty_predictions_have_undefined_precision_and_zero_recall(self):
        result,_=evaluate_coco(coco_truth([frame()],'vehicle_localization'),[],(.25,))
        self.assertIsNone(result['operating_points'][0]['precision'])
        self.assertEqual(result['operating_points'][0]['recall'],0)
        self.assertEqual(result['mAP50'],0)

    def test_van_and_truncated_objects_are_ignored_without_relabeling(self):
        f=frame(objects=[dict(source_id=1,source_class='van',truncation=0,bbox=[10,10,20,20]),
                         dict(source_id=2,source_class='bus',truncation=.6,bbox=[40,40,20,20])])
        truth=coco_truth([f],'car_bus_common_classes')
        self.assertTrue(all(a['iscrowd'] for a in truth['annotations']))
        result,_=evaluate_coco(truth,[prediction()],(.25,))
        self.assertIsNone(result['mAP50'])
        self.assertIsNone(result['operating_points'][0]['recall'])
        self.assertEqual(result['operating_points'][0]['tp'],0)

    def test_xml_frame_sequence_and_classes_are_validated(self):
        xml=b'<sequence name="MVI_1"><ignored_region/><frame num="1"><target_list/></frame></sequence>'
        self.assertEqual(len(parse_detrac(xml,'MVI_1',1)),1)
        with self.assertRaisesRegex(ValueError,'sequence'):parse_detrac(xml,'MVI_2',1)
        with self.assertRaisesRegex(ValueError,'count'):parse_detrac(xml,'MVI_1',2)
        with self.assertRaisesRegex(ValueError,'frame'):parse_detrac(xml.replace(b'num="1"',b'num="3"'),'MVI_1',1)

    def test_unknown_source_class_and_invalid_box_are_not_silently_repaired(self):
        xml=b'<sequence name="MVI_1"><frame num="1"><target_list><target id="1"><box left="0" top="0" width="20" height="20"/><attribute vehicle_type="truck" truncation_ratio="0"/></target></target_list></frame></sequence>'
        with self.assertRaisesRegex(ValueError,'class'):parse_detrac(xml,'MVI_1',1)
        with self.assertRaisesRegex(ValueError,'box'):parse_detrac(xml.replace(b'truck',b'car').replace(b'width="20"',b'width="0"'),'MVI_1',1)


if __name__=='__main__':unittest.main()
