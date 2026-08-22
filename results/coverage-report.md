# Physical AI Crash-Test Lab — Coverage and Comparison Report

- **Scenario suite:** `warehouse_ppe_v2`
- **Test manifest:** `warehouse_ppe_v2-test`
- **Manifest fingerprint:** `aae5a75f676c0b5a9d5cd8d0530ad154`
- **Baseline model:** `helmet-detector@baseline-v1` (fingerprint `7098ae05e0be7cdbf58e4916032c6a62`)
- **Candidate model:** `helmet-detector@candidate-v2` (fingerprint `f214366b1bfcd687be647348d1b4d148`)
- **Frames evaluated:** 864
- **Data source:** `isaac_sim_replicator`
- **Schema version:** `1.0.0`
- **Generated:** 2026-08-21T23:53:36Z

## 1. Evaluation configuration

Declared before evaluation. Every metric below is conditional on these values.

| Setting | Value |
| --- | --- |
| classes | `['person', 'hard_hat']` |
| iou_threshold | `0.5` |
| min_samples_for_finding | `20` |
| score_threshold | `0.35` |

## 2. Scenario factors and their physical meaning

Condition buckets were declared before any results were inspected. Each maps
to a physical quantity the simulator applies and this report quotes.

| Factor | Bucket | Physical range | Unit |
| --- | --- | --- | --- |
| lighting | bright | 600.0 – 1200.0 | lux (scene illuminance at the worker) |
| lighting | normal | 200.0 – 600.0 | lux (scene illuminance at the worker) |
| lighting | dim | 10.0 – 80.0 | lux (scene illuminance at the worker) |
| camera_angle | eye_level | 0.0 – 10.0 | degrees of camera elevation below horizontal |
| camera_angle | high_oblique | 35.0 – 60.0 | degrees of camera elevation below horizontal |
| distance | near | 1.5 – 3.0 | metres from camera to worker |
| distance | mid | 3.0 – 6.0 | metres from camera to worker |
| distance | far | 6.0 – 10.0 | metres from camera to worker |
| helmet_state | visible | 0.85 – 1.0 | fraction of hard-hat surface visible to the camera |
| helmet_state | partial | 0.25 – 0.6 | fraction of hard-hat surface visible to the camera |
| helmet_state | absent | 0.0 | fraction of hard-hat surface visible to the camera |
| background_clutter | low | 0 – 3 | count of distractor objects within the frame |
| background_clutter | high | 8 – 20 | count of distractor objects within the frame |

## 3. Baseline overall performance

The figure a conventional test run would report — and the figure the
condition breakdown in section 4 exists to interrogate.

| Metric | Value |
| --- | --- |
| hard_hat recall | 0.681 [0.64–0.72] (n=455) |
| hard_hat precision | 0.969 [0.94–0.98] (n=320) |
| person recall | 0.837 [0.81–0.86] (n=827) |
| frame accuracy (compliance verdict) | 0.701 [0.67–0.73] (n=864) |
| **dangerous miss rate** | **0.000 [0.00–0.01] (n=288)** |
| false alarm rate | 0.448 [0.41–0.49] (n=576) |

*Dangerous miss* = the scene contained no hard hat and the system reported the
worker as compliant. *False alarm* = a compliant worker was flagged. These are
not interchangeable: the first leaves someone unprotected, the second is a
nuisance that erodes trust in the system.

## 4. Weakest condition slices

Ranked on `hard_hat_recall`, worst first, by the lower bound of the 95%
confidence interval. Slices with fewer than 20 samples are
excluded from the ranking and listed separately in section 5.

| Condition slice | Dimension | Frames | Metric (95% CI) |
| --- | --- | --- | --- |
| `lighting×helmet_state=dim+partial` | lighting×helmet_state | 96 | 0.165 [0.10–0.26] (n=79) |
| `camera_angle×helmet_state=high_oblique+partial` | camera_angle×helmet_state | 144 | 0.238 [0.16–0.34] (n=84) |
| `lighting×distance=dim+far` | lighting×distance | 96 | 0.449 [0.32–0.59] (n=49) |
| `distance×helmet_state=far+partial` | distance×helmet_state | 96 | 0.433 [0.32–0.55] (n=67) |
| `lighting×distance=dim+near` | lighting×distance | 96 | 0.448 [0.33–0.58] (n=58) |
| `distance×helmet_state=near+partial` | distance×helmet_state | 96 | 0.427 [0.33–0.53] (n=89) |
| `helmet_state=partial` | helmet_state | 288 | 0.462 [0.40–0.53] (n=223) |
| `lighting=dim` | lighting | 288 | 0.477 [0.40–0.56] (n=155) |
| `lighting×distance=dim+mid` | lighting×distance | 96 | 0.542 [0.40–0.67] (n=48) |
| `distance×helmet_state=mid+partial` | distance×helmet_state | 96 | 0.537 [0.42–0.65] (n=67) |
| `lighting×helmet_state=normal+partial` | lighting×helmet_state | 96 | 0.589 [0.47–0.69] (n=73) |
| `camera_angle=high_oblique` | camera_angle | 432 | 0.580 [0.51–0.65] (n=174) |
| _… 23 further slices omitted_ | | | |

**Weakest adequately-powered slice:** `lighting×helmet_state=dim+partial` at 0.165 [0.10–0.26] (n=79).

**Worst factor interaction:** `lighting×helmet_state=dim+partial` at 0.165 [0.10–0.26] (n=79) — a combination effect that the single-factor margins average away.

## 5. Coverage gaps and underpowered slices

Reported so that thin coverage stays visible rather than being silently
omitted. These are **not** findings — the sample size cannot support a
conclusion in either direction.

| Condition slice | Dimension | Frames | Metric (95% CI) |
| --- | --- | --- | --- |
| `cell=dim+high_oblique+near+partial+low` | condition_cell | 16 | 0.000 [0.00–0.23] (n=13) |
| `cell=dim+high_oblique+mid+partial+low` | condition_cell | 16 | 0.000 [0.00–0.30] (n=9) |
| `cell=dim+high_oblique+far+partial+low` | condition_cell | 16 | 0.091 [0.02–0.38] (n=11) |
| `cell=normal+high_oblique+far+partial+low` | condition_cell | 16 | 0.167 [0.03–0.56] (n=6) |
| `cell=dim+eye_level+far+partial+low` | condition_cell | 16 | 0.200 [0.07–0.45] (n=15) |
| `cell=normal+high_oblique+mid+partial+low` | condition_cell | 16 | 0.286 [0.08–0.64] (n=7) |
| `cell=dim+eye_level+near+partial+low` | condition_cell | 16 | 0.250 [0.10–0.49] (n=16) |
| `cell=bright+high_oblique+near+partial+low` | condition_cell | 16 | 0.267 [0.11–0.52] (n=15) |
| `cell=bright+high_oblique+mid+partial+low` | condition_cell | 16 | 0.400 [0.12–0.77] (n=5) |
| `cell=dim+eye_level+mid+partial+low` | condition_cell | 16 | 0.333 [0.15–0.58] (n=15) |
| `cell=normal+high_oblique+near+partial+low` | condition_cell | 16 | 0.385 [0.18–0.64] (n=13) |
| `cell=normal+high_oblique+far+visible+low` | condition_cell | 16 | 0.667 [0.35–0.88] (n=9) |
| _… 24 further slices omitted_ | | | |

**Explicitly not tested in this suite:**

- Weather, wet or reflective floor surfaces.
- Sensor modalities other than RGB.
- Multiple simultaneous workers and inter-person occlusion.
- Motion blur and rolling-shutter effects.
- Hard-hat colours and geometries beyond the single modelled asset.
- Any real-world imagery.

## 6. Baseline versus candidate

Both models evaluated on manifest `warehouse_ppe_v2-test`, fingerprint
`aae5a75f676c0b5a9d5cd8d0530ad154` — byte-identical for both runs. Neither
model was trained on these frames.

| | Baseline | Candidate | Δ |
| --- | --- | --- | --- |
| overall `hard_hat_recall` | 0.681 [0.64–0.72] (n=455) | 0.941 [0.92–0.96] (n=455) | +0.259 |

A change is called material at |Δ| ≥ 0.05 and
significant at 95% by a two-proportion z-test on the difference. Slices
with fewer than 20 samples on either side receive no verdict at all — the
same bar section 4 applies to findings. Everything else is reported as
inconclusive rather than as a win.

### 6.1 Improved

| Condition slice | Frames | Baseline | Candidate | Δ | Verdict |
| --- | --- | --- | --- | --- | --- |
| `helmet_state=visible` | 288 | 0.892 [0.85–0.93] (n=232) | 0.948 [0.91–0.97] (n=232) | +0.056 | improved |
| `camera_angle×helmet_state=eye_level+visible` | 144 | 0.887 [0.82–0.93] (n=142) | 0.958 [0.91–0.98] (n=142) | +0.070 | improved |
| `lighting=bright` | 288 | 0.803 [0.73–0.86] (n=147) | 0.946 [0.90–0.97] (n=147) | +0.143 | improved |
| `lighting×helmet_state=dim+visible` | 96 | 0.803 [0.70–0.88] (n=76) | 0.947 [0.87–0.98] (n=76) | +0.145 | improved |
| `lighting×distance=normal+mid` | 96 | 0.812 [0.68–0.90] (n=48) | 0.958 [0.86–0.99] (n=48) | +0.146 | improved |
| `lighting=normal` | 288 | 0.771 [0.70–0.83] (n=153) | 0.928 [0.88–0.96] (n=153) | +0.157 | improved |
| `lighting×distance=normal+near` | 96 | 0.800 [0.68–0.88] (n=60) | 1.000 [0.94–1.00] (n=60) | +0.200 | improved |
| `distance=mid` | 288 | 0.739 [0.66–0.81] (n=138) | 0.949 [0.90–0.98] (n=138) | +0.210 | improved |
| `lighting×distance=bright+near` | 96 | 0.754 [0.63–0.84] (n=61) | 0.967 [0.89–0.99] (n=61) | +0.213 | improved |
| `camera_angle=eye_level` | 432 | 0.744 [0.69–0.79] (n=281) | 0.964 [0.94–0.98] (n=281) | +0.221 | improved |
| `distance=far` | 288 | 0.638 [0.55–0.71] (n=138) | 0.884 [0.82–0.93] (n=138) | +0.246 | improved |
| `lighting×helmet_state=bright+partial` | 96 | 0.662 [0.55–0.76] (n=71) | 0.944 [0.86–0.98] (n=71) | +0.282 | improved |
| _… 14 further slices omitted_ | | | | | |

### 6.2 Regressed

_None._

### 6.3 Inconclusive

Changed by more than the material threshold, but not significantly for the
sample size available. Not a win and not a loss.

| Condition slice | Frames | Baseline | Candidate | Δ | Verdict |
| --- | --- | --- | --- | --- | --- |
| `distance×helmet_state=near+visible` | 96 | 0.911 [0.83–0.95] (n=90) | 0.967 [0.91–0.99] (n=90) | +0.056 | inconclusive |
| `distance×helmet_state=far+visible` | 96 | 0.831 [0.73–0.90] (n=71) | 0.915 [0.83–0.96] (n=71) | +0.085 | inconclusive |
| `lighting×distance=normal+far` | 96 | 0.689 [0.54–0.80] (n=45) | 0.800 [0.66–0.89] (n=45) | +0.111 | inconclusive |
| `lighting×distance=bright+far` | 96 | 0.795 [0.65–0.89] (n=44) | 0.932 [0.82–0.98] (n=44) | +0.136 | inconclusive |

### 6.4 No verdict — insufficient samples

Listed for completeness so thin coverage stays visible. These slices are
**not** claims in either direction.

| Condition slice | Frames | Baseline | Candidate | Δ | Verdict |
| --- | --- | --- | --- | --- | --- |
| `cell=bright+eye_level+mid+visible+low` | 16 | 0.938 [0.72–0.99] (n=16) | 0.938 [0.72–0.99] (n=16) | +0.000 | underpowered |
| `cell=bright+eye_level+near+visible+low` | 16 | 1.000 [0.81–1.00] (n=16) | 1.000 [0.81–1.00] (n=16) | +0.000 | underpowered |
| `cell=bright+high_oblique+far+partial+low` | 16 | 1.000 [0.57–1.00] (n=5) | 1.000 [0.57–1.00] (n=5) | +0.000 | underpowered |
| `cell=bright+high_oblique+far+visible+low` | 16 | 1.000 [0.68–1.00] (n=8) | 1.000 [0.68–1.00] (n=8) | +0.000 | underpowered |
| `cell=bright+high_oblique+mid+visible+low` | 16 | 1.000 [0.61–1.00] (n=6) | 1.000 [0.61–1.00] (n=6) | +0.000 | underpowered |
| `cell=bright+high_oblique+near+visible+low` | 16 | 0.929 [0.69–0.99] (n=14) | 0.929 [0.69–0.99] (n=14) | +0.000 | underpowered |
| `cell=normal+eye_level+mid+visible+low` | 16 | 0.938 [0.72–0.99] (n=16) | 0.938 [0.72–0.99] (n=16) | +0.000 | underpowered |
| `cell=normal+eye_level+near+visible+low` | 16 | 1.000 [0.81–1.00] (n=16) | 1.000 [0.81–1.00] (n=16) | +0.000 | underpowered |
| `cell=normal+high_oblique+far+visible+low` | 16 | 0.667 [0.35–0.88] (n=9) | 0.667 [0.35–0.88] (n=9) | +0.000 | underpowered |
| `cell=normal+high_oblique+mid+visible+low` | 16 | 1.000 [0.70–1.00] (n=9) | 1.000 [0.70–1.00] (n=9) | +0.000 | underpowered |
| `cell=normal+high_oblique+near+visible+low` | 16 | 1.000 [0.80–1.00] (n=15) | 1.000 [0.80–1.00] (n=15) | +0.000 | underpowered |
| `cell=bright+eye_level+far+visible+low` | 16 | 0.812 [0.57–0.93] (n=16) | 0.875 [0.64–0.97] (n=16) | +0.062 | underpowered |
| _… 24 further slices omitted_ | | | | | |

## 7. Limitations and what this report does not claim

- This report documents performance on a defined simulated scenario suite. It supports engineering review and does not replace real-world validation or a qualified safety assessment.
- Simulation coverage does not prove real-world performance. A synthetic-to-real domain gap exists and is not quantified by this report.
- No claim of safety certification is made or implied.
- Human safety procedures must not depend solely on this system.
- False positives and false negatives carry different operational consequences; a single accuracy figure conceals that asymmetry.
- Metrics are reported at declared IoU and confidence thresholds. Different thresholds yield different numbers.
- Scene geometry is primitive stand-ins (cylinder worker, cube hard hat), not photorealistic assets. Absolute performance figures will not transfer to real imagery; the comparison between model versions is the meaningful result.
- Lighting buckets map to an UNCALIBRATED simulator intensity, not measured illuminance. Bucket ordering is meaningful; the lux values are nominal.
- CONFOUND: if the candidate's training set is larger than the baseline's, some of the improvement is attributable to data volume rather than to targeting. Improvement concentrated in the targeted slice is evidence for targeting; broad improvement across unrelated slices is not. A clean test holds total training volume constant and varies only which conditions the extra frames cover. Compare the train_images counts in each export manifest before drawing a conclusion.

## 8. Reproduction

Every frame is regenerable from its scenario id: seeds are derived by hash from
`(suite name, scenario id)` rather than drawn at random, so the suite can be
rebuilt on any machine at any time.

| Artifact | Identity |
| --- | --- |
| scenario suite | `warehouse_ppe_v2` |
| test manifest | `warehouse_ppe_v2-test` |
| manifest fingerprint | `aae5a75f676c0b5a9d5cd8d0530ad154` |
| schema version | `1.0.0` |
| baseline model fingerprint | `7098ae05e0be7cdbf58e4916032c6a62` |
| candidate model fingerprint | `f214366b1bfcd687be647348d1b4d148` |
