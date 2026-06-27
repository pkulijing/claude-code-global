#!/usr/bin/env bash
# PostToolUse hook: AI 改完文件后自动 fix（lint --fix + format），等价于编辑器的 fix-on-save。
# 只做能自动修的修复，残余 lint 问题留给 /commit 阶段统一抓取。
# Best-effort: 永不因工具失败阻塞 agent。

set -u

FILE=$(jq -r '.tool_input.file_path // empty' 2>/dev/null) || exit 0
[ -z "$FILE" ] && exit 0
[ -f "$FILE" ] || exit 0

case "$FILE" in
  *.py)
    # 顺序与 ruff 官方推荐一致：先 lint --fix，再 format
    # F401(unused-import) 不在分步 Edit 中途自动删：import 先加、usage 后补的中间态
    # 跨越 formatter 时会被误删 → 下次跑测 F821。残余 unused import 留给 /commit 抓取。
    uv run --quiet ruff check --fix --unfixable F401 --quiet "$FILE" >/dev/null 2>&1
    uv run --quiet ruff format "$FILE" >/dev/null 2>&1
    ;;
  *.md)
    command -v prettier >/dev/null 2>&1 \
      && prettier --write --log-level warn "$FILE" >/dev/null 2>&1
    ;;
esac

exit 0
