const THREAT_COLORS = { high: "var(--critical)", medium: "var(--hazard)", low: "var(--good)" };

export default function Hero({ summary, highThreat }) {
  return (
    <section className="hero" id="top">
      <div>
        <div className="kicker">Physical AI · NVIDIA Omniverse</div>
        <h1>
          Place cameras right the first time.
          <br />
          Know which zones are <span className="mono bad">high threat</span> before you mount.
        </h1>
        <p className="sub">
          AI-guided site survey for warehouse safety cameras. Tells installers where
          to mount at eye level, and tells floor managers which aisles need lighting
          or extra coverage — derived from simulation-measured blind spots.
        </p>
        <div className="cta">
          <a className="btn primary" href="#cameras">Camera placement guide</a>
          <a className="btn hz" href="#threats">Floor manager alerts</a>
        </div>
        <div className="stats">
          <div className="stat">
            <div className="n">{summary.total_zones}</div>
            <div className="k">zones surveyed</div>
          </div>
          <div className="stat">
            <div className="n" style={{ color: THREAT_COLORS.high }}>{highThreat}</div>
            <div className="k">high-threat areas</div>
          </div>
          <div className="stat">
            <div className="n">{summary.cameras_recommended}</div>
            <div className="k">cameras recommended</div>
          </div>
          <div className="stat">
            <div className="n">{summary.zones_needing_lighting}</div>
            <div className="k">zones need lighting</div>
          </div>
        </div>
      </div>
      <div className="heroshot map-preview" aria-hidden="true">
        <svg viewBox="-12 -4 28 24" className="hero-svg">
          {["A", "B", "C", "D", "E", "F"].map((col, ci) =>
            [0, 1, 2, 3].map((row) => {
              const threat = row >= 3 && (ci === 0 || ci === 5) ? "high" : row >= 2 ? "medium" : "low";
              return (
                <rect
                  key={`${col}${row + 1}`}
                  x={-10 + ci * 4}
                  y={-2 + row * 5}
                  width={3.8}
                  height={4.8}
                  rx={0.3}
                  fill={THREAT_COLORS[threat]}
                  opacity={threat === "high" ? 0.55 : threat === "medium" ? 0.35 : 0.2}
                  stroke="var(--border)"
                  strokeWidth={0.08}
                />
              );
            })
          )}
          <circle cx={-6} cy={5.5} r={0.35} fill="var(--accent)" />
          <circle cx={2} cy={5.5} r={0.35} fill="var(--accent)" />
          <circle cx={-6} cy={15.5} r={0.35} fill="var(--accent)" />
          <text x={-11} y={-2.5} fill="var(--muted)" fontSize="1.2" fontFamily="IBM Plex Mono">WINDOW WALL</text>
        </svg>
        <div className="tag">
          <i /> SIMREADY WAREHOUSE · THREAT OVERLAY
        </div>
      </div>
    </section>
  );
}
