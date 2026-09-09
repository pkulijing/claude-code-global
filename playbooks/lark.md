# lark-cli 飞书文档创作规则

> 本文档由 `claude-code-global` 仓库的 `playbooks/lark.md` 提供，经 `install.sh` 双轨软链到 `~/.claude/playbooks/lark.md`（CC 端）与 `~/.codex/playbooks/lark.md`（Codex 端）。修改请回到 `claude-code-global` 仓库，不要直接编辑软链目标。
>
> **触发条件**：Coding Agent 在本轮任务涉及用 lark-cli（lark-doc）创作或编辑飞书云文档，**或为 lark-cli 申请 / 排查授权**时，**必须先把本文件读入上下文**，再开始动手。

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

### 2.2 图 / 文件定位：置顶用 block_move_after，插正文中间用 --selection-with-ellipsis

`docs +media-insert` **默认**把图 / 文件追加到**文末**。要它落在别处有两条路，别混用：

- **置顶** → 用 `block_move_after` 锚 `<title>`（id == document_id）。
- **插到正文中间** → 直接用 `--selection-with-ellipsis <锚点文本>` 配 `--before`，**一步**把图插到指定段落前 / 后，不必走「先 append 到文末、再 `block_move_after` 重定位」那两步。
  ⚠ 锚点文本里含引号（中文弯引号或半角 `"`）会被 shell 吃掉、报 `unmatched "`，**挑不含引号的片段做锚点**。

### 2.3 `--content` 与 `--file` 都只接受 CWD 内相对路径

`docs +create --content @file` 与 `docs +media-insert --file` **都**只接受 **CWD 内的相对路径**，传绝对路径直接被拒：

```
"message": "unsafe file path: --file must be a relative path within the current directory,
 got \"/Users/.../assets/frame_sample_grid.jpg\"
 (hint: use a relative path like ./filename; flags that support stdin can read an out-of-tree file via '-' instead)"
```

- **内容文件**宜写在 gitignore 的 `output/` 目录，再用 `@output/xxx.md` 形式传入，规避 shell 转义问题。
- **配图同理，且更容易撞上**：图往往产自 `docs/<轮次>/assets/`（甚至在另一个 git worktree 里），而 lark-cli 需要在项目根跑 —— 先把图**拷进 CWD 内的 `output/`**，再用 `./output/xxx.jpg` 传入。

报错提示里给的 `-`（stdin）**仅对支持 stdin 的 flag 有效**，别拿它当通用逃生舱。

### 2.4 带图的文档：markdown 里直接留 mermaid 围栏，导入器自动转原生画板

推送**含 ` ```mermaid ` 代码块**的 markdown 时：

```sh
lark-cli docs +update --command append --doc-format markdown --content @file.md
```

飞书的 markdown 导入器会**自动**把每个 mermaid 围栏渲染成**原生画板块**——返回的 `new_blocks` 里即是 `block_type: whiteboard`。实测 `stateDiagram-v2` 与 `flowchart` 均正确渲染、中文标签正常；产物是**原生可编辑画板**（不是图片、也不是代码块），团队成员可在飞书里继续拖拽调整。

**所以向飞书推带图的架构 / 流程文档时，最省事的高保真路径就是「markdown 里原样留 mermaid 围栏 + append」**：既**不需要**先建空白画板再走 lark-whiteboard 那条填充路径，也**不需要**把 mermaid 预渲染成 PNG 再插图。

**已知瑕疵**：mermaid 自动布局下个别标签会轻微重叠或长文本折行。画板可编辑，人工微调即可，不影响这条路径的选择。

### 2.5 走 SVG 路线填画板：箭头用 `marker-end`、回写前反转 z 序、文本宽度放宽

2.4 那条（markdown 留 mermaid 围栏、导入器自动转画板）**能走就走**；只有需要精确控制版式（自定义布局、虚线语义、指定折点）时才走 `lark-whiteboard` 的 **SVG 路线**（`whiteboard-cli -f svg --to openapi` 编译成节点再回写）。这条通道上有三个坑，共同特征是**本地全绿、只有真写进画板才暴露**：

**① 箭头一律 `marker-end`，禁止 `<line>` + `<polygon>` 手拼三角形。**
连线写 `<line>` / `<polyline>` + `marker-end="url(#id)"`，`<marker>` 定义在 `<defs>` 里，svg-parser 会编译成原生 `connector` 节点（`end.arrow_style: "triangle_arrow"`），节点可拖、箭头可编辑。手拼的三角形则编译成**两个互不相干的节点**：线成了 `arrow_style:"none"` 的裸线，三角形降级成 `type:"svg"` **内嵌图片节点**——用户在飞书里一拖就散，且内嵌 svg 节点还无法经 raw 通道回写（`field validation failed` 99992402）。
同理另外两样也别手画：`stroke-dasharray` → `border_style:"dash"`，`<polyline>` 的折点 → `shape:"right_angled_polyline"` + `turning_points`。线型、折点、箭头三样都能用 SVG 原生属性表达，没有任何理由手拼。

> 之所以容易连犯两次：SVG 路线的文档（`routes/svg.md`、`lark-doc/references/lark-doc-whiteboard.md` 的「可识别的元素」段）**通篇没提箭头怎么画**，只有 DSL 路线的 `elements/connectors.md` 提 `endArrow`——于是「自己画个三角形」成了最自然的选择。

**② 回写前把节点顺序反过来（`nodes.reverse()`）。**
画板的 z 序与 SVG 文档序**相反**：请求里的 `nodes[0]` 拿到最大 `z_index`（最上层），于是 SVG 里先画的背景矩形在画板里反而浮在最上面，**盖住它自己的标签**——线上表现是「所有带填充图形里的文字全部不可见」。按 skill 给的原命令（`whiteboard-cli --to openapi | lark-cli whiteboard +update`）直推必踩，要在两条命令之间插一步反转。

**③ `text_shape` 宽度放大到 `w * 1.15 + 12`，且 SVG 里字号一律用整数。**
whiteboard-cli 按**本地字体**度量精确贴合宽度，而画板硬编码 Noto Sans SC 更宽，非整数字号（10.5 / 11.5）还会被向上取整——结果一批短标签在线上全折成两行。center 对齐的元素放宽后同步左移 `dx/2`。

**自检只认「编译产物 + 线上回读」，把你写的那份源 SVG 渲成 PNG 一律不算数**——上面三条在写进画板之前全都看不出来：`--check` 全绿，源 SVG 渲出来的 PNG 也全对（本地就是按 SVG 语义渲的，层序、字宽本来就对），错的是画板侧的语义。两步：

1. **编译产物**：`npx -y @larksuite/whiteboard-cli@^0.2.12 -i diagram.svg -f svg --to openapi --format json`，grep `arrow_style`；图上本该有箭头却出现 `"arrow_style":"none"`，就是拼错了。
2. **线上回读**：`+query --output_as raw` 校验节点数 / 箭头 / z 序 / 文本行数，再 `+query --output_as svg` 把**画板里真实存着的那份** SVG 拉回来、本地渲成 PNG 肉眼看 —— 渲的不再是你写的源文件，所以这一步算数。
   ⚠ **别拿画板预览图接口验收**：刚写入后它返回「生成中」占位图且缓存不刷新，靠它验收等于没验。

## 3. 授权与 scope 管理

任何用 lark-cli 的项目都要过授权这一关，而 scope 申请策略直接决定**会不会惊动租户管理员**。下面六条是实测出的最小 scope 授权工作流。

### 3.1 绝不用 `--domain` 打包授权

`--domain drive` 会捎带密级（secure-label）、权限设置（permission）、申请权限（apply-permission）这类**敏感 scope**——既违反最小权限，又可能触发租户审批（实测被管理员审批流卡住）。**一律逐条列 scope，不按 domain 打包。**

### 3.2 用本地预检凑最小集，一次凑齐再授权

lark-cli 对每条命令做**本地 scope 预检查**，可以据此精确收集所需 scope，不必猜：

- 读命令直接试跑；**写命令用 `--dry-run`**；
- 从报错的 `missing_scopes` 字段抄下精确 scope 名；
- **把本轮要用的命令全部预检一遍、凑齐清单再发起授权**——否则每漏一条就要重新扫一次码。

### 3.3 审批中的 scope 要先拆出去

设备授权是**整包生效**的：申请集合里只要含一个「审批中」的 scope，整个 device flow 就报 `app pending approval`，**连那些本来免审批的 scope 也一并拿不到**。

**应对**：把免审批子集拆出来单独授权，先解锁对应工作线，审批中的那部分等批下来再补。

### 3.4 scope 在服务端增量累积

多次 `auth login` 的 scope **服务端累积**（返回里区分 `already_granted` / `newly_granted`），后补 scope 不影响已有授权。所以 3.3 的拆分授权是安全的，不会把先前拿到的权限冲掉。

### 3.5 换机器必须重新认证，不能拷配置

user token **按机器隔离**，拷 `~/.config/lark-cli` 不可靠。新机器上重新 `config init --app-id <同一应用>` + 重新扫码即可，**授权集合会自动带上历史 union**（因为 3.4 的服务端累积）。

### 3.6 无人值守场景：通知走 bot，user token 失效要显式报警

- **bot 身份（appId + secret）不受 user token 过期影响**，故定时任务里的通知类操作一律走 bot；
- user token 失效时，任务应**降级为「发通知提醒重新 `auth login`」而非静默失败**——否则定时任务会安静地连续失败很多天而无人察觉。
