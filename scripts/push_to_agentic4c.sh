#!/bin/bash
# 推送到 GitHub 组织 AGENTIC4system-C 下的仓库 main 分支
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export GIT_DIR="${GIT_DIR:-/tmp/pa-soc-git.git}"
export GIT_WORK_TREE="${GIT_WORK_TREE:-$ROOT}"

ORG="AGENTIC4system-C"
REPO_NAME="${REPO_NAME:-PA-SoC-Agentic4Systems}"
HTTPS_URL="https://github.com/${ORG}/${REPO_NAME}.git"
SSH_URL="git@${ORG}.github.com:${ORG}/${REPO_NAME}.git"
REMOTE="${REMOTE:-agentic4c}"

GIT_HTTPS_OPTS=(
    -c http.version=HTTP/1.1
    -c http.postBuffer=524288000
)

git remote remove "$REMOTE" 2>/dev/null || true
git remote add "$REMOTE" "$HTTPS_URL"

echo "=== 推送到 ${ORG}/${REPO_NAME} (main) ==="
echo "    $HTTPS_URL"
for i in 1 2 3; do
    if git "${GIT_HTTPS_OPTS[@]}" push "$REMOTE" main:main 2>&1; then
        echo "✓ 推送成功"
        exit 0
    fi
    echo "[重试 $i/3] HTTPS 失败，5秒后重试..."
    sleep 5
done

echo ""
echo "=== 切换 SSH 重试 ==="
git remote set-url "$REMOTE" "git@github.com:${ORG}/${REPO_NAME}.git"
if git push "$REMOTE" main:main 2>&1; then
    echo "✓ SSH 推送成功"
    exit 0
fi

echo ""
echo "推送失败。组织 ${ORG} 下尚无公开仓库时，请先创建空仓库："
echo "  https://github.com/organizations/${ORG}/repositories/new"
echo "  仓库名: ${REPO_NAME}  (可通过 REPO_NAME=xxx 修改)"
echo "  可见性: Public"
echo "  不要勾选 README / .gitignore / license"
echo ""
echo "创建后重新运行:"
echo "  bash $ROOT/scripts/push_to_agentic4c.sh"
exit 1
