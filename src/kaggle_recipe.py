"""Công cụ cho thí nghiệm Kaggle đổi recipe nhưng giữ nguyên release dữ liệu.

Đầu vào: config mới, manifest recipe và bundle gốc đã khóa. Đầu ra: kiểm
lineage, kiểm backward/VRAM, chính sách dừng và một dòng metric mỗi epoch.
Module không tự train hoặc tải dữ liệu khi import; trainer gọi các hook.
"""
from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path

from src.data_preparation import sha256_file


def check_revised_inputs(config: dict,root: Path):
    """Kiểm bundle cũ nguyên vẹn rồi cho phép đúng config/code mới đã ghi nhận."""
    from src.training_bundle import check_portable_inputs,safe_path
    revision=json.loads(safe_path(root,config['recipe_revision_manifest']).read_text('utf-8'))
    target=safe_path(root,revision['config_path'])
    if json.loads(target.read_text('utf-8'))!=config or sha256_file(target)!=revision['config_sha256']:
        raise ValueError('Revised config differs from locked recipe')
    base_path=safe_path(root,revision['base_config'])
    if sha256_file(base_path)!=revision['base_config_sha256']:raise ValueError('Base config changed')
    base=json.loads(base_path.read_text('utf-8'))
    for key in ('dataset','label_policy','initial_weights','initial_weights_sha256','portable_bundle_manifest','evaluation_splits'):
        if config.get(key)!=base.get(key):raise ValueError('Recipe revision cannot change data/weights/evaluation: '+key)
    changes={key for key in set(base)|set(config) if base.get(key)!=config.get(key)}
    if changes!=set(revision['changed_fields']):raise ValueError('Unrecorded recipe changes')
    for name,record in revision['code_files'].items():
        if sha256_file(safe_path(root,name))!=record['sha256']:raise ValueError('Runtime code changed: '+name)
    # Không sửa hash cũ để chấp nhận code mới: runtime nằm riêng, tất cả file
    # của bundle gốc vẫn phải vượt checker gốc (ảnh, nhãn, split, provenance).
    return check_portable_inputs(base,root)


class DelayedEarlyStopping:
    """Theo dõi best từ đầu; chỉ đếm chờ dừng sau mốc bắt đầu đã chốt.

    start_epoch=25/patience=25: dù best ở epoch1 cũng không dừng trước epoch50.
    Không reset best checkpoint hoặc dừng vì chỉ mất cải thiện ở đầu run.
    """
    def __init__(self,patience: int,start_epoch: int,*,best_fitness=0.0,best_epoch=0):
        if patience<1 or start_epoch<21:raise ValueError('Require patience>0 and stopping start after epoch20')
        self.patience=patience;self.start_epoch=start_epoch
        self.best_fitness=best_fitness;self.best_epoch=best_epoch;self.possible_stop=False

    def __call__(self,epoch,fitness):
        if fitness is None:return False
        if fitness>self.best_fitness or self.best_fitness==0:
            self.best_fitness=fitness;self.best_epoch=epoch
        delta=epoch-max(self.best_epoch,self.start_epoch)
        self.possible_stop=epoch>self.start_epoch and delta>=self.patience-1
        stop=epoch>self.start_epoch and delta>=self.patience
        if stop:print(f'B0_STOP epoch={epoch} best_epoch={self.best_epoch} patience={self.patience} start_epoch={self.start_epoch}',flush=True)
        return stop


class EpochLogFilter:
    """Ghép chunk SSE, bỏ progress batch, chỉ xuất một kết quả/epoch và lỗi."""
    def __init__(self,prefer_markers=False):
        self.buffer='';self.epoch=None;self.seen=set();self.errors=False;self.notices=set()
        self.prefer_markers=prefer_markers

    def feed(self,text: str,final=False) -> list[str]:
        self.buffer+=text.replace('\r','\n');lines=self.buffer.split('\n')
        self.buffer='' if final else lines.pop()
        result=[]
        for line in lines:
            line=re.sub(r'\x1b\[[0-9;]*[A-Za-z]','',line).strip()
            if not line:continue
            # Ultralytics có thể tự giảm batch sau OOM ở epoch đầu; thông báo
            # việc này nhưng vẫn lọc tiến độ batch, không giấu thay đổi thực tế.
            if 'Reducing to batch=' in line and ('out of memory' in line.lower() or 'memory error' in line.lower()):
                if line not in self.notices:self.notices.add(line);result.append(line)
                continue
            if line.startswith('B0_EPOCH '):
                row=json.loads(line[len('B0_EPOCH '):]);epoch=int(row['epoch'])
                if epoch not in self.seen:
                    self.seen.add(epoch)
                    values=' '.join(f'{label}={100*row[key]:.2f}%' for label,key in (
                        ('P','metrics/precision(B)'),('R','metrics/recall(B)'),('mAP50','metrics/mAP50(B)'),('mAP50-95','metrics/mAP50-95(B)')) if key in row)
                    losses=' '.join(f'{label}={row[key]:.4f}' for label,key in (
                        ('box','train/box_loss'),('cls','train/cls_loss'),('dfl','train/dfl_loss')) if key in row)
                    result.append(f'Epoch {epoch}/{int(row.get("total_epochs",0))} | {losses} | {values}')
                continue
            summary=re.match(r'^Epoch (\d+)(?:/|:)',line)
            if summary:
                epoch=int(summary[1])
                if epoch not in self.seen:self.seen.add(epoch);result.append(line)
                continue
            match=re.match(r'^(\d+)/(\d+)\s+',line)
            if match:self.epoch=int(match[1])
            if '%' in line and re.search(r'\b\d+/\d+\b',line):continue
            match=re.match(r'^all\s+(\d+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*$',line)
            if match and not self.prefer_markers and self.epoch is not None and self.epoch not in self.seen:
                self.seen.add(self.epoch)
                result.append(f'Epoch {self.epoch}: P={match[3]} R={match[4]} mAP50={match[5]} mAP50-95={match[6]}')
            if line.startswith(('Traceback','RuntimeError','ValueError','CUDA out of memory')):self.errors=True
            if line.startswith(('B0_STOP','B0_RESOURCE','B0_RESULT','EarlyStopping:')):
                if line not in self.notices:self.notices.add(line);result.append(line)
            elif self.errors:result.append(line)
        return result


class EpochStream(io.TextIOBase):
    """Lọc stdout của CLI SSE mà không làm mất cơ chế nối lại của SDK."""
    def __init__(self,target):self.target=target;self.parser=EpochLogFilter()
    def write(self,text):
        for line in self.parser.feed(text):self.target.write(line+'\n')
        self.target.flush();return len(text)
    def flush(self):self.target.flush()
    def finish(self):
        for line in self.parser.feed('',final=True):self.target.write(line+'\n')
        self.target.flush()


def backward_probe(trainer,config: dict,root: Path) -> None:
    """Đo 3 bước backward trên bản sao và ảnh/nhãn TRAIN thật, không lưu model.

    Không dùng ảnh tổng hợp, nhãn tự tạo, val/test/reserve hoặc sửa trọng số run.
    Phép đo bao gồm optimizer state, nhưng không bảo đảm mọi batch đều cùng VRAM.
    """
    import copy,gc,time
    import cv2,numpy as np,torch
    from src.training_bundle import load_rows
    state=torch.get_rng_state();cuda_states=torch.cuda.get_rng_state_all()
    dataset=root/config['dataset'];rows=[r for r in load_rows(dataset.parent/'provenance.csv') if r['split']=='train'][:config['batch']]
    images=[];classes=[];boxes=[];indices=[]
    for index,row in enumerate(rows):
        img=cv2.imread(str(dataset.parent/row['export_image']))
        if img is None:raise ValueError('Probe cannot decode train image')
        images.append(cv2.resize(img,(config['imgsz'],config['imgsz']))[:,:,::-1].copy())
        for line in (dataset.parent/row['export_label']).read_text('utf-8').splitlines():
            values=list(map(float,line.split()));classes.append([values[0]]);boxes.append(values[1:]);indices.append(index)
    device=trainer.device;probe=copy.deepcopy(trainer.model).float().train()
    if config['optimizer']=='SGD':
        optimizer=torch.optim.SGD(probe.parameters(),lr=config['lr0'],momentum=config['momentum'],weight_decay=config['weight_decay'])
    elif config['optimizer']=='AdamW':
        optimizer=torch.optim.AdamW(probe.parameters(),lr=config['lr0'],weight_decay=config['weight_decay'])
    else:
        raise ValueError('Unsupported optimizer for resource probe')
    scaler=torch.amp.GradScaler('cuda',init_scale=1024,enabled=config['amp'])
    batch={'img':torch.from_numpy(np.stack(images)).permute(0,3,1,2).to(device).float()/255,
           'cls':torch.tensor(classes,device=device).reshape(-1,1),'bboxes':torch.tensor(boxes,device=device).reshape(-1,4),
           'batch_idx':torch.tensor(indices,device=device)}
    torch.cuda.reset_peak_memory_stats(device);torch.cuda.synchronize(device);start=time.perf_counter()
    try:
        for _ in range(3):
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast('cuda',enabled=config['amp']):loss,_=probe(batch);loss=loss.sum()
            if not torch.isfinite(loss):raise RuntimeError('Non-finite AMP loss; no automatic recipe change')
            scaler.scale(loss).backward();scaler.unscale_(optimizer)
            if any(p.grad is not None and not torch.isfinite(p.grad).all() for p in probe.parameters()):
                raise RuntimeError('Non-finite AMP gradient; no automatic recipe change')
            scaler.step(optimizer);scaler.update()
        torch.cuda.synchronize(device)
        report=dict(status='passed',batch=config['batch'],imgsz=config['imgsz'],amp=config['amp'],steps=3,
            seconds_per_step=(time.perf_counter()-start)/3,peak_allocated_bytes=torch.cuda.max_memory_allocated(device),
            peak_reserved_bytes=torch.cuda.max_memory_reserved(device),source_split='train',checkpoint_written=False,
            real_training_weights_modified=False,scope='resource/finite-loss smoke, not validation or a quality result')
        (Path(trainer.save_dir)/'backward_preflight.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print('B0_RESOURCE '+json.dumps(report),flush=True)
    finally:
        del probe,optimizer,scaler,batch
        gc.collect();torch.cuda.empty_cache();torch.set_rng_state(state);torch.cuda.set_rng_state_all(cuda_states)


def install_callbacks(model,config: dict,root: Path) -> None:
    """Gắn chính sách dừng, đo tài nguyên và dòng CSV cuối epoch cho recipe mới."""
    seen=set()
    def start(trainer):
        old=trainer.stopper
        trainer.stopper=DelayedEarlyStopping(config['patience'],config['early_stopping_start_epoch'],
            best_fitness=old.best_fitness,best_epoch=old.best_epoch)
        backward_probe(trainer,config,root)
    def end(trainer):
        epoch=trainer.epoch+1
        if epoch in seen:return
        path=Path(trainer.save_dir)/'results.csv'
        if not path.exists():return
        with path.open(encoding='utf-8') as stream:rows=list(csv.DictReader(stream))
        if not rows:return
        row={k.strip():float(v) for k,v in rows[-1].items()}
        if int(row['epoch'])!=epoch:return
        row['total_epochs']=trainer.epochs
        seen.add(epoch)
        print('B0_EPOCH '+json.dumps(row,ensure_ascii=False),flush=True)
    model.add_callback('on_train_start',start);model.add_callback('on_fit_epoch_end',end)


RECIPE_CONFIG='configs/b0_s960_adamw_kaggle_v2.json'
RECIPE_RUN='b0_s960_adamw_kaggle_v2'


def prepare_experiment(root: Path, config_path: str=RECIPE_CONFIG, run: str=RECIPE_RUN) -> dict:
    """Tạo notebook/overlay nhỏ, tái dùng Dataset 4GB mà không sửa bundle cũ."""
    import hashlib,ast
    from scripts import kaggle_b0 as base
    folder=root/'outputs/kaggle'/run
    if (folder/'deployment.json').exists():raise FileExistsError('Experiment already submitted; do not replace it')
    config=json.loads((root/config_path).read_text('utf-8'))
    original=json.loads((root/base.CONFIG).read_text('utf-8'))
    cloud=(root/'scripts/kaggle_b0.py').read_text('utf-8')
    cloud=cloud.replace("CONFIG='configs/b0_s960_full_kaggle_v1.json'",f'CONFIG={config_path!r}')
    cloud=cloud.replace("RUN='b0_s960_full_kaggle_v1'",f'RUN={run!r}')
    payload={config_path:(root/config_path).read_bytes().decode('utf-8'),
        'runtime/train_b0.py':(root/'scripts/train_b0.py').read_text('utf-8'),
        'runtime/kaggle_b0.py':cloud,'src/kaggle_recipe.py':Path(__file__).read_text('utf-8')}
    code_files={name:dict(sha256=hashlib.sha256(body.encode()).hexdigest()) for name,body in payload.items() if name.endswith('.py')}
    revision=dict(schema_version=1,config_path=config_path,config_sha256=sha256_file(root/config_path),
        base_config=base.CONFIG,base_config_sha256=sha256_file(root/base.CONFIG),code_files=code_files,
        changed_fields=sorted(k for k in set(config)|set(original) if config.get(k)!=original.get(k)),
        dataset_changed=False,labels_changed=False,splits_changed=False,initial_weights_changed=False)
    payload[config['recipe_revision_manifest']]=json.dumps(revision,ensure_ascii=False,indent=2)+'\n'
    hashes={name:hashlib.sha256(body.encode()).hexdigest() for name,body in payload.items()}
    overlay="""# Chỉ thêm file runtime mới; không ghi đè bất kỳ file nào trong bundle gốc.
import json,hashlib
payload=json.loads(__PAYLOAD__)
expected=json.loads(__HASHES__)
original=json.loads((PROJECT/'data/training_bundle_manifest.json').read_text())
for name,body in payload.items():
    if name in original['files'] or name=='data/training_bundle_manifest.json': raise RuntimeError('Overlay would replace original evidence')
    target=safe_member(PROJECT,name)
    if target.exists(): raise RuntimeError('Overlay file already exists')
    if hashlib.sha256(body.encode()).hexdigest()!=expected[name]: raise RuntimeError('Overlay hash differs')
    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(body.encode('utf-8'))
print('Recipe overlay verified; original data/manifest unchanged',flush=True)
"""
    replacements={'__PAYLOAD__':repr(json.dumps(payload,ensure_ascii=True)),'__HASHES__':repr(json.dumps(hashes))}
    overlay=re.sub('__PAYLOAD__|__HASHES__',lambda match:replacements[match[0]],overlay)
    nb=base.notebook()
    nb['cells'][0]['source']=f"# B0 — thí nghiệm Kaggle mới: {run}\nDữ liệu/nhãn/split và checkpoint đầu giữ nguyên. Optimizer {config['optimizer']}, batch {config['batch']}, AMP {config['amp']}, epochs {config['epochs']}, early stopping sau {config['early_stopping_start_epoch']} với patience {config['patience']}. GPU0, validation; không dùng test/reserve."
    for cell in nb['cells']:
        if cell['cell_type']=='code':cell['source']=cell['source'].replace("PROJECT/'scripts/kaggle_b0.py'","PROJECT/'runtime/kaggle_b0.py'")
    nb['cells'].insert(2,dict(id='recipe-overlay',cell_type='code',metadata={},execution_count=None,outputs=[],source=overlay))
    for cell in nb['cells']:
        if cell['cell_type']=='code':ast.parse(cell['source'])
    metadata=base.read(base.STAGING/'notebook/kernel-metadata.json')
    metadata['code_file']='train_b0.ipynb';metadata['machine_shape']='NvidiaTeslaT4'
    base.write(folder/'notebook/train_b0.ipynb',nb)
    base.write(folder/'notebook/kernel-metadata.json',metadata)
    base.write(folder/'recipe_revision.json',revision)
    receipt=dict(run=run,config_sha256=revision['config_sha256'],notebook_sha256=sha256_file(folder/'notebook/train_b0.ipynb'),
        data_bundle_sha256=base.read(base.STAGING/'dataset/bundle_receipt.json')['archive_sha256'],
        overlay_sha256=hashes,dataset_uploaded=False,status='prepared_not_submitted')
    base.write(folder/'preparation.json',receipt)
    return receipt


def publish_experiment(root: Path, config_path: str=RECIPE_CONFIG, run: str=RECIPE_RUN) -> dict:
    """Chỉ gửi notebook nhỏ của run mới; không gọi Dataset create/version/upload."""
    from scripts import kaggle_b0 as base
    folder=root/'outputs/kaggle'/run;path=folder/'deployment.json'
    if path.exists():
        return dict(message='Submission already recorded; do not launch twice',state=base.read(path))
    receipt=base.read(folder/'preparation.json')
    if sha256_file(root/config_path)!=receipt['config_sha256'] or sha256_file(folder/'notebook/train_b0.ipynb')!=receipt['notebook_sha256']:
        raise ValueError('Prepared experiment changed')
    api=base.api_client()
    status=json.loads(str(api.kernels_status(base.KERNEL_ID)))
    if status['status'] in ('RUNNING','QUEUED'):raise RuntimeError('Another notebook active; do not run in parallel')
    base.verify_remote_dataset(api,folder/'remote_metadata',base.read(base.STAGING/'dataset/bundle_receipt.json'))
    quota=json.loads(api.quota_view().to_json())
    gpu=quota['gpuQuota']
    duration=lambda value:float(re.match(r'[0-9]+(?:\.[0-9]+)?',str(value))[0])
    remaining=duration(gpu['totalTimeAllowed'])-duration(gpu.get('timeUsed','0s'))-duration(gpu.get('timeReserved','0s'))
    if remaining<7200:raise RuntimeError('Less than2hours GPU quota; do not start a long free run')
    state=dict(run=run,phase='submission_pending',config=config_path,config_sha256=receipt['config_sha256'],
        dataset_uploaded=False,free_tier_only=True,quota_snapshot=quota,remaining_gpu_seconds_approx=remaining,
        test_inference=False,reserve_inference=False,monitoring_enabled=False)
    base.write(path,state)
    result=base.push_gpu_notebook(api,folder/'notebook')
    if result is None or result.error:
        state.update(phase='submission_rejected',error=base.safe_server_message(getattr(result,'error',None)))
        base.write(path,state);raise RuntimeError(state['error'])
    state.update(phase='submitted_not_completed',notebook_version=result.version_number,
        notebook_url='https://www.kaggle.com/code/'+base.KERNEL_ID,kernel_submitted=True)
    base.write(path,state)
    if result.invalid_dataset_sources:raise RuntimeError('Submitted with invalid input; do not submit twice')
    api.kernels_pull(base.KERNEL_ID,str(folder/'remote_metadata/notebook'),metadata=True)
    remote=base.read(folder/'remote_metadata/notebook/kernel-metadata.json')
    if remote.get('is_private') is not True:raise RuntimeError('Submitted notebook privacy not verified')
    state['remote_notebook_private_verified']=True
    state['requested_machine_shape']=remote.get('machine_shape')
    state['remote_status']=str(api.kernels_status(base.KERNEL_ID+'/'+str(result.version_number)))
    base.write(path,state)
    return state
