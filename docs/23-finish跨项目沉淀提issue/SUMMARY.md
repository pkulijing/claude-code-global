# Round 23 总结：/finish 跨项目反思可沉淀流程并提 issue

## 开发项背景

> 来自 [#6 /finish 收尾时主动识别「可沉淀项」并提醒用户](https://github.com/pkulijing/claude-code-global/issues/6)

每个开发轮里常冒出「值得复用」的经验（可加进模板的字段、可新增的全局 skill·hook、可写进宪法的约定），但这些经验散落在对话或 SUMMARY 的「局限性 / 后续 TODO」段里，靠人主动捡，容易错过抽象时机。

原始 issue #6 把这件事定位在 **claude-code-global 自身** `/finish` 时往 SUMMARY 写一段 + 打印提醒（方向 A）。发起人在开发前澄清，把范围放大为：在**任意项目** `/finish` 时反思可沉淀的重复性流程，并对跨项目资产类候选**直接向 claude-code-global 仓库提 issue**（跨仓库），这类 issue **不进任何 BACKLOG 索引**。

## 实现方案

### 关键设计

1. **propose → 逐条确认 → 再 file**：提 issue 是外部可见动作，不自动提交、不阻塞 commit；逐条决策，支持「先放一放」。
2. **候选硬上限 3 条**：按价值排序取 top 3，宁缺毋滥控制噪音（呼应 issue 的「容易啥都觉得能沉淀」风险点）。配合三条判定标准（跨项目通用 / 有具体落点 / ≥2 次模式）。
3. **两路去向**：跨项目资产（templates / 全局 skill·hook / GLOBAL_AGENTS.md）→ 跨仓库提到 claude-code-global；仅当前项目可复用 → 仅建议本地 `/backlog`，不替用户 file。
4. **跨仓库目标动态派生**：从 `~/.claude/global-repo`（`install.sh` 软链到本仓库）的 remote 派生 slug + platform，不硬编码，多设备/改名都成立。验证覆盖 ssh/https × github/gitlab（含 gitlab 嵌套 group）四种 URL 形态。
5. **自指守卫**：`/finish` 跑在 claude-code-global 自身时，跨项目资产候选改走本地 `/backlog`（遵循本项目「issue 进 BACKLOG」约定），不 API 自 file 到自己。
6. **三轴 label 兼容**：跨仓库 issue 读 claude-code-global 自己的 `.github/labels.yml` 选 `area:`（install/skill/hook/template/doc），保持三轴 label 约定。
7. **`platform_issue.py issue-create` 加 `--repo`**：把命令拼装抽成纯函数 `build_issue_create_cmd()`（可单测），透传 `--repo` 给 `gh`/`glab`，平台用顶层已有的 `--platform` override 显式指定（不依赖 cwd remote）。

### 开发内容概括

- `scripts/platform_issue.py`：抽 `build_issue_create_cmd()` 纯函数；`issue-create` 加 `--repo` 参数；`cmd_issue_create` 改为调纯函数 + 执行；`--self-test` 新增 4 条命令拼装用例（github/gitlab × 有无 repo）。
- `skills/finish/SKILL.md`：SUMMARY 步加「可沉淀项」段说明；新增「跨项目可沉淀流程反思」步（含判定标准、去向分类、自指守卫、逐条确认、跨仓库 file 五个子步）；frontmatter description 同步。
- **顺手治理**：把 finish 历史累积的「见缝插针」式步骤编号（`1.5` / `3.5` 这种插入式 `.5`）整体重排为连续整数 **Step 1~9**，同步更新文内所有交叉引用；`5.1~5.5` 这类真子步骤保留嵌套（重排为 `8.1~8.5`）。

### 额外产物

- 开发前在 issue #6 留了一条澄清评论，记录「原始描述 → 细化意图」的演化，便于未来追溯。
- `build_issue_create_cmd` 的 4 条 self-test 用例（TDD 先红后绿）。

## 局限性

- **跨仓库提 issue 未端到端实跑**：self-test 只覆盖命令拼装，真正的 `gh issue create --repo` 跨仓库调用要等首个真实候选出现时才会 dogfood。
- **新行为对其他项目尚未生效**：`/finish` 是软链到 master 的全局 skill，本轮改动合并 + `install.sh` 重跑（或下次自动同步）后才在其他项目激活。
- **判定靠模型自觉**：「值得沉淀」「具体落点」仍是模型主观判断，3 条上限只能压数量，压不了误判方向；实际噪音水平要用一段时间才看得清。

## 后续 TODO

- 在真实的「别的项目」里 dogfood 一次跨仓库提 issue，验证 slug/platform 派生 + label 选取 + body 回链在 GitHub（及 GitLab）端真实可用。
- 观察一段时间，若「可沉淀项」提示噪音过大或长期为空，再回头收紧/放松判定标准（对应 issue #6 的方向 B/C 升级判断）。

## 可沉淀项

- **见缝插针式编号是通病**：finish 的 `.5` 步骤累积问题，其他 skill（start 等）也可能有同类「插入步骤不重排」的历史。属潜在的跨项目/跨 skill 治理项，但**落点不够具体、出现次数不足 2**，本轮不达提 issue 门槛，仅记录于此。
- 其余无。
