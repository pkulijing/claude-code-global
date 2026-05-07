# SUMMARY — round 14：模板支持 GitLab 双轨

对应 issue：[#2 让 \_common / stack 模板支持 GitLab 项目](https://github.com/pkulijing/claude-code-global/issues/2)

## 1. 开发项背景

`templates/_common/` 与 `templates/python-uv/` 内含 GitHub 专属文件（`.github/ISSUE_TEMPLATE/`、`.github/labels.yml`、`.github/workflows/lint.yml`），但完全没有 GitLab 等价物。当目标项目跑在 GitLab 上时：

- `.github/...` 文件被复制过去等同于死文件（GitLab 不识别）
- 没有 `.gitlab/issue_templates/`、没有 `.gitlab-ci.yml`，整套 sync-skill 流程在 GitLab 项目上走不通

属用户能感知的明显问题，priority P1。

## 2. 实现方案

### 2.1 关键设计决策（与初版方案对比）

需求阶段一开始倾向「按 platform freeze + 模板侧拆 `__shared__/__github__/__gitlab__` 三层 + marker 加 `platform` 字段」。讨论后**改用更简单的「项目侧双兼容」**：

> 模板里 GitHub + GitLab 两套文件**全部**复制到目标项目；skill 中真正调命令行的步骤（如 `gh label create`）按当前 `git remote` 判定走哪一支。

成立基础是 **互不干扰**：

- GitHub Actions 只读 `.github/workflows/`、不看 `.gitlab-ci.yml`；反之亦然
- GitHub Issues 只读 `.github/ISSUE_TEMPLATE/`、GitLab Issues 只读 `.gitlab/issue_templates/`
- 对端文件在另一平台等同于死文件，零意外行为

收益对比初版方案：

- 模板目录 schema 不动（无需引入 `__shared__/__github__/__gitlab__` 嵌套层）
- `.cc-template.yml` 不动（无需 `platform` 字段、无需老 marker 兼容）
- 不需要 D+A 去重逻辑（避免一类高风险代码）
- bootstrap 零交互（无需检测 / 询问 platform）
- 双 remote / 镜像场景天然支持

唯一代价：项目根永久多 4–5 个对端文件（GitHub 项目里有 `.gitlab/...` + `.gitlab-ci.yml`；反之 GitLab 项目里有 `.github/...` 多个）。但都不会被对端读取，纯粹是仓库内的"死文件"。

工作量从初版的 1.5–2 轮压到 0.5–1 轮。

### 2.2 不做 symlink 共享 issue template 的原因

人 review 阶段问到「能不能用 symlink 让 `.github/...` 和 `.gitlab/...` 指向同一份内容」。结论是不能：

- GitHub 用 frontmatter `labels: ["type:feat"]` 自动打 type label
- GitLab 用 body 首行 quick action `/label ~"type:feat"` 自动打 type label
- 两份内容必须**不同**才能保留各平台的「自动打 label」便利
- 共用一份「中性」内容会让两边都丢失自动 label，代价大于收益
- CI 文件（GitHub Actions YAML vs GitLab CI YAML）结构完全不同，本来也不可能 symlink
- symlink 在 Windows 协作者那边支持差，跨平台风险

最终选择：两份独立内容、复制成本可接受（issue templates 3 份 × 平均 ~25 行）。

### 2.3 GitLab quick action 占位约定

GitLab issue template 首行放 `/label ~"type:..."`、紧跟一行 HTML 注释解释「请勿删除、勿在前面插任何内容（含空行）」。模板维护者改写时只要保持 quick action 单独占第一行就能保留自动 label 行为。

### 2.4 GitLab CI lint job

`templates/python-uv/__root__/.gitlab-ci.yml`：等价于 GitHub 版的 ruff check + ruff format --check，用 `python:3.12-slim` 镜像，`pip install uv` + `uv sync --frozen` 装依赖，rules 限定 MR 与默认分支 push 触发。性能优化（uv venv cache、镜像源加速）留后续按需迭代。

### 2.5 skill `gh label create` 的双轨判定

`/bootstrap` 的 Step 3.3.5 与 `/sync-project-config` 的 6 节执行步骤都按相同三分支判定 `git remote get-url origin`：

- 含 `github.com` → 跑 `gh label create --force ...`
- 含 `gitlab` 字样 → 跳过，提示「留待后续 `gh→glab` 适配 issue 落地」
- 其他（无 origin / 自托管 GitLab URL 不含 `gitlab` 字样）→ 跳过 + 提示

**本轮不调 `glab label create`**，整体留给后续 issue。

## 3. 开发内容概括

### 新增模板文件

- [`templates/_common/__root__/.gitlab/issue_templates/feat.md`](../../templates/_common/__root__/.gitlab/issue_templates/feat.md)
- [`templates/_common/__root__/.gitlab/issue_templates/bug.md`](../../templates/_common/__root__/.gitlab/issue_templates/bug.md)
- [`templates/_common/__root__/.gitlab/issue_templates/spike.md`](../../templates/_common/__root__/.gitlab/issue_templates/spike.md)
- [`templates/python-uv/__root__/.gitlab-ci.yml`](../../templates/python-uv/__root__/.gitlab-ci.yml)

3 个 issue templates 按 §2.3 约定首行放 quick action，body 沿用 GitHub 版结构（`> type/area/priority` 提示块 + 动机/希望达到/候选方向/风险/scope 五段）。spike 沿用 `type:refactor`（与 GitHub 版一致）。

### 改动 skill 文件

- [`skills/sync-project-config/SKILL.md`](../../skills/sync-project-config/SKILL.md)：
  - 4.3 节「TODO 生成」处把「依赖 `gh auth status` + GitHub remote」收紧为按 origin URL 三分支判定
  - 6 节「执行 `accept (gh label sync)`」改为按 origin URL 走三分支动作（GitHub 跑 / GitLab 跳 / 其他跳）
- [`skills/bootstrap/SKILL.md`](../../skills/bootstrap/SKILL.md)：
  - Step 3 头部说明加「GitHub 与 GitLab 双轨同时落」+ 互不干扰简述
  - Step 3.3.5 标题与正文改为「同步 labels（按 origin 平台判定）」+ 三分支
  - Step 5 收尾建议第 5/6 条对应改写、把「无 GitHub remote」展开为「GitHub auth 失败 / 无 origin / GitLab origin」三种情况

### 改动文档

- [`docs/11-跨项目共享模板与sync-skill/SCHEMA.md`](../11-跨项目共享模板与sync-skill/SCHEMA.md) 末尾加「## 关于平台双兼容（round 14 引入）」一节：表格列出 GitHub / GitLab 两套文件 + 互不干扰前提 + marker schema 不变 + skill 端三分支判定 + 后续待落地

### 额外产物

- 本轮的 PROMPT.md 经历了一次设计方向重写（初版方案 → 双兼容方案），重写过程也记在 PROMPT.md 的「设计方向（与作者讨论后确定：项目侧双兼容）」段落，作为以后 review 时的参考案例「轻 schema、重运行时」对「重 schema、轻运行时」的取舍

## 4. 验证

### 4.1 自身仓库 dogfood（手工 git diff 验证）

跑：

```bash
git diff --name-status ecbb9d4b4e03aa93bc716384cc3141464ee4af04..HEAD -- templates/
git status --short templates/
```

得到：

```
?? templates/_common/__root__/.gitlab/
?? templates/python-uv/__root__/.gitlab-ci.yml
```

**符合 PLAN §4.1 预期**：4 项纯新增（3 个 issue templates + 1 个 `.gitlab-ci.yml`），无 D（删除）/ M（修改）类条目。

⚠️ **未跑完整的 `/sync-project-config`**：本仓库 `.cc-template.yml` 中 `stacks: []`（global-repo 自身的特殊状态，从 round 11 起就这样），会触发 sync skill 的「单 stack 断言」失败。这不是本轮引入的问题，本轮只能用手工 diff 替代 sync 的端到端验证。

### 4.2 实际 GitLab repo 验证（未做）

PLAN §4.2–4.4 期望在临时 GitLab repo 上验证 bootstrap、quick action 自动 label 等行为。本轮**未做**实地验证（无随手可用的 GitLab 测试 repo）。后续要么由用户在自己的 GitLab 项目上 dogfood、要么作为后续 issue 一起落。

## 5. 局限性

1. **skill 内 `gh issue *` / `gh issue create` / `gh issue view` 调用未做双轨适配**——`/backlog`、`/start <#>`、`/finish` 在 GitLab 项目上仍会失败或行为不正确。本轮只解决了 `gh label create` 这一处，是因为它是 sync/bootstrap 唯一会主动调命令行的点
2. **GitLab labels 同步未实现**——没有 `glab label create` 调用、没有 GitLab 平台 labels 配置约定（GitLab 不像 GitHub 有 `.github/labels.yml` 这种原生约定）
3. **项目根永久多对端文件**——这是双兼容设计的明示代价，不是 bug。如果用户介意，未来可以加 opt-out flag（如 marker 加 `platforms: [github]`）
4. **GitLab quick action 实地行为未验证**——只在文档里约定了首行规则，实际是否生效需 GitLab 项目验证
5. **本仓库 marker `stacks: []` 状态阻塞了完整 sync 端到端验证**——round 11 遗留状态，与本轮无关，但导致 dogfood 不彻底

## 6. 后续 TODO

按优先级：

1. **新 issue（`area:skill` `type:feat`）**：「skill 内 `gh` → `glab` 双轨适配」——含 `/backlog`、`/start`、`/finish`、`/sync-project-config` 中所有 `gh` 调用点的兜底；本轮已为这件事在模板侧准备就绪（`.gitlab/issue_templates/` 已就位）
2. **新 issue（`area:template` `type:feat`）**：GitLab labels 同步——决定要不要在 `_common` 里放一份 `.gitlab/labels.yml` 等价配置 + 在 sync/bootstrap 中调 `glab label create`；与 1 一起做最佳
3. **新 issue（`area:meta` `type:test`）**：实地 GitLab 项目验证清单（quick action 首行约定是否生效、`.gitlab-ci.yml` 首次跑通、issue templates 在 web UI 下拉中显示等）
4. **新 issue（`area:template` `type:refactor`，可选）**：本仓库 `.cc-template.yml` 当前 `stacks: []` 状态阻塞了 sync 端到端 dogfood——是否该让 global-repo 自身也声明 `stacks: [{stack: python-uv, path: .}]`（毕竟自己也用 ruff），让以后改模板时能跑 sync 自检
