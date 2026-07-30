# rules/*.md 按需加载：从「无条件常驻」改为「显式 Read 契约 + paths 加成」

> 来自 [#70 rules/\*.md 被全文自动加载，与「命中触发条件才 Read」的设计意图冲突（每会话常驻 ~12.6k token）](https://github.com/pkulijing/claude-code-global/issues/70)
> Labels: `type:perf` `area:doc` `priority:P1`

## 背景

`rules/*.md` 经 `install.sh` 软链到 `~/.claude/rules/` 后，被 CC 当作**用户级 memory 目录**全文自动加载——每次会话、每个项目、无论是否命中触发条件。这与 `GLOBAL_AGENTS.md`「领域规则文档（rules/）」一节写明的设计意图（「命中触发条件时必须主动 Read 对应文件」）直接冲突：下沉到 `rules/` 是为了「避免本宪法臃肿」，但 token 成本一分没省，只是从一个文件挪到了八个文件。

issue 提出时是 5 份 ~12.6k token；本轮开轮时已增至 **8 份、正文合计 77,575 字符（≈19.4k token）**，外加 `GLOBAL_AGENTS.md` 自身 18,912 字符（≈4.7k token）——cc-global 一家占掉每会话约 **24k token** 常驻上下文，而任意单个项目里真正用得上的通常只有一到两份。

| 文件 | 字符 |
| --- | ---: |
| `rules/python.md` | 27,843 |
| `rules/ros2.md` | 17,243 |
| `rules/cloud-routine.md` | 9,814 |
| `rules/frontend.md` | 8,822 |
| `rules/shell.md` | 6,672 |
| `rules/scheduled-agent.md` | 6,271 |
| `rules/lark.md` | 5,305 |
| `rules/feishu-bot.md` | 3,605 |
| **rules 小计** | **77,575** |
| `GLOBAL_AGENTS.md` | 18,912 |

## 开轮前已完成的机制核查（用户对 issue 前提提出质疑，故先查证）

用户的质疑有两条：①「拆成 rules 文件不就是为了按需加载吗？怎么会全局默认加载？确定是真实行为？」②「按文件扩展名区分的机制根本不够 robust」。**两条都查清了，结论是：现象属实、且第二条担忧成立。**

### 结论 1：现象属实，根因在 CC 2.1.220 二进制内可定位

- **当场实证**：本轮开轮会话的系统提示里，八份 rules 全在，标题均为 `Contents of <path> (user's private global instructions for all projects)`——包括与本轮任务无关的 `ros2.md` / `feishu-bot.md`。
- **代码级根因**（`strings` 提取自 `~/.local/share/claude/versions/2.1.220`）：初始 memory 加载函数中，用户级分支把 `~/.claude/rules` 当 rules 目录整体扫入，`conditionalRule: false`：

  ```js
  if (pg("userSettings")) {
    let E = tPt("User");  r.push(...await Lpe(E, "User", n, !0));      // ~/.claude/CLAUDE.md
    let A = ffo();        // = join(~/.claude, "rules")
    r.push(...await ePt({rulesDir: A, type: "User", ..., conditionalRule: !1}))
  }
  ```

  而 `ePt` 的目录遍历里，过滤条件是：

  ```js
  c.push(...E.filter((A) => o ? A.globs : !A.globs))   // o = conditionalRule
  ```

  即：**没有 `globs` 的 `.md` 走无条件常驻，有 `globs` 的才走条件加载**。`globs` 来自 frontmatter 的 `paths` 键：

  ```js
  function fny(e){
    let {frontmatter:t, content:r} = Lp(e);
    if (!t.paths) return {content:r};                      // 无 paths → 无条件常驻
    let n = Zno(t.paths).map(o => o.endsWith("/**") ? o.slice(0,-3) : o).filter(o => o.length>0);
    if (n.length===0 || n.every(o => o==="**")) return {content:r};   // paths:["**"] 亦视为无条件
    return {content:r, paths:n}
  }
  ```

- **性质澄清**：这不是宪法刻意规避的「`@mention` 自动展开」，而是 `~/.claude/rules/` 这个**目录本身就是一个用户级 memory 目录**。`install.sh` 把仓库 `rules/` 软链成它，等于亲手把八份文档注册进了全局 memory。

### 结论 2：`paths` 只能当加成，不能当唯一入口

带 `paths` 的规则改走条件加载路径（`ifo()`），语义是「**Agent 碰到匹配的文件路径时才把该规则作为 attachment 注入**」，实测/读码得到的边界：

- **触发点有限**：`FileReadTool`（文本 / notebook / 图片）与 IDE 打开文件会把路径推入 `nestedMemoryAttachmentTriggers`；纯规划阶段未读文件、`Write` 一个全新文件等场景不触发。
- **匹配基准是 `originalCwd`**：用户级规则把触发文件路径 `relative(originalCwd, file)` 后用 `ignore` 包（gitignore 语义）匹配；落在 cwd 之外（结果以 `..` 开头）一律不匹配。
- **注入时机在「读完文件之后」**：规则到手时部分决策可能已经做出，削弱「动手前先读」的事前约束价值。
- **触发条件与文件面不是一一映射**：`lark.md` / `cloud-routine.md` / `scheduled-agent.md` / `feishu-bot.md` 的触发条件是「任务性质」，没有任何文件面；`shell.md` 甚至有一条是「向用户给出需手动粘贴的命令」；`CMakeLists.txt` 既可能是 ROS 2 也可能是普通 C++。

**因此本轮的定位是**：`paths` 的语义是「你正在碰这个文件 → 顺手递给你」，而 rules 的触发条件是「本轮任务的性质」，两者只部分重叠。真正的入口必须是 `GLOBAL_AGENTS.md` 的指针表 + 显式 Read；`paths` 只作免费加成。旁证：Codex 端（`~/.codex/rules/`）一直就是纯「指针表 + 主动 Read」模式，该契约在那一端已长期运行。

## 需求

1. **让 `rules/*.md` 退出无条件常驻**，把每会话常驻上下文从 ~24k token 降到只剩 `GLOBAL_AGENTS.md` 一份。
2. **补强宪法的显式 Read 契约**：rules 不再默认在上下文里，指针表从「省事的目录」升级为「唯一可靠入口」，措辞与位置需相应加强。
3. **给有文件面的 rules 配 `paths`** 作为加成（碰到匹配文件时自动送达），无文件面的靠契约。
4. **必须实测验证**，不能只凭读码——至少验证「加 `paths` 后新会话确实不再全文加载」与「碰到匹配文件时确实注入」两条。
5. 顺带确认对 `install.sh` 双轨软链、Codex 端无副作用。

## 约束与注意

- **实测的软链陷阱**：`~/.claude/rules` 软链指向**主 checkout** 的 `rules/`，在本轮 worktree 内改文件**不会**影响实测结果。验证时须临时重指软链到 worktree，测完恢复。
- 本轮改的是**指令规则文件本身**（`rules/*.md` + `GLOBAL_AGENTS.md`），按宪法属于「绝不自动跳过 review」的类别。
- 新增风险须显式承认：加 `paths` 后最坏情况**不是「照旧全文加载」**（issue 原文的判断在这点上不准确），而是「规则不在上下文里、且 Agent 忘了 Read」。这条风险的缓解手段必须在方案里写明。
