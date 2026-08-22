const LINKS = [
  ["explorer", "Explorer"],
  ["evidence", "Evidence"],
  ["report", "Report"],
];

export default function Nav({ active }) {
  return (
    <nav className="nav">
      <a className="wordmark" href="#top" style={{ textDecoration: "none", padding: 0 }}>
        <span className="sq" aria-hidden="true" />
        Crash-Test Lab
      </a>
      <div className="links">
        {LINKS.map(([id, label]) => (
          <a key={id} href={`#${id}`} className={active === id ? "on" : ""}>
            {label}
          </a>
        ))}
      </div>
    </nav>
  );
}
