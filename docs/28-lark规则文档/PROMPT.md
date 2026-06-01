> 来自 [#14 约定：lark-cli 创作的飞书文档默认加 lark-cli 署名行](https://github.com/pkulijing/claude-code-global/issues/14)
> Labels: `type:docs` `area:doc` `priority:P2`
>
> 实现方式（用户本轮指定）：**采用「新增 rules 独立文档」方案**（issue 给出的两个落点中的前者），即新建 `rules/lark.md`，而非在宪法里新增 lark 章节。

## 背景

来源：**wujie-data-format**（具身数据通用格式与转换/可视化工具集）round 22「面向非技术同事的两份飞书文档」。该轮用 lark-cli 的 doc 工具产出了两份飞书云文档，用户希望「lark-cli 创作的文档带可识别的出品标识，显得专业、可追溯」（类比 Claude Code 给 PR 末尾加 `Generated with Claude Code` trailer），并明确要求**沉淀为全局规则**。

经 `/finish` 的跨项目沉淀反思，该需求满足"跨项目通用 + 重复性"两条沉淀门槛：

- **通用**：任何项目用 lark-cli 产出飞书文档都适用，与具体业务无关。
- **重复性**：lark 文档创作在多个项目/多轮里反复发生，署名是稳定、可机械执行的约定。

## 需求

在 `claude-code-global` 仓库新建领域规则文档 **`rules/lark.md`**（与 `rules/python.md` 平级，目录级软链已自动覆盖到 CC `~/.claude/rules/` 与 Codex `~/.codex/rules/` 两端），把 lark-cli 飞书文档创作的**署名约定**与配套**实操技巧**一起收口；并在 `GLOBAL_AGENTS.md` 按既有「指针 + 触发条件」范式登记一条指向 `rules/lark.md` 的引用。

### 1. 署名约定（规则主体）

用 lark-cli（lark-doc）创建飞书云文档时，**默认在标题正下方、首个内容块之上**插入一行极简署名 blockquote（灰字）：

```
> ⚡ Crafted with lark-cli · <YYYY-MM-DD>
```

**例外**：正式 / 对外严肃文档若不宜署名可省略。

### 2. 配套 lark-cli 实操技巧（一并收进规则文档）

issue 在 round 22 已实测验证、值得沉淀的操作要点：

- **署名落位**：`docs +create` 建好文档后，用 `docs +update --command block_insert_after --block-id <document_id>` 锚在标题后插入该 blockquote —— docx 里 `<title>` 块 id **等于** document_id，锚它即落在正文最前、结论 callout 之上。
- **图/文件置顶**：`docs +media-insert` 只能把图/文件追加到**文末**；要重定位用 `block_move_after`，锚 `<title>`（id==document_id）即可置顶。
- **内容文件路径**：`docs +create --content @file` 只接受 **CWD 内相对路径**；内容文件宜写在 gitignore 的 `output/` 再用 `@相对路径` 传入，规避 shell 转义。

### 3. GLOBAL_AGENTS.md 指针登记

仿照 `rules/python.md` 的两处既有写法：

- 「## 领域规则文档（rules/）」段末「当前已沉淀的领域规则」列表加一行 `rules/lark.md`；
- 新增一节简短指针（含 CC / Codex 实际路径 + 触发条件），触发条件为「本轮任务涉及用 lark-cli 创作 / 编辑飞书云文档时，必须先把 `rules/lark.md` 读入上下文」。

## 范围与约束

- **不改 `install.sh`**：`rules/` 已是目录级软链，新增 `rules/lark.md` 即时生效，无需重装（项目 CLAUDE.md 已明确）。
- 文档全程中文撰写；`rules/lark.md` 头部沿用 `rules/python.md` 的 banner（说明真源 + 触发条件 + "勿编辑软链目标"）。
- 触发条件措辞要精准：仅在「用 lark-cli 创作飞书文档」时触发，不要泛化到"任何 lark 操作"，避免无谓加载。

## 待决问题

- 署名文案是否完全照搬 issue 的 `⚡ Crafted with lark-cli · <YYYY-MM-DD>`，还是要微调（emoji / 措辞）。
- 触发条件的边界：是否也覆盖"用 lark-cli 编辑既有飞书文档"（非创建），还是仅限新建文档时署名。
