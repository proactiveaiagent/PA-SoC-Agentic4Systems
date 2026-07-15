#!/bin/bash
# 在 Linux x86-64 上构建 C2/libaec.so（macOS 无法链接 libaec_device.so）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

bash "$ROOT/runtime/setup_starter_kit.sh"
make -C "$ROOT/runtime"

echo "✓ 已生成: $ROOT/runtime/libaec.so"
echo ""
echo "打包提交:"
echo "  TRACKC_MEMBERS=\"3054_3尹杰亮\" bash $ROOT/scripts/pack_trackc_submission.sh"
