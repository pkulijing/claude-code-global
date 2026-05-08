# SUMMARY — round 15：让 backlog/start/finish 三件套 skill 在 GitLab 项目上可用

对应 issue：[#3 让 backlog / start / finish 等 skill 在 GitLab 项目上可用（gh ↔ glab 双轨）](https://github.com/pkulijing/claude-code-global/issues/3)

## 1. 开发项背景

Round 14 把模板侧 GitHub/GitLab 双兼容（issue templates + CI 文件并存）落到位，并在 `/bootstrap` 与 `/sync-project-config` 中按 `git remote get-url origin` 三分支判定（GitHub / GitLab / 其他），但 GitLab 分支当前是「跳过 + 提示」未真正调 `glab`；**skill 内 5 处 `gh` CLI 调用仍是 GitHub 独占**：在 GitLab 项目上跑 `/backlog`、`/start <#>` 会前置失败或行为静默错位。

属用户能感知的明显能力缺口（priority P1）。

## 2. 实现方案

### 2.1 关键设计决策

PROMPT 阶段提了两条候选路径，PLAN 阶段经一次 Plan agent critique 后定稿，三个核心决定：

#### 决定 A：抽 helper（方向 B）而非每个 skill 内三分支

PROMPT 阶段最初倾向方向 A（每个 SKILL.md 内 detect platform → 分支调用），但本轮 in-scope 的 CLI 触点已增至 5 处（`/backlog` 的 auth + create + label-list + repo-slug + `/start` 的 issue-view + `/bootstrap` `/sync-project-config` 的 label-upsert），三分支逻辑重复 5 次的长期漂移成本高于单次抽象成本。

最终采纳**方向 B**：单文件 `scripts/platform_issue.py` 封装 5 个平台原语 + 字段归一 + color 规范化，SKILL.md 全部走平台无关 helper。

#### 决定 B：跨平台共读 `.github/labels.yml`（不复制 `.gitlab/labels.yml`）

PROMPT 第 3.4 项原写「新增 `templates/_common/__root__/.gitlab/labels.yml`」，PLAN 阶段修订为「helper 跨平台共读 `.github/labels.yml`」。理由：

- labels schema 完全跨平台一致（`{name, color, description}` × 9 条），新建副本只引入维护漂移
- `.github/labels.yml` 在 GitLab 项目里**不是**给平台读的死文件 —— 它是 helper 私有输入，与 `.gitlab-ci.yml` 在 GitHub 项目里"被平台忽略"的语义不同
- 如未来 GitLab 真出现 GitLab 特异字段需求，加可选字段成本仍低于拆文件

#### 决定 C：立 `scripts/` 为新二级目录范式

与 `hooks/` 软链模式同构，`install.sh` 加一段对称循环：

- `mkdir -p "$TARGET_DIR/scripts"`
- 逐文件软链（与 hooks 一致），不整目录软链
- SKILL.md 调用永远写完整路径：`python3 $HOME/.claude/scripts/platform_issue.py <subcommand>`
- helper `#!/usr/bin/env python3` shebang + `chmod +x`，但调用时仍显式写 `python3`（不依赖 PATH）

未来「既不是 hook（无 trigger）、又不是 skill（不直接被 model 调用）、但需要稳定路径被 SKILL.md 调用的辅助脚本」都归入 `scripts/`。

### 2.2 helper 实现关键约束

- **零第三方依赖**：禁用 PyYAML（PEP 668 风险 + 破坏「软链即装好」承诺）；自己写 30 行最小 yml parser，专门支持 `labels.yml` 极简 schema（list of dict + 三 string field + `#` 注释 + `---` doc header）
- **隐藏 `--self-test` subcommand**：跑 yml round-trip + 字段映射 + color 规范化纯函数自检，TDD 红→绿→重构的"红"步骤就是 self-test 失败
- **统一字段归一**：GitLab 端的 `iid` / `web_url` / `description` / `labels: [str]` 一律映射为 GitHub 风格 `number` / `url` / `body` / `labels: [str]`，SKILL.md 永远读同一 schema
- **color 双向转换**：GitHub 用裸 hex（`0E8A16`），GitLab 加 `#` 前缀（`#0E8A16`），helper 内自动按平台转换
- **exit code 协议**：`0` 全部成功 / `1` 通用错误 / `2` 平台未知 / `3` 认证失败 / `4` CLI 缺失 —— SKILL.md 按 exit code 分支文案

### 2.3 `glab` 与 `gh` 的关键差异处理

PLAN 阶段 verify 出 3 个差异点，helper 内全部抹平：

1. **json 字段命名**：`iid`/`number`、`web_url`/`url`、`description`/`body`、`labels: [str]`/`labels: [{name}]` —— `normalize_issue()` 函数统一映射
2. **`glab label create` 无 `--force`**：用 `glab label list --output json` 拿现存 name→id 映射，存在则 `glab label edit -l <id> -c #<hex> -d <desc>`，否则 `glab label create -n <name> -c #<hex> -d <desc>`；GitHub 端继续用 `gh label create --force`
3. **color 格式**：上文已述

### 2.4 `/finish` 零代码改动

`Closes #N` 在 GitHub & GitLab 都自动关 issue（GitLab 还支持 `Fixes`/`Resolves`/`Implements` 等更多关键词 + cross-project `Closes group/project#N` 引用）。`/finish` SKILL.md 只加一句注释说明跨平台兼容，**无需平台分支处理**。

## 3. 开发内容概括

### 新增文件

- [`scripts/platform_issue.py`](../../scripts/platform_issue.py) —— 单文件 helper，~360 行，零第三方依赖（仅 stdlib：`argparse` / `json` / `pathlib` / `re` / `subprocess` / `sys`）
- [`docs/15-三件套skill支持GitLab双轨/PROMPT.md`](PROMPT.md)
- [`docs/15-三件套skill支持GitLab双轨/PLAN.md`](PLAN.md)
- 本 SUMMARY.md

### 修改文件

- [`install.sh`](../../install.sh) —— 加 `scripts/` 软链段（与 hooks 对称）+ `mkdir -p "$TARGET_DIR/scripts"`
- [`skills/backlog/SKILL.md`](../../skills/backlog/SKILL.md) —— 5 处 gh 调用全替换为 helper；BACKLOG.md 骨架 `{owner}/{repo}` 改 `{slug}` + `{closed-issues-url}` 按平台生成
- [`skills/start/SKILL.md`](../../skills/start/SKILL.md) —— `gh issue view` → helper `issue-view`；issue URL 模式增 GitLab 形态
- [`skills/finish/SKILL.md`](../../skills/finish/SKILL.md) —— `Closes #N` 注释加跨平台说明（GitHub / GitLab 均原生）
- [`skills/bootstrap/SKILL.md`](../../skills/bootstrap/SKILL.md) —— Step 3.3.5 整段三分支替换为 helper `label-sync-from-file`；Step 5 收尾建议按 helper exit code 重写
- [`skills/sync-project-config/SKILL.md`](../../skills/sync-project-config/SKILL.md) —— §4.3 + §6 的 GitHub/GitLab 三分支替换为 helper 调用
- [`GLOBAL_CLAUDE.md`](../../GLOBAL_CLAUDE.md) —— 「Backlog 与开发项管理（GitHub Issue 驱动）」→「（Issue 驱动，GitHub / GitLab 双轨）」；issue templates 双轨说明；`Closes #N` 跨平台说明
- [`README.md`](../../README.md) —— 新增 `## Scripts` 一节（含 `### 私有化部署 GitLab 的 glab 证书问题` troubleshooting 子节，dogfood 实测后补录）；部署表加 `scripts/*` 行；Skills 表 / Backlog 段 / 平台双兼容段 全部去 GitHub-only 措辞

### 额外产物

- helper 的 `--self-test` 隐藏 subcommand：4 类纯函数级断言（yml parser、字段映射 GitHub/GitLab 双向、color 规范化 4 case + 2 防御性 case），TDD 红→绿→重构的"红"指南
- 软链 `scripts/` 这个新二级目录范式，未来加新 helper 复用

## 4. 验证

### 4.1 helper self-test（TDD 红→绿）

```bash
$ python3 ~/.claude/scripts/platform_issue.py --self-test
self-test: OK
```

### 4.2 GitHub 端集成 dogfood（本仓库）

```bash
$ python3 ~/.claude/scripts/platform_issue.py detect-platform
github
$ python3 ~/.claude/scripts/platform_issue.py repo-slug
pkulijing/claude-code-global
$ python3 ~/.claude/scripts/platform_issue.py issue-view 3
{ "number": 3, "title": "...", "body": "...", "url": "...", "labels": [...] }   # 字段归一正确
```

### 4.3 `--platform` override

```bash
$ python3 ~/.claude/scripts/platform_issue.py --platform gitlab detect-platform
gitlab    # exit 0，强制覆盖 detect 结果
```

### 4.4 install.sh 幂等

二次跑 `install.sh` 全部条目报「已跳过…（软链接已正确）」，`settings.json` 报「内容已包含基线」。

### 4.5 未做的验证

- **`label-sync-from-file` 端到端**：避免真改本仓库 labels，仅手工核对 helper 内部 `gh label create --force` 与 `glab label list/edit/create` 调用形态。需要在一个 sandbox repo 上跑端到端验证（→ 后续 TODO）
- **GitLab 真实项目 dogfood**：手边无随手可用的 GitLab 测试 repo（→ 后续 TODO，与 round 14 §4.2 同列）
- **`/backlog`、`/start`、`/finish` 三件套整链调用**：跑流程会真创 issue / 改 BACKLOG / 提 commit，本轮验证仅停在 helper 单元 + GitHub read-only 集成。本轮 commit 自身就是 `/finish` 流程的天然 dogfood

## 5. 局限性

1. **GitLab 实地 dogfood 缺位**：helper 的 GitLab 分支（`glab issue create` / `glab label edit` / `glab label create` 等）仅靠 `--help` 输出 + 文档核对实现，未在真实 GitLab repo 上端到端跑过。可能的细节坑：`glab issue create` 的 `-d` 长 body 是否需 escape、`glab label edit -l` 的 ID 类型（int/str）、cross-project URL 是否能被 `glab issue view` 正确处理等
2. **自托管 GitLab URL 启发式仍弱**：`detect-platform` 只匹配 origin 含 `gitlab` 字样；自托管常见 host（如 `git.company.com`）会被 detect 为 unknown，需用户 `--platform gitlab` override。这是 round 14 已知的妥协
3. **`label-sync-from-file` 无 `--dry-run` 模式**：dogfood 时如想看「会同步什么」需要硬跑实际同步。已记入后续 TODO
4. **yml parser 是受控 schema 专用**：仅支持 `labels.yml` 的极简形态（顶层 list of dict + 3 string field）。如未来 labels.yml schema 扩展（如加嵌套 / list-of-list），parser 需相应升级 —— 但反正只我们自己用，可控
5. **本仓库 `.cc-template.yml` `stacks: []` 状态阻塞 dogfood-via-sync**：round 11 遗留状态，round 14 SUMMARY 已记，与本轮无关
6. **helper 体积~360 行，已接近"该不该拆"的边界**：本轮单文件够用；如下一轮再加 2-3 个 subcommand 或新平台分支，应考虑拆 `scripts/lib/`

## 6. 后续 TODO

按优先级：

1. **新 issue（`area:skill` `area:meta` `type:test`）**：实地 GitLab repo 端到端验证清单 —— 含 helper 各 subcommand、quick action 首行规则、`.gitlab-ci.yml` 首跑、issue templates web UI 显示等。round 14 SUMMARY §6 已记，本轮再次确认延续
2. **新 issue（`area:skill` `type:feat`）**：自托管 GitLab URL 启发式增强 —— 在 detect-platform unknown 分支增 `glab api /version` 探测兜底，避免 `git.company.com` 类自托管 URL 永远要 `--platform` override
3. **新 issue（`area:skill` `type:feat`）**：`label-sync-from-file` 加 `--dry-run` 模式 —— PLAN dogfood 阶段就发现需要，本轮没做
4. **新 issue（`area:meta` `type:refactor`，可选）**：本仓库 `.cc-template.yml` 当前 `stacks: []` 状态修复 —— round 11/14 都遗留至此，是否让 global-repo 自身也声明 `stacks: [{stack: python-uv, path: .}]`，让以后改模板时能跑 sync 自检
5. **新 issue（`area:skill` `type:perf`，低优先级）**：helper 加 `--debug` 已隐含但未在 SKILL.md 文档化的"调用追踪"模式 —— PLAN 阶段提过，实际实现时已加（`--debug` flag stderr 输出 `[debug] run: <cmd>`），仅未在 SKILL.md 推介给用户
