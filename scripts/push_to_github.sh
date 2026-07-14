#!/bin/bash
# 在 macOS 系统终端（非 Cursor 沙箱）中运行此脚本
set -euo pipefail

export GIT_DIR=/tmp/pa-soc-git.git
export GIT_WORK_TREE=/Users/jel/PA-SoC-Agentic4Systems

REPO_NAME="PA-SoC-Agentic4Systems"
DESCRIPTION="Proactive Agent SoC chip design for Agentic4Systems GPGPU competition 2026"

echo "=== PA-SoC GitHub 上传脚本 ==="

# 检查提交
git log -1 --oneline

# 尝试用 gh 创建仓库
if command -v gh &>/dev/null; then
    echo "使用 gh CLI 创建仓库..."
    gh auth status || gh auth login
    gh repo create "$REPO_NAME" --public --description "$DESCRIPTION" --source "$GIT_WORK_TREE" --remote origin --push
    gh repo view --web 2>/dev/null || true
    echo "完成！仓库地址: https://github.com/$(gh api user -q .login)/$REPO_NAME"
    exit 0
fi

# 回退：用 git credential + API 创建
echo "gh 未安装，使用 GitHub API..."
CREDS=$(printf "protocol=https\nhost=github.com\n\n" | git credential-osxkeychain get)
USER=$(echo "$CREDS" | awk -F= '/^username=/{print $2}')
TOKEN=$(echo "$CREDS" | awk -F= '/^password=/{print $2}')

if [ -z "$TOKEN" ]; then
    echo "错误：未找到 GitHub 凭据。请先运行: gh auth login"
    echo "或在 GitHub 网页创建空仓库后执行:"
    echo "  export GIT_DIR=/tmp/pa-soc-git.git GIT_WORK_TREE=/Users/jel/PA-SoC-Agentic4Systems"
    echo "  git remote add origin https://github.com/<你的用户名>/$REPO_NAME.git"
    echo "  git push -u origin main"
    exit 1
fi

echo "GitHub 用户: $USER"

# 创建仓库（若已存在则跳过）
HTTP_CODE=$(curl -s -o /tmp/gh_create.json -w "%{http_code}" \
    -X POST -H "Authorization: token $TOKEN" \
    -H "Accept: application/vnd.github+json" \
    https://api.github.com/user/repos \
    -d "{\"name\":\"$REPO_NAME\",\"description\":\"$DESCRIPTION\",\"private\":false}")

if [ "$HTTP_CODE" = "201" ]; then
    echo "仓库创建成功"
elif [ "$HTTP_CODE" = "422" ]; then
    echo "仓库已存在，继续推送..."
else
    cat /tmp/gh_create.json
    echo "创建失败 (HTTP $HTTP_CODE)"
    exit 1
fi

# 配置 remote 并推送
git remote remove origin 2>/dev/null || true
git remote add origin "https://github.com/$USER/$REPO_NAME.git"
git push -u origin main

echo ""
echo "=== 上传完成 ==="
echo "仓库地址: https://github.com/$USER/$REPO_NAME"
