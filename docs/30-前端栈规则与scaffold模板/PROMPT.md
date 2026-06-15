> 来自 [#19 沉淀前端栈维度：rules/frontend.md + 前端 scaffold 模板（与后端正交）](https://github.com/pkulijing/claude-code-global/issues/19)
> Labels: `type:feat` `area:template` `priority:P2`

# 需求：沉淀「前端栈维度」（rules/frontend.md + 前端 scaffold 模板 + 正交组合机制）

## 来源

teleop-survey **round 11**「操作端去 Electron 化重构落地一期」（代码在共享仓 `~/Work/teleop-operator`，FastAPI daemon + React/TS 前端）。那一轮是团队**第一个 FastAPI + TS 项目**，把整套前端栈规范落地并经假件 + 真机双向验证。活样板：`~/Work/teleop-operator/frontend/`（lint/typecheck/build 全绿）。

## 为什么值得沉淀

- **重复性**：后续任何「带 web 前端」的项目（遥操控制台、数采看板、内部工具…）都会复用同一套前端选型与规范。
- **通用性**：与具体业务无关，纯工程栈约定。
- **现状缺口**：后端维度已有 `rules/python.md`（uv / ruff / src 布局 / OO 风格）+ bootstrap 落 src 骨架 + `templates/python-uv/`；**前端维度完全空白**。本轮边做边定规范，不沉淀下轮又得重定。

## 核心设计方向：前端 / 后端是**正交两维**（关键约束）

不要搞「FastAPI + 前端」这种**耦合模板** —— 否则后端一换语言（Python → C++ / Go）就要再造一份「前端 + 新后端」，组合爆炸。应把**前端**与**后端**作为两个独立维度，各有模板 / 规则，一个项目可自由组合（只后端 / 只前端 / 两者）；换后端维度时前端维度原样复用。

## 具体落点（三件）

### 1. `rules/frontend.md`（类比 `rules/python.md`，双轨软链到 `~/.claude/rules` + `~/.codex/rules`）

沉淀以下前端栈硬性约定：

- 包管理 npm + **npmmirror**（`.npmrc`）；
- **Biome** 作「前端的 ruff」（`biome check` / `--write`，recommended + 100 列 + 双引号）；
- **tailwind v4** CSS-first（`@tailwindcss/vite`，无 `tailwind.config.js`）；
- **shadcn-ui**（new-york / neutral，`components.json`，`cn` helper，新增组件方式）；
- 暗色默认 + 可切（theme-provider + mode-toggle）；
- 底层 / WebGL 层用 `overrides` 关 `noNonNullAssertion` / `useHookAtTopLevel`（DOM / WebGL 惯用 `!`）；
- 前后端分离时 vite dev `server.proxy` 把 `/api`·`/ws` 代理到后端 daemon，生产由后端静态托管 `dist`。

### 2. 前端 scaffold 模板（`templates/<frontend-stack>/` 新增）

React 19 + Vite 6 + TS(strict) + 上述 tailwind / shadcn / Biome / `.npmrc` / vite proxy + theme-provider / mode-toggle / Button 等基础件。形态需与现有 `python-uv` 模板的 `__root__` / `__subpath__` / fragment 约定保持一致。

### 3. 正交组合机制（bootstrap / sync-project-config）

把「前端维度」做成可叠加开关（与已有后端 src 布局正交）。一个仓可只后端、只前端、或前后端并存；后端维度换语言时前端维度不动。

## 现状机制约束（本轮需直面）

调研 `bootstrap` / `sync-project-config` 后确认：现状两个 skill 的模板消费机制**假设单一 stack**——

- bootstrap 让用户选**一个** stack，marker `stacks` 写 1 条；
- sync **硬断言** `len(stacks) <= 1`，多 stack 直接报错退出；
- marker schema（`.agent-template.yml`）**已预留**多 stack / monorepo 形态，但实现未走该分支；
- `__subpath__` 落点 `path` 现恒为 `.`。

因此「正交组合」不是加个开关那么轻，而是要把单 stack 假设升级为「多 stack 叠加」。本轮需确定改造深度。

## 本轮待决范围（计划阶段与人类对齐）

1. 前端 stack 目录命名（`react-vite` / `web-react` / …）。
2. scaffold 落地形态：哪些直接进模板、哪些靠 `npm create` + bootstrap 命令生成。
3. 正交组合机制的改造深度：本轮是否完整实现多 stack 叠加（含 path 灵活化），还是分轮推进。
