"""Run a model's predictions against a locked manifest.

The evaluator never touches the simulator. It consumes three things — a
manifest, a set of ground-truth boxes, and a set of predictions — which is
what makes the whole diagnosis half of this system testable on a laptop with
no GPU, and replayable on stage from saved artifacts.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Sequence

from .boxes import Box
from .matching import (
    DEFAULT_IOU_THRESHOLD,
    DEFAULT_SCORE_THRESHOLD,
    FrameResult,
    match_frame,
)
from .metrics import (
    Slice,
    build_slice,
    slice_by_condition,
    slice_by_factor,
    slice_by_factor_pair,
)
from .schema import CLASSES, Condition
from .suite import Manifest


class EvaluationError(ValueError):
    """The evaluation cannot be trusted as configured."""


@dataclass(frozen=True)
class EvalConfig:
    """Thresholds, declared before evaluation and printed in the report.

    A recall number is meaningless without the confidence threshold that
    produced it, so these travel with every result.
    """

    iou_threshold: float = DEFAULT_IOU_THRESHOLD
    score_threshold: float = DEFAULT_SCORE_THRESHOLD
    classes: tuple[str, ...] = CLASSES
    min_samples_for_finding: int = 20

    def as_dict(self) -> dict[str, object]:
        return {
            "iou_threshold": self.iou_threshold,
            "score_threshold": self.score_threshold,
            "classes": list(self.classes),
            "min_samples_for_finding": self.min_samples_for_finding,
        }


@dataclass(frozen=True)
class ModelRef:
    """Identity of the model under test.

    `fingerprint` should be a hash of the weights file in real use. It exists
    so a report can never be silently attributed to the wrong model version.
    """

    name: str
    version: str
    fingerprint: str = "unfingerprinted"
    notes: str = ""

    @property
    def ref(self) -> str:
        return f"{self.name}@{self.version}"

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "version": self.version,
            "fingerprint": self.fingerprint,
            "notes": self.notes,
            "ref": self.ref,
        }

    @classmethod
    def from_weights(cls, name: str, version: str, path: str | Path, notes: str = "") -> "ModelRef":
        digest = hashlib.blake2b(Path(path).read_bytes(), digest_size=16).hexdigest()
        return cls(name=name, version=version, fingerprint=digest, notes=notes)


@dataclass
class Evaluation:
    """The scored result of one model against one manifest."""

    model: ModelRef
    manifest_name: str
    manifest_fingerprint: str
    suite: str
    config: EvalConfig
    results: tuple[FrameResult, ...]
    conditions: dict[str, Condition] = field(default_factory=dict)
    data_source: str = "unspecified"

    # -- slices ---------------------------------------------------------

    def overall(self) -> Slice:
        return build_slice("overall", "overall", list(self.results), self.config.classes)

    def by_condition(self) -> dict[str, Slice]:
        return slice_by_condition(self.results, self.conditions, self.config.classes)

    def by_factor(self, factor: str) -> dict[str, Slice]:
        return slice_by_factor(self.results, self.conditions, factor, self.config.classes)

    def by_factor_pair(self, factor_a: str, factor_b: str) -> dict[str, Slice]:
        return slice_by_factor_pair(
            self.results, self.conditions, factor_a, factor_b, self.config.classes
        )

    def all_slices(self, factors: Sequence[str], pairs: Sequence[tuple[str, str]]) -> dict[str, Slice]:
        """Every slice worth ranking: single factors, pairs, and full cells."""
        out: dict[str, Slice] = {}
        for factor in factors:
            for bucket, sl in self.by_factor(factor).items():
                out[f"{factor}={bucket}"] = sl
        for factor_a, factor_b in pairs:
            for key, sl in self.by_factor_pair(factor_a, factor_b).items():
                out[f"{factor_a}×{factor_b}={key}"] = sl
        for label, sl in self.by_condition().items():
            out[f"cell={label}"] = sl
        return out

    # -- persistence ----------------------------------------------------

    def as_dict(self) -> dict[str, object]:
        return {
            "model": self.model.as_dict(),
            "manifest_name": self.manifest_name,
            "manifest_fingerprint": self.manifest_fingerprint,
            "scenario_suite": self.suite,
            "config": self.config.as_dict(),
            "data_source": self.data_source,
            "frame_count": len(self.results),
            "overall": self.overall().as_dict(),
            "frames": [r.as_dict() for r in self.results],
        }

    def write(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.as_dict(), indent=2, sort_keys=True))
        return path


def evaluate(
    manifest: Manifest,
    truth: Mapping[str, Sequence[Box]],
    predictions: Mapping[str, Sequence[Box]],
    model: ModelRef,
    config: EvalConfig | None = None,
    data_source: str = "unspecified",
    require_complete: bool = True,
) -> Evaluation:
    """Score `predictions` against `truth` over exactly the frames in `manifest`.

    Args:
        require_complete: if True (the default), refuse to evaluate when the
            model produced no output for some manifest frames. A silently
            skipped frame inflates every metric — a model that crashes on dark
            images would otherwise score beautifully on the ones it survived.

    Raises:
        EvaluationError: on missing ground truth, or on missing predictions
            when `require_complete` is set.
    """
    config = config or EvalConfig()

    missing_truth = [s.scenario_id for s in manifest.scenarios if s.scenario_id not in truth]
    if missing_truth:
        raise EvaluationError(
            f"ground truth missing for {len(missing_truth)} manifest frames, "
            f"e.g. {missing_truth[:3]}"
        )

    missing_preds = [s.scenario_id for s in manifest.scenarios if s.scenario_id not in predictions]
    if missing_preds and require_complete:
        raise EvaluationError(
            f"model {model.ref} produced no predictions for {len(missing_preds)} of "
            f"{len(manifest)} manifest frames, e.g. {missing_preds[:3]}. "
            f"Scoring only the frames it managed would overstate performance. "
            f"Pass require_complete=False only if empty output is a deliberate "
            f"'detected nothing' result."
        )

    results: list[FrameResult] = []
    conditions: dict[str, Condition] = {}
    for scenario in manifest.scenarios:
        sid = scenario.scenario_id
        conditions[sid] = scenario.condition
        results.append(
            match_frame(
                sid,
                truth[sid],
                predictions.get(sid, ()),
                truth_compliant=scenario.condition.helmet_present,
                iou_threshold=config.iou_threshold,
                score_threshold=config.score_threshold,
                classes=config.classes,
            )
        )

    return Evaluation(
        model=model,
        manifest_name=manifest.name,
        manifest_fingerprint=manifest.fingerprint,
        suite=manifest.suite,
        config=config,
        results=tuple(results),
        conditions=conditions,
        data_source=data_source,
    )
