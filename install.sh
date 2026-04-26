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

# 合并基线 JSON 配置进本地配置文件（非破坏性）
# 策略：object 递归合并 / array 并集去重 / 标量仓库胜出 / null 视为未设置
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
        return
    fi

    # 计算合并结果
    # 注意：jq 函数参数是"滤镜表达式"，调用处会重新对当前 . 求值——
    # 在 reduce 内部 . 会变成累加器，导致 a[$k] 被解成"索引累加器"而报错。
    # 所以先用 `a as $a | b as $b` 把两侧绑定成真值再递归。
    local merged
    merged="$(jq -s '
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
      merge(.[0]; .[1])
    ' "$dst" "$src")"

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

# 合并 settings.base.json → ~/.claude/settings.json（不软链接，需合并本机特有设置）
if [ -f "$REPO_DIR/settings.base.json" ]; then
    merge_settings "$REPO_DIR/settings.base.json" "$TARGET_DIR/settings.json"
else
    warn "仓库中未找到 settings.base.json，跳过"
fi

echo ""
echo "=============================="
echo " 安装完成"
echo "=============================="
