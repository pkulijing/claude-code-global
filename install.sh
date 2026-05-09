#!/usr/bin/env bash
set -euo pipefail

# 自动检测仓库根目录
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_DIR="$HOME/.claude"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()    { echo -e "${BLUE}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC}   $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }

# 由本仓库管理的 hook 条目，command 末尾必须带这条 bash 注释作为身份标记。
# 完整格式（严格匹配）：# @claude-code-global:<hook-name>
# 例如：bash $HOME/.claude/hooks/fix-after-edit.sh # @claude-code-global:fix-after-edit
#
# 模型：把 settings.json 里所有带此标记的 hook 条目看作"由本仓库管理的 hook 集合"，
# 用 hook-name 唯一标识。每次 install 做集合差分：
#   - 旧 ∩ 新（同名）  → 用基线版本替换（字段变化也覆盖）
#   - 旧 \ 新（仅旧有）→ 删除
#   - 新 \ 旧（仅新有）→ 新增
# 实现上等价于：剔除所有 managed 条目 → 合并基线 → 集合天然就等于基线 managed 集合。
# 用户手动添加的 hook（不带此标记）始终保留。
MANAGED_MARKER_REGEX="# *@claude-code-global:[A-Za-z0-9_-]+"

# 从 settings JSON 提取所有 managed hook 的 name 列表（去重排序），输出空格分隔字符串
# 用法: list_managed_names <json-file>
list_managed_names() {
    local file="$1"
    [ -f "$file" ] || { echo ""; return; }
    jq -r '
      [
        .hooks // {} | to_entries[].value[]?.hooks[]?
        | (.command // "")
        | select(test("# *@claude-code-global:[A-Za-z0-9_-]+"))
        | capture("# *@claude-code-global:(?<n>[A-Za-z0-9_-]+)").n
      ] | unique | join(" ")
    ' "$file" 2>/dev/null || echo ""
}

# 合并基线 JSON 配置进本地配置文件（非破坏性）
# 策略：
#   1. 计算 managed name 集合差分（旧/新 → added/removed/replaced），打印日志
#   2. 剔除 dst 中所有 .hooks.<event>[].hooks[] 中 command 匹配 MANAGED_MARKER_REGEX 的条目
#      连带空掉的 matcher 和 event 一并清理
#   3. 与基线递归合并：object 递归 / array 并集去重 / 标量仓库胜出 / null 视为未设置
#      合并后 managed 集合天然等于基线
# 用法: merge_settings <基线JSON> <目标JSON>
merge_settings() {
    local src="$1"
    local dst="$2"
    local name
    name="$(basename "$dst")"

    # 依赖 jq
    if ! command -v jq >/dev/null 2>&1; then
        warn "未找到 jq，跳过合并 ${name}（macOS 自带；其他系统请用包管理器安装）"
        return
    fi

    # 本地没有：直接复制（不是软链接，本机需自行编辑）
    if [ ! -f "$dst" ]; then
        cp "$src" "$dst"
        success "已创建 ${name}（从 $(basename "$src") 初始化）"
        info "  managed hooks 新增: $(list_managed_names "$src")"
        return
    fi

    # Step 1: 计算 managed name 集合差分并打印
    local old_names new_names
    old_names="$(list_managed_names "$dst")"
    new_names="$(list_managed_names "$src")"
    if [ -n "$old_names" ] || [ -n "$new_names" ]; then
        local added removed replaced
        added="$(comm -13 <(echo "$old_names" | tr ' ' '\n' | sort -u) <(echo "$new_names" | tr ' ' '\n' | sort -u) | tr '\n' ' ' | sed 's/ *$//')"
        removed="$(comm -23 <(echo "$old_names" | tr ' ' '\n' | sort -u) <(echo "$new_names" | tr ' ' '\n' | sort -u) | tr '\n' ' ' | sed 's/ *$//')"
        replaced="$(comm -12 <(echo "$old_names" | tr ' ' '\n' | sort -u) <(echo "$new_names" | tr ' ' '\n' | sort -u) | tr '\n' ' ' | sed 's/ *$//')"
        info "managed hooks 集合差分："
        [ -n "$replaced" ] && info "  替换（同名覆盖）: $replaced"
        [ -n "$added"    ] && info "  新增: $added"
        [ -n "$removed"  ] && info "  删除: $removed"
    fi

    # Step 2: 剔除 dst 中所有 managed 条目（command 匹配 MANAGED_MARKER_REGEX）
    local pruned
    pruned="$(jq --arg re "$MANAGED_MARKER_REGEX" '
      if .hooks then
        .hooks |= (
          with_entries(
            .value |= (
              map(.hooks |= map(select(((.command // "") | test($re)) | not)))
              | map(select((.hooks // []) | length > 0))
            )
          )
          | with_entries(select(.value | length > 0))
        )
      else . end
    ' "$dst")"

    # Step 3: 把 pruned 与基线递归合并
    # 注意：jq 函数参数是"滤镜表达式"，调用处会重新对当前 . 求值——
    # 在 reduce 内部 . 会变成累加器，导致 a[$k] 被解成"索引累加器"而报错。
    # 所以先用 `a as $a | b as $b` 把两侧绑定成真值再递归。
    local merged
    merged="$(jq -n --argjson a "$pruned" --slurpfile b "$src" '
      def merge(a; b):
        a as $a | b as $b |
        if   ($a|type)=="object" and ($b|type)=="object" then
          reduce (($a|keys_unsorted)+($b|keys_unsorted)|unique)[] as $k
            ({}; .[$k] = merge($a[$k]; $b[$k]))
        elif ($a|type)=="array"  and ($b|type)=="array"  then
          ($a + $b) | unique
        elif $b == null then $a
        else $b
        end;
      merge($a; $b[0])
    ')"

    # 等价性检查：把当前文件也过一遍 jq 规范化，再和合并结果比较，避免因空白差异误报变化
    local current
    current="$(jq '.' "$dst")"
    if [ "$merged" = "$current" ]; then
        info "已跳过 ${name}（内容已包含基线）"
        return
    fi

    # 真的变了：备份后写入
    local ts
    ts="$(date +%Y%m%d-%H%M%S)"
    cp "$dst" "${dst}.bak.${ts}"
    printf '%s\n' "$merged" > "$dst"
    success "已合并 ${name}（备份：${name}.bak.${ts}）"
}

# 创建一个符号链接，处理已存在的情况
# 用法: link_item <源路径> <目标路径>
link_item() {
    local src="$1"
    local dst="$2"
    local name
    name="$(basename "$dst")"

    if [ -L "$dst" ]; then
        local current_target
        current_target="$(readlink "$dst")"
        if [ "$current_target" = "$src" ]; then
            info "已跳过 ${name}（软链接已正确）"
            return
        else
            rm "$dst"
            ln -s "$src" "$dst"
            success "已更新 ${name}（旧链接指向 ${current_target}）"
        fi
    elif [ -e "$dst" ]; then
        mv "$dst" "${dst}.bak"
        ln -s "$src" "$dst"
        warn "已备份 ${name} → ${name}.bak，并创建软链接"
    else
        ln -s "$src" "$dst"
        success "已链接 $name"
    fi
}

# 确保目标目录存在
mkdir -p "$TARGET_DIR"
mkdir -p "$TARGET_DIR/skills"
mkdir -p "$TARGET_DIR/hooks"
mkdir -p "$TARGET_DIR/scripts"

echo "=============================="
echo " Claude Code 全局配置安装"
echo "=============================="
echo ""
info "仓库目录: $REPO_DIR"
info "目标目录: $TARGET_DIR"
echo ""

# 链接 GLOBAL_CLAUDE.md → ~/.claude/CLAUDE.md
if [ -f "$REPO_DIR/GLOBAL_CLAUDE.md" ]; then
    link_item "$REPO_DIR/GLOBAL_CLAUDE.md" "$TARGET_DIR/CLAUDE.md"
else
    warn "仓库中未找到 GLOBAL_CLAUDE.md，跳过"
fi

# 链接 skills（逐个子目录）
if [ -d "$REPO_DIR/skills" ]; then
    for skill_dir in "$REPO_DIR/skills"/*/; do
        # 检查是否真的有子目录（glob 无匹配时会保留原样）
        [ -d "$skill_dir" ] || continue
        skill_name="$(basename "$skill_dir")"
        link_item "$REPO_DIR/skills/$skill_name" "$TARGET_DIR/skills/$skill_name"
    done
else
    warn "仓库中未找到 skills/ 目录，跳过"
fi

# 链接 hooks（逐个文件）
if [ -d "$REPO_DIR/hooks" ]; then
    for hook_path in "$REPO_DIR/hooks"/*; do
        # 检查是否真的有文件（glob 无匹配时会保留原样）
        [ -e "$hook_path" ] || continue
        hook_name="$(basename "$hook_path")"
        link_item "$REPO_DIR/hooks/$hook_name" "$TARGET_DIR/hooks/$hook_name"
    done
else
    warn "仓库中未找到 hooks/ 目录，跳过"
fi

# 链接 scripts（逐个文件）
# 这些是被 SKILL.md 显式调用的稳定脚本（如 platform_issue.py），
# 由 SKILL.md 通过 $HOME/.claude/scripts/<name> 引用
if [ -d "$REPO_DIR/scripts" ]; then
    for script_path in "$REPO_DIR/scripts"/*; do
        [ -e "$script_path" ] || continue
        script_name="$(basename "$script_path")"
        link_item "$REPO_DIR/scripts/$script_name" "$TARGET_DIR/scripts/$script_name"
    done
else
    warn "仓库中未找到 scripts/ 目录，跳过"
fi

# 链接 templates 目录到 ~/.claude/templates/
# 让 /bootstrap 与 /sync-project-config 通过 stable 路径读取共享模板
if [ -d "$REPO_DIR/templates" ]; then
    link_item "$REPO_DIR/templates" "$TARGET_DIR/templates"
else
    warn "仓库中未找到 templates/ 目录，跳过"
fi

# 链接仓库根到 ~/.claude/global-repo/
# 让 /sync-project-config 通过此 stable 路径访问 templates 的 git 历史，
# 用于 git diff <old>..HEAD -- templates/<stack>/ 计算模板版本变化
link_item "$REPO_DIR" "$TARGET_DIR/global-repo"

# 合并 settings.base.json → ~/.claude/settings.json（不软链接，需合并本机特有设置）
if [ -f "$REPO_DIR/settings.base.json" ]; then
    merge_settings "$REPO_DIR/settings.base.json" "$TARGET_DIR/settings.json"
else
    warn "仓库中未找到 settings.base.json，跳过"
fi

# 注册 OS 自动同步调度器（launchd / systemd user timer）
# 让 scripts/auto-update.sh 自动跑「登录 + 每小时」
# 失败 warn 不阻塞主 install
if [ -x "$REPO_DIR/scheduler/install.sh" ]; then
    echo ""
    bash "$REPO_DIR/scheduler/install.sh" || warn "调度器注册失败，可手动：bash $REPO_DIR/scheduler/install.sh"
fi

echo ""
echo "=============================="
echo " 安装完成"
echo "=============================="
