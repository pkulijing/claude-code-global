# SUMMARY — 接入 prettier/ruff format-after-edit hook

## 开发项背景

daobidao 项目在 commit `c8c91c7` 接入了一个 PostToolUse hook：CC 编辑 `.py`/`.md` 后自动调 `ruff format` / `prettier --write`，目的是消除 **「CC 编辑文件 → 用户在 VS Code 保存触发 formatOnSave → 整文件被重新格式化产生大 diff」** 的反复重排。

这个痛点对所有项目通用，不止 daobidao。本轮把 hook 提到全局，所有项目共享一份；项目本地原有的相同 hook 由用户自行删除。

## 实现方案

### 关键设计

- **路径策略**：hook command 用 `bash $HOME/.claude/hooks/format-after-edit.sh` 绝对路径（`$HOME` 由 shell 展开，CC 的 hook command 走 shell 已验证），避免依赖 cwd —— 全局 hook 在任意项目下都能稳定定位脚本。
- **部署方式**：仿 `skills/` 的逐文件软链路径，`install.sh` 把 `hooks/format-after-edit.sh` 软链到 `~/.claude/hooks/`，脚本本体可以直接在仓库里修改、立即生效。
- **best-effort 设计完整保留**：缺 `prettier` 静默跳过、缺 `uv` 错误被吞、`exit 0` 永不阻塞 agent —— 所以这个 hook 部署到所有项目（包括非 Python、非 Node 的）都不会出问题。
- **VS Code 配置不全局化**：`.vscode/*` 是 IDE per-project 配置，不属于 CC 全局仓库职责；`.prettierrc` 受 prettier 从 cwd 往上找配置的限制，全局仓库覆盖不了。这两类改为在 `GLOBAL_CLAUDE.md` 里加一条「项目本地推荐配置」约定，由各项目自行维护。

### 开发内容概括

| 文件                                | 改动                                                                           |
| ----------------------------------- | ------------------------------------------------------------------------------ |
| `hooks/format-after-edit.sh` (新增) | 1:1 复制 daobidao 的脚本，按扩展名分发到 ruff/prettier，chmod +x               |
| `settings.base.json`                | 顶层加 `hooks.PostToolUse`，matcher 为 `Edit\|MultiEdit\|Write`，timeout 30    |
| `install.sh`                        | 增加 `hooks/` 目录创建 + 逐文件软链段（仿 skills 段）                          |
| `GLOBAL_CLAUDE.md`                  | 新增「项目本地推荐配置」段落（位于「环境变量管理」与「Python 开发规则」之间）  |
| `CLAUDE.md`（项目）                 | 「目录结构」与「开发注意事项」补充 `hooks/` 相关说明                           |
| `.prettierrc` (新增)                | 本仓库 dogfood：`{ "proseWrap": "preserve" }`                                  |
| `skills/bootstrap/SKILL.md`         | 新增 Step 3「写 `.prettierrc`」（已存在则跳过）；收尾建议增补 `.vscode/*` 提示 |

### 额外产物

- `docs/10-接入prettier-format-hook/{PROMPT,PLAN,SUMMARY}.md` 三件套
- 部署后端到端测试方法（写在 PLAN.md 测试计划里），手测过 `$HOME` 展开 + prettier 触发 markdown 格式化两条路径
- 本轮自身验证了 hook：写 SUMMARY.md 时被 PostToolUse hook 触发了 prettier，dogfood 闭环成立

## 局限性

1. **`uv run` 在非 uv 项目会失败但被静默吞掉**：本轮 1:1 移植 daobidao 版本，没做「先 `command -v ruff` → fallback `uv run`」的健壮性优化。后果是非 uv 项目编辑 `.py` 时会无谓地启动 uv 子进程并失败（但不影响 agent，仅浪费几百毫秒）。
2. **daobidao 项目本地的 hook 脚本与 settings 配置仍未删除**：用户自行处理，未在本轮范围内。两份 hook 同时存在不会导致错误（ruff/prettier 幂等），仅多跑一次。
3. **DEVTREE 未更新**：用户表示自己处理 epic 归属，本轮文档没碰 `docs/DEVTREE.md`。
4. **bootstrap 中只新增 `.prettierrc`，未自动创建 `.vscode/*`**：因为不是所有用户都用 VS Code，强加会污染。仅在收尾建议里提示用户按 `GLOBAL_CLAUDE.md` 推荐自行补。

## 后续 TODO

1. **hook 健壮性优化**（backlog 候选）：`format-after-edit.sh` 的 `.py` 分支改成「先 `command -v ruff` → fallback `uv run --quiet ruff format`」，省掉非 uv 项目的无谓子进程开销。
2. **DEVTREE epic 归属**：用户处理。可能需要新建一个「自动化与 IDE 协同」epic 容纳本轮（以及未来潜在的更多 hook、IDE 集成相关工作）。
3. **本轮可被验证为通用方案后**，可以扩展更多扩展名分发（如 `.json` → `prettier`、`.ts/.tsx` → `prettier`），目前只覆盖 `.py` 和 `.md`。
4. **可选：bootstrap 增加交互式询问是否生成 `.vscode/*`**，命中 VS Code 用户时一步到位。当前是放到收尾建议，依赖用户主动补。
