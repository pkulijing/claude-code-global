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
