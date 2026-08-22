import { useMemo, useState } from "react";
import Nav from "./components/Nav.jsx";
import Hero from "./components/Hero.jsx";
import FloorMap from "./components/FloorMap.jsx";
import CameraGuide from "./components/CameraGuide.jsx";
import ThreatBoard from "./components/ThreatBoard.jsx";
import ZoneDetail from "./components/ZoneDetail.jsx";
import { useReveal, useActiveSection } from "./lib/useReveal.js";
import sitePlan from "./data/site_plan.json";

const IDS = ["map", "cameras", "threats"];

export default function App() {
  const [active, setActive] = useState("");
  const [selectedZone, setSelectedZone] = useState(null);
  const [view, setView] = useState("threat");
  useReveal();
  useActiveSection(IDS, setActive);

  const summary = sitePlan.summary;
  const highThreat = useMemo(
    () => sitePlan.zones.filter((z) => z.threat === "high"),
    []
  );

  return (
    <>
      <Nav active={active} />
      <main className="shell">
        <Hero summary={summary} highThreat={highThreat.length} />
        <section id="map" className="sechead">
          <FloorMap
            data={sitePlan}
            view={view}
            onViewChange={setView}
            selectedId={selectedZone?.id}
            onSelect={setSelectedZone}
          />
        </section>
        <section id="cameras" className="sechead">
          <CameraGuide cameras={sitePlan.cameras} zones={sitePlan.zones} />
        </section>
        <section id="threats" className="sechead">
          <ThreatBoard zones={sitePlan.zones} onSelect={setSelectedZone} />
        </section>
      </main>
      <ZoneDetail zone={selectedZone} onClose={() => setSelectedZone(null)} />
      <footer className="site">
        <span>
          Built on NVIDIA Omniverse · Isaac Sim · Physical AI zone modelling.
        </span>
        <span>{sitePlan.disclaimer}</span>
      </footer>
    </>
  );
}
