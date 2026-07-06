---
name: bootstrap
description: 为空项目搭建文档骨架（README.md / CLAUDE.md / DEVTREE.md），仅在项目首次开发前调用一次
disable-model-invocation: false
---

用户调用此 skill 表示要为一个**全新空项目**搭建文档骨架。本 skill 是一次性脚手架，**不**用于已有 `docs/` 历史的项目。

## 前置检查

按顺序检查，**任一命中就立即停止并报告**，不要尝试覆盖已有内容：

- `docs/` 下已存在 `N-` 数字前缀开头的开发轮次目录 → "项目已初始化（检测到 docs/N-xxx），不应运行 bootstrap。"
- `CLAUDE.md` 已存在 → "已有 CLAUDE.md，如要重置请先备份再删除原文件。"
- `DEVTREE.md` 已存在 → 同上提示

全部通过才继续。

## 信息收集

**一次性问全**，不要逐条来回：

1. **项目名称**（默认取当前目录名，告知默认值）
2. **项目一句话描述**（用作 README 与 CLAUDE.md 的开篇）
3. **是否已有第一个待启动开发项的初步想法？**（仅用于决定收尾时是否提示运行 `/backlog`，不需要详细内容）

参数（args）若非空，可作为问题 1 或 2 的输入；不足部分仍需向用户问全。

## 执行流程

### Step 1：写 README.md

```markdown
# {项目名}

{一句话描述}

## 目录结构

（待补充）

## 开发流程

本项目遵循 [全局 Constitution](https://github.com/pkulijing/claude-code-global/blob/master/GLOBAL_AGENTS.md) 中定义的「需求 - 计划 - 执行 - 总结」四步开发模式，文档记录见 `docs/`。
```

### Step 2：写 CLAUDE.md

```markdown
# {项目名}

{一句话描述}

## 目录结构

（待补充）

## 开发注意事项

（待补充）
```

**不**调用内置 `/init`：空项目无可扫的代码，等代码长起来后由用户手动跑 `/init` 重写更合适。

### Step 3：模板初始化（\_common + 按 stack）

为项目套用一份 `claude-code-global` 管理的「跨项目共享开发配置」（`.pre-commit-config.yaml` / `.vscode/` / `.gitignore` / `lint.yml` / `.gitlab-ci.yml`（变体组，按 runner 类型选一个落地，见 Step 3.3.7）/ `pyproject.toml [tool.ruff]` / issue templates 双套 / `.github/labels.yml` / `.prettierrc` 等）。**GitHub 与 GitLab 双轨同时落**、互不干扰（各读各的 CI / issue templates）。labels 同步等命令行步骤由 helper `$HOME/.claude/scripts/platform_issue.py` 按 `git remote` 自动 dispatch（契约见 `~/.claude/scripts/platform_issue.md`）。字段约定见 `~/.claude/global-repo/docs/11-跨项目共享模板与sync-skill/SCHEMA.md`。

`~/.claude/templates/` 下有两类目录：

- **`_common/`**：所有项目都套用，stack-无关（issue templates 双套、labels.yml、.prettierrc 等通用资源），bootstrap 会**自动应用**，不让用户选择
- **`<stack>/`**（如 `python-uv`、`react-vite`）：技术栈特异资源，**前端 / 后端正交、可多选叠加**（如后端 `python-uv` + 前端 `react-vite` 同仓并存）；各 stack 落点由其 `stack.yml` 的 `default_path` 决定

#### Step 3.1：探测可用 stack

- 读取 `~/.claude/templates/` 下**非下划线开头**的子目录，得到可选 stack 列表（如 `python-uv`、`react-vite`）
- 对每个 stack 读其 `stack.yml`（若存在）取两个字段：`default_path`（该 stack `__subpath__/` 文件相对项目根的落点，**缺省 `.`**——即 stack 目录下没有 `stack.yml` 或没写该字段时落项目根）与 `label`（选择列表展示名，缺省用 stack 目录名）。例：`python-uv` 无 `stack.yml` → path `.`（落根）；`react-vite` 的 `stack.yml` 写 `default_path: frontend` → 落 `frontend/` 子目录
- 下划线开头的目录（如 `_common/`）是伪 stack，自动应用，不进入用户选项
- `~/.claude/templates/` 不存在 → 提示用户「尚未通过 install.sh 部署 templates，跳过模板初始化」并跳过 Step 3 整个段落

#### Step 3.2：用户选 stack（可多选）

前端 / 后端是正交维度，一个项目可叠加多个 stack。询问用户，让其**勾选 0 个或多个** stack：

- 各 stack 一个选项，展示其 `label`（来自 Step 3.1）
- 允许全不选（只套 `_common`）

各 stack 的落点由其 `default_path` 决定（Step 3.1 已解析），**不向用户询问 path**：后端 `python-uv` 落项目根，前端 `react-vite` 落 `frontend/`，互不干扰、可同仓并存。

若一个都没选 → 跳过 Step 3.3 的 stack 部分，但 **`_common` 仍然应用**（除非 `_common/` 也不存在）；若 `_common/` 不存在则 Step 3.3 完全跳过。

#### Step 3.3：复制模板内容到项目

**先应用 `_common`，再按用户选的每个 `<stack>` 依次应用**（同名文件以 stack 优先，但理论上不应有冲突 —— 见 `~/.claude/global-repo/docs/12-backlog改为issue驱动/SUMMARY.md` 中 \_common 与 stack 的边界划分）。

对每个生效来源（先 `_common/`，再逐个选中的 `<stack>/`）：

- 把 `__root__/` 下所有文件（含点文件、含子目录结构）复制到**项目根**
- 把 `__subpath__/` 下所有文件复制到该来源的落点：`_common` 与 `default_path` 为 `.` 的 stack（如 `python-uv`）落**项目根**；`default_path` 为子目录的 stack（如 `react-vite` → `frontend/`）落 `<default_path>/`（目录不存在则建）
- 遇到目标已存在的文件：列入「冲突清单」，逐条向用户确认 take 模板 / 保留项目侧 / 智能合并；不要默认覆盖

特殊处理（一）—— **变体组文件**（凡文件名形如 `<target>.variant.<key>`，`.variant.` 在文件名末段、`<key>` 不含点）是「一组互斥变体」中的一员：同一 `<target>` 的多个 `.variant.<key>` 表示「需按环境选一个落地」。`.gitlab-ci.yml` 这类**会被工具真实执行**的运行时配置不能把多变体都落进项目再让用户删（漏删即得会真跑的错误配置），故选择前移到本步交互、只落选中那一份。本步把这些文件从普通复制流程中**剔除**（不落地为 `*.variant.*`），按 `<target>` 聚合成变体组，实际「选一个并落地」在 Step 3.3.7 执行。当前唯一变体组：

- `.gitlab-ci.yml.variant.docker` / `.gitlab-ci.yml.variant.shell` → target `.gitlab-ci.yml`，按 GitLab runner 类型选一个（见 Step 3.3.7）。

特殊处理（二）—— **fragment 文件**（凡文件名以 `.fragment` 结尾）不能直接落地为同名文件，它们是片段、需**合并**进目标文件。去掉 `.fragment` 后缀即得目标相对路径，目标始终落**项目根**。本步只把这些片段从普通文件复制流程中**剔除**（不落地为 `*.fragment` 文件），实际合并动作在 Step 3.3.6 执行。当前两类 fragment：

- `pyproject.toml.<section>.fragment` → 合并进项目根 `pyproject.toml` 对应段（TOML 段合并）。`<section>` 用 `-` 分隔层级（`ruff` → `[tool.ruff]`、`uv` → `[tool.uv]`、`uv-index` → `[[tool.uv.index]]`）。
- `.vscode/<name>.json.fragment` → 合并进项目根 `.vscode/<name>.json`（JSON 合并）。各 stack 的编辑器配置以此形式汇聚到**项目根** `.vscode/`（VS Code 单根工作区只读仓库根的 `.vscode/`，故落根才生效；子目录 stack 如 `react-vite` 也借此落根、可与 `python-uv` union）。

#### Step 3.3.5：同步 labels（helper 自动按平台 dispatch）

复制完后，如果项目根出现了 `.github/labels.yml`（来自 `_common`），调 helper：

```bash
python3 $HOME/.claude/scripts/platform_issue.py label-sync-from-file .github/labels.yml
```

helper 完整行为（平台 detect、gh/glab dispatch、color 转换、exit 2/3/4 降级、stdout TSV）见 `~/.claude/scripts/platform_issue.md`。stdout 结果原样展示给用户；exit 2/3/4 按契约降级为收尾提示（见 Step 5 收尾反馈第 6 条），不阻塞后续步骤。

#### Step 3.3.6：合并 fragments

对 Step 3.3 剔除出来的每一份 `*.fragment`，按类型合并：

**`pyproject.toml.<section>.fragment`（TOML 段合并）：**

`<section>` 用 `-` 分隔层级映射到 TOML 表头：`ruff` → `[tool.ruff]`、`uv` → `[tool.uv]`、`uv-index` → `[[tool.uv.index]]`、`uv-workspace` → `[tool.uv.workspace]`、`pytest` → `[tool.pytest.ini_options]`（以 fragment 内实际表头为准）。

- 项目根**有** `pyproject.toml` → AI 智能合并，保留用户已有字段，模板新增字段追加；冲突字段询问用户。数组段（`[[tool.X]]`，如 `[[tool.uv.index]]`）按 `name` 字段 union。
- 项目根**无** `pyproject.toml`：
  - `python-uv`（单包）→ **标记为 needs-step-3.5**（待 Step 3.5.1 `uv init --package` 生成 `[project]` 骨架后再合）。
  - `python-uv-workspace`（多包虚拟根）→ **直接用本 stack 的 workspace fragments 内容创建根 `pyproject.toml`**（虚拟根本就无 `[project]`、不该 `uv init`；多份 fragment 依次合并即得 `[tool.uv.workspace]` + 共享配置的完整虚拟根）。**不**标记 needs-step-3.5。
  - 其他 stack → 退化为提示「先 `uv init` / 等价命令再 `/sync-project-config`」并跳过。

**`.vscode/<name>.json.fragment`（JSON 合并，目标项目根 `.vscode/<name>.json`）：**

- 目标**不存在** → 用 fragment 内容创建（含父目录 `.vscode/`）。
- 目标**已存在** → 按目标语义合并：`extensions.json` 的 `recommendations` 数组做**有序去重 union**；`settings.json` 做**顶层键 union**（键只一侧→并入；两侧都为对象→递归深合并；标量冲突→询问）。
- 多个 stack 的同名 fragment 依次合并进**同一个**项目根目标（先 `_common` 再逐个 stack），得各 stack 推荐 / 设置的并集（前后端语言作用域键天然不相交，纯 union）。

#### Step 3.3.7：落地变体组（按环境选一个）

对 Step 3.3 剔除并按 `<target>` 聚合出来的每个变体组（同 `<target>`、多个 `.variant.<key>`）：

1. **问用户选一个 key**——列出该组各变体，展示人话说明。key 的人话说明由本 skill 按已知 key 硬编码给出（未知 key 直接展示 key 字面）。当前已知：
   - `.gitlab-ci.yml` 组：`docker` → "Docker executor runner（GitLab.com / 官方 docker runner，image 提供 uv+Python）"；`shell` → "本地 shell runner（公司自建、无 docker executor，runner 无 uv 时脚本装）"。
2. **只把选中那份落地**为 `<target>`（去掉 `.variant.<key>` 后缀，落到该来源 stack 的落点：`python-uv` path `.` → 项目根）。其余变体一律不落地。
3. 目标 `<target>` 已存在（罕见，如项目侧本就有 `.gitlab-ci.yml`）→ 列入冲突清单，逐条确认 take 选中变体 / 保留项目侧 / 智能合并（同 Step 3.3 普通文件冲突处理）。
4. **记住每个变体组的选择**（`<target>` → 选中 key），供 Step 3.6 写进 marker。

> 为何前移到此交互而非「都落地让用户删」：`.gitlab-ci.yml` 会被 GitLab 真实解析执行，多变体并存 + 手删是地雷（漏删即错误 CI）。选择前移、只落一份，保证项目侧永远是干净可跑的单一版本。

#### Step 3.5：（选中含 python-uv 或 python-uv-workspace 时）后端项目实际可跑化

选中的 stack **既不含** `python-uv` **也不含** `python-uv-workspace` 则**整段跳过**。命中其一时（落点 path 均为 `.`，下列 uv 命令都在项目根执行），**先询问用户确认是否执行**（默认 yes，给「只要配置不要装依赖」选项）；选 no 则跳过整段并在收尾反馈中提示用户后续可手动跑。

> `python-uv`（单包）与 `python-uv-workspace`（多包虚拟根）**互斥**，正常只会命中其一；两步分别按各自分支走。

##### Step 3.5.1：确保 pyproject.toml 存在

**单包 `python-uv`**：

```bash
[ -f pyproject.toml ] && echo "exists, skip uv init" || uv init --package
```

`--package` 落标准 src 布局（生成 `src/<pkg>/__init__.py` 空文件、无 hello world + 含 `[build-system] uv_build` 的 `pyproject.toml`），见 `rules/python.md` §2。空目录 bootstrap 走 `uv init --package` 分支；老项目 adopt 走 `exists` 分支。

**多包 `python-uv-workspace`**：**不要 `uv init --package`** —— 它会在虚拟根写出 `[project]` + `src/` 破坏 workspace 形态。虚拟根 `pyproject.toml` 由本 stack 的 workspace fragments（`uv-workspace` / `uv` / `uv-index` / `ruff` / `pytest`）合并而成，成员包随模板 `packages/*` 已整体复制就位。故本步只需**确保上述 fragments 已合**（Step 3.3.6 对「目标不存在」会用 fragment 内容创建根 `pyproject.toml`），不执行任何 `uv init`。

跑完后**回到 Step 3.3.6**处理所有标记 needs-step-3.5 的片段（清华源 fragment 必须先合，否则 3.5.2 在国内会卡）。

##### Step 3.5.2：装常用 dev 依赖

```bash
uv add --dev pytest pytest-cov ruff
```

uv 会跳过已装的，幂等。失败 → 报告 stdout/stderr，提示用户手动重试，暂停 skill 不继续。**不**自动回滚已写文件。

> **`python-uv-workspace`**：`uv add --dev` 在虚拟根（无 `[project]`）同样把依赖写进根 `[dependency-groups] dev` 并触发一次 `uv sync`——会把 `packages/*` 各成员一并 editable 装入、解析跨成员 `[tool.uv.sources] workspace=true` 依赖。无需额外 `uv init`，本步即让整个工作区可跑（`uv run pytest` 跑全树）。

##### Step 3.5.3：确保 pre-commit 全局可用

```bash
command -v pre-commit >/dev/null || uv tool install pre-commit
```

##### Step 3.5.4：注册 git hook

```bash
pre-commit install
```

成功后打印 `pre-commit installed at .git/hooks/pre-commit`。**不**强制跑 `pre-commit run --all-files`（首次接入易出大量 finding，让用户自决）。

#### Step 3.5b：（选中含 react-vite 时）前端依赖安装

选中的 stack **不含** `react-vite` 则**整段跳过**。含 `react-vite` 时，模板已在 Step 3.3 整体复制到 `frontend/`（含写死版本的 `package.json` + 固化 npmmirror 源的 `.npmrc`）。**先询问用户确认是否执行**（默认 yes，给「只要文件不装依赖」选项）：

```bash
cd frontend && npm install
```

`.npmrc` 已固化 npmmirror 源，`npm install` 自动走国内镜像。失败 → 报告 stdout/stderr，提示用户手动重试，**不**自动回滚已写文件。装完可选 `npm run lint` / `npm run build` 验证。

#### Step 3.6：写 `.agent-template.yml` marker

在项目根创建 `.agent-template.yml`（字段来源详见 SCHEMA.md）。`stacks` 列表写**所有选中的 stack**，每条 `path` 取其 `default_path`（Step 3.1 解析）；若该 stack 在 Step 3.3.7 落了变体组，把「`<target>` → 选中 key」写进该条的 `variants` map：

```yaml
# 由 claude-code-global 管理，非必要请勿手动编辑
source: <git -C ~/.claude/global-repo config --get remote.origin.url 的输出>
template_commit: <git -C ~/.claude/global-repo rev-parse HEAD 的输出>
bootstrap_time: <当前 UTC 时间的 ISO 8601 字符串>
stacks:
  - stack: python-uv
    path: .
    skipped: []
    variants: # 仅当该 stack 落了变体组时写，缺省不写
      .gitlab-ci.yml: shell # Step 3.3.7 用户选的 key
  - stack: react-vite
    path: frontend
    skipped: []
```

上例是「后端 + 前端」并存形态；只选其一就只写对应那一条，一个都没选则写 `stacks: []` 并在顶层加 `skipped: []`（见 SCHEMA.md 无 stack 形态）。`variants` 是可选字段：只有落了变体组的 stack 才写，无变体组的 stack（如 `react-vite`）不写该字段。

`source` 取不到 origin 时填占位符 `https://github.com/<owner>/claude-code-global`，并在收尾里提示用户手动补全。

### Step 4：调用 `/devtree` 落 DEVTREE.md 骨架

直接调用 `/devtree`。`/devtree` 自身已支持「冷启动」：当 `docs/DEVTREE.md` 不存在或 Epic 结构为空时，会写入完整骨架（分类图例 + 可视化占位 + 节点索引占位 + Epic 结构占位）。

**不要**在本 skill 里复制一份 DEVTREE 骨架模板 —— 单一事实来源在 `/devtree`。

### Step 5：收尾反馈

- echo-back 新建文件的路径：`README.md`、`CLAUDE.md`、`docs/DEVTREE.md`，以及（若 Step 3 未跳过）模板复制的文件清单 + `.agent-template.yml`（跳过的项注明「已存在，未覆盖」或「用户在冲突清单中选择保留」）
- 给出下一步建议清单：
  1. 检查并补完 `README.md` 与 `CLAUDE.md` 的「待补充」段
  2. 在 `DEVTREE.md` 的「Epic 结构」区块下添加首批叶 Epic
  3. 若选了 python-uv 且 Step 3.5 已执行：项目已可 `uv run pytest` / `git commit`；可选跑 `pre-commit run --all-files` 验证全量配置（首次接入易出 finding）。若选了 react-vite 且 Step 3.5b 已执行：`frontend/` 已可 `npm run dev` / `npm run build`
  4. 若 Step 3.5 被用户跳过（「只要配置不要装依赖」）：未来可手动跑 `uv init --package && uv add --dev pytest pytest-cov ruff && uv tool install pre-commit && pre-commit install`，或重跑 `/sync-project-config` adopt 走自动流程
  5. 若 Step 3 整段跳过 / `pyproject.toml` 不存在 / 选了非 python-uv stack：未来可运行 `/sync-project-config` 走 adopt 模式补全
  6. 若 Step 3.3.5 跳过了 labels 同步：按 helper exit code 提示补救（exit 3 auth → `gh`/`glab auth login`；exit 2 无 origin → 关联 remote 或自托管 GitLab 加 `--platform gitlab` 重跑；exit 4 CLI 缺失 → `brew install gh`/`glab`），补齐后 `/sync-project-config`。详见 `~/.claude/scripts/platform_issue.md`
  7. 若 `.github/labels.yml` 中 `area:` 段还是占位符：提示「按本项目实际模块改 area 段后跑 `/sync-project-config` 重新同步 labels」
  8. 若已有第一个开发项想法（信息收集第 3 问回答「有」），运行 `/backlog` 登记
  9. 准备好后运行 `/start` 开启 round 0
  10. 领域规范集中在 `~/.claude/rules/` 对应文件、按 GLOBAL_AGENTS 触发条件主动读入，不需要在项目根独立放指针 md：选了 `python-uv` 见 `rules/python.md`（涉及 Python 时）、选了 `react-vite` 见 `rules/frontend.md`（涉及前端时）
- **不调用 `/commit`** —— 是否立即提交由用户决定（与 `/backlog` 一致）
