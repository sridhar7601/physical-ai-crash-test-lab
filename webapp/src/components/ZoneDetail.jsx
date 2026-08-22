const THREAT_LABEL = { high: "HIGH THREAT", medium: "MEDIUM", low: "LOW RISK" };

export default function ZoneDetail({ zone, onClose }) {
  if (!zone) return null;

  return (
    <div className="detail-overlay" onClick={onClose} role="presentation">
      <aside
        className="detail-panel"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label={`Zone ${zone.id} details`}
      >
        <button type="button" className="detail-close" onClick={onClose} aria-label="Close">
          ×
        </button>
        <div className="kicker">Zone detail</div>
        <h2 className="detail-title">
          <span className="mono">{zone.id}</span> — {zone.name}
        </h2>
        <div className={`detail-badge ${zone.threat}`}>{THREAT_LABEL[zone.threat]}</div>
        <div className="detail-stats">
          <div><span className="k">Threat score</span><span className="v mono">{zone.threat_score.toFixed(2)}</span></div>
          <div><span className="k">Luminosity</span><span className="v mono">{zone.lux} lux ({zone.lux_bucket})</span></div>
          <div><span className="k">Occlusion</span><span className="v">{zone.occlusion}</span></div>
          <div><span className="k">Cameras</span><span className="v">{zone.covered_by.length ? zone.covered_by.join(", ") : "None"}</span></div>
        </div>
        <p className="detail-reason">{zone.reason}</p>
        <h3>Recommended actions</h3>
        <ul className="detail-actions">
          {zone.actions.map((a) => (
            <li key={a}>{a}</li>
          ))}
        </ul>
      </aside>
    </div>
  );
}
