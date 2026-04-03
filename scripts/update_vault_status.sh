#!/bin/bash
# MCP 커밋 후 Vault 현황 자동 업데이트
# git post-commit hook 또는 deploy 스크립트에서 호출

set -e
cd /opt/nexus-finance-mcp

# 현재 MCP 상태 수집
VERSION=$(grep -o '"version": "[^"]*"' mcp_servers/gateway/gateway_server.py | head -1 | cut -d'"' -f4 2>/dev/null || echo "unknown")
HEALTH=$(curl -s http://localhost:8100/health 2>/dev/null || echo '{}')
TOOL_COUNT=$(echo "$HEALTH" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_count',0))" 2>/dev/null || echo "?")
SERVER_COUNT=$(echo "$HEALTH" | python3 -c "import sys,json; print(json.load(sys.stdin).get('loaded_servers',0))" 2>/dev/null || echo "?")
FAILED=$(echo "$HEALTH" | python3 -c "import sys,json; print(json.load(sys.stdin).get('failed_servers',0))" 2>/dev/null || echo "?")
GIT_HASH=$(git log --oneline -1 | cut -d' ' -f1)
DATE=$(date +%Y-%m-%d)

VAULT_FILE="/root/obsidian-vault/02-Areas/luxon-infra/MCP-Current-Status.md"

cat > "$VAULT_FILE" << EOF
---
title: MCP 현재 상태 (자동 업데이트)
date: ${DATE}
tags: [mcp, status, auto-generated]
---

# Nexus Finance MCP — 현재 상태

| 항목 | 값 |
|------|-----|
| 버전 | \`${VERSION}\` |
| 도구 수 | **${TOOL_COUNT}** |
| 서버 수 | **${SERVER_COUNT}** |
| 실패 서버 | ${FAILED} |
| Git | \`${GIT_HASH}\` |
| 업데이트 | ${DATE} |
| Health | \`http://localhost:8100/health\` |
| 외부 접속 | \`http://62.171.141.206/mcp\` (Bearer 토큰) |

## 연결 노트
- [[MCP-Usage-Guide]] — 활용 가이드
- [[MCP-v4.0-Status-20260403]] — v4.0 상세 현황
- [[MOC-Luxon-Infra]] — 전체 인프라

---
*\`scripts/update_vault_status.sh\` 에 의해 자동 생성*
EOF

# Vault git commit (if changed)
cd /root/obsidian-vault
if ! git diff --quiet "$VAULT_FILE" 2>/dev/null; then
    git add "$VAULT_FILE"
    git commit -m "Auto: MCP status update — ${TOOL_COUNT} tools / ${SERVER_COUNT} servers [${GIT_HASH}]" 2>/dev/null || true
fi

echo "Vault status updated: ${TOOL_COUNT} tools / ${SERVER_COUNT} servers"
