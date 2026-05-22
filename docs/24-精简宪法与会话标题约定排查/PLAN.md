# PLAN

仅改 `GLOBAL_AGENTS.md` 一个文件（纯文档/规范精简，无代码、无测试适用项）。三处改动：

1. 删除失效的「会话标题约定」整节
2. 精简「项目本地推荐配置」节
3. 精简「Backlog 与开发项管理」节

Python 开发规则、git 规则、环境变量管理、核心开发模式（除会话标题约定外）等均**不动**。

---

## 改动 1：删除「### 会话标题约定（Coding Agent 自身行为约束）」整节（现 59–65 行）

排查已实锤该约定机制上无法落地（标题由独立 `ai-title` 摘要器基于全程会话生成、英文、不读首条回复），整节删除。轮次定位本就由 `docs/N-*` 目录名承担，无需此约定。

> 注：删除后，"核心开发模式"下保留「需求生命周期 / 测试先行 / 文档记录规范」三个子节。

---

## 改动 2：精简「## 项目本地推荐配置」（现 90–110 行，21 行 → 约 9 行）

把每个模板文件的逐项内容（`.prettierrc` / `.vscode` / `.pre-commit-config.yaml` / CI / ruff 段……）整段抄写删掉——这些细节属于模板本体与 skill 文档。保留原则 + 指向。

**精简后全文：**

```markdown
## 项目本地推荐配置（由 stack 模板统一管理）

每个项目应配置一份与 PostToolUse 自动 fix hook（`fix-after-edit.sh`）对齐的本地工具链（formatOnSave、commit 前 lint 闸门、CI 兜底等），避免「Agent 编辑 → 保存重排 → 大 diff」的反复，并在 commit 前拦住 lint 问题。

这套配置不由各项目手动维护，全部通过 stack 模板统一管理：

- 新项目 → `/bootstrap` 选 stack 自动落地
- 老项目首次接入 / 拉取模板更新 → `/sync-project-config`

各 stack 模板的具体文件清单与内容见 `~/.claude/templates/<stack>/`，schema 与设计见 `docs/11-跨项目共享模板与sync-skill/`。
```

---

## 改动 3：精简「## Backlog 与开发项管理」（现 112–148 行，37 行 → 约 12 行）

保留全部**原则**（issue 为真源、三轴 label、三件套分工、Closes #N 双向链接、已完成不追踪），删掉 issue template 双轨路径、helper 字段归一 schema、各子节的逐条展开——这些在三件套 skill 与对应 docs 里。

**精简后全文：**

```markdown
## Backlog 与开发项管理（Issue 驱动，GitHub / GitLab 双轨）

开发项以 **issue 为真源**：详情、讨论、跨轮上下文都沉淀在 issue 里；`docs/BACKLOG.md` 退化为**未关闭 issue 的扁平索引**。平台由 `git remote get-url origin` 自动判定，三件套 skill 统一走 `~/.claude/scripts/platform_issue.py` helper，不直接调 `gh` / `glab`。

- **三轴 label**：每条 issue 必打 `type:*`（全集统一）/ `area:*`（项目特异）/ `priority:*`（P0/P1/P2），由 `_common` 模板的 `.github/labels.yml` 维护。
- **三件套 skill**：`/backlog` 建 issue + 写 BACKLOG 索引、`/start <issue#>` 拉详情开轮、`/finish` 收尾并在 commit 写 `Closes #N`。
- **Closes #N**：commit/PR 描述写 `Closes #N`，合并到 default branch 自动关 issue（GitHub / GitLab 原生支持），issue 永久保留、与 commit/MR 双向可查——这是跨轮上下文可追溯的关键保证。
- **已完成项**不在 BACKLOG.md 追踪（看平台 closed issues）；BACKLOG.md 末尾「## 已完成 / 不再追踪」段只记**刻意决定不做**的项 + 原因。

issue template 双轨、helper 字段归一 schema 等实现细节见三件套 skill 与 `docs/12-backlog改为issue驱动/`、`docs/14-模板支持GitLab双轨/`。
```

---

## 验证

- 改后通读 `GLOBAL_AGENTS.md`，确认无悬空引用、章节层级完整。
- 无需 `install.sh`（该文件是软链，改内容即时生效）。

## 收尾

`/finish` 走标准收尾（本轮无 issue，commit message 不含 `Closes #N`）。
