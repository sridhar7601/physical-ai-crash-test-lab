# Physical AI Crash-Test Lab — Coverage and Comparison Report

- **Scenario suite:** `warehouse_ppe_v1`
- **Test manifest:** `warehouse_ppe_v1-test`
- **Manifest fingerprint:** `52c6a41371a41ba3e6c82e287429c790`
- **Baseline model:** `helmet-detector@baseline-v1` (fingerprint `c3c517d03bd46cca438cb632d8a1ed9e`)
- **Candidate model:** `helmet-detector@candidate-v2` (fingerprint `037f48feb8514e453f9e90588a1de18e`)
- **Frames evaluated:** 540
- **Data source:** `isaac_sim_replicator`
- **Schema version:** `1.0.0`
- **Generated:** 2026-08-21T20:32:59Z

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
| hard_hat recall | 0.449 [0.40–0.50] (n=354) |
| hard_hat precision | 0.716 [0.65–0.77] (n=222) |
| person recall | 0.957 [0.94–0.97] (n=540) |
| frame accuracy (compliance verdict) | 0.719 [0.68–0.75] (n=540) |
| **dangerous miss rate** | **0.000 [0.00–0.02] (n=180)** |
| false alarm rate | 0.422 [0.37–0.47] (n=360) |

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
| `lighting×helmet_state=dim+partial` | lighting×helmet_state | 60 | 0.034 [0.01–0.12] (n=59) |
| `distance×helmet_state=near+partial` | distance×helmet_state | 60 | 0.034 [0.01–0.12] (n=58) |
| `camera_angle×helmet_state=high_oblique+partial` | camera_angle×helmet_state | 90 | 0.033 [0.01–0.09] (n=90) |
| `distance×helmet_state=far+partial` | distance×helmet_state | 60 | 0.050 [0.02–0.14] (n=60) |
| `lighting×helmet_state=normal+partial` | lighting×helmet_state | 60 | 0.051 [0.02–0.14] (n=59) |
| `helmet_state=partial` | helmet_state | 180 | 0.084 [0.05–0.13] (n=178) |
| `camera_angle×helmet_state=eye_level+partial` | camera_angle×helmet_state | 90 | 0.136 [0.08–0.22] (n=88) |
| `distance×helmet_state=mid+partial` | distance×helmet_state | 60 | 0.167 [0.09–0.28] (n=60) |
| `lighting×helmet_state=bright+partial` | lighting×helmet_state | 60 | 0.167 [0.09–0.28] (n=60) |
| `lighting×distance=dim+far` | lighting×distance | 60 | 0.275 [0.16–0.43] (n=40) |
| `lighting×distance=dim+mid` | lighting×distance | 60 | 0.275 [0.16–0.43] (n=40) |
| `lighting×distance=dim+near` | lighting×distance | 60 | 0.289 [0.17–0.45] (n=38) |
| _… 23 further slices omitted_ | | | |

**Weakest adequately-powered slice:** `lighting×helmet_state=dim+partial` at 0.034 [0.01–0.12] (n=59).

**Worst factor interaction:** `lighting×helmet_state=dim+partial` at 0.034 [0.01–0.12] (n=59) — a combination effect that the single-factor margins average away.

## 5. Coverage gaps and underpowered slices

Reported so that thin coverage stays visible rather than being silently
omitted. These are **not** findings — the sample size cannot support a
conclusion in either direction.

| Condition slice | Dimension | Frames | Metric (95% CI) |
| --- | --- | --- | --- |
| `cell=bright+eye_level+near+partial+low` | condition_cell | 10 | 0.000 [0.00–0.28] (n=10) |
| `cell=bright+high_oblique+mid+partial+low` | condition_cell | 10 | 0.000 [0.00–0.28] (n=10) |
| `cell=bright+high_oblique+near+partial+low` | condition_cell | 10 | 0.000 [0.00–0.28] (n=10) |
| `cell=dim+eye_level+far+partial+low` | condition_cell | 10 | 0.000 [0.00–0.28] (n=10) |
| `cell=dim+eye_level+mid+partial+low` | condition_cell | 10 | 0.000 [0.00–0.28] (n=10) |
| `cell=dim+eye_level+mid+visible+low` | condition_cell | 10 | 0.000 [0.00–0.28] (n=10) |
| `cell=dim+high_oblique+far+partial+low` | condition_cell | 10 | 0.000 [0.00–0.28] (n=10) |
| `cell=dim+high_oblique+near+partial+low` | condition_cell | 10 | 0.000 [0.00–0.28] (n=10) |
| `cell=normal+eye_level+far+partial+low` | condition_cell | 10 | 0.000 [0.00–0.28] (n=10) |
| `cell=normal+high_oblique+far+partial+low` | condition_cell | 10 | 0.000 [0.00–0.28] (n=10) |
| `cell=normal+high_oblique+mid+partial+low` | condition_cell | 10 | 0.000 [0.00–0.28] (n=10) |
| `cell=normal+high_oblique+near+partial+low` | condition_cell | 10 | 0.000 [0.00–0.28] (n=10) |
| _… 24 further slices omitted_ | | | |

**Explicitly not tested in this suite:**

- Weather, wet or reflective floor surfaces.
- Sensor modalities other than RGB.
- Multiple simultaneous workers and inter-person occlusion.
- Motion blur and rolling-shutter effects.
- Hard-hat colours and geometries beyond the single modelled asset.
- Any real-world imagery.

## 6. Baseline versus candidate

Both models evaluated on manifest `warehouse_ppe_v1-test`, fingerprint
`52c6a41371a41ba3e6c82e287429c790` — byte-identical for both runs. Neither
model was trained on these frames.

| | Baseline | Candidate | Δ |
| --- | --- | --- | --- |
| overall `hard_hat_recall` | 0.449 [0.40–0.50] (n=354) | 0.963 [0.94–0.98] (n=354) | +0.514 |

A change is called material at |Δ| ≥ 0.05 and
significant at 95% by a two-proportion z-test on the difference. Slices
with fewer than 20 samples on either side receive no verdict at all — the
same bar section 4 applies to findings. Everything else is reported as
inconclusive rather than as a win.

### 6.1 Improved

| Condition slice | Frames | Baseline | Candidate | Δ | Verdict |
| --- | --- | --- | --- | --- | --- |

| `distance×helmet_state=far+visible` | 60 | 0.833 [0.72–0.91] (n=60) | 0.983 [0.91–1.00] (n=60) | +0.150 | improved |
| `distance×helmet_state=near+visible` | 60 | 0.804 [0.68–0.89] (n=56) | 0.964 [0.88–0.99] (n=56) | +0.161 | improved |
| `helmet_state=visible` | 180 | 0.818 [0.75–0.87] (n=176) | 0.983 [0.95–0.99] (n=176) | +0.165 | improved |
| `distance×helmet_state=mid+visible` | 60 | 0.817 [0.70–0.89] (n=60) | 1.000 [0.94–1.00] (n=60) | +0.183 | improved |
| `lighting×distance=bright+mid` | 60 | 0.675 [0.52–0.80] (n=40) | 0.975 [0.87–1.00] (n=40) | +0.300 | improved |
| `camera_angle×helmet_state=eye_level+visible` | 90 | 0.663 [0.56–0.75] (n=86) | 0.977 [0.92–0.99] (n=86) | +0.314 | improved |
| `lighting=bright` | 180 | 0.563 [0.47–0.65] (n=119) | 0.983 [0.94–1.00] (n=119) | +0.420 | improved |
| `lighting×distance=bright+far` | 60 | 0.550 [0.40–0.69] (n=40) | 0.975 [0.87–1.00] (n=40) | +0.425 | improved |
| `lighting×distance=normal+far` | 60 | 0.500 [0.35–0.65] (n=40) | 0.925 [0.80–0.97] (n=40) | +0.425 | improved |
| `lighting×helmet_state=dim+visible` | 60 | 0.525 [0.40–0.65] (n=59) | 0.966 [0.88–0.99] (n=59) | +0.441 | improved |
| `camera_angle=high_oblique` | 270 | 0.500 [0.43–0.57] (n=180) | 0.950 [0.91–0.97] (n=180) | +0.450 | improved |
| `lighting×distance=normal+mid` | 60 | 0.525 [0.37–0.67] (n=40) | 0.975 [0.87–1.00] (n=40) | +0.450 | improved |
| _… 20 further slices omitted_ | | | | | |

### 6.2 Regressed

_None._

### 6.3 Inconclusive

Changed by more than the material threshold, but not significantly for the
sample size available. Not a win and not a loss.

_None._

### 6.4 No verdict — insufficient samples

Listed for completeness so thin coverage stays visible. These slices are
**not** claims in either direction.

| Condition slice | Frames | Baseline | Candidate | Δ | Verdict |
| --- | --- | --- | --- | --- | --- |
| `cell=dim+high_oblique+far+visible+low` | 10 | 1.000 [0.72–1.00] (n=10) | 0.900 [0.60–0.98] (n=10) | -0.100 | underpowered |
| `cell=bright+eye_level+far+visible+low` | 10 | 1.000 [0.72–1.00] (n=10) | 1.000 [0.72–1.00] (n=10) | +0.000 | underpowered |
| `cell=bright+eye_level+mid+visible+low` | 10 | 1.000 [0.72–1.00] (n=10) | 1.000 [0.72–1.00] (n=10) | +0.000 | underpowered |
| `cell=bright+high_oblique+mid+visible+low` | 10 | 1.000 [0.72–1.00] (n=10) | 1.000 [0.72–1.00] (n=10) | +0.000 | underpowered |
| `cell=bright+high_oblique+near+visible+low` | 10 | 1.000 [0.72–1.00] (n=10) | 1.000 [0.72–1.00] (n=10) | +0.000 | underpowered |
| `cell=dim+high_oblique+mid+visible+low` | 10 | 1.000 [0.72–1.00] (n=10) | 1.000 [0.72–1.00] (n=10) | +0.000 | underpowered |
| `cell=normal+eye_level+far+visible+low` | 10 | 1.000 [0.72–1.00] (n=10) | 1.000 [0.72–1.00] (n=10) | +0.000 | underpowered |
| `cell=normal+eye_level+mid+visible+low` | 10 | 1.000 [0.72–1.00] (n=10) | 1.000 [0.72–1.00] (n=10) | +0.000 | underpowered |
| `cell=normal+eye_level+near+visible+low` | 10 | 0.875 [0.53–0.98] (n=8) | 0.875 [0.53–0.98] (n=8) | +0.000 | underpowered |
| `cell=normal+high_oblique+far+visible+low` | 10 | 1.000 [0.72–1.00] (n=10) | 1.000 [0.72–1.00] (n=10) | +0.000 | underpowered |
| `cell=normal+high_oblique+near+visible+low` | 10 | 1.000 [0.72–1.00] (n=10) | 1.000 [0.72–1.00] (n=10) | +0.000 | underpowered |
| `cell=bright+high_oblique+far+visible+low` | 10 | 0.900 [0.60–0.98] (n=10) | 1.000 [0.72–1.00] (n=10) | +0.100 | underpowered |
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
| scenario suite | `warehouse_ppe_v1` |
| test manifest | `warehouse_ppe_v1-test` |
| manifest fingerprint | `52c6a41371a41ba3e6c82e287429c790` |
| schema version | `1.0.0` |
| baseline model fingerprint | `c3c517d03bd46cca438cb632d8a1ed9e` |
| candidate model fingerprint | `037f48feb8514e453f9e90588a1de18e` |

