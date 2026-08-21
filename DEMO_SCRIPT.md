# Demo video script — 3 minutes

Record the DCV desktop (https://<instance-ip>:8443) with a screen recorder, or
QuickTime on the Mac over the browser tab. Practice once; keep cuts tight.

## 0:00–0:25 — The trap (slides or README on screen)
> "A warehouse installs an AI camera to check hard hats. It tests at 98%
> recall and gets signed off. Then it misses a worker in a dim corner, helmet
> half-hidden behind a pallet — the exact case that causes an injury.
> You can't stage 500 dangerous conditions in a real warehouse. So we built a
> crash-test lab: we stage them in simulation instead."

## 0:25–1:00 — Real frames from Isaac Sim (file manager on the VM)
Open ~/crashtestlab/datasets/test/frames — open one bright frame, one dim frame
side by side. Then open the matching label JSON in ~/crashtestlab/datasets/test/labels.
> "1,080 frames rendered on an L40S with Isaac Sim and Replicator. Every
> condition is a physical quantity — lux, metres, degrees. And because the
> simulator placed the helmet, every frame comes with pixel-perfect ground
> truth for free — including a MEASURED occlusion fraction, not an assumed one."

## 1:00–1:45 — The reveal (terminal on the VM)
    cd ~/crashtestlab && python3 -m crashlab.pipeline diagnose \
      --dataset datasets/test --predictions preds/baseline \
      --manifest artifacts/warehouse_ppe_v1-test.json \
      --model-name helmet-detector --model-version baseline-v1 --out /tmp/d
Point at the output:
> "We trained a real YOLO detector on well-lit, unoccluded footage — what a
> team actually collects. Overall recall 0.45. But scored BY CONDITION:
> bright and visible, 0.98. Dim and partially occluded — 0.034. Three percent.
> The overall number hid a blind spot exactly where people get hurt.
> Nobody told the analyser what we withheld from training. It found this."

## 1:45–2:25 — The fix, and the honest experiment
Show scripts/full_loop.sh briefly, then the four-way table in the README.
> "The lab turns the worst slice into a render request: 600 frames aimed at
> dim-plus-occluded. Retrain, re-test on the byte-identical suite: 0.03 to 0.93.
> But is that targeting, or just MORE data? We ran the control most demos skip:
> same volume, one arm random frames, one arm targeted. Coverage alone gets you
> to 0.85. Targeting adds a further significant +0.05 to +0.11. We can tell you
> exactly what the aiming is worth — because we measured it."

## 2:25–3:00 — The evidence (open results/coverage-report.md on GitHub)
Scroll the report: fingerprints, CIs, regressions section, limitations.
> "Every claim ships as a versioned report: manifest fingerprints, sample
> counts, confidence intervals, regressions with equal prominence, and what we
> did NOT test. Automotive safety has crash-test institutions everyone trusts.
> Physical AI has nothing comparable. This is that missing institution —
> and for Presidio, a readiness assessment that becomes environments,
> synthetic-data engineering, and managed validation of every model release."

## Backup if the VM is down
`python3 -m crashlab demo` on any laptop replays the entire loop on fixtures —
it prints a banner marking outputs as synthetic placeholders.
