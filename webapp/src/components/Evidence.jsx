import { useState } from "react";
import { fmt, rampAt } from "../lib/format.js";

const LIGHT = ["bright", "normal", "dim"];
const HAT = ["visible", "partial", "absent"];

export default function Evidence({ data }) {
  const [tip, setTip] = useState(null);
  const show = (ev, node) =>
    setTip({ x: ev.clientX, y: ev.clientY, node });
  const hide = () => setTip(null);

  const o = data.overall;
  const det = o.detection.hard_hat;
  const cmp = data.comparison;

  return (
    <>
      <div className="sechead reveal" id="evidence">
        <div className="kicker">02 · The evidence</div>
        <h2 className="secline">One number hid two blind spots</h2>
        <p className="seclede">
          The same frames, scored by condition instead of averaged. Every rate
          carries its sample count and a 95% confidence interval; slices with
          too little evidence get no verdict at all.
        </p>
      </div>

      <div className="tiles reveal">
        <Tile k="Baseline recall (overall)" v={fmt(det.recall.value)}
              fn={`n=${det.recall.denominator} · CI ${fmt(det.recall.ci95_low,2)}–${fmt(det.recall.ci95_high,2)}`} />
        <Tile k="Weakest condition" v={fmt(data.analysis.weakest_slice?.value)} tone="crit"
              fn={data.analysis.weakest_slice?.slice} />
        <Tile k="Dangerous-miss rate" v={fmt(o.safety.dangerous_miss_rate.value)}
              fn={`bare head passed as compliant · n=${o.safety.dangerous_miss_rate.denominator}`} />
        <Tile k="False-alarm rate" v={fmt(o.safety.false_alarm_rate.value)}
              fn={`compliant worker flagged · n=${o.safety.false_alarm_rate.denominator}`} />
      </div>

      <div className="cards reveal">
        <div className="card">
          <h3>Miss-rate heatmap — lighting × helmet state</h3>
          <p className="note">
            Darker cells miss more hard hats. Labels show recall and sample
            count; a dashed outline means the cell is below the sample bar and
            receives no verdict.
          </p>
          <Heatmap data={data} onHover={show} onLeave={hide} />
        </div>

        <div className="card">
          <h3>Weakest slices, ranked</h3>
          <p className="note">Worst first by the lower bound of the 95% interval. Whiskers show the interval.</p>
          <Ranked findings={data.analysis.findings.slice(0, 10)} onHover={show} onLeave={hide} />
        </div>

        {cmp && (
          <div className="card">
            <h3>Before → after, on the identical locked suite</h3>
            <p className="note">
              Baseline → candidate per condition slice. Significant changes only
              (two-proportion z-test, 95%); regressions would appear in red with
              equal prominence — this run had {cmp.regressed.length}.
            </p>
            <div className="chartlegend">
              <span><span className="swd" style={{ background: "var(--s250)" }} />baseline</span>
              <span><span className="swd" style={{ background: "var(--s550)" }} />candidate</span>
            </div>
            <Dumbbells rows={[...cmp.regressed, ...cmp.improved.slice(0, 9)]} onHover={show} onLeave={hide} />
          </div>
        )}

        {data.arms?.length > 0 && (
          <div className="card">
            <h3>Is it targeting, or just more data?</h3>
            <p className="note">
              Recall on the weakest slice. Arms B and C trained on identical
              volume — only where the extra frames were aimed differs. The
              honest reading: coverage does most of the work, and targeting's
              edge here sits below significance, so we report it as such.
            </p>
            <Arms arms={data.arms} onHover={show} onLeave={hide} />
          </div>
        )}
      </div>

      {tip && (
        <div className="tooltip" style={{ left: Math.min(tip.x + 14, innerWidth - 300), top: tip.y + 14 }}>
          {tip.node}
        </div>
      )}
    </>
  );
}

const Tile = ({ k, v, fn, tone }) => (
  <div className="tile">
    <div className="k">{k}</div>
    <div className={`v ${tone || ""}`}>{v}</div>
    {fn && <div className="fn">{fn}</div>}
  </div>
);

function Heatmap({ data, onHover, onLeave }) {
  const all = [...data.analysis.findings, ...data.analysis.underpowered_slices];
  const cell = (li, h) =>
    all.find((f) => {
      const c = f.constraints || {};
      return Object.keys(c).length === 2 && c.lighting === li && c.helmet_state === h;
    });
  const CW = 150, CH = 66, LX = 84, TY = 28;
  return (
    <svg viewBox={`0 0 ${LX + HAT.length * CW + 8} ${TY + LIGHT.length * CH + 6}`} role="img"
         aria-label="hard hat miss rate by lighting and helmet state">
      {HAT.map((h, j) => (
        <text key={h} x={LX + j * CW + CW / 2} y={TY - 10} textAnchor="middle" fill="var(--muted)" fontSize="12">{h}</text>
      ))}
      {LIGHT.map((li, i) => (
        <g key={li}>
          <text x={LX - 8} y={TY + i * CH + CH / 2 + 4} textAnchor="end" fill="var(--muted)" fontSize="12">{li}</text>
          {HAT.map((h, j) => {
            const f = cell(li, h);
            const miss = f && f.value != null ? 1 - f.value : null;
            const fill = miss == null ? "var(--grid)" : rampAt(miss);
            const dark = miss != null && miss > 0.45;
            const under = f ? f.underpowered : true;
            return (
              <g key={h}
                 onMouseMove={(ev) => onHover(ev, f ? (
                   <><b>{li} + {h}</b><br />recall {fmt(f.value)} · miss {f.value != null ? fmt(1 - f.value) : "n/a"}<br />
                   n={f.denominator} · CI {fmt(f.ci95_low, 2)}–{fmt(f.ci95_high, 2)}
                   {f.underpowered && <><br /><i>below sample bar — no verdict</i></>}</>
                 ) : "no data")}
                 onMouseLeave={onLeave}>
                <rect x={LX + j * CW + 1} y={TY + i * CH + 1} width={CW - 2} height={CH - 2} rx="7"
                      fill={fill} stroke={under ? "var(--muted)" : "none"} strokeDasharray={under ? "4 3" : undefined} />
                <text x={LX + j * CW + CW / 2} y={TY + i * CH + CH / 2 - 2} textAnchor="middle"
                      fontSize="16" fontWeight="600" fill={dark ? "#fff" : "var(--ink)"}>
                  {f && f.value != null ? fmt(f.value, 2) : "n/a"}
                </text>
                <text x={LX + j * CW + CW / 2} y={TY + i * CH + CH / 2 + 16} textAnchor="middle" fontSize="11"
                      fill={dark ? "rgba(255,255,255,.85)" : "var(--ink2)"}>
                  n={f ? f.denominator : 0}{under ? " · no verdict" : ""}
                </text>
              </g>
            );
          })}
        </g>
      ))}
    </svg>
  );
}

function Ranked({ findings, onHover, onLeave }) {
  const BW = 560, RH = 27, LW = 300;
  const x = (v) => LW + v * BW;
  return (
    <svg viewBox={`0 0 ${LW + BW + 76} ${findings.length * RH + 16}`} role="img" aria-label="weakest slices ranked">
      {findings.map((f, i) => {
        const y = i * RH + 12;
        return (
          <g key={f.slice} onMouseMove={(ev) => onHover(ev, (
              <><b>{f.slice}</b><br />recall {fmt(f.value)} · n={f.denominator}<br />CI {fmt(f.ci95_low, 2)}–{fmt(f.ci95_high, 2)}</>
            ))} onMouseLeave={onLeave}>
            <text x={LW - 10} y={y + 9} textAnchor="end" fontSize="12" fill="var(--ink2)">{f.slice}</text>
            <line x1={x(0)} y1={y + 5} x2={x(1)} y2={y + 5} stroke="var(--grid)" />
            <line x1={x(f.ci95_low)} y1={y + 5} x2={x(f.ci95_high)} y2={y + 5} stroke="var(--axis)" strokeWidth="2" />
            <rect x={x(0)} y={y} width={Math.max(2, f.value * BW)} height="10" rx="4" fill="var(--s400)" />
            <text x={x(f.value) + 7} y={y + 9} fontSize="12" fill="var(--ink)">
              {fmt(f.value)}<tspan fill="var(--muted)"> n={f.denominator}</tspan>
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function Dumbbells({ rows, onHover, onLeave }) {
  const BW = 480, RH = 30, LW = 320;
  const x = (v) => LW + v * BW;
  return (
    <svg viewBox={`0 0 ${LW + BW + 84} ${rows.length * RH + 26}`} role="img" aria-label="before after by slice">
      {[0, 0.25, 0.5, 0.75, 1].map((t) => (
        <g key={t}>
          <line x1={x(t)} y1="8" x2={x(t)} y2={rows.length * RH + 8} stroke="var(--grid)" />
          <text x={x(t)} y={rows.length * RH + 22} textAnchor="middle" fontSize="11" fill="var(--muted)">{t}</text>
        </g>
      ))}
      {rows.map((r, i) => {
        const y = i * RH + 18;
        const col = r.classification === "regressed" ? "var(--critical)" : "var(--s550)";
        return (
          <g key={r.slice} onMouseMove={(ev) => onHover(ev, (
              <><b>{r.slice}</b><br />baseline {fmt(r.baseline.value)} (n={r.baseline.denominator})<br />
              candidate {fmt(r.candidate.value)} (n={r.candidate.denominator})<br />
              Δ {r.delta > 0 ? "+" : ""}{fmt(r.delta)} · {r.classification}</>
            ))} onMouseLeave={onLeave}>
            <text x={LW - 10} y={y + 4} textAnchor="end" fontSize="12" fill="var(--ink2)">{r.slice}</text>
            <line x1={x(r.baseline.value)} y1={y} x2={x(r.candidate.value)} y2={y} stroke="var(--axis)" strokeWidth="2" />
            <circle cx={x(r.baseline.value)} cy={y} r="6" fill="var(--s250)" stroke="var(--surface)" strokeWidth="2" />
            <circle cx={x(r.candidate.value)} cy={y} r="6" fill={col} stroke="var(--surface)" strokeWidth="2" />
            <text x={x(Math.max(r.baseline.value, r.candidate.value)) + 10} y={y + 4} fontSize="12" fill="var(--ink)">
              {r.delta > 0 ? "+" : ""}{fmt(r.delta, 2)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function Arms({ arms, onHover, onLeave }) {
  const BW = 520, BH = 44, LW = 300;
  const x = (v) => LW + v * BW;
  const shades = ["var(--s250)", "var(--s400)", "var(--s550)", "var(--s700)"];
  return (
    <svg viewBox={`0 0 ${LW + BW + 76} ${arms.length * BH + 28}`} role="img" aria-label="volume matched arms">
      {[0, 0.25, 0.5, 0.75, 1].map((t) => (
        <g key={t}>
          <line x1={x(t)} y1="6" x2={x(t)} y2={arms.length * BH + 6} stroke="var(--grid)" />
          <text x={x(t)} y={arms.length * BH + 24} textAnchor="middle" fontSize="11" fill="var(--muted)">{t}</text>
        </g>
      ))}
      {arms.map((m, i) => {
        const y = i * BH + 12;
        return (
          <g key={m.key} onMouseMove={(ev) => onHover(ev, (
              <><b>{m.key} — {m.label}</b><br />weakest-slice recall {fmt(m.target_value)} (n={m.target_n})<br />
              CI {m.target_ci ? `${fmt(m.target_ci[0], 2)}–${fmt(m.target_ci[1], 2)}` : "n/a"}<br />
              overall {fmt(m.overall)}</>
            ))} onMouseLeave={onLeave}>
            <text x={LW - 10} y={y + 13} textAnchor="end" fontSize="12" fill="var(--ink2)">{m.key} · {m.label}</text>
            <rect x={x(0)} y={y} width={Math.max(2, (m.target_value || 0) * BW)} height="18" rx="4" fill={shades[i % 4]} />
            {m.target_ci && (
              <line x1={x(m.target_ci[0])} y1={y + 9} x2={x(m.target_ci[1])} y2={y + 9}
                    stroke="var(--ink)" strokeOpacity=".55" strokeWidth="2" />
            )}
            <text x={x(m.target_value || 0) + 8} y={y + 13} fontSize="12.5" fontWeight="600" fill="var(--ink)">
              {fmt(m.target_value)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
