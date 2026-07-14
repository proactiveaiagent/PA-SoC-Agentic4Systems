#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SUITE="${2:-public}"
OUTPUT="${4:-/tmp/aec_tests}"
mkdir -p "$OUTPUT"
python3 "$ROOT/tests/run_tests.py" | tee "$OUTPUT/test.log"
echo "[tests] suite=$SUITE 完成"
