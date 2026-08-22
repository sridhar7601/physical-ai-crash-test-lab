import { useCallback, useEffect, useMemo, useRef, useState } from "react";

const LIGHT = ["bright", "normal", "dim"];
const HAT = ["visible", "partial", "absent"];
const BAD = ["missed", "wrong_place", "hallucinated"];

const VERDICT = {
  missed: ["bad", "NO DETECTION", <>Helmet present — <b>the model found nothing</b>. In production this worker's PPE state is invisible in exactly the dangerous condition.</>],
  wrong_place: ["bad", "NO MATCH", <>Helmet present — the model fired, but <b>not on the helmet</b> (no IoU-0.5 match).</>],
  hit: ["good", "DETECTED", <><b>Helmet detected</b> and matched to ground truth at IoU ≥ 0.5.</>],
  hallucinated: ["bad", "FALSE COMPLIANT", <>No helmet worn — <b>the model reported one anyway</b>: a bare-headed worker passes as compliant.</>],
  correct_none: ["good", "CLEAR", <>No helmet worn — and <b>correctly, no helmet detected</b>.</>],
};

const TOUR = [
  ["bright|visible", "baseline", 3200],
  ["dim|partial", "baseline", 4600],
  ["dim|partial", "candidate", 4600],
  ["bright|absent", "baseline", 3600],
  ["dim|partial", "candidate", 2400],
];

export default function Explorer({ data }) {
  const [cell, setCell] = useState("dim|partial");
  const [idx, setIdx] = useState(0);
  const [model, setModel] = useState("baseline");
  const [showGT, setShowGT] = useState(true);
  const [showPred, setShowPred] = useState(true);
  const [touring, setTouring] = useState(false);
  const timers = useRef([]);

  const entries = data.cells[cell] || [];
  const e = entries[idx] || entries[0];

  const stopTour = useCallback(() => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
    setTouring(false);
  }, []);

  const runTour = () => {
    if (touring) return stopTour();
    setTouring(true);
    const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
    let t = 0;
    TOUR.forEach(([k, m, d]) => {
      timers.current.push(
        setTimeout(() => {
          setCell(k);
          setIdx(0);
          setModel(m);
        }, t)
      );
      t += reduced ? 1200 : d;
    });
    timers.current.push(setTimeout(stopTour, t));
  };
  useEffect(() => stopTour, [stopTour]);

  const nextFrame = useCallback(() => {
    setIdx((v) => (v + 1) % (entries.length || 1));
  }, [entries.length]);

  useEffect(() => {
    const onKey = (ev) => {
      if (!["b", "c", "n"].includes(ev.key)) return;
      stopTour();
      if (ev.key === "b") setModel("baseline");
      if (ev.key === "c") setModel("candidate");
      if (ev.key === "n") nextFrame();
    };
    addEventListener("keydown", onKey);
    return () => removeEventListener("keydown", onKey);
  }, [nextFrame, stopTour]);

  const badCells = useMemo(() => {
    const m = {};
    for (const k of Object.keys(data.cells))
      m[k] = (data.cells[k] || []).some((x) => BAD.includes(x.story.baseline));
    return m;
  }, [data]);

  if (!e) return null;
  const [cls, word, text] = VERDICT[e.story[model]];
  const [l, h] = cell.split("|");
  const boxes = [
    ...(showGT ? e.gt.map((b) => ({ ...b, gt: true })) : []),
    ...(showPred ? e[model] : []),
  ];

  return (
    <>
      <div className="sechead reveal" id="explorer">
        <div className="kicker">01 · The reveal</div>
        <h2 className="secline">See it fail, then watch the fix land</h2>
        <p className="seclede">
          Real frames from the locked test suite, with each model's real
          detections drawn over them. Pick a condition, flip the model. Nothing
          is staged — boxes come from stored predictions at the report's own
          thresholds.
        </p>
        <div style={{ marginBottom: 20 }}>
          <button className="play" onClick={runTour} aria-pressed={touring}>
            <span className="tri" aria-hidden="true" />
            {touring ? "Stop" : "Play the story"}
          </button>
        </div>
      </div>

      <div className="stagewrap reveal">
        <div>
          <Viewer entry={e} boxes={boxes} model={model} cond={`${l.toUpperCase()} / ${h.toUpperCase()}`} />
          <div className={`verdict ${cls}`}>
            <span className="status">{word}</span>
            <p key={`${e.id}-${model}`}>{text}</p>
          </div>
        </div>

        <div className="console">
          <div className="panel">
            <h3>Condition — lighting × helmet</h3>
            <div className="matrix">
              <span />
              {HAT.map((x) => (
                <span className="head" key={x}>{x}</span>
              ))}
              {LIGHT.map((li) => (
                <Row key={li} li={li} cell={cell} badCells={badCells}
                     onPick={(k) => { stopTour(); setCell(k); setIdx(0); }} />
              ))}
            </div>
            <div className="keylist">
              <div><span className="dot" style={{ background: "var(--critical)" }} />baseline misses the helmet here</div>
              <div><span className="dot" style={{ background: "var(--good)" }} />baseline handles this cell</div>
            </div>
          </div>

          <div className="panel">
            <h3>Model under test</h3>
            <div className={`seg ${model === "candidate" ? "cand" : ""}`} role="group" aria-label="model">
              <span className="thumb" aria-hidden="true" />
              <button className={model === "baseline" ? "on" : ""} aria-pressed={model === "baseline"}
                      onClick={() => { stopTour(); setModel("baseline"); }}>Baseline</button>
              <button className={model === "candidate" ? "on" : ""} aria-pressed={model === "candidate"}
                      onClick={() => { stopTour(); setModel("candidate"); }}>Candidate</button>
            </div>
            <div className="tglrow">
              <label className="tgl"><input type="checkbox" checked={showGT} onChange={(ev) => setShowGT(ev.target.checked)} />Ground truth</label>
              <label className="tgl"><input type="checkbox" checked={showPred} onChange={(ev) => setShowPred(ev.target.checked)} />Detections</label>
              <button className="minibtn" onClick={() => { stopTour(); nextFrame(); }}>Next example</button>
            </div>
          </div>

          <div className="panel">
            <h3>Reading the overlay</h3>
            <div className="legend">
              <div><span className="sw" style={{ borderColor: "var(--accent-2)" }} />model: hard hat (with confidence)</div>
              <div><span className="sw" style={{ borderColor: "var(--axis)" }} />model: person</div>
              <div><span className="sw" style={{ borderStyle: "dashed", borderColor: "var(--ink)" }} />ground truth (simulator)</div>
            </div>
            <div className="keylist">
              <div><kbd>b</kbd> baseline &nbsp; <kbd>c</kbd> candidate &nbsp; <kbd>n</kbd> next frame</div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

function Row({ li, cell, badCells, onPick }) {
  return (
    <>
      <span className="lab">{li}</span>
      {HAT.map((h) => {
        const k = `${li}|${h}`;
        return (
          <button key={k} className={`cellbtn ${cell === k ? "on" : ""}`}
                  aria-pressed={cell === k} onClick={() => onPick(k)}>
            {h}
            <span className="dot" style={{ background: badCells[k] ? "var(--critical)" : "var(--good)" }} />
          </button>
        );
      })}
    </>
  );
}

/** Two stacked <img> layers so a frame change crossfades instead of blinking. */
function Viewer({ entry, boxes, model, cond }) {
  const [layers, setLayers] = useState([entry.img, null]);
  const [front, setFront] = useState(0);
  const [dims, setDims] = useState({ w: 640, h: 360 });
  const imgs = [useRef(null), useRef(null)];

  useEffect(() => {
    const back = 1 - front;
    setLayers((L) => {
      const n = [...L];
      n[back] = entry.img;
      return n;
    });
    const id = setTimeout(() => setFront(back), 20);
    return () => clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entry.img]);

  const onLoad = (ev) => setDims({ w: ev.target.naturalWidth, h: ev.target.naturalHeight });

  return (
    <div className="viewer">
      {layers.map((src, i) => (
        <img key={i} ref={imgs[i]} className={i === front ? "on" : ""} onLoad={onLoad}
             src={src ? `data:image/jpeg;base64,${src}` : undefined}
             alt={i === front ? "rendered warehouse frame" : ""} />
      ))}
      <svg viewBox={`0 0 ${dims.w} ${dims.h}`} preserveAspectRatio="none" aria-hidden="true">
        {boxes.map((b, i) => {
          const [x1, y1, x2, y2] = b.bbox;
          const stroke = b.gt ? "rgba(255,255,255,.95)" : b.label === "hard_hat" ? "var(--accent-2)" : "rgba(255,255,255,.45)";
          return (
            <g key={i}>
              <rect x={x1} y={y1} width={x2 - x1} height={y2 - y1} rx="3" fill="none"
                    stroke={stroke} strokeWidth="3.5" strokeDasharray={b.gt ? "9 7" : undefined} />
              {!b.gt && b.label === "hard_hat" && b.score !== undefined && (
                <text x={x1 + 2} y={Math.max(17, y1 - 8)} fontSize="16" fontWeight="600" fill={stroke}
                      fontFamily="IBM Plex Mono, monospace" paintOrder="stroke"
                      stroke="rgba(0,0,0,.55)" strokeWidth="3">
                  hard_hat {b.score}
                </text>
              )}
            </g>
          );
        })}
      </svg>
      <div className="hud">
        <div className="top">
          <span className="cam">CAM 02 · {cond}</span>
          <span>{entry.id}</span>
        </div>
        <div className="bot">
          {[["LUX", Math.round(entry.lux)], ["OCCLUSION", entry.occl == null ? "—" : entry.occl.toFixed(2)],
            ["RANGE", `${entry.distance_m} m`], ["ELEV", `${entry.elev}°`], ["MODEL", model.toUpperCase()]]
            .map(([k, v]) => (<span key={k}>{k} <b>{v}</b></span>))}
        </div>
        <span className="corner tl" /><span className="corner tr" />
        <span className="corner bl" /><span className="corner br" />
      </div>
    </div>
  );
}
