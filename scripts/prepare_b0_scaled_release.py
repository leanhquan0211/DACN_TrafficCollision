"""Tạo release B0 với bbox tác giả và âm có căn cứ, theo nhóm nguồn đã khóa.

Đầu vào: index/split impact đã kiểm, phiếu rà cũ và pool DETRAC/TAD. Đầu ra:
index/split/provenance và khóa readiness để exporter tạo dataset YOLO. Chạy
sau khi có dữ liệu và review tương ứng; không biến frame thiếu nhãn thành âm.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import json
import html
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data_preparation import save_csv, save_json, sha256_file
from scripts.prepare_b0_pilot_index import export_plan, export_dataset
from src.data_preparation import validate_b0_verified_origins
from src.storage_paths import output_path, run_folder

OUT = ROOT / "data/processed/b0_accident_scaled_v1"
READY = ROOT / "data/b0_readiness.json"
VERIFIED_OUT = ROOT / "data/processed/b0_verified_pilot_v1"
VERIFIED_POLICY = ROOT / "configs/b0_verified_label_policy.json"


def normal_extension_plan(base_rows: list[dict], base_split: list[dict], manifest: dict,
                          review: dict, review_name: str) -> tuple[list[dict],list[dict],list[dict]]:
    """Thêm đúng normal đã nhóm, giữ mọi split cũ và để holdout ở ngoài train.

    Hàm thuần để kiểm các quy tắc chống leakage mà không cần đọc video. Nhãn
    âm phải đến từ folder normal của tác giả; một nhóm/cảnh không qua hai tập.
    """
    validate_b0_verified_origins(base_rows)
    rows=[dict(r) for r in base_rows];splits=[dict(s) for s in base_split]
    assignments={(r['source_dataset'],r['source_sequence'],int(r['source_frame'])):r['split'] for r in base_split}
    old_groups={r['leakage_group']:assignments[(r['source_dataset'],r['source_sequence'],int(r['source_frame']))] for r in base_rows}
    profiles={};group_splits=dict(old_groups)
    for group in review['groups']:
        split=group['assignment']
        if split not in ('train','val','reserve_negative_holdout','exclude'):
            raise ValueError('New normal assignment is not authorized')
        name=group['group_id']
        if name in group_splits and group_splits[name]!=split:
            raise ValueError('One reviewed source group crosses splits')
        group_splits[name]=split
        for sequence in group['sequences']:
            if sequence in profiles:raise ValueError('Sequence belongs to multiple reviewed groups')
            profiles[sequence]=(name,split)
    if set(profiles)!={c['sequence'] for c in manifest['clips']}:
        raise ValueError('Review must cover every prepared clip, including exclusions')
    seen=set(assignments);reserve=[]
    for sample in manifest['samples']:
        if sample['label_origin']!='author_normal_folder_clip_label' or sample['collision_label']!='negative':
            raise ValueError('New negatives require explicit public author-normal labels')
        key=('TAD',sample['source_sequence'],int(sample['source_frame']))
        if key in seen:raise ValueError('Duplicate existing or new source frame')
        seen.add(key)
        group,split=profiles[key[1]]
        if split=='exclude':continue
        if split=='reserve_negative_holdout':
            reserve.append(dict(sample,leakage_group=group,split=split));continue
        row=dict(source_dataset='TAD',source_sequence=key[1],source_frame=key[2],source_path=sample['image'],
                 asset_kind='image',collision_label='negative',label_origin='author_normal_folder_clip_label',
                 label_evidence=review_name,accident_bbox_count=0,converted_label='',leakage_group=group,
                 camera_id_verified=False,training_release_allowed=False)
        if 'split' in base_rows[0]:row['split']='unassigned'
        if set(row)!=set(base_rows[0]):raise ValueError('Base pool schema differs; do not silently omit provenance fields')
        rows.append(row);splits.append(dict(source_dataset='TAD',source_sequence=key[1],source_frame=key[2],split=split))
    validate_b0_verified_origins(rows)
    export_plan(rows,splits)
    return rows,splits,reserve


def build_normal_expansion(review_path: Path, output: Path) -> None:
    """Phát hành pilot mới sau review cảnh; không thay release/model/test cũ."""
    from scripts.train_b0 import check_inputs
    review_path=review_path.resolve()
    if not review_path.is_relative_to(ROOT):raise ValueError('Review outside project')
    review=json.loads(review_path.read_text(encoding='utf-8'))
    manifest_path=ROOT/review['normal_manifest'];screen_path=ROOT/review['group_screen']
    for path,key in ((manifest_path,'normal_manifest_sha256'),(screen_path,'group_screen_sha256')):
        if not path.resolve().is_relative_to(ROOT) or sha256_file(path)!=review[key]:
            raise ValueError('Reviewed source evidence changed')
    if review.get('model_predictions_seen_before_assignment') is not False:
        raise ValueError('Normal groups must be assigned before model prediction')
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    if review.get('release_key')=='hard_negative_pilot_release':
        frozen=ROOT/review['group_assignment_before_mining']
        if sha256_file(frozen)!=review['group_assignment_before_mining_sha256']:
            raise ValueError('Pre-mining assignments changed')
        assigned=json.loads(frozen.read_text(encoding='utf-8'))
        if assigned['groups']!=review['groups'] or manifest['group_assignment_sha256']!=sha256_file(frozen):
            raise ValueError('Mined samples differ from frozen source assignments')
        if manifest['validation_or_reserve_mined'] is not False:
            raise ValueError('Do not select evaluation frames with model scores')
    base_config=ROOT/review.get('base_training_config','configs/b0_verified_pilot_v1.json')
    prior_config=json.loads(base_config.read_text(encoding='utf-8'))
    check_inputs(prior_config)
    readiness=json.loads(READY.read_text(encoding='utf-8'))
    release_key=review.get('release_key','normal_expanded_pilot_release')
    if release_key not in ('normal_expanded_pilot_release','hard_negative_pilot_release'):
        raise ValueError('Unknown normal-data release key')
    if release_key in readiness:raise FileExistsError('Normal expansion release already exists')
    prior=readiness[prior_config.get('release_key','verified_pilot_release')]
    base_index=ROOT/prior['pool'];base_split=ROOT/prior['split_manifest']
    if sha256_file(base_index)!=review['base_index_sha256'] or sha256_file(base_split)!=review['base_split_sha256']:
        raise ValueError('Original release differs from normal expansion review')
    rows,splits,reserved=normal_extension_plan(csv_rows(base_index),csv_rows(base_split),manifest,review,
                                             review_path.relative_to(ROOT).as_posix())
    # Các PNG mới phải đúng sample hash đã decode; raw video vẫn nối được qua manifest.
    for sample in manifest['samples']:
        if sha256_file(ROOT/sample['image'])!=sample['image_sha256']:
            raise ValueError('New normal image differs from prepared manifest')
    for clip in manifest['clips']:
        if sha256_file(ROOT/clip['source_video'])!=clip['video_sha256']:
            raise ValueError('New raw normal clip changed')
    policy=ROOT/review.get('label_policy','configs/b0_normal_expanded_label_policy.json')
    if not policy.is_file():raise FileNotFoundError('Missing expanded normal label policy')
    output.mkdir(parents=True,exist_ok=False)
    registry=ROOT/'data/registries';name=output.name
    index=registry/f'{name}_index.csv';split_file=registry/f'{name}_split.csv'
    asset_file=registry/f'{name}_asset_hashes.json';holdout_file=registry/f'{name}_holdout.json'
    if any(p.exists() for p in (index,split_file,asset_file,holdout_file)):
        raise FileExistsError('New release registry already exists')
    save_csv(index,rows,list(rows[0]));save_csv(split_file,splits,list(splits[0]))
    assets={r[k] for r in rows for k in ('source_path','label_evidence','converted_label') if r[k]}
    assets.update((manifest_path.relative_to(ROOT).as_posix(),screen_path.relative_to(ROOT).as_posix()))
    assets.update(c['source_video'] for c in manifest['clips'])
    save_json(asset_file,{p:sha256_file(ROOT/p) for p in sorted(assets)})
    # Holdout negative độc lập với lần train mới; không trộn vào test ảnh cũ đã xem.
    labels=manifest_path.parent/'holdout_labels';labels.mkdir(exist_ok=False)
    for sample in reserved:
        label=labels/f"{sample['source_sequence']}_f{sample['source_frame']:06d}.txt"
        label.write_text('',encoding='utf-8')
        sample.update(label=label.relative_to(ROOT).as_posix(),label_sha256=sha256_file(label))
    reserve_sequences={r['source_sequence'] for r in reserved}
    save_json(holdout_file,dict(scope='sealed additional negative-only holdout; not a new positive/negative event benchmark',
        source_url=manifest['source_url'],clips=[c for c in manifest['clips'] if c['sequence'] in reserve_sequences],
        samples=reserved,sample_count=len(reserved),review=review_path.relative_to(ROOT).as_posix(),
        review_sha256=sha256_file(review_path),model_predictions_seen=False,camera_independence_verified=False))
    plan=export_plan(rows,splits)
    summary=dict(scope='basic-image pilot with source-reviewed normal expansion; validation-only model selection',
        samples=len(rows),split_labels={s:dict(Counter(r['collision_label'] for r in plan if r['split']==s)) for s in ('train','val','test')},
        original_samples=len(csv_rows(base_index)),added_exported_samples=len(rows)-len(csv_rows(base_index)),
        reserved_negative_frames=len(reserved),reserved_negative_sequences=sorted(reserve_sequences),
        original_positive_labels_changed=0,original_split_changed=False,legacy_test_already_consumed=True,
        camera_independence_verified=False,review=review_path.relative_to(ROOT).as_posix(),
        negative_holdout=holdout_file.relative_to(ROOT).as_posix())
    save_json(output/'split_report.json',summary)
    backup=manifest_path.parent/'readiness_before_release.json'
    if backup.exists():raise FileExistsError('Readiness backup already exists')
    shutil.copy2(READY,backup)
    readiness[release_key]=dict(can_train=True,split_created=True,scope='verified_negative_image_pilot_normal_expansion',
        pool=index.relative_to(ROOT).as_posix(),split_manifest=split_file.relative_to(ROOT).as_posix(),
        split_report=(output/'split_report.json').relative_to(ROOT).as_posix(),
        export_pool_sha256=sha256_file(index),export_split_sha256=sha256_file(split_file),export_policy_sha256=sha256_file(policy),
        export_asset_manifest=asset_file.relative_to(ROOT).as_posix(),export_asset_manifest_sha256=sha256_file(asset_file),
        initial_weights_sha256=sha256_file(ROOT/'yolov8n.pt'),negative_holdout=holdout_file.relative_to(ROOT).as_posix(),
        scope_note='Old consumed test preserved for provenance; train experiments evaluate validation only')
    from datetime import datetime,timezone,timedelta
    readiness['updated_date']=datetime.now(timezone(timedelta(hours=7))).date().isoformat()
    READY.write_text(json.dumps(readiness,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    try:
        export_dataset(index,split_file,output/'dataset','pilot',release_key,policy)
    except Exception:
        readiness[release_key]['can_train']=False
        readiness[release_key]['export_failed']=True
        READY.write_text(json.dumps(readiness,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        raise
    write_normal_overview(review_path,output)
    print(json.dumps(summary,ensure_ascii=False),flush=True)


def mine_assigned_normal(groups_path: Path) -> Path:
    """Chọn âm khó CHỈ từ nhóm đã khóa train; val/reserve lấy đều, không inference.

    Mỗi train clip:20mẫu đều + một mẫu score cao nhất trong mỗi10bin thời gian
    chưa được lấy, tổng30. Nhãn rỗng vẫn đến từ normal tác giả, không từ score.
    Đây là chọn frame offline, khác hard-negative mining theo loss/anchor SSD.
    """
    import cv2
    import numpy as np
    groups_path=groups_path.resolve()
    review=json.loads(groups_path.read_text(encoding='utf-8'))
    manifest_path=ROOT/review['candidate_manifest']
    if sha256_file(manifest_path)!=review['candidate_manifest_sha256']:raise ValueError('Candidate manifest changed')
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    audit=manifest_path.parent;target=audit/'selected_normal_manifest.json'
    if target.exists():raise FileExistsError('Preserve previous mined selection')
    assignments={}
    for group in review['groups']:
        if group['assignment'] not in ('train','val','reserve_negative_holdout','exclude'):
            raise ValueError('Unknown assignment before mining')
        for sequence in group['sequences']:
            if sequence in assignments:raise ValueError('Sequence assigned more than once')
            assignments[sequence]=group['assignment']
    if set(assignments)!={c['sequence'] for c in manifest['clips']}:raise ValueError('Incomplete assignments')
    checkpoint=ROOT/review['mining_checkpoint']
    if sha256_file(checkpoint)!=review['mining_checkpoint_sha256']:raise ValueError('Mining checkpoint changed')
    os.environ['YOLO_CONFIG_DIR']=str(ROOT/'.tmp/ultralytics');os.environ['YOLO_OFFLINE']='true';os.environ['YOLO_AUTOINSTALL']='false'
    import ultralytics
    from ultralytics import YOLO
    if ultralytics.__version__!=review['ultralytics_version']:raise ValueError('Mining version changed')
    from src.b0_diagnostics import hard_negative_indices
    model=YOLO(str(checkpoint));selected=[];scores=[];clips=[]
    if model.names!={0:'accident'}:raise ValueError('Mining requires the locked accident checkpoint')
    for clip in manifest['clips']:
        sequence=clip['sequence'];role=assignments[sequence]
        candidates=sorted([s for s in manifest['samples'] if s['source_sequence']==sequence],key=lambda s:s['source_frame'])
        if role=='exclude':clips.append(clip);continue
        take=30
        if len(candidates)<take:raise ValueError('Too few candidate frames')
        if role=='train':
            ranked={}
            for i,sample in enumerate(candidates):
                path=ROOT/sample['image']
                if sha256_file(path)!=sample['image_sha256']:raise ValueError('Candidate image changed')
                frame=cv2.imdecode(np.frombuffer(path.read_bytes(),np.uint8),1)
                prediction=model.predict(frame,imgsz=960,device='0',conf=.01,iou=.7,max_det=100,verbose=False)[0]
                score=max(prediction.boxes.conf.cpu().tolist(),default=0)
                ranked[i]=score
                scores.append(dict(sequence=sequence,source_frame=sample['source_frame'],score=score,role='train'))
            anchors,hard=hard_negative_indices([ranked[i] for i in range(len(candidates))])
            chosen=anchors|hard
            for i in sorted(chosen):selected.append(dict(candidates[i],selection_reason='uniform_anchor' if i in anchors else 'training_only_ranked_hard',mining_score=ranked[i]))
        else:
            chosen={round(i*(len(candidates)-1)/(take-1)) for i in range(take)}
            selected.extend(dict(candidates[i],selection_reason='uniform_no_model_prediction',mining_score=None) for i in sorted(chosen))
        if len(chosen)!=30:raise ValueError('Unexpected frame selection count')
        clips.append(dict(clip,candidate_frame_indices=clip['sampled_frame_indices'],
                          sampled_frame_indices=[candidates[i]['source_frame'] for i in sorted(chosen)]))
        print(f'Mining/selection {sequence}: {role}, {len(chosen)} frames',flush=True)
    save_csv(audit/'train_candidate_scores.csv',scores,list(scores[0]))
    save_json(target,dict(manifest,clips=clips,samples=selected,sample_count=len(selected),
        group_assignment=groups_path.relative_to(ROOT).as_posix(),group_assignment_sha256=sha256_file(groups_path),
        mining_checkpoint=review['mining_checkpoint'],mining_checkpoint_sha256=review['mining_checkpoint_sha256'],
        selection='train only:20uniform+10temporal-bin ranked; val/reserve:30uniform without model predictions',
        validation_or_reserve_mined=False))
    return target


def csv_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_normal_overview(review_path: Path, output: Path) -> Path:
    """Tạo một trang xem nguồn, split và mốc val; không chạy model từ trang."""
    review=json.loads(review_path.read_text(encoding='utf-8'))
    manifest_path=ROOT/review['normal_manifest'];audit=manifest_path.parent
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    summary=json.loads((output/'split_report.json').read_text(encoding='utf-8'))
    groups={s:g for g in review['groups'] for s in g['sequences']}
    reference=audit/'reference_val/report.json'
    reference=json.loads(reference.read_text(encoding='utf-8')) if reference.exists() else None
    completed_folder=run_folder(ROOT,output.name)
    completed_path=completed_folder/'experiment.json' if completed_folder else None
    completed=json.loads(completed_path.read_text(encoding='utf-8')) if completed_path and completed_path.exists() else None
    training_state=f"Đã train xong {completed['epochs_completed']} epoch và đo validation." if completed else 'Chưa có báo cáo train hoàn tất cho dataset mới.'
    counts=Counter(groups[c['sequence']]['assignment'] for c in manifest['clips'])
    decoded=sum(c['decoded_frames'] for c in manifest['clips'])
    sampled=manifest.get('selection','30 frame đều mỗi clip trước prediction')
    config_name=review.get('training_config','configs/b0_normal_expanded_v1.json')
    val_images=sum(summary['split_labels']['val'].values())
    link=lambda path:html.escape(Path(os.path.relpath(path,audit)).as_posix(),quote=True)
    roles={'train':'Train mới','val':'Validation mới','reserve_negative_holdout':'Giữ riêng, chưa chạy model','exclude':'Loại'}
    parts=['<!doctype html><html lang="vi"><meta charset="utf-8"><title>B0 normal expansion</title>',
        '<style>body{font:16px system-ui;max-width:1200px;margin:30px auto;padding:0 20px;background:#f4f7fb;color:#142b44}table{border-collapse:collapse;background:white;width:100%}td,th{padding:9px;border:1px solid #cad6e4;text-align:left}img{max-width:100%}p{line-height:1.65}details{padding:12px;background:white;margin:12px 0}a{color:#145bab}code{overflow-wrap:anywhere}</style>',
        '<h1>B0: dữ liệu normal mở rộng</h1>',
        f'<p>{len(manifest["clips"])} clip train/normal công khai của tác giả TAD, {decoded} frame đã giải mã đủ. Chọn mẫu: {html.escape(sampled)}. Nhãn normal đến từ tác giả; nhận xét cảnh/split do AI kiểm, không phải xác nhận mới của người dùng.</p>',
        f"<p>Dataset pilot mới: <b>{summary['samples']} ảnh</b>. Clip theo vai trò: {html.escape(str(dict(counts)))}; giữ riêng {summary['reserved_negative_frames']} frame. Test cũ và holdout cũ đã xem vẫn ngoài lần train mới. {training_state}</p>",
        '<table><tr><th>Tập</th><th>Dương</th><th>Âm</th></tr>']
    for split,counts in summary['split_labels'].items():
        parts.append(f"<tr><td>{split}</td><td>{counts.get('positive',0)}</td><td>{counts.get('negative',0)}</td></tr>")
    parts.append('</table><h2>Mốc model cũ trên validation mới</h2>')
    if reference:
        parts.append(f'<p>Cùng {val_images} ảnh val mới; P/R/F1 ở confidence 0,25, IoU ghép 0,5. Đây là checkpoint mốc, chưa phải model mới đã train.</p><table><tr><th>Checkpoint cũ</th><th>mAP50–95</th><th>Precision</th><th>Recall</th><th>F1</th><th>TP/FP/FN</th></tr>')
        for r in reference['results']:
            metrics=r['fixed_threshold_metrics'];official=r['official_bbox_metrics']
            name=Path(r['reference_experiment']).parent.name
            parts.append(f"<tr><td>{html.escape(name)}</td><td>{official['metrics/mAP50-95(B)']:.4f}</td><td>{metrics['precision']:.4f}</td><td>{metrics['recall']:.4f}</td><td>{metrics['f1']:.4f}</td><td>{metrics['tp']}/{metrics['fp']}/{metrics['fn']}</td></tr>")
        parts.append('</table><p><a href="reference_val/report.json">Report và hash validation</a></p>')
    else:parts.append('<p>Chưa có mốc validation trong bản trang này.</p>')
    if completed:
        metric=completed['official_bbox_metrics']['val'];fixed=completed['fixed_threshold_metrics']['val']
        parts.append(f"<h2>Kết quả run normal mở rộng</h2><p>Epoch hoàn thành: {completed['epochs_completed']}. Cùng {val_images} ảnh validation; test cũ và reserve chưa được suy luận trong run này.</p><table><tr><th>mAP50</th><th>mAP50–95</th><th>TP/FP/FN tại 0,25/0,5</th><th>P/R/F1 tại ngưỡng cố định</th><th>Frame âm có bbox</th></tr><tr><td>{metric['metrics/mAP50(B)']:.5f}</td><td>{metric['metrics/mAP50-95(B)']:.5f}</td><td>{fixed['tp']}/{fixed['fp']}/{fixed['fn']}</td><td>{fixed['precision']:.5f}/{fixed['recall']:.5f}/{fixed['f1']:.5f}</td><td>{fixed['negative_frames_with_predictions']}/{fixed['negative_frames']}</td></tr></table><p><a href='{link(completed_path)}'>Experiment và hash checkpoint</a></p>")
    parts.append('<h2>Clip và vai trò</h2><table><tr><th>Clip gốc</th><th>Frame decode</th><th>Vai trò</th><th>Xem ba mốc</th></tr>')
    for c in manifest['clips']:
        name=c['sequence'];role=roles[groups[name]['assignment']]
        parts.append(f"<tr><td><a href='{link(ROOT/c['source_video'])}'>{html.escape(name)}</a></td><td>{c['decoded_frames']}</td><td>{role}</td><td><a href='scenes/{name}.jpg'>Đầu/giữa/cuối</a></td></tr>")
    parts.append('</table><p>Khác tên file và hash không chứng minh camera độc lập. Đã nhìn ba mốc mỗi clip, các cặp gần nhất với dữ liệu cũ, và giữ mỗi cảnh tạm trong một tập. FPS container chưa chứng minh timing camera.</p>')
    if (audit/'mined_train_examples.jpg').exists():
        parts.append('<details><summary>Mẫu train chọn theo score cũ</summary><p>Chỉ minh họa cách chọn frame train; không phải kết quả model mới hoặc nhãn do dự đoán sinh ra.</p><img src="mined_train_examples.jpg"></details>')
    for page_image in sorted(audit.glob('scene_page_*.jpg')):parts.append(f'<details><summary>{page_image.name}</summary><img src="{page_image.name}"></details>')
    parts.append('<details><summary>15 vùng GT train nhỏ nhất ở mức dưới 8 pixel sau resize640</summary><p>Phóng pixel gần nhất để kiểm tra, không tạo thêm dữ liệu train và không sửa nhãn tác giả.</p><img src="small_train_positive_crops.jpg"></details>')
    parts.append('<p>Kiểm đủ 1.320 bbox dương cũ: không có lỗi biên/kích thước; 152 bbox có cạnh ngắn sau resize640 dưới 16 pixel. Vùng mờ/nhỏ được giữ với cờ khó, không tự suy ra nhãn sai.</p>')
    parts.append(f'<h2>Chạy bước tiếp theo</h2><p>Kiểm trước:</p><pre><code>.\\.venv\\Scripts\\python.exe -X utf8 -B scripts/train_b0.py --config {html.escape(config_name)} --check</code></pre><p>Lệnh train do người dùng tự chạy:</p><pre><code>.\\.venv\\Scripts\\python.exe -X utf8 -B scripts/train_b0.py --config {html.escape(config_name)} --train</code></pre><p>Recipe nằm trong config đã khóa; chỉ đánh giá val sau train, không dùng test cũ hoặc reserve chọn tham số.</p></html>')
    body='\n'.join(parts)
    if completed:
        body=body.replace('<h2>Chạy bước tiếp theo</h2>','<h2>Lệnh đã dùng cho run</h2>').replace(
            'Lệnh train do người dùng chạy khi sẵn sàng:','Lệnh train đã dùng:')
    page=audit/'index.html';page.write_text(body,encoding='utf-8')
    return page


def build_verified(output: Path) -> None:
    """Khóa release mới chỉ dùng âm có review hoặc nhãn normal công khai."""
    original=ROOT/"data/processed/b0_accident_scaled_v1"
    review_path=ROOT/"data/reviews/2026-10-27-b0-near-duplicate-review.json"
    review=json.loads(review_path.read_text(encoding="utf-8"))
    if sha256_file(original/"dataset/provenance.csv")!=review["input_provenance_sha256"]:
        raise ValueError("Original provenance differs from duplicate review")
    excluded={r["group"] for r in review["excluded_test_groups"]}
    readiness=json.loads(READY.read_text(encoding="utf-8"))
    prior=readiness["expanded_pilot_release"]
    manifest=ROOT/prior["export_asset_manifest"]
    if sha256_file(manifest)!=prior["export_asset_manifest_sha256"]:
        raise ValueError("Original asset fingerprint manifest changed")
    old_hashes=json.loads(manifest.read_text(encoding="utf-8"))
    original_rows=csv_rows(original/"index.csv")
    assignments={(x["source_dataset"],x["source_sequence"],int(x["source_frame"])):x["split"]
                 for x in csv_rows(original/"split.csv")}
    rows=[];splits=[]
    def add(row: dict, split: str) -> None:
        rows.append(row)
        splits.append(dict(source_dataset=row["source_dataset"],source_sequence=row["source_sequence"],
                           source_frame=row["source_frame"],split=split))
    for row in original_rows:
        key=(row["source_dataset"],row["source_sequence"],int(row["source_frame"]))
        split=assignments[key]
        if row["label_origin"]=="derived_author_first_visible_contact_candidate":
            continue
        if split=="test" and row["leakage_group"] in excluded:
            continue
        for name in (row["source_path"],row["label_evidence"],row["converted_label"]):
            if name and old_hashes.get(name)!=sha256_file(ROOT/name):
                raise ValueError(f"Previously audited asset changed: {name}")
        add(row,split)
    pool=csv_rows(ROOT/"data/processed/b0_public_pilot_v3/index.csv")
    groups={}
    for row in pool:
        if row["collision_label"]=="negative" and row["source_dataset"] in ("UA-DETRAC","TAD"):
            groups.setdefault((row["source_dataset"],row["source_sequence"]),[]).append(row)
    detrac={ (r["source_sequence"],int(r["source_frame"])):r for r in csv_rows(ROOT/"data/processed/b0_reviewed_negatives/frames.csv") }
    user_review=json.loads((ROOT/"data/reviews/2026-10-19-user-confirmations.json").read_text(encoding="utf-8"))
    user_hashes={r["video_id"]:r["sha256"] for r in user_review["statements"]}
    source_review=json.loads((ROOT/"data/reviews/2026-10-24-pilot-source-review.json").read_text(encoding="utf-8"))
    tad={r["sequence"]:r for r in source_review["normal_clips"]}
    selected_counts={}
    for (dataset,sequence),items in sorted(groups.items()):
        items.sort(key=lambda r:int(r["source_frame"]))
        count=min(len(items),100 if dataset=="UA-DETRAC" else 50)
        indexes=[round(i*(len(items)-1)/(count-1)) for i in range(count)] if count>1 else [0]
        if len(set(indexes))!=count:
            raise ValueError("Nonunique uniform frame selection")
        if dataset=="TAD":
            clip=tad[sequence]
            if clip["annotation_origin"]!="author_normal_folder_clip_label" or sha256_file(ROOT/clip["path"])!=clip["sha256"]:
                raise ValueError(f"TAD source/review changed: {sequence}")
        for i in indexes:
            row=items[i]
            if dataset=="UA-DETRAC":
                record=detrac[(sequence,int(row["source_frame"]))]
                if row["label_origin"]!="user_full_sequence_review" or record["source_image"]!=row["source_path"]:
                    raise ValueError("DETRAC review/source mismatch")
                if sha256_file(ROOT/row["source_path"])!=record["image_sha256"]:
                    raise ValueError("DETRAC image differs from reviewed index")
                if user_hashes.get("UA_DETRAC_"+sequence)!=record["parent_video_sha256"]:
                    raise ValueError("DETRAC user review does not match parent video")
                if sha256_file(ROOT/record["parent_video"])!=record["parent_video_sha256"]:
                    raise ValueError("DETRAC parent video changed")
            elif row["label_origin"]!="author_normal_folder_clip_label":
                raise ValueError("TAD frame has no author normal-clip label")
            add(row,"train")
        selected_counts[dataset+":"+sequence]=count
    plan=export_plan(rows,splits)
    if any(r["label_origin"]=="derived_author_first_visible_contact_candidate" for r in plan):
        raise ValueError("Unreviewed derived negatives prohibited")
    if len({(r["source_dataset"],r["source_sequence"],int(r["source_frame"])) for r in rows})!=len(rows):
        raise ValueError("Duplicate source frame")
    output.mkdir(parents=True)
    index=output/"index.csv";split_path=output/"split.csv"
    save_csv(index,rows,list(rows[0]));save_csv(split_path,splits,list(splits[0]))
    counts={s:dict(Counter(r["collision_label"] for r in plan if r["split"]==s)) for s in ("train","val","test")}
    report=dict(scope="verified-negative basic image pilot",samples=len(rows),split_labels=counts,
                label_origins=dict(Counter(r["label_origin"] for r in rows)),
                added_negative_samples=selected_counts,excluded_test_groups=sorted(excluded),
                no_unreviewed_preimpact_candidates=True,
                caveats=["Added 400 negatives come from only five clips and three conservative source groups",
                         "Negative domain differs from ACCIDENT positives; camera/source shortcut is possible",
                         "Test includes only five reviewed negatives; near-duplicate search is not exhaustive"])
    save_json(output/"split_report.json",report)
    assets={name for r in rows for name in (r["source_path"],r["label_evidence"],r["converted_label"]) if name}
    hashes={name:sha256_file(ROOT/name) for name in sorted(assets)}
    asset_manifest=output/"asset_hashes.json";save_json(asset_manifest,hashes)
    if "verified_pilot_release" in readiness:
        raise ValueError("Verified pilot release already exists")
    backup=output_path(ROOT,'data_audit','v015_verified_release_readiness',child='readiness_before_verified_release.json')
    if backup.exists():
        raise FileExistsError("Readiness backup already exists")
    backup.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(READY,backup)
    readiness["verified_pilot_release"]=dict(can_train=True,split_created=True,scope="verified_negative_image_pilot",
        decision="Author impact boxes, individually reviewed ACCIDENT negative frames, user-reviewed DETRAC and author normal TAD; no unreviewed weak labels",
        pool=index.relative_to(ROOT).as_posix(),split_manifest=split_path.relative_to(ROOT).as_posix(),
        split_report=(output/"split_report.json").relative_to(ROOT).as_posix(),
        export_pool_sha256=sha256_file(index),export_split_sha256=sha256_file(split_path),
        export_policy_sha256=sha256_file(VERIFIED_POLICY),
        export_asset_manifest=asset_manifest.relative_to(ROOT).as_posix(),export_asset_manifest_sha256=sha256_file(asset_manifest),
        initial_weights_sha256=sha256_file(ROOT/"yolov8n.pt"))
    READY.write_text(json.dumps(readiness,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False),flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Khóa release B0 ảnh với bbox tác giả và âm đã xác minh")
    parser.add_argument("--output", type=Path, default=OUT)
    parser.add_argument("--verified",action="store_true",help="Tạo release chỉ dùng âm đã rà hoặc normal tác giả; loại nhóm test trùng")
    parser.add_argument('--normal-expansion-review',type=Path,help='Review nhóm normal mới để mở rộng release verified hiện có')
    parser.add_argument('--mine-normal-groups',type=Path,help='Chọn frame âm khó sau khi đã khóa nhóm train/val/reserve')
    args = parser.parse_args()
    if args.mine_normal_groups:
        print(mine_assigned_normal(args.mine_normal_groups));return 0
    if args.normal_expansion_review:
        if args.verified:parser.error('Choose one release mode')
        output=(ROOT/'data/processed/b0_normal_expanded_v1') if args.output==OUT else (ROOT/args.output).resolve()
        if not output.resolve().is_relative_to(ROOT) or output.exists():parser.error('New output inside project required')
        build_normal_expansion(args.normal_expansion_review,output)
        return 0
    output = (ROOT / args.output).resolve()
    if not output.is_relative_to(ROOT) or output.exists():
        if not (args.verified and output==OUT.resolve()):
            parser.error("Output must be a new directory inside project")
    if args.verified:
        output=VERIFIED_OUT.resolve() if output==OUT.resolve() else output
        if output.exists():
            parser.error("Verified output must be a new directory")
        if not VERIFIED_POLICY.is_file():
            parser.error("Missing verified-negative policy")
        build_verified(output)
        return 0
    parser.error("Legacy weak-negative release is withdrawn; use --verified")

if __name__ == "__main__":
    raise SystemExit(main())
