# SUMMARY：`.vscode/` 落项目根、跨 stack 合并（fragment 机制泛化）

## 开发项背景

round 30 沉淀 `react-vite` 前端栈模板时，把整套前端脚手架（含 `.vscode/extensions.json` + `.vscode/settings.json`）放在 `templates/react-vite/__subpath__/`，落点由 `stack.yml` 的 `default_path: frontend` 决定——即前端的 `.vscode/` 最终落在项目的 `frontend/.vscode/` 子目录。

**问题表现**：用户打开项目根目录时，VS Code **不提示安装** `frontend/.vscode/extensions.json` 里推荐的 Biome 插件。

**根因**：VS Code 单根工作区**只读取「打开的工作区根」的 `.vscode/`**；子目录（`frontend/.vscode/`）的 `extensions.json` 推荐与 `settings.json` 配置在「打开仓库根」这一惯常用法下完全失效。而本仓库开发惯例正是「打开仓库根」，于是前端栈的编辑器增益形同虚设。后端 `python-uv` 能生效只是因为 `default_path: .`「恰好落根」，不是对子目录 stack 也成立的统一机制。

**额外隐患**：react-vite 的 `settings.json` 含**全局键**（`editor.defaultFormatter` / `editor.formatOnSave` / 全局 `codeActionsOnSave`），一旦落根会把 Biome 设成所有语言（含 Python）的默认格式化器。

## 实现方案

### 关键设计

**复用并泛化既有的 `pyproject.toml.*.fragment` 机制**：今天 fragment 只有一类（TOML 段合并），本轮新增第二类（JSON 文件合并），让编辑器配置以 fragment 形式从各 stack 汇聚、合并进**项目根 `.vscode/`**。

1. **fragment 泛化判定**：凡文件名以 `.fragment` 结尾即不直接落地，去掉后缀得目标相对路径（始终落项目根），由 skill 按目标类型合并。两类：
   - `pyproject.toml.<section>.fragment` → TOML 段合并（既有，不动）
   - `.vscode/<name>.json.fragment` → **JSON 合并（新增）**
2. **JSON 合并语义**：`extensions.json` 的 `recommendations` 数组做有序去重 union；`settings.json` 对象做顶层键 union（键只一侧→并入；两侧都为对象→递归深合并；标量冲突→询问）。
3. **react-vite settings 全语言作用域化**：去掉全局键，全部下沉到 `[typescript]` / `[json]` / … 语言块（对照 python-uv 的「好公民」写法）。这是落根不污染 Python 的前提——前后端的语言作用域键天然不相交，纯 union 零冲突。
4. **两 stack 统一走 fragment**：python-uv 的 `.vscode/`（落点本就是根）也改为 fragment，否则混合仓里它 verbatim 落根会与 react-vite 的 fragment 目标撞文件、互相覆盖。统一 fragment 才能 union 共存。
5. **存量迁移去重规则**：模板把资源从「`__subpath__` 普通文件」改为「`__root__/*.fragment`」时，diff 同时出现「删除旧文件 + 新增 fragment」。skill 判断二者目标项目路径是否相同：相同（python-uv：旧落点=新目标=根 `.vscode/`）→ 判为机制迁移、抑制删除提案、仅幂等合并；不同（react-vite：旧 `frontend/.vscode/` vs 新根 `.vscode/`）→ 照常删旧 + 合并进根。

### 开发内容概括

| 类别                          | 改动                                                                                                                                                                                                             |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **模板**                      | 两 stack 的 `.vscode/` 从 `__subpath__/` 迁到 `__root__/*.fragment`（python-uv 两文件 + react-vite extensions 为纯改名；react-vite settings 重构为语言作用域，删+增）                                            |
| **bootstrap SKILL**           | Step 3.3「剔除 fragment」从「仅 pyproject」泛化为「所有 `*.fragment`」；Step 3.3.6 改名「合并 fragments」，新增 `.vscode/*.json.fragment` 的 JSON 合并分支                                                       |
| **sync-project-config SKILL** | §2.4 特殊段泛化为两类 fragment + 新增「fragment 迁移去重」规则；adopt 路径（§4.3）、accept 动作（§6）补 `.vscode` JSON 合并；修正一处过时示例（`__subpath__/.vscode/old.json` → `__subpath__/configs/old.json`） |
| **文档**                      | `rules/frontend.md` §4.3（落根说明 + 取舍）、项目 `CLAUDE.md`（fragment 两分类）、`SCHEMA.md`（scope 关系段 + skipped 示例）、`README.md`（两 stack 模板内容描述）                                               |

### 额外产物

- **合并走查脚本**（一次性验证，非交付）：模拟纯前端 / 纯后端 / 混合三种仓形态的 fragment 合并，断言「无全局键污染」「settings 顶层键零冲突」「Python 仍由 ruff 接管」，全部通过。
- 4 个 fragment 文件均经 `python3 -m json.tool` 校验为合法 JSON。

## 局限性

- **JSON 合并是 AI 按 skill 指令执行**，无独立 helper 脚本与单测（与既有 pyproject fragment 一致）。本轮产物全是模板文件 + skill markdown，无可执行代码，故不适用 TDD；改以「JSON 合法性 + 三形态走查」验证。AI 执行合并存在偶发偏差风险，未被自动化测试兜住。
- **单独打开 `frontend/` 子目录开发会丢这些编辑器设置**：配置只落仓库根、不在 `frontend/` 留副本（避免双份漂移）。取舍前提是「打开仓库根」这一仓库惯例，已在 `rules/frontend.md` 注明。
- **存量项目迁移依赖 sync 的「迁移去重」规则正确执行**：python-uv 老项目首次 sync 时，靠 skill 识别「旧落点=新目标」抑制伪删除——这条规则本身也是 AI 判定，未自动化验证。

## 后续 TODO

- 可选硬化：把 JSON fragment 合并抽成带单测的 `merge_json_fragment.py` helper，届时 pyproject 段合并也可一并脚本化，让两类 fragment 合并都有确定性实现 + 测试兜底，替掉「AI 临场合并」。
- 真实回归：在一个 react-vite 单 stack 项目与一个 python-uv+react-vite 混合项目上各跑一次 `/bootstrap` 与存量 `/sync-project-config`，端到端验证根 `.vscode/` 合并产物与迁移去重。

## 可沉淀项

本轮**就发生在 claude-code-global 仓库内部**——所有改动（模板、skill、规则文档）本身即是跨项目资产的直接修改，不存在「需另向 claude-code-global 提 issue」的外溢候选。

唯一够格的沉淀候选是上面「后续 TODO」首条（`merge_json_fragment.py` helper + 单测），**去向 = 本项目内 `/backlog` 起 issue**（自指守卫：当前仓库即 claude-code-global，不跨仓 file）。是否起由用户在 Step 3 决定。
