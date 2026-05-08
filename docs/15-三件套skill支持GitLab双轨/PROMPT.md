> 来自 [#3 让 backlog / start / finish 等 skill 在 GitLab 项目上可用（gh ↔ glab 双轨）](https://github.com/pkulijing/claude-code-global/issues/3)
> Labels: `type:feat` `area:skill` `priority:P1`

## 1. 背景

Round 14 已经把 GitLab 双兼容**模板侧**落到位（`.gitlab/issue_templates/` + `.gitlab-ci.yml` 在所有项目共存；`/bootstrap`、`/sync-project-config` 中的 `gh label create` 已三分支判定）。但 **skill 内 `gh issue *` 调用仍是 GitHub 独占**：在 GitLab 项目上跑 `/backlog`、`/start <#>`、`/finish` 会前置检查失败、或调用真实失败、或行为静默错位（issue 不会被 commit 关掉）。

`/finish` 走 `Closes #N` 关 issue —— 这一关键字 **GitHub 与 GitLab 都支持**（GitLab 支持 `Closes`/`Fixes`/`Resolves` 等同样的关闭关键词），但需要进一步验证、并在文档里写清两者兼容。

**前置项一并合入本轮**：GitLab labels 同步（round 14 SUMMARY §6 后续 TODO #2）。原本想留给独立 issue（`area:template`），但它实际上是 `/backlog` 在 GitLab 项目下能用的**硬前置** —— 没同步 labels 就 `glab issue create --label "type:feat"` 会失败。本轮一起做掉，避免「skill 改完了但项目跑不起来」的撕裂状态。

## 2. 希望达到

三件套 skill（`/backlog`、`/start`、`/finish`）在 GitLab 项目上**等价可用**：

- `/backlog`：在 GitLab 项目下走 `glab issue create`（带相同的三轴 label），并在 BACKLOG.md 写入对应 issue 链接
- `/start <N>` / `/start <issue URL>`：在 GitLab 项目下走 `glab issue view <N>`，把 title/body/labels/url 写进新一轮的 PROMPT.md
- `/finish`：commit message body 仍写 `Closes #N`（两端兼容），但要**确认**该关键字在 GitLab 上的实际语义并在文档里说明
- 前置检查：根据 `git remote get-url origin` 走平台分支
  - GitHub → `gh auth status` + `gh ...`
  - GitLab → `glab auth status` + `glab ...`
  - 其他（无 remote / 自托管含/不含 `gitlab` 字样的复杂情况）→ 给清晰提示

## 3. 范围（Scope）

**In-scope（本轮要做）**：

1. `/backlog` 的 platform 双轨：`gh auth status` → `gh|glab auth status`；`gh issue create` → `gh|glab issue create`
2. `/start` 的 platform 双轨：`gh issue view --json` → `gh|glab issue view`（需核实 `glab` 输出结构、json 字段对齐）
3. `/finish` 的 `Closes #N` 跨平台兼容性**核实**：在 SKILL.md 加注释说明「`Closes #N` 在 GitLab 上同样自动关 issue」
4. **GitLab labels 同步（合入本轮的前置项）**：
   - 模板侧新增 `templates/_common/__root__/.gitlab/labels.yml`，与 `.github/labels.yml` 同源（`type:*` / `priority:*` 全集一致；`area:*` 由项目自行维护）
   - `/bootstrap` 的 Step 3.3.5 与 `/sync-project-config` 的 6 节执行步骤：把 round 14 中 GitLab 分支的「跳过 + 提示」改为真正调 `glab label create`（带等价 `--force` 覆盖更新语义）
5. `GLOBAL_CLAUDE.md` 的「Backlog 与开发项管理（GitHub Issue 驱动）」段同步加 GitLab 等价说明（heading 可能要从「GitHub Issue 驱动」改为更平台中立的措辞）
6. 文档（PROMPT/PLAN/SUMMARY 标准三件套）

**Out-of-scope（本轮不做）**：

- 实地 GitLab 项目验证清单（quick action 首行规则、`.gitlab-ci.yml` 首跑、issue templates web UI 等）—— 留给独立 issue（依赖手边有真实 GitLab 项目）
- 本仓库 `.cc-template.yml` `stacks: []` 状态修复 —— 与本 round 无关

## 4. 方向（已定：B 抽 helper）

考量过两条路径：

- **方向 A：每个 skill 内 detect platform → 分支调用 `gh` 或 `glab`**
  - 优点：改动局部、每个 skill 自包含、可读性好
  - 缺点：detect 与分支逻辑在多处重复，未来加新平台或加新调用点容易漂移
- **方向 B：抽 helper 封装平台无关的原语（`issue_create` / `issue_view` / `issue_close_keyword` / `label_upsert` 等）**
  - 优点：DRY；新增第四个 skill 也免费拿到双轨能力；输出契约统一便于 SKILL.md 解析
  - 缺点：多一层抽象；shell 脚本输出契约需要自定义并文档化；全局仓首次引入「skill 调脚本」的模式

**决策：B**。理由：

1. 本轮 in-scope 的触点已经是 4~5 处（`/backlog` auth + create、`/start` view、`/bootstrap` 与 `/sync-project-config` 的 label upsert）—— 三分支逻辑重复 4~5 次，每次都跟 PROMPT 风险段那几条注意点（自托管 URL 启发式、`--force` 等价语义、json 字段映射）同步漂移，长期成本 > 单次抽象成本
2. round 14 在 `gh label create` 那处用方向 A 是因为只有 1 处触点；本轮如果继续 A，那处和新加的触点会**两种风格混杂**，反而比纯 B 更乱；本轮可以顺手把 round 14 那处也迁到 helper（小重构）
3. helper 只负责 CLI 调用 + 字段映射，不引入业务逻辑；SKILL.md 的可读性损失有限（"调一行 helper"比"三分支 if/else 复读"更短）

helper 形态在 PLAN 阶段定稿（候选：bash script `scripts/platform_issue.sh` / python module `scripts/platform_issue.py` —— 取决于 json 解析复杂度）。

## 5. 风险 / 注意点

- `glab` CLI 未必预装 —— 前置检查失败时需要给清晰的安装引导（macOS：`brew install glab`；其他平台 → glab repo 的 README）
- `glab issue view` 与 `gh issue view --json` 输出结构**不完全对齐**：需要核实 `glab` 是否支持 `--output json` / `-F json` 等价参数、字段命名（GitLab 是 `iid` 而非 `number`、`web_url` 而非 `url` 等）
- `glab label create` 是否支持 `--force` 等价的「已存在则覆盖更新」语义 —— GitHub `gh label create --force` 是覆盖更新；如果 `glab` 没有等价 flag，可能需要先 `glab label list` 后判定 create vs update（或先 delete 再 create，这种 destructive 路径要避免）
- `Closes #N` 在 GitLab 上的精确行为：**只有合并到 default branch 时才自动关**，且默认分支必须配置正确；与 GitHub 行为基本一致，但 PLAN 阶段要在 `glab` 文档里再核对一次
- 自托管 GitLab：URL 不一定含 `gitlab` 字样（如 `git.company.com`）—— 复用 round 14 的「含 `gitlab` 字样」启发式同样不完美。本轮**沿用** round 14 的判定规则，不解决自托管 URL 启发式问题（独立 issue）

## 6. 关联

- **前置依赖**：[#14 模板支持 GitLab 双轨（项目侧双兼容）](../14-模板支持GitLab双轨/SUMMARY.md) —— 已合并，模板侧已就位
- **本轮吸收的前置项**：round 14 SUMMARY §6 后续 TODO #2 「GitLab labels 同步」 —— 不再开独立 issue，并入 in-scope §3.4
- **同期独立 issue**（非阻塞，本轮不做）：实地 GitLab 项目验证清单
- **复用约定**：round 14 的「按 `git remote get-url origin` 三分支判定」启发式（GitHub / GitLab / 其他）

## 7. 估时

约 1 轮：触点 4 处主调用点（`/backlog` auth + create、`/start` view、`/bootstrap` & `/sync-project-config` 的 label create）+ 模板 1 个新文件 + 文档同步。PLAN 阶段需要先核实 3 个事实：`glab issue view` json 输出结构、`Closes #N` 在 GitLab 默认分支的语义、`glab label create` 的覆盖更新语义。
