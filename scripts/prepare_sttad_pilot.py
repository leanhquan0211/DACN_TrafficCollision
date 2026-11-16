"""Verify selected STTAD samples, index author boxes and make a review sheet.

Unlabelled frames remain unknown. No train/val/test, fake seconds or negative
labels are generated. A 20-FPS preview is only for presentation if requested.
"""
from collections import defaultdict
from datetime import datetime
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.data_preparation import new_audit_dir,save_csv,save_json,sha256_file
from src.sttad_pilot import blob_id,parse_pixel_boxes,validate_registry


def main():
    import cv2
    import numpy as np
    registry_path=ROOT/"data/registries/sttad_selected_sources.json"
    registry=json.loads(registry_path.read_text());validate_registry(registry)
    raw=ROOT/"data_raw/sttad/author_samples"
    for item in registry["files"]:
        path=raw/item["path"]
        if not path.is_file() or blob_id(path.read_bytes())!=item["git_blob_sha1"]:
            raise ValueError(f"Missing/mismatched source: {item['path']}")
    # Preserve source split memberships without inventing memberships for other frames.
    memberships={kind:set((raw/f"{kind}list.txt").read_text().splitlines()) for kind in ("train","test")}
    out=new_audit_dir(ROOT/"outputs/audits","sttad_pilot_"+datetime.now(ZoneInfo("Asia/Bangkok")).date().isoformat())
    frames=[];regions=[];sequences=[];montage=[];fingerprints=defaultdict(set);exclusions=[]
    for sequence in registry["sequences"]:
        key=sequence["key"];image_dir=raw/"rgb-images"/key;label_dir=raw/"labels"/key
        images=sorted(image_dir.glob("*.jpg"),key=lambda p:int(p.stem))
        if not images:raise ValueError(f"No images: {key}")
        missing=[];labelled=[];shape=None;row_tiles=[];decoded=0
        for image_path in images:
            image=cv2.imread(str(image_path));label_path=label_dir/(image_path.stem+".txt")
            if image is None:
                if label_path.is_file():raise ValueError(f"Label points to invalid image: {image_path}")
                body=image_path.read_bytes()
                exclusions.append(dict(path=str(image_path.relative_to(ROOT)),sha256=sha256_file(image_path),
                    bytes=len(body),reason="Declared JPG is not a decodable image; source preserved",raw_text=body.decode("utf-8",errors="replace") if len(body)<200 else ""))
                continue
            index=decoded;decoded+=1
            height,width=image.shape[:2]
            if shape is None:shape=(width,height)
            if shape!=(width,height):raise ValueError(f"Changing image size: {key}")
            fingerprint=sha256_file(image_path);fingerprints[fingerprint].add(key)
            source_label="labels/"+key+"/"+label_path.name
            source_membership=";".join(kind for kind,values in memberships.items() if source_label in values) or "unlisted"
            boxes=parse_pixel_boxes(label_path.read_bytes(),width,height,sequence["source_class_id"]) if label_path.is_file() else []
            frames.append(dict(sequence=key,frame_index=index,source_frame_number=int(image_path.stem),
                image=str(image_path.relative_to(ROOT)),sha256=fingerprint,width_px=width,height_px=height,
                label=str(label_path.relative_to(ROOT)) if boxes else "",label_state="source_accident_region" if boxes else "unknown_no_label",
                source_split_membership=source_membership,project_split="unassigned",source_time_s="",training_eligible=False))
            if not boxes:missing.append(int(image_path.stem));continue
            labelled.append((int(image_path.stem),image_path,boxes))
            for j,box in enumerate(boxes):
                norm=box["bbox_cxcywh_norm"];xyxy=box["bbox_xyxy"]
                regions.append(dict(sequence=key,source_frame_number=int(image_path.stem),region_index=j,
                    source_class_id=box["source_class_id"],project_class_name="accident",
                    xmin_px=xyxy[0],ymin_px=xyxy[1],xmax_px=xyxy[2],ymax_px=xyxy[3],
                    cx=norm[0],cy=norm[1],w=norm[2],h=norm[3],
                    source_label_sha256=sha256_file(label_path),training_eligible=False,project_split="unassigned"))
        orphan_labels=[p.name for p in label_dir.glob("*.txt") if not (image_dir/(p.stem+".jpg")).is_file()]
        if orphan_labels:raise ValueError(f"Labels without matching images: {key}: {orphan_labels}")
        for frame_number,path,boxes in (labelled[0],labelled[len(labelled)//2],labelled[-1]):
            image=cv2.imread(str(path))
            for box in boxes:
                x1,y1,x2,y2=map(round,box["bbox_xyxy"])
                cv2.rectangle(image,(x1,y1),(x2,y2),(0,200,255),max(2,round(image.shape[1]/500)))
            # Letterbox keeps the geometry of each source aspect ratio.
            scale=min(480/image.shape[1],270/image.shape[0]);resized=cv2.resize(image,(round(image.shape[1]*scale),round(image.shape[0]*scale)))
            tile=np.full((305,480,3),18,dtype=np.uint8);x=(480-resized.shape[1])//2;y=35+(270-resized.shape[0])//2
            tile[y:y+resized.shape[0],x:x+resized.shape[1]]=resized
            cv2.putText(tile,f"{Path(key).name} / source frame {frame_number}",(10,23),cv2.FONT_HERSHEY_SIMPLEX,.48,(240,240,240),1)
            row_tiles.append(tile)
        montage.append(np.concatenate(row_tiles,axis=1))
        sequences.append(dict(sequence=key,declared_jpg_files=len(images),frames=decoded,labelled_frames=len(labelled),unknown_frames=len(missing),
            first_labelled_source_frame=labelled[0][0],last_labelled_source_frame=labelled[-1][0],
            labelled_frame_numbers=[item[0] for item in labelled],unknown_frame_numbers=missing,
            width_px=shape[0],height_px=shape[1],source_fps_verified=False,
            source_split_memberships=sorted({r["source_split_membership"] for r in frames if r["sequence"]==key}),
            camera_id=None,source_event_id=None,independence_verified=False))
    cv2.imwrite(str(out/"author_regions_contact_sheet.jpg"),np.concatenate(montage,axis=0))
    # Full source-box review, beyond the three representative frames per sequence.
    tiles=[]
    for row in frames:
        if row["label_state"]!="source_accident_region":continue
        image=cv2.imread(str(ROOT/row["image"]))
        expected=next(s["source_class_id"] for s in registry["sequences"] if s["key"]==row["sequence"])
        for box in parse_pixel_boxes((ROOT/row["label"]).read_bytes(),row["width_px"],row["height_px"],expected):
            x1,y1,x2,y2=map(round,box["bbox_xyxy"]);cv2.rectangle(image,(x1,y1),(x2,y2),(0,200,255),max(2,round(image.shape[1]/500)))
        scale=min(480/image.shape[1],270/image.shape[0]);preview=cv2.resize(image,(round(image.shape[1]*scale),round(image.shape[0]*scale)))
        tile=np.full((305,480,3),18,dtype=np.uint8);x=(480-preview.shape[1])//2;y=35+(270-preview.shape[0])//2
        tile[y:y+preview.shape[0],x:x+preview.shape[1]]=preview
        cv2.putText(tile,f"{Path(row['sequence']).name} / source frame {row['source_frame_number']}",(10,23),cv2.FONT_HERSHEY_SIMPLEX,.48,(240,240,240),1)
        tiles.append(tile)
    for start in range(0,len(tiles),16):
        page=tiles[start:start+16]
        while len(page)%4:page.append(np.full((305,480,3),18,dtype=np.uint8))
        mosaic=np.concatenate([np.concatenate(page[i:i+4],axis=1) for i in range(0,len(page),4)],axis=0)
        cv2.imwrite(str(out/f"review_all_{start//16+1:02}.jpg"),mosaic)
    save_csv(out/"frames.csv",frames,list(frames[0]))
    save_csv(out/"accident_regions.csv",regions,list(regions[0]))
    if exclusions:save_csv(out/"excluded_source_files.csv",exclusions,list(exclusions[0]))
    duplicates=[dict(sha256=h,sequences=sorted(keys)) for h,keys in fingerprints.items() if len(keys)>1]
    summary=dict(complete=True,commit=registry["commit"],registry_sha256=sha256_file(registry_path),
        sequences=sequences,total_frames=len(frames),total_regions=len(regions),
        labelled_frames=sum(s["labelled_frames"] for s in sequences),unknown_frames=sum(s["unknown_frames"] for s in sequences),
        all_declared_images_valid=not exclusions,excluded_source_files=exclusions,
        exact_image_duplicates_across_selected_sequences=duplicates,near_duplicates_or_camera_independence_verified=False,
        temporal_labels_complete=False,source_seconds_verified=False,project_split_created=False,training_eligible=False,
        metadata_is_not_full_benchmark=True,raw_sources_modified=False)
    save_json(out/"report.json",summary);print(json.dumps(dict(output=str(out),**summary),ensure_ascii=False,indent=2))


if __name__=="__main__":main()
