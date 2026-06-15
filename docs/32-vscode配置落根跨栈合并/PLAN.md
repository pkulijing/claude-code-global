# PLAN：`.vscode/` 落项目根、跨 stack 合并（fragment 机制泛化）

## 1. 问题根因

- VS Code 单根工作区下**只读「工作区根」的 `.vscode/`**；`frontend/.vscode/` 在「打开仓库根」时完全不生效。
- react-vite 的 `.vscode/` 经 `__subpath__/` + `default_path: frontend` 落到 `frontend/.vscode/` → 打开根目录看不到 biome 推荐。
- python-uv 的 `.vscode/` 只是因为 `default_path: .`「恰好落根」才生效——不是对子目录 stack 也成立的统一机制。
- 额外隐患：react-vite 的 `settings.json` 含**全局键**（`editor.defaultFormatter` / `editor.formatOnSave` / 全局 `codeActionsOnSave`），一旦落根会把 Biome 设成所有语言（含 Python）的默认格式化器。

## 2. 设计：把 `.vscode/` 升级为「根级、可跨 stack 合并」的 fragment 资源

核心思路 = **复用并泛化既有的 `pyproject.toml.*.fragment` 机制**。今天 fragment 只有一类（TOML 段合并）；本轮新增一类（JSON 文件合并），让编辑器配置以 fragment 形式从各 stack 汇聚、合并进**项目根 `.vscode/`**。

### 2.1 fragment 分类（泛化后）

`*.fragment` 文件一律**不直接落地**，按目标文件类型分派合并：

| fragment 命名                       | 目标                       | 合并语义                  |
| ----------------------------------- | -------------------------- | ------------------------- |
| `pyproject.toml.<section>.fragment` | 根 `pyproject.toml` 对应段 | TOML 段合并（既有，不动） |
| `.vscode/<name>.json.fragment`      | 根 `.vscode/<name>.json`   | **JSON 合并（新增）**     |

判定规则：文件名以 `.fragment` 结尾即为 fragment；去掉 `.fragment` 后缀得目标相对路径（如 `.vscode/extensions.json.fragment` → `.vscode/extensions.json`），目标始终落**项目根**。

### 2.2 JSON 合并语义（`.vscode/*.json.fragment`）

- **`extensions.json`**（`recommendations` 数组）：与目标 `recommendations` 做**有序去重 union**（已有的不重复加，新的追加到末尾）。目标不存在 → 用 fragment 内容创建。
- **`settings.json`**（对象）：**顶层键 union**；
  - 键只在一侧 → 直接并入；
  - 键两侧都有且**值均为对象**（如两 stack 都定义 `[json]`）→ 递归深合并；
  - 键两侧都有且为**标量冲突**（同键不同值）→ **询问用户**取舍。
  - 实践中两 stack 的语言作用域键天然不相交（`[python]`/`[markdown]` vs `[typescript]`/`[typescriptreact]`/`[json]`/…），纯 union、零冲突。

> 合并由 skill 指令驱动 AI 执行（与 `pyproject.toml.*.fragment` 一致，无独立 helper 脚本）。

## 3. 模板文件改动

### 3.1 react-vite：settings 全语言作用域化 + 移为 fragment

**删除** `templates/react-vite/__subpath__/.vscode/`（两个文件，连空目录）。

**新增** `templates/react-vite/__root__/.vscode/extensions.json.fragment`：

```json
{ "recommendations": ["biomejs.biome"] }
```

**新增** `templates/react-vite/__root__/.vscode/settings.json.fragment`（去掉全局键，全部下沉到语言块，对照 python-uv「好公民」写法）：

```json
{
  "[typescript]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "biomejs.biome",
    "editor.codeActionsOnSave": { "source.organizeImports.biome": "explicit" }
  },
  "[typescriptreact]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "biomejs.biome",
    "editor.codeActionsOnSave": { "source.organizeImports.biome": "explicit" }
  },
  "[javascript]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "biomejs.biome",
    "editor.codeActionsOnSave": { "source.organizeImports.biome": "explicit" }
  },
  "[javascriptreact]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "biomejs.biome",
    "editor.codeActionsOnSave": { "source.organizeImports.biome": "explicit" }
  },
  "[json]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "biomejs.biome"
  },
  "[jsonc]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "biomejs.biome"
  },
  "[css]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "biomejs.biome"
  }
}
```

（补 `[javascript]`/`[javascriptreact]`：Biome 同样格式化 JS 家族，React 项目可能有 `.jsx`/`.js`。）

### 3.2 python-uv：`.vscode/` 也改为 fragment（混合仓才能与 react-vite 共并）

> 必须改：若只有 react-vite 走 fragment、python-uv 仍 verbatim 落根，混合仓里两者会在根 `.vscode/` 撞文件、互相覆盖。两 stack 统一走 fragment 才能 union。content 不变、只换机制与文件名。

**删除** `templates/python-uv/__subpath__/.vscode/`。

**新增** `templates/python-uv/__root__/.vscode/extensions.json.fragment`：

```json
{
  "recommendations": [
    "charliermarsh.ruff",
    "esbenp.prettier-vscode",
    "ms-python.python"
  ]
}
```

**新增** `templates/python-uv/__root__/.vscode/settings.json.fragment`（内容 = 原文件，`[python]`/`[markdown]` 两块照搬）。

## 4. Skill 改动

### 4.1 `bootstrap/SKILL.md`

- **Step 3.3（剔除 fragment）**：把「剔除 `pyproject.toml.*.fragment`」泛化为「剔除所有 `*.fragment`」，不落地为同名文件。
- **Step 3.3.6（合并 fragment）**：现标题/正文只讲 pyproject；扩为「合并 fragments」，新增 `.vscode/*.json.fragment` 的 JSON 合并分支（按 §2.2 语义），与 pyproject TOML 合并并列。

### 4.2 `sync-project-config/SKILL.md`

- **§2.4 特殊段**（line 131）：把「特殊：`pyproject.toml.*.fragment` 永不直接写文件」泛化为两类 fragment，补 `.vscode/*.json.fragment` 的 JSON 合并语义（§2.2）。
- **§2.4 / §6 执行**（line 210/282）：accept 分支补「`.vscode` fragment → JSON 合并」动作，与 pyproject 段合并并列。
- **存量迁移去重**（见 §5）：补一条规则处理「`__subpath__` 删除 + 同目标 `*.fragment` 新增」的伪删除。

## 5. 存量项目迁移（sync 路径）

模板 diff 会同时出现「删除旧 `__subpath__/.vscode/*` + 新增 `__root__/.vscode/*.fragment`」。两种 stack 表现不同：

- **react-vite**：旧落点 `frontend/.vscode/*` 与新落点根 `.vscode/*` **不同路径** → 删除 `frontend/.vscode/*`（合法询问）+ fragment 合并进根（新建/合并）。两动作互不矛盾，按常规流程走即可。
- **python-uv**：旧落点 = 根 `.vscode/*`，新 fragment 目标**也是**根 `.vscode/*` → 同一路径。会产生「建议删除根 `.vscode/settings.json`」与「fragment 合并进根 `.vscode/settings.json`」自相矛盾的提案。

**新增 skill 规则**：当某 `__subpath__/X` 的删除，其**目标项目路径**与某新增 `*.fragment` 的**目标项目路径相同** → 判为「机制迁移而非真删除」，**跳过删除询问**，仅执行 fragment 合并（python-uv content 不变 → 合并为幂等 no-op，根 `.vscode/` 原样保留）。

## 6. 文档更新（写「当前真相」）

- `rules/frontend.md` §4.3（line 56）：`.vscode/settings.json` 措辞更新为「根 `.vscode/settings.json`（由 react-vite 的 `.vscode/settings.json.fragment` 合并而来）」；并补一句：编辑器配置落项目根、跨 stack 合并，打开仓库根即生效。
- `CLAUDE.md`（项目根，line 17 模板段）：补一句 fragment 两分类（TOML 段 + `.vscode` JSON）说明，点明 `.vscode/` 经 fragment 汇聚到项目根。
- `docs/11-跨项目共享模板与sync-skill/SCHEMA.md`：
  - 「与文件 scope 的关系」补 fragment 泛化说明；
  - `skipped[].file` 示例里的 `__subpath__/.vscode/settings.json` 改为仍有效的示例（如 `__root__/.vscode/settings.json.fragment`）。
- 不改 round-30 的 SUMMARY/PLAN（历史快照，按「注释写当前真相、不改演化史」原则保留）。
- 新增本轮 `docs/32-.../SUMMARY.md`（收尾时）。

## 7. 验证（手动场景，无可执行代码）

本轮产物全是模板文件 + skill markdown，**无新增可执行代码**（JSON 合并是 AI 按 skill 指令执行，与既有 pyproject fragment 一致，无 helper 脚本）→ **不适用单元测试 TDD**。改以「机制走查 + JSON 合法性」验证：

1. **JSON 合法性**：所有新增 `*.fragment` 用 `python3 -m json.tool` 校验是合法 JSON（fragment 本体即合法 JSON 对象，便于合并）。
2. **纯前端仓走查**：react-vite 单 stack → 根 `.vscode/extensions.json` = `{recommendations:[biomejs.biome]}`、根 `.vscode/settings.json` = 语言作用域块。打开根即提示 biome。
3. **纯后端仓走查**：python-uv 单 stack → 与改动前根 `.vscode/` 等价（content 未变）。
4. **混合仓走查**：python-uv + react-vite → 根 `.vscode/extensions.json.recommendations` = ruff/prettier/python/biome 四项 union；`settings.json` = `[python]`/`[markdown]`/`[typescript]`/… 全部并存、无全局键污染 Python。
5. **存量迁移走查**：按 §5 两分支逐条核对 sync 提案不自相矛盾。

> 后续可选硬化（不在本轮）：把 JSON fragment 合并抽成带单测的 `merge_json_fragment.py` helper（届时 pyproject 合并也可一并脚本化）。见 TODO。

## 8. 风险与权衡

- **打开 `frontend/` 子目录的前端开发者**：根 `.vscode/` 不再在 `frontend/` 留副本 → 直接打开 `frontend/` 会丢 biome formatOnSave。取舍：本仓库惯例是「打开仓库根」，留副本会引入双份漂移，故**只落根**。在 frontend.md 注明此约定。
- **fragment 机制泛化**面较广（动两个 skill + 两个 stack + 迁移规则），但与既有 pyproject fragment 同构，认知成本低、长期一致。
- 备选「各 stack verbatim 落 `__root__/.vscode/` + 靠冲突时 AI 合并」被否：违反 SCHEMA「stacks 的 `__root__` 不应同名冲突」约定，且每次 sync 都要临时 AI 合并、脆弱。fragment 是与现有设计一致的正解。

## 9. 执行顺序

1. 模板文件：删旧 `__subpath__/.vscode/`、加两 stack 的 `__root__/.vscode/*.fragment`（§3）。
2. `bootstrap/SKILL.md`（§4.1）、`sync-project-config/SKILL.md`（§4.2 + §5 迁移规则）。
3. 文档：frontend.md / 项目 CLAUDE.md / SCHEMA.md（§6）。
4. 验证走查（§7）。
5. `/finish` 收尾：SUMMARY.md + 反思沉淀 + commit。
