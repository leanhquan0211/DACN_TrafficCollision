"""Trích ảnh impact và ứng viên âm trước impact từ ACCIDENT v9 đã tải.

Đầu vào: MP4 thật/metadata gốc cùng receipt SHA ở data_raw/accident/public_selected/.
Đầu ra: PNG sạch, TXT bbox tác giả, báo cáo từng clip ở
outputs/data_audits/v004_accident_scale/ cho lần chạy mới.
Chạy sau khi tải thêm MP4; lệnh có thể chạy lại để tiếp tục clip chưa xử lý. Script
chỉ kiểm mapping kỹ thuật; ảnh trước impact là ứng viên nhãn dẫn xuất, không là
annotation âm tác giả hoặc bằng chứng toàn đoạn không tai nạn.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import cv2
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.audit_accident_public import METADATA_SHA256, check_timestamps, validate_row
from src.data_preparation import sha256_file
from src.storage_paths import output_path, require_output_path

RAW=ROOT/'data_raw/accident/public_selected'
DEFAULT_OUTPUT=output_path(ROOT,'data_audit','v004_accident_scale')
TYPES={'t-bone','rear-end','sideswipe','head-on'}


def write_png(path: Path, frame: np.ndarray) -> str:
    """Lưu pixel sạch lossless; chạy lại chỉ chấp nhận đúng byte PNG cũ."""
    success,encoded=cv2.imencode('.png',frame)
    if not success:
        raise ValueError('PNG encode failed')
    body=encoded.tobytes()
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        if hashlib.sha256(path.read_bytes()).digest()!=hashlib.sha256(body).digest():
            raise ValueError(f'Existing PNG differs: {path}')
    else:
        path.write_bytes(body)
    return sha256_file(path)


def extract_one(row: dict, receipt: dict, output: Path) -> dict:
    """Giải mã tuần tự để đối chiếu frame/PTS; chưa quyết định train/val/test."""
    source=(RAW/row['path']).resolve()
    if not source.is_relative_to(RAW.resolve()) or not source.is_file():
        raise ValueError('Missing or unsafe source video')
    if source.stat().st_size!=receipt['size_bytes'] or sha256_file(source)!=receipt['sha256']:
        raise ValueError('Source video differs from receipt')
    checked=validate_row(row)
    frame_index=checked['frame'];width=checked['width'];height=checked['height']
    # Chỉ giữ vài frame cần thiết trong RAM; không sao chép toàn clip sang ảnh.
    wanted={frame_index,0,max(0,int(frame_index*.25)),max(0,int(frame_index*.49))}
    pictures={};points=[];count=0;bad_shape=False
    capture=cv2.VideoCapture(str(source))
    try:
        if not capture.isOpened():
            raise ValueError('Video cannot open')
        while True:
            ok,frame=capture.read()
            if not ok:
                break
            if frame.shape[:2]!=(height,width):
                bad_shape=True
            if count in wanted:
                pictures[count]=frame.copy()
            points.append(capture.get(cv2.CAP_PROP_POS_MSEC)/1000)
            count+=1
    finally:
        capture.release()
    if bad_shape or count!=checked['declared_frames']+1 or frame_index not in pictures:
        raise ValueError(f'Decode/dimension/frame-count mismatch: decoded={count}, metadata={checked["declared_frames"]}')
    time_check=check_timestamps(points,frame_index,float(row['accident_time']))
    if not time_check['pts_mapping_verified']:
        raise ValueError(f'Impact PTS mismatch: {time_check}')
    stem=Path(row['path']).stem
    impact_path=output/'images/impact'/f'{stem}_f{frame_index:06d}.png'
    impact_sha=write_png(impact_path,pictures[frame_index])
    label_path=output/'labels_yolo'/f'{stem}_f{frame_index:06d}.txt'
    _,cx,cy,bw,bh=checked['yolo']
    label_text=f'0 {cx:.10f} {cy:.10f} {bw:.10f} {bh:.10f}\n'
    label_path.parent.mkdir(parents=True,exist_ok=True)
    if label_path.exists():
        if label_path.read_text(encoding='utf-8')!=label_text:
            raise ValueError(f'Existing converted label differs: {label_path}')
    else:
        label_path.write_text(label_text,encoding='utf-8')
    # Paper định nghĩa impact là tiếp xúc nhìn thấy đầu tiên. Chỉ lấy tối đa
    # hai frame trước nửa clip, cách impact >=1 giây theo PTS file phát hành.
    candidates=sorted(i for i in wanted if i<frame_index/2 and points[frame_index]-points[i]>=1)
    early=[]
    for index in candidates[-2:]:
        path=output/'images/preimpact'/f'{stem}_f{index:06d}.png'
        digest=write_png(path,pictures[index])
        early.append(dict(source_frame=index,pts_seconds=points[index],
                          margin_seconds=points[frame_index]-points[index],
                          image=path.relative_to(ROOT).as_posix(),image_sha256=digest,
                          label_origin='derived_author_first_visible_contact_candidate',
                          author_negative_annotation=False,whole_frame_visual_review=False))
    return dict(status='technical_pass',source_sequence=stem,
                source_group='ACCIDENT:'+stem.rsplit('_',1)[0],
                source_video=source.relative_to(ROOT).as_posix(),video_sha256=receipt['sha256'],
                author_split_iid=row['split_in_distribution'],author_split_geo=row['split_geo_aware'],
                source_type=row['type'],quality=row['quality'],region=row['region'],
                source_frame=frame_index,decoded_frames=count,width=width,height=height,
                bbox_xyxy_norm=list(checked['xyxy_norm']),bbox_area_norm=bw*bh,
                impact_image=impact_path.relative_to(ROOT).as_posix(),impact_image_sha256=impact_sha,
                converted_label=label_path.relative_to(ROOT).as_posix(),
                converted_label_sha256=sha256_file(label_path),
                author_metadata=RAW.joinpath('metadata-real.csv').relative_to(ROOT).as_posix(),
                author_region_scope='collision participants at first visible contact only',
                source_fps_verified=False,**time_check,preimpact_candidates=early)


def main() -> int:
    parser=argparse.ArgumentParser(description='Incrementally extract/verify public ACCIDENT impact boxes and early frame candidates')
    parser.add_argument('--output',type=Path,default=DEFAULT_OUTPUT)
    parser.add_argument('--max-new',type=int,default=0,help='0 = all available unprocessed clips')
    parser.add_argument('--workers',type=int,default=4,help='1..8 independent video decoders')
    args=parser.parse_args()
    if not 1 <= args.workers <= 8:
        parser.error('--workers must be 1..8')
    output=(ROOT/args.output).resolve()
    require_output_path(ROOT,output,'data_audit')
    output.mkdir(parents=True,exist_ok=True)
    journal=output/'clips.jsonl'
    prior={}
    if journal.exists():
        for line in journal.read_text(encoding='utf-8').splitlines():
            row=json.loads(line)
            if row['source_sequence'] in prior:
                raise ValueError('Duplicate journal sequence')
            prior[row['source_sequence']]=row
    receipts=json.loads((RAW/'download_receipts.json').read_text(encoding='utf-8'))
    with (RAW/'metadata-real.csv').open(encoding='utf-8-sig',newline='') as stream:
        metadata=list(csv.DictReader(stream))
    metadata_sha=sha256_file(RAW/'metadata-real.csv')
    if metadata_sha!=METADATA_SHA256:
        raise ValueError('ACCIDENT v9 metadata hash differs from the verified public source')
    selected=[row for row in metadata if row['type'] in TYPES
              and Path(row['path']).stem not in prior and row['path'] in receipts
              and (RAW/row['path']).is_file()]
    if args.max_new>0:
        selected=selected[:args.max_new]

    def process(row: dict) -> dict:
        name=row['path'];stem=Path(name).stem
        try:
            return extract_one(row,receipts[name],output)
        except Exception as exc:
            return dict(status='technical_reject',source_sequence=stem,
                        source_video=(RAW/name).relative_to(ROOT).as_posix(),
                        reason=str(exc),author_split_iid=row['split_in_distribution'],source_type=row['type'])

    done=0
    # Mỗi thread giải mã một video độc lập; chỉ thread chính ghi journal nên
    # không có hai dòng chen nhau. Journal giúp chạy lại sau khi gián đoạn.
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures=[pool.submit(process,row) for row in selected]
        for future in as_completed(futures):
            entry=future.result()
            with journal.open('a',encoding='utf-8',newline='\n') as stream:
                stream.write(json.dumps(entry,ensure_ascii=False)+'\n')
            prior[entry['source_sequence']]=entry;done+=1
            if done%25==0:
                print(f'extracted {done} new, {sum(x["status"]=="technical_pass" for x in prior.values())} technical pass total',flush=True)
    counts={s:sum(x['status']==s for x in prior.values()) for s in ('technical_pass','technical_reject')}
    report=dict(source='https://www.kaggle.com/datasets/picekl/accident/versions/9',
                metadata_sha256=metadata_sha,processed=len(prior),new_this_run=done,
                status_counts=counts,source_split_counts={s:sum(x['status']=='technical_pass' and x['author_split_iid']==s for x in prior.values()) for s in ('train','test')},
                positive_impact_images=counts['technical_pass'],
                preimpact_candidates=sum(len(x.get('preimpact_candidates',[])) for x in prior.values()),
                label_caveat='Preimpact candidates have no author-negative or whole-frame visual review; paper first-visible-contact used only as derivation; impact is author box, not per-frame detection GT')
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False),flush=True)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
