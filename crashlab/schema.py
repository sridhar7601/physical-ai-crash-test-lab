"""Scenario schema: the vocabulary of the crash-test lab.

Two rules govern this module, both from PLAN.md:

1. Condition buckets are declared HERE, before any results are looked at.
   Choosing buckets after seeing scores is how you accidentally p-hack a
   demo into existence.

2. Every bucket maps to a physical quantity (lux, metres, degrees). That
   mapping is what makes this Physical AI rather than image tagging: the
   simulator consumes it to place lights and cameras, and the report quotes
   it so a reader knows what "dim" actually meant.
"""

from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass, asdict, field
from typing import Iterator, Mapping, Sequence

SCHEMA_VERSION = "1.0.0"


# --------------------------------------------------------------------------
# Factors and their physical meaning
# --------------------------------------------------------------------------

#: Every factor, and every bucket it may take. Declared up front.
FACTORS: dict[str, tuple[str, ...]] = {
    "lighting": ("bright", "normal", "dim"),
    "camera_angle": ("eye_level", "high_oblique"),
    "distance": ("near", "mid", "far"),
    "helmet_state": ("visible", "partial", "absent"),
    "background_clutter": ("low", "high"),
}

#: What each bucket means as a physical quantity. The simulator samples
#: uniformly within the range; the report prints the range verbatim.
PHYSICAL_RANGES: dict[str, dict[str, object]] = {
    "lighting": {
        "unit": "lux (scene illuminance at the worker)",
        "buckets": {
            "bright": (600.0, 1200.0),
            "normal": (200.0, 600.0),
            "dim": (10.0, 80.0),
        },
    },
    "camera_angle": {
        "unit": "degrees of camera elevation below horizontal",
        "buckets": {
            "eye_level": (0.0, 10.0),
            "high_oblique": (35.0, 60.0),
        },
    },
    "distance": {
        "unit": "metres from camera to worker",
        "buckets": {
            "near": (1.5, 3.0),
            "mid": (3.0, 6.0),
            "far": (6.0, 10.0),
        },
    },
    "helmet_state": {
        "unit": "fraction of hard-hat surface visible to the camera",
        "buckets": {
            "visible": (0.85, 1.0),
            "partial": (0.25, 0.60),
            "absent": (0.0, 0.0),  # no hard hat present at all
        },
    },
    "background_clutter": {
        "unit": "count of distractor objects within the frame",
        "buckets": {
            "low": (0, 3),
            "high": (8, 20),
        },
    },
}

#: Buckets of `helmet_state` in which the worker IS wearing a hard hat.
#: `absent` is the safety-critical case: a non-compliant worker.
HELMET_PRESENT_STATES: frozenset[str] = frozenset({"visible", "partial"})

#: Object classes the detector is expected to produce.
CLASSES: tuple[str, ...] = ("person", "hard_hat")

#: PLAN.md section 7 says implement three or four factors. Clutter is pinned
#: to a single value by default so the cell count stays sane; widen it only
#: if the sprint has time to spare.
DEFAULT_FACTOR_LEVELS: dict[str, tuple[str, ...]] = {
    "lighting": FACTORS["lighting"],
    "camera_angle": FACTORS["camera_angle"],
    "distance": FACTORS["distance"],
    "helmet_state": FACTORS["helmet_state"],
    "background_clutter": ("low",),
}


class SchemaError(ValueError):
    """A scenario or factor level that the schema does not define."""


def validate_levels(levels: Mapping[str, Sequence[str]]) -> None:
    """Raise if `levels` names an unknown factor or an undeclared bucket."""
    for factor, chosen in levels.items():
        if factor not in FACTORS:
            raise SchemaError(
                f"unknown factor {factor!r}; known factors: {sorted(FACTORS)}"
            )
        if not chosen:
            raise SchemaError(f"factor {factor!r} has no levels selected")
        unknown = set(chosen) - set(FACTORS[factor])
        if unknown:
            raise SchemaError(
                f"factor {factor!r} has undeclared buckets {sorted(unknown)}; "
                f"declared: {list(FACTORS[factor])}"
            )


# --------------------------------------------------------------------------
# Condition: one cell of the scenario matrix
# --------------------------------------------------------------------------


@dataclass(frozen=True, order=True)
class Condition:
    """One combination of factor buckets — a cell in the scenario matrix."""

    lighting: str
    camera_angle: str
    distance: str
    helmet_state: str
    background_clutter: str = "low"

    def __post_init__(self) -> None:
        for factor in FACTORS:
            value = getattr(self, factor)
            if value not in FACTORS[factor]:
                raise SchemaError(
                    f"{factor}={value!r} is not a declared bucket; "
                    f"declared: {list(FACTORS[factor])}"
                )

    @property
    def helmet_present(self) -> bool:
        """True when a hard hat physically exists in the scene.

        The detector's job is harder than "find a hat": when this is False the
        correct answer is *no hard-hat box at all*, and a spurious detection
        means the system passes a bare-headed worker as compliant.
        """
        return self.helmet_state in HELMET_PRESENT_STATES

    @property
    def expected_objects(self) -> tuple[str, ...]:
        return ("person", "hard_hat") if self.helmet_present else ("person",)

    def key(self) -> tuple[str, ...]:
        """Stable tuple identity, ordered by `FACTORS`."""
        return tuple(getattr(self, factor) for factor in FACTORS)

    def label(self) -> str:
        """Compact human label, e.g. ``dim+high_oblique+far+partial+low``."""
        return "+".join(self.key())

    def slug(self) -> str:
        """Filesystem-safe short form used in scenario ids."""
        return "-".join(getattr(self, f)[:4] for f in FACTORS)

    def as_dict(self) -> dict[str, str]:
        return {factor: getattr(self, factor) for factor in FACTORS}

    def physical_ranges(self) -> dict[str, dict[str, object]]:
        """The physical quantity behind each bucket, for simulator + report."""
        out: dict[str, dict[str, object]] = {}
        for factor in FACTORS:
            bucket = getattr(self, factor)
            spec = PHYSICAL_RANGES[factor]
            low, high = spec["buckets"][bucket]  # type: ignore[index]
            out[factor] = {
                "bucket": bucket,
                "unit": spec["unit"],
                "min": low,
                "max": high,
            }
        return out

    @classmethod
    def from_dict(cls, data: Mapping[str, str]) -> "Condition":
        missing = set(FACTORS) - set(data) - {"background_clutter"}
        if missing:
            raise SchemaError(f"condition missing factors: {sorted(missing)}")
        return cls(**{f: data[f] for f in FACTORS if f in data})


def iter_conditions(
    levels: Mapping[str, Sequence[str]] | None = None,
) -> Iterator[Condition]:
    """Yield every `Condition` in the cross product of `levels`.

    Order is deterministic — it follows the declaration order in `FACTORS`.
    """
    levels = dict(levels or DEFAULT_FACTOR_LEVELS)
    validate_levels(levels)
    ordered = [tuple(levels.get(f, FACTORS[f])) for f in FACTORS]
    for combo in itertools.product(*ordered):
        yield Condition(**dict(zip(FACTORS, combo)))


# --------------------------------------------------------------------------
# Deterministic seeds
# --------------------------------------------------------------------------


def derive_seed(suite_name: str, scenario_id: str) -> int:
    """Map (suite, scenario) to a stable 32-bit seed.

    Derived by hash rather than drawn from a random source, so the same
    scenario id always regenerates the same frame — on any machine, in any
    process, months later. Reproducibility is a headline claim of the report,
    and it cannot rest on a seed someone forgot to write down.
    """
    digest = hashlib.blake2b(
        f"{suite_name}/{scenario_id}".encode(), digest_size=4
    ).digest()
    return int.from_bytes(digest, "big")


# --------------------------------------------------------------------------
# Scenario: one frame to be generated
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Scenario:
    """A single frame request: one condition, one seed, one reproducible image."""

    scenario_id: str
    condition: Condition
    seed: int
    replicate: int
    suite: str

    @property
    def expected_objects(self) -> tuple[str, ...]:
        return self.condition.expected_objects

    def as_dict(self) -> dict[str, object]:
        """The metadata block written beside every generated frame."""
        return {
            "schema_version": SCHEMA_VERSION,
            "scenario_suite": self.suite,
            "scenario_id": self.scenario_id,
            "seed": self.seed,
            "replicate": self.replicate,
            "condition": self.condition.as_dict(),
            "condition_label": self.condition.label(),
            "physical_ranges": self.condition.physical_ranges(),
            "helmet_present": self.condition.helmet_present,
            "expected_objects": list(self.expected_objects),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "Scenario":
        return cls(
            scenario_id=str(data["scenario_id"]),
            condition=Condition.from_dict(data["condition"]),  # type: ignore[arg-type]
            seed=int(data["seed"]),  # type: ignore[arg-type]
            replicate=int(data["replicate"]),  # type: ignore[arg-type]
            suite=str(data["scenario_suite"]),
        )


def make_scenario(suite: str, condition: Condition, replicate: int) -> Scenario:
    """Build a `Scenario` with a deterministic id and seed."""
    scenario_id = f"{condition.slug()}-r{replicate:03d}"
    return Scenario(
        scenario_id=scenario_id,
        condition=condition,
        seed=derive_seed(suite, scenario_id),
        replicate=replicate,
        suite=suite,
    )


def dumps(obj: object) -> str:
    """Canonical JSON: sorted keys, stable separators, hashable output."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=_default)


def _default(obj: object) -> object:
    if isinstance(obj, Condition):
        return obj.as_dict()
    if hasattr(obj, "as_dict"):
        return obj.as_dict()  # type: ignore[attr-defined]
    if hasattr(obj, "__dataclass_fields__"):
        return asdict(obj)  # type: ignore[arg-type]
    if isinstance(obj, (set, frozenset)):
        return sorted(obj)
    raise TypeError(f"not JSON serialisable: {type(obj).__name__}")
