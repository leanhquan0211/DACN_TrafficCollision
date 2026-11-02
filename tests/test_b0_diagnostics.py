"""Kiểm các ranh giới frame, nhãn unknown và ghép bbox của chẩn đoán B0.

Dùng dữ liệu nhỏ tự tạo để bắt lỗi tính metric, không đại diện kết quả model.
Chạy bằng unittest discover; không cần GPU hay video thật.
"""
import unittest
from src.b0_diagnostics import classify_case, positive_runs, resized_size_counts, temporal_summary, confidence_metrics, choose_confidence, require_unseen_negative_holdout, CausalScoreFilter, hard_negative_indices, filter_state_summary


def frame(index, count=1):
    return dict(source_frame=index,prediction_count=count,max_confidence=.8 if count else 0)


class B0DiagnosticsTests(unittest.TestCase):
    def test_temporal_presence_does_not_claim_onset_delay_or_bbox_counts(self):
        records=[dict(frame(i,0),ema_on=True) for i in range(8)]
        measured=filter_state_summary(records,'ema_on',[
            dict(event_id='reviewed',start_frame=3,end_frame_inclusive=6)],False)
        interval=measured['reviewed_intervals'][0]
        self.assertEqual(interval['active_frames'],4)
        self.assertTrue(interval['active_before_reviewed_interval'])
        self.assertNotIn('predicted_boxes',measured)
        self.assertEqual(measured['outside_intervals_label'],'unknown_not_negative')

    def test_hard_negative_sampling_keeps_uniform_context_and_temporal_coverage(self):
        scores=[i/100 for i in range(60)]
        anchors,hard=hard_negative_indices(scores)
        self.assertEqual((len(anchors),len(hard),len(anchors|hard)),(20,10,30))
        self.assertFalse(anchors&hard)
        self.assertEqual({i*10//60 for i in hard},set(range(10)))
        self.assertEqual((anchors,hard),hard_negative_indices(scores))
        with self.assertRaises(ValueError):hard_negative_indices([.5]*30)

    def test_causal_filters_need_warmup_reset_gaps_and_ignore_future(self):
        def run(scores):
            state=CausalScoreFilter(.27,3,5,.3)
            return [state.step(i,s) for i,s in enumerate(scores)]
        prefix=run([1,0,1,0,1])
        extended=run([1,0,1,0,1,0,0,0])
        self.assertEqual(prefix,extended[:5])
        self.assertFalse(any(p['kofn_on'] for p in prefix[:4]))
        self.assertTrue(prefix[4]['kofn_on'])
        state=CausalScoreFilter(.27,3,5,.3)
        for i in range(5):state.step(i,1)
        after_gap=state.step(7,0)
        self.assertFalse(after_gap['kofn_on']);self.assertEqual(after_gap['ema_score'],0)
        with self.assertRaises(ValueError):state.step(7,0)

    def test_fixed_temporal_filters_do_not_remove_persistent_false_signal(self):
        state=CausalScoreFilter(.27,3,5,.3)
        values=[state.step(i,.8) for i in range(20)]
        self.assertTrue(all(v['kofn_on'] for v in values[4:]))
        self.assertTrue(all(v['ema_on'] for v in values[2:]))

    def test_threshold_filter_rematches_and_counts_negative_boxes_separately(self):
        cases=[dict(source_sequence='positive',source_frame=1,collision_label='positive',gt_xyxy=[[0,0,10,10]],
                    predictions=[dict(xyxy=[0,0,10,10],confidence=.8),dict(xyxy=[30,30,40,40],confidence=.3)]),
               dict(source_sequence='negative',source_frame=1,collision_label='negative',gt_xyxy=[],
                    predictions=[dict(xyxy=[0,0,10,10],confidence=.6),dict(xyxy=[30,30,40,40],confidence=.4)])]
        low=confidence_metrics(cases,.25,.5)
        self.assertEqual((low['tp'],low['fp'],low['fn']),(1,3,0))
        self.assertEqual((low['negative_frames_with_predictions'],low['negative_predicted_boxes']),(1,2))
        high=confidence_metrics(cases,.6,.5)
        self.assertEqual((high['tp'],high['fp'],high['fn']),(1,0,0))
        missed=confidence_metrics(cases,.8,.5)
        self.assertEqual((missed['tp'],missed['fp'],missed['fn']),(0,0,1))

    def test_threshold_metrics_reject_unknown_and_duplicate_frames(self):
        unknown=dict(source_sequence='x',source_frame=1,collision_label='unknown',gt_xyxy=[],predictions=[])
        with self.assertRaises(ValueError):confidence_metrics([unknown],.25,.5)
        negative=dict(unknown,collision_label='negative')
        with self.assertRaises(ValueError):confidence_metrics([negative,negative],.25,.5)

    def test_operating_point_keeps_recall_floor_and_deterministic_tie_break(self):
        a=dict(confidence=.4,recall=.72,precision=.7,f1=.71,negative_frames_with_predictions=3)
        b=dict(confidence=.8,recall=.6,precision=.95,f1=.74,negative_frames_with_predictions=0)
        c=dict(a,confidence=.45,negative_frames_with_predictions=2)
        self.assertEqual(choose_confidence([a,b,c],.70),c)
        self.assertEqual(choose_confidence([a,b,c],0),b)
        with self.assertRaises(ValueError):choose_confidence([b],.70)

    def test_holdout_cannot_be_reused_after_failure_or_consumption(self):
        record=dict(model_predictions_seen=False,samples=[{'collision_label':'negative'}])
        require_unseen_negative_holdout(record)
        for changed in [dict(record,model_predictions_seen=True),dict(record,evaluation_status='started'),
                        dict(record,evaluation_status='failed_consumed_not_for_tuning')]:
            with self.assertRaises(ValueError):require_unseen_negative_holdout(changed)

    def test_size_bins_use_long_edge_scale_and_preserve_matching(self):
        case={'width':1280,'height':720,'objects':[
            {'min_side_pixels':24,'matched':False},{'min_side_pixels':64,'matched':True}]}
        small=resized_size_counts([case],640)
        larger=resized_size_counts([case],960)
        self.assertEqual(small['below_16']['missed'],1)
        self.assertEqual(larger['16_to_32']['missed'],1)
        self.assertEqual(small['32_to_64']['matched'],1)
        self.assertEqual(larger['32_to_64']['matched'],1)

    def test_runs_reset_on_empty_frame_gap_and_clip_end(self):
        result = positive_runs([frame(0),frame(1),frame(2,0),frame(3),frame(5),frame(6)])
        self.assertEqual([(r['start_frame'],r['end_frame_inclusive']) for r in result],[(0,1),(3,3),(5,6)])

    def test_unknown_outside_interval_is_not_negative(self):
        interval=dict(event_id='sample',start_frame=2,end_frame_inclusive=3)
        result=temporal_summary([frame(0),frame(1),frame(2,0),frame(3),frame(4)],[interval],False)
        self.assertEqual(result['reviewed_intervals'][0]['frames_with_any_bbox'],1)
        self.assertEqual(result['reviewed_intervals'][0]['first_bbox_offset_frames'],1)
        self.assertEqual(result['outside_intervals_label'],'unknown_not_negative')
        self.assertNotIn('false_raw_runs',result)

    def test_incomplete_gt_interval_and_contradicting_negative_rejected(self):
        event=dict(event_id='sample',start_frame=2,end_frame_inclusive=3)
        with self.assertRaises(ValueError):temporal_summary([frame(2)],[event],False)
        with self.assertRaises(ValueError):temporal_summary([frame(2),frame(3)],[event],True)
        with self.assertRaises(ValueError):positive_runs([frame(1),frame(1)])

    def test_negative_counts_include_boxes_and_not_only_frames(self):
        result=temporal_summary([frame(0,2),frame(1,0),frame(2,1)],[],True)
        self.assertEqual(result['frames_with_predictions'],2)
        self.assertEqual(result['predicted_boxes'],3)
        self.assertEqual(result['false_raw_runs'],2)

    def test_fp_geometry_and_fn_are_separate(self):
        case=dict(gt_xyxy=[[0,0,10,10]],tp=0,fn=1,predictions=[
            dict(xyxy=[5,0,15,10],confidence=.8,matched_gt=None),
            dict(xyxy=[30,30,40,40],confidence=.7,matched_gt=None)])
        result=classify_case(case,100,100,.5)
        self.assertEqual(result['categories']['localization_overlap_below_matching_iou'],1)
        self.assertEqual(result['categories']['false_positive_disjoint_from_annotated_region'],1)
        self.assertFalse(result['objects'][0]['matched'])
        self.assertAlmostEqual(result['objects'][0]['image_area_fraction'],.01)


if __name__=='__main__':unittest.main()
