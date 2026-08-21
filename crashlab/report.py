"""The evidence report.

PLAN.md section 20 sets the standard this module has to meet: state what was
tested, with what sample sizes, what improved, what regressed, what was never
tested, and what the report does not claim.

One safeguard is deliberately loud. Any evaluation whose `data_source` is not
a real simulator run is stamped as SYNTHETIC PLACEHOLDER at the top of the
report and beside every table. Fixture data exists so the pipeline can be
built and rehearsed before Isaac Sim is ready — it must never be mistaken for
a measurement, least of all by our own team the morning after a long sprint.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .analysis import FailureAnalysis, Finding
from .compare import Comparison, SliceDelta
from .evaluate import Evaluation
from .schema import FACTORS, PHYSICAL_RANGES, SCHEMA_VERSION

#: `data_source` values that represent a genuine simulator run.
REAL_SOURCES: frozenset[str] = frozenset(
    {"isaac_sim_replicator", "real_photographs"}
)

STANDARD_LIMITATIONS: tuple[str, ...] = (
    "This report documents performance on a defined simulated scenario suite. "
    "It supports engineering review and does not replace real-world validation "
    "or a qualified safety assessment.",
    "Simulation coverage does not prove real-world performance. A synthetic-to-real "
    "domain gap exists and is not quantified by this report.",
    "No claim of safety certification is made or implied.",
    "Human safety procedures must not depend solely on this system.",
    "False positives and false negatives carry different operational consequences; "
    "a single accuracy figure conceals that asymmetry.",
    "Metrics are reported at declared IoU and confidence thresholds. Different "
    "thresholds yield different numbers.",
)


def is_synthetic(evaluation: Evaluation) -> bool:
    return evaluation.data_source not in REAL_SOURCES


def _banner(evaluation: Evaluation) -> list[str]:
    if not is_synthetic(evaluation):
        return []
    return [
        "> ## ⚠️ SYNTHETIC PLACEHOLDER — NOT A MEASUREMENT",
        f"> Predictions in this report came from `{evaluation.data_source}`, not from a",
        "> model run against simulator output. Every number below is fabricated test",
        "> data used to exercise the pipeline. **Do not quote, present, or submit these",
        "> figures as results.**",
        "",
    ]


def _rate_cell(rate) -> str:
    if rate.value is None:
        return "n/a (n=0)"
    interval = rate.interval
    ci = f" [{interval[0]:.2f}–{interval[1]:.2f}]" if interval else ""
    return f"{rate.value:.3f}{ci} (n={rate.denominator})"


def _findings_table(findings: Sequence[Finding], limit: int) -> list[str]:
    if not findings:
        return ["_No slices in this category._", ""]
    lines = [
        "| Condition slice | Dimension | Frames | Metric (95% CI) |",
        "| --- | --- | --- | --- |",
    ]
    for finding in findings[:limit]:
        lines.append(
            f"| `{finding.slice_name}` | {finding.dimension} | {finding.frames} "
            f"| {_rate_cell(finding.rate)} |"
        )
    if len(findings) > limit:
        lines.append(f"| _… {len(findings) - limit} further slices omitted_ | | | |")
    lines.append("")
    return lines


def _delta_table(deltas: Sequence[SliceDelta], limit: int) -> list[str]:
    if not deltas:
        return ["_None._", ""]
    lines = [
        "| Condition slice | Frames | Baseline | Candidate | Δ | Verdict |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for delta in deltas[:limit]:
        change = "n/a" if delta.delta is None else f"{delta.delta:+.3f}"
        lines.append(
            f"| `{delta.slice_name}` | {delta.frames} | {_rate_cell(delta.baseline)} "
            f"| {_rate_cell(delta.candidate)} | {change} | {delta.classify()} |"
        )
    if len(deltas) > limit:
        lines.append(f"| _… {len(deltas) - limit} further slices omitted_ | | | | | |")
    lines.append("")
    return lines


@dataclass(frozen=True)
class Report:
    """A rendered evidence report, in Markdown and JSON."""

    markdown: str
    payload: dict

    def write(self, directory: str | Path, stem: str = "coverage-report") -> tuple[Path, Path]:
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        md_path = directory / f"{stem}.md"
        json_path = directory / f"{stem}.json"
        md_path.write_text(self.markdown)
        json_path.write_text(json.dumps(self.payload, indent=2, sort_keys=True))
        return md_path, json_path


def build_report(
    baseline: Evaluation,
    analysis: FailureAnalysis,
    candidate: Evaluation | None = None,
    comparison: Comparison | None = None,
    *,
    generated_at: str = "unstamped",
    suite_replicates: int | None = None,
    untested_notes: Sequence[str] = (),
    extra_limitations: Sequence[str] = (),
    top_n: int = 12,
) -> Report:
    """Render the evidence report.

    `generated_at` is passed in rather than read from the clock, so the same
    inputs always produce the same document.
    """
    synthetic = is_synthetic(baseline) or (candidate is not None and is_synthetic(candidate))

    lines: list[str] = []
    lines += _banner(baseline)
    lines += [
        "# Physical AI Crash-Test Lab — Coverage and Comparison Report",
        "",
        f"- **Scenario suite:** `{baseline.suite}`",
        f"- **Test manifest:** `{baseline.manifest_name}`",
        f"- **Manifest fingerprint:** `{baseline.manifest_fingerprint}`",
        f"- **Baseline model:** `{baseline.model.ref}` (fingerprint `{baseline.model.fingerprint}`)",
    ]
    if candidate is not None:
        lines.append(
            f"- **Candidate model:** `{candidate.model.ref}` "
            f"(fingerprint `{candidate.model.fingerprint}`)"
        )
    lines += [
        f"- **Frames evaluated:** {len(baseline.results)}",
        f"- **Data source:** `{baseline.data_source}`"
        + ("  ⚠️ **synthetic placeholder**" if synthetic else ""),
        f"- **Schema version:** `{SCHEMA_VERSION}`",
        f"- **Generated:** {generated_at}",
        "",
        "## 1. Evaluation configuration",
        "",
        "Declared before evaluation. Every metric below is conditional on these values.",
        "",
        "| Setting | Value |",
        "| --- | --- |",
    ]
    for key, value in sorted(baseline.config.as_dict().items()):
        lines.append(f"| {key} | `{value}` |")
    if suite_replicates is not None:
        lines.append(f"| replicates_per_condition_cell | `{suite_replicates}` |")
    lines.append("")

    # -- what "dim" actually meant ------------------------------------------
    lines += [
        "## 2. Scenario factors and their physical meaning",
        "",
        "Condition buckets were declared before any results were inspected. Each maps",
        "to a physical quantity the simulator applies and this report quotes.",
        "",
        "| Factor | Bucket | Physical range | Unit |",
        "| --- | --- | --- | --- |",
    ]
    for factor in FACTORS:
        spec = PHYSICAL_RANGES[factor]
        for bucket, (low, high) in spec["buckets"].items():  # type: ignore[index]
            span = f"{low} – {high}" if low != high else f"{low}"
            lines.append(f"| {factor} | {bucket} | {span} | {spec['unit']} |")
    lines.append("")

    # -- headline ------------------------------------------------------------
    overall = baseline.overall()
    lines += [
        "## 3. Baseline overall performance",
        "",
        "The figure a conventional test run would report — and the figure the",
        "condition breakdown in section 4 exists to interrogate.",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| hard_hat recall | {_rate_cell(overall.detection['hard_hat'].recall)} |",
        f"| hard_hat precision | {_rate_cell(overall.detection['hard_hat'].precision)} |",
        f"| person recall | {_rate_cell(overall.detection['person'].recall)} |",
        f"| frame accuracy (compliance verdict) | {_rate_cell(overall.safety.frame_accuracy)} |",
        f"| **dangerous miss rate** | **{_rate_cell(overall.safety.dangerous_miss_rate)}** |",
        f"| false alarm rate | {_rate_cell(overall.safety.false_alarm_rate)} |",
        "",
        "*Dangerous miss* = the scene contained no hard hat and the system reported the",
        "worker as compliant. *False alarm* = a compliant worker was flagged. These are",
        "not interchangeable: the first leaves someone unprotected, the second is a",
        "nuisance that erodes trust in the system.",
        "",
    ]

    # -- the failure map -----------------------------------------------------
    lines += [
        "## 4. Weakest condition slices",
        "",
        f"Ranked on `{analysis.metric_name}`, worst first, by the lower bound of the 95%",
        f"confidence interval. Slices with fewer than {analysis.min_samples} samples are",
        "excluded from the ranking and listed separately in section 5.",
        "",
    ]
    lines += _findings_table(analysis.findings, top_n)

    weakest = analysis.weakest
    if weakest is not None:
        lines += [
            f"**Weakest adequately-powered slice:** `{weakest.slice_name}` at "
            f"{_rate_cell(weakest.rate)}.",
            "",
        ]
        interactions = analysis.interactions()
        if interactions:
            lines += [
                f"**Worst factor interaction:** `{interactions[0].slice_name}` at "
                f"{_rate_cell(interactions[0].rate)} — a combination effect that the "
                "single-factor margins average away.",
                "",
            ]

    # -- coverage gaps -------------------------------------------------------
    lines += [
        "## 5. Coverage gaps and underpowered slices",
        "",
        "Reported so that thin coverage stays visible rather than being silently",
        "omitted. These are **not** findings — the sample size cannot support a",
        "conclusion in either direction.",
        "",
    ]
    lines += _findings_table(analysis.underpowered, top_n)
    if untested_notes:
        lines += ["**Explicitly not tested in this suite:**", ""]
        lines += [f"- {note}" for note in untested_notes]
        lines.append("")

    # -- comparison ----------------------------------------------------------
    if comparison is not None:
        lines += [
            "## 6. Baseline versus candidate",
            "",
            f"Both models evaluated on manifest `{comparison.manifest_name}`, fingerprint",
            f"`{comparison.manifest_fingerprint}` — byte-identical for both runs. Neither",
            "model was trained on these frames.",
            "",
            "| | Baseline | Candidate | Δ |",
            "| --- | --- | --- | --- |",
            f"| overall `{comparison.metric_name}` | {_rate_cell(comparison.overall.baseline)} "
            f"| {_rate_cell(comparison.overall.candidate)} | "
            f"{'n/a' if comparison.overall.delta is None else format(comparison.overall.delta, '+.3f')} |",
            "",
            f"A change is called material at |Δ| ≥ {comparison.threshold} and",
            "significant at 95% by a two-proportion z-test on the difference. Slices",
            f"with fewer than {comparison.slices[0].min_samples if comparison.slices else 20} "
            "samples on either side receive no verdict at all — the",
            "same bar section 4 applies to findings. Everything else is reported as",
            "inconclusive rather than as a win.",
            "",
            "### 6.1 Improved",
            "",
        ]
        lines += _delta_table(comparison.improved(), top_n)
        lines += ["### 6.2 Regressed", ""]
        lines += _delta_table(comparison.regressed(), top_n)
        lines += [
            "### 6.3 Inconclusive",
            "",
            "Changed by more than the material threshold, but not significantly for the",
            "sample size available. Not a win and not a loss.",
            "",
        ]
        lines += _delta_table(comparison.inconclusive(), top_n)
        lines += [
            "### 6.4 No verdict — insufficient samples",
            "",
            "Listed for completeness so thin coverage stays visible. These slices are",
            "**not** claims in either direction.",
            "",
        ]
        lines += _delta_table(comparison.underpowered(), top_n)
    else:
        lines += [
            "## 6. Baseline versus candidate",
            "",
            "_No candidate model was evaluated. This report documents failure discovery",
            "only and makes no improvement claim._",
            "",
        ]

    # -- limitations ---------------------------------------------------------
    lines += ["## 7. Limitations and what this report does not claim", ""]
    for limitation in list(STANDARD_LIMITATIONS) + list(extra_limitations):
        lines.append(f"- {limitation}")
    if synthetic:
        lines.append(
            "- **The predictions in this report are synthetic placeholder data, not "
            "model output. No performance claim of any kind is supported.**"
        )
    lines.append("")

    lines += [
        "## 8. Reproduction",
        "",
        "Every frame is regenerable from its scenario id: seeds are derived by hash from",
        "`(suite name, scenario id)` rather than drawn at random, so the suite can be",
        "rebuilt on any machine at any time.",
        "",
        "| Artifact | Identity |",
        "| --- | --- |",
        f"| scenario suite | `{baseline.suite}` |",
        f"| test manifest | `{baseline.manifest_name}` |",
        f"| manifest fingerprint | `{baseline.manifest_fingerprint}` |",
        f"| schema version | `{SCHEMA_VERSION}` |",
        f"| baseline model fingerprint | `{baseline.model.fingerprint}` |",
    ]
    if candidate is not None:
        lines.append(f"| candidate model fingerprint | `{candidate.model.fingerprint}` |")
    lines.append("")

    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "synthetic_placeholder": synthetic,
        "data_source": baseline.data_source,
        "baseline": baseline.as_dict(),
        "candidate": None if candidate is None else candidate.as_dict(),
        "analysis": analysis.as_dict(),
        "comparison": None if comparison is None else comparison.as_dict(),
        "limitations": list(STANDARD_LIMITATIONS) + list(extra_limitations),
        "untested": list(untested_notes),
    }

    return Report(markdown="\n".join(lines), payload=payload)
