# lark-cli 飞书文档创作规则

> 本文档由 `claude-code-global` 仓库的 `rules/lark.md` 提供，经 `install.sh` 双轨软链到 `~/.claude/rules/lark.md`（CC 端）与 `~/.codex/rules/lark.md`（Codex 端）。修改请回到 `claude-code-global` 仓库，不要直接编辑软链目标。
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

### 2.2 图 / 文件置顶：用 block_move_after 重定位

`docs +media-insert` 只能把图 / 文件追加到**文末**。要把它移到正文最前，用 `block_move_after` 锚 `<title>`（id == document_id）即可置顶。

### 2.3 内容文件只接受 CWD 内相对路径

`docs +create --content @file` 只接受 **CWD 内的相对路径**。内容文件宜写在 gitignore 的 `output/` 目录，再用 `@output/xxx.md` 形式传入，规避 shell 转义问题。

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
