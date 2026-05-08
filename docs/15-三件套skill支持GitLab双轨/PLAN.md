# PLAN — round 15：让 backlog/start/finish 三件套 skill 在 GitLab 项目上可用

> 对应 issue：[#3 让 backlog / start / finish 等 skill 在 GitLab 项目上可用（gh ↔ glab 双轨）](https://github.com/pkulijing/claude-code-global/issues/3)
> Labels: `type:feat` `area:skill` `priority:P1`
> 配套 PROMPT：`docs/15-三件套skill支持GitLab双轨/PROMPT.md`

## 1. Context（为什么）

Round 14 把模板侧 GitHub/GitLab 双兼容（issue templates + CI 文件并存）落到位，并在 `/bootstrap` 与 `/sync-project-config` 中按 `git remote get-url origin` 三分支判定（GitHub / GitLab / 其他），但 GitLab 分支当前是「跳过 + 提示」未真正调 `glab`；**skill 内 5 处 `gh` CLI 调用仍是 GitHub 独占**：在 GitLab 项目上跑 `/backlog`、`/start <#>` 会前置失败或行为静默错位。

本轮通过引入 **`scripts/platform_issue.py`** 一个跨平台 helper，把所有 CLI 调用集中在 helper 内分平台 dispatch，让 SKILL.md 调用平台无关的命令。同时把 round 14 留下的「GitLab labels 同步」前置项一起做掉（avoid 撕裂状态）。

## 2. 关键设计决定（已与作者对齐）

### 2.1 helper 用 python3 单文件，零第三方依赖

- `scripts/platform_issue.py`，仅用 stdlib（`subprocess` / `json` / `argparse` / `pathlib` / `sys` / `re`）
- **禁止引入 PyYAML**（PEP 668 风险 + 破坏「软链即装好」承诺）
- yml 解析：自己写 ~30 行的 line-state-machine，专门支持 `labels.yml` 极简 schema（list of dict + 三个 string field + `#` 注释 + `---` doc header）
- 提供隐藏 `--self-test` subcommand 跑 yml round-trip + 字段映射纯函数自检

### 2.2 不新建 `.gitlab/labels.yml`，跨平台共读 `.github/labels.yml`

- labels schema 完全跨平台一致（`{name, color, description}` × 9 条），新建副本只会引入维护漂移
- `.github/labels.yml` 在 GitLab 项目里**不是**给平台读的死文件 —— 它是 helper 私有输入，与 `.gitlab-ci.yml` 在 GitHub 项目里"被平台忽略"的语义不同
- 这条**修订** PROMPT 第 3.4 项原写的「新增 `.gitlab/labels.yml`」
- helper `label-sync-from-file` 接收路径参数（不 hard-code），未来用户若搬路径仍兼容

### 2.3 立 `scripts/` 为新二级目录范式 + 软链到 `~/.claude/scripts/`

- 与 `hooks/` 软链模式同构：`install.sh` 加一段对称循环 + `mkdir -p "$TARGET_DIR/scripts"`
- 逐文件软链（与 hooks 一致），不整目录软链
- SKILL.md 调用永远写完整路径：`python3 $HOME/.claude/scripts/platform_issue.py <subcommand>`
- helper 文件加 `#!/usr/bin/env python3` shebang + `chmod +x`，但调用时仍显式写 `python3`（不依赖 PATH）

### 2.4 `/finish` 不调 helper

`Closes #N` 在 GitHub & GitLab 都自动关 issue（GitLab 还支持 `Fixes`/`Resolves` 等更多关键词 + cross-project `group/project#N`）。`/finish` SKILL.md 只加一句注释说明跨平台兼容，**零代码改动**。

## 3. helper API 契约

```
platform_issue.py [--platform github|gitlab] [--debug] <subcommand> [args...]
```

通用约定：

- 不传 `--platform` → 自动 detect（`git remote get-url origin` 含 `github.com` / 含 `gitlab` 字样 / 否则 unknown）
- `--debug` 隐藏 flag → stderr 输出 helper 内部跑了哪条 `gh`/`glab` 命令、收到的原始 json
- exit code：`0` 全部成功 / `1` 通用执行错误 / `2` 平台检测失败（unknown）/ `3` 认证失败 / `4` 上游 CLI（gh/glab）未安装
- stderr 始终含人话错误描述

### Subcommands

| 命令                                                                    | stdout                                                                   | 用途                                               |
| ----------------------------------------------------------------------- | ------------------------------------------------------------------------ | -------------------------------------------------- |
| `detect-platform`                                                       | `github` / `gitlab` / `unknown`                                          | 单纯探测                                           |
| `auth-status`                                                           | 简述（如 `github: logged in as foo`）                                    | 检查登录态；exit 3 if not authed                   |
| `repo-slug`                                                             | `owner/repo` (GH) 或 `namespace/project` (GL)                            | 项目标识                                           |
| `issue-create --title T --body-file F --label L1 --label L2 --label L3` | 单行 issue URL                                                           | 创 issue；stderr 输出 `created on github / gitlab` |
| `issue-view <N>`                                                        | 标准化 json（schema 见下）                                               | 读 issue 详情                                      |
| `label-list`                                                            | 一行一个 label name                                                      | 仅供 fallback；SKILL 优先读 yml                    |
| `label-sync-from-file <path>`                                           | 每行 TSV `<status>\t<name>[\t<msg>]` + 末行 `summary: N synced, M error` | 上 yml 中所有 label                                |

### `issue-view` 输出 schema（强制归一为 GitHub 字段名）

```json
{
  "number": 3,
  "title": "...",
  "body": "...",
  "url": "https://...",
  "labels": ["type:feat", "area:skill", "priority:P1"]
}
```

GitLab 端的 `iid` → `number`、`web_url` → `url`、`description` → `body`、`labels: ["str"]` 直接复用（GitHub 的 `labels: [{name, ...}]` 取 `.name`）。SKILL.md 模型读到的永远是 GitHub 风格 schema。

### `label-sync-from-file` 内部行为

- GitHub 分支：`gh label create --force --color "<RAW_HEX>" --description "<D>" "<NAME>"` 逐条
- GitLab 分支：`glab label list --output json` 取 name set；对每条 yml 条目，存在则 `glab label edit -n NAME -c "#HEX" -d D`，否则 `glab label create -n NAME -c "#HEX" -d D`
- color 转换在 helper 内自动：GitHub 用裸 hex、GitLab 加 `#` 前缀
- unknown 平台 → exit 2，每条不动

## 4. 实施步骤（按 commit 边界拆）

### Step 0：把本 PLAN 文件落到项目 docs

`cp ~/.claude/plans/smooth-floating-key.md docs/15-三件套skill支持GitLab双轨/PLAN.md`

### Step 1：实现 `scripts/platform_issue.py`（含 self-test）

- 单文件 ~300-400 行
- 顶部常量：subcommand 注册、字段映射表
- 函数分层：`_call_gh()` / `_call_glab()` 薄 subprocess 封装；每个 subcommand 一个 handler；统一在 handler 出口做字段归一
- 最小 yml parser + `--self-test` round-trip
- argparse subparsers + 顶层 try/except → 翻译成 exit 1 + stderr 人话

**先跑 `--self-test` 验证 yml parser + 字段映射正确，再继续。**

### Step 2：改 `install.sh` 加 `scripts/` 软链段

- 在现有 hooks 软链段之后插入对称循环
- `mkdir -p "$TARGET_DIR/scripts"` 一并加入
- 跑 `bash install.sh` 验证幂等（既有 `link_item` 的"已正确"分支接管）+ 软链建出来 + helper 可执行

### Step 3：改 SKILL.md（5 个文件）

按下表替换。每改完一个，单独 commit。

| 文件                                  | 改动                                                                                                                                                                                                                                                                                                                   |
| ------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `skills/backlog/SKILL.md`             | 5 处 gh 调用替换：`gh auth status` → helper `auth-status`；`gh label list --json name` → helper `label-list`（仅作 yml 缺失 fallback）；`gh issue create` → helper `issue-create`；`gh repo view --json nameWithOwner -q .nameWithOwner` → helper `repo-slug`；前置检查从「`gh auth status`」改为 helper `auth-status` |
| `skills/start/SKILL.md`               | L33 `gh issue view` → helper `issue-view <N>`；注明输出归一 json schema；issue 参数解析仍在 SKILL.md 里做（识别 `#N` / GitHub URL / **新增** GitLab URL `https://gitlab.com/.../-/issues/N` 模式）                                                                                                                     |
| `skills/finish/SKILL.md`              | 仅在 `Closes #N` 段加一行注释「在 GitHub 与 GitLab 默认分支均自动关 issue（GitLab 还支持 `Fixes`/`Resolves` 等关键词与 cross-project 引用），无平台分支处理需求」                                                                                                                                                      |
| `skills/bootstrap/SKILL.md`           | Step 3.3.5 整段替换为调 helper `label-sync-from-file .github/labels.yml`；Step 5 第 5/6 条提示文本更新（GitLab 不再"暂留"）                                                                                                                                                                                            |
| `skills/sync-project-config/SKILL.md` | §4.3 + §6 同上替换；保留 helper exit 2/3 时的「跳过 + 提示」兜底                                                                                                                                                                                                                                                       |

### Step 4：改 `GLOBAL_CLAUDE.md`「Backlog 与开发项管理」段

- heading 从「Backlog 与开发项管理（GitHub Issue 驱动）」→ 改为更平台中立措辞，如「Backlog 与开发项管理（Issue 驱动，GitHub / GitLab 双轨）」
- 三件套 skill 工作流段落补一句：「skill 内不直接调 `gh` / `glab`，全部走 `~/.claude/scripts/platform_issue.py` helper；helper 按 `git remote get-url origin` 自动 dispatch」
- `Closes #N` 那段补「GitHub 与 GitLab 均原生支持」

### Step 5：改 `README.md`

- 新增 `scripts/` 一节解释角色（"被 SKILL.md 调用的稳定脚本，软链到 `~/.claude/scripts/`"）
- 目录结构总览补 `scripts/`

### Step 6：本轮 SUMMARY + dogfood

按 GLOBAL_CLAUDE.md 「文档记录规范」写 `docs/15-.../SUMMARY.md`，含本轮决策（A/B/C 三决定 + critique 结果），后续 TODO（实地 GitLab repo 验证清单仍是独立 issue）。

## 5. 测试与验证（TDD where applicable）

按 GLOBAL_CLAUDE.md TDD 原则，helper 是「有清晰输入输出契约的纯函数 + CLI wrapper」，**适用 TDD**。

### 5.1 helper 内嵌单测（推荐）

`platform_issue.py --self-test` 跑：

1. **yml parser round-trip**：内嵌一段固定 yml 字符串（含 `---` header、`#` 注释、9 条 list of dict），parser 输出 list of dict，逐字段断言
2. **字段映射**：输入 GitLab json `{"iid": 3, "web_url": "...", "description": "...", "labels": ["a","b"]}`，输出 GitHub schema `{"number": 3, "url": "...", "body": "...", "labels": ["a","b"]}`
3. **color 规范化**：`normalize_color("0E8A16", "github")` → `"0E8A16"`；`normalize_color("0E8A16", "gitlab")` → `"#0E8A16"`；`normalize_color("#0E8A16", "github")` → `"0E8A16"`（防御重复 #）
4. **平台 detect**：mock `subprocess.run` 返回不同 origin URL，断言 detect 输出

`--self-test` 写在最前面，先红后绿，强制 helper 实现正确再继续 Step 2/3。

### 5.2 端到端 dogfood（手工，本轮在本仓库做）

- [x] 跑 `bash install.sh` 幂等通过
- [ ] 在本仓库（`pkulijing/claude-code-global`，GitHub remote）跑 `python3 ~/.claude/scripts/platform_issue.py auth-status` → 期望 exit 0 + "github: logged in"
- [ ] 跑 `python3 ~/.claude/scripts/platform_issue.py issue-view 3` → 期望输出本 issue（#3）归一 json，含 `"number": 3`
- [ ] 跑 `python3 ~/.claude/scripts/platform_issue.py repo-slug` → 期望 `pkulijing/claude-code-global`
- [ ] 跑 `python3 ~/.claude/scripts/platform_issue.py label-sync-from-file templates/_common/__root__/.github/labels.yml` —— **谨慎**：这会真的改本仓库 labels；建议建一个 sandbox repo 或临时把 yml 复制过来测；或改用 `--dry-run` flag（**新增 TODO**：是否给 sync 加 dry-run 模式）
- [ ] 临时 mock 一个 `git remote set-url origin https://gitlab.example/foo/bar.git` 跑 `detect-platform` → 期望 `gitlab` + exit 0；跑完恢复

### 5.3 实地 GitLab repo 验证

**out-of-scope** —— PROMPT 已明示，留给独立 issue（依赖手边有真实 GitLab 项目）。

## 6. 风险与回退

- **风险 1：python3 在某些 minimal Linux 不存在** —— macOS 自带；用户使用 Claude Code 的环境基本都是 dev box，python3 是事实标准。helper 在 install.sh 时不强校验 python3 存在，调用失败时 SKILL.md 看到 exit code → 报错引导
- **风险 2：自托管 GitLab URL 不含 `gitlab` 字样**（如 `git.company.com`） —— 沿用 round 14 启发式，detect → unknown → helper exit 2 → SKILL.md 提示用户用 `--platform gitlab` override（当前 SKILL.md 不会用，但 helper 接受）。**完整解决留独立 issue**（如调 `glab api /version` 探测）
- **风险 3：本轮触碰 5 个 SKILL.md 文件 + 1 个 install.sh + 1 个 GLOBAL_CLAUDE.md，体量略大** —— Step 3 按文件单独 commit，每个改动 < 100 行，回退粒度细
- **回退预案**：本轮所有 commit 走单一 PR；若 helper 设计在使用中暴露大问题，整 PR revert 即可回到 round 14 状态（GitLab 项目仍可用 `--label` 等手工 workaround）

## 7. 关键文件清单（实施时改动）

新增：

- `/Users/wujie/Personal/claude-code-global/scripts/platform_issue.py`
- `/Users/wujie/Personal/claude-code-global/docs/15-三件套skill支持GitLab双轨/PLAN.md`（Step 0 落盘）

修改：

- `/Users/wujie/Personal/claude-code-global/install.sh` — 加 `scripts/` 软链段
- `/Users/wujie/Personal/claude-code-global/skills/backlog/SKILL.md`
- `/Users/wujie/Personal/claude-code-global/skills/start/SKILL.md`
- `/Users/wujie/Personal/claude-code-global/skills/finish/SKILL.md` — 仅加注释
- `/Users/wujie/Personal/claude-code-global/skills/bootstrap/SKILL.md`
- `/Users/wujie/Personal/claude-code-global/skills/sync-project-config/SKILL.md`
- `/Users/wujie/Personal/claude-code-global/CLAUDE.md` 是项目 CLAUDE.md，**不动**；改 `~/.claude/CLAUDE.md` 的真源即 `GLOBAL_CLAUDE.md`
- `/Users/wujie/Personal/claude-code-global/GLOBAL_CLAUDE.md` — Backlog 段平台中立化
- `/Users/wujie/Personal/claude-code-global/README.md` — 加 `scripts/` 章节

## 8. 估时

约 1 个开发轮次（half-day to full-day）：

- helper 实现 + self-test：~3-4 小时（含 yml parser）
- install.sh + 5 个 SKILL.md 改写：~1-2 小时
- 文档（GLOBAL_CLAUDE / README / SUMMARY）：~1 小时
- dogfood + 边界 case 验证：~1 小时

## 9. 后续 TODO（不在本轮 scope）

- 实地 GitLab repo 端到端验证清单（quick action 首行规则、`.gitlab-ci.yml` 首跑、issue templates web UI）
- 自托管 GitLab URL 启发式增强（`glab api /version` 探测）
- helper `label-sync-from-file` 加 `--dry-run` 模式（dogfood 时发现需要）
- 若 helper 体量后续超 600 行，考虑拆 `scripts/lib/`
- 本仓库 `.cc-template.yml` `stacks: []` 状态修复（与本 round 无关，round 11 遗留）
