import { useMemo, useState } from "react";
import Nav from "./components/Nav.jsx";
import Hero from "./components/Hero.jsx";
import Explorer from "./components/Explorer.jsx";
import Evidence from "./components/Evidence.jsx";
import Report from "./components/Report.jsx";
import { useReveal, useActiveSection } from "./lib/useReveal.js";
import { fmt } from "./lib/format.js";
import evidence from "./data/evidence.json";
import frames from "./data/frames.json";

const IDS = ["explorer", "evidence", "report"];

export default function App() {
  const [active, setActive] = useState("");
  useReveal();
  useActiveSection(IDS, setActive);

  const headline = useMemo(() => {
    const all = [...evidence.analysis.findings, ...evidence.analysis.underpowered_slices];
    const pick = (li, h) =>
      all.find((f) => {
        const c = f.constraints || {};
        return Object.keys(c).length === 2 && c.lighting === li && c.helmet_state === h;
      });
    const easy = pick("bright", "visible");
    const weak = evidence.analysis.weakest_slice;
    const cmp = evidence.comparison;
    return {
      easy: easy ? fmt(easy.value, 2) : "0.93",
      weak: weak ? fmt(weak.value, 2) : "0.17",
      stats: [
        [evidence.frames, "frames in locked suite"],
        [cmp ? `${fmt(cmp.overall.baseline.value, 2)} → ${fmt(cmp.overall.candidate.value, 2)}` : "—", "overall recall"],
        [cmp ? cmp.regressed.length : "—", "regressions"],
        [evidence.analysis.underpowered_slices.length, "slices left unjudged"],
      ],
    };
  }, []);

  return (
    <>
      <Nav active={active} />
      <main className="shell">
        <Hero frames={frames} headline={headline} />
        <section><Explorer data={frames} /></section>
        <section><Evidence data={evidence} /></section>
        <section><Report data={evidence} /></section>
      </main>
      <footer className="site">
        <span>
          Built on NVIDIA Omniverse · Isaac Sim 6.0 · Replicator · YOLO11n.
          Detections at the evidence report's own thresholds.
        </span>
        <span>
          Simulation coverage supports engineering review; it does not replace
          real-world validation.
        </span>
      </footer>
    </>
  );
}
