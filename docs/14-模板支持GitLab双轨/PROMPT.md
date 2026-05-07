> 来自 [#2 让 \_common / stack 模板支持 GitLab 项目（CI / issue templates 双轨）](https://github.com/pkulijing/claude-code-global/issues/2)
> Labels: `type:feat` `area:template` `priority:P1`

## 背景

当前 `templates/_common` 与各 stack 模板（如 `python-uv`）里有一批 **GitHub 专属** 文件：

- `templates/_common/__root__/.github/ISSUE_TEMPLATE/`（feat / bug / spike）
- `templates/_common/__root__/.github/labels.yml`
- `templates/python-uv/__root__/.github/workflows/lint.yml`

当目标项目实际跑在 **GitLab** 上时：

- GitLab 不识别 `.github/` 下的内容 → 这些文件被复制过去等同于死文件
- 更重要的是：**当前完全没有 GitLab 等价物**，导致整套 sync-skill 流程在 GitLab 项目上走不通（用户能感知到的明显问题，priority P1）

## 设计方向（与作者讨论后确定：项目侧双兼容）

经讨论我们**放弃**「bootstrap 时按 remote freeze platform、项目只落对应平台文件」的方案，改走更简单的方向：

> **项目侧同时落 GitHub + GitLab 两套文件，互不干扰；skill 调命令行时（`gh` / `glab`）再根据当前 `git remote` 动态选。**

理由：

1. **互不干扰**：
   - GitHub Actions 只读 `.github/workflows/`，从不看 `.gitlab-ci.yml`；反之 GitLab CI 只读 `.gitlab-ci.yml`，不看 `.github/workflows/`
   - issue templates 同理，各看各家目录
   - 所以两套并存时，**对端文件就是死文件，不会触发任何意外行为**
2. **设计大幅简化**：
   - 模板目录 schema 不动（不引入 `__shared__/__github__/__gitlab__` 三层）
   - `.cc-template.yml` 不需要 `platform` 字段
   - 不需要 D+A 去重 / schema 迁移逻辑
   - bootstrap 零交互（不需要询问 platform）
3. **双 remote / 镜像场景天然支持**：用户把仓库同时挂 GitHub + GitLab、或在两端来回切，零成本
4. **skill 端 `gh` ↔ `glab` 适配真正解耦**：每次调用时检测 `git remote`，不依赖 marker

唯一代价：**项目根永久多 4–5 个对端文件**（GitHub 项目里有 `.gitlab/` + `.gitlab-ci.yml`，反之 GitLab 项目里有 `.github/` 下若干）。这点噪音 << 上面的设计简化收益。

## 希望达到的最终效果

1. **`templates/_common/__root__/`** 内同时含：
   - `.github/ISSUE_TEMPLATE/{feat,bug,spike}.md`（GitHub 现状保留）
   - `.github/labels.yml`（保留）
   - `.gitlab/issue_templates/{feat,bug,spike}.md`（**新增**，内容用 GitLab quick action `/label ~"type:feat"` 替代 GitHub frontmatter `labels:`）
   - `.prettierrc`（保留，平台无关）
2. **`templates/python-uv/__root__/`** 内同时含：
   - `.github/workflows/lint.yml`（保留）
   - `.gitlab-ci.yml`（**新增**，等价的 ruff check + ruff format --check job）
3. **sync-project-config skill** 的 `gh label create` 调用增加一句 `git remote get-url origin` 判定：
   - origin 指向 GitHub → 跑 `gh label create`
   - origin 指向 GitLab / 没 origin → 跳过并打印「GitLab labels 同步将在后续 issue 落地」提示
   - **本轮不**实现 `glab label create`（留给后续）
4. **bootstrap skill** 几乎不需要改逻辑，只是模板里多了几个 GitLab 文件被一起复制；同样的 `gh label create` 兜底判定加一下

## Scope（本轮交付）

- ✅ `templates/_common/__root__/.gitlab/issue_templates/{feat,bug,spike}.md`：新增 3 个 GitLab issue template，内容沿用 GitHub 版结构、把 frontmatter `labels:` 换成 body 顶部 `/label ~"type:..."` quick action
- ✅ `templates/python-uv/__root__/.gitlab-ci.yml`：新增 GitLab CI lint job
- ✅ `skills/sync-project-config/SKILL.md`：`gh label create` 步骤前加 `git remote` 判定 + GitLab 跳过提示
- ✅ `skills/bootstrap/SKILL.md`：同样的 `gh label create` 判定 + 收尾文案补充 GitLab 项目的提示分支
- ✅ `docs/11-跨项目共享模板与sync-skill/SCHEMA.md`：补一段说明双兼容设计（schema 本身不变，但行为有变）
- ⏸️ skill 内 `gh` → `glab` 双轨适配（`/backlog`、`/start`、`/finish` 中的 `gh issue *` 调用）：**本轮不做**，单独 issue 跟进
- ⏸️ GitLab labels 同步（`glab label create` 调用 + GitLab 平台 labels 配置约定）：本轮不做，与 `gh→glab` 适配那个 issue 一起落

估约 0.5–1 轮开发（远小于初版方案的 1.5–2 轮）。

## 风险与注意点

- **GitLab issue template 的 quick action 必须放在 body 首行**才生效，编写时注意；模板文件里加注释提醒
- **GitLab CI 镜像选择**：先用 `python:3.12-slim` + `pip install uv` 最简形态，性能调优（cache uv venv 等）留后续
- **现有 GitHub 项目下次 sync** 会看到「新增 4 个 GitLab 相关文件」的 TODO；这是**预期行为**，用户 accept 后项目里多 4 个死文件、不影响 GitHub 流程；如果用户嫌噪音，可以 skip 这几条（marker 的 `skipped[]` 机制覆盖此场景）
- **不实现 symlink 共享**：GitHub frontmatter（`labels:`）vs GitLab quick action（`/label ~"..."`）机制不同，issue template 必须分两份内容才能保留各自平台的「自动打 label」便利；CI 文件结构更是完全不同

## 关联

- 后续 issue（`area:skill`）：skill 内所有 `gh issue *` / `gh label *` 调用做 `gh`/`glab` 双轨适配；本轮交付让模板侧准备就绪、为后续 skill 改造扫除文件层面障碍
- 后续 issue（`area:template`）：GitLab labels 同步约定（如要不要在 `_common` 里放一份 `.gitlab/labels-equivalent.yml` + skill 调 `glab label create`）
