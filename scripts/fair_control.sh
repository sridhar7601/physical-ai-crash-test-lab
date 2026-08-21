#!/usr/bin/env bash
# The fair control arm: bulk collection sampled from EVERY condition.
#
# The earlier control drew only from the hard conditions, ~20% of which were the
# target condition by construction -- far too generous to the control. Real bulk
# collection draws from the whole distribution, where the weak condition is rare
# (6 of 54 cells). This arm reproduces that, at identical training volume to the
# targeted arm.
set -u
cd /home/ubuntu/crashtestlab
DET=/home/ubuntu/detenv/bin/python
ART=artifacts
SUITE=warehouse_ppe_v1
N=250
mkdir -p records
stamp() { date -u +"[%H:%M:%S] $*"; }

stamp "=== 1. build an all-conditions pool (fresh frames, no collisions) ==="
python3 -m crashlab.pipeline pool --suite $SUITE \
    --test-manifest $ART/${SUITE}-test.json \
    --frames-per-condition 6 --replicate-offset 2000 \
    --disjoint-from $ART/${SUITE}-train.json $ART/${SUITE}-remediation.json \
    --out $ART/${SUITE}-pool.json

stamp "=== 2. render the pool ==="
/opt/IsaacSim/python.sh -m crashlab.generator.generate \
    --manifest $ART/${SUITE}-pool.json --out datasets/pool \
    --subframes 16 --width 960 --height 540 --resume 2>&1 | grep -E "^\[gen\] (done|man|scen)" 

stamp "=== 3. sample $N frames from ALL conditions (the fair bulk arm) ==="
$DET -m crashlab.detector.yolo_dataset --dataset datasets/pool \
    --out yolo/extra_bulk_all --filter all --sample $N

stamp "=== 4. how much of that sample is the target condition? ==="
python3 - <<'PYEOF'
import json, os
d = "datasets/pool/labels"
picked = {p.replace(".txt", "") for p in os.listdir("yolo/extra_bulk_all/labels/train")} | \
         {p.replace(".txt", "") for p in os.listdir("yolo/extra_bulk_all/labels/val")}
tgt = tot = 0
for sid in picked:
    lab = json.load(open(f"{d}/{sid}.json"))
    c = lab["scenario"]["condition"]
    tot += 1
    if c["lighting"] == "dim" and c["helmet_state"] == "partial":
        tgt += 1
print(f"  target condition in the bulk sample: {tgt}/{tot} = {tgt/tot:.1%}")
print(f"  (the earlier 'hard' control had roughly 20%; the matrix rate is 6/54 = 11.1%)")
PYEOF

stamp "=== 5. assemble arm_bulk_all ==="
rm -rf yolo/arm_bulk_all
$DET -m crashlab.detector merge --out yolo/arm_bulk_all \
    --sources yolo/baseline yolo/extra_bulk_all --label "easy + all-conditions bulk (n=$N)"

echo
stamp "VOLUME CHECK against the targeted arm"
for arm in arm_bulk_all arm_targeted; do
  echo "  $arm train=$(ls yolo/$arm/images/train | wc -l) val=$(ls yolo/$arm/images/val | wc -l)"
done
echo

stamp "=== 6. train arm_bulk_all ==="
$DET -m crashlab.detector.train --data yolo/arm_bulk_all/data.yaml \
    --out runs --name arm_bulk_all --epochs 40 --imgsz 640 --batch 16 \
    --record records/arm_bulk_all.json 2>&1 | tail -6
W=$(python3 -c "import json;print(json.load(open('records/arm_bulk_all.json'))['weights'])")
FP=$(python3 -c "import json;print(json.load(open('records/arm_bulk_all.json'))['weights_fingerprint'])")

stamp "=== 7. predict on the locked test suite ==="
$DET -m crashlab.detector.predict --weights "$W" \
    --dataset datasets/test --out preds/arm_bulk_all 2>&1 | tail -3

stamp "=== 8. diagnose ==="
python3 -m crashlab.pipeline diagnose \
    --dataset datasets/test --predictions preds/arm_bulk_all \
    --manifest $ART/${SUITE}-test.json \
    --model-name helmet-detector --model-version arm-bulk-all \
    --model-fingerprint "$FP" \
    --model-notes "195 easy frames plus $N frames sampled from ALL conditions. Volume-matched to arm_targeted." \
    --out results/arm_bulk_all 2>&1 | sed -n '/OVERALL/,/withheld/p' | head -16

stamp "=== 9. FAIR CONTROL: all-conditions bulk vs targeted, equal volume ==="
python3 -m crashlab.pipeline compare --baseline results/arm_bulk_all \
    --candidate results/arm_targeted --manifest $ART/${SUITE}-test.json \
    --out results/fair_control_report --stamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

stamp "=== FAIR CONTROL COMPLETE ==="
