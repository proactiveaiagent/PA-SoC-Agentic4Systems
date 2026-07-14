#!/bin/bash
# 获取竞赛官方 starter-kit（C2 Runtime）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="$ROOT/third_party/starter-kit"
CONTEST_REPO="https://github.com/ephonic/Agentic4SystemSummerSchoolContest.git"

if [ -f "$TARGET/include/aec_runtime.h" ]; then
    echo "[setup] starter-kit 已存在: $TARGET"
    exit 0
fi

mkdir -p "$ROOT/third_party"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

echo "[setup] 克隆竞赛仓库..."
git clone --depth 1 --filter=blob:none --sparse "$CONTEST_REPO" "$TMP/contest"
cd "$TMP/contest"
git sparse-checkout set Track-C/C2-runtime/starter-kit

echo "[setup] 复制 starter-kit..."
cp -R Track-C/C2-runtime/starter-kit "$TARGET"
echo "[setup] 完成: $TARGET"
ls "$TARGET/include/"
