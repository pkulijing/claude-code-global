# platform_issue.py helper 契约

`scripts/platform_issue.py` 按 `git remote get-url origin` 自动判定 GitHub / GitLab，是 issue / label 操作的统一入口。skill 不直接调 `gh` / `glab`，一律走本 helper。本文档是 helper 行为的单一真源，`bootstrap` / `sync-project-config` / `finish` 各处引用此文件，不再各自复述。

## 调用形式

```bash
python3 $HOME/.claude/scripts/platform_issue.py [--platform github|gitlab] [--repo <slug>] <subcommand> ...
```

- `--platform` / `--repo` 省略时按当前仓库 `git remote` 自动判定、对本仓库操作；跨仓库操作（如向 claude-code-global 沉淀 issue）显式带 `--repo <slug>`。
- 常用子命令：`issue-view <N>`、`issue-create`、`issue-comment`、`issue-label-add` / `issue-label-remove`、`label-list`、`label-sync-from-file <path>`。

## issue-list 语义

```bash
python3 $HOME/.claude/scripts/platform_issue.py issue-list [--limit N] [--repo <slug>] [--no-body]
```

只列 **open** issue，stdout 是归一 json **数组**，每项 schema 与 `issue-view` 完全一致（`number` / `title` / `body` / `url` / `labels` / `updatedAt`）—— 消费方（`/triage`）据此读 `labels` 取 priority 轴、读 `body` 取 scope 字段，不必关心是哪端答的。`--limit` 默认 100（GitHub `--limit` ↔ GitLab `--per-page`）。

- **`updatedAt`**：平台给什么就是什么（GitLab 侧字段名是 `updated_at`，helper 归一）；**平台没给就是 `null`，绝不拿「现在」兜底** —— 它的消费方拿它和一个更早的快照比对「这条 issue 有没有被人动过」，编一个时间戳会让那道闸永远答「没动过」。
- **`--no-body`**：整个丢掉 `body` 字段（不是截断），GitHub 侧在服务端就不取。用于**只要时间戳的复核式重读** —— `/routine-dev` 打 `auto:skip` 前要确认「读完正文到现在这段时间里没人编辑过它」，若为此把所有正文再拉一遍，花掉的正是这个 label 要省的那笔。GitLab 无字段选择能力，argv 不变、正文在归一层丢，schema 承诺一致。

## issue-comment 语义

```bash
python3 $HOME/.claude/scripts/platform_issue.py issue-comment --issue <N> --body-file <F> [--repo <slug>]
```

**「issue 是单一真源」的工作流下，沉淀讨论与结论的动作本身就是评论** —— 补实测数据、贴验证产物、记录决策更正、写 spike 结论。缺了它，单一真源就只能写不能续，于是只剩「违反规则直调 `gh`」或「做不成事」两条坏路。

两端差异正是 helper 存在的理由（连子命令名都不一样）：

|        | 命令                              | 正文传入                       |
| ------ | --------------------------------- | ------------------------------ |
| GitHub | `gh issue comment <N>`            | `--body-file <F>`              |
| GitLab | `glab issue note <N>`             | `-m <text>`，**无 `--body-file`** |

- **长正文安全**：一律以 argv 列表交给 `subprocess`、**不经 shell**，正文里的反引号 / `$VAR` / 引号原样传入，无需转义。已按 `playbooks/shell.md` §4 配沙盘用例（桩掉 `gh` / `glab`，断言真实 argv），覆盖含代码块的长 markdown。
- **输出**：评论 URL 单行到 stdout（与 `issue-create` 同构）。**GitLab 侧 `issue note` 的输出 schema 未经实测**：取不到 URL 时不报错（评论已经发出去了，此时失败等于把成功的副作用谎报成失败），只在 stderr 留一行 `warn:`，exit 仍为 0。

## issue-label-add / issue-label-remove 语义

```bash
python3 $HOME/.claude/scripts/platform_issue.py issue-label-add    --issue <N> --label <X> [--label <Y>] [--repo <slug>]
python3 $HOME/.claude/scripts/platform_issue.py issue-label-remove --issue <N> --label <X> [--repo <slug>]
```

两端连子命令带 flag 名都不同：

|        | 加                                      | 删                                        |
| ------ | --------------------------------------- | ----------------------------------------- |
| GitHub | `gh issue edit <N> --add-label <X>`     | `gh issue edit <N> --remove-label <X>`    |
| GitLab | `glab issue update <N> --label <X>`     | `glab issue update <N> --unlabel <X>`     |

- **增量语义**：只动指定的那几个 label，issue 上已有的原样保留。消费方（`/routine-dev` 打 `auto:skip`）依赖这一点 —— 换成全量替换会把三轴 label 悄悄抹掉。
- **一个 label 一次 flag**，绝不拼成 `"a,b"`：label 名本身可以含逗号，拼起来会被平台侧拆成两个不存在的名字。
- **输出**：成功打一行 `added on <platform>: #<N> <labels>`（删则 `removed`）。**失败原样透传底层 stderr 并 exit 1** —— 打标是为了持久化一个判断，谎报成功会让调用方以为结论已落库。
- **GitLab 侧未经实测**（本机没装 `glab`）：argv 形态由纯函数 + 沙盘桩测钉住，真实 flag 语义待有 GitLab 环境时校，与 `issue-comment` 的 GitLab 输出 schema 同属一类未验项。

## label-sync-from-file 语义

`label-sync-from-file .github/labels.yml` 把 labels.yml 同步到远端（`.github/labels.yml` schema 跨平台一致，是 helper 私有输入而非平台读的死文件——GitLab 项目也读 `.github/` 同一份，不建 `.gitlab/labels.yml` 副本）：

- **GitHub** → 对每条 `gh label create --force`（`--force` 在已存在时覆盖更新）。
- **GitLab** → 先 `glab label list --output json` 拿现存 name→id 映射；存在则 `glab label edit`，否则 `glab label create`。
- **color 格式** helper 自动转换：GitHub 用裸 hex（`0E8A16`），GitLab 加 `#` 前缀（`#0E8A16`）。
- stdout 输出每条 TSV `<status>\t<name>[\t<msg>]` + 末行 `summary: N synced, M error`，原样展示给用户。

## exit code 降级（调用方统一按此处理，不阻塞其他动作）

| exit | 含义                                                  | 降级提示                                                                                           |
| ---- | ----------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| 2    | 平台未知（无 origin / 自托管 URL 不含 `gitlab` 字样） | 「labels 同步跳过；GitHub 请补 origin remote，自托管 GitLab 加 `--platform gitlab` override 重跑」 |
| 3    | auth 失败                                             | 「跑 `gh auth login` 或 `glab auth login` 后重试」                                                 |
| 4    | CLI 缺失                                              | 「先 `brew install gh` / `brew install glab`」                                                     |

## 三轴 label 硬约束（issue-create）

跨仓库 `issue-create --repo <slug>` **必须带三轴 label**（`type:*` / `area:*` / `priority:*`），helper 对「跨仓库 + 零 label」创建强制拦截（确需裸提加 `--allow-no-label`）。

**失败绝不去 label 重试**：若某 label 在目标仓库不存在导致 `gh`/`glab` 整条失败，**不要**去掉 `--label` 重试求成功——那正是历史上产出无 label 裸 issue（如 #12）的原因。正确做法：先 `label-list --repo <slug>` 校验 label 真实存在（labels.yml 是真源、未必已同步到远端，二者可能脱节），改选已存在的同轴 label，或先 `label-sync-from-file` 同步远端后再校验重试。
