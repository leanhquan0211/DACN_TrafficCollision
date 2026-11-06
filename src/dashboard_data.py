"""Đọc artifact nghiên cứu để hiển thị dashboard; không train, tải hay sửa nhãn.

Đầu vào là project root và các run/CSV/JSON đã có. Đầu ra là DTO JSON cùng
danh mục media bằng ID; trình duyệt không được gửi đường dẫn file tùy ý.
Giữ metric theo epoch, best revalidation và fixed-threshold ở các trường riêng.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from pathlib import Path
import re
import subprocess
import struct
import threading
import time
import zipfile
from src.storage_paths import artifact_catalog, artifact_path, run_folder

METRICS = {"precision": "metrics/precision(B)", "recall": "metrics/recall(B)",
           "map50": "metrics/mAP50(B)", "map95": "metrics/mAP50-95(B)"}
# Nhãn UI ổn định theo thứ tự thí nghiệm; ID/thư mục và version Kaggle giữ nguyên.
RUN_LABELS = {
    "b0_basic_pilot_v1": "L01 · Basic pilot",
    "b0_accident_scaled_v1": "L02 · Accident scaled 1",
    "b0_accident_scaled_v2": "L03 · Accident scaled 2",
    "b0_verified_pilot_v1": "L04 · Verified pilot",
    "b0_verified_lr001_val_v1": "L05 · LR 0,001 / validation",
    "b0_verified_lr001_full60_v1": "L06 · LR 0,001 / 60 epoch",
    "b0_normal_expanded_v1": "L07 · Normal expanded",
    "b0_s960_v1": "L08 · YOLOv8s 960",
    "b0_s960_hardneg_v1": "L09 · Hard negatives",
    "b0_s960_full_kaggle_v1": "K09 · Full Kaggle pilot",
    "b0_s960_adamw_kaggle_v2": "K10 · AdamW",
    "b0_s960_sgd_kaggle_v3": "K11 · SGD",
    "b0_s960_sgd_low_lr_kaggle_v4": "K12 · SGD LR 0,00015",
}
DOCUMENTS = {
    "progress": ("Tiến độ baseline", "progress/README.md"),
    "report": ("Báo cáo tổng hợp", "docs/BAO_CAO_TIEN_DO_DACN.md"),
    "slides": ("PDF 14 slide", "docs/SLIDE_TIEN_DO_DACN.pdf"),
    "report-pdf": ("PDF báo cáo", "docs/BAO_CAO_TIEN_DO_DACN.pdf"),
    "glossary": ("Thuật ngữ", "reference/GLOSSARY.md"),
    "literature": ("Literature review", "reference/LITERATURE_REVIEW.md"),
    "notes": ("Lời trình bày slide", "docs/CHU_THICH_SLIDE_DACN.md"),
    "setup": ("Cài đặt và phục hồi", "docs/GETTING_STARTED.md"),
}


def read_json(path: Path, default=None):
    """Artifact thiếu/lỗi được trả trạng thái vắng; không tạo số liệu thay thế."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def number(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (ValueError, TypeError):
        return None


def csv_rows(path: Path):
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            return [{str(k).strip(): v.strip() if isinstance(v, str) else v
                     for k, v in row.items() if k is not None} for row in csv.DictReader(stream)]
    except (OSError, csv.Error):
        return []


class DashboardStore:
    """Chuẩn hóa dữ liệu local và cấp media ID trong phạm vi project đã kiểm."""
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.media: dict[str, Path] = {}
        self.lock = threading.RLock()
        self.cache: dict[str, tuple[float, object]] = {}

    def inside(self, path: Path):
        resolved = path.resolve()
        return resolved if resolved.is_relative_to(self.root) else None

    def asset(self, path: Path):
        """Chỉ đăng ký ảnh/video/tài liệu được server chủ động chọn, không nhận URL path."""
        path = self.inside(path)
        if path is None or not path.is_file() or path.suffix.lower() not in {
                ".png", ".jpg", ".jpeg", ".mp4", ".webm", ".pdf", ".md"}:
            return None
        key = hashlib.sha256(path.relative_to(self.root).as_posix().encode()).hexdigest()[:24]
        with self.lock:
            self.media[key] = path
        return "/api/media/" + key

    def media_path(self, key: str):
        with self.lock:
            path = self.media.get(key)
        # Kiểm lại sau resolve để chặn symlink bị đổi giữa hai request.
        return self.inside(path) if path and path.is_file() else None

    def folder(self, run_id: str):
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", run_id):
            raise ValueError("Run ID không hợp lệ")
        folder = run_folder(self.root, run_id)
        if folder is None or not folder.is_dir():
            raise ValueError("Không tìm thấy run")
        return folder

    def deployment(self, run_id: str):
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", run_id):
            return None
        path = self.inside(artifact_path(self.root, self.root / "outputs/kaggle" / run_id / "deployment.json"))
        data = read_json(path, {}) if path else {}
        return data if isinstance(data, dict) and data.get("run", run_id) == run_id and isinstance(data.get("notebook_version"), int) else None

    def label(self, run_id: str, deployment=None):
        if run_id in RUN_LABELS:
            return RUN_LABELS[run_id]
        if deployment:
            return f"K{deployment['notebook_version']:02d} · {run_id.replace('_', ' ')}"
        return "Local · " + run_id.replace("_", " ")

    def history(self, folder: Path):
        result = []
        for row in csv_rows(folder / "results.csv"):
            # Dòng đang ghi dở không có đủ các metric chính sẽ bị bỏ, không nội suy.
            if number(row.get("epoch")) is None or any(number(row.get(v)) is None for v in METRICS.values()):
                continue
            item = {"epoch": int(float(row["epoch"])), "seconds": number(row.get("time"))}
            item.update({k: number(row.get(v)) for k, v in METRICS.items()})
            item.update({k: number(row.get(k)) for k in row if "loss" in k or k.startswith("lr/")})
            result.append(item)
        return result

    def run(self, run_id: str, detailed=True):
        deployment = self.deployment(run_id)
        local_path = run_folder(self.root, run_id)
        if local_path is None and deployment:
            config_path = self.inside(self.root / str(deployment.get("config") or f"configs/{run_id}.json"))
            config = read_json(config_path, {}) if config_path and config_path.suffix == ".json" else {}
            result = {"id": run_id, "title": self.label(run_id, deployment), "status": "submitted",
                      "epochs": 0, "best_epoch": None, "config": config,
                      "metrics": {key: None for key in METRICS}, "fixed": {}, "provenance": None,
                      "dataset_hash": None, "checkpoint_hash": None, "device": None,
                      "torch": None, "ultralytics": None, "limitations": "Chỉ có hồ sơ gửi Kaggle; chưa tải artifact.",
                      "updated_at": (self.root / "outputs/kaggle" / run_id / "deployment.json").stat().st_mtime,
                      "source": f"outputs/kaggle/{run_id}/deployment.json",
                      "local_available": False, "cloud_version": deployment["notebook_version"]}
            if detailed:
                result.update(history=[], charts=[], logs=[])
            return result
        folder = self.folder(run_id)
        experiment = read_json(folder / "experiment.json", {})
        config = experiment.get("config") or read_json(folder / "requested_config.json", {})
        if not config:
            config = read_json(self.root / "configs" / (run_id + ".json"), {})
        history = self.history(folder)
        official = experiment.get("official_bbox_metrics", {}).get("val", {})
        fixed = experiment.get("fixed_threshold_metrics", {}).get("val", {})
        # Chỉ quét val đã đo; không mở test/reserve để chọn model.
        if not fixed:
            fixed = read_json(folder / "cases_val/metrics.json", {})
        best = max(history, key=lambda r: r.get("map95") or -1) if history else None
        withdrawn = "accident_scaled" in run_id
        status = "withdrawn" if withdrawn else "completed" if experiment else "unknown"
        files = [p for p in (folder / "experiment.json", folder / "results.csv") if p.is_file()]
        result = {
            "id": run_id, "title": self.label(run_id, deployment),
            "status": status, "epochs": experiment.get("epochs_completed", len(history)),
            "best_epoch": best["epoch"] if best else None, "config": config,
            "metrics": {k: number(official.get(v)) for k, v in METRICS.items()}, "fixed": fixed,
            "provenance": experiment.get("provenance_sha256"),
            "dataset_hash": experiment.get("dataset_yaml_sha256"),
            "checkpoint_hash": experiment.get("checkpoint_sha256"),
            "device": experiment.get("device"), "torch": experiment.get("torch"),
            "ultralytics": experiment.get("ultralytics"), "limitations": experiment.get("limitations"),
            "updated_at": max((p.stat().st_mtime for p in files), default=None),
            "source": (folder / "experiment.json").relative_to(self.root).as_posix() if experiment else "results.csv (chưa có experiment hoàn tất)",
            "connection": "local_artifacts", "live_status": "not_verified",
            "local_available": True, "cloud_version": deployment["notebook_version"] if deployment else None,
        }
        if detailed:
            charts = []
            for relative in ["training_summary/results.png", "metrics_val/BoxPR_curve.png",
                             "metrics_val/BoxF1_curve.png", "metrics_val/BoxP_curve.png",
                             "metrics_val/BoxR_curve.png", "metrics_val/confusion_matrix.png"]:
                url = self.asset(folder / relative)
                if url:
                    charts.append({"name": relative.split("/")[-1], "url": url, "source": relative})
            result.update(history=history, charts=charts, logs=self.epoch_logs(history),
                          environment={"device": result["device"], "torch": result["torch"], "ultralytics": result["ultralytics"]})
        return result

    @staticmethod
    def epoch_logs(history):
        return [f"Epoch {r['epoch']:>3}  |  P {r['precision']:.4f}  R {r['recall']:.4f}  mAP50 {r['map50']:.4f}  mAP50–95 {r['map95']:.4f}"
                for r in history]

    def runs(self):
        folder = self.root / "outputs/training"
        results, warnings = [], []
        candidates = {p.name for p in folder.iterdir() if p.is_dir()} if folder.is_dir() else set()
        # Trang Huấn luyện hiển thị B0; T0/B3 vẫn tra cứu được trong Explore.
        candidates.update(str(x['id']) for x in artifact_catalog(self.root)
                          if x['kind'] == 'run' and x['available'] and x['baseline'] == 'B0')
        for run_id in sorted(candidates):
            path = run_folder(self.root, run_id)
            if path and ((path / "experiment.json").is_file() or (path / "results.csv").is_file()):
                try:
                    results.append(self.run(run_id, detailed=False))
                except (ValueError, OSError, TypeError) as exc:
                    warnings.append(f"{run_id}: không đọc được artifact ({type(exc).__name__})")
        present = {run["id"] for run in results}
        cloud_root = self.root / "outputs/kaggle"
        if cloud_root.is_dir():
            for path in sorted(cloud_root.iterdir()):
                if path.is_dir() and path.name not in present and self.deployment(path.name):
                    try:
                        results.append(self.run(path.name, detailed=False))
                    except (ValueError, OSError, TypeError) as exc:
                        warnings.append(f"{path.name}: không đọc được deployment ({type(exc).__name__})")
        results.sort(key=lambda r: r["updated_at"] or 0, reverse=True)
        return {"runs": results, "warnings": warnings, "read_at": time.time(),
                "mode": "read_only", "cloud": "not_connected"}

    def provenance_rows(self, run_id):
        """Đọc provenance đúng release; dùng ZIP đã có mà không giải nén/copy media."""
        folder = self.folder(run_id)
        config = self.run(run_id, False)["config"]
        dataset = self.inside(self.root / config.get("dataset", "missing.yaml"))
        if dataset and (dataset.parent / "provenance.csv").is_file():
            return csv_rows(dataset.parent / "provenance.csv")
        if config.get("portable_bundle_manifest"):
            archive = artifact_path(self.root, "outputs/kaggle/b0_s960_full_kaggle_v1/dataset/b0_full_bundle.zip")
            if archive.is_file():
                with zipfile.ZipFile(archive) as z:
                    info = z.getinfo("data/kaggle_full/provenance.csv")
                    if info.file_size > 10 * 1024 * 1024:
                        raise ValueError("Provenance quá lớn")
                    return list(csv.DictReader(io.StringIO(z.read(info).decode("utf-8-sig"))))
        return []

    def dataset(self, run_id, split="all"):
        key = "dataset:" + run_id + ":" + split
        with self.lock:
            cached = self.cache.get(key)
            if cached and time.monotonic() - cached[0] < 30:
                return cached[1]
        rows = [r for r in self.provenance_rows(run_id) if split == "all" or r.get("split") == split]
        sources, splits, sizes = {}, {}, []
        groups, sequences = set(), set()
        for row in rows:
            row_split = row.get("split", "unknown")
            splits[row_split] = splits.get(row_split, 0) + 1
            name = row.get("source_dataset", "unknown")
            item = sources.setdefault(name, {"name": name, "positive": 0, "negative": 0, "unknown": 0, "images": 0, "clips": set(), "groups": set()})
            label = row.get("collision_label", "unknown")
            item[label if label in ("positive", "negative") else "unknown"] += 1
            item["images"] += 1
            item["clips"].add(row.get("source_sequence"))
            item["groups"].add(row.get("leakage_group"))
            groups.add(row.get("leakage_group")); sequences.add((name, row.get("source_sequence")))
        for item in sources.values():
            item["clips"] = len(item["clips"]); item["groups"] = len(item["groups"])
        histogram = [{"name": "< 0,1%", "count": 0}, {"name": "0,1–1%", "count": 0},
                     {"name": "1–5%", "count": 0}, {"name": "≥ 5%", "count": 0}]
        measured = skipped = 0
        # Chỉ đo bbox GT val đã có prediction; ảnh PNG sạch cung cấp đúng W/H.
        # Không infer ảnh mới hoặc gán kích thước mặc định khi thiếu media.
        if split in ("all", "val"):
            origins = {(r.get("source_sequence"), str(r.get("source_frame"))): r for r in rows if r.get("split") == "val"}
            for case in read_json(self.folder(run_id) / "cases_val/predictions.json", []):
                source = origins.get((case.get("source_sequence"), str(case.get("source_frame"))), {}).get("source_path")
                path = self.inside(self.root / source) if source else None
                dimensions = None
                if path and path.is_file():
                    with path.open("rb") as stream:
                        header = stream.read(24)
                    if len(header) >= 24 and header[:8] == b"\x89PNG\r\n\x1a\n":
                        dimensions = struct.unpack(">II", header[16:24])
                for bbox in case.get("gt_xyxy", []):
                    if not dimensions or min(dimensions) <= 0:
                        skipped += 1
                        continue
                    area = max(0, bbox[2]-bbox[0]) * max(0, bbox[3]-bbox[1]) / (dimensions[0]*dimensions[1])
                    index = 0 if area < .001 else 1 if area < .01 else 2 if area < .05 else 3
                    histogram[index]["count"] += 1; measured += 1
        report = {"run": run_id, "samples": len(rows), "sources": list(sources.values()), "splits": splits,
                  "clips": len(sequences), "groups": len(groups), "scope": "release_provenance",
                  "bbox_sizes": {"histogram": histogram, "measured": measured, "skipped": skipped, "scope": "validation_GT_area_percent_of_original_image"},
                  "note": "Số clip/nhóm không chứng minh số camera hoặc tai nạn độc lập. Chỉ đọc metadata, không suy luận test/reserve."}
        with self.lock:
            self.cache[key] = (time.monotonic(), report)
        return report

    def cloud(self, version: int):
        """Snapshot có timeout/cache; chỉ gọi khi người dùng yêu cầu trên web."""
        with self.lock:
            cached = self.cache.get("cloud:" + str(version))
            if cached and time.monotonic() - cached[0] < 20:
                return cached[1]
        python = self.root / ".tmp/kaggle_cli_env/Scripts/python.exe"
        if not python.is_file():
            return {"connected": False, "reason": "cli_environment_missing", "message": "Chưa có môi trường Kaggle CLI local. Xem docs/kaggle_training.md; kết quả lịch sử vẫn đọc được."}
        try:
            result = subprocess.run([str(python), "-X", "utf8", "-B", "-m", "src.dashboard_cloud", "--version", str(version)],
                                    cwd=self.root, capture_output=True, text=True, encoding="utf-8", timeout=35)
            data = json.loads(result.stdout) if result.returncode == 0 else {"connected": False, "reason": "reader_failed", "message": "Không đọc được snapshot Kaggle; kiểm môi trường CLI local."}
        except (OSError, subprocess.TimeoutExpired, ValueError):
            data = {"connected": False, "reason": "timeout_or_network", "message": "Quá thời gian chờ/kết nối lỗi. Cloud run không bị hủy; có thể đọc lại sau."}
        with self.lock:
            self.cache["cloud:" + str(version)] = (time.monotonic(), data)
        return data

    def cases(self, run_id, kind="all", search="", offset=0, limit=24):
        folder = self.folder(run_id)
        rows = read_json(folder / "cases_val/predictions.json", [])
        if not isinstance(rows, list):
            rows = []
        selected = []
        for row in rows:
            if kind in ("tp", "fp", "fn") and not row.get(kind):
                continue
            if search.lower() not in str(row.get("source_sequence", "")).lower():
                continue
            selected.append(row)
        # Lấy ảnh sạch từ provenance để bật/tắt GT/prediction chính xác theo tọa độ.
        provenance = {(r.get("source_sequence"), str(r.get("source_frame"))): r for r in self.provenance_rows(run_id) if r.get("split") == "val"}
        result = []
        for row in selected[offset:offset + limit]:
            item = dict(row)
            seq, frame = str(row.get("source_sequence", "")), str(row.get("source_frame", ""))
            if not re.fullmatch(r"[\w-]+", seq) or not frame.isdigit():
                continue
            item["image"] = self.asset(folder / "cases_val" / f"{seq}_f{int(frame):06}.jpg")
            original = provenance.get((seq, frame), {}).get("source_path")
            item["clean_image"] = self.asset(self.root / original) if original else None
            result.append(item)
        return {"items": result, "total": len(selected), "offset": offset, "limit": limit,
                "scope": "validation_only", "note": "Ảnh so sánh đã vẽ và ảnh sạch (nếu còn local) có vai trò khác nhau."}

    def temporal(self):
        folder = run_folder(self.root, 'b1_causal_diagnostics_v1') or self.root / "outputs/training/b0_s960_v1/temporal_diagnostics_v1"
        report = read_json(folder / "report.json", {})
        result = []
        for seq in report.get("sequences", []):
            name = seq.get("sequence", "")
            if not re.fullmatch(r"[\w-]+", name):
                continue
            video = folder / "videos" / name
            rows = csv_rows(video / "frames.csv")
            result.append({"id": name, "frames": seq.get("frames"), "role": seq.get("role"),
                           "source_fps_verified": seq.get("source_fps_verified", False),
                           "comparison": seq.get("filter_comparison", {}), "history": rows,
                           "video": self.asset(video / "b0_accident.mp4")})
        return {"sequences": result, "checkpoint": "b0_s960_v1", "confidence": 0.27,
                "scope": "temporal_diagnostic_not_event_benchmark", "note": report.get("note")}

    def documents(self):
        return [{"id": key, "name": title, "path": relative, "url": self.asset(self.root / relative),
                 "format": Path(relative).suffix[1:]} for key, (title, relative) in DOCUMENTS.items()]

    def artifacts(self):
        """Một danh mục vật lý chung cho output chuẩn và LEGACY; chỉ đọc metadata."""
        return {'artifacts': artifact_catalog(self.root), 'read_at': time.time(), 'mode': 'read_only'}

    def explore(self):
        """Ánh xạ ảo từ registry cố định; không mở đường dẫn do request gửi.

        Chỉ đọc metadata nhỏ và snapshot đã tạo thủ công. Không liệt kê dataset
        hay nhận arbitrary path; run chưa có mapping được giữ ở Chưa phân loại.
        """
        with self.lock:
            cached = self.cache.get("explore")
            if cached and time.monotonic() - cached[0] < 30:
                return cached[1]
        registry_path = self.root / "data/registries/project_explorer.json"
        registry = read_json(registry_path)
        if not isinstance(registry, dict) or registry.get('schema_version') != 1:
            raise ValueError('Registry khám phá chưa có hoặc sai schema')
        baselines = registry.get('baseline_folders', [])
        ids = [b.get('id') for b in baselines]
        if len(ids) != len(set(ids)) or set(ids) != {'B0', 'B1', 'B2', 'T0', 'B3'}:
            raise ValueError('Registry baseline không hợp lệ')
        inventory = self.runs()
        all_artifacts = artifact_catalog(self.root)
        actual_runs = {r['id']: r for r in inventory['runs']}
        mapped, keys, versions = [], set(), set()
        for entry in registry.get('runs', []):
            run_id, baseline, version = entry.get('run_id'), entry.get('baseline'), entry.get('version')
            if (not isinstance(run_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', run_id)
                    or baseline not in ids or not isinstance(version, str)
                    or not re.fullmatch(r'v\d{3}_[a-z0-9_]+', version)
                    or run_id in keys or (baseline, version[:4]) in versions
                    or entry.get('lifecycle') not in {'active', 'historical', 'withdrawn', 'failed', 'unknown'}):
                raise ValueError('Run/version trong registry trùng hoặc không hợp lệ')
            keys.add(run_id); versions.add((baseline, version[:4]))
            actual = actual_runs.get(run_id)
            path = entry.get('actual_path') or (f"outputs/training/{run_id}" if actual and actual.get('local_available') else f"outputs/kaggle/{run_id}")
            if not isinstance(path, str) or not path.startswith(('outputs/training/', 'outputs/audits/', 'outputs/kaggle/', 'outputs/baselines/')):
                raise ValueError('Đường dẫn run ngoài phạm vi cho phép')
            safe = self.inside(artifact_path(self.root, path))
            if safe is None or '..' in Path(path).parts:
                raise ValueError('Đường dẫn run không an toàn')
            evidence_path = entry.get('evidence_path')
            evidence = None
            if evidence_path:
                if not isinstance(evidence_path, str) or '..' in Path(evidence_path).parts or not evidence_path.startswith(('outputs/training/', 'outputs/audits/', 'outputs/baselines/')):
                    raise ValueError('Đường dẫn bằng chứng không an toàn')
                safe_evidence = self.inside(artifact_path(self.root, evidence_path))
                evidence = read_json(safe_evidence) if safe_evidence and safe_evidence.is_file() else None
            config_file = entry.get('config')
            if not config_file and (self.root/'configs'/f'{run_id}.json').is_file():
                config_file = f'configs/{run_id}.json'
            dataset_path = (actual or {}).get('config', {}).get('dataset')
            mapped.append({'id': run_id, 'baseline': baseline, 'version': version, 'name': entry.get('name'),
                           'lifecycle': entry['lifecycle'], 'actual_path': safe.relative_to(self.root).as_posix() if safe and safe.exists() else path,
                           'storage_state': entry.get('storage_state', 'LEGACY'),
                           'available': safe.is_dir(), 'kind': entry.get('kind', 'training'),
                           'config_path': config_file, 'dataset_release': dataset_path if actual else None,
                           'status': actual.get('status') if actual else ('evidence_present' if isinstance(evidence, dict) else 'unknown'),
                           'notebook_version': actual.get('cloud_version') if actual else None,
                           'metrics': actual.get('metrics') if actual else None, 'fixed': actual.get('fixed') if actual else None,
                           'provenance': actual.get('provenance') if actual else None,
                           'source': entry.get('source'), 'evidence_path': safe_evidence.relative_to(self.root).as_posix() if evidence_path and safe_evidence and safe_evidence.exists() else evidence_path, 'available_in_training': actual is not None})
        for run_id, actual in actual_runs.items():
            if run_id not in keys:
                path = f"outputs/training/{run_id}" if actual.get('local_available') else f"outputs/kaggle/{run_id}"
                mapped.append({'id': run_id, 'baseline': None, 'version': None, 'name': actual['title'],
                               'lifecycle': 'unknown', 'actual_path': path, 'available': bool(actual.get('local_available')),
                               'storage_state': 'LEGACY',
                               'kind': 'training', 'status': actual['status'], 'notebook_version': actual.get('cloud_version'),
                               'metrics': actual.get('metrics'), 'fixed': actual.get('fixed'), 'provenance': actual.get('provenance'),
                               'source': actual.get('source'), 'available_in_training': True})
        # Mỗi lần quét ghi file mới, giữ lại snapshot cũ; chỉ tìm đúng mẫu tên cố định.
        snapshots = []
        for candidate in [*(self.root/'outputs/audits').glob('project_explorer_inventory*.json'),
                          *(self.root/'outputs/data_audits').glob('v*/project_explorer_inventory*.json')]:
            if not re.fullmatch(r'project_explorer_inventory(?:_[0-9A-Za-z_-]+)?\.json', candidate.name):
                continue
            value = read_json(candidate, {})
            if isinstance(value, dict) and value.get('schema_version') == 1 and isinstance(value.get('recorded_at'), str):
                snapshots.append((value['recorded_at'], candidate, value))
        _, snapshot_path, snapshot = max(snapshots, key=lambda x: x[0]) if snapshots else ('', None, {})
        # Chỉ chấp nhận đúng các path thống kê đã định nghĩa; không tin path trong snapshot để đọc file.
        allowed = {'data_raw/accident', 'data_raw/tad', 'data_raw/ua_detrac', 'data_raw/cadp', 'data_raw/sttad',
                   'data_samples/ua_detrac', 'data_samples/cadp', 'data/processed', 'outputs/training', 'outputs/audits', 'outputs/kaggle',
                   'outputs/baselines', 'outputs/shared_evaluations', 'outputs/system_evidence', 'outputs/data_audits'}
        fields = ('path', 'exists', 'bytes', 'files', 'video_files', 'image_files', 'archives', 'errors')
        entries = {e.get('path'): {k: e.get(k) for k in fields} for e in snapshot.get('entries', []) if isinstance(e, dict) and e.get('path') in allowed}
        sources = []
        for source in registry.get('dataset_sources', []):
            item = dict(source)
            item['raw_snapshot'] = entries.get(item.get('raw_path'))
            item['sample_snapshot'] = entries.get(item.get('sample_path'))
            if item.get('id') == 'UA-DETRAC':
                archive_path = artifact_path(self.root, 'outputs/audits/detrac_preparation/archive_sequences.csv')
                archive_rows = csv_rows(archive_path)
                item['catalog'] = {'sequences': len(archive_rows),
                                   'images': sum(int(r['image_count']) for r in archive_rows if str(r.get('image_count', '')).isdigit()),
                                   'source': archive_path.relative_to(self.root).as_posix()} if archive_rows else None
            if item.get('id') == 'ACCIDENT':
                audit_path = artifact_path(self.root, 'outputs/audits/event_evaluator_v1/temporal_inventory_2026-11-05_v6.json')
                audit = read_json(audit_path, {})
                item['catalog'] = {'sequences': audit.get('metadata_rows'), 'images': None,
                                   'source': audit_path.relative_to(self.root).as_posix()} if audit else None
            sources.append(item)
        dataset = None
        reference_run = 'b0_s960_sgd_low_lr_kaggle_v4'
        if reference_run in actual_runs and actual_runs[reference_run].get('local_available'):
            try:
                dataset = {'run_id': reference_run, 'train': self.dataset(reference_run, 'train'),
                           'val': self.dataset(reference_run, 'val')}
            except (OSError, ValueError, KeyError, zipfile.BadZipFile):
                dataset = None
        structure = []
        structure_paths = {'outputs/training', 'outputs/baselines/03_b2_motion_rules/v001_motion_pilot',
                           'outputs/baselines/03_b2_motion_rules/v002_overlap_fix', 'outputs/shared_evaluations/v001_event_evaluator',
                           'outputs/system_evidence/v001_b2_alerts', 'outputs/data_audits/v001_detrac_preparation', 'outputs/audits',
                           'data_raw', 'data_samples', 'data/processed', 'src', 'scripts', 'configs', 'docs',
                           'reference', 'progress', 'outputs/kaggle'}
        for node in registry.get('structure', []):
            item = dict(node)
            item['actual_paths'] = [artifact_path(self.root, p).relative_to(self.root).as_posix() for p in node.get('actual_paths', []) if isinstance(p, str) and p in structure_paths and self.inside(artifact_path(self.root, p)) is not None]
            item['available'] = any((self.root/p).exists() for p in item['actual_paths'])
            structure.append(item)
        classifications = {'data/processed': 'regenerable', 'outputs/training': 'historical',
                           'outputs/audits': 'mixed', 'outputs/kaggle': 'historical', 'outputs/baselines': 'historical',
                           'outputs/shared_evaluations': 'historical', 'outputs/system_evidence': 'historical',
                           'outputs/data_audits': 'historical'}
        storage_entries = [dict(e, classification=classifications.get(p, 'source' if p.startswith('data_raw/') else 'derived'))
                           for p, e in entries.items()]
        result = {'registry_version': registry.get('registry_version'), 'registry_source': 'data/registries/project_explorer.json',
                  'description': registry.get('description'), 'baselines': baselines, 'runs': mapped,
                  'datasets': sources, 'training_dataset': dataset, 'structure': structure,
                  'artifacts': all_artifacts,
                  'storage': {'recorded_at': snapshot.get('recorded_at'), 'scope': snapshot.get('scope'),
                              'entries': storage_entries, 'source': snapshot_path.relative_to(self.root).as_posix() if snapshot_path and entries else None},
                  'warnings': inventory['warnings'], 'read_at': time.time(), 'read_only': True}
        with self.lock:
            self.cache['explore'] = (time.monotonic(), result)
        return result

    def project(self):
        """Dẫn về bảng baseline nguồn; dấu có-bằng-chứng dựa trên artifact, không tự nghiệm thu."""
        text = (self.root / "progress/README.md").read_text(encoding="utf-8") if (self.root / "progress/README.md").is_file() else ""
        runs = self.runs()["runs"]
        b1_folder = run_folder(self.root, 'b1_causal_diagnostics_v1')
        temporal = read_json(b1_folder / 'report.json', {}) if b1_folder else {}
        baselines = []
        for key, name, evidence, label in [
            ("B0", "Detector ảnh", any(r["status"] == "completed" for r in runs), "Có kết quả ảnh"),
            ("B1", "Lọc theo thời gian", bool(temporal.get("sequences")), "Có chẩn đoán"),
            ("B2", "Luật chuyển động", artifact_path(self.root, 'outputs/audits/b2_motion_v2/cadp_v2_pair_audit.json').is_file(), "Đã thử; chưa benchmark event"),
            ("T0", "MLP hiện tại", (self.root / 'src/temporal_training.py').is_file(), "Có code; chưa train"),
            ("B3 / T1", "GRU một chiều", (self.root / 'src/temporal_verifiers.py').is_file(), "Có code; chưa train")]:
            section = re.search(r"^## " + re.escape(key.split(" /")[0]) + r"[^\n]*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
            baselines.append({"id": key, "name": name, "evidence": evidence,
                              "label": label, "source_excerpt": section[1].strip()[:500] if section else None})
        return {"baselines": baselines, "source": "progress/README.md", "document": self.asset(self.root / "progress/README.md"),
                "note": "Dấu trạng thái chỉ ghi nhận artifact đã đăng ký; điều kiện hoàn thành xem bảng baseline nguồn."}
