# DEVTREE 表格免 prettier 对齐

## 背景

每次 `/devtree` 刷新 `docs/DEVTREE.md` 后，git diff 都特别大——即使只新增一行或改一个格子，整张表都被标记为改动。

排查确认根因：`hooks/fix-after-edit.sh` 的 PostToolUse hook 对每个被编辑的 `*.md` 跑 `prettier --write`。Prettier 格式化 GFM 表格时会把**每一列的所有单元格用空格补齐到该列最宽单元格的宽度**（列对齐）。所以只要某格内容长度一变，整列都要重新补空格 → 几十行全部标记为改动。

这是 Prettier 的 opinionated 行为，**没有任何配置选项能关掉表格列对齐**（实测 prettier 3.8.3，Markdown 只有 `proseWrap` 等旋钮）。当前 `.prettierrc` 也只有 `proseWrap: preserve`。

对用户而言这个对齐**零价值**：DEVTREE 是 `/devtree` skill 机器生成、通过 VSCode preview 可视化阅读的，裸 Markdown 表格本来就难读，对齐补空格只制造 diff 噪音、不带来任何可读性收益。渲染结果两种写法完全相同（无损），底层字节差别巨大。

## 需求

让 DEVTREE.md 的表格 diff 只反映真实内容变化。**范围限定：只豁免 DEVTREE，不影响其他手写 Markdown 文档**（rules/、SKILL.md、docs 正文等仍保留 prettier 对齐——那些是人手写、极少改、在终端/GitHub 裸看时对齐反而更清楚，重排代价罕见）。

## 已确认的方案（用户拍板：只豁免 DEVTREE）

三处改动，缺一不可：

1. **本仓库根 `.prettierignore`** 加 `**/DEVTREE.md`：让 hook 里的 `prettier --write` 跳过它。已实测：即使 hook 传的是**绝对路径**、文件在 `docs/` 子目录，Prettier 也会尊重 `.prettierignore` 并零改动跳过（exit=0），故 hook 本身不用动。

2. **模板 `templates/_common/__root__/.prettierignore`** 同步加同款规则：新项目 `bootstrap` / 老项目 `sync-project-config` 自动带上，效果覆盖所有下游项目。

3. **`/devtree` skill（`skills/devtree/SKILL.md`）改成生成紧凑单空格表格**：把 SKILL.md 里的示例表格和相关约定从「对齐补空格」改成「单空格 `| a | b |`」。否则即便 prettier 不再对齐，AI 重建区块时仍会手动去对齐、产生 ripple diff——两者必须一起改才彻底根治。

## 约束

- 只碰 DEVTREE 相关，不动其他 markdown 的 prettier 行为。
- 属跨项目全局配置改动（改全局 skill + 共享模板），影响所有下游项目——按四步开发模式走完，`/finish` 收尾。

## 验收

- 本仓库 & 新 bootstrap 项目根都有 `.prettierignore` 含 `**/DEVTREE.md`。
- 对 DEVTREE.md 跑 hook（或手动 `prettier --write docs/DEVTREE.md`）不改动文件。
- `/devtree` skill 文档里的表格示例是紧凑单空格形态。
- 模拟「DEVTREE 表格新增一行」场景，diff 只有新增行、不波及旧行。
