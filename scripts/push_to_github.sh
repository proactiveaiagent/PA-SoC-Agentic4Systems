#!/bin/bash
# 稳定推送到 GitHub（HTTP/1.1 规避 HTTP2 错误，HTTPS 失败时切换 SSH）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export GIT_DIR="${GIT_DIR:-/tmp/pa-soc-git.git}"
export GIT_WORK_TREE="${GIT_WORK_TREE:-$ROOT}"

HTTPS_URL="https://github.com/proactiveaiagent/PA-SoC-Agentic4Systems.git"
SSH_URL="git@github.com:proactiveaiagent/PA-SoC-Agentic4Systems.git"

# 规避 "Error in the HTTP2 framing layer" / "Empty reply from server"
GIT_HTTPS_OPTS=(
    -c http.version=HTTP/1.1
    -c http.postBuffer=524288000
)

git remote set-url origin "$HTTPS_URL"

echo "=== 尝试 HTTPS 推送 (HTTP/1.1) ==="
for i in 1 2 3; do
    if git "${GIT_HTTPS_OPTS[@]}" push -u origin main 2>&1; then
        echo "✓ HTTPS 推送成功"
        exit 0
    fi
    echo "[重试 $i/3] HTTPS 失败，5秒后重试..."
    sleep 5
done

echo ""
echo "=== 切换 SSH 推送 ==="
git remote set-url origin "$SSH_URL"

if ssh -T -o ConnectTimeout=15 git@github.com 2>&1 | grep -qi "successfully authenticated"; then
    git push -u origin main
    echo "✓ SSH 推送成功"
    exit 0
fi

echo ""
echo "推送失败。请在本机终端依次尝试："
echo ""
echo "  # 方案 1：强制 HTTP/1.1（修复 HTTP2 framing 错误）"
echo "  export GIT_DIR=/tmp/pa-soc-git.git GIT_WORK_TREE=$ROOT"
echo "  git -c http.version=HTTP/1.1 push -u origin main"
echo ""
echo "  # 方案 2：改用 SSH（HTTPS 不稳定时更可靠）"
echo "  git remote set-url origin $SSH_URL"
echo "  git push -u origin main"
echo ""
echo "  # 方案 3：若使用代理（如 Clash 7897），为 GitHub 单独配置或临时关闭"
echo "  git config --global http.https://github.com.proxy http://127.0.0.1:7897"
echo "  # 或：git config --global --unset http.proxy"
echo ""
echo "  # 添加 SSH 公钥：GitHub → Settings → SSH keys"
echo "  cat ~/.ssh/id_ed25519.pub"
exit 1
