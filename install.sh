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

echo ""
echo "=============================="
echo " 安装完成"
echo "=============================="
