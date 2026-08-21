"""Match detections against ground truth, per frame.

Greedy confidence-ordered matching, the convention COCO evaluation uses:
walk predictions from most to least confident, and let each claim the
best still-unclaimed ground-truth box of the same class above the IoU
threshold. Whatever is left over is a false positive or a false negative.

Also derived here: the frame-level *safety verdict*. Detection metrics tell an
ML engineer how the model behaves; the safety verdict tells a safety manager
whether the system would have flagged a bare-headed worker. They are not the
same question, and conflating them is how a 91%-accurate model gets signed off
while missing the cases that matter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from .boxes import Box, iou

DEFAULT_IOU_THRESHOLD = 0.5
DEFAULT_SCORE_THRESHOLD = 0.35


@dataclass(frozen=True)
class ClassCounts:
    """True positives, false positives and false negatives for one class."""

    label: str
    tp: int = 0
    fp: int = 0
    fn: int = 0

    def __add__(self, other: "ClassCounts") -> "ClassCounts":
        if self.label != other.label:
            raise ValueError(f"cannot add counts for {self.label!r} and {other.label!r}")
        return ClassCounts(self.label, self.tp + other.tp, self.fp + other.fp, self.fn + other.fn)

    def as_dict(self) -> dict[str, object]:
        return {"label": self.label, "tp": self.tp, "fp": self.fp, "fn": self.fn}


@dataclass(frozen=True)
class SafetyVerdict:
    """Frame-level compliance call, with its operational consequence.

    `truth_compliant` comes from the scenario (did the scene contain a hard
    hat?). `predicted_compliant` is what the system would have concluded.

    The asymmetry matters:
      * dangerous miss — bare head passed as compliant. A worker is unprotected
        and nobody is alerted. This is the failure that injures someone.
      * false alarm — compliant worker flagged. Annoying, erodes trust in the
        system, but nobody gets hurt.
    """

    truth_compliant: bool
    predicted_compliant: bool

    @property
    def dangerous_miss(self) -> bool:
        return (not self.truth_compliant) and self.predicted_compliant

    @property
    def false_alarm(self) -> bool:
        return self.truth_compliant and (not self.predicted_compliant)

    @property
    def correct(self) -> bool:
        return self.truth_compliant == self.predicted_compliant

    def as_dict(self) -> dict[str, object]:
        return {
            "truth_compliant": self.truth_compliant,
            "predicted_compliant": self.predicted_compliant,
            "dangerous_miss": self.dangerous_miss,
            "false_alarm": self.false_alarm,
            "correct": self.correct,
        }


@dataclass(frozen=True)
class FrameResult:
    """Everything learned from scoring one frame."""

    scenario_id: str
    counts: dict[str, ClassCounts]
    safety: SafetyVerdict
    matched_ious: tuple[float, ...] = field(default=())

    def as_dict(self) -> dict[str, object]:
        return {
            "scenario_id": self.scenario_id,
            "counts": {k: v.as_dict() for k, v in sorted(self.counts.items())},
            "safety": self.safety.as_dict(),
        }


def match_frame(
    scenario_id: str,
    truth: Sequence[Box],
    predictions: Sequence[Box],
    *,
    truth_compliant: bool,
    iou_threshold: float = DEFAULT_IOU_THRESHOLD,
    score_threshold: float = DEFAULT_SCORE_THRESHOLD,
    classes: Sequence[str] = ("person", "hard_hat"),
) -> FrameResult:
    """Score one frame.

    Args:
        truth_compliant: whether the scene actually contained a hard hat.
            Taken from the scenario metadata, never inferred from the boxes.
        score_threshold: predictions below this confidence are discarded
            before matching. Declared in the report alongside every metric.
    """
    kept = [p for p in predictions if (p.score is None or p.score >= score_threshold)]

    counts: dict[str, ClassCounts] = {}
    matched_ious: list[float] = []

    for label in classes:
        gt = [b for b in truth if b.label == label]
        preds = sorted(
            (p for p in kept if p.label == label),
            key=lambda b: (-(b.score if b.score is not None else 1.0), b.x1, b.y1),
        )

        claimed: set[int] = set()
        tp = 0
        for pred in preds:
            best_index, best_iou = -1, 0.0
            for index, truth_box in enumerate(gt):
                if index in claimed:
                    continue
                overlap = iou(pred, truth_box)
                if overlap > best_iou:
                    best_index, best_iou = index, overlap
            if best_index >= 0 and best_iou >= iou_threshold:
                claimed.add(best_index)
                matched_ious.append(best_iou)
                tp += 1

        counts[label] = ClassCounts(
            label=label, tp=tp, fp=len(preds) - tp, fn=len(gt) - tp
        )

    # The system concludes "compliant" when it detected a hard hat at all.
    predicted_compliant = any(
        p.label == "hard_hat" for p in kept
    )

    return FrameResult(
        scenario_id=scenario_id,
        counts=counts,
        safety=SafetyVerdict(
            truth_compliant=truth_compliant,
            predicted_compliant=predicted_compliant,
        ),
        matched_ious=tuple(matched_ious),
    )
