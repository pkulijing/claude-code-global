# 模板落地机制

> **单一真源**：`templates/` 下的东西怎么落到项目里，只在本文写一遍。`/bootstrap`
> （首次套用）与 `/sync-project-config`（后续同步 / adopt）共读，两端经 `install.sh`
> 目录级软链后路径为 `~/.claude/templates/MECHANICS.md`。
>
> **何时读**：这两个 skill **在真正往项目里写文件之前必须先读本文** —— 具体是
> bootstrap 的 Step 3.3 与 sync 的 2.4 / 4.3。只看流程骨架不落地的（如
> `--dry-run`、只想知道有哪几步）不必读。
>
> 字段 schema 与当初的设计取舍见 `~/.claude/global-repo/docs/11-跨项目共享模板与sync-skill/`。

## 1. 目录约定与落点

`~/.claude/templates/` 下两类目录：

- **`_common/`** —— 所有项目自动应用、不让用户选，承载 stack-无关资源（issue templates 双套、`labels.yml`、`.prettierrc` 等）。下划线开头的目录都是伪 stack，不进用户选项。
- **`<stack>/`** —— 技术栈特异。**前端 / 后端正交、可多选叠加**（`python-uv` + `react-vite` 同仓并存）。各 stack 读自己的 `stack.yml` 取 `default_path`（`__subpath__/` 的落点，**缺省 `.`**）与 `label`（选择列表展示名，缺省用目录名）。例：`python-uv` 无 `stack.yml` → 落项目根；`react-vite` 写 `default_path: frontend` → 落 `frontend/`。

每个来源内两个作用域：

| 作用域 | 落点 |
| --- | --- |
| `__root__/<rel>` | **项目根** `<rel>`，任何来源都落根 |
| `__subpath__/<rel>` | 该来源 stack 的 `<path>/<rel>` |

`_common` **不应出现 `__subpath__/` 内容**（设计约束：它只承载 stack-无关的根级资源）；万一违反，按项目根兜底并输出警告。

**冲突**：不同 stack 的 `__subpath__` 落到各自子树、天然不撞；`__root__` 由各 stack 与 `_common` 共同贡献到根，**不应有同名冲突**（设计约束），万一有则 stack 优先。目标文件已存在一律列入冲突清单逐条问用户（take 模板 / 保留项目侧 / 智能合并），**不默认覆盖**。

## 2. fragment 文件（合并，不直接落地）

凡文件名以 `.fragment` 结尾的都是**片段**，永远不落地为同名文件。去掉 `.fragment` 后缀即得目标相对路径，**目标始终在项目根**。复制流程要先把它们剔除出去，再按类型合并。

### 2.1 `pyproject.toml.<section>.fragment` —— TOML 段合并

`<section>` 用 `-` 分隔层级：`ruff` → `[tool.ruff]`、`uv` → `[tool.uv]`、`uv-index` → `[[tool.uv.index]]`、`uv-workspace` → `[tool.uv.workspace]`、`pytest` → `[tool.pytest.ini_options]`。**以 fragment 内实际表头为准。**

- 项目侧**无此段** → 直接追加；**已有** → AI 智能合并：保留用户自定义字段、追加模板新增字段、冲突字段问用户。
- **数组段**（双方括号，如 `[[tool.uv.index]]`）按 `name` 字段 union，项目侧已有同名条目则跳过，避免重复注册。
- 项目根**无 `pyproject.toml`**，按场景分四路：
  - 选了 `python-uv`（单包）→ 标记「待可跑化步骤」，等 `uv init --package` 生成 `[project]` 骨架后再合（见 §4）；
  - 选了 `python-uv-workspace`（多包虚拟根）→ **直接用本 stack 的 workspace fragments 内容创建根 `pyproject.toml`**，不等、也不 `uv init`（虚拟根本就无 `[project]`）；
  - normal sync 路径 → 标记 `skipped: 项目无 pyproject.toml`；
  - 其他 stack → 提示「先 `uv init` 或等价命令再重跑」并跳过。

### 2.2 `.vscode/<name>.json.fragment` —— JSON 合并

目标是**项目根** `.vscode/<name>.json`。

- 目标**不存在** → 用 fragment 内容创建（含父目录）。
- 目标**已存在** → 按目标语义合并：`extensions.json` 的 `recommendations` 数组做**有序去重 union**；`settings.json` 做**顶层键 union**（键只一侧→并入；两侧都是对象→递归深合并；标量冲突→问用户）。
- 多个 stack 的同名 fragment 依次合并进**同一个**根目标（先 `_common` 再逐个 stack），得各 stack 的并集（前后端的语言作用域键天然不相交，纯 union）。

**为什么一定落根**：VS Code 单根工作区只读仓库根的 `.vscode/`，子目录 stack（如 `react-vite`）也必须借此落根才生效。

## 3. 变体组 `<target>.variant.<key>`

同一 `<target>` 的多个 `.variant.<key>` 是**一组互斥变体**，只有一个能落地为 `<target>`（去掉后缀）。复制流程同样要先把它们剔除、按 `<target>` 聚合。

**落地**：问用户选一个 key（展示人话说明，未知 key 直接展示字面），只把选中那份落地到该来源 stack 的落点，其余一律不落地；目标已存在则走冲突清单。选择记进 marker 对应 stack 的 `variants[<target>]`。

**为什么选择要前移到交互、而不是都落地让用户删**：`.gitlab-ci.yml` 这类配置会被工具**真实解析执行**，多变体并存 + 手删是地雷（漏删即得一份会真跑的错误配置）。

**当前唯一变体组** `.gitlab-ci.yml`（人话说明，改动时本文是唯一出处）：

- `docker` —— Docker executor runner（GitLab.com / 官方 docker runner，image 提供 uv+Python）
- `shell` —— 本地 shell runner（公司自建、无 docker executor，runner 无 uv 时脚本装）

**老项目 marker 无 `variants` 字段**（bootstrap 早于本机制）→ 该变体组标记「需补选」，决策时问用户选一个，落地后把选择写回 marker。

**选中的 key 那份被模板删除** → 提示用户改选其他变体；非选中 key 被删则静默忽略。

## 4. 后端可跑化（`python-uv` / `python-uv-workspace`）

两者**互斥**，正常只命中其一；都不选则整段跳过。落点 path 均为 `.`，下列命令都在项目根执行。**先问用户确认是否执行**（默认 yes，给「只要配置不要装依赖」选项），选 no 则跳过整段并记入收尾反馈。

1. **确保 `pyproject.toml` 存在**
   - 单包 `python-uv`：`[ -f pyproject.toml ] && echo "exists, skip uv init" || uv init --package`。`--package` 落标准 src 布局（`src/<pkg>/__init__.py` 空文件 + 含 `[build-system] uv_build` 的 `pyproject.toml`），见 `playbooks/python.md` §2。空目录 bootstrap 走 init 分支，老项目 adopt 走 exists 分支。
   - 多包 `python-uv-workspace`：**绝不 `uv init --package`** —— 它会在虚拟根写出 `[project]` + `src/`，破坏 workspace 形态。虚拟根 `pyproject.toml` 由本 stack 的 workspace fragments 合并而成、成员包随模板 `packages/*` 复制就位，本步只需确保那些 fragments 已合。
   - 跑完**回头处理**所有标记「待可跑化步骤」的 fragment。**清华源那段必须先合**，否则下一步在国内会卡。
2. **装 dev 依赖**：`uv add --dev pytest pytest-cov ruff`。uv 会跳过已装的，幂等。失败 → 报告 stdout/stderr、提示手动重试、暂停，**不自动回滚已写文件**。
   `python-uv-workspace` 下同样写进根 `[dependency-groups] dev` 并触发一次 `uv sync`，把 `packages/*` 各成员 editable 装入、解析跨成员 `workspace=true` 依赖 —— 本步即让整个工作区可跑（`uv run pytest` 跑全树）。
3. **确保 pre-commit 可用**：`command -v pre-commit >/dev/null || uv tool install pre-commit`
4. **注册 git hook**：`pre-commit install`，成功后打印 `pre-commit installed at .git/hooks/pre-commit`。**不**强制跑 `pre-commit run --all-files`（首次接入易出大量 finding，让用户自决）。

## 5. 前端依赖安装（`react-vite`）

不选则整段跳过。模板（含写死版本的 `package.json` + 固化 npmmirror 源的 `.npmrc`）已随复制落到 `frontend/`。**先问用户确认**（默认 yes，给「只要文件不装依赖」选项）：

```bash
cd frontend && npm install
```

`.npmrc` 已固化国内镜像。失败 → 报告 stdout/stderr、提示手动重试，**不自动回滚**。装完可选 `npm run lint` / `npm run build` 验证。

## 6. 迁移去重（只在 normal sync 遇得到）

模板把某资源换了承载形式时，diff 会同时出现「删旧的」和「加新的」。**若二者的目标项目路径相同，那是机制迁移而非真删除，必须抑制删除提案** —— 否则会把项目侧正在用的文件删掉。

- **普通文件 → fragment**：`D __subpath__/X` + `A __root__/X.fragment`。目标路径**相同**（如 `python-uv` 的 `__subpath__/.vscode/settings.json`，path `.` → 根；与新的根 `.vscode/settings.json.fragment` 同落根）→ 抑制删除，只做 fragment 合并（内容不变时合并是幂等 no-op，原文件原样保留）。目标**不同**（如 `react-vite` 的 `__subpath__/.vscode/*` 落 `frontend/.vscode/`，新 fragment 落根）→ 二者不矛盾，照常提案删旧 + 合并进根。
- **普通文件 → 变体组**：`D X` + 多个 `A X.variant.<key>`。这些变体的落地目标都是同一个 `X` → 抑制对 `X` 的删除提案，改按 §3 处理这组变体（老项目 marker 必然无 `variants`，走「需补选」）。净效果：老项目从一份写死的 `.gitlab-ci.yml` 平滑迁到按 runner 选定的变体，文件本身不被误删。
