import copy
import json
from pathlib import Path
import unittest

from src.vehicle_labels import VehicleLabels

CONFIG = json.loads((Path(__file__).resolve().parents[1]/'configs/vehicle_inference.json').read_text())


def vehicle(name='car', confidence=.8, ident=1):
    return dict(track_id=ident, class_name=name, class_id=7 if name=='truck' else 2,
                confidence=confidence, bbox_xyxy=[10,10,80,80])


class VehicleLabelTests(unittest.TestCase):
    def test_weak_new_truck_is_uncertain_and_raw_prediction_is_preserved(self):
        engine = VehicleLabels(CONFIG)
        raw = vehicle('truck',.23)
        saved = copy.deepcopy(raw)
        item = engine.update(0,[raw])[0]
        self.assertEqual(raw,saved)
        self.assertEqual(item['class_name'],'truck')
        self.assertEqual(item['confidence'],.23)
        self.assertIsNone(item['display_class']['name'])
        self.assertEqual(item['display_class']['status'],'uncertain')

    def test_history_resists_one_weak_class_flip_without_renaming_real_trucks(self):
        for name, flipped in [('car','truck'),('truck','car')]:
            engine = VehicleLabels(CONFIG)
            for i in range(4): engine.update(i,[vehicle(name)])
            item = engine.update(4,[vehicle(flipped,.23)])[0]
            self.assertEqual(item['display_class']['name'],name)
            self.assertEqual(item['class_name'],flipped)

    def test_conflicting_strong_evidence_abstains_instead_of_forcing_a_class(self):
        engine = VehicleLabels(CONFIG)
        for i,name in enumerate(['car','truck','car','truck']):
            item = engine.update(i,[vehicle(name)])[0]
        self.assertIsNone(item['display_class']['name'])

    def test_no_identity_or_history_leaks_between_ids_cuts_gaps_or_runs(self):
        for reset in ('id','cut','gap','scale'):
            engine = VehicleLabels(CONFIG)
            for i in range(4): engine.update(i,[vehicle()])
            raw=vehicle('truck',.23,ident=2 if reset=='id' else 1)
            index=4
            if reset=='gap':
                for index in range(4,8):engine.update(index,[])
                index=8
            if reset=='scale':raw['bbox_xyxy']=[0,0,300,300]
            item=engine.update(index,[raw],scene_cut=reset=='cut')[0]
            self.assertIsNone(item['display_class']['name'],reset)
        self.assertIsNone(VehicleLabels(CONFIG).update(0,[vehicle('truck',.23)])[0]['display_class']['name'])

    def test_window_is_bounded_and_new_evidence_can_replace_old_class(self):
        engine=VehicleLabels(CONFIG)
        for i in range(30):item=engine.update(i,[vehicle('car' if i<15 else 'truck')])[0]
        self.assertEqual(item['display_class']['name'],'truck')
        self.assertLessEqual(item['display_class']['support_observations'],CONFIG['history_frames'])

    def test_untracked_detections_do_not_accumulate_a_fake_history(self):
        engine=VehicleLabels(CONFIG)
        for i in range(10):item=engine.update(i,[vehicle(ident=None)])[0]
        self.assertEqual(item['display_class']['status'],'tentative')
        self.assertEqual(item['display_class']['support_observations'],1)
        self.assertEqual(engine.tracks,{})


if __name__=='__main__':unittest.main()
