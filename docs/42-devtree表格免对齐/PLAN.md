# PLAN：DEVTREE 表格免 prettier 对齐

## 根因回顾（已实测确认）

- `hooks/fix-after-edit.sh` 的 PostToolUse hook 对每个被编辑 `*.md` 跑 `prettier --write`。
- Prettier（3.8.3）格式化 GFM 表格时把每列补空格对齐到该列最宽单元格；内容一变整列重排 → diff 爆炸。
- Prettier **无任何选项**能关表格对齐（Markdown 仅 `proseWrap` 等旋钮）。唯一出路：让 Prettier **别碰** DEVTREE.md。
- 实测：`.prettierignore` 里 `**/DEVTREE.md` 对 hook 传入的**绝对路径 + 子目录**文件生效，Prettier 零改动跳过（exit=0）。故 hook 本身不动。

## 关键设计

### 决策 1：范围只豁免 DEVTREE（用户拍板）

其他手写 md（rules/、SKILL.md、docs 正文）保留 prettier 对齐——人手写、极少改、终端/GitHub 裸看时对齐更清楚，重排代价罕见。只 DEVTREE 是机器生成 + preview 阅读，对齐纯噪音。

### 决策 2：SKILL.md 的载荷是「散文规则」，不是改示例表

**关键洞察**：`skills/devtree/SKILL.md` 自身是 `.md`、**不在**豁免名单里。我在其中写的任何紧凑表格，会被 hook 的 prettier 在我 Edit 后**立刻重新对齐**——committed 结果必然是对齐的。所以「把 SKILL.md 里的示例表改成紧凑」是徒劳的 no-op。

真正决定 `/devtree` 输出空格形态的是 SKILL.md 里的**书面指令**。因此：

- 在「输出格式模板」段加一条明确规则：生成到 DEVTREE.md 的表格用**紧凑单空格** `| a | b |`，绝不对齐补空格；给出 WHY（DEVTREE.md 已被 prettier 豁免 + 对齐制造 diff 噪音）。
- 在示例表附近加一句括注：下方示例经 prettier 对齐仅供看**结构**，实际输出用紧凑单空格。
- 示例表本身**不改**（改了也会被 prettier 打回，徒增 churn）。

## 落地改动（3 处文件）

1. **新增 `/.prettierignore`**（本仓库根）：

   ```
   # DEVTREE.md 由 /devtree 机器生成、经 preview 阅读，裸表格无需对齐。
   # Prettier 补空格对齐表格 → 内容一变整列重排、diff 爆炸，故豁免。
   **/DEVTREE.md
   ```

2. **新增 `templates/_common/__root__/.prettierignore`**：内容同上。跟随同目录既有 `.prettierrc`（plain 文件、straight-copy）的先例，`bootstrap` / `sync-project-config` 自动落到下游项目根，覆盖所有下游。

3. **改 `skills/devtree/SKILL.md`**：在「输出格式模板」段（§152 附近）插入紧凑表格规则 + 示例括注（如上「决策 2」）。

## 测试与验收

本仓库是 bash/config 仓，无单测框架，验收走脚本化手工验证：

- [ ] `prettier --write docs/DEVTREE.md` 后 `git status` 显示 DEVTREE.md 未改动（被豁免）。
- [ ] 对一个非 DEVTREE 的 md（如某 SUMMARY）跑 prettier 仍会格式化（证明只豁免了 DEVTREE、没误伤全局）。
- [ ] 模拟「节点索引新增一行」：紧凑表格下 diff 只含新增行、不波及旧行（对照对齐表格会整列重排）。
- [ ] SKILL.md 里能读到明确的「输出紧凑单空格表格」规则。

## 自然验证 / 收尾

`/finish` 收尾会跑 `/devtree` 把本轮（round 42）加入节点索引并**从零重建**——按新规则应产出紧凑单空格的节点索引表，即为端到端验证。本仓库现存 DEVTREE.md 的历史对齐表格由该次重建自然迁移为紧凑，无需手动批量改写。

## 局限性 / TODO

- 下游项目若已自带 `.prettierignore`，straight-copy 会覆盖它（与既有 `.prettierrc` 同款行为，非本轮引入）。当前跟随先例，不为此单独引入 merge 逻辑；如未来出现真实冲突再议。
- 已合入历史项目的 DEVTREE.md 仍是对齐表格，直到各自下次 `/devtree` 重建才转紧凑（自然迁移，可接受）。
