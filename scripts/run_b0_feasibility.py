"""Fine-tune one-class accident YOLO on a tiny, explicitly labelled development pilot.

This command does not override research readiness or produce event metrics.
"""
from datetime import datetime
import argparse
import csv
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import time
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ["YOLO_CONFIG_DIR"]=str(ROOT/"configs/ultralytics")
os.environ["YOLO_OFFLINE"]="true"
os.environ["MPLCONFIGDIR"]=str(ROOT/".cache/matplotlib")
from src.b0_feasibility import verify
from src.data_preparation import save_csv,save_json,sha256_file


def iou(a,b):
    area=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    total=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-area
    return area/total if total>0 else 0


def diagnose(model,dataset,rows,output,config):
    import cv2
    import numpy as np
    threshold=config["diagnostic_confidence_threshold"];overlap=config["diagnostic_iou_threshold"]
    cases=[];tiles=[];totals=dict(tp_boxes=0,fp_boxes=0,fn_boxes=0,negative_frames=0,negative_frames_with_predictions=0)
    with (output/"validation_predictions.jsonl").open("x") as stream:
        for row in (r for r in rows if r["split"]=="val"):
            path=dataset/row["image_export"];image=cv2.imread(str(path));height,width=image.shape[:2]
            truth=[]
            for line in (dataset/row["label_export"]).read_text().splitlines():
                cls,cx,cy,w,h=map(float,line.split())
                truth.append([(cx-w/2)*width,(cy-h/2)*height,(cx+w/2)*width,(cy+h/2)*height])
            result=model.predict(str(path),device="cpu",imgsz=config["training"]["imgsz"],conf=threshold,verbose=False)[0]
            predictions=[dict(bbox_xyxy=box,confidence=float(score),class_id=int(cls)) for box,score,cls in zip(result.boxes.xyxy.cpu().tolist(),result.boxes.conf.cpu().tolist(),result.boxes.cls.cpu().tolist())]
            pairs=sorted(((iou(t,p["bbox_xyxy"]),j,k) for j,t in enumerate(truth) for k,p in enumerate(predictions)),reverse=True)
            used_gt=set();used_pred=set()
            for score,j,k in pairs:
                if score>=overlap and j not in used_gt and k not in used_pred:used_gt.add(j);used_pred.add(k)
            tp=len(used_gt);fp=len(predictions)-tp;fn=len(truth)-tp
            totals["tp_boxes"]+=tp;totals["fp_boxes"]+=fp;totals["fn_boxes"]+=fn
            totals["negative_frames"]+=not truth;totals["negative_frames_with_predictions"]+=not truth and bool(predictions)
            cases.append(dict(scene_group=row["scene_group"],source_frame_number=row["source_frame_number"],label_origin=row["label_origin"],gt_regions=len(truth),predicted_regions=len(predictions),tp_boxes=tp,fp_boxes=fp,fn_boxes=fn,max_confidence=max((p["confidence"] for p in predictions),default=0),image=row["image_export"]))
            stream.write(json.dumps(dict(**cases[-1],predictions=predictions),allow_nan=False)+"\n")
            for box in truth:
                x1,y1,x2,y2=map(round,box);cv2.rectangle(image,(x1,y1),(x2,y2),(60,220,90),max(2,width//500))
            for p in predictions:
                x1,y1,x2,y2=map(round,p["bbox_xyxy"]);cv2.rectangle(image,(x1,y1),(x2,y2),(0,160,255),max(2,width//500))
            scale=min(480/width,270/height);small=cv2.resize(image,(round(width*scale),round(height*scale)))
            tile=np.full((325,480,3),18,dtype=np.uint8);x=(480-small.shape[1])//2;y=55+(270-small.shape[0])//2;tile[y:y+small.shape[0],x:x+small.shape[1]]=small
            title=f"{Path(row['scene_group']).name} frame {row['source_frame_number']}"
            cv2.putText(tile,title,(8,21),cv2.FONT_HERSHEY_SIMPLEX,.48,(245,245,245),1)
            cv2.putText(tile,f"GREEN=source GT  ORANGE=prediction  TP={tp} FP={fp} FN={fn}",(8,43),cv2.FONT_HERSHEY_SIMPLEX,.4,(245,245,245),1)
            tiles.append(tile)
    save_csv(output/"validation_cases.csv",cases,list(cases[0]))
    while len(tiles)%3:tiles.append(np.full_like(tiles[0],18))
    cv2.imwrite(str(output/"validation_cases.jpg"),np.concatenate([np.concatenate(tiles[i:i+3],axis=1) for i in range(0,len(tiles),3)],axis=0))
    totals.update(confidence_threshold=threshold,iou_threshold=overlap,scope="diagnostic frame/bbox counts on development validation; not event precision/recall")
    save_json(output/"validation_diagnostics.json",totals)
    return totals


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feasibility-only",action="store_true",required=True)
    parser.add_argument("--dataset",type=Path,default=ROOT/"data/processed/b0_feasibility_2026-11-16")
    parser.add_argument("--output",type=Path,default=ROOT/"outputs/experiments/b0_feasibility_2026-11-16")
    args=parser.parse_args();dataset=args.dataset.resolve();output=args.output.resolve()
    info,rows=verify(ROOT,dataset)
    config=json.loads((dataset/"experiment_config.json").read_text())
    if config["purpose"]!="software_feasibility_only":raise ValueError("Unsupported purpose")
    if not output.is_relative_to(ROOT):raise ValueError("Keep experiment inside project")
    weights=ROOT/"yolov8n.pt";catalog=json.loads((ROOT/"data/download_catalog.json").read_text())
    expected=next(x["expected_sha256"] for x in catalog["assets"] if x["id"]=="yolov8n")
    if sha256_file(weights)!=expected:raise ValueError("Base weights fingerprint mismatch")
    import torch
    from ultralytics import YOLO,settings
    from ultralytics.utils import USER_CONFIG_DIR
    from matplotlib import font_manager
    # Keep all optional integrations local/off; settings directory is inside repo.
    disabled={k:False for k in ("sync","clearml","wandb","mlflow","comet","neptune","dvc","tensorboard","hub") if k in settings}
    settings.update(disabled)
    plot_font=Path(font_manager.findfont("DejaVu Sans"))
    USER_CONFIG_DIR.mkdir(parents=True,exist_ok=True)
    if not (USER_CONFIG_DIR/"Arial.ttf").exists():shutil.copyfile(plot_font,USER_CONFIG_DIR/"Arial.ttf")
    output.mkdir(parents=True,exist_ok=False)
    baseline_hashes={p:sha256_file(ROOT/p) for p in ("data/manifest.csv","data/b0_readiness.json","configs/b0_region_proposal.json")}
    metadata=dict(purpose="software_feasibility_only",started_at=datetime.now(ZoneInfo("Asia/Bangkok")).isoformat(),
        dataset=str(dataset),dataset_readiness_sha256=sha256_file(dataset/"readiness.json"),dataset_manifest_sha256=info["manifest_sha256"],
        base_weights_sha256=expected,config=config,counts=info["counts"],python=platform.python_version(),
        packages={p:importlib.metadata.version(p) for p in ("torch","torchvision","ultralytics","numpy","opencv-python")},
        code_sha256={p:sha256_file(ROOT/p) for p in ("src/b0_feasibility.py","scripts/prepare_b0_feasibility.py","scripts/run_b0_feasibility.py")},
        formal_inputs_sha256_before=baseline_hashes,optional_integrations_disabled=disabled,
        plot_font_source=str(plot_font),plot_font_sha256=sha256_file(plot_font),
        formal_research_training_approved=False,test_set_evaluated=False,event_metrics_measured=False)
    save_json(output/"run_metadata.json",metadata)
    try:
        model=YOLO(str(weights));threads=config["cpu_threads"]
        def restore_threads(trainer):torch.set_num_threads(threads)
        model.add_callback("on_pretrain_routine_start",restore_threads)
        epoch_threads=[]
        model.add_callback("on_train_epoch_end",lambda trainer:epoch_threads.append(dict(epoch=trainer.epoch,threads=torch.get_num_threads())))
        started=time.perf_counter()
        metrics=model.train(data=str(dataset/"dataset.yaml"),project=str(output),name="train",exist_ok=False,**config["training"])
        train_seconds=time.perf_counter()-started
        best=output/"train/weights/best.pt";last=output/"train/weights/last.pt"
        if not best.is_file() or not last.is_file():raise RuntimeError("Training did not save both checkpoints")
        trained=YOLO(str(best))
        if trained.names!={0:"accident"}:raise RuntimeError(f"Unexpected checkpoint class mapping: {trained.names}")
        trained.add_callback("on_predict_start",lambda predictor:torch.set_num_threads(threads))
        diagnostics=diagnose(trained,dataset,rows,output,config)
        verify(ROOT,dataset)
        preserved={p:sha256_file(ROOT/p)==h for p,h in baseline_hashes.items()}
        if not all(preserved.values()):raise RuntimeError("Formal research inputs unexpectedly changed")
        report=dict(complete=True,purpose="software_feasibility_only",training_performed=True,
            completed_at=datetime.now(ZoneInfo("Asia/Bangkok")).isoformat(),
            best_checkpoint=str(best),best_sha256=sha256_file(best),last_checkpoint=str(last),last_sha256=sha256_file(last),
            class_names=trained.names,training_wall_s=train_seconds,cpu_threads_per_epoch=epoch_threads,
            validation_metrics={k:float(v) for k,v in metrics.results_dict.items()},validation_diagnostics=diagnostics,
            validation_scope="tiny development validation, no locked test; not a research benchmark",
            formal_inputs_preserved=preserved,formal_b0_gate_satisfied=False,collision_alert_implemented=False,
            event_metrics_measured=False,test_set_evaluated=False,limitations=config["limitations"])
        save_json(output/"report.json",report);print(json.dumps(report,ensure_ascii=False,indent=2))
    except BaseException as exc:
        save_json(output/"failure.json",dict(complete=False,error=str(exc),error_type=type(exc).__name__))
        raise


if __name__=="__main__":main()
