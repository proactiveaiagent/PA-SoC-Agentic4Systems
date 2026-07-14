#!/bin/bash
# 稳定推送到 GitHub（HTTPS 失败时自动切换 SSH 并重试）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export GIT_DIR="${GIT_DIR:-/tmp/pa-soc-git.git}"
export GIT_WORK_TREE="${GIT_WORK_TREE:-$ROOT}"

HTTPS_URL="https://github.com/proactiveaiagent/PA-SoC-Agentic4Systems.git"
SSH_URL="git@github.com:proactiveaiagent/PA-SoC-Agentic4Systems.git"

git remote set-url origin "$HTTPS_URL"

echo "=== 尝试 HTTPS 推送 ==="
for i in 1 2 3; do
    if git push -u origin main 2>&1; then
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
echo "推送失败。请尝试："
echo "  1. 检查网络 / VPN / 代理"
echo "  2. 在 GitHub Settings → SSH keys 添加公钥："
echo "     cat ~/.ssh/id_ed25519.pub"
echo "  3. 手动切换 SSH 后推送："
echo "     git remote set-url origin $SSH_URL"
echo "     git push -u origin main"
exit 1
