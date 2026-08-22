# Physical AI Crash-Test Lab — Coverage and Comparison Report

- **Scenario suite:** `warehouse_ppe_v2`
- **Test manifest:** `warehouse_ppe_v2-test`
- **Manifest fingerprint:** `aae5a75f676c0b5a9d5cd8d0530ad154`
- **Baseline model:** `helmet-detector@arm-bulk` (fingerprint `071cd41feced957d3a58683bf9300392`)
- **Candidate model:** `helmet-detector@candidate-v2` (fingerprint `f214366b1bfcd687be647348d1b4d148`)
- **Frames evaluated:** 864
- **Data source:** `isaac_sim_replicator`
- **Schema version:** `1.0.0`
- **Generated:** 2026-08-22T03:43:37Z

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
| hard_hat recall | 0.930 [0.90–0.95] (n=455) |
| hard_hat precision | 0.964 [0.94–0.98] (n=439) |
| person recall | 0.932 [0.91–0.95] (n=827) |
| frame accuracy (compliance verdict) | 0.833 [0.81–0.86] (n=864) |
| **dangerous miss rate** | **0.000 [0.00–0.01] (n=288)** |
| false alarm rate | 0.250 [0.22–0.29] (n=576) |

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
| `lighting×distance=normal+far` | lighting×distance | 96 | 0.778 [0.64–0.87] (n=45) |
| `distance×helmet_state=far+partial` | distance×helmet_state | 96 | 0.821 [0.71–0.89] (n=67) |
| `camera_angle×helmet_state=high_oblique+partial` | camera_angle×helmet_state | 144 | 0.845 [0.75–0.91] (n=84) |
| `lighting×distance=dim+far` | lighting×distance | 96 | 0.878 [0.76–0.94] (n=49) |
| `distance=far` | distance | 288 | 0.855 [0.79–0.90] (n=138) |
| `lighting×distance=bright+far` | lighting×distance | 96 | 0.909 [0.79–0.96] (n=44) |
| `distance×helmet_state=far+visible` | distance×helmet_state | 96 | 0.887 [0.79–0.94] (n=71) |
| `lighting×distance=dim+mid` | lighting×distance | 96 | 0.917 [0.80–0.97] (n=48) |
| `lighting×distance=bright+mid` | lighting×distance | 96 | 0.929 [0.81–0.98] (n=42) |
| `lighting×helmet_state=normal+partial` | lighting×helmet_state | 96 | 0.904 [0.82–0.95] (n=73) |
| `distance×helmet_state=mid+partial` | distance×helmet_state | 96 | 0.910 [0.82–0.96] (n=67) |
| `lighting×helmet_state=dim+partial` | lighting×helmet_state | 96 | 0.911 [0.83–0.96] (n=79) |
| _… 23 further slices omitted_ | | | |

**Weakest adequately-powered slice:** `lighting×distance=normal+far` at 0.778 [0.64–0.87] (n=45).

**Worst factor interaction:** `lighting×distance=normal+far` at 0.778 [0.64–0.87] (n=45) — a combination effect that the single-factor margins average away.

## 5. Coverage gaps and underpowered slices

Reported so that thin coverage stays visible rather than being silently
omitted. These are **not** findings — the sample size cannot support a
conclusion in either direction.

| Condition slice | Dimension | Frames | Metric (95% CI) |
| --- | --- | --- | --- |
| `cell=normal+high_oblique+far+partial+low` | condition_cell | 16 | 0.333 [0.10–0.70] (n=6) |
| `cell=bright+high_oblique+mid+partial+low` | condition_cell | 16 | 0.600 [0.23–0.88] (n=5) |
| `cell=dim+high_oblique+far+partial+low` | condition_cell | 16 | 0.636 [0.35–0.85] (n=11) |
| `cell=normal+high_oblique+far+visible+low` | condition_cell | 16 | 0.667 [0.35–0.88] (n=9) |
| `cell=dim+high_oblique+mid+partial+low` | condition_cell | 16 | 0.778 [0.45–0.94] (n=9) |
| `cell=normal+high_oblique+mid+partial+low` | condition_cell | 16 | 0.857 [0.49–0.97] (n=7) |
| `cell=dim+high_oblique+mid+visible+low` | condition_cell | 16 | 0.889 [0.57–0.98] (n=9) |
| `cell=bright+high_oblique+far+partial+low` | condition_cell | 16 | 1.000 [0.57–1.00] (n=5) |
| `cell=bright+high_oblique+mid+visible+low` | condition_cell | 16 | 1.000 [0.61–1.00] (n=6) |
| `cell=bright+eye_level+far+partial+low` | condition_cell | 16 | 0.867 [0.62–0.96] (n=15) |
| `cell=normal+eye_level+far+partial+low` | condition_cell | 16 | 0.867 [0.62–0.96] (n=15) |
| `cell=bright+eye_level+far+visible+low` | condition_cell | 16 | 0.875 [0.64–0.97] (n=16) |
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
| overall `hard_hat_recall` | 0.930 [0.90–0.95] (n=455) | 0.941 [0.92–0.96] (n=455) | +0.011 |

A change is called material at |Δ| ≥ 0.05 and
significant at 95% by a two-proportion z-test on the difference. Slices
with fewer than 20 samples on either side receive no verdict at all — the
same bar section 4 applies to findings. Everything else is reported as
inconclusive rather than as a win.

### 6.1 Improved

_None._

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
| `cell=bright+high_oblique+near+partial+low` | 16 | 1.000 [0.80–1.00] (n=15) | 0.933 [0.70–0.99] (n=15) | -0.067 | underpowered |
| `cell=normal+eye_level+far+partial+low` | 16 | 0.867 [0.62–0.96] (n=15) | 0.800 [0.55–0.93] (n=15) | -0.067 | underpowered |
| `cell=bright+eye_level+far+visible+low` | 16 | 0.875 [0.64–0.97] (n=16) | 0.875 [0.64–0.97] (n=16) | +0.000 | underpowered |
| `cell=bright+eye_level+mid+partial+low` | 16 | 1.000 [0.80–1.00] (n=15) | 1.000 [0.80–1.00] (n=15) | +0.000 | underpowered |
| `cell=bright+eye_level+mid+visible+low` | 16 | 0.938 [0.72–0.99] (n=16) | 0.938 [0.72–0.99] (n=16) | +0.000 | underpowered |
| `cell=bright+eye_level+near+partial+low` | 16 | 1.000 [0.81–1.00] (n=16) | 1.000 [0.81–1.00] (n=16) | +0.000 | underpowered |
| `cell=bright+eye_level+near+visible+low` | 16 | 1.000 [0.81–1.00] (n=16) | 1.000 [0.81–1.00] (n=16) | +0.000 | underpowered |
| `cell=bright+high_oblique+far+partial+low` | 16 | 1.000 [0.57–1.00] (n=5) | 1.000 [0.57–1.00] (n=5) | +0.000 | underpowered |
| `cell=bright+high_oblique+far+visible+low` | 16 | 1.000 [0.68–1.00] (n=8) | 1.000 [0.68–1.00] (n=8) | +0.000 | underpowered |
| `cell=bright+high_oblique+mid+partial+low` | 16 | 0.600 [0.23–0.88] (n=5) | 0.600 [0.23–0.88] (n=5) | +0.000 | underpowered |
| `cell=bright+high_oblique+mid+visible+low` | 16 | 1.000 [0.61–1.00] (n=6) | 1.000 [0.61–1.00] (n=6) | +0.000 | underpowered |
| `cell=bright+high_oblique+near+visible+low` | 16 | 0.929 [0.69–0.99] (n=14) | 0.929 [0.69–0.99] (n=14) | +0.000 | underpowered |
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
| baseline model fingerprint | `071cd41feced957d3a58683bf9300392` |
| candidate model fingerprint | `f214366b1bfcd687be647348d1b4d148` |
