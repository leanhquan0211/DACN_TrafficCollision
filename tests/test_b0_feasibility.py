import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from src.b0_feasibility import prepare,verify
from src.sttad_pilot import blob_id


class FeasibilityDatasetTests(unittest.TestCase):
    def setUp(self):
        import cv2
        import numpy as np
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.output=self.root/"dataset"
        self.scenes={"T-T_crash/T-T_crash_1":"train","V-V_crash/V-V_crash_0":"val"}
        self.raw=self.root/"data_raw/sttad/author_samples";self.raw.mkdir(parents=True)
        self.negatives=[];files=[];sequences=[]
        for scene_index,(scene,split) in enumerate(self.scenes.items()):
            cls=6 if scene_index==0 else 11;sequences.append(dict(key=scene,source_class_id=cls))
            for frame in (1,2,3):
                rng=np.random.default_rng(scene_index*10+frame)
                image=rng.integers(0,255,(32,32,3),dtype=np.uint8)
                ok,encoded=cv2.imencode(".jpg",image);self.assertTrue(ok)
                relative=f"rgb-images/{scene}/{frame:05}.jpg";path=self.raw/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(encoded.tobytes())
                files.append(dict(path=relative,git_blob_sha1=blob_id(path.read_bytes())))
                if frame==1:self.negatives.append(dict(sequence=scene,source_frame_number=frame,image=str(path.relative_to(self.root)),image_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),label="negative_frame"))
            relative=f"labels/{scene}/00002.txt";path=self.raw/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(f"{cls} 4 4 20 24\n")
            files.append(dict(path=relative,git_blob_sha1=blob_id(path.read_bytes())))
        self.registry=dict(repository="https://github.com/ZTR02/STTAD",commit="a"*40,sequences=sequences,files=files)
        self.review=dict(purpose="software_feasibility_only",reviewer="codex_agent",user_or_teacher_approval=False,negative_frames=self.negatives)
        self.config=dict(purpose="software_feasibility_only",formal_research_approval=False,classes={"0":"accident"},registry="registry.json",review="review.json",scene_splits=self.scenes,test_split=None,source_classes=[6,11],near_duplicate_phash_distance=0,limitations=["fixture development data"])
        self.save()

    def save(self):
        for name,value in (("registry.json",self.registry),("review.json",self.review),("config.json",self.config)):
            (self.root/name).write_text(json.dumps(value))

    def run_prepare(self):return prepare(self.root,self.root/"config.json",self.output)

    def test_only_explicit_negatives_export_empty_labels_and_keep_unknown_out(self):
        info=self.run_prepare();_,rows=verify(self.root,self.output)
        self.assertEqual(len(rows),4)
        self.assertEqual(len(info["excluded"]),2)
        self.assertTrue(all(x["reason"]=="unknown_no_review" for x in info["excluded"]))
        self.assertTrue(info["feasibility_training_allowed"])
        self.assertFalse(info["research_training_allowed"])
        self.assertFalse(info["test_split_present"])
        for row in rows:
            label=(self.output/row["label_export"]).read_text()
            if row["label_origin"]=="agent_development_frame_review":self.assertEqual(label,"")
            else:self.assertEqual([float(x) for x in label.split()],[0,.375,.4375,.5,.625])
        self.assertFalse(any("00003" in row["image_export"] for row in rows))

    def test_source_positive_cannot_be_overridden_by_negative_review(self):
        record=dict(self.negatives[0]);record["source_frame_number"]=2
        p=self.raw/"rgb-images"/record["sequence"]/"00002.jpg"
        record.update(image=str(p.relative_to(self.root)),image_sha256=hashlib.sha256(p.read_bytes()).hexdigest())
        self.review["negative_frames"].append(record);self.save()
        with self.assertRaisesRegex(ValueError,"Source-positive"):self.run_prepare()
        self.assertFalse(self.output.exists())

    def test_duplicate_content_across_split_blocks_export(self):
        train=self.raw/"rgb-images/T-T_crash/T-T_crash_1/00002.jpg"
        relative="rgb-images/V-V_crash/V-V_crash_0/00002.jpg";val=self.raw/relative;val.write_bytes(train.read_bytes())
        next(x for x in self.registry["files"] if x["path"]==relative)["git_blob_sha1"]=blob_id(val.read_bytes());self.save()
        with self.assertRaisesRegex(ValueError,"Cross-split duplicate"):self.run_prepare()
        self.assertFalse(self.output.exists())

    def test_source_change_or_review_hash_mismatch_cannot_be_exported(self):
        source=self.root/self.negatives[0]["image"];source.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError,"Source fingerprint"):self.run_prepare()
        self.assertFalse(self.output.exists())

    def test_tampered_export_is_rejected_and_does_not_mutate_source(self):
        self.run_prepare();_,rows=verify(self.root,self.output)
        row=rows[0];original=(self.root/row["image_source"]).read_bytes()
        (self.output/row["image_export"]).write_bytes(b"tampered export")
        self.assertEqual((self.root/row["image_source"]).read_bytes(),original)
        with self.assertRaisesRegex(ValueError,"Image fingerprint"):verify(self.root,self.output)

    def test_missing_negative_review_is_not_replaced_by_missing_source_labels(self):
        self.review["negative_frames"]=[];self.save()
        with self.assertRaisesRegex(ValueError,"reviewed negative"):self.run_prepare()
        self.assertFalse(self.output.exists())

    def test_human_approval_or_formal_test_cannot_be_forged_by_this_exporter(self):
        self.review["user_or_teacher_approval"]=True;self.save()
        with self.assertRaisesRegex(ValueError,"forge human"):self.run_prepare()
        self.review["user_or_teacher_approval"]=False;self.config["test_split"]="test";self.save()
        with self.assertRaisesRegex(ValueError,"no test split"):self.run_prepare()


if __name__=="__main__":unittest.main()
