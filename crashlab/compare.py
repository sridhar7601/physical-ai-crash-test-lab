"""Baseline versus candidate, on a provably unchanged test suite.

The one hard guarantee this module provides: it raises rather than compares
when the two evaluations did not run on the identical manifest. Every
before-and-after claim in the report depends on that, and "we're pretty sure
it was the same test set" is not a foundation to put a safety argument on.

It also reports regressions with the same prominence as improvements. A tool
that only surfaces wins is a sales demo, not an instrument.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

from .analysis import DEFAULT_FACTORS, DEFAULT_PAIRS
from .evaluate import Evaluation
from .metrics import Z_95, Rate


class ComparisonError(ValueError):
    """The two evaluations are not comparable."""


@dataclass(frozen=True)
class SliceDelta:
    """One condition slice, before and after.

    Classification uses a two-proportion z-test on the *difference*, not a
    comparison of the two separate confidence intervals. Non-overlapping
    intervals are a much stricter bar than a test of the difference — using
    them as the criterion buries real regressions as "inconclusive", which is
    the one direction of error this tool must not make.

    The test treats the two samples as independent. They are in fact paired
    (both models ran on the same frames), so a paired test would have more
    power still; the independent form is the conservative choice and is noted
    as such in the report.
    """

    slice_name: str
    dimension: str
    frames: int
    baseline: Rate
    candidate: Rate
    min_samples: int = 20

    @property
    def delta(self) -> float | None:
        if self.baseline.value is None or self.candidate.value is None:
            return None
        return self.candidate.value - self.baseline.value

    @property
    def underpowered(self) -> bool:
        """True when either side has too few samples to support a verdict."""
        return (
            self.baseline.denominator < self.min_samples
            or self.candidate.denominator < self.min_samples
        )

    @property
    def intervals_overlap(self) -> bool:
        """Informational only — deliberately not the classification rule."""
        a, b = self.baseline.interval, self.candidate.interval
        if a is None or b is None:
            return True
        return a[0] <= b[1] and b[0] <= a[1]

    @property
    def z_statistic(self) -> float | None:
        """Two-proportion z on the difference. None when undefined."""
        p1, p2 = self.baseline.value, self.candidate.value
        n1, n2 = self.baseline.denominator, self.candidate.denominator
        if p1 is None or p2 is None or n1 == 0 or n2 == 0:
            return None
        variance = p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2
        if variance <= 0.0:
            # Both proportions at a boundary: significant iff they differ.
            return None if p1 == p2 else math.inf * (1 if p2 > p1 else -1)
        return (p2 - p1) / math.sqrt(variance)

    @property
    def significant(self) -> bool:
        z = self.z_statistic
        return z is not None and abs(z) >= Z_95

    def classify(self, threshold: float = 0.05) -> str:
        """``improved`` | ``regressed`` | ``unchanged`` | ``underpowered`` | ``inconclusive``.

        Order matters. Sample size is checked first: a slice with too little
        evidence gets no verdict at all, in either direction. This mirrors the
        bar `analysis.analyse` applies to findings — a regression reported off
        ten frames would undercut every other number in the report.
        """
        delta = self.delta
        if delta is None:
            return "undefined"
        if self.underpowered:
            return "underpowered"
        if abs(delta) < threshold:
            return "unchanged"
        if not self.significant:
            return "inconclusive"
        return "improved" if delta > 0 else "regressed"

    def as_dict(self) -> dict[str, object]:
        z = self.z_statistic
        return {
            "slice": self.slice_name,
            "dimension": self.dimension,
            "frames": self.frames,
            "baseline": self.baseline.as_dict(),
            "candidate": self.candidate.as_dict(),
            "delta": self.delta,
            "z_statistic": None if z is None or math.isinf(z) else z,
            "significant_at_95": self.significant,
            "intervals_overlap": self.intervals_overlap,
            "underpowered": self.underpowered,
            "classification": self.classify(),
        }


@dataclass(frozen=True)
class Comparison:
    """The full before/after picture on one locked manifest."""

    metric_name: str
    manifest_name: str
    manifest_fingerprint: str
    baseline_ref: str
    candidate_ref: str
    overall: SliceDelta
    slices: tuple[SliceDelta, ...]
    threshold: float

    def _of(self, classification: str) -> tuple[SliceDelta, ...]:
        return tuple(s for s in self.slices if s.classify(self.threshold) == classification)

    def improved(self) -> tuple[SliceDelta, ...]:
        return self._of("improved")

    def regressed(self) -> tuple[SliceDelta, ...]:
        return self._of("regressed")

    def inconclusive(self) -> tuple[SliceDelta, ...]:
        return self._of("inconclusive")

    def underpowered(self) -> tuple[SliceDelta, ...]:
        return self._of("underpowered")

    def unchanged(self) -> tuple[SliceDelta, ...]:
        return self._of("unchanged")

    def as_dict(self) -> dict[str, object]:
        return {
            "metric": self.metric_name,
            "manifest_name": self.manifest_name,
            "manifest_fingerprint": self.manifest_fingerprint,
            "baseline": self.baseline_ref,
            "candidate": self.candidate_ref,
            "material_change_threshold": self.threshold,
            "significance_test": (
                "two-proportion z-test on the difference, 95% two-sided; treats the "
                "two samples as independent, which is conservative given both models "
                "ran on identical frames"
            ),
            "overall": self.overall.as_dict(),
            "improved": [s.as_dict() for s in self.improved()],
            "regressed": [s.as_dict() for s in self.regressed()],
            "inconclusive": [s.as_dict() for s in self.inconclusive()],
            "underpowered": [s.as_dict() for s in self.underpowered()],
            "all_slices": [s.as_dict() for s in self.slices],
        }


def compare(
    baseline: Evaluation,
    candidate: Evaluation,
    metric: str = "hard_hat_recall",
    factors: Sequence[str] = DEFAULT_FACTORS,
    pairs: Sequence[tuple[str, str]] = DEFAULT_PAIRS,
    threshold: float = 0.05,
) -> Comparison:
    """Compare two evaluations that ran on the same manifest.

    Raises:
        ComparisonError: if the manifest fingerprints differ, if the
            evaluation thresholds differ, or if the models are identical.
    """
    if baseline.manifest_fingerprint != candidate.manifest_fingerprint:
        raise ComparisonError(
            "refusing to compare: the two evaluations ran on different test "
            f"suites.\n  baseline {baseline.manifest_name} "
            f"fingerprint={baseline.manifest_fingerprint}\n  candidate "
            f"{candidate.manifest_name} fingerprint={candidate.manifest_fingerprint}\n"
            "A before/after claim requires a byte-identical test suite."
        )

    if baseline.config.as_dict() != candidate.config.as_dict():
        raise ComparisonError(
            "refusing to compare: different evaluation thresholds.\n"
            f"  baseline  {baseline.config.as_dict()}\n"
            f"  candidate {candidate.config.as_dict()}\n"
            "Changing the confidence or IoU threshold changes the metric, so "
            "the difference would not be attributable to the model."
        )

    if baseline.model.ref == candidate.model.ref:
        raise ComparisonError(
            f"baseline and candidate are the same model ({baseline.model.ref}). "
            "Nothing to compare."
        )

    base_slices = baseline.all_slices(factors, pairs)
    cand_slices = candidate.all_slices(factors, pairs)

    min_samples = baseline.config.min_samples_for_finding

    deltas: list[SliceDelta] = []
    for name in sorted(set(base_slices) & set(cand_slices)):
        b, c = base_slices[name], cand_slices[name]
        base_rate, cand_rate = b.primary(metric), c.primary(metric)
        # A slice where the metric has no denominator carries no information.
        # `hard_hat_recall` over helmet_state=absent is the common case: there
        # were no hard hats to find, so recall is undefined rather than zero.
        if not base_rate.is_reportable and not cand_rate.is_reportable:
            continue
        deltas.append(
            SliceDelta(
                slice_name=name,
                dimension=b.dimension,
                frames=b.frames,
                baseline=base_rate,
                candidate=cand_rate,
                min_samples=min_samples,
            )
        )

    # Worst regressions first, then largest improvements — the order a
    # reviewer should read them in.
    deltas.sort(key=lambda d: (d.delta if d.delta is not None else 0.0, d.slice_name))

    overall = SliceDelta(
        slice_name="overall",
        dimension="overall",
        frames=baseline.overall().frames,
        baseline=baseline.overall().primary(metric),
        candidate=candidate.overall().primary(metric),
        min_samples=min_samples,
    )

    return Comparison(
        metric_name=metric,
        manifest_name=baseline.manifest_name,
        manifest_fingerprint=baseline.manifest_fingerprint,
        baseline_ref=baseline.model.ref,
        candidate_ref=candidate.model.ref,
        overall=overall,
        slices=tuple(deltas),
        threshold=threshold,
    )
