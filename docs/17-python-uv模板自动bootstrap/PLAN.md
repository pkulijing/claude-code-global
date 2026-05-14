# PLAN

## 1. 方向选择：**方向 B**（含向 A 演进的预留）

| 方向                                                                       | 选  | 原因                                                                                                                                                            |
| -------------------------------------------------------------------------- | --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **A. `templates/<stack>/post-adopt.sh`，sync/bootstrap 检测到则执行**      | ❌  | 引入第三方 shell 脚本入口，跨平台兼容（macOS/Linux/Windows-WSL）、权限位、错误传播、回滚都要重做一套；当前只有一个 stack，扩展点是**过度抽象**。                |
| **B. 直接写进 bootstrap / sync-project-config 的 python-uv 分支专属 step** | ✅  | 命令编排沿用现有 AI 编排风格（Markdown + 由模型按 step 执行），改动局部、风险可控；当未来加 node / rust stack 时再抽象到方向 A 不迟。**YAGNI + 演进路径明确**。 |
| **C. 独立 `/bootstrap-python` skill**                                      | ❌  | 用户多记一个命令，体验割裂；违背「跑完 `/bootstrap` 立刻可开发」的初衷。                                                                                        |

**方向 A 的演进伏笔**：把 python-uv 的 bootstrap step 集中到 SKILL.md 内的「Step 3.5（python-uv 专属）」单一段落里 —— 未来要抽象成 `post-adopt.sh` 时，等同于把这一段从 SKILL.md 搬到模板目录、再加一个「检测脚本存在则执行」的通用入口。

## 2. 现状回顾

- `/bootstrap` 当前流程：1) 写 README → 2) 写 CLAUDE → 3) 套模板（\_common + 用户选的 stack） → 4) 跑 `/devtree` → 5) 收尾反馈。Step 3 只复制文件 + 合并 `[tool.ruff]` 段，**不**跑任何命令。
- `/sync-project-config` adopt 模式：跟 bootstrap Step 3 几乎一样的逻辑（复制文件 + 冲突询问 + 合并 ruff 段 + labels 同步），最后写 marker。也**不**跑任何 `uv` / `pre-commit` 命令。
- `pyproject.toml.ruff.fragment` 是已有的「片段合并」特殊机制 —— 项目根**无** pyproject.toml 时，当前会跳过并提示「先 `uv init` 再 `/sync-project-config`」。本轮的核心修改就是**让 bootstrap / sync adopt 自己把 `uv init` 跑了**，不让用户回到外部命令行。

## 3. 设计要点

### 3.1 涉及哪几个入口？

| 入口                               | 是否新增 bootstrap step | 备注                                                                                                                                                                                               |
| ---------------------------------- | ----------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/bootstrap` Step 3                | ✅ 在 3.3 之后插入 3.5  | 面向空目录，安全。                                                                                                                                                                                 |
| `/sync-project-config` adopt       | ✅ 在 4.3 套模板之后    | 面向老项目，需检测 pyproject 存在 → 跳过 `uv init`，但 dev deps / pre-commit install 照跑。                                                                                                        |
| `/sync-project-config` normal sync | ❌                      | 用户已 bootstrap 过，理论上 dev deps / pre-commit 早装好；本轮不主动重跑（幂等也带来日志噪音）。**例外**：未来检测到 `pre-commit install` 没装（`.git/hooks/pre-commit` 不存在）可补，但本轮不做。 |

### 3.2 命令顺序（python-uv stack 专属）

```
1. 检测 pyproject.toml 是否存在
   ├── 不存在 → `uv init --bare`（不生成 src/ hello world，保留干净仓库）
   └── 存在   → 跳过，记录「已存在」
2. 合并模板的 [[tool.uv.index]] 段（清华源）进 pyproject.toml  ← 新增 fragment
3. 合并模板的 [tool.ruff] 段进 pyproject.toml                  ← 现有逻辑，保留
4. `uv add --dev pytest pytest-cov ruff`                        ← 在 1+2 完成后才跑，否则会卡国内源
5. 检测 pre-commit:
   - `command -v pre-commit` 有 → 跳过安装
   - 无 → `uv tool install pre-commit`
6. `pre-commit install`（确保 .git/hooks/pre-commit 落地）
```

### 3.3 清华源 index 段：新增 fragment

`uv init` 出来的 `pyproject.toml` 不含 `[[tool.uv.index]]`，国内拉 pypi 直连会很慢。本轮在模板里**新增**一份 fragment：

`templates/python-uv/__subpath__/pyproject.toml.uv-index.fragment`：

```toml
# 此片段由 bootstrap / sync-project-config 智能合并进项目 pyproject.toml。
# 已自定义的 index 配置（如内网源）会被保留，模板段以追加方式叠加。

[[tool.uv.index]]
name = "tuna"
url = "https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple"
default = true
```

> **不**在本轮把 torch 的 aliyun 镜像也写进去 —— Constitution 里写了 torch 要单独走 aliyun，但 99% 项目不用 torch，硬塞会增加 noise。需要 torch 的项目在自己 pyproject 里追加即可。

### 3.4 fragment 合并机制扩展

当前 skill 只识别一个 magic 文件名 `pyproject.toml.ruff.fragment`。本轮统一为「凡是匹配 `pyproject.toml.*.fragment` 的，都做 [tool.X] 段智能 merge」：

- `pyproject.toml.ruff.fragment` → 合并 `[tool.ruff]` 段（保留）
- `pyproject.toml.uv-index.fragment` → 合并 `[[tool.uv.index]]` 段（新增）

merge 语义：

- 项目侧没有此段 → 直接追加
- 项目侧已有此段 → AI 智能合并（保留用户自定义字段，模板缺的项追加；冲突字段询问用户）
- 特别地对数组段（如 `[[tool.uv.index]]`）：按 name 字段 union（已存在 `name = "tuna"` 则跳过）

### 3.5 失败处理

每一步都可能失败。统一规则：

- 单步失败 → **立即停止**，打印错误 + 当前状态摘要 + 「下一步可手动跑：`<原命令>` 后再 `/sync-project-config`」
- **不**自动 retry（用户更清楚是网络问题还是命令本身）
- **不**自动回滚已生效的步骤（已 `uv init` 的不删，已落地的 fragment 不撤回 —— 让用户 `git diff` + `git checkout` 自决）

具体逐步预期失败：

| 步骤                         | 可能失败                             | 处理                                                         |
| ---------------------------- | ------------------------------------ | ------------------------------------------------------------ |
| `uv init`                    | uv 未安装                            | 提示安装 uv（`brew install uv` / `curl -LsSf astral.sh/uv`） |
| `uv add --dev`               | 网络问题、清华源宕机                 | 提示 `uv add` 失败原因，建议手动重试或临时改 index           |
| `uv tool install pre-commit` | 网络、磁盘                           | 提示安装 pre-commit 失败，建议手动 `brew install pre-commit` |
| `pre-commit install`         | 不在 git repo（前置已挡）/ hook 冲突 | 提示用户检查 `.git/hooks/pre-commit`                         |

### 3.6 dev deps 硬编码

本轮固定 `pytest pytest-cov ruff` 三件。后续若要 `mypy` / `coverage[toml]` / `pytest-asyncio` 再开下一轮抽成模板变量。

## 4. 详细方案

### 4.1 修改 `skills/bootstrap/SKILL.md`

#### Step 3.3 末尾（在「冲突清单」处理之后）追加：

> #### Step 3.3.6：合并 pyproject.toml fragments
>
> 把 `pyproject.toml.ruff.fragment` 和 `pyproject.toml.uv-index.fragment`（如存在）合并进项目根 `pyproject.toml`。逻辑同 3.3 但允许 pyproject.toml 还不存在 —— 不存在则把合并**推迟**到 Step 3.5.1 完成 `uv init` 之后。

（具体来说：把现有「项目根没有 pyproject.toml → 提示先 `uv init`」改为「→ 标记 fragments 待 3.5 后合并」）

#### 在 Step 3.5（labels 同步前）插入：

> ### Step 3.5：（仅 python-uv stack）项目实际可跑化
>
> stack ≠ `python-uv` 则**整段跳过**。stack == `python-uv` 时，按以下子步骤执行；执行前**先用 AskUserQuestion 让用户确认是否执行**（默认 yes，给 no/skip 选项），让用户保留只要配置不要装依赖的选项。
>
> #### Step 3.5.1：确保 pyproject.toml 存在
>
> - `[ -f pyproject.toml ]` 不存在 → 跑 `uv init --bare`（不生成 hello world），完成后继续
> - 已存在 → 报告「检测到现有 pyproject.toml，跳过 uv init」，继续
>
> 跑完后回到 Step 3.3.6 处理待合并 fragments。
>
> #### Step 3.5.2：装常用 dev 依赖
>
> ```bash
> uv add --dev pytest pytest-cov ruff
> ```
>
> uv 会跳过已装的，幂等。失败 → 报告 stdout/stderr，提示用户手动重试 + 暂停 skill。
>
> #### Step 3.5.3：确保 pre-commit 全局可用
>
> ```bash
> if ! command -v pre-commit >/dev/null; then
>   uv tool install pre-commit
> fi
> ```
>
> #### Step 3.5.4：注册 git hook
>
> ```bash
> pre-commit install
> ```
>
> 成功后打印 `pre-commit installed at .git/hooks/pre-commit`，并提示用户可选跑 `pre-commit run --all-files` 验证（不强制跑，避免首次接入大量 finding 噪音）。

#### Step 5 收尾反馈：删掉「未来手动跑 pre-commit install」相关条目，因为本轮已经自动做了。改为：

> - python-uv stack 已自动 bootstrap：项目可立刻 `uv run pytest` / `git commit`
> - 如需启用 pre-commit 完整验证：`pre-commit run --all-files`

### 4.2 修改 `skills/sync-project-config/SKILL.md`

#### Adopt 模式 4.3 末尾追加：

> #### 4.4 （仅 python-uv stack）项目实际可跑化
>
> 同 bootstrap 的 Step 3.5（4.4.1 ~ 4.4.4），逻辑一致。区别：
>
> - 本入口下 pyproject.toml **更可能已存在**（老项目 adopt），跳过 `uv init` 是常态
> - 仍需把 fragment 合并 + dev deps + pre-commit install 一次性做完
> - 因走 AskUserQuestion 用户决策，仍保留「跳过整段」选项

#### Normal sync 不动。

但 6.2 收尾反馈中第 2 条「如需启用 pre-commit：`pre-commit install` 后 `pre-commit run --all-files` 验证」修订为：

> 2. 如新加入的 `.pre-commit-config.yaml` 还未生效，跑 `pre-commit install`（adopt 模式已自动做过）

### 4.3 新增 `templates/python-uv/__subpath__/pyproject.toml.uv-index.fragment`

内容见 §3.3。

### 4.4 `GLOBAL_CLAUDE.md` 局部修订

「项目本地推荐配置（由 stack 模板统一管理）」段落里有一句：

> 新项目 → `/bootstrap` 选 stack（如 `python-uv`），自动写入 `.prettierrc` / `.vscode/` / `.pre-commit-config.yaml` / `.gitignore` / `.github/workflows/lint.yml` / `pyproject.toml [tool.ruff]` 段、并生成 `.cc-template.yml` marker

补一句：

> python-uv stack 还会自动跑 `uv init` / `uv add --dev pytest pytest-cov ruff` / `pre-commit install`，新项目跑完即可 `uv run pytest` / `git commit`。

### 4.5 文档同步

- `docs/11-跨项目共享模板与sync-skill/PLAN.md`：是历史 plan，**不动**
- `docs/17-.../SUMMARY.md`：在 /finish 时撰写
- README.md：`/finish` 的 Step 3.5（README review）会判定是否要更新——目前 README 没有详写 python-uv bootstrap 行为，可以加一句

## 5. 测试方案

本轮是 skill markdown + AI 编排 + 命令执行，不存在传统单元测试。改为 **smoke test 清单**（在 SUMMARY.md 里记录测试结果）。

### 5.1 Smoke A：bootstrap 新空项目

```bash
mkdir /tmp/cc-smoke-bootstrap && cd /tmp/cc-smoke-bootstrap && git init
# 在 Claude Code 中跑 /bootstrap，选 python-uv
```

**期望**：

- [ ] `pyproject.toml` 存在，含 `[tool.ruff]` + `[[tool.uv.index]]` 段
- [ ] `uv.lock` 存在
- [ ] `uv tree --depth 1` 输出含 `pytest` / `pytest-cov` / `ruff`
- [ ] `command -v pre-commit` 有输出
- [ ] `.git/hooks/pre-commit` 存在
- [ ] `pre-commit run --all-files` 通过（空项目应通过）
- [ ] `.cc-template.yml` 内 `template_commit` 是 HEAD

### 5.2 Smoke B：sync adopt 已有 pyproject 的老项目

```bash
mkdir /tmp/cc-smoke-adopt && cd /tmp/cc-smoke-adopt && git init
cat > pyproject.toml <<EOF
[project]
name = "legacy"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = []
EOF
# 在 Claude Code 中跑 /sync-project-config，选 python-uv adopt
```

**期望**：

- [ ] `uv init` **未**执行（已存在）
- [ ] `pyproject.toml` 现含 `[tool.ruff]` + `[[tool.uv.index]]` 段，**且 `[project].name = "legacy"` 保留**
- [ ] dev deps 已加
- [ ] `pre-commit install` 生效

### 5.3 Smoke C：失败路径

- 临时把 `uv` 改名 `mv $(which uv) /tmp/uv.bak`，跑 bootstrap → 期望在 Step 3.5.1 报错并暂停，已写文件不回滚（事先记录）
- 恢复 uv：`mv /tmp/uv.bak $(which uv)`

### 5.4 不测什么

- 多 stack：本轮不支持
- normal sync 路径：本轮没碰，靠现有行为保证
- Windows / WSL：用户机不在 Windows，不验

## 6. 风险与回滚

| 风险                                                 | 影响                                       | 缓解                                                                            |
| ---------------------------------------------------- | ------------------------------------------ | ------------------------------------------------------------------------------- |
| `uv init --bare` 行为在 uv 升级后变了                | bootstrap 新项目结构不符合预期             | smoke A 验证；pin `uv >= 0.5` 写入 SKILL 文档提示                               |
| `uv tool install pre-commit` 与 brew 装的版本冲突    | 用户既有 brew pre-commit 又有 uv tool 版本 | `command -v pre-commit` 探测即跳过；不强行接管                                  |
| AI 编排时跳过/漏跑某一子步                           | 项目处于半 bootstrap 状态                  | SKILL 文档里写明「单步失败立即暂停 + 报当前状态」；SUMMARY 在测试段验证完整链路 |
| 老项目 adopt 时用户拒绝 4.4，但 ruff fragment 已合并 | 老项目得到了 ruff 段但没 dev deps          | 这是用户主动选择，文档明确「拒绝 4.4 = 只要配置，不动依赖」                     |

回滚：`git checkout -- pyproject.toml uv.lock .python-version` + `rm -rf .venv` 即可还原 bootstrap 前状态。pre-commit hook 通过 `pre-commit uninstall` 清掉。

## 7. 实施步骤（执行阶段）

按依赖顺序：

1. 新增 `templates/python-uv/__subpath__/pyproject.toml.uv-index.fragment`
2. 修改 `skills/sync-project-config/SKILL.md`：扩展 fragment 合并逻辑（支持 `pyproject.toml.*.fragment` 任意 X）+ 加 4.4 段
3. 修改 `skills/bootstrap/SKILL.md`：3.3.6 标记延迟合并 + 新增 3.5 段 + 改 Step 5 收尾措辞
4. 修改 `GLOBAL_CLAUDE.md`：补一句 python-uv 自动 bootstrap
5. 跑 Smoke A / B / C，记录结果到 SUMMARY.md
6. `/finish`（含 SUMMARY、关 issue #5、删 BACKLOG 行、commit）

## 8. 后续 TODO（不在本轮范围）

- 抽象到方向 A：当出现 node / rust 等第二个 stack 时，把 `Step 3.5` 段从 SKILL.md 搬到 `templates/<stack>/post-adopt.{sh,py}`，bootstrap / sync 改为「检测脚本则执行」
- dev deps 可配置：抽成 `templates/python-uv/post-adopt.config.yml` 或 marker 字段
- normal sync 主动补 `pre-commit install`：检测 `.git/hooks/pre-commit` 不存在则补做
- torch / aliyun index：需求侧由用户按需追加，模板暂不内置
