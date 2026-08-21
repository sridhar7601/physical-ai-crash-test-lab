#!/usr/bin/env bash
# Run this ON the GPU instance, immediately after connecting.
#
# Purpose: answer the go/no-go gate questions in PLAN.md section 13 before
# spending sprint hours. The AMI is OV-Template-aws-ubuntu-isaac_sim-*, so
# Isaac Sim is expected to be pre-installed — this confirms it and locates it.
#
# Paste the entire output back into the conversation.

echo "=================================================================="
echo " 1. GPU AND DRIVER"
echo "=================================================================="
nvidia-smi 2>&1 || echo ">>> FAIL: no NVIDIA driver. This is blocking."
echo
echo "--- driver / CUDA versions ---"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv 2>&1 || true
cat /proc/driver/nvidia/version 2>/dev/null || true

echo
echo "=================================================================="
echo " 2. WHERE IS ISAAC SIM?"
echo "=================================================================="
for p in /isaac-sim "$HOME/isaac-sim" /opt/nvidia /opt/isaac-sim \
         "$HOME/.local/share/ov" /usr/local/isaac-sim; do
  [ -e "$p" ] && echo "FOUND: $p" && ls -la "$p" 2>/dev/null | head -12 && echo
done
echo "--- home directory ---"
ls -la "$HOME"
echo
echo "--- anything named isaac / omniverse on disk ---"
find / -maxdepth 4 \( -iname "*isaac*" -o -iname "*omniverse*" \) \
     -not -path "*/proc/*" 2>/dev/null | head -25
echo
echo "--- launcher scripts (isaac-sim.sh / python.sh) ---"
find / -maxdepth 5 -name "isaac-sim*.sh" -o -maxdepth 5 -name "python.sh" 2>/dev/null | head -10

echo
echo "=================================================================="
echo " 3. DOCKER (Isaac Sim often ships as a container)"
echo "=================================================================="
if command -v docker >/dev/null; then
  docker images 2>&1 | head -20
  echo "--- running containers ---"
  docker ps 2>&1 | head -10
else
  echo "docker not installed"
fi

echo
echo "=================================================================="
echo " 4. REMOTE DESKTOP (Amazon DCV) — needed to see the 3D viewport"
echo "=================================================================="
if command -v dcv >/dev/null || systemctl list-unit-files 2>/dev/null | grep -q dcv; then
  echo "DCV appears INSTALLED — big time saver."
  systemctl status dcvserver --no-pager 2>&1 | head -8
  echo "--- existing sessions ---"
  sudo dcv list-sessions 2>&1 | head -5
else
  echo "DCV not found — will need setup per the AWS guide."
fi
echo "--- listening ports (looking for 8443) ---"
(ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null) | head -20

echo
echo "=================================================================="
echo " 5. PYTHON / PYTORCH / GPU VISIBILITY"
echo "=================================================================="
echo "python3: $(python3 --version 2>&1)"
python3 - <<'PY' 2>&1 || echo "torch not available in system python (may live inside Isaac Sim's bundled python)"
import torch
print("torch:", torch.__version__)
print("cuda available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("device:", torch.cuda.get_device_name(0))
PY

echo
echo "=================================================================="
echo " 6. DISK AND MEMORY (rendered frames consume space quickly)"
echo "=================================================================="
df -h | grep -vE "^tmpfs|^devtmpfs"
echo
free -h
echo
echo "vCPUs: $(nproc)"

echo
echo "=================================================================="
echo " 7. OS"
echo "=================================================================="
. /etc/os-release 2>/dev/null && echo "$PRETTY_NAME"
uname -r
echo
echo "=========================== DONE ================================="
echo "Gate check — all of these must be true before committing the sprint:"
echo "  [ ] nvidia-smi shows a GPU"
echo "  [ ] Isaac Sim located on disk or as a container image"
echo "  [ ] DCV present, or a clear path to installing it"
echo "  [ ] torch sees CUDA (system python or Isaac Sim's bundled python)"
echo "  [ ] >50GB free disk"
