"""Đóng gói/kiểm release B0 di động, giữ nguyên nguồn nhãn và split.

Đầu vào: provenance đã khóa, normal tác giả và nhóm train đã rà. Đầu ra:
projection train/val, hash bundle và YAML đường dẫn tại máy chạy. Dùng qua
scripts/kaggle_b0.py; không tải dataset, tạo nhãn dương hoặc tự train.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import zipfile

from src.data_preparation import sha256_file, validate_b0_verified_origins


def safe_path(root: Path, name: str) -> Path:
    """Không để đường dẫn manifest/ZIP thoát root, kể cả tên kiểu Windows."""
    if '\\' in name or ':' in name or PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts:
        raise ValueError('Unsafe package path')
    target=(root/name).resolve()
    if not target.is_relative_to(root.resolve()):raise ValueError('Package path escapes root')
    return target


def csv_bytes(rows: list[dict], fields: list[str]) -> bytes:
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields)
    writer.writeheader();writer.writerows(rows)
    return stream.getvalue().encode('utf-8')


def load_rows(path: Path) -> list[dict]:
    with path.open(encoding='utf-8-sig',newline='') as stream:return list(csv.DictReader(stream))


def sample_key(row: dict) -> tuple:
    return row['source_dataset'],row['source_sequence'],int(row['source_frame'])


def full_train_projection(base: list[dict], candidates: dict, assignments: dict) -> tuple[list[dict],list[dict]]:
    """Giữ mọi train/val cũ và dùng đủ normal ứng viên thuộc nhóm TRAIN cũ.

    Không thêm từ val/reserve/exclude, không nhân ảnh hoặc lan bbox impact.
    Nhãn rỗng chỉ dựa author normal; thêm frame không thêm camera/sự kiện.
    """
    validate_b0_verified_origins(base)
    rows=[dict(r) for r in base if r['split'] in ('train','val')]
    known={sample_key(r) for r in base};groups={};roles={}
    for g in assignments['groups']:
        for seq in g['sequences']:
            if seq in roles:raise ValueError('Duplicate source assignment')
            roles[seq]=g['assignment'];groups[seq]=g['group_id']
    if assignments.get('model_predictions_seen_before_assignment') is not False:
        raise ValueError('Missing frozen pre-mining grouping')
    empty=hashlib.sha256(b'').hexdigest();added=[]
    for sample in candidates['samples']:
        seq=sample['source_sequence'];key=('TAD',seq,int(sample['source_frame']))
        if seq not in roles:raise ValueError('Unreviewed candidate source')
        if roles[seq]!='train' or key in known:continue
        if sample['collision_label']!='negative' or sample['label_origin']!='author_normal_folder_clip_label':
            raise ValueError('Only author-normal labels may add empty bbox labels')
        row={k:'' for k in base[0]}
        image='images/train/'+hashlib.sha256(f'TAD:{seq}:{key[2]}:kaggle-full-v1'.encode()).hexdigest()+'.png'
        row.update(source_dataset='TAD',source_sequence=seq,source_frame=str(key[2]),source_path=sample['image'],
            asset_kind='image',collision_label='negative',label_origin=sample['label_origin'],
            label_evidence='metadata/groups_before_mining.json',accident_bbox_count='0',
            leakage_group=groups[seq],camera_id_verified='False',split='train',training_release_allowed='False',
            export_image=image,export_label=image.replace('images/','labels/').removesuffix('.png')+'.txt',
            image_sha256=sample['image_sha256'],label_sha256=empty)
        known.add(key);rows.append(row);added.append(sample)
    verify_rows(rows)
    return rows,added


def verify_rows(rows: list[dict]) -> None:
    """Kiểm nhóm, identity, đường dẫn và hash không giao các tập."""
    validate_b0_verified_origins(rows)
    identities=set();groups={};sequences={};pixels={};paths=set()
    for row in rows:
        if row['split'] not in ('train','val'):raise ValueError('Test/reserve not permitted in training bundle')
        key=sample_key(row)
        if key in identities:raise ValueError('Duplicate source frame')
        identities.add(key)
        for mapping,name in ((groups,row['leakage_group']),(sequences,key[:2])):
            if name in mapping and mapping[name]!=row['split']:raise ValueError('Group/source crosses splits')
            mapping[name]=row['split']
        for field,prefix in (('export_image','images'),('export_label','labels')):
            p=row[field]
            safe_path(Path.cwd(),p)
            if not p.startswith(prefix+'/'+row['split']+'/') or p in paths:raise ValueError('Conflicting export path')
            paths.add(p)
        signature=(row['split'],row['label_sha256'])
        if row['image_sha256'] in pixels and pixels[row['image_sha256']]!=signature:
            raise ValueError('Image crosses splits or has contradictory labels')
        pixels[row['image_sha256']]=signature


def materialize_paths(root: Path, config: dict) -> Path:
    """Chỉ tạo YAML máy chạy; không sửa YAML/hash của release nguồn."""
    import yaml
    target=safe_path(root,config['dataset']);target.parent.mkdir(parents=True,exist_ok=True)
    data=dict(path=target.parent.as_posix(),train='images/train',val='images/val',names={0:'accident'})
    text=yaml.safe_dump(data,allow_unicode=True,sort_keys=False)
    if target.exists() and target.read_text('utf-8')!=text:raise ValueError('Runtime YAML already differs')
    target.write_text(text,encoding='utf-8')
    return target


def check_portable_inputs(config: dict, root: Path) -> tuple[Path,list[dict]]:
    """Xác minh package và phép mở rộng có chứng cứ trước dùng trainer cũ.

    Hash nguồn không bị thay để chấp nhận Linux path; YAML runtime được kiểm
    ngữ nghĩa riêng. Mọi ảnh/nhãn cũ và split phải giữ nguyên byte; phần mới
    phải truy được về normal tác giả thuộc đúng nhóm train đã khóa trước đó.
    """
    import yaml
    manifest=json.loads(safe_path(root,config['portable_bundle_manifest']).read_text('utf-8'))
    if config!=json.loads(safe_path(root,manifest['config_path']).read_text('utf-8')):
        raise ValueError('Config differs from package')
    if sha256_file(safe_path(root,manifest['config_path']))!=manifest['config_sha256']:
        raise ValueError('Package config changed')
    for name,info in manifest['files'].items():
        path=safe_path(root,name)
        if path.stat().st_size!=info['size_bytes'] or sha256_file(path)!=info['sha256']:
            raise ValueError('Packaged file changed: '+name)
    source=json.loads(safe_path(root,'metadata/source_config.json').read_text('utf-8'))
    if any(config.get(k)!=source.get(k) for k in manifest['recipe_keys']):
        raise ValueError('Training recipe changed during migration')
    if config.get('evaluation_splits')!=['val']:raise ValueError('Portable auto evaluation must be validation only')
    dataset=safe_path(root,config['dataset']);data=yaml.safe_load(dataset.read_text('utf-8'))
    if data!=dict(path=dataset.parent.as_posix(),train='images/train',val='images/val',names={0:'accident'}):
        raise ValueError('Runtime dataset YAML differs; test is prohibited')
    rows=load_rows(dataset.parent/'provenance.csv');verify_rows(rows)
    base=load_rows(root/'metadata/source_provenance.csv')
    candidates=json.loads((root/'metadata/normal_candidates.json').read_text('utf-8'))
    groups=json.loads((root/'metadata/groups_before_mining.json').read_text('utf-8'))
    if sha256_file(root/'metadata/normal_candidates.json')!=groups['candidate_manifest_sha256']:
        raise ValueError('Candidate manifest differs from frozen grouping evidence')
    expected,added=full_train_projection(base,candidates,groups)
    if rows!=expected:raise ValueError('Projection differs from verified original rows/candidates')
    if len(rows)!=manifest['samples'] or len(added)!=manifest['added_normal_frames']:
        raise ValueError('Projection count differs')
    for row in rows:
        for field,hash_key in (('export_image','image_sha256'),('export_label','label_sha256')):
            path=safe_path(dataset.parent,row[field])
            if sha256_file(path)!=row[hash_key]:raise ValueError('Projected image/label changed')
    policy=json.loads(safe_path(root,config['label_policy']).read_text('utf-8'))
    if not policy['pilot_training_release_allowed']:raise ValueError('Portable pilot not released')
    if sha256_file(safe_path(root,config['initial_weights']))!=source['initial_weights_sha256']:
        raise ValueError('Initial checkpoint differs from locked source recipe')
    return dataset,rows


def verify_bundle(archive: Path, receipt: dict) -> dict:
    """Đọc CRC/hash ZIP và chặn file ngoài allowlist, không cần giải nén dataset."""
    if sha256_file(archive)!=receipt['archive_sha256']:raise ValueError('Archive fingerprint differs')
    with zipfile.ZipFile(archive) as z:
        names=z.namelist()
        if len(names)!=len(set(names)):raise ValueError('Duplicate ZIP member')
        for name in names:safe_path(Path.cwd(),name)
        manifest=json.loads(z.read('data/training_bundle_manifest.json'))
        if set(names)!=set(manifest['files'])|{'data/training_bundle_manifest.json'}:
            raise ValueError('Unexpected/missing package file')
        for name,info in manifest['files'].items():
            digest=hashlib.sha256();size=0
            with z.open(name) as stream:
                for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk);size+=len(chunk)
            if size!=info['size_bytes'] or digest.hexdigest()!=info['sha256']:raise ValueError('Archive member changed')
    return dict(status='verified',files=len(names),samples=manifest['samples'],added_normal_frames=manifest['added_normal_frames'])
