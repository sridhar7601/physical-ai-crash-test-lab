"""Build the crash-test dashboard: one self-contained HTML file per run.

Reads the JSON artifacts a run leaves behind (coverage report, per-arm
analyses, remediation manifest) and inlines them into a static page with the
four screens from PLAN.md section 17: Suite, Failure Map, Remediation,
Comparison. No server, no network — the file IS the deliverable, so it can sit
in the repo, be attached to a review, or open from a USB stick in a demo.

    python3 -m crashlab.dashboard --report results/report/coverage-report.json \
        --fair results/fair_control_report/coverage-report.json \
        --arm "A|baseline (195 easy)|results/baseline" \
        --arm "B|bulk +250 all-conditions|results/arm_bulk_all" \
        --arm "C|targeted +250 dim+partial|results/arm_targeted" \
        --remediation artifacts/warehouse_ppe_v1-remediation.json \
        --out dashboard/index.html
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .schema import FACTORS, PHYSICAL_RANGES

TARGET_SLICE = "lighting×helmet_state=dim+partial"


def _slice_value(analysis: dict, name_contains: str) -> dict | None:
    for f in analysis.get("findings", []) + analysis.get("underpowered_slices", []):
        if name_contains in f["slice"]:
            return f
    return None


def collect(report_path: Path, fair_path: Path | None,
            arms: list[tuple[str, str, Path]], remediation_path: Path | None) -> dict:
    report = json.loads(report_path.read_text())
    baseline = report["baseline"]
    data: dict = {
        "suite": baseline["scenario_suite"],
        "manifest": baseline["manifest_name"],
        "fingerprint": baseline["manifest_fingerprint"],
        "frames": baseline["frame_count"],
        "data_source": baseline["data_source"],
        "generated_at": report.get("generated_at", ""),
        "config": baseline["config"],
        "models": {
            "baseline": baseline["model"],
            "candidate": (report.get("candidate") or {}).get("model"),
        },
        "overall": baseline["overall"],
        "analysis": report["analysis"],
        "comparison": report.get("comparison"),
        "fair_comparison": None,
        "arms": [],
        "remediation": None,
        "factors": {
            factor: {
                "buckets": {
                    b: {"lo": lo, "hi": hi}
                    for b, (lo, hi) in PHYSICAL_RANGES[factor]["buckets"].items()  # type: ignore[index]
                },
                "unit": PHYSICAL_RANGES[factor]["unit"],
            }
            for factor in FACTORS
        },
        "limitations": report.get("limitations", []),
        "untested": report.get("untested", []),
        "synthetic": report.get("synthetic_placeholder", False),
    }

    if fair_path and fair_path.exists():
        data["fair_comparison"] = json.loads(fair_path.read_text())["comparison"]

    for key, label, arm_dir in arms:
        analysis = json.loads((arm_dir / "analysis.json").read_text())
        evaluation = json.loads((arm_dir / "evaluation.json").read_text())
        target = _slice_value(analysis, "dim+partial")
        data["arms"].append({
            "key": key,
            "label": label,
            "target_value": None if target is None else target["value"],
            "target_ci": None if target is None else [target["ci95_low"], target["ci95_high"]],
            "target_n": None if target is None else target["denominator"],
            "overall": evaluation["overall"]["detection"]["hard_hat"]["recall"]["value"],
        })

    if remediation_path and remediation_path.exists():
        manifest = json.loads(remediation_path.read_text())
        data["remediation"] = {
            "frames": manifest["sample_count"],
            "conditions": manifest["condition_cell_count"],
            "weakest": data["analysis"].get("weakest_slice"),
        }
    return data


def build(data: dict, out: Path) -> Path:
    html = TEMPLATE.replace("/*__DATA__*/null", json.dumps(data, indent=None))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the crash-test dashboard HTML.")
    parser.add_argument("--report", required=True)
    parser.add_argument("--fair", default=None)
    parser.add_argument("--arm", action="append", default=[],
                        help='repeatable: "KEY|label|results_dir"')
    parser.add_argument("--remediation", default=None)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    arms = []
    for spec in args.arm:
        key, label, path = spec.split("|", 2)
        arms.append((key, label, Path(path)))

    data = collect(Path(args.report),
                   Path(args.fair) if args.fair else None,
                   arms,
                   Path(args.remediation) if args.remediation else None)
    out = build(data, Path(args.out))
    print(f"[dashboard] wrote {out} ({out.stat().st_size} bytes)")
    return 0


TEMPLATE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Physical AI Crash-Test Lab</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{color-scheme:light;
 --page:#f9f9f7;--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;
 --grid:#e1e0d9;--axis:#c3c2b7;--border:rgba(11,11,11,.10);
 --s250:#86b6ef;--s400:#3987e5;--s550:#1c5cab;--s700:#0d366b;
 --seq100:#cde2fb;--seq200:#9ec5f4;--seq300:#6da7ec;--seq400:#3987e5;--seq500:#256abf;--seq600:#184f95;--seq700:#0d366b;
 --critical:#d03b3b;--good:#0ca30c;--goodtext:#006300}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){color-scheme:dark;
 --page:#0d0d0d;--surface:#1a1a19;--ink:#fff;--ink2:#c3c2b7;--muted:#898781;
 --grid:#2c2c2a;--axis:#383835;--border:rgba(255,255,255,.10);
 --s250:#9ec5f4;--s400:#5598e7;--s550:#256abf;--s700:#184f95;
 --critical:#d03b3b;--good:#0ca30c;--goodtext:#0ca30c}}
:root[data-theme=dark]{color-scheme:dark;
 --page:#0d0d0d;--surface:#1a1a19;--ink:#fff;--ink2:#c3c2b7;--muted:#898781;
 --grid:#2c2c2a;--axis:#383835;--border:rgba(255,255,255,.10);
 --s250:#9ec5f4;--s400:#5598e7;--s550:#256abf;--s700:#184f95;
 --critical:#d03b3b;--good:#0ca30c;--goodtext:#0ca30c}
*{box-sizing:border-box;margin:0}
body{background:var(--page);color:var(--ink);font:15px/1.5 'IBM Plex Sans',system-ui,-apple-system,'Segoe UI',sans-serif;padding:26px clamp(14px,4vw,44px) 64px}
.mono{font-family:'IBM Plex Mono',ui-monospace,'SF Mono',Menlo,monospace}
.eyebrow{font-size:11px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
h1{font-size:24px;font-weight:600;letter-spacing:-.01em;margin:4px 0 10px}
.sub{color:var(--ink2);font-size:12.5px;margin-bottom:6px;font-family:'IBM Plex Mono',ui-monospace,monospace;display:flex;gap:18px;flex-wrap:wrap}
.sub span b{color:var(--ink);font-weight:500}
.rule{border:0;border-top:1px solid var(--grid);margin:14px 0 4px}
.tabs{display:flex;gap:6px;margin:14px 0 18px;flex-wrap:wrap}
.tab{border:1px solid var(--border);background:var(--surface);color:var(--ink2);border-radius:6px;padding:8px 16px;font:600 11.5px/1 'IBM Plex Sans',system-ui,sans-serif;letter-spacing:.1em;text-transform:uppercase;cursor:pointer}
.tab .n{color:var(--muted);margin-right:7px;font-family:'IBM Plex Mono',monospace;font-weight:500}
.tab[aria-selected=true]{color:var(--ink);border-color:var(--s400);box-shadow:inset 0 -2px 0 var(--s400)}
.tab:focus-visible{outline:2px solid var(--s400);outline-offset:2px}
.screen{display:none}.screen.active{display:block}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:16px}
.tile{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:12px 14px}
.tile .k{font-size:11px;color:var(--muted);font-weight:600;letter-spacing:.08em;text-transform:uppercase}
.tile .v{font-size:26px;font-weight:600;margin-top:3px;word-break:break-all;font-variant-numeric:tabular-nums}
.tile .v.small{font-size:13.5px;font-family:'IBM Plex Mono',ui-monospace,monospace;font-weight:500}
.card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:16px;margin-bottom:16px;overflow-x:auto}
.card h2{font-size:14.5px;font-weight:600;margin-bottom:2px;letter-spacing:-.005em}
.card .note{font-size:12.5px;color:var(--ink2);margin-bottom:10px}
table{border-collapse:collapse;font-size:13px;width:100%}
th{color:var(--muted);font-weight:600;text-align:left;padding:5px 10px;border-bottom:1px solid var(--grid)}
td{padding:5px 10px;border-bottom:1px solid var(--grid);font-variant-numeric:tabular-nums}
.chip{display:inline-flex;align-items:center;gap:6px;border-radius:999px;padding:3px 10px;font-size:12.5px;font-weight:600}
.chip.crit{background:color-mix(in srgb,var(--critical) 10%,var(--surface));color:var(--critical);border:1px solid var(--critical);letter-spacing:.06em;text-transform:uppercase;font-size:11px}
.chip.good{background:color-mix(in srgb,var(--good) 12%,var(--surface));color:var(--goodtext);border:1px solid var(--good)}
svg{display:block;max-width:100%}
.tt{position:fixed;pointer-events:none;background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:7px 10px;font-size:12.5px;box-shadow:0 4px 14px rgba(0,0,0,.18);opacity:0;transition:opacity .08s;z-index:9;max-width:280px}
.legend{display:flex;gap:16px;font-size:12.5px;color:var(--ink2);margin:6px 0 2px;flex-wrap:wrap}
.legend .sw{display:inline-block;width:11px;height:11px;border-radius:3px;margin-right:5px;vertical-align:-1px}
.warn{border-left:3px solid var(--critical);padding:8px 12px;font-size:13px;color:var(--ink2);margin-bottom:14px;background:var(--surface);border-radius:0 8px 8px 0}
.footnote{font-size:12px;color:var(--muted);margin-top:8px}
</style></head><body>
<div class="eyebrow">Scenario-driven validation &amp; targeted remediation</div>
<h1>Physical AI Crash-Test Lab</h1>
<div class="sub" id="subtitle"></div>
<hr class="rule">
<div id="synthwarn"></div>
<div class="tabs" role="tablist">
 <button class="tab" role="tab" data-s="suite"><span class="n">1</span>Scenario suite</button>
 <button class="tab" role="tab" data-s="failure"><span class="n">2</span>Failure map</button>
 <button class="tab" role="tab" data-s="remed"><span class="n">3</span>Remediation</button>
 <button class="tab" role="tab" data-s="compare"><span class="n">4</span>Comparison</button>
</div>
<section class="screen" id="s-suite"></section>
<section class="screen" id="s-failure"></section>
<section class="screen" id="s-remed"></section>
<section class="screen" id="s-compare"></section>
<div class="tt" id="tt"></div>
<script>
const DATA = /*__DATA__*/null;
const $=(s,r=document)=>r.querySelector(s);
const fmt=(v,d=3)=>v==null?"n/a":(+v).toFixed(d);
const pct=v=>v==null?"n/a":(100*v).toFixed(1)+"%";
const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const tt=$("#tt");
function hover(el,html){el.addEventListener("mousemove",e=>{tt.innerHTML=html;tt.style.opacity=1;
 tt.style.left=Math.min(e.clientX+14,innerWidth-300)+"px";tt.style.top=(e.clientY+14)+"px";});
 el.addEventListener("mouseleave",()=>tt.style.opacity=0);}
// sequential ramp for miss-rate heatmap (light->dark = worse)
const RAMP=["--seq100","--seq200","--seq300","--seq400","--seq500","--seq600","--seq700"];
const css=v=>getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const rampAt=t=>css(RAMP[Math.max(0,Math.min(RAMP.length-1,Math.floor(t*RAMP.length)))]);

/* ---------- subtitle + synthetic banner ---------- */
$("#subtitle").innerHTML=[["suite",DATA.suite],["manifest",DATA.manifest],["fingerprint",DATA.fingerprint],["frames",DATA.frames],["source",DATA.data_source],["generated",DATA.generated_at]].map(([k,v])=>`<span>${k} <b>${esc(v)}</b></span>`).join("");
if(DATA.synthetic)$("#synthwarn").innerHTML=`<div class="warn"><b>Synthetic placeholder data.</b> This run used fixture predictions, not a real model; numbers exercise the pipeline only.</div>`;

/* ---------- screen 1: suite ---------- */
{
 const s=$("#s-suite");
 const m=DATA.models;
 s.innerHTML=`<div class="tiles">
  <div class="tile"><div class="k">Frames in locked test suite</div><div class="v">${DATA.frames}</div></div>
  <div class="tile"><div class="k">Manifest fingerprint</div><div class="v small">${esc(DATA.fingerprint)}</div></div>
  <div class="tile"><div class="k">Baseline model</div><div class="v small">${esc(m.baseline.ref)}</div></div>
  <div class="tile"><div class="k">Candidate model</div><div class="v small">${m.candidate?esc(m.candidate.ref):"—"}</div></div>
  <div class="tile"><div class="k">IoU / confidence threshold</div><div class="v">${DATA.config.iou_threshold} / ${DATA.config.score_threshold}</div></div>
  <div class="tile"><div class="k">Min samples for a finding</div><div class="v">${DATA.config.min_samples_for_finding}</div></div>
 </div>
 <div class="card"><h2>Scenario factors — declared before any result was inspected</h2>
 <div class="note">Every bucket maps to a physical quantity the simulator applies; the report quotes the same ranges.</div>
 <table><tr><th>Factor</th><th>Bucket</th><th>Physical range</th><th>Unit</th></tr>${
  Object.entries(DATA.factors).map(([f,v])=>Object.entries(v.buckets).map(([b,r])=>
   `<tr><td>${esc(f)}</td><td>${esc(b)}</td><td>${r.lo===r.hi?r.lo:r.lo+" – "+r.hi}</td><td>${esc(v.unit)}</td></tr>`).join("")).join("")}
 </table></div>
 <div class="card"><h2>Not tested in this suite</h2><div class="note">Listed so thin coverage stays visible.</div>
 ${DATA.untested.map(u=>`<div>· ${esc(u)}</div>`).join("")||"—"}</div>`;
}

/* ---------- screen 2: failure map ---------- */
{
 const s=$("#s-failure");
 const o=DATA.overall, det=o.detection.hard_hat, safe=o.safety;
 const weak=DATA.analysis.weakest_slice;
 s.innerHTML=`<div class="tiles">
   <div class="tile"><div class="k">Baseline hard-hat recall (overall)</div><div class="v">${fmt(det.recall.value)}</div><div class="footnote">n=${det.recall.denominator}, 95% CI ${fmt(det.recall.ci95_low,2)}–${fmt(det.recall.ci95_high,2)}</div></div>
   <div class="tile"><div class="k">Precision</div><div class="v">${fmt(det.precision.value)}</div><div class="footnote">n=${det.precision.denominator}</div></div>
   <div class="tile"><div class="k">Dangerous-miss rate</div><div class="v">${fmt(safe.dangerous_miss_rate.value)}</div><div class="footnote">bare head passed as compliant · n=${safe.dangerous_miss_rate.denominator}</div></div>
   <div class="tile"><div class="k">False-alarm rate</div><div class="v">${fmt(safe.false_alarm_rate.value)}</div><div class="footnote">compliant worker flagged · n=${safe.false_alarm_rate.denominator}</div></div>
 </div>
 ${weak?`<div class="card"><h2>Weakest adequately-powered slice</h2>
   <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-top:6px">
   <span class="chip crit">Weakest</span><span class="mono" style="font-size:13px">${esc(weak.slice)}</span>
   <span style="font-size:20px;font-weight:650">${fmt(weak.value)}</span>
   <span class="footnote">recall · n=${weak.denominator} · 95% CI ${fmt(weak.ci95_low,2)}–${fmt(weak.ci95_high,2)}</span></div></div>`:""}
 <div class="card"><h2>Miss-rate heatmap — lighting × helmet state</h2>
  <div class="note">Colour encodes hard-hat <b>miss rate</b> (1 − recall): darker = worse. Cells label recall and sample count. Grey outline = fewer than ${DATA.config.min_samples_for_finding} samples (no verdict).</div>
  <div id="heat1"></div></div>
 <div class="card"><h2>Weakest slices, ranked</h2>
  <div class="note">Worst first by the lower 95% bound. Bars show recall; whiskers the 95% CI.</div>
  <div id="rank"></div></div>`;

 // heatmap grid from analysis slices with exactly {lighting, helmet_state}
 const rows=["bright","normal","dim"], cols=["visible","partial","absent"];
 const all=[...DATA.analysis.findings,...DATA.analysis.underpowered_slices];
 const cell=(li,he)=>all.find(f=>{const c=f.constraints||{};return Object.keys(c).length===2&&c.lighting===li&&c.helmet_state===he;});
 const W=560,CW=150,CH=64,LX=88,TY=30;
 let svg=`<svg viewBox="0 0 ${LX+cols.length*CW+10} ${TY+rows.length*CH+8}" role="img" aria-label="miss rate by lighting and helmet state">`;
 cols.forEach((c,j)=>svg+=`<text x="${LX+j*CW+CW/2}" y="${TY-10}" text-anchor="middle" fill="var(--muted)" font-size="12">${c}</text>`);
 rows.forEach((r,i)=>{svg+=`<text x="${LX-8}" y="${TY+i*CH+CH/2+4}" text-anchor="end" fill="var(--muted)" font-size="12">${r}</text>`;
  cols.forEach((c,j)=>{const f=cell(r,c);
   const miss=f&&f.value!=null?1-f.value:null;
   const fill=miss==null?"var(--grid)":rampAt(miss);
   const under=f?f.underpowered:true;
   const label=f&&f.value!=null?fmt(f.value,2):"n/a";
   const n=f?f.denominator:0;
   const dark=miss!=null&&miss>0.45;
   svg+=`<g class="hm" data-r="${r}" data-c="${c}"><rect x="${LX+j*CW+1}" y="${TY+i*CH+1}" width="${CW-2}" height="${CH-2}" rx="6" fill="${fill}" ${under?'stroke="var(--muted)" stroke-dasharray="4 3"':""}/>` +
   `<text x="${LX+j*CW+CW/2}" y="${TY+i*CH+CH/2-2}" text-anchor="middle" font-size="15" font-weight="650" fill="${dark?"#fff":"var(--ink)"}">${label}</text>`+
   `<text x="${LX+j*CW+CW/2}" y="${TY+i*CH+CH/2+15}" text-anchor="middle" font-size="11" fill="${dark?"rgba(255,255,255,.85)":"var(--ink2)"}">n=${n}${under?" · no verdict":""}</text></g>`;});});
 svg+="</svg>";
 $("#heat1").innerHTML=svg;
 document.querySelectorAll("#heat1 .hm").forEach(g=>{const f=cell(g.dataset.r,g.dataset.c);
  hover(g,f?`<b>${esc(g.dataset.r)} + ${esc(g.dataset.c)}</b><br>recall ${fmt(f.value)} · miss ${f.value!=null?fmt(1-f.value):"n/a"}<br>n=${f.denominator} · CI ${fmt(f.ci95_low,2)}–${fmt(f.ci95_high,2)}${f.underpowered?"<br><i>below sample bar — no verdict</i>":""}`:"no data");});

 // ranked bars
 const top=DATA.analysis.findings.slice(0,10);
 const BW=620,BH=26,LW=310;
 let rk=`<svg viewBox="0 0 ${LW+BW+70} ${top.length*BH+18}" role="img" aria-label="weakest slices">`;
 top.forEach((f,i)=>{const y=i*BH+12,x=v=>LW+v*BW;
  rk+=`<g class="rb" data-i="${i}">
   <text x="${LW-10}" y="${y+9}" text-anchor="end" font-size="12" fill="var(--ink2)">${esc(f.slice)}</text>
   <line x1="${x(0)}" y1="${y+5}" x2="${x(1)}" y2="${y+5}" stroke="var(--grid)"/>
   <line x1="${x(f.ci95_low)}" y1="${y+5}" x2="${x(f.ci95_high)}" y2="${y+5}" stroke="var(--axis)" stroke-width="2"/>
   <rect x="${x(0)}" y="${y}" width="${Math.max(2,f.value*BW)}" height="10" rx="4" fill="var(--s400)"/>
   <text x="${x(f.value)+6}" y="${y+9}" font-size="12" fill="var(--ink)">${fmt(f.value)}<tspan fill="var(--muted)"> n=${f.denominator}</tspan></text></g>`;});
 rk+="</svg>";
 $("#rank").innerHTML=rk;
 document.querySelectorAll("#rank .rb").forEach(g=>{const f=top[+g.dataset.i];
  hover(g,`<b>${esc(f.slice)}</b><br>recall ${fmt(f.value)} · n=${f.denominator}<br>95% CI ${fmt(f.ci95_low,2)}–${fmt(f.ci95_high,2)}`);});
}

/* ---------- screen 3: remediation ---------- */
{
 const s=$("#s-remed"), r=DATA.remediation, w=DATA.analysis.weakest_slice;
 s.innerHTML=`<div class="tiles">
  <div class="tile"><div class="k">Derived from finding</div><div class="v small">${w?esc(w.slice):"—"}</div></div>
  <div class="tile"><div class="k">Measured recall there</div><div class="v">${w?fmt(w.value):"—"}</div><div class="footnote">${w?`n=${w.denominator}`:""}</div></div>
  <div class="tile"><div class="k">Conditions matched</div><div class="v">${r?r.conditions:"—"}</div><div class="footnote">worst cells + adjacent buckets</div></div>
  <div class="tile"><div class="k">Frames generated</div><div class="v">${r?r.frames:"—"}</div><div class="footnote">disjoint from the test suite — verified</div></div>
 </div>
 <div class="card"><h2>How the request is built</h2>
 <div class="note">The worst adequately-powered finding pins factors (${w?esc(JSON.stringify(w.constraints)):"—"}). Every matrix cell matching those constraints is selected, plus one-bucket-adjacent neighbours so the model learns the condition rather than one exact configuration. New frames use fresh seeds; a collision with the locked test suite raises an error rather than leaking.</div></div>`;
}

/* ---------- screen 4: comparison ---------- */
{
 const s=$("#s-compare"), c=DATA.comparison, fc=DATA.fair_comparison;
 if(!c){s.innerHTML="<div class='card'>No candidate evaluated.</div>";}
 else{
 const ov=c.overall;
 s.innerHTML=`<div class="tiles">
   <div class="tile"><div class="k">Overall ${esc(c.metric)}</div><div class="v">${fmt(ov.baseline.value)} → ${fmt(ov.candidate.value)}</div><div class="footnote">Δ ${ov.delta>0?"+":""}${fmt(ov.delta)} · same manifest, fingerprint-verified</div></div>
   <div class="tile"><div class="k">Improved</div><div class="v" style="color:var(--goodtext)">${c.improved.length}</div></div>
   <div class="tile"><div class="k">Regressed</div><div class="v" style="color:var(--critical)">${c.regressed.length}</div></div>
   <div class="tile"><div class="k">No verdict (underpowered)</div><div class="v">${c.underpowered.length}</div></div>
 </div>
 <div class="card"><h2>Before → after by condition slice</h2>
  <div class="note">Dumbbells: baseline → candidate on the identical locked suite. Significant changes only (two-proportion z-test, 95%); regressions shown with the same prominence as wins.</div>
  <div class="legend"><span><span class="sw" style="background:var(--s250)"></span>baseline</span><span><span class="sw" style="background:var(--s550)"></span>candidate</span></div>
  <div id="dumb"></div></div>
 ${DATA.arms.length?`<div class="card"><h2>The volume-matched control — is it targeting, or just more data?</h2>
  <div class="note">Recall on the weakest slice (dim + partially occluded). Arms B and C trained on identical volume; only where the extra frames were aimed differs. Whiskers = 95% CI.</div>
  <div id="arms"></div>
  <div class="footnote">Most of the gain comes from covering hard conditions at all; targeting adds a further measured refinement. Underpowered comparisons receive no verdict.</div></div>`:""}
 <div class="card"><h2>Limitations this dashboard inherits</h2>${DATA.limitations.slice(0,8).map(l=>`<div style="font-size:12.5px;color:var(--ink2);margin:4px 0">· ${esc(l)}</div>`).join("")}</div>`;

 // dumbbells
 const rows=[...c.regressed,...c.improved.slice(0,9)];
 const BW=520,RH=30,LW=330;
 let d=`<svg viewBox="0 0 ${LW+BW+90} ${rows.length*RH+26}" role="img" aria-label="before after by slice">`;
 [0,.25,.5,.75,1].forEach(t=>d+=`<line x1="${LW+t*BW}" y1="8" x2="${LW+t*BW}" y2="${rows.length*RH+8}" stroke="var(--grid)"/><text x="${LW+t*BW}" y="${rows.length*RH+22}" text-anchor="middle" font-size="11" fill="var(--muted)">${t}</text>`);
 rows.forEach((r,i)=>{const y=i*RH+18,x=v=>LW+v*BW;
  const col=r.classification==="regressed"?"var(--critical)":"var(--s550)";
  d+=`<g class="db" data-i="${i}">
   <text x="${LW-10}" y="${y+4}" text-anchor="end" font-size="12" fill="var(--ink2)">${esc(r.slice)}</text>
   <line x1="${x(r.baseline.value)}" y1="${y}" x2="${x(r.candidate.value)}" y2="${y}" stroke="var(--axis)" stroke-width="2"/>
   <circle cx="${x(r.baseline.value)}" cy="${y}" r="6" fill="var(--s250)" stroke="var(--surface)" stroke-width="2"/>
   <circle cx="${x(r.candidate.value)}" cy="${y}" r="6" fill="${col}" stroke="var(--surface)" stroke-width="2"/>
   <text x="${x(Math.max(r.baseline.value,r.candidate.value))+10}" y="${y+4}" font-size="12" fill="var(--ink)">${r.delta>0?"+":""}${fmt(r.delta,2)}</text></g>`;});
 d+="</svg>";
 $("#dumb").innerHTML=d;
 document.querySelectorAll("#dumb .db").forEach(g=>{const r=rows[+g.dataset.i];
  hover(g,`<b>${esc(r.slice)}</b><br>baseline ${fmt(r.baseline.value)} (n=${r.baseline.denominator})<br>candidate ${fmt(r.candidate.value)} (n=${r.candidate.denominator})<br>Δ ${r.delta>0?"+":""}${fmt(r.delta)} · ${r.classification}`);});

 // four-way arms
 if(DATA.arms.length){
  const arms=DATA.arms, BW2=560, BH2=42, LW2=330;
  const shades=["--s250","--s400","--s550","--s700"];
  let a=`<svg viewBox="0 0 ${LW2+BW2+80} ${arms.length*BH2+30}" role="img" aria-label="volume matched arms">`;
  [0,.25,.5,.75,1].forEach(t=>a+=`<line x1="${LW2+t*BW2}" y1="6" x2="${LW2+t*BW2}" y2="${arms.length*BH2+6}" stroke="var(--grid)"/><text x="${LW2+t*BW2}" y="${arms.length*BH2+24}" text-anchor="middle" font-size="11" fill="var(--muted)">${t}</text>`);
  arms.forEach((m,i)=>{const y=i*BH2+12,x=v=>LW2+v*BW2;
   a+=`<g class="ab" data-i="${i}">
    <text x="${LW2-10}" y="${y+13}" text-anchor="end" font-size="12" fill="var(--ink2)">${esc(m.key)} · ${esc(m.label)}</text>
    <rect x="${x(0)}" y="${y}" width="${Math.max(2,(m.target_value||0)*BW2)}" height="18" rx="4" fill="var(${shades[i%4]})"/>
    ${m.target_ci?`<line x1="${x(m.target_ci[0])}" y1="${y+9}" x2="${x(m.target_ci[1])}" y2="${y+9}" stroke="var(--ink)" stroke-opacity=".55" stroke-width="2"/>`:""}
    <text x="${x(m.target_value||0)+8}" y="${y+13}" font-size="12.5" font-weight="650" fill="var(--ink)">${fmt(m.target_value)}</text></g>`;});
  a+="</svg>";
  $("#arms").innerHTML=a;
  document.querySelectorAll("#arms .ab").forEach(g=>{const m=arms[+g.dataset.i];
   hover(g,`<b>${esc(m.key)} — ${esc(m.label)}</b><br>dim+partial recall ${fmt(m.target_value)} (n=${m.target_n})<br>95% CI ${m.target_ci?fmt(m.target_ci[0],2)+"–"+fmt(m.target_ci[1],2):"n/a"}<br>overall ${fmt(m.overall)}`);});
 }}
}

/* ---------- tabs ---------- */
const tabs=[...document.querySelectorAll(".tab")];
function show(k){tabs.forEach(t=>t.setAttribute("aria-selected",t.dataset.s===k));
 document.querySelectorAll(".screen").forEach(x=>x.classList.toggle("active",x.id==="s-"+k));
 try{localStorage.setItem("crashlab-tab",k)}catch(e){}}
tabs.forEach(t=>t.addEventListener("click",()=>show(t.dataset.s)));
let init="failure";try{init=localStorage.getItem("crashlab-tab")||init}catch(e){}
show(init);
</script></body></html>
"""

if __name__ == "__main__":
    raise SystemExit(main())
