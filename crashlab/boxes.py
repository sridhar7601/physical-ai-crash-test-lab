"""Bounding boxes and IoU. Pure stdlib, pixel coordinates.

Convention: (x1, y1) top-left inclusive, (x2, y2) bottom-right exclusive,
matching the COCO-style corner format Replicator emits.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


class BoxError(ValueError):
    """A geometrically impossible box."""


@dataclass(frozen=True)
class Box:
    """One annotation or detection."""

    label: str
    x1: float
    y1: float
    x2: float
    y2: float
    score: float | None = None  # None for ground truth

    def __post_init__(self) -> None:
        if self.x2 <= self.x1 or self.y2 <= self.y1:
            raise BoxError(
                f"degenerate box for {self.label!r}: "
                f"({self.x1}, {self.y1}) -> ({self.x2}, {self.y2})"
            )
        if self.score is not None and not 0.0 <= self.score <= 1.0:
            raise BoxError(f"score {self.score} outside [0, 1]")

    @property
    def area(self) -> float:
        return (self.x2 - self.x1) * (self.y2 - self.y1)

    def as_dict(self) -> dict[str, object]:
        out: dict[str, object] = {
            "label": self.label,
            "bbox": [self.x1, self.y1, self.x2, self.y2],
        }
        if self.score is not None:
            out["score"] = self.score
        return out

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "Box":
        bbox = data["bbox"]
        x1, y1, x2, y2 = (float(v) for v in bbox)  # type: ignore[union-attr]
        score = data.get("score")
        return cls(
            label=str(data["label"]),
            x1=x1,
            y1=y1,
            x2=x2,
            y2=y2,
            score=None if score is None else float(score),  # type: ignore[arg-type]
        )


def iou(a: Box, b: Box) -> float:
    """Intersection over union. 0.0 when the boxes do not overlap."""
    ix1, iy1 = max(a.x1, b.x1), max(a.y1, b.y1)
    ix2, iy2 = min(a.x2, b.x2), min(a.y2, b.y2)
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    intersection = (ix2 - ix1) * (iy2 - iy1)
    union = a.area + b.area - intersection
    return intersection / union if union > 0 else 0.0
