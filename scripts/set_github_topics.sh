#!/bin/bash
# 为 GitHub 仓库添加 Topics 标签
set -euo pipefail

REPO="proactiveaiagent/PA-SoC-Agentic4Systems"
TOPICS='["gpgpu","proactive-agent","agentic4systems","aec-isa","chip-design","soc","ai-agent","reinforcement-learning"]'

CREDS=$(printf "protocol=https\nhost=github.com\n\n" | git credential-osxkeychain get 2>/dev/null || true)
TOKEN=$(echo "$CREDS" | awk -F= '/^password=/{print $2}')
USER=$(echo "$CREDS" | awk -F= '/^username=/{print $2}')

if [ -z "$TOKEN" ]; then
    echo "错误: 未找到 GitHub token，请手动在仓库 Settings → Topics 添加："
    echo "  gpgpu, proactive-agent, agentic4systems, aec-isa, chip-design, soc, ai-agent, reinforcement-learning"
    exit 1
fi

HTTP=$(curl -s -o /tmp/topics_resp.json -w "%{http_code}" \
    -X PUT \
    -H "Authorization: token $TOKEN" \
    -H "Accept: application/vnd.github.mercy-preview+json" \
    "https://api.github.com/repos/$REPO/topics" \
    -d "{\"names\":$TOPICS}")

if [ "$HTTP" = "200" ] || [ "$HTTP" = "201" ]; then
    echo "Topics 已添加: https://github.com/$REPO"
    cat /tmp/topics_resp.json
else
    echo "添加失败 (HTTP $HTTP):"
    cat /tmp/topics_resp.json
    exit 1
fi
