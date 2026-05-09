# Claude Code 全局配置

通过 GitHub 仓库管理 Claude Code 的全局配置（`CLAUDE.md` / `skills/` / `hooks/` / `scripts/` / `scheduler/` / `settings.base.json`）和「跨项目共享开发配置模板」（`templates/`），支持多设备同步与跨项目复用。多设备自动同步（无需手动 `git pull && bash install.sh`）见下文「多设备自动同步」。

开发流程遵循 [`GLOBAL_CLAUDE.md`](GLOBAL_CLAUDE.md) 中定义的「需求 → 计划 → 执行 → 总结」四步模式，开发项以 issue 为真源（GitHub / GitLab 双轨自动判定，详见下文「Backlog 与开发项管理」）。

## 工作原理

Claude Code 会读取 `~/.claude/` 下的全局配置。本仓库通过 `install.sh` 按两种方式部署（软链接 / 合并）：

| 仓库文件             | 部署到                    | 方式                     | 说明                                                                                                       |
| -------------------- | ------------------------- | ------------------------ | ---------------------------------------------------------------------------------------------------------- |
| `GLOBAL_CLAUDE.md`   | `~/.claude/CLAUDE.md`     | 软链接                   | 修改仓库即修改实际配置，`git pull` 即完成同步                                                              |
| `skills/*/`          | `~/.claude/skills/*/`     | 软链接（逐个子目录）     | 不影响 `~/.claude/skills/` 下不属于本仓库的 skill                                                          |
| `hooks/*`            | `~/.claude/hooks/*`       | 软链接（逐个文件）       | hook 脚本本体；由 `settings.base.json` 中带 `# @claude-code-global:<name>` 标记的条目以绝对路径引用        |
| `scripts/*`          | `~/.claude/scripts/*`     | 软链接（逐个文件）       | 被 SKILL.md 显式调用的稳定脚本（如 `platform_issue.py`），SKILL.md 通过 `$HOME/.claude/scripts/...` 引用   |
| `templates/`         | `~/.claude/templates/`    | 软链接（整目录）         | 跨项目共享开发配置模板源，由 `/bootstrap` `/sync-project-config` 读取                                      |
| 仓库根目录           | `~/.claude/global-repo/`  | 软链接                   | 让 `/sync-project-config` 通过 stable 路径访问模板的 git 历史，计算模板版本变化                            |
| `settings.base.json` | `~/.claude/settings.json` | **合并**（非破坏性）     | 本机特有设置保留；仅追加/覆盖基线里声明的项                                                                |
| `scheduler/`         | （不部署）                | 由 `install.sh` 末尾消费 | 渲染模板后写到 `~/Library/LaunchAgents/`（macOS）或 `~/.config/systemd/user/`（Linux），注册自动同步调度器 |

`settings.json` 之所以不软链接，是因为它通常既含跨机共享设置（如 `permissions.allow`），又含本机特有偏好（如 `effortLevel`）。合并规则：

- **object**：递归合并
- **array**：并集去重（如 `permissions.allow` 会把仓库基线里的条目追加进本地已有的列表，而不是覆盖）
- **scalar**：仓库基线胜出；不想跨机共享的标量就别写进 `settings.base.json`
- 多次运行 `install.sh` 幂等；真正发生变化时会先备份成 `settings.json.bak.<timestamp>`

合并依赖 `jq`（macOS 自带 `/usr/bin/jq`；Linux 各发行版用包管理器安装）。

## 安装

```bash
git clone <repo-url> ~/Developer/claude-code-global
bash ~/Developer/claude-code-global/install.sh
```

重复执行 `install.sh` 是安全的（幂等），不会影响 `~/.claude/skills/` 下不属于本仓库的 skill。

## GLOBAL_CLAUDE.md 内容概览

`GLOBAL_CLAUDE.md` 定义了所有项目通用的开发规范：

| 模块                     | 内容                                                                                                                                                                                   |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **核心开发模式**         | 需求 → 计划 → 执行 → 总结的四步协作流程，每个开发项在 `docs/` 下留档（PROMPT.md / PLAN.md / SUMMARY.md）                                                                               |
| **git 规则**             | 中文 semantic commit message，AI 提交须带 Co-authored-by，`.gitignore` 按目录拆分                                                                                                      |
| **环境变量管理**         | `.env.local`（真实值，gitignore）+ `.env.example`（占位符，提交），禁止泄露密钥                                                                                                        |
| **Python 开发规则**      | 使用 uv 管理依赖（禁止 pip install），ruff 格式化，清华 + sjtu 镜像源                                                                                                                  |
| **Backlog / 开发项管理** | issue 为真源（GitHub / GitLab 自动双轨），三轴 label（`type:*` / `area:*` / `priority:*`），三件套 skill：`/backlog` `/start` `/finish`；`docs/BACKLOG.md` 仅作未关闭 issue 的扁平索引 |
| **跨项目共享配置**       | `templates/_common/` + stack 模板（如 `python-uv`）由 `/bootstrap`（新项目）和 `/sync-project-config`（老项目 adopt / 拉新）统一管理                                                   |

## Skills

基线 `settings.base.json` 中预置了 `permissions.allow: ["Skill(*)"]`，让所有 slash command 默认放行，避免反复弹权限确认。

本仓库提供以下 skill。`/backlog` `/start` `/finish` 三件套配合 `/commit` 形成完整的「issue 驱动」开发闭环；其余按需调用。

| Skill                  | 用途                                                                                                                                                                             |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/backlog`             | 把一条想法走 issue templates 创建成 issue（GitHub / GitLab 自动判定，含三轴 label），并在 `docs/BACKLOG.md` 索引中加一行                                                         |
| `/start`               | 开新一轮开发：创建 `docs/<编号>-<描述>/`，撰写 PROMPT.md，进入计划模式撰写 PLAN.md 等用户确认后再写代码。支持 `#<issue 号>` / GitHub or GitLab issue URL（推荐），也支持自由描述 |
| `/finish`              | 收尾本轮：撰写 SUMMARY.md → 关联并关闭 issue（如有 `Closes #N`，GitHub / GitLab 均原生支持） → 更新 BACKLOG.md → `/devtree` → 必要时同步 README → `/commit`                      |
| `/commit`              | 分析当前变更，自动生成中文 semantic commit message 并提交，末尾自动附加 Co-authored-by                                                                                           |
| `/bootstrap`           | 为空项目搭建文档骨架（README / CLAUDE / DEVTREE）+ 选 stack 铺设跨项目模板，仅在项目首次开发前调用一次                                                                           |
| `/sync-project-config` | 把本仓库管理的「跨项目共享开发配置模板」最新变化同步进当前项目；含 adopt 模式（无 marker 老项目首次接入）                                                                        |
| `/devtree`             | 依据 `docs/DEVTREE.md` 中作者维护的 Epic 结构，重新生成可视化图表和节点索引                                                                                                      |
| `/rebase`              | 诊断本地分支分叉并按清单引导完成 rebase，历史保持 FF 直线                                                                                                                        |
| `/pybump`              | 升级 Python 项目版本号（`pyproject.toml`），提交并打 tag                                                                                                                         |
| `/clean-local-setting` | 清理项目 `.claude/settings.local.json` 中的 permissions 列表（分类、交互确认、保留备份）                                                                                         |

## Hooks

`hooks/` 下放跨项目共用的 hook 脚本，由 `install.sh` 软链到 `~/.claude/hooks/`，并由 `settings.base.json` 中的 hook 条目以绝对路径 `$HOME/.claude/hooks/...` 引用。

| Hook                               | 触发时机                  | 作用                                                                                                                                                       |
| ---------------------------------- | ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `fix-after-edit.sh`                | PostToolUse（Edit/Write） | 编辑后自动跑项目本地工具链（如 `ruff check --fix`、`prettier --write`），让 AI 改动跟项目 formatter 输出对齐，避免 VS Code 保存时 formatOnSave 触发大 diff |
| `scripts/auto-update.sh --session` | SessionStart（startup）   | 新 Claude session 启动时静默拉本仓库更新；输出当前版本 hash + GitHub commit 链接，更新后追加重启提醒。详见下文「多设备自动同步」                           |

由本仓库管理的 hook 条目以 `# @claude-code-global:<hook-name>` 注释作为身份标记；`install.sh` 通过这个标记做集合差分（增 / 删 / 同名替换），不影响用户手动添加的 hook。

## Scripts

`scripts/` 下是被 SKILL.md 显式调用的稳定脚本（非 hook、非 skill），由 `install.sh` 软链到 `~/.claude/scripts/`，SKILL.md 通过绝对路径 `$HOME/.claude/scripts/<name>` 引用。

| Script              | 用途                                                                                                                                                                                                                        |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `platform_issue.py` | 跨平台 issue / label / repo helper：封装 `gh` ↔ `glab` 双轨调用，按 `git remote get-url origin` 自动 dispatch。被 `/backlog` `/start` `/bootstrap` `/sync-project-config` 调用。零第三方依赖（仅 stdlib），含 `--self-test` |
| `auto-update.sh`    | 多设备自动同步主脚本：跑 `git fetch` → ff-only `git pull` → `bash install.sh`，被 OS 调度器（launchd/systemd）和 Claude SessionStart hook 共用，30min 共享节流。详见下文「多设备自动同步」                                  |

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

| 模板         | 适用项目                        | 内容（节选）                                                                                                                                                                            |
| ------------ | ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `_common/`   | 所有项目（其他 stack 自动叠加） | 通用 issue templates（GitHub + GitLab 双轨）、`.github/labels.yml` 三轴 label、`.prettierrc` 等                                                                                         |
| `python-uv/` | Python 项目（uv + ruff）        | `.gitignore` / `.pre-commit-config.yaml` / `.vscode/`（formatOnSave + ruff）/ `pyproject.toml [tool.ruff]` 片段 / CI workflow（GitHub Actions `lint.yml` + GitLab CI `.gitlab-ci.yml`） |

**平台双兼容**（round 14 引入，round 15 完成 skill 端双轨适配）：模板内容同时含 GitHub（`.github/...`）与 GitLab（`.gitlab/...` + `.gitlab-ci.yml`）两套等价文件，bootstrap / sync 一并落地——对端文件在另一平台等同于死文件，互不干扰。skill 中真正调命令行的步骤（如 labels 同步、issue 创建 / 查看）由 `scripts/platform_issue.py` 按 `git remote get-url origin` 自动 dispatch 到 `gh` / `glab`，SKILL.md 不直接调平台 CLI。`.github/labels.yml` schema 跨平台一致，GitLab 项目下也读同一份（不复制 `.gitlab/labels.yml`）。详见 [docs/11-跨项目共享模板与sync-skill/SCHEMA.md](docs/11-跨项目共享模板与sync-skill/SCHEMA.md) 末尾「关于平台双兼容」一节。

工作流：

- **新项目** → `/bootstrap` 选 stack（如 `python-uv`），自动写入相关配置 + 生成 `.cc-template.yml` marker
- **已有老项目** → `/sync-project-config` 进入 adopt 模式补全 marker 并铺模板
- **模板更新后** → 在项目目录跑 `/sync-project-config` 拉新（AI 智能 merge，per-file 用户决策）

## 多设备自动同步

每次换设备都手动 `git pull && bash install.sh` 很烦。本仓库提供**双触发**自动同步机制（共用 [scripts/auto-update.sh](scripts/auto-update.sh)，30min 共享节流互不重复）：

| 触发方                                                    | 时机              | 模式        | 输出                                                                                |
| --------------------------------------------------------- | ----------------- | ----------- | ----------------------------------------------------------------------------------- |
| **OS 调度器**（macOS launchd / Linux systemd user timer） | 登录跑 + 每小时跑 | 后台        | 完整日志 → `~/.claude/logs/auto-update.log`，stdout 静默                            |
| **Claude SessionStart hook**                              | 新 session 启动   | `--session` | install 详情入日志；stdout 输出当前版本 + GitHub commit URL，更新后追加 ⚠️ 重启提醒 |

**`bash install.sh` 末尾自动调 [scheduler/install.sh](scheduler/install.sh)** 注册 OS 调度器（macOS 写 `~/Library/LaunchAgents/com.claude-code-global.auto-update.plist` + `launchctl load -w`；Linux 写 `~/.config/systemd/user/` + `systemctl --user enable --now`）。失败 warn 不阻塞主 install。

**关键行为**：

- dirty working tree / non-fast-forward / 网络错误 → 跳过 + 写日志 + **不更新时间戳**（下次重试）
- 只在 master 分支自动 pull
- 第一台设备首次仍要手动 `git clone + bash install.sh`（hook 自举的硬限制）
- 正在跑的旧 Claude session 不会自动应用新配置 —— SessionStart 模式输出会提醒用户 `/exit` 重开

**逃生舱**：取消调度器注册跑 `bash scheduler/uninstall.sh`。详细设计见 [docs/16-自动同步全局配置/SUMMARY.md](docs/16-自动同步全局配置/SUMMARY.md)。

## Backlog 与开发项管理

详细规范见 [`GLOBAL_CLAUDE.md`](GLOBAL_CLAUDE.md) 中「Backlog 与开发项管理」段。要点：

- 开发项以 **issue 为真源**（GitHub / GitLab 自动双轨判定）：详情、讨论、跨轮上下文都沉淀在 issue
- `docs/BACKLOG.md` 是**未关闭 issue 的扁平索引**，按 priority 分组
- 三轴 label：`type:*`（feat/bug/refactor/perf/test/docs）、`area:*`（项目特异）、`priority:*`（P0/P1/P2）
- 工作流：`/backlog` 起新想法 → `/start <issue#>` 开新轮 → `/finish` 收尾时 PR/commit 写 `Closes #N` 自动关 issue（GitHub / GitLab 均原生支持）
