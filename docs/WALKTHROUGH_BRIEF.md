# Walkthrough Brief — Physical AI Crash-Test Lab

A design brief for a 2–4 minute video walkthrough (Innovation Sprint 2026
submission). Everything in here is real and already built; the video's job is
to sequence it, not to invent anything.

## One-liner

A crash-test lab for AI vision: it finds the exact conditions where a safety
camera goes blind, generates simulation data aimed at that blind spot, and
proves the fix on an untouched, fingerprint-locked test suite.

## Audience and tone

Hackathon judges (engineering + business). Tone: calm, precise, industrial —
an instrument, not an ad. Confidence comes from measured numbers and honest
caveats, never hype words ("revolutionary", "game-changing" are banned).

## Visual identity (already established — reuse, don't reinvent)

- Type: IBM Plex Sans (UI/headings), IBM Plex Mono (identifiers, numbers, HUD)
- Dark-first "control room" ground: page #0e0f0e, surface #161716,
  ink #f4f4f1, secondary #b9b9b2
- Accent (detections, actions): #3987e5
- Signature motif: safety-amber hazard stripe #eda100, 45°, used sparingly
  (top band, section dividers)
- Status: critical #e66767, good #0ca30c — always paired with a text label,
  never color alone
- Camera-HUD styling on imagery: mono OSD text, corner brackets, red-dot CAM chip

## Assets on hand

- Live interactive pages (screen-record these):
  - Crash-Test Explorer: https://claude.ai/code/artifact/5ae7579c-15b5-4a1c-8400-8a7ac6736701
  - Evidence dashboard: https://claude.ai/code/artifact/c9a1e6c4-fb33-4c95-a2a9-4cf1a2f546fd
- Stills in repo `docs/images/`: bright warehouse frame, dim occluded frame,
  high-angle frame (SimReady warehouse, worker wearing the labelled hard hat)
- Repo for code shots: https://github.com/sridhar7601/physical-ai-crash-test-lab
- Terminal footage possible on the VM (Isaac Sim renders, training runs)

## The numbers (only use these — they are measured)

- Test suite: 864 frames, 54 condition cells, fingerprint aae5a75f…
- Baseline (trained on easy footage): overall recall 0.681
  - bright + visible: 0.934
  - dim + partially occluded: 0.165  ← the blind spot
  - high camera + occluded: 0.238    ← second blind spot, found unaided
- After 600 targeted frames: dim+occluded 0.165 → 0.949; 26 slices improved,
  0 regressed; dangerous-miss rate 0.7%
- Volume-matched control (identical 385-image training sets):
  bulk-coverage arm 0.911 vs targeted arm 0.949 on the blind spot — a
  consistent edge, honestly reported as below statistical significance
- 2,328 frames rendered on an NVIDIA L40S; YOLO11n; Isaac Sim 6.0 + Replicator

## Storyboard (target 3:00)

1. **0:00–0:20 — The trap.** Dark title card, hazard stripe, one line:
   "A helmet detector passed testing at 93%." Beat. "It was 17% in the dark."
   Show the bright frame, then cut to the dim occluded frame.
2. **0:20–0:50 — Why simulation.** The three stills pan slowly with HUD
   overlays; VO: staging dangerous warehouse conditions is unsafe and slow, so
   we built the warehouse in NVIDIA Isaac Sim — every frame ships with exact
   ground truth, including a measured occlusion fraction on a genuinely worn
   hard hat.
3. **0:50–1:40 — The reveal (screen capture: Explorer).** Cursor clicks
   bright/visible → DETECTED. Clicks dim/partial → "NO DETECTION" verdict
   panel. Press `c` → the box snaps on with its confidence. This flip is the
   thesis; let it breathe, repeat it once.
4. **1:40–2:20 — The evidence (screen capture: dashboard).** Failure-map
   heatmap (dark cell = blind spot), then Comparison tab: dumbbells, then the
   three-bar volume-matched control. VO states the honest finding: coverage
   does most of the work; targeting adds a real but modest edge — and the
   instrument says so instead of overclaiming.
5. **2:20–2:50 — What this is for.** One screen of the closed loop diagram
   (declare → render → score by condition → target → retrain → prove) + the
   report's fingerprint line. VO: every claim ships with sample counts,
   confidence intervals, and regressions given equal billing.
6. **2:50–3:00 — Close.** Product name, hazard stripe, repo URL, "Built on
   NVIDIA Omniverse · Isaac Sim · Replicator."

## Copy rules

- Numbers always in Plex Mono with their n (e.g., "0.165 · n=79").
- Say "measured", "locked suite", "no regressions"; never "proves safety".
- The mandatory caveat if space allows: simulation coverage supports
  engineering review; it does not replace real-world validation.
