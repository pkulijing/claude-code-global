# 总结：新增 /bootstrap skill 处理空项目初始化

## 背景

现有 `/start` skill 假设项目已有基础文档骨架（`CLAUDE.md` / `BACKLOG.md` / `DEVTREE.md` / `README.md`），直接进入「开新一轮开发项」流程。但全新空项目首轮开发时这些骨架都不存在，单跑 `/start` 会缺东西。

需要在 `/start` 里兜底建骨架，还是新增一个一次性脚手架 skill？讨论后选择后者，避免热路径 skill（`/start` 每轮跑）夹带一次性分支（bootstrap 整个项目只跑一次）的逻辑膨胀。

## 实现方案

### 关键设计

1. **职责拆分**：`/bootstrap` 负责「立项目骨架」（一次性），`/start` 负责「开新一轮开发」（高频）。两者通过 `/start` 的前置检查耦合 —— 检测到空项目就提示用户先跑 `/bootstrap`，而不是自动兜底。
2. **DEVTREE 骨架的单一事实来源**：本来打算让 bootstrap 自带一份 DEVTREE 骨架模板，但会与 `/devtree` 双向同步。最终改为给 `/devtree` 加「冷启动」分支：当文件不存在或 Epic 结构为空时落骨架。bootstrap 只调用 `/devtree`，不重复模板。
3. **不创建 BACKLOG.md**：`/backlog` 已经处理「文件不存在时初始化」，bootstrap 不重复造轮子，让用户首次需要登记开发项时自然触发。
4. **不调用内置 `/init`**：`/init` 依赖代码扫描，对空项目无意义，等代码长起来再让用户手动跑。
5. **`/start` 前置检查的判定条件**：用 `CLAUDE.md` + `DEVTREE.md` **双缺**判定空项目，比单测一项更稳，避免误判半初始化项目。

### 开发内容概括

- 新增 `skills/bootstrap/SKILL.md`：前置检查（三条「已存在则停」）→ 一次性收集（项目名 / 描述 / 是否有首个 backlog 想法）→ 写 README.md → 写 CLAUDE.md → 调用 `/devtree` → 收尾反馈
- 修改 `skills/devtree/SKILL.md`：核心原则节加「例外：冷启动」一句，执行步骤前插入「第零步：冷启动判定与骨架落盘」
- 修改 `skills/start/SKILL.md`：第 9 行加前置检查段，明确「`/start` 只负责开新一轮开发，不负责项目首次初始化」
- 跑 `install.sh` 让新 skill 软链接到 `~/.claude/skills/bootstrap`

### 额外产物

无（skill 是 Markdown 提示词，行为靠对话验证；本轮未涉及测试用例或样例文件）。

## 局限性

- **冷启动占位文案的引用稳定性**：`/devtree` 冷启动写入的 Epic 结构占位中包含 `~/.claude/skills/devtree/SKILL.md` 的硬编码路径，假设用户用 `install.sh` 部署。如未来部署方式变化（如改成 plugin 包），这条引用会失效。
- **`/start` 前置提示的覆盖面**：依赖用户走 `/start` 流程才能看到「请先跑 /bootstrap」提示。若用户从一开始就手写文档绕开 skill 体系，bootstrap 这条入口感知不到。可接受 —— bootstrap 本来就是给「按 Constitution 走流程」的用户准备的。
- **冷启动后用户仍需手填 Epic 结构再跑一次 `/devtree`**：冷启动产物是占位骨架，渲染图与索引仍是占位，用户加了首批叶 Epic 后必须再跑一次 `/devtree` 才能看到正式渲染。这是 Epic 结构作者主权的必然代价，不是 bug。

## 后续 TODO

- **`/finish` 可考虑加一步「提醒用户更新 Epic 结构」**：每轮 `/finish` 都需要作者把新轮次塞进 Epic 结构后 `/devtree` 才会包含它。当前 skill 没有显式提醒，容易漏。可在 `/finish` 步骤 3 之前加一行提示「确认 Epic 结构已包含本轮编号，否则可视化不会更新」。
- **bootstrap 未来可扩展**：如 `git init` 引导、`.gitignore` 模板、`.env.example` 占位等。当前版本聚焦三个文档文件，扩展空间留给后续轮次按需加。
- **`/start` 前置检查可演进为通用「环境就绪检查」**：当前只查 `CLAUDE.md` + `DEVTREE.md`，未来若再多骨架文件（如 `.editorconfig`、CI 配置等）需要前置确认，可把检查抽成共享段。
