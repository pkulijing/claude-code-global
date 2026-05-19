# Round 22：CC 与 Codex 双兼容 — 主链（#1-#4）

> 来自 [#8 支持 CC 与 Codex 双兼容（单一真源 + install.sh 双轨部署）](https://github.com/pkulijing/claude-code-global/issues/8)
> Labels: `type:feat` `area:install` `priority:P1`

## 背景

user 现在同时使用 Claude Code (CC) 与 OpenAI Codex 两个 coding agent。本仓库管理的开发宪法（`GLOBAL_CLAUDE.md`）+ 工作流 skills（`/start` `/finish` `/commit` `/devtree` 等）+ 自动 lint hooks 当前完全为 CC 设计；Codex 那端在用，但什么辅助都没有，开发体验割裂、配置即将漂移。

Round 20 调研（见 `docs/20-CC与codex双兼容调研/SUMMARY.md`）确认两端约定高度对称（AGENTS.md 跨工具标准、SKILL.md frontmatter 相同、hooks 事件名相同），仓库内容 ~85% 本就 Agent-neutral。调研选定**方案 A**：单一真源 + 双轨 install。

## 本轮范围

issue #8 共 8 个 checklist 子项。本轮（Round 22）做 **#1-#7**；只留 **#8（双装端到端实测）**给作者自己测试。

- **#1**〔refactor doc〕`GLOBAL_CLAUDE.md → GLOBAL_AGENTS.md` 改名 + Agent-neutral 改写
- **#2**〔refactor skill〕skills body 9 处 CC-specific 字符串中性化
- **#3**〔feat install〕新增 `codex.config.base.toml`，镜像 `settings.base.json` 的 hooks 注册 + permissions profile
- **#4**〔feat install〕`install.sh` 双轨重构：检测 `~/.claude/` 与 `~/.codex/` 各自存在与否，按需软链 + 合并 settings
- **#5**〔refactor template〕`.cc-template.yml → .agent-template.yml`，sync skill 见旧名自动迁移
- **#6**〔refactor install〕`auto-update.sh` 与 `scheduler/` 用 `$AGENT_HOME` 变量化
- **#7**〔docs〕README 增「同时支持 CC 与 Codex」段，含双装方式、AGENTS.md 标准说明、known limitations

## 目标

本仓库**单一真源**地服务 CC 与 Codex：

- 跑一次 `bash install.sh` 自动给两端都装好（缺哪端就只装哪端）
- skills / hooks / 主指令文档单份在仓库里，软链到 `~/.claude/` 与 `~/.codex/` 两边
- 新增 skill / 改 hook 不用写两遍
- 已有 CC 工作流不退化

## 约束 / 注意点

- Codex hooks 首次需 `/hooks` slash review 后才生效 —— `install.sh` 跑完要打印明确提示
- `disable-model-invocation` frontmatter 未实测 Codex 是否容忍 —— 本轮保守保留，实测留待 #8
- `fix-after-edit.sh` 现读 `.tool_input.file_path`，Codex stdin JSON 字段名可能不同 —— 实测留待 #8，本轮不动脚本
- CC 是否原生读 `AGENTS.md` 未实测 —— 本轮维持「`~/.claude/CLAUDE.md` 软链 `GLOBAL_AGENTS.md`」
- 改名属破坏性变更：`GLOBAL_CLAUDE.md` / `.cc-template.yml` 改名后所有活文件引用都要同步更新
- `.cc-template.yml → .agent-template.yml` 属破坏性变更，老项目首次 `/sync-project-config` 时需识别旧名自动迁移（#5）

## 不做（明确排除）

- #8 双装端到端实测：在 Codex 中实跑 `/start` `/finish` `/commit` `/devtree`、记录 `disable-model-invocation` frontmatter 容忍度、实测 hooks stdin JSON schema —— 留给作者自己测试
