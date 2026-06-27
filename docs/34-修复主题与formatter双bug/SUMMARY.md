# SUMMARY — 修复主题切换与 formatter 删 import 两个 bug

本轮一次性收口两个跨项目沉淀（来自 teleop-operator 实战）的独立小 bug。二者无耦合，仅因都属「小修」合并到同一轮 worktree。

---

## Bug 1（#21）：react-vite 模板主题切换在 system 模式下错乱

### 背景

- **表现**：`theme === "system"` 且 OS 为浅色时，页面被 provider 正确解析成浅色，但切换按钮 JS 仍按 `isDark = theme === "dark" || theme === "system"` 把 system 当深色 → 显月亮图标、点击 `setTheme(isDark ? "light" : "dark")` 算成 `setTheme("light")`，可视无变化，按钮像"坏了"。
- **影响**：任何用此模板、开 system 模式的项目；另 OS 明暗实时切换页面不跟随（要刷新）。

### 关键设计

根因是消费者直接读三态 `theme` 推断明暗，而非读「system 解析后的实际生效值」。采用 next-themes 同款 `resolvedTheme` 模式：Provider 把解析结果固化为 `resolvedTheme: "dark" | "light"` 并经 context 暴露，消费者一律读它。

### 开发内容

- `templates/react-vite/__subpath__/src/components/theme-provider.tsx`：
  - `ThemeProviderState` 加 `resolvedTheme` 字段；新增 `resolvedTheme` state。
  - effect 收敛为单一 `apply()`：算 resolved → 改 root class → `setResolvedTheme`；`theme === "system"` 时订阅 `matchMedia("(prefers-color-scheme: dark)")` 的 `change`，cleanup 解绑 → OS 明暗实时跟随、切走 system 时正确解绑。
  - context value 暴露 `{ theme, resolvedTheme, setTheme }`。
- `templates/react-vite/__subpath__/src/components/mode-toggle.tsx`：`isDark` 改读 `resolvedTheme === "dark"`，JSDoc 同步更正。

保留 system 三态、不砍功能（模板面向通用）。图标切换本就靠 tailwind `dark:` 变体，JSX 未动。

---

## Bug 2（#22）：PostToolUse formatter 在分步 Edit 间删 import

### 背景

- **表现**：TDD「先加 import、usage 在后续 Edit 补」时，PostToolUse 的 `ruff check --fix` 在两次 Edit 之间跑，把尚无 usage 的 import 当 F401 删掉；下一步补 usage 后 import 已没 → 下次跑测 `F821 Undefined name`。
- **影响**：任何「ruff 挂 PostToolUse + 分步 Edit」的 Python 项目，单轮可反复踩中，是稳定可复现的工序摩擦。

### 关键设计

方向与人类确认：走 **hook 改造**（不加 doc 纪律）。`hooks/fix-after-edit.sh` 的 `ruff check --fix` 追加 `--unfixable F401` —— F401 仍被**报告**（不漏检），但 PostToolUse 阶段**不自动删**，残余 unused import 留给 `/commit` 统一抓取（与 hook 现有注释精神一致）。其余可自动修的 lint（import 排序、引号等）与 `ruff format` 均不受影响。

### 开发内容

- `hooks/fix-after-edit.sh`：`*.py` 分支 `ruff check --fix` → `ruff check --fix --unfixable F401`，附 WHY 注释。
- hook 脚本本体是软链，改内容无需重装，下次触发即生效。

### 额外产物

- 验证记录：临时 `import os`（无 usage）跑 `ruff check --fix --unfixable F401` 确认 import 保留且 F401 仍报告；对照不带 `--unfixable` 确认旧行为会删空。（验证用临时文件已清理。）

---

## 局限性

- **#21**：模板内无前端测试脚手架/node_modules，未能本地跑 Vitest 验证，靠类型自洽 + 逻辑审阅 + ruff 同类验证保障；真实回归依赖下游消费项目。
- **#22**：仅治 ruff(Python) 侧。前端 biome 的 import 删除走手动 `npm run lint:fix`（不挂 PostToolUse），不在此问题范围；若未来把 biome 挂上 PostToolUse 需同等处理。`--unfixable F401` 只豁免 unused-import，其它会删符号的规则（如 F811 redefinition）仍可能在极端分步写法下误伤，但远低频，暂不处理。

## 后续 TODO

- 观察 `--unfixable F401` 上线后分步 Edit 摩擦是否归零；若仍偶发其它规则误删，再评估扩展 unfixable 列表。
- （可选）若后续把前端 biome 纳入 PostToolUse formatter，需为其配等价的「不删 unused import」档。

## 可沉淀项

暂无。本轮两项修复本身就是对 claude-code-global 自有资产（`react-vite` 模板、`fix-after-edit.sh` hook）的直接改进，无需再向外抽象——修复落地即沉淀。
