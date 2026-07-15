#!/bin/bash
# 按 Agentic4Systems Track-C 提交规范打包压缩包
#
# 用法:
#   TRACKC_MEMBERS="20260001张三-20260002李四-20260003王五" \
#     bash scripts/pack_trackc_submission.sh
#
# 输出:
#   dist/TrackC-<成员信息>.zip

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export GIT_DIR="${GIT_DIR:-/tmp/pa-soc-git.git}"
export GIT_WORK_TREE="${GIT_WORK_TREE:-$ROOT}"

MEMBERS="${TRACKC_MEMBERS:-20260001张三-20260002李四-20260003王五}"
PKG_NAME="TrackC-${MEMBERS}"
STAGING="$ROOT/dist/${PKG_NAME}"
ZIP_PATH="$ROOT/dist/${PKG_NAME}.zip"

echo "=== Track-C 提交打包 ==="
echo "成员标识: ${MEMBERS}"
echo "输出: ${ZIP_PATH}"

rm -rf "$STAGING"
mkdir -p "$STAGING"/{C1/compiler,C2/agents,C3}

# ── C1 ──────────────────────────────────────────────
echo "[C1] compiler/"
cp -R "$ROOT/trackc_submission/C1/compiler/"* "$STAGING/C1/compiler/"
chmod +x "$STAGING/C1/compiler/aec-cc"

# ── C2 ──────────────────────────────────────────────
echo "[C2] libaec.so + agents/"
LIBAEC_SRC="${LIBAEC_SO:-$ROOT/runtime/libaec.so}"

if [ ! -f "$LIBAEC_SRC" ]; then
    echo "  构建 libaec.so (需 Linux x86-64) ..."
    if make -C "$ROOT/runtime" 2>/dev/null; then
        LIBAEC_SRC="$ROOT/runtime/libaec.so"
    elif command -v docker >/dev/null 2>&1; then
        echo "  尝试 Docker 构建 ..."
        docker run --rm -v "$ROOT:/work" -w /work/runtime \
            gcc:13 bash -lc '
                apt-get update -qq && apt-get install -y -qq make g++ >/dev/null
                cp -R /work/third_party/starter-kit /tmp/sk 2>/dev/null || true
                make -C /work/runtime 2>&1
            ' && LIBAEC_SRC="$ROOT/runtime/libaec.so"
    fi
fi

if [ ! -f "$LIBAEC_SRC" ]; then
    SK="$ROOT/third_party/starter-kit/libaec.so"
    if [ -f "$SK" ]; then
        LIBAEC_SRC="$SK"
    fi
fi

if [ ! -f "$LIBAEC_SRC" ]; then
    echo ""
    echo "[error] 未找到 libaec.so。请在 Linux 环境构建后指定路径:"
    echo "  LIBAEC_SO=/path/to/libaec.so bash scripts/pack_trackc_submission.sh"
    echo "  或: bash runtime/setup_starter_kit.sh && make -C runtime"
    exit 1
fi

cp "$LIBAEC_SRC" "$STAGING/C2/libaec.so"
cp "$ROOT/agents/dma_agent.py" "$STAGING/C2/agents/"
cp "$ROOT/agents/kernel_agent.py" "$STAGING/C2/agents/"

# ── C3 ──────────────────────────────────────────────
echo "[C3] scheduler + readme.md"
cp "$ROOT/software/scheduler/pa_scheduler.py" "$STAGING/C3/"
cp "$ROOT/trackc_submission/C3/infer_worker.py" "$STAGING/C3/"
cp "$ROOT/trackc_submission/C3/readme.md" "$STAGING/C3/"
chmod +x "$STAGING/C3/infer_worker.py"

# ── 校验目录结构 ────────────────────────────────────
echo ""
echo "=== 目录结构校验 ==="
for path in \
    "C1/compiler/aec-cc" \
    "C1/compiler/src/aec_cc.py" \
    "C2/libaec.so" \
    "C2/agents/dma_agent.py" \
    "C2/agents/kernel_agent.py" \
    "C3/pa_scheduler.py" \
    "C3/infer_worker.py" \
    "C3/readme.md"; do
    if [ -e "$STAGING/$path" ]; then
        echo "  ✓ $path"
    else
        echo "  ✗ 缺失: $path"
        exit 1
    fi
done

# ── 打 zip ──────────────────────────────────────────
mkdir -p "$ROOT/dist"
rm -f "$ZIP_PATH"
(
    cd "$ROOT/dist"
    zip -r "${PKG_NAME}.zip" "${PKG_NAME}"
)

echo ""
echo "✓ 打包完成: ${ZIP_PATH}"
echo ""
echo "解压后结构:"
echo "  ${PKG_NAME}/"
echo "  ├── C1/compiler/aec-cc"
echo "  ├── C2/libaec.so"
echo "  └── C3/readme.md"
echo ""
echo "修改成员信息:"
echo "  TRACKC_MEMBERS=\"20260001张三-20260002李四-20260003王五\" bash scripts/pack_trackc_submission.sh"
