#!/usr/bin/env bash
# 用 ChatGPT 登录的 Codex 执行一次性任务
# 用法: ./codex_run.sh "任务描述" [工作目录] [超时秒数]
# 环境里 HOME 可能被 Hermes 改写，这里强制用 /root 让 codex 读到正确的 ChatGPT 会话
set -euo pipefail

TASK="${1:?需要提供任务描述}"
WORKDIR="${2:-/root}"
TIMEOUT="${3:-300}"

export HOME=/root
export PATH="/root/.nvm/versions/node/v22.22.0/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
# 清掉可能干扰的中转环境变量
unset ANTHROPIC_BASE_URL ANTHROPIC_AUTH_TOKEN 2>/dev/null || true

cd "$WORKDIR"

echo ">>> [codex_run] 工作目录: $WORKDIR"
echo ">>> [codex_run] 登录状态:"
codex login status 2>&1 || echo "  (无法获取登录状态)"

echo ">>> [codex_run] 开始执行任务..."
timeout "$TIMEOUT" codex exec --skip-git-repo-check "$TASK"
CODE=$?
echo ""
echo ">>> [codex_run] 完成，退出码: $CODE"
exit $CODE
