export default function CameraGuide({ cameras, zones }) {
  const mounts = cameras.filter((c) => !c.avoid);
  const avoid = cameras.filter((c) => c.avoid);

  return (
    <div className="reveal">
      <div className="kicker">For installers</div>
      <h2 className="secline">Where to mount cameras</h2>
      <p className="seclede">
        Eye-level mounts (1.8 m, 0–10° elevation) maximise PPE detection. High-angle
        mounts in dim zones drop recall to ~24%.
      </p>
      <div className="cam-grid">
        {mounts.map((cam) => (
          <div className="card cam-card" key={cam.id}>
            <div className="cam-head">
              <span className="cam-id mono">{cam.id}</span>
              <span className="cam-pos mono">
                ({cam.x} m, {cam.y} m)
              </span>
            </div>
            <div className="cam-specs">
              <div><span className="k">Height</span><span className="v mono">{cam.height_m} m</span></div>
              <div><span className="k">Angle</span><span className="v mono">{cam.angle_deg}°</span></div>
              <div><span className="k">Covers</span><span className="v">{cam.covers.length} zones</span></div>
            </div>
            <p className="cam-note">{cam.note}</p>
            <div className="cam-covers">
              {cam.covers.map((zid) => {
                const z = zones.find((zz) => zz.id === zid);
                return (
                  <span key={zid} className={`cover-chip ${z?.threat || ""}`}>
                    {zid}
                  </span>
                );
              })}
            </div>
          </div>
        ))}
      </div>
      {avoid.length > 0 && (
        <div className="avoid-box">
          <h3>Avoid these placements</h3>
          {avoid.map((cam) => (
            <div key={cam.id} className="avoid-item">
              <span className="mono bad">{cam.id}</span>
              <span>{cam.note}</span>
              <span className="mono muted">
                {cam.height_m} m · {cam.angle_deg}°
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
