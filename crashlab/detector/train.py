"""Train a YOLO detector on an exported dataset.

Note on licensing: Ultralytics YOLO is AGPL-3.0. Fine for a hackathon
prototype; it needs replacing (NVIDIA TAO, or a permissively licensed
detector) before this ships as a Presidio product. Recorded here rather than
discovered later.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def train(
    data_yaml: str | Path,
    out_dir: str | Path,
    name: str,
    base_weights: str = "yolo11n.pt",
    epochs: int = 40,
    imgsz: int = 640,
    batch: int = 16,
    seed: int = 20260821,
    patience: int = 12,
    record_path: str | Path | None = None,
) -> dict:
    """Fine-tune `base_weights` and return a record of what was produced."""
    from ultralytics import YOLO

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    model = YOLO(base_weights)
    model.train(
        data=str(data_yaml),
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        seed=seed,
        patience=patience,
        project=str(out_dir),
        name=name,
        exist_ok=True,
        verbose=True,
        plots=False,
        deterministic=True,
    )

    # Ask the trainer where it actually wrote, rather than reconstructing the
    # path. Ultralytics resolves `project` against its own runs root, so
    # out_dir/name is not where the weights land (observed:
    # runs/detect/runs/baseline/weights/best.pt for project=runs name=baseline).
    save_dir = Path(getattr(model.trainer, "save_dir", out_dir / name))
    weights = save_dir / "weights" / "best.pt"
    if not weights.exists():
        found = sorted(Path(".").rglob("best.pt"))
        raise RuntimeError(
            f"training finished but no weights at {weights}. "
            f"best.pt files on disk: {[str(f) for f in found[:5]]}"
        )

    digest = hashlib.blake2b(weights.read_bytes(), digest_size=16).hexdigest()
    record = {
        "name": name,
        "weights": str(weights),
        "weights_fingerprint": digest,
        "base_weights": base_weights,
        "data_yaml": str(data_yaml),
        "epochs": epochs,
        "imgsz": imgsz,
        "batch": batch,
        "seed": seed,
        "save_dir": str(save_dir),
    }
    # Write to a caller-chosen path as well as beside the weights, so scripts
    # downstream have one predictable location to read.
    (save_dir / "train_record.json").write_text(json.dumps(record, indent=2))
    if record_path is not None:
        record_path = Path(record_path)
        record_path.parent.mkdir(parents=True, exist_ok=True)
        record_path.write_text(json.dumps(record, indent=2))
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train a YOLO detector.")
    parser.add_argument("--data", required=True, help="path to data.yaml")
    parser.add_argument("--out", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--weights", default="yolo11n.pt")
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--record", default=None,
                        help="path to write the train record JSON (predictable location)")
    args = parser.parse_args(argv)

    record = train(args.data, args.out, args.name, args.weights,
                   args.epochs, args.imgsz, args.batch,
                   record_path=args.record)
    print("[train] " + json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
