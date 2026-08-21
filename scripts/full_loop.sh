#!/usr/bin/env bash
# The complete crash-test loop on real rendered data.
#
# Stages are independent so any one can be re-run. GPU stages use the detenv
# virtualenv; analysis stages use plain python3 (pure stdlib).
set -u
cd /home/ubuntu/crashtestlab
mkdir -p records
DET=/home/ubuntu/detenv/bin/python
ART=artifacts
SUITE=warehouse_ppe_v1
stamp() { date -u +"[%H:%M:%S] $*"; }

stage="${1:-all}"

if [[ "$stage" == "baseline" || "$stage" == "all" ]]; then
  stamp "=== 1. export EASY training set (the realistic data gap) ==="
  $DET -m crashlab.detector.yolo_dataset --dataset datasets/train \
      --out yolo/baseline --filter easy

  stamp "=== 2. train baseline ==="
  $DET -m crashlab.detector.train --data yolo/baseline/data.yaml \
      --out runs --name baseline --epochs 40 --imgsz 640 --batch 16 \
      --record records/baseline.json 2>&1 | tail -20
  BW=$(python3 -c "import json;print(json.load(open('records/baseline.json'))['weights'])")
  BFP=$(python3 -c "import json;print(json.load(open('records/baseline.json'))['weights_fingerprint'])")
  stamp "baseline weights: $BW"

  stamp "=== 3. baseline predictions over the locked test suite ==="
  $DET -m crashlab.detector.predict --weights "$BW" \
      --dataset datasets/test --out preds/baseline 2>&1 | tail -6

  stamp "=== 4. diagnose ==="
  python3 -m crashlab.pipeline diagnose \
      --dataset datasets/test --predictions preds/baseline \
      --manifest $ART/${SUITE}-test.json \
      --model-name helmet-detector --model-version baseline-v1 \
      --model-fingerprint "$BFP" \
      --model-notes "Trained only on bright, unoccluded, near/mid frames (filter=easy). Disclosed deliberately." \
      --out results/baseline

  stamp "=== 5. targeted remediation request ==="
  python3 -m crashlab.pipeline remediate --analysis results/baseline \
      --suite $SUITE --test-manifest $ART/${SUITE}-test.json \
      --frames-per-condition 50 --out $ART/${SUITE}-remediation.json
fi

if [[ "$stage" == "candidate" || "$stage" == "all" ]]; then
  stamp "=== 6. render the remediation frames ==="
  /opt/IsaacSim/python.sh -m crashlab.generator.generate \
      --manifest $ART/${SUITE}-remediation.json --out datasets/remediation \
      --subframes 16 --width 960 --height 540 --resume 2>&1 | grep -E "^\[gen\]" | tail -8

  stamp "=== 7. export candidate training set (easy + targeted) ==="
  $DET -m crashlab.detector.yolo_dataset --dataset datasets/remediation \
      --out yolo/remediation --filter all
  # Merge through the library, not cp: the merge writes a manifest recording
  # what actually went in. Copying files in afterwards left the manifest
  # claiming 195 images for a model trained on 689.
  rm -rf yolo/candidate
  $DET -m crashlab.detector merge --out yolo/candidate \
      --sources yolo/baseline yolo/remediation --label "easy + targeted remediation"
  echo "candidate train images: $(ls yolo/candidate/images/train | wc -l)"

  stamp "=== 8. train candidate ==="
  $DET -m crashlab.detector.train --data yolo/candidate/data.yaml \
      --out runs --name candidate --epochs 40 --imgsz 640 --batch 16 \
      --record records/candidate.json 2>&1 | tail -20
  CW=$(python3 -c "import json;print(json.load(open('records/candidate.json'))['weights'])")
  CFP=$(python3 -c "import json;print(json.load(open('records/candidate.json'))['weights_fingerprint'])")
  stamp "candidate weights: $CW"

  stamp "=== 9. candidate predictions over the SAME locked test suite ==="
  $DET -m crashlab.detector.predict --weights "$CW" \
      --dataset datasets/test --out preds/candidate 2>&1 | tail -6

  stamp "=== 10. diagnose candidate ==="
  python3 -m crashlab.pipeline diagnose \
      --dataset datasets/test --predictions preds/candidate \
      --manifest $ART/${SUITE}-test.json \
      --model-name helmet-detector --model-version candidate-v2 \
      --model-fingerprint "$CFP" \
      --model-notes "Baseline training set plus targeted frames for the weakest measured condition." \
      --out results/candidate

  stamp "=== 11. compare on the unchanged suite ==="
  python3 -m crashlab.pipeline compare --baseline results/baseline \
      --candidate results/candidate --manifest $ART/${SUITE}-test.json \
      --out results/report --stamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
fi

stamp "=== LOOP STAGE '$stage' COMPLETE ==="
