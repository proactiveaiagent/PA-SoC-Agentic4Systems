#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SUITE="${2:-public}"
OUTPUT="${4:-$ROOT/evidence/regression}"
mkdir -p "$OUTPUT"

echo "=== PA-SoC 测试回归 ==="

# 1. 单元测试
python3 "$ROOT/tests/run_tests.py" | tee "$OUTPUT/unit_test.log"

# 2. 官方 testcases 回归（CModel）
echo ""
echo "--- 官方 testcases 回归 ---"
python3 "$ROOT/tests/regression/run_regression.py" \
    --target cmodel \
    --output "$OUTPUT" \
    | tee -a "$OUTPUT/official_regression.log"

echo "[tests] suite=$SUITE 完成 → $OUTPUT"
