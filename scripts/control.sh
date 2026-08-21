#!/usr/bin/env bash
# Volume-matched control: does TARGETING beat BULK at equal data volume?
#
#   arm_bulk     = 195 easy + N frames sampled at random from the hard conditions
#   arm_targeted = 195 easy + N frames from the measured weak condition
#
# Same base, same N, same test suite. The only difference is where the extra
# frames were aimed, so the gap between the arms isolates the effect of
# targeting from the effect of simply having more data.
set -u
cd /home/ubuntu/crashtestlab
DET=/home/ubuntu/detenv/bin/python
ART=artifacts
SUITE=warehouse_ppe_v1
N=250
mkdir -p records
stamp() { date -u +"[%H:%M:%S] $*"; }

stamp "=== extra frames: BULK (random hard conditions), n=$N ==="
$DET -m crashlab.detector.yolo_dataset --dataset datasets/train \
    --out yolo/extra_bulk --filter hard --sample $N

stamp "=== extra frames: TARGETED (the measured weak condition), n=$N ==="
$DET -m crashlab.detector.yolo_dataset --dataset datasets/remediation \
    --out yolo/extra_targeted --filter all --sample $N

for arm in bulk targeted; do
  stamp "=== assemble arm_$arm ==="
  rm -rf yolo/arm_$arm
  $DET -m crashlab.detector merge --out yolo/arm_$arm \
      --sources yolo/baseline yolo/extra_$arm --label "easy + $arm extra (n=$N)"
done

echo
stamp "VOLUME CHECK (the arms must match)"
for arm in bulk targeted; do
  echo "  arm_$arm train=$(ls yolo/arm_$arm/images/train | wc -l) val=$(ls yolo/arm_$arm/images/val | wc -l)"
done
echo

for arm in bulk targeted; do
  stamp "=== train arm_$arm ==="
  $DET -m crashlab.detector.train --data yolo/arm_$arm/data.yaml \
      --out runs --name arm_$arm --epochs 40 --imgsz 640 --batch 16 \
      --record records/arm_$arm.json 2>&1 | tail -8
  W=$(python3 -c "import json;print(json.load(open('records/arm_$arm.json'))['weights'])")
  FP=$(python3 -c "import json;print(json.load(open('records/arm_$arm.json'))['weights_fingerprint'])")

  stamp "=== predict arm_$arm on the locked test suite ==="
  $DET -m crashlab.detector.predict --weights "$W" \
      --dataset datasets/test --out preds/arm_$arm 2>&1 | tail -3

  stamp "=== diagnose arm_$arm ==="
  python3 -m crashlab.pipeline diagnose \
      --dataset datasets/test --predictions preds/arm_$arm \
      --manifest $ART/${SUITE}-test.json \
      --model-name helmet-detector --model-version "arm-$arm" \
      --model-fingerprint "$FP" \
      --model-notes "195 easy frames plus $N $arm frames. Volume-matched against the other arm." \
      --out results/arm_$arm 2>&1 | sed -n '/OVERALL/,/withheld/p' | head -18
done

stamp "=== CONTROLLED COMPARISON: bulk vs targeted, equal volume ==="
python3 -m crashlab.pipeline compare --baseline results/arm_bulk \
    --candidate results/arm_targeted --manifest $ART/${SUITE}-test.json \
    --out results/control_report --stamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

stamp "=== CONTROL COMPLETE ==="
