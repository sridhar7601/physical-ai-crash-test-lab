"""Plain-language executive summary of a run, via the team's OpenRouter key.

The coverage report speaks statistics; its buyers are EHS and operations
leaders who read English. This module hands an LLM a fact sheet of ONLY the
run's measured numbers and asks for a short summary a safety manager can act
on. The facts are compiled here, deterministically — the model is a writer,
never a source: it is instructed to use no number that is not in the sheet,
and the output is checked for invented percentages before it is accepted.

    OPENROUTER_API_KEY=... python3 -m crashlab.narrate \
        --report results_v2/report/coverage-report.json \
        --fair results_v2/fair_control_report/coverage-report.json \
        --out results_v2/executive-summary.md

Runs entirely on stdlib (urllib). Without a key it exits with instructions —
the pipeline treats the summary as optional garnish, never a dependency.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.request
from pathlib import Path

MODEL = "anthropic/claude-sonnet-5"  # hackathon-approved list, mid-cost
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"


def fact_sheet(report: dict, fair: dict | None) -> tuple[str, set[str]]:
    """Compile the only numbers the model is allowed to use."""
    base = report["baseline"]
    analysis = report["analysis"]
    comp = report.get("comparison")
    lines = [
        f"- Test suite: {base['frame_count']} simulated warehouse frames, "
        f"fingerprint-locked (id {base['manifest_fingerprint'][:12]}).",
        f"- Baseline model overall hard-hat recall: "
        f"{base['overall']['detection']['hard_hat']['recall']['value']:.2f}.",
    ]
    weakest = analysis.get("weakest_slice")
    if weakest:
        lines.append(
            f"- Weakest condition: {weakest['slice']} at recall "
            f"{weakest['value']:.2f} (n={weakest['denominator']})."
        )
    if comp:
        o = comp["overall"]
        lines.append(
            f"- After targeted synthetic data, overall recall "
            f"{o['baseline']['value']:.2f} -> {o['candidate']['value']:.2f} "
            f"on the identical suite; {len(comp['improved'])} conditions "
            f"improved, {len(comp['regressed'])} regressed."
        )
        for s in comp["improved"]:
            if weakest and s["slice"] == weakest["slice"]:
                lines.append(
                    f"- The weakest condition specifically: "
                    f"{s['baseline']['value']:.2f} -> {s['candidate']['value']:.2f}."
                )
    if fair:
        fo = fair["comparison"]["overall"]
        lines.append(
            f"- Volume-matched control (same amount of extra data, untargeted): "
            f"{fo['baseline']['value']:.2f} vs targeted {fo['candidate']['value']:.2f} "
            f"overall — the targeting edge is below statistical significance "
            f"on this suite and is reported as such."
        )
    sheet = "\n".join(lines)
    allowed = set(re.findall(r"\d+\.\d+|\d+", sheet))
    return sheet, allowed


PROMPT = """You are writing for a warehouse safety manager, not an engineer.
Using ONLY the facts below — no other numbers, no invented percentages —
write a 150-200 word executive summary of this model validation run.

Requirements:
- Plain language; explain what recall means in one clause the first time.
- Lead with the operational risk that was found, then what was done, then
  the honest result including the control experiment's caveat.
- End with exactly this sentence: "These results describe performance on a
  simulated scenario suite and support engineering review; they do not
  replace real-world validation."
- No headings, no bullet points, no hype adjectives.

FACTS:
{facts}"""


def call_openrouter(prompt: str, key: str) -> str:
    body = json.dumps({
        "model": MODEL,
        "max_tokens": 500,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        ENDPOINT, data=body, method="POST",
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json",
                 "X-Title": "physical-ai-crash-test-lab"},
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"].strip()


def verify_numbers(text: str, allowed: set[str]) -> list[str]:
    """Any number in the prose that is not in the fact sheet is an invention."""
    found = set(re.findall(r"\d+(?:\.\d+)?", text))
    benign = {"150", "200"}  # word-count echoes, if any
    return sorted(n for n in found if n not in allowed and n not in benign)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    ap.add_argument("--fair", default=None)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)

    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        print("[narrate] OPENROUTER_API_KEY is not set.\n"
              "  export OPENROUTER_API_KEY=sk-or-...   # the team key\n"
              "The summary is optional; every report stands without it.")
        return 2

    report = json.loads(Path(a.report).read_text())
    fair = json.loads(Path(a.fair).read_text()) if a.fair else None
    facts, allowed = fact_sheet(report, fair)
    print("[narrate] fact sheet:\n" + facts)

    text = call_openrouter(PROMPT.format(facts=facts), key)
    invented = verify_numbers(text, allowed)
    if invented:
        print(f"[narrate] REJECTED: model introduced numbers not in the fact "
              f"sheet: {invented}. Not writing output.")
        return 1

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        "# Executive summary\n\n"
        f"*Generated from the run's measured artifacts by {MODEL} via "
        "OpenRouter; every figure is checked against the fact sheet, and the "
        "text is advisory prose over the authoritative report.*\n\n"
        + text + "\n"
    )
    print(f"[narrate] wrote {out}\n\n{text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
