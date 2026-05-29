# PLAN

本 PLAN 同时回应 [#11](https://github.com/pkulijing/claude-code-global/issues/11) 与 [#12](https://github.com/pkulijing/claude-code-global/issues/12)。两件事归并到同一轮的根本理由：**它们共同重塑"Python 项目模板"这一资产**——一侧改"项目骨架"，一侧改"领域规则文档"，分开做会反复触碰相同文件（`GLOBAL_AGENTS.md` / `templates/python-uv/` / `bootstrap` / `sync-project-config` / `install.sh`），合并到同一 PR 反而干净。

## 0. 总体决策摘要

| 决策点                               | 结论                                                                                                                 |
| ------------------------------------ | -------------------------------------------------------------------------------------------------------------------- |
| 子 CLAUDE.md 落位                    | 新建仓库顶层目录 `rules/`，本轮只产出 `rules/python.md`                                                              |
| install.sh 部署                      | 双轨软链 `rules/` → `~/.claude/rules/` 与 `~/.codex/rules/`（参照 templates/ 现成的目录级软链）                      |
| 引用形式                             | `GLOBAL_AGENTS.md` 用"指针 + 触发条件"文字引用，**不**依赖 `@mention` 解析；同时附路径给 Agent 自行 Read             |
| Python 规则归并                      | `rules/python.md` 一份承载：原 GLOBAL_AGENTS Python 章节 4 条 + #12 七条新风格 + TDD 例外细化 + 注释纪律细化         |
| GLOBAL_AGENTS.md Python 章节         | 瘦身为 ≤ 5 行指针 + 一段"领域规则文档机制"说明                                                                       |
| src 布局落地手段                     | 借 `uv init --package` 自带能力生成 src 骨架，避免在模板里塞包名占位符；模板侧仅追加必要 `pyproject.toml.*.fragment` |
| bootstrap / sync-project-config 改动 | `uv init --bare` → `uv init --package`（含一个回滚旋钮）；fragment 命名约定保持不变                                  |
| 范围                                 | 不引入除 Python 外的其他 `rules/*.md`；不改 `templates/_common/`；不动 hooks                                         |

## 1. 子 CLAUDE.md 机制设计

### 1.1 目录名选定

候选：`rules/` vs `agent-rules/` vs `CLAUDE.md.d/`。

| 候选           | 优势                                                                                   | 劣势                                                                    |
| -------------- | -------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| `rules/`       | 简短；语义"领域规则"清晰；与 `skills/` `hooks/` `scripts/` `templates/` 同级，扩展性强 | "rules"语义偏窄，未来若放 checklist / runbook 类内容稍勉强              |
| `agent-rules/` | 强调"给 Agent 看的"                                                                    | 拗口；与现有目录命名风格（skills / hooks 等都不带 "agent-" 前缀）不一致 |
| `CLAUDE.md.d/` | 致敬"foo.d/"的 Unix 习惯；语义上是 CLAUDE.md 的扩展点                                  | CC 专属命名，对 Codex 端别扭；本轮已确立**双端**机制                    |

**采用 `rules/`**。本轮只放 `rules/python.md`；未来如需扩展（`rules/git-hooks.md` / `rules/release.md`）天然可加。

### 1.2 引用形式

`GLOBAL_AGENTS.md` 的 Python 章节改为：

```markdown
## Python 开发规则

Python 项目（pyproject.toml / uv / ruff / 包内代码）相关规范集中维护在领域规则文档 **`rules/python.md`**：

- CC 端实际路径：`~/.claude/rules/python.md`
- Codex 端实际路径：`~/.codex/rules/python.md`

**触发条件**：本轮任务一旦涉及 Python 代码、pyproject.toml、依赖管理或 Python 风格判断，**必须先把 `rules/python.md` 读入上下文**，再开始动手。
```

并在文档靠前位置（"核心开发模式"之前或紧邻）补一节：

```markdown
## 领域规则文档（rules/）

为避免本宪法臃肿，所有"领域专属"规则（语言、栈、流程）下沉到 `rules/<topic>.md`：

- CC 端：`~/.claude/rules/<topic>.md`
- Codex 端：`~/.codex/rules/<topic>.md`

**约定**：每章节在本宪法中只保留"指针 + 触发条件"两句话；Agent 命中触发条件时必须主动 Read 对应文件，不依赖 `@mention` 自动展开。
```

> 不用 `@rules/python.md` mention 的原因：CC 的 `@mention` 在主指令文档里的解析行为依赖运行时，并非显式契约；Codex 端无对应机制。"指针 + 触发条件 + 显式 Read"是两端都稳的做法。

### 1.3 install.sh 改动

在 `deploy_agent()` 函数现有「templates 目录软链」段之前/之后加一段：

```bash
# rules 目录（领域规则文档，参照 templates 走目录级软链）
if [ -d "$REPO_DIR/rules" ]; then
    link_item "$REPO_DIR/rules" "$agent_home/rules"
else
    warn "仓库中未找到 rules/ 目录，跳过"
fi
```

- 用整目录软链（不是逐文件），原因：rules 内只放纯 md，不存在 CC/Codex 端不同表现的需要；目录级软链改动最小、未来加 `rules/*.md` 时无需重跑 install.sh（只改文件本身）。
- 注意 templates 是目录级软链时也用了 `link_item` 直接拼整个目录路径，这里同款语法。

## 2. rules/python.md 内容组织

### 2.1 章节结构

```markdown
# Python 开发规则

> 本文档由 `~/.claude/global-repo/rules/python.md` 提供，双轨软链到 `~/.claude/` 与 `~/.codex/`。修改请回到 `claude-code-global` 仓库。

## 1. 环境与工具

（原 GLOBAL_AGENTS Python 章节 4 条原文搬入）

- uv 管依赖（`uv add` / 禁 `pip install`）
- `uv run` 跑脚本（禁直接 `python` / `python3`）
- ruff 做格式化 + lint
- pypi index：清华 + aliyun pytorch-wheels（带 extra）
- torch 2.5.1 / cu121 默认版本

## 2. 项目骨架（src 布局）

- 包目录 `src/<pkg>/`，**不平铺在仓库根**（#11）
- `pyproject.toml [build-system]` 用 hatchling
- `[tool.hatch.build.targets.wheel] packages = ["src/<pkg>"]`
- `[tool.pytest.ini_options] pythonpath = ["src"]` + `testpaths = ["tests"]`
- `uv sync` 即可编辑安装；`python -m <pkg>` / `pytest` 干净 import
- 顶层 `configs/` / `tests/` 与 `src/` 平级
- bootstrap / sync-project-config 已自动落该布局，手工新建包请遵循同样结构

## 3. 开发风格

（#12 七条原文搬入，结构保持 rule / 为什么 / 适用边界 / 反例 / 边界条款）

### 3.1 偏好面向对象，避免"满文件 free functions"

### 3.2 包内绝对 import

### 3.3 文件名 = 核心类名的 snake_case

### 3.4 注释 / docstring 写"当前真相"，不写"演化历史"

### 3.5 外部不可靠类型用 Protocol 鸭子型契约

### 3.6 dict-of-dicts 是 OO 重构的强信号

### 3.7 整合类必须 ≥ 1 条 happy-path integration test

## 4. 测试

（呼应 GLOBAL_AGENTS TDD 章节，补充 Python 特异内容）

- TDD 适用：业务逻辑 / 纯函数 / 算法 / 有清晰契约的接口
- 例外：探索性原型、UI、外部系统集成可后补；但整合类落地后必须有 1 条端到端 smoke（#12 第 7 条）
- 测试结构：`tests/` 与 `src/` 同级，`pyproject.toml [tool.pytest.ini_options] pythonpath = ["src"]` 已搞定 import 路径
```

### 2.2 粒度选择

- **环境与工具（§1）**：原文搬入，不删不压。
- **项目骨架（§2）**：从 #11 issue body 提炼为 5 条要点 + 一段操作提示，去掉示例代码（不需要重复在 pyproject fragment 里写过的内容）。
- **开发风格（§3）**：**#12 七条原文 1:1 搬入**。原 issue 已经写了规则 / 为什么 / 边界 / 反例 / 例外，删任何一段都损失信息密度。`rules/python.md` 作为"独立、可任意长度"的文档恰好承得起。
- **测试（§4）**：呼应 GLOBAL_AGENTS TDD 段 + #12 第 7 条 + Python 特异内容（pytest pythonpath / testpaths），避免读者还要在两个文件之间跳。

### 2.3 GLOBAL_AGENTS.md 现有 Python 章节如何处理

- 现有 4 条 bullet **从 GLOBAL_AGENTS.md 删除**（已搬入 rules/python.md §1）。
- 章节正文换成 §1.2 描述的 ≤ 5 行指针。
- TDD 章节维持原状不动 —— #12 第 7 条放进 rules/python.md §4 即可，不重复污染顶层宪法。
- "文档记录规范"章节维持原状不动 —— #12 第 4 条（注释不写演化历史）属于 Python 风格，放 rules/python.md §3.4 即可，不上提到顶层。

## 3. python-uv 模板的 src 布局改造

### 3.1 关键发现：uv 自带 `--package` 模式

uv 0.4 起支持 `uv init --package`，生成的项目骨架已经是 src 布局：`src/<pkg>/__init__.py` + 含 `[build-system] hatchling` + `[tool.hatch.build.targets.wheel] packages = ["src/<pkg>"]` 的 `pyproject.toml`。**这正是 #11 想要的样子**。

→ 当前 bootstrap Step 3.5.1 / sync-project-config Step 4.4.1 用的 `uv init --bare`，**改成 `uv init --package`**（保留 `--bare` 是为了"避免 hello world 文件"，但 `--package` 模式下生成的 `src/<pkg>/__init__.py` 是空文件，不是 hello world，符合"干净仓库"诉求）。

> 兜底：本轮在写代码阶段会本地跑一次 `uv init --package` 验证（在 `$CLAUDE_JOB_DIR` 临时目录内），确认产物符合预期再改 skill。如果 `--package` 的产物与 #11 落点有 gap，再用模板 fragment 补差。

### 3.2 仍需要在模板里加的东西

无论 `uv init --package` 的产物多完整，以下几条是 uv 不会自动给的：

1. **`pyproject.toml [tool.pytest.ini_options]`**：`pythonpath = ["src"]` + `testpaths = ["tests"]`。
   - 新增 `templates/python-uv/__subpath__/pyproject.toml.pytest.fragment`
2. **`tests/` 目录骨架**：放一个 `tests/__init__.py`（保持空）+ 可选 `tests/test_smoke.py`（仅 import 测试 + 一个 `assert True` 占位，作为 #12 第 7 条"happy-path smoke"的最小示范）。
   - 放在 `templates/python-uv/__subpath__/tests/`。
3. **`configs/` 目录**：约定有就建一个，**不放**任何文件（一个空目录在 git 里需要占位文件，可用 `.gitkeep`）。
   - 放在 `templates/python-uv/__subpath__/configs/.gitkeep`。
4. **项目根新增 `CLAUDE.md` 模板**：内容只一段 "本项目使用 python-uv 栈，Python 规范见 `~/.claude/rules/python.md`（CC）/ `~/.codex/rules/python.md`（Codex）"。让 Agent 进入任何 python-uv 项目就立刻拿到一个跳板，不必每次依赖 GLOBAL_AGENTS 加载机制。
   - 放在 `templates/python-uv/__root__/CLAUDE.md.fragment`（**新约定**：`.fragment` 后缀也用于 md 类合并，避免覆盖项目已有 CLAUDE.md；合并策略：项目无 → 创建；项目有 → 在末尾追加 "## Python 规范" 一段，去重）。
   - 是否引入这种"md fragment"机制：**列为待用户确认的开关**（见 §9）。如果用户不想要，就把这段放进 §3.3 由 bootstrap 直接写。

### 3.3 bootstrap / sync-project-config 的具体改动

#### bootstrap (`skills/bootstrap/SKILL.md`)

- **Step 3.5.1**：
  - 原文：`[ -f pyproject.toml ] && echo "exists, skip uv init" || uv init --bare`
  - 改为：`[ -f pyproject.toml ] && echo "exists, skip uv init" || uv init --package`
  - 同时调整旁注："`--package` 让 uv 直接生成 src 布局（`src/<pkg>/__init__.py` + 含 hatchling 配置的 pyproject）；这是 round 25 落地 #11 的方式。空目录 bootstrap 必然走 `uv init --package` 分支；老项目 adopt 走 `exists` 分支。"
- **Step 3.5.2**：增一行 "`uv init --package` 时已经把当前包安装为可编辑包"（不需要额外 `uv sync`）。
- **Step 3 新增 Step 3.7**：**Python 规范指引提示**。
  - "已部署 `~/.claude/rules/python.md` 与 `~/.codex/rules/python.md`；本项目所有 Python 编码遵循其中规则。GLOBAL_AGENTS Python 章节指针已生效，无需在项目根再放一份 CLAUDE.md。"

#### sync-project-config (`skills/sync-project-config/SKILL.md`)

- **Step 4.4.1**：同 bootstrap Step 3.5.1 改动。
- **Step 2.4 / 4.3**：在 fragment 处理列表里把新增的 `pyproject.toml.pytest.fragment` 自动纳入既有"`pyproject.toml.*.fragment` 智能合并"流程 —— 命名约定已经覆盖，无需改文本，只要新文件存在即可。
- **Step 4.4** 注释更新：把"`uv init --bare` 避免 hello world"换成"`uv init --package` 直接落 src 布局"。

#### 占位符问题：彻底回避

走 `uv init --package` 路线后，包名占位符（`src/<pkg>/`）由 uv 在用户机器上动态生成（基于当前目录名 / `uv init --name`），**模板侧根本不出现 `<pkg>`**。无需引入 `__pkg__/` / `{{pkg}}` 任何渲染机制。

### 3.4 对已有项目的兼容

- 新建项目走 bootstrap → 落 src 布局 ✓
- 老项目（已经是平铺布局，没 src/）跑 `sync-project-config`：
  - 模板里**不含** src 骨架（src 骨架是 uv init 生成的），所以 sync 不会"侵入式改结构"
  - 老项目只会拿到新的 `pyproject.toml.pytest.fragment` 合并提议（在 normal sync 第 6 节按现有 fragment 合并语义处理），不会被强制改成 src 布局 —— 与 #11 期望一致（#11 主要是"新项目模板"诉求）
  - 老项目想主动改 src 布局：自行手动迁移，模板不负责（这是侵入性结构变更，应由人评估）

## 4. install.sh 改动

只在 `deploy_agent()` 内新增一段 `rules/` 目录软链（详细代码见 §1.3）。其余逻辑（settings 合并 / TOML 合并 / hook 标记 / 自动同步调度）一概不动。

不修改 `settings.base.json` / `codex.config.base.toml` —— `rules/` 是普通文档，不出现在 hook / config 里。

## 5. 仓库根 CLAUDE.md / DEVTREE.md 更新

`CLAUDE.md`（项目级）的 "目录结构" 段当前列了 GLOBAL_AGENTS / skills / hooks / scripts / scheduler / templates / docs。增一行：

```markdown
- `rules/` — 领域规则文档（按 `<topic>.md` 拆分；本轮新建 `python.md`），双轨软链到 `~/.claude/rules/` 与 `~/.codex/rules/`
```

`docs/DEVTREE.md` 末尾的 Epic 索引按 `/devtree` 工作流追加本轮节点（具体节点描述在 `/finish` 阶段产出，PLAN 阶段不预占）。

## 6. 测试 / 验收

### 6.1 自动可验

- `bash install.sh` 在本机可成功跑完，CC 与 Codex 两端均存在 `~/.claude/rules/python.md` 与 `~/.codex/rules/python.md`，且都是软链到本仓库的 `rules/python.md`。
- `~/.claude/CLAUDE.md` 与 `~/.codex/AGENTS.md` 中 Python 章节正文 ≤ 5 行，并显式列出 rules/python.md 触发条件。
- `rules/python.md` markdown 渲染无破损（manual review）。

### 6.2 手工 smoke

- 在 `$CLAUDE_JOB_DIR/test-bootstrap-py` 跑：
  ```bash
  mkdir -p $CLAUDE_JOB_DIR/test-bootstrap-py && cd $CLAUDE_JOB_DIR/test-bootstrap-py
  uv init --package
  ls -la src/
  cat pyproject.toml | grep -A2 hatch.build
  ```
  验证 src 布局是否真的由 `--package` 产出。
- 验通过后，模拟 bootstrap 流程把 fragment 合并进 pyproject，跑 `uv sync && uv run pytest`，确认 pytest 能 import `src/<pkg>/`。

### 6.3 文档可读性

- 第三方视角读完 GLOBAL_AGENTS 与 rules/python.md，能否完整还原"开发 Python 项目需要遵守的所有规则"？尤其检查"开发风格 7 条"是否原汁原味（不被压缩成 bullet）。

### 6.4 不改变的边界

- 既有项目跑 `sync-project-config` 不被强制改结构（§3.4）。
- `templates/_common/` 内容字节级不动。
- `settings.base.json` / `codex.config.base.toml` / `hooks/*` 不动。

## 7. 关键文件变更清单

新增：

- `rules/python.md`
- `templates/python-uv/__subpath__/pyproject.toml.pytest.fragment`
- `templates/python-uv/__subpath__/tests/__init__.py`
- `templates/python-uv/__subpath__/tests/test_smoke.py`
- `templates/python-uv/__subpath__/configs/.gitkeep`
- `templates/python-uv/__root__/CLAUDE.md.fragment`（**待 §9 确认**）

修改：

- `GLOBAL_AGENTS.md`（Python 章节瘦身 + 新增"领域规则文档"小节）
- `install.sh`（`deploy_agent()` 增 rules/ 软链段）
- `skills/bootstrap/SKILL.md`（Step 3.5.1 改 `uv init --package`、新增 Step 3.7、旁注更新）
- `skills/sync-project-config/SKILL.md`（Step 4.4.1 改 `uv init --package`、Step 4.4 注释更新）
- `CLAUDE.md`（项目级，目录结构段新增 rules/ 条目）
- `docs/DEVTREE.md`（在 `/finish` 阶段由 `/devtree` 追加）

无改动（但需要 mention 一下避免误删）：

- `templates/_common/`
- `settings.base.json` / `codex.config.base.toml`
- `hooks/`
- `scripts/`
- 其他 `skills/*/`（含 `/start /finish /backlog` 等）

## 8. 执行顺序（建议）

1. 写 `rules/python.md`（**先此**，因为后续 GLOBAL_AGENTS / SKILL 都要引用它）
2. 改 `GLOBAL_AGENTS.md`
3. 改 `install.sh` + 本地 `bash install.sh` 验证软链生效
4. 跑 §6.2 手工 smoke 验证 `uv init --package`，确定不需要补额外 fragment
5. 改 `templates/python-uv/__subpath__/` 下 fragment / tests / configs
6. 改 `skills/bootstrap/SKILL.md` + `skills/sync-project-config/SKILL.md`
7. 改本仓库 `CLAUDE.md`
8. （`/finish` 阶段）跑 `/devtree`、`/commit` 含 `Closes #11 #12`

## 9. 关键开关（已与用户确认）

### 9.1 项目级 `CLAUDE.md` 注入：**不引入**

- 不新增 `templates/python-uv/__root__/CLAUDE.md.fragment`，不在 sync-project-config 里新增 md fragment 合并语义。
- 仅靠 `GLOBAL_AGENTS.md` 顶层指针 + 触发条件让 Agent 主动 Read `rules/python.md`。
- 影响：§7 文件清单去掉 `CLAUDE.md.fragment` 一项；§3.2 第 4 条作废；§3.3 bootstrap Step 3.7 文案改为"指针已在 GLOBAL_AGENTS 生效，无需项目级 CLAUDE.md"。

### 9.2 src 布局来源：**`uv init --package`**

- 走 §3.1 推荐路径：bootstrap / sync 把 `uv init --bare` 改为 `uv init --package`，uv 自带能力产出 src 布局。
- **执行阶段第 1 步**仍保留 §6.2 的本地 smoke：跑一次 `uv init --package` 看产物是否含 `src/<pkg>/__init__.py` + hatchling build-system + `packages = ["src/<pkg>"]`。若产物有 gap：**当场停下汇报用户**再决定补 fragment 还是改方案；不擅自切换 fallback。

---

**两个开关已定，PLAN 终稿。等用户给出"开始执行"指令后进入写代码阶段。**
