"""Synthetic ground truth and synthetic predictions.

Purpose, stated plainly: to build and rehearse the entire diagnosis-and-
comparison loop before Isaac Sim produces a single frame, and to give the demo
a replayable fallback if the simulator dies on stage (PLAN.md section 21).

Everything here is fabricated. `data_source` is stamped `fixture_synthetic`
throughout, and `report.py` prints a refusal banner on any report built from
it. These numbers exist to prove the plumbing works — never to be quoted.

The detector profiles below encode a *deliberately* seeded weakness: the
baseline is poor in dim light, poor under partial occlusion, and much worse
when both occur together. That is what a model trained only on easy,
well-lit footage actually looks like — and the analyser has to rediscover it
from the frames alone, with no knowledge of these parameters.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Mapping, Sequence

from .boxes import Box
from .schema import Condition, Scenario

IMAGE_WIDTH = 1280
IMAGE_HEIGHT = 720

DATA_SOURCE = "fixture_synthetic"

#: Apparent person height in pixels for each distance bucket — the projection
#: of a ~1.75 m worker at that range through the modelled camera.
PERSON_HEIGHT_PX: dict[str, float] = {"near": 520.0, "mid": 300.0, "far": 150.0}


# --------------------------------------------------------------------------
# Ground truth
# --------------------------------------------------------------------------


def truth_boxes(scenario: Scenario) -> list[Box]:
    """Ground-truth annotation for one scenario.

    Stands in for what Replicator's bounding-box annotator will emit. Geometry
    is driven by the scenario's physical buckets, so a `far` frame really does
    contain a smaller worker than a `near` one.
    """
    condition = scenario.condition
    rng = random.Random(scenario.seed)

    height = PERSON_HEIGHT_PX[condition.distance]
    width = height * 0.38

    # High oblique cameras foreshorten the standing figure.
    if condition.camera_angle == "high_oblique":
        height *= 0.82

    cx = rng.uniform(width, IMAGE_WIDTH - width)
    top = rng.uniform(10.0, max(11.0, IMAGE_HEIGHT - height - 10.0))

    person = Box(
        label="person",
        x1=cx - width / 2,
        y1=top,
        x2=cx + width / 2,
        y2=top + height,
    )
    boxes = [person]

    if condition.helmet_present:
        hat_width = width * 0.75
        hat_height = max(6.0, height * 0.10)
        boxes.append(
            Box(
                label="hard_hat",
                x1=cx - hat_width / 2,
                y1=top,
                x2=cx + hat_width / 2,
                y2=top + hat_height,
            )
        )
    return boxes


def truth_set(scenarios: Sequence[Scenario]) -> dict[str, list[Box]]:
    return {s.scenario_id: truth_boxes(s) for s in scenarios}


# --------------------------------------------------------------------------
# Detector profiles
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class DetectorProfile:
    """A fake detector, described by how its accuracy degrades.

    Multiplicative factors per bucket, plus an explicit interaction term for
    the dim-and-occluded combination. The interaction is the whole point: a
    model can be tolerable in dim light and tolerable under occlusion while
    collapsing when both apply, and single-factor testing never sees it.
    """

    name: str
    version: str
    base_hat: float
    lighting: Mapping[str, float]
    helmet_state: Mapping[str, float]
    distance: Mapping[str, float]
    camera_angle: Mapping[str, float]
    dim_occluded_interaction: float
    hat_fp_when_absent: Mapping[str, float]
    base_person: float = 0.995
    notes: str = ""

    def hat_recall_probability(self, condition: Condition) -> float:
        """Probability of correctly detecting a hard hat that is present."""
        if not condition.helmet_present:
            return 0.0
        p = self.base_hat
        p *= self.lighting.get(condition.lighting, 1.0)
        p *= self.helmet_state.get(condition.helmet_state, 1.0)
        p *= self.distance.get(condition.distance, 1.0)
        p *= self.camera_angle.get(condition.camera_angle, 1.0)
        if condition.lighting == "dim" and condition.helmet_state == "partial":
            p *= self.dim_occluded_interaction
        return max(0.0, min(1.0, p))

    def person_probability(self, condition: Condition) -> float:
        p = self.base_person
        p *= min(1.0, self.lighting.get(condition.lighting, 1.0) + 0.15)
        p *= min(1.0, self.distance.get(condition.distance, 1.0) + 0.08)
        return max(0.0, min(1.0, p))

    def hat_false_positive_probability(self, condition: Condition) -> float:
        """Probability of hallucinating a hard hat on a bare head.

        This is the mechanism behind a *dangerous miss*: the system reports a
        bare-headed worker as compliant, and nobody is alerted.
        """
        if condition.helmet_present:
            return 0.0
        return self.hat_fp_when_absent.get(condition.lighting, 0.05)


#: A model trained on bright, unoccluded footage — the common real-world case.
#: Acceptable on the frames its team happened to collect; poor everywhere else.
BASELINE_PROFILE = DetectorProfile(
    name="helmet-detector-baseline",
    version="v0.1.0-fixture",
    base_hat=0.99,
    lighting={"bright": 1.00, "normal": 0.99, "dim": 0.72},
    helmet_state={"visible": 1.00, "partial": 0.78},
    distance={"near": 1.00, "mid": 1.00, "far": 0.97},
    camera_angle={"eye_level": 1.00, "high_oblique": 0.99},
    dim_occluded_interaction=0.55,
    hat_fp_when_absent={"bright": 0.06, "normal": 0.11, "dim": 0.28},
    notes=(
        "FIXTURE. Simulates a detector trained only on bright, unoccluded frames. "
        "Weakness in dim+partial is deliberately seeded so the analyser can be "
        "verified against a known answer."
    ),
)

#: The same model after targeted remediation on the dim+occluded cluster.
#: Note the deliberate regression at long range — remediation is a trade, and a
#: report that only ever shows wins is not an instrument.
CANDIDATE_PROFILE = DetectorProfile(
    name="helmet-detector-candidate",
    version="v0.2.0-fixture",
    base_hat=0.99,
    lighting={"bright": 1.00, "normal": 0.99, "dim": 0.95},
    helmet_state={"visible": 1.00, "partial": 0.94},
    distance={"near": 1.00, "mid": 1.00, "far": 0.60},
    camera_angle={"eye_level": 1.00, "high_oblique": 0.99},
    dim_occluded_interaction=0.90,
    hat_fp_when_absent={"bright": 0.04, "normal": 0.06, "dim": 0.10},
    notes=(
        "FIXTURE. Simulates the baseline after fine-tuning on targeted dim+occluded "
        "frames. Long-range performance is deliberately and substantially degraded, "
        "so the comparison stage has a genuine regression to surface — the case a "
        "demo-only tool would quietly omit."
    ),
)


# --------------------------------------------------------------------------
# Predictions
# --------------------------------------------------------------------------


def _jitter(box: Box, rng: random.Random, score: float) -> Box:
    """Perturb a truth box into a plausible detection.

    Kept small enough to stay above a 0.5 IoU threshold: a localisation study
    is not what this fixture is for, and drifting boxes would contaminate the
    recall signal the analyser is being tested on.
    """
    width = box.x2 - box.x1
    height = box.y2 - box.y1
    dx = rng.uniform(-0.04, 0.04) * width
    dy = rng.uniform(-0.04, 0.04) * height
    sx = 1.0 + rng.uniform(-0.05, 0.05)
    sy = 1.0 + rng.uniform(-0.05, 0.05)
    cx = (box.x1 + box.x2) / 2 + dx
    cy = (box.y1 + box.y2) / 2 + dy
    new_w = max(4.0, width * sx)
    new_h = max(4.0, height * sy)
    return Box(
        label=box.label,
        x1=cx - new_w / 2,
        y1=cy - new_h / 2,
        x2=cx + new_w / 2,
        y2=cy + new_h / 2,
        score=score,
    )


def predict(
    scenario: Scenario,
    truth: Sequence[Box],
    profile: DetectorProfile,
    score_floor: float = 0.36,
) -> list[Box]:
    """Fabricate one detector's output for one frame."""
    # Seed off both the scenario and the profile, so baseline and candidate
    # make independent errors on the same frame while each stays reproducible.
    rng = random.Random(f"{profile.name}/{profile.version}/{scenario.seed}")
    condition = scenario.condition
    predictions: list[Box] = []

    for box in truth:
        if box.label == "person":
            if rng.random() < profile.person_probability(condition):
                score = rng.uniform(0.70, 0.99)
                predictions.append(_jitter(box, rng, score))
        elif box.label == "hard_hat":
            if rng.random() < profile.hat_recall_probability(condition):
                # Confidence sags in exactly the conditions recall does — the
                # texture a real detector shows.
                ceiling = 0.55 + 0.44 * profile.hat_recall_probability(condition)
                score = rng.uniform(score_floor + 0.02, max(score_floor + 0.05, ceiling))
                predictions.append(_jitter(box, rng, score))

    # Hallucinated hat on a bare head → the dangerous-miss path.
    if not condition.helmet_present:
        if rng.random() < profile.hat_false_positive_probability(condition):
            person = next((b for b in truth if b.label == "person"), None)
            if person is not None:
                width = (person.x2 - person.x1) * 0.7
                height = max(6.0, (person.y2 - person.y1) * 0.10)
                cx = (person.x1 + person.x2) / 2
                predictions.append(
                    Box(
                        label="hard_hat",
                        x1=cx - width / 2,
                        y1=person.y1,
                        x2=cx + width / 2,
                        y2=person.y1 + height,
                        score=rng.uniform(score_floor + 0.01, 0.62),
                    )
                )
    return predictions


def prediction_set(
    scenarios: Sequence[Scenario],
    truth: Mapping[str, Sequence[Box]],
    profile: DetectorProfile,
) -> dict[str, list[Box]]:
    return {
        s.scenario_id: predict(s, truth[s.scenario_id], profile) for s in scenarios
    }


def model_ref(profile: DetectorProfile):
    """A `ModelRef` for a fixture profile, fingerprinted by its parameters."""
    import hashlib

    from .evaluate import ModelRef

    payload = "|".join(
        [
            profile.name,
            profile.version,
            str(profile.base_hat),
            str(sorted(profile.lighting.items())),
            str(sorted(profile.helmet_state.items())),
            str(sorted(profile.distance.items())),
            str(sorted(profile.camera_angle.items())),
            str(profile.dim_occluded_interaction),
        ]
    )
    digest = hashlib.blake2b(payload.encode(), digest_size=16).hexdigest()
    return ModelRef(
        name=profile.name,
        version=profile.version,
        fingerprint=f"fixture:{digest}",
        notes=profile.notes,
    )
