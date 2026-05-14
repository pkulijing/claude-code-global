# SUMMARY — python-uv 模板自动 bootstrap 项目

> Closes #5

## 背景

`/bootstrap` 选 python-uv 之后只落配置文件（`.pre-commit-config.yaml` / `pyproject.toml [tool.ruff]` 段 / `.vscode/` / `lint.yml` / `.gitlab-ci.yml` 等），但**不**真的把项目跑起来 —— 用户仍要手动跑 `uv init` / `uv add --dev pytest pytest-cov ruff` / `uv tool install pre-commit` / `pre-commit install` 四步才能 `uv run pytest` 或 `git commit`。配置已经躺在仓库里却跑不通，体验断裂。

希望「跑完 `/bootstrap` 选 python-uv（或老项目 `/sync-project-config` adopt）后，项目立刻可开发」。

## 实现方案

### 关键设计

1. **方向 B（不是 A/C）**：直接把命令链路写进 bootstrap / sync-project-config 的 python-uv 分支专属 step，**不**引入通用 `post-adopt.sh` 扩展点。当前只有一个 stack，过度抽象；演进路径明确（未来加新 stack 时再搬到 `templates/<stack>/post-adopt.{sh,py}`）。

2. **两个入口、同一段命令**：
   - bootstrap 新增 **Step 3.5**（空目录 → `uv init --bare` 必然走）
   - sync-project-config adopt 新增 **4.4**（老项目 → 已有 pyproject 时跳过 uv init）
   - **normal sync 不动**：用户已 bootstrap 过，幂等重跑只增加噪音

3. **fragment 合并机制通配化**：旧版只识别 `pyproject.toml.ruff.fragment`，本轮通用化为 `pyproject.toml.<section>.fragment`（`<section>` 用 `-` 分隔层级，如 `uv-index` → `[[tool.uv.index]]`）。数组段（双方括号）按 `name` 字段 union，避免重复注册。

4. **fragment 合并时机的「延迟」**：
   - 当 `pyproject.toml` 已存在 → Step 3.3.6 立即合并
   - 当 `pyproject.toml` 不存在（空目录 bootstrap） → 标记 `needs-step-3.5`，等 Step 3.5.1 `uv init --bare` 完成后回头合并
   - 清华源 fragment 必须先合再 `uv add`，否则在国内拉 pypi.org 会卡

5. **命令顺序**：`uv init --bare` → merge fragments → `uv add --dev pytest pytest-cov ruff` → `command -v pre-commit || uv tool install pre-commit` → `pre-commit install`。

6. **失败处理**：每一步独立报错，立即停止，**不**自动 retry、**不**自动回滚（让用户 `git diff` + `git checkout` 自决）。skill 入口前用 `AskUserQuestion` 给「只要配置不要装依赖」选项，让用户主动跳过整段。

7. **dev deps 硬编码**：`pytest pytest-cov ruff`。后续若要 `mypy` / `coverage[toml]` 等再开下一轮抽成模板变量（YAGNI）。

8. **不内置 torch aliyun 源**：Constitution 规定 torch 走 aliyun 镜像，但 99% 项目不用 torch，硬塞会加 noise。torch 项目自己在 pyproject 追加。

### 开发内容

新增：

- [`templates/python-uv/__subpath__/pyproject.toml.uv-index.fragment`](../../templates/python-uv/__subpath__/pyproject.toml.uv-index.fragment) — 清华源 `[[tool.uv.index]]` 段片段，bootstrap / sync 智能合并进项目 pyproject.toml

修改：

- [`skills/bootstrap/SKILL.md`](../../skills/bootstrap/SKILL.md)
  - Step 3.3 末尾：fragment 特殊处理改为通配 `pyproject.toml.*.fragment`，从普通文件复制流程剔除
  - **新增 Step 3.3.6**：fragment 合并（有 pyproject → 立即合；无 → 标 needs-step-3.5）
  - **新增 Step 3.5**：python-uv 专属，含 3.5.1 `uv init --bare` / 3.5.2 `uv add --dev` / 3.5.3 探测+安装 pre-commit / 3.5.4 `pre-commit install`
  - 旧 Step 3.4 marker 重编号为 **3.6**（放在 3.5 后写入，反映完整 stack 已落地）
  - Step 5 收尾反馈：调整下一步建议（python-uv 已自动 bootstrap → 可立即 `uv run pytest`；Step 3.5 跳过 → 提示手动命令；其他 stack / 全跳过 → 引导 `/sync-project-config`）
- [`skills/sync-project-config/SKILL.md`](../../skills/sync-project-config/SKILL.md)
  - 2.4 fragment 特殊处理改为通配，加上「adopt 路径下 python-uv stack 标记延迟到 4.4 后合并」
  - **新增 4.4 段**：与 bootstrap 3.5 等价，老项目 `uv init` 跳过是常态
  - 6 节 accept (pyproject 段合并) 措辞通配
  - 6.2 收尾反馈：明确 normal sync 不重跑 uv / pre-commit bootstrap
- [`GLOBAL_CLAUDE.md`](../../GLOBAL_CLAUDE.md) §「项目本地推荐配置」：补一句 python-uv 自动 bootstrap 行为

### 额外产物

- 三个 smoke test 在 `$CLAUDE_JOB_DIR/smoke-{a,b,c}` 实跑验证命令链路（不验 skill AI 编排本体）

## 验证

| Smoke | 场景                                  | 结果                                                                                                                                                                                          |
| ----- | ------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A     | 空目录 bootstrap                      | ✅ `uv init --bare` 出干净 `[project]` 段 → fragments 合并 → `uv add --dev` 装 pytest 9.0.3 / pytest-cov 7.1.0 / ruff 0.15.13 → `pre-commit install` → `pre-commit run --all-files` 全 Passed |
| B     | 老项目 adopt（已有 `pyproject.toml`） | ✅ 跳过 `uv init` → `name = "legacy"` 保留 / `requires-python = ">=3.11"` 保留 → 追加 `[tool.ruff]` + `[[tool.uv.index]]` 段 → dev deps + pre-commit install OK                               |
| C     | `uv` 不在 PATH                        | ✅ exit 127、stderr `command not found: uv`、无副作用 —— shell 能正常传播失败，skill 编排可 catch                                                                                             |

> Skill AI 编排本体（AskUserQuestion 流程、单步失败暂停）只能在真实 `/bootstrap` / `/sync-project-config` 调用时验证，本轮已实跑过命令链路本身。

## 局限性

1. **命令链路靠 SKILL.md 文本约束 AI 编排**：没法静态保证 AI 一定按序跑完 4 步，单步失败时也得靠 AI 正确解读 stderr 暂停。需要在真实使用时持续观察。
2. **失败不自动回滚**：`uv init` 之后 `uv add` 失败，pyproject.toml 不会还原。用户得 `git diff` + `git checkout` 自决。
3. **normal sync 不会补漏 `pre-commit install`**：当前用户已在某次 bootstrap / adopt 中没装 pre-commit，后续 normal sync 不会主动补。需要后续 round 加「检测 `.git/hooks/pre-commit` 不存在则补」。
4. **dev deps 硬编码**：项目想要不同 dev 集（如 mypy / coverage 单测项目）只能 `uv add` 后再叠。
5. **多 stack 未支持**：本轮仍假设单 stack（path = `.`），与 round 11 限制一致。

## 后续 TODO

- normal sync 主动补 `pre-commit install`：检测 `.git/hooks/pre-commit` 不存在则补做（P2）
- dev deps 可配置：抽成 `templates/python-uv/post-adopt.config.yml` 或 marker 字段（按需求触发）
- 抽象到方向 A：第二个 stack（node / rust）出现时，把 Step 3.5 段从 SKILL.md 搬到 `templates/<stack>/post-adopt.{sh,py}`，bootstrap / sync 改为「检测脚本则执行」（P2，等触发器）
- torch / aliyun index：用户按需追加，模板暂不内置
