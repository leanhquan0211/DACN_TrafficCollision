"""Kiểm tra các lỗi nhãn dễ gây sai tập B0, không chạy model hoặc train.

Chạy `python -B -m unittest discover -s tests -v` trong project. Đầu vào gồm
fixture thiếu nhãn/nhiều sự kiện và kết quả pilot đã sinh; đầu ra là pass/fail.
"""

import csv
import json
import unittest
from copy import deepcopy
from pathlib import Path

from scripts.prepare_b0_candidates import build_candidates, normalize
from scripts.maintenance.apply_cadp_frame_review import apply_review
from scripts.prepare_cadp_pilot import read_vatic
from scripts.maintenance.update_manifest_reviews import read_manifest


RULE = json.loads(Path("configs/b0_region_proposal.json").read_text(encoding="utf-8"))


def source_row(gt_id, box, frame=0, outside=0):
    return dict(track_id=gt_id, bbox=box, frame=frame, outside=outside,
                occluded=0, generated=0, label="Car", attributes=["Colliding"])


class LabelSafetyTests(unittest.TestCase):
    def test_missing_or_outside_never_becomes_negative(self):
        images = {0: Path("0.jpg"), 1: Path("1.jpg")}
        event = dict(event_id="event", participant_gt_ids=[0, 1], start_frame=0, end_frame_inclusive=1)
        for rows in ([source_row(0, [1, 1, 10, 10])],
                     [source_row(0, [1, 1, 10, 10]), source_row(1, [5, 5, 15, 15], outside=1)]):
            candidates, frames = build_candidates(rows, images, [event], "000001", 100, 100, RULE)
            self.assertEqual(candidates, [])
            self.assertTrue(all(f["frame_label_status"]=="unknown_not_certified_negative" for f in frames))
            self.assertTrue(all(not f["empty_negative_exported"] for f in frames))

    def test_two_events_do_not_merge_all_colliding_vehicles(self):
        rows = [source_row(i, box) for i, box in enumerate(([1, 1, 10, 10], [5, 5, 20, 20],
                                                          [60, 60, 70, 70], [65, 65, 90, 90]))]
        events = [dict(event_id=f"event{i}",participant_gt_ids=ids,start_frame=0,end_frame_inclusive=0)
                  for i, ids in enumerate(([0, 1], [2, 3]))]
        candidates, _ = build_candidates(rows, {0: Path("0.jpg")}, events, "000001", 100, 100, RULE)
        self.assertEqual(len(candidates), 2)
        self.assertEqual([(c["xmin"],c["ymin"],c["xmax"],c["ymax"]) for c in candidates],
                         [(1, 1, 20, 20), (60, 60, 90, 90)])
        self.assertTrue(all(not c["training_eligible"] for c in candidates))

    def test_bounds_are_rejected_instead_of_silently_clipped(self):
        with self.assertRaises(ValueError):
            normalize([source_row(0, [-1, 1, 20, 20])], {0: Path("0.jpg")}, 100, 100, "000001")

    @unittest.skipUnless(Path("data_raw/cadp/pilot_1407/1407.txt").is_file(),
                         "Integration test needs the original CADP TXT; see docs/GETTING_STARTED.md")
    def test_confirmed_interval_cannot_drift(self):
        _, rows = read_manifest(Path("data/manifest.csv"))
        path = Path("data/reviews/2026-10-19-cadp-001407-frame-confirmation.json")
        review = json.loads(path.read_text(encoding="utf-8"))
        before = deepcopy(rows)
        apply_review(rows, review, path)
        self.assertEqual(before, rows)  # chạy lại đúng phiếu không đổi nhãn/ghi chú
        bad = deepcopy(review)
        bad["events"][0]["start_frame"] = 95
        with self.assertRaises(ValueError):
            apply_review(deepcopy(rows), bad, path)
        self.assertTrue(all(not r["onset_s"] and not r["end_s"] for r in rows if r["source_dataset"]=="CADP"))


@unittest.skipUnless(Path("data/processed/b0_proposals/001407/report.json").is_file()
                     and Path("data_raw/cadp/pilot_1407/1407.txt").is_file(),
                     "Integration test needs the restored CADP pilot/proposals; see docs/GETTING_STARTED.md")
class ActualPilotOutputTests(unittest.TestCase):
    def test_proposals_roundtrip_and_keep_provenance(self):
        folder = Path("data/processed/b0_proposals/001407")
        with (folder/"region_proposals.csv").open(encoding="utf-8",newline="") as stream:
            proposals = list(csv.DictReader(stream))
        self.assertEqual(len(proposals), 35)
        self.assertEqual({int(r["source_frame"]) for r in proposals}, set(range(96, 131)))
        files = list((folder/"labels_proposed").glob("*.txt"))
        self.assertEqual(len(files), 35)
        source = read_vatic(Path("data_raw/cadp/pilot_1407/1407.txt"))
        for item in proposals:
            frame = int(item["source_frame"])
            self.assertTrue(Path(item["source_image"]).is_file())
            self.assertEqual(item["training_eligible"], "False")
            tokens = (folder/"labels_proposed"/f"001407_{frame:06d}.txt").read_text().split()
            self.assertEqual(tokens[0], "0")
            cx,cy,w,h = map(float,tokens[1:])
            restored = [(cx-w/2)*1280, (cy-h/2)*720, (cx+w/2)*1280, (cy+h/2)*720]
            for actual,key in zip(restored,("xmin","ymin","xmax","ymax")):
                self.assertAlmostEqual(actual,float(item[key]),delta=.00002)
            for row in source:
                if row["frame"]==frame and row["track_id"] in (0,2):
                    x1,y1,x2,y2=row["bbox"]
                    self.assertTrue(float(item["xmin"])<=x1<x2<=float(item["xmax"]))
                    self.assertTrue(float(item["ymin"])<=y1<y2<=float(item["ymax"]))
        with (folder/"frames.csv").open(encoding="utf-8",newline="") as stream:
            frames = list(csv.DictReader(stream))
        self.assertEqual(len(frames), 221)
        self.assertEqual(sum(r["frame_label_status"]=="unknown_not_certified_negative" for r in frames), 186)
        self.assertTrue(all(r["empty_negative_exported"]=="False" for r in frames))
        self.assertFalse((folder/"dataset.yaml").exists())


if __name__ == "__main__":
    unittest.main()
