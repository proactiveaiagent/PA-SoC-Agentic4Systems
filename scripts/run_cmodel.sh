#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CASE="${2:-}"
OUTPUT="${4:-/tmp/aec_cmodel_out}"
mkdir -p "$OUTPUT"

bash "$ROOT/scripts/setup_testcases.sh"

if [ -n "$CASE" ] && [ -f "$CASE/case.yaml" ]; then
    REL=$(python3 -c "
import os,sys
p=sys.argv[1]
base=os.path.join('$ROOT/third_party/official-testcases/tests/aec_cases')
print(os.path.relpath(p, base))
" "$CASE")
    python3 "$ROOT/tests/regression/run_regression.py" --case "$REL" --output "$OUTPUT"
else
    python3 "$ROOT/tests/regression/run_regression.py" --target cmodel --output "$OUTPUT"
fi
