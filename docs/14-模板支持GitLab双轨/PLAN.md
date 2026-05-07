# PLAN — round 14：模板支持 GitLab 双轨（项目侧双兼容方案）

## 1. 总体目标 & 非目标

**目标**：让 `~/.claude/templates/` 在生成项目本地配置时同时落 GitHub + GitLab 两套等价文件，互不干扰；skill 中真正调命令行的步骤（当前唯一一处是 `gh label create`）按当前 `git remote` 判定走哪一支。

**与初版方案（platform freeze + 三层 `__shared__/__github__/__gitlab__`）的差异**：放弃模板侧 schema 拆分、放弃 marker `platform` 字段、放弃 D+A 去重，纯靠 GitHub/GitLab 互不读对方目录的天然性质实现「双兼容」。设计大幅简化，本轮工作量从 1.5–2 轮降到 0.5–1 轮。

**非目标（明确不做，留后续 issue）**：

- skill 内 `gh issue *` / `gh label *` 调用做 `gh` ↔ `glab` 双轨适配（`/backlog`、`/start`、`/finish`、sync 等）
- GitLab labels 同步（`glab label create` 调用 + 配置文件约定）
- 模板侧 schema 改造（保持现有 `__root__` / `__subpath__` 两层不变）
- 多 stack monorepo

## 2. 关键设计决策

### 2.1 互不干扰前提的成立性

| 平台           | 读取                           | 不读取                         |
| -------------- | ------------------------------ | ------------------------------ |
| GitHub Actions | `.github/workflows/*.yml`      | `.gitlab-ci.yml`               |
| GitLab CI      | `.gitlab-ci.yml`               | `.github/workflows/*.yml`      |
| GitHub Issues  | `.github/ISSUE_TEMPLATE/*.md`  | `.gitlab/issue_templates/*.md` |
| GitLab Issues  | `.gitlab/issue_templates/*.md` | `.github/ISSUE_TEMPLATE/*.md`  |

→ 两套并存时**对端文件就是死文件**，零意外行为。这是本方案成立的基础。

### 2.2 不做 symlink 共享

issue template 两个平台的「自动打 label」机制不同：

- GitHub 用 frontmatter `labels: ["type:feat"]`
- GitLab 用 body 首行 quick action `/label ~"type:feat"`

如果共用一份「中性」内容，两边都会丢失自动打 label 的便利。代价大于收益，**两份独立内容**。CI 文件结构差异更大（GitHub Actions 与 GitLab CI 是两套完全不同的 YAML schema），本来也不可能共用。

### 2.3 `gh label create` 的双轨判定

当前 `bootstrap` Step 3.3.5 与 `sync-project-config` 在 adopt 模式下都会调 `gh label create --force` 把 `.github/labels.yml` 推到 GitHub。本轮加一个判定：

```bash
origin_url=$(git remote get-url origin 2>/dev/null || echo "")
case "$origin_url" in
  *github.com*)
    # 跑 gh label create ...
    ;;
  *gitlab*)
    # 打印「检测到 GitLab remote，labels 同步留待后续 issue（glab label create 适配）」
    ;;
  *)
    # 无 origin / 自托管 GitLab 等：打印「无法判定平台，labels 同步跳过；如确为 GitHub 请手动跑 gh label create 或重设 origin」
    ;;
esac
```

**注意：本轮不调 `glab label create`**——把 GitLab labels 同步整体留给后续 `gh→glab` 适配 issue。

### 2.4 GitLab issue templates 内容设计

每个文件首行放 `/label ~"type:xxx"` quick action，注释提醒不要插空行；其余结构沿用 GitHub 版（`> type:` / `> 优先级判断:` / `**动机**` / `**希望达到**` / `**候选方向**` / `**风险**` / `**scope**`），保留体验一致性。

GitHub 版的 frontmatter `labels:` 对应到 GitLab 时全部转 quick action，例：

```markdown
<!-- 提交时此行 quick action 会自动打上 type:feat 标签；勿插空行勿删 -->

/label ~"type:feat"

> **type**: `feat` / **area**: `<请填本项目 area: 标签>` / **priority**: `<P0|P1|P2>`
> **优先级判断**：…

---

**动机**：…
**希望达到**：…
**候选方向**：…

- 方向 A：……
- 方向 B：……

**风险 / 注意点**：…

**scope**：…
```

### 2.5 GitLab CI lint 内容设计

等价于 GitHub 版的 ruff check + ruff format --check：

```yaml
# 与 .github/workflows/lint.yml 等价的 GitLab CI 版本：ruff check + ruff format --check
# bootstrap / sync-project-config 会同时落两份；GitHub 项目 / GitLab 项目各看各家，互不干扰
stages:
  - lint

ruff:
  stage: lint
  image: python:3.12-slim
  before_script:
    - pip install --quiet uv
    - uv sync --frozen
  script:
    - uv run ruff check .
    - uv run ruff format --check .
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
```

性能优化（uv venv cache、镜像源加速等）本轮不做，留后续按需迭代。

## 3. 实施步骤

### Step 1：新增 GitLab issue templates

文件：

- `templates/_common/__root__/.gitlab/issue_templates/feat.md`
- `templates/_common/__root__/.gitlab/issue_templates/bug.md`
- `templates/_common/__root__/.gitlab/issue_templates/spike.md`

内容按 §2.4 模板，三种 type 的 quick action 分别为 `~"type:feat"` / `~"type:bug"` / `~"type:feat"`（spike 沿用 GitHub 版的 `type:feat`，对照 `.github/ISSUE_TEMPLATE/spike.md`）。

⚠️ 实际写之前先 Read 一遍 `.github/ISSUE_TEMPLATE/{feat,bug,spike}.md` 确认 frontmatter `labels:` 实际值，逐一映射，避免写错。

### Step 2：新增 GitLab CI lint job

文件：`templates/python-uv/__root__/.gitlab-ci.yml`，内容按 §2.5。

### Step 3：sync-project-config skill 加 `gh label create` 双轨判定

改 `skills/sync-project-config/SKILL.md` 的「6. 执行」节中 `accept (gh label sync)` 这条：

- 在调用 `gh label create` 前先按 §2.3 的判定逻辑分支
- TODO 清单生成阶段（4.3 节末尾）也对应调整描述：当前是「**额外把 `gh label create` 作为单独一条 TODO**（依赖 `gh auth status` + GitHub remote；缺失则该条标 skipped 并提示）」——把「依赖 GitHub remote」收紧到「origin URL 含 `github.com`」并明确 GitLab 分支提示文案

### Step 4：bootstrap skill 同步加双轨判定

改 `skills/bootstrap/SKILL.md` 的 Step 3.3.5：当前文案「如果项目根出现了 `.github/labels.yml`（来自 `_common`），且 `git remote get-url origin` 指向 GitHub」——这条已经隐含了 GitHub 判定，但当前没有对 GitLab 分支的明确提示。补充：

- origin 含 `gitlab` → 打印「检测到 GitLab remote，labels 同步留待后续 issue（glab 适配）」
- 无 origin → 沿用现有「先 `gh repo create` 再跑 sync」提示，但加一句「若 remote 实际是 GitLab，labels 同步暂未实现」

Step 5（收尾反馈）的下一步建议清单也对应补一句 GitLab 项目的注记。

### Step 5：SCHEMA.md 文档更新

在 `docs/11-跨项目共享模板与sync-skill/SCHEMA.md` 末尾加一节「### 平台双兼容（round 14 引入）」：

- 说明模板侧的 `.github/...` 与 `.gitlab/...` 同时分发、互不干扰
- 说明 marker schema **不变**（不引入 `platform` 字段）
- 说明 skill 中 `gh label create` 按 origin URL 判定走哪一支；`glab label create` 留后续
- 列出后续待实现项指针

### Step 6：dogfood 自身仓库

`claude-code-global` 自己跑一次 `/sync-project-config`，预期：

- 看到「新增 4 个 GitLab 相关文件」的 TODO（3 个 issue templates + 1 个 `.gitlab-ci.yml`）
- 因本仓库 origin 是 GitHub，`gh label create` 走 GitHub 分支照常跑（如已是最新无变化）
- accept 全部新增 → 项目根多出 `.gitlab/issue_templates/...` 与 `.gitlab-ci.yml`
- 验证 marker 中 `template_commit` 被回写到当前 HEAD

### Step 7：SUMMARY.md 收尾

按四步开发模式总结：

- 实现方案：双兼容设计的成立基础（互不干扰）+ 各平台 issue template 自动 label 机制差异为何不能 symlink 共享
- 额外产物：GitLab CI lint job 草稿、issue templates 中文版的 GitLab 适配
- 局限性：（1）skill 内 `gh issue *` 双轨未做；（2）GitLab labels 同步未做；（3）项目根多 4 个死文件
- 后续 TODO：开 `area:skill` 新 issue 跟踪 `gh→glab` 全面适配（含 labels 同步）

## 4. 关键测试用例（人工 dogfood + 临时仓库 dry-run）

本仓库无 Python 模块测试基础设施，关键验证点：

### 4.1 现有 GitHub 项目下次 sync

输入：本 `claude-code-global` 仓库自己（已 adopt 自身模板，origin 是 GitHub）。

跑 `/sync-project-config`，期望：

- TODO 出现 4 项新增（3 个 GitLab issue templates + 1 个 `.gitlab-ci.yml`）
- 没有 D（删除）类条目
- `gh label create` 步骤照常跑（origin 含 `github.com`）
- accept 后项目根新增 `.gitlab/issue_templates/{feat,bug,spike}.md` 与 `.gitlab-ci.yml`

### 4.2 临时新建 GitLab 项目 bootstrap

输入：临时空目录、手动 `git init` 后 `git remote add origin git@gitlab.com:foo/bar.git`。

跑 `/bootstrap`，期望：

- 套用 `_common` + `python-uv` → 项目根同时出现 `.github/...` 与 `.gitlab/...` 两套
- `gh label create` 步骤跳过，打印「检测到 GitLab remote，labels 同步留待后续 issue」
- 不报错、不阻塞

### 4.3 无 origin 项目 bootstrap

输入：临时空目录、`git init` 后**不加** remote。

跑 `/bootstrap`，期望：

- 模板复制照常完成（双套）
- `gh label create` 跳过，打印「无 origin，labels 同步跳过；如确为 GitHub 请补 remote 后跑 sync」
- 不报错

### 4.4 GitLab issue template quick action 生效

人工验证（在临时 GitLab repo）：

- 把生成的 `.gitlab/issue_templates/feat.md` 提交 push 到 GitLab
- 在 web UI 创建 issue → 确认「Description」下拉里出现 `feat` 选项
- 选中后 body 自动填入模板内容
- 提交 issue → 确认 `type:feat` label 被自动打上（前提：GitLab 项目里 `type:feat` label 已存在；不存在时 quick action 静默 no-op，不会报错）

### 4.5 互不干扰验证

人工核对（不需跑 CI）：

- GitHub 项目里有 `.gitlab-ci.yml` → GitHub Actions 不会因此跑 GitLab CI（GitHub 根本不读这个文件）
- GitLab 项目里有 `.github/workflows/lint.yml` → GitLab CI 不会跑 GitHub Actions
- GitLab 项目里有 `.github/ISSUE_TEMPLATE/feat.md` → GitLab issue 创建界面不会显示这个模板（只看 `.gitlab/issue_templates/`）

## 5. 关键风险

1. **GitLab quick action 必须 body 首行**：写模板时如果不慎插空行或注释行在前，自动打 label 会失效。模板文件首行用 `<!-- ... -->` HTML 注释提醒、quick action 紧跟其后；首行 HTML 注释 GitLab 渲染时会被忽略，不影响 issue body 显示。**实际**：GitLab 的 quick action 解析对前置的 HTML 注释是否容忍需要验证；保险起见把注释挪到 quick action 之后，让 quick action 真正占据 body 首行。
2. **`.github/labels.yml` 在 GitLab 项目里就是死文件**：用户可能困惑「GitLab 不用 labels.yml 为什么我项目里有？」。SUMMARY 里要说明这是双兼容设计的预期产物，留待 `gh→glab` 适配 round 决定是否给 GitLab 加一份对应配置。
3. **现有项目 sync 时 4 个新增文件不可避免**：用户可以选 skip，但下次模板再变这几个文件还会重新进 TODO（按 sync skill 现行 skipped 语义）。这不是 bug，是设计选择，需在 SUMMARY 里说明。

## 6. 局限性（开发完后写进 SUMMARY）

- skill 内 `gh issue *` / `gh issue create` / `gh issue view` 等调用未做双轨适配，GitLab 项目跑 `/backlog`、`/start <#>`、`/finish` 仍会失败或行为异常 → 单独 issue 跟踪
- GitLab labels 同步未实现（无 `glab label create` 调用）
- 项目根永久多 4–5 个对端文件（双兼容设计的代价）
- 仍假设单 stack（schema 不变）

## 7. 后续 TODO（不在本轮做）

- 新 issue（`area:skill` `type:feat`）：「skill 内 `gh` → `glab` 双轨适配」，含 `/backlog`、`/start`、`/finish`、sync `gh label create` → `glab label create`、bootstrap 同步等所有命令行调用点；本轮已为这件事在模板侧准备就绪
- 新 issue（`area:template` `type:docs`）：双兼容设计的「项目根多对端文件」是否要加 opt-out flag（如 `.cc-template.yml` 加 `platforms: [github]` 让用户显式选择只发一套）；先不做、看实际反馈
