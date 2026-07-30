#!/usr/bin/env python3
"""指令面预算量化 —— 给 `/routine-slim` 当触发器、给精简 PR 当证据。

三个子命令：

    measure                 扫指令面，出每文件字符数 / token 估算 / 分类
    delta [--since REF]     与历史版本比，算增长率（无状态：基线从 git 历史算）
    check-refs              跨文件引用可达性检查

**为什么要有这个脚本**：没有数，精简就是拍脑袋 —— 既定不出「该不该动手」的阈值，
也证明不了「省了多少」。

token 估算的标定
----------------
中文按英文经验值（4 字符/token）估会低估约 3 倍，必须实测标定。本脚本的系数由 CC
`/context` 的两个实测点解出（2026-07-31，claude-opus-5）：

    GLOBAL_AGENTS.md  9,922 字符（CJK 4,844 / 非 CJK 5,078） = 8,000 token
    CLAUDE.md         5,042 字符（CJK 1,403 / 非 CJK 3,639） = 3,600 token

    => CJK 1.0313 token/字、非 CJK 0.5917 token/字

非 CJK 那档比英文散文的 0.25 高得多，因为这里的「非 CJK」大量是 markdown 记号、
路径、命令与代码 —— 这类切得比散文碎。**换模型或大改文风后需重新标定**：跑
`/context` 拿新的实测点，重解下面两个常数。
"""

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


def _glob_match(path: str, pattern: str) -> bool:
    """glob 匹配，`*` **不跨 `/`**。

    不能用 `fnmatch`：它的 `*` 会跨目录分隔符，于是 `skills/*/SKILL.md` 连
    `skills/a/b/SKILL.md` 也匹配，与 `Path.glob` 口径不一致 —— `delta` 的新侧走
    `Path.glob`、旧侧走这里，口径一旦不同就会算出假的增长。
    """
    regex = "".join(r"[^/]*" if part == "*" else re.escape(part)
                    for part in re.split(r"(\*)", pattern))
    return re.fullmatch(regex, path) is not None

# ── token 估算系数（标定来源见模块 docstring，改动前先重新实测）────────────────
CJK_TOKENS_PER_CHAR = 1.0313
NON_CJK_TOKENS_PER_CHAR = 0.5917

_CJK_RANGES = (
    (0x3000, 0x303F),    # CJK 标点
    (0x3400, 0x4DBF),    # 扩展 A
    (0x4E00, 0x9FFF),    # 基本区
    (0xF900, 0xFAFF),    # 兼容表意
    (0xFF00, 0xFFEF),    # 全角形式
    (0x20000, 0x2FA1F),  # 扩展 B+
)


def is_cjk(ch: str) -> bool:
    o = ord(ch)
    return any(lo <= o <= hi for lo, hi in _CJK_RANGES)


def estimate_tokens(text: str) -> int:
    cjk = sum(1 for c in text if is_cjk(c))
    return round(cjk * CJK_TOKENS_PER_CHAR + (len(text) - cjk) * NON_CJK_TOKENS_PER_CHAR)


# ── 扫描面 ────────────────────────────────────────────────────────────────────
# resident = 每会话无条件进上下文；lazy = 命中触发条件才读。
# 注：skill 的 frontmatter `description` 其实也常驻（skill listing，全仓合计约
# 2k token），但它随 SKILL.md 一起改、单独建模没有收益，故并入 lazy 计。
RESIDENT = ("GLOBAL_AGENTS.md", "CLAUDE.md")
LAZY_GLOBS = ("skills/*/SKILL.md", "skills/*/references/*.md", "playbooks/*.md",
              "templates/MECHANICS.md")


def instruction_paths(root: Path) -> list[str]:
    """指令面的全部文件，仓库相对路径，稳定排序。"""
    out = [p for p in RESIDENT if (root / p).is_file()]
    for pattern in LAZY_GLOBS:
        out.extend(sorted(str(p.relative_to(root)) for p in root.glob(pattern) if p.is_file()))
    return out


def _category(rel: str) -> str:
    return "resident" if rel in RESIDENT else "lazy"


@dataclass
class Entry:
    path: str
    chars: int
    tokens: int
    category: str


@dataclass
class Report:
    entries: list[Entry] = field(default_factory=list)
    total_chars: int = 0
    total_tokens: int = 0
    resident_chars: int = 0
    resident_tokens: int = 0
    lazy_chars: int = 0
    lazy_tokens: int = 0


def measure(root: Path) -> Report:
    report = Report()
    for rel in instruction_paths(root):
        text = (root / rel).read_text(encoding="utf-8")
        entry = Entry(rel, len(text), estimate_tokens(text), _category(rel))
        report.entries.append(entry)
        report.total_chars += entry.chars
        report.total_tokens += entry.tokens
        if entry.category == "resident":
            report.resident_chars += entry.chars
            report.resident_tokens += entry.tokens
        else:
            report.lazy_chars += entry.chars
            report.lazy_tokens += entry.tokens
    return report


# ── 跨文件引用检查 ────────────────────────────────────────────────────────────
# 「只允许搬走不允许蒸发」的机械兑现：指针指不到东西，等于那条信息真的没了。
#
# **只认精确白名单，不做启发式**。因为 skill 正文里谈的路径大多根本不是本仓的：
# `src/`、`frontend/`、`.vscode/settings.json`、`docs/BACKLOG.md` 说的是**消费方
# 项目**，`__root__/`、`_common/` 是模板内的抽象位置，`rules/` 是被刻意保留的历史
# 提法。按「长得像路径」去查会得到一屏误报，而误报会让人干脆不看这个检查 —— 那就
# 等于没有。故这里只查精简动作真正会产出的那几种指针形态，其余一律记为「未覆盖」。

_CODE_SPAN = re.compile(r"`([^`\n]+)`")
# ~/.claude/<X>/ 与 ~/.codex/<X>/ 是本仓同名目录的软链投影，须归一回仓库内路径
_HOME_SUBDIRS = ("skills", "hooks", "scripts", "templates", "playbooks")
# 可判定的指针形态 —— 与精简产出的指针一一对应
_CHECKABLE = (
    "GLOBAL_AGENTS.md",
    "playbooks/*.md",
    "skills/*/SKILL.md",
    "skills/*/references/*.md",
    "references/*.md",            # 相对所属 skill 目录
    "scripts/*",
    "hooks/*",
    "templates/*.md",             # 顶层共享文档（如 MECHANICS.md），不含各 stack 内容
    ".github/labels.yml",
    ".github/workflows/*.yml",
)


def _normalize_ref(raw: str) -> str | None:
    """把一个引用归一为仓库相对路径；判不出 / 不可判定 → None。"""
    ref = raw.strip()
    if " " in ref or "\t" in ref:
        return None                                    # 带空格的是命令 / 示例输出，不是路径
    if "://" in ref or ref.startswith("/"):
        return None                                    # URL 与绝对路径都不在仓库里
    if any(c in ref for c in "*<>?{}|") or "..." in ref:
        return None                                    # glob 与占位符是模式不是路径

    for home in ("~/.claude/", "~/.codex/", "$HOME/.claude/", "$HOME/.codex/"):
        if ref.startswith(home):
            rest = ref[len(home):]
            if rest in ("CLAUDE.md", "AGENTS.md"):
                ref = "GLOBAL_AGENTS.md"               # 两端主指令文档都软链自宪法
            elif rest.startswith("global-repo/"):
                ref = rest[len("global-repo/"):]
            elif rest.split("/", 1)[0] in _HOME_SUBDIRS:
                ref = rest
            else:
                return None                            # ~/.claude/settings.json 等非本仓产物
            break
    if "$" in ref or ref.startswith("~/"):
        return None                                    # 含变量的路径无法静态判定

    return ref if any(_glob_match(ref, p) for p in _CHECKABLE) else None


def extract_refs(text: str) -> list[str]:
    """从 markdown 里抽出可判定的跨文件引用（去重、保序）。"""
    seen: dict[str, None] = {}
    for span in _CODE_SPAN.findall(text):
        ref = _normalize_ref(span)
        if ref is not None:
            seen.setdefault(ref, None)
    return list(seen)


@dataclass
class BrokenRef:
    source: str
    ref: str


def check_refs(root: Path) -> list[BrokenRef]:
    broken: list[BrokenRef] = []
    for rel in instruction_paths(root):
        text = (root / rel).read_text(encoding="utf-8")
        parts = rel.split("/")
        # `references/x.md` 是相对所属 skill 目录写的（见 skills/finish/SKILL.md 的先例）
        skill_dir = "/".join(parts[:2]) if parts[0] == "skills" and len(parts) > 2 else None
        for ref in extract_refs(text):
            target = root / ref
            if ref.startswith("references/") and skill_dir:
                target = root / skill_dir / ref
            if not target.exists():
                broken.append(BrokenRef(rel, ref))
    return broken


# ── 与历史版本比 ──────────────────────────────────────────────────────────────

def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args],
                          capture_output=True, text=True, check=True).stdout


def resolve_since_ref(root: Path, since: str | None, weeks: int = 4) -> str:
    """基线 ref。**不落状态文件、不打 tag** —— 直接从 git 历史算。"""
    if since:
        return since
    out = _git(root, "rev-list", "-1", f"--before={weeks} weeks ago", "HEAD").strip()
    if out:
        return out
    # 仓库比窗口还年轻 → 退到根提交，此时 delta 即「有史以来的增长」
    return _git(root, "rev-list", "--max-parents=0", "HEAD").split()[-1]


def file_at_ref(root: Path, ref: str, rel: str) -> str | None:
    try:
        return _git(root, "show", f"{ref}:{rel}")
    except subprocess.CalledProcessError:
        return None


def _paths_at_ref(root: Path, ref: str) -> list[str]:
    """该 ref 下属于指令面的文件。与 `instruction_paths` 共用同一套 glob，保证口径一致。"""
    tracked = _git(root, "ls-tree", "-r", "--name-only", ref).splitlines()
    return [p for p in tracked
            if p in RESIDENT or any(_glob_match(p, g) for g in LAZY_GLOBS)]


@dataclass
class Delta:
    since_ref: str
    old_chars: int
    new_chars: int
    old_tokens: int
    new_tokens: int
    growth_ratio: float
    per_file: list[tuple[str, int, int]] = field(default_factory=list)


def delta(root: Path, since: str | None = None) -> Delta:
    ref = resolve_since_ref(root, since)
    old: dict[str, int] = {}
    old_tokens = 0
    for rel in _paths_at_ref(root, ref):
        text = file_at_ref(root, ref, rel)
        if text is None:
            continue
        old[rel] = len(text)
        old_tokens += estimate_tokens(text)

    report = measure(root)
    new = {e.path: e.chars for e in report.entries}

    old_chars, new_chars = sum(old.values()), sum(new.values())
    per_file = [(p, old.get(p, 0), new.get(p, 0)) for p in sorted(set(old) | set(new))]
    ratio = (new_chars - old_chars) / old_chars if old_chars else 0.0
    return Delta(ref, old_chars, new_chars, old_tokens, report.total_tokens, ratio, per_file)


# ── CLI ───────────────────────────────────────────────────────────────────────

def _repo_root() -> Path:
    try:
        return Path(_git(Path.cwd(), "rev-parse", "--show-toplevel").strip())
    except subprocess.CalledProcessError:
        return Path.cwd()


def _cmd_measure(args) -> int:
    report = measure(_repo_root())
    if args.json:
        print(json.dumps({
            "total_chars": report.total_chars, "total_tokens": report.total_tokens,
            "resident_chars": report.resident_chars, "resident_tokens": report.resident_tokens,
            "lazy_chars": report.lazy_chars, "lazy_tokens": report.lazy_tokens,
            "entries": [vars(e) for e in report.entries],
        }, ensure_ascii=False, indent=2))
        return 0
    print(f"{'字符':>8} {'~token':>8}  {'类别':<9} 文件")
    for e in sorted(report.entries, key=lambda e: -e.chars):
        print(f"{e.chars:8,} {e.tokens:8,}  {e.category:<9} {e.path}")
    print(f"\n{'常驻':<6} {report.resident_chars:8,} 字符  ~{report.resident_tokens:,} token（每会话每项目）")
    print(f"{'懒加载':<6} {report.lazy_chars:8,} 字符  ~{report.lazy_tokens:,} token")
    print(f"{'合计':<6} {report.total_chars:8,} 字符  ~{report.total_tokens:,} token")
    return 0


def _cmd_delta(args) -> int:
    d = delta(_repo_root(), args.since)
    print(f"基线 {d.since_ref[:12]}：{d.old_chars:,} 字符 / ~{d.old_tokens:,} token")
    print(f"当前          ：{d.new_chars:,} 字符 / ~{d.new_tokens:,} token")
    print(f"增长          ：{d.growth_ratio:+.1%}")
    changed = [(p, o, n) for p, o, n in d.per_file if o != n]
    if changed:
        print("\n变化明细（字符）：")
        for p, o, n in sorted(changed, key=lambda x: -(x[2] - x[1])):
            print(f"  {n - o:+8,}  {o:7,} → {n:7,}  {p}")
    if args.threshold is not None:
        over = d.growth_ratio > args.threshold / 100
        print(f"\n阈值 {args.threshold:+.0f}%：{'超出，该动手' if over else '未超出，空转退出'}")
        return 1 if over else 0
    return 0


def _cmd_check_refs(args) -> int:
    broken = check_refs(_repo_root())
    if not broken:
        print("check-refs: 无失效引用 ✅")
        return 0
    print(f"check-refs: {len(broken)} 条失效引用 ❌")
    for b in broken:
        print(f"  {b.source} → {b.ref}")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="指令面预算量化")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("measure", help="扫指令面出量化表")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=_cmd_measure)

    p = sub.add_parser("delta", help="与历史版本比增长率")
    p.add_argument("--since", help="基线 git ref（缺省取 4 周前）")
    p.add_argument("--threshold", type=float,
                   help="增长率阈值（百分比）；超出则 exit 1，供 routine 当闸用")
    p.set_defaults(func=_cmd_delta)

    p = sub.add_parser("check-refs", help="跨文件引用可达性检查")
    p.set_defaults(func=_cmd_check_refs)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
