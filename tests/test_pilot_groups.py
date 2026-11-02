"""Kiểm ràng buộc chia nhóm và tham chiếu frame, không chạy model hay Internet.

Fixture kiểm số frame, file giả ảnh, video đọc thiếu và nhóm xung đột. Một
test tích hợp kiểm pool thật nếu đã phục hồi dữ liệu; skip nếu máy chỉ có Git.
"""

import csv
import json
import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import cv2
import numpy as np

from scripts.audit_pilot_groups import images, audit_exported_split
from scripts.prepare_b0_pilot_index import leakage_group
from scripts.prepare_b0_pilot_index import accident_entries
from scripts.prepare_b0_pilot_index import validate_yolo
from scripts.prepare_b0_pilot_index import preimpact_entries
from scripts.prepare_b0_pilot_index import export_plan, export_dataset
from scripts.train_b0 import match_boxes, validate_resume_inputs, organize_train_previews, evaluation_splits, training_arguments, initial_weights_digest, apply_resume_patience, recorded_resume_patience
from scripts.evaluate_b0_clean import normal_summary
from src.data_preparation import sha256_file, validate_b0_verified_origins


class ExportTests(unittest.TestCase):
    """Fixture riêng kiểm ảnh/âm/video và gate; không mở gate dữ liệu project."""
    def setUp(self):
        self.parent=Path(__file__).resolve().parents[1]/".tmp"
        self.root=self.parent/("export_fixture_"+uuid.uuid4().hex)
        self.root.mkdir(parents=True)
        (self.root/"data").mkdir();(self.root/"configs").mkdir()
        self.rows=[];self.splits=[]
        (self.root/"evidence.json").write_text("{}",encoding="utf-8")
        (self.root/"box.txt").write_text("0 0.5 0.5 0.25 0.25\n",encoding="utf-8")
        for i in range(6):
            image=np.full((32,32,3),i*30,np.uint8)
            ok,body=cv2.imencode(".png",image);self.assertTrue(ok)
            (self.root/f"{i}.png").write_bytes(body.tobytes())
            row=dict(source_dataset="fixture",source_sequence=str(i//2),source_frame=str(i),
                     source_path=f"{i}.png",asset_kind="image",collision_label="positive" if i%2==0 else "negative",
                     label_origin="fixture_review",label_evidence="evidence.json",accident_bbox_count=1 if i%2==0 else 0,
                     converted_label="box.txt" if i%2==0 else "",leakage_group=f"scene{i//2}",
                     camera_id_verified=False,split="unassigned",training_release_allowed=False)
            self.rows.append(row)
            self.splits.append({k:row[k] for k in ("source_dataset","source_sequence","source_frame")}|{"split":("train","val","test")[i//2]})
        # Một âm là tham chiếu frame 1 của video thật để kiểm vòng decode.
        writer=cv2.VideoWriter(str(self.root/"fixture.avi"),cv2.VideoWriter_fourcc(*"MJPG"),5,(32,32))
        self.assertTrue(writer.isOpened())
        writer.write(np.zeros((32,32,3),np.uint8));writer.write(np.full((32,32,3),120,np.uint8));writer.release()
        self.rows[1].update(source_path="fixture.avi",asset_kind="video_frame_reference")
        for name,rows in (("pool.csv",self.rows),("split.csv",self.splits)):
            with (self.root/name).open('w',encoding='utf-8',newline='') as f:
                w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        policy=self.root/"configs/b0_public_label_policy.json";policy.write_text('{"training_release_allowed":true}')
        paths={r[k] for r in self.rows for k in ("source_path","converted_label","label_evidence") if r[k]}
        self.ready=dict(can_train=True,split_created=True,export_pool_sha256=sha256_file(self.root/"pool.csv"),
                        export_split_sha256=sha256_file(self.root/"split.csv"),export_policy_sha256=sha256_file(policy),
                        export_asset_sha256={p:sha256_file(self.root/p) for p in paths})
        self.write_ready()

    def write_ready(self):
        (self.root/"data/b0_readiness.json").write_text(json.dumps(self.ready),encoding='utf-8')

    def tearDown(self):
        self.assertTrue(self.root.resolve().is_relative_to(self.parent.resolve()))
        shutil.rmtree(self.root)

    def run_export(self):
        with patch("scripts.prepare_b0_pilot_index.ROOT",self.root):
            export_dataset(self.root/"pool.csv",self.root/"split.csv",self.root/"export")

    def test_export_images_video_and_true_negative_empty_labels(self):
        self.run_export()
        self.assertTrue((self.root/"export/dataset.yaml").is_file())
        report=json.loads((self.root/"export/report.json").read_text(encoding='utf-8'))
        self.assertEqual(report['provenance_sha256'],sha256_file(self.root/'export/provenance.csv'))
        self.assertEqual(report['dataset_yaml_sha256'],sha256_file(self.root/'export/dataset.yaml'))
        with (self.root/"export/provenance.csv").open(encoding='utf-8',newline='') as f:rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),6)
        for row in rows:
            label=(self.root/"export"/row['export_label']).read_text()
            self.assertEqual(bool(label.strip()),row['collision_label']=='positive')
            if row['asset_kind']=='video_frame_reference':
                image=cv2.imdecode(np.frombuffer((self.root/"export"/row['export_image']).read_bytes(),np.uint8),1)
                self.assertAlmostEqual(float(image.mean()),120,delta=2)

    def test_exported_similarity_suggests_cross_split_pair(self):
        self.run_export()
        with patch('scripts.audit_pilot_groups.ROOT',self.root):
            report_dir=audit_exported_split(self.root/'export')
        report=json.loads((report_dir/'report.json').read_text(encoding='utf-8'))
        self.assertEqual(report['images'],6)
        self.assertTrue(report['candidates'])
        self.assertTrue(all(r['first_split']!=r['second_split'] for r in report['candidates']))

    def test_closed_gate_writes_nothing(self):
        self.ready['can_train']=False;self.write_ready()
        with self.assertRaisesRegex(ValueError,'blocked'):self.run_export()
        self.assertFalse((self.root/"export").exists())

    def test_pilot_gate_does_not_open_benchmark(self):
        # Pilot được phát hành riêng; benchmark vẫn bị khóa trên cùng tập nguồn.
        self.ready['can_train']=False
        self.ready['pilot_release']={k:v for k,v in self.ready.items() if k!='pilot_release'}
        self.ready['pilot_release']['can_train']=True
        self.write_ready()
        (self.root/'configs/b0_public_label_policy.json').write_text(
            '{"training_release_allowed":false,"pilot_training_release_allowed":true}')
        self.ready['pilot_release']['export_policy_sha256']=sha256_file(
            self.root/'configs/b0_public_label_policy.json')
        self.write_ready()
        with patch('scripts.prepare_b0_pilot_index.ROOT',self.root):
            with self.assertRaisesRegex(ValueError,'blocked'):
                export_dataset(self.root/'pool.csv',self.root/'split.csv',self.root/'benchmark')
            export_dataset(self.root/'pool.csv',self.root/'split.csv',self.root/'pilot','pilot')
        self.assertFalse((self.root/'benchmark').exists())
        self.assertEqual(json.loads((self.root/'pilot/report.json').read_text())['release_kind'],'pilot')

    def test_changed_media_rejected_before_writing(self):
        (self.root/"0.png").write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'asset differs'):self.run_export()
        self.assertFalse((self.root/"export").exists())

    def test_decode_failure_never_publishes_dataset_yaml(self):
        (self.root/"0.png").write_bytes(b'not an image')
        self.ready['export_asset_sha256']['0.png']=sha256_file(self.root/"0.png")
        self.write_ready()
        with self.assertRaisesRegex(ValueError,'decode'):self.run_export()
        self.assertTrue((self.root/"export/failure.json").exists())
        self.assertFalse((self.root/"export/dataset.yaml").exists())

    def test_group_leakage_and_missing_class_rejected(self):
        changed=[dict(r) for r in self.splits];changed[1]['split']='test'
        with self.assertRaisesRegex(ValueError,'crosses splits'):export_plan(self.rows,changed)
        with self.assertRaisesRegex(ValueError,'both labeled'):export_plan(self.rows,self.splits[:-1])

    def test_resume_checks_config_and_original_dataset(self):
        import yaml
        run=self.root/'run';(run/'weights').mkdir(parents=True)
        dataset=self.root/'dataset.yaml';dataset.write_text('names: {}',encoding='utf-8')
        config={'epochs':60,'batch':8,'device':'0','optimizer':'SGD','mosaic':.5,'scale':.3}
        config_path=self.root/'run_config.json';config_path.write_text(json.dumps(config),encoding='utf-8')
        shutil.copy2(config_path,run/'requested_config.json')
        (run/'args.yaml').write_text(yaml.safe_dump(dict(config,data=str(dataset))),encoding='utf-8')
        (run/'weights/last.pt').write_bytes(b'fixture')
        self.assertEqual(validate_resume_inputs(config,config_path,dataset,run),run/'weights/last.pt')
        (run/'args.yaml').write_text(yaml.safe_dump(dict(config,data=str(dataset),mosaic=1.0)),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'argument differs: mosaic'):
            validate_resume_inputs(config,config_path,dataset,run)
        (run/'args.yaml').write_text(yaml.safe_dump(dict(config,data=str(dataset))),encoding='utf-8')
        process=MagicMock()
        process.info={'pid':123456789,'cmdline':['python','scripts/train_b0.py','--config',str(config_path),'--train']}
        with patch('psutil.process_iter',return_value=[process]):
            with self.assertRaisesRegex(ValueError,'already running'):
                validate_resume_inputs(config,config_path,dataset,run)
        config_path.write_text(json.dumps(dict(config,batch=16)),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'config differs'):
            validate_resume_inputs(config,config_path,dataset,run)

    def test_recipe_forwards_augmentation_without_research_metadata(self):
        values=training_arguments({'imgsz':960,'mosaic':.5,'scale':.3,'close_mosaic':10,
                                   'nbs':64,'method_sources':['paper'],'target':{'map50':.7}})
        self.assertEqual(values,{'imgsz':960,'mosaic':.5,'scale':.3,'close_mosaic':10,'nbs':64})

    def test_resume_patience_overrides_restored_infinity_without_resetting_best(self):
        from types import SimpleNamespace
        run=self.root/'resume';(run/'weights').mkdir(parents=True)
        (run/'weights/last.pt').write_bytes(b'checkpoint_fixture')
        cfg=self.root/'config.json';cfg.write_text('{"patience":0}')
        stopper=SimpleNamespace(patience=float('inf'),best_epoch=7,best_fitness=.5,possible_stop=False)
        trainer=SimpleNamespace(save_dir=run,stopper=stopper,start_epoch=9,args=SimpleNamespace(patience=0))
        apply_resume_patience(trainer,15,cfg)
        self.assertEqual((stopper.patience,stopper.best_epoch,stopper.best_fitness),(15,7,.5))
        self.assertEqual(trainer.args.patience,15)
        self.assertEqual(recorded_resume_patience(run,cfg),15)
        apply_resume_patience(trainer,10,cfg)
        record=json.loads((run/'resume_events.json').read_text(encoding='utf-8'))
        self.assertEqual([e['patience'] for e in record['events']],[15,10])
        self.assertFalse(record['events'][-1]['optimizer_reset'])
        self.assertEqual((run/'weights/last.pt').read_bytes(),b'checkpoint_fixture')
        cfg.write_text('{"patience":1}')
        with self.assertRaisesRegex(ValueError,'history differs'):
            recorded_resume_patience(run,cfg)

    def test_resume_accepts_only_recorded_patience_change_in_saved_args(self):
        from types import SimpleNamespace
        import yaml
        run=self.root/'resume';(run/'weights').mkdir(parents=True)
        dataset=self.root/'data.yaml';dataset.write_text('names: {}')
        config={'patience':0,'epochs':100,'batch':2}
        cfg=self.root/'config.json';cfg.write_text(json.dumps(config))
        shutil.copy2(cfg,run/'requested_config.json')
        (run/'weights/last.pt').write_bytes(b'checkpoint_fixture')
        saved=dict(config,data=str(dataset));saved['patience']=15
        (run/'args.yaml').write_text(yaml.safe_dump(saved))
        with self.assertRaisesRegex(ValueError,'argument differs: patience'):
            validate_resume_inputs(config,cfg,dataset,run)
        trainer=SimpleNamespace(save_dir=run,stopper=SimpleNamespace(patience=float('inf'),best_epoch=7,best_fitness=.5),
                                start_epoch=9,args=SimpleNamespace(patience=0))
        apply_resume_patience(trainer,15,cfg)
        self.assertEqual(validate_resume_inputs(config,cfg,dataset,run),run/'weights/last.pt')
        saved['batch']=4;(run/'args.yaml').write_text(yaml.safe_dump(saved))
        with self.assertRaisesRegex(ValueError,'argument differs: batch'):
            validate_resume_inputs(config,cfg,dataset,run)

    def test_model_ablation_preserves_legacy_pretrained_digest(self):
        release={'initial_weights_sha256':'original_n_digest'}
        self.assertEqual(initial_weights_digest({},release),'original_n_digest')
        self.assertEqual(initial_weights_digest({'initial_weights_sha256':'new_s_digest'},release),'new_s_digest')
        self.assertEqual(release['initial_weights_sha256'],'original_n_digest')

    def test_normal_probe_counts_frames_boxes_and_clips_separately(self):
        cases=self.root/'normal_cases';cases.mkdir()
        rows=[{'source_sequence':'a','prediction_count':'2','fp':'2'},
              {'source_sequence':'a','prediction_count':'0','fp':'0'},
              {'source_sequence':'b','prediction_count':'1','fp':'1'}]
        with (cases/'cases.csv').open('w',encoding='utf-8',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
        metrics={'negative_frames':3,'negative_frames_with_predictions':2,
                 'negative_frame_false_positive_rate':2/3,'fp':3}
        result=normal_summary(metrics,cases)
        self.assertEqual((result['frames'],result['frames_with_predictions'],result['false_boxes']), (3,2,3))
        self.assertEqual((result['clips'],result['clips_with_any_predictions']), (2,2))

    def test_train_preview_organization_preserves_other_files_and_refuses_overwrite(self):
        run=self.root/'run';run.mkdir()
        (run/'train_batch0.jpg').write_bytes(b'preview')
        (run/'results.csv').write_text('epoch\n1\n',encoding='utf-8')
        (run/'val_batch0_pred.jpg').write_bytes(b'val')
        (run/'BoxPR_curve.png').write_bytes(b'curve')
        (run/'results.png').write_bytes(b'plot')
        organize_train_previews(run)
        self.assertEqual((run/'train_batches/train_batch0.jpg').read_bytes(),b'preview')
        self.assertEqual((run/'validation_during_training/batches/val_batch0_pred.jpg').read_bytes(),b'val')
        self.assertEqual((run/'validation_during_training/curves/BoxPR_curve.png').read_bytes(),b'curve')
        self.assertEqual((run/'training_summary/results.png').read_bytes(),b'plot')
        self.assertTrue((run/'results.csv').exists())
        (run/'train_batch0.jpg').write_bytes(b'other')
        with self.assertRaises(FileExistsError):organize_train_previews(run)

    def test_experiment_can_lock_validation_only(self):
        self.assertEqual(evaluation_splits({'evaluation_splits':['val']}),('val',))
        self.assertEqual(evaluation_splits({}),('val','test'))
        for bad in ([],['test'],['val','test','test']):
            with self.subTest(bad=bad),self.assertRaises(ValueError):evaluation_splits({'evaluation_splits':bad})


class PoolLabelTests(unittest.TestCase):
    def test_verified_pilot_rejects_unknown_or_unreviewed_negative(self):
        validate_b0_verified_origins([{'collision_label':'negative','label_origin':'user_full_sequence_review'},
                                      {'collision_label':'positive','label_origin':'author_accident_impact_region'}])
        for label, origin in [('negative','derived_author_first_visible_contact_candidate'),
                              ('unknown','author_normal_folder_clip_label'),
                              ('negative','missing_annotation')]:
            with self.subTest(label=label,origin=origin), self.assertRaises(ValueError):
                validate_b0_verified_origins([{'collision_label':label,'label_origin':origin}])

    def test_valid_accident_box(self):
        validate_yolo("0 0.5 0.5 1 1\n", 1)

    def test_bad_geometry_and_missing_positive_labels_are_rejected(self):
        for text in ("", "0 nan 0.5 0.2 0.2", "0 0.1 0.5 0.4 0.2",
                     "0 0.5 0.5 0 0.2", "1 0.5 0.5 0.2 0.2"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                validate_yolo(text, 1)


class PilotMetricTests(unittest.TestCase):
    def test_one_ground_truth_cannot_match_two_predictions(self):
        gt=[[0,0,10,10]]
        predictions=[{'xyxy':[0,0,10,10],'confidence':.9},
                     {'xyxy':[0,0,10,10],'confidence':.7}]
        result=match_boxes(gt,predictions,.5)
        self.assertEqual((result['tp'],result['fp'],result['fn']),(1,1,0))

    def test_missing_box_and_prediction_on_negative(self):
        self.assertEqual((match_boxes([[0,0,10,10]],[],.5)['fn'],
                          match_boxes([], [{'xyxy':[0,0,10,10],'confidence':.8}],.5)['fp']),
                         (1,1))


class GroupAuditTests(unittest.TestCase):
    def test_shared_scene_stays_together_without_relabeling_other_sources(self):
        review = {"leakage_groups": [{"id": "road", "members": ["D:A", "D:B", "D:C"]}]}
        self.assertEqual(leakage_group("D:A", review), leakage_group("D:C", review))
        self.assertNotEqual(leakage_group("S:other", review), "road")

    def test_conflicting_group_evidence_is_rejected(self):
        review = {"leakage_groups": [{"id": "a", "members": ["D:A"]}, {"id": "b", "members": ["D:A"]}]}
        with self.assertRaises(ValueError):
            leakage_group("D:A", review)

    def test_numeric_frame_order_and_non_image_is_not_silently_decoded(self):
        fixture_root = Path(__file__).resolve().parents[1]/".tmp"
        fixture_root.mkdir(exist_ok=True)
        # TemporaryDirectory dùng mode 0700 gây ACL lỗi trên sandbox Windows;
        # dùng thư mục workspace thường, chỉ dọn đúng bốn file fixture đã tạo.
        folder = fixture_root/("group_fixture_"+uuid.uuid4().hex)
        folder.mkdir()
        try:
            ok, body = cv2.imencode(".jpg", np.zeros((16, 16, 3), np.uint8))
            self.assertTrue(ok)
            for n in (10, 2, 0):
                (folder/f"{n}.jpg").write_bytes(body.tobytes())
            (folder/"1.jpg").write_bytes(b"not image")
            # Hàm đọc nguồn tính đường dẫn tương đối trong project.
            with patch("scripts.audit_pilot_groups.ROOT", folder):
                rows = list(images({"path": "."}))
            self.assertEqual([r[1] for r in rows], [0, 1, 2, 10])
            self.assertIsNone(rows[1][2])
        finally:
            self.assertTrue(folder.resolve().is_relative_to(fixture_root.resolve()))
            for name in ("0.jpg", "1.jpg", "2.jpg", "10.jpg"):
                (folder/name).unlink(missing_ok=True)
            folder.rmdir()

    def test_truncated_video_is_not_reported_as_complete(self):
        cap = MagicMock()
        cap.isOpened.return_value = True
        cap.get.return_value = 2
        cap.read.side_effect = [(True, np.zeros((16,16,3), np.uint8)), (False, None)]
        with patch("scripts.audit_pilot_groups.cv2.VideoCapture", return_value=cap):
            with self.assertRaises(ValueError):
                list(images({"path": "fixture.mp4"}))
        cap.release.assert_called_once()


@unittest.skipUnless(Path("data/processed/b0_public_pilot_v1/index.csv").exists(),
                     "Integration test needs locally prepared pilot index")
class ActualPoolTests(unittest.TestCase):
    def test_provenance_grouping_and_unknown_exclusion(self):
        with Path("data/processed/b0_public_pilot_v1/index.csv").open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 2376)
        self.assertEqual(sum(r["collision_label"] == "positive" for r in rows), 31)
        self.assertEqual({r["split"] for r in rows}, {"unassigned"})
        detrac = [r for r in rows if r["source_dataset"] == "UA-DETRAC"]
        self.assertEqual(len({r["leakage_group"] for r in detrac}), 1)
        self.assertFalse(any(r["source_dataset"] == "CADP" for r in rows))
        tad = [r for r in rows if r["source_dataset"] == "TAD"]
        self.assertEqual(len(tad), 308)
        self.assertTrue(all(r["asset_kind"] == "video_frame_reference" for r in tad))
        self.assertTrue(all(r["label_origin"] == "author_normal_folder_clip_label" for r in tad))


@unittest.skipUnless(Path("outputs/audits/accident_public/verification.json").exists(),
                     "Integration test needs locally audited ACCIDENT sample")
class ActualAccidentPoolTests(unittest.TestCase):
    def test_only_reviewed_impact_regions_join_pool(self):
        rows = accident_entries(Path("outputs/audits/accident_public/report.json"),
                                Path("data/reviews/2026-10-25-accident-source-review.json"))
        self.assertEqual(len(rows), 4)
        self.assertFalse({r["source_sequence"] for r in rows} & {"2QZf8MiIRK0_00", "-FQxK6HdxNU_00"})
        self.assertTrue(all(r["collision_label"] == "positive" and r["split"] == "unassigned" for r in rows))
        self.assertTrue(all(not r["training_release_allowed"] for r in rows))
        self.assertEqual(len({r["leakage_group"] for r in rows}), 4)


@unittest.skipUnless(Path("data/processed/b0_public_pilot_v3/index.csv").exists(),
                     "Needs locally prepared expansion")
class ExpansionTests(unittest.TestCase):
    def test_reviewed_frames_keep_scope_and_group(self):
        rows = preimpact_entries(Path("data/reviews/2026-10-26-preimpact-frame-review.json"))
        self.assertEqual(len(rows),30)
        self.assertTrue(all(r["collision_label"]=="negative" and not r["converted_label"] for r in rows))
        with Path("data/processed/b0_public_pilot_v3/index.csv").open(encoding="utf-8",newline="") as f:
            pool = list(csv.DictReader(f))
        self.assertEqual(len(pool),2423)
        for row in rows:
            positive = [r for r in pool if r["source_dataset"]=="ACCIDENT" and
                        r["source_sequence"]==row["source_sequence"] and r["collision_label"]=="positive"]
            self.assertEqual(len(positive),1)
            self.assertEqual(positive[0]["leakage_group"],row["leakage_group"])
            self.assertLess(row["source_frame"],int(positive[0]["source_frame"]))

    def test_changed_candidate_evidence_is_rejected(self):
        with patch("scripts.prepare_b0_pilot_index.sha256_file",return_value="changed"):
            with self.assertRaisesRegex(ValueError,"report changed"):
                preimpact_entries(Path("data/reviews/2026-10-26-preimpact-frame-review.json"))


if __name__ == "__main__":
    unittest.main()
