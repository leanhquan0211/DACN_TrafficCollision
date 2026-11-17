"""Verify the existing B0 checkpoint's training provenance and rerun train/val diagnostics.

No training, new labels, threshold selection or test-set creation is performed.
"""
import argparse
from datetime import datetime
import importlib.metadata
import json
import os
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ['YOLO_CONFIG_DIR']=str(ROOT/'configs/ultralytics')
os.environ['YOLO_OFFLINE']='true'
os.environ['MPLCONFIGDIR']=str(ROOT/'.cache/matplotlib')
from src.b0_feasibility import verify
from src.data_preparation import save_json,sha256_file
from scripts.run_b0_feasibility import diagnose


def run(dataset,experiment,output):
    info,rows=verify(ROOT,dataset)
    original=json.loads((experiment/'report.json').read_text())
    metadata=json.loads((experiment/'run_metadata.json').read_text())
    weights=experiment/'train/weights/best.pt'
    if sha256_file(weights)!=original['best_sha256'] or info['manifest_sha256']!=metadata['dataset_manifest_sha256']:
        raise ValueError('Checkpoint/training dataset provenance mismatch')
    output.mkdir(parents=True,exist_ok=False)
    import torch
    from ultralytics import YOLO
    model=YOLO(str(weights))
    if model.names!={0:'accident'}:raise ValueError('Wrong checkpoint task/classes')
    model.add_callback('on_val_start',lambda validator:torch.set_num_threads(4))
    model.add_callback('on_predict_start',lambda predictor:torch.set_num_threads(4))
    metrics={}
    for split in ('train','val'):
        result=model.val(data=str(dataset/'dataset.yaml'),split=split,imgsz=640,batch=2,
            device='cpu',workers=0,conf=.001,iou=.7,agnostic_nms=False,plots=True,
            project=str(output),name=split,exist_ok=False,verbose=False)
        metrics[split]={k:float(v) for k,v in result.results_dict.items()}
    diagnostics=diagnose(model,dataset,rows,output,json.loads((dataset/'experiment_config.json').read_text()))
    tp,fp,fn=(diagnostics[k] for k in ('tp_boxes','fp_boxes','fn_boxes'))
    fixed=dict(confidence=.25,iou=.5,tp=tp,fp=fp,fn=fn,
               precision=tp/(tp+fp) if tp+fp else None,recall=tp/(tp+fn) if tp+fn else None,
               f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None)
    verify(ROOT,dataset)
    if sha256_file(weights)!=original['best_sha256']:raise ValueError('Checkpoint changed')
    report=dict(complete=True,recorded_at=datetime.now(ZoneInfo('Asia/Bangkok')).isoformat(),
        purpose='audit_existing_checkpoint_no_retraining',training_performed=False,
        checkpoint=str(weights.relative_to(ROOT)),checkpoint_sha256=sha256_file(weights),
        base_weights_sha256=metadata['base_weights_sha256'],dataset_manifest_sha256=info['manifest_sha256'],
        dataset_counts=info['counts'],training_config=metadata['config'],metrics=metrics,
        original_training_report_metrics=original['validation_metrics'],validation_fixed_operating_point=fixed,
        precision_recall_scope='Ultralytics curve operating point, not fixed confidence0.25; train is diagnostic only',
        packages={p:importlib.metadata.version(p) for p in ('torch','ultralytics','numpy')},
        code_sha256=sha256_file(Path(__file__)),test_set_evaluated=False,event_metrics_measured=False,
        research_gate_satisfied=False,limitations=original['limitations'])
    save_json(output/'report.json',report)
    print(json.dumps(dict(dataset_counts=info['counts'],metrics=metrics,fixed=fixed),indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset',type=Path,default=ROOT/'data/processed/b0_feasibility_2026-11-16')
    parser.add_argument('--experiment',type=Path,default=ROOT/'outputs/experiments/b0_feasibility_2026-11-16')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if not args.output.resolve().is_relative_to(ROOT/'outputs'):parser.error('Keep artifacts below outputs/')
    run(args.dataset.resolve(),args.experiment.resolve(),args.output.resolve())
