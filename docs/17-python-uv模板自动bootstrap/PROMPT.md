> 来自 [#5 feat(template): python-uv 模板首次接入时自动 bootstrap 项目（uv init + dev deps + pre-commit install）](https://github.com/pkulijing/claude-code-global/issues/5)
> Labels: `type:feat` `area:template` `priority:P1`

## 背景

python-uv 模板目前只落「配置文件」（`.pre-commit-config.yaml` / `pyproject.toml [tool.ruff]` 段 / `.vscode/` / `.gitlab-ci.yml` 等），但**不**真的把项目 bootstrap 起来。新项目 sync 完模板后，用户还要手动：

1. `uv init` 才有可执行的 `pyproject.toml` / `.python-version` / `src` 骨架
2. `uv add --dev pytest pytest-cov ruff` 装常用 dev 依赖
3. 全局没有 `pre-commit` 的话还得先 `uv tool install pre-commit`
4. `pre-commit install` 才能让 `.pre-commit-config.yaml` 真的生效

四步全是机械操作，配置文件已经躺在仓库里却跑不通，体验断裂。应该在「首次接入模板」这一刻一次到位。

## 希望达到

跑完 `/bootstrap` 选 python-uv（或老项目跑 `/sync-project-config` adopt）后：

- `pyproject.toml` 已 `uv init` 出来（含 python version / 默认 src layout / 已 merge 模板的 `[tool.ruff]` 段 + `[[tool.uv.index]]` 清华源段）
- 默认 dev 依赖已通过 `uv add --dev` 加好：`pytest` / `pytest-cov` / `ruff`
- `pre-commit` 全局可用（先 `command -v pre-commit` 探测，没有就 `uv tool install pre-commit`）
- `pre-commit install` 已执行（`.git/hooks/pre-commit` 就位）

之后立刻能 `uv run pytest` / `git commit` 跑通，不用再翻文档复制命令。

## 候选方向

- **方向 A**：sync-project-config skill 加一个「post-adopt 命令式 bootstrap」阶段，命令集中到 `templates/python-uv/post-adopt.sh`（或 `.py`）；skill 检测到该文件存在则执行 —— 模板侧扩展点统一
- **方向 B**：把这些步骤直接写进 sync-project-config skill 的 python-uv 分支专属逻辑里，不走通用 hook 机制 —— 简单直接，但其他 stack 想要类似能力时要再写一遍
- **方向 C**：维持配置静态化，提供独立 `/bootstrap-python` skill 单独管动作步骤；sync 只管文件，bootstrap 管命令 —— 关切分离最干净，但用户多记一个命令

PLAN 阶段定方向 A/B/C 再实施。

## 风险 / 注意点

- **已有 `pyproject.toml` 的老项目接入**：`uv init` 会拒绝 / 与现有内容冲突 → 必须先检测，已存在则跳过 `uv init`，但 dev 依赖 / pre-commit install 还要照跑
- **`uv tool install pre-commit` 与已装的 pipx/brew/系统 pip 版本冲突** → `command -v pre-commit` 探测够不够，还是要更细（例如版本范围、`pre-commit --version` 解析）
- **网络源**：`uv init` 出来的初始 `pyproject.toml` 不带 `[[tool.uv.index]]`，需要先 merge 进清华源段再 `uv add`，否则在国内会卡
- **dev 依赖硬编码 vs 可配置**：本轮先硬编码 `pytest pytest-cov ruff`，后续若要 mypy / coverage 工具再考虑抽成模板变量
- **bootstrap 与 sync adopt 的差异**：bootstrap 面向空目录，可以放心从 0 开始；sync adopt 面向有内容的老项目，必须考虑跳过、增量、和回滚

## scope

约 1 个开发轮次。先在 PLAN 阶段定方向 A/B/C，再实施。
