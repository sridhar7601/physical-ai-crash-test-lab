"""Metrics, sliced by condition.

This is the module that turns "91% accurate" into "41% in dim light with a
partially occluded helmet". Everything here obeys two rules from PLAN.md:

* No proportion is ever reported without its denominator. A rate computed on
  four frames and a rate computed on four hundred look identical on a
  dashboard and mean entirely different things.
* Interval estimates use the Wilson score interval rather than the normal
  approximation, because per-cell sample sizes here are small and the normal
  approximation misbehaves badly near 0 and 1 — exactly where the interesting
  failures live.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

from .matching import ClassCounts, FrameResult
from .schema import FACTORS, Condition

#: 95% two-sided normal quantile, for Wilson intervals.
Z_95 = 1.959963984540054


def wilson_interval(successes: int, total: int, z: float = Z_95) -> tuple[float, float] | None:
    """Wilson score interval for a binomial proportion.

    Returns None when `total` is zero — an unknown rate, not a rate of zero.
    """
    if total <= 0:
        return None
    if successes < 0 or successes > total:
        raise ValueError(f"successes={successes} outside [0, {total}]")
    n = float(total)
    k = float(successes)
    z2 = z * z
    denominator = n + z2
    centre = (k + z2 / 2.0) / denominator
    spread = (z / denominator) * math.sqrt((k * (n - k) / n) + (z2 / 4.0))
    return max(0.0, centre - spread), min(1.0, centre + spread)


@dataclass(frozen=True)
class Rate:
    """A proportion that always travels with its denominator."""

    name: str
    numerator: int
    denominator: int

    @property
    def value(self) -> float | None:
        if self.denominator == 0:
            return None
        return self.numerator / self.denominator

    @property
    def interval(self) -> tuple[float, float] | None:
        return wilson_interval(self.numerator, self.denominator)

    @property
    def is_reportable(self) -> bool:
        """False when there is no evidence at all behind this number."""
        return self.denominator > 0

    def format(self, places: int = 3) -> str:
        if self.value is None:
            return f"{self.name}: n/a (n=0)"
        text = f"{self.name}: {self.value:.{places}f} (n={self.denominator})"
        ci = self.interval
        if ci is not None:
            text += f" [95% CI {ci[0]:.3f}–{ci[1]:.3f}]"
        return text

    def as_dict(self) -> dict[str, object]:
        ci = self.interval
        return {
            "name": self.name,
            "value": self.value,
            "numerator": self.numerator,
            "denominator": self.denominator,
            "ci95_low": None if ci is None else ci[0],
            "ci95_high": None if ci is None else ci[1],
        }


@dataclass(frozen=True)
class DetectionMetrics:
    """Precision / recall / F1 for one class, plus the raw counts."""

    label: str
    counts: ClassCounts

    @property
    def precision(self) -> Rate:
        return Rate("precision", self.counts.tp, self.counts.tp + self.counts.fp)

    @property
    def recall(self) -> Rate:
        return Rate("recall", self.counts.tp, self.counts.tp + self.counts.fn)

    @property
    def f1(self) -> float | None:
        p, r = self.precision.value, self.recall.value
        if p is None or r is None or (p + r) == 0:
            return None
        return 2 * p * r / (p + r)

    def as_dict(self) -> dict[str, object]:
        return {
            "label": self.label,
            "counts": self.counts.as_dict(),
            "precision": self.precision.as_dict(),
            "recall": self.recall.as_dict(),
            "f1": self.f1,
        }


@dataclass(frozen=True)
class SafetyMetrics:
    """Frame-level compliance performance.

    `dangerous_miss_rate` is the headline number for a safety audience: of the
    frames where the worker genuinely had no hard hat, how often did the system
    say they were fine?
    """

    frames: int
    dangerous_misses: int
    non_compliant_frames: int
    false_alarms: int
    compliant_frames: int
    correct: int

    @property
    def dangerous_miss_rate(self) -> Rate:
        return Rate("dangerous_miss_rate", self.dangerous_misses, self.non_compliant_frames)

    @property
    def false_alarm_rate(self) -> Rate:
        return Rate("false_alarm_rate", self.false_alarms, self.compliant_frames)

    @property
    def frame_accuracy(self) -> Rate:
        return Rate("frame_accuracy", self.correct, self.frames)

    def as_dict(self) -> dict[str, object]:
        return {
            "frames": self.frames,
            "dangerous_miss_rate": self.dangerous_miss_rate.as_dict(),
            "false_alarm_rate": self.false_alarm_rate.as_dict(),
            "frame_accuracy": self.frame_accuracy.as_dict(),
        }


def safety_metrics(results: Iterable[FrameResult]) -> SafetyMetrics:
    frames = dangerous = non_compliant = alarms = compliant = correct = 0
    for result in results:
        frames += 1
        verdict = result.safety
        if verdict.truth_compliant:
            compliant += 1
            alarms += int(verdict.false_alarm)
        else:
            non_compliant += 1
            dangerous += int(verdict.dangerous_miss)
        correct += int(verdict.correct)
    return SafetyMetrics(
        frames=frames,
        dangerous_misses=dangerous,
        non_compliant_frames=non_compliant,
        false_alarms=alarms,
        compliant_frames=compliant,
        correct=correct,
    )


def detection_metrics(
    results: Iterable[FrameResult], classes: Sequence[str] = ("person", "hard_hat")
) -> dict[str, DetectionMetrics]:
    totals = {label: ClassCounts(label) for label in classes}
    for result in results:
        for label, counts in result.counts.items():
            if label in totals:
                totals[label] = totals[label] + counts
    return {label: DetectionMetrics(label, counts) for label, counts in totals.items()}


# --------------------------------------------------------------------------
# Slices: the same metrics, restricted to a subset of frames
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Slice:
    """Metrics over a named subset of frames.

    `dimension` records *how* the subset was carved (a whole condition cell, a
    single factor bucket, a pair of factors), so the report can distinguish a
    finding about "dim light" from a finding about "dim light AND occlusion".

    `constraints` records *what* was held fixed, as factor -> bucket. This is
    what makes a finding actionable: the remediation stage needs to turn "the
    worst slice" back into concrete scenes the simulator can render, and a
    display name like ``lighting×helmet_state=dim+partial`` is not something to
    parse back apart with string surgery.
    """

    name: str
    dimension: str
    frames: int
    detection: dict[str, DetectionMetrics]
    safety: SafetyMetrics
    scenario_ids: tuple[str, ...] = ()
    constraints: Mapping[str, str] = field(default_factory=dict)

    def primary(self, metric: str = "hard_hat_recall") -> Rate:
        """The number this slice is judged on.

        Defaults to hard-hat recall: of the hard hats that were really there,
        how many did the detector find? Missing them is the safety-relevant
        direction of error.
        """
        if metric == "hard_hat_recall":
            return self.detection["hard_hat"].recall
        if metric == "hard_hat_precision":
            return self.detection["hard_hat"].precision
        if metric == "person_recall":
            return self.detection["person"].recall
        if metric == "dangerous_miss_rate":
            return self.safety.dangerous_miss_rate
        if metric == "frame_accuracy":
            return self.safety.frame_accuracy
        raise ValueError(f"unknown primary metric {metric!r}")

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "dimension": self.dimension,
            "frames": self.frames,
            "constraints": dict(sorted(self.constraints.items())),
            "detection": {k: v.as_dict() for k, v in sorted(self.detection.items())},
            "safety": self.safety.as_dict(),
        }


def build_slice(
    name: str,
    dimension: str,
    results: Sequence[FrameResult],
    classes: Sequence[str] = ("person", "hard_hat"),
    constraints: Mapping[str, str] | None = None,
) -> Slice:
    return Slice(
        name=name,
        dimension=dimension,
        frames=len(results),
        detection=detection_metrics(results, classes),
        safety=safety_metrics(results),
        scenario_ids=tuple(r.scenario_id for r in results),
        constraints=dict(constraints or {}),
    )


def slice_by_condition(
    results: Sequence[FrameResult],
    conditions: Mapping[str, Condition],
    classes: Sequence[str] = ("person", "hard_hat"),
) -> dict[str, Slice]:
    """One slice per full condition cell."""
    grouped: dict[str, list[FrameResult]] = {}
    cell_constraints: dict[str, dict[str, str]] = {}
    for result in results:
        condition = conditions.get(result.scenario_id)
        if condition is None:
            continue
        label = condition.label()
        grouped.setdefault(label, []).append(result)
        cell_constraints[label] = condition.as_dict()
    return {
        label: build_slice(
            label, "condition_cell", members, classes, cell_constraints[label]
        )
        for label, members in sorted(grouped.items())
    }


def slice_by_factor(
    results: Sequence[FrameResult],
    conditions: Mapping[str, Condition],
    factor: str,
    classes: Sequence[str] = ("person", "hard_hat"),
) -> dict[str, Slice]:
    """One slice per bucket of a single factor, marginalising the others."""
    if factor not in FACTORS:
        raise ValueError(f"unknown factor {factor!r}")
    grouped: dict[str, list[FrameResult]] = {}
    for result in results:
        condition = conditions.get(result.scenario_id)
        if condition is None:
            continue
        grouped.setdefault(getattr(condition, factor), []).append(result)
    return {
        bucket: build_slice(
            f"{factor}={bucket}", factor, members, classes, {factor: bucket}
        )
        for bucket, members in sorted(grouped.items())
    }


def slice_by_factor_pair(
    results: Sequence[FrameResult],
    conditions: Mapping[str, Condition],
    factor_a: str,
    factor_b: str,
    classes: Sequence[str] = ("person", "hard_hat"),
) -> dict[str, Slice]:
    """One slice per combination of two factors.

    Pairs are where the interesting failures hide: a model can be acceptable
    in dim light and acceptable under occlusion, yet fall apart when both
    happen at once. Single-factor marginals average that interaction away.
    """
    for factor in (factor_a, factor_b):
        if factor not in FACTORS:
            raise ValueError(f"unknown factor {factor!r}")
    grouped: dict[str, list[FrameResult]] = {}
    pair_constraints: dict[str, dict[str, str]] = {}
    for result in results:
        condition = conditions.get(result.scenario_id)
        if condition is None:
            continue
        bucket_a = getattr(condition, factor_a)
        bucket_b = getattr(condition, factor_b)
        key = f"{bucket_a}+{bucket_b}"
        grouped.setdefault(key, []).append(result)
        pair_constraints[key] = {factor_a: bucket_a, factor_b: bucket_b}
    dimension = f"{factor_a}×{factor_b}"
    return {
        key: build_slice(
            f"{dimension}={key}", dimension, members, classes, pair_constraints[key]
        )
        for key, members in sorted(grouped.items())
    }
