"""Verify a relocated demo bundle with SHA-256, using Python standard library."""
import argparse
import hashlib
import json
from pathlib import Path


def verify(root):
    root=root.resolve()
    manifest=json.loads((root/"BUNDLE_MANIFEST.json").read_text())
    failures=[];seen=set()
    for item in manifest["files"]:
        path=(root/item["path"]).resolve()
        if not path.is_relative_to(root) or item["path"] in seen:
            raise ValueError("Invalid or duplicate manifest path")
        seen.add(item["path"])
        digest=hashlib.sha256()
        if path.is_file():
            with path.open("rb") as stream:
                for block in iter(lambda:stream.read(1024*1024),b""):
                    digest.update(block)
        if not path.is_file() or path.stat().st_size!=item["bytes"] or digest.hexdigest()!=item["sha256"]:
            failures.append(item["path"])
    return dict(verified=not failures,files_checked=len(seen),failures=failures,
                scope="packaged files only; not research dataset readiness")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root",type=Path,nargs="?",default=Path(__file__).resolve().parents[1])
    result=verify(parser.parse_args().root)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(0 if result["verified"] else 1)
