#!/usr/bin/env bash
# claude-code-global 用户可配置项：可 source 的库。
#
# 背景：仓库原本把所有偏好硬编码，缺一层「用户可配置」。本库提供最小机制——
# 用户偏好以扁平 KEY=value 存于【真实配置】（默认 ~/.claude-code-global/config.env），
# 仓库内只放 user.config.example.env 作为示例基线（committed）。
#
# 三条设计约束（详见 docs/27-用户可配置项机制/DESIGN.md）：
#   1) 真实配置落在 agent home / 仓库外 → git pull、多设备 auto-update 永不触碰；
#   2) seed 是「user-wins」语义：缺文件才整份 seed，已存在绝不覆盖，
#      example 新增的 key 才逐个「补缺追加」默认值（与 install.sh 里 merge_settings 的
#      「标量仓库胜出」相反——偏好必须用户值优先）；
#   3) 读取走安全解析（grep 取值 + 剥注释/引号），不 blind `source` 用户文件。
#
# 被 install.sh、未来 hook / skill、以及 docs/25-.../verify-user-config.sh 共同 source。
# 所有命令替换处都加 `|| true` 兜底，使本库在调用方开启 `set -e`+`pipefail` 时也不会
# 因 grep 空匹配等正常情况误退出。

# 用户真实配置文件路径；允许 CCG_USER_CONFIG 覆盖（测试沙箱 / 自定义位置用）。
ccg_user_config_path() {
    echo "${CCG_USER_CONFIG:-$HOME/.claude-code-global/config.env}"
}

# 列出某文件里所有「配置 key」（行首 KEY= 的 KEY 名；忽略注释与空行）。
# 用法: ccg_config_keys_in <file>
ccg_config_keys_in() {
    local file="$1"
    [ -f "$file" ] || return 0
    grep -E '^[A-Za-z_][A-Za-z0-9_]*=' "$file" 2>/dev/null | sed -E 's/=.*//' || true
}

# 安全读取某 key 的值：grep 行首 KEY=、取最后一条、剥行内注释与首尾引号。
# 不 source 文件，避免任意代码执行。无该 key 时输出空、返回 0。
# 用法: ccg_read_config <KEY>   （从当前用户真实配置读）
ccg_read_config() {
    local key="$1"
    local file line val
    file="$(ccg_user_config_path)"
    [ -f "$file" ] || return 0
    line="$(grep -E "^${key}=" "$file" 2>/dev/null | tail -n 1 || true)"
    [ -n "$line" ] || return 0
    val="${line#*=}"
    # 行内注释：仅在 " #"（空白+井号）处截断，保留值内合法的 #
    val="${val%% #*}"
    # 去首尾空白
    val="${val#"${val%%[![:space:]]*}"}"
    val="${val%"${val##*[![:space:]]}"}"
    # 剥成对的首尾引号
    case "$val" in
        \"*\") val="${val#\"}"; val="${val%\"}" ;;
        \'*\') val="${val#\'}"; val="${val%\'}" ;;
    esac
    printf '%s\n' "$val"
}

# seed 用户配置（user-wins）：
#   - 真实配置不存在 → mkdir + 整份复制 example
#   - 已存在 → 逐 key 检查 example 中的 key，本地缺失的才从 example 取整行追加；已有的绝不动
# 用法: ccg_seed_user_config <example_path>
ccg_seed_user_config() {
    local example="$1"
    local file
    file="$(ccg_user_config_path)"

    if [ ! -f "$example" ]; then
        echo "[user-config] 警告：找不到 example ${example}，跳过 seed" >&2
        return 0
    fi

    if [ ! -f "$file" ]; then
        mkdir -p "$(dirname "$file")"
        cp "$example" "$file"
        echo "[user-config] 已创建用户配置：${file}（从 $(basename "$example") 初始化）"
        return 0
    fi

    local appended="" key exline
    while IFS= read -r key; do
        [ -n "$key" ] || continue
        if ! grep -qE "^${key}=" "$file" 2>/dev/null; then
            exline="$(grep -E "^${key}=" "$example" 2>/dev/null | head -n 1 || true)"
            printf '%s\n' "$exline" >> "$file"
            appended="${appended:+$appended }${key}"
        fi
    done < <(ccg_config_keys_in "$example")

    if [ -n "$appended" ]; then
        echo "[user-config] 已向 $file 补缺新配置项：$appended"
    fi
}

# 读 GIT_INIT_DEFAULT_BRANCH，非空且有 git 才设全局 init.defaultBranch。
# 空值 = 不动用户 git 配置（用户借空值 opt-out）。写入位置遵循 git 规则
# （$HOME/.gitconfig 或 $GIT_CONFIG_GLOBAL）。
ccg_apply_git_default_branch() {
    command -v git >/dev/null 2>&1 || return 0
    local branch
    branch="$(ccg_read_config GIT_INIT_DEFAULT_BRANCH || true)"
    [ -n "$branch" ] || return 0
    git config --global init.defaultBranch "$branch"
    echo "[user-config] 已设 git 全局 init.defaultBranch = $branch"
}
