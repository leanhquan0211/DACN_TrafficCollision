"""Đọc danh mục ZIP công khai bằng HTTP Range, không tải toàn bộ dataset.

Đầu vào: URL ZIP hỗ trợ byte ranges; tùy chọn tên member cần lấy. Đầu ra:
CSV danh mục, báo cáo byte mạng và member nhỏ được chọn giữ nguyên cấu trúc.
Chạy khi cân nhắc nguồn lớn; từ chối server trả cả file, quá ngân sách hoặc
đường dẫn ZIP không an toàn. Không giải nén tất cả, không train hay sửa nhãn.
Chế độ offline --prepare-normal-batch kiểm CRC/giải mã và lấy frame đều
từ các clip train/normal tác giả; nhãn/split được duyệt ở bước release riêng.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import shutil
import sys
import urllib.request
import urllib.error
import time
import zipfile
import zlib
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data_preparation import new_audit_dir, save_csv, save_json, sha256_file

TAD_URL = "https://drive.usercontent.google.com/download?id=14GNlNcWLzN-sbzvmrMuSbAg_rZZ5yd26&export=download&confirm=t"


def prepare_normal_batch(plan_path: Path) -> Path:
    """Kiểm batch train/normal đã tải và trích frame đều trước khi xem model.

    Giải mã đủ từng clip, đối chiếu CRC/size từ ZIP, giữ nhãn normal của tác
    giả và source frame. Kết quả chưa có split/train permission: cần kiểm
    cảnh trùng và phiếu quyết định trước khi phát hành dataset mới.
    """
    import cv2
    import numpy as np
    cv2.setNumThreads(1)
    plan_path=plan_path.resolve()
    if not plan_path.is_relative_to(ROOT):raise ValueError('Plan outside project')
    plan=json.loads(plan_path.read_text(encoding='utf-8'))
    output=(ROOT/plan['audit_output']).resolve()
    raw=(ROOT/plan['raw_root']).resolve()
    if not output.is_relative_to(ROOT) or not raw.is_relative_to(ROOT):
        raise ValueError('Batch paths outside project')
    receipt_path=output/'report.json'
    receipt=json.loads(receipt_path.read_text(encoding='utf-8'))
    names={x['path'] for x in plan['members']}
    if (plan['source_url']!=TAD_URL or receipt['source_url']!=TAD_URL
            or receipt.get('fetch_plan_sha256')!=sha256_file(plan_path)
            or set(receipt['fetched_members'])!=names):
        raise ValueError('Download receipt differs from locked batch')
    manifest=output/'normal_manifest.json'
    if manifest.exists():raise FileExistsError('Prepared batch already exists')
    clips=[];samples=[];rejected=[]
    for expected in plan['members']:
        name=expected['path'];path=(raw/Path(*PurePosixPath(name).parts)).resolve()
        if not name.startswith('TAD-benchmark/train/normal/') or not path.is_relative_to(raw):
            raise ValueError('Only public author train/normal members are permitted')
        crc=0
        with path.open('rb') as stream:
            for chunk in iter(lambda:stream.read(1024*1024),b''):crc=zlib.crc32(chunk,crc)
        if path.stat().st_size!=int(expected['size_bytes']) or f'{crc&0xffffffff:08x}'!=expected['crc32']:
            raise ValueError('Downloaded clip differs from ZIP metadata')
        capture=cv2.VideoCapture(str(path));count=0;shape=None;shape_changed=False
        try:
            reported=int(capture.get(cv2.CAP_PROP_FRAME_COUNT));fps=float(capture.get(cv2.CAP_PROP_FPS))
            while True:
                ok,frame=capture.read()
                if not ok:break
                if shape is None:shape=frame.shape[:2]
                elif frame.shape[:2]!=shape:shape_changed=True
                count+=1
        finally:capture.release()
        if count==0 or shape_changed or (reported>0 and count!=reported):
            rejected.append(dict(member=name,reason='decode_or_dimension_mismatch',decoded=count,reported=reported))
            continue
        take=min(int(plan['samples_per_clip']),count)
        if take<1:raise ValueError('Sample count must be positive')
        indices=[round(i*(count-1)/(take-1)) for i in range(take)] if take>1 else [0]
        if len(set(indices))!=take:raise ValueError('Duplicate sampled frames')
        capture=cv2.VideoCapture(str(path));wanted=set(indices);previews=[];seen=set()
        try:
            for index in range(count):
                ok,frame=capture.read()
                if not ok:raise ValueError('Repeated decode incomplete')
                if index not in wanted:continue
                target=output/'images'/f'{path.stem}_f{index:06d}.png'
                target.parent.mkdir(parents=True,exist_ok=True)
                ok,body=cv2.imencode('.png',frame)
                if not ok:raise ValueError('Sample encoding failed')
                with target.open('xb') as stream:stream.write(body.tobytes())
                samples.append(dict(source_dataset='TAD',source_sequence=path.stem,source_frame=index,
                    source_video=path.relative_to(ROOT).as_posix(),image=target.relative_to(ROOT).as_posix(),
                    image_sha256=sha256_file(target),label_origin='author_normal_folder_clip_label',
                    collision_label='negative',user_review=False,split='unassigned'))
                if index in (indices[0],indices[len(indices)//2],indices[-1]):
                    h,w=frame.shape[:2];ratio=min(320/w,180/h)
                    small=cv2.resize(frame,(round(w*ratio),round(h*ratio)))
                    cell=np.full((205,320,3),25,np.uint8);cell[:small.shape[0],:small.shape[1]]=small
                    cv2.putText(cell,f'{path.stem} f{index}',(3,198),cv2.FONT_HERSHEY_SIMPLEX,.42,(255,255,255),1)
                    previews.append(cell)
                seen.add(index)
        finally:capture.release()
        if seen!=wanted:raise ValueError('Missing sampled frame')
        if len(previews)==3:
            contact=np.concatenate(previews,axis=1);ok,body=cv2.imencode('.jpg',contact)
            if not ok:raise ValueError('Scene preview encoding failed')
            preview=output/'scenes'/f'{path.stem}.jpg';preview.parent.mkdir(exist_ok=True)
            preview.write_bytes(body.tobytes())
        clips.append(dict(sequence=path.stem,source_member=name,source_video=path.relative_to(ROOT).as_posix(),
            video_sha256=sha256_file(path),zip_crc32=expected['crc32'],decoded_frames=count,
            width=shape[1],height=shape[0],container_fps=fps,source_fps_verified=False,
            sampled_frame_indices=indices,label_origin='author_normal_folder_clip_label',
            split='unassigned',camera_id_verified=False))
        print(f'Prepared {path.stem}: {count} decoded, {take} samples',flush=True)
    report=dict(scope='public author train/normal batch, pending source grouping and split',
        source_url=TAD_URL,fetch_plan=plan_path.relative_to(ROOT).as_posix(),fetch_plan_sha256=sha256_file(plan_path),
        download_report=receipt_path.relative_to(ROOT).as_posix(),download_report_sha256=sha256_file(receipt_path),
        clips=clips,samples=samples,sample_count=len(samples),rejected=rejected,
        selection='uniform source frame sampling fixed before model prediction',can_train=False,
        author_normal_label_not_user_review=True,source_fps_verified=False)
    save_json(manifest,report)
    print(f'Normal batch ready for grouping: {manifest}',flush=True)
    return manifest


def prepare_normal_test(source_report: Path, raw_root: Path, samples: int) -> Path:
    """Kiểm clip test/normal của tác giả và trích frame thưa để đo báo nhầm.

    Nhãn normal thuộc cấp clip của nguồn, không phải review của người dùng.
    Giải mã toàn clip trước khi chọn đều theo số frame; không suy thời gian
    ghi hình gốc từ FPS container. Ảnh/nhãn rỗng chỉ lưu trong outputs audit.
    """
    import cv2
    cv2.setNumThreads(1)
    source_report=source_report.resolve();raw_root=raw_root.resolve()
    if not source_report.is_relative_to(ROOT) or not raw_root.is_relative_to(ROOT):
        raise ValueError('Paths must remain inside the project')
    source=json.loads(source_report.read_text(encoding='utf-8'))
    if source['source_url']!=TAD_URL:
        raise ValueError('Unexpected TAD source URL')
    with (source_report.parent/'members.csv').open(encoding='utf-8-sig',newline='') as stream:
        members={r['path']:r for r in csv.DictReader(stream)}
    names=sorted(source['fetched_members'])
    if not names or len(names)!=len(set(names)) or any(
        not n.startswith('TAD-benchmark/test/normal/') or not n.lower().endswith('.mp4') for n in names
    ):
        raise ValueError('Only distinct author test/normal MP4 clips are accepted')
    output=ROOT/'outputs/audits/tad_normal_test_v1'
    registry=ROOT/'data/registries/b0_tad_normal_test_v1.json'
    if output.exists():
        raise FileExistsError('Use a new normal-test version; existing audit is preserved')
    output.mkdir(parents=True)
    entries=[];clips=[]
    for name in names:
        target=(raw_root/Path(*PurePosixPath(name).parts)).resolve()
        if not target.is_relative_to(raw_root) or name not in members:
            raise ValueError('Unsafe or missing source member')
        expected=members[name]
        crc=0
        with target.open('rb') as stream:
            for chunk in iter(lambda:stream.read(1024*1024),b''):
                crc=zlib.crc32(chunk,crc)
        if target.stat().st_size!=int(expected['size_bytes']) or f'{crc&0xffffffff:08x}'!=expected['crc32']:
            raise ValueError(f'ZIP member size/CRC mismatch: {name}')
        capture=cv2.VideoCapture(str(target));count=0;shape=None;bad_shape=False
        try:
            if not capture.isOpened():raise ValueError(f'Cannot open {name}')
            reported=int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
            fps=float(capture.get(cv2.CAP_PROP_FPS))
            while True:
                ok,frame=capture.read()
                if not ok:break
                if shape is None:shape=frame.shape[:2]
                elif frame.shape[:2]!=shape:bad_shape=True
                count+=1
        finally:
            capture.release()
        if count==0 or bad_shape or (reported>0 and reported!=count):
            raise ValueError(f'Decode/dimensions/frame count mismatch: {name}, {count}/{reported}')
        take=min(samples,count)
        indices=[round(i*(count-1)/(take-1)) for i in range(take)] if take>1 else [0]
        if len(set(indices))!=take:raise ValueError('Frame selection not unique')
        wanted=set(indices);capture=cv2.VideoCapture(str(target));idx=0;seen=set()
        try:
            while idx<=max(wanted):
                ok,frame=capture.read()
                if not ok:raise ValueError(f'Cannot re-decode selected frame {idx} of {name}')
                if idx in wanted:
                    stem=f'{target.stem}_f{idx:06d}'
                    image=output/'images'/f'{stem}.png';label=output/'labels'/f'{stem}.txt'
                    image.parent.mkdir(parents=True,exist_ok=True);label.parent.mkdir(parents=True,exist_ok=True)
                    success,body=cv2.imencode('.png',frame)
                    if not success:raise ValueError('Cannot encode sample')
                    image.write_bytes(body.tobytes());label.write_text('',encoding='utf-8')
                    entries.append(dict(source_dataset='TAD',source_sequence=target.stem,source_frame=idx,
                        source_video=target.relative_to(ROOT).as_posix(),label_origin='author_normal_folder_clip_label',
                        collision_label='negative',user_review=False,image=image.relative_to(ROOT).as_posix(),
                        image_sha256=sha256_file(image),label=label.relative_to(ROOT).as_posix(),
                        label_sha256=sha256_file(label)))
                    seen.add(idx)
                idx+=1
        finally:
            capture.release()
        if seen!=wanted:raise ValueError('Missing selected frames')
        clips.append(dict(sequence=target.stem,source_member=name,source_video=target.relative_to(ROOT).as_posix(),
                          video_sha256=sha256_file(target),zip_crc32=expected['crc32'],decoded_frames=count,
                          width=shape[1],height=shape[0],container_fps=fps,source_fps_verified=False,
                          sampled_frame_indices=indices))
    report=dict(scope='author TAD test/normal clip labels; frame-level external negative probe, not event benchmark',
        source_report=source_report.relative_to(ROOT).as_posix(),source_report_sha256=sha256_file(source_report),
        source_url=TAD_URL,clips=clips,samples=entries,sample_count=len(entries),
        selection='uniform frames per clip fixed before evaluating any model',
        limitations=['Author normal folder label, not user review','Camera independence from training not verified',
                     'Sparse sampled frames; not false alerts per hour'])
    if registry.exists():
        # Máy clone đã có snapshot: kiểm media/ảnh tái tạo khớp byte đã khóa,
        # không sửa hash chỉ để vượt mismatch. Tên thư mục audit tải có thể khác.
        prior=json.loads(registry.read_text(encoding='utf-8'))
        for key in ('source_url','clips','samples','sample_count','selection'):
            if prior[key]!=report[key]:
                raise ValueError(f'Restored normal probe differs from registry: {key}')
        report['registry_sha256']=sha256_file(registry)
    else:
        save_json(registry,report)
    save_json(output/'report.json',report)
    print(json.dumps({'clips':len(clips),'frames':len(entries),'report':str(output/'report.json')}),flush=True)
    return output


class RangeZip(io.RawIOBase):
    """Cung cấp seek/read cho zipfile; chỉ nhận đúng 206 và Content-Range."""

    def __init__(self, url: str, budget: int, ledger: Path | None = None):
        self.url, self.budget, self.transferred, self.position = url, budget, 0, 0
        self.ledger=ledger
        self.reserved=0
        if ledger and ledger.exists():
            record=json.loads(ledger.read_text(encoding='utf-8'))
            if record['source_url']!=url:raise ValueError('Transfer ledger URL changed')
            self.reserved=record['reserved_response_bytes']
        self.size = None
        self.fetch(0, 1)

    def fetch(self, start: int, count: int) -> bytes:
        """Thử lại lỗi kết nối tối đa3lần; mỗi request vẫn tính vào sổ ngân sách."""
        for attempt in range(3):
            try:return self._fetch_once(start,count)
            except (urllib.error.URLError,TimeoutError):
                if attempt==2:raise
                print(f'Transient Range connection error; retry {attempt+1}/2',flush=True)
                time.sleep(1)

    def _fetch_once(self, start: int, count: int) -> bytes:
        if count <= 0:
            return b""
        if (self.reserved if self.ledger else self.transferred) + count > self.budget:
            raise ValueError("HTTP Range byte budget exhausted; no full download")
        if self.ledger:
            # Tính cả request lỗi vào ngân sách theo kích thước đã yêu cầu.
            # Đây là cận bảo thủ, không khẳng định là byte thực nhận khi timeout.
            self.reserved+=count
            pending=self.ledger.with_suffix('.json.tmp')
            pending.write_text(json.dumps(dict(source_url=self.url,reserved_response_bytes=self.reserved,
                semantics='requested Range response bytes, includes failed attempts conservatively'))+'\n',encoding='utf-8')
            pending.replace(self.ledger)
        req = urllib.request.Request(self.url, headers={"User-Agent": "DACN-public-zip-audit",
                                                      "Range": f"bytes={start}-{start+count-1}"})
        with urllib.request.urlopen(req, timeout=30) as response:
            match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", response.headers.get("Content-Range", ""))
            if response.status != 206 or not match:
                raise ValueError("Server did not honor HTTP Range; refusing full file")
            first, last, total = map(int, match.groups())
            if first != start or last != start+count-1 or (self.size is not None and total != self.size):
                raise ValueError("Remote range/size changed")
            self.size = total
            body = response.read(count+1)
        self.transferred += len(body)
        if len(body) != count:
            raise ValueError("Incomplete or oversized range response")
        return body

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        self.position = offset if whence == 0 else (self.position + offset if whence == 1 else self.size + offset)
        if not 0 <= self.position <= self.size:
            raise ValueError("Invalid ZIP seek")
        return self.position

    def read(self, size=-1):
        count = self.size-self.position if size < 0 else min(size, self.size-self.position)
        body = self.fetch(self.position, count)
        self.position += len(body)
        return body


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect public ZIP central directory using bounded HTTP ranges")
    parser.add_argument("--url", default=TAD_URL)
    parser.add_argument("--max-mib", type=int, default=8)
    parser.add_argument("--fetch-members", nargs="*", default=[])
    parser.add_argument("--fetch-plan",type=Path,help="Config khóa member/CRC/kích thước để tải chọn lọc có thể lặp lại")
    parser.add_argument("--audit-dir",type=Path,help="Thư mục audit MỚI để gom kết quả của một batch")
    parser.add_argument('--resume-fetch',action='store_true',help='Tiếp tục audit tải dở, dùng lại file đúng CRC/size; không ghi đè report hoàn tất')
    parser.add_argument("--raw-root", type=Path, default=Path("data_raw/tad/public_selected"))
    parser.add_argument("--prepare-normal-test",type=Path,help="Audit report đã tải test/normal; không truy cập mạng")
    parser.add_argument("--prepare-normal-batch",type=Path,help="Config batch train/normal đã tải; kiểm CRC/decode và trích frame, không mạng")
    parser.add_argument("--samples-per-clip",type=int,default=20)
    args = parser.parse_args()
    if args.prepare_normal_batch:
        if args.fetch_members or args.fetch_plan or args.prepare_normal_test:
            parser.error('Prepare normal batch is an offline, separate mode')
        prepare_normal_batch(args.prepare_normal_batch)
        return 0
    plan=None
    if args.fetch_plan:
        plan_path=args.fetch_plan.resolve()
        if not plan_path.is_relative_to(ROOT) or args.fetch_members or args.prepare_normal_test:
            parser.error("Fetch plan must be inside project and used without other modes")
        plan=json.loads(plan_path.read_text(encoding='utf-8'))
        if plan['source_url']!=args.url:
            parser.error('Fetch plan URL differs from selected public ZIP')
        args.fetch_members=[r['path'] for r in plan['members']]
        if len(set(args.fetch_members))!=len(args.fetch_members):
            parser.error('Fetch plan contains duplicate members')
    if args.prepare_normal_test:
        if args.fetch_members or args.samples_per_clip<1:
            parser.error("Normal-test mode requires samples-per-clip >=1 and no fetch-members")
        prepare_normal_test(args.prepare_normal_test,args.raw_root,args.samples_per_clip)
        return 0
    if args.max_mib <= 0:
        parser.error("--max-mib must be positive")
    if args.audit_dir:
        audit=args.audit_dir.resolve()
        if not audit.is_relative_to(ROOT) or (audit.exists() and not args.resume_fetch):
            parser.error('Audit directory must be new and inside project')
        if args.resume_fetch and (not plan or not audit.is_dir() or (audit/'report.json').exists()):
            parser.error('Resume needs a fetch plan and incomplete existing audit')
    else:
        audit=None
    # Chừa chỗ trước khi tải; không dùng ZIP tổng 4 GB khi chỉ cần vài member.
    if plan and shutil.disk_usage(ROOT).free < sum(int(r['size_bytes']) for r in plan['members'])+512*1024**2:
        raise OSError('Insufficient disk reserve for selected members')
    if audit is None:
        audit = new_audit_dir(ROOT/"outputs/audits", "tad_public_zip")
    else:
        audit.mkdir(parents=True,exist_ok=args.resume_fetch)
    remote = RangeZip(args.url, args.max_mib*1024**2,audit/'transfer_ledger.json' if plan else None)
    with zipfile.ZipFile(remote) as archive:
        rows = [dict(path=x.filename, size_bytes=x.file_size, compressed_bytes=x.compress_size,
                     crc32=f"{x.CRC:08x}", is_directory=x.is_dir()) for x in archive.infolist()]
        if (audit/'members.csv').exists():
            with (audit/'members.csv').open(encoding='utf-8-sig',newline='') as source:previous=list(csv.DictReader(source))
            if previous!=[{k:str(v) for k,v in r.items()} for r in rows]:raise ValueError('ZIP listing changed during resume')
        else:save_csv(audit/"members.csv", rows, list(rows[0]))
        if plan:
            observed={r['path']:r for r in rows}
            for expected in plan['members']:
                if any(str(observed.get(expected['path'],{}).get(k))!=str(expected[k])
                       for k in ('size_bytes','compressed_bytes','crc32')):
                    raise ValueError('Remote member differs from locked fetch plan')
        retrieved = []
        reused = []
        for name in args.fetch_members:
            member = archive.getinfo(name)
            p = PurePosixPath(name)
            raw = args.raw_root.resolve()
            target = (raw/Path(*p.parts)).resolve()
            if (p.is_absolute() or ".." in p.parts or "\\" in name or ":" in name or not raw.is_relative_to(ROOT)
                    or not target.is_relative_to(raw) or member.is_dir() or member.file_size > args.max_mib*1024**2):
                raise ValueError(f"Unsafe or oversized member: {name}")
            # File đã có phải đúng CRC/size; dùng lại để lượt tải dở không tốn
            # mạng lặp lại. File khác byte bị chặn, không tự ghi đè dữ liệu gốc.
            if target.exists():
                crc=0
                with target.open('rb') as stream:
                    for chunk in iter(lambda:stream.read(1024*1024),b''):crc=zlib.crc32(chunk,crc)
                if target.stat().st_size!=member.file_size or crc&0xffffffff!=member.CRC:
                    raise ValueError(f'Existing source differs: {target}')
                retrieved.append(name);reused.append(name)
                print(f'Reused {name}',flush=True)
                continue
            # zipfile tự đối chiếu CRC sau đọc; kiểm trước ghi, không ghi đè.
            with archive.open(member) as stream:
                body = stream.read(member.file_size+1)
            if len(body) != member.file_size:
                raise ValueError("Unexpected uncompressed size")
            if target.exists():
                if target.read_bytes() != body:
                    raise ValueError(f"Existing source differs: {target}")
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as stream:
                    stream.write(body)
            retrieved.append(name)
            print(f'Retrieved {name} ({len(body)} bytes)',flush=True)
    report = dict(source_url=args.url, archive_bytes=remote.size, network_bytes=remote.transferred,
                  member_count=len(rows), fetched_members=retrieved, full_archive_downloaded=False,
                  central_directory_readable=True, full_archive_crc_checked=False)
    if plan:
        report.update(fetch_plan=args.fetch_plan.relative_to(Path('.')).as_posix() if not args.fetch_plan.is_absolute() else args.fetch_plan.relative_to(ROOT).as_posix(),
                      fetch_plan_sha256=sha256_file(args.fetch_plan),reused_members=reused,
                      conservative_requested_response_bytes_all_attempts=remote.reserved)
    save_json(audit/"report.json", report)
    print(json.dumps(report))
    print(f"Report: {(audit/'report.json').relative_to(ROOT).as_posix()}")
    for row in rows[:12]:
        print(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
