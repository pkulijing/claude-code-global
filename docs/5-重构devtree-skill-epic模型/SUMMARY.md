# 开发总结：重构 /devtree skill — Epic 模型

## 开发项背景

希望解决的问题：原版 `/devtree` 强制在开发项之间建立父子边，导致追求同一宏观目标的多个并行开发项被错误地排成线性链条，缺乏"收束感"。例如 whisper-input 中针对 Linux 安装体验的 3、9、10、12 四轮迭代，用旧方案只能串成一条链，无法表达它们属于同一个目标的并列尝试。

## 实现方案

### 关键设计

- **Epic 层**：在项目根目标与开发项之间引入 Epic（目标层），形成「根目标 → 非叶 Epic → 叶 Epic → 开发项」的四层树。叶 Epic 是实际承载开发项的容器，同一叶 Epic 内的开发项互相并列，不画边。
- **职责分离**：作者手动维护「Epic 结构」区块（Markdown 标题树），AI 仅重新生成「可视化」和「节点索引」两个区块，严格不修改作者区块。
- **可视化方案**：
  - 非叶 Epic → 普通 Mermaid 节点 + `-->` 边构成真正的有根树主干
  - 叶 Epic → `subgraph` 卡片，内部 `direction TB`，开发项用 `~~~` 不可见链接强制纵向堆叠
  - Epic 节点统一用 `classDef epic` 配色区分，`font-weight:bold` 突出标题，`%%{init}%%` 的 `rankSpacing: 25` 压缩卡片内间距
- **状态图标**：叶 Epic 标题前加 ✅/🔄/❌ 表达完成状态，一眼可见进度

### 开发内容概括

- 完全重写 `skills/devtree/SKILL.md`：引入 Epic 层概念，重新定义三区块文件结构、执行四步骤、Mermaid 格式规范（subgraph 卡片 + 不可见链接 + init 配置）
- 将 `whisper-input/docs/DEVTREE.md` 与 `EPICS.md` 合并为新格式单文件：Epic 结构区块 + 新 Mermaid 可视化 + 节点索引表
- 将 `claude-code-global/docs/DEVTREE.md` 同步说明（当前仍为旧格式，待后续更新）

### 额外产物

无

## 局限性

- `~~~ ` 不可见链接在部分旧版 Mermaid 渲染器中可能不被支持，降级时节点会水平排列而非纵向堆叠
- `rankSpacing` 是全局参数，无法单独控制卡片内间距与卡片间间距，只能折中取值
- Mermaid 静态 SVG 不支持节点折叠，对节点数量多的项目图会较大

## 后续 TODO

- 将 `claude-code-global/docs/DEVTREE.md` 从旧父子格式迁移到新 Epic 格式
- 删除已合并的 `whisper-input/docs/EPICS.md`（内容已并入 DEVTREE.md，文件冗余）
- 若未来项目开发项数量继续增长，可探索按功能域分页或用非 Mermaid 方案（如 D3.js）实现可交互折叠树
