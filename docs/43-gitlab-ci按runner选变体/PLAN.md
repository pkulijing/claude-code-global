# PLAN：`.gitlab-ci.yml` 模板按 runner 类型选变体（引入「变体组」模板机制）

## 已敲定的设计取舍

| 取舍               | 决定                                                                                                         |
| ------------------ | ------------------------------------------------------------------------------------------------------------ |
| 变体组声明形式     | **文件名命名约定**（类比 `*.fragment`）：`<target>.variant.<key>`                                            |
| 变体选择持久化     | **记进 marker** `.agent-template.yml`，normal sync 只同步选中那一支                                          |
| shell 变体 uv 安装 | `before_script` 检测 `command -v uv`，缺失则 `curl -LsSf https://astral.sh/uv/install.sh \| sh` + source env |
| 锚点约定           | shell 变体注释固化「未来复用 `before_script` 用 YAML 锚点 `&`/`*`，禁 `!reference`」                         |

## 机制设计：`.variant.<key>` 命名约定

**识别规则**：模板某目录下出现一组同 `<target>`、后缀 `.variant.<key>` 的文件 →
判为「一组互斥变体」，`<target>` 为落地目标名，`<key>` 为变体标识。

```
templates/python-uv/__root__/
  .gitlab-ci.yml.variant.docker    # → target .gitlab-ci.yml, key=docker
  .gitlab-ci.yml.variant.shell     # → target .gitlab-ci.yml, key=shell
```

skill 消费时：

1. 扫描发现变体组（按 `<target>` 聚合 `.variant.*` 文件）。
2. 向用户展示各 key 让其选一个（key 的人话说明由 skill 按已知 key 给：`docker`→"Docker executor runner（GitLab.com / 官方 docker runner）"、`shell`→"本地 shell runner（公司自建，无 docker executor）"）。
3. **只把选中那份**落地为 `<target>`（去掉 `.variant.<key>` 后缀），其余变体不落地。
4. 把选择记进 marker（见下）。

**为何类比 fragment 而非 sidecar**：现有 `*.fragment` 已确立「靠文件名后缀声明特殊处理」的先例，`.variant.<key>` 与之同构，零新增 sidecar 文件、认知负担最小。key 的人话说明放 skill 侧（少数已知 key 硬编码映射），不落额外元数据文件。

**边界**：`.variant.` 必须出现在文件名**末段**（`<target>.variant.<key>`，key 不含点）。与 `.fragment` 互斥（一个文件不同时是 fragment 和 variant）。当前只有一个变体组（gitlab-ci），机制设计成通用的、未来可复用。

## marker schema 扩展

`stacks[i]` 增一个可选字段 `variants`（map: 变体 target → 选中的 key）：

```yaml
stacks:
  - stack: python-uv
    path: .
    skipped: []
    variants:
      .gitlab-ci.yml: shell # 用户 bootstrap/adopt 时选的变体 key
```

- 缺省（老 marker 无此字段）→ 视作「未记录变体选择」，normal sync 命中变体组更新时**询问补选**（向后兼容）。
- normal sync 读到 `variants[.gitlab-ci.yml]=shell` → 只用 `shell` 变体与已落地 `.gitlab-ci.yml` 做四象限 diff，不碰 `docker` 变体、不重问。

SCHEMA.md（`docs/11-.../SCHEMA.md`）同步补 `variants` 字段说明。

## 具体改动清单

### A. 模板文件（templates/python-uv/**root**/）

**A1. 删** `.gitlab-ci.yml`（拆成两个变体，原文件不再直接存在）。

**A2. 新增** `.gitlab-ci.yml.variant.docker` —— 即现有 docker 版内容，仅头注释微调（说明这是 docker executor 变体、shell 变体见同组另一文件）：

```yaml
# .gitlab-ci.yml —— docker-executor 变体（GitLab.com / 官方 docker runner）
# runner 为 docker executor 时用本变体：image 提供 uv + Python，before_script 直接 sync。
# 本地 shell runner（公司自建、无 docker executor）改用 .variant.shell。
# 与 .github/workflows/lint.yml 等价：ruff check + ruff format --check。
stages:
  - lint

ruff:
  stage: lint
  image: ghcr.io/astral-sh/uv:python3.12-bookworm-slim
  before_script:
    - uv sync --frozen
  script:
    - uv run ruff check .
    - uv run ruff format --check .
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
```

**A3. 新增** `.gitlab-ci.yml.variant.shell` —— shell-runner 变体：

```yaml
# .gitlab-ci.yml —— shell-runner 变体（本地 shell runner，公司自建，无 docker executor）
# 不指定 image：job 直接在宿主机跑。runner 无 uv 时用官方脚本装（uv 自带 standalone Python）。
# GitLab.com / 官方 docker runner 改用 .variant.docker。
#
# 复用约定：若未来多 job 需复用 before_script，一律用标准 YAML 锚点（&anchor / *anchor），
# 禁用 GitLab 的 !reference —— 通用 YAML 解析器（如 pre-commit 的 check-yaml）不认 !reference
# 自定义 tag，会报 "could not determine a constructor for the tag '!reference'" 让 commit 失败；
# YAML 锚点 GitLab 同样支持、且 check-yaml 能过。
stages:
  - lint

ruff:
  stage: lint
  before_script:
    - command -v uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh
    - . "$HOME/.local/bin/env" # 把本次安装的 uv 加进 PATH（幂等：已装时该脚本仅设 PATH）
    - uv sync --frozen
  script:
    - uv run ruff check .
    - uv run ruff format --check .
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
```

> shell 变体不写 `image:`；uv 官方装脚本落 `~/.local/bin`，`. "$HOME/.local/bin/env"` 是官方提供的 PATH 注入脚本。当前单 job，锚点是「未来若加 job」的前瞻约束，写进注释固化。

### B. bootstrap SKILL.md（skills/bootstrap/SKILL.md）

在 **Step 3.3「复制模板内容到项目」** 增加变体组处理段（与 fragment 剔除并列）：

- Step 3.3 复制流程里，**识别 `.variant.<key>` 文件、从普通复制流程剔除**（类比 fragment 剔除），聚合成变体组。
- 新增 **Step 3.3.7「落地变体组」**：对每个变体组，问用户选一个 key（展示人话说明），只把选中那份写为 `<target>`；其余不落地。
- **Step 3.6 写 marker** 处：`stacks[i]` 增写 `variants: {<target>: <选中 key>}`。

### C. sync-project-config SKILL.md（skills/sync-project-config/SKILL.md）

三处：

- **2.1 解析 marker**：增读 `stacks[i].variants`（map，可缺省）。
- **2.4 四象限分析**：识别 `.variant.<key>` 文件——
  - marker 有该 target 的选择 → 只拿选中 key 的变体文件与项目侧 `<target>` 做四象限（其余 key 变体的 diff 忽略）。
  - marker 无记录（老项目）→ 该变体组标记「需补选」，5 节决策时问用户选一个，选后写回 marker。
- **4.2/4.3 adopt**：与 bootstrap Step 3.3.7 对称——adopt 全套用时对变体组问用户选一个、只落选中份、写进 marker `variants`。
- **6.1 更新 marker**：回写时保留 / 更新 `variants` 字段。

### D. SCHEMA.md（docs/11-跨项目共享模板与sync-skill/SCHEMA.md）

补 `stacks[i].variants` 字段定义 + `.variant.<key>` 命名约定说明。

### E. 本仓库自身 marker

本仓库 `.agent-template.yml` 是 `stacks: []`（len==0，仅 `_common`），**不含 python-uv**，故不受影响、无需改。

## TDD / 验证策略

本轮是**模板 + SKILL.md 文字流程约定**的调整，无可单测的业务代码（模板消费引擎就是 AI 照 SKILL.md 执行）。验证方式：

1. **YAML 合法性**：对两个 `.variant.*` 文件跑 `python3 -c "import yaml; yaml.safe_load(...)"`（模拟 pre-commit check-yaml），确认都能被通用解析器解析（尤其验证 shell 变体没引入 `!reference`）。
2. **命名约定自洽**：确认 `.variant.` 后缀不与 `.fragment` 冲突、`<target>` 反解正确。
3. **SKILL.md 流程自洽走查**：人工走查 bootstrap / sync 两条路径，确认变体组在「复制/剔除/落地/marker/normal-sync diff」各环节都被正确接住，无悬空分支。
4. **文档 review**：确认 SCHEMA.md 与两个 SKILL.md 对 `variants` 字段和命名约定的描述一致（单一真源无 drift）。

## 收尾

- `/finish` 收尾：写 SUMMARY.md、跨项目沉淀反思、README review、`Closes #32`、rebase + FF merge + 清理 worktree。
- 记忆已在 `/quick` 阶段沉淀 `feedback_runtime_config_no_pick_one_yourself`（可执行配置不塞多变体让用户自选），本轮正是其落地。

## 不做

- 不给其他 stack（react-vite / ros2）加变体（当前无此需求，机制通用、未来按需用）。
- 不引入任何代码化的模板引擎（保持「AI 照 SKILL.md 执行」的现有形态）。
- 不改 `.github/workflows/lint.yml`（GitHub Actions 的 `setup-uv` 已处理好安装，无 runner 类型问题）。
