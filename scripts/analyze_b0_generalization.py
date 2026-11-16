"""Reproduce train/validation diagnostics without retraining or selecting a threshold."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import statistics
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["YOLO_CONFIG_DIR"] = str(ROOT / "configs/ultralytics")
os.environ["YOLO_OFFLINE"] = "true"
os.environ["MPLCONFIGDIR"] = str(ROOT / ".cache/matplotlib")

from src.b0_feasibility import verify
from src.data_preparation import save_csv, save_json, sha256_file
from scripts.run_b0_feasibility import iou


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, default=ROOT / "outputs/experiments/b0_feasibility_2026-11-16")
    parser.add_argument("--dataset", type=Path, default=ROOT / "data/processed/b0_feasibility_2026-11-16")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/audits/b0_feasibility_2026-11-16/generalization")
    args = parser.parse_args()
    dataset, experiment, output = args.dataset.resolve(), args.experiment.resolve(), args.output.resolve()
    if not output.is_relative_to(ROOT):
        raise ValueError("Keep diagnostic output inside project")
    info, rows = verify(ROOT, dataset)
    metadata = json.loads((experiment / "run_metadata.json").read_text())
    report = json.loads((experiment / "report.json").read_text())
    if not report["complete"] or report["purpose"] != "software_feasibility_only":
        raise ValueError("Expected completed feasibility run")
    if info["manifest_sha256"] != metadata["dataset_manifest_sha256"]:
        raise ValueError("Dataset differs from the training run")
    checkpoint = experiment / "train/weights/best.pt"
    if sha256_file(checkpoint) != report["best_sha256"]:
        raise ValueError("Checkpoint differs from the training run")
    config = metadata["config"]
    threshold = config["diagnostic_confidence_threshold"]
    overlap = config["diagnostic_iou_threshold"]
    import cv2
    import torch
    from ultralytics import YOLO
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(config["cpu_threads"])
    model = YOLO(str(checkpoint))
    if model.names != {0: "accident"}:
        raise ValueError("Unexpected model class mapping")
    cases = []
    for row in rows:
        path = dataset / row["image_export"]
        height, width = cv2.imread(str(path)).shape[:2]
        truth = []
        for line in (dataset / row["label_export"]).read_text().splitlines():
            _, cx, cy, w, h = map(float, line.split())
            truth.append([(cx-w/2)*width, (cy-h/2)*height, (cx+w/2)*width, (cy+h/2)*height])
        if len(truth) > 1:
            raise ValueError("This frame-level diagnostic expects at most one source region per frame")
        result = model.predict(str(path), device="cpu", imgsz=config["training"]["imgsz"], conf=0.001, verbose=False)[0]
        boxes, scores = result.boxes.xyxy.cpu().tolist(), result.boxes.conf.cpu().tolist()
        matched = max((score for box, score in zip(boxes, scores) if truth and iou(truth[0], box) >= overlap), default=0)
        cases.append(dict(split=row["split"], scene=row["scene_group"], frame=int(row["source_frame_number"]),
                          positive=bool(truth), max_confidence=max(scores, default=0),
                          iou50_matched_confidence=matched,
                          detected_positive=bool(truth) and matched >= threshold,
                          predictions_at_fixed_threshold=sum(s >= threshold for s in scores)))
    summary = {}
    for split in ("train", "val"):
        positives = [c for c in cases if c["split"] == split and c["positive"]]
        negatives = [c for c in cases if c["split"] == split and not c["positive"]]
        summary[split] = dict(positive_frames=len(positives),
                              positive_frames_with_iou50_match_conf025=sum(c["detected_positive"] for c in positives),
                              positive_frames_with_iou50_match_conf001=sum(c["iou50_matched_confidence"] >= .001 for c in positives),
                              median_iou50_matched_confidence=statistics.median(c["iou50_matched_confidence"] for c in positives),
                              negative_frames=len(negatives),
                              negative_frames_with_predictions=sum(c["predictions_at_fixed_threshold"] > 0 for c in negatives))
    save_csv(output / "frames.csv", cases, list(cases[0]))
    save_json(output / "report.json", dict(
        purpose="development_generalization_diagnostic", completed_at=datetime.now(ZoneInfo("Asia/Bangkok")).isoformat(),
        scope="Frame diagnostics only; training frames are not evaluation data; no event metrics or locked test",
        checkpoint_sha256=report["best_sha256"], dataset_manifest_sha256=info["manifest_sha256"],
        producer_sha256=sha256_file(Path(__file__)), confidence_threshold=threshold, iou_threshold=overlap,
        inference_collection_confidence=.001, threshold_selected_by_this_analysis=False, summary=summary))
    figure, axes = plt.subplots(figsize=(8, 4.5), layout="constrained")
    for index, split in enumerate(("train", "val")):
        scores = [c["iou50_matched_confidence"] for c in cases if c["split"] == split and c["positive"]]
        axes.scatter([index+(j-(len(scores)-1)/2)*.015 for j in range(len(scores))], scores, alpha=.8, label=f"{split}: {len(scores)} labelled positive frames")
    axes.axhline(threshold, color="black", linestyle="--", label=f"Fixed confidence {threshold}")
    axes.set(xticks=[0, 1], xticklabels=["Train (seen scenes)", "Validation (other scenes)"],
             ylabel="Best confidence among predictions with IoU >= 0.5", ylim=(0, 1),
             title="Tiny pilot diagnostic: source labels, no locked test")
    axes.legend(fontsize=8)
    figure.savefig(output / "confidence_by_split.png", dpi=180)
    plt.close(figure)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
