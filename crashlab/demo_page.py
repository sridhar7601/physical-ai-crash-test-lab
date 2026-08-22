"""Build the interactive frame explorer: real frames, real detections.

    python3 -m crashlab.demo_page --data demo_data.json --out demo/index.html

The page is the hands-on half of the evidence: pick a condition cell, see an
actual rendered frame, and flip between the baseline and candidate models to
watch their real detections drawn over the image. Nothing is staged — boxes
come from each model's stored predictions on the locked test suite.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def build(data_path: Path, out: Path) -> Path:
    data = json.loads(data_path.read_text())
    html = TEMPLATE.replace("/*__DATA__*/null", json.dumps(data, separators=(",", ":")))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    out = build(Path(a.data), Path(a.out))
    print(f"[demo] wrote {out} ({out.stat().st_size} bytes)")
    return 0


TEMPLATE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Crash-Test Explorer</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{color-scheme:light;
 --page:#f9f9f7;--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;
 --grid:#e1e0d9;--axis:#c3c2b7;--border:rgba(11,11,11,.10);
 --accent:#2a78d6;--accent-strong:#1c5cab;--critical:#d03b3b;--good:#006300}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){color-scheme:dark;
 --page:#0d0d0d;--surface:#1a1a19;--ink:#fff;--ink2:#c3c2b7;--muted:#898781;
 --grid:#2c2c2a;--axis:#383835;--border:rgba(255,255,255,.10);
 --accent:#3987e5;--accent-strong:#5598e7;--critical:#e66767;--good:#0ca30c}}
:root[data-theme=dark]{color-scheme:dark;
 --page:#0d0d0d;--surface:#1a1a19;--ink:#fff;--ink2:#c3c2b7;--muted:#898781;
 --grid:#2c2c2a;--axis:#383835;--border:rgba(255,255,255,.10);
 --accent:#3987e5;--accent-strong:#5598e7;--critical:#e66767;--good:#0ca30c}
*{box-sizing:border-box;margin:0}
body{background:var(--page);color:var(--ink);font:15px/1.5 'IBM Plex Sans',system-ui,-apple-system,'Segoe UI',sans-serif;padding:26px clamp(14px,4vw,44px) 64px}
.mono{font-family:'IBM Plex Mono',ui-monospace,'SF Mono',Menlo,monospace}
.eyebrow{font-size:11px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
h1{font-size:24px;font-weight:600;letter-spacing:-.01em;margin:4px 0 6px}
.lede{color:var(--ink2);font-size:13.5px;max-width:640px;margin-bottom:18px}
.wrap{display:grid;grid-template-columns:minmax(220px,280px) 1fr;gap:18px;align-items:start}
@media (max-width:860px){.wrap{grid-template-columns:1fr}}
.panel{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:14px}
.panel h2{font-size:11px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin-bottom:10px}
.matrix{display:grid;grid-template-columns:auto repeat(3,1fr);gap:6px;font-size:12px}
.matrix .lab{align-self:center;color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.06em;padding-right:4px;text-align:right}
.matrix .head{text-align:center;color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.06em}
.cellbtn{border:1px solid var(--border);background:var(--page);border-radius:8px;padding:12px 4px;cursor:pointer;color:var(--ink2);font:500 12px 'IBM Plex Sans',sans-serif;position:relative}
.cellbtn:hover{border-color:var(--axis)}
.cellbtn[aria-pressed=true]{border-color:var(--accent);color:var(--ink);box-shadow:inset 0 0 0 1px var(--accent)}
.cellbtn .dot{position:absolute;top:6px;right:6px;width:7px;height:7px;border-radius:50%}
.cellbtn:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.keylist{margin-top:12px;font-size:12px;color:var(--ink2);display:grid;gap:6px}
.keylist .dot{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:7px;vertical-align:1px}
.viewer{position:relative;border-radius:10px;overflow:hidden;background:#000;border:1px solid var(--border)}
.viewer img{display:block;width:100%;height:auto}
.viewer svg{position:absolute;inset:0;width:100%;height:100%}
.controls{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:12px 0 4px}
.seg{display:inline-flex;border:1px solid var(--border);border-radius:8px;overflow:hidden}
.seg button{border:0;background:var(--page);color:var(--ink2);font:600 12px 'IBM Plex Sans',sans-serif;letter-spacing:.05em;text-transform:uppercase;padding:9px 16px;cursor:pointer}
.seg button[aria-pressed=true]{background:var(--accent);color:#fff}
.tgl{display:inline-flex;align-items:center;gap:7px;font-size:13px;color:var(--ink2);cursor:pointer;user-select:none}
.tgl input{accent-color:var(--accent);width:15px;height:15px}
.btn{border:1px solid var(--border);background:var(--surface);color:var(--ink2);border-radius:8px;padding:8px 14px;font:500 13px 'IBM Plex Sans',sans-serif;cursor:pointer}
.btn:hover{border-color:var(--axis);color:var(--ink)}
.verdict{border-left:3px solid var(--axis);border-radius:0 8px 8px 0;background:var(--surface);padding:10px 14px;font-size:13.5px;margin-top:12px}
.verdict.bad{border-left-color:var(--critical)}
.verdict.good{border-left-color:var(--good)}
.verdict b{font-weight:600}
.meta{display:flex;gap:18px;flex-wrap:wrap;margin-top:10px;font-size:12px;color:var(--ink2)}
.meta span b{color:var(--ink);font-weight:500;font-family:'IBM Plex Mono',monospace}
.legend{display:flex;gap:16px;font-size:12px;color:var(--ink2);margin-top:10px;flex-wrap:wrap}
.sw{display:inline-block;width:14px;height:0;border-top:3px solid;margin-right:6px;vertical-align:3px}
.foot{margin-top:22px;font-size:12px;color:var(--muted);max-width:660px}
</style></head><body>
<div class="eyebrow">Physical AI Crash-Test Lab</div>
<h1>Crash-Test Explorer</h1>
<p class="lede">Real frames from the locked test suite, with each model's real
detections drawn over them. Pick a condition, then flip between the baseline
and the remediated candidate. Nothing here is staged.</p>
<div class="wrap">
 <div class="panel">
  <h2>Condition — lighting × helmet</h2>
  <div class="matrix" id="matrix"></div>
  <div class="keylist">
    <div><span class="dot" style="background:var(--critical)"></span>baseline misses the helmet here</div>
    <div><span class="dot" style="background:var(--good)"></span>baseline handles this cell</div>
  </div>
 </div>
 <div>
  <div class="viewer" id="viewer"><img id="frame" alt="rendered warehouse frame"><svg id="overlay" preserveAspectRatio="none"></svg></div>
  <div class="controls">
   <span class="seg" role="group" aria-label="model">
     <button id="mBase" aria-pressed="true">Baseline</button><button id="mCand" aria-pressed="false">Candidate</button>
   </span>
   <label class="tgl"><input type="checkbox" id="showGT" checked>Ground truth</label>
   <label class="tgl"><input type="checkbox" id="showPred" checked>Detections</label>
   <button class="btn" id="next">Next example</button>
  </div>
  <div class="legend">
    <span><span class="sw" style="border-color:var(--accent)"></span>model: hard hat</span>
    <span><span class="sw" style="border-color:var(--axis)"></span>model: person</span>
    <span><span class="sw" style="border-style:dashed;border-color:var(--ink)"></span>ground truth</span>
  </div>
  <div class="verdict" id="verdict"></div>
  <div class="meta" id="meta"></div>
 </div>
</div>
<p class="foot">Detections are each model's stored predictions on the
fingerprint-locked test suite at confidence ≥ <span id="conf"></span>, IoU 0.5 —
the same thresholds as the evidence report. Ground truth comes from the
simulator; occlusion is measured by the renderer per frame.</p>
<script>
const DATA=/*__DATA__*/null;
const LIGHT=["bright","normal","dim"],HAT=["visible","partial","absent"];
const $=s=>document.querySelector(s);
$("#conf").textContent=DATA.conf;
let cell="dim|partial",idx=0,model="baseline";
function cellStories(k){return (DATA.cells[k]||[]).map(e=>e.story.baseline)}
const matrix=$("#matrix");
matrix.innerHTML='<span></span>'+HAT.map(h=>`<span class="head">${h}</span>`).join("");
for(const l of LIGHT){
 matrix.innerHTML+=`<span class="lab">${l}</span>`+HAT.map(h=>{
  const k=`${l}|${h}`,st=cellStories(k);
  const bad=st.includes("missed")||st.includes("wrong_place")||st.includes("hallucinated");
  return `<button class="cellbtn" data-k="${k}" aria-pressed="false">${l[0].toUpperCase()+l.slice(1)}<br>${h}<span class="dot" style="background:var(${bad?"--critical":"--good"})"></span></button>`;
 }).join("");
}
const VTEXT={
 missed:['bad','Helmet present — <b>the model found nothing</b>. In production, this worker\'s PPE state is invisible in exactly the dangerous condition.'],
 wrong_place:['bad','Helmet present — the model fired, but <b>not on the helmet</b> (no IoU-0.5 match).'],
 hit:['good','<b>Helmet detected</b> and matched to ground truth at IoU ≥ 0.5.'],
 hallucinated:['bad','No helmet worn — <b>the model reported one anyway</b>: a bare-headed worker passes as compliant.'],
 correct_none:['good','No helmet worn — and <b>correctly, no helmet detected</b>.']};
function draw(){
 const e=(DATA.cells[cell]||[])[idx]; if(!e) return;
 $("#frame").src="data:image/jpeg;base64,"+e.img;
 const img=$("#frame");
 const render=()=>{
  const W=img.naturalWidth,H=img.naturalHeight;
  const ov=$("#overlay"); ov.setAttribute("viewBox",`0 0 ${W} ${H}`); ov.innerHTML="";
  const box=(b,style,dash)=>{const[x1,y1,x2,y2]=b.bbox;
   ov.innerHTML+=`<rect x="${x1}" y="${y1}" width="${x2-x1}" height="${y2-y1}" fill="none" stroke="${style}" stroke-width="3" ${dash?'stroke-dasharray="8 6"':''}/>`
   +(b.score!==undefined&&b.label==="hard_hat"?`<text x="${x1}" y="${Math.max(14,y1-6)}" font-size="15" font-weight="600" fill="${style}" font-family="IBM Plex Mono,monospace">${b.label} ${b.score}</text>`:"");};
  if($("#showGT").checked)for(const b of e.gt)box(b,"rgba(255,255,255,.92)",true);
  if($("#showPred").checked)for(const b of e[model])box(b,b.label==="hard_hat"?"var(--accent)":"var(--axis)");
 };
 img.complete?render():img.onload=render;
 const st=e.story[model],[cls,txt]=VTEXT[st]||['','' ];
 $("#verdict").className="verdict "+cls;
 $("#verdict").innerHTML=`<b style="text-transform:uppercase;letter-spacing:.05em;font-size:11px">${model}</b> — ${txt}`;
 $("#meta").innerHTML=[["frame",e.id],["target lux",Math.round(e.lux)],["measured occlusion",e.occl==null?"n/a":e.occl.toFixed(2)],["distance",e.distance_m+" m"],["elevation",e.elev+"°"]].map(([k,v])=>`<span>${k} <b>${v}</b></span>`).join("");
 document.querySelectorAll(".cellbtn").forEach(b=>b.setAttribute("aria-pressed",b.dataset.k===cell));
 $("#mBase").setAttribute("aria-pressed",model==="baseline");
 $("#mCand").setAttribute("aria-pressed",model==="candidate");
}
matrix.addEventListener("click",ev=>{const b=ev.target.closest(".cellbtn");if(!b)return;cell=b.dataset.k;idx=0;draw();});
$("#mBase").onclick=()=>{model="baseline";draw()};
$("#mCand").onclick=()=>{model="candidate";draw()};
$("#next").onclick=()=>{idx=(idx+1)%((DATA.cells[cell]||[]).length||1);draw()};
$("#showGT").onchange=draw; $("#showPred").onchange=draw;
addEventListener("keydown",e=>{if(e.key==="b")$("#mBase").click();if(e.key==="c")$("#mCand").click();if(e.key==="n")$("#next").click();});
draw();
</script></body></html>
"""

if __name__ == "__main__":
    raise SystemExit(main())
