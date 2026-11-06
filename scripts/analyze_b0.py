"""Phân tích lỗi B0 đã đo và chạy lại theo từng frame video sạch.

Đầu vào: config khóa checkpoint, report cũ, video/ảnh và căn cứ nhãn.
Đầu ra: một thư mục diagnostics trong run hiện hành, có HTML, CSV/JSON,
MP4 dự đoán và kiểm đọc lại. Chạy sau train bằng --check rồi --run;
không train, đổi ngưỡng, tải dataset hoặc tạo nhãn cho frame chưa biết.
Chế độ --validation-reference dùng config train mới để đo các checkpoint
cũ trên cùng split val; test và reserve âm không đi qua suy luận ở chế độ đó.
--saved-validation phân tích prediction val đã lưu, không nạp model suy luận.
--select-operating-point quét confidence trên val rồi ghi khóa sử dụng;
--evaluate-operating-holdout chỉ đo một lần tập âm bằng khóa đã chốt.
--temporal-diagnostics so B0/EMA/k-of-N trên cùng frame video sạch; không
train, không tối ưu lại tham số theo holdout đã xem và không suy timing CADP.
"""
from __future__ import annotations

import argparse
from collections import Counter
import html
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.b0_diagnostics import classify_case, object_size_summary, resized_size_counts, temporal_summary, confidence_metrics, choose_confidence, require_unseen_negative_holdout, CausalScoreFilter, filter_state_summary
from src.data_preparation import H264Writer, probe_video, save_csv, save_json, sha256_file
from scripts.train_b0 import check_inputs, evaluate_frames, read_csv, workspace
from src.storage_paths import require_output_path


def validation_references(config_path: Path) -> Path:
    """Đo các checkpoint mốc trên cùng validation mới trước lần train dữ liệu.

    Chỉ đọc split val; test cũ và reserve âm mới không được suy luận ở đây.
    Đây là mốc so sánh trước train, không phải kết quả model mở rộng đã học.
    """
    config=json.loads(config_path.read_text(encoding='utf-8'))
    if config.get('evaluation_splits')!=['val']:
        raise ValueError('Validation reference requires validation-only experiment')
    dataset,rows=check_inputs(config)
    output=workspace(config['reference_validation_output'])
    if output.exists() and any(p.is_file() for p in output.rglob('*')):
        raise FileExistsError('Validation reference output already contains results')
    sources=[]
    for record in config['reference_experiments']:
        experiment_path=verify_file(record['path'],record['sha256'])
        experiment=json.loads(experiment_path.read_text(encoding='utf-8'))
        verify_file(experiment['checkpoint'],experiment['checkpoint_sha256'])
        for key in ('imgsz','prediction_confidence','matching_iou','ultralytics_version'):
            if experiment['config'][key]!=config[key]:raise ValueError('Reference inference settings differ')
        sources.append((experiment_path,experiment))
    os.environ['YOLO_CONFIG_DIR']=str(ROOT/'.tmp/ultralytics')
    os.environ['MPLCONFIGDIR']=str(ROOT/'.tmp/matplotlib')
    os.environ['YOLO_OFFLINE']='true';os.environ['YOLO_AUTOINSTALL']='false'
    import ultralytics
    from ultralytics import YOLO
    if ultralytics.__version__!=config['ultralytics_version']:raise ValueError('Ultralytics version differs')
    output.mkdir(parents=True,exist_ok=True)
    measured=[]
    for experiment_path,experiment in sources:
        target=output/experiment_path.parent.name;target.mkdir(exist_ok=True)
        model=YOLO(str(workspace(experiment['checkpoint'])))
        if model.names!={0:'accident'}:raise ValueError('Reference checkpoint is not B0 accident')
        metrics=model.val(data=str(dataset),split='val',device=config['device'],imgsz=config['imgsz'],
                          batch=config['batch'],workers=0,plots=True,project=str(target),name='ultralytics',exist_ok=True)
        manual=evaluate_frames(model,rows,dataset,'val',config,target/'cases')
        result=dict(reference_experiment=experiment_path.relative_to(ROOT).as_posix(),
            checkpoint=experiment['checkpoint'],checkpoint_sha256=experiment['checkpoint_sha256'],
            split='val',images=sum(r['split']=='val' for r in rows),
            official_bbox_metrics={k:float(v) for k,v in metrics.results_dict.items()},fixed_threshold_metrics=manual,
            provenance_sha256=sha256_file(dataset.parent/'provenance.csv'))
        save_json(target/'report.json',result);measured.append(result)
        print(f'Validation reference completed: {experiment_path.parent.name}',flush=True)
    save_json(output/'report.json',dict(status='complete',config=config_path.relative_to(ROOT).as_posix(),
        config_sha256=sha256_file(config_path),results=measured,test_inference=False,
        reserved_negative_holdout_inference=False,new_model_trained=False,
        scope='baseline measurements on enlarged validation only; not a new independent test result'))
    return output


def verify_file(path: str, digest: str) -> Path:
    """File nguồn phải đúng fingerprint; không tự cập nhật hash khi khác."""
    result = workspace(path)
    if sha256_file(result) != digest:
        raise ValueError(f'Fingerprint differs: {path}')
    return result


def prediction_cache(model, config: dict, rows: list[dict], dataset: Path) -> list[dict]:
    """Đọc đúng val, cache score thấp một lần rồi quét ngưỡng mà không chạy lại YOLO."""
    import cv2
    import numpy as np
    if any(r['split']!='val' for r in rows):raise ValueError('Threshold selection is validation-only')
    cases=[]
    for index,row in enumerate(rows):
        frame=cv2.imdecode(np.frombuffer((dataset.parent/row['export_image']).read_bytes(),np.uint8),1)
        if frame is None:raise ValueError('Cannot decode validation image')
        height,width=frame.shape[:2];gt=[]
        for line in (dataset.parent/row['export_label']).read_text().splitlines():
            cls,cx,cy,bw,bh=map(float,line.split())
            if cls!=0:raise ValueError('Not an accident bbox')
            gt.append([(cx-bw/2)*width,(cy-bh/2)*height,(cx+bw/2)*width,(cy+bh/2)*height])
        result=model.predict(frame,imgsz=config['imgsz'],device=config['device'],
                             conf=.01,iou=.7,max_det=100,verbose=False,save=False)[0]
        predictions=[dict(xyxy=b,confidence=s) for b,s in zip(result.boxes.xyxy.cpu().tolist(),result.boxes.conf.cpu().tolist())]
        cases.append(dict(source_sequence=row['source_sequence'],source_frame=int(row['source_frame']),
            leakage_group=row['leakage_group'],collision_label=row['collision_label'],
            gt_xyxy=gt,predictions=predictions))
        if (index+1)%50==0:print(f'Cached validation {index+1}/{len(rows)}',flush=True)
    return cases


def select_operating_point(config_path: Path) -> Path:
    """Chốt confidence chỉ từ validation; ghi khóa trước khi mở holdout âm.

    Quy tắc được ghi ra trước prediction: recall >=0,70, sau đó F1 lớn nhất.
    Cùng quy tắc cho n640 đối chứng; không thay model/IoU/nhãn để đạt ngưỡng.
    Đây là hiệu chỉnh điểm vận hành, không train hay tính lại mAP.
    """
    config=json.loads(config_path.read_text(encoding='utf-8'))
    if config.get('evaluation_splits')!=['val']:raise ValueError('Need validation-only training config')
    dataset,rows=check_inputs(config)
    rows=[r for r in rows if r['split']=='val']
    run=workspace(config['output']);current_path=run/'experiment.json'
    current=json.loads(current_path.read_text(encoding='utf-8'))
    if sha256_file(config_path)!=current['config_sha256']:raise ValueError('Source config changed')
    reference_path=workspace(config['reference_experiment'])
    reference=json.loads(reference_path.read_text(encoding='utf-8'))
    if reference['provenance_sha256']!=current['provenance_sha256']:raise ValueError('Reference uses different data')
    for experiment in (current,reference):verify_file(experiment['checkpoint'],experiment['checkpoint_sha256'])
    holdout_path=ROOT/'data/registries/b0_normal_expanded_v1_holdout.json'
    holdout=json.loads(holdout_path.read_text(encoding='utf-8'))
    require_unseen_negative_holdout(holdout)
    if {r['source_sequence'] for r in rows}&{r['source_sequence'] for r in holdout['samples']}:
        raise ValueError('Holdout source appears in validation')
    output=run/'operating_point_v1'
    locked_path=ROOT/'configs'/f'{run.name}_operating_point_v1.json'
    if output.exists() or locked_path.exists():raise FileExistsError('Preserve previous threshold selection')
    output.mkdir()
    from datetime import datetime,timezone,timedelta
    report_date=datetime.now(timezone(timedelta(hours=7))).date().isoformat()
    policy=dict(date=report_date,selection_split='val',minimum_recall=.70,
        thresholds=[round(i/100,2) for i in range(5,96)],cache_min_confidence=.01,
        matching_iou=.5,nms_iou=.7,max_det=100,
        objective='maximize bbox F1 subject to recall>=0.70; ties: fewer negative frames hit, higher precision, higher confidence',
        sources=['https://scikit-learn.org/stable/modules/classification_threshold.html',
                 'https://docs.ultralytics.com/guides/yolo-performance-metrics/',
                 'https://docs.ultralytics.com/modes/predict/'],
        adaptation='Apply validation-only threshold tuning to bbox matching, not sklearn classification probabilities; recall floor/grid/ties are project choices fixed before this sweep.')
    save_json(output/'policy_before_selection.json',policy)
    os.environ['YOLO_CONFIG_DIR']=str(ROOT/'.tmp/ultralytics');os.environ['MPLCONFIGDIR']=str(ROOT/'.tmp/matplotlib')
    os.environ['YOLO_OFFLINE']='true';os.environ['YOLO_AUTOINSTALL']='false'
    import ultralytics
    from ultralytics import YOLO
    if ultralytics.__version__!=config['ultralytics_version']:raise ValueError('Ultralytics version differs')
    results=[];sweeps=[]
    for name,experiment,path in [('s960',current,current_path),('n640',reference,reference_path)]:
        model=YOLO(str(workspace(experiment['checkpoint'])))
        if model.names!={0:'accident'}:raise ValueError('Not an accident checkpoint')
        cases=prediction_cache(model,experiment['config'],rows,dataset)
        parity=confidence_metrics(cases,.25,.5)
        for key in ('tp','fp','fn','negative_frames_with_predictions'):
            if parity[key]!=experiment['fixed_threshold_metrics']['val'][key]:
                raise ValueError(f'Cached inference disagrees with saved .25 metrics: {name}/{key}')
        save_json(output/f'{name}_validation_predictions.json',dict(cache_min_confidence=.01,cases=cases,
            checkpoint_sha256=experiment['checkpoint_sha256'],provenance_sha256=current['provenance_sha256']))
        sweep=[confidence_metrics(cases,t,.5) for t in policy['thresholds']]
        save_csv(output/f'{name}_thresholds.csv',sweep,list(sweep[0]))
        try:selected=choose_confidence(sweep,.70)
        except ValueError:selected=None
        if name=='s960' and selected is None:raise ValueError('S960 cannot meet prespecified recall floor')
        results.append(dict(model=name,experiment=path.relative_to(ROOT).as_posix(),
            experiment_sha256=sha256_file(path),checkpoint=experiment['checkpoint'],checkpoint_sha256=experiment['checkpoint_sha256'],
            imgsz=experiment['config']['imgsz'],at_original_confidence=parity,selected=selected,
            unconstrained_max_f1=choose_confidence(sweep,0)))
        sweeps.append((name,sweep,selected))
        del model
    report=dict(status='complete',policy=policy,validation_images=len(rows),
        validation_positive_boxes=sum(int(r['accident_bbox_count']) for r in rows),
        dataset_yaml_sha256=sha256_file(dataset),provenance_sha256=current['provenance_sha256'],models=results,
        negative_holdout_before_sha256=sha256_file(holdout_path),negative_holdout_inference=False,
        legacy_test_inference=False,model_training=False,map_recomputed=False,
        limitation='Reused validation; source groups provisional. Threshold changes the operating point, not model weights or previously reported mAP.')
    save_json(output/'selection.json',report)
    selected=results[0]['selected']
    locked=dict(status='locked_on_validation_before_holdout',date=report_date,
        checkpoint=current['checkpoint'],checkpoint_sha256=current['checkpoint_sha256'],
        training_config=config_path.relative_to(ROOT).as_posix(),training_config_sha256=current['config_sha256'],
        selection_report=(output/'selection.json').relative_to(ROOT).as_posix(),selection_report_sha256=sha256_file(output/'selection.json'),
        policy_sha256=sha256_file(output/'policy_before_selection.json'),
        prediction_confidence=selected['confidence'],imgsz=config['imgsz'],device=config['device'],
        matching_iou=.5,nms_iou=.7,max_det=100,ultralytics_version=config['ultralytics_version'],
        minimum_validation_recall=.70,selected_validation_metrics=selected,
        negative_holdout_manifest=holdout_path.relative_to(ROOT).as_posix(),negative_holdout_before_sha256=sha256_file(holdout_path),
        output=output.relative_to(ROOT).as_posix(),scope='image B0 operating point, not a confirmed accident/event alert')
    save_json(locked_path,locked)
    # Một hình đủ hai góc nhìn: F1 theo confidence và đường P/R theo cùng grid.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    for name,sweep,point in sweeps:
        axes[0].plot([p['confidence'] for p in sweep],[p['f1'] for p in sweep],label=name)
        axes[1].plot([p['recall'] for p in sweep],[p['precision'] for p in sweep],label=name)
        if point:
            axes[0].scatter([point['confidence']],[point['f1']])
            axes[1].scatter([point['recall']],[point['precision']])
    axes[0].set(xlabel='Confidence',ylabel='BBox F1',title='Validation confidence sweep')
    axes[1].set(xlabel='BBox recall',ylabel='BBox precision',title='Validation operating points (IoU .50)')
    axes[1].axvline(.70,color='grey',linestyle='--',label='Recall floor .70')
    for ax in axes:ax.set_xlim(0,1);ax.set_ylim(0,1);ax.grid(alpha=.25);ax.legend()
    fig.tight_layout();fig.savefig(output/'validation_curves.png',dpi=150);plt.close(fig)
    print(json.dumps(dict(locked_config=locked_path.relative_to(ROOT).as_posix(),models=results),ensure_ascii=False,indent=2))
    return locked_path


def evaluate_operating_holdout(config_path: Path) -> Path:
    """Đo một lần holdout âm bằng khóa sẵn; tuyệt đối không quét lại ngưỡng.

    Chỉ có nhãn normal cấp clip và frame lấy thưa: báo ảnh có hộp/nhóm, không
    tính recall/F1/mAP tai nạn hoặc suy ra false alerts/hour. Đánh dấu mở ngay
    trước inference, kể cả lỗi cũng không coi holdout vẫn còn nguyên để tune.
    """
    import cv2
    import numpy as np
    from datetime import datetime,timezone,timedelta
    config=json.loads(config_path.read_text(encoding='utf-8'))
    if config['status']!='locked_on_validation_before_holdout':raise ValueError('Need locked operating point')
    verify_file(config['selection_report'],config['selection_report_sha256'])
    verify_file(config['training_config'],config['training_config_sha256'])
    checkpoint=verify_file(config['checkpoint'],config['checkpoint_sha256'])
    source=json.loads(workspace(config['training_config']).read_text(encoding='utf-8'))
    _,training_rows=check_inputs(source)
    manifest_path=workspace(config['negative_holdout_manifest'])
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'));require_unseen_negative_holdout(manifest)
    verify_file(config['negative_holdout_manifest'],config['negative_holdout_before_sha256'])
    samples=manifest['samples']
    if len(samples)!=120 or len({s['source_sequence'] for s in samples})!=4:raise ValueError('Unexpected holdout inventory')
    if {s['source_sequence'] for s in samples}&{r['source_sequence'] for r in training_rows}:
        raise ValueError('Holdout source found in existing dataset')
    for sample in samples:
        verify_file(sample['image'],sample['image_sha256'])
        label=verify_file(sample['label'],sample['label_sha256'])
        if label.read_text().strip() or sample['label_origin']!='author_normal_folder_clip_label':
            raise ValueError('Need author-normal empty bbox label')
    output=workspace(config['output'])
    if (output/'holdout_report.json').exists() or (output/'holdout_manifest_before_evaluation.json').exists():
        raise FileExistsError('Holdout was already opened; preserve previous evaluation')
    os.environ['YOLO_CONFIG_DIR']=str(ROOT/'.tmp/ultralytics');os.environ['YOLO_OFFLINE']='true';os.environ['YOLO_AUTOINSTALL']='false'
    import ultralytics
    from ultralytics import YOLO
    if ultralytics.__version__!=config['ultralytics_version']:raise ValueError('Ultralytics version differs')
    model=YOLO(str(checkpoint))
    if model.names!={0:'accident'}:raise ValueError('Not an accident checkpoint')
    (output/'holdout_manifest_before_evaluation.json').write_bytes(manifest_path.read_bytes())
    def update_manifest():
        pending=manifest_path.with_suffix('.json.tmp')
        pending.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');pending.replace(manifest_path)
    manifest['evaluation_status']='started'
    manifest['evaluation_started_at']=datetime.now(timezone(timedelta(hours=7))).isoformat()
    manifest['operating_point_config']=config_path.relative_to(ROOT).as_posix()
    manifest['operating_point_config_sha256']=sha256_file(config_path)
    update_manifest()
    cases=[];groups={}
    try:
        for sample in samples:
            image=cv2.imdecode(np.frombuffer(workspace(sample['image']).read_bytes(),np.uint8),1)
            if image is None:raise ValueError('Cannot decode holdout image')
            result=model.predict(image,imgsz=config['imgsz'],device=config['device'],
                conf=config['prediction_confidence'],iou=config['nms_iou'],max_det=config['max_det'],verbose=False,save=False)[0]
            if not manifest['model_predictions_seen']:
                manifest['model_predictions_seen']=True;update_manifest()
            predictions=[dict(xyxy=b,confidence=s) for b,s in zip(result.boxes.xyxy.cpu().tolist(),result.boxes.conf.cpu().tolist())]
            cases.append(dict(source_sequence=sample['source_sequence'],source_frame=sample['source_frame'],image=sample['image'],
                              image_sha256=sample['image_sha256'],prediction_count=len(predictions),predictions=predictions))
            g=groups.setdefault(sample['source_sequence'],dict(frames=0,frames_with_predictions=0,predicted_boxes=0))
            g['frames']+=1;g['frames_with_predictions']+=bool(predictions);g['predicted_boxes']+=len(predictions)
        save_json(output/'holdout_predictions.json',cases)
        rows=[{k:r[k] for k in ('source_sequence','source_frame','image','prediction_count')} for r in cases]
        save_csv(output/'holdout_cases.csv',rows,list(rows[0]))
        hits=sum(bool(r['prediction_count']) for r in cases)
        report=dict(status='complete',scope='one-time sparse negative-only holdout; not full event/camera benchmark',
            locked_config=config_path.relative_to(ROOT).as_posix(),locked_config_sha256=sha256_file(config_path),
            checkpoint_sha256=config['checkpoint_sha256'],confidence=config['prediction_confidence'],
            images=len(cases),groups=groups,frames_with_predictions=hits,
            negative_frame_prediction_fraction=hits/len(cases),predicted_boxes=sum(r['prediction_count'] for r in cases),
            groups_with_any_predicted_sample=sum(bool(g['frames_with_predictions']) for g in groups.values()),
            recall=None,f1=None,map=None,false_alerts_per_hour=None,
            author_label='normal folder clip label; user review remains false',
            source_fps_verified=False,camera_independence_verified=False,
            original_manifest_sha256=config['negative_holdout_before_sha256'],selection_config_modified=False,
            full_B0_complete=False,temporal_event_evaluation=False)
        save_json(output/'holdout_report.json',report)
        manifest['evaluation_status']='complete'
        manifest['evaluation_report']=(output/'holdout_report.json').relative_to(ROOT).as_posix()
        manifest['evaluation_report_sha256']=sha256_file(output/'holdout_report.json');update_manifest()
        print(json.dumps(report,ensure_ascii=False,indent=2))
    except Exception as error:
        manifest['evaluation_status']='failed_consumed_not_for_tuning';update_manifest()
        save_json(output/'holdout_failure.json',dict(error=repr(error),do_not_retune_on_holdout=True))
        raise
    write_operating_page(config_path)
    return output/'holdout_report.json'


def write_operating_page(config_path: Path) -> Path:
    """Vẽ ảnh lỗi và trang đọc kết quả từ cache; không suy luận lại holdout."""
    import cv2
    import numpy as np
    config=json.loads(config_path.read_text(encoding='utf-8'))
    output=workspace(config['output'])
    selection=json.loads((output/'selection.json').read_text(encoding='utf-8'))
    holdout=json.loads((output/'holdout_report.json').read_text(encoding='utf-8'))
    cases=json.loads((output/'holdout_predictions.json').read_text(encoding='utf-8'))
    examples=[]
    for sequence in sorted({r['source_sequence'] for r in cases}):
        examples.extend(sorted((r for r in cases if r['source_sequence']==sequence and r['predictions']),
                        key=lambda r:max(p['confidence'] for p in r['predictions']),reverse=True)[:3])
    if examples:
        canvas=np.full((4*245,3*360,3),25,np.uint8)
        for index,case in enumerate(examples[:12]):
            frame=cv2.imdecode(np.frombuffer(workspace(case['image']).read_bytes(),np.uint8),1)
            for prediction in case['predictions']:
                x1,y1,x2,y2=map(round,prediction['xyxy'])
                cv2.rectangle(frame,(x1,y1),(x2,y2),(0,0,255),2)
                cv2.putText(frame,f"{prediction['confidence']:.2f}",(x1,max(y1-5,20)),cv2.FONT_HERSHEY_SIMPLEX,.6,(0,0,255),2)
            height,width=frame.shape[:2];ratio=min(356/width,207/height)
            frame=cv2.resize(frame,(round(width*ratio),round(height*ratio)))
            y,x=(index//3)*245,(index%3)*360
            canvas[y:y+frame.shape[0],x:x+frame.shape[1]]=frame
            cv2.putText(canvas,case['source_sequence'],(x+3,y+222),cv2.FONT_HERSHEY_SIMPLEX,.42,(255,255,255),1)
            cv2.putText(canvas,f"author normal | frame {case['source_frame']}",(x+3,y+239),cv2.FONT_HERSHEY_SIMPLEX,.42,(255,255,255),1)
        ok,body=cv2.imencode('.jpg',canvas)
        if not ok:raise ValueError('Cannot encode holdout error sheet')
        (output/'holdout_false_positives.jpg').write_bytes(body.tobytes())
    parts=['<!doctype html><html lang="vi"><meta charset="utf-8"><title>B0: ngưỡng và holdout âm</title>',
        '<style>body{font:16px system-ui;max-width:1150px;margin:30px auto;padding:0 20px;line-height:1.6}table{border-collapse:collapse;width:100%}td,th{padding:9px;border:1px solid #bbc}img{max-width:100%}</style>',
        '<h1>B0: chọn ngưỡng trên validation và kiểm holdout âm</h1>',
        '<p>Checkpoint và confidence đã khóa trước khi mở holdout. Không train, không thay mAP đã báo cáo. Cùng sàn recall 70%, recall thực tế hai model khác nhẹ do bước ngưỡng/số bbox rời rạc.</p>',
        '<table><tr><th>Model</th><th>Confidence</th><th>TP/FP/FN</th><th>P/R/F1</th><th>Ảnh âm có hộp /126</th></tr>']
    for model in selection['models']:
        p=model['selected']
        if p:
            parts.append(f"<tr><td>{model['model']}</td><td>{p['confidence']}</td><td>{p['tp']}/{p['fp']}/{p['fn']}</td><td>{p['precision']:.2%}/{p['recall']:.2%}/{p['f1']:.2%}</td><td>{p['negative_frames_with_predictions']}</td></tr>")
    parts.extend(['</table><p><a href="selection.json">Quy tắc và kết quả val</a> · <a href="s960_thresholds.csv">CSV ngưỡng s960</a> · <a href="n640_thresholds.csv">CSV ngưỡng n640</a></p>',
        '<img src="validation_curves.png"><h2>Holdout âm đã mở một lần</h2>',
        f"<p><b>{holdout['frames_with_predictions']}/{holdout['images']} ảnh có dự đoán ({holdout['negative_frame_prediction_fraction']:.2%}), tổng {holdout['predicted_boxes']} hộp.</b> Chỉ nhãn normal tác giả, chưa là xác nhận người dùng. Không có dương nên không báo recall/F1/mAP; frame lấy thưa, không suy ra cảnh báo/giờ hoặc kết quả toàn clip.</p>",
        '<table><tr><th>Chuỗi</th><th>Ảnh đã lấy</th><th>Ảnh có hộp</th><th>Tổng hộp</th></tr>'])
    for sequence,g in holdout['groups'].items():
        parts.append(f"<tr><td>{html.escape(sequence)}</td><td>{g['frames']}</td><td>{g['frames_with_predictions']}</td><td>{g['predicted_boxes']}</td></tr>")
    parts.append('</table><p><a href="holdout_report.json">Report holdout</a> · <a href="holdout_cases.csv">Từng frame</a> · <a href="holdout_predictions.json">BBox/score đã lưu</a></p>')
    if examples:parts.append('<h2>Một số dự đoán sai trên ảnh normal tác giả</h2><p>Hộp đỏ là dự đoán; ảnh gốc giữ riêng, không sửa nhãn theo prediction.</p><img src="holdout_false_positives.jpg">')
    parts.append('<p>Holdout đã được đánh dấu mở; không dùng để chọn lại ngưỡng hoặc gọi là test độc lập mới trong lần sau. Chỉ bốn nhóm, camera độc lập chưa chứng minh. B0 sự kiện chưa hoàn thành.</p></html>')
    path=output/'index.html';path.write_text('\n'.join(parts),encoding='utf-8')
    return path


def check_config(config: dict) -> list[dict]:
    """Kiểm release và nguồn nhãn trước khi nạp model hoặc tạo output."""
    training = json.loads(workspace(config['training_config']).read_text(encoding='utf-8'))
    _, rows = check_inputs(training)
    experiment = json.loads(verify_file(config['experiment'], config['experiment_sha256']).read_text(encoding='utf-8'))
    verify_file(experiment['checkpoint'], experiment['checkpoint_sha256'])
    operating=None
    if config.get('operating_point'):
        operating=json.loads(verify_file(config['operating_point'],config['operating_point_sha256']).read_text(encoding='utf-8'))
        if operating['checkpoint_sha256']!=experiment['checkpoint_sha256']:raise ValueError('Operating checkpoint differs')
    for key in ('imgsz', 'prediction_confidence', 'matching_iou', 'ultralytics_version'):
        if config[key] != (operating[key] if operating else training[key]):
            raise ValueError(f'Diagnostic changes locked parameter: {key}')
    for record in config['evidence_files']:
        verify_file(record['path'], record['sha256'])
    normal = json.loads(workspace(config['normal_manifest']).read_text(encoding='utf-8'))
    normal_clips = {c['sequence']:c for c in normal['clips']}
    reviews = json.loads(workspace(config['detrac_review']).read_text(encoding='utf-8'))['statements']
    cadp = json.loads(workspace(config['cadp_review']).read_text(encoding='utf-8'))
    if sha256_file(workspace(cadp['annotation_path'])) != cadp['annotation_sha256']:
        raise ValueError('CADP annotations no longer match user review')
    for spec in config['sequences']:
        if spec['label_origin'] == 'author_normal_folder_clip_label':
            clip = normal_clips[spec['sequence']]
            if clip['source_video'] != spec['path'] or clip['video_sha256'] != spec['sha256'] or spec['source_fps_verified'] != clip['source_fps_verified']:
                raise ValueError('TAD video differs from author-normal manifest')
            if [spec['frames'],spec['width'],spec['height']] != [clip['decoded_frames'],clip['width'],clip['height']]:
                raise ValueError('TAD dimensions or frame count differs from manifest')
        elif spec['label_origin'] == 'user_full_sequence_review':
            matches = [r for r in reviews if r.get('video_id') == 'UA_DETRAC_'+spec['sequence']]
            if len(matches)!=1 or matches[0].get('scope')!='full_sequence' or matches[0].get('collision_label')!='negative' or matches[0]['sha256']!=spec['sha256']:
                raise ValueError('DETRAC video lacks matching full-sequence review')
        elif spec['label_origin'] == 'author_vatic_user_frame_review':
            if spec['sequence']!='CADP_001407' or spec['intervals']!=cadp['events'] or spec['source_fps_verified']:
                raise ValueError('CADP interval or timing differs from frame review')
        else:
            raise ValueError('Unrecognized diagnostic label origin')
        if spec['kind'] == 'images':
            entries = read_csv(verify_file(spec['images_index'], spec['index_sha256']))
            if [int(r['source_frame']) for r in entries] != list(range(spec['frames'])):
                raise ValueError('Non-contiguous source image index')
            for row in entries:
                verify_file(row['relative_path'], row['sha256'])
        else:
            verify_file(spec['path'], spec['sha256'])
        if spec['label'] not in ('reviewed_colliding_interval', 'negative'):
            raise ValueError('Missing explicit label scope')
    return rows


def relative_link(path: Path, root: Path) -> str:
    return Path(os.path.relpath(path, root)).as_posix()


def contact_sheet(cases: list[dict], target: Path, title: str) -> None:
    """Lưu tối đa 12 case đã xếp hạng; bảng CSV vẫn giữ toàn bộ lỗi."""
    import cv2
    import numpy as np
    canvas = np.full((3*235, 4*340, 3), 24, np.uint8)
    for index, case in enumerate(cases[:12]):
        frame = cv2.imdecode(np.frombuffer(workspace(case['example']).read_bytes(), np.uint8), 1)
        if frame is None:
            raise ValueError('Cannot read existing case preview')
        h, w = frame.shape[:2]
        scale = min(336/w, 200/h)
        frame = cv2.resize(frame, (round(w*scale), round(h*scale)))
        y, x = (index//4)*235, (index%4)*340
        canvas[y:y+frame.shape[0], x:x+frame.shape[1]] = frame
        text = f"#{index+1} {case['source_sequence'][:23]}"
        cv2.putText(canvas, text, (x+3,y+216), cv2.FONT_HERSHEY_SIMPLEX, .42, (255,255,255), 1)
        cv2.putText(canvas, title+f" {case['source_frame']}", (x+3,y+231), cv2.FONT_HERSHEY_SIMPLEX, .42, (255,255,255), 1)
    ok, data = cv2.imencode('.jpg', canvas)
    if not ok:
        raise ValueError('Cannot encode error contact sheet')
    target.write_bytes(data.tobytes())


def image_analysis(config: dict, rows: list[dict], output: Path) -> dict:
    """Dùng prediction đã lưu để phân tích lỗi; không suy luận lại test."""
    folder = output/'image_errors'
    folder.mkdir()
    dataset = workspace(json.loads(workspace(config['training_config']).read_text())['dataset']).parent
    samples = {(r['source_sequence'], int(r['source_frame'])): dataset/r['export_image'] for r in rows}
    normal = json.loads(workspace(config['normal_manifest']).read_text(encoding='utf-8')) if config.get('normal_manifest') else {'samples':[]}
    samples.update({(r['source_sequence'], int(r['source_frame'])): workspace(r['image']) for r in normal['samples']})
    import cv2
    import numpy as np
    all_cases = []
    detailed = []
    groups = {}
    for source in config['image_cases']:
        case_dir = workspace(source['path'])
        cases = read_csv(case_dir/'cases.csv')
        predictions = json.loads((case_dir/'predictions.json').read_text(encoding='utf-8'))
        predictions = {(p['source_sequence'], int(p['source_frame'])):p for p in predictions}
        totals = Counter()
        for case in cases:
            identity = (case['source_sequence'], int(case['source_frame']))
            detail = predictions[identity]
            frame = cv2.imdecode(np.frombuffer(samples[identity].read_bytes(), np.uint8), 1)
            if frame is None:
                raise ValueError('Cannot read evaluated clean image')
            h, w = frame.shape[:2]
            geometry = classify_case(detail, w, h, config['matching_iou'])
            totals.update(geometry['categories'])
            for key in ('tp','fp','fn'):
                if int(case[key]) != detail[key]:
                    raise ValueError('Saved CSV and JSON counts differ')
            record = dict(scope=source['scope'], source_sequence=identity[0], source_frame=identity[1],
                          tp=int(case['tp']), fp=int(case['fp']), fn=int(case['fn']),
                          example=(case_dir/case['example']).relative_to(ROOT).as_posix(),
                          max_confidence=max((p['confidence'] for p in detail['predictions']),default=0),
                          min_gt_area_fraction=min((o['image_area_fraction'] for o in geometry['objects']),default=1))
            all_cases.append(record)
            detailed.append(dict(**record, **geometry))
        groups[source['scope']] = dict(frames=len(cases), tp=sum(int(x['tp']) for x in cases),
                                       fp=sum(int(x['fp']) for x in cases), fn=sum(int(x['fn']) for x in cases),
                                       geometry_categories=dict(totals))
    # Xếp hạng có quy tắc cố định để dễ nhìn, không bỏ các case còn lại khỏi metric.
    fp = sorted((r for r in all_cases if r['fp']), key=lambda r:r['max_confidence'], reverse=True)
    fn = sorted((r for r in all_cases if r['fn']), key=lambda r:r['min_gt_area_fraction'])
    contact_sheet(fp, folder/'false_positives.jpg', 'FP frame')
    contact_sheet(fn, folder/'false_negatives.jpg', 'FN frame')
    normal_fp = sorted((r for r in fp if r['scope']=='external_normal_sparse_already_consumed'),
                       key=lambda r:r['max_confidence'],reverse=True)
    contact_sheet(normal_fp,folder/'normal_false_positives.jpg','normal FP frame')
    save_csv(folder/'cases.csv', all_cases, list(all_cases[0]))
    save_json(folder/'details.json', detailed)
    result = dict(groups=groups, top_false_positive_cases=fp[:12], top_false_negative_cases=fn[:12],
                  gt_size_statistics=object_size_summary(detailed),
                  gt_min_side_resized={str(size):resized_size_counts(detailed,size) for size in (640,960)},
                  size_projection_note='GT sizes projected to each image size; TP/FN retain the original saved prediction matches, not inference at the projected size.',
                  matching_iou=config['matching_iou'], confidence=config['prediction_confidence'],
                  classification='geometry only; content causes require visual inspection')
    save_json(folder/'report.json', result)
    return result


def media_timestamps(path: Path, frames: int) -> list[float]:
    """Lấy PTS container, giữ tách biệt với thời điểm camera ghi hình gốc."""
    result = subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries',
                             'frame=best_effort_timestamp_time','-of','json',str(path)],
                            capture_output=True, check=True, encoding='utf-8')
    values = [float(f['best_effort_timestamp_time']) for f in json.loads(result.stdout)['frames']]
    if len(values) != frames or any(b <= a for a,b in zip(values, values[1:])):
        raise ValueError('Invalid or incomplete media timestamps')
    return values


def video_analysis(model, config: dict, spec: dict, output: Path) -> dict:
    """Ảnh sạch → bbox accident → log frame → MP4, không dùng bbox GT đầu vào."""
    import cv2
    import numpy as np
    import torch
    target = output/'videos'/spec['sequence']
    target.mkdir(parents=True)
    capture = None
    if spec['kind'] == 'images':
        entries = read_csv(workspace(spec['images_index']))
        def frames():
            for entry in entries:
                image = cv2.imdecode(np.frombuffer(workspace(entry['relative_path']).read_bytes(),np.uint8),1)
                if image is None:
                    raise ValueError('Cannot decode clean source image')
                yield int(entry['source_frame']), image
        stream = frames()
        pts = [None]*spec['frames']
    else:
        pts = media_timestamps(workspace(spec['path']), spec['frames'])
        capture = cv2.VideoCapture(str(workspace(spec['path'])))
        if not capture.isOpened():
            capture.release()
            raise ValueError('Cannot open clean video')
        def frames():
            index = 0
            while True:
                ok, image = capture.read()
                if not ok:
                    break
                yield index, image
                index += 1
        stream = frames()
    records = []
    policy=config.get('temporal_policy')
    filter_state=CausalScoreFilter(config['prediction_confidence'],policy['k'],policy['n'],policy['ema_alpha']) if policy else None
    predictions_file = target/'predictions.jsonl'
    video = target/'b0_accident.mp4'
    torch.cuda.reset_peak_memory_stats() if config['device'] != 'cpu' else None
    started = time.perf_counter()
    try:
        with predictions_file.open('w',encoding='utf-8') as predictions, H264Writer(
                video,spec['width'],spec['height'],spec['display_fps']) as writer:
            for source_frame, frame in stream:
                if source_frame >= spec['frames'] or frame.shape[:2] != (spec['height'],spec['width']):
                    raise ValueError('Source frame count or dimensions changed')
                # Đồng bộ CUDA trước/sau để độ trễ không chỉ là thời gian gửi lệnh GPU.
                if config['device'] != 'cpu': torch.cuda.synchronize()
                before = time.perf_counter()
                result = model.predict(frame,device=config['device'],imgsz=config['imgsz'],
                                       conf=.01 if policy else config['prediction_confidence'],iou=.7,max_det=100,verbose=False)[0]
                if config['device'] != 'cpu': torch.cuda.synchronize()
                latency = (time.perf_counter()-before)*1000
                boxes = [dict(xyxy=box,confidence=score,class_id=0) for box,score in zip(
                    result.boxes.xyxy.cpu().tolist(),result.boxes.conf.cpu().tolist())]
                all_boxes=boxes
                boxes=[b for b in boxes if b['confidence']>config['prediction_confidence']]
                reviewed = any(e['start_frame'] <= source_frame <= e['end_frame_inclusive'] for e in spec.get('intervals',[]))
                record = dict(source_frame=source_frame,
                              original_source_frame=source_frame+spec.get('original_frame_offset',0),
                              media_timestamp_s=pts[source_frame],
                              source_timestamp_s=pts[source_frame] if spec['source_fps_verified'] else None,
                              prediction_count=len(boxes),max_confidence=max((b['confidence'] for b in all_boxes),default=0),
                              inference_wall_ms=latency,
                              temporal_label='negative' if spec['label']=='negative' else 'reviewed_colliding' if reviewed else 'unknown')
                if filter_state:record.update(filter_state.step(source_frame,record['max_confidence']))
                records.append(record)
                predictions.write(json.dumps(dict(**record,boxes=boxes),ensure_ascii=False)+'\n')
                drawn = result[result.boxes.conf>config['prediction_confidence']].plot()
                if filter_state:
                    cv2.putText(drawn,f"B0 {int(record['b0_on'])} | k-of-N {int(record['kofn_on'])} | EMA {int(record['ema_on'])}",
                                (10,80),cv2.FONT_HERSHEY_SIMPLEX,.6,(0,220,255),2)
                # Dòng đầu tách rõ dự đoán accident với nhãn tác giả/người dùng.
                cv2.putText(drawn, f"B0 prediction | frame {source_frame} | conf >= {config['prediction_confidence']}",
                            (10,25),cv2.FONT_HERSHEY_SIMPLEX,.65,(255,255,255),2)
                if spec['kind'] == 'images':
                    cv2.putText(drawn,'DISPLAY FPS ONLY | original camera FPS unknown',
                                (10,52),cv2.FONT_HERSHEY_SIMPLEX,.55,(0,220,255),2)
                writer.write(drawn)
                if (source_frame+1)%250 == 0:
                    print(f"{spec['sequence']}: {source_frame+1}/{spec['frames']}",flush=True)
        elapsed = time.perf_counter()-started
        if len(records) != spec['frames']:
            raise ValueError('Incomplete source decode; no valid sequence report')
    finally:
        if capture is not None: capture.release()
    # Đọc lại TẤT CẢ frame video đã xuất để bắt file ghi thiếu/không giải mã được.
    reread = probe_video(video)
    if reread['decoded_frames'] != len(records):
        raise ValueError('Output video frame count differs')
    summary = temporal_summary(records,spec.get('intervals',[]),spec['label']=='negative')
    if filter_state:
        filtered={}
        for name,field in [('B0','b0_on'),('B1_kofn','kofn_on'),('B1_EMA','ema_on')]:
            filtered[name]=filter_state_summary(records,field,spec.get('intervals',[]),spec['label']=='negative')
        summary['filter_comparison']=filtered
        summary['temporal_policy']=policy
    summary.update(sequence=spec['sequence'],role=spec['role'],label_origin=spec['label_origin'],
                   source_fps_verified=spec['source_fps_verified'],fps_scope=spec['fps_scope'],
                   source_spec=spec,output_video=video.relative_to(ROOT).as_posix(),output_validation=reread,
                   inference_median_ms=float(np.median([r['inference_wall_ms'] for r in records])),
                   inference_p95_ms=float(np.percentile([r['inference_wall_ms'] for r in records],95)),
                   pipeline_wall_seconds=elapsed,offline_pipeline_fps=len(records)/elapsed,
                   pipeline_scope='sequential decode+predict+plot+encode+encoder flush; excludes model load, warmup, hash and output reread',
                   peak_torch_allocated_bytes=torch.cuda.max_memory_allocated() if config['device']!='cpu' else None,
                   dropped_frames=0,metric_scope='B0 raw frame and consecutive-run diagnostic; not confirmed alerts or held-out event benchmark')
    save_csv(target/'frames.csv',records,list(records[0]))
    save_json(target/'report.json',summary)
    return summary


def write_page(output: Path, images: dict, videos: list[dict]) -> None:
    """Một trang mở được offline để người mới xem video, ảnh lỗi và bảng số liệu."""
    roles = {'training_source_operational_diagnostic':'Nguồn từng dùng train — kiểm vận hành',
             'previously_consumed_external_normal_probe':'Normal TAD tác giả — probe đã xem',
             'external_debug_temporal_presence_only':'CADP — debug theo khoảng frame'}
    normal = [v for v in videos if v['label_origin']=='author_normal_folder_clip_label']
    training = [v for v in videos if v['role']=='training_source_operational_diagnostic']
    intervals = [e for v in videos for e in v.get('reviewed_intervals',[])]
    parts = ['<!doctype html><html lang="vi"><meta charset="utf-8"><title>B0 diagnostics</title>',
             '<style>body{font:16px system-ui;max-width:1200px;margin:30px auto;padding:0 20px;background:#f5f7fa;color:#17283d}table{border-collapse:collapse;width:100%;background:white}td,th{padding:10px;border:1px solid #ccd5df;text-align:left}img{max-width:100%}video{width:100%;max-height:650px}a{color:#1559aa}details{background:white;padding:12px;margin:12px 0}p{line-height:1.6}</style>',
             '<h1>B0: lỗi ảnh và dự đoán video</h1>',
             '<p>Checkpoint hiện hành, confidence 0,25. Hộp trên video là dự đoán B0; không phải annotation tác giả. Đoạn frame có bbox liên tiếp chỉ là log thô, chưa phải cảnh báo sự kiện. Dữ liệu đã xem không dùng để chọn ngưỡng.</p>',
             f"<p><b>Kết quả chính:</b> {sum(v['frames_with_predictions'] for v in normal)}/{sum(v['frames'] for v in normal)} frame normal TAD có dự đoán. Các chuỗi kiểm vận hành từng dùng train có {sum(v['predicted_boxes'] for v in training)} bbox. CADP có bbox trong {sum(e['frames_with_any_bbox'] for e in intervals)}/{sum(e['reviewed_frames'] for e in intervals)} frame đã xác nhận Colliding, nhưng chưa kiểm IoU vùng accident vì không có GT vùng cùng định nghĩa.</p>",
             '<h2>Lỗi ảnh đã đo</h2><table><tr><th>Phạm vi</th><th>Ảnh</th><th>TP</th><th>FP</th><th>FN</th></tr>']
    for name, group in images['groups'].items():
        parts.append(f"<tr><td>{html.escape(name)}</td><td>{group['frames']}</td><td>{group['tp']}</td><td>{group['fp']}</td><td>{group['fn']}</td></tr>")
    parts.append('</table><p>Ảnh lỗi: xanh là GT, đỏ là prediction. Bảng CSV giữ toàn bộ case.</p><a href="image_errors/cases.csv">CSV tất cả ảnh</a>')
    for kind, title in [('false_positives','Ảnh có FP, xếp theo confidence cao nhất trong ảnh'),('false_negatives','Ảnh có FN, xếp theo vùng GT nhỏ nhất trong ảnh')]:
        parts.append(f'<h3>{title}</h3><img src="image_errors/{kind}.jpg">')
    parts.append('<h3>Dự đoán sai trên normal TAD có nhãn tác giả</h3><img src="image_errors/normal_false_positives.jpg">')
    parts.append('<h2>Video đã đọc lại đủ frame</h2><table><tr><th>Chuỗi</th><th>Vai trò</th><th>Frame</th><th>Frame có bbox</th><th>Đoạn thô</th></tr>')
    for v in videos:
        name = html.escape(v['sequence'])
        parts.append(f"<tr><td><a href='#video-{name}'>{name}</a></td><td>{html.escape(roles.get(v['role'],v['role']))}</td><td>{v['frames']}</td><td>{v['frames_with_predictions']}</td><td>{len(v['raw_positive_runs'])}</td></tr>")
    parts.append('</table>')
    for v in videos:
        name = html.escape(v['sequence'])
        path = html.escape(relative_link(workspace(v['output_video']),output),quote=True)
        parts.append(f"<details id='video-{name}'><summary>{name} — mở video và log</summary><p>{html.escape(v['metric_scope'])}</p><video controls preload='none' src='{path}'></video><p><a href='videos/{name}/frames.csv'>CSV theo frame</a> · <a href='videos/{name}/report.json'>Report</a></p></details>")
    parts.append('<p>CADP: chỉ frame 96–130 có xác nhận Colliding, ngoài khoảng là unknown; video trình chiếu 20 FPS không xác nhận thời gian ghi hình. DETRAC: đã dùng để train. TAD: nhãn normal của tác giả, probe đã xem, chưa chứng minh camera độc lập.</p></html>')
    (output/'index.html').write_text('\n'.join(parts),encoding='utf-8')


def run_temporal_comparison(config_path: Path, config: dict) -> Path:
    """Chạy B0/B1 cùng cache frame, tham số đã chốt; không tune trên video.

    Nguồn val và nguồn đã consumed được báo riêng. CADP chỉ kiểm hiện diện
    trong96–130, không có GT vùng và timing nguồn nên không báo event recall.
    """
    output=workspace(config['output'])
    if output.exists():raise FileExistsError('Preserve temporal diagnostic run')
    os.environ['YOLO_CONFIG_DIR']=str(ROOT/'.tmp/ultralytics');os.environ['MPLCONFIGDIR']=str(ROOT/'.tmp/matplotlib')
    os.environ['YOLO_OFFLINE']='true';os.environ['YOLO_AUTOINSTALL']='false'
    import torch
    import ultralytics
    import numpy as np
    from ultralytics import YOLO
    if ultralytics.__version__!=config['ultralytics_version']:raise ValueError('Ultralytics version differs')
    experiment=json.loads(workspace(config['experiment']).read_text(encoding='utf-8'))
    model=YOLO(str(workspace(experiment['checkpoint'])))
    if model.names!={0:'accident'}:raise ValueError('Not accident model')
    output.mkdir();shutil.copy2(config_path,output/'requested_config.json')
    for _ in range(3):model.predict(np.zeros((config['imgsz'],config['imgsz'],3),np.uint8),device=config['device'],conf=.01,verbose=False)
    videos=[]
    for spec in config['sequences']:
        videos.append(video_analysis(model,config,spec,output))
        print(f"Temporal completed {spec['sequence']}",flush=True)
    aggregate={}
    for role in sorted({v['role'] for v in videos}):
        group=[v for v in videos if v['role']==role and v['source_spec']['label']=='negative']
        if not group:continue
        aggregate[role]={}
        for name in ('B0','B1_kofn','B1_EMA'):
            aggregate[role][name]=dict(frames=sum(v['frames'] for v in group),
                active_frames=sum(v['filter_comparison'][name]['active_frames'] for v in group),
                raw_on_bouts=sum(len(v['filter_comparison'][name]['raw_on_bouts']) for v in group))
    report=dict(status='complete',config_sha256=sha256_file(config_path),checkpoint_sha256=experiment['checkpoint_sha256'],
        temporal_policy=config['temporal_policy'],sequences=videos,negative_aggregate_by_role=aggregate,
        policy_tuned_on_videos=False,full_B1_complete=False,temporal_event_evaluation=False,
        note='Causal scene-state diagnostic, not confirmed event alerts. CADP interval presence only; source FPS unknown. Consumed holdout remains consumed, never train data.')
    save_json(output/'report.json',report)
    parts=['<!doctype html><html lang="vi"><meta charset="utf-8"><title>B0/B1 theo frame</title>',
        '<style>body{font:16px system-ui;max-width:1200px;margin:30px auto;line-height:1.6}td,th{padding:8px;border:1px solid #bbc}table{border-collapse:collapse;width:100%}video{width:100%}</style>',
        '<h1>B0 và B1 causal trên video sạch</h1><p>Confidence0,27; k=3/N=5 đủ cửa sổ, EMA alpha0,3 từ0. Tham số chốt trước đo, không quét trên các clip. ON là trạng thái nghi vấn, chưa phải xác nhận tai nạn.</p>',
        '<table><tr><th>Video / vai trò</th><th>Frame</th><th>B0 ON</th><th>k-of-N ON</th><th>EMA ON</th></tr>']
    for v in videos:
        counts=[v['filter_comparison'][name]['active_frames'] for name in ('B0','B1_kofn','B1_EMA')]
        parts.append(f"<tr><td>{v['sequence']}<br>{v['role']}</td><td>{v['frames']}</td><td>{counts[0]}</td><td>{counts[1]}</td><td>{counts[2]}</td></tr>")
    parts.append('</table><p>ON trên clip âm là false active frame; raw ON bout không đồng nghĩa một alert. CADP ngoài96–130 unknown, trong khoảng chỉ đo hiện diện vì không có GT vùng accident và timing nguồn. Không báo recall/F1 event hoặc cảnh báo/giờ từ các clip ngắn.</p>')
    for v in videos:
        link=relative_link(workspace(v['output_video']),output)
        parts.append(f'<details><summary>{v["sequence"]}: xem video và CSV</summary><video controls preload="none" src="{link}"></video><a href="videos/{v["sequence"]}/frames.csv">CSV frame</a> · <a href="videos/{v["sequence"]}/report.json">Report</a></details>')
    parts.append('<p><a href="report.json">Báo cáo đầy đủ và timing</a></p></html>')
    (output/'index.html').write_text('\n'.join(parts),encoding='utf-8')
    return output/'report.json'


def main() -> int:
    parser = argparse.ArgumentParser(description='Audit existing B0 errors and clean full-video predictions')
    parser.add_argument('--config',type=Path,default=Path('configs/b0_diagnostics_v1.json'))
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check',action='store_true')
    mode.add_argument('--run',action='store_true')
    mode.add_argument('--validation-reference',action='store_true',help='Đo checkpoint mốc trên val mới bằng config train; không đo test/holdout')
    mode.add_argument('--saved-validation',action='store_true',help='Phân tích prediction val đã lưu của config train; không suy luận/train/test')
    mode.add_argument('--select-operating-point',action='store_true',help='Chọn confidence trên val, recall>=70%%; khóa trước khi mở holdout')
    mode.add_argument('--evaluate-operating-holdout',action='store_true',help='Đo một lần holdout âm bằng config điểm vận hành đã khóa')
    mode.add_argument('--temporal-diagnostics',action='store_true',help='Đo B0 và bộ lọc B1 causal trên video, không train/tune')
    args = parser.parse_args()
    config_path = workspace(args.config)
    # Các mode ghi chỉ được mở bằng config có output canonical. Config lịch sử
    # vẫn đọc được, nhưng không tạo thêm diagnostics lồng trong run LEGACY.
    if not args.check:
        planned = json.loads(config_path.read_text(encoding='utf-8'))
        if args.validation_reference:
            require_output_path(ROOT,planned['reference_validation_output'],'shared_evaluation')
        elif args.temporal_diagnostics:
            require_output_path(ROOT,planned['output'],'baseline',baseline='B1')
        elif args.run:
            require_output_path(ROOT,planned['output'],'data_audit')
        else:
            require_output_path(ROOT,planned['output'],'baseline',baseline='B0')
    if args.select_operating_point:
        select_operating_point(config_path)
        return 0
    if args.evaluate_operating_holdout:
        evaluate_operating_holdout(config_path)
        return 0
    if args.validation_reference:
        validation_references(config_path)
        return 0
    config = json.loads(config_path.read_text(encoding='utf-8'))
    if args.saved_validation:
        dataset,rows=check_inputs(config)
        run=workspace(config['output'])
        experiment=json.loads((run/'experiment.json').read_text(encoding='utf-8'))
        verify_file(experiment['checkpoint'],experiment['checkpoint_sha256'])
        if experiment['config_sha256']!=sha256_file(config_path):raise ValueError('Training config changed')
        # Lọc val trước khi dựng lookup; test và reserve không được phân tích
        # hoặc chạy dự đoán trong chế độ chỉ kiểm lỗi validation này.
        rows=[r for r in rows if r['split']=='val']
        output=run/'diagnostics'
        if output.exists():raise FileExistsError('Preserve existing diagnostics')
        output.mkdir()
        spec=dict(training_config=config_path.relative_to(ROOT).as_posix(),
                  image_cases=[dict(path=(run/'cases_val').relative_to(ROOT).as_posix(),scope='validation')],
                  matching_iou=config['matching_iou'],prediction_confidence=config['prediction_confidence'])
        image_analysis(spec,rows,output)
        print(f'Saved validation error analysis: {output}')
        return 0
    rows = check_config(config)
    if args.temporal_diagnostics:
        run_temporal_comparison(config_path,config)
        return 0
    print(json.dumps(dict(status='inputs_verified',sequences=len(config['sequences']),
                          expected_frames=sum(s['frames'] for s in config['sequences']))),flush=True)
    if args.check: return 0
    output = workspace(config['output'])
    if output.exists(): raise FileExistsError('Diagnostics output exists; preserve the original run')
    os.environ['YOLO_CONFIG_DIR']=str(ROOT/'.tmp/ultralytics')
    os.environ['MPLCONFIGDIR']=str(ROOT/'.tmp/matplotlib')
    os.environ['YOLO_OFFLINE']='true'; os.environ['YOLO_AUTOINSTALL']='false'
    output.mkdir()
    shutil.copy2(config_path,output/'requested_config.json')
    try:
        images = image_analysis(config,rows,output)
        print('Image error analysis saved',flush=True)
        import numpy as np
        import ultralytics
        import torch
        from ultralytics import YOLO
        if ultralytics.__version__ != config['ultralytics_version']:
            raise ValueError('Ultralytics version differs')
        experiment = json.loads(workspace(config['experiment']).read_text(encoding='utf-8'))
        model = YOLO(str(workspace(experiment['checkpoint'])))
        if model.names != {0:'accident'}: raise ValueError('Not the B0 accident checkpoint')
        # Warmup tách khỏi log video; không giữ toàn video trong RAM.
        for _ in range(3): model.predict(np.zeros((640,640,3),np.uint8),device=config['device'],verbose=False)
        videos = []
        for spec in config['sequences']:
            videos.append(video_analysis(model,config,spec,output))
            print(f"Completed {spec['sequence']}: {videos[-1]['frames_with_predictions']}/{videos[-1]['frames']} frames with predictions",flush=True)
        result = dict(status='complete',config_sha256=sha256_file(config_path),
                      checkpoint=experiment['checkpoint'],checkpoint_sha256=experiment['checkpoint_sha256'],
                      image_analysis=images,sequences=videos,ultralytics=ultralytics.__version__,torch=torch.__version__,
                      scope=config['scope'],full_B0_complete=False,threshold_tuned=False)
        save_json(output/'report.json',result)
        write_page(output,images,videos)
        print(f"Completed: {output/'index.html'}",flush=True)
    except Exception as error:
        save_json(output/'failure.json',dict(status='failed',error=repr(error)))
        raise
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
