"""Prepare pinned YOLO ONNX and ONNX Runtime Web assets for the Pages export."""
from pathlib import Path
from importlib.metadata import distribution
import hashlib
import io
import json
import shutil
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
WEIGHTS_SHA = "f59b3d833e2ff32e194b5bb8e08d211dc7c5bdf144b90d2c8412c47ccfc83b36"
VERSION = "1.23.2"


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    import torch
    import onnx
    import onnxruntime
    from ultralytics import YOLO
    source = ROOT / "yolov8n.pt"
    if digest(source) != WEIGHTS_SHA: raise ValueError("Source checkpoint fingerprint mismatch")
    model_dir, runtime_dir = ROOT / ".cache/browser-model", ROOT / ".cache/browser-runtime"
    model_dir.mkdir(parents=True, exist_ok=True)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, model_dir / "yolov8n.pt")
    model = model_dir / "yolov8n.onnx"
    metadata = model_dir / "model.json"
    # Existing verified exports are reused; the exporter embeds a creation date.
    if model.exists() or metadata.exists():
        prior = json.loads(metadata.read_text())
        if prior["sha256"] != digest(model) or prior["source_weights_sha256"] != WEIGHTS_SHA:
            raise ValueError("Existing ONNX assets mismatch; preserve and inspect them before rebuilding")
    else:
        torch.set_num_threads(4)
        YOLO(model_dir / "yolov8n.pt").export(format="onnx", imgsz=640, opset=17,
            simplify=False, dynamic=False, half=False, nms=False, device="cpu")
        onnx.checker.check_model(str(model))
        record = dict(schema_version=1, model="YOLOv8n COCO pretrained", source_weights_sha256=WEIGHTS_SHA,
            sha256=digest(model), bytes=model.stat().st_size, input=[1,3,640,640], output=[1,84,8400],
            opset=17, precision="FP32", exporter="ultralytics 8.4.178", browser_runtime="onnxruntime-web " + VERSION,
            confidence=.25, agnostic_nms_iou=.7, training_performed=False, browser_accuracy_evaluated=False,
            source="https://github.com/ultralytics/ultralytics", license="AGPL-3.0")
        metadata.write_text(json.dumps(record, indent=2) + "\n")
    with urllib.request.urlopen("https://registry.npmjs.org/onnxruntime-web/" + VERSION, timeout=30) as response:
        npm = json.load(response)
    archive = runtime_dir / "package.tgz"
    if not archive.exists():
        with urllib.request.urlopen(npm["dist"]["tarball"], timeout=120) as response: data = response.read()
        if hashlib.sha1(data).hexdigest() != npm["dist"]["shasum"]: raise ValueError("NPM tarball mismatch")
        archive.write_bytes(data)
    data = archive.read_bytes()
    if hashlib.sha1(data).hexdigest() != npm["dist"]["shasum"]: raise ValueError("Cached NPM tarball mismatch")
    names = ("ort.wasm.min.js", "ort-wasm-simd-threaded.mjs", "ort-wasm-simd-threaded.wasm")
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        for name in names:
            payload = tar.extractfile("package/dist/" + name).read()
            target = runtime_dir / name
            if target.exists() and target.read_bytes() != payload: raise ValueError("Cached runtime mismatch: " + name)
            target.write_bytes(payload)
    # npm package lacks license files. Preserve MIT and third-party texts from
    # the official installed ORT distribution and AGPL from Ultralytics.
    ort_dir = Path(onnxruntime.__file__).parent
    shutil.copyfile(ort_dir / "LICENSE", runtime_dir / "ONNX-RUNTIME-LICENSE.txt")
    shutil.copyfile(ort_dir / "ThirdPartyNotices.txt", runtime_dir / "ThirdPartyNotices.txt")
    dist = distribution("ultralytics")
    license_file = next(f for f in dist.files if str(f).endswith("licenses/LICENSE"))
    shutil.copyfile(dist.locate_file(license_file), runtime_dir / "ULTRALYTICS-LICENSE.txt")
    record = dict(package="onnxruntime-web", version=VERSION, url=npm["dist"]["tarball"],
        tarball_sha256=digest(archive), tarball_sha1=npm["dist"]["shasum"],
        license_texts_from=dict(onnxruntime=onnxruntime.__version__, ultralytics=dist.version),
        files={name:digest(runtime_dir / name) for name in (*names,"ONNX-RUNTIME-LICENSE.txt","ThirdPartyNotices.txt","ULTRALYTICS-LICENSE.txt")})
    (runtime_dir / "provenance.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(dict(model_sha256=digest(model), runtime_version=VERSION,
        cache=".cache/browser-model and .cache/browser-runtime", training_performed=False), indent=2))


if __name__ == "__main__": main()
