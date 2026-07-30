# PLAN：`rules/` → `playbooks/`，让领域规则文档真正按需加载

## 一、方案定位（与 issue #70 建议的分歧）

issue #70 建议「给 `rules/*.md` 加 `paths` 前置声明」。**本轮不采纳这条，改为给目录换一个 CC 不认识的名字。** 理由：

`~/.claude/rules/` 是 **Claude Code 的保留目录**，语义是「用户级 memory 的模块化分片，可选加路径作用域」——放进去的 `.md` **默认就是系统提示的一部分**，`paths` 只是给它加一个作用域开关。而我们要的是「一批按需读的文档」。加 `paths` 等于：先把文档放进一个默认常驻的目录，再用 frontmatter 去关掉那个我们本来就不想要的默认值。换个中性目录名则从根上不产生这个默认值。

三条决定性理由：

1. **不再依赖 CC 内部行为**。这次的坑正是 CC 的加载语义在我们不知情时生效；`paths` 的解析、`/**` 归一化、`ignore` 包匹配、相对 `originalCwd` 这些全是未文档化的实现细节，随版本漂移。中性目录名下这些一概不适用。
2. **两端对称**。Codex 端（`~/.codex/rules/`）本来就只是「文件躺在那里，靠 `AGENTS.md` 指针主动 Read」——同一份契约在那端已长期运行且工作正常。改名后 CC 与 Codex 机制完全一致，一句话说得清。
3. **`paths` 加成本身价值有限**：它的注入时机是「**读完文件之后**」，而契约要求的是「**动手前先读**」——安全网晚一步到场；且触发点只有 `FileReadTool` 与 IDE 打开文件，纯规划阶段、`Write` 新文件均不触发；匹配还要求路径落在 `originalCwd` 之内。

**代价**（明确承认）：改完之后，八份文档 100% 依赖「宪法指针表 + 显式 Read」这一条通路。这条契约此前因为文档一直全文常驻而**从未被真正检验过**。缓解手段见 §六。

目录名 `playbooks/` 已核查不是 CC 保留名（二进制里零 `join(configDir, "playbooks")` 构造）。

## 二、改动清单

### 2.1 目录改名

```
git mv rules playbooks
```

八份文档内容本身不变，仅改各自顶部自述头里的路径（见 2.4）。

### 2.2 `install.sh`

1. 第 344–348 行的 rules 软链段改为 `playbooks`（`link_item "$REPO_DIR/playbooks" "$agent_home/playbooks"`），注释同步。
2. **新增旧路径迁移清理**——这是必须项：老机器上 `~/.claude/rules` 与 `~/.codex/rules` 软链仍在，不删则八份文档继续常驻，本轮收益归零。新增函数：

   ```sh
   # 旧路径迁移：本仓曾把 rules/ 软链到 <agent_home>/rules，而 rules 是 CC 保留目录名，
   # 会让文档被当作用户级 memory 全文注入每个会话。仅当它确实是指向本仓的软链时才删。
   unlink_legacy_dir() {
       local link="$1" expect="$2"
       [ -L "$link" ] || return 0                        # 真实目录 / 不存在 → 一律不碰
       [ "$(readlink "$link")" = "$expect" ] || return 0  # 指向别处的软链 → 不碰
       rm -f "$link"
       info "已清理旧的 ${link}（rules 是 CC 保留目录名，改用 playbooks）"
   }
   ```

   在 `deploy_agent` 内、链接 `playbooks` 之前调用 `unlink_legacy_dir "$agent_home/rules" "$REPO_DIR/rules"`。
   **安全边界**：非软链（用户自建真实 `rules/` 目录）不动、指向别处的软链不动 —— 只回收本仓自己留下的那一个。
3. 为让迁移逻辑可单测，在主流程段（第 381 行起）之前加一行 source 守卫：

   ```sh
   [ "${CCG_INSTALL_LIB_ONLY:-0}" = "1" ] && return 0
   ```

### 2.3 `GLOBAL_AGENTS.md`（宪法）——本轮的核心改动

「领域规则文档（rules/）」一节整体改写。目标：把指针表从「省事的目录」升级为**唯一入口**，并让 Agent 知道「这些文件默认不在上下文里」这个新事实。

改写后结构：

```markdown
## 领域规则文档（playbooks/）

"领域专属"规则（语言、栈、流程）下沉到 `playbooks/<topic>.md`（CC 端实际路径
`~/.claude/playbooks/<topic>.md`、Codex 端 `~/.codex/playbooks/<topic>.md`——同一份
文档被两端共读，按自己所在端取路径）。

**这些文件默认不在你的上下文里。** 本宪法只保留下表「触发条件 → 读哪个文件」，不复述
各规则内容；Agent **命中触发条件时，必须在动手之前主动 Read 对应文件**——这是唯一入口，
没有任何机制会替你把它们送到手边。

- **先 Read 再动手**，不是"边做边查"：这些文档里大量是禁令与固定坑（"禁止 pip install"、
  "`$var` 紧贴 CJK 必须写 `${var}`"），事后读等于事后返工。
- **不得凭记忆作答**：你对某份规则内容的"印象"可能来自别的项目、别的版本，或纯属幻觉。
  命中就 Read，哪怕你觉得记得。
- **拿不准算不算命中，就 Read**：一次 Read 的代价远低于一次踩坑——本仓沉淀的每条规则背后
  都是一次实际返工。

> 目录名是 `playbooks/` 而非 `rules/`，因为 `~/.claude/rules/` 是 Claude Code 的**保留
> 目录**：放进去的 `.md` 会被当作用户级 memory 全文注入每一个会话，与本节"按需读"的设计
> 意图正相反。**别改回去。**

当前已沉淀的领域规则（命中触发条件即 Read）：
（下表原样保留，仅路径 rules/ → playbooks/）
```

表格条目本身不改写触发条件措辞——现有描述已足够可判别，本轮不夹带。

### 2.4 其余引用（仅改路径字符串，不改语义）

| 文件 | 处理 |
| --- | --- |
| `playbooks/*.md` × 8 | 各自顶部自述头 `本文档由 …仓库的 rules/x.md 提供 / 软链到 ~/.claude/rules/x.md` → `playbooks` |
| `README.md`（15 处） | 目录结构说明、规则清单链接 |
| `CLAUDE.md`（2 处） | `rules/` 目录说明条目 |
| `skills/routine-docs/SKILL.md`（11 处） | 落点判定、共享登记文件清单、指令规则文件识别 |
| `skills/review-loop/SKILL.md`（5 处） | 「指令规则文件绝不跳过 review」的清单 |
| `skills/bootstrap/SKILL.md`（2 处） | |
| `skills/{start,quick,sync-project-config}/SKILL.md`（各 1 处） | |
| `templates/ros2/__subpath__/src/ros2_{cpp,py}_pkg/README.md` | 各 1 处 |
| `docs/DEVTREE.md`（8 处） | 活文档索引，需更新 |
| `docs/25…49/*`（历史轮次文档） | **不动** —— 它们是当时事实的记录，改写等于篡改历史 |

### 2.5 本仓 `CLAUDE.md` 补一条「保留名」教训

宪法里只放短版（"别改回去"）；详细版落本仓 `CLAUDE.md`，因为它只在开发本仓时才用得上：

> **往 `~/.claude/` 下新增目录前，先确认该名字不是 CC 保留名。** 已知保留（CC 二进制里有
> `join(configDir, X)` 构造）：`rules` / `skills` / `agents` / `commands` / `hooks` /
> `plugins` / `workflows` / `themes` / `plans` / `tasks` / `teams` / `projects` /
> `sessions` / `cache` / `backups` / `debug` / `sessions`。本仓的 `scripts/` /
> `templates/` / `playbooks/` 经核查均非保留名。核查方法：`strings <cc 二进制>` 后搜
> `join(...)` 构造。踩过一次的代价见 `docs/51-rules按需加载/`。

## 三、验证（TDD 正序）

### 3.1 红态已确证，无需再造

「八份全文常驻」在开轮会话里已当场取证（系统提示里八份俱在，标题为
`(user's private global instructions for all projects)`），并已在 CC 2.1.220 二进制里定位到
产生该行为的三段代码（见 PROMPT.md）。**红态不需要再跑一遍。**

### 3.2 `install.sh` 迁移逻辑的沙盘测试（真正需要先写测试的部分）

这是本轮唯一有分支逻辑、且**误判会删掉用户真实目录**的代码，按 shell.md §4 配沙盘测试
`docs/51-rules按需加载/test-unlink-legacy.sh`（副作用全落 `mktemp -d`，断言取证于真实文件系统状态而非日志字符串）：

| 用例 | 前置状态 | 期望 |
| --- | --- | --- |
| 1 | `<home>/rules` 是指向 `$REPO_DIR/rules` 的软链 | 被删除 |
| 2 | `<home>/rules` 是用户自建的**真实目录**（内含文件） | 原样保留，文件不丢 |
| 3 | `<home>/rules` 是指向**别处**的软链 | 原样保留 |
| 4 | `<home>/rules` 不存在 | no-op，退出码 0 |
| 5 | `<home>/rules` 是**断链**（指向已被 `git mv` 掉的 `$REPO_DIR/rules`） | 被删除（这正是升级路径上的真实形态） |

用例 5 是关键：`git mv` 之后旧软链就是断的，`[ -L ]` 仍为真、`readlink` 仍返回原始目标字符串，
故上面的实现能覆盖；**但必须先写这条测试确认，不能想当然**（`[ -e ]` / `readlink -f` 在断链上的行为
与 `[ -L ]` / `readlink` 不同，写错就漏删，本轮收益归零且无人察觉）。

测试通过 `CCG_INSTALL_LIB_ONLY=1 source install.sh` 拿到函数，不触发主流程。

### 3.3 端到端验证：常驻上下文真的消失了

**必须实测，不接受只凭读码。** 步骤（顺序不能乱）：

1. 在 worktree 内跑 `bash install.sh` —— 注意这会把 `~/.claude/playbooks` 软链指向 **worktree** 的目录。
2. 在一个**与本仓无关的项目**（如任一 Python 仓）开一个全新 CC 会话，跑 `/context`：
   - 期望：`Contents of .../playbooks/*.md` **一条都不出现**；
   - 期望：`~/.claude/CLAUDE.md`（宪法）仍在；
   - 记录 Memory / system prompt 的 token 数，与改前对比应下降约 19k。
3. 同一会话内 Read 一个 `.py` 文件，再看上下文 —— 期望 `python.md` **仍不出现**（确认已彻底退出自动加载通路，而非改走条件通路）。
4. **`/finish` 合并回主分支之后**，在主 checkout 跑一次 `bash install.sh`，把 `~/.claude/playbooks` 软链改回指向主 checkout —— 否则 worktree 被清理后软链即断，八份文档对两端同时消失。
   **时序不能提前**：验证期间主 checkout 尚未合并、根本还没有 `playbooks/` 目录，此时跑 install 只会 warn 跳过、软链仍指向 worktree，等于没做。此步写进 `/finish` 的收尾 checklist。
5. 确认 `~/.claude/rules` 与 `~/.codex/rules` 已被迁移逻辑清掉。

> `claude -p` 自动化探针（用 `--output-format json` 读 `usage.input_tokens` 做客观口径）会先试；
> 若被权限门禁拦下（无头 `claude` 拉起属已知被拦场景），就整理成一条 `bash ~/x.sh` 交给用户执行，
> 不在这里空转。

### 3.4 契约可靠性抽查（本轮做一次，不作为放行闸）

改完后开一个干净会话，喂一条**命中触发条件但不碰任何匹配文件**的需求（如「帮我设计一个每天定时唤起
无头 agent 整理文档库的方案」），观察 Agent 是否**主动 Read `playbooks/scheduled-agent.md`**。
这条抽查的作用是给「契约是否真能替代常驻」积累第一手证据，结果写进 SUMMARY.md 的局限性一节；
**不通过也不阻断本轮**（那属于宪法措辞的后续迭代，而非本轮交付物）。

## 四、执行顺序

1. 写 `test-unlink-legacy.sh`，跑 → 红（函数还不存在）
2. 改 `install.sh`（迁移函数 + source 守卫 + playbooks 软链），跑测试 → 绿
3. `git mv rules playbooks`，改八份文档自述头
4. 改 `GLOBAL_AGENTS.md`（核心）
5. 改 `README.md` / `CLAUDE.md`（含 2.5 的保留名教训） / 六个 skill / 两个 ros2 模板 README / `docs/DEVTREE.md`
6. 全仓复扫，确认非 docs/ 区域已无 `rules/` 残留（`grep -rn 'rules/' --include='*.md' --include='*.sh' . | grep -v '^./docs/'`）
7. 跑 `bash install.sh` + §3.3 端到端验证
8. `/commit`（**本轮改的是指令规则文件本身，按宪法绝不跳过 review**）

## 五、不做的事（划清边界）

- **不给任何文档加 `paths` frontmatter** —— 单一机制，见 §一。
- **不改八份文档的正文内容**，只改自述头路径。内容优化另开轮。
- **不改触发条件表的措辞**。若 §3.4 抽查暴露路由不清，另开轮处理，不在本轮夹带。
- **不加 hook 兜底**（如用 UserPromptSubmit 做关键词路由提示）—— 记入后续 TODO，本轮不引入新机制。
- **不动历史 docs/**。
- **不把 lark / cloud-routine 等并进对应 skill** —— issue 里提到的那条路是另一个话题。

## 六、风险与缓解

| 风险 | 缓解 |
| --- | --- |
| **Agent 不主动 Read，规则事实上失效**（本轮引入的主要新风险） | 宪法三条硬约束（先读再动手 / 不凭记忆 / 拿不准就读）+ §3.4 抽查取证；后续可加 hook 兜底 |
| 老机器旧软链未清，收益归零且无人察觉 | `unlink_legacy_dir` + 沙盘用例 5（断链形态）+ §3.3 步骤 5 人工确认 |
| 误删用户自建的真实 `~/.claude/rules` | 沙盘用例 2/3 钉死：非软链、指向别处一律不碰 |
| worktree 内 install 留下断软链 | §3.3 步骤 4 显式回滚，写进执行 checklist |
| 引用改漏，文档指向不存在的路径 | §四 步骤 6 全仓复扫 |
| Codex 端受影响 | Codex 不解析 frontmatter、也不自动加载该目录，改名对它只是路径变更；`install.sh` 双轨同步处理 |

## 七、额外产物

- `docs/51-rules按需加载/test-unlink-legacy.sh` —— install.sh 迁移逻辑的沙盘测试
- `docs/51-rules按需加载/PROMPT.md` 里的机制考据（CC 2.1.220 memory 加载路径的代码级定位）—— 后续再遇到「某文件是不是被自动加载」的问题时可直接复用这套 `strings` 取证方法
