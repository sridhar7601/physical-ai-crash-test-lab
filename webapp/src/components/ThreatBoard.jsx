const THREAT_LABEL = { high: "HIGH", medium: "MEDIUM", low: "LOW" };

export default function ThreatBoard({ zones, onSelect }) {
  const ranked = [...zones].sort((a, b) => b.threat_score - a.threat_score);
  const high = ranked.filter((z) => z.threat === "high");
  const medium = ranked.filter((z) => z.threat === "medium");

  return (
    <div className="reveal">
      <div className="kicker">For floor managers</div>
      <h2 className="secline">Threat zones — ranked by risk</h2>
      <p className="seclede">
        Areas where safety cameras may go blind: dim lighting, shelf occlusion, or
        no eye-level coverage. Each card includes recommended actions.
      </p>
      <div className="tiles">
        <div className="tile">
          <div className="k">High threat</div>
          <div className="v crit">{high.length}</div>
          <div className="fn">zones need immediate attention</div>
        </div>
        <div className="tile">
          <div className="k">Medium threat</div>
          <div className="v" style={{ color: "var(--hazard)" }}>{medium.length}</div>
          <div className="fn">monitor and plan remediation</div>
        </div>
        <div className="tile">
          <div className="k">Dim zones</div>
          <div className="v">{zones.filter((z) => z.lux_bucket === "dim").length}</div>
          <div className="fn">below 80 lux threshold</div>
        </div>
      </div>
      <div className="threat-list">
        {ranked.map((z) => (
          <button
            type="button"
            key={z.id}
            className={`threat-row ${z.threat}`}
            onClick={() => onSelect(z)}
          >
            <div className="threat-row-head">
              <span className="zone-id mono">{z.id}</span>
              <span className="zone-name">{z.name}</span>
              <span className={`threat-badge ${z.threat}`}>
                {THREAT_LABEL[z.threat]}
              </span>
              <span className="threat-score mono">{z.threat_score.toFixed(2)}</span>
            </div>
            <p className="threat-reason">{z.reason}</p>
            <ul className="threat-actions">
              {z.actions.map((a) => (
                <li key={a}>{a}</li>
              ))}
            </ul>
            <div className="threat-meta mono">
              <span>{z.lux} lux</span>
              <span>{z.occlusion} occlusion</span>
              <span>{z.covered_by.length ? `covered by ${z.covered_by.join(", ")}` : "uncovered"}</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
