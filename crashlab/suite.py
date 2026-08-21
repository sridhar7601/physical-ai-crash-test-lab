"""Scenario suites and the locked train/test split.

The integrity of every claim this system makes rests on one thing: the test
suite used to score the candidate is byte-for-byte the suite used to score the
baseline. So a `Manifest` carries a `fingerprint` — a hash of its scenario ids
— and `compare.py` refuses to compare across differing fingerprints.

The split is *stratified per condition cell*. A plain random split would leave
some cells with one or two test frames, and a per-condition metric computed on
two frames is noise wearing a lab coat.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from .schema import (
    SCHEMA_VERSION,
    Condition,
    Scenario,
    dumps,
    iter_conditions,
    make_scenario,
)


class SplitError(ValueError):
    """The requested split cannot be satisfied by the suite as built."""


@dataclass(frozen=True)
class Manifest:
    """An ordered, hashable set of scenarios with a declared role."""

    name: str
    role: str  # "test" | "train" | "remediation" | "full"
    suite: str
    scenarios: tuple[Scenario, ...]

    def __len__(self) -> int:
        return len(self.scenarios)

    @property
    def fingerprint(self) -> str:
        """Stable hash over scenario ids and seeds.

        Two manifests with the same fingerprint contain exactly the same
        frames. This is the mechanism behind the "unchanged test suite" claim.
        """
        payload = dumps(
            [[s.scenario_id, s.seed] for s in sorted(self.scenarios, key=lambda s: s.scenario_id)]
        )
        return hashlib.blake2b(payload.encode(), digest_size=16).hexdigest()

    def by_condition(self) -> dict[Condition, tuple[Scenario, ...]]:
        grouped: dict[Condition, list[Scenario]] = {}
        for scenario in self.scenarios:
            grouped.setdefault(scenario.condition, []).append(scenario)
        return {cond: tuple(items) for cond, items in grouped.items()}

    def condition_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for scenario in self.scenarios:
            label = scenario.condition.label()
            counts[label] = counts.get(label, 0) + 1
        return counts

    def scenario_ids(self) -> frozenset[str]:
        return frozenset(s.scenario_id for s in self.scenarios)

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "manifest_name": self.name,
            "role": self.role,
            "scenario_suite": self.suite,
            "fingerprint": self.fingerprint,
            "sample_count": len(self.scenarios),
            "condition_cell_count": len(self.by_condition()),
            "scenarios": [s.as_dict() for s in self.scenarios],
        }

    def write(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.as_dict(), indent=2, sort_keys=True))
        return path

    @classmethod
    def read(cls, path: str | Path) -> "Manifest":
        data = json.loads(Path(path).read_text())
        manifest = cls(
            name=str(data["manifest_name"]),
            role=str(data["role"]),
            suite=str(data["scenario_suite"]),
            scenarios=tuple(Scenario.from_dict(s) for s in data["scenarios"]),
        )
        recorded = str(data.get("fingerprint", ""))
        if recorded and recorded != manifest.fingerprint:
            raise SplitError(
                f"manifest at {path} has been altered since it was written: "
                f"recorded fingerprint {recorded}, recomputed {manifest.fingerprint}"
            )
        return manifest


def build_scenarios(
    suite: str,
    replicates: int,
    levels: Mapping[str, Sequence[str]] | None = None,
) -> tuple[Scenario, ...]:
    """Build `replicates` frames for every cell in the condition matrix."""
    if replicates < 1:
        raise SplitError("replicates must be at least 1")
    scenarios: list[Scenario] = []
    for condition in iter_conditions(levels):
        for replicate in range(replicates):
            scenarios.append(make_scenario(suite, condition, replicate))
    return tuple(scenarios)


def build_suite(
    suite: str,
    replicates: int = 8,
    levels: Mapping[str, Sequence[str]] | None = None,
) -> Manifest:
    """The full scenario suite, before any split."""
    return Manifest(
        name=f"{suite}-full",
        role="full",
        suite=suite,
        scenarios=build_scenarios(suite, replicates, levels),
    )


def stratified_split(
    manifest: Manifest,
    test_per_cell: int,
    split_seed: int = 20260821,
    min_test_per_cell: int = 5,
) -> tuple[Manifest, Manifest]:
    """Split into (train, test), holding out `test_per_cell` frames per cell.

    Args:
        test_per_cell: frames reserved for the exam in EVERY condition cell.
        split_seed: fixed so the split is reproducible.
        min_test_per_cell: refuse to build a suite whose per-cell metrics
            would be statistically meaningless. Set lower only deliberately.

    Raises:
        SplitError: if any cell cannot supply `test_per_cell` frames while
            leaving at least one for training.
    """
    if test_per_cell < min_test_per_cell:
        raise SplitError(
            f"test_per_cell={test_per_cell} is below min_test_per_cell="
            f"{min_test_per_cell}. Per-condition metrics on a handful of "
            f"frames cannot support a finding — raise replicates instead."
        )

    grouped = manifest.by_condition()
    train: list[Scenario] = []
    test: list[Scenario] = []

    for condition in sorted(grouped, key=lambda c: c.key()):
        members = sorted(grouped[condition], key=lambda s: s.scenario_id)
        if len(members) < test_per_cell + 1:
            raise SplitError(
                f"condition {condition.label()!r} has {len(members)} frames; "
                f"need at least {test_per_cell + 1} to hold out "
                f"{test_per_cell} for test and keep 1 for train"
            )
        # Seed per cell so adding a cell later does not reshuffle other cells.
        rng = random.Random(f"{split_seed}/{condition.label()}")
        shuffled = list(members)
        rng.shuffle(shuffled)
        test.extend(shuffled[:test_per_cell])
        train.extend(shuffled[test_per_cell:])

    key = lambda s: s.scenario_id  # noqa: E731
    train_manifest = Manifest(
        name=f"{manifest.suite}-train",
        role="train",
        suite=manifest.suite,
        scenarios=tuple(sorted(train, key=key)),
    )
    test_manifest = Manifest(
        name=f"{manifest.suite}-test",
        role="test",
        suite=manifest.suite,
        scenarios=tuple(sorted(test, key=key)),
    )

    leaked = train_manifest.scenario_ids() & test_manifest.scenario_ids()
    if leaked:
        raise SplitError(f"train/test leak on {len(leaked)} scenarios: {sorted(leaked)[:5]}")

    return train_manifest, test_manifest


def remediation_manifest(
    suite: str,
    conditions: Iterable[Condition],
    frames_per_condition: int,
    test_manifest: Manifest,
    replicate_offset: int = 1000,
) -> Manifest:
    """Build targeted training frames for the conditions that failed.

    New frames use replicate indices offset well past the original suite, so
    their scenario ids — and therefore their seeds — cannot collide with the
    locked test set. The collision check at the end is not paranoia: silently
    training on a test frame would invalidate every number in the report.
    """
    conditions = list(conditions)
    if not conditions:
        raise SplitError(
            "remediation set requested for zero conditions. An empty manifest "
            "would send a no-op job to the simulator and report as success — "
            "refusing. Check that the failure analysis produced a target."
        )
    if frames_per_condition < 1:
        raise SplitError(f"frames_per_condition must be >= 1, got {frames_per_condition}")

    scenarios: list[Scenario] = []
    for condition in conditions:
        for i in range(frames_per_condition):
            scenarios.append(
                make_scenario(suite, condition, replicate_offset + i)
            )

    manifest = Manifest(
        name=f"{suite}-remediation",
        role="remediation",
        suite=suite,
        scenarios=tuple(scenarios),
    )

    overlap = manifest.scenario_ids() & test_manifest.scenario_ids()
    if overlap:
        raise SplitError(
            f"remediation set overlaps the locked test suite on "
            f"{len(overlap)} scenarios: {sorted(overlap)[:5]}. "
            f"Raise replicate_offset."
        )
    return manifest


def neighbours(condition: Condition, factors: Sequence[str] = ("distance", "lighting")) -> list[Condition]:
    """Conditions one bucket away along `factors`.

    PLAN.md section 9 asks remediation to include adjacent conditions, so the
    model learns the underlying difficulty rather than memorising one exact
    configuration.
    """
    from .schema import FACTORS

    out: list[Condition] = []
    for factor in factors:
        current = getattr(condition, factor)
        levels = FACTORS[factor]
        index = levels.index(current)
        for offset in (-1, 1):
            j = index + offset
            if 0 <= j < len(levels):
                out.append(
                    Condition(**{**condition.as_dict(), factor: levels[j]})
                )
    # Deduplicate while keeping order stable.
    seen: set[tuple[str, ...]] = {condition.key()}
    unique: list[Condition] = []
    for cond in out:
        if cond.key() not in seen:
            seen.add(cond.key())
            unique.append(cond)
    return unique
