"""Export only allowlisted, verified demo artifacts to a static GitHub Pages site."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import shutil
import sys
import threading
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data_preparation import sha256_file
from src.demo_server import DemoState, rooted


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n")


def build(destination: Path):
    destination = destination.resolve()
    allowed = ROOT / "outputs"
    if not destination.is_relative_to(allowed) or destination == allowed:
        raise ValueError("Export must be a new directory below outputs/")
    if destination.exists():
        raise FileExistsError("Refusing to overwrite an existing export")
    # Deliberately bypass the local UI's upload/job recovery. Only the explicit
    # built-in catalog is read; personal storage is never enumerated or exported.
    state = DemoState.__new__(DemoState)
    state.root, state.runs, state.lock = ROOT, {}, threading.RLock()
    config = json.loads((ROOT / "configs/demo_catalog.json").read_text())
    selected = []
    for sample in config["samples"]:
        if not re.fullmatch(r"[a-z0-9-]+", sample["id"]):
            raise ValueError("Unsafe public sample ID")
        if sample["source"].startswith("outputs/demo_app/") or sample["id"].startswith("upload-"):
            raise ValueError("Personal uploads cannot be published")
        for mode, path in sample["reports"].items():
            if mode not in {"collision", "tracking", "detection"}:
                raise ValueError("Unexpected demo mode")
            entry = state.load_run(rooted(ROOT, path), sample)
            if entry["report"]["mode"] != mode:
                raise ValueError("Catalog mode mismatch")
            selected.append((sample, mode, entry))
    # Validate every original report/hash/decode before writing any public files.
    destination.mkdir(parents=True)
    for name in ("index.html", "app.js"):
        shutil.copy2(ROOT / "demo/pages" / name, destination / name)
    shutil.copy2(ROOT / "demo/style.css", destination / "style.css")
    (destination / ".nojekyll").write_text("")
    published = {}

    def copy_asset(source: Path, relative: str):
        if not source.resolve().is_relative_to(ROOT):
            raise ValueError("External asset rejected")
        target = rooted(destination, relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if sha256_file(source) != sha256_file(target):
                raise ValueError("Conflicting export path")
        else:
            shutil.copy2(source, target)
        if source.stat().st_size != target.stat().st_size or sha256_file(source) != sha256_file(target):
            raise ValueError("Copied artifact fingerprint mismatch")
        return "./" + relative

    for sample, mode, entry in selected:
        sample_id = sample["id"]
        public = published.setdefault(sample_id, {k: sample[k] for k in ("id", "title", "description", "timing_status")})
        public.setdefault("runs", {})
        base = f"media/{sample_id}/{mode}"
        assets = {
            "source": copy_asset(entry["paths"]["input_video"], f"media/{sample_id}/source.mp4"),
            "output": copy_asset(entry["paths"]["output_video"], f"{base}/output.mp4"),
            "cache": copy_asset(entry["paths"]["frame_cache"], f"{base}/frames.jsonl"),
            "report": f"./{base}/summary.json",
        }
        events = []
        for event in entry["events"]:
            event = dict(event)
            for kind, suffix in (("snapshot", "jpg"), ("clip", "mp4")):
                source = (entry["paths"]["output_video"].parent / event[kind]).resolve()
                if not source.is_relative_to(entry["paths"]["output_video"].parent.resolve()):
                    raise ValueError("Evidence path escapes run")
                if sha256_file(source) != event[kind + "_sha256"]:
                    raise ValueError("Evidence fingerprint mismatch")
                event[kind + "_url"] = copy_asset(source, f"{base}/{event['event_id']}.{suffix}")
            events.append(event)
        state.runs[entry["id"]] = entry
        summary = state.run_summary(entry["id"])
        summary.update(artifact_type="public_demo_summary", original_report_sha256=sha256_file(entry["report_path"]),
                       static_replay_only=True, research_test_evaluated=False)
        summary["events"] = events
        if mode == "collision":
            assets["events"] = f"./{base}/events.json"
            write_json(destination / base / "events.json", dict(schema_version=1, experimental=True,
                       score_is_probability=False, method=entry["report"]["collision_method"], events=events))
        write_json(destination / base / "summary.json", summary)
        public["runs"][mode] = f"./data/{sample_id}-{mode}.json"
        write_json(destination / "data" / f"{sample_id}-{mode}.json", dict(summary, assets=assets, frames=entry["frames"]))
    copy_asset(ROOT / "delivery/collision_2026-11-16/BAO_CAO_PHAT_HIEN_VA_CHAM.pdf", "media/bao-cao-va-cham.pdf")
    catalog = dict(schema_version=1, static_replay_only=True, generated_at=datetime.now(ZoneInfo("Asia/Bangkok")).isoformat(),
                   research_test_evaluated=False, samples=list(published.values()))
    write_json(destination / "data/catalog.json", catalog)
    files = [dict(path=p.relative_to(destination).as_posix(), bytes=p.stat().st_size, sha256=sha256_file(p))
             for p in sorted(destination.rglob("*")) if p.is_file()]
    manifest = dict(schema_version=1, static_replay_only=True, private_uploads_included=False,
                    contains_model=False, files=files, original_reports=[dict(sample_id=s["id"], mode=m,
                    report_sha256=sha256_file(e["report_path"])) for s, m, e in selected])
    write_json(destination / "PUBLIC_MANIFEST.json", manifest)
    return dict(export=str(destination), samples=len(published), runs=len(selected), files=len(files) + 1,
                bytes=sum(p["bytes"] for p in files), private_uploads_included=False, static_replay_only=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build((ROOT / args.output).resolve()), ensure_ascii=False, indent=2))
