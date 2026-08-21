"""Command line entry point.

    python3 -m crashlab demo          run the full loop on fixture data
    python3 -m crashlab build-suite   write the suite and locked split
    python3 -m crashlab factors       print the declared buckets

`demo` is also the stage fallback: it exercises every stage of the loop with no
GPU, no simulator, and no network, so there is always something to show.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import analysis as analysis_mod
from . import fixtures
from .compare import compare
from .evaluate import EvalConfig, evaluate
from .report import build_report
from .schema import FACTORS, PHYSICAL_RANGES
from .suite import (
    build_suite,
    remediation_manifest,
    stratified_split,
)

DEFAULT_SUITE = "warehouse_ppe_v1"


def _rule(title: str) -> None:
    print()
    print("=" * 78)
    print(f" {title}")
    print("=" * 78)


def cmd_factors(args: argparse.Namespace) -> int:
    _rule("DECLARED SCENARIO FACTORS")
    print("Buckets are fixed before any results are inspected, and each maps to a")
    print("physical quantity the simulator applies.\n")
    for factor, buckets in FACTORS.items():
        spec = PHYSICAL_RANGES[factor]
        print(f"{factor}  ({spec['unit']})")
        for bucket in buckets:
            low, high = spec["buckets"][bucket]  # type: ignore[index]
            span = f"{low} – {high}" if low != high else f"{low}"
            print(f"    {bucket:<14} {span}")
        print()
    return 0


def cmd_build_suite(args: argparse.Namespace) -> int:
    full = build_suite(args.suite, replicates=args.replicates)
    train, test = stratified_split(
        full, test_per_cell=args.test_per_cell, min_test_per_cell=args.min_test_per_cell
    )

    _rule("SCENARIO SUITE")
    print(f"suite               {args.suite}")
    print(f"condition cells     {len(full.by_condition())}")
    print(f"replicates per cell {args.replicates}")
    print(f"total frames        {len(full)}")
    print(f"train frames        {len(train)}")
    print(f"test frames         {len(test)}  ({args.test_per_cell} per cell)")
    print(f"test fingerprint    {test.fingerprint}")

    out = Path(args.out)
    for manifest in (full, train, test):
        path = manifest.write(out / f"{manifest.name}.json")
        print(f"wrote               {path}")
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    suite_name = args.suite
    out = Path(args.out)
    config = EvalConfig(min_samples_for_finding=args.min_samples)

    # -- 1. define the test ------------------------------------------------
    full = build_suite(suite_name, replicates=args.replicates)
    train, test = stratified_split(full, test_per_cell=args.test_per_cell)

    _rule("STEP 1  DEFINE THE TEST")
    print(f"condition cells      {len(full.by_condition())}")
    print(f"frames total         {len(full)}   train {len(train)}   test {len(test)}")
    print(f"test fingerprint     {test.fingerprint}")
    print("The test manifest is now locked. Nothing below may modify it.")

    # -- 2. ground truth + baseline predictions ---------------------------
    truth = fixtures.truth_set(test.scenarios)
    baseline_preds = fixtures.prediction_set(
        test.scenarios, truth, fixtures.BASELINE_PROFILE
    )

    baseline_eval = evaluate(
        test,
        truth,
        baseline_preds,
        model=fixtures.model_ref(fixtures.BASELINE_PROFILE),
        config=config,
        data_source=fixtures.DATA_SOURCE,
    )

    _rule("STEP 2  THE HEADLINE NUMBER (and why it misleads)")
    overall = baseline_eval.overall()
    print(f"  {overall.detection['hard_hat'].recall.format()}")
    print(f"  {overall.detection['hard_hat'].precision.format()}")
    print(f"  {overall.safety.frame_accuracy.format()}")
    print(f"  {overall.safety.dangerous_miss_rate.format()}")

    easy = baseline_eval.by_factor_pair("lighting", "helmet_state").get("bright+visible")
    if easy is not None:
        print()
        print("  Restricted to the conditions an acceptance test usually covers:")
        print(f"    bright + fully visible helmet -> {easy.primary('hard_hat_recall').format()}")
        print("  This is the number that gets a model signed off.")

    # -- 3. break it apart by condition -----------------------------------
    failure = analysis_mod.analyse(baseline_eval, metric=args.metric)

    _rule("STEP 3  THE SAME FRAMES, SLICED BY CONDITION")
    print(f"ranked on {failure.metric_name}, worst first "
          f"(lower 95% CI bound; min {failure.min_samples} samples)\n")
    for finding in failure.findings[: args.top]:
        print("  " + finding.describe())

    interactions = failure.interactions()
    if interactions:
        print()
        print("  Worst factor interaction (invisible to single-factor testing):")
        print("  " + interactions[0].describe())

    if failure.underpowered:
        print()
        print(f"  {len(failure.underpowered)} slices withheld as underpowered "
              f"(<{failure.min_samples} samples) — reported as coverage gaps, not findings.")

    # -- 4. targeted remediation request ----------------------------------
    target = analysis_mod.target_conditions(failure, baseline_eval, top_n=1)
    remediation = remediation_manifest(
        suite_name,
        target.conditions,
        frames_per_condition=args.remediation_frames,
        test_manifest=test,
    )

    _rule("STEP 4  TARGETED DATA REQUEST")
    print(f"derived from         {target.source_finding.slice_name}")
    print(f"                     {target.source_finding.rate.format()}")
    print(f"constraints          {dict(target.source_finding.constraints)}")
    print(f"conditions matched   {len(target.conditions)} "
          f"({len(target.conditions) - target.neighbour_count} direct, "
          f"{target.neighbour_count} adjacent)")
    for condition in target.conditions[: args.top]:
        print(f"    {condition.label()}")
    if len(target.conditions) > args.top:
        print(f"    ... and {len(target.conditions) - args.top} more")
    print(f"frames requested     {len(remediation)}")
    print("overlap with test    none (verified disjoint, else remediation would raise)")
    print()
    print("  Adjacent buckets are included deliberately: remediating the whole")
    print("  interaction generalises better than drilling one exact configuration.")

    # -- 5. candidate on the unchanged suite ------------------------------
    candidate_preds = fixtures.prediction_set(
        test.scenarios, truth, fixtures.CANDIDATE_PROFILE
    )
    candidate_eval = evaluate(
        test,
        truth,
        candidate_preds,
        model=fixtures.model_ref(fixtures.CANDIDATE_PROFILE),
        config=config,
        data_source=fixtures.DATA_SOURCE,
    )

    comparison = compare(baseline_eval, candidate_eval, metric=args.metric)

    _rule("STEP 5  BASELINE vs CANDIDATE, SAME LOCKED SUITE")
    print(f"manifest fingerprint {comparison.manifest_fingerprint}  (identical for both)")
    print(f"overall              {comparison.overall.baseline.format()}")
    print(f"                  -> {comparison.overall.candidate.format()}")
    delta = comparison.overall.delta
    print(f"delta                {'n/a' if delta is None else format(delta, '+.3f')}")

    print(f"\nimproved slices      {len(comparison.improved())}")
    for item in comparison.improved()[: args.top]:
        print(f"    {item.slice_name:<44} {item.baseline.value:.3f} -> "
              f"{item.candidate.value:.3f}  ({item.delta:+.3f}, n={item.frames})")

    print(f"\nregressed slices     {len(comparison.regressed())}")
    if not comparison.regressed():
        print("    none")
    for item in comparison.regressed()[: args.top]:
        print(f"    {item.slice_name:<44} {item.baseline.value:.3f} -> "
              f"{item.candidate.value:.3f}  ({item.delta:+.3f}, n={item.frames})")

    print(f"\ninconclusive slices  {len(comparison.inconclusive())}  "
          f"(moved, but not significantly for the sample size)")
    print(f"unchanged slices     {len(comparison.unchanged())}  "
          f"(|delta| < {comparison.threshold})")
    print(f"no verdict           {len(comparison.underpowered())}  "
          f"(fewer than {args.min_samples} samples — reported, never claimed)")

    # -- 6. evidence report -----------------------------------------------
    report = build_report(
        baseline_eval,
        failure,
        candidate=candidate_eval,
        comparison=comparison,
        generated_at=args.stamp,
        suite_replicates=args.replicates,
        untested_notes=[
            "Weather, wet or reflective floor surfaces.",
            "Sensor modalities other than RGB (no depth, thermal or LiDAR).",
            "Multiple simultaneous workers and inter-person occlusion.",
            "Motion blur and rolling-shutter effects.",
            "Hard-hat colours and types beyond the single modelled asset.",
            "Any real-world imagery whatsoever.",
        ],
    )
    md_path, json_path = report.write(out, stem="coverage-report")

    _rule("STEP 6  EVIDENCE REPORT")
    print(f"markdown             {md_path}")
    print(f"json                 {json_path}")
    print(f"synthetic flag       {report.payload['synthetic_placeholder']}")
    print()
    print("  Predictions came from fixture profiles, not a real model, so the report")
    print("  carries a refusal banner. Swap fixtures.prediction_set() for real detector")
    print("  output and set data_source='isaac_sim_replicator' to make it quotable.")
    print()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crashlab",
        description="Physical AI Crash-Test Lab — scenario-driven perception validation.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_factors = sub.add_parser("factors", help="print the declared condition buckets")
    p_factors.set_defaults(func=cmd_factors)

    p_build = sub.add_parser("build-suite", help="build and write the suite + locked split")
    p_build.add_argument("--suite", default=DEFAULT_SUITE)
    p_build.add_argument("--replicates", type=int, default=20)
    p_build.add_argument("--test-per-cell", type=int, default=10)
    p_build.add_argument("--min-test-per-cell", type=int, default=5)
    p_build.add_argument("--out", default="artifacts")
    p_build.set_defaults(func=cmd_build_suite)

    p_demo = sub.add_parser("demo", help="run the full loop on fixture data")
    p_demo.add_argument("--suite", default=DEFAULT_SUITE)
    p_demo.add_argument("--replicates", type=int, default=20)
    p_demo.add_argument("--test-per-cell", type=int, default=10)
    p_demo.add_argument("--metric", default="hard_hat_recall")
    p_demo.add_argument("--min-samples", type=int, default=20)
    p_demo.add_argument("--remediation-frames", type=int, default=250)
    p_demo.add_argument("--top", type=int, default=8)
    p_demo.add_argument("--out", default="artifacts")
    p_demo.add_argument(
        "--stamp",
        default="fixture-run",
        help="value recorded as generated_at; passed in so output stays deterministic",
    )
    p_demo.set_defaults(func=cmd_demo)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
