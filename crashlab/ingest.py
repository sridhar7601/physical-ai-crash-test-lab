"""Read generated frames back into the evaluator.

The bridge between the two halves of the system. The generator needs a GPU and
Isaac Sim; everything downstream reads only these JSON files. That separation
is what makes the diagnosis half testable on a laptop and replayable on stage.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from .boxes import Box
from .suite import Manifest


class IngestError(ValueError):
    """The generated dataset does not match the manifest it claims."""


@dataclass(frozen=True)
class Dataset:
    """Ground truth loaded from a generator run."""

    root: Path
    manifest_name: str
    manifest_fingerprint: str
    suite: str
    data_source: str
    truth: dict[str, list[Box]]
    frame_parameters: dict[str, dict]
    consistency_failures: tuple[str, ...]
    missing: tuple[str, ...]

    def __len__(self) -> int:
        return len(self.truth)

    def image_path(self, scenario_id: str) -> Path:
        return self.root / "frames" / f"{scenario_id}.png"


def load_dataset(
    root: str | Path,
    manifest: Manifest | None = None,
    require_complete: bool = True,
) -> Dataset:
    """Load labels from a generator output directory.

    Args:
        manifest: if given, verify the dataset was generated from exactly this
            manifest. A dataset silently paired with the wrong suite would make
            every downstream metric meaningless.
        require_complete: refuse to load when frames are missing. A partial
            dataset scored as if complete overstates performance.
    """
    root = Path(root)
    labels_dir = root / "labels"
    if not labels_dir.is_dir():
        raise IngestError(f"no labels directory at {labels_dir}")

    summary_path = root / "generation_manifest.json"
    summary = json.loads(summary_path.read_text()) if summary_path.exists() else {}

    if manifest is not None:
        recorded = summary.get("manifest_fingerprint")
        if recorded and recorded != manifest.fingerprint:
            raise IngestError(
                f"dataset at {root} was generated from a different manifest.\n"
                f"  dataset  fingerprint {recorded}\n"
                f"  expected fingerprint {manifest.fingerprint}"
            )

    truth: dict[str, list[Box]] = {}
    params: dict[str, dict] = {}
    inconsistent: list[str] = []

    for path in sorted(labels_dir.glob("*.json")):
        label = json.loads(path.read_text())
        scenario_id = label["scenario"]["scenario_id"]
        truth[scenario_id] = [Box.from_dict(b) for b in label.get("boxes", [])]
        params[scenario_id] = label.get("frame_parameters", {})
        if not label.get("consistency", {}).get("ok", True):
            inconsistent.append(scenario_id)

    missing: list[str] = []
    if manifest is not None:
        missing = [s.scenario_id for s in manifest.scenarios if s.scenario_id not in truth]
        if missing and require_complete:
            raise IngestError(
                f"{len(missing)} of {len(manifest)} manifest frames are missing from "
                f"{root}, e.g. {missing[:3]}. Evaluating the rest would overstate "
                f"coverage. Re-run the generator with --resume, or pass "
                f"require_complete=False deliberately."
            )

    return Dataset(
        root=root,
        manifest_name=summary.get("manifest_name", manifest.name if manifest else "unknown"),
        manifest_fingerprint=summary.get("manifest_fingerprint", ""),
        suite=summary.get("scenario_suite", manifest.suite if manifest else "unknown"),
        data_source=summary.get("data_source", "unknown"),
        truth=truth,
        frame_parameters=params,
        consistency_failures=tuple(inconsistent),
        missing=tuple(missing),
    )
