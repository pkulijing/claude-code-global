# SUMMARY：backlog 工作流改造为 GitHub Issue 驱动

## 开发项背景

`claude-code-global` 中的 backlog 原本由 `/backlog` skill 写 5 字段结构化条目到 `docs/BACKLOG.md`，BACKLOG 是真源。在 `daobidao`（即 `whisper-input`）项目 30+ 轮实测后浮现四个具体问题：

1. 跨轮上下文沉淀在文件、和 git/PR 脱节，未来读 git log 看不到决策上下文
2. 完成后只是"删一行"，"为什么没做这条 / 为什么改了这个方案"的判断过程消失
3. BACKLOG.md 是裸文本，没法 label / query / 跨项目对比
4. 新想法在 SUMMARY「后续 TODO」段腐烂，没有强制流入 BACKLOG 的机制

daobidao 项目已实战另一套模型：GitHub Issues 是真源（permanent + `Closes #N`），BACKLOG.md 退化为索引。本轮把这套改造应用到 `claude-code-global`，让所有未来通过 `/bootstrap` 起的项目都自然采用此工作流。

## 实现方案

### 关键设计

经 Q1~Q5 拍板（详见 [PROMPT.md](PROMPT.md)）：

1. **Q1 area label 管理**：项目侧 `.github/labels.yml`（YAML list），bootstrap/sync 调 `gh label create --force` 同步。templates 提供 starter（type/priority 全集 + area placeholder）
2. **Q2 无 GitHub remote 优雅降级**：写 issue templates 文件不依赖 remote；`gh label create` 跳过并在收尾提示
3. **Q3 `/backlog` 直接调 gh CLI**：AI 与用户对话写 body → 选三轴 label → `gh issue create` → 拿 URL → 加一行到 BACKLOG.md
4. **Q4 SUMMARY「后续 TODO」保持 free-form**：不强制每条开 issue。SUMMARY 是回顾文档不是承诺清单
5. **Q5「已完成 / 不再追踪」段**：骨架默认含此段，`/finish` 在 SUMMARY 写完后软提示用户补录刻意不做的项

执行中浮现的额外设计变更（计划外，由用户中途指出）：

6. **`_common` 伪 stack 提前实现**：原计划把 issue templates / labels.yml / .prettierrc 放到 `templates/python-uv/`（同时承认 stack-无关、备注"未来 _common 再迁移"）。用户指出这违反 stack 语义，立即引入 `_common` 伪 stack：
   - `templates/_common/__root__/` 承载完全 stack-无关的根级资源
   - bootstrap / sync 自动应用 `_common`，不进入 stack 选项（下划线开头被过滤）
   - SCHEMA.md 增节说明 `_common` 是隐式约定，不进 marker `stacks` 列表

### 开发内容概括

按调整后的 PLAN 实施：

- **`templates/_common/__root__/`**（新增）：3 个 issue template + `labels.yml` + `.prettierrc`（从 python-uv 迁移过来）
- **`templates/python-uv/__root__/`**（保留 Python 专属）：`.pre-commit-config.yaml` / `.gitignore` / `.github/workflows/lint.yml`
- **`skills/backlog/SKILL.md`**（重写）：从"写 5 字段条目到文件"改为"走 issue template + 三轴 label → `gh issue create` → BACKLOG.md 索引"
- **`skills/start/SKILL.md`**（加 issue 驱动分支）：参数若是 `#N` 或完整 GitHub issue URL，`gh issue view` 拉详情贴进 PROMPT.md 顶部
- **`skills/finish/SKILL.md`**（重构）：识别 PROMPT.md 顶部 issue 引用 → 让 `/commit` 在 message body 写 `Closes #N` → BACKLOG.md 删对应行；新增 step 1.5 软提示「不再追踪」段补录
- **`skills/bootstrap/SKILL.md`**（增 `_common` 自动应用 + `gh label create`）：Step 3 显式说明 `_common` 与 `<stack>` 双源、Step 3.3.5 同步 GitHub labels（无 remote 时降级）、Step 5 收尾反馈对齐
- **`skills/sync-project-config/SKILL.md`**（扫两个源）：2.3 git diff 同时扫 `templates/<stack>/` + `templates/_common/`、4.3 adopt 模式同时套用、6 执行新增 "accept (gh label sync)" 动作
- **`docs/11-跨项目共享模板与sync-skill/SCHEMA.md`**（新增段）：「关于 `_common` 伪 stack」明确隐式约定不进 marker
- **`GLOBAL_CLAUDE.md`**（新增「Backlog 与开发项管理」节）：三轴 label / issue templates / 三件套 skill 工作流 / Closes #N 双向链接 / 已完成 不再追踪

### 额外产物

- **本仓库 dogfood**：
  - `.github/ISSUE_TEMPLATE/` 三个 template
  - `.github/labels.yml` 含 14 条 label（type×6 + priority×3 + area×5：install/skill/hook/template/doc）
  - `docs/BACKLOG.md` 用新格式重写（之前为空，刚好切）
  - 实测 `gh label create --force` 把 14 条 label 全推到 GitHub `pkulijing/claude-code-global` 仓库 ✓
- **机械验证**：YAML 语法、install.sh 幂等、`~/.claude/templates/` 软链含 `_common` 与 `python-uv` 都可读

## 局限性

1. **多 stack monorepo 仍仅 schema-ready，逻辑未实现**：与 round 11 一样，sync 启动时显式断言单 stack；多 stack 跨 stack root 文件 merge（含 `_common` 跨多 stack 的语义）留至后续 round
2. **`/backlog` `/start <issue#>` `/finish` 三件套端到端尚未真实跑过**：本轮做了 `gh label create` 实测，但全流程（创 issue → 开新轮 → 关联 commit → 关 issue → 删 BACKLOG 行）还没在真实 issue 上跑一次。下一轮真的开 issue 时会自然检验
3. **AI 解析 YAML 的鲁棒性**：bootstrap / sync 都让 AI 直接读 `.github/labels.yml`，复杂 YAML（含锚点、多文档等）可能误读；当前 labels.yml 结构简单未触发问题
4. **`Closes #N` 在 feature branch 直 commit 不开 PR 的语义**：GitHub 自动关 issue 仅在 default branch 触发；本仓库习惯直 push master 没问题，但 PR-based workflow 的项目要等 PR merge
5. **`area:placeholder` 在新项目首跑后会真的被推到 GitHub**：bootstrap 先 `gh label create` 再让用户改 labels.yml，过程中 placeholder 会留在 GitHub。后续 sync 用户改完 labels.yml 后能正确清理（gh 不支持自动删除 label，需要手动 `gh label delete area:placeholder` 或留着）
6. **issue templates 中 frontmatter 的 `labels:` 字段与三轴 label 不全对齐**：模板只设 `type:*`（自动），`area` 与 `priority` 仍要 issue 创建时由 skill 显式 `--label` 加。模板的 blockquote 占位提示了三轴，但表单里没强制
7. **本轮 PLAN.md 与最终实现有偏离**：PLAN 原写 `templates/python-uv/__root__/.github/`，执行中按用户反馈迁到 `_common`。docs/12 中 PLAN 与 SUMMARY 都保留这一偏离的来龙去脉，未来读 plan 仍能追溯

## 后续 TODO

按重要性 / 时机：

1. **多 stack 支持**（含 `_common` + 多 stack 共存语义）：bootstrap 反复 add stack、sync 处理 `stacks` 多项 + AI 跨 stack root 文件 merge —— 与 round 11 后续 TODO 合并到一轮
2. **真实跑一遍 backlog → start → finish 三件套**：等下次有真需求时自然检验；如发现端到端 bug，开 issue 修复
3. **`gh label delete` 收尾自动化**：bootstrap 推完 placeholder 后，sync 时若 labels.yml 已改了 area，提议把 GitHub 上多余的 area 删掉
4. **issue template 的 `labels:` frontmatter 自动加 area / priority**：当前只有 `type:*` 是 frontmatter 自动；可探索把"在创建时让用户选 area/priority"放到 issue body checklist + `gh issue edit --add-label`
5. **跨项目 backlog 聚合视图**：一个命令看所有项目所有 P0
6. **`area` label 多选 vs 单选**：当前 skill 默认单选；某些项目可能要多 area（如同时影响 stt 与 ui）—— 视用法决定
7. **历史项目的 BACKLOG 迁移工具**：本仓库已切，daobidao 已迁，其他项目未来要迁时再考虑
