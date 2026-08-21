"""Read detector predictions from disk.

Separate from `crashlab.detector.predict` on purpose: that module imports
ultralytics, and the analysis half must stay importable without torch present.
"""

from __future__ import annotations

import json
from pathlib import Path

from .boxes import Box


def load_predictions(pred_dir: str | Path) -> dict[str, list[Box]]:
    """Read a prediction directory into `{scenario_id: [Box, ...]}`."""
    pred_dir = Path(pred_dir)
    if not pred_dir.is_dir():
        raise FileNotFoundError(f"no prediction directory at {pred_dir}")
    out: dict[str, list[Box]] = {}
    for path in sorted(pred_dir.glob("*.json")):
        if path.name.startswith("_"):
            continue
        data = json.loads(path.read_text())
        out[data["scenario_id"]] = [Box.from_dict(b) for b in data["boxes"]]
    if not out:
        raise FileNotFoundError(f"no prediction files found in {pred_dir}")
    return out
