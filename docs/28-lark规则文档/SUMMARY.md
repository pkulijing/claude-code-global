# SUMMARY — 新增 rules/lark.md 领域规则文档（Closes #14）

## 开发项背景

issue [#14](https://github.com/pkulijing/claude-code-global/issues/14)「约定：lark-cli 创作的飞书文档默认加 lark-cli 署名行」由 wujie-data-format round 22 的 `/finish` 跨项目沉淀反思自动提出：该轮用 lark-cli 产出两份飞书云文档，用户希望文档带可识别、可追溯的出品署名（类比 Claude Code 给 PR 末尾加 `Generated with Claude Code` trailer），并明确要求沉淀为全局规则。该需求满足"跨项目通用 + 重复性"门槛。

issue 给了两个候选落点：①新建 `rules/lark.md` 独立领域规则文档；②宪法新增 lark 章节。**用户本轮明确指定方案 ①**。

## 实现方案

### 关键设计

1. **复用 `rules/` 目录级软链，不动 install.sh**：`install.sh` 已把 `rules/` 整目录软链到 CC `~/.claude/rules/` 与 Codex `~/.codex/rules/`（本轮已验证两端软链均存在、同指主树 `rules/`）。新增 `rules/lark.md` 经 FF 合并回主树后即时出现在两端，无需重跑 install.sh。
2. **结构对称 `rules/python.md`**：`lark.md` 沿用 python.md 头部 banner（真源说明 + 触发条件 + "勿编辑软链目标"）与分节风格；`GLOBAL_AGENTS.md` 里 lark 指针节与 Python 指针节**平级独立**，两个领域规则并列呈现、不分主次。
3. **正文写"当前真相"**：`rules/lark.md` 不写 `round 22` / `issue #14` 等开发历史标记，只用"实战验证过"的中性表述，使规则文档对未来读者干净可读。
4. **触发条件精准**：仅在「用 lark-cli 创作/编辑飞书云文档」时触发 Read，不泛化到任意 lark 操作；署名约定本身仅约束「创建」场景，编辑既有文档按需补署名、不强制。

### 开发内容概括

- **新建 `rules/lark.md`**：§1 文档署名约定（默认在标题正下方插一行灰字 blockquote `> ⚡ Crafted with lark-cli · <YYYY-MM-DD>`，含 WHY 与"正式/对外严肃文档可省略"例外）；§2 三条 lark-cli docx 实操技巧（2.1 署名落位锚 `<title>` 块、id==document_id；2.2 媒体置顶用 `block_move_after`；2.3 内容文件只接受 CWD 内相对路径，宜放 gitignore 的 `output/`）。
- **改 `GLOBAL_AGENTS.md`（+10 行）**：「当前已沉淀的领域规则」列表加 `rules/lark.md` 一行；文件末尾追加与「## Python 开发规则」并列的「## lark-cli 文档创作规则」指针节（CC/Codex 实际路径 + 触发条件）。

### 额外产物

无额外脚本 / 测试（纯文档轮）。验证以软链生效性核查代替：确认 `~/.claude/rules` 与 `~/.codex/rules` 均为软链且指向主树 `rules/`，佐证"合并后即时生效、无需重装"的设计结论成立。

## 局限性

- 署名约定是**人工执行的约定**而非自动化 hook：依赖 Coding Agent 命中触发条件主动 Read `rules/lark.md` 并照做，没有机制强制 lark-cli 创建文档时一定插入署名行。
- 署名文案中的日期 `<YYYY-MM-DD>` 需 Agent 创建文档当天手填，规则未提供取当天日期的标准方式（交由执行时上下文）。

## 后续 TODO

- 若未来 lark-cli 文档署名出现频繁遗漏，可考虑把署名约定从"文档约定"升级为"封装进某个 lark skill 的创建流程"，让署名随 `docs +create` 自动落位（当前 issue 已给出 `block_insert_after` 的具体锚点，封装成本不高）。
- 观察 `rules/lark.md` §2 的 docx 实操技巧是否随 lark-cli 版本演进失效，需要时同步更新。

## 可沉淀项

暂无额外可沉淀项 —— **本轮动作本身即是一次跨项目沉淀**（把 issue #14 收口为 `rules/lark.md`），且当前仓库就是 claude-code-global，Step 3 跨项目反思命中自指守卫。本轮复用的「领域规则文档 = banner + 触发条件 + 分节」范式此前已由 `rules/python.md` 确立，非新增可沉淀模式。
