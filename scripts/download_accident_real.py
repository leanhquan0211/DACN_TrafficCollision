"""Tải tiếp nối clip ACCIDENT thật có bbox xe–xe từ Kaggle v9.

Đầu vào: metadata-real.csv tác giả; nếu thiếu, danh mục member được lấy qua API
public và lưu ở .tmp/. Đầu ra: MP4 gốc trong data_raw, receipt SHA từng file và
báo cáo audit. Dùng trước prepare_accident_scale.py, không tải synthetic.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import time
import urllib.parse
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.data_preparation import sha256_file
from scripts.audit_accident_public import METADATA_SHA256
from src.storage_paths import output_path

parser=argparse.ArgumentParser(description='Tải tiếp nối ACCIDENT v9 real vehicle collisions từ Kaggle public')
parser.add_argument('--workers',type=int,default=16)
parser.add_argument('--audit-version',default='v016_accident_download',help='New vNNN_short_description audit directory')
args=parser.parse_args()
if not 1 <= args.workers <= 16:
    parser.error('--workers must be 1..16')
report_path=output_path(ROOT,'data_audit',args.audit_version,child='report.json')
if report_path.exists():
    raise FileExistsError(f'Audit report exists; choose a new --audit-version: {report_path}')

listing_path=ROOT/'.tmp/accident_v9_full_listing.json'
if not listing_path.exists():
    # Giới hạn kích thước trang/tổng để API sai schema không lấp đầy đĩa.
    listing_path.parent.mkdir(parents=True,exist_ok=True)
    catalog_rows=[];token=None;transferred=0;pages=0
    while True:
        params={'datasetVersionNumber':9,'pageSize':1000}
        if token:
            params['pageToken']=token
        url='https://www.kaggle.com/api/v1/datasets/list/picekl/accident?'+urllib.parse.urlencode(params)
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'DACN-public-source-audit'}),timeout=40) as response:
            data=response.read(2_000_001)
        transferred+=len(data)
        if len(data)>2_000_000 or transferred>10_000_000:
            raise ValueError('Catalog response exceeds metadata budget')
        page=json.loads(data)
        catalog_rows.extend({'name':r['name'],'bytes':int(r['totalBytes'])} for r in page['datasetFiles'])
        pages+=1;token=page.get('nextPageToken')
        if not token:
            break
        if pages>100:
            raise ValueError('Catalog pagination loop')
    if len({r['name'] for r in catalog_rows})!=len(catalog_rows):
        raise ValueError('Duplicate catalog member')
    listing_path.write_text(json.dumps({'version':9,'pages':pages,'transferred_bytes':transferred,'members':catalog_rows},indent=2)+'\n',encoding='utf-8')
catalog=json.loads(listing_path.read_text(encoding='utf-8'))
if catalog['version']!=9:
    raise ValueError('Catalog version mismatch')
metadata_path=ROOT/'data_raw/accident/public_selected/metadata-real.csv'
if not metadata_path.is_file() or sha256_file(metadata_path)!=METADATA_SHA256:
    raise ValueError('Missing or changed ACCIDENT v9 metadata; restore the verified source before downloading')
with metadata_path.open(encoding='utf-8-sig',newline='') as source:
    metadata={r['path']:r for r in csv.DictReader(source)}
types={'t-bone','rear-end','sideswipe','head-on'}
def eligible(row):
    try:
        x1,y1,x2,y2=map(float,(row['x1'],row['y1'],row['x2'],row['y2']))
        return row['type'] in types and 0<=x1<x2<=1 and 0<=y1<y2<=1 and 0<=int(row['accident_frame'])<int(row['no_frames'])
    except (ValueError,TypeError):
        return False
members=[r for r in catalog['members'] if r['name'] in metadata and eligible(metadata[r['name']])]
members.sort(key=lambda entry:(metadata[entry['name']]['split_in_distribution']!='train',entry['name']))
assert len(members)==1346
raw=(ROOT/'data_raw/accident/public_selected').resolve()
assert raw.is_relative_to(ROOT)
receipt_path=raw/'download_receipts.json'
receipts=json.loads(receipt_path.read_text(encoding='utf-8')) if receipt_path.exists() else {}
expected_total=sum(r['bytes'] for r in members)
if shutil.disk_usage(ROOT).free < expected_total*2 + 4*2**30:
    raise OSError('Insufficient free-space reserve')

def get(entry):
    name=entry['name']; size=entry['bytes']
    target=(raw/name).resolve()
    if not target.is_relative_to(raw):
        raise ValueError('Unsafe target path')
    known=receipts.get(name)
    if target.exists() and known and target.stat().st_size==size and sha256_file(target)==known['sha256']:
        return (name,known,0)
    url='https://www.kaggle.com/api/v1/datasets/download/picekl/accident/'+urllib.parse.quote(name,safe='')+'?datasetVersionNumber=9'
    last=None
    for attempt in range(4):
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'DACN-public-source-audit'})
            with urllib.request.urlopen(req,timeout=45) as response:
                body=response.read(size+65537)
            transfer=len(body)
            if transfer>size+65536:
                raise ValueError('Response exceeds member size budget')
            if body.startswith(b'PK'):
                with zipfile.ZipFile(io.BytesIO(body)) as archive:
                    files=[x for x in archive.infolist() if not x.is_dir()]
                    if len(files)!=1 or files[0].filename not in (name,Path(name).name):
                        raise ValueError('Unexpected ZIP member')
                    body=archive.read(files[0])
            if len(body)!=size:
                raise ValueError(f'Listed size {size} differs from downloaded {len(body)}')
            digest=hashlib.sha256(body).hexdigest()
            if target.exists():
                if sha256_file(target)!=digest:
                    raise ValueError('Unreceipted local file differs from versioned endpoint; preserved')
            else:
                target.parent.mkdir(parents=True,exist_ok=True)
                with target.open('xb') as out:
                    out.write(body)
            return (name,{'url':url,'size_bytes':size,'sha256':digest,
                          'identity_status':'observed_local_sha256_from_versioned_public_endpoint'},transfer)
        except Exception as exc:
            last=exc
            if attempt<3:
                time.sleep(2**attempt)
    raise RuntimeError(f'{name}: {last}')

pending=[x for x in members if not (x['name'] in receipts and (raw/x['name']).exists()
         and (raw/x['name']).stat().st_size==x['bytes'] and sha256_file(raw/x['name'])==receipts[x['name']]['sha256'])]
print(f'Inventory {len(members)}, already receipted {len(members)-len(pending)}, pending {len(pending)}, {expected_total/2**30:.2f} GiB total',flush=True)
failures=[];transferred=0;done=0;start=time.monotonic()
with ThreadPoolExecutor(max_workers=args.workers) as pool:
    futures={pool.submit(get,entry):entry['name'] for entry in pending}
    for future in as_completed(futures):
        try:
            name,record,network_bytes=future.result()
            receipts[name]=record
            transferred+=network_bytes
            done+=1
        except Exception as exc:
            failures.append({'name':futures[future],'reason':str(exc)})
        if (done+len(failures))%25==0:
            receipt_path.write_text(json.dumps(receipts,indent=2)+'\n',encoding='utf-8')
            print(f'checked {done+len(failures)}/{len(pending)}, OK {done}, failed {len(failures)}, network {transferred/2**30:.2f} GiB',flush=True)
receipt_path.write_text(json.dumps(receipts,indent=2)+'\n',encoding='utf-8')
report_path.parent.mkdir(parents=True,exist_ok=True)
report={'source':'https://www.kaggle.com/datasets/picekl/accident/versions/9',
        'listing_sha256':sha256_file(listing_path),'listed_real_members':len(members),
        'listed_real_bytes':expected_total,'downloaded_or_verified':len(members)-len(pending)+done,
        'failures':failures,'network_bytes_this_run':transferred,'elapsed_seconds':time.monotonic()-start,
        'scope':'valid metadata vehicle-vehicle real videos only; author IID-train members downloaded first; no label approval or project split implied'}
report_path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(f'FINAL {report["downloaded_or_verified"]}/{len(members)}; failures {len(failures)}; {report_path}',flush=True)
if failures:
    raise SystemExit(1)
