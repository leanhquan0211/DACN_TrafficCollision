"""Kiểm lỗi chuyển nhãn có thể làm hỏng B0; chạy unittest, không cần Internet.

Fixture nhỏ kiểm pixel/chuẩn hóa, nhãn sai, file đặt nhầm thư mục và chính sách
unknown/che khuất. Đầu ra pass/fail; không thay thế audit media thật.
"""

import unittest
from unittest.mock import MagicMock, patch

from scripts.audit_sttad_public import index_tree, parse_boxes
from scripts.audit_cadp_b0_quality import classify
from scripts.inspect_public_zip import RangeZip
from scripts.audit_accident_public import BudgetDownload, check_timestamps, member_url, validate_row
from scripts.audit_accident_public import preimpact_indices
from scripts.prepare_b0_scaled_release import normal_extension_plan


class PublicLabelAuditTests(unittest.TestCase):
    def test_preimpact_selection_uses_pts_margin_not_average_fps(self):
        self.assertEqual(preimpact_indices([0,.1,.2,.9,1.0,1.1],5),[0,1])
        self.assertEqual(preimpact_indices([0,.1,.2],2),[])
        self.assertEqual(preimpact_indices([0,.5,1,1.5,2,2.5,3],6),[0,1,2])

    def test_preimpact_rejects_invalid_timestamps(self):
        for points,impact in (([0,0,1],2),([0,float('nan'),2],2),([0,1],2)):
            with self.assertRaises(ValueError):
                preimpact_indices(points,impact)

    def test_accident_vfr_uses_pts_and_does_not_shift_frame(self):
        points = [0, .04, .20, .24]
        self.assertTrue(check_timestamps(points, 2, .20)["pts_mapping_verified"])
        self.assertFalse(check_timestamps(points, 3, .20)["pts_mapping_verified"])
        self.assertFalse(check_timestamps([0, 0, 0], 1, 0)["pts_mapping_verified"])

    def test_accident_nested_member_is_one_url_parameter(self):
        self.assertIn("real_videos%2Fsource_00.mp4?datasetVersionNumber=9", member_url("real_videos/source_00.mp4"))

    def test_accident_box_is_normalized_and_keeps_one_impact_frame(self):
        row = dict(path="real_videos/source_00.mp4", x1=".1", y1=".2", x2=".5", y2=".6",
                   center_x=".3", center_y=".4", width="1280", height="720",
                   accident_frame="17", no_frames="49")
        result = validate_row(row)
        self.assertEqual(result["frame"], 17)
        self.assertEqual(result["yolo"][:3], (0, .3, .4))
        self.assertAlmostEqual(result["yolo"][3], .4)
        self.assertEqual(result["declared_frames"], 49)

    def test_accident_invalid_source_indices_are_not_silently_shifted(self):
        row = dict(path="real_videos/source_00.mp4", x1=".1", y1=".2", x2=".5", y2=".6",
                   center_x=".3", center_y=".4", width="1280", height="720",
                   accident_frame="17", no_frames="49")
        for changed in ({"accident_frame": "49"}, {"accident_frame": "17.5"},
                        {"x2": "1.2"}, {"center_x": ".8"}, {"width": "nan"},
                        {"path": "../source.mp4"}):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                validate_row(dict(row, **changed))

    def test_accident_full_download_refused_before_body_read(self):
        response = MagicMock(headers={"Content-Length": "20000000000"})
        response.__enter__.return_value = response
        with patch("scripts.audit_accident_public.urllib.request.urlopen", return_value=response):
            with self.assertRaises(ValueError):
                BudgetDownload(1024).get("https://example.invalid/one.mp4", 1024)
        response.read.assert_not_called()

    def test_pixel_xyxy_roundtrip_preserves_source_class(self):
        row = parse_boxes("11 100 50 300 150", 400, 200)[0]
        self.assertEqual(row["source_class"], 11)
        self.assertEqual(row["project_class"], 0)
        self.assertEqual((row["cx_norm"], row["cy_norm"], row["w_norm"], row["h_norm"]), (.5, .5, .5, .5))

    def test_invalid_or_missing_annotation_does_not_become_negative(self):
        for body in ("", "11 0 0 401 100", "11 nan 0 1 1", "11 300 0 100 100", "11 0 0 1"):
            with self.subTest(body=body), self.assertRaises(ValueError):
                parse_boxes(body, 400, 200)

    def test_exact_paths_and_wrong_extensions_are_not_repaired(self):
        paths = ["labels/V-T_crash/V-P_crash_3/00001.txt", "rgb-images/V-T_crash/V-T_crash_0/00001.jpg",
                 "labels/V-P_crash/V-P_crash_3/00001.jpg"]
        _, groups = index_tree({"tree": [dict(type="blob", path=p) for p in paths]})
        self.assertEqual(groups["V-T_crash/V-P_crash_3"]["labels_without_image"], 1)
        self.assertEqual(groups["V-T_crash/V-T_crash_0"]["paired"], 0)
        self.assertEqual(len(groups["V-P_crash/V-P_crash_3"]["unexpected_files"]), 1)

    def test_unknown_and_occlusion_have_explicit_exclusions(self):
        frame = dict(sequence="001407", source_frame="96", source_image="96.jpg", missing_known_track_rows="[]")
        self.assertEqual(classify(frame, None)["derived_geometry_quality"], "exclude")
        proposal = dict(any_occluded="1", overlaps_ignore_region="0", any_generated="1")
        result = classify(frame, proposal)
        self.assertIn("occluded", result["reasons"])
        self.assertFalse(result["training_eligible"])
        proposal["any_occluded"] = "0"
        self.assertEqual(classify(frame, proposal)["derived_geometry_quality"], "passes_explicit_source_flags")

    def test_remote_zip_refuses_full_response_before_reading(self):
        response = MagicMock(status=200, headers={})
        response.__enter__.return_value = response
        with patch("scripts.inspect_public_zip.urllib.request.urlopen", return_value=response):
            with self.assertRaises(ValueError):
                RangeZip("https://example.invalid/data.zip", 100)
        response.read.assert_not_called()

    def test_remote_zip_budget_blocks_next_request(self):
        response = MagicMock(status=206, headers={"Content-Range": "bytes 0-0/10"})
        response.__enter__.return_value = response
        response.read.return_value = b"a"
        with patch("scripts.inspect_public_zip.urllib.request.urlopen", return_value=response) as network:
            remote = RangeZip("https://example.invalid/data.zip", 1)
            self.assertEqual(remote.size, 10)
            with self.assertRaises(ValueError):
                remote.fetch(1, 1)
            self.assertEqual(network.call_count, 1)

    def test_remote_zip_ledger_keeps_budget_across_resume_instances(self):
        import uuid
        from pathlib import Path
        response=MagicMock(status=206,headers={'Content-Range':'bytes 0-0/10'})
        response.__enter__.return_value=response;response.read.return_value=b'a'
        parent=Path(__file__).resolve().parents[1]/'.tmp';parent.mkdir(exist_ok=True)
        folder=parent/('ledger_fixture_'+uuid.uuid4().hex);folder.mkdir()
        ledger=folder/'ledger.json'
        with patch('scripts.inspect_public_zip.urllib.request.urlopen',return_value=response) as network:
            RangeZip('https://example.invalid/data.zip',2,ledger)
            RangeZip('https://example.invalid/data.zip',2,ledger)
            with self.assertRaisesRegex(ValueError,'budget exhausted'):
                RangeZip('https://example.invalid/data.zip',2,ledger)
            self.assertEqual(network.call_count,2)


class NormalExpansionTests(unittest.TestCase):
    def inputs(self):
        rows=[];splits=[]
        for split in ('train','val','test'):
            for frame,label in enumerate(('negative','positive')):
                row=dict(source_dataset='ACCIDENT',source_sequence=split+'_event',source_frame=frame,
                    source_path=split+str(frame)+'.png',asset_kind='image',collision_label=label,
                    label_origin='author_accident_impact_region' if label=='positive' else 'derived_author_preimpact_assistant_frame_review',
                    label_evidence='review.json',accident_bbox_count=int(label=='positive'),
                    converted_label='positive.txt' if label=='positive' else '',leakage_group='group_'+split,
                    camera_id_verified=False,training_release_allowed=False,split='unassigned')
                rows.append(row);splits.append(dict(source_dataset='ACCIDENT',source_sequence=row['source_sequence'],source_frame=frame,split=split))
        manifest=dict(clips=[dict(sequence=x) for x in ('new_train','new_val','reserve')],samples=[
            dict(source_sequence=x,source_frame=0,image=x+'.png',collision_label='negative',
                 label_origin='author_normal_folder_clip_label') for x in ('new_train','new_val','reserve')])
        review=dict(groups=[dict(group_id='new_'+x,sequences=[x],assignment=s) for x,s in
                            zip(('new_train','new_val','reserve'),('train','val','reserve_negative_holdout'))])
        return rows,splits,manifest,review

    def test_normal_extension_preserves_old_test_and_seals_reserve(self):
        rows,splits,manifest,review=self.inputs()
        new,assignments,reserve=normal_extension_plan(rows,splits,manifest,review,'new_review.json')
        self.assertEqual(new[:len(rows)],rows)
        self.assertEqual(assignments[:len(splits)],splits)
        self.assertEqual(len(new),8)
        self.assertEqual([r['source_sequence'] for r in reserve],['reserve'])
        self.assertFalse(any(r['source_sequence']=='reserve' for r in new))
        self.assertEqual(sum(r['split']=='test' for r in assignments),2)

    def test_group_link_to_old_train_cannot_be_new_validation(self):
        rows,splits,manifest,review=self.inputs();review['groups'][1]['group_id']='group_train'
        with self.assertRaises(ValueError):normal_extension_plan(rows,splits,manifest,review,'review.json')

    def test_weak_negative_or_duplicate_frame_rejected(self):
        for change in ('weak','duplicate'):
            rows,splits,manifest,review=self.inputs()
            if change=='weak':manifest['samples'][0]['label_origin']='derived_author_first_visible_contact_candidate'
            else:manifest['samples'].append(dict(manifest['samples'][0]))
            with self.assertRaises(ValueError):normal_extension_plan(rows,splits,manifest,review,'review.json')

    def test_unreviewed_clip_and_new_mixed_test_assignment_rejected(self):
        rows,splits,manifest,review=self.inputs();review['groups'].pop()
        with self.assertRaises(ValueError):normal_extension_plan(rows,splits,manifest,review,'review.json')
        rows,splits,manifest,review=self.inputs();review['groups'][0]['assignment']='test'
        with self.assertRaises(ValueError):normal_extension_plan(rows,splits,manifest,review,'review.json')

    def test_same_scene_cannot_be_train_and_reserve(self):
        rows,splits,manifest,review=self.inputs();review['groups'][2]['group_id']=review['groups'][0]['group_id']
        with self.assertRaises(ValueError):normal_extension_plan(rows,splits,manifest,review,'review.json')


if __name__ == "__main__":
    unittest.main()
