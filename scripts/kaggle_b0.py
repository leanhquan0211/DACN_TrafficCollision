"""Chuẩn bị, gửi và nhận một run B0 PRIVATE trên Kaggle.

Đầu vào: release/source config đã khóa và normal ứng viên có nhãn tác giả.
Đầu ra: ZIP train/val, notebook, receipt và kết quả tải về. prepare/verify chỉ
đọc/đóng gói trên laptop; bootstrap/execute chỉ chạy trong Kaggle có GPU.
publish cần đăng nhập tài khoản; không in token, không theo dõi train liên tục.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.metadata as metadata
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.data_preparation import sha256_file
from src.training_bundle import csv_bytes,full_train_projection,load_rows,materialize_paths,safe_path,verify_bundle
from src.storage_paths import registered_run, registry_data, output_path, run_folder

SOURCE_CONFIG='configs/b0_s960_hardneg_v1.json'
CONFIG='configs/b0_s960_full_kaggle_v1.json'
RUN='b0_s960_full_kaggle_v1'
STAGING=ROOT/'outputs/kaggle'/RUN
DATASET_ID='laqun0211/dacn-b0-full-trainval-v1'
KERNEL_ID='laqun0211/dacn-b0-s960-full-v1'
GPU_IMAGE='gcr.io/kaggle-gpu-images/python@sha256:9a6bcfda6d03b2cd9aa347ee8c1bae62043328ed0f4afe9bda014e4f8bbf9435'


def read(path: Path) -> dict:return json.loads(path.read_text('utf-8'))


def write(path: Path,value: object) -> None:
    """Metadata vận hành thay nguyên tử; artifact gốc không ghi đè."""
    path.parent.mkdir(parents=True,exist_ok=True)
    pending=path.with_suffix(path.suffix+'.tmp')
    pending.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');pending.replace(path)


def frozen_write(path: Path,value: dict) -> None:
    if path.exists():
        if read(path)!=value:raise FileExistsError('Existing locked metadata differs: '+str(path))
    else:write(path,value)


def notebook() -> dict:
    """Notebook nhận cả ZIP lẫn thư mục Kaggle tự giải nén; giữ trainer trong gói."""
    # Hash manifest được chốt trong notebook nhỏ; khi Kaggle giải nén mất ZIP,
    # vẫn đối chiếu được toàn bộ file với cùng snapshot, không cần upload lại.
    with zipfile.ZipFile(STAGING/'dataset/b0_full_bundle.zip') as z:
        manifest_hash=hashlib.sha256(z.read('data/training_bundle_manifest.json')).hexdigest()
    bootstrap='''from pathlib import Path, PurePosixPath
import hashlib, json, os, shutil, subprocess, sys, zipfile, urllib.request
# Python con không dùng backend inline của kernel Kaggle. Agg vẫn xuất PNG
# loss/PR/confusion matrix, không thay mô hình hoặc công thức huấn luyện.
os.environ['MPLBACKEND']='Agg'
if not Path('/kaggle/working').is_dir():
    raise RuntimeError('Notebook này cần chạy trên Kaggle, không train laptop.')
gpu_command=shutil.which('nvidia-smi')
if not gpu_command:
    report={'stage':'gpu_gate','status':'blocked_no_gpu','training_started':False,'reason':'nvidia-smi missing; requested GPU is not proof of allocated GPU'}
    Path('/kaggle/working/gpu_check.json').write_text(json.dumps(report,indent=2))
    raise RuntimeError('Phiên không có nvidia-smi/GPU. Đã lưu gpu_check.json; không cài môi trường hay train CPU.')
gpu=subprocess.run([gpu_command,'--query-gpu=name,memory.total,driver_version','--format=csv,noheader'],capture_output=True,text=True)
if gpu.returncode!=0:
    Path('/kaggle/working/gpu_check.json').write_text(json.dumps({'stage':'gpu_gate','status':'blocked_gpu_command_failed','training_started':False}))
    raise RuntimeError('GPU command thất bại; xem gpu_check.json. Chưa cài môi trường hay train.')
print('GPU được cấp:',gpu.stdout,flush=True)
Path('/kaggle/working/gpu_check.json').write_text(json.dumps({'stage':'gpu_gate','status':'nvidia_smi_passed','gpu_info':gpu.stdout,'training_started':False}))
# Kiểm mạng trước khi đọc/copy vài GB: metadata Internet=True có thể chưa
# phản ánh phiên thật. Không mất thời gian giải nén rồi mới phát hiện lỗi pip.
try:
    with urllib.request.urlopen('https://pypi.org/simple/uv/',timeout=10) as response: response.read(1)
except Exception as error:
    Path('/kaggle/working/startup_check.json').write_text(json.dumps({'status':'blocked_internet','error_type':type(error).__name__,'training_started':False}))
    raise RuntimeError('Phiên chưa truy cập được PyPI. Bật Internet trong Notebook options; không cài môi trường hoặc đọc gói lớn.') from None
Path('/kaggle/working/startup_check.json').write_text(json.dumps({'status':'gpu_and_network_gate_passed','training_started':False}))
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()
def safe_member(root,name):
    p=PurePosixPath(name)
    if not name or p.is_absolute() or '..' in p.parts or chr(92) in name or ':' in name: raise RuntimeError('Đường dẫn gói không an toàn.')
    target=root.joinpath(*p.parts)
    if not target.resolve().is_relative_to(root.resolve()): raise RuntimeError('File vượt thư mục gói.')
    return target
PROJECT=Path('/tmp/DACN_TrafficCollision')
if PROJECT.exists(): raise RuntimeError('Project tạm đã tồn tại. Không chạy chồng; dùng session mới để tránh ghi đè.')
inputs=Path('/kaggle/input')
archives=list(inputs.rglob('b0_full_bundle.zip'))
manifests=list(inputs.rglob('training_bundle_manifest.json'))
if len(archives)==1 and not manifests:
    archive=archives[0]
    receipt=json.loads((archive.parent/'bundle_receipt.json').read_text())
    if digest(archive)!=receipt['archive_sha256']: raise RuntimeError('Bundle SHA khác receipt; không chạy.')
    with zipfile.ZipFile(archive) as z:
        names=z.namelist()
        if len(names)!=len(set(names)): raise RuntimeError('ZIP có member trùng.')
        for name in names: safe_member(PROJECT,name)
        size=sum(x.file_size for x in z.infolist())
        if size>16*2**30 or shutil.disk_usage('/tmp').free<size+6*2**30: raise RuntimeError('Không đủ chỗ trống cho gói + môi trường.')
        z.extractall(PROJECT)
elif not archives and len(manifests)==1:
    manifest_path=manifests[0]
    if digest(manifest_path)!='__MANIFEST_SHA256__': raise RuntimeError('Manifest khác snapshot đã khóa.')
    source=manifest_path.parent.parent
    manifest=json.loads(manifest_path.read_text())
    names=set(manifest['files'])|{'data/training_bundle_manifest.json'}
    actual={p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file()}
    if actual!=names: raise RuntimeError('Gói giải nén thiếu/thừa file.')
    size=sum(item['size_bytes'] for item in manifest['files'].values())
    if size>16*2**30 or shutil.disk_usage('/tmp').free<size+6*2**30: raise RuntimeError('Không đủ chỗ trống cho gói + môi trường.')
    for index,(name,item) in enumerate(manifest['files'].items(),1):
        path=safe_member(source,name)
        if path.stat().st_size!=item['size_bytes'] or digest(path)!=item['sha256']: raise RuntimeError('File khác manifest: '+name)
        if index%1000==0: print('Đã kiểm',index,'file',flush=True)
    # Input Kaggle chỉ đọc; sao chép snapshot đã kiểm vào /tmp để trainer tạo YAML/output.
    for name in sorted(names):
        target=safe_member(PROJECT,name);target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(safe_member(source,name),target)
else:
    raise RuntimeError('Input cần đúng một ZIP hoặc một gói đã giải nén. ZIP='+str(len(archives))+' manifest='+str(len(manifests)))
verified=PROJECT/'data/training_bundle_manifest.json'
if digest(verified)!='__MANIFEST_SHA256__': raise RuntimeError('Manifest sau chuẩn bị khác snapshot.')
print('Đã chuẩn bị',json.loads(verified.read_text())['samples'],'ảnh train/val; chưa bắt đầu train.',flush=True)
'''
    bootstrap=bootstrap.replace('__MANIFEST_SHA256__',manifest_hash)
    cells=[dict(cell_type='markdown',metadata={},source='# B0 PRIVATE — train đầy đủ trên Kaggle\n'
        'Một run mới, không resume hardneg đã xong. Giữ recipe/nhãn/val; thêm420normal train có căn cứ. '
        'GPU0,batch2,FP32,960,SGD0.0003,40max/patience10. Test/reserve không có trong gói. '
        'Bật Internet để cài đúng phiên bản; chọn GPU. Không dùng Run All hai lần trong một session.'),
        dict(cell_type='code',metadata={},execution_count=None,outputs=[],source=bootstrap),
        dict(cell_type='code',metadata={},execution_count=None,outputs=[],source=
             "import subprocess\nsubprocess.run([sys.executable,str(PROJECT/'scripts/kaggle_b0.py'),'bootstrap'],cwd=PROJECT,check=True)\n"),
        dict(cell_type='code',metadata={},execution_count=None,outputs=[],source=
             "B0PY=Path('/tmp/dacn_b0_env/bin/python')\n"
             "os.environ['MPLBACKEND']='Agg'\n"
             "plot_check=\"import matplotlib; import matplotlib.pyplot as plt; assert matplotlib.get_backend().lower()=='agg'; plt.plot([0,1],[0,1]); plt.savefig('/kaggle/working/plot_backend_check.png'); plt.close(); print('Plot backend Agg: passed',flush=True)\"\n"
             "subprocess.run([str(B0PY),'-u','-c',plot_check],cwd=PROJECT,check=True)\n"
             "subprocess.run([str(B0PY),'-u',str(PROJECT/'scripts/kaggle_b0.py'),'execute'],cwd=PROJECT,check=True)\n"),
        dict(cell_type='markdown',metadata={},source='Khi xong, mở Output: `b0_results.zip`, `results_receipt.json`, '
             '`run_status.json` và `live_console.log`. Chỉ trạng thái completed cùng experiment.json hợp lệ mới là train hoàn tất. '
             'Không tự đo test/reserve hoặc thay model B0 đang khóa.')]
    for index,cell in enumerate(cells):cell['id']='b0-cell-'+str(index)
    return dict(nbformat=4,nbformat_minor=5,metadata=dict(kernelspec=dict(display_name='Python 3',language='python',name='python3')),cells=cells)


def runtime_pins() -> str:
    """Khóa dependency thực dùng; torch/CUDA cài riêng đúng phiên bản nguồn."""
    from packaging.requirements import Requirement
    seen=set();queue=['ultralytics','lap','filelock','fsspec','jinja2','networkx','sympy','setuptools'];lines=[]
    while queue:
        name=queue.pop(0).lower().replace('_','-')
        if name in seen or name in ('torch','torchvision'):continue
        seen.add(name);dist=metadata.distribution(name);lines.append(dist.metadata['Name']+'=='+dist.version)
        for dependency in dist.requires or []:
            r=Requirement(dependency)
            if r.marker is None or r.marker.evaluate({'extra':''}):queue.append(r.name)
    return '\n'.join(sorted(lines,key=str.lower))+'\n'


def prepare() -> None:
    """Đóng gói allowlist trực tiếp vào ZIP, không nhân đôi raw/dataset trên đĩa."""
    from scripts.train_b0 import check_inputs,TRAIN_KEYS
    source=read(ROOT/SOURCE_CONFIG);dataset,base=check_inputs(source)
    completed=read(ROOT/source['output']/'experiment.json')
    if sha256_file(ROOT/source['output']/'weights/best.pt')!=completed['checkpoint_sha256']:
        raise ValueError('Completed hardneg checkpoint changed')
    candidates_path=ROOT/'outputs/audits/b0_hard_negative_sources_v1/normal_manifest.json'
    groups_path=candidates_path.parent/'groups_before_mining.json'
    candidates=read(candidates_path);groups=read(groups_path)
    if sha256_file(candidates_path)!=groups['candidate_manifest_sha256']:raise ValueError('Candidate evidence changed')
    rows,added=full_train_projection(base,candidates,groups)
    if len(rows)!=2988 or len(added)!=420:raise ValueError('Expected2681train+307val with420additional normal frames')
    if (ROOT/'outputs/training'/RUN).exists():raise FileExistsError('New run output already exists')
    config=dict(source,scope='kaggle_full_verified_train_candidates_same_recipe',
        dataset='data/kaggle_full/dataset.yaml',release_key='kaggle_full_pilot_release',
        label_policy='configs/b0_kaggle_full_label_policy.json',initial_weights='weights/initial.pt',
        output='outputs/training/'+RUN,preflight_report='outputs/kaggle_preflight.json',
        portable_bundle_manifest='data/training_bundle_manifest.json',
        source_config=SOURCE_CONFIG,source_config_sha256=sha256_file(ROOT/SOURCE_CONFIG),
        migration_note='User authorizes full verified data:all60normal candidates/14already-assigned train clips; +420normal, no new independent events. Old train/val bytes/splits retained; test/reserve media excluded. Same source checkpoint and all TRAIN_KEYS. GPU0 only; no automatic batch/AMP/epoch tuning.',
        hardware_decision='Kaggle allocated GPU0 only, samebatch2/FP32/workers0/960 as source. Clean Python3.12.10 and pinned Torch2.11.0+cu128/Ultralytics8.4.178; GPU model/VRAM/driver recorded, not guaranteed faster. No CPU fallback or automatic OOM tuning.',
        training_mode='One new Kaggle run, not resume of completed hardneg and not initialization from the newly trained hardneg best; initial checkpoint follows the locked source recipe.',
        limitations='New data-selection/environment experiment, not a pure hardware reproduction or promised metric gain. No test/reserve inference; old checkpoints/operating point unchanged. GPU/Python/CUDA recorded; do not resume completed local run.')
    config.pop('reference_experiments',None);config.pop('reference_validation_output',None)
    frozen_write(ROOT/CONFIG,config)
    policy=read(ROOT/source['label_policy'])
    policy.update(policy_version='b0_kaggle_full_normal_candidates_v1',
        additional_negative_selection='All60verified candidates per14preassigned train clips, instead of30; +420negative frames. Same original validation, no test/reserve media.',
        limitations=policy['limitations']+' Additional frames are correlated; no extra independent collision events or camera-independence claim.')
    policy['negative_sources'][-1]='New24author-normal TAD clips:14train useall60verified candidates each,3validation retain30uniform each,4reserve excluded and3possible-consumed-camera clips excluded. Source assignments frozen before mining; no new pseudo-labels.'
    frozen_write(ROOT/config['label_policy'],policy)
    upload=STAGING/'dataset';upload.mkdir(parents=True,exist_ok=True)
    archive=upload/'b0_full_bundle.zip'
    if archive.exists():raise FileExistsError('Bundle exists; use verify/publish instead of overwriting')
    files={};memory={}
    def source_file(name: str,path: Path):
        safe_path(ROOT,name)
        if name in files or name in memory:raise ValueError('Duplicate package file')
        files[name]=path
    def data(name: str,value: bytes):
        safe_path(ROOT,name)
        if name in files or name in memory:raise ValueError('Duplicate package file')
        memory[name]=value
    for name in ('scripts/train_b0.py','scripts/kaggle_b0.py','src/data_preparation.py','src/training_bundle.py',CONFIG,config['label_policy']):
        source_file(name,ROOT/name)
    for name,path in {'metadata/source_config.json':ROOT/SOURCE_CONFIG,
        'metadata/source_provenance.csv':dataset.parent/'provenance.csv',
        'metadata/source_report.json':dataset.parent/'report.json','metadata/source_dataset.yaml':dataset,
        'metadata/normal_candidates.json':candidates_path,'metadata/groups_before_mining.json':groups_path,
        'metadata/source_index.csv':ROOT/'data/registries/b0_s960_hardneg_v1_index.csv',
        'metadata/source_split.csv':ROOT/'data/registries/b0_s960_hardneg_v1_split.csv',
        'weights/initial.pt':ROOT/source['initial_weights']}.items():source_file(name,path)
    data('requirements-kaggle.lock',runtime_pins().encode())
    data('DATA_SOURCES.md',('PRIVATE project training snapshot. Original author rights apply; not a public relicense.\n'
         'ACCIDENT v9:https://www.kaggle.com/datasets/picekl/accident/versions/9\n'
         'TAD:https://github.com/UnicomAI/UnicomBenchmark/tree/main/TADBench\n'
         'UA-DETRAC:https://detrac-db.rit.albany.edu/\n'
         'Ultralytics code/pretrained ancestry:https://github.com/ultralytics/ultralytics (AGPL-3.0)\n'
         'Positive bbox retained only at author impact frames. Normal labels from author/reviewed scope, not predictions.\n').encode())
    data('data/kaggle_full/provenance.csv',csv_bytes(rows,list(base[0])))
    data('data/kaggle_full/split.csv',csv_bytes([
        {k:r[k] for k in ('source_dataset','source_sequence','source_frame','split')} for r in rows],
        ['source_dataset','source_sequence','source_frame','split']))
    old_keys={(r['source_dataset'],r['source_sequence'],int(r['source_frame'])) for r in base}
    for r in rows:
        original=(r['source_dataset'],r['source_sequence'],int(r['source_frame'])) in old_keys
        image=dataset.parent/r['export_image'] if original else ROOT/r['source_path']
        if sha256_file(image)!=r['image_sha256']:raise ValueError('Image source differs from provenance')
        source_file('data/kaggle_full/'+r['export_image'],image)
        if original:source_file('data/kaggle_full/'+r['export_label'],dataset.parent/r['export_label'])
        else:data('data/kaggle_full/'+r['export_label'],b'')
    size=sum(p.stat().st_size for p in files.values())+sum(map(len,memory.values()))
    if shutil.disk_usage(STAGING).free<size+2*2**30:raise OSError('Not enough space for bundle')
    records={name:dict(size_bytes=p.stat().st_size,sha256=sha256_file(p)) for name,p in files.items()}
    records.update({name:dict(size_bytes=len(body),sha256=hashlib.sha256(body).hexdigest()) for name,body in memory.items()})
    manifest=dict(schema_version=1,config_path=CONFIG,config_sha256=sha256_file(ROOT/CONFIG),files=records,
        samples=len(rows),split_counts=dict(Counter(r['split'] for r in rows)),added_normal_frames=len(added),
        original_train_val_frames=2568,validation_unchanged=True,new_independent_events_added=0,
        recipe_keys=list(TRAIN_KEYS),source_config_sha256=sha256_file(ROOT/SOURCE_CONFIG),
        test_media_included=False,reserve_media_included=False,secret_files_included=False)
    data('data/training_bundle_manifest.json',(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode())
    # PNG/PT đã nén: ZIP_STORED giảm CPU laptop; text nhỏ nén riêng. Không tải raw.
    with zipfile.ZipFile(archive,'x',allowZip64=True) as z:
        for i,(name,p) in enumerate(sorted(files.items()),1):
            z.write(p,name,compress_type=zipfile.ZIP_STORED if p.suffix in ('.png','.pt') else zipfile.ZIP_DEFLATED)
            if i%1000==0:print('Packed',i,'files',flush=True)
        for name,body in sorted(memory.items()):z.writestr(name,body,compress_type=zipfile.ZIP_DEFLATED)
    receipt=dict(status='prepared_not_uploaded',dataset_id=DATASET_ID,kernel_id=KERNEL_ID,
        archive_sha256=sha256_file(archive),archive_bytes=archive.stat().st_size,samples=len(rows),
        split_counts=manifest['split_counts'],added_normal_frames=len(added),
        config_sha256=manifest['config_sha256'],run=RUN,private_required=True,
        old_hardneg_checkpoint_sha256=completed['checkpoint_sha256'],training_launched=False)
    frozen_write(upload/'bundle_receipt.json',receipt)
    frozen_write(upload/'dataset-metadata.json',dict(title='DACN B0 Full Trainval V1',id=DATASET_ID,
        licenses=[dict(name='other')],description='PRIVATE verified project train/val snapshot. Mixed original-source licenses apply separately; original author rights retained. No new redistribution license is granted. No test/reserve media. Sources/provenance in bundle. Not a public dataset release.'))
    kernel=STAGING/'notebook';kernel.mkdir(exist_ok=True)
    frozen_write(kernel/'train_b0.ipynb',notebook())
    frozen_write(kernel/'kernel-metadata.json',dict(id=KERNEL_ID,title='DACN B0 S960 Full V1',
        code_file='train_b0.ipynb',language='python',kernel_type='notebook',is_private=True,enable_gpu=True,
        enable_internet=True,dataset_sources=[DATASET_ID],competition_sources=[],kernel_sources=[],model_sources=[]))
    print(json.dumps(receipt,ensure_ascii=False,indent=2),flush=True)


def require_kaggle() -> Path:
    """Không cho nhầm lệnh cloud thành train nặng trên laptop."""
    working=Path('/kaggle/working')
    if os.name!='posix' or not working.is_dir():raise RuntimeError('Cloud execution is allowed only inside Kaggle')
    return working


def bootstrap() -> None:
    """Cài environment riêng trong /tmp, pin phiên bản thay vì upgrade mặc định."""
    require_kaggle()
    venv=Path('/tmp/dacn_b0_env');python=venv/'bin/python'
    if venv.exists():raise FileExistsError('Environment already exists; do not run bootstrap twice')
    # Kaggle image có thể dùng Python3.13. Tạo Python3.12.10 riêng bằng uv;
    # venv sạch tránh tự dùng Albumentations/integration có sẵn làm lệch recipe.
    uv_dir=Path('/tmp/dacn_uv')
    subprocess.run([sys.executable,'-m','pip','install','--target',str(uv_dir),'--no-deps','uv==0.13.4'],check=True)
    env=os.environ.copy();env['PYTHONPATH']=str(uv_dir)
    env['UV_PYTHON_INSTALL_DIR']='/tmp/dacn_python';env['UV_CACHE_DIR']='/tmp/dacn_uv_cache'
    subprocess.run([sys.executable,'-m','uv','venv','--python','3.12.10','--seed',str(venv)],env=env,check=True)
    # Torch/CUDA pin riêng; không đổi batch/AMP nếu driver hoặc quota không phù hợp.
    subprocess.run([str(python),'-m','pip','install','torch==2.11.0+cu128','torchvision==0.26.0+cu128',
        '--index-url','https://download.pytorch.org/whl/cu128'],check=True)
    subprocess.run([str(python),'-m','pip','install','--no-deps','-r',str(ROOT/'requirements-kaggle.lock')],check=True)
    print('Pinned cloud environment prepared; no training yet.',flush=True)


def execute() -> None:
    """Kiểm GPU/full data/forward rồi chạy đúng một run; luôn giữ log/kết quả."""
    working=require_kaggle();config=read(ROOT/CONFIG)
    if (ROOT/config['output']).exists():raise FileExistsError('Cloud run already exists; no resume/overwrite')
    os.environ['YOLO_OFFLINE']='true';os.environ['YOLO_AUTOINSTALL']='false'
    os.environ['WANDB_MODE']='disabled';os.environ['COMET_MODE']='DISABLED'
    os.environ['MPLBACKEND']='Agg'
    os.environ['YOLO_CONFIG_DIR']=str(ROOT/'.tmp/ultralytics');os.environ['MPLCONFIGDIR']=str(ROOT/'.tmp/matplotlib')
    import torch,ultralytics
    if sys.version_info[:3]!=(3,12,10):raise RuntimeError('Python differs from locked3.12.10')
    for line in (ROOT/'requirements-kaggle.lock').read_text('utf-8').splitlines():
        package,version=line.split('==',1)
        if metadata.version(package)!=version:raise RuntimeError('Pinned dependency mismatch: '+package)
    if ultralytics.__version__!=config['ultralytics_version']:raise RuntimeError('Ultralytics version mismatch')
    if torch.__version__!='2.11.0+cu128' or torch.version.cuda!='12.8':raise RuntimeError('Torch/CUDA differs from locked setup')
    if not torch.cuda.is_available():raise RuntimeError('No CUDA GPU allocated; will not train on CPU')
    materialize_paths(ROOT,config)
    environment=dict(python=sys.version,torch=torch.__version__,torch_cuda=torch.version.cuda,
        ultralytics=ultralytics.__version__,gpu=torch.cuda.get_device_name(0),gpu_count=torch.cuda.device_count(),
        gpu_vram_bytes=torch.cuda.get_device_properties(0).total_memory,device_used='0',batch=config['batch'],amp=config['amp'],
        pip_freeze=subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True),
        resource_note=config.get('hardware_decision','GPU0 only; locked recipe, no automatic resource tuning.'))
    write(working/'runtime_environment.json',environment)
    state=dict(status='preflight',run=RUN,training_process_started=False,training_completed=False,
        test_inference=False,reserve_inference=False,config_sha256=sha256_file(ROOT/CONFIG))
    write(working/'run_status.json',state)
    def call(mode):
        command=[sys.executable,'-u',str(ROOT/config.get('trainer_entrypoint','scripts/train_b0.py')),'--config',str(ROOT/CONFIG),mode]
        epoch_filter=None
        if config.get('epoch_logging_only') and mode=='--train':
            from src.kaggle_recipe import EpochLogFilter
            epoch_filter=EpochLogFilter(prefer_markers=True)
        with (working/'live_console.log').open('a',encoding='utf-8') as log:
            log.write('\nMODE '+mode+'\n');log.flush()
            process=subprocess.Popen(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace')
            for line in process.stdout:
                log.write(line);log.flush()
                if epoch_filter:
                    for summary in epoch_filter.feed(line):print(summary,flush=True)
                else:print(line,end='',flush=True)
            if epoch_filter:
                for summary in epoch_filter.feed('',final=True):print(summary,flush=True)
            if process.wait():raise RuntimeError('Training tool failed during '+mode+'; see live_console.log')
    try:
        call('--check');call('--preflight')
        state.update(status='training',training_process_started=True);write(working/'run_status.json',state)
        call('--train')
        experiment=read(ROOT/config['output']/'experiment.json')
        if experiment['config_sha256']!=sha256_file(ROOT/CONFIG):raise ValueError('Completed run config differs')
        if experiment['checkpoint_sha256']!=sha256_file(ROOT/experiment['checkpoint']):raise ValueError('Completed checkpoint differs')
        state.update(status='completed',training_completed=True,epochs_completed=experiment['epochs_completed'])
        print('B0_RESULT '+json.dumps(experiment['official_bbox_metrics']),flush=True)
    except Exception as error:
        state.update(status='failed',error_type=type(error).__name__,error=str(error));raise
    finally:
        write(working/'run_status.json',state)
        out=ROOT/config['output'];out.mkdir(parents=True,exist_ok=True)
        for p in ('runtime_environment.json','run_status.json','live_console.log'):
            if (working/p).exists():shutil.copy2(working/p,out/p)
        if (ROOT/config['preflight_report']).exists():shutil.copy2(ROOT/config['preflight_report'],out/'preflight.json')
        if config.get('recipe_revision_manifest'):
            shutil.copy2(ROOT/config['recipe_revision_manifest'],out/'recipe_revision.json')
        contents={p.relative_to(out).as_posix():dict(sha256=sha256_file(p),size_bytes=p.stat().st_size) for p in out.rglob('*') if p.is_file()}
        write(out/'artifacts_manifest.json',dict(run=RUN,config_sha256=sha256_file(ROOT/CONFIG),files=contents,status=state['status']))
        target=working/'b0_results.zip'
        with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
            for p in out.rglob('*'):
                if p.is_file():z.write(p,RUN+'/'+p.relative_to(out).as_posix())
        write(working/'results_receipt.json',dict(archive_sha256=sha256_file(target),archive_bytes=target.stat().st_size,
            run=RUN,config_sha256=sha256_file(ROOT/CONFIG),status=state['status'],training_completed=state['training_completed']))


def credentials_present() -> bool:
    """Chỉ kiểm sự tồn tại; không đọc/in token hoặc tìm bí mật toàn máy."""
    folder=Path(os.environ.get('KAGGLE_CONFIG_DIR',str(Path.home()/'.kaggle')))
    return bool(os.environ.get('KAGGLE_API_TOKEN') or (os.environ.get('KAGGLE_USERNAME') and os.environ.get('KAGGLE_KEY'))
        or any((folder/n).is_file() for n in ('kaggle.json','access_token'))
        or (Path.home()/'.kaggle/credentials.json').is_file())


def api_client():
    if not credentials_present():raise RuntimeError('AUTHENTICATION_REQUIRED: run Kaggle OAuth login locally; never send tokens in chat.')
    # CLI được cài riêng trong .tmp hoặc người dùng gọi bằng environment KaggleCLI.
    try:import kaggle
    except ImportError:
        candidates=[ROOT/'.tmp/kaggle_cli_env/Lib/site-packages']
        for path in candidates:
            if path.is_dir():sys.path.insert(0,str(path))
        import kaggle
    api=kaggle.api;api.authenticate()
    username=api.get_config_value('username')
    if username!='laqun0211':raise RuntimeError('Authenticated Kaggle account must be laqun0211')
    return api


def safe_server_message(value: object) -> str:
    """Chỉ giữ thông báo ngắn; che URL ký và giá trị xác thực trước khi ghi log."""
    message=str(value)
    message=re.sub(r'https?://\S+', '[URL omitted]', message)
    message=re.sub(r'(?i)(bearer\s+)\S+', r'\1[REDACTED]', message)
    message=re.sub(r'(?i)((?:token|password|authorization|api[_-]?key)\s*[=:]\s*)\S+', r'\1[REDACTED]', message)
    return message[:1000]


def dataset_info(document: dict) -> dict:
    """SDK có thể bọc metadata trong info; không suy ra PRIVATE khi thiếu trường."""
    info=document.get('info',document)
    if not isinstance(info,dict):raise ValueError('Invalid remote Dataset metadata')
    return info


def verify_remote_dataset(api,folder: Path,receipt: dict) -> dict:
    """Chỉ tải metadata và receipt nhỏ, xác minh đúng gói PRIVATE trước khi gửi train."""
    api.dataset_metadata(DATASET_ID,str(folder))
    remote=dataset_info(read(folder/'dataset-metadata.json'))
    if remote.get('isPrivate',remote.get('is_private')) is not True:
        raise RuntimeError('Cannot verify Dataset is PRIVATE; notebook not submitted')
    # Kiểm chủ sở hữu/slug khi server trả trường; receipt ràng buộc gói đã khóa.
    owner,slug=DATASET_ID.split('/')
    if remote.get('ownerUser',owner)!=owner or remote.get('datasetSlug',slug)!=slug:
        raise ValueError('Remote Dataset identity differs')
    api.dataset_download_file(DATASET_ID,'bundle_receipt.json',path=str(folder),force=True,quiet=True)
    if read(folder/'bundle_receipt.json').get('archive_sha256')!=receipt['archive_sha256']:
        raise RuntimeError('Existing Dataset receipt differs; no overwrite or notebook launch')
    return remote


def push_gpu_notebook(api,folder: Path,*,no_run: bool=False):
    """Gửi rõ image GPU và kiểu thực thi; metadata T4 không chứng minh cấp GPU."""
    meta=read(folder/'kernel-metadata.json')
    if meta.get('is_private') is not True or meta.get('dataset_sources')!=[DATASET_ID]:
        raise ValueError('Notebook privacy/input differs')
    if meta.get('enable_gpu') is not True:raise ValueError('GPU must be explicitly requested')
    from kagglesdk.kernels.types.kernels_api_service import ApiSaveKernelRequest
    from kagglesdk.kernels.types.kernels_enums import KernelExecutionType
    request=ApiSaveKernelRequest()
    request.slug=meta['id'];request.new_title=meta['title']
    request.text=json.dumps(read(safe_path(folder,meta['code_file'])),ensure_ascii=False)
    request.language='python';request.kernel_type='notebook'
    request.is_private=True;request.enable_gpu=True;request.enable_tpu=False;request.enable_internet=True
    request.dataset_data_sources=[DATASET_ID];request.machine_shape='NvidiaTeslaT4'
    # Bản chỉ lưu sẽ được người dùng chọn Accelerator trên UI; để Kaggle chọn
    # image mới phù hợp phần cứng, không giữ pin CPU từ phiên lỗi trước.
    if no_run:request.docker_image_pinning_type='latest'
    else:request.docker_image=GPU_IMAGE;request.docker_image_pinning_type='original'
    request.kernel_execution_type=KernelExecutionType.QUICK_SAVE if no_run else KernelExecutionType.SAVE_AND_RUN_ALL
    with api.build_kaggle_client() as client:
        return client.kernels.kernels_api_client.save_kernel(request)


def publish(allow_reupload: bool=False) -> None:
    """Tạo PRIVATE Dataset/Notebook; idempotent để không tự chạy vòng thứ hai."""
    receipt=read(STAGING/'dataset/bundle_receipt.json')
    if sha256_file(STAGING/'dataset/b0_full_bundle.zip')!=receipt['archive_sha256']:raise ValueError('Upload bundle changed')
    state_path=STAGING/'deployment.json'
    state=read(state_path) if state_path.exists() else dict(dataset_id=DATASET_ID,kernel_id=KERNEL_ID,
        archive_sha256=receipt['archive_sha256'],dataset_created=False,kernel_submitted=False,private_required=True)
    if state['archive_sha256']!=receipt['archive_sha256']:raise ValueError('Do not replace an already submitted experiment')
    if state['kernel_submitted']:
        print('Notebook already submitted; no second launch.',flush=True);return
    kernel=read(STAGING/'notebook/kernel-metadata.json')
    if kernel['is_private'] is not True or kernel['dataset_sources']!=[DATASET_ID]:raise ValueError('Notebook privacy/data source changed')
    try:
        api=api_client()
        if not state['dataset_created']:
            # Upload thành công mới chỉ là đưa blob lên server. Nếu lần trước bị
            # chặn, đối chiếu Dataset/receipt trước; không tự gửi lại cả 4 GB.
            if state.get('phase')=='submission_blocked':
                verification=STAGING/'recovery_metadata'
                try:
                    api.dataset_metadata(DATASET_ID,str(verification))
                except Exception:
                    if not allow_reupload:
                        raise RuntimeError('Previous upload failed; remote Dataset cannot be verified. No re-upload performed. Inspect Kaggle Datasets and docs/kaggle_training.md; --allow-reupload explicitly permits another full upload.') from None
                else:
                    verify_remote_dataset(api,verification,receipt)
                    state.update(dataset_created=True,phase='dataset_recovered',dataset_url='https://www.kaggle.com/datasets/'+DATASET_ID)
                    write(state_path,state)
        if not state['dataset_created']:
            result=api.dataset_create_new(str(STAGING/'dataset'),public=False,convert_to_csv=False,dir_mode='skip')
            if result is None or getattr(result,'error',None) or str(result.status).lower()!='ok':
                raise RuntimeError('Dataset creation rejected: '+safe_server_message(getattr(result,'error',None) or 'empty response/status='+str(getattr(result,'status',None))))
            state.update(dataset_created=True,dataset_url='https://www.kaggle.com/datasets/'+DATASET_ID,phase='dataset_created')
            state['dataset_create_response']={key:str(getattr(result,key,'')) for key in ('ref','url','status')}
            write(state_path,state)
        # Ngay sau tạo, quyền đọc/trạng thái có thể chưa sẵn sàng. Dừng an toàn
        # và dùng lại Dataset ở lần gọi sau; tuyệt đối không gửi lại ZIP vì 403.
        try:status=str(api.dataset_status(DATASET_ID))
        except Exception as error:
            response=getattr(error,'response',None)
            if getattr(response,'status_code',None) not in (403,404):raise
            state.update(phase='dataset_access_pending',dataset_status='unavailable',
                error_message=safe_server_message('Dataset created; status returned HTTP '+str(response.status_code)),
                next_action='Run publish again later WITHOUT --allow-reupload. If persistent, check Dataset access; do not re-upload.')
            write(state_path,state)
            print(json.dumps(state,ensure_ascii=False,indent=2));return
        if status.lower() not in ('ready','datasetstatus.ready'):
            state.update(phase='dataset_processing',dataset_status=status);write(state_path,state)
            print('Dataset uploaded but processing. Re-run publish later; no training submitted yet.');return
        verification=STAGING/'remote_metadata'
        verify_remote_dataset(api,verification,receipt)
        state.update(remote_dataset_private_verified=True,remote_receipt_verified=True,dataset_status=status)
        for key in ('error_message','error_type','next_action'):state.pop(key,None)
        write(state_path,state)
        result=push_gpu_notebook(api,STAGING/'notebook')
        if result is None or getattr(result,'error',None):raise RuntimeError('Notebook submission rejected: '+safe_server_message(getattr(result,'error',None) or 'empty response'))
        state.update(kernel_submitted=True,phase='submitted_not_completed',notebook_url='https://www.kaggle.com/code/'+KERNEL_ID,
            monitoring_enabled=False,notebook_version=getattr(result,'version_number',None),requested_gpu_image=GPU_IMAGE)
        # Ghi đã submit TRƯỚC status request: lỗi mạng ở status không được làm
        # lần gọi sau gửi thêm một thí nghiệm ngoài quyền một-run của người dùng.
        write(state_path,state)
        if getattr(result,'invalidDatasetSources',None) or getattr(result,'invalid_dataset_sources',None):
            raise RuntimeError('Notebook submitted with invalid Dataset input; do not automatically resubmit')
        api.kernels_pull(KERNEL_ID,str(verification/'notebook'),metadata=True)
        if read(verification/'notebook/kernel-metadata.json').get('is_private') not in (True,'true'):
            raise RuntimeError('Notebook privacy could not be verified after submission')
        state['remote_notebook_private_verified']=True
        state['remote_status']=str(api.kernels_status(KERNEL_ID))
        write(state_path,state);print(json.dumps(state,ensure_ascii=False,indent=2))
    except Exception as error:
        # Giữ lỗi gốc đã lọc; không dump request/header/credential. Trước đây chỉ
        # ghi RuntimeError nên không phân biệt được lỗi tạo Dataset với hết quota.
        response=getattr(error,'response',None)
        detail=str(error) if response is None else 'HTTP '+str(response.status_code)
        if response is not None:
            try:
                body=response.json();detail+=' '+str(body.get('message',body.get('error','')))
            except (ValueError,AttributeError):pass
        state.update(phase='authentication_required' if not credentials_present() else 'submission_blocked',error_type=type(error).__name__,
            error_message=safe_server_message(detail),
            next_action=('Dataset already created: retry publish WITHOUT --allow-reupload; no ZIP upload is needed.' if state.get('dataset_created')
                else 'See docs/kaggle_training.md; publish will not repeat a failed full upload without --allow-reupload.'))
        write(state_path,state)
        print(json.dumps(state,ensure_ascii=False,indent=2));raise RuntimeError(state['error_message']) from None


def fetch(version: int | None=None, *, resume_download: bool=False) -> None:
    """Kiểm hash toàn bộ ZIP rồi đặt bản tải mới vào baseline B0 canonical."""
    api=api_client();download=STAGING/'download'
    if download.exists():
        if not resume_download:raise FileExistsError('Download folder exists; preserve evidence; use --resume-download only for an interrupted download')
        allowed={'b0_results.zip','b0_results.zip.kaggle-partial','results_receipt.json','results_receipt.json.kaggle-partial'}
        if any(p.is_symlink() or not p.is_file() or p.name not in allowed for p in download.iterdir()):
            raise ValueError('Unexpected file in download folder; preserve it and inspect manually')
    else:download.mkdir(parents=True)
    entry=registered_run(ROOT,RUN)
    if entry is None or entry.get('baseline')!='B0':raise ValueError('Register Kaggle run and canonical version before fetch')
    destination=output_path(ROOT,'baseline',entry['version'],baseline='B0')
    if run_folder(ROOT,RUN) is not None or destination.exists():raise FileExistsError('Local result already exists; no overwrite')
    api.kernels_output(KERNEL_ID+('/'+str(version) if version is not None else ''),str(download),file_pattern=r'(b0_results\.zip|results_receipt\.json)$',quiet=False)
    archive=download/'b0_results.zip';receipt=read(download/'results_receipt.json')
    if receipt['run']!=RUN or receipt['config_sha256']!=sha256_file(ROOT/CONFIG):raise ValueError('Wrong experiment output')
    if sha256_file(archive)!=receipt['archive_sha256']:raise ValueError('Downloaded archive differs')
    pending=destination.with_name(destination.name+'.partial')
    if pending.exists():raise FileExistsError('Partial extraction exists; inspect before retry')
    with zipfile.ZipFile(archive) as z:
        if len(z.namelist())!=len(set(z.namelist())):raise ValueError('Duplicate result member')
        for name in z.namelist():
            safe_path(ROOT,name)
            if not name.startswith(RUN+'/'):raise ValueError('Unexpected result path')
        manifest=json.loads(z.read(RUN+'/artifacts_manifest.json'))
        if set(z.namelist())!={RUN+'/'+p for p in manifest['files']}|{RUN+'/artifacts_manifest.json'}:
            raise ValueError('Result allowlist differs')
        for name,info in manifest['files'].items():
            body=z.read(RUN+'/'+name)
            if len(body)!=info['size_bytes'] or hashlib.sha256(body).hexdigest()!=info['sha256']:raise ValueError('Result file changed')
        if receipt['training_completed']:
            experiment=json.loads(z.read(RUN+'/experiment.json'))
            if hashlib.sha256(z.read(RUN+'/weights/best.pt')).hexdigest()!=experiment['checkpoint_sha256']:
                raise ValueError('Best checkpoint differs from experiment')
        # ZIP lịch sử có tiền tố RUN/; giải nén sang thư mục version mới mà
        # không đổi byte checkpoint, rồi rename nguyên tử khi đã ghi xong.
        pending.mkdir(parents=True,exist_ok=False)
        for member in z.infolist():
            relative=Path(member.filename).relative_to(RUN)
            # ZIP dùng dấu /; Path trên Windows đổi sang \\ nên phải trả về POSIX cho safe_path.
            target=safe_path(pending,relative.as_posix())
            if member.is_dir():
                target.mkdir(parents=True,exist_ok=True)
            else:
                target.parent.mkdir(parents=True,exist_ok=True)
                with z.open(member) as src,target.open('xb') as dst:shutil.copyfileobj(src,dst)
        (pending/'artifact_identity.json').write_text(json.dumps({
            'run_id':RUN,'baseline':'B0','name':entry.get('name',RUN),
            'source_archive_sha256':receipt['archive_sha256']},ensure_ascii=False,indent=2),encoding='utf-8')
        pending.rename(destination)
    registry=registry_data(ROOT)
    for row in registry['runs']:
        if row['run_id']==RUN:
            row['legacy_previous_path']=row['actual_path']
            row['actual_path']=destination.relative_to(ROOT).as_posix()
            row['storage_state']='CANONICAL'
    write(ROOT/'data/registries/project_explorer.json',registry)
    write(STAGING/'retrieval.json',dict(status='downloaded_verified',training_completed=receipt['training_completed'],
        local_output=str(destination.relative_to(ROOT)),archive_sha256=receipt['archive_sha256'],test_inference=False,reserve_inference=False))
    print('Downloaded and verified:',destination,'; training completed:',receipt['training_completed'])


def remote_logs(*,follow: bool=False,version: int | None=None,epochs_only: bool=False) -> None:
    """Đọc log một lần hoặc theo dõi SSE; ngắt terminal không hủy train cloud."""
    target=KERNEL_ID+('/'+str(version) if version is not None else '')
    api=api_client()
    if follow:
        # SDK xử lý nối lại và bỏ log trùng khi stream bị ngắt. Đây chỉ là API
        # đọc log, không gửi notebook hoặc gọi lệnh hủy phiên trên Kaggle.
        print('Following '+target+' (read-only). Ctrl+C disconnects logs; Kaggle continues.',flush=True)
        try:
            if epochs_only:
                import contextlib
                from src.kaggle_recipe import EpochStream
                stream=EpochStream(sys.stdout)
                try:
                    with contextlib.redirect_stdout(stream):api.kernels_logs_cli(target,kernel_opt=None,follow=True)
                finally:stream.finish()
            else:api.kernels_logs_cli(target,kernel_opt=None,follow=True)
        except KeyboardInterrupt:print('\nStopped viewing logs; cloud session was not cancelled.',flush=True)
        return
    raw=api.kernels_logs(target)
    try:
        events=json.loads(raw)
        body=''.join(str(item.get('data','')) for item in events) if isinstance(events,list) else str(raw)
    except (ValueError,TypeError):body=str(raw)
    (STAGING/'latest_remote_logs.txt').write_text(body,encoding='utf-8')
    if epochs_only:
        from src.kaggle_recipe import EpochLogFilter
        body='\n'.join(EpochLogFilter().feed(body,final=True))
    print(body if body else 'No logs available yet; no evidence that training has started.')


def kernel_access_denied(error: Exception) -> bool:
    """Nhận diện 401/403 kể cả khi Kaggle SDK bọc HTTPError trong ValueError."""
    seen=set()
    while error is not None and id(error) not in seen:
        seen.add(id(error))
        response=getattr(error,'response',None)
        if getattr(response,'status_code',None) in (401,403):return True
        error=error.__cause__ or error.__context__
    return False


def report_kernel_access_error(error: Exception) -> None:
    """Báo cách đăng nhập lại mà không tiết lộ thông tin xác thực."""
    print('Kaggle từ chối truy cập notebook PRIVATE (HTTP 401/403). '
          'Trạng thái train hiện chưa xác minh được; lỗi xem log không tự dừng train.\n'
          'Đăng nhập lại tài khoản laqun0211 bằng lệnh:\n'
          r'.\.tmp\kaggle_cli_env\Scripts\kaggle.exe auth login'+'\n'
          'Sau đó thử lại lệnh status/log. Nếu vẫn lỗi, kiểm quyền truy cập notebook trên Kaggle; '
          'không gửi token vào chat và không publish lại.',file=sys.stderr)


def main() -> int:
    global CONFIG,RUN,STAGING
    parser=argparse.ArgumentParser(description='B0 PRIVATE Kaggle package/deploy/fetch; no local training')
    parser.add_argument('action',choices=('prepare','verify','publish','prepare-recipe','publish-recipe','status','logs','fetch','bootstrap','execute'))
    parser.add_argument('--allow-reupload',action='store_true',help='Allow a full upload retry after a failed Dataset creation; may transfer 4 GB again')
    parser.add_argument('--follow',action='store_true',help='With logs: stream live output; Ctrl+C only disconnects viewing')
    parser.add_argument('--version',type=int,help='With logs/status/fetch: select an exact notebook version, e.g. 10')
    parser.add_argument('--epochs-only',action='store_true',help='With logs: show one summary per epoch, no batch progress')
    parser.add_argument('--resume-download',action='store_true',help='With fetch: resume an interrupted Kaggle download without removing existing evidence')
    parser.add_argument('--experiment',choices=('full','adamw-v2','sgd-v3','sgd-low-lr-v4'),default='full',help='Select the intended recipe for preparation, submission or fetch')
    args=parser.parse_args()
    if args.follow and args.action!='logs':parser.error('--follow is only available with logs')
    if args.epochs_only and args.action!='logs':parser.error('--epochs-only is only available with logs')
    if args.resume_download and args.action!='fetch':parser.error('--resume-download is only available with fetch')
    if args.version is not None and (args.version<1 or args.action not in ('logs','status','fetch')):
        parser.error('--version must be positive and is only available with logs/status/fetch')
    recipe_config=recipe_run=None
    if args.experiment!='full':
        if args.action not in ('fetch','prepare-recipe','publish-recipe'):parser.error('--experiment is only available with recipe preparation, submission or fetch')
        from src.kaggle_recipe import RECIPE_CONFIG,RECIPE_RUN
        recipes={
            'adamw-v2':(RECIPE_CONFIG,RECIPE_RUN),
            'sgd-v3':('configs/b0_s960_sgd_kaggle_v3.json','b0_s960_sgd_kaggle_v3'),
            'sgd-low-lr-v4':('configs/b0_s960_sgd_low_lr_kaggle_v4.json','b0_s960_sgd_low_lr_kaggle_v4'),
        }
        recipe_config,recipe_run=recipes[args.experiment]
        if args.action=='fetch':CONFIG=recipe_config;RUN=recipe_run;STAGING=ROOT/'outputs/kaggle'/RUN
    if args.action=='prepare':prepare()
    elif args.action=='prepare-recipe':
        from src.kaggle_recipe import prepare_experiment
        print(json.dumps(prepare_experiment(ROOT,recipe_config,recipe_run) if recipe_config else prepare_experiment(ROOT),indent=2))
    elif args.action=='publish-recipe':
        from src.kaggle_recipe import publish_experiment
        print(json.dumps(publish_experiment(ROOT,recipe_config,recipe_run) if recipe_config else publish_experiment(ROOT),indent=2))
    elif args.action=='verify':print(json.dumps(verify_bundle(STAGING/'dataset/b0_full_bundle.zip',read(STAGING/'dataset/bundle_receipt.json'))))
    elif args.action=='publish':publish(allow_reupload=args.allow_reupload)
    elif args.action in ('status','logs'):
        try:
            if args.action=='status':print(api_client().kernels_status(KERNEL_ID+('/'+str(args.version) if args.version is not None else '')))
            else:remote_logs(follow=args.follow,version=args.version,epochs_only=args.epochs_only)
        except Exception as error:
            if not kernel_access_denied(error):raise
            report_kernel_access_error(error)
            return 1
    elif args.action=='fetch':fetch(version=args.version,resume_download=args.resume_download)
    else:
        try:
            bootstrap() if args.action=='bootstrap' else execute()
        except Exception as error:
            # GPU/version/setup thất bại vẫn có trạng thái, không báo đã train.
            working=Path('/kaggle/working')
            if os.name=='posix' and working.is_dir() and not (working/'run_status.json').exists():
                write(working/'run_status.json',dict(status='blocked_before_training',stage=args.action,
                    error_type=type(error).__name__,error=str(error),training_completed=False,
                    test_inference=False,reserve_inference=False))
            raise
    return 0


if __name__=='__main__':raise SystemExit(main())
