# Round 22：CC 与 Codex 双兼容主链（#1-#7）— SUMMARY

> 来自 [#8 支持 CC 与 Codex 双兼容（单一真源 + install.sh 双轨部署）](https://github.com/pkulijing/claude-code-global/issues/8)
> 本轮完成 issue #8 的 8 个 checklist 子项中的 **#1-#7**；#8（双装端到端实测）按计划留给作者自测。

## 开发项背景

作者现在同时使用 Claude Code (CC) 与 OpenAI Codex 两个 coding agent。本仓库管理的开发宪法 + 工作流 skills + 自动 lint hooks 原本完全为 CC 设计：软链到 `~/.claude/`、settings 用 CC 私有 JSON schema。Codex 那端在用，却什么辅助都没有，开发体验割裂、两端配置即将漂移。

Round 20 调研确认两端约定高度对称（`AGENTS.md` 跨工具标准、SKILL.md frontmatter 相同、hooks 事件名相同），仓库内容约 85% 本就 agent-neutral，选定**方案 A**：单一真源 + 双轨 install。本轮把方案 A 的主链落地。

希望达到：跑一次 `bash install.sh` 自动给 CC 与 Codex 两端都装好（缺哪端只装哪端），skills / hooks / 主指令文档单份维护，新增 skill / 改 hook 不用写两遍，且已有 CC 工作流不退化。

## 实现方案

### 关键设计

1. **`install.sh` 是唯一感知 agent 差异的层**。仓库产物（skills / hooks / scripts / 主指令文档）保持单份单一真源，不分裂为 `for-cc/` 和 `for-codex/`。`install.sh` 抽出 `deploy_agent` 函数，对 `~/.claude/` 与 `~/.codex/` 各调一次；检测哪端 home 目录存在就装哪端。
2. **`AGENTS.md` 作为锚点**。`GLOBAL_CLAUDE.md` 改名 `GLOBAL_AGENTS.md`，软链为 CC 的 `~/.claude/CLAUDE.md` 与 Codex 的 `~/.codex/AGENTS.md`，对齐跨工具事实标准。
3. **TOML marker 块整体重写**。Codex 配置是 TOML，无 jq 可用。`merge_toml` 用一对 marker 注释（`# >>> claude-code-global managed >>>` … `# <<< … <<<`）包裹托管块，用 awk 做「删旧块插新块」。marker 块只含 `[[hooks.*]]` 数组表，可安全追加到任意 TOML 文件末尾而不破坏结构；用户在块外手写的内容（`approval_policy` / `[projects]` 等）一律保留。
4. **skill body 工具名中性化**。CC 的 `AskUserQuestion` 与 Codex 的 `RequestUserInputQuestion` 概念等价；skill body 里 8 处工具名改成自然语言「询问用户」后，CC 仍会触发 native tool，Codex 也走自己的等价 API，两端都不破坏。
5. **`$AGENT_HOME` 变量化**。`auto-update.sh` 的日志 / 节流戳路径由硬编码 `~/.claude/` 改为 `${AGENT_HOME:-$HOME/.claude}`，使 Codex-only 机器也能正常落日志。

### 开发内容概括

- **#1** `git mv GLOBAL_CLAUDE.md GLOBAL_AGENTS.md`；正文「称呼」段增补 Codex / Coding Agent 术语，「计划」步与「会话标题约定」段的 CC-specific 表述泛化为 Coding Agent。改名传播到 `CLAUDE.md`、`skills/bootstrap`、`.github/labels.yml`。
- **#2** skills body 9 处中性化：8 处 `AskUserQuestion` → 「询问用户」自然语言；`/start` 1 处「进入计划模式」→「起草 PLAN.md 并请用户确认」。
- **#3** 新增 `codex.config.base.toml`：marker 块镜像 `settings.base.json` 的 `SessionStart`（auto-update）+ `PostToolUse`（fix-after-edit）hook 注册；块外给推荐的 `approval_policy = "on-request"` / `sandbox_mode = "workspace-write"`（仅首次创建写入）。
- **#4** `install.sh` 双轨重构：新增 `deploy_agent` 函数 + `merge_toml`/`extract_toml_block`；检测两端 home 目录按需部署；两端都不存在时 warn 退出；末尾若部署了 Codex 打印 `/hooks` review 提示。
- **#5** `.cc-template.yml → .agent-template.yml`（含本仓库根的 marker 文件）；`/sync-project-config` 的「模式判断」段新增「旧名 marker 自动迁移」步骤（见旧名且无新名 → `git mv`；新旧并存 → 报冲突停手）。
- **#6** `auto-update.sh` 加 `AGENT_HOME` 变量；scheduler 模板注入 `{{AGENT_HOME}}` 占位符（systemd `Environment=` / launchd `EnvironmentVariables`）；`scheduler/install.sh` 智能选取 agent home。
- **#7** README 新增「同时支持 Claude Code 与 Codex」章节（设计依据、双装方式、部署对照表、已知限制）+ 就地修订改名后过期的字面量。

### 额外产物

- `docs/22-CC与codex双兼容主链/` 下的 PROMPT.md / PLAN.md / SUMMARY.md。
- 测试以一次性 harness 形式做（从 `install.sh` 提取 `merge_toml` + `extract_toml_block` 在 `/tmp` 验证 4 场景），未沉淀为仓库内测试文件 —— install.sh 属 shell 集成脚本，按宪法走「集成类先跑通」，核心验证用手动可重复 checklist（见 PLAN「测试策略」）。

## 局限性

1. **`disable-model-invocation` frontmatter 未实测**。本轮保守保留该 CC 私有字段，Codex 0.130.0 对未知 frontmatter 是否报错未验证。
2. **Codex hooks stdin JSON schema 未实测**。`codex.config.base.toml` 的 `[[hooks.*]]` 字段（`matcher` / `timeout` 是否被 Codex 支持）按最合理形态写；`fix-after-edit.sh` 现读 `.tool_input.file_path`，Codex 字段名可能不同，本轮未动脚本。
3. **skill body 路径硬编码未解**。`$HOME/.claude/scripts/...`、`~/.claude/global-repo`、`~/.claude/templates` 在 skill body 中仍硬编码。双装机器上 `~/.claude/` 始终存在故无碍；纯 Codex 机器尚未适配。
4. **Codex hooks 首次需 `/hooks` review**。与 CC「settings.json 声明即生效」不同；install.sh 已打印提示，但无法自动化。
5. **roadmap #6「双装时跑两遍」的有意偏离**。`install.sh` 单跑即双轨部署，再注册第二个调度器只会重复 pull 同一仓库，故本轮只注册一个调度器、`AGENT_HOME` 按存在的 agent home 智能选取（优先 `~/.claude`）。
6. **`.github/labels.yml` 的 `area:doc` 描述已就地改为 `GLOBAL_AGENTS.md`**，但远端 label 描述需下次 `/sync-project-config` 或 label 同步才会更新。

## 后续 TODO

- **issue #8 的 #8 子项**：双装端到端实测 —— 在 Codex 中实跑 `/start` `/finish` `/commit` `/devtree`，实测 `disable-model-invocation` frontmatter 容忍度、hooks stdin JSON schema、`fix-after-edit.sh` 在 Codex 端的字段一致性。这是 issue #8 收尾的最后一项，留给作者自测。
- 据 #8 实测结果，必要时给 `fix-after-edit.sh` 加 `.tool_input.file_path // .tool_call.file_path` 之类的字段 fallback。
- 若未来要支持**纯 Codex 机器**，需把 skill body 的 `~/.claude/...` 硬编码改为 `${AGENT_HOME:-...}` 或等价形式（本轮按双装场景收敛，未做）。
- CC 是否原生读 `AGENTS.md` 未实测；若读，install.sh 可省一条 `~/.claude/CLAUDE.md` 软链。
