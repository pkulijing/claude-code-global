# Round 23 实现计划：/finish 跨项目反思可沉淀流程并提 issue

## 目标拆解

1. `/finish`（全局 skill，作用于任意项目）新增一步：反思本轮是否有可沉淀的重复性流程。
2. 对「跨项目资产」类候选，propose → 用户确认 → **跨仓库**向 claude-code-global 提 issue。
3. 这类 issue 不进任何 BACKLOG 索引。
4. 「仅当前项目可复用」类候选 → 仅建议本地 `/backlog`，不自动 file。

## 关键设计

### A. `platform_issue.py issue-create` 支持跨仓库 `--repo`

当前 `cmd_issue_create` 用当前 cwd 的 remote 推断平台、在当前仓库建 issue。跨仓库提 issue 到 claude-code-global 需要：

- 新增 `--repo <slug>` 参数，透传给 `gh issue create --repo <slug>` / `glab issue create --repo <slug>`（`-R` 长写法）；
- 平台用顶层已有的 `--platform` override 显式指定（由 skill 从 `~/.claude/global-repo` 派生后传入），不依赖 cwd remote。

**可测性重构（TDD 抓手）**：把命令拼装抽成纯函数

```python
def build_issue_create_cmd(platform, title, body_path, labels, repo):
    # 返回 argv 列表，不执行
```

`cmd_issue_create` 改为「读 body 校验 → 调 build_issue_create_cmd → \_run → 解析 URL」。

### B. 目标 slug + platform 动态派生（skill 内）

```bash
GLOBAL_DIR="$HOME/.claude/global-repo"          # install.sh 软链到本仓库
URL=$(git -C "$GLOBAL_DIR" remote get-url origin)
SLUG=$(printf '%s' "$URL" | sed -E 's#\.git$##; s#^git@[^:]+:##; s#^https?://[^/]+/##')
case "$URL" in *github.com*) PLAT=github;; *gitlab*) PLAT=gitlab;; *) PLAT="";; esac
```

不硬编码 `pkulijing/claude-code-global`，多设备/改名都成立。`$GLOBAL_DIR` 不存在或派生失败 → 跳过 file，仅在 SUMMARY 记录候选，不阻塞 finish。

### C. `/finish` 新增 Step 1.6「跨项目可沉淀流程反思」

放在 Step 1.5（不再追踪补录）之后、Step 2（issue/BACKLOG）之前 —— 与其它 SUMMARY-time 反思步骤聚在一起，且跨仓库 file 与当前仓库 commit/worktree 正交。

子步：

1. **反思候选**，判定标准（尽量三条都满足才算）：
   - 跨项目通用（不是本项目特有逻辑）；
   - 有具体落点（指明改哪个 template 字段 / 哪个 skill·hook / GLOBAL_AGENTS.md 哪段）；
   - 出现 ≥2 次的模式，或明显通用。
   - **最多保留 3 条**（按价值排序取 top 3，宁缺毋滥，控制噪音）。
2. **归类去向**：
   - 跨项目资产（templates / 全局 skill·hook / GLOBAL_AGENTS.md）→ 跨仓库提到 claude-code-global；
   - 仅当前项目可复用 → 文字建议「在本项目跑 `/backlog`」，本步不 file。
3. **无候选** → 打印「本轮无可沉淀项」，结束本步。
4. **当前仓库就是 claude-code-global**（`git rev-parse --show-toplevel` == `realpath ~/.claude/global-repo`）→ 跨项目资产候选改为建议走本地 `/backlog`（遵循本项目「issue 进 BACKLOG」约定），不 API 自 file。
5. **有跨项目候选** → **逐条**用 AskUserQuestion 问用户：现在提 / 先放一放 / 不提。逐条决策、可只提其中几条；支持「先放一放」不阻塞。
6. **用户确认要提的**，每条：
   - 派生 SLUG + PLAT（设计 B）；
   - 选三轴 label：`type:*`（feat/refactor/docs 按性质）+ `priority:P2`（默认排队）+ `area:*`（读 `$GLOBAL_DIR/.github/labels.yml` 选 install/skill/hook/template/doc）；
   - 写临时 body md：来源项目名 + 轮次 + 为什么值得沉淀 + 具体落点建议 + 「跨项目自动沉淀、未进 BACKLOG」标注；
   - 调 `python3 $HOME/.claude/scripts/platform_issue.py --platform $PLAT issue-create --repo $SLUG --title "..." --body-file /tmp/xx.md --label type:X --label area:Y --label priority:P2`；
   - 打印返回的 issue URL。
7. **不更新任何 BACKLOG.md**（明示：跨项目沉淀 issue 不进索引）。

### D. SUMMARY 新增「## 可沉淀项」段（Step 1）

SUMMARY 末尾（后续 TODO 之后）加一段，列本轮识别到的可沉淀流程及去向；无则写「暂无」。这是本地持久记录，Step 1.6 据此对跨项目项采取行动。

## 测试用例（TDD，先红后绿）

`scripts/platform_issue.py --self-test` 新增 `build_issue_create_cmd` 用例：

| 场景                     | 期望 argv 关键片段                                                                 |
| ------------------------ | ---------------------------------------------------------------------------------- |
| github 无 repo 无 label  | `gh issue create --title T --body-file BF`                                         |
| github 有 repo + 2 label | 含 `--repo owner/x` 且每个 label 一组 `--label`                                    |
| gitlab 有 repo           | `glab issue create ... --description ... --yes --repo owner/x`，label 用 `--label` |
| gitlab 无 repo           | 不含 `--repo`                                                                      |

先加会失败的断言（函数还不存在）→ 实现 `build_issue_create_cmd` → `--self-test` 转绿。

## 涉及文件

1. `scripts/platform_issue.py` — 抽 `build_issue_create_cmd` 纯函数 + 加 `--repo` 参数 + self-test 用例。
2. `skills/finish/SKILL.md` — Step 1 加「可沉淀项」段说明；新增 Step 1.6。
3. （评估）`GLOBAL_AGENTS.md` — 是否在 /finish 描述里点一句新行为；倾向不改，SKILL 为真源。
4. SUMMARY README review：本轮改 skill 行为属「面向用户约定」，finish 时按 Step 3.5 评估 README。

## 验证

- `python3 scripts/platform_issue.py --self-test` 通过；
- 干跑：构造命令检查（self-test 覆盖），不真建测试 issue；
- 真·端到端 file 留到本轮 `/finish` 时若有真实候选再 dogfood。

## 不做（控制 scope）

- 不做方向 B（候选自动落 BACKLOG/memory 成跟进入口）；
- 不起独立 `/distill` / `/retro` skill（方向 C）；
- 不自动 file（坚持 propose → 确认）。
