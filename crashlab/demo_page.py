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
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>
/* Dark-first: this is a viewing instrument; frames read best on a dark ground. */
:root{color-scheme:dark;
 --page:#0e0f0e;--surface:#161716;--panel:#1b1c1b;--ink:#f4f4f1;--ink2:#b9b9b2;--muted:#84847d;
 --grid:#262725;--axis:#3a3b38;--border:rgba(255,255,255,.09);
 --accent:#3987e5;--accent-2:#5598e7;--hazard:#eda100;--critical:#e66767;--good:#0ca30c;
 --scrim-top:linear-gradient(180deg,rgba(0,0,0,.62),rgba(0,0,0,0) 34%);
 --scrim-bot:linear-gradient(0deg,rgba(0,0,0,.66),rgba(0,0,0,0) 40%);
 --lift:0 14px 40px rgba(0,0,0,.45)}
@media (prefers-color-scheme:light){:root:not([data-theme=dark]){color-scheme:light;
 --page:#f4f4f0;--surface:#fdfdfb;--panel:#f8f8f5;--ink:#101010;--ink2:#4c4c48;--muted:#8a8a83;
 --grid:#e3e3dc;--axis:#c6c6be;--border:rgba(16,16,16,.10);
 --accent:#2a78d6;--accent-2:#1c5cab;--hazard:#b57b00;--critical:#c53030;--good:#0a7a0a;
 --lift:0 14px 34px rgba(20,20,15,.14)}}
:root[data-theme=light]{color-scheme:light;
 --page:#f4f4f0;--surface:#fdfdfb;--panel:#f8f8f5;--ink:#101010;--ink2:#4c4c48;--muted:#8a8a83;
 --grid:#e3e3dc;--axis:#c6c6be;--border:rgba(16,16,16,.10);
 --accent:#2a78d6;--accent-2:#1c5cab;--hazard:#b57b00;--critical:#c53030;--good:#0a7a0a;
 --lift:0 14px 34px rgba(20,20,15,.14)}
*{box-sizing:border-box;margin:0}
html{scroll-behavior:smooth}
body{background:var(--page);color:var(--ink);font:15px/1.5 'IBM Plex Sans',system-ui,-apple-system,'Segoe UI',sans-serif;
 padding:0 clamp(16px,4.5vw,56px) 72px;min-height:100vh}
body::before{content:"";display:block;height:5px;margin:0 calc(-1*clamp(16px,4.5vw,56px)) 26px;
 background:repeating-linear-gradient(-45deg,var(--hazard) 0 14px,transparent 14px 28px);opacity:.9}
.mono{font-family:'IBM Plex Mono',ui-monospace,'SF Mono',Menlo,monospace}

/* masthead */
header{display:flex;justify-content:space-between;align-items:flex-end;gap:20px;flex-wrap:wrap;margin-bottom:22px}
.eyebrow{font-size:11px;font-weight:600;letter-spacing:.16em;text-transform:uppercase;color:var(--hazard)}
h1{font-size:clamp(26px,3.4vw,34px);font-weight:600;letter-spacing:-.015em;margin-top:4px}
.lede{color:var(--ink2);font-size:13.5px;max-width:560px;margin-top:8px;text-wrap:pretty}
.playwrap{display:flex;flex-direction:column;align-items:flex-end;gap:6px}
.play{border:1px solid var(--hazard);background:transparent;color:var(--ink);border-radius:999px;
 padding:11px 22px;font:600 12.5px 'IBM Plex Sans',sans-serif;letter-spacing:.09em;text-transform:uppercase;
 cursor:pointer;display:inline-flex;align-items:center;gap:10px;transition:background .18s,transform .18s}
.play:hover{background:color-mix(in srgb,var(--hazard) 14%,transparent);transform:translateY(-1px)}
.play .tri{width:0;height:0;border-left:9px solid var(--hazard);border-top:6px solid transparent;border-bottom:6px solid transparent;transition:border-left-color .18s}
.play[data-on="1"] .tri{border:0;width:9px;height:11px;background:linear-gradient(90deg,var(--hazard) 0 3px,transparent 3px 6px,var(--hazard) 6px 9px)}
.playhint{font-size:11px;color:var(--muted)}

/* stage grid */
.stagewrap{display:grid;grid-template-columns:minmax(0,1.55fr) minmax(300px,1fr);gap:20px;align-items:start}
@media (max-width:980px){.stagewrap{grid-template-columns:1fr}}

/* viewer */
.viewer{position:relative;border-radius:14px;overflow:hidden;background:#000;border:1px solid var(--border);box-shadow:var(--lift);aspect-ratio:16/9}
.viewer img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:0;transition:opacity .28s ease}
.viewer img.on{opacity:1}
.viewer svg{position:absolute;inset:0;width:100%;height:100%}
.viewer svg rect{transition:opacity .22s ease}
.hud{position:absolute;inset:0;pointer-events:none;font-family:'IBM Plex Mono',monospace}
.hud .top{position:absolute;inset:0 0 auto 0;padding:14px 16px;display:flex;justify-content:space-between;background:var(--scrim-top);color:#fff;font-size:12px;letter-spacing:.05em}
.hud .bot{position:absolute;inset:auto 0 0 0;padding:12px 16px;display:flex;gap:18px;flex-wrap:wrap;background:var(--scrim-bot);color:rgba(255,255,255,.92);font-size:11.5px}
.hud .bot b{color:#fff;font-weight:600}
.hud .cam::before{content:"";display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--hazard);margin-right:8px;animation:blink 2.4s infinite}
@keyframes blink{0%,72%{opacity:1}86%{opacity:.25}100%{opacity:1}}
.corner{position:absolute;width:20px;height:20px;border:2px solid rgba(255,255,255,.5)}
.corner.tl{top:10px;left:10px;border-right:0;border-bottom:0}
.corner.tr{top:10px;right:10px;border-left:0;border-bottom:0}
.corner.bl{bottom:10px;left:10px;border-right:0;border-top:0}
.corner.br{bottom:10px;right:10px;border-left:0;border-top:0}

/* verdict under viewer */
.verdict{margin-top:14px;border-radius:10px;background:var(--surface);border:1px solid var(--border);
 padding:13px 16px;font-size:14px;display:flex;gap:14px;align-items:center;min-height:56px;
 transition:border-color .25s;position:relative;overflow:hidden}
.verdict .status{font:600 11px 'IBM Plex Mono',monospace;letter-spacing:.12em;padding:5px 10px;border-radius:5px;white-space:nowrap}
.verdict.bad .status{background:color-mix(in srgb,var(--critical) 16%,transparent);color:var(--critical)}
.verdict.good .status{background:color-mix(in srgb,var(--good) 18%,transparent);color:var(--good)}
.verdict.bad{border-left:4px solid var(--critical)}
.verdict.good{border-left:4px solid var(--good)}
.verdict p{color:var(--ink2);animation:rise .3s ease}
.verdict p b{color:var(--ink);font-weight:600}
@keyframes rise{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:none}}

/* console */
.console{display:grid;gap:14px}
.panel{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:16px}
.panel h2{font-size:11px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin-bottom:12px}
.matrix{display:grid;grid-template-columns:auto repeat(3,1fr);gap:7px}
.matrix .lab{align-self:center;color:var(--muted);font-size:10.5px;text-transform:uppercase;letter-spacing:.07em;padding-right:6px;text-align:right}
.matrix .head{text-align:center;color:var(--muted);font-size:10.5px;text-transform:uppercase;letter-spacing:.07em;padding-bottom:2px}
.cellbtn{border:1px solid var(--border);background:var(--panel);border-radius:9px;padding:13px 4px 11px;cursor:pointer;
 color:var(--ink2);font:500 12px 'IBM Plex Sans',sans-serif;position:relative;
 transition:transform .16s ease,border-color .16s,color .16s,background .16s}
.cellbtn:hover{transform:translateY(-2px);border-color:var(--axis);color:var(--ink)}
.cellbtn[aria-pressed=true]{border-color:var(--accent);color:var(--ink);background:color-mix(in srgb,var(--accent) 10%,var(--panel));box-shadow:inset 0 0 0 1px var(--accent)}
.cellbtn .dot{position:absolute;top:7px;right:7px;width:7px;height:7px;border-radius:50%}
.cellbtn:focus-visible,.play:focus-visible,.seg button:focus-visible,.btn:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.keylist{margin-top:12px;font-size:11.5px;color:var(--muted);display:grid;gap:5px}
.keylist .dot{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:7px;vertical-align:1px}

/* model switch */
.seg{position:relative;display:grid;grid-template-columns:1fr 1fr;border:1px solid var(--border);border-radius:9px;overflow:hidden;background:var(--panel)}
.seg .thumb{position:absolute;top:3px;bottom:3px;left:3px;width:calc(50% - 6px);border-radius:6px;background:var(--accent);
 transition:transform .22s cubic-bezier(.2,.8,.2,1)}
.seg[data-m="candidate"] .thumb{transform:translateX(calc(100% + 6px))}
.seg button{position:relative;z-index:1;border:0;background:transparent;color:var(--ink2);
 font:600 12px 'IBM Plex Sans',sans-serif;letter-spacing:.07em;text-transform:uppercase;padding:11px 8px;cursor:pointer;transition:color .2s}
.seg button[aria-pressed=true]{color:#fff}
.tglrow{display:flex;gap:16px;flex-wrap:wrap;margin-top:12px}
.tgl{display:inline-flex;align-items:center;gap:7px;font-size:13px;color:var(--ink2);cursor:pointer;user-select:none}
.tgl input{accent-color:var(--accent);width:15px;height:15px}
.btn{border:1px solid var(--border);background:var(--panel);color:var(--ink2);border-radius:9px;padding:10px 14px;
 font:500 13px 'IBM Plex Sans',sans-serif;cursor:pointer;transition:color .16s,border-color .16s}
.btn:hover{border-color:var(--axis);color:var(--ink)}
.legend{display:grid;gap:7px;font-size:12px;color:var(--ink2);margin-top:2px}
.sw{display:inline-block;width:16px;height:0;border-top:3px solid;margin-right:8px;vertical-align:3px;border-radius:2px}
kbd{font:500 11px 'IBM Plex Mono',monospace;color:var(--ink2);border:1px solid var(--border);border-bottom-width:2px;border-radius:4px;padding:1px 6px;background:var(--panel)}

footer{margin-top:30px;padding-top:16px;border-top:1px solid var(--grid);display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;font-size:11.5px;color:var(--muted)}
footer .mono{color:var(--ink2)}

/* staged reveal */
.reveal{opacity:0;transform:translateY(10px);animation:in .5s ease forwards}
header.reveal{animation-delay:.02s}.stagewrap>.reveal:nth-child(1){animation-delay:.12s}.stagewrap>.reveal:nth-child(2){animation-delay:.22s}
@keyframes in{to{opacity:1;transform:none}}
@media (prefers-reduced-motion:reduce){
 *,*::before,*::after{animation:none!important;transition:none!important}
 .reveal{opacity:1;transform:none}}
</style></head><body>
<header class="reveal">
 <div>
  <div class="eyebrow">Physical AI Crash-Test Lab</div>
  <h1>Crash-Test Explorer</h1>
  <p class="lede">Real frames from the fingerprint-locked test suite, with each
  model's real detections drawn over them. Pick a condition; flip the model.
  Nothing is staged.</p>
 </div>
 <div class="playwrap">
  <button class="play" id="tour"><span class="tri"></span><span id="tourlabel">Play the story</span></button>
  <span class="playhint">30-second guided sequence</span>
 </div>
</header>
<div class="stagewrap">
 <div class="reveal">
  <div class="viewer" id="viewer">
   <img id="imgA" alt=""><img id="imgB" alt="rendered warehouse frame">
   <svg id="overlay" preserveAspectRatio="none"></svg>
   <div class="hud">
    <div class="top"><span class="cam" id="hudcond"></span><span id="hudframe"></span></div>
    <div class="bot" id="hudmeta"></div>
    <span class="corner tl"></span><span class="corner tr"></span><span class="corner bl"></span><span class="corner br"></span>
   </div>
  </div>
  <div class="verdict" id="verdict"><span class="status" id="vstatus"></span><p id="vtext"></p></div>
 </div>
 <div class="console reveal">
  <div class="panel">
   <h2>Condition — lighting × helmet</h2>
   <div class="matrix" id="matrix"></div>
   <div class="keylist">
    <div><span class="dot" style="background:var(--critical)"></span>baseline misses the helmet here</div>
    <div><span class="dot" style="background:var(--good)"></span>baseline handles this cell</div>
   </div>
  </div>
  <div class="panel">
   <h2>Model under test</h2>
   <div class="seg" id="seg" data-m="baseline" role="group" aria-label="model">
     <span class="thumb"></span>
     <button id="mBase" aria-pressed="true">Baseline</button><button id="mCand" aria-pressed="false">Candidate</button>
   </div>
   <div class="tglrow">
    <label class="tgl"><input type="checkbox" id="showGT" checked>Ground truth</label>
    <label class="tgl"><input type="checkbox" id="showPred" checked>Detections</label>
    <button class="btn" id="next">Next example</button>
   </div>
  </div>
  <div class="panel">
   <h2>Reading the overlay</h2>
   <div class="legend">
    <div><span class="sw" style="border-color:var(--accent)"></span>model: hard hat (with confidence)</div>
    <div><span class="sw" style="border-color:var(--axis)"></span>model: person</div>
    <div><span class="sw" style="border-style:dashed;border-color:var(--ink)"></span>ground truth (simulator)</div>
   </div>
   <div class="keylist" style="margin-top:12px">
    <div><kbd>b</kbd> baseline&nbsp;&nbsp;<kbd>c</kbd> candidate&nbsp;&nbsp;<kbd>n</kbd> next frame</div>
   </div>
  </div>
 </div>
</div>
<footer>
 <span>Detections at confidence ≥ <span id="conf" class="mono"></span>, IoU 0.5 — the evidence report's own thresholds. Occlusion measured per frame by the renderer.</span>
 <span class="mono">suite warehouse_ppe_v2 · NVIDIA Isaac Sim / Replicator · YOLO11n</span>
</footer>
<script>
const DATA=/*__DATA__*/null;
const LIGHT=["bright","normal","dim"],HAT=["visible","partial","absent"];
const $=s=>document.querySelector(s);
const reduced=matchMedia("(prefers-reduced-motion: reduce)").matches;
$("#conf").textContent=DATA.conf;
let cell="dim|partial",idx=0,model="baseline",layer=0;
const imgs=[$("#imgA"),$("#imgB")];
const stories=k=>(DATA.cells[k]||[]).map(e=>e.story.baseline);
const matrix=$("#matrix");
matrix.innerHTML='<span></span>'+HAT.map(h=>`<span class="head">${h}</span>`).join("");
for(const l of LIGHT){
 matrix.innerHTML+=`<span class="lab">${l}</span>`+HAT.map(h=>{
  const k=`${l}|${h}`,st=stories(k);
  const bad=st.some(s=>["missed","wrong_place","hallucinated"].includes(s));
  return `<button class="cellbtn" data-k="${k}" aria-pressed="false">${h}<span class="dot" style="background:var(${bad?"--critical":"--good"})"></span></button>`;
 }).join("");
}
const VTEXT={
 missed:['bad','NO DETECTION','Helmet present — <b>the model found nothing</b>. In production, this worker\'s PPE state is invisible in exactly the dangerous condition.'],
 wrong_place:['bad','NO MATCH','Helmet present — the model fired, but <b>not on the helmet</b> (no IoU-0.5 match).'],
 hit:['good','DETECTED','<b>Helmet detected</b> and matched to ground truth at IoU ≥ 0.5.'],
 hallucinated:['bad','FALSE COMPLIANT','No helmet worn — <b>the model reported one anyway</b>: a bare-headed worker passes as compliant.'],
 correct_none:['good','CLEAR','No helmet worn — and <b>correctly, no helmet detected</b>.']};
function entry(){return (DATA.cells[cell]||[])[idx]}
function drawBoxes(e){
 const ov=$("#overlay");
 const img=imgs[layer];
 const render=()=>{
  ov.setAttribute("viewBox",`0 0 ${img.naturalWidth} ${img.naturalHeight}`);ov.innerHTML="";
  const put=(b,stroke,dash)=>{const[x1,y1,x2,y2]=b.bbox;
   ov.innerHTML+=`<rect x="${x1}" y="${y1}" width="${x2-x1}" height="${y2-y1}" fill="none" stroke="${stroke}" stroke-width="3.5" ${dash?'stroke-dasharray="9 7"':""} rx="3"/>`
   +(b.score!==undefined&&b.label==="hard_hat"?`<text x="${x1+2}" y="${Math.max(17,y1-8)}" font-size="16" font-weight="600" fill="${stroke}" font-family="IBM Plex Mono,monospace" paint-order="stroke" stroke="rgba(0,0,0,.55)" stroke-width="3">hard_hat ${b.score}</text>`:"");};
  if($("#showGT").checked)for(const b of e.gt)put(b,"rgba(255,255,255,.95)",true);
  if($("#showPred").checked)for(const b of e[model])put(b,b.label==="hard_hat"?"var(--accent-2)":"rgba(255,255,255,.45)");
 };
 img.complete?render():img.onload=render;
}
function draw(newFrame){
 const e=entry(); if(!e)return;
 if(newFrame){
  layer=1-layer;
  const img=imgs[layer];
  img.classList.remove("on");
  img.src="data:image/jpeg;base64,"+e.img;
  (img.decode?img.decode().catch(()=>{}):Promise.resolve()).then(()=>{
    imgs.forEach((im,i)=>im.classList.toggle("on",i===layer));
    drawBoxes(e);
  });
 } else drawBoxes(e);
 const [l,h]=cell.split("|");
 $("#hudcond").textContent=`CAM 02 · ${l.toUpperCase()} / ${h.toUpperCase()}`;
 $("#hudframe").textContent=e.id;
 $("#hudmeta").innerHTML=[["LUX",Math.round(e.lux)],["OCCLUSION",e.occl==null?"—":e.occl.toFixed(2)],["RANGE",e.distance_m+" m"],["ELEV",e.elev+"°"],["MODEL",model.toUpperCase()]].map(([k,v])=>`<span>${k} <b>${v}</b></span>`).join("");
 const st=e.story[model],[cls,word,txt]=VTEXT[st];
 const v=$("#verdict");v.className="verdict "+cls;
 $("#vstatus").textContent=word;
 const vt=$("#vtext");vt.style.animation="none";void vt.offsetWidth;vt.style.animation="";vt.innerHTML=txt;
 document.querySelectorAll(".cellbtn").forEach(b=>b.setAttribute("aria-pressed",b.dataset.k===cell));
 $("#seg").dataset.m=model;
 $("#mBase").setAttribute("aria-pressed",model==="baseline");
 $("#mCand").setAttribute("aria-pressed",model==="candidate");
}
function setCell(k){cell=k;idx=0;draw(true)}
function setModel(m){if(model!==m){model=m;draw(false)}}
matrix.addEventListener("click",ev=>{const b=ev.target.closest(".cellbtn");if(b){stopTour();setCell(b.dataset.k)}});
$("#mBase").onclick=()=>{stopTour();setModel("baseline")};
$("#mCand").onclick=()=>{stopTour();setModel("candidate")};
$("#next").onclick=()=>{stopTour();idx=(idx+1)%((DATA.cells[cell]||[]).length||1);draw(true)};
$("#showGT").onchange=()=>draw(false);$("#showPred").onchange=()=>draw(false);
addEventListener("keydown",e=>{
 if(["b","c","n"].includes(e.key))stopTour();
 if(e.key==="b")setModel("baseline");if(e.key==="c")setModel("candidate");
 if(e.key==="n"){idx=(idx+1)%((DATA.cells[cell]||[]).length||1);draw(true)}});
/* guided tour: the money sequence */
let tourT=[];
const STEPS=[
 ["bright|visible","baseline",3200],["dim|partial","baseline",4600],
 ["dim|partial","candidate",4600],["bright|absent","baseline",3600],["dim|partial","candidate",2600]];
function stopTour(){tourT.forEach(clearTimeout);tourT=[];$("#tour").dataset.on="0";$("#tourlabel").textContent="Play the story"}
$("#tour").onclick=()=>{
 if(tourT.length){stopTour();return}
 $("#tour").dataset.on="1";$("#tourlabel").textContent="Stop";
 let t=0;
 for(const [k,m,d] of STEPS){
  tourT.push(setTimeout(()=>{cell=k;idx=0;model=m;draw(true)},t));t+=reduced?1400:d;
 }
 tourT.push(setTimeout(stopTour,t));
};
draw(true);
</script></body></html>
"""

if __name__ == "__main__":
    raise SystemExit(main())
