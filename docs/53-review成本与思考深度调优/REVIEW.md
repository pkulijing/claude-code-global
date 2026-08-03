# Round 53 · review 留痕

本轮改的是 `/review-loop` 自身。`~/.claude/skills/` 软链指向主 checkout，worktree 内改 SKILL.md 不即刻生效，故沿用 round 48 / 50 的**自举法**：手动按**新** SKILL.md 的规则跑，正好活体验证新编队。

- **选档**：diff 为 `agents/*.md` + `skills/*.md` + `GLOBAL_AGENTS.md` + `install.sh` + `README.md` / `CLAUDE.md` → Step 2 判定**不跳过**（指令规则文件 + 配置面）；不命中复杂特征（无并发 / 状态机 / 跨进程）→ **默认档**（`review-orchestrator` ×1 + `code-reviewer` ×3，角度 ①②③）。
- **闸 A（运行验证）**：本轮有可运行面，**已跑**：
  - `bash docs/53-review成本与思考深度调优/test-agents-link.sh` → 4 组 7 项全绿；
  - `python3 scripts/context_budget.py check-refs` → 无失效引用。

## 委派前撞到的两件事（未计入迭代轮数）

**1. 新 agent 类型不在当前会话热加载。** 首次用 `subagent_type: review-orchestrator` 委派直接报 `Agent type 'review-orchestrator' not found`——当前会话在 `~/.claude/agents/` 存在之前就启动了，agent 注册表在会话启动时定型。这条已写进本仓 `CLAUDE.md` 的开发注意事项，随即被自己撞上验证。

**改用 `claude --agent review-orchestrator -p <任务书>` 起 headless 会话当 orchestrator**：同一份定义、同样钉死的 model 与 effort，等价且不必重启当前会话。

**2. `--dangerously-skip-permissions` 被 auto mode 分类器拒绝**（合理）。改为显式只读白名单：`Read,Grep,Glob,Agent,TodoWrite,Bash(git:*),Bash(bash:*),Bash(python3:*),Bash(grep:*),…`。这也顺带验证了：**reviewer 编队跑在只读工具面上是可行的**，与 agent 定义里 `disallowedTools` 去掉 `Edit`/`Write` 的设计一致。

## 第 1 轮

**编队实测**：orchestrator 成功并行起 3 个 `code-reviewer`，角度清单从 `references/angles.md` 逐字转发。transcript 里**全程只有 `claude-sonnet-5`，没有 opus** —— 说明默认档没有误用 `code-reviewer-deep`，档位表按预期生效。

**finding：0 条。** 三个角度均 clean。各角度实际核对到的要点（留痕，非 finding）：

| 角度 | 核对结论 |
| --- | --- |
| ① 契约与装配 | `deploy_agent` 新增第 5 参 `link_agents` 的两处调用点（`install.sh:448,455`）参数顺序、默认值、省略行为均与改动前一致；`agents/*.md` 的三个 `name` 与 SKILL.md 档位表 / angles.md / 测试脚本的引用一致 |
| ② 缺陷定向扫描 | `"${5:-no}"` 默认值取法正确；三份 frontmatter 字段名与取值合法（`effort: medium` 在枚举内、`disallowedTools` 用的是减量语义）；`test-agents-link.sh` case 4 的 `grep` 匹配串经**字节级核对**（`cat -A`）与实际行一致，非假绿/假红；未见硬编码、资源泄漏、吞异常、重复实现 |
| ③ 项目规范合规 | 改动后的 `CLAUDE.md` / `GLOBAL_AGENTS.md` 逐条核对无违反；命中的 playbook（`shell.md`——新测试脚本含中文注释；`cloud-routine.md`——改了两条 routine 的 SKILL.md）均读了再判，无违反 |

**三要素并闸全过 → review clean ✅**（自动修复 0 轮，未触及 2 轮上限）

## 新档位的实测数据

| 项 | round 50 旧档（`sonnet` 全 `xhigh`） | round 53 新档（`sonnet` 全 `medium`） |
| --- | --- | --- |
| 编队 | orchestrator + 3 reviewer | orchestrator + 3 reviewer（同） |
| diff 性质 | 指令规则文件 | 指令规则文件 + shell（同类） |
| **耗时** | **~11 min** | **4 min 25 s** |
| 工具调用 / turns | 24 次工具调用 | 43 turns |
| token | 117,401（当时记录，口径未注明） | 输出 52,589 / 输入 86（不含 cache 读写） |
| finding ≥80 | 0 | 0 |

**口径诚实声明**：round 50 的 117,401 是当时从 Agent 工具返回值里抄的数，**没有注明是否含 cache 读**，所以两个 token 数字不保证同口径、不该当作精确比率用。**真正同口径可比的是耗时**——同样的默认档、同样 3 个 reviewer、同类的指令文件 diff，**11 min → 4 min 25 s**。

## ⚠ 这轮 review 证明了什么、没证明什么

**证明了**：新编队接线正确（专用类型起得来、effort 钉死生效、默认档不误用 opus、角度清单能原文转发、只读工具面够用），且**同类 diff 上耗时降到约 40%**。

**没证明**：降档后**难复现 bug 的检出率**没掉。理由有二：

1. 本轮 diff 是指令文件 + 一小段 shell，**不含并发 / 状态机 / 难复现代码**；
2. **0 finding 不构成检出率证据** —— round 50 的旧档在同类 diff 上同样是 0 条 ≥80（外加 2 条被置信闸滤掉的低置信项）。两边都 0，只能说明「新档没有变得更吵」，不能说明「新档不会漏」。

人类已拍板本轮**不做 A/B**（A/B 本身要烧的正是本轮想省的额度）。相应的升档判据写在 `SUMMARY.md` 的「局限性」里，并同步到 issue #98 的收尾评论。
