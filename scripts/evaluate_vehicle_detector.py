"""Measure pretrained vehicle detector on registered, labelled DETRAC development images."""
import argparse
from collections import Counter
from datetime import datetime
import csv
import importlib.metadata
import json
import math
import os
from pathlib import Path
import sys
import time
from zipfile import ZipFile
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['YOLO_CONFIG_DIR'] = str(ROOT/'configs/ultralytics')
os.environ['YOLO_OFFLINE'] = 'true'
os.environ['MPLCONFIGDIR'] = str(ROOT/'.cache/matplotlib')
from src.data_preparation import save_json, sha256_file
from src.detection_evaluation import parse_detrac, coco_truth, task_predictions, evaluate_coco


def run(config_path, output, resume=False):
    config = json.loads(config_path.read_text()); config_hash = sha256_file(config_path)
    if config['project_test_sequences'] or config['local_training_sequences']:
        raise ValueError('This command only measures the declared pretrained development baseline')
    weights = ROOT/config['weights']; inventory = ROOT/config['image_inventory']
    if sha256_file(weights) != config['weights_sha256'] or sha256_file(inventory) != config['image_inventory_sha256']:
        raise ValueError('Checkpoint/image inventory fingerprint mismatch')
    catalog = json.loads((ROOT/'data/download_catalog.json').read_text())
    asset = next(x for x in catalog['assets'] if x['id'] == config['annotations_asset'])
    archive_path = ROOT/asset['path']
    if sha256_file(archive_path) != asset['expected_sha256']:
        raise ValueError('Annotation archive fingerprint mismatch; restore registered asset first')
    if resume:
        if (output/'report.json').exists() or json.loads((output/'protocol.json').read_text()) != config:
            raise ValueError('Resume requires the same incomplete protocol, never a completed report')
    else:
        output.mkdir(parents=True, exist_ok=False)
        save_json(output/'protocol.json', config)
    registry = {(r['sequence'], r['filename']): r for r in csv.DictReader(inventory.open(newline=''))}
    frames, source_metadata, image_metadata = [], [], []
    from PIL import Image
    with ZipFile(archive_path) as archive:
        for sequence, expected in config['sequences'].items():
            member = 'DETRAC-Train-Annotations-XML/'+sequence+'.xml'
            data = archive.read(member)
            import hashlib
            source_metadata.append(dict(sequence=sequence, member=member, sha256=hashlib.sha256(data).hexdigest()))
            for frame in parse_detrac(data, sequence, expected):
                filename = f"img{frame['source_frame']:05d}.jpg"
                reference = registry[sequence,filename]
                relative = f'data_raw/ua_detrac/DETRAC-Images/{sequence}/{filename}'
                image = ROOT/relative
                digest = sha256_file(image)
                if image.stat().st_size != int(reference['size_bytes']) or digest != reference['mirror_sha256']:
                    raise ValueError('Source image fingerprint mismatch: '+relative)
                with Image.open(image) as im:
                    width,height = im.size
                if (width,height) != (960,540):
                    raise ValueError('Unexpected annotation/image coordinate system')
                frame.update(id=len(frames)+1, sequence=sequence, file_name=relative, width=width, height=height)
                frames.append(frame)
                image_metadata.append(dict(image_id=frame['id'], sequence=sequence, source_frame=frame['source_frame'], path=relative, sha256=digest))
    if resume:
        if json.loads((output/'image_manifest.json').read_text()) != image_metadata:
            raise ValueError('Resume image manifest differs')
    else:
        save_json(output/'image_manifest.json', image_metadata)
    truths = {task: coco_truth(frames, task, config['truncation_ignore_from']) for task in config['evaluation_tasks']}
    def save_derived(path, value):
        if resume and path.exists():
            if json.loads(path.read_text()) != value:
                raise ValueError('Existing evaluation artifact differs; preserved: '+str(path))
        else:
            save_json(path,value)
    for task,truth in truths.items():save_derived(output/(task+'_ground_truth.json'), truth)
    import torch
    from ultralytics import YOLO
    torch.set_num_threads(config['cpu_threads'])
    profiles = {}
    for profile, agnostic in config['profiles'].items():
        folder=output/profile;folder.mkdir(exist_ok=resume)
        model=YOLO(str(weights))
        model.add_callback('on_predict_start',lambda predictor:torch.set_num_threads(config['cpu_threads']))
        predictions=[];started=time.perf_counter();cache_path=folder/'predictions.jsonl'
        reused=resume and cache_path.exists()
        if reused:
            cached=[json.loads(line) for line in cache_path.read_text().splitlines()]
            if [r['image_id'] for r in cached] != [f['id'] for f in frames]:
                raise ValueError('Only a complete prediction stream may be resumed')
            for row in cached:
                for p in row['predictions']:
                    if (p['image_id']!=row['image_id'] or p['category_id'] not in config['inference']['classes']
                            or not math.isfinite(p['score']) or not config['inference']['conf']<=p['score']<=1
                            or len(p['bbox'])!=4 or not all(math.isfinite(v) for v in p['bbox']) or min(p['bbox'][2:])<=0):
                        raise ValueError('Invalid resumed prediction')
                predictions.extend(row['predictions'])
            elapsed=None  # No invented inference time for the interrupted run.
            print(f'{profile}: reused complete {len(cached)}-image stream; no inference rerun',flush=True)
        else:
            with cache_path.open('x') as stream:
                for frame in frames:
                    # Ground truth is never passed to the detector or used for filtering predictions.
                    result=model.predict(str(ROOT/frame['file_name']),agnostic_nms=agnostic,verbose=False,**config['inference'])[0]
                    current=[]
                    for box,score,cls in zip(result.boxes.xyxy.tolist(),result.boxes.conf.tolist(),result.boxes.cls.tolist()):
                        x1,y1,x2,y2=box
                        current.append(dict(image_id=frame['id'],category_id=int(cls),bbox=[x1,y1,x2-x1,y2-y1],score=float(score)))
                    predictions.extend(current)
                    stream.write(json.dumps(dict(image_id=frame['id'],predictions=current),allow_nan=False)+'\n')
                    if frame['id']%250==0:print(f'{profile}: {frame["id"]}/{len(frames)} images',flush=True)
            elapsed=time.perf_counter()-started
        prediction_metadata=dict(complete=True,protocol_sha256=config_hash,weights_sha256=sha256_file(weights),
            image_manifest_sha256=sha256_file(output/'image_manifest.json'),cache_sha256=sha256_file(cache_path),
            reused_after_interrupted_evaluation=reused,inference_wall_s=elapsed)
        metadata_path=folder/'prediction_metadata.json'
        if metadata_path.exists():
            previous=json.loads(metadata_path.read_text())
            if any(previous[k]!=prediction_metadata[k] for k in ('protocol_sha256','weights_sha256','image_manifest_sha256','cache_sha256')):
                raise ValueError('Prediction cache provenance mismatch')
        else:save_json(metadata_path,prediction_metadata)
        results={}
        for task,truth in truths.items():
            projected=task_predictions(predictions,task)
            result,log=evaluate_coco(truth,projected,config['operating_confidences'])
            result['by_sequence']={}
            for sequence in config['sequences']:
                ids=[f['id'] for f in frames if f['sequence']==sequence]
                subset,sublog=evaluate_coco(truth,projected,config['operating_confidences'],ids)
                subset.pop('pr_curve_iou50');result['by_sequence'][sequence]=subset
                log+='\n'+sequence+'\n'+sublog
            save_derived(folder/(task+'.json'),result)
            (folder/(task+'_coco.log')).write_text(log)
            results[task]=result
        profiles[profile]=dict(agnostic_nms=agnostic,images=len(frames),predictions=len(predictions),
                              inference_wall_s=elapsed,reused_prediction_cache=reused,
                              effective_args=(dict(config['inference'],agnostic_nms=agnostic) if reused else {k:getattr(model.predictor.args,k,None) for k in ('conf','iou','imgsz','max_det','agnostic_nms','rect')}),results=results)
        save_derived(folder/'summary.json',profiles[profile])
    if sha256_file(config_path)!=config_hash or sha256_file(weights)!=config['weights_sha256']:
        raise ValueError('Protocol/checkpoint changed during evaluation')
    for item in image_metadata:
        if sha256_file(ROOT/item['path'])!=item['sha256']:raise ValueError('Image changed during evaluation')
    report=dict(complete=True,recorded_at=datetime.now(ZoneInfo('Asia/Bangkok')).isoformat(),protocol=config,
        protocol_sha256=config_hash,weights_sha256=sha256_file(weights),checkpoint_train_data=model.ckpt.get('train_args',{}).get('data'),
        annotation_archive_sha256=sha256_file(archive_path),annotation_members=source_metadata,
        image_manifest_sha256=sha256_file(output/'image_manifest.json'),
        source_class_box_counts=dict(Counter(o['source_class'] for f in frames for o in f['objects'])),
        source_xml_boxes=len([o for f in frames for o in f['objects']]),images=len(frames),profiles=profiles,
        packages={p:importlib.metadata.version(p) for p in ('torch','ultralytics','numpy','pycocotools')},
        code_sha256={p:sha256_file(ROOT/p) for p in ('src/detection_evaluation.py','scripts/evaluate_vehicle_detector.py')},
        training_performed=False,test_set_evaluated=False,official_detrac_benchmark=False,event_metrics_measured=False,
        limitations=['Development scenes, not independent cameras or locked test','Only localization and common car/bus classes; no justified van/others-to-truck mapping','Raw detector output only, no tracking or display-label votes','COCO ignore/maxDet protocol is specified here; not the official DETRAC evaluator'])
    save_json(output/'report.json',report)
    print(json.dumps({k:{task:{m:r[m] for m in ('mAP50','mAP50_95','operating_points')} for task,r in v['results'].items()} for k,v in profiles.items()},indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=ROOT/'configs/vehicle_evaluation.json')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--resume',action='store_true',help='Reuse only complete streams under the same incomplete protocol')
    args=parser.parse_args()
    destination=args.output.resolve()
    if not destination.is_relative_to(ROOT/'outputs'):parser.error('Keep evaluation artifacts below outputs/')
    run(args.config.resolve(),destination,args.resume)
