# Round 30 开发总结：沉淀前端栈维度

> 对应 issue [#19](https://github.com/pkulijing/claude-code-global/issues/19)。详细方案见同目录 `PLAN.md`，本文件只概括关键设计与产物。

## 开发项背景

后端维度此前已完备：`rules/python.md` + `templates/python-uv/` + bootstrap 自动落 src 骨架。但**前端维度完全空白** —— 每起一个带前端的新项目，都要从零回忆「React 19 + Vite 6 + TS strict + tailwind v4 CSS-first + shadcn + Biome + npmmirror」这套组合并手敲一遍。

teleop-survey 一轮已把这整套栈在 `~/Work/teleop-operator/frontend/` 落地、lint/typecheck/build 全绿，是经实战验证的活样板。本轮把它**沉淀为可复用的全局资产**：一份领域规则文档 + 一套复制即用的 scaffold 模板，并打通「前端 / 后端正交两维、可同仓叠加」的组合机制。

## 实现方案

### 关键设计

1. **正交两维 + 固定 path 约定**：前端、后端是独立维度，一个仓可只后端 / 只前端 / 两者并存。落点用**固定约定**而非交互式询问 —— 后端 `python-uv` 落根（`.`，维持现状零破坏），前端 `react-vite` 落 `frontend/` 子目录。
2. **stack 自描述（`stack.yml`）承载 path**：在 `templates/<stack>/` 放 `stack.yml`（`default_path` + `label` / `description`），bootstrap / sync 读它决定落点与展示名。`react-vite` 写 `default_path: frontend`；`python-uv` **不放**该文件 → 缺省 `.`。选此方案是为契合仓库既定哲学「templates 目录级软链、新增 stack 子目录下游即时可见、不改 skill 逻辑」—— 硬编码映射表每加 stack 要改两处 skill，破坏该特性。
3. **单 stack 假设升级为多 stack 叠加**：原 `sync` 硬断言 `len(stacks) <= 1` 且 `path == .`，无法承载前后端并存。本轮把 bootstrap / sync 的「选 stack」由单选改多选、「落点」由遍历 stack 各自 `default_path` 决定、marker 的 `stacks[]` 记多条。**向后兼容是硬要求**：`len == 1`（现有 `python-uv` / `path .`）退化为旧单 stack 路径、逐字等价；`len == 0`（如本仓自身）仍走顶层 `skipped`。
4. **scaffold = 模板预存整套、复制即用**：前端文件全部归入 `__subpath__/`（落 `frontend/`），`package.json` 走整体文件（依赖版本写死，换确定性与 1:1 复现）而非 fragment。npmmirror 由模板内 `.npmrc` 固化，`npm install` 自动走国内源。

### 开发内容概括

- **`rules/frontend.md`（新建）**：类比 `rules/python.md` 的领域规则文档。抬头双轨软链说明 + 触发条件；§环境工具（npm + npmmirror + Biome 作「前端的 ruff」+ 版本基线）；§项目骨架（落 `frontend/` + `@/` alias + `index.css` 承载 tailwind v4）；§选型约定（tailwind v4 CSS-first、shadcn new-york/neutral、暗色默认可切）；§风格细则（Biome overrides 对 WebGL 目录关 `noNonNullAssertion`、vite `server.proxy` 代理 `/api`·`/ws`）。
- **`templates/react-vite/`（新建，19 文件）**：逐字抽自活样板并去业务化。配置（`package.json` / `.npmrc` / `biome.json` / `components.json` / `vite.config.ts` / `tsconfig.json` / `index.html` / `.gitignore`）+ 源码基础件（`main.tsx` / `index.css` / `vite-env.d.ts` / `lib/utils.ts` / `theme-provider` / `mode-toggle` / `ui/button` / 最小占位 `App.tsx`）+ 编辑器增益（`.vscode/` Biome formatOnSave）+ `stack.yml`（`default_path: frontend`）。
- **`skills/bootstrap/SKILL.md` 改造**：Step 3.1 读 `stack.yml`；3.2 单选→多选；3.3 按各 stack `default_path` 落点；3.5 python-uv 触发条件改「选中集合含 python-uv」；新增 3.5b（react-vite 在 `frontend/` 跑 `npm install`）；3.6 marker 写多条。
- **`skills/sync-project-config/SKILL.md` 改造**：2.1 去掉 `len<=1` / `path==.` 硬断言改遍历；2.3 多源 diff；2.4 落点按来源 stack 的 path；2.5 per-stack `skipped`；4.2 adopt 多选；新增 4.5 react-vite adopt 的 `npm install`；6.1 marker 多条。
- **文档联动**：`GLOBAL_AGENTS.md`（rules 列表加 `frontend.md` + 新增「## 前端开发规则」指针段）、`docs/11/SCHEMA.md`（多 stack len 0/1/multi 语义 + 各 stack 独立 path）、项目 `CLAUDE.md`、`README.md`（rules 表 + 内容概览 + 模板表 + bootstrap 工作流各加前端维度）、`docs/DEVTREE.md`（round 30 归入「项目模板机制」Epic 节点）。

### 额外产物

- **模板自检（等价 happy-path integration smoke）**：把 `templates/react-vite/__subpath__/` 整套复制到临时目录，`npm install`（走 npmmirror）→ `npm run lint`（biome）→ `npm run typecheck`（tsc）→ `npm run build`（vite build）全绿，证明抽取的模板可独立跑通。
- **install.sh 不改的核对结论**：`rules/`、`templates/` 均目录级软链，新增 `frontend.md`、`react-vite/`（含 `stack.yml`）自动可见，无需重装。

## 局限性

- 前端模板 `package.json` 依赖版本写死 → 会随时间过时，需偶尔人工 bump（已接受，换取确定性与 1:1 复现）。
- 本轮**不**处理：交互式自定义 path、monorepo 根级同名文件（如前后端各自 `.gitignore` / `.prettierrc`）的精细冲突合并 —— 留后续轮，SCHEMA.md 已注明。
- `_common/__root__/.prettierrc` 落根，前端用 Biome 在 `frontend/` 子目录自治、互不影响（前端不受根 prettier 管），本轮未清理这处冗余。

## 后续 TODO

- 视实际需要补「交互式自定义 path」与「monorepo 根级同名文件冲突合并」（本轮刻意留白的两项）。
- 前端模板依赖版本定期 bump（可考虑配一个轻量 `/fe-bump` 或纳入现有维护流程）。
- 评估是否清理 `_common/.prettierrc` 与前端 Biome 的职责重叠（目前井水不犯河水，优先级低）。

## 可沉淀项

本轮产物本身就是跨项目资产（rules/frontend.md + react-vite 模板 + 多 stack 机制），落点即 claude-code-global 仓库内，无需再向外提 issue。过程中浮现一条**对本仓后续维护可复用**的经验：

- **「新增一个 stack 维度」现已有可重复配方**：抽活样板 → 全部归入 `__subpath__/`（按 `stack.yml` `default_path` 决定落点）→ 去业务化（占位名 / 中性注释 / 泛化示例）→ 模板自检跑通（install/lint/typecheck/build 全绿当 happy-path smoke）。这套步骤已在 python-uv、react-vite 两次走通，值得在 `docs/11/SCHEMA.md` 或一份 contributor 指南里固化，避免下次加 stack（如某后端语言）重新摸索。**去向**：本仓为 claude-code-global，按自指守卫走**本地 `/backlog`**（issue 进 BACKLOG），不向外 file；优先级 P2，非紧急。
