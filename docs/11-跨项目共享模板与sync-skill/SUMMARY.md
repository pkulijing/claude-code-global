# SUMMARY：跨项目共享模板与 sync skill

## 开发项背景

上一轮 `feat(11): 加 lint 闸门` 补齐了 lint 拦截链中的两环（PostToolUse hook + `/commit` 闸门），但**业界标准是四层**：

1. 编辑器内 LSP（fix-on-save）
2. AI 编辑后 hook（已实现）
3. **commit 前 pre-commit framework**（项目级配置，本仓库不管）
4. **CI**（项目级配置，本仓库不管）

第 3、4 层是项目级配置，引出更宏观的问题：除 CC 自身配置外，还有一类「跨项目共用的开发配置」（pre-commit、`.vscode/`、CI、`pyproject.toml [tool.ruff]` 段、`.gitignore` 等）需要统一管理机制 —— 否则每个新项目重做、老项目同步靠记忆。

经讨论，**单仓库统管**两类资源（CC 自身 + 跨项目模板），通过两个 skill 入口完成 propagate（`/bootstrap` 处理新项目、`/sync-project-config` 处理老项目）。

## 实现方案

### 关键设计

经 Q1~Q11 拍板（详见 [PROMPT.md](PROMPT.md)）：

1. **仓库一身二职**：保留 CC 配置职责，新增 `templates/<stack>/` 资源类
2. **stack 颗粒度**：按技术栈切，本轮只做 `python-uv` 一个 stack
3. **文件 scope**：每个模板文件标 `__root__/`（写到 git 根）或 `__subpath__/`（写到 stack subdir，对单 stack 项目即根）。多 stack 时 root 文件由 AI 跨 stack merge（本轮不实现）
4. **Marker schema**：`.cc-template.yml` 在项目根、commit 进 git，含 `source` / `template_commit` / `bootstrap_time` / `stacks: [{stack, path, skipped: [...]}]`。`stacks` 是列表为多 stack 留位，本轮 sync 断言 length=1 + path=`.`
5. **AI 智能 merge**：sync 中 per-file 四象限分析（模板侧 M/A/D × 项目侧是否自定义），AI 给出建议；用户批量决策；不机械 replace/merge
6. **skipped 持久化**：marker 中 skipped 项带 `skipped_at_commit`，sync 时 `git log <skipped_at_commit>..HEAD -- <file>` 判断模板那条之后是否变了 → 没变则自动跳过、变了则重新提案
7. **Adopt 模式**：sync 在无 marker 项目里走 adopt 分支（用户选 stack → 全套用），不动 bootstrap 的"空目录"语义
8. **install.sh 扩展**：新增两条软链 `templates/` → `~/.claude/templates/`、仓库根 → `~/.claude/global-repo`（让 sync 用 `git -C ~/.claude/global-repo diff` 拿模板版本变化）
9. **AI 直接读写 YAML**：不引入 yq / pyyaml 依赖，对齐 skills 的 AI 驱动风格

### 开发内容概括

按 [PLAN.md](PLAN.md) 八步顺序实现：

- **Step 1**：`templates/python-uv/` 7 个文件（pre-commit-config / gitignore / lint workflow / prettierrc / ruff fragment / vscode settings & extensions）
- **Step 2**：`install.sh` 增加两条 `link_item` 调用，复用既有 helper
- **Step 3**：`/bootstrap` SKILL.md 新增 Step 3.{1..4}「模板初始化」流程（探测 stack → AskUserQuestion 选择 → 复制 + 智能合并 pyproject 段 → 写 marker），删除原独立的 `.prettierrc` 写入步骤（被模板取代）；收尾反馈同步更新
- **Step 4**：新增 `skills/sync-project-config/SKILL.md`，含前置检查 / 模式判断 / Normal sync 6 步 / Adopt 模式 / 用户批量决策 / 执行回写 marker 完整流程；多 stack 防误用断言写明
- **Step 5**：`GLOBAL_CLAUDE.md`「项目本地推荐配置」段重写为「由 stack 模板统一管理」，列出 python-uv stack 的具体内容
- **Step 6**：写 `SCHEMA.md`，含字段定义 + 单 stack / 多 stack 两种示例

### 额外产物

- **PROMPT.md / PLAN.md / SCHEMA.md** 三份完整设计文档
- **[memory] feedback_dependency_versions.md**：记录"模板里凭印象写过时版本号"这一错误，未来撰写带版本号的模板/配置前必须实查
- **机械验证**：JSON / YAML 全部语法正确；pre-commit 在合成 test 项目里跑通所有 hooks（ruff-check 抓到 unused import、ruff-format 真的 reformat 错误代码）

## 局限性

1. **多 stack monorepo 仅 schema 就位、逻辑未实现**：sync 启动时显式 assert length=1 + path=`.`，多 stack 直接报错。AI 跨 stack merge（如 `.pre-commit-config.yaml` 同时挂 ruff + eslint hooks）留至后续 round
2. **本轮只做 python-uv 一个 stack**：node、`_common`（伪 stack 承载完全 stack-无关的根文件）等其他 stack 待真实需求驱动
3. **CI 配置目前是 inline `lint.yml`**，未引用 `<user>/.github` 仓库的 reusable workflow。后续 round 部署 reusable workflow 后可把模板里的 `lint.yml` 改成 `uses:` 引用，CI 升级一次受益所有项目
4. **bootstrap / sync 的端到端验证**仍依赖用户在真实项目里跑（涉及 AskUserQuestion 等交互）。本轮只做了机械层面的语法/install 软链/pre-commit hook 实测，剩余路径在用户接下来使用过程中验收
5. **YAML 由 AI 解析**有误读风险（rare），marker 字段简单 + skill 在写之前自我回显让用户确认作为防线
6. **无 broken-symlink 清理**：install.sh 不主动删 `~/.claude/hooks/` 里指向已不存在源的失效软链（之前的取舍：差分集合管 settings.json 条目，不越界管软链文件）
7. **依赖版本固定为 2026-04 时点最新**：`ruff-pre-commit@v0.15.12`、`pre-commit-hooks@v6.0.0`、`actions/checkout@v6`、`astral-sh/setup-uv@v8`。后续模板更新时需手动 bump，没有自动 dependabot 类机制

## 后续 TODO

按重要性 / 时机：

1. **多 stack monorepo 支持**：bootstrap 支持反复添加 stack（不同 subpath）、sync 处理 `stacks` 多项、AI 跨 stack root 文件 merge
2. **`<user>/.github` reusable workflows 部署**：把 lint.yml 改成单点 CI 配置，所有项目自动受益
3. **更多 stack**：node / `_common` / 视真实项目需要扩
4. **Marker 校验 hook**（项目侧 pre-commit）：每次 commit 验证 `.cc-template.yml` 存在 + schema 合规
5. **sync 的 dry-run 模式**：只列 TODO 不执行，便于先看后做
6. **依赖版本自动更新通道**：考虑给 templates/ 自己加 dependabot / pre-commit autoupdate 周期
7. **「凭印象写版本」反模式自检**：把这次踩的坑写进相关 skill 的 reminder（写模板前用 GitHub API 查 latest tag）

后续每条单独以 `/start` 新轮次推进。
