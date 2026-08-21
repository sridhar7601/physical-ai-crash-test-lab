"""Physical AI Crash-Test Lab — scenario-driven validation for perception models.

The loop, in the order the modules implement it:

    schema    declare the condition buckets and their physical meaning
    suite     build the scenario matrix, lock a stratified train/test split
    fixtures  stand in for the simulator until Isaac Sim is ready
    evaluate  score predictions against ground truth, frame by frame
    metrics   precision/recall/safety verdicts, sliced by condition
    analysis  rank the weak slices; turn the worst into a data request
    compare   baseline vs candidate on a provably unchanged suite
    report    versioned evidence, including regressions and coverage gaps

Pure standard library, deliberately: the same code runs on a laptop and inside
Isaac Sim's bundled Python without an install step.
"""

from __future__ import annotations

__version__ = "0.1.0"

from .analysis import FailureAnalysis, Finding, analyse, target_conditions
from .boxes import Box, iou
from .compare import Comparison, ComparisonError, compare
from .evaluate import EvalConfig, Evaluation, EvaluationError, ModelRef, evaluate
from .matching import ClassCounts, FrameResult, SafetyVerdict, match_frame
from .metrics import Rate, Slice, wilson_interval
from .report import Report, build_report
from .schema import CLASSES, FACTORS, PHYSICAL_RANGES, Condition, Scenario
from .suite import Manifest, build_suite, remediation_manifest, stratified_split

__all__ = [
    "__version__",
    "Box",
    "iou",
    "CLASSES",
    "FACTORS",
    "PHYSICAL_RANGES",
    "Condition",
    "Scenario",
    "Manifest",
    "build_suite",
    "stratified_split",
    "remediation_manifest",
    "ClassCounts",
    "FrameResult",
    "SafetyVerdict",
    "match_frame",
    "Rate",
    "Slice",
    "wilson_interval",
    "EvalConfig",
    "Evaluation",
    "EvaluationError",
    "ModelRef",
    "evaluate",
    "FailureAnalysis",
    "Finding",
    "analyse",
    "target_conditions",
    "Comparison",
    "ComparisonError",
    "compare",
    "Report",
    "build_report",
]
