"""Huấn luyện và đo B0 pilot ảnh bằng nhãn vùng accident đã khóa.

Đầu vào: config JSON, dataset YOLO/provenance đã export và pretrained cục bộ.
Đầu ra: checkpoint, loss/log, metric bbox, dự đoán và ví dụ TP/FP/FN.
Chạy --check để kiểm đầu vào, --train để chạy một thí nghiệm mới; --resume
chỉ tiếp tục run dở có checkpoint/optimizer và config đã khóa. Pilot nhỏ
chỉ kiểm học/phát hiện trên ảnh; chưa đo sự kiện, delay hoặc báo sai/giờ.
--preflight kiểm decode/bbox và forward GPU nhưng không chạy backward/train.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
import shutil
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.data_preparation import save_csv, save_json, sha256_file, validate_b0_verified_origins

# Chỉ các trường này được đưa vào Ultralytics. Khóa cùng danh sách khi resume
# để augmentation/LR không âm thầm khác công thức đã ghi trong config.
TRAIN_KEYS=("epochs","patience","imgsz","batch","workers","device","amp","optimizer","seed","lr0","momentum",
            "lrf","warmup_epochs","warmup_bias_lr","weight_decay","nbs","mosaic","close_mosaic","scale","mixup","cos_lr")


def training_arguments(config: dict) -> dict:
    """Lấy tham số train tường minh; trường nguồn/metric không đi vào model.train."""
    return {key:config[key] for key in TRAIN_KEYS if key in config}


def initial_weights_digest(config: dict, release: dict) -> str:
    """Release khóa dữ liệu; config mới được khóa riêng checkpoint khởi tạo.

    Các config cũ vẫn kiểm SHA pretrained từ release. Thử nghiệm đổi n sang s
    phải khai SHA riêng trong config, không sửa SHA của release hoặc model cũ.
    """
    return config.get('initial_weights_sha256',release['initial_weights_sha256'])


def recorded_resume_patience(output: Path, config_path: Path) -> int | None:
    """Đọc chính sách dừng đã áp dụng; không sửa config/hash của run gốc."""
    path=output/'resume_events.json'
    if not path.exists():return None
    record=json.loads(path.read_text(encoding='utf-8'))
    events=record['events']
    if record['config_sha256']!=sha256_file(config_path):
        raise ValueError('Resume policy history differs from original config')
    value=events[-1]['patience'] if events else None
    if value is not None and (not isinstance(value,int) or isinstance(value,bool) or value<1):
        raise ValueError('Invalid recorded early stopping patience')
    return value


def apply_resume_patience(trainer, patience: int, config_path: Path) -> None:
    """Bật dừng sớm SAU khôi phục checkpoint, giữ mốc best và optimizer.

    Ultralytics 8.4.178 nạp lại stopper.__dict__ từ checkpoint; chỉ truyền
    patience vào train() có thể bị trạng thái cũ (vô hạn) ghi đè. Callback
    on_train_start đặt lại riêng patience sau resume, không reset best_epoch.
    """
    if not isinstance(patience,int) or isinstance(patience,bool) or patience<1:
        raise ValueError('Resume patience must be a positive integer')
    from datetime import datetime,timezone,timedelta
    output=Path(trainer.save_dir)
    recorded_resume_patience(output,config_path)
    path=output/'resume_events.json'
    record=json.loads(path.read_text(encoding='utf-8')) if path.exists() else dict(
        config_sha256=sha256_file(config_path),events=[])
    previous=trainer.stopper.patience
    # Chỉ đổi điều kiện dừng. Mốc tốt nhất đã học và mọi trạng thái tối ưu
    # vẫn do resume của Ultralytics khôi phục nguyên trạng.
    trainer.stopper.patience=patience
    trainer.stopper.possible_stop=(trainer.start_epoch-trainer.stopper.best_epoch)>=patience-1
    trainer.args.patience=patience
    record['events'].append(dict(timestamp=datetime.now(timezone(timedelta(hours=7))).isoformat(),
        timezone='Asia/Bangkok',type='resume_early_stopping_override',
        completed_epochs=trainer.start_epoch,patience=patience,
        previous_patience=str(previous),best_epoch=trainer.stopper.best_epoch,
        best_fitness=trainer.stopper.best_fitness,checkpoint_sha256=sha256_file(output/'weights/last.pt'),
        optimizer_reset=False,config_modified=False))
    # Ghi thay thế qua file tạm để một lần ngắt không để lại JSON nửa chừng.
    pending=output/'resume_events.json.tmp'
    pending.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    pending.replace(path)
    print(f'Resume early stopping: patience={patience}; retained best epoch={trainer.stopper.best_epoch}',flush=True)


def workspace(path: str | Path) -> Path:
    """Giới hạn đường dẫn config/output trong project, kể cả máy Windows có dấu."""
    result=(ROOT/path).resolve()
    if not result.is_relative_to(ROOT):
        raise ValueError(f"Outside workspace: {path}")
    return result


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig",newline="") as stream:
        return list(csv.DictReader(stream))


def iou(a: list[float], b: list[float]) -> float:
    """IoU là diện tích giao/chia hợp hai hộp xyxy, không phải xác suất va chạm."""
    intersection=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    union=max(0,a[2]-a[0])*max(0,a[3]-a[1])+max(0,b[2]-b[0])*max(0,b[3]-b[1])-intersection
    return intersection/union if union>0 else 0.0


def match_boxes(gt: list[list[float]], predictions: list[dict], threshold: float) -> dict:
    """Ghép tham lam theo confidence; một bbox GT chỉ nhận tối đa một TP.

    Dự đoán thừa/không khớp là FP. GT chưa ghép là FN. Đây là metric bbox
    tại một ngưỡng cố định, khác mAP quét confidence và khác event metrics.
    """
    used=set();matches=[]
    for prediction in sorted(predictions,key=lambda r:r["confidence"],reverse=True):
        candidates=[(iou(prediction["xyxy"],box),i) for i,box in enumerate(gt) if i not in used]
        overlap,index=max(candidates,default=(0,-1))
        matched=index>=0 and overlap>=threshold
        if matched:
            used.add(index)
        matches.append(dict(**prediction,matched_gt=index if matched else None,iou=overlap))
    return dict(tp=len(used),fp=len(predictions)-len(used),fn=len(gt)-len(used),predictions=matches)


def check_inputs(config: dict) -> tuple[Path, list[dict]]:
    """Kiểm release/hash và group trước train; không sửa fingerprint để bỏ mismatch."""
    # Bundle Kaggle/local giữ hash release nguồn và chứng minh projection riêng;
    # không yêu cầu raw video hoặc đổi fingerprint cũ vì khác đường dẫn máy.
    if config.get('recipe_revision_manifest'):
        from src.kaggle_recipe import check_revised_inputs
        return check_revised_inputs(config,ROOT)
    if config.get('portable_bundle_manifest'):
        from src.training_bundle import check_portable_inputs
        return check_portable_inputs(config,ROOT)
    dataset=workspace(config["dataset"])
    report=json.loads((dataset.parent/"report.json").read_text(encoding="utf-8"))
    release_key=config.get("release_key","pilot_release")
    policy_path=workspace(config.get("label_policy","configs/b0_public_label_policy.json"))
    ready=json.loads((ROOT/"data/b0_readiness.json").read_text(encoding="utf-8"))[release_key]
    policy=json.loads(policy_path.read_text(encoding="utf-8"))
    if report["status"]!="complete" or report["release_kind"]!="pilot" or report.get("release_key","pilot_release")!=release_key or not ready["can_train"] or not policy["pilot_training_release_allowed"]:
        raise ValueError("No authorized basic-image pilot release")
    if report["pool_sha256"]!=ready["export_pool_sha256"] or report["split_sha256"]!=ready["export_split_sha256"]:
        raise ValueError("Export differs from locked pilot release")
    if sha256_file(workspace(ready["pool"]))!=ready["export_pool_sha256"] or sha256_file(workspace(ready["split_manifest"]))!=ready["export_split_sha256"]:
        raise ValueError("Locked pool or split manifest changed")
    if report.get("provenance_sha256") and sha256_file(dataset.parent/"provenance.csv")!=report["provenance_sha256"]:
        raise ValueError("Export provenance changed")
    if report.get("dataset_yaml_sha256") and sha256_file(dataset)!=report["dataset_yaml_sha256"]:
        raise ValueError("Export dataset YAML changed")
    if sha256_file(policy_path)!=ready["export_policy_sha256"]:
        raise ValueError("Pilot label policy changed after release")
    rows=read_csv(dataset.parent/"provenance.csv")
    if release_key in ("verified_pilot_release","normal_expanded_pilot_release","hard_negative_pilot_release"):
        validate_b0_verified_origins(rows)
    groups={};sequence_splits={};image_records={}
    for row in rows:
        if any(not row[field].replace('\\','/').startswith(prefix+row['split']+'/')
               for field,prefix in (("export_image","images/"),("export_label","labels/"))):
            raise ValueError("Export path does not match its split")
        for field,hash_key in (("export_image","image_sha256"),("export_label","label_sha256")):
            path=(dataset.parent/row[field]).resolve()
            if not path.is_relative_to(dataset.parent) or sha256_file(path)!=row[hash_key]:
                raise ValueError("Exported dataset bytes changed")
        for mapping,key in ((groups,row["leakage_group"]),(sequence_splits,(row["source_dataset"],row["source_sequence"]))):
            if key in mapping and mapping[key]!=row["split"]:
                raise ValueError("Source group leakage")
            mapping[key]=row["split"]
        # Tên nguồn khác chưa bảo đảm ảnh khác: pixel trùng không được qua hai
        # split hoặc nhận hai label khác nhau, dù source_group đang khác.
        digest=row["image_sha256"]
        signature=(row["split"],row["label_sha256"])
        if digest in image_records and image_records[digest]!=signature:
            raise ValueError("Identical image crosses splits or has conflicting labels")
        image_records[digest]=signature
    if len(rows)!=report["samples"] or sha256_file(workspace(config["initial_weights"]))!=initial_weights_digest(config,ready):
        raise ValueError("Sample count or initial weights changed")
    return dataset,rows


def evaluate_frames(model, rows: list[dict], dataset: Path, split: str, config: dict, output: Path) -> dict:
    """Lưu toàn bộ ảnh của split tại ngưỡng khóa sẵn, không chọn riêng case đẹp."""
    import cv2
    import numpy as np
    output.mkdir(parents=True,exist_ok=False)
    records=[];details=[];total=dict(tp=0,fp=0,fn=0)
    negative_frames=negative_fp=0
    for row in (r for r in rows if r["split"]==split):
        path=dataset.parent/row["export_image"]
        image=cv2.imdecode(np.frombuffer(path.read_bytes(),np.uint8),1)
        if image is None:
            raise ValueError("Cannot decode exported evaluation image")
        h,w=image.shape[:2];gt=[]
        for line in (dataset.parent/row["export_label"]).read_text().splitlines():
            _,cx,cy,bw,bh=map(float,line.split())
            gt.append([(cx-bw/2)*w,(cy-bh/2)*h,(cx+bw/2)*w,(cy+bh/2)*h])
        # Truyền mảng ảnh để OpenCV/Ultralytics không vướng Unicode path.
        result=model.predict(source=image,imgsz=config["imgsz"],device=config["device"],
                             conf=config["prediction_confidence"],iou=.7,max_det=100,verbose=False)[0]
        predictions=[dict(xyxy=box,confidence=score) for box,score in zip(
            result.boxes.xyxy.cpu().tolist(),result.boxes.conf.cpu().tolist())]
        matched=match_boxes(gt,predictions,config["matching_iou"])
        for key in total:
            total[key]+=matched[key]
        if not gt:
            negative_frames+=1;negative_fp+=bool(predictions)
        identity=f"{row['source_sequence']}_f{int(row['source_frame']):06d}"
        records.append(dict(source_sequence=row["source_sequence"],source_frame=row["source_frame"],
                            leakage_group=row["leakage_group"],collision_label=row["collision_label"],
                            tp=matched["tp"],fp=matched["fp"],fn=matched["fn"],
                            prediction_count=len(predictions),example=identity+".jpg"))
        details.append(dict(source_sequence=row["source_sequence"],source_frame=row["source_frame"],gt_xyxy=gt,**matched))
        # Xanh lá là GT tác giả, đỏ là dự đoán model; PNG đầu vào giữ sạch.
        for box in gt:
            x1,y1,x2,y2=map(round,box);cv2.rectangle(image,(x1,y1),(x2,y2),(0,255,0),2)
        for pred in predictions:
            x1,y1,x2,y2=map(round,pred["xyxy"]);cv2.rectangle(image,(x1,y1),(x2,y2),(0,0,255),2)
            cv2.putText(image,f"pred {pred['confidence']:.2f}",(x1,max(20,y1-6)),cv2.FONT_HERSHEY_SIMPLEX,.6,(0,0,255),2)
        cv2.putText(image,"GT green | prediction red | IMAGE PILOT",(8,25),cv2.FONT_HERSHEY_SIMPLEX,.6,(255,255,255),2)
        ok,body=cv2.imencode(".jpg",image)
        if not ok:
            raise ValueError("Example encoding failed")
        (output/(identity+".jpg")).write_bytes(body.tobytes())
    precision=total["tp"]/(total["tp"]+total["fp"]) if total["tp"]+total["fp"] else 0.0
    recall=total["tp"]/(total["tp"]+total["fn"]) if total["tp"]+total["fn"] else 0.0
    metrics=dict(**total,precision=precision,recall=recall,f1=2*precision*recall/(precision+recall) if precision+recall else 0.0,
                 confidence=config["prediction_confidence"],matching_iou=config["matching_iou"],
                 negative_frames=negative_frames,negative_frames_with_predictions=negative_fp,
                 negative_frame_false_positive_rate=negative_fp/negative_frames if negative_frames else None,
                 metric_scope="bbox/frame on a tiny held-out source-group pilot; NOT event metrics or false alerts/hour")
    save_csv(output/"cases.csv",records,list(records[0]));save_json(output/"predictions.json",details)
    save_json(output/"metrics.json",metrics)
    return metrics


def validate_resume_inputs(config: dict, config_path: Path, dataset: Path, output: Path) -> Path:
    """Chặn resume nhầm run, config hoặc dataset; không ghi đè run hoàn tất."""
    import psutil
    import yaml
    # Không cho hai tiến trình cùng ghi checkpoint của một run. PID cũ không
    # phải bằng chứng run còn sống; so command line và config của process thật.
    own_pids={os.getpid()}
    try:
        own_pids.update(p.pid for p in psutil.Process().parents())
    except (psutil.Error,OSError):
        pass
    for process in psutil.process_iter(['pid','cmdline']):
        if process.info['pid'] in own_pids:
            continue
        command=process.info.get('cmdline') or []
        if not any(str(arg).replace('\\','/').lower().endswith('/train_b0.py') for arg in command):
            continue
        if '--config' in command:
            index=command.index('--config')
            if index+1<len(command) and workspace(command[index+1])==config_path.resolve():
                raise ValueError('A training process is already running with this config')
    snapshot=output/"requested_config.json"
    last=output/"weights/last.pt"
    args_file=output/"args.yaml"
    if not output.is_dir() or not snapshot.is_file() or not last.is_file() or not args_file.is_file():
        raise ValueError("Resume needs the original run, config snapshot, args.yaml and last.pt")
    if (output/"experiment.json").exists() or (output/"cases_val").exists() or (output/"cases_test").exists():
        raise ValueError("Run is completed or evaluation has started; do not resume training")
    if sha256_file(snapshot)!=sha256_file(config_path):
        raise ValueError("Resume config differs from the locked run snapshot")
    saved=yaml.safe_load(args_file.read_text(encoding="utf-8"))
    prior_patience=recorded_resume_patience(output,config_path)
    for key in TRAIN_KEYS:
        if key in config and str(saved.get(key))!=str(config[key]):
            if key=='patience' and prior_patience is not None and saved.get(key)==prior_patience:
                continue
            raise ValueError(f"Resume trainer argument differs: {key}")
    if Path(saved["data"]).resolve()!=dataset.resolve():
        raise ValueError("Resume dataset differs from the original run")
    return last


def organize_train_previews(output: Path) -> None:
    """Gom ảnh/biểu đồ theo chức năng sau train; giữ CSV, config, checkpoint."""
    groups={output/'train_batches':list(output.glob('train_batch*.jpg')),
            output/'validation_during_training'/'batches':list(output.glob('val_batch*.jpg')),
            output/'validation_during_training'/'curves':list(output.glob('Box*_curve.png'))+list(output.glob('confusion_matrix*.png')),
            output/'training_summary':[p for p in (output/'results.png',output/'labels.jpg') if p.exists()]}
    for target,files in groups.items():
        if any((target/image.name).exists() for image in files):
            raise FileExistsError(f'Preview already exists in {target}')
    for target,files in groups.items():
        if files:
            target.mkdir(parents=True,exist_ok=True)
            for image in files:
                image.rename(target/image.name)


def evaluation_splits(config: dict) -> tuple[str, ...]:
    """Run thử tham số chỉ đo val; test đã xem không dùng để chọn cấu hình."""
    splits=tuple(config.get('evaluation_splits',['val','test']))
    if splits not in (('val',),('val','test')):
        raise ValueError('evaluation_splits must be [val] or [val,test]')
    return splits


def preflight(config_path: Path, config: dict, dataset: Path, rows: list[dict]) -> Path:
    """Kiểm ảnh/nhãn và forward GPU, tuyệt đối không optimizer/backward/train.

    Dựng thử head một class từ checkpoint khởi tạo để kiểm kiến trúc. Model thử
    chỉ ở RAM, không lưu checkpoint và không có kết quả dự đoán tai nạn.
    Bộ nhớ forward không đại diện bộ nhớ backward khi người dùng train thật.
    """
    import math
    import cv2
    import numpy as np
    from collections import Counter
    output=workspace(config['preflight_report'])
    if output.exists():raise FileExistsError('Preflight report exists; preserve evidence')
    if workspace(config['output']).exists():raise FileExistsError('Training output already exists')
    decoded=Counter();boxes=Counter()
    for row in (r for r in rows if r['split'] in ('train','val')):
        image=cv2.imdecode(np.frombuffer((dataset.parent/row['export_image']).read_bytes(),np.uint8),1)
        if image is None:raise ValueError('Cannot decode train/validation image')
        decoded[row['split']]+=1
        lines=(dataset.parent/row['export_label']).read_text().splitlines()
        if bool(lines)!=(row['collision_label']=='positive'):raise ValueError('Positive/negative label mismatch')
        for line in lines:
            cls,cx,cy,w,h=map(float,line.split())
            if not all(math.isfinite(x) for x in (cls,cx,cy,w,h)) or cls!=0 or min(w,h)<=0 or min(cx-w/2,cy-h/2)<-1e-8 or max(cx+w/2,cy+h/2)>1+1e-8:
                raise ValueError('Invalid YOLO bbox')
            boxes[row['split']]+=1
    print(f'Preflight decoded train/val: {dict(decoded)}',flush=True)
    os.environ['YOLO_CONFIG_DIR']=str(ROOT/'.tmp/ultralytics')
    os.environ['YOLO_OFFLINE']='true';os.environ['YOLO_AUTOINSTALL']='false'
    import torch
    import ultralytics
    from ultralytics import YOLO
    from ultralytics.nn.tasks import DetectionModel
    if ultralytics.__version__!=config['ultralytics_version']:raise ValueError('Ultralytics version differs')
    if not torch.cuda.is_available():raise RuntimeError('Configured GPU is unavailable')
    checkpoint=workspace(config['initial_weights']);before=sha256_file(checkpoint)
    original=YOLO(str(checkpoint))
    adapted=DetectionModel(original.model.yaml,nc=1,verbose=False)
    adapted.load(original.model,verbose=False)
    device=torch.device('cuda:'+str(config['device']))
    adapted.to(device).float().eval()
    batch=torch.zeros(config['batch'],3,config['imgsz'],config['imgsz'],device=device)
    torch.cuda.reset_peak_memory_stats(device)
    with torch.inference_mode():
        for _ in range(2):
            result=adapted(batch)
    torch.cuda.synchronize(device)
    assert before==sha256_file(checkpoint)
    record=dict(status='prepared_not_trained',config=config_path.relative_to(ROOT).as_posix(),
        config_sha256=sha256_file(config_path),initial_weights_sha256=before,
        dataset_yaml_sha256=sha256_file(dataset),provenance_sha256=sha256_file(dataset.parent/'provenance.csv'),
        decoded_images=dict(decoded),bbox_counts=dict(boxes),input_shape=list(batch.shape),
        parameters=sum(p.numel() for p in adapted.parameters()),
        peak_forward_allocated_bytes=torch.cuda.max_memory_allocated(device),
        peak_forward_reserved_bytes=torch.cuda.max_memory_reserved(device),
        device=torch.cuda.get_device_name(device),torch=torch.__version__,ultralytics=ultralytics.__version__,
        optimizer_created=False,backward_called=False,training_started=False,checkpoint_written=False,
        test_inference=False,negative_holdout_inference=False,
        limitation='Forward-only memory is not a training VRAM guarantee; no accuracy claim before training.')
    output.parent.mkdir(parents=True,exist_ok=True)
    save_json(output,record)
    print(json.dumps(record,ensure_ascii=False,indent=2))
    return output


def main() -> int:
    parser=argparse.ArgumentParser(description="Train/evaluate a locked basic-image B0 pilot; no dataset downloads")
    parser.add_argument("--config",type=Path,default=Path("configs/b0_pilot.json"))
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check",action="store_true");mode.add_argument("--train",action="store_true")
    mode.add_argument("--preflight",action="store_true",help="Kiểm decode/bbox và forward GPU, không train/backward hoặc lưu checkpoint")
    mode.add_argument("--resume",action="store_true",help="Tiếp tục run dở từ last.pt và optimizer, giữ nguyên config")
    parser.add_argument("--resume-workers",type=int,choices=(0,1,2),default=None,
                        help="Giảm số DataLoader workers khi resume để bớt dùng RAM; không đổi tham số học")
    parser.add_argument('--resume-patience',type=int,default=None,
                        help='Bật early stopping khi resume, ví dụ 15 epoch không tăng mAP50-95; không sửa config gốc')
    args=parser.parse_args();config=json.loads(args.config.read_text(encoding="utf-8"))
    if args.resume_workers is not None and not args.resume:
        parser.error("--resume-workers chỉ dùng cùng --resume")
    if args.resume_patience is not None and (not args.resume or args.resume_patience<1):
        parser.error('--resume-patience phải >=1 và chỉ dùng cùng --resume')
    selected_splits=evaluation_splits(config)
    dataset,rows=check_inputs(config)
    if args.check:
        print(json.dumps(dict(samples=len(rows),splits={s:sum(r["split"]==s for r in rows) for s in ("train","val","test")},status="verified")))
        return 0
    if args.preflight:
        preflight(args.config.resolve(),config,dataset,rows)
        return 0
    output=workspace(config["output"])
    if output.exists() and not args.resume:
        raise FileExistsError("Use a new run name/config; do not overwrite experiments")
    last=validate_resume_inputs(config,args.config,dataset,output) if args.resume else None
    resume_patience=(args.resume_patience if args.resume_patience is not None else
                     recorded_resume_patience(output,args.config)) if args.resume else None
    if args.resume and resume_patience is not None:
        backup=output/'args_before_resume_patience.yaml'
        if not backup.exists():shutil.copy2(output/'args.yaml',backup)
    # Đặt cache trong .tmp và offline trước import; chỉ dùng checkpoint sẵn có.
    os.environ["YOLO_CONFIG_DIR"]=str(ROOT/".tmp/ultralytics")
    os.environ["MPLCONFIGDIR"]=str(ROOT/".tmp/matplotlib")
    os.environ["YOLO_OFFLINE"]="true";os.environ["YOLO_AUTOINSTALL"]="false"
    os.environ["TORCH_HOME"]=str(ROOT/".tmp/torch")
    font=Path(os.environ.get("WINDIR","C:/Windows"))/"Fonts/arial.ttf"
    # Phiên bản đang khóa nối thêm thư mục Ultralytics vào YOLO_CONFIG_DIR.
    # Đặt font hệ thống đúng nơi để các lần chạy sau không tải lại font.
    cache=ROOT/".tmp/ultralytics/Ultralytics";cache.mkdir(parents=True,exist_ok=True)
    if font.exists() and not (cache/"Arial.ttf").exists():
        shutil.copy2(font,cache/"Arial.ttf")
    import torch
    import ultralytics
    from ultralytics import YOLO
    # Ultralytics 8.4.178 thử lại torch.save sau RuntimeError; khi đích là
    # BytesIO, lần đầu có thể đã đóng buffer và lỗi lần sau che nguyên nhân.
    # Gọi bản gốc cho buffer để log đúng lỗi đầu tiên; vẫn giữ retry khi ghi file.
    import io
    from ultralytics.utils import patches as ultra_patches
    retrying_save=torch.save
    def save_with_buffer_diagnostics(*args, **kwargs):
        target=args[1] if len(args)>1 else kwargs.get("f")
        save=ultra_patches._torch_save if isinstance(target,io.BytesIO) else retrying_save
        return save(*args,**kwargs)
    torch.save=save_with_buffer_diagnostics
    if ultralytics.__version__!=config["ultralytics_version"]:
        raise ValueError("Ultralytics version differs from experiment config")
    if config["device"]!="cpu" and not torch.cuda.is_available():
        raise RuntimeError("Configured CUDA device unavailable; use an explicit new CPU config")
    model=YOLO(str(last if args.resume else workspace(config["initial_weights"])))
    if config.get('recipe_revision_manifest'):
        from src.kaggle_recipe import install_callbacks
        install_callbacks(model,config,ROOT)
    start=time.perf_counter()
    if args.resume:
        # Tránh trường hợp Ultralytics tự bắt đầu run mới khi checkpoint đã bị
        # strip optimizer hoặc đã hết epoch; resume phải giữ trạng thái cũ.
        if not model.ckpt or model.ckpt.get("optimizer") is None or not 0 <= model.ckpt.get("epoch",-1) < config["epochs"]-1:
            raise ValueError("last.pt is not an incomplete resumable checkpoint with optimizer")
        # Ultralytics cho phép đổi workers khi resume: batch/optimizer/LR/seed và
        # checkpoint vẫn thuộc cùng run, còn ảnh được nạp ở tiến trình chính nếu =0.
        resume_workers=config["workers"] if args.resume_workers is None else args.resume_workers
        overrides={}
        if resume_patience is not None:
            overrides['patience']=resume_patience
            model.add_callback('on_train_start',lambda trainer:apply_resume_patience(trainer,resume_patience,args.config))
        model.train(resume=True,data=str(dataset),device=config["device"],workers=resume_workers,**overrides)
    else:
        output.mkdir(parents=True,exist_ok=False)
        shutil.copy2(args.config,output/"requested_config.json")
        model.train(data=str(dataset),project=str(output.parent),name=output.name,exist_ok=True,
                    deterministic=True,cache=False,plots=True,save=True,**training_arguments(config))
    organize_train_previews(output)
    checkpoint=output/"weights/best.pt"
    trained=YOLO(str(checkpoint))
    if trained.names!={0:"accident"}:
        raise ValueError("Checkpoint does not expose accident class")
    # Checkpoint chọn theo val trong train; confidence/IoU đã khóa trước run.
    # Test chỉ chạy sau đó, không dùng test để chỉnh model/ngưỡng.
    official={};manual={}
    for split in selected_splits:
        measured=trained.val(data=str(dataset),split=split,device=config["device"],imgsz=config["imgsz"],
                             batch=config["batch"],workers=0,plots=True,project=str(output),name="metrics_"+split)
        official[split]={k:float(v) for k,v in measured.results_dict.items()}
        manual[split]=evaluate_frames(trained,rows,dataset,split,config,output/("cases_"+split))
    history=read_csv(output/"results.csv")
    save_json(output/"experiment.json",dict(scope=config["scope"],config=config,
              config_sha256=sha256_file(args.config),dataset_yaml_sha256=sha256_file(dataset),
              provenance_sha256=sha256_file(dataset.parent/"provenance.csv"),
              initial_weights_sha256=sha256_file(workspace(config["initial_weights"])),
              checkpoint=checkpoint.relative_to(ROOT).as_posix(),checkpoint_sha256=sha256_file(checkpoint),
              epochs_completed=len(history),torch=torch.__version__,ultralytics=ultralytics.__version__,
              device=torch.cuda.get_device_name(0) if config["device"]!="cpu" else "cpu",
              wall_seconds_including_evaluation=time.perf_counter()-start,resumed_from_last=bool(args.resume),
              effective_patience=model.trainer.args.patience,
              resume_policy_history='resume_events.json' if (output/'resume_events.json').exists() else None,
              official_bbox_metrics=official,
              fixed_threshold_metrics=manual,limitations=config["limitations"],
              full_B0_complete=False,temporal_event_evaluation=False))
    print(f"Completed pilot: {output/'experiment.json'}")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
