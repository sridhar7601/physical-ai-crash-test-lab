# Demo video — what to say, shot by shot (3:00)

**Record:** the published site (one browser tab, full screen) plus two short
cuts to the VM desktop. Do one dry run; keep the cursor slow and deliberate.

**Site:** https://claude.ai/code/artifact/1a2641ec-1bd2-4944-b121-a4ca7f52cfbe

**Golden rules while narrating**
- Say every number with its context ("0.17 recall, 79 samples"), never a bare percentage.
- Never say "proves it's safe". Say "measured on a simulated suite".
- Let the Explorer flip land in silence for one beat. That silence is the demo.

---

## 0:00–0:22 · The trap
*Shot: site hero. The two frames auto-rotate behind you.*

> "A warehouse installs an AI camera to check that workers wear hard hats. It
> tested at ninety-three percent recall in good lighting, and it got signed
> off. Then it missed a worker in a dim aisle with his helmet half-hidden
> behind racking — seventeen percent recall in that condition. The average
> hid it. You cannot stage five hundred dangerous warehouse conditions to
> find that, so we built the warehouse in simulation instead. This is a
> crash-test lab for AI vision."

## 0:22–0:50 · Why simulation earns its place
*Shot: scroll slowly to the Explorer; hover a frame so the HUD reads out.*

> "These are NVIDIA Isaac Sim renders of the SimReady warehouse — real
> racking, real pallets, and a worker actually wearing the hard hat we're
> detecting. Every condition is a physical quantity: lux, metres, degrees of
> camera elevation. And because the simulator owns the scene, every frame
> ships with pixel-perfect ground truth for free — including the occlusion
> fraction, measured by the renderer, not assumed by us. Two thousand three
> hundred frames, rendered on an L40S."

## 0:50–1:40 · The reveal — the money shot
*Shot: click "Play the story", or drive it manually. Manual is stronger.*

Click **bright / visible** → box on the helmet, verdict DETECTED.
> "Good light, helmet visible. The model finds it. This is the test the model passed."

Click **dim / partial**, model still Baseline. **Pause. Say nothing for a beat.**
> "Same warehouse. Dim aisle, helmet partly behind racking. No detection at
> all. In production, this worker's PPE state is simply invisible — in exactly
> the condition where somebody gets hurt."

Press **c** (candidate). Box snaps onto the helmet.
> "Same frame. Same locked test suite. This is the model after the lab told us
> which data to generate — six hundred frames aimed at that specific
> condition. Zero point one seven to zero point nine five."

Optional, if pacing allows — click **bright / absent**:
> "And the opposite failure: no helmet worn, but the model reports one. A
> bare-headed worker passing as compliant. The lab counts that separately,
> because those two mistakes have very different consequences."

## 1:40–2:20 · The evidence
*Shot: scroll to Evidence. Hover the dark heatmap cell, then the arms chart.*

> "Here's the same run, scored by condition instead of averaged. Every cell
> carries its sample count and a confidence interval, and the dashed cells got
> no verdict at all — too little evidence to claim anything either way."

Hover the three-bar chart.
> "And this is the experiment most demos skip. Was the gain from *targeting*,
> or just from *more data*? So we trained a control on the identical amount of
> untargeted data. Coverage alone gets you to zero point nine one. Targeting
> gets zero point nine five — a consistent edge that does not clear
> significance on this suite, and our own tooling reports it as unchanged
> rather than claiming a win. On the earlier, simpler scene, targeting *was*
> significant. Whether targeted generation is worth paying for is an empirical
> question — and this is the instrument that answers it."

## 2:20–2:45 · The report
*Shot: scroll to Report.*

> "Every run ships this: the verdict, the limitations we refuse to paper over,
> and the reproduction identity — suite fingerprint, both model hashes, the
> thresholds. Seeds derive by hash, so any frame in this report can be
> regenerated on any machine. Twenty-six conditions improved, zero regressed,
> and the regressions section is built to be as prominent as the wins."

## 2:45–3:00 · Close
*Shot: back to hero, or the repo.*

> "Automotive safety has crash-test institutions that buyers, insurers and
> regulators all trust. Physical AI works around people every day and has
> nothing comparable. For Presidio that's a readiness assessment that becomes
> Omniverse environments, synthetic-data engineering, and managed validation of
> every model release. Simulation coverage supports engineering review — it
> doesn't replace real-world validation. That line is in every report we ship."

---

## Fallback if anything breaks live
`python3 -m crashlab demo` replays the whole loop on fixtures on any laptop,
and prints a banner marking the output as synthetic placeholder data.

## Recording checklist
- [ ] Browser zoom 100%, window 1920×1080, no bookmarks bar
- [ ] Dark mode (the site is dark-first — it looks best)
- [ ] Explorer: click through the sequence once before recording
- [ ] Mic: no room echo; one take per section is fine, cut between
