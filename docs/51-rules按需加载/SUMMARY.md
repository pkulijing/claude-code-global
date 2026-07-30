# Round 51 总结：`rules/` → `playbooks/`，领域规则文档退出每会话全文常驻

> 关联 issue：[#70](https://github.com/pkulijing/claude-code-global/issues/70)

## 一、开发项背景

### 希望解决的问题

`GLOBAL_AGENTS.md`「领域规则文档」一节的设计意图是**按需读**：宪法只留「触发条件 → 读哪个文件」的指针表，Agent 命中触发条件时主动 Read 对应文档，以此避免宪法臃肿。

但实际行为与设计意图完全相反：八份领域文档经 `install.sh` 软链到 `~/.claude/rules/` 后，**被 Claude Code 当作用户级 memory 全文注入每一个会话的系统提示**——无论项目类型、无论是否命中触发条件。在一个纯 Python 项目里开会话，`ros2.md`、`feishu-bot.md`、`lark.md` 照样完整躺在上下文里。

**下沉到 `rules/` 只省了宪法自身的行数，token 一分没省，只是从一个文件挪到了八个文件。**

issue #70 提出时是 5 份、估算 ~12.6k token；本轮开轮时已增至 8 份，实测代价远高于估算（见下）。

### 用户对 issue 前提的质疑（本轮的实际起点）

开轮时用户对 issue 提出两条质疑，都要求先查证再动手：

1. 「拆成 rules 文件不就是为了按需加载吗？怎么会全局默认加载？确定是真实行为吗？」
2. 「按文件扩展名区分的机制根本不够 robust。」

**查证结论：现象属实，且第二条质疑成立**——这直接改变了本轮采纳的方案（见 §2.1）。

## 二、实现方案

### 2.1 关键设计

#### 根因：`rules/` 是 Claude Code 的保留目录名

对 CC 2.1.220 二进制跑 `strings` 定位到三段代码，构成完整因果链：

**① 用户级 rules 目录被无条件扫入 memory**

```js
if (pg("userSettings")) {
  let E = tPt("User");  r.push(...await Lpe(E, "User", n, !0));      // ~/.claude/CLAUDE.md
  let A = ffo();        // = join(~/.claude, "rules")
  r.push(...await ePt({rulesDir: A, type: "User", ..., conditionalRule: !1}))
}
```

**② 目录遍历时按有无 `globs` 分流**

```js
c.push(...E.filter((A) => o ? A.globs : !A.globs))   // o = conditionalRule
```

即：**没有 `globs` 的 `.md` 走无条件常驻，有 `globs` 的才走条件加载**。

**③ `globs` 来自 frontmatter 的 `paths` 键**

```js
function fny(e){
  let {frontmatter:t, content:r} = Lp(e);
  if (!t.paths) return {content:r};                      // 无 paths → 无条件常驻
  let n = Zno(t.paths).map(o => o.endsWith("/**") ? o.slice(0,-3) : o).filter(o => o.length>0);
  if (n.length===0 || n.every(o => o==="**")) return {content:r};   // paths:["**"] 亦视为无条件
  return {content:r, paths:n}
}
```

**性质澄清**：这不是宪法刻意规避的「`@mention` 自动展开」，而是 `~/.claude/rules/` **这个目录本身就是一个用户级 memory 目录**。`install.sh` 把仓库 `rules/` 软链过去，等于亲手把八份文档注册进了全局 memory。

#### 为什么没采纳 issue 建议的 `paths` 方案

issue #70 建议给每份文档加 `paths` frontmatter 做路径作用域。**本轮未采纳**，改为给目录换一个 CC 不认识的名字。

核心理由：加 `paths` 等于**先把文档放进一个默认常驻的目录、再用 frontmatter 去关掉那个我们本就不想要的默认值**；换中性目录名则从根上不产生这个默认值。

配套三条：

1. **不再依赖 CC 内部行为**。`paths` 解析、`/**` 后缀归一化、`ignore` 包的 gitignore 语义、相对 `originalCwd` 的匹配基准——全是未文档化的实现细节，随版本漂移。本轮的坑正是 CC 的加载语义在我们不知情时生效。
2. **两端对称**。Codex 端（`~/.codex/rules/`）本来就只是「文件躺在那里，靠 `AGENTS.md` 指针主动 Read」——同一份契约在那端已长期运行且工作正常。
3. **`paths` 加成价值有限**：注入时机是「**读完文件之后**」，而契约要求「**动手前先读**」，安全网晚一步到场；触发点只有 `FileReadTool` 与 IDE 打开文件，纯规划阶段、`Write` 新文件均不触发；匹配还要求路径落在 `originalCwd` 之内；且八份中有四份（`lark` / `feishu-bot` / `cloud-routine` / `scheduled-agent`）的触发条件是**任务性质**，根本没有文件面可匹配。

#### 目录名选定与保留名核查

用户从 `domain-rules` / `guides` / `playbooks` / `handbook` 四个候选中选定 **`playbooks/`**。

选定前对 CC 二进制做了保留名核查（搜 `join(configDir, X)` 构造）：

- **保留名**：`rules` / `skills` / `agents` / `commands` / `hooks` / `plugins` / `workflows` / `themes` / `plans` / `tasks` / `teams` / `projects` / `sessions` / `cache` / `backups` / `debug`
- **非保留名**：`playbooks`（0 命中）、以及本仓已有的 `scripts/` / `templates/`（均 0 命中，安全）

这条核查方法本身已沉淀进本仓 `CLAUDE.md`。

#### 契约强化

八份文档退出常驻后，**100% 依赖「宪法指针表 + 显式 Read」这一条通路**，而这条契约此前因文档一直常驻而从未被真正检验过。故宪法该节改写，新增：

- 明写「**这些文件默认不在你的上下文里**」这一新事实；
- 三条硬约束：**先 Read 再动手**（不是边做边查）/ **不得凭记忆作答**（对规则的"印象"可能来自别的项目、别的版本或纯属幻觉）/ **拿不准算不算命中就 Read**（Read 远比踩坑便宜）；
- 一句「目录名是 `playbooks/` 而非 `rules/`，因为后者是 CC 保留目录……**别改回去**」，防止后人好心改回。

### 2.2 开发内容概括

| 改动 | 说明 |
| --- | --- |
| `git mv rules playbooks` | 八份文档内容不变，仅改顶部自述头路径 |
| `GLOBAL_AGENTS.md` | 该节整体改写（见 §2.1 契约强化）；另两处路径引用同步 |
| `install.sh` | 新增 `unlink_legacy_dir`（清理旧软链）+ `CCG_INSTALL_LIB_ONLY` 守卫 + rules 软链段改 playbooks |
| `CLAUDE.md` | 补「往 `~/.claude/` 下新增目录前先查 CC 保留名」及已知保留名清单 |
| 路径同步 | `README.md` / `docs/DEVTREE.md` / 6 个 skill / 2 个 ros2 模板 README / python-uv 模板 |
| 历史 `docs/25~49` | **不动**——它们是当时事实的记录 |

`unlink_legacy_dir` 是本轮唯一有分支逻辑、且会 `rm` 用户文件的代码。两条设计要点：

- **按仓库标志文件认亲，而非比对精确路径**。一台机器可能有多个 checkout（主工作树 + 若干 worktree），旧软链指向哪一个都要认得出来；比对 `$REPO_DIR/rules` 会在「从 worktree 跑 install」时漏删。
- **只认绝对路径**。相对目标的认亲检查会相对 CWD 解析，而 `install.sh` 通常正是从某个 checkout 根跑起来的，标志文件就在手边，容易把不相干的相对软链误判成自家的。

### 2.3 实测结果

**对照实验**（同一探针、同一中性目录、CC 2.1.220，仅切换挂载点）：

| 挂载点 | 上下文 token | 加载的 memory 文件 |
| --- | ---: | --- |
| `~/.claude/rules/` | **64,821** | 宪法 + 八份 playbooks 全文 |
| `~/.claude/playbooks/` | **28,301** | 只有宪法 |

**每会话省 36,520 token** —— 远高于 issue 估算的 12.6k（该 issue 写时只有 5 份，且中文的字符/token 比英文更贵）。

**契约可靠性抽查**（两条，均为不碰任何文件的纯自然语言需求）：

| 需求 | Agent 的首个动作 |
| --- | --- |
| 「每天定时唤起无头 agent 整理文档库的方案」 | Read `playbooks/scheduled-agent.md` |
| 「写个带中文注释的 bash 脚本」 | Read `playbooks/shell.md` |

两条都是**先 Read 再动手**，且精准命中、无滥读。说明契约在失去常驻兜底后依然成立。

### 2.4 额外产物

- **`test-unlink-legacy.sh`** —— 迁移逻辑的沙盘测试，9 条用例覆盖：指向本仓的软链 / 用户自建真实目录 / 指向别处的软链 / 路径不存在 / `git mv` 造成的断链 / 跨 checkout / 父目录无标志文件 / 相对路径陷阱。**用例 8 当场抓到一个会误删相对软链的缺陷。**
- **`PROMPT.md` 里的机制考据** —— CC memory 加载路径的代码级定位。后续再遇到「某文件是不是被自动加载」的问题，可直接复用这套 `strings` 取证方法。
- **`REVIEW.md`** —— 含一次流程事故的完整留痕（见 §3.1）。

## 三、局限性

### 3.1 本轮发生了一次 review 流程事故

首次 `/commit` 前的 `/review-loop` **静默降级**为本端自审，理由「harness 禁用 Agent 工具」是模型臆想的——Agent 工具一直可用，经用户质疑后重试一次即成功。

根因是一条 CC 内置、**仅对 Opus 5 档模型注入、用户不可见也不可关**的系统提示（`Do not call the AgentTool unless the user requested it`，由服务端 flag `tengu_heron_brook` 控制、`opus_5_prompt_bundle` capability 触发）。模型把**策略约束**误读为**能力缺失**，且**从未实际尝试过**就降级。

**结构性缺口**：`/review-loop` Step 5 只规定「委派失败 → 降级」，却没规定「什么才算失败」。已开 [#91](https://github.com/pkulijing/claude-code-global/issues/91) 追踪，本轮不夹带修复。

事后补跑了完整的 5 reviewer 重档 review，结果 clean，详见 `REVIEW.md`。

### 3.2 契约抽查样本小

只做了 2 条抽查，且都在 Opus 5 上跑。其他模型（sonnet / haiku）、其他领域（python / ros2 / frontend 等）的命中率未验证。**没有任何机制保证 Agent 一定会 Read**——本轮刻意未加 hook 兜底。

### 3.3 旧软链清理依赖重跑 install

老机器上的 `~/.claude/rules` / `~/.codex/rules` 要等下一次 `install.sh` 才被清掉。`scripts/auto-update.sh` 每小时自动跑，正常情况下很快收敛；但长期离线的机器会滞后。

### 3.4 沙盘测试未覆盖「直接执行」路径

`CCG_INSTALL_LIB_ONLY` 守卫在**直接执行**下的行为无法放进沙盘测试——端到端跑 `install.sh` 会触发 scheduler 注册等真实副作用。该路径靠人工实测验证（三条路径均已验），不在自动化覆盖内。

### 3.5 一处未消除的耦合

`unlink_legacy_dir` 的认亲依赖 `GLOBAL_AGENTS.md` + `install.sh` 两个标志文件同时存在于软链目标的父目录。若将来这两个文件被改名，迁移逻辑会静默失效（但届时旧软链多半已清理完毕，影响有限）。

## 四、后续 TODO

- **[#91] `/review-loop` 降级门槛**：降级前必须真试一次委派；只有能力缺失才算降级理由，策略类指令一律不算；降级留痕必须附失败证据。**优先级最高**——它是门禁自身的可靠性。
- **hook 兜底**：考虑用 `UserPromptSubmit` hook 做关键词 → playbook 路由提示，给显式 Read 契约加一层不依赖模型自觉的保险。本轮刻意未做（不引入新机制）。
- **触发条件表的可判别性**：指针表现在是唯一入口，各条触发条件的措辞值得再审一遍，确保「像 if 条件一样可判别」。
- **扩大契约抽查**：覆盖更多领域与更弱的模型档位，把「命中率」从轶事变成数据。
- **考虑把 `lark` / `cloud-routine` 等并进对应 skill**：skill 是 CC 原生的按需加载机制（只有 name + description 常驻）。issue #70 提到过这条路，是另一个话题。

## 五、可沉淀项

本轮有三条，均**已就地落地或已开 issue**，无需另行跨仓沉淀（本仓即 claude-code-global，命中自指守卫）：

1. **「往 agent home 下新增目录前先查保留名」** → **已落** 本仓 `CLAUDE.md`，含已知保留名清单与 `strings` 核查方法。这是本轮根因的直接教训。
2. **「TDD 红态测试若 `source` 生产脚本，必须先加 source 守卫再跑红」** → **已开** [#92](https://github.com/pkulijing/claude-code-global/issues/92)，落点 `playbooks/shell.md` 沙盘测试一节。本轮亲历：守卫还没加就跑红态测试，`source install.sh` 执行了完整安装主流程（`$0` 在 source 语境下是调用方，`REPO_DIR` 被算成 `docs/51-.../`），把两端 `global-repo` 软链改指歪了，且**全程不报错**。教训是「红 → 绿」的正序有个未被写下的前置条件——**跑红本身没有副作用**；不成立时要让位于「先加隔离、再跑红」。
3. **「降级判据必须是能力缺失而非策略推断」** → **已开** [#91](https://github.com/pkulijing/claude-code-global/issues/91)。

另有一条**已在本轮就地修复**、不必沉淀：`install.sh` 的 source 守卫若被意外 export 会静默 no-op 伪装成功（review 报的 70 分观察，未过阻断线但与本轮教训同源，已加 source 语境判断）。
