# PROMPT — 修复主题切换与 formatter 删 import 两个 bug

本轮一次性收口两个跨项目沉淀的小 bug，二者独立、互不耦合，仅因都属「小修」而合并到同一轮 worktree。

---

## Bug 1：react-vite 模板主题切换在 system 模式下错乱

> 来自 [#21 react-vite 模板：主题切换在 system 模式下显示/行为错乱（缺 resolvedTheme）](https://github.com/pkulijing/claude-code-global/issues/21)
> Labels: `type:bug` `priority:P2` `area:template`

### 背景 / 现象

模板的 `mode-toggle.tsx` 用三态 `theme`（`dark`/`light`/`system`）直接算 `isDark`：

```ts
const isDark = theme === "dark" || theme === "system"; // ← 把 system 一律当深色
```

当 `theme === "system"` 且**操作系统是浅色**时：

- `theme-provider` 其实正确地把 system 解析成 light、给 root 加了 `.light`，页面**是浅色**；
- 但按钮 JS 以为 `isDark = true` → 显示**月亮图标**、点击逻辑 `setTheme(isDark ? "light" : "dark")` 用了错的 `isDark`；
- 点一下变成 `setTheme("light")`，可视上无变化 → 按钮像"坏了/没适配深浅模式"。

另外 `theme-provider` 的 effect **没监听 `prefers-color-scheme` 的 change 事件**，system 模式下 OS 明暗实时切换页面不跟随（要刷新）。

### 通用解法（next-themes 同款 `resolvedTheme` 模式）

让 Provider 暴露一个 **`resolvedTheme: "dark" | "light"`**（已把 system 解析后的实际生效值），消费者一律读它、不读三态 `theme`；并订阅 matchMedia change 让 system 实时跟随。

### 落点

- `templates/react-vite/__subpath__/src/components/theme-provider.tsx`：加 `resolvedTheme` 状态 + matchMedia change 监听 + context 暴露。
- `templates/react-vite/__subpath__/src/components/mode-toggle.tsx`：`isDark` 改读 `resolvedTheme`。

保留 system 三态（模板面向通用），按 resolvedTheme 正解，**不砍功能**。

---

## Bug 2：PostToolUse formatter 在分步 Edit 间删掉「当前未用」import

> 来自 [#22 PostToolUse formatter 在分步 Edit 间删掉「当前未用」import，导致下次跑测 F821](https://github.com/pkulijing/claude-code-global/issues/22)
> Labels: `type:feat` `priority:P2` `area:hook`

### 背景 / 现象

TDD「先改 import 行、usage 在后续 Edit 里补」的写法下，**PostToolUse 格式化器（`hooks/fix-after-edit.sh` 里的 `ruff check --fix`）在两次 Edit 之间跑**，会把「此刻还没有 usage」的 import 当成 unused（F401）删掉；等下一个 Edit 把 usage 写进去后，import 已经没了 → 下次跑测 `F821 Undefined name`。单轮可反复踩中 4+ 次，是稳定可复现的工序摩擦。

### 落点方向（issue 留给 maintainer 定夺）

issue 给了两条，可择一或并行：

1. **写法纪律（doc/约定）**：固化「import + usage 同一次 Edit 同进，绝不留中间态跨越 formatter」。
2. **hook 侧缓解（更稳，本 issue 标 `area:hook`）**：让 PostToolUse formatter 不在分步编辑中途吃掉 import。

本轮方向在 PLAN.md 中给出推荐并请人类确认。

---

## 约束

- 两个 bug 改动独立，分别可单独 review；commit 时在描述写 `Closes #21`、`Closes #22`。
- 前端改动遵循 `rules/frontend.md`；hook 改动遵循全局宪法。
- 模板文件改完无需重装（目录级软链即时生效）；hook **脚本本体是软链，改内容无需重装**。
