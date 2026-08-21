"""Drive the loop on real rendered data.

Pure stdlib: reads rendered labels and prediction JSON from disk, and never
imports torch or omni. That is what lets the same commands run on the GPU box
or on a laptop from a copied artifacts directory.

    python3 -m crashlab.pipeline diagnose \
        --dataset datasets/test --predictions preds/baseline \
        --model-name helmet-baseline --model-version v1 --out results/baseline

    python3 -m crashlab.pipeline remediate \
        --analysis results/baseline --suite warehouse_ppe_v1 \
        --test-manifest artifacts/warehouse_ppe_v1-test.json \
        --frames-per-condition 50 --out artifacts/remediation.json

    python3 -m crashlab.pipeline compare \
        --baseline results/baseline --candidate results/candidate \
        --out results/report
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .analysis import analyse, target_conditions
from .compare import compare
from .detector_io import load_predictions
from .evaluate import EvalConfig, ModelRef, evaluate
from .ingest import load_dataset
from .report import build_report
from .schema import Condition
from .suite import Manifest, remediation_manifest


def _eval_config(args) -> EvalConfig:
    return EvalConfig(
        iou_threshold=args.iou,
        score_threshold=args.score,
        min_samples_for_finding=args.min_samples,
    )


def cmd_diagnose(args) -> int:
    manifest = Manifest.read(args.manifest) if args.manifest else None
    dataset = load_dataset(args.dataset, manifest, require_complete=not args.allow_partial)

    print(f"[pipeline] dataset      {args.dataset}")
    print(f"[pipeline] frames       {len(dataset)}")
    print(f"[pipeline] data source  {dataset.data_source}")
    if dataset.consistency_failures:
        print(f"[pipeline] WARNING     {len(dataset.consistency_failures)} frames failed the "
              f"generator consistency check and are still included; "
              f"see generation_manifest.json")

    predictions = load_predictions(args.predictions)
    print(f"[pipeline] predictions  {len(predictions)} frames")

    model = ModelRef(
        name=args.model_name,
        version=args.model_version,
        fingerprint=args.model_fingerprint,
        notes=args.model_notes,
    )

    if manifest is None:
        raise SystemExit("--manifest is required: evaluation is defined against a manifest")

    evaluation = evaluate(
        manifest, dataset.truth, predictions, model=model,
        config=_eval_config(args), data_source=dataset.data_source,
        require_complete=not args.allow_partial,
    )

    failure = analyse(evaluation, metric=args.metric)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    evaluation.write(out / "evaluation.json")
    (out / "analysis.json").write_text(json.dumps(failure.as_dict(), indent=2))
    (out / "model.json").write_text(json.dumps(model.as_dict(), indent=2))

    overall = evaluation.overall()
    print()
    print("  OVERALL")
    print(f"    {overall.detection['hard_hat'].recall.format()}")
    print(f"    {overall.detection['hard_hat'].precision.format()}")
    print(f"    {overall.detection['person'].recall.format()}")
    print(f"    {overall.safety.dangerous_miss_rate.format()}")
    print(f"    {overall.safety.false_alarm_rate.format()}")
    print("    (a detector that never fires scores a perfect dangerous_miss_rate "
          "and a terrible false_alarm_rate; read them together)")
    print()
    print(f"  WEAKEST SLICES on {failure.metric_name} (worst first)")
    for finding in failure.findings[: args.top]:
        print("    " + finding.describe())
    print()
    print(f"  {len(failure.underpowered)} slices withheld as underpowered "
          f"(<{failure.min_samples} samples)")
    print(f"  wrote {out}/evaluation.json, analysis.json")
    return 0


def cmd_remediate(args) -> int:
    analysis_path = Path(args.analysis) / "analysis.json"
    data = json.loads(analysis_path.read_text())

    weakest = data.get("weakest_slice")
    if weakest is None:
        raise SystemExit("analysis has no adequately-powered finding to target")

    constraints = weakest.get("constraints") or {}
    if not constraints:
        raise SystemExit(f"weakest slice {weakest['slice']!r} pins no factors; cannot render it")

    # Expand the constraints into every matching condition, plus neighbours —
    # remediating a whole interaction generalises better than one exact cell.
    from .schema import iter_conditions
    from .suite import neighbours

    matched = [
        c for c in iter_conditions()
        if all(getattr(c, k) == v for k, v in constraints.items())
    ]
    direct = len(matched)
    for condition in list(matched):
        for neighbour in neighbours(condition):
            if neighbour not in matched:
                matched.append(neighbour)

    test_manifest = Manifest.read(args.test_manifest)
    manifest = remediation_manifest(
        args.suite, matched, args.frames_per_condition, test_manifest
    )
    out = Path(args.out)
    manifest.write(out)

    print(f"[pipeline] targeting    {weakest['slice']}")
    print(f"[pipeline] metric       {weakest['value']:.3f} (n={weakest['denominator']})")
    print(f"[pipeline] constraints  {constraints}")
    print(f"[pipeline] conditions   {len(matched)} ({direct} direct, "
          f"{len(matched) - direct} adjacent)")
    print(f"[pipeline] frames       {len(manifest)}")
    print(f"[pipeline] overlap      none (verified disjoint from the test suite)")
    print(f"[pipeline] wrote        {out}")
    return 0


def cmd_pool(args) -> int:
    """Build a fresh frame pool spanning every condition.

    Needed for an honest bulk-collection control. Real-world bulk collection
    draws from the whole condition distribution, in which the weak condition is
    rare -- so a control sampled only from the hard conditions is far too
    generous to the control and understates what targeting is worth.

    Frames use a replicate offset well past every existing manifest, so their
    scenario ids -- and therefore their seeds -- cannot collide with the locked
    test suite or an earlier remediation set.
    """
    from .schema import iter_conditions

    conditions = list(iter_conditions())
    test_manifest = Manifest.read(args.test_manifest)
    manifest = remediation_manifest(
        args.suite, conditions, args.frames_per_condition,
        test_manifest, replicate_offset=args.replicate_offset,
    )

    # remediation_manifest guards against the test suite; also check any other
    # manifests the caller names, so two pools can never silently share frames.
    for other_path in args.disjoint_from or []:
        other = Manifest.read(other_path)
        overlap = manifest.scenario_ids() & other.scenario_ids()
        if overlap:
            raise SystemExit(
                f"pool overlaps {other_path} on {len(overlap)} scenarios "
                f"(e.g. {sorted(overlap)[:3]}). Raise --replicate-offset."
            )

    manifest.write(args.out)
    print(f"[pipeline] conditions  {len(conditions)} (every cell in the matrix)")
    print(f"[pipeline] per cell    {args.frames_per_condition}")
    print(f"[pipeline] frames      {len(manifest)}")
    print(f"[pipeline] offset      {args.replicate_offset}")
    print(f"[pipeline] disjoint    test suite" +
          (f" + {len(args.disjoint_from)} other manifest(s)" if args.disjoint_from else ""))
    print(f"[pipeline] wrote       {args.out}")
    return 0


def cmd_compare(args) -> int:
    from .evaluate import Evaluation

    baseline = _load_evaluation(Path(args.baseline), args)
    candidate = _load_evaluation(Path(args.candidate), args)

    comparison = compare(baseline, candidate, metric=args.metric)
    failure = analyse(baseline, metric=args.metric)

    report = build_report(
        baseline, failure, candidate=candidate, comparison=comparison,
        generated_at=args.stamp,
        untested_notes=[
            "Weather, wet or reflective floor surfaces.",
            "Sensor modalities other than RGB.",
            "Multiple simultaneous workers and inter-person occlusion.",
            "Motion blur and rolling-shutter effects.",
            "Hard-hat colours and geometries beyond the single modelled asset.",
            "Any real-world imagery.",
        ],
        extra_limitations=[
            "Scene geometry is primitive stand-ins (cylinder worker, cube hard hat), "
            "not photorealistic assets. Absolute performance figures will not transfer "
            "to real imagery; the comparison between model versions is the meaningful "
            "result.",
            "Lighting buckets map to an UNCALIBRATED simulator intensity, not measured "
            "illuminance. Bucket ordering is meaningful; the lux values are nominal.",
            "CONFOUND: if the candidate's training set is larger than the baseline's, "
            "some of the improvement is attributable to data volume rather than to "
            "targeting. Improvement concentrated in the targeted slice is evidence for "
            "targeting; broad improvement across unrelated slices is not. A clean test "
            "holds total training volume constant and varies only which conditions the "
            "extra frames cover. Compare the train_images counts in each export "
            "manifest before drawing a conclusion.",
        ],
    )
    out = Path(args.out)
    md, js = report.write(out, stem="coverage-report")

    print(f"[pipeline] baseline   {comparison.baseline_ref}")
    print(f"[pipeline] candidate  {comparison.candidate_ref}")
    print(f"[pipeline] manifest   {comparison.manifest_fingerprint} (identical for both)")
    print()
    print(f"  overall {comparison.overall.baseline.format()}")
    print(f"       -> {comparison.overall.candidate.format()}")
    delta = comparison.overall.delta
    print(f"  delta   {'n/a' if delta is None else format(delta, '+.3f')}")
    print()
    for title, items in (("IMPROVED", comparison.improved()),
                         ("REGRESSED", comparison.regressed())):
        print(f"  {title} ({len(items)})")
        for item in items[: args.top]:
            print(f"    {item.slice_name:<46} {item.baseline.value:.3f} -> "
                  f"{item.candidate.value:.3f} ({item.delta:+.3f}, n={item.frames})")
        if not items:
            print("    none")
    print()
    print(f"  inconclusive {len(comparison.inconclusive())}   "
          f"unchanged {len(comparison.unchanged())}   "
          f"no-verdict {len(comparison.underpowered())}")
    print(f"  wrote {md}")
    return 0


def _load_evaluation(directory: Path, args):
    """Rebuild an Evaluation from a diagnose run's saved artifacts."""
    from .evaluate import Evaluation
    from .matching import ClassCounts, FrameResult, SafetyVerdict

    data = json.loads((directory / "evaluation.json").read_text())
    manifest = Manifest.read(args.manifest)

    results = []
    conditions = {s.scenario_id: s.condition for s in manifest.scenarios}
    for frame in data["frames"]:
        counts = {
            label: ClassCounts(label, c["tp"], c["fp"], c["fn"])
            for label, c in frame["counts"].items()
        }
        safety = frame["safety"]
        results.append(FrameResult(
            scenario_id=frame["scenario_id"],
            counts=counts,
            safety=SafetyVerdict(
                truth_compliant=safety["truth_compliant"],
                predicted_compliant=safety["predicted_compliant"],
            ),
        ))

    model = data["model"]
    cfg = data["config"]
    return Evaluation(
        model=ModelRef(model["name"], model["version"], model["fingerprint"], model["notes"]),
        manifest_name=data["manifest_name"],
        manifest_fingerprint=data["manifest_fingerprint"],
        suite=data["scenario_suite"],
        config=EvalConfig(
            iou_threshold=cfg["iou_threshold"],
            score_threshold=cfg["score_threshold"],
            classes=tuple(cfg["classes"]),
            min_samples_for_finding=cfg["min_samples_for_finding"],
        ),
        results=tuple(results),
        conditions=conditions,
        data_source=data["data_source"],
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="crashlab.pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p):
        p.add_argument("--iou", type=float, default=0.5)
        p.add_argument("--score", type=float, default=0.35)
        p.add_argument("--min-samples", type=int, default=20)
        p.add_argument("--metric", default="hard_hat_recall")
        p.add_argument("--top", type=int, default=10)

    d = sub.add_parser("diagnose", help="evaluate a model and rank its weak conditions")
    d.add_argument("--dataset", required=True)
    d.add_argument("--predictions", required=True)
    d.add_argument("--manifest", required=True)
    d.add_argument("--model-name", required=True)
    d.add_argument("--model-version", required=True)
    d.add_argument("--model-fingerprint", default="unfingerprinted")
    d.add_argument("--model-notes", default="")
    d.add_argument("--allow-partial", action="store_true")
    d.add_argument("--out", required=True)
    common(d)
    d.set_defaults(func=cmd_diagnose)

    r = sub.add_parser("remediate", help="turn the worst finding into a render request")
    r.add_argument("--analysis", required=True)
    r.add_argument("--suite", required=True)
    r.add_argument("--test-manifest", required=True)
    r.add_argument("--frames-per-condition", type=int, default=50)
    r.add_argument("--out", required=True)
    r.set_defaults(func=cmd_remediate)

    pl = sub.add_parser("pool", help="build a fresh all-conditions frame pool")
    pl.add_argument("--suite", required=True)
    pl.add_argument("--test-manifest", required=True)
    pl.add_argument("--frames-per-condition", type=int, default=6)
    pl.add_argument("--replicate-offset", type=int, default=2000)
    pl.add_argument("--disjoint-from", nargs="*", default=None,
                    help="other manifests this pool must not overlap")
    pl.add_argument("--out", required=True)
    pl.set_defaults(func=cmd_pool)

    c = sub.add_parser("compare", help="baseline vs candidate on the same suite")
    c.add_argument("--baseline", required=True)
    c.add_argument("--candidate", required=True)
    c.add_argument("--manifest", required=True)
    c.add_argument("--out", required=True)
    c.add_argument("--stamp", default="unstamped")
    common(c)
    c.set_defaults(func=cmd_compare)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
