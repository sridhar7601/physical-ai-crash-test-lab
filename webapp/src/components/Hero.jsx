import { useEffect, useState } from "react";

/** Rotates the two exemplar frames: the easy case, then the blind spot. */
export default function Hero({ frames, headline }) {
  const shots = [
    { key: "bright|visible", tag: "CAM 02 · BRIGHT / VISIBLE" },
    { key: "dim|partial", tag: "CAM 02 · DIM / PARTIAL" },
  ]
    .map((s) => ({ ...s, img: frames.cells[s.key]?.[0]?.img }))
    .filter((s) => s.img);
  const [i, setI] = useState(0);
  useEffect(() => {
    if (shots.length < 2) return;
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const t = setInterval(() => setI((v) => (v + 1) % shots.length), 4200);
    return () => clearInterval(t);
  }, [shots.length]);

  return (
    <section className="hero" id="top">
      <div>
        <div className="kicker">Physical AI · NVIDIA Omniverse</div>
        <h1>
          The helmet detector passed at <span className="mono">{headline.easy}</span>.
          <br />
          In the dark it was <span className="mono bad">{headline.weak}</span>.
        </h1>
        <p className="sub">
          A crash-test lab for AI vision. It finds the exact conditions where a
          safety camera goes blind, generates simulation data aimed at that blind
          spot, and proves the fix on an untouched, fingerprint-locked test suite.
        </p>
        <div className="cta">
          <a className="btn primary" href="#explorer">See it fail, then fix it</a>
          <a className="btn" href="#evidence">Read the evidence</a>
        </div>
        <div className="stats">
          {headline.stats.map(([n, k]) => (
            <div className="stat" key={k}>
              <div className="n">{n}</div>
              <div className="k">{k}</div>
            </div>
          ))}
        </div>
      </div>
      <div className="heroshot">
        {shots.map((s, j) => (
          <img
            key={s.key}
            className={j === i ? "on" : ""}
            src={`data:image/jpeg;base64,${s.img}`}
            alt={j === 0 ? "brightly lit warehouse frame" : "dim frame, helmet occluded"}
          />
        ))}
        <span className="tag mono">
          <i aria-hidden="true" />
          {shots[i]?.tag}
        </span>
      </div>
    </section>
  );
}
