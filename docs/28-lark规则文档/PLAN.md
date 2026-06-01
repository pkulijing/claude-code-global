# PLAN — 新增 rules/lark.md 领域规则文档（Closes #14）

## 目标

把「lark-cli 创作飞书文档默认加署名行」沉淀为全局规则，落点采用**新增 `rules/lark.md` 独立领域规则文档**（用户本轮指定，对应 issue 两个候选落点中的前者），并在 `GLOBAL_AGENTS.md` 按既有「指针 + 触发条件」范式登记。

## 设计要点

1. **复用 `rules/` 目录级软链**：`install.sh` 已把 `rules/` 整目录软链到 CC `~/.claude/rules/` 与 Codex `~/.codex/rules/`，新增 `rules/lark.md` **即时生效、无需重装**（项目 CLAUDE.md 已明确）。本轮**不动 `install.sh`**。
2. **结构对称 `rules/python.md`**：`lark.md` 沿用 python.md 的头部 banner（真源说明 + 触发条件 + "勿编辑软链目标"）、分节编号风格。GLOBAL_AGENTS.md 里 lark 指针节与 Python 指针节**平级独立**（两个领域规则并列呈现，不分主次）。
3. **遵守注释/文档"写当前真相"原则**：`rules/lark.md` 正文不写 `round 22` / `issue #14` 等开发历史标记，只写"实战验证过"的中性表述，使规则文档对未来读者干净可读。
4. **触发条件精准化**：仅在「用 lark-cli 创作 / 编辑飞书云文档」时触发 Read，不泛化到任意 lark 操作，避免无谓上下文加载。

## 改动清单

### A. 新建 `rules/lark.md`（完整草案）

```markdown
# lark-cli 飞书文档创作规则

> 本文档由 `claude-code-global` 仓库的 `rules/lark.md` 提供，经 `install.sh` 双轨软链到 `~/.claude/rules/lark.md`（CC 端）与 `~/.codex/rules/lark.md`（Codex 端）。修改请回到 `claude-code-global` 仓库，不要直接编辑软链目标。
>
> **触发条件**：Coding Agent 在本轮任务涉及用 lark-cli（lark-doc）创作或编辑飞书云文档时，**必须先把本文件读入上下文**，再开始动手。

## 1. 文档署名约定

用 lark-cli（lark-doc）**创建**飞书云文档时，默认在**标题正下方、首个内容块之上**插入一行极简署名 blockquote（灰字 quote 块）：

> ⚡ Crafted with lark-cli · <YYYY-MM-DD>

`<YYYY-MM-DD>` 取文档创建当天日期。

**为什么**：让 lark-cli 产出的文档带可识别、可追溯的出品标识，显得专业 —— 类比 Claude Code 给 PR 末尾加 `Generated with Claude Code` trailer。

**例外**：正式 / 对外严肃文档若不宜署名，可省略。

## 2. lark-cli docx 实操技巧

下列要点在实战中验证过，配合署名约定一并落地：

### 2.1 署名落位：锚标题块插在最前

`docs +create` 建好文档后，用 `docs +update --command block_insert_after --block-id <document_id>` 把署名 blockquote 锚在标题后：docx 里 `<title>` 块的 id **等于** document_id，锚它即落在正文最前、结论 callout 之上。

### 2.2 图 / 文件置顶：用 block_move_after 重定位

`docs +media-insert` 只能把图 / 文件追加到**文末**。要把它移到正文最前，用 `block_move_after` 锚 `<title>`（id == document_id）即可置顶。

### 2.3 内容文件只接受 CWD 内相对路径

`docs +create --content @file` 只接受 **CWD 内的相对路径**。内容文件宜写在 gitignore 的 `output/` 目录，再用 `@output/xxx.md` 形式传入，规避 shell 转义问题。
```

### B. 改 `GLOBAL_AGENTS.md`（两处）

1. 「## 领域规则文档（rules/）」段末「当前已沉淀的领域规则」列表，在 `rules/python.md` 行后追加一行：

   ```
   - `rules/lark.md` — lark-cli 创作飞书云文档（署名约定 + docx 实操技巧）
   ```

2. 文件末尾追加与「## Python 开发规则」并列的新节：

   ```markdown
   ## lark-cli 文档创作规则

   用 lark-cli（lark-doc）创作 / 编辑飞书云文档相关规范（署名约定 + docx 实操技巧）集中维护在领域规则文档 **`rules/lark.md`**：

   - CC 端：`~/.claude/rules/lark.md`
   - Codex 端：`~/.codex/rules/lark.md`

   **触发条件**：本轮任务一旦涉及用 lark-cli 创作或编辑飞书云文档，**必须先把 `rules/lark.md` 读入上下文**，再开始动手。
   ```

## 验证

- 纯文档轮，无代码逻辑 → 不涉及 TDD / 单测。
- `ls -l ~/.claude/rules/lark.md`（及 `~/.codex/rules/lark.md`，若 Codex 端已安装）确认目录级软链让新文件即时出现在两端，**无需重跑 install.sh**。
- 复核 `~/.claude/CLAUDE.md`（软链至 GLOBAL_AGENTS.md）已自动反映两处指针改动。
- 通读 `rules/lark.md`：确认无 round/issue 历史标记、署名文案与 issue 一致、触发条件措辞精准。

## 待决问题的默认决定（用户可在确认时推翻）

- **署名文案**：照搬 issue 已认可的 `⚡ Crafted with lark-cli · <YYYY-MM-DD>`，不微调。
- **触发范围**：触发条件覆盖「创作 / 编辑」飞书文档；但**署名约定本身仅约束"创建"场景**，编辑既有文档时按需补署名、不强制。

## 收尾

`/finish`：撰写 SUMMARY.md、commit 写 `Closes #14`、rebase + FF 合并 worktree 回 master、更新 BACKLOG（#14 未进 BACKLOG 索引，故无需删行）。
