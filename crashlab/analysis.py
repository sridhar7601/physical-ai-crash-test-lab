"""Rank the weak scenario clusters.

Step 6 of the loop, and the reason the product exists: an overall score hides
the holes, so we sort the same frames into condition slices and rank them by
how badly they perform.

Two disciplines keep this honest:

* A slice below `min_samples` is reported as **underpowered**, not as a
  finding. It is listed separately so a gap in coverage stays visible instead
  of quietly vanishing.
* Ranking prefers the *upper* confidence bound of the failure rate. A slice
  scoring 0.30 on 8 frames and one scoring 0.30 on 300 frames are not equally
  strong evidence, and the interval is what encodes the difference.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence

from .evaluate import Evaluation
from .metrics import Rate, Slice
from .schema import FACTORS

#: Factor pairs worth ranking. Interactions between illumination and occlusion
#: are the classic hiding place for perception failures.
DEFAULT_PAIRS: tuple[tuple[str, str], ...] = (
    ("lighting", "helmet_state"),
    ("lighting", "distance"),
    ("camera_angle", "helmet_state"),
    ("distance", "helmet_state"),
)

DEFAULT_FACTORS: tuple[str, ...] = ("lighting", "camera_angle", "distance", "helmet_state")


@dataclass(frozen=True)
class Finding:
    """One condition slice, with enough context to defend or dismiss it."""

    slice_name: str
    dimension: str
    frames: int
    metric_name: str
    rate: Rate
    underpowered: bool
    constraints: Mapping[str, str] = field(default_factory=dict)

    @property
    def specificity(self) -> int:
        """How many factors this finding pins down.

        A finding over two factors is more actionable than one over a single
        margin: it names a scene the simulator can actually render.
        """
        return len(self.constraints)

    @property
    def value(self) -> float | None:
        return self.rate.value

    @property
    def pessimistic(self) -> float:
        """Worst plausible performance, for ranking.

        Uses the lower confidence bound so a small sample cannot win the
        ranking on a lucky point estimate alone.
        """
        interval = self.rate.interval
        if interval is None:
            return 1.0
        return interval[0]

    def as_dict(self) -> dict[str, object]:
        return {
            "slice": self.slice_name,
            "dimension": self.dimension,
            "frames": self.frames,
            "metric": self.metric_name,
            "underpowered": self.underpowered,
            "constraints": dict(sorted(self.constraints.items())),
            **{k: v for k, v in self.rate.as_dict().items() if k != "name"},
        }

    def describe(self) -> str:
        flag = "  [UNDERPOWERED]" if self.underpowered else ""
        return f"{self.slice_name:<44} {self.rate.format()}{flag}"


@dataclass(frozen=True)
class FailureAnalysis:
    """The ranked outcome of one evaluation."""

    metric_name: str
    higher_is_better: bool
    findings: tuple[Finding, ...]
    underpowered: tuple[Finding, ...]
    min_samples: int

    @property
    def weakest(self) -> Finding | None:
        """The worst adequately-powered slice, or None if there are none."""
        return self.findings[0] if self.findings else None

    def cells(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.dimension == "condition_cell")

    def interactions(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if "×" in f.dimension)

    def as_dict(self) -> dict[str, object]:
        return {
            "metric": self.metric_name,
            "higher_is_better": self.higher_is_better,
            "min_samples_for_finding": self.min_samples,
            "weakest_slice": None if self.weakest is None else self.weakest.as_dict(),
            "findings": [f.as_dict() for f in self.findings],
            "underpowered_slices": [f.as_dict() for f in self.underpowered],
        }


def analyse(
    evaluation: Evaluation,
    metric: str = "hard_hat_recall",
    factors: Sequence[str] = DEFAULT_FACTORS,
    pairs: Sequence[tuple[str, str]] = DEFAULT_PAIRS,
    min_samples: int | None = None,
    higher_is_better: bool = True,
) -> FailureAnalysis:
    """Rank every condition slice from worst to best on `metric`.

    Args:
        metric: see `Slice.primary`. Defaults to hard-hat recall — missed hats
            are the safety-relevant direction of error.
        higher_is_better: False for metrics like `dangerous_miss_rate`, where a
            large value is the bad outcome.
    """
    for factor in factors:
        if factor not in FACTORS:
            raise ValueError(f"unknown factor {factor!r}")

    min_samples = (
        evaluation.config.min_samples_for_finding if min_samples is None else min_samples
    )

    findings: list[Finding] = []
    weak_evidence: list[Finding] = []

    for name, sl in evaluation.all_slices(factors, pairs).items():
        rate = sl.primary(metric)
        if not rate.is_reportable:
            # No denominator at all: the metric is undefined here, not zero.
            continue
        finding = Finding(
            slice_name=name,
            dimension=sl.dimension,
            frames=sl.frames,
            metric_name=metric,
            rate=rate,
            underpowered=rate.denominator < min_samples,
            constraints=dict(sl.constraints),
        )
        (weak_evidence if finding.underpowered else findings).append(finding)

    def sort_key(f: Finding) -> tuple[float, int, str]:
        # Worst first. `pessimistic` is the lower CI bound, so for a
        # higher-is-better metric we ascend it; otherwise we descend the point
        # estimate's optimistic side.
        if higher_is_better:
            return (f.pessimistic, -f.frames, f.slice_name)
        interval = f.rate.interval
        upper = interval[1] if interval else 0.0
        return (-upper, -f.frames, f.slice_name)

    findings.sort(key=sort_key)
    weak_evidence.sort(key=sort_key)

    return FailureAnalysis(
        metric_name=metric,
        higher_is_better=higher_is_better,
        findings=tuple(findings),
        underpowered=tuple(weak_evidence),
        min_samples=min_samples,
    )


@dataclass(frozen=True)
class RemediationTarget:
    """A concrete, renderable data request derived from a finding."""

    source_finding: Finding
    conditions: tuple  # tuple[Condition, ...]
    neighbour_count: int

    def as_dict(self) -> dict[str, object]:
        return {
            "derived_from": self.source_finding.as_dict(),
            "condition_count": len(self.conditions),
            "neighbour_count": self.neighbour_count,
            "conditions": [c.label() for c in self.conditions],
        }


class NoTargetError(ValueError):
    """No finding in the analysis can be turned into a data request."""


def target_conditions(
    analysis: FailureAnalysis,
    evaluation: Evaluation,
    top_n: int = 1,
    include_neighbours: bool = True,
) -> RemediationTarget:
    """Turn the ranking into a concrete remediation request.

    A finding is a *slice*, and most slices are not single scenes: with a
    realistic replicate count, individual condition cells almost always fall
    below the sample bar, while interaction slices like ``dim+partial`` have
    ample evidence. So rather than insisting on cells, we take the worst
    adequately-powered finding and expand its constraints into every matching
    condition — which is the right request anyway, since remediating a whole
    interaction generalises better than drilling one exact configuration.

    Raises:
        NoTargetError: when nothing is both adequately powered and specific
            enough to render. Silently returning an empty request would send a
            zero-frame job to the simulator and read as success.
    """
    from .suite import neighbours

    all_conditions = sorted(set(evaluation.conditions.values()), key=lambda c: c.key())

    # Prefer the worst finding that actually pins factors down. Findings are
    # already ordered worst-first; among equals, more specific wins.
    candidates = [f for f in analysis.findings if f.specificity > 0]
    if not candidates:
        raise NoTargetError(
            f"no adequately-powered finding to target: {len(analysis.findings)} "
            f"findings, {len(analysis.underpowered)} slices withheld as "
            f"underpowered (<{analysis.min_samples} samples). Raise replicates "
            f"or lower min_samples — deliberately, and say so in the report."
        )

    chosen_findings = candidates[:top_n]
    matched: list = []
    for finding in chosen_findings:
        for condition in all_conditions:
            if all(
                getattr(condition, factor) == bucket
                for factor, bucket in finding.constraints.items()
            ):
                if condition not in matched:
                    matched.append(condition)

    if not matched:
        raise NoTargetError(
            f"finding {chosen_findings[0].slice_name!r} matched no condition in "
            f"the suite; constraints {dict(chosen_findings[0].constraints)}"
        )

    direct = len(matched)
    if include_neighbours:
        for condition in list(matched):
            for neighbour in neighbours(condition):
                if neighbour not in matched:
                    matched.append(neighbour)

    return RemediationTarget(
        source_finding=chosen_findings[0],
        conditions=tuple(matched),
        neighbour_count=len(matched) - direct,
    )
