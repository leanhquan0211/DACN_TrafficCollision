"""A small, explicit software-feasibility experiment, separate from research gates.

Uses pinned author accident regions and individually recorded agent-negative
frames. Never promotes unlabelled frames or CADP proposals into ground truth.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import shutil

from src.data_preparation import save_csv, save_json, sha256_file
from src.sttad_pilot import blob_id, parse_pixel_boxes, validate_registry


def project_path(root: Path, relative: str) -> Path:
    path=(root/relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Path outside project")
    return path


def phash(image) -> int:
    import cv2
    import numpy as np
    gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
    values=cv2.dct(cv2.resize(gray,(32,32)).astype(np.float32))[:8,:8].flatten()
    bits=values>np.median(values[1:])
    return sum(int(bit)<<i for i,bit in enumerate(bits))


def prepare(root: Path, config_path: Path, output: Path) -> dict:
    import cv2
    root=root.resolve();output=output.resolve()
    if not output.is_relative_to(root):raise ValueError("Keep feasibility output inside project")
    config=json.loads(config_path.read_text())
    if config.get("purpose")!="software_feasibility_only" or config.get("formal_research_approval") is not False:
        raise ValueError("This exporter is for software feasibility only")
    if config.get("classes")!={"0":"accident"}:raise ValueError("Expected one accident class")
    if config.get("test_split") is not None or set(config["scene_splits"].values())!={"train","val"}:
        raise ValueError("Expected development train/val scene groups, no test split")
    registry_path=project_path(root,config["registry"])
    registry=json.loads(registry_path.read_text());validate_registry(registry)
    if set(config["scene_splits"])!={s["key"] for s in registry["sequences"]}:
        raise ValueError("Every selected scene must have one development split")
    raw=root/"data_raw/sttad/author_samples"
    indexed={item["path"]:item for item in registry["files"]}
    for path,item in indexed.items():
        source=project_path(raw,path)
        if not source.is_file() or blob_id(source.read_bytes())!=item["git_blob_sha1"]:
            raise ValueError(f"Source fingerprint mismatch: {path}")
    review_path=project_path(root,config["review"]);review=json.loads(review_path.read_text())
    if (review.get("purpose")!="software_feasibility_only" or review.get("reviewer")!="codex_agent"
            or review.get("user_or_teacher_approval") is not False):
        raise ValueError("Expected explicit agent development review; do not forge human approval")
    negatives={}
    for record in review["negative_frames"]:
        key=(record["sequence"],record["source_frame_number"])
        if key in negatives or record.get("label")!="negative_frame":
            raise ValueError("Duplicate/unsupported frame review")
        expected=raw/"rgb-images"/key[0]/f"{key[1]:05}.jpg"
        if project_path(root,record["image"])!=expected.resolve() or sha256_file(expected)!=record["image_sha256"]:
            raise ValueError("Review/image fingerprint mismatch")
        negatives[key]=record
    rows=[];excluded=[];used_negatives=set()
    for sequence in registry["sequences"]:
        scene=sequence["key"];split=config["scene_splits"][scene]
        if sequence["source_class_id"] not in config["source_classes"]:
            raise ValueError("Unsupported accident source class")
        for relative in sorted(p for p in indexed if p.startswith("rgb-images/"+scene+"/")):
            source=raw/relative;number=int(source.stem);image=cv2.imread(str(source))
            label_relative="labels/"+scene+"/"+source.stem+".txt"
            has_label=label_relative in indexed;negative=(scene,number) in negatives
            if image is None:
                if has_label or negative:raise ValueError("Selected label/review points to invalid image")
                excluded.append(dict(path=str(source.relative_to(root)),reason="source_not_image"));continue
            if has_label and negative:raise ValueError("Source-positive frame cannot be reviewed negative")
            if not has_label and not negative:
                excluded.append(dict(path=str(source.relative_to(root)),reason="unknown_no_review"));continue
            h,w=image.shape[:2]
            boxes=parse_pixel_boxes((raw/label_relative).read_bytes(),w,h,sequence["source_class_id"]) if has_label else []
            text="".join("0 "+" ".join(f"{value:.10f}" for value in b["bbox_cxcywh_norm"])+"\n" for b in boxes)
            if negative:used_negatives.add((scene,number))
            name=scene.replace("/","__")+"__"+source.name
            rows.append(dict(scene_group=scene,split=split,source_frame_number=number,
                image_source=str(source.relative_to(root)),image_sha256=sha256_file(source),
                source_label=str((raw/label_relative).relative_to(root)) if has_label else "",
                source_label_sha256=sha256_file(raw/label_relative) if has_label else "",
                label_origin="author_accident_region" if has_label else "agent_development_frame_review",
                source_class_id=sequence["source_class_id"] if has_label else "",
                region_count=len(boxes),image_export=f"images/{split}/{name}",
                label_export=f"labels/{split}/{Path(name).stem}.txt",label_sha256=hashlib.sha256(text.encode()).hexdigest(),
                phash64=f"{phash(image):016x}",_label_text=text))
    if used_negatives!=set(negatives):raise ValueError("Review points to an unselected/unregistered frame")
    counts={}
    for split in ("train","val"):
        subset=[r for r in rows if r["split"]==split]
        positive=sum(r["region_count"]>0 for r in subset);negative=len(subset)-positive
        if not positive or not negative:raise ValueError(f"{split} needs explicit positive and reviewed negative frames")
        counts[split]=dict(images=len(subset),positive_frames=positive,negative_frames=negative,
                           scenes=sorted({r["scene_group"] for r in subset}))
    cross=[];minimum=64
    for a in (r for r in rows if r["split"]=="train"):
        for b in (r for r in rows if r["split"]=="val"):
            distance=(int(a["phash64"],16)^int(b["phash64"],16)).bit_count();minimum=min(minimum,distance)
            if a["image_sha256"]==b["image_sha256"] or distance<=config["near_duplicate_phash_distance"]:
                cross.append(dict(train=a["image_source"],val=b["image_source"],phash_distance=distance))
    if cross:raise ValueError(f"Cross-split duplicate/near-duplicate candidates need review: {cross[:3]}")
    # Validation finished before exporting any training files.
    output.mkdir(parents=True,exist_ok=False)
    for row in rows:
        image_path=output/row["image_export"];label_path=output/row["label_export"]
        image_path.parent.mkdir(parents=True,exist_ok=True);label_path.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(root/row["image_source"],image_path)
        label_path.write_text(row.pop("_label_text"))
    save_csv(output/"manifest.csv",rows,list(rows[0]))
    save_json(output/"dataset.yaml",dict(path=str(output),train="images/train",val="images/val",names={"0":"accident"}))
    save_json(output/"experiment_config.json",config)
    save_json(output/"review_snapshot.json",review)
    info=dict(schema_version=1,complete=True,purpose="software_feasibility_only",feasibility_training_allowed=True,
        research_training_allowed=False,formal_b0_gate_satisfied=False,test_split_present=False,
        counts=counts,excluded=excluded,minimum_cross_split_phash_distance=minimum,
        phash_screen_is_not_proof_of_camera_independence=True,source_seconds_verified=False,
        source_registry=str(registry_path.relative_to(root)),source_registry_sha256=sha256_file(registry_path),
        config_source=str(config_path.resolve().relative_to(root)),config_sha256=sha256_file(config_path),
        review_source=str(review_path.relative_to(root)),review_sha256=sha256_file(review_path),
        manifest_sha256=sha256_file(output/"manifest.csv"),dataset_yaml_sha256=sha256_file(output/"dataset.yaml"),
        config_snapshot_sha256=sha256_file(output/"experiment_config.json"),review_snapshot_sha256=sha256_file(output/"review_snapshot.json"),
        limitations=config["limitations"])
    save_json(output/"readiness.json",info)
    return info


def verify(root: Path, dataset: Path) -> tuple[dict,list[dict]]:
    info=json.loads((dataset/"readiness.json").read_text())
    if (info.get("purpose")!="software_feasibility_only" or info.get("complete") is not True
            or info.get("feasibility_training_allowed") is not True or info.get("research_training_allowed") is not False):
        raise ValueError("Not an explicitly prepared feasibility dataset")
    for name,key in (("manifest.csv","manifest_sha256"),("dataset.yaml","dataset_yaml_sha256"),
                     ("experiment_config.json","config_snapshot_sha256"),("review_snapshot.json","review_snapshot_sha256")):
        if sha256_file(dataset/name)!=info[key]:raise ValueError(f"Dataset metadata fingerprint mismatch: {name}")
    for name,key in (("source_registry","source_registry_sha256"),("config_source","config_sha256"),("review_source","review_sha256")):
        if sha256_file(project_path(root,info[name]))!=info[key]:raise ValueError(f"Source decision changed: {name}")
    with (dataset/"manifest.csv").open() as stream:rows=list(csv.DictReader(stream))
    seen=set();groups={"train":set(),"val":set()};content={"train":set(),"val":set()}
    for row in rows:
        if row["split"] not in groups:raise ValueError("Unsupported split")
        identity=(row["scene_group"],row["source_frame_number"])
        if identity in seen:raise ValueError("Repeated source frame")
        seen.add(identity);groups[row["split"]].add(row["scene_group"]);content[row["split"]].add(row["image_sha256"])
        for prefix in (root,dataset):
            key="image_source" if prefix==root else "image_export"
            if sha256_file(project_path(prefix,row[key]))!=row["image_sha256"]:raise ValueError("Image fingerprint mismatch")
        if sha256_file(project_path(dataset,row["label_export"]))!=row["label_sha256"]:raise ValueError("Export label fingerprint mismatch")
        if row["source_label"] and sha256_file(project_path(root,row["source_label"]))!=row["source_label_sha256"]:
            raise ValueError("Author label fingerprint mismatch")
    if groups["train"]&groups["val"] or content["train"]&content["val"]:raise ValueError("Scene/content leakage")
    for split in groups:
        if sum(r["split"]==split for r in rows)!=info["counts"][split]["images"]:raise ValueError("Manifest count mismatch")
    return info,rows
