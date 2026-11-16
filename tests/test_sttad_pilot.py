import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.sttad_pilot import blob_id,fetch_blob,parse_pixel_boxes,parse_tree,validate_registry


class LabelTests(unittest.TestCase):
    def test_published_pixel_xyxy_converts_without_vehicle_box_or_fps_assumptions(self):
        boxes=parse_pixel_boxes(b"11 20 10 80 50\n",100,80,11)
        self.assertEqual(boxes[0]["bbox_xyxy"],[20,10,80,50])
        self.assertEqual(boxes[0]["bbox_cxcywh_norm"],[.5,.375,.6,.5])
        self.assertEqual(boxes[0]["source_class_id"],11)

    def test_corrupt_or_unsupported_labels_are_not_silently_fixed(self):
        cases=[(b"\xff\xd8\xffjpeg","JPEG"),(b"", "Empty"),(b"11 1 2 3", "Expected"),
               (b"11 nan 1 20 30","Non-finite"),(b"6 1 2 20 30","Class/category"),
               (b"11 20 5 200 20","outside"),(b"11 .5 .5 .2 .2","outside")]
        for body,message in cases:
            with self.subTest(body=body):
                with self.assertRaisesRegex(ValueError,message):parse_pixel_boxes(body,100,80,11)

    def test_source_tree_rejects_paths_that_escape_or_use_symlink_modes(self):
        self.assertEqual(parse_tree("100644 blob "+"a"*40+"\tREADME.md"),{"README.md":"a"*40})
        for value in ("100644 blob "+"a"*40+"\t../outside", "120000 blob "+"a"*40+"\tlink"):
            with self.assertRaises(ValueError):parse_tree(value)


class VerifiedSourceTests(unittest.TestCase):
    def test_verified_download_then_offline_reuse_and_mismatch_preservation(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/"file.txt";body=b"11 1 2 3 4\n";expected=blob_id(body)
            with patch("src.sttad_pilot.urlopen",return_value=io.BytesIO(body)):
                self.assertEqual(fetch_blob("a"*40,"labels/V-V_crash/V-V_crash_0/00001.txt",target,expected),"downloaded_verified")
            with patch("src.sttad_pilot.urlopen",side_effect=AssertionError("network must not be used")):
                self.assertEqual(fetch_blob("a"*40,"labels/V-V_crash/V-V_crash_0/00001.txt",target,expected),"reused_verified")
            target.write_bytes(b"existing different data")
            with self.assertRaisesRegex(ValueError,"preserved"):
                fetch_blob("a"*40,"labels/V-V_crash/V-V_crash_0/00001.txt",target,expected)
            self.assertEqual(target.read_bytes(),b"existing different data")

    def test_wrong_or_oversized_download_never_publishes_a_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/"file.txt"
            for data,limit in ((b"<html>quota</html>",100),(b"too long",3)):
                with patch("src.sttad_pilot.urlopen",return_value=io.BytesIO(data)):
                    with self.assertRaises(ValueError):
                        fetch_blob("a"*40,"README.md",target,blob_id(b"expected"),max_bytes=limit)
                self.assertFalse(target.exists())
                self.assertEqual(list(Path(tmp).iterdir()),[])

    def test_registry_cannot_expand_selection_or_duplicate_downloads(self):
        registry=dict(repository="https://github.com/ZTR02/STTAD",commit="a"*40,
            sequences=[dict(key="V-V_crash/V-V_crash_0")],
            files=[dict(path="rgb-images/V-V_crash/V-V_crash_0/00001.jpg",git_blob_sha1="b"*40),
                   dict(path="labels/V-V_crash/V-V_crash_0/00001.txt",git_blob_sha1="c"*40)])
        validate_registry(registry)
        registry["files"].append(dict(path="labels/V-P_crash/V-P_crash_0/00001.txt",git_blob_sha1="c"*40))
        with self.assertRaisesRegex(ValueError,"unselected"):validate_registry(registry)
        registry["files"]=[registry["files"][0]]*2
        with self.assertRaisesRegex(ValueError,"Duplicate"):validate_registry(registry)


class PreparationTests(unittest.TestCase):
    def test_import_keeps_unlabelled_frames_unknown_and_excludes_text_disguised_as_jpg(self):
        import cv2
        import numpy as np
        from scripts import prepare_sttad_pilot
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);raw=root/"data_raw/sttad/author_samples";key="T-T_crash/T-T_crash_1"
            files={"README.md":b"source", "trainlist.txt":b"labels/T-T_crash/T-T_crash_1/00002.txt\n", "testlist.txt":b""}
            for i in range(1,4):
                ok,encoded=cv2.imencode(".jpg",np.full((24,32,3),i*50,dtype=np.uint8));self.assertTrue(ok)
                files[f"rgb-images/{key}/{i:05}.jpg"]=encoded.tobytes()
            files[f"rgb-images/{key}/00004.jpg"]=b"0,002-003\n"
            for i in (2,3):files[f"labels/{key}/{i:05}.txt"]=b"6 2 2 24 20\n"
            for name,body in files.items():
                path=raw/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(body)
            registry=dict(repository="https://github.com/ZTR02/STTAD",commit="a"*40,
                sequences=[dict(key=key,source_class_id=6)],files=[dict(path=k,git_blob_sha1=blob_id(v)) for k,v in files.items()])
            registry_path=root/"data/registries/sttad_selected_sources.json";registry_path.parent.mkdir(parents=True);registry_path.write_text(json.dumps(registry))
            with patch.object(prepare_sttad_pilot,"ROOT",root),patch("sys.stdout",new=io.StringIO()):prepare_sttad_pilot.main()
            reports=list((root/"outputs/audits").rglob("report.json"));self.assertEqual(len(reports),1)
            result=json.loads(reports[0].read_text())
            self.assertEqual((result["total_frames"],result["labelled_frames"],result["unknown_frames"]),(3,2,1))
            self.assertEqual(len(result["excluded_source_files"]),1)
            self.assertFalse(result["training_eligible"])
            self.assertFalse(result["project_split_created"])
            self.assertFalse(result["source_seconds_verified"])
            self.assertEqual((raw/f"rgb-images/{key}/00004.jpg").read_bytes(),b"0,002-003\n")
            self.assertEqual(list(root.rglob("dataset.yaml")),[])


if __name__=="__main__":unittest.main()
