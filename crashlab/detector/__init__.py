"""Detector training and inference.

Deliberately isolated from the rest of `crashlab`: only this package imports
torch/ultralytics, and only `generator` imports omni. The analysis half stays
pure stdlib, so it runs on a laptop, in CI, and inside Isaac Sim's Python
without any of these dependencies present.

Predictions are handed on as plain JSON, which is why `evaluate.py` never needs
to know a model existed.
"""

from __future__ import annotations

__all__ = ["yolo_dataset", "train", "predict"]
