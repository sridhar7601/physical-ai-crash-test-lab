# Physical AI Crash-Test Lab — Coverage and Comparison Report

- **Scenario suite:** `warehouse_ppe_v1`
- **Test manifest:** `warehouse_ppe_v1-test`
- **Manifest fingerprint:** `52c6a41371a41ba3e6c82e287429c790`
- **Baseline model:** `helmet-detector@arm-bulk-all` (fingerprint `359aca11e185cebeed43b1287dc6fd9e`)
- **Candidate model:** `helmet-detector@arm-targeted` (fingerprint `4deba81e051acad493af5f33db9f04f8`)
- **Frames evaluated:** 540
- **Data source:** `isaac_sim_replicator`
- **Schema version:** `1.0.0`
- **Generated:** 2026-08-21T21:24:24Z

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
| hard_hat recall | 0.898 [0.86–0.93] (n=354) |
| hard_hat precision | 0.909 [0.87–0.93] (n=350) |
| person recall | 1.000 [0.99–1.00] (n=540) |
| frame accuracy (compliance verdict) | 0.946 [0.92–0.96] (n=540) |
| **dangerous miss rate** | **0.000 [0.00–0.02] (n=180)** |
| false alarm rate | 0.081 [0.06–0.11] (n=360) |

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
| `distance×helmet_state=far+partial` | distance×helmet_state | 60 | 0.683 [0.56–0.79] (n=60) |
| `lighting×distance=bright+far` | lighting×distance | 60 | 0.800 [0.65–0.90] (n=40) |
| `lighting×distance=normal+far` | lighting×distance | 60 | 0.825 [0.68–0.91] (n=40) |
| `camera_angle×helmet_state=high_oblique+partial` | camera_angle×helmet_state | 90 | 0.789 [0.69–0.86] (n=90) |
| `lighting×helmet_state=normal+partial` | lighting×helmet_state | 60 | 0.814 [0.70–0.89] (n=59) |
| `lighting×helmet_state=bright+partial` | lighting×helmet_state | 60 | 0.817 [0.70–0.89] (n=60) |
| `lighting×helmet_state=dim+partial` | lighting×helmet_state | 60 | 0.847 [0.73–0.92] (n=59) |
| `lighting×distance=dim+near` | lighting×distance | 60 | 0.895 [0.76–0.96] (n=38) |
| `helmet_state=partial` | helmet_state | 180 | 0.826 [0.76–0.87] (n=178) |
| `lighting×distance=bright+near` | lighting×distance | 60 | 0.897 [0.76–0.96] (n=39) |
| `distance=far` | distance | 180 | 0.842 [0.77–0.90] (n=120) |
| `lighting×distance=dim+far` | lighting×distance | 60 | 0.900 [0.77–0.96] (n=40) |
| _… 23 further slices omitted_ | | | |

**Weakest adequately-powered slice:** `distance×helmet_state=far+partial` at 0.683 [0.56–0.79] (n=60).

**Worst factor interaction:** `distance×helmet_state=far+partial` at 0.683 [0.56–0.79] (n=60) — a combination effect that the single-factor margins average away.

## 5. Coverage gaps and underpowered slices

Reported so that thin coverage stays visible rather than being silently
omitted. These are **not** findings — the sample size cannot support a
conclusion in either direction.

| Condition slice | Dimension | Frames | Metric (95% CI) |
| --- | --- | --- | --- |
| `cell=normal+high_oblique+far+partial+low` | condition_cell | 10 | 0.500 [0.24–0.76] (n=10) |
| `cell=bright+eye_level+far+partial+low` | condition_cell | 10 | 0.600 [0.31–0.83] (n=10) |
| `cell=bright+high_oblique+far+partial+low` | condition_cell | 10 | 0.600 [0.31–0.83] (n=10) |
| `cell=dim+eye_level+near+partial+low` | condition_cell | 10 | 0.667 [0.35–0.88] (n=9) |
| `cell=normal+high_oblique+mid+partial+low` | condition_cell | 10 | 0.700 [0.40–0.89] (n=10) |
| `cell=bright+high_oblique+near+partial+low` | condition_cell | 10 | 0.800 [0.49–0.94] (n=10) |
| `cell=dim+eye_level+far+partial+low` | condition_cell | 10 | 0.800 [0.49–0.94] (n=10) |
| `cell=dim+high_oblique+far+partial+low` | condition_cell | 10 | 0.800 [0.49–0.94] (n=10) |
| `cell=dim+high_oblique+mid+partial+low` | condition_cell | 10 | 0.800 [0.49–0.94] (n=10) |
| `cell=normal+eye_level+far+partial+low` | condition_cell | 10 | 0.800 [0.49–0.94] (n=10) |
| `cell=normal+eye_level+near+visible+low` | condition_cell | 10 | 0.875 [0.53–0.98] (n=8) |
| `cell=bright+eye_level+near+visible+low` | condition_cell | 10 | 0.889 [0.57–0.98] (n=9) |
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
| overall `hard_hat_recall` | 0.898 [0.86–0.93] (n=354) | 0.949 [0.92–0.97] (n=354) | +0.051 |

A change is called material at |Δ| ≥ 0.05 and
significant at 95% by a two-proportion z-test on the difference. Slices
with fewer than 20 samples on either side receive no verdict at all — the
same bar section 4 applies to findings. Everything else is reported as
inconclusive rather than as a win.

### 6.1 Improved

| Condition slice | Frames | Baseline | Candidate | Δ | Verdict |
| --- | --- | --- | --- | --- | --- |

| `distance×helmet_state=mid+partial` | 60 | 0.900 [0.80–0.95] (n=60) | 0.983 [0.91–1.00] (n=60) | +0.083 | improved |
| `lighting=bright` | 180 | 0.891 [0.82–0.94] (n=119) | 0.975 [0.93–0.99] (n=119) | +0.084 | improved |
| `camera_angle×helmet_state=eye_level+partial` | 90 | 0.864 [0.78–0.92] (n=88) | 0.966 [0.90–0.99] (n=88) | +0.102 | improved |
| `helmet_state=partial` | 180 | 0.826 [0.76–0.87] (n=178) | 0.933 [0.89–0.96] (n=178) | +0.107 | improved |
| `camera_angle×helmet_state=high_oblique+partial` | 90 | 0.789 [0.69–0.86] (n=90) | 0.900 [0.82–0.95] (n=90) | +0.111 | improved |
| `lighting×distance=bright+far` | 60 | 0.800 [0.65–0.90] (n=40) | 0.950 [0.83–0.99] (n=40) | +0.150 | improved |
| `lighting×helmet_state=bright+partial` | 60 | 0.817 [0.70–0.89] (n=60) | 0.967 [0.89–0.99] (n=60) | +0.150 | improved |
| `distance×helmet_state=far+partial` | 60 | 0.683 [0.56–0.79] (n=60) | 0.867 [0.76–0.93] (n=60) | +0.183 | improved |

### 6.2 Regressed

_None._

### 6.3 Inconclusive

Changed by more than the material threshold, but not significantly for the
sample size available. Not a win and not a loss.

| Condition slice | Frames | Baseline | Candidate | Δ | Verdict |
| --- | --- | --- | --- | --- | --- |
| `lighting×distance=dim+mid` | 60 | 0.950 [0.83–0.99] (n=40) | 1.000 [0.91–1.00] (n=40) | +0.050 | inconclusive |
| `distance×helmet_state=near+partial` | 60 | 0.897 [0.79–0.95] (n=58) | 0.948 [0.86–0.98] (n=58) | +0.052 | inconclusive |
| `lighting×distance=dim+near` | 60 | 0.895 [0.76–0.96] (n=38) | 0.947 [0.83–0.99] (n=38) | +0.053 | inconclusive |
| `camera_angle=high_oblique` | 270 | 0.883 [0.83–0.92] (n=180) | 0.939 [0.89–0.97] (n=180) | +0.056 | inconclusive |
| `distance=far` | 180 | 0.842 [0.77–0.90] (n=120) | 0.917 [0.85–0.95] (n=120) | +0.075 | inconclusive |
| `lighting×distance=bright+near` | 60 | 0.897 [0.76–0.96] (n=39) | 0.974 [0.87–1.00] (n=39) | +0.077 | inconclusive |
| `lighting×helmet_state=dim+partial` | 60 | 0.847 [0.73–0.92] (n=59) | 0.932 [0.84–0.97] (n=59) | +0.085 | inconclusive |
| `lighting×helmet_state=normal+partial` | 60 | 0.814 [0.70–0.89] (n=59) | 0.898 [0.80–0.95] (n=59) | +0.085 | inconclusive |
| `lighting×distance=normal+far` | 60 | 0.825 [0.68–0.91] (n=40) | 0.925 [0.80–0.97] (n=40) | +0.100 | inconclusive |

### 6.4 No verdict — insufficient samples

Listed for completeness so thin coverage stays visible. These slices are
**not** claims in either direction.

| Condition slice | Frames | Baseline | Candidate | Δ | Verdict |
| --- | --- | --- | --- | --- | --- |
| `cell=dim+eye_level+far+visible+low` | 10 | 1.000 [0.72–1.00] (n=10) | 0.900 [0.60–0.98] (n=10) | -0.100 | underpowered |
| `cell=dim+high_oblique+far+visible+low` | 10 | 1.000 [0.72–1.00] (n=10) | 0.900 [0.60–0.98] (n=10) | -0.100 | underpowered |
| `cell=normal+high_oblique+mid+visible+low` | 10 | 1.000 [0.72–1.00] (n=10) | 0.900 [0.60–0.98] (n=10) | -0.100 | underpowered |
| `cell=normal+high_oblique+near+partial+low` | 10 | 1.000 [0.72–1.00] (n=10) | 0.900 [0.60–0.98] (n=10) | -0.100 | underpowered |
| `cell=bright+eye_level+far+visible+low` | 10 | 1.000 [0.72–1.00] (n=10) | 1.000 [0.72–1.00] (n=10) | +0.000 | underpowered |
| `cell=bright+eye_level+mid+partial+low` | 10 | 1.000 [0.72–1.00] (n=10) | 1.000 [0.72–1.00] (n=10) | +0.000 | underpowered |
| `cell=bright+eye_level+mid+visible+low` | 10 | 1.000 [0.72–1.00] (n=10) | 1.000 [0.72–1.00] (n=10) | +0.000 | underpowered |
| `cell=bright+eye_level+near+partial+low` | 10 | 1.000 [0.72–1.00] (n=10) | 1.000 [0.72–1.00] (n=10) | +0.000 | underpowered |
| `cell=bright+eye_level+near+visible+low` | 10 | 0.889 [0.57–0.98] (n=9) | 0.889 [0.57–0.98] (n=9) | +0.000 | underpowered |
| `cell=bright+high_oblique+far+visible+low` | 10 | 1.000 [0.72–1.00] (n=10) | 1.000 [0.72–1.00] (n=10) | +0.000 | underpowered |
| `cell=bright+high_oblique+mid+visible+low` | 10 | 1.000 [0.72–1.00] (n=10) | 1.000 [0.72–1.00] (n=10) | +0.000 | underpowered |
| `cell=dim+eye_level+mid+partial+low` | 10 | 1.000 [0.72–1.00] (n=10) | 1.000 [0.72–1.00] (n=10) | +0.000 | underpowered |
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
| baseline model fingerprint | `359aca11e185cebeed43b1287dc6fd9e` |
| candidate model fingerprint | `4deba81e051acad493af5f33db9f04f8` |

