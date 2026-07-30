#!/usr/bin/env bash
set -euo pipefail

# 自动检测仓库根目录
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

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

# Codex config.toml 的托管块由一对 marker 注释包裹，整块由 install.sh 重写。
TOML_MARKER_BEGIN="# >>> claude-code-global managed >>>"
TOML_MARKER_END="# <<< claude-code-global managed <<<"

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

# 从一个文件中提取 marker 块（含首尾 marker 行本身），输出到 stdout
# 用法: extract_toml_block <file>
extract_toml_block() {
    awk -v b="$TOML_MARKER_BEGIN" -v e="$TOML_MARKER_END" '
        $0 == b { inblk = 1 }
        inblk   { print }
        $0 == e { inblk = 0 }
    ' "$1"
}

# 合并基线 TOML 配置进本地 config.toml（非破坏性）
# 策略（与 merge_settings 等价，但 TOML 无 jq，改用 marker 块整体重写）：
#   - dst 不存在 → 整份复制基线（含 marker 块外的推荐策略）
#   - dst 存在且无 marker 块 → 末尾追加基线的 marker 块
#   - dst 存在且有旧 marker 块 → 用基线的块整体替换旧块
#   - 块内容与现有一致 → 跳过（不产生空备份）
# marker 块只含 [[hooks.*]] 数组表，可安全追加到任意 TOML 文件末尾；
# 用户在 marker 块外手写的内容（含 approval_policy / [projects] 等）一律保留。
# 用法: merge_toml <基线TOML> <目标TOML>
merge_toml() {
    local src="$1"
    local dst="$2"
    local name
    name="$(basename "$dst")"

    # 本地没有：整份复制
    if [ ! -f "$dst" ]; then
        cp "$src" "$dst"
        success "已创建 ${name}（从 $(basename "$src") 初始化）"
        return
    fi

    # 提取基线的 marker 块
    local block
    block="$(extract_toml_block "$src")"
    if [ -z "$block" ]; then
        warn "基线 $(basename "$src") 无 marker 块，跳过合并 ${name}"
        return
    fi

    local ts
    if grep -qF "$TOML_MARKER_BEGIN" "$dst"; then
        # 已有 marker 块：比较是否需要更新
        local current_block
        current_block="$(extract_toml_block "$dst")"
        if [ "$current_block" = "$block" ]; then
            info "已跳过 ${name}（marker 块已是最新）"
            return
        fi
        # 整体替换旧块：备份后用 awk 删旧块插新块
        ts="$(date +%Y%m%d-%H%M%S)"
        cp "$dst" "${dst}.bak.${ts}"
        local block_file merged_file
        block_file="$(mktemp)"
        merged_file="$(mktemp)"
        printf '%s\n' "$block" > "$block_file"
        awk -v b="$TOML_MARKER_BEGIN" -v e="$TOML_MARKER_END" -v nf="$block_file" '
            $0 == b {
                inblk = 1
                while ((getline line < nf) > 0) print line
                close(nf)
                next
            }
            inblk && $0 == e { inblk = 0; next }
            inblk { next }
            { print }
        ' "$dst" > "$merged_file"
        mv "$merged_file" "$dst"
        rm -f "$block_file"
        success "已更新 ${name} 的 marker 块（备份：${name}.bak.${ts}）"
    else
        # 无 marker 块：末尾追加
        ts="$(date +%Y%m%d-%H%M%S)"
        cp "$dst" "${dst}.bak.${ts}"
        printf '\n%s\n' "$block" >> "$dst"
        success "已向 ${name} 追加 marker 块（备份：${name}.bak.${ts}）"
    fi
}

# 以 user-wins 语义把推荐的系统级 uv 配置 seed 到 ~/.config/uv/uv.toml
# 策略（与 scripts/user-config.sh 的 ccg_seed_user_config 一致：缺省才填、绝不覆盖）：
#   - 目标不存在 → 建父目录 + 整份复制基线
#   - 目标已存在 → 一律不碰（用户自管），仅打印一行提示
# 不做字段级 merge：uv.toml 的 python-preference 是标量键，
# 在用户已设同键时 marker-block 追加会触发 TOML 重复键错误，得不偿失。
# 用法: seed_uv_config <基线TOML>
seed_uv_config() {
    local src="$1"
    local dst="${XDG_CONFIG_HOME:-$HOME/.config}/uv/uv.toml"

    if [ ! -f "$src" ]; then
        warn "未找到 $(basename "$src")，跳过系统级 uv 配置 seed"
        return
    fi

    if [ -f "$dst" ]; then
        info "已跳过 ${dst}（已存在，用户自管）"
        info "  如需机器级 only-managed，可手动加：python-preference = \"only-managed\""
        return
    fi

    mkdir -p "$(dirname "$dst")"
    cp "$src" "$dst"
    success "已创建 ${dst}（从 $(basename "$src") 初始化系统级 uv 配置）"
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

# 清理本仓早期留下的旧 rules 软链。
# 用法: unlink_legacy_dir <链接路径>
#
# 背景：本仓曾把 rules/ 软链到 <agent_home>/rules，而 rules 是 Claude Code 的**保留目录名**——
# 放进去的 .md 会被当作用户级 memory 全文注入每一个会话的系统提示（与「按需读」的设计意图正相反）。
# 改用中性目录名 playbooks/ 后，老机器上的旧软链必须清掉，否则那八份文档继续常驻、收益归零，
# 而且是静默的：install 全绿、日志漂亮，没人会发现。
#
# 认亲方式：软链目标形如 <某目录>/rules，且 <某目录> 带本仓标志文件。**不比对当次 $REPO_DIR
# 的精确路径**——一台机器上可能有多个 checkout（主工作树 + 若干 worktree），旧软链指向哪一个
# 都得认得出来；比对精确路径会在「从 worktree 跑 install」时漏删。
#
# 安全边界：非软链（用户自建的真实目录）不碰；目标不叫 rules 的不碰；父目录不带本仓标志
# 文件的不碰。注意用 -L / readlink 而非 -e / readlink -f——目录改名后旧软链已是断链，后者
# 在断链上不工作，会造成静默漏删。
unlink_legacy_dir() {
    local link="$1"
    [ -L "$link" ] || return 0

    local target parent
    target="$(readlink "$link")"
    # 只认绝对路径：相对目标下面的认亲检查会相对 CWD 解析，而本脚本通常正是从某个
    # checkout 根跑起来的，标志文件就在手边，容易把不相干的相对软链误判成自家的。
    # 本仓建的软链一律是绝对路径，直接拒掉相对路径即可，不做花哨解析。
    case "$target" in
    /*/rules) ;;
    *) return 0 ;;
    esac
    parent="${target%/rules}"
    [ -f "${parent}/GLOBAL_AGENTS.md" ] && [ -f "${parent}/install.sh" ] || return 0

    rm -f "$link"
    info "已清理旧的 ${link}（rules 是 CC 保留目录名，改用 playbooks）"
}

# 部署一个 agent 端：软链 skills/hooks/scripts/templates/global-repo + 主指令文档，
# 并合并各端的 settings/config 基线。
# 用法: deploy_agent <agent_home> <主指令文档名> <agent 标签> <config 类型: json|toml>
deploy_agent() {
    local agent_home="$1"
    local main_doc="$2"
    local label="$3"
    local config_kind="$4"

    echo ""
    echo "------------------------------"
    info "部署 ${label}：${agent_home}"
    echo "------------------------------"

    mkdir -p "$agent_home/skills" "$agent_home/hooks" "$agent_home/scripts"

    # 主指令文档（GLOBAL_AGENTS.md → ~/.claude/CLAUDE.md 或 ~/.codex/AGENTS.md）
    if [ -f "$REPO_DIR/GLOBAL_AGENTS.md" ]; then
        link_item "$REPO_DIR/GLOBAL_AGENTS.md" "$agent_home/$main_doc"
    else
        warn "仓库中未找到 GLOBAL_AGENTS.md，跳过"
    fi

    # skills（逐个子目录）
    if [ -d "$REPO_DIR/skills" ]; then
        for skill_dir in "$REPO_DIR/skills"/*/; do
            [ -d "$skill_dir" ] || continue
            local skill_name
            skill_name="$(basename "$skill_dir")"
            link_item "$REPO_DIR/skills/$skill_name" "$agent_home/skills/$skill_name"
        done
    else
        warn "仓库中未找到 skills/ 目录，跳过"
    fi

    # hooks（逐个文件）
    if [ -d "$REPO_DIR/hooks" ]; then
        for hook_path in "$REPO_DIR/hooks"/*; do
            [ -e "$hook_path" ] || continue
            local hook_name
            hook_name="$(basename "$hook_path")"
            link_item "$REPO_DIR/hooks/$hook_name" "$agent_home/hooks/$hook_name"
        done
    else
        warn "仓库中未找到 hooks/ 目录，跳过"
    fi

    # scripts（逐个文件）
    if [ -d "$REPO_DIR/scripts" ]; then
        for script_path in "$REPO_DIR/scripts"/*; do
            [ -e "$script_path" ] || continue
            local script_name
            script_name="$(basename "$script_path")"
            link_item "$REPO_DIR/scripts/$script_name" "$agent_home/scripts/$script_name"
        done
    else
        warn "仓库中未找到 scripts/ 目录，跳过"
    fi

    # templates 目录
    if [ -d "$REPO_DIR/templates" ]; then
        link_item "$REPO_DIR/templates" "$agent_home/templates"
    else
        warn "仓库中未找到 templates/ 目录，跳过"
    fi

    # 旧路径迁移：曾软链到 <agent_home>/rules，而 rules 是 CC 保留目录名（见 unlink_legacy_dir）
    unlink_legacy_dir "$agent_home/rules"

    # playbooks 目录（领域规则文档，按 <topic>.md 组织；目录级软链，新增 md 不需要重跑 install）
    if [ -d "$REPO_DIR/playbooks" ]; then
        link_item "$REPO_DIR/playbooks" "$agent_home/playbooks"
    else
        warn "仓库中未找到 playbooks/ 目录，跳过"
    fi

    # 仓库根 → global-repo（供 /sync-project-config 访问模板 git 历史）
    link_item "$REPO_DIR" "$agent_home/global-repo"

    # settings / config 合并（CC 用 JSON，Codex 用 TOML）
    if [ "$config_kind" = "json" ]; then
        if [ -f "$REPO_DIR/settings.base.json" ]; then
            merge_settings "$REPO_DIR/settings.base.json" "$agent_home/settings.json"
        else
            warn "仓库中未找到 settings.base.json，跳过"
        fi
    else
        if [ -f "$REPO_DIR/codex.config.base.toml" ]; then
            merge_toml "$REPO_DIR/codex.config.base.toml" "$agent_home/config.toml"
        else
            warn "仓库中未找到 codex.config.base.toml，跳过"
        fi
    fi
}

# 测试可 source 本脚本只取函数定义、不跑安装主流程（见 docs/51-rules按需加载/test-unlink-legacy.sh）。
#
# 只在 source 语境下生效：直接执行时，哪怕环境里意外带了这个变量也照常安装。否则
# `CCG_INSTALL_LIB_ONLY=1 bash install.sh` 会零输出 + 退出码 0 地静默 no-op，伪装成
# 一次成功的安装——而定时跑 install.sh 的正是 scripts/auto-update.sh，这种失败不会
# 有任何人察觉（与本轮 unlink_legacy_dir 漏删是同一类病：全绿、无感、收益归零）。
if [ "${CCG_INSTALL_LIB_ONLY:-0}" = "1" ] && [ "${BASH_SOURCE[0]}" != "$0" ]; then
    return 0
fi

echo "=============================="
echo " Coding Agent 全局配置安装"
echo "=============================="
echo ""
info "仓库目录: $REPO_DIR"

# 双轨部署：检测 ~/.claude（Claude Code）与 ~/.codex（Codex）各自是否存在，
# 对存在的一侧部署，缺哪侧跳过哪侧。agent 自身安装时会创建其 home 目录。
DEPLOYED_ANY=0
DEPLOYED_CODEX=0

if [ -d "$HOME/.claude" ]; then
    deploy_agent "$HOME/.claude" "CLAUDE.md" "Claude Code" "json"
    DEPLOYED_ANY=1
else
    info "未检测到 ~/.claude，跳过 Claude Code 端"
fi

if [ -d "$HOME/.codex" ]; then
    deploy_agent "$HOME/.codex" "AGENTS.md" "Codex" "toml"
    DEPLOYED_ANY=1
    DEPLOYED_CODEX=1
else
    info "未检测到 ~/.codex，跳过 Codex 端"
fi

if [ "$DEPLOYED_ANY" = "0" ]; then
    echo ""
    warn "未检测到 ~/.claude 或 ~/.codex，未部署任何 agent。"
    warn "请先安装 Claude Code 或 Codex CLI（它们会创建各自的 home 目录），再重跑本脚本。"
    exit 0
fi

# 用户可配置项：seed 真实配置 + 应用偏好（全局一次，与具体 agent 端无关）
# 机制见 scripts/user-config.sh 与 docs/27-用户可配置项机制/DESIGN.md
if [ -f "$REPO_DIR/scripts/user-config.sh" ]; then
    echo ""
    echo "------------------------------"
    info "用户可配置项"
    echo "------------------------------"
    # shellcheck disable=SC1091
    source "$REPO_DIR/scripts/user-config.sh"
    ccg_seed_user_config "$REPO_DIR/user.config.example.env" || warn "用户配置 seed 失败（不阻塞）"
    ccg_apply_git_default_branch || warn "应用 git 默认分支失败（不阻塞）"
else
    warn "未找到 scripts/user-config.sh，跳过用户可配置项处理"
fi

# 系统级 uv 配置：seed ~/.config/uv/uv.toml（机器级 only-managed + 清华源默认）
# user-wins：缺失才创建，已存在不动。与具体 agent 端无关，故全局只跑一次。
if [ -f "$REPO_DIR/uv.config.base.toml" ]; then
    echo ""
    echo "------------------------------"
    info "系统级 uv 配置"
    echo "------------------------------"
    seed_uv_config "$REPO_DIR/uv.config.base.toml"
else
    warn "未找到 uv.config.base.toml，跳过系统级 uv 配置 seed"
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

if [ "$DEPLOYED_CODEX" = "1" ]; then
    echo ""
    warn "Codex hooks 首次需进入 Codex 跑一次 /hooks 命令 review 后才会生效。"
fi
