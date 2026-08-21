"""Run a trained detector over a rendered dataset and write predictions.

Output is one JSON file per scenario, in exactly the shape `crashlab.boxes.Box`
consumes. That is the whole interface between the GPU half and the analysis
half: no torch import ever reaches the evaluator.

Predictions are written for EVERY manifest frame, including frames where the
model detected nothing (an empty list). `evaluate()` refuses to score a
manifest with missing predictions, because silently skipping frames a model
choked on inflates every metric.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def predict(
    weights: str | Path,
    dataset_root: str | Path,
    out_dir: str | Path,
    conf: float = 0.05,
    imgsz: int = 640,
    device: str = "0",
) -> dict:
    """Run inference over every frame in `dataset_root`.

    Args:
        conf: deliberately low. Thresholding belongs in `EvalConfig`, applied
            consistently at scoring time — not baked into the raw predictions,
            where it could differ between two models being compared.
    """
    from ultralytics import YOLO

    dataset_root = Path(dataset_root)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    frames = sorted((dataset_root / "frames").glob("*.png"))
    if not frames:
        raise RuntimeError(f"no frames under {dataset_root / 'frames'}")

    model = YOLO(str(weights))
    names = model.names

    written = empty = 0
    for index, frame in enumerate(frames, start=1):
        scenario_id = frame.stem
        result = model.predict(
            source=str(frame), conf=conf, imgsz=imgsz,
            device=device, verbose=False,
        )[0]

        boxes = []
        for row in result.boxes:
            cls = int(row.cls.item())
            xyxy = [float(v) for v in row.xyxy[0].tolist()]
            boxes.append({
                "label": names[cls],
                "bbox": xyxy,
                "score": float(row.conf.item()),
            })
        if not boxes:
            empty += 1

        (out_dir / f"{scenario_id}.json").write_text(
            json.dumps({"scenario_id": scenario_id, "boxes": boxes}, indent=2)
        )
        written += 1
        if index % 100 == 0:
            print(f"[predict] {index}/{len(frames)}", flush=True)

    summary = {
        "weights": str(weights),
        "dataset": str(dataset_root),
        "frames": written,
        "frames_with_no_detection": empty,
        "raw_conf_floor": conf,
        "imgsz": imgsz,
    }
    (out_dir / "_predict_summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def load_predictions(pred_dir: str | Path) -> dict:
    """Read a prediction directory into `{scenario_id: [Box, ...]}`."""
    from ..boxes import Box

    pred_dir = Path(pred_dir)
    out: dict[str, list] = {}
    for path in sorted(pred_dir.glob("*.json")):
        if path.name.startswith("_"):
            continue
        data = json.loads(path.read_text())
        out[data["scenario_id"]] = [Box.from_dict(b) for b in data["boxes"]]
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a detector over a dataset.")
    parser.add_argument("--weights", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--conf", type=float, default=0.05)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", default="0")
    args = parser.parse_args(argv)

    summary = predict(args.weights, args.dataset, args.out,
                      args.conf, args.imgsz, args.device)
    print("[predict] " + json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
