"""Kiểm trùng ảnh/cảnh và độ lệch nguồn của pilot trước khi chia tập.

Đầu vào: inventory hiện có, audit STTAD và hai clip normal TAD lấy chọn lọc.
Đầu ra: fingerprint frame, cặp ảnh gần giống, bảng nguồn/nhãn và montage cảnh.
Chế độ --normal-batch còn nhận batch normal mới, dataset cũ và probe đã xem
để rà nhóm và bbox nhỏ trước release; không chạy model hoặc tự gán nhãn.
Chạy trong giai đoạn dữ liệu; hash gần nhau chỉ đề xuất kiểm cảnh, không chứng
minh cùng camera/sự kiện và không tự chia split hoặc thay nhãn người dùng.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data_preparation import new_audit_dir, save_csv, save_json, sha256_file


def phash(gray: np.ndarray) -> int:
    """DCT thấp tần giữ bố cục ảnh; bỏ DC để độ sáng không quyết định toàn hash."""
    small = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA).astype(np.float32)
    low = cv2.dct(small)[:8, :8].ravel()[1:]
    result = 0
    for bit in low > np.median(low):
        result = (result << 1) | int(bit)
    return result


def features(picture: np.ndarray) -> tuple[int, int, np.ndarray]:
    """So cả ảnh và vùng giữa để gợi ý các bản crop/đổi viền; không suy camera."""
    gray = cv2.cvtColor(picture, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    crop = gray[h//10:h-h//10, w//10:w-w//10]
    thumb = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA)
    return phash(gray), phash(crop), thumb


def write_small_positive_crops(records: list[dict], output: Path) -> int:
    """Phóng crop GT train nhỏ để nhìn pixel thật; không tạo ảnh train mới."""
    chosen=sorted((r for r in records if r['split']=='train' and float(r['min_side_at_640'])<8),
                  key=lambda r:float(r['min_side_at_640']))[:16]
    canvas=np.full((4*225,4*320,3),25,np.uint8)
    for i,row in enumerate(chosen):
        image=cv2.imdecode(np.frombuffer((ROOT/row['image']).read_bytes(),np.uint8),1);h,w=image.shape[:2]
        _,cx,cy,bw,bh=map(float,(ROOT/row['label']).read_text().splitlines()[0].split())
        x1,y1,x2,y2=(cx-bw/2)*w,(cy-bh/2)*h,(cx+bw/2)*w,(cy+bh/2)*h
        pad=max(32,(x2-x1)*1.5,(y2-y1)*1.5)
        left,top=max(0,int(x1-pad)),max(0,int(y1-pad))
        right,bottom=min(w,int(x2+pad+1)),min(h,int(y2+pad+1))
        crop=image[top:bottom,left:right];scale=min(316/crop.shape[1],190/crop.shape[0])
        crop=cv2.resize(crop,(round(crop.shape[1]*scale),round(crop.shape[0]*scale)),interpolation=cv2.INTER_NEAREST)
        cv2.rectangle(crop,(round((x1-left)*scale),round((y1-top)*scale)),
                      (round((x2-left)*scale),round((y2-top)*scale)),(0,255,0),1)
        y,x=(i//4)*225,(i%4)*320
        canvas[y:y+crop.shape[0],x:x+crop.shape[1]]=crop
        cv2.putText(canvas,row['source_sequence'][:28],(x+3,y+207),cv2.FONT_HERSHEY_SIMPLEX,.4,(255,255,255),1)
        cv2.putText(canvas,f"min side at 640: {float(row['min_side_at_640']):.2f}px",(x+3,y+221),cv2.FONT_HERSHEY_SIMPLEX,.4,(255,255,255),1)
    ok,body=cv2.imencode('.jpg',canvas)
    if not ok:raise ValueError('Crop preview encoding failed')
    with output.open('xb') as stream:stream.write(body.tobytes())
    return len(chosen)


def audit_normal_batch(manifest_path: Path, base: Path, probe_path: Path) -> Path:
    """Rà cảnh batch normal với nhau, dataset cũ và probe đã xem trước split.

    Hash chỉ đề xuất cặp cần xem. Giữ ảnh đầu/giữa/cuối và cặp gần nhất để
    AI/người kiểm quyết định nhóm; không tự coi tên khác là camera độc lập.
    Đồng thời kiểm bbox dương cũ và kích thước biểu kiến ở ảnh inference 640.
    """
    cv2.setNumThreads(1)
    manifest_path=manifest_path.resolve();base=base.resolve();probe_path=probe_path.resolve()
    if any(not p.is_relative_to(ROOT) for p in (manifest_path,base,probe_path)):
        raise ValueError('Audit paths outside project')
    audit=manifest_path.parent
    if (audit/'group_screen.json').exists():raise FileExistsError('Batch grouping already audited')
    batch=json.loads(manifest_path.read_text(encoding='utf-8'))
    probe=json.loads(probe_path.read_text(encoding='utf-8'))
    old_report=json.loads((base/'report.json').read_text(encoding='utf-8'))
    expected_provenance=old_report.get('provenance_sha256')
    if not expected_provenance:
        # Export cũ chưa ghi trường này; experiment hoàn tất vẫn khóa hash.
        experiment=ROOT/'outputs/training'/base.parent.name/'experiment.json'
        expected_provenance=json.loads(experiment.read_text(encoding='utf-8'))['provenance_sha256']
    if sha256_file(base/'provenance.csv')!=expected_provenance:
        raise ValueError('Base provenance changed')
    with (base/'provenance.csv').open(encoding='utf-8-sig',newline='') as stream:old=list(csv.DictReader(stream))
    records=[dict(scope='new_normal',sequence=s['source_sequence'],frame=int(s['source_frame']),
                  path=s['image'],sha=s['image_sha256']) for s in batch['samples']]
    records += [dict(scope='base_'+r['split'],sequence=r['source_sequence'],frame=int(r['source_frame']),
                     path=(base/r['export_image']).relative_to(ROOT).as_posix(),sha=r['image_sha256']) for r in old]
    records += [dict(scope='consumed_normal_probe',sequence=s['source_sequence'],frame=int(s['source_frame']),
                     path=s['image'],sha=s['image_sha256']) for s in probe['samples']]
    vectors=[];pixels=defaultdict(list);sizes={}
    for record in records:
        path=(ROOT/record['path']).resolve()
        if not path.is_relative_to(ROOT) or sha256_file(path)!=record['sha']:
            raise ValueError('Audit source image changed')
        image=cv2.imdecode(np.frombuffer(path.read_bytes(),np.uint8),1)
        if image is None:raise ValueError('Audit image decode failed')
        full,crop,_=features(image);gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
        small=cv2.resize(gray,(9,8),interpolation=cv2.INTER_AREA);difference=0
        for bit in (small[:,1:]>small[:,:-1]).flat:difference=(difference<<1)|int(bit)
        vectors.append((full,crop,difference))
        pixels[hashlib.sha256(image.tobytes()).hexdigest()].append(record)
        sizes[record['path']]=image.shape[:2]
    pair_best={};new_count=len(batch['samples'])
    for i in range(new_count):
        a=records[i];fa,ca,da=vectors[i]
        for j in range(i+1,len(records)):
            b=records[j]
            if a['sequence']==b['sequence']:continue
            fb,cb,db=vectors[j];full=(fa^fb).bit_count();crop=(ca^cb).bit_count();dh=(da^db).bit_count()
            score=(min(full,crop),full+crop,dh)
            key=(a['sequence'],b['sequence'],b['scope'])
            if key not in pair_best or score<pair_best[key][0]:
                pair_best[key]=(score,dict(first_sequence=a['sequence'],first_image=a['path'],
                    second_sequence=b['sequence'],second_image=b['path'],second_scope=b['scope'],
                    phash_distance=full,crop_phash_distance=crop,dhash_distance=dh,
                    visual_candidate=min(full,crop)<=8 and dh<=12))
    pairs=[v[1] for v in pair_best.values()]
    candidates=[p for p in pairs if p['visual_candidate']]
    nearest=[]
    for name in sorted({r['sequence'] for r in records[:new_count]}):
        choices=sorted((p for p in pairs if p['first_sequence']==name and p['second_scope']!='new_normal'),
                       key=lambda p:(min(p['phash_distance'],p['crop_phash_distance']),p['dhash_distance']))
        nearest.extend(choices[:3])
    exact=[dict(pixel_sha256=digest,members=items) for digest,items in pixels.items()
           if any(r['scope']=='new_normal' for r in items) and len({r['sequence'] for r in items})>1]
    # Mỗi trang sáu chuỗi, mỗi chuỗi ba thời điểm: dễ nhìn và giữ ảnh nguồn sạch.
    scenes=sorted((audit/'scenes').glob('*.jpg'))
    for start in range(0,len(scenes),6):
        pages=[cv2.imdecode(np.frombuffer(p.read_bytes(),np.uint8),1) for p in scenes[start:start+6]]
        ok,body=cv2.imencode('.jpg',cv2.vconcat(pages))
        if not ok:raise ValueError('Scene overview encoding failed')
        (audit/f'scene_page_{start//6+1}.jpg').write_bytes(body.tobytes())
    for start in range(0,len(nearest[::3]),6):
        pages=[]
        for pair in nearest[::3][start:start+6]:
            cells=[]
            for field in ('first_image','second_image'):
                im=cv2.imdecode(np.frombuffer((ROOT/pair[field]).read_bytes(),np.uint8),1)
                h,w=im.shape[:2];ratio=min(480/w,270/h);im=cv2.resize(im,(round(w*ratio),round(h*ratio)))
                cell=np.full((300,480,3),25,np.uint8);cell[:im.shape[0],:im.shape[1]]=im
                label=pair['first_sequence'] if field=='first_image' else pair['second_sequence']+' '+pair['second_scope']
                cv2.putText(cell,label[:64],(3,289),cv2.FONT_HERSHEY_SIMPLEX,.4,(255,255,255),1);cells.append(cell)
            pages.append(cv2.hconcat(cells))
        ok,body=cv2.imencode('.jpg',cv2.vconcat(pages))
        if not ok:raise ValueError('Nearest scene preview encoding failed')
        (audit/f'nearest_base_page_{start//6+1}.jpg').write_bytes(body.tobytes())
    positive=[]
    for row in old:
        if row['collision_label']!='positive':continue
        label=(base/row['export_label']);text=label.read_text()
        if sha256_file(label)!=row['label_sha256']:raise ValueError('Base positive label changed')
        height,width=sizes[(base/row['export_image']).relative_to(ROOT).as_posix()]
        for line in text.splitlines():
            cls,cx,cy,bw,bh=map(float,line.split())
            if (cls!=0 or not all(np.isfinite(v) for v in (cx,cy,bw,bh)) or min(bw,bh)<=0
                    or min(cx-bw/2,cy-bh/2)<-1e-6 or max(cx+bw/2,cy+bh/2)>1+1e-6):
                raise ValueError('Invalid original positive bbox; no automatic correction')
            positive.append(dict(source_sequence=row['source_sequence'],source_frame=row['source_frame'],split=row['split'],
                image=(base/row['export_image']).relative_to(ROOT).as_posix(),label=label.relative_to(ROOT).as_posix(),
                bbox_area_fraction=bw*bh,min_side_at_640=min(bw*width,bh*height)*640/max(width,height),
                bbox_valid=True,auto_excluded=False))
    save_csv(audit/'small_positive_audit.csv',positive,list(positive[0]))
    small_crop_count=write_small_positive_crops(positive,audit/'small_train_positive_crops.jpg')
    selected=sorted((r for r in positive if r['split']=='train'),key=lambda r:r['min_side_at_640'])[:12]
    from scripts.analyze_b0 import contact_sheet
    # Chỉ contact sheet train cho quyết định dữ liệu tiếp theo; nhãn dương gốc giữ nguyên.
    original_cases=[]
    for row in selected:
        im=cv2.imdecode(np.frombuffer((ROOT/row['image']).read_bytes(),np.uint8),1);h,w=im.shape[:2]
        for line in (ROOT/row['label']).read_text().splitlines():
            _,cx,cy,bw,bh=map(float,line.split());cv2.rectangle(im,(round((cx-bw/2)*w),round((cy-bh/2)*h)),
                (round((cx+bw/2)*w),round((cy+bh/2)*h)),(0,255,0),2)
        target=audit/'small_positive_previews'/f"{row['source_sequence']}.jpg";target.parent.mkdir(exist_ok=True)
        ok,body=cv2.imencode('.jpg',im)
        if not ok:raise ValueError('Positive preview encoding failed')
        target.write_bytes(body.tobytes())
        original_cases.append(dict(source_sequence=row['source_sequence'],source_frame=row['source_frame'],example=target.relative_to(ROOT).as_posix()))
    contact_sheet(original_cases,audit/'small_train_positives.jpg','train GT frame')
    result=dict(normal_manifest=manifest_path.relative_to(ROOT).as_posix(),normal_manifest_sha256=sha256_file(manifest_path),
        base_dataset=base.relative_to(ROOT).as_posix(),base_provenance_sha256=sha256_file(base/'provenance.csv'),
        consumed_probe=probe_path.relative_to(ROOT).as_posix(),consumed_probe_sha256=sha256_file(probe_path),
        normal_samples=new_count,base_images=len(old),probe_images=len(probe['samples']),
        candidate_pairs=candidates,nearest_base_pairs=nearest,exact_pixel_duplicates=exact,
        new_group_pairs=[p for p in pairs if p['second_scope']=='new_normal'],
        positive_bbox_count=len(positive),invalid_positive_boxes=0,
        positives_min_side_at_640_lt8=sum(r['min_side_at_640']<8 for r in positive),
        positives_min_side_at_640_lt16=sum(r['min_side_at_640']<16 for r in positive),
        smallest_train_crops_reviewable=small_crop_count,
        positive_label_changes=0,camera_independence_verified=False,
        warning='Hash candidates require visual review; no close match does not prove independent cameras; no model predictions used')
    save_json(audit/'group_screen.json',result)
    print(json.dumps({k:result[k] for k in ('normal_samples','base_images','probe_images','positive_bbox_count','positives_min_side_at_640_lt16')}),flush=True)
    return audit


def audit_exported_split(dataset: Path, extra_normal_manifest: Path | None = None, report_path: Path | None = None) -> Path:
    """Gợi ý ảnh gần giống xuyên split từ PNG đã export; không tự sửa split.

    pHash và dHash cùng cần gần nhau để giảm cặp sai. Kết quả cần được nhìn
    lại; ảnh/camera gần giống vẫn có thể lọt ngoài ngưỡng và không có bằng
    chứng tính độc lập chỉ từ hash.
    """
    dataset=dataset.resolve()
    if not dataset.is_relative_to(ROOT):
        raise ValueError("Dataset outside project")
    with (dataset/"provenance.csv").open(encoding="utf-8-sig",newline="") as stream:
        rows=list(csv.DictReader(stream))
    if extra_normal_manifest:
        extra_normal_manifest=extra_normal_manifest.resolve()
        if not extra_normal_manifest.is_relative_to(ROOT):
            raise ValueError("Normal manifest outside project")
        manifest=json.loads(extra_normal_manifest.read_text(encoding="utf-8"))
        for sample in manifest["samples"]:
            path=(ROOT/sample["image"]).resolve()
            if not path.is_relative_to(ROOT) or sample["label_origin"]!="author_normal_folder_clip_label":
                raise ValueError("Invalid external normal sample")
            if sha256_file(path)!=sample["image_sha256"]:
                raise ValueError("External normal sample changed")
            rows.append(dict(source_sequence=sample["source_sequence"],source_frame=sample["source_frame"],
                             split="external_normal",export_image=path.as_posix()))
    vectors=[]
    cv2.setNumThreads(1)
    for row in rows:
        path=(dataset/row["export_image"]).resolve()
        allowed_root=ROOT if row["split"]=="external_normal" else dataset
        if not path.is_relative_to(allowed_root):
            raise ValueError("Image path outside dataset")
        gray=cv2.imdecode(np.frombuffer(path.read_bytes(),np.uint8),cv2.IMREAD_GRAYSCALE)
        if gray is None:
            raise ValueError(f"Cannot decode exported image: {path}")
        small=cv2.resize(gray,(9,8),interpolation=cv2.INTER_AREA)
        difference=small[:,1:]>small[:,:-1]
        dhash=0
        for bit in difference.flat:
            dhash=(dhash<<1)|int(bit)
        vectors.append((phash(gray),dhash))
    pairs=[]
    for i,a in enumerate(rows):
        for j in range(i):
            b=rows[j]
            if a["split"]==b["split"]:
                continue
            hp=(vectors[i][0]^vectors[j][0]).bit_count()
            if hp<=5:
                hd=(vectors[i][1]^vectors[j][1]).bit_count()
                if hd<=8:
                    pairs.append(dict(first_sequence=a["source_sequence"],first_frame=a["source_frame"],
                        first_split=a["split"],first_image=a["export_image"],
                        second_sequence=b["source_sequence"],second_frame=b["source_frame"],
                        second_split=b["split"],second_image=b["export_image"],
                        phash_distance=hp,dhash_distance=hd))
    if report_path is None:
        audit=new_audit_dir(ROOT/"outputs/audits","b0_exported_similarity")
        report_path=audit/'report.json'
    else:
        report_path=report_path.resolve()
        if not report_path.is_relative_to(ROOT) or report_path.exists():
            raise ValueError('Split audit needs a new report inside project')
        audit=report_path.parent;audit.mkdir(parents=True,exist_ok=True)
    save_json(report_path,dict(dataset=dataset.relative_to(ROOT).as_posix(),
        images=len(rows),candidates=pairs,thresholds={"phash_hamming_max":5,"dhash_hamming_max":8},
        scope="Candidate resemblance, not proof of identical event or independent cameras"))
    print(json.dumps({"images":len(rows),"candidate_pairs":len(pairs),"report":str(report_path)}))
    return audit


def inputs(inventory: Path, sttad_report: Path, tad_dir: Path) -> list[dict]:
    """Dùng một nhóm cho mỗi nguồn gốc, không thêm preview hoặc clip dẫn xuất."""
    groups = {}
    with inventory.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            if not row["clean_source_path"] or row["collision_label"] == "unknown":
                continue
            key = row["source_dataset"] + ":" + row["source_sequence"]
            groups[key] = dict(key=key, dataset=row["source_dataset"], sequence=row["source_sequence"],
                               label=row["collision_label"], path=row["clean_source_path"],
                               label_evidence=row["review_status"])
    sttad = json.loads(sttad_report.read_text(encoding="utf-8"))
    for sequence in sttad["selected_sequences"]:
        key = "STTAD:" + sequence
        groups[key] = dict(key=key, dataset="STTAD", sequence=sequence, label="positive",
                           path=sttad["raw_root"] + "/rgb-images/" + sequence,
                           label_evidence="author_region_annotation;not_user_reviewed")
    for path in sorted(tad_dir.glob("*.mp4")):
        key = "TAD:" + path.stem
        groups[key] = dict(key=key, dataset="TAD", sequence=path.stem, label="negative",
                           path=path.relative_to(ROOT).as_posix(),
                           label_evidence="author_normal_folder_clip_label;not_user_reviewed")
    for row in groups.values():
        path = (ROOT/row["path"]).resolve()
        if not path.is_relative_to(ROOT) or not path.exists():
            raise ValueError(f"Missing or outside-project input: {row['path']}")
    return list(groups.values())


def images(group: dict):
    """Giải mã toàn input; giữ lỗi riêng. Số frame video là chỉ số decode bắt đầu 0."""
    path = ROOT/group["path"]
    if path.is_dir():
        files = sorted((p for p in path.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png")),
                       key=lambda p: int(p.stem.removeprefix("img")))
        for file in files:
            picture = cv2.imdecode(np.frombuffer(file.read_bytes(), np.uint8), cv2.IMREAD_COLOR)
            yield file.relative_to(ROOT).as_posix(), int(file.stem.removeprefix("img")), picture
    else:
        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            raise ValueError(f"Video cannot open: {path}")
        try:
            reported = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            frame = 0
            while True:
                ok, picture = cap.read()
                if not ok:
                    break
                yield group["path"] + f"#frame={frame}", frame, picture
                frame += 1
            if frame != reported:
                raise ValueError(f"Video decode count {frame} != metadata {reported}: {path}")
        finally:
            cap.release()


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit pilot source groups, near images and source/label bias; no split")
    parser.add_argument("--inventory", type=Path, default=ROOT/"data/pilot_inventory.csv")
    parser.add_argument("--sttad-report", type=Path)
    parser.add_argument("--exported-dataset", type=Path, help="Kiểm ảnh gần giống xuyên split trong một dataset YOLO đã xuất")
    parser.add_argument("--extra-normal-manifest", type=Path, help="Thêm mẫu normal bên ngoài để kiểm gần trùng với dataset")
    parser.add_argument('--split-report',type=Path,help='Gom báo cáo split vào audit batch đang dùng, file mới và không ghi đè')
    parser.add_argument('--normal-batch',type=Path,help='Rà batch normal đã tải trước khi chốt nhóm/split')
    parser.add_argument('--base-dataset',type=Path,help='Dataset YOLO cũ dùng đối chiếu cảnh và kiểm nhãn dương')
    parser.add_argument('--consumed-normal-probe',type=Path,help='Probe normal đã xem, không được biến thành train')
    parser.add_argument("--tad-dir", type=Path, default=ROOT/"data_raw/tad/public_selected/TAD-benchmark/train/normal")
    parser.add_argument("--accident-report", type=Path, action="append", default=[],
                        help="Thêm batch ACCIDENT trước đăng ký manifest; có thể lặp lại")
    args = parser.parse_args()
    if args.normal_batch:
        if not args.base_dataset or not args.consumed_normal_probe:
            parser.error('Normal batch needs --base-dataset and --consumed-normal-probe')
        audit_normal_batch(args.normal_batch,args.base_dataset,args.consumed_normal_probe)
        return 0
    if args.exported_dataset:
        audit_exported_split(args.exported_dataset,args.extra_normal_manifest,args.split_report)
        return 0
    if args.extra_normal_manifest:
        parser.error("--extra-normal-manifest requires --exported-dataset")
    if not args.sttad_report:
        parser.error("Supply --sttad-report or --exported-dataset")
    groups = inputs(args.inventory, args.sttad_report, args.tad_dir)
    by_key = {g["key"]:g for g in groups}
    for report_path in args.accident_report:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        for clip in report["selected_clips"]:
            key = "ACCIDENT:"+clip["source_sequence"]
            if key in by_key and by_key[key]["path"] != clip["source_video"]:
                raise ValueError("Conflicting source paths for one sequence")
            by_key[key] = dict(key=key, dataset="ACCIDENT", sequence=clip["source_sequence"],
                               label="positive", path=clip["source_video"],
                               label_evidence="author_impact_event;not_full_clip_bbox_coverage")
    groups = list(by_key.values())
    audit = new_audit_dir(ROOT/"outputs/audits", "pilot_groups")
    all_records, features_by_group, summary, montage, exact = [], {}, [], [], defaultdict(list)
    for group in groups:
        records, vectors, examples = [], [], {}
        bad, sizes, brightness = [], Counter(), []
        source_path = ROOT/group["path"]
        if source_path.is_dir():
            count_hint = sum(p.suffix.lower() in (".jpg", ".jpeg", ".png") for p in source_path.iterdir())
        else:
            cap = cv2.VideoCapture(str(source_path))
            count_hint = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.release()
        for ordinal, (path, frame, picture) in enumerate(images(group)):
            if picture is None:
                bad.append(path)
                continue
            full, crop, thumb = features(picture)
            height, width = picture.shape[:2]
            # Hash pixel giải mã nhận ra ảnh giống hệt kể cả file nén khác nhau.
            digest = hashlib.sha256(f"{width}x{height}:".encode() + picture.tobytes()).hexdigest()
            record = dict(group=group["key"], source_frame=frame, source_path=path, width=width, height=height,
                          pixel_sha256=digest, phash63=f"{full:016x}", crop_phash63=f"{crop:016x}")
            records.append(record)
            exact[digest].append((group["key"], path))
            vectors.append((full, crop, thumb))
            # Chỉ giữ ba ảnh nhỏ cho montage, không tích cả video trong RAM.
            thumbnail = cv2.resize(picture, (320, 180))
            if not examples:
                examples["first"] = thumbnail
            if ordinal == count_hint//2:
                examples["middle"] = thumbnail
            examples["last"] = thumbnail
            sizes[f"{width}x{height}"] += 1
            brightness.append(float(thumb.mean()))
        if not records:
            raise ValueError(f"No decoded frame: {group['key']}")
        features_by_group[group["key"]] = (records, vectors)
        all_records.extend(records)
        summary.append(dict(**group, decoded_frames=len(records), excluded_decode_files=json.dumps(bad),
                            dimensions=json.dumps(sizes), mean_gray=round(float(np.mean(brightness)), 2),
                            verified_camera_id="", independence_status="not_proven_by_image_hash",
                            source_fps_verified=False, split="unassigned"))
        # Ba mốc nguyên bản: dùng xem bối cảnh/độ đông và thay cảnh, không vẽ đáp án.
        panel = cv2.hconcat([examples["first"], examples.get("middle", examples["last"]), examples["last"]])
        header = np.zeros((26, 960, 3), dtype=np.uint8)
        cv2.putText(header, group["key"] + " | source label=" + group["label"], (5, 18),
                    cv2.FONT_HERSHEY_SIMPLEX, .43, (255,255,255), 1)
        montage.append(cv2.vconcat([header, panel]))
        print(group["key"], "decoded", len(records), "excluded", len(bad), flush=True)
    nearest = []
    # Tìm cặp gần nhất giữa MỖI đôi nhóm trên toàn frame đã decode. Ngưỡng 8
    # chỉ sàng lọc để nhìn lại, không dùng xác nhận trùng/độc lập hay gán nhãn.
    for i, group in enumerate(groups):
        ra, va = features_by_group[group["key"]]
        for other in groups[i+1:]:
            rb, vb = features_by_group[other["key"]]
            best = (999, 999, 0, 0, 999, 999)
            for a, (fa, ca, _) in enumerate(va):
                for b, (fb, cb, _) in enumerate(vb):
                    full, crop = (fa ^ fb).bit_count(), (ca ^ cb).bit_count()
                    candidate = (min(full, crop), full+crop, a, b, full, crop)
                    if candidate < best:
                        best = candidate
            _, _, a, b, full, crop = best
            rmse = float(np.sqrt(np.mean((va[a][2].astype(float)-vb[b][2])**2))/255)
            nearest.append(dict(group_a=group["key"], group_b=other["key"],
                                frame_a=ra[a]["source_path"], frame_b=rb[b]["source_path"],
                                full_hamming=full, crop_hamming=crop, gray_rmse=round(rmse, 5),
                                candidate_for_visual_check=min(full,crop)<=8,
                                status="heuristic_only_no_auto_merge_or_independence_claim"))
    cross_exact = [dict(pixel_sha256=d, groups=json.dumps(sorted({x[0] for x in members})),
                        examples=json.dumps(members[:6])) for d, members in exact.items() if len({x[0] for x in members})>1]
    save_csv(audit/"frame_fingerprints.csv", all_records, list(all_records[0]))
    save_csv(audit/"groups.csv", summary, list(summary[0]))
    save_csv(audit/"nearest_cross_group_pairs.csv", nearest, list(nearest[0]))
    save_csv(audit/"exact_cross_group_duplicates.csv", cross_exact, ["pixel_sha256", "groups", "examples"])
    ok, jpg = cv2.imencode(".jpg", cv2.vconcat(montage))
    if not ok:
        raise ValueError("Montage encoding failed")
    with (audit/"scene_overview.jpg").open("xb") as stream:
        stream.write(jpg.tobytes())
    report = dict(group_count=len(groups), decoded_frames=len(all_records),
                  source_label_groups=dict(Counter(x["dataset"]+":"+x["label"] for x in groups)),
                  cross_group_exact_pixel_hashes=len(cross_exact),
                  near_pair_candidates=sum(r["candidate_for_visual_check"] for r in nearest),
                  compared_group_pairs=len(nearest), candidate_threshold_phash_hamming=8,
                  camera_independence_verified=False, source_fps_verified=False, split_created=False,
                  warning="No close hash does not prove distinct cameras/events; candidates need scene checks",
                  sttad_report=args.sttad_report.as_posix(),
                  accident_reports=[p.as_posix() for p in args.accident_report])
    save_json(audit/"report.json", report)
    print(json.dumps(report))
    print(f"Report: {(audit/'report.json').relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
