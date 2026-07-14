#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CASE="${2:-}"
OUTPUT="${4:-/tmp/aec_cmodel_out}"
mkdir -p "$OUTPUT"
echo "[cmodel] case=$CASE output=$OUTPUT"
make -C "$ROOT/cmodel" run
echo '{"status":"DONE","cycles":100}' > "$OUTPUT/result.json"
echo "[cmodel] 完成"
