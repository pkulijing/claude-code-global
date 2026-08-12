# 前端开发规则

> 本文档由 `claude-code-global` 仓库的 `playbooks/frontend.md` 提供，经 `install.sh` 双轨软链到 `~/.claude/playbooks/frontend.md`（CC 端）与 `~/.codex/playbooks/frontend.md`（Codex 端）。修改请回到 `claude-code-global` 仓库，不要直接编辑软链目标。
>
> **触发条件**：Coding Agent 在本轮任务涉及前端代码 / web UI、React / Vite / TypeScript 前端工程，或 Biome / tailwind / shadcn 等前端栈选型判断时，**必须先把本文件读入上下文**，再开始动手。

前端是与后端**正交**的独立维度：一个仓库可以只有前端、只有后端，或前后端并存。本规则只管前端这一维，与后端用什么语言（Python / Go / C++…）无关。配套的开箱即用脚手架是 `react-vite` stack 模板（`bootstrap` / `sync-project-config` 消费），落在项目的 `frontend/` 子目录。

## 1. 环境与工具

- 用 **npm** 管理依赖，源固定走 **npmmirror**（原淘宝源），在 `frontend/.npmrc` 写 `registry=https://registry.npmmirror.com`。类比 Python 侧固化清华源——团队一致、国内加速。除非特殊要求，不改用其他源。
- **Biome** 作「前端的 ruff」：`npm run lint`（= `biome check .`）做检查，`npm run lint:fix`（= `biome check --write .`）做格式化 + 修复。配置基线：`recommended` preset + 100 列 + 双引号 + 2 空格缩进，集中在 `biome.json`。
  - **`biome.json` 必须是纯 JSON，不要加任何注释或 `"//"` 注释键**。Biome 对配置键做严格校验：`"//"` 这种键会直接报 `unknown key` 让 `biome check` 失败；而 `//` 行注释虽不报错，却会让 Biome 静默回落到默认（tab 缩进）配置，使你的 space/100 列设置全部失效、产出海量伪 error。要解释某段配置，把说明写到本规则或 PR 里，别写进 `biome.json`。
- **TypeScript strict**：`tsconfig.json` 开 `strict` + `noUnusedLocals` + `noUnusedParameters` + `noFallthroughCasesInSwitch`。`npm run typecheck`（= `tsc --noEmit`）做类型门禁，`npm run build`（= `tsc --noEmit && vite build`）构建前先过类型。
- 版本基线：**React 19 + Vite 6 + TypeScript 5.7**。模板 `package.json` 把依赖版本写死以保证可复现，会随时间过时，需偶尔人工 bump。
- **worktree 内跑门禁先备齐 `node_modules`**：`/start` 默认在独立 git worktree 内开一轮，而 worktree 只 checkout tracked 文件——`frontend/node_modules` 被 gitignore、**不随 worktree 创建而来**。于是在 worktree 里跑前端门禁（`tsc` / `biome` / `vite build`）会因缺 `node_modules`（typescript / biome / vite 全找不到）直接炸。凡 `react-vite` stack + worktree 工作流并存即触发，与具体项目无关。两条路子：① 从主 checkout 软链一份过来跑完即删（`ln -s <主checkout>/.../frontend/node_modules <worktree>/.../frontend/node_modules`）；② 在 worktree 内 `npm install`（npmmirror、增量幂等）。**警告**：软链法跑完务必 `rm` 且**勿 commit**——`node_modules/` 带尾斜杠的 gitignore 模式只匹配目录、不匹配软链，软链会以 untracked 身份冒进 `git status`。这是「worktree 只 checkout tracked 文件 → gitignored 运行时依赖（`node_modules` / `.env.local` / build 产物…）全缺」这个**通用类别**的前端实例，通用应对见 `/start` skill 的「worktree 创建」小节。

## 2. 项目骨架

前端落 `frontend/` 子目录，标准 Vite + React + TS 布局：

- `frontend/src/` 放源码；`@/` alias 指向 `src/`，**必须在两处同时声明**——`vite.config.ts` 的 `resolve.alias` 管运行时 / 构建，`tsconfig.json` 的 `compilerOptions.paths` 管类型 / IDE 跳转；少配一处就会一边能跑一边报错。
- `frontend/src/index.css` 是 tailwind v4 的唯一入口，承载 `@import "tailwindcss"` + 明暗主题的 oklch CSS 变量 + `@theme inline` 映射。
- `frontend/src/lib/utils.ts` 放 `cn` helper（shadcn 组件标配）；`frontend/src/components/ui/` 放 shadcn 组件；`frontend/src/components/` 放自有组件。
- 入口链：`index.html` → `src/main.tsx`（`createRoot` 渲染 `<App />`）→ `src/App.tsx`。
- 构建产物 `frontend/dist/`，供后端静态托管（如 FastAPI `StaticFiles` / nginx）。

## 3. 选型与约定

### 3.1 tailwind v4 CSS-first

用 `@tailwindcss/vite` 插件接入，**没有 `tailwind.config.js`**。v4 把配置从 JS 配置文件挪进 CSS：主题变量、色板、radius 等都在 `index.css` 的 `@theme` / `:root` / `.dark` 里声明。不要再去找或新建 `tailwind.config.js`。

### 3.2 shadcn-ui

- 风格固定 **new-york** + baseColor **neutral**，配置在 `components.json`（`cssVariables: true`、`css: src/index.css`、`aliases` 指向 `@/`）。
- 新增组件用 **`npx shadcn@latest add <name>`**，由 CLI 按 `components.json` 生成到 `src/components/ui/`。**不手写、不从别处整段拷贝** shadcn 组件——让 CLI 保证与 `components.json` 一致。
- 组件 className 一律走 `cn(...)`（`clsx` 条件拼接 + `tailwind-merge` 消解冲突类）。

### 3.3 暗色默认 + 可切

- `theme-provider.tsx` 提供 `ThemeProvider` + `useTheme`：**默认深色**，可切 light / system，写 `localStorage` 持久化，靠根元素 `.dark` class 驱动 tailwind。
- `mode-toggle.tsx` 是切换按钮（日 / 月图标，`lucide-react`）。`ModeToggle` 依赖 `useTheme`，所以必须置于 `ThemeProvider` 子树内。

## 4. 风格细则

### 4.1 底层 / WebGL 目录用 Biome overrides 放宽

DOM / WebGL / canvas API 大量返回可空类型、且常在非顶层位置组织逻辑，这类目录里惯用非空断言 `!` 与非顶层 Hook 是合理的。为它们在 `biome.json` 的 `overrides` 里按目录关掉 `style.noNonNullAssertion` 与 `correctness.useHookAtTopLevel`，而不是全局关、也不是逐行 `// biome-ignore`。模板已留一个 `src/gl/**` 的示例 override，**按你实际的底层目录名改 `includes`**（如 `src/video/**`、`src/canvas/**`）；没有这类目录就删掉整个 override 条目。

### 4.2 前后端分离的 dev proxy

前后端分离开发时，`vite.config.ts` 的 `server.proxy` 把 `/api`、`/ws` 代理到后端服务（改 `BACKEND` 常量为实际监听地址），让前端 dev server 与后端同源调试；生产环境前端不再代理，由后端静态托管 `vite build` 出的 `dist`。纯前端项目（无后端）直接删掉 `server.proxy` 段。

### 4.3 import 组织交给 Biome

Biome 的 assist（`organizeImports`）负责 import 排序与分组（external 一组、`@/` 一组，组间空行）。项目根 `.vscode/settings.json`（`[typescript]` 等语言块里的 `source.organizeImports.biome`）已配保存即整；手写时按同样分组，最终以 `npm run lint` 为准。

> 编辑器配置（`.vscode/`）的落点：模板把 `extensions.json` / `settings.json` 以 `.vscode/*.json.fragment` 形式从各 stack **合并进项目根** `.vscode/`（不落 `frontend/.vscode/`）。原因：VS Code 单根工作区只读「打开的工作区根」的 `.vscode/`，子目录的推荐 / 设置在「打开仓库根」这一惯例下不生效；落根后打开仓库根即提示装 Biome 插件、即享 formatOnSave。settings 全部走语言作用域键（`[typescript]` / `[json]` / …），故与后端 `python-uv` 的 `[python]` / `[markdown]` 在同一份根 `settings.json` 里 union 共存、互不污染。代价：单独打开 `frontend/` 子目录开发会丢这些设置——本仓库惯例是打开仓库根，故不在 `frontend/` 留副本以免双份漂移。

### 4.4 label 关联自定义输入组件用 `htmlFor` + `id`

给表单控件加 `<label>` 时，**别**用 `<label>文字<Input/></label>` 包裹结构指望 Biome 推断关联。Biome 的 a11y 规则 `a11y/noLabelWithoutControl` 只认它**静态能识别为表单控件**的元素：原生 `<select>` / `<input>` 放行，而 shadcn 的 `Input` / `Textarea` 等是自定义组件，Biome 看不出其内部渲染原生 `<input>`，于是把 label 判成「没有关联控件」、`lint:fix` 也修不掉。

修法：显式关联——`<label htmlFor="x">` + `<Input id="x" />` 匹配 id 即过。这是自包含、a11y-correct 的解，优于在 `biome.json` 给该规则配 `inputComponents`（后者要改全局配置）。

### 4.5 照抄持有外部资源的组件时，setup 与 teardown 必须成对核对

凡组件持有**外部资源**——WebGL context、canvas、`AudioContext`、`WebSocket` 等长连接、`ResizeObserver` / `IntersectionObserver`、`setInterval` / `setTimeout`——照抄它的初始化就必须**逐行核对它的 cleanup**，不能只抄前半。这类组件的正确性有一半在 cleanup 里，而 cleanup 通常在文件末尾、离 setup 很远；照抄的人眼睛停在「建场景」那一段，没往下读到配对的「拆场景」。

WebGL 要点名 `renderer.forceContextLoss()`：

```js
renderer.dispose();
renderer.forceContextLoss(); // 缺了它，底层 context 不会被真正放弃
```

`renderer.dispose()` 只释放 three.js 内部的 GL 资源，**不放弃底层 WebGL context**；漏了配套这一步，每次卸载泄漏一个。同理，卸载时要对场景内 mesh 的 geometry / material 逐个 dispose。

**失效不在肇事者身上报错**，这是它难查的根本原因：浏览器每页的 context 数有上限，攒满后被强制丢弃的是**最旧的那个**——也就是常驻的那个实时窗黑屏，而不是刚打开的新页面。现场只看到「主 3D 窗莫名黑了」，归因线索完全不指向肇事组件。这类「泄漏方与受害方分离」的 bug 事后排查代价极高，靠一条事前核对极便宜。

配套：异步加载（URDF / GLTF / 大资源）的完成回调里，`if (disposed)` 分支不能只 `return`，要把**已建好的对象树就地释放**——此时它既没进场景、ref 也还是 null，cleanup 根本看不到它。

判据：**条件挂载（切 tab 即卸）的组件比常驻组件更需要严格 cleanup**。常驻组件一辈子只挂载一次，泄漏不显；条件挂载的挂载 / 卸载次数与用户操作次数同阶，每次进出都泄漏一个，几分钟就能撞上限。React StrictMode 下首次挂载还必然多一次「挂了立刻卸」。

## 5. 测试

前端组件 / 纯逻辑的单测可用 Vitest + Testing Library，遵循全局宪法 TDD 章节（有清晰输入输出契约的逻辑先写测试）。`react-vite` 模板当前未预置测试脚手架，引入测试时把 Vitest 配置与 `test` 脚本一并补进 `frontend/`；编排型组件（拼装多个子组件做端到端流程的页面）至少补一条 happy-path 渲染冒烟。
