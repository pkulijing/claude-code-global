# SUMMARY：DEVTREE 表格免 prettier 对齐

## 开发项背景

**问题表现**：每次 `/devtree` 刷新 `docs/DEVTREE.md` 后，git diff 都特别大——即使只新增一行或改一个格子，整张 Markdown 表都被标记为改动。

**根因**：`hooks/fix-after-edit.sh` 的 PostToolUse hook 对每个被编辑 `*.md` 跑 `prettier --write`。Prettier（3.8.3）格式化 GFM 表格时把每列的所有单元格补空格对齐到该列最宽单元格；只要某格内容长度一变，整列都要重排 → diff 爆炸。而 DEVTREE.md 是 `/devtree` skill 机器生成、通过 VSCode preview 阅读的，裸表格对齐对用户零价值、纯噪音。

**为什么不能靠配置关掉**：实测 prettier 无任何选项能关表格对齐（Markdown 仅 `proseWrap` 等旋钮），`.prettierrc` 也只有 `proseWrap: preserve`。唯一出路是让 prettier **别碰** DEVTREE.md。

## 实现方案

### 关键设计

1. **`.prettierignore` 豁免 DEVTREE，而非改 hook**。实测确认：`.prettierignore` 里 `**/DEVTREE.md` 对 hook 传入的**绝对路径 + 子目录**文件也生效（prettier 尊重 ignore、零改动跳过、exit=0），故 hook 本身不动、blast radius 最小。范围只豁免 DEVTREE：其他手写 md（rules/、SKILL.md、docs 正文）保留对齐——那些人手写、极少改、终端/GitHub 裸看时对齐更清楚。

2. **SKILL.md 的载荷是「散文规则」，不是改示例表**。关键洞察：`skills/devtree/SKILL.md` 自身是 `.md`、**不在**豁免名单，我在其中写的紧凑示例会被 hook 的 prettier 在 Edit 后立刻打回对齐——committed 结果必然对齐，改示例是徒劳 no-op。真正决定 `/devtree` 输出空格形态的是 SKILL.md 里的**书面指令**。所以加的是明确规则 + 示例括注（说明示例的对齐是 prettier 所致、仅供看结构），示例表本身不动。

### 开发内容概括

三处改动：

1. **新增 `/.prettierignore`**（本仓库根）：`**/DEVTREE.md` + WHY 注释。
2. **新增 `templates/_common/__root__/.prettierignore`**：内容同上，跟随同目录既有 `.prettierrc`（plain 文件 straight-copy）先例，`bootstrap` / `sync-project-config` 自动落下游项目根，覆盖所有下游。
3. **改 `skills/devtree/SKILL.md`**：「输出格式模板」段加「表格一律用紧凑单空格」规则（含 WHY）+ 示例括注；第四步（生成节点索引）加一句指针。

### 额外产物

- 脚本化验收（4 条）现场跑通，其中最有说服力的量化对比：同一「新增一行」改动，**紧凑表格 diff = 1 行，对齐表格 diff = 9 行**。

## 局限性

- 下游项目若已自带 `.prettierignore`，straight-copy 会覆盖它（与既有 `.prettierrc` 同款行为，非本轮引入）。当前跟随先例，不为此单独引入 merge 逻辑。
- 已合入历史项目的 DEVTREE.md 仍是对齐表格，直到各自下次 `/devtree` 重建才转紧凑（自然迁移，可接受）。本仓库自身的 DEVTREE.md 由本轮 `/finish` 的 `/devtree` 重建即转紧凑。

## 后续 TODO

- 若未来出现「下游项目自带 `.prettierignore` 被模板覆盖」的真实冲突，再考虑给根级 ignore 文件引入 append/merge 语义（类似 `.vscode/*.fragment` 的合并思路）。目前无实例、不预先复杂化。

## 可沉淀项

本轮改动本身就发生在 claude-code-global（全局资产仓）内，三处改动已直接落进全局 skill + 共享模板，无需再向别处沉淀。

一条**通用经验**值得记一笔（去向：本仓库内已体现，无需额外提 issue）：**「让机器生成、靠 preview 阅读的 Markdown 免除 prettier 表格对齐」是一个可复用范式**——判据是「文件是工具生成的 + 人不看裸文本 + 内容频繁重建」，手段是 `.prettierignore` 豁免 + 生成端约定紧凑单空格。DEVTREE 是首个实例；未来若有同类机器生成 md（如自动生成的索引/清单）可套用同一手法。
