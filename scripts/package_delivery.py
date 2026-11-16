"""Package a finite, offline demo snapshot; never archive venv/all datasets."""
from datetime import datetime
import argparse
import json
from pathlib import Path
import sys
import zipfile
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.data_preparation import sha256_file,unique_path
from src.demo_server import DemoState


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,help="Optional new archive inside project; never overwrite")
    args=parser.parse_args()
    state=DemoState(ROOT)
    if state.errors:
        raise ValueError(state.errors)
    files=set()
    for name in ("AGENTS.md","README.md","YOLO_Lo_trinh_DACN.xlsx","requirements.txt","requirements-data.txt",
                 "requirements-delivery.txt","demo.sh",".gitignore","yolov8n.pt"):
        files.add(ROOT/name)
    for folder in ("src","scripts","tests","demo","configs","docs","progress"):
        for path in (ROOT/folder).rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts and not path.is_relative_to(ROOT/"configs/ultralytics"):
                files.add(path)
    # Only tracked-style metadata, no processed images/cache or unbounded raw data.
    for path in (ROOT/"data").rglob("*"):
        if path.is_file() and "processed" not in path.relative_to(ROOT/"data").parts:
            files.add(path)
    for name in ("data_raw/README.md","data_samples/README.md","outputs/README.md"):
        files.add(ROOT/name)
    for sample in state.samples.values():
        # Only the explicit built-in catalog is distributable here. Personal
        # uploads and their job folders remain local to the user's machine.
        if not sample.get('reports'):
            continue
        files.add(ROOT/sample["source"])
        for relative in sample["reports"].values():
            path=ROOT/relative
            entry=state.load_run(path,sample)
            files.add(path);files.update(entry["paths"].values())
            if entry['report'].get('timing_evidence'):
                evidence=Path(entry['report']['timing_evidence'])
                files.add(evidence if evidence.is_absolute() else ROOT/evidence)
            if entry['report']['mode'] == 'collision':
                files.add(entry['paths']['output_video'].with_suffix('.events.json'))
                for event in entry['events']:
                    files.update(entry['paths']['output_video'].parent/event[kind] for kind in ('snapshot','clip'))
    for name in ("README.md","BAO_CAO_HIEN_TRANG.docx","SLIDE_DEMO.pptx","BAO_CAO_HIEN_TRANG.pdf","SLIDE_DEMO.pdf","document_provenance.json"):
        path=ROOT/"delivery"/name
        if path.exists():files.add(path)
    files.update((ROOT/"delivery/assets").glob("*.jpg"))
    files.update(p for p in (ROOT/'delivery/collision_2026-11-16').glob('*') if p.is_file())
    for relative in ('tests.log','browser_check.json','http_check.json','recovery_check.json','collision_dashboard.png',
                     'final_replay/report.json','final_replay/config.json','final_replay/collision_rules.py'):
        path=ROOT/'outputs/audits/collision_2026-11-16'/relative
        if path.exists():files.add(path)
    for name in ("http_acceptance.json","browser_acceptance.json","relocation.json","relocated_http_acceptance.json","tests.log","dashboard.png","dashboard_mobile.png","validation.json"):
        path=ROOT/"outputs/audits/delivery_2026-11-14"/name
        if path.exists():files.add(path)
    snapshot=ROOT/"logs/requirements-installed-2026-11-14-cpu.txt"
    if snapshot.exists():files.add(snapshot)
    entries=[]
    for path in sorted(files):
        if not path.is_file() or not path.resolve().is_relative_to(ROOT):
            raise ValueError(f"Missing or external bundle file: {path}")
        entries.append(dict(path=path.relative_to(ROOT).as_posix(),bytes=path.stat().st_size,sha256=sha256_file(path)))
    manifest=dict(schema_version=1,created_at=datetime.now(ZoneInfo("Asia/Bangkok")).isoformat(),
                  purpose="local vehicle inference and experimental collision alerts; not completed collision research",files=entries,
                  contains_full_dataset=False,includes_python_environment=False,final_research_submission_ready=False)
    date=datetime.now(ZoneInfo('Asia/Bangkok')).date().isoformat()
    destination=(ROOT/args.output).resolve() if args.output else unique_path(ROOT/f"delivery/TrafficLab_demo_{date}.zip")
    if not destination.is_relative_to(ROOT):raise ValueError("Archive must remain inside project")
    destination.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(destination,"x",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for path in sorted(files):archive.write(path,"TrafficLab/"+path.relative_to(ROOT).as_posix())
        archive.writestr("TrafficLab/BUNDLE_MANIFEST.json",json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
    (destination.with_suffix(".zip.sha256")).write_text(sha256_file(destination)+"  "+destination.name+"\n")
    print(json.dumps(dict(archive=str(destination),files=len(entries),bytes=destination.stat().st_size,sha256=sha256_file(destination)),indent=2))


if __name__=="__main__":main()
