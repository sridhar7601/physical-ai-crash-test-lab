"""Render a scenario manifest into frames, labels and metadata.

Run inside Isaac Sim's Python:

    /opt/IsaacSim/python.sh -m crashlab.generator.generate \
        --manifest artifacts/warehouse_ppe_v1-test.json \
        --out datasets/warehouse_ppe_v1-test

Output layout, one directory per manifest:

    frames/<scenario_id>.png       rendered image
    labels/<scenario_id>.json      boxes + physical params + measured occlusion
    generation_manifest.json       what was produced, and what failed

`ingest.py` reads that back into the evaluator without touching the simulator,
so the diagnosis half of the system never depends on a GPU being present.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import traceback
from pathlib import Path

DATA_SOURCE = "isaac_sim_replicator"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a scenario manifest.")
    parser.add_argument("--manifest", required=True, help="manifest JSON from build-suite")
    parser.add_argument("--out", required=True, help="output directory")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--subframes", type=int, default=24,
                        help="ray-traced accumulation subframes per frame; "
                             "higher is cleaner and slower")
    parser.add_argument("--limit", type=int, default=0,
                        help="render only N scenarios (smoke tests)")
    parser.add_argument("--spread", action="store_true",
                        help="with --limit, sample evenly across the manifest instead "
                             "of taking the first N. The first N alphabetically are all "
                             "one corner of the condition matrix, which makes a smoke "
                             "test that misses most of what could break.")
    parser.add_argument("--resume", action="store_true",
                        help="skip scenarios whose label file already exists")
    parser.add_argument("--scene", default="warehouse", choices=("warehouse", "primitive"),
                        help="'warehouse' uses NVIDIA SimReady assets (photoreal); "
                             "'primitive' is the dependency-free fallback")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    out = Path(args.out)
    frames_dir = out / "frames"
    labels_dir = out / "labels"
    frames_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)

    # Import before Isaac Sim starts: a bad manifest path should fail in a
    # second, not after a two-minute simulator boot.
    from ..suite import Manifest

    manifest = Manifest.read(args.manifest)
    scenarios = list(manifest.scenarios)
    if args.limit:
        if args.spread and args.limit < len(scenarios):
            # Deterministic shuffle, NOT a fixed stride. Scenario ids sort into
            # contiguous blocks per condition cell, so any stride that divides
            # the block size aliases onto one bucket -- an 18-frame "spread"
            # sample came back 18/18 helmet_state=absent, which looks like a
            # working smoke test while exercising a third of the matrix.
            shuffled = list(scenarios)
            random.Random(f"smoke/{manifest.fingerprint}").shuffle(shuffled)
            scenarios = sorted(shuffled[: args.limit], key=lambda s: s.scenario_id)
        else:
            scenarios = scenarios[: args.limit]

    if args.resume:
        pending = [s for s in scenarios if not (labels_dir / f"{s.scenario_id}.json").exists()]
        print(f"[gen] resume: {len(scenarios) - len(pending)} already done, "
              f"{len(pending)} to render", flush=True)
        scenarios = pending

    print(f"[gen] manifest    {manifest.name}", flush=True)
    print(f"[gen] fingerprint {manifest.fingerprint}", flush=True)
    print(f"[gen] scenarios   {len(scenarios)}", flush=True)
    if not scenarios:
        print("[gen] nothing to do", flush=True)
        return 0

    from isaacsim import SimulationApp

    sim = SimulationApp({"headless": True, "renderer": "RayTracedLighting"})

    rendered: list[str] = []
    failures: list[dict] = []
    summary_path = out / "generation_manifest.json"

    def save_summary(complete: bool) -> None:
        """Persist progress after every frame.

        Kit runs with fastShutdown and hard-exits the process, so anything
        written only at the end can be lost outright. Saving as we go also
        means a crash at frame 400 does not discard the first 399.
        """
        summary_path.write_text(json.dumps({
            "manifest_name": manifest.name,
            "manifest_fingerprint": manifest.fingerprint,
            "scenario_suite": manifest.suite,
            "data_source": DATA_SOURCE,
            "scene": args.scene,
            "complete": complete,
            "requested": len(scenarios),
            "rendered": len(rendered),
            "failed": len(failures),
            "resolution": [args.width, args.height],
            "subframes": args.subframes,
            "scenario_ids": rendered,
            "failures": failures,
        }, indent=2, sort_keys=True))

    try:
        import numpy as np
        import omni.replicator.core as rep

        from .scene import plan_frame

        if args.scene == "warehouse":
            from .scene_warehouse import WarehouseSceneV2 as Scene
        else:
            from .scene import WarehouseScene as Scene
        scene = Scene(resolution=(args.width, args.height))

        rgb_annot = rep.AnnotatorRegistry.get_annotator("rgb")
        bbox_annot = rep.AnnotatorRegistry.get_annotator("bounding_box_2d_tight")
        rgb_annot.attach(scene.render_product)
        bbox_annot.attach(scene.render_product)
        print("[gen] scene built, annotators attached", flush=True)

        for index, scenario in enumerate(scenarios, start=1):
            try:
                params = plan_frame(scenario)
                scene.apply(params, random.Random(scenario.seed ^ 0x5EED))

                rep.orchestrator.step(rt_subframes=args.subframes)

                rgb = rgb_annot.get_data()
                bbox = bbox_annot.get_data()

                boxes, measured = _decode_boxes(bbox)
                _write_png(np.asarray(rgb), frames_dir / f"{scenario.scenario_id}.png")

                label = {
                    "scenario": scenario.as_dict(),
                    "frame_parameters": params.as_dict(),
                    "boxes": boxes,
                    "measured_occlusion": measured,
                    "image": f"frames/{scenario.scenario_id}.png",
                    "image_size": [args.width, args.height],
                    "data_source": DATA_SOURCE,
                }
                label["consistency"] = _check_consistency(scenario, boxes, measured)

                (labels_dir / f"{scenario.scenario_id}.json").write_text(
                    json.dumps(label, indent=2, sort_keys=True)
                )
                rendered.append(scenario.scenario_id)

                if index % 10 == 0 or index == len(scenarios):
                    print(f"[gen] {index}/{len(scenarios)} "
                          f"({len(failures)} failed)", flush=True)
                    save_summary(complete=False)

            except Exception:
                failures.append({
                    "scenario_id": scenario.scenario_id,
                    "error": traceback.format_exc(limit=3),
                })
                print(f"[gen] FAILED {scenario.scenario_id}", flush=True)

        save_summary(complete=True)
        print(f"[gen] done: {len(rendered)} rendered, {len(failures)} failed", flush=True)

    except Exception:
        traceback.print_exc()
        save_summary(complete=False)
        return 1
    finally:
        try:
            sim.close()
        except Exception:
            pass

    return 0 if not failures else 2


def _decode_boxes(bbox) -> tuple[list[dict], list[dict]]:
    """Turn the annotator's structured array into plain JSON boxes.

    Also extracts `occlusionRatio`, which the renderer measures per object.
    That is what lets the occlusion bucket be *verified* rather than asserted:
    we placed real geometry on the sightline and then read back how much of the
    helmet the camera could actually see.
    """
    if not isinstance(bbox, dict):
        return [], []
    data = bbox.get("data")
    info = bbox.get("info", {}) or {}
    id_to_labels = info.get("idToLabels", {}) or {}
    if data is None or len(data) == 0:
        return [], []

    boxes: list[dict] = []
    measured: list[dict] = []
    for row in data:
        semantic_id = int(row["semanticId"])
        entry = id_to_labels.get(str(semantic_id), {})
        raw = entry.get("class") if isinstance(entry, dict) else str(entry)
        if not raw:
            continue
        # Two realities of labelling on real assets, discovered on the SimReady
        # warehouse: (1) semantics inherit down the prim hierarchy, so the hat
        # mesh under a person-labelled root reports the combined class
        # "hard_hat,person"; (2) NVIDIA assets carry their own semantics (rack,
        # pallet, box, floor...). Split the combined class and keep only ours —
        # the hat wins over person for the hat mesh, and scenery is dropped.
        parts = {part.strip() for part in str(raw).split(",")}
        if "hard_hat" in parts:
            label = "hard_hat"
        elif "person" in parts:
            label = "person"
        else:
            continue
        x1, y1 = float(row["x_min"]), float(row["y_min"])
        x2, y2 = float(row["x_max"]), float(row["y_max"])
        if x2 <= x1 or y2 <= y1:
            continue  # fully occluded or off-frame; no usable box
        boxes.append({"label": label, "bbox": [x1, y1, x2, y2]})

        names = getattr(row.dtype, "names", ()) or ()
        if "occlusionRatio" in names:
            measured.append({
                "label": label,
                "occlusion_ratio": float(row["occlusionRatio"]),
                "visible_fraction": 1.0 - float(row["occlusionRatio"]),
            })
    return boxes, measured


def _check_consistency(scenario, boxes: list[dict], measured: list[dict]) -> dict:
    """Cross-check the rendered frame against what the scenario asked for.

    A generator that quietly emits frames not matching their own labels would
    poison every downstream metric, and the failure would look like a model
    problem. Each frame carries its own verdict so a bad batch is visible.
    """
    condition = scenario.condition
    labels = [b["label"] for b in boxes]
    problems: list[str] = []

    if "person" not in labels:
        problems.append("no person box: worker not visible in frame")

    has_hat_box = "hard_hat" in labels
    if condition.helmet_present and not has_hat_box:
        problems.append("helmet expected but no hard_hat box produced")
    if not condition.helmet_present and has_hat_box:
        problems.append("helmet absent in scenario but a hard_hat box was rendered")

    hat_occlusion = next(
        (m["occlusion_ratio"] for m in measured if m["label"] == "hard_hat"), None
    )
    if condition.helmet_state == "partial":
        if hat_occlusion is None:
            problems.append("partial occlusion requested but none measured")
        elif hat_occlusion < 0.05:
            problems.append(
                f"partial occlusion requested but measured only {hat_occlusion:.3f}"
            )

    return {
        "ok": not problems,
        "problems": problems,
        "measured_hat_occlusion": hat_occlusion,
    }


def _write_png(array, path: Path) -> None:
    """Write RGB(A) to PNG, preferring PIL and falling back to stdlib.

    The fallback exists because Isaac Sim's bundled Python may not ship PIL,
    and a missing image library is a silly reason to lose a render.
    """
    if array is None or getattr(array, "size", 0) == 0:
        raise RuntimeError("renderer returned an empty frame")

    rgb = array[..., :3]
    try:
        from PIL import Image

        Image.fromarray(rgb.astype("uint8")).save(path)
        return
    except ImportError:
        pass

    import struct
    import zlib

    height, width = rgb.shape[0], rgb.shape[1]
    raw = bytearray()
    data = rgb.astype("uint8").tobytes()
    stride = width * 3
    for y in range(height):
        raw.append(0)  # filter type 0
        raw.extend(data[y * stride:(y + 1) * stride])

    def chunk(tag: bytes, payload: bytes) -> bytes:
        return (struct.pack(">I", len(payload)) + tag + payload
                + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF))

    header = struct.pack(">2I5B", width, height, 8, 2, 0, 0, 0)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(bytes(raw), 6))
        + chunk(b"IEND", b"")
    )


if __name__ == "__main__":
    sys.exit(main())
