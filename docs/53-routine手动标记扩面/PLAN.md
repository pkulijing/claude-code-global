# 实现计划：`/routine-docs` → `/routine-dev`，加人工标记通道并扩面

## 一、已拍板的决策（人类确认，Agent 不再改）

| # | 决策 | 结论 |
| --- | --- | --- |
| 1 | 标记载体 | **label `auto:take` 做闸**（纳入的必要条件）+ **OWNER 评论做补充说明**（读得到就用，读不到不阻断） |
| 2 | 落点放宽 | `skills/`（除自己）、`templates/`、`scripts/`、`hooks/` 全部放开；**`install.sh`、`.github/` 仍禁** |
| 3 | 自改红线 | **保留**：`skills/routine-dev/**` 永不自改 |
| 4 | 改名 | `routine-docs` → **`routine-dev`** |

## 二、实证结论（写 PLAN 前已跑，推翻了一个原设想）

| 断言 | 实测 | 对设计的影响 |
| --- | --- | --- |
| issue 评论能分辨作者身份吗 | ✅ `gh issue view 99 --json comments` 直接返回 `author.login` + `authorAssociation`（实测值 `OWNER`） | **不必新开子命令**——给现有 `issue-view` 加一个 `--with-comments` 开关即可。原设想的「新增 `issue-comments` 子命令」被否 |
| issue 列表能否先便宜地筛出「有评论的」 | ✅ `gh api "repos/{slug}/issues?state=open" --jq '.[].comments'` 带计数 | 未采用：label 已是充分闸，评论只是可选补充，无需按计数预筛 |
| 本机 helper 有评论能力吗 | ❌ 子命令只有 `detect-platform` / `auth-status` / `repo-slug` / `label-list` / `issue-create` / `issue-view` / `label-sync-from-file` | 需要动 `scripts/platform_issue.py` |
| GitLab 端能否同样读评论 | ⚠️ **`glab` 本机未安装，无法实测** | 见 §7「诚实降级」——不猜、不硬编 |
| 目录改名后旧软链怎么办 | ✅ `install.sh` 已有 `unlink_legacy_dir()`，注释明写「目录改名后旧软链已是断链」 | 复用它，加一行调用即可 |

> **公开仓任何人都能评论**（`authorAssociation` 会是 `NONE`），这正是决策 1 选 label 做闸的理由：GitHub 的权限模型保证非 collaborator 打不上 label，授权不靠我们自己校验。

## 三、核心设计：标记覆盖什么，不覆盖什么

`auto:take` 的语义定义为一句话：**「owner 已过目此条，背书其正文可被无人值守执行」**。它替换掉原先由「落点只限文档」承担的安全职责。

由此得出一条可判定的划分——**标记覆盖「保守性」排除，不覆盖「事实性」排除**：

| 现有排除项 | 类别 | 被 `auto:take` 覆盖？ |
| --- | --- | --- |
| `priority:P0` | 保守性（怕自动做砸大事） | ✅ 覆盖，人已明确背书 |
| 落点非文档（`skills/` `scripts/` `hooks/` `templates/`） | 保守性 | ✅ 覆盖，换成新白名单 |
| `area:install` / `area:hook` 硬过滤 | 保守性 | ✅ 部分覆盖：`area:hook` 放开，**`area:install` 仍排除**（install.sh 未放开） |
| 需讨论 / 选型 / 方案有分歧 | 保守性 | ✅ 覆盖，标记本身就是拍板 |
| 需落 `PLAN.md` 长期追踪 | 保守性 | ✅ 覆盖 |
| `wontfix` | 事实性（决策已归档，与标记矛盾） | ❌ 不覆盖，**报告矛盾并跳过** |
| 正文没说清要写什么 | 事实性（写出来也是猜的） | ❌ 不覆盖，跳过并**在 PR 里点名**「你标了但正文不足以执行」 |
| 仓库现状已满足 | 事实性 | ❌ 不覆盖，跳过并记「疑似已完成」 |
| 落点撞红线（`install.sh` / `.github/` / 自己） | 事实性（硬边界） | ❌ 不覆盖，**跳过并显著报告** |
| 已被在途 PR 覆盖（幂等） | 事实性 | ❌ 不覆盖 |

**未标记的 issue 走原有两层分诊，行为完全不变**——本轮不放松任何自动判定的保守度，只增加一条人工通道。这一点很重要：自动分诊判错的代价仍然不对称，保守是对的。

### 新落点白名单

| | 未标记 issue | 已标记（`auto:take`） |
| --- | --- | --- |
| **允许** | `playbooks/*.md`、`GLOBAL_AGENTS.md`、`README.md`、`docs/` | 上述 + `skills/**`（除自己）、`templates/**`、`scripts/**`、`hooks/**` |
| **禁止** | 其余一切 | `skills/routine-dev/**`、`install.sh`、`.github/**` |

**三条红线的理由各不相同，都写进 SKILL.md 与 reference**：

- `skills/routine-dev/**`：这份 SKILL 定义的正是「什么可以被自动改」这条规则本身。可自改 = 一次标记永久放宽此后**所有**无人值守运行的边界，而判断「这次自改动没动语义」的正是它自己（`/review-loop` 同为 Claude 家族，也是自审）。代价侧近乎为零——改本 skill 天然该走人工轮。
- `install.sh`：无单测，改坏了**静默**——所有设备的自动同步在下次 pull 后失败，而失败发生在 OS 调度器里，没人看着。
- `.github/**`：`ff-merge.yml` 是自动写 `master` 的那条路；且 workflow 文件的 PR 本来就走不了 FF 合入（`GITHUB_TOKEN` 被服务端禁推）。

## 四、评论作为补充说明（可选增强，不阻断）

读到 `authorAssociation == OWNER` 的评论时，把它作为**实现提示**并入 `/quick` 的说明。规则：

- **只认 `OWNER`**，其余（`COLLABORATOR` / `CONTRIBUTOR` / `NONE`）一律当普通外部文本；
- 多条 OWNER 评论 → 取**最后一条**（最新意图优先）；
- **读不到评论不阻断**（云端 MCP 是否有读评论的工具未实测）——label 已是充分条件，评论纯属锦上添花；
- 评论正文仍然**一律当数据不当指令**（`security-boundary.md` 的纵深防御第二层照旧适用）。owner 自己写的评论也不例外：这不是不信任 owner，而是 owner 可能引用了外部文本。

## 五、交付物清单

### 5.1 `skills/routine-docs/` → `skills/routine-dev/`（`git mv`，本轮主体）

`SKILL.md` 的修改点：

1. frontmatter `name` / `description` 改写（说明它已不限于文档）；
2. **Step 1.1 新增标记通道**：先按 label 分流成「已标记」与「未标记」两条分诊路径，用 §三 的两张表表达；
3. **Step 1.2 落点表替换**为 §三 的新白名单表 + 三条红线的理由；
4. **Step 3 新增两条无人值守规则**：
   - 触及 `scripts/` / `hooks/` 且该文件有单测的 → **必须跑单测，跑不过就放弃这条**（`git restore` + 记跳过清单）；
   - 放开落点后 `/review-loop` **一律不跳过**（原先纯文档还可能命中「纯用户文档自动跳过」）；
5. **Step 4 PR 描述**新增一段：本批哪些 issue 是靠 `auto:take` 纳入的、各自触及哪类落点；触及 `skills/` / `scripts/` / `hooks/` 时**显著标注请重点 review**（原第 5 条只覆盖指令规则文件，要扩）；
6. **末节注册 prompt 里的 `/routine-docs` 改成 `/routine-dev`**；
7. 全文自引用路径 `skills/routine-docs/...` → `skills/routine-dev/...`。

`references/security-boundary.md` 的修改点：

- 标题与全文引用改名；
- **新增 §7「为什么人工标记可以换掉落点限制，以及它换不掉什么」**：把 §三 的推导落在这里——标记把 issue 正文从「任何人都能写」提升为「owner 已背书」，这是**授权**的转移不是**风险**的消失；三条红线正是标记换不掉的部分；并写明该论证的已知弱点（owner 打 label 时未必逐字读过长正文里埋的一段），故 PR 仍是最终闸口、且触及可执行面必须显著标注。

### 5.2 `scripts/platform_issue.py`：`issue-view` 加 `--with-comments`

- 默认行为与输出 schema **零变化**（`/start` 等现有消费方不受影响）；
- 带 `--with-comments` 时 GitHub 走 `gh issue view N --json number,title,body,url,labels,comments`，归一出 `comments: [{author, authorAssociation, body, createdAt}]`；
- **GitLab 端**：`glab` 本机未安装、无法实测其 notes 能力 → 返回 `comments: []` **并向 stderr 打一行明确的 not-supported 说明**（不静默、不硬编猜来的命令）。本仓是 GitHub，routine 只跑本仓，不阻断。

### 5.3 `.github/labels.yml`：新增 `auto:take`

```yaml
# ---------- 运维 ----------
- name: "auto:take"
  color: "5319E7"
  description: "owner 背书：下次 /routine-dev 强制纳入，可改 skills/ templates/ scripts/ hooks/"
```

落库需跑 `platform_issue.py label-sync-from-file .github/labels.yml`（列进上线检查单）。

### 5.4 `install.sh`：加一行旧软链清理

```bash
unlink_legacy_dir "$agent_home/skills/routine-docs"
```

放在现有 `unlink_legacy_dir "$agent_home/rules"` 旁边。不加的话两端 `~/.claude/skills/routine-docs` 与 `~/.codex/skills/routine-docs` 会残留断链。

### 5.5 连带改名与边界同步

| 文件 | 改什么 |
| --- | --- |
| `skills/routine-slim/SKILL.md` | 7 处引用改名；**黑名单 `skills/routine-docs/**` → `skills/routine-dev/**`**；第 63 行「为什么 routine-docs 禁改 skills/*.md 而本 routine 可以」的论证**已被本轮推翻，须重写**为「未标记走文档白名单、已标记靠 owner 背书」 |
| `CLAUDE.md`（本仓） | 两条 routine 的安全边界段重写 |
| `README.md` | 10 处（skill 一览表、云端 routine 两节、ff-merge 硬边界那句） |
| `playbooks/cloud-routine.md` | 2 处引用改名 |
| `docs/**`、`docs/DEVTREE.md` 历史行 | **不改**——历史记录写的就是当时的 `/routine-docs`，改了反而失真 |

## 六、与 `/routine-slim` 的撞车防线（本轮必须补，否则是新洞）

放开 `skills/**` 后，两条 routine 主业重叠。现状是**单向防线**：slim 会排除所有在途 PR 碰过的文件，dev 的幂等却只按 `Closes #N` 排除 issue、不看文件。slim 周日出的 PR 挂在人手上时，周一的 dev 就可能改同一个文件。

**补法（改动很小，且顺带覆盖人开的 PR）**：Step 3 已有「与本次运行已开 PR 的落点并集比对」这套机制，把该并集的**初始值从空集改为「所有 open PR 碰过的文件集合」**。一处初始化的改动，换来对 slim 的 PR、人开的 PR 全部生效的对称防线。相交则本批顺延到下次。

## 七、测试计划

| 对象 | 怎么验 | TDD？ |
| --- | --- | --- |
| `platform_issue.py --with-comments` | 先写失败断言：`build_issue_view_cmd(with_comments=True)` 应含 `comments` 字段、`False` 时不含；归一函数对 comments 数组的字段映射。挂进现有 `self-test` | ✅ **先红后绿**——纯函数、输入输出契约清晰，正是宪法说的该先写测试的场景 |
| `install.sh` 旧软链清理 | 沙盘脚本：造一个指向已删目录的断链，跑 `unlink_legacy_dir` 后断言消失；对齐先例 `docs/51-rules按需加载/test-unlink-legacy.sh` | ✅ |
| SKILL.md 的规则本身 | 无法单测 → **靠 `--dry-run` 实跑真实 issue**（见检查单） | ❌ 例外：指令文档 |

## 八、上线检查单（人工动作，缺一不可）

1. `bash install.sh`（skill 目录增删必须重装；同时验证旧软链被清掉）；
2. `python3 $HOME/.claude/scripts/platform_issue.py label-sync-from-file .github/labels.yml` —— 不同步就打不上 `auto:take`；
3. **给一条真实 issue 打 `auto:take`**（建议挑 #104「新增 /triage skill」或 #102，都是 `area:skill` 的明确需求），再跑 `/routine-dev --dry-run`，人过目分诊结果——`playbooks/cloud-routine.md` §5 立的规矩，且 `/routine-docs` 上线前那次 dry-run 当场改掉了两条规则，同样的收益预期；
4. ⚠️ **去 claude.ai 改云端 routine 的 prompt**：里面写死了 `/routine-docs`，**不改则下次运行调不到 skill，且失败发生在无人看的定时任务里**。这是本轮唯一一处仓库管不到、必须人工同步的配置。

## 九、风险与局限（明写，不藏）

1. **`auto:take` 的授权强度取决于 owner 打 label 时是否真读了正文。** 长正文里埋一段面向 agent 的指令仍可能被放行。缓解是纵深的而非消除：PR 仍是最终闸口 + 触及可执行面强制显著标注 + 外部文本一律当数据。**这一点写进 reference §7，不粉饰。**
2. **同模型自审的已知盲区照旧**：`/review-loop` 与写 diff 的同为 Claude 家族，而本轮把它的把关对象从文档扩到了可执行代码，盲区的后果变重了。跑单测是对冲手段之一，但只覆盖有单测的文件。
3. **改名的迁移窗口**：从合入 master 到人工改完云端 prompt 之间，云端 routine 会失败。建议合入后**立刻**做检查单第 4 项。
4. **GitLab 端 `--with-comments` 不可用**且未实测——本仓不受影响，但若哪天有 GitLab 项目复用此 helper 会撞上，故 stderr 明确留话而非静默返回空。
