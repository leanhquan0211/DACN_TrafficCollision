"""Behavioral checks: causal alerts require interaction and a motion change."""
import copy
import json
from pathlib import Path
import unittest

from src.collision_rules import CollisionRules

CONFIG = json.loads((Path(__file__).resolve().parents[1]/'configs/collision_rules.json').read_text())


def obj(ident, x, y=100, confidence=.8):
    return dict(track_id=ident,bbox_xyxy=[x,y,x+40,y+40],confidence=confidence,missing_mask=0)


def frame(index, objects):
    return dict(frame_index=index,video_time_s=index/25,source_time_s=None,observations=objects)


def impact(index, shift=0, ids=(1,2)):
    return [obj(ids[0],100+shift),obj(ids[1],240-4*min(index,29)+shift)]


class CollisionRuleTests(unittest.TestCase):
    def replay(self, sequence, config=CONFIG):
        engine=CollisionRules(config)
        outputs=[engine.update(frame(i,objects)) for i,objects in enumerate(sequence)]
        return engine,outputs

    def test_approach_contact_stop_produces_one_automatic_event_without_gt_or_source_seconds(self):
        engine,_=self.replay([impact(i) for i in range(80)])
        self.assertEqual(len(engine.events),1)
        event=engine.events[0]
        self.assertGreater(event['frame_index'],29)
        self.assertEqual(event['track_ids'],[1,2])
        self.assertTrue(event['automatic'])
        self.assertTrue(event['needs_review'])
        self.assertIsNone(event['source_time_s'])
        self.assertFalse(event['score_is_probability'])
        self.assertTrue(event['features']['approach'])
        self.assertTrue(any(event['features']['sudden_stop']))

    def test_stationary_overlap_parallel_driving_braking_apart_and_smooth_crossing_do_not_alert(self):
        sequences=[
            [[obj(1,100),obj(2,115)] for _ in range(80)],
            [[obj(1,100+2*i),obj(2,115+2*i)] for i in range(80)],
            [[obj(1,100),obj(2,240-4*min(i,29),y=200)] for i in range(80)],
            [[obj(1,100),obj(2,240-4*i)] for i in range(70)],
        ]
        for sequence in sequences:
            with self.subTest(sequence=sequences.index(sequence)):
                self.assertEqual(self.replay(sequence)[0].events,[])

    def test_prefix_output_does_not_change_when_future_frames_change(self):
        prefix=[impact(i) for i in range(36)]
        a,rows_a=self.replay(prefix+[[obj(1,100),obj(2,124)] for _ in range(10)])
        b,rows_b=self.replay(prefix+[[obj(1,700),obj(2,900)] for _ in range(10)])
        self.assertEqual(rows_a[:36],rows_b[:36])
        self.assertEqual([e for e in a.events if e['frame_index']<36],[e for e in b.events if e['frame_index']<36])

    def test_short_occlusion_does_not_invent_observations_and_long_gap_resets_motion(self):
        sequence=[impact(i) if i != 32 else [obj(1,100)] for i in range(60)]
        engine,rows=self.replay(sequence)
        self.assertEqual(rows[32]['candidates'],[])
        self.assertTrue(engine.events)
        sequence=[impact(i) if not 27<=i<=40 else [obj(1,100)] for i in range(70)]
        self.assertEqual(self.replay(sequence)[0].events,[])

    def test_pair_cooldown_does_not_hide_another_pair(self):
        sequence=[impact(i)+impact(i,shift=600,ids=(3,4)) for i in range(80)]
        engine,_=self.replay(sequence)
        self.assertEqual([e['track_ids'] for e in engine.events],[[1,2],[3,4]])

    def test_scene_cut_clears_history_and_confirmation(self):
        engine=CollisionRules(CONFIG)
        for i in range(65):
            engine.update(frame(i,impact(i)),scene_cut=i==30)
        self.assertEqual(engine.events,[])
        self.assertEqual(engine.segment,1)

    def test_low_quality_track_and_id_switch_cannot_borrow_an_old_track_motion(self):
        sequence=[[dict(o,confidence=.2) for o in impact(i)] for i in range(70)]
        self.assertEqual(self.replay(sequence)[0].events,[])
        sequence=[impact(i,ids=(1,2 if i<29 else 20)) for i in range(70)]
        self.assertEqual(self.replay(sequence)[0].events,[])

    def test_rejects_frame_gap_clock_reversal_duplicate_ids_and_bad_confirmation_config(self):
        engine=CollisionRules(CONFIG)
        with self.assertRaises(ValueError):engine.update(frame(1,[]))
        engine.update(frame(0,[]))
        with self.assertRaises(ValueError):engine.update(dict(frame(1,[]),video_time_s=0))
        engine=CollisionRules(CONFIG)
        with self.assertRaises(ValueError):engine.update(frame(0,[obj(1,100),obj(1,130)]))
        config=copy.deepcopy(CONFIG);config['confirmation_hits']=config['confirmation_window_frames']+1
        with self.assertRaises(ValueError):CollisionRules(config)

    def test_small_boxes_are_abstained_and_pixel_scaling_is_consistent(self):
        original=CollisionRules(CONFIG)
        doubled=CollisionRules(CONFIG,image_width=1280,image_height=1280)
        tiny=CollisionRules(CONFIG,image_width=1280,image_height=1280)
        for i in range(65):
            objects=impact(i)
            original.update(frame(i,objects))
            scaled=[dict(o,bbox_xyxy=[v*2 for v in o['bbox_xyxy']]) for o in objects]
            doubled.update(frame(i,scaled))
            tiny.update(frame(i,objects))
        self.assertEqual(len(original.events),1)
        self.assertEqual(original.events[0]['frame_index'],doubled.events[0]['frame_index'])
        self.assertEqual(tiny.events,[])


if __name__=='__main__':
    unittest.main()
