#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "[build] PA-SoC AEC GPGPU"
bash runtime/setup_starter_kit.sh 2>/dev/null || true
make -C cmodel all
make -C runtime all 2>/dev/null || echo "[warn] runtime 需要 starter-kit libaec_device.so"
echo "[build] 完成"
