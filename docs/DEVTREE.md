# 开发树

## 分类图例

| 图标 | 类型 | 说明                      |
| ---- | ---- | ------------------------- |
| 🌱   | 初建 | 某功能域首次从零建立      |
| ✨   | 功能 | 扩展用户可感知的能力      |
| 🐛   | 修复 | 纠正缺陷或回归            |
| 🏗️   | 重构 | 内部结构改善,用户行为不变 |
| 📦   | 工程 | 打包/CI/分发/工具链       |
| 🔬   | 探索 | 调研,可能被搁置           |

---

## 可视化

```mermaid
%%{init: {'flowchart': {'rankSpacing': 30, 'nodeSpacing': 20}}}%%
graph TD
  classDef genesis  fill:#d4edda,stroke:#28a745,color:#155724,font-weight:bold
  classDef feature  fill:#cce5ff,stroke:#0d6efd,color:#003d8f,font-weight:bold
  classDef bugfix   fill:#f8d7da,stroke:#dc3545,color:#721c24,font-weight:bold
  classDef refactor fill:#fff3cd,stroke:#ffc107,color:#664d03,font-weight:bold
  classDef infra    fill:#e2d9f3,stroke:#6f42c1,color:#3d1a78,font-weight:bold
  classDef research fill:#e2e3e5,stroke:#6c757d,color:#383d41,font-weight:bold
  classDef epic     fill:#f8f9fa,stroke:#adb5bd,color:#495057,font-weight:bold,font-size:15px

  ROOT["claude-code-global"]:::epic
  ROOT --> base["基础机制"]:::epic
  ROOT --> toolchain["开发工具链"]:::epic
  base --> e_cc_reuse
  base --> e_cc_merge
  base --> e_userconfig
  base --> e_template
  base --> e_multi_agent
  base --> e_constitution
  toolchain --> e_bootstrap
  toolchain --> e_finish
  toolchain --> devmgmt["开发项管理"]:::epic
  toolchain --> codemgmt["代码管理"]:::epic
  devmgmt --> e_devtree
  devmgmt --> e_backlog
  codemgmt --> e_rebase
  codemgmt --> e_format
  toolchain --> e_content

  subgraph e_cc_reuse["✅ CC 工具复用"]
    direction TB
    N0["🌱 0 · 安装脚本"]:::genesis
    N2["🏗️ 2 · 重构项目 CLAUDE 文件结构"]:::refactor
    N16["📦 16 · 自动同步全局配置"]:::infra
    N19["🐛 19 · 修复 Linux 自动同步缺陷"]:::bugfix
    N0 ~~~ N2
    N2 ~~~ N16
    N16 ~~~ N19
  end

  subgraph e_cc_merge["✅ CC 配置合并"]
    direction TB
    N6["📦 6 · settings 合并机制"]:::infra
    N8["📦 8 · 权限配置治理与清理 skill"]:::infra
    N6 ~~~ N8
  end

  subgraph e_userconfig["🔄 用户可配置项"]
    direction TB
    N27["🌱 27 · 用户可配置项机制"]:::genesis
  end

  subgraph e_template["🔄 项目模板机制"]
    direction TB
    N11["✨ 11 · 跨项目共享模板与 sync-skill"]:::feature
    N14["✨ 14 · 模板支持 GitLab 双轨"]:::feature
    N15["✨ 15 · 三件套 skill 支持 GitLab 双轨"]:::feature
    N17["✨ 17 · python-uv 模板自动 bootstrap"]:::feature
    N18["✨ 18 · sync 支持无 stack 路径"]:::feature
    N30["✨ 30 · 前端栈规则与 scaffold 模板"]:::feature
    N31["📦 31 · python 模板默认 only-managed"]:::infra
    N32["🐛 32 · vscode 配置落根跨栈合并"]:::bugfix
    N11 ~~~ N14
    N14 ~~~ N15
    N15 ~~~ N17
    N17 ~~~ N18
    N18 ~~~ N30
    N30 ~~~ N31
    N31 ~~~ N32
  end

  subgraph e_multi_agent["🔄 多 Agent 兼容"]
    direction TB
    N20["🔬 20 · CC 与 Codex 双兼容调研"]:::research
    N22["✨ 22 · CC 与 Codex 双兼容主链"]:::feature
    N20 ~~~ N22
  end

  subgraph e_constitution["🔄 全局宪法治理"]
    direction TB
    N24["🏗️ 24 · 精简宪法与会话标题约定排查"]:::refactor
    N25["🏗️ 25 · python 模板与子 CLAUDE 机制"]:::refactor
    N28["✨ 28 · lark 规则文档"]:::feature
    N24 ~~~ N25
    N25 ~~~ N28
  end

  subgraph e_bootstrap["✅ 项目初始化"]
    direction TB
    N9["📦 9 · 创建 bootstrap-skill"]:::infra
  end

  subgraph e_finish["✅ 开发项收尾"]
    direction TB
    N1["✨ 1 · 创建 commit-skill"]:::feature
    N13["✨ 13 · finish 收尾同步 README"]:::feature
    N21["✨ 21 · finish 自动收尾 worktree"]:::feature
    N23["✨ 23 · finish 跨项目沉淀提 issue"]:::feature
    N26["🐛 26 · finish 沉淀 issue 强制打 label"]:::bugfix
    N1 ~~~ N13
    N13 ~~~ N21
    N21 ~~~ N23
    N23 ~~~ N26
  end

  subgraph e_devtree["✅ DEVTREE 管理"]
    direction TB
    N4["✨ 4 · 创建 devtree-skill"]:::feature
    N5["🏗️ 5 · 重构 devtree-skill-epic 模型"]:::refactor
    N4 ~~~ N5
  end

  subgraph e_backlog["✅ BACKLOG 管理"]
    direction TB
    N7["✨ 7 · 创建 backlog-skill"]:::feature
    N12["✨ 12 · backlog 改为 issue 驱动"]:::feature
    N7 ~~~ N12
  end

  subgraph e_rebase["✅ rebase 工作流"]
    direction TB
    N3["✨ 3 · 创建 rebase-skill"]:::feature
  end

  subgraph e_format["🔄 代码格式化"]
    direction TB
    N10["📦 10 · 接入 prettier 格式化 hook"]:::infra
  end

  subgraph e_content["🔄 内容创作 skill"]
    direction TB
    N29["🐛 29 · paper-read 资产就近存放"]:::bugfix
  end
```

---

## 节点索引

> 最后更新：2026-06-15 | 共 33 轮

| #   | 名称                           | 类型    | 所属 Epic      | 一句话描述                                                                                                                                                                                                                                                    |
| --- | ------------------------------ | ------- | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0   | 安装脚本                       | 🌱 初建 | CC 工具复用    | 通过符号链接将 CLAUDE.md 与 skills 部署到 ~/.claude/                                                                                                                                                                                                          |
| 1   | 创建 commit-skill              | ✨ 功能 | 开发项收尾     | 创建 /commit skill，补全 /finish 流程的最后一环                                                                                                                                                                                                               |
| 2   | 重构项目 CLAUDE 文件结构       | 🏗️ 重构 | CC 工具复用    | 分离全局规范与项目说明，解决 CLAUDE.md 语义错位                                                                                                                                                                                                               |
| 3   | 创建 rebase-skill              | ✨ 功能 | rebase 工作流  | 创建 /rebase skill，诊断+分段引导本地分叉整理                                                                                                                                                                                                                 |
| 4   | 创建 devtree-skill             | ✨ 功能 | DEVTREE 管理   | 创建 /devtree skill，可视化开发树并集成到 /finish 流程                                                                                                                                                                                                        |
| 5   | 重构 devtree-skill-epic 模型   | 🏗️ 重构 | DEVTREE 管理   | 引入 Epic 层，叶 Epic 为 subgraph 卡片，重构可视化方案                                                                                                                                                                                                        |
| 6   | settings 合并机制              | 📦 工程 | CC 配置合并    | install.sh 新增 settings.base.json 与本地 settings.json 的非破坏性合并（对象递归、数组并集）                                                                                                                                                                  |
| 7   | 创建 backlog-skill             | ✨ 功能 | BACKLOG 管理   | 创建 /backlog skill，交互式扩写 + 归类后追加条目到 docs/BACKLOG.md                                                                                                                                                                                            |
| 8   | 权限配置治理与清理 skill       | 📦 工程 | CC 配置合并    | 调研 CC 权限匹配规则，重写 settings.base.json，新增 /clean-local-setting skill，清理 5 项目 local 配置（257→54 条）                                                                                                                                           |
| 9   | 创建 bootstrap-skill           | 📦 工程 | 项目初始化     | 新增 /bootstrap 处理空项目骨架（README/CLAUDE/DEVTREE），改 /devtree 支持冷启动，改 /start 加前置检查                                                                                                                                                         |
| 10  | 接入 prettier 格式化 hook      | 📦 工程 | 代码格式化     | 新增全局 PostToolUse hook（.py/.md 编辑后自动格式化），bootstrap skill 增写 .prettierrc 与项目本地推荐配置约定                                                                                                                                                |
| 11  | 跨项目共享模板与 sync-skill    | ✨ 功能 | 项目模板机制   | 新增 templates/<stack>/，扩展 /bootstrap 与新增 /sync-project-config，跨项目模板分发 + AI 智能 merge + marker 管理                                                                                                                                            |
| 12  | backlog 改为 issue 驱动        | ✨ 功能 | BACKLOG 管理   | 把 backlog 工作流改为 GitHub Issue 真源（三轴 label + issue templates + Closes #N），引入 \_common 伪 stack 承载 stack-无关资源                                                                                                                               |
| 13  | finish 收尾同步 README         | ✨ 功能 | 开发项收尾     | /finish 末尾新增 Step 3.5（README review），命中触发清单则同步更新 README；本轮一次性补齐 README 基线（hooks / 模板 / 全量 skill 表 / BACKLOG 工作流）                                                                                                        |
| 14  | 模板支持 GitLab 双轨           | ✨ 功能 | 项目模板机制   | \_common 与 python-uv 模板同时落 GitHub + GitLab 两套等价文件（issue templates + CI），bootstrap/sync 的 gh label create 按 origin 平台三分支判定                                                                                                             |
| 15  | 三件套 skill 支持 GitLab 双轨  | ✨ 功能 | 项目模板机制   | 新增 scripts/platform_issue.py helper（封装 gh ↔ glab 双轨调用），让 /backlog /start /finish /bootstrap /sync-project-config 在 GitLab 项目上等价可用                                                                                                         |
| 16  | 自动同步全局配置               | 📦 工程 | CC 工具复用    | scripts/auto-update.sh + scheduler/(launchd/systemd) + SessionStart hook 三位一体，多设备自动 git pull + install 并在 Claude 启动时反馈版本/更新                                                                                                              |
| 17  | python-uv 模板自动 bootstrap   | ✨ 功能 | 项目模板机制   | bootstrap / sync adopt 在 python-uv stack 自动跑 uv init --bare + uv add --dev pytest pytest-cov ruff + pre-commit install，新项目即开即可 uv run pytest / git commit                                                                                         |
| 18  | sync 支持无 stack 路径         | ✨ 功能 | 项目模板机制   | /sync-project-config 放宽 `len(stacks) ≤ 1` 断言，adopt 加「无 stack（只 \_common）」选项，length=0 项目把 skipped 写在 marker 顶层，闭环可跑                                                                                                                 |
| 19  | 修复 Linux 自动同步缺陷        | 🐛 修复 | CC 工具复用    | 修开发项 16 Linux 侧两缺陷：systemd timer 改 `OnCalendar=hourly` 解「燃尽」；auto-update.sh 加 untracked 撞名预检，归入「跳过」而非反复 git pull failed                                                                                                       |
| 20  | CC 与 Codex 双兼容调研         | 🔬 探索 | 多 Agent 兼容  | 调研 Codex 配置约定与本仓库耦合度，确认 ~85% 内容 Agent-neutral，提出「单一真源 + install.sh 双轨」方案 A 并落 issue #8                                                                                                                                       |
| 21  | finish 自动收尾 worktree       | ✨ 功能 | 开发项收尾     | /start 默认建独立 worktree、/finish 新增 Step 5 自动 rebase+FF merge+清理，工作流并行化；附 GLOBAL_CLAUDE.md 简述与 .claude/.gitignore                                                                                                                        |
| 22  | CC 与 Codex 双兼容主链         | ✨ 功能 | 多 Agent 兼容  | GLOBAL_AGENTS.md 改名 + skills 中性化 + 新增 codex.config.base.toml + install.sh 双轨重构（deploy_agent / merge_toml），单一真源部署到 ~/.claude 与 ~/.codex                                                                                                  |
| 23  | finish 跨项目沉淀提 issue      | ✨ 功能 | 开发项收尾     | /finish 新增「跨项目可沉淀流程反思」步，对跨项目资产候选可直接向 claude-code-global 跨仓库提 issue（不进 BACKLOG）；platform_issue.py 加 --repo；顺手把步骤编号重排为连续整数                                                                                 |
| 24  | 精简宪法与会话标题约定排查     | 🏗️ 重构 | 全局宪法治理   | 精简 GLOBAL_AGENTS.md 冗余实现细节（删「会话标题约定」「项目本地推荐配置」两节、Backlog 节并入「核心开发模式 → 需求管理」），并查实会话标题由 ai-title 摘要器生成、Round 前缀机制上无效                                                                       |
| 25  | python 模板与子 CLAUDE 机制    | 🏗️ 重构 | 全局宪法治理   | 引入 `rules/<topic>.md` 领域规则文档机制（首例 `rules/python.md` 含 #12 七条 Python 风格 + 原 Python 章节），python-uv 模板接入 `uv init --package` 落标准 src 布局 + pytest fragment                                                                         |
| 26  | finish 沉淀 issue 强制打 label | 🐛 修复 | 开发项收尾     | helper 对「跨仓库 `--repo` + 零 label」创建强制拦截（`--allow-no-label` 逃生）、`label-list` 支持 `--repo` 跨仓库校验；finish Step 3.5 加创建前 label 校验与「失败绝不丢 label」兜底；GLOBAL_AGENTS.md 补硬约束；回补 #12 三轴 label                          |
| 27  | 用户可配置项机制               | 🌱 初建 | 用户可配置项   | 引入扁平 env 用户配置（仓库外、user-wins seed、CC/Codex 共享），首例 git init 默认分支 → install.sh 设 git config --global init.defaultBranch；附 verify 脚本与 DESIGN 设计文档                                                                               |
| 28  | lark 规则文档                  | ✨ 功能 | 全局宪法治理   | 新增 rules/lark.md 领域规则文档（lark-cli 创作飞书云文档默认加 `⚡ Crafted with lark-cli` 署名行 + docx 实操技巧），GLOBAL_AGENTS.md 加并列指针节                                                                                                             |
| 29  | paper-read 资产就近存放        | 🐛 修复 | 内容创作 skill | paper-read skill 图片资产默认从「固定根目录 assets」改为「与笔记 markdown 同级 assets/」就近原则，引用用相对路径                                                                                                                                              |
| 30  | 前端栈规则与 scaffold 模板     | ✨ 功能 | 项目模板机制   | 新增 rules/frontend.md + templates/react-vite/ 前端 scaffold（React 19 + Vite 6 + TS strict + tailwind v4 + shadcn + Biome，npmmirror），bootstrap/sync 升级为多 stack 叠加 + stack.yml 自描述 path，前后端正交可同仓并存                                     |
| 31  | python 模板默认 only-managed   | 📦 工程 | 项目模板机制   | python-uv 模板新增 `[tool.uv] python-preference=only-managed` fragment + install.sh 以 user-wins seed 系统级 `~/.config/uv/uv.toml`，让 uv 全权管 python、避免系统 python 缺 `Python.h` 致 C 扩展编译失败；rules/python.md §1 记坑                            |
| 32  | vscode 配置落根跨栈合并        | 🐛 修复 | 项目模板机制   | 泛化 fragment 机制新增 `.vscode/*.json.fragment` 类，各 stack 编辑器配置合并进项目根 `.vscode/`（修 react-vite 落 `frontend/.vscode/`、打开仓库根 biome 推荐不触发）；react-vite settings 全语言作用域化防污染 Python；bootstrap/sync 加 JSON 合并 + 迁移去重 |

---

## Epic 结构

> 由作者手动维护。AI 只负责「可视化」和「节点索引」两个区块。

### 基础机制

#### CC 工具复用

- 状态：已完成
- 轮次：0, 2, 16, 19

#### CC 配置合并

- 状态：已完成
- 轮次：6, 8

#### 用户可配置项

- 状态：进行中
- 轮次：27

#### 项目模板机制

- 状态：进行中
- 轮次：11, 14, 15, 17, 18, 30, 31, 32

#### 多 Agent 兼容

- 状态：进行中
- 轮次：20, 22

#### 全局宪法治理

- 状态：进行中
- 轮次：24, 25, 28

### 开发工具链

#### 项目初始化

- 状态：已完成
- 轮次：9

#### 开发项收尾

- 状态：已完成
- 轮次：1, 13, 21, 23, 26

#### 开发项管理

##### DEVTREE 管理

- 状态：已完成
- 轮次：4, 5

##### BACKLOG 管理

- 状态：已完成
- 轮次：7, 12

#### 代码管理

##### rebase工作流

- 状态：已完成
- 轮次：3

##### 代码格式化

- 状态：进行中
- 轮次：10

#### 内容创作 skill

- 状态：进行中
- 轮次：29
