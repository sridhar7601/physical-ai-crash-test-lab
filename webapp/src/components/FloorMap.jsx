const THREAT_FILL = {
  high: "color-mix(in srgb, var(--critical) 55%, var(--panel))",
  medium: "color-mix(in srgb, var(--hazard) 40%, var(--panel))",
  low: "color-mix(in srgb, var(--good) 25%, var(--panel))",
};
const LUX_FILL = {
  bright: "color-mix(in srgb, var(--good) 35%, var(--panel))",
  normal: "color-mix(in srgb, var(--hazard) 30%, var(--panel))",
  dim: "color-mix(in srgb, var(--critical) 40%, var(--panel))",
};

function mapBounds(zones) {
  const xs = zones.map((z) => z.x);
  const ys = zones.map((z) => z.y);
  const x2 = zones.map((z) => z.x + z.width);
  const y2 = zones.map((z) => z.y + z.height);
  const pad = 1.5;
  return {
    minX: Math.min(...xs) - pad,
    minY: Math.min(...ys) - pad,
    maxX: Math.max(...x2) + pad,
    maxY: Math.max(...y2) + pad,
  };
}

export default function FloorMap({ data, view, onViewChange, selectedId, onSelect }) {
  const { zones, cameras } = data;
  const bounds = mapBounds(zones);
  const w = bounds.maxX - bounds.minX;
  const h = bounds.maxY - bounds.minY;

  const toSvg = (x, y) => [
    ((x - bounds.minX) / w) * 100,
    ((y - bounds.minY) / h) * 100,
  ];

  return (
    <div className="reveal">
      <div className="kicker">Interactive site map</div>
      <h2 className="secline">Warehouse floor — click a zone for details</h2>
      <p className="seclede">
        Toggle between threat risk and luminosity overlays. Green = safe, amber =
        moderate, red = high threat or dim lighting.
      </p>
      <div className="map-toolbar">
        <div className="seg map-seg">
          <div className={`thumb ${view === "lux" ? "cand" : ""}`} />
          <button type="button" className={view === "threat" ? "on" : ""} onClick={() => onViewChange("threat")}>
            Threat
          </button>
          <button type="button" className={view === "lux" ? "on" : ""} onClick={() => onViewChange("lux")}>
            Luminosity
          </button>
        </div>
      </div>
      <div className="map-wrap card">
        <svg viewBox="0 0 100 70" className="floor-svg" role="img" aria-label="warehouse floor map">
          <rect x={0} y={0} width={100} height={70} fill="var(--panel)" rx={1} />
          {zones.map((z) => {
            const [sx, sy] = toSvg(z.x, z.y);
            const [ex] = toSvg(z.x + z.width, z.y);
            const [, ey] = toSvg(z.x, z.y + z.height);
            const fill = view === "lux" ? LUX_FILL[z.lux_bucket] : THREAT_FILL[z.threat];
            return (
              <g key={z.id}>
                <rect
                  x={sx}
                  y={sy}
                  width={ex - sx - 0.3}
                  height={ey - sy - 0.3}
                  rx={0.5}
                  fill={fill}
                  stroke={selectedId === z.id ? "var(--accent)" : "var(--border)"}
                  strokeWidth={selectedId === z.id ? 0.4 : 0.15}
                  className="zone-rect"
                  onClick={() => onSelect(z)}
                  style={{ cursor: "pointer" }}
                />
                <text x={sx + (ex - sx) / 2} y={sy + (ey - sy) / 2} textAnchor="middle"
                  dominantBaseline="middle" fontSize="2.2" fill="var(--ink)" fontWeight="600">
                  {z.id}
                </text>
              </g>
            );
          })}
          {cameras.filter((c) => !c.avoid).map((c) => {
            const [cx, cy] = toSvg(c.x, c.y);
            return (
              <g key={c.id}>
                <circle cx={cx} cy={cy} r={1.2} fill="var(--accent)" stroke="#fff" strokeWidth={0.2} />
                <text x={cx} y={cy - 1.8} textAnchor="middle" fontSize="1.4" fill="var(--accent)" fontFamily="IBM Plex Mono">
                  {c.id}
                </text>
              </g>
            );
          })}
          {cameras.filter((c) => c.avoid).map((c) => {
            const [cx, cy] = toSvg(c.x, c.y);
            return (
              <g key={c.id}>
                <line x1={cx - 1} y1={cy - 1} x2={cx + 1} y2={cy + 1} stroke="var(--critical)" strokeWidth={0.3} />
                <line x1={cx + 1} y1={cy - 1} x2={cx - 1} y2={cy + 1} stroke="var(--critical)" strokeWidth={0.3} />
              </g>
            );
          })}
        </svg>
        <div className="map-legend">
          {view === "threat" ? (
            <>
              <span><i className="ldot high" /> High threat</span>
              <span><i className="ldot med" /> Medium</span>
              <span><i className="ldot low" /> Low</span>
              <span><i className="ldot cam" /> Camera mount</span>
              <span><i className="ldot avoid" /> Avoid placement</span>
            </>
          ) : (
            <>
              <span><i className="ldot low" /> Bright (600+ lux)</span>
              <span><i className="ldot med" /> Normal (200–600)</span>
              <span><i className="ldot high" /> Dim (10–80)</span>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
