"""Download only pinned, selected STTAD author samples; no research split change."""
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime
import argparse
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.data_preparation import new_audit_dir,save_json,sha256_file
from src.sttad_pilot import fetch_blob,validate_registry


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download",action="store_true",help="Without this flag only print the bounded selection")
    parser.add_argument("--workers",type=int,choices=range(1,5),default=4)
    args=parser.parse_args()
    registry_path=ROOT/"data/registries/sttad_selected_sources.json"
    registry=json.loads(registry_path.read_text());validate_registry(registry)
    print(f"Selected {len(registry['sequences'])} sequences / {len(registry['files'])} files; commit {registry['commit']}",flush=True)
    if not args.download:return 0
    output=ROOT/"data_raw/sttad/author_samples"
    audit=new_audit_dir(ROOT/"outputs/audits","sttad_download_"+datetime.now(ZoneInfo("Asia/Bangkok")).date().isoformat())
    results=[];errors=[]
    def one(item):
        status=fetch_blob(registry["commit"],item["path"],output/item["path"],item["git_blob_sha1"])
        return dict(path=item["path"],status=status,sha256=sha256_file(output/item["path"]),bytes=(output/item["path"]).stat().st_size)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures={pool.submit(one,item):item for item in registry["files"]}
        for future in as_completed(futures):
            try:results.append(future.result())
            except Exception as exc:errors.append(dict(path=futures[future]["path"],error=str(exc)))
            done=len(results)+len(errors)
            if done%25==0 or done==len(futures):print(f"Verified {len(results)}/{len(futures)}, errors {len(errors)}",flush=True)
    report=dict(complete=not errors,commit=registry["commit"],registry_sha256=sha256_file(registry_path),
                results=sorted(results,key=lambda x:x["path"]),errors=errors,training_performed=False,existing_reviews_modified=False)
    save_json(audit/"report.json",report);print(f"Audit: {audit}")
    return int(bool(errors))


if __name__=="__main__":raise SystemExit(main())
