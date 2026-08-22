import { fmt } from "../lib/format.js";

export default function Report({ data }) {
  const w = data.analysis.weakest_slice;
  const o = data.comparison?.overall;
  const m = data.models;

  return (
    <>
      <div className="sechead reveal" id="report">
        <div className="kicker">03 · The report</div>
        <h2 className="secline">What we claim, and what we refuse to claim</h2>
        <p className="seclede">
          Every run ships a versioned document: the verdict, the limitations,
          and the identity needed to reproduce any frame in it.
        </p>
      </div>

      <div className="reportwrap reveal">
        <p className="bigline">
          {w && o ? (
            <>
              The suite exposed <span className="mono">{w.slice}</span> at recall{" "}
              <span className="mono">{fmt(w.value, 2)}</span>; after targeted data,{" "}
              <span className="mono">{fmt(o.baseline.value, 2)} → {fmt(o.candidate.value, 2)}</span>{" "}
              overall with {data.comparison.regressed.length} regressions.
            </>
          ) : (
            "Failure-discovery run — no candidate evaluated."
          )}
        </p>

        {data.summary ? (
          <div className="summary">
            <div className="who">Executive summary — generated from measured artifacts, number-checked</div>
            {data.summary.split(/\n\n+/).map((p, i) => <p key={i}>{p}</p>)}
          </div>
        ) : (
          <div className="summary pending">
            <div className="who">Executive summary</div>
            <p>
              Not yet generated for this run. Produce it with the team's
              OpenRouter key —{" "}
              <span className="mono">python3 -m crashlab.narrate --report … --out …</span>{" "}
              — then rebuild this page. The prose is checked against the run's
              fact sheet and rejected if it introduces a number the run did not
              measure.
            </p>
          </div>
        )}

        <div className="card" style={{ marginTop: 16 }}>
          <h3>Limitations — what this run does not claim</h3>
          <ul className="limits">
            {data.limitations.map((l, i) => <li key={i}>{l}</li>)}
          </ul>
        </div>

        <div className="card">
          <h3>Not tested in this suite</h3>
          <ul className="limits">
            {data.untested.map((l, i) => <li key={i}>{l}</li>)}
          </ul>
        </div>

        <div className="card">
          <h3>Reproduction identity</h3>
          <dl className="idgrid">
            <dt>scenario suite</dt><dd>{data.suite}</dd>
            <dt>test manifest</dt><dd>{data.manifest} · {data.frames} frames</dd>
            <dt>manifest fingerprint</dt><dd>{data.fingerprint}</dd>
            <dt>baseline model</dt><dd>{m.baseline.ref} · {m.baseline.fingerprint}</dd>
            {m.candidate && (<><dt>candidate model</dt><dd>{m.candidate.ref} · {m.candidate.fingerprint}</dd></>)}
            <dt>thresholds</dt>
            <dd>IoU {data.config.iou_threshold} · confidence {data.config.score_threshold} · min n {data.config.min_samples_for_finding}</dd>
            <dt>generated</dt><dd>{data.generated_at}</dd>
          </dl>
          <p className="note" style={{ marginTop: 12, marginBottom: 0 }}>
            Seeds derive by hash from (suite, scenario id), so any frame is
            regenerable on any machine.
          </p>
        </div>
      </div>
    </>
  );
}
