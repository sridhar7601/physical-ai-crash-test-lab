"""Export a rendered dataset into YOLO format.

Also defines the training-set *filters*, which carry more weight than they
look. The baseline is trained on an `easy` subset — bright, unoccluded, close
range — because that is what a team who collected footage on a good day in a
well-lit aisle actually has. The weakness the whole product exists to find is
therefore a real consequence of a realistic data gap, not a number we tuned.

That choice must be stated wherever the baseline is reported. Undisclosed, it
would be rigging the demo.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

#: Class index order. Fixed here and nowhere else.
CLASS_NAMES: tuple[str, ...] = ("person", "hard_hat")
CLASS_INDEX: dict[str, int] = {name: i for i, name in enumerate(CLASS_NAMES)}

#: Below this, a training export gets a loud warning. Learned the hard way: 65
#: images produced a detector with 0.02 recall across every condition.
MIN_USEFUL_TRAIN_IMAGES = 150


@dataclass(frozen=True)
class Filter:
    """A named subset of conditions, with a human-readable rationale."""

    name: str
    description: str
    predicate: Callable[[dict], bool]


def _condition(label: dict) -> dict:
    return label["scenario"]["condition"]


#: Well-lit, unoccluded footage at any range — "what we happened to collect".
#:
#: Excludes exactly two things: dim lighting and partial occlusion. Those are
#: therefore the weaknesses the analyser should discover, and the interaction
#: between them should be the worst slice of all.
#:
#: Sizing matters as much as the exclusions. An earlier version also excluded
#: `normal` lighting and `far` range, leaving 65 training images -- too few for
#: YOLO to learn an object as small as a hard hat, so the model failed
#: uniformly (recall 0.02 everywhere) and there was no failure *map* to find.
#: A useless baseline is one that is bad in a specific, discoverable way, not
#: one that is bad at everything.
EASY = Filter(
    name="easy",
    description=(
        "bright or normal lighting, helmet fully visible or absent, all ranges "
        "and camera angles. Represents a team that collected training footage in "
        "well-lit aisles with unobstructed views. Dim lighting and partial "
        "occlusion are excluded, so a model trained on this is expected to fail "
        "in those conditions -- that expectation is what the analyser must "
        "rediscover from the frames alone."
    ),
    predicate=lambda lab: (
        _condition(lab)["lighting"] in ("bright", "normal")
        and _condition(lab)["helmet_state"] in ("visible", "absent")
    ),
)

ALL = Filter(
    name="all",
    description="every frame in the manifest, all conditions",
    predicate=lambda lab: True,
)

#: Exactly the complement of EASY: the frames a well-lit-aisle collection
#: missed. Sampling from here simulates generic bulk data collection -- it
#: incidentally contains some of the hard cases, just not many, which is
#: precisely the situation a customer is in.
HARD = Filter(
    name="hard",
    description=(
        "the complement of `easy`: dim lighting or partial occlusion. Sampling "
        "N frames from here is the CONTROL arm -- the same data volume as "
        "targeted remediation, but spread across conditions rather than aimed "
        "at the measured weakness."
    ),
    predicate=lambda lab: not EASY.predicate(lab),
)

FILTERS: dict[str, Filter] = {f.name: f for f in (EASY, HARD, ALL)}


def to_yolo_lines(label: dict) -> list[str]:
    """Convert one label file's boxes to normalised YOLO rows."""
    width, height = label["image_size"]
    rows: list[str] = []
    for box in label.get("boxes", []):
        name = box["label"]
        if name not in CLASS_INDEX:
            continue
        x1, y1, x2, y2 = box["bbox"]
        cx = ((x1 + x2) / 2.0) / width
        cy = ((y1 + y2) / 2.0) / height
        bw = (x2 - x1) / width
        bh = (y2 - y1) / height
        # Clamp: a box grazing the frame edge can round marginally out of range,
        # which ultralytics rejects outright.
        cx, cy = min(max(cx, 0.0), 1.0), min(max(cy, 0.0), 1.0)
        bw, bh = min(max(bw, 1e-6), 1.0), min(max(bh, 1e-6), 1.0)
        rows.append(f"{CLASS_INDEX[name]} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")
    return rows


def export(
    dataset_root: str | Path,
    out_root: str | Path,
    train_filter: Filter = ALL,
    val_fraction: float = 0.15,
    skip_inconsistent: bool = True,
    sample: int | None = None,
    sample_seed: int = 20260821,
) -> dict:
    """Write a YOLO-format dataset and return a manifest describing it.

    Args:
        skip_inconsistent: drop frames whose generator consistency check
            failed. Training on a frame whose labels do not match its own
            scenario teaches the model the wrong thing, and the count of what
            was dropped belongs in the report.
    """
    dataset_root = Path(dataset_root)
    out_root = Path(out_root)
    labels_dir = dataset_root / "labels"

    for split in ("train", "val"):
        (out_root / "images" / split).mkdir(parents=True, exist_ok=True)
        (out_root / "labels" / split).mkdir(parents=True, exist_ok=True)

    selected: list[tuple[str, dict]] = []
    dropped_filter = dropped_inconsistent = 0

    for path in sorted(labels_dir.glob("*.json")):
        label = json.loads(path.read_text())
        if skip_inconsistent and not label.get("consistency", {}).get("ok", True):
            dropped_inconsistent += 1
            continue
        if not train_filter.predicate(label):
            dropped_filter += 1
            continue
        selected.append((label["scenario"]["scenario_id"], label))

    available = len(selected)
    sampled_from = None
    if sample is not None and sample < available:
        # Shuffle then take, rather than stride: scenario ids sort into
        # contiguous blocks per condition, so any stride risks landing on one
        # bucket. Seeded so two arms of an experiment are reproducible.
        import random as _random

        shuffled = list(selected)
        _random.Random(f"sample/{sample_seed}/{train_filter.name}").shuffle(shuffled)
        selected = sorted(shuffled[:sample], key=lambda item: item[0])
        sampled_from = available
    elif sample is not None and sample > available:
        raise ValueError(
            f"asked for {sample} frames but the {train_filter.name!r} filter only "
            f"matches {available} in {dataset_root}. Volume-matched arms cannot be "
            f"built from this dataset; render more frames or lower the target."
        )

    # Deterministic val split: every Nth frame, so re-running produces the same
    # split without needing a stored seed.
    stride = max(2, int(1 / val_fraction)) if val_fraction > 0 else 0
    counts = {"train": 0, "val": 0}
    for index, (scenario_id, label) in enumerate(selected):
        split = "val" if stride and index % stride == 0 else "train"
        src = dataset_root / label["image"]
        shutil.copyfile(src, out_root / "images" / split / f"{scenario_id}.png")
        (out_root / "labels" / split / f"{scenario_id}.txt").write_text(
            "\n".join(to_yolo_lines(label)) + "\n"
        )
        counts[split] += 1

    (out_root / "data.yaml").write_text(
        "path: {}\ntrain: images/train\nval: images/val\nnames:\n{}\n".format(
            out_root.resolve(),
            "\n".join(f"  {i}: {n}" for i, n in enumerate(CLASS_NAMES)),
        )
    )

    manifest = {
        "source_dataset": str(dataset_root),
        "filter": train_filter.name,
        "filter_description": train_filter.description,
        "selected": len(selected),
        "train_images": counts["train"],
        "val_images": counts["val"],
        "dropped_by_filter": dropped_filter,
        "dropped_inconsistent": dropped_inconsistent,
        "sample_requested": sample,
        "sampled_from_available": sampled_from,
        "sample_seed": sample_seed if sample is not None else None,
        "classes": list(CLASS_NAMES),
    }
    if counts["train"] < MIN_USEFUL_TRAIN_IMAGES:
        manifest["warning"] = (
            f"only {counts['train']} training images: too few to learn small objects "
            f"reliably. A model trained on this will likely fail everywhere rather "
            f"than in a specific discoverable way, which defeats the purpose of the "
            f"failure analysis. Widen the filter or raise suite replicates."
        )
        print(f"[export] WARNING: {manifest['warning']}")

    (out_root / "export_manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Export a rendered dataset to YOLO format.")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--filter", default="all", choices=sorted(FILTERS))
    parser.add_argument("--val-fraction", type=float, default=0.15)
    parser.add_argument("--sample", type=int, default=None,
                        help="take only N matching frames (deterministic), so two "
                             "experiment arms can be volume-matched")
    parser.add_argument("--sample-seed", type=int, default=20260821)
    args = parser.parse_args(argv)

    manifest = export(args.dataset, args.out, FILTERS[args.filter],
                      args.val_fraction, sample=args.sample,
                      sample_seed=args.sample_seed)
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


def merge(
    destination: str | Path,
    sources: Iterable[str | Path],
    label: str = "merged",
) -> dict:
    """Combine exported YOLO datasets, recording what actually went in.

    Exists because doing this with `cp` in a shell script leaves the
    destination's `export_manifest.json` describing only the first export --
    observed: a candidate trained on 689 images whose manifest claimed 195.
    For a system whose central claim is reproducible evidence, mis-recording a
    training set is a correctness bug, not untidiness.
    """
    destination = Path(destination)
    contributions: list[dict] = []

    for split in ("train", "val"):
        (destination / "images" / split).mkdir(parents=True, exist_ok=True)
        (destination / "labels" / split).mkdir(parents=True, exist_ok=True)

    for source in sources:
        source = Path(source)
        added = {"source": str(source), "train": 0, "val": 0}
        try:
            src_manifest = json.loads((source / "export_manifest.json").read_text())
            added["filter"] = src_manifest.get("filter")
            added["source_dataset"] = src_manifest.get("source_dataset")
        except FileNotFoundError:
            added["filter"] = "unknown"

        for split in ("train", "val"):
            for image in sorted((source / "images" / split).glob("*.png")):
                shutil.copyfile(image, destination / "images" / split / image.name)
                txt = source / "labels" / split / f"{image.stem}.txt"
                if txt.exists():
                    shutil.copyfile(txt, destination / "labels" / split / txt.name)
                added[split] += 1
        contributions.append(added)

    counts = {
        split: len(list((destination / "images" / split).glob("*.png")))
        for split in ("train", "val")
    }

    (destination / "data.yaml").write_text(
        "path: {}\ntrain: images/train\nval: images/val\nnames:\n{}\n".format(
            destination.resolve(),
            "\n".join(f"  {i}: {n}" for i, n in enumerate(CLASS_NAMES)),
        )
    )

    manifest = {
        "label": label,
        "merged_from": contributions,
        "train_images": counts["train"],
        "val_images": counts["val"],
        "classes": list(CLASS_NAMES),
    }
    (destination / "export_manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def main_merge(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Merge exported YOLO datasets.")
    parser.add_argument("--out", required=True)
    parser.add_argument("--sources", required=True, nargs="+")
    parser.add_argument("--label", default="merged")
    args = parser.parse_args(argv)
    print(json.dumps(merge(args.out, args.sources, args.label), indent=2))
    return 0
