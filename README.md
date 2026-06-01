# Coding Agent 全局配置（Claude Code + Codex）

通过 GitHub 仓库**单一真源**地管理 Claude Code 与 OpenAI Codex 两个 coding agent 的全局配置（`GLOBAL_AGENTS.md` / `skills/` / `hooks/` / `scripts/` / `scheduler/` / `settings.base.json` / `codex.config.base.toml` / `user.config.example.env`）、「跨项目共享开发配置模板」（`templates/`）和「领域规则文档」（`rules/`，按 `<topic>.md` 拆分语言 / 栈 / 流程细则，由 GLOBAL_AGENTS.md 顶层指针引用），支持多设备同步与跨项目复用。`install.sh` 双轨部署到 `~/.claude/` 与 `~/.codex/`，缺哪端就只装哪端，详见下文「同时支持 Claude Code 与 Codex」。多设备自动同步（无需手动 `git pull && bash install.sh`）见下文「多设备自动同步」。

开发流程遵循 [`GLOBAL_AGENTS.md`](https://github.com/pkulijing/claude-code-global/blob/master/GLOBAL_AGENTS.md) 中定义的「需求 → 计划 → 执行 → 总结」四步模式，开发项以 issue 为真源（GitHub / GitLab 双轨自动判定，详见下文「Backlog 与开发项管理」）。

## 工作原理

Claude Code 读取 `~/.claude/`、Codex 读取 `~/.codex/` 下的全局配置。本仓库通过 `install.sh` 双轨部署到两端（软链接 / 合并）。下表以 Claude Code 端为例，Codex 端结构对称（见「同时支持 Claude Code 与 Codex」）：

| 仓库文件                  | 部署到                                                 | 方式                                | 说明                                                                                                                                                                                    |
| ------------------------- | ------------------------------------------------------ | ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GLOBAL_AGENTS.md`        | `~/.claude/CLAUDE.md`（Codex 为 `~/.codex/AGENTS.md`） | 软链接                              | 修改仓库即修改实际配置，`git pull` 即完成同步                                                                                                                                           |
| `skills/*/`               | `~/.claude/skills/*/`                                  | 软链接（逐个子目录）                | 不影响 `~/.claude/skills/` 下不属于本仓库的 skill                                                                                                                                       |
| `hooks/*`                 | `~/.claude/hooks/*`                                    | 软链接（逐个文件）                  | hook 脚本本体；由 `settings.base.json` 中带 `# @claude-code-global:<name>` 标记的条目以绝对路径引用                                                                                     |
| `scripts/*`               | `~/.claude/scripts/*`                                  | 软链接（逐个文件）                  | 被 SKILL.md 显式调用的稳定脚本（如 `platform_issue.py`），SKILL.md 通过 `$HOME/.claude/scripts/...` 引用                                                                                |
| `templates/`              | `~/.claude/templates/`                                 | 软链接（整目录）                    | 跨项目共享开发配置模板源，由 `/bootstrap` `/sync-project-config` 读取                                                                                                                   |
| `rules/`                  | `~/.claude/rules/`                                     | 软链接（整目录）                    | 领域规则文档（按 `<topic>.md` 拆，如 `python.md`），由 GLOBAL_AGENTS 顶层指针引用，Agent 命中触发条件时主动 Read                                                                        |
| 仓库根目录                | `~/.claude/global-repo/`                               | 软链接                              | 让 `/sync-project-config` 通过 stable 路径访问模板的 git 历史，计算模板版本变化                                                                                                         |
| `settings.base.json`      | `~/.claude/settings.json`                              | **合并**（非破坏性）                | 本机特有设置保留；仅追加/覆盖基线里声明的项                                                                                                                                             |
| `user.config.example.env` | `~/.claude-code-global/config.env`                     | **seed**（user-wins，非软链非合并） | 仓库内是示例基线；真实配置在仓库外、`git pull`/自动同步不覆盖；只在用户未设时填默认、新增 key 才补缺追加。详见 [docs/27-用户可配置项机制/DESIGN.md](docs/27-用户可配置项机制/DESIGN.md) |
| `scheduler/`              | （不部署）                                             | 由 `install.sh` 末尾消费            | 渲染模板后写到 `~/Library/LaunchAgents/`（macOS）或 `~/.config/systemd/user/`（Linux），注册自动同步调度器                                                                              |

`settings.json` 之所以不软链接，是因为它通常既含跨机共享设置（如 `permissions.allow`），又含本机特有偏好（如 `effortLevel`）。合并规则：

- **object**：递归合并
- **array**：并集去重（如 `permissions.allow` 会把仓库基线里的条目追加进本地已有的列表，而不是覆盖）
- **scalar**：仓库基线胜出；不想跨机共享的标量就别写进 `settings.base.json`
- 多次运行 `install.sh` 幂等；真正发生变化时会先备份成 `settings.json.bak.<timestamp>`

合并依赖 `jq`（macOS 自带 `/usr/bin/jq`；Linux 各发行版用包管理器安装）。

## 同时支持 Claude Code 与 Codex

本仓库**单一真源**地服务 Claude Code (CC) 与 OpenAI Codex 两个 coding agent：skills / hooks / 主指令文档单份维护，`install.sh` 双轨软链到两端，新增 skill / 改 hook 不用写两遍。

设计依据：`AGENTS.md` 已是多家 agent 共同采纳的跨工具事实标准（Codex / Cursor / Aider / Windsurf 等），仓库内容约 85% 本就 agent-neutral，CC 耦合主要在包装层（安装路径 / settings schema）而非内容层。因此把全局规范文档命名为 `GLOBAL_AGENTS.md`，软链为 CC 的 `CLAUDE.md` 与 Codex 的 `AGENTS.md`。

`install.sh` 自动检测 `~/.claude/` 与 `~/.codex/` 各自是否存在（agent 自身安装时会创建其 home 目录），对存在的一侧部署，缺哪端就跳过哪端：

| 仓库产物                                                          | Claude Code（`~/.claude/`）                         | Codex（`~/.codex/`）                                            |
| ----------------------------------------------------------------- | --------------------------------------------------- | --------------------------------------------------------------- |
| 主指令文档                                                        | `CLAUDE.md` ← `GLOBAL_AGENTS.md`                    | `AGENTS.md` ← `GLOBAL_AGENTS.md`                                |
| `skills/` `hooks/` `scripts/` `templates/` `rules/` `global-repo` | 软链                                                | 软链                                                            |
| 配置基线                                                          | `settings.json` ← 合并 `settings.base.json`（JSON） | `config.toml` ← 合并 `codex.config.base.toml`（TOML marker 块） |

Codex 端配置基线 `codex.config.base.toml` 镜像 `settings.base.json` 的 hook 注册（`SessionStart` 自动同步 + `PostToolUse` 自动 fix）。合并策略：`config.toml` 不存在则整份复制；已存在则只注入 / 整体替换 `# >>> claude-code-global managed >>>` … `# <<< … <<<` 之间的 marker 块，块外用户内容（`approval_policy` / `[projects]` 等）一律保留。

**已知限制**：

- Codex hooks 首次需进入 Codex 跑一次 `/hooks` 命令 review 后才生效（`install.sh` 跑完会打印提示）。
- skill body 中 `$HOME/.claude/scripts/...` 等路径仍硬编码；双装机器上 `~/.claude/` 始终存在故无碍，纯 Codex 机器尚未适配。
- skill frontmatter 的 `disable-model-invocation` 字段、`fix-after-edit.sh` 读取的 hook stdin JSON 字段名在 Codex 端的容忍度 / 一致性待端到端实测（见 issue #8）。

## 安装

```bash
git clone <repo-url> ~/Developer/claude-code-global
bash ~/Developer/claude-code-global/install.sh
```

重复执行 `install.sh` 是安全的（幂等），不会影响 `~/.claude/skills/` 下不属于本仓库的 skill。

## GLOBAL_AGENTS.md 内容概览

`GLOBAL_AGENTS.md` 定义了所有项目通用的开发规范：

| 模块                      | 内容                                                                                                                                                                                   |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **核心开发模式**          | 需求 → 计划 → 执行 → 总结的四步协作流程，每个开发项在 `docs/` 下留档（PROMPT.md / PLAN.md / SUMMARY.md）；每轮默认在独立 git worktree 内进行，支持多轮并行                             |
| **git 规则**              | 中文 semantic commit message，AI 提交须带 Co-authored-by，`.gitignore` 按目录拆分                                                                                                      |
| **环境变量管理**          | `.env.local`（真实值，gitignore）+ `.env.example`（占位符，提交），禁止泄露密钥                                                                                                        |
| **领域规则文档**          | 语言 / 栈 / 流程的具体细则下沉到 `rules/<topic>.md`（CC 端 `~/.claude/rules/`、Codex 端 `~/.codex/rules/`）；本宪法只保留"指针 + 触发条件"，Agent 命中条件时主动 Read 对应文件         |
| **Python 开发规则**       | 指针到 [`rules/python.md`](rules/python.md)：uv 管依赖 / ruff / pypi index（清华 + aliyun pytorch-wheels）/ src 布局 + uv_build / 7 条 Python 风格 / 测试约定                          |
| **lark-cli 文档创作规则** | 指针到 [`rules/lark.md`](rules/lark.md)：lark-cli 创作飞书云文档默认加署名行（`⚡ Crafted with lark-cli · <YYYY-MM-DD>`）+ docx 实操技巧（署名落位 / 媒体置顶 / 内容文件相对路径）     |
| **Backlog / 开发项管理**  | issue 为真源（GitHub / GitLab 自动双轨），三轴 label（`type:*` / `area:*` / `priority:*`），三件套 skill：`/backlog` `/start` `/finish`；`docs/BACKLOG.md` 仅作未关闭 issue 的扁平索引 |
| **跨项目共享配置**        | `templates/_common/` + stack 模板（如 `python-uv`）由 `/bootstrap`（新项目）和 `/sync-project-config`（老项目 adopt / 拉新）统一管理                                                   |

## Skills

基线 `settings.base.json` 中预置了 `permissions.allow: ["Skill(*)"]`，让所有 slash command 默认放行，避免反复弹权限确认。

本仓库提供以下 skill。`/backlog` `/start` `/finish` 三件套配合 `/commit` 形成完整的「issue 驱动」开发闭环；其余按需调用。

| Skill                  | 用途                                                                                                                                                                                                                                                                                                                                                                                  |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/backlog`             | 把一条想法走 issue templates 创建成 issue（GitHub / GitLab 自动判定，含三轴 label），并在 `docs/BACKLOG.md` 索引中加一行                                                                                                                                                                                                                                                              |
| `/start`               | 开新一轮开发：默认建独立 git worktree（`.claude/worktrees/round<N>-*`）+ 同名分支，再建 `docs/<编号>-<描述>/`、撰写 PROMPT.md，进入计划模式撰写 PLAN.md 等用户确认后再写代码。支持 `#<issue 号>` / GitHub or GitLab issue URL（推荐），也支持自由描述；`--no-worktree` 跳过 worktree 在当前分支直接干                                                                                 |
| `/finish`              | 收尾本轮：撰写 SUMMARY.md → 反思跨项目可沉淀流程（任意项目都跑，逐条确认后可直接向 claude-code-global 跨仓库提 issue，这类 issue 不进任何 BACKLOG） → 关联并关闭 issue（如有 `Closes #N`，GitHub / GitLab 均原生支持） → 更新 BACKLOG.md → `/devtree` → 必要时同步 README → `/commit` → worktree 轮自动收尾（rebase → FF 合并主分支 → 二次确认后清理 worktree/分支/tag，不自动 push） |
| `/commit`              | 分析当前变更，自动生成中文 semantic commit message 并提交，末尾自动附加 Co-authored-by                                                                                                                                                                                                                                                                                                |
| `/bootstrap`           | 为空项目搭建文档骨架（README / CLAUDE / DEVTREE）+ 选 stack 铺设跨项目模板，仅在项目首次开发前调用一次                                                                                                                                                                                                                                                                                |
| `/sync-project-config` | 把本仓库管理的「跨项目共享开发配置模板」最新变化同步进当前项目；含 adopt 模式（无 marker 老项目首次接入）                                                                                                                                                                                                                                                                             |
| `/devtree`             | 依据 `docs/DEVTREE.md` 中作者维护的 Epic 结构，重新生成可视化图表和节点索引                                                                                                                                                                                                                                                                                                           |
| `/rebase`              | 诊断本地分支分叉并按清单引导完成 rebase，历史保持 FF 直线                                                                                                                                                                                                                                                                                                                             |
| `/pybump`              | 升级 Python 项目版本号（`pyproject.toml`），提交并打 tag                                                                                                                                                                                                                                                                                                                              |
| `/clean-local-setting` | 清理项目 `.claude/settings.local.json` 中的 permissions 列表（分类、交互确认、保留备份）                                                                                                                                                                                                                                                                                              |

## Hooks

`hooks/` 下放跨项目共用的 hook 脚本，由 `install.sh` 软链到 `~/.claude/hooks/`，并由 `settings.base.json` 中的 hook 条目以绝对路径 `$HOME/.claude/hooks/...` 引用。

| Hook                               | 触发时机                  | 作用                                                                                                                                                       |
| ---------------------------------- | ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `fix-after-edit.sh`                | PostToolUse（Edit/Write） | 编辑后自动跑项目本地工具链（如 `ruff check --fix`、`prettier --write`），让 AI 改动跟项目 formatter 输出对齐，避免 VS Code 保存时 formatOnSave 触发大 diff |
| `scripts/auto-update.sh --session` | SessionStart（startup）   | 新 Claude session 启动时静默拉本仓库更新；输出当前版本 hash + GitHub commit 链接，更新后追加重启提醒。详见下文「多设备自动同步」                           |

由本仓库管理的 hook 条目以 `# @claude-code-global:<hook-name>` 注释作为身份标记；`install.sh` 通过这个标记做集合差分（增 / 删 / 同名替换），不影响用户手动添加的 hook。

## Scripts

`scripts/` 下是被 SKILL.md 显式调用的稳定脚本（非 hook、非 skill），由 `install.sh` 软链到 `~/.claude/scripts/`，SKILL.md 通过绝对路径 `$HOME/.claude/scripts/<name>` 引用。

| Script              | 用途                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `platform_issue.py` | 跨平台 issue / label / repo helper：封装 `gh` ↔ `glab` 双轨调用，按 `git remote get-url origin` 自动 dispatch。被 `/backlog` `/start` `/finish` `/bootstrap` `/sync-project-config` 调用；`issue-create` 支持 `--repo` 跨仓库提 issue（配合 `--platform`，供 `/finish` 把可沉淀项提到 claude-code-global）——跨仓库创建强制带 ≥1 个 `--label`（零 label 直接拒绝，确需裸提才加 `--allow-no-label`），`label-list` 亦支持 `--repo` 以便创建前校验目标仓库 label。零第三方依赖（仅 stdlib），含 `--self-test` |
| `user-config.sh`    | 用户可配置项的可 source 库：`ccg_seed_user_config`（user-wins seed，缺省才填/补缺追加）、`ccg_read_config`（安全解析，不 blind `source`）、`ccg_apply_git_default_branch`。被 `install.sh` source，未来 hook/skill 可复用。详见 [docs/27-用户可配置项机制/DESIGN.md](docs/27-用户可配置项机制/DESIGN.md)                                                                                                                                                                                                   |
| `auto-update.sh`    | 多设备自动同步主脚本：跑 `git fetch` → ff-only `git pull` → `bash install.sh`，被 OS 调度器（launchd/systemd）和 Claude SessionStart hook 共用，30min 共享节流。详见下文「多设备自动同步」                                                                                                                                                                                                                                                                                                                 |

### 私有化部署 GitLab 的 glab 证书问题

如果 `glab auth login` 报错形如 `x509: certificate signed by unknown authority` 或 `tls: failed to verify`，多半是私有化部署的 GitLab 用了自签或内部 CA 签发的证书。**永久修复**（不要用 `skip_tls_verify` 类降级方案）：把服务器证书加到系统信任库。

1. 抓证书：

   ```bash
   openssl s_client -showcerts -connect your-gitlab-host.com:443 </dev/null 2>/dev/null \
     | openssl x509 -outform PEM > gitlab.crt
   ```

2. 加到系统信任库：
   - **macOS**：打开 Keychain Access → 把 `gitlab.crt` 拖进 **System** keychain → 双击该证书 → Trust 段设为 **Always Trust**
   - **Linux (Ubuntu/Debian)**：
     ```bash
     sudo cp gitlab.crt /usr/local/share/ca-certificates/
     sudo update-ca-certificates
     ```

加完后重新 `glab auth login` 即可。

## 跨项目共享模板

`templates/` 下维护「跨项目共享开发配置模板」，由 `install.sh` 软链到 `~/.claude/templates/`，供 `/bootstrap` 与 `/sync-project-config` 在目标项目中铺设 / 同步。

| 模板         | 适用项目                        | 内容（节选）                                                                                                                                                                                                                                                                                                                          |
| ------------ | ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `_common/`   | 所有项目（其他 stack 自动叠加） | 通用 issue templates（GitHub + GitLab 双轨）、`.github/labels.yml` 三轴 label、`.prettierrc` 等                                                                                                                                                                                                                                       |
| `python-uv/` | Python 项目（uv + ruff）        | `.gitignore` / `.pre-commit-config.yaml` / `.vscode/`（formatOnSave + ruff）/ `pyproject.toml` 三个片段（`[tool.ruff]` + `[[tool.uv.index]]` 清华源 + `[tool.pytest.ini_options]` src 布局 pythonpath/testpaths） / `tests/` + `configs/` 骨架（与 src/ 平级）/ CI workflow（GitHub Actions `lint.yml` + GitLab CI `.gitlab-ci.yml`） |

**平台双兼容**（round 14 引入，round 15 完成 skill 端双轨适配）：模板内容同时含 GitHub（`.github/...`）与 GitLab（`.gitlab/...` + `.gitlab-ci.yml`）两套等价文件，bootstrap / sync 一并落地——对端文件在另一平台等同于死文件，互不干扰。skill 中真正调命令行的步骤（如 labels 同步、issue 创建 / 查看）由 `scripts/platform_issue.py` 按 `git remote get-url origin` 自动 dispatch 到 `gh` / `glab`，SKILL.md 不直接调平台 CLI。`.github/labels.yml` schema 跨平台一致，GitLab 项目下也读同一份（不复制 `.gitlab/labels.yml`）。详见 [docs/11-跨项目共享模板与sync-skill/SCHEMA.md](docs/11-跨项目共享模板与sync-skill/SCHEMA.md) 末尾「关于平台双兼容」一节。

工作流：

- **新项目** → `/bootstrap` 选 stack（如 `python-uv`），自动写入相关配置 + 生成 `.agent-template.yml` marker
- **已有老项目** → `/sync-project-config` 进入 adopt 模式补全 marker 并铺模板
- **模板更新后** → 在项目目录跑 `/sync-project-config` 拉新（AI 智能 merge，per-file 用户决策；normal sync 不重跑 stack bootstrap）

**python-uv stack 自动 bootstrap**（round 17 引入，round 25 改用 `uv init --package`）：`/bootstrap` 选 `python-uv` 与 `/sync-project-config` 走 adopt 路径时，除了落配置文件，还会自动跑 `uv init --package`（已有 `pyproject.toml` 时跳过）+ `uv add --dev pytest pytest-cov ruff` + 必要时 `uv tool install pre-commit` + `pre-commit install`。`--package` 让 uv 直接落标准 src 布局（`src/<pkg>/__init__.py` + 含 `[build-system] uv_build` 的 `pyproject.toml`）；模板配套 fragment 把 `[tool.pytest.ini_options] pythonpath=["src"] testpaths=["tests"]` 合并进 pyproject。新项目跑完 `/bootstrap` 立即可 `uv run pytest` / `git commit`，不需要再手敲命令。用户可选「只要配置不要装依赖」跳过整段。详见 [docs/17-python-uv模板自动bootstrap/SUMMARY.md](docs/17-python-uv模板自动bootstrap/SUMMARY.md) 与 [docs/25-python模板与子CLAUDE机制/SUMMARY.md](docs/25-python模板与子CLAUDE机制/SUMMARY.md)。

## 多设备自动同步

每次换设备都手动 `git pull && bash install.sh` 很烦。本仓库提供**双触发**自动同步机制（共用 [scripts/auto-update.sh](scripts/auto-update.sh)，30min 共享节流互不重复）：

| 触发方                                                    | 时机              | 模式        | 输出                                                                                |
| --------------------------------------------------------- | ----------------- | ----------- | ----------------------------------------------------------------------------------- |
| **OS 调度器**（macOS launchd / Linux systemd user timer） | 登录跑 + 每小时跑 | 后台        | 完整日志 → `$AGENT_HOME/logs/auto-update.log`（默认 `~/.claude/`），stdout 静默     |
| **Claude SessionStart hook**                              | 新 session 启动   | `--session` | install 详情入日志；stdout 输出当前版本 + GitHub commit URL，更新后追加 ⚠️ 重启提醒 |

**`bash install.sh` 末尾自动调 [scheduler/install.sh](scheduler/install.sh)** 注册 OS 调度器（macOS 写 `~/Library/LaunchAgents/com.claude-code-global.auto-update.plist` + `launchctl load -w`；Linux 写 `~/.config/systemd/user/` + `systemctl --user enable --now`）。失败 warn 不阻塞主 install。

**关键行为**：

- dirty working tree / non-fast-forward / 网络错误 → 跳过 + 写日志 + **不更新时间戳**（下次重试）
- 只在 master 分支自动 pull
- 第一台设备首次仍要手动 `git clone + bash install.sh`（hook 自举的硬限制）
- 正在跑的旧 Claude session 不会自动应用新配置 —— SessionStart 模式输出会提醒用户 `/exit` 重开

**逃生舱**：取消调度器注册跑 `bash scheduler/uninstall.sh`。详细设计见 [docs/16-自动同步全局配置/SUMMARY.md](docs/16-自动同步全局配置/SUMMARY.md)。

## Backlog 与开发项管理

详细规范见 [`GLOBAL_AGENTS.md`](https://github.com/pkulijing/claude-code-global/blob/master/GLOBAL_AGENTS.md) 中「核心开发模式 → 需求管理」段。要点：

- 开发项以 **issue 为真源**（GitHub / GitLab 自动双轨判定）：详情、讨论、跨轮上下文都沉淀在 issue
- `docs/BACKLOG.md` 是**未关闭 issue 的扁平索引**，按 priority 分组
- 三轴 label：`type:*`（feat/bug/refactor/perf/test/docs）、`area:*`（项目特异）、`priority:*`（P0/P1/P2）
- 工作流：`/backlog` 起新想法 → `/start <issue#>` 开新轮 → `/finish` 收尾时 PR/commit 写 `Closes #N` 自动关 issue（GitHub / GitLab 均原生支持）
