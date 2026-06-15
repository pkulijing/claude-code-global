# Round 30：沉淀前端栈维度（rules/frontend.md + react-vite 模板 + 正交组合机制）

## Context

来自 [#19](https://github.com/pkulijing/claude-code-global/issues/19)。后端维度已完备（`rules/python.md` + `templates/python-uv/` + bootstrap 落 src 骨架），**前端维度完全空白**。teleop-survey round 11 已把一整套前端栈（React 19 + Vite 6 + TS strict + tailwind v4 CSS-first + shadcn + Biome + npmmirror）在 `~/Work/teleop-operator/frontend/` 落地并 lint/typecheck/build 全绿。本轮把它沉淀为可复用的全局资产。

**核心约束（正交两维）**：前端、后端是独立维度，一个仓可只后端 / 只前端 / 两者并存；换后端语言时前端维度原样复用。但现状 `bootstrap`/`sync` 假设单一 stack（sync 硬断言 `len(stacks) <= 1` 且 `path == .`），无法承载前后端并存。本轮须把单 stack 假设升级为「多 stack 叠加 + 固定 path 约定」。

## 已定决策

| 决策            | 选择                                                                                                 |
| --------------- | ---------------------------------------------------------------------------------------------------- |
| 组合机制深度    | 多 stack 叠加 + **固定 path 约定**（不做交互式 path 询问 / monorepo 根级同名冲突精细化，留后续轮）   |
| 前端 stack 命名 | `react-vite`（框架-构建工具，与 `python-uv` 同构）                                                   |
| scaffold 形态   | **模板预存整套、复制即用**；`package.json` 走整体文件（非 fragment）                                 |
| path 约定       | 后端 `python-uv`→`.`（根，维持现状零破坏）；前端 `react-vite`→固定 `frontend/`                       |
| 前端包源        | **npmmirror**（`.npmrc` 固化 `registry=https://registry.npmmirror.com`），`npm install` 自动走国内源 |

## 落点 1：`rules/frontend.md`（新建，类比 `rules/python.md`）

双轨软链由 `rules/` 目录级软链自动覆盖（**无需改 install.sh**）。结构：

- 抬头：双轨软链说明 + **触发条件**（本轮涉及前端代码 / web UI / React / Vite / Biome / tailwind / shadcn 时，先 Read 本文件）。
- §1 环境与工具：npm + **npmmirror**（`.npmrc`）；**Biome** 作「前端的 ruff」（`biome check` / `biome check --write`，recommended + 100 列 + 双引号）；版本基线 React 19 / Vite 6 / TS strict。
- §2 项目骨架：前端落 `frontend/` 子目录（与后端正交，后端在根）；`src/` 布局 + `@/` alias + `index.css` 承载 tailwind v4 CSS-first。
- §3 选型与约定：**tailwind v4 CSS-first**（`@tailwindcss/vite`，无 `tailwind.config.js`）；**shadcn-ui**（new-york / neutral、`components.json`、`cn` helper、新增组件用 `npx shadcn add`）；**暗色默认 + 可切**（theme-provider + mode-toggle）。
- §4 风格细则：Biome `overrides` 对底层 / WebGL 目录关 `noNonNullAssertion` / `useHookAtTopLevel`（DOM/WebGL 惯用 `!`）；前后端分离时 vite dev `server.proxy` 把 `/api`·`/ws` 代理到后端 daemon，生产由后端静态托管 `dist`。

风格遵循 `python.md` 既定调性：写 WHY、不写演化历史、不硬编码业务维度。

## 落点 2：`templates/react-vite/`（新建，逐字抽自活样板 + 去业务化）

前端文件全部落 `frontend/` 子目录 → 全部归入 `__subpath__/`（`__root__/` 不放文件）。清单：

- 配置：`package.json`（整体，依赖版本写死；`name` 改占位、去 teleop 化）、`.npmrc`、`biome.json`、`components.json`、`vite.config.ts`、`tsconfig.json`、`index.html`、`.gitignore`（`node_modules`/`dist`/`*.local`/`.vite`）。
- 源码基础件：`src/main.tsx`、`src/index.css`（tailwind v4 + oklch 明暗变量，原样通用）、`src/vite-env.d.ts`、`src/lib/utils.ts`（`cn`）、`src/components/theme-provider.tsx`、`src/components/mode-toggle.tsx`、`src/components/ui/button.tsx`、`src/App.tsx`（**新写最小占位**：ThemeProvider 包裹 + 一个标题 + Button + ModeToggle 演示）。
- 编辑器增益（新增、非搬运）：`.vscode/extensions.json`（推荐 `biomejs.biome`）+ `.vscode/settings.json`（Biome 为默认格式化器 + formatOnSave）。
- **去业务化**：`theme-provider` 的 `storageKey` `teleop-theme`→`app-theme`；`index.html` title 占位；`vite.config.ts` 的 DAEMON 注释泛化（保留 `/api`·`/ws` proxy 范式 + `127.0.0.1:8080` 示例）；`biome.json` 的 `overrides.includes` 由 `src/video/**` 改为中性示例 + 注释引导（"把底层/WebGL 目录加进来"）。

## 落点 3：正交组合机制改造（多 stack 叠加 + 固定 path）

### 3a. path 约定承载方式：**stack 自描述**（推荐方案 a）

新增 `templates/<stack>/stack.yml`：`default_path:`（缺省 `.`）+ 可选 `label`/`description`（bootstrap 选择列表展示用）。仅给 `templates/react-vite/stack.yml` 写 `default_path: frontend`；`python-uv` **不放**该文件 → 默认 `.`。
**为何选 a**：契合仓库既定哲学「templates 目录级软链、新增 stack 子目录下游即时可见、不改 skill 逻辑」（见项目 CLAUDE.md）。硬编码映射表（方案 b）每加 stack 要改两处 skill，破坏该特性。stack.yml 不承载复杂 init 逻辑（见 3b）。

### 3b. `skills/bootstrap/SKILL.md`

- **Step 3.1 探测 stack**：对每个 stack 读 `stack.yml` 取 `default_path`（缺省 `.`）与 `label`。
- **Step 3.2 选 stack：单选 → 多选**（可勾 0~N 个，如同时选 `python-uv` + `react-vite`）。
- **Step 3.3 复制**：遍历选中 stack，`__root__/<rel>`→根、`__subpath__/<rel>`→`<该 stack default_path>/<rel>`；`_common` 仍先应用。
- **Step 3.5（python-uv 专属）**：触发条件由「stack == python-uv」改为「选中集合含 python-uv」，逻辑不变（uv init + fragment 顺序约束保留）。
- **新增 Step 3.5b（react-vite 专属）**：若选中含 react-vite → 模板已整体复制到 `frontend/`，确认在 `frontend/` 跑 `npm install`（默认 yes，给「只要文件不装依赖」选项）；npmmirror 由 `.npmrc` 固化。**per-stack 初始化在 SKILL.md 显式分段表达**，不强求统一抽象（python 的 fragment 顺序约束无法纯声明式承载）。
- **Step 3.6 marker**：`stacks` 写所有选中 stack，各自 `path` 取其 `default_path`。

### 3c. `skills/sync-project-config/SKILL.md`

- **2.1 断言**：去掉 `len <= 1` 与 `path == .` 硬限制 → 改为遍历 `stacks` 列表（每条读 `stack`/`path`/`skipped`）；保留 `len == 0` 顶层 `skipped` 语义。
- **2.3 diff**：遍历 `marker.stacks`，对每个 stack 扫 `templates/<stack>/` + 始终扫 `_common/`，pathspec 列全（保留「不省略 pathspec」告诫）。
- **2.4 落点映射**：`__subpath__/<rel>` → **该文件所属 stack 的 `path`**/`<rel>`；来源 stack 由 diff 路径 `templates/<stack>/...` 直接判定。fragment 仍仅 python-uv 适用，合到 `<python-uv path>/pyproject.toml`（即根）；react-vite 无 fragment。
- **2.5 / 6 / 6.1 skipped**：每个 stack 维护各自 `skipped[]`（`file` 字段带来源 stack 维度以消歧）；`len == 0` 仍走顶层 `skipped`。
- **4.2 adopt 选 stack：单选 → 多选**；保留「无 stack（只 \_common）」。
- **4.4（python-uv 专属）**：触发条件改为「选中含 python-uv」；**新增 react-vite adopt 的 `npm install` 段**（同 3b 的 Step 3.5b）。

### 3d. 向后兼容（硬要求）

现有单 stack 项目（marker `stacks` 长度 1、`python-uv`、`path .`）在新指令下：遍历退化为单条、path `.`，行为须与旧版逐字等价；`len == 0`（如本仓自身）仍走顶层 `skipped`。执行时对每处「遍历」显式标注「len==1 时等价旧单 stack 路径」。

## 落点 4：文档联动

- **`GLOBAL_AGENTS.md`**：①「领域规则文档（rules/）」段的「当前已沉淀」列表加 `rules/frontend.md` 一行；②新增「## 前端开发规则」指针段（类比「## Python 开发规则」），含触发条件。
- **`docs/11-跨项目共享模板与sync-skill/SCHEMA.md`**：把「本轮支持 len 0/1、path 恒为 `.`」更新为「支持多 stack（len ≥ 0），各 stack 独立 path（python-uv→`.`、react-vite→`frontend`），仍不做交互式 path / monorepo 同名冲突」。
- **项目 `CLAUDE.md`**：`rules/` 与 `templates/` 描述各加一句提及 `frontend.md` / `react-vite`（轻改）。

## 不改 / 需核对

- **install.sh 不改**：`rules/`、`templates/` 均目录级软链，新增 `frontend.md`、`react-vite/`（含 `stack.yml`）自动可见。执行时**核对** install.sh 确为目录级软链以确认此判断；若实为逐文件软链则需重装。

## 验证

1. **模板自检（核心，等价 happy-path integration smoke）**：把 `templates/react-vite/__subpath__/` 整套复制到临时目录，依次 `npm install`（走 npmmirror）→ `npm run lint`（biome）→ `npm run typecheck`（tsc）→ `npm run build`（vite build），要求全绿。证明抽取的模板可独立跑通。
2. **机制走查**（SKILL.md 是 AI 指令，无自动化测试 → 走查为主）：
   - bootstrap 选 `[python-uv, react-vite]` → 落点 = 根（python）+ `frontend/`（前端），marker 写两条。
   - 纯前端选 `[react-vite]` → 仍落 `frontend/`，marker 一条。
   - **向后兼容**：现有 `python-uv`/`path .` marker 走 sync 新指令，行为不变。
3. **文档核对**：GLOBAL_AGENTS.md 指针段措辞、SCHEMA.md 断言、rules/frontend.md 触发条件齐备。

## TDD 说明

本轮产物为文档（rules / SKILL.md / SCHEMA.md）+ 静态模板文件，无传统业务逻辑 / 纯函数，TDD「先写失败单测」不直接适用。模板可用性以验证 §1 的 npm install/lint/typecheck/build 全绿作为等价 integration smoke 把关。

## 建议执行顺序

抽模板并跑通自检（§验证 1）→ 写 `rules/frontend.md` → 改 bootstrap/sync（含 stack.yml）→ 文档联动（GLOBAL_AGENTS/SCHEMA/CLAUDE）→ 整体走查（§验证 2/3）。

## 风险与边界

- 前端模板 `package.json` 依赖版本写死 → 会随时间过时，需偶尔人工 bump（已接受，换取确定性与 1:1 复现）。
- 本轮**不**处理：交互式自定义 path、monorepo 根级同名文件（如前后端各自 `.gitignore`/`.prettierrc`）的精细冲突合并 → 留后续轮，SCHEMA.md 注明。
- `_common/__root__/.prettierrc` 落根，前端用 Biome 在 `frontend/` 子目录自治、互不影响（前端不受根 prettier 管），暂不清理冗余。
