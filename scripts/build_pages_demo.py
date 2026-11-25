"""Export allowlisted replays and the browser upload app to GitHub Pages."""
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
    for name in ("index.html", "app.js", "upload.html", "upload.js", "browser-core.js", "browser-worker.js"):
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

    model_dir = ROOT / ".cache/browser-model"
    runtime_dir = ROOT / ".cache/browser-runtime"
    model = json.loads((model_dir / "model.json").read_text())
    runtime = json.loads((runtime_dir / "provenance.json").read_text())
    if (model["source_weights_sha256"] != sha256_file(ROOT / "yolov8n.pt")
            or model["sha256"] != sha256_file(model_dir / "yolov8n.onnx")
            or model["browser_runtime"] != "onnxruntime-web 1.23.2"):
        raise ValueError("Browser model fingerprint/version mismatch")
    if runtime["version"] != "1.23.2" or not runtime.get("files"):
        raise ValueError("Missing browser runtime fingerprint inventory")
    for name, fingerprint in runtime["files"].items():
        if Path(name).name != name or sha256_file(runtime_dir / name) != fingerprint:
            raise ValueError("Browser runtime fingerprint mismatch: " + name)
    for name in ("yolov8n.onnx", "model.json"):
        copy_asset(model_dir / name, "models/" + name)
    for name in ("ort.wasm.min.js", "ort-wasm-simd-threaded.mjs", "ort-wasm-simd-threaded.wasm",
                 "ONNX-RUNTIME-LICENSE.txt", "ThirdPartyNotices.txt", "ULTRALYTICS-LICENSE.txt", "provenance.json"):
        copy_asset(runtime_dir / name, "vendor/" + name)
    rules = json.loads((ROOT / "configs/collision_rules.json").read_text())
    write_json(destination / "data/browser-config.json", dict(
        schema_version=1, tracker="browser_iou_velocity_v1", sampling_hz=20,
        rules=rules, rules_source_sha256=sha256_file(ROOT / "configs/collision_rules.json"),
        scope="browser deployment experiment; not Python/ByteTrack benchmark; no independent accuracy evaluation"))

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
    # Keep the measured development results with the static replay. They are
    # copied unchanged from the reviewed ledger, not inferred from demo clips.
    copy_asset(ROOT / "docs/evidence/2026-11-17-evaluation.json", "data/evaluation.json")
    copy_asset(ROOT / "docs/evidence/figures/2026-11-17-vehicle_pr.pdf", "media/vehicle-pr.pdf")
    copy_asset(ROOT / "docs/evidence/figures/2026-11-17-b0_train_val.pdf", "media/b0-train-val.pdf")
    catalog = dict(schema_version=1, static_replay_only=True, generated_at=datetime.now(ZoneInfo("Asia/Bangkok")).isoformat(),
                   research_test_evaluated=False, samples=list(published.values()))
    write_json(destination / "data/catalog.json", catalog)
    files = [dict(path=p.relative_to(destination).as_posix(), bytes=p.stat().st_size, sha256=sha256_file(p))
             for p in sorted(destination.rglob("*")) if p.is_file()]
    manifest = dict(schema_version=2, static_replay_only=False, browser_inference_implemented=True,
                    private_uploads_included=False, contains_model=True,
                    model=model, files=files, original_reports=[dict(sample_id=s["id"], mode=m,
                    report_sha256=sha256_file(e["report_path"])) for s, m, e in selected])
    write_json(destination / "PUBLIC_MANIFEST.json", manifest)
    return dict(export=str(destination), samples=len(published), runs=len(selected), files=len(files) + 1,
                bytes=sum(p["bytes"] for p in files), private_uploads_included=False,
                static_replay_only=False, browser_inference_implemented=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build((ROOT / args.output).resolve()), ensure_ascii=False, indent=2))
