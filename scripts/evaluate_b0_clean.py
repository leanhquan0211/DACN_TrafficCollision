"""Đo checkpoint B0 trên test đã loại các nhóm trùng train.

Đầu vào: run train hoàn tất, config, provenance và phiếu loại nhóm được khóa
trước khi xem test. Đầu ra: YAML/list test sạch, metric bbox Ultralytics,
TP/FP/FN ở ngưỡng cố định và ảnh từng case trong thư mục run. Chạy sau train;
không thay dataset, checkpoint, ngưỡng hoặc nhãn tác giả.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.data_preparation import save_json, sha256_file
from scripts.train_b0 import check_inputs, evaluate_frames, workspace


def load_normal_probe(path: Path, train_rows: list[dict]) -> tuple[list[dict],dict]:
    """Kiểm video/ảnh của probe normal; không suy ra nhãn từ TXT thiếu."""
    manifest=json.loads(path.read_text(encoding='utf-8'))
    train_paths={r['source_path'] for r in train_rows
                 if r['split']=='train' and r['asset_kind']=='video_frame_reference'}
    train_hashes={sha256_file(workspace(path)) for path in train_paths}
    train_images={r['image_sha256'] for r in train_rows if r['split']=='train'}
    clips={x['sequence']:x for x in manifest['clips']}
    for clip in clips.values():
        source=workspace(clip['source_video'])
        if sha256_file(source)!=clip['video_sha256'] or clip['video_sha256'] in train_hashes:
            raise ValueError('Normal test video changed or is identical to training video')
    rows=[];identities=set()
    for sample in manifest['samples']:
        if sample['label_origin']!='author_normal_folder_clip_label' or sample['collision_label']!='negative':
            raise ValueError('Normal probe lacks author clip label')
        if sample['source_sequence'] not in clips or sample['source_video']!=clips[sample['source_sequence']]['source_video']:
            raise ValueError('Normal sample does not match source clip')
        image=workspace(sample['image']);label=workspace(sample['label'])
        if sha256_file(image)!=sample['image_sha256'] or sha256_file(label)!=sample['label_sha256'] or label.read_text().strip():
            raise ValueError('Normal probe image or empty label changed')
        if sample['image_sha256'] in train_images:
            raise ValueError('Identical normal probe frame appears in training')
        key=(sample['source_sequence'],int(sample['source_frame']))
        if key in identities:raise ValueError('Duplicate normal probe frame')
        identities.add(key)
        rows.append(dict(split='test',source_sequence=key[0],source_frame=key[1],
            leakage_group='TAD:'+key[0],collision_label='negative',
            export_image=image.as_posix(),export_label=label.as_posix()))
    if len(rows)!=manifest['sample_count']:
        raise ValueError('Normal probe sample count differs from locked manifest')
    return rows,manifest


def normal_summary(metrics: dict, cases: Path) -> dict:
    """Báo số frame/clip có dự đoán; không gọi đây là cảnh báo theo giờ."""
    import csv
    with (cases/'cases.csv').open(encoding='utf-8-sig',newline='') as stream:
        rows=list(csv.DictReader(stream))
    by_clip={}
    for row in rows:
        clip=by_clip.setdefault(row['source_sequence'],{'frames':0,'frames_with_predictions':0,'false_boxes':0})
        clip['frames']+=1;clip['frames_with_predictions']+=int(int(row['prediction_count'])>0)
        clip['false_boxes']+=int(row['fp'])
    return dict(frames=metrics['negative_frames'],frames_with_predictions=metrics['negative_frames_with_predictions'],
        negative_frame_false_positive_rate=metrics['negative_frame_false_positive_rate'],
        false_boxes=metrics['fp'],clips=len(by_clip),clips_with_any_predictions=sum(x['frames_with_predictions']>0 for x in by_clip.values()),
        by_clip=by_clip,scope='sparse labeled-normal frames; not event false alarms/hour')


def main() -> int:
    parser=argparse.ArgumentParser(description="Đánh giá B0 trên test đã loại nhóm near-duplicate được rà trước test")
    parser.add_argument('--config',type=Path,default=Path('configs/b0_verified_pilot_v1.json'))
    parser.add_argument('--review',type=Path,default=Path('data/reviews/2026-10-27-b0-near-duplicate-review.json'))
    parser.add_argument('--reference-experiment',type=Path,help='Tùy chọn so checkpoint run cũ trên cùng test sạch')
    parser.add_argument('--normal-manifest',type=Path,help='Tùy chọn probe clip normal tác giả đã cố định trước khi xem test')
    parser.add_argument('--check',action='store_true',help='Chỉ kiểm input và danh sách sạch; không chạy model')
    args=parser.parse_args()
    config_path=workspace(args.config);review_path=workspace(args.review)
    config=json.loads(config_path.read_text(encoding='utf-8'))
    review=json.loads(review_path.read_text(encoding='utf-8'))
    dataset,rows=check_inputs(config)
    provenance=dataset.parent/'provenance.csv'
    reviewed_provenance=workspace(review['input_provenance'])
    if sha256_file(reviewed_provenance)!=review['input_provenance_sha256']:
        raise ValueError('Provenance gốc khác phiếu loại nhóm đã khóa')
    for key in ('candidate_report','visual_evidence'):
        if sha256_file(workspace(review[key]))!=review[key+'_sha256']:
            raise ValueError(f'Bằng chứng rà thay đổi: {key}')
    excluded={item['group'] for item in review['excluded_test_groups']}
    if len(excluded)!=len(review['excluded_test_groups']):
        raise ValueError('Nhóm loại bị trùng')
    observed={r['leakage_group'] for r in rows if r['split']=='test'}
    if config.get('release_key')=='verified_pilot_release':
        if excluded & observed:
            raise ValueError('Release mới vẫn chứa nhóm test đã loại')
    elif not excluded<=observed:
        raise ValueError('Nhóm loại không nằm trong test gốc')
    # Bỏ toàn nhóm đã xác nhận trùng, không chỉ một ảnh; train/val giữ nguyên.
    clean=[r for r in rows if r['split']=='test' and r['leakage_group'] not in excluded]
    counts=Counter(r['collision_label'] for r in clean)
    expected=review['expected_clean_test']
    if len(clean)!=expected['images'] or counts['positive']!=expected['positive'] or counts['negative']!=expected['negative']:
        raise ValueError('Thành phần test sạch khác phiếu đã khóa')
    normal_rows=[];normal_manifest=None
    if args.normal_manifest:
        normal_rows,normal_manifest=load_normal_probe(workspace(args.normal_manifest),rows)
    print(json.dumps({'clean_test_images':len(clean),'positive':counts['positive'],
                      'negative':counts['negative'],'excluded_groups':len(excluded),
                      'external_normal_frames':len(normal_rows)},ensure_ascii=False),flush=True)
    if args.check:
        return 0
    run=workspace(config['output'])
    experiment=run/'experiment.json'
    if not experiment.is_file():
        raise ValueError('Run chưa kết thúc; chưa được đo test sạch')
    original=json.loads(experiment.read_text(encoding='utf-8'))
    checkpoint=workspace(original['checkpoint'])
    if sha256_file(checkpoint)!=original['checkpoint_sha256'] or sha256_file(config_path)!=original['config_sha256']:
        raise ValueError('Checkpoint/config khác run đã hoàn thành')
    output=run/'clean_test'
    if output.exists():
        raise FileExistsError('Clean test output đã tồn tại; không ghi đè')
    output.mkdir()
    # Danh sách đường dẫn chỉ tham chiếu PNG đã export; không sao chép ảnh hay
    # di chuyển nhãn. Ultralytics tìm TXT tương ứng qua images/ -> labels/.
    listing=output/'images.txt'
    listing.write_text(''.join((dataset.parent/r['export_image']).resolve().as_posix()+'\n' for r in clean),encoding='utf-8')
    yaml=output/'dataset.yaml'
    yaml.write_text('path: '+json.dumps(dataset.parent.as_posix(),ensure_ascii=False)+'\n'
                    'train: images/train\nval: images/val\ntest: '+json.dumps(listing.as_posix(),ensure_ascii=False)+
                    '\nnames:\n  0: accident\n',encoding='utf-8')
    os.environ['YOLO_CONFIG_DIR']=str(ROOT/'.tmp/ultralytics')
    os.environ['MPLCONFIGDIR']=str(ROOT/'.tmp/matplotlib')
    os.environ['YOLO_OFFLINE']='true';os.environ['YOLO_AUTOINSTALL']='false'
    os.environ['TORCH_HOME']=str(ROOT/'.tmp/torch')
    cache=ROOT/'.tmp/ultralytics/Ultralytics';cache.mkdir(parents=True,exist_ok=True)
    font=Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts/arial.ttf'
    if font.exists() and not (cache/'Arial.ttf').exists():
        shutil.copy2(font,cache/'Arial.ttf')
    import ultralytics
    from ultralytics import YOLO
    if ultralytics.__version__!=config['ultralytics_version']:
        raise ValueError('Version Ultralytics khác config')
    model=YOLO(str(checkpoint))
    measured=model.val(data=str(yaml),split='test',device=config['device'],imgsz=config['imgsz'],
                       batch=config['batch'],workers=0,plots=True,project=str(output),name='ultralytics')
    bbox={k:float(v) for k,v in measured.results_dict.items()}
    manual=evaluate_frames(model,clean,dataset,'test',config,output/'cases')
    reference=None;baseline=None
    if args.reference_experiment:
        reference_path=workspace(args.reference_experiment)
        previous=json.loads(reference_path.read_text(encoding='utf-8'))
        old_config=previous['config']
        for key in ('imgsz','prediction_confidence','matching_iou'):
            if old_config[key]!=config[key]:
                raise ValueError(f'Run tham chiếu khác ngưỡng/kích thước cố định: {key}')
        old_checkpoint=workspace(previous['checkpoint'])
        if sha256_file(old_checkpoint)!=previous['checkpoint_sha256']:
            raise ValueError('Checkpoint run tham chiếu đã thay đổi')
        # Hai model cùng 112 ảnh và ngưỡng; dữ liệu train + optimizer thay đổi
        # cùng lúc nên phép so này không tách riêng nguyên nhân cải thiện.
        baseline=YOLO(str(old_checkpoint))
        old_measured=baseline.val(data=str(yaml),split='test',device=config['device'],imgsz=config['imgsz'],
            batch=config['batch'],workers=0,plots=True,project=str(output),name='reference_ultralytics')
        old_manual=evaluate_frames(baseline,clean,dataset,'test',config,output/'reference_cases')
        reference=dict(experiment=reference_path.relative_to(ROOT).as_posix(),
            checkpoint=old_checkpoint.relative_to(ROOT).as_posix(),checkpoint_sha256=sha256_file(old_checkpoint),
            ultralytics_bbox_metrics={k:float(v) for k,v in old_measured.results_dict.items()},
            fixed_threshold_metrics=old_manual,
            interpretation='Same images and thresholds; multiple training changes prevent causal attribution')
    external=None
    if normal_rows:
        normal_cases=output/'normal_cases'
        result=evaluate_frames(model,normal_rows,dataset,'test',config,normal_cases)
        external=dict(manifest=workspace(args.normal_manifest).relative_to(ROOT).as_posix(),
            manifest_sha256=sha256_file(workspace(args.normal_manifest)),
            author_label='TAD test/normal clip label; not user-reviewed',
            model=normal_summary(result,normal_cases))
        if baseline is not None:
            old_cases=output/'normal_reference_cases'
            old_result=evaluate_frames(baseline,normal_rows,dataset,'test',config,old_cases)
            external['reference']=normal_summary(old_result,old_cases)
    save_json(output/'report.json',dict(status='complete',scope='clean held-out image-level B0 pilot, not event benchmark',
        review=review_path.relative_to(ROOT).as_posix(),review_sha256=sha256_file(review_path),
        input_provenance_sha256=sha256_file(provenance),checkpoint=checkpoint.relative_to(ROOT).as_posix(),
        checkpoint_sha256=sha256_file(checkpoint),config_sha256=sha256_file(config_path),
        image_list_sha256=sha256_file(listing),images=len(clean),label_counts=dict(counts),
        ultralytics_bbox_metrics=bbox,fixed_threshold_metrics=manual,reference=reference,external_normal_probe=external,
        limitations=['Five reviewed negative frames only','Near-duplicate screening is not exhaustive',
                     'Camera and event independence not fully proven','No temporal or long-video metrics'],
        original_114_image_test='contaminated, not a valid independent test result'))
    print(f'Clean evaluation: {output/"report.json"}',flush=True)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
