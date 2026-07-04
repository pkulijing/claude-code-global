# SUMMARY：`.gitlab-ci.yml` 模板按 runner 类型选变体（引入「变体组」模板机制）

> 对应 issue [#32](https://github.com/pkulijing/claude-code-global/issues/32)｜round 43

## 开发项背景

### 希望解决的问题

`bootstrap` / `sync-project-config` 落的共享 `.gitlab-ci.yml` 模板写死了 `image: ghcr.io/astral-sh/uv:...` 的 **docker-executor 写法**。但公司流水线常是**本地 shell runner（非 docker executor）**——`image:` 被忽略、job 在宿主机直接跑，宿主机可能没有 uv，CI 跑不了（来自 `teleop-operator` round 16 沉淀）。

需要一份 shell-runner 变体：不指定 `image:`、`before_script` 检测 uv 缺失则官方脚本装。issue 还带一个具体坑：shell 变体若用 GitLab 的 `!reference` 复用 `before_script`，会被 pre-commit 的 `check-yaml` 卡住（通用 YAML 解析器不认 `!reference` 自定义 tag）→ 必须改用标准 YAML 锚点 `&`/`*`。

### 关键转折：从「加一份 shell 变体」升级为「引入一类模板机制」

最初尝试走 `/quick` 小改，方案是把 docker + shell 两个 job 都写进同一份 `.gitlab-ci.yml`、留一句「用哪个删哪个」——**被用户当场拦下并推翻**。原因：`.gitlab-ci.yml` 是会被 GitLab **真实解析执行**的运行时配置，不是给人看的文档；多变体并存 + 留给用户手删是地雷（漏删即得会真跑的错误 CI）。

正确做法是把「选哪个变体」的决策**前移到模板初始化的交互**，skill 只落用户选中那一份。这是模板体系里第一个「需按环境选变体」的文件，故本轮升级为**引入一类通用的「变体组」模板机制**，而非给 gitlab-ci 打的一次性补丁——遂从 `/quick` 切到正规 `/start #32`。

## 实现方案

### 关键设计

1. **变体组 = 文件名命名约定 `<target>.variant.<key>`**（类比已有的 `*.fragment` 机制）。同一 `<target>` 的多个 `.variant.<key>` 文件表示「一组互斥变体、需按环境选一个落地」，去掉后缀即得落地目标名。选择「命名约定」而非「sidecar 声明文件」，是因为 `*.fragment` 已确立「靠文件名后缀声明特殊处理」的先例，零新增元数据文件、认知负担最小；且 `python-uv` 无 `stack.yml`，机制不能强依赖 sidecar 存在。

2. **选择前移到初始化交互、只落一份**。bootstrap / sync 消费到变体组时问用户选一个 key（人话说明由 skill 按已知 key 硬编码给），只把选中那份落地为 `<target>`，其余不落地。保证项目侧永远是干净可跑的单一版本。

3. **选择记进 marker `stacks[].variants`**（map: `<target>` → 选中 key）。normal sync 据此只同步选中那一支、不重问用户；老 marker 无此字段则询问补选（向后兼容）。

4. **向后兼容的迁移去重**：本轮把已存在的普通文件 `.gitlab-ci.yml` 改成变体组，老项目 normal sync 的 diff 会同时出现 `D .gitlab-ci.yml` + `A .variant.*`。sync 2.4 新增「普通文件→变体组迁移去重」段，识别出「落地目标同一」→ **抑制误删提案**、转交变体组处理，保证老项目平滑迁移、`.gitlab-ci.yml` 不被误删。

5. **shell 变体的 uv 安装**：`before_script` 用 `command -v uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh` 检测缺失才装（幂等），再 `. "$HOME/.local/bin/env"` 注入 PATH。注释固化「未来复用 before_script 用 YAML 锚点、禁 `!reference`」的约定与原因，回应 issue 的坑（当前单 job 是前瞻约束）。

### 开发内容概括

- **模板**（`templates/python-uv/__root__/`）：删旧 `.gitlab-ci.yml`，新增 `.gitlab-ci.yml.variant.docker`（docker executor 版）+ `.gitlab-ci.yml.variant.shell`（shell runner 版）。
- **bootstrap SKILL.md**：Step 3.3 识别并剔除变体组文件、新增 Step 3.3.7「落地变体组」、Step 3.6 写 marker `variants`、Step 3 总览描述标注 gitlab-ci 是变体组。
- **sync-project-config SKILL.md**：2.1 读 `variants`、2.4 变体组四象限 + 普通文件→变体组迁移去重、4.3 adopt 对称、第 6 节 accept 分支 + 6.1 回写 `variants`。
- **SCHEMA.md**：字段定义加 `variants`、新增 `stacks[].variants` 字段说明、文末新增「变体组文件」段、平台双兼容表更新 gitlab-ci 行。
- **根 CLAUDE.md**：`templates/` 机制描述补一句变体组。

### 额外产物

- 一段自校验脚本（模拟 skill 的变体组识别 + target 反解 + fragment 互斥逻辑），确认命名约定自洽无歧义——非入库代码，作为走查手段。
- 用 `uv run --with pyyaml` 做 `check-yaml` 等价校验，确认两个变体文件均能被通用 YAML 解析器 `safe_load`、shell 变体无 `!reference`、命令串纯 ASCII。

## 局限性

- **无自动化测试**：模板消费机制是「AI 照 SKILL.md 文字流程执行」，没有代码化引擎，故变体组的「识别→剔除→落地→marker→normal-sync diff」全链路只能靠人工走查 + 上述自校验脚本佐证，无法进 CI 回归。这是本仓库模板机制的一贯形态，非本轮引入。
- **人话说明两处冗余**：变体 key 的人话说明在 bootstrap Step 3.3.7 与 sync 2.4 各写了一份（sync 处引用 bootstrap 为权威源并注明「改动时两处同步」），未做到严格单一真源。当前仅一个变体组、两处措辞已对齐，成本可接受；变体组增多后可考虑抽出。
- **shell 变体 `. "$HOME/.local/bin/env"` 路径假设**：依赖 uv 官方安装脚本落 `~/.local/bin` 的默认行为。若 runner 用了非默认 `UV_INSTALL_DIR`，该行会失效——但这是官方默认路径，实际偏离概率低，未做防御。

## 后续 TODO

- 若未来出现第二个变体组（如 `.github/workflows/*` 也要按某维度选变体），届时把「变体 key 人话说明」抽成单一真源（如放进模板侧一个轻量映射），消除当前 bootstrap / sync 两处冗余。
- 可考虑给 `install.sh` 或一个 skill 加一条轻量 lint：扫 `templates/` 确认变体组命名约定自洽（同组 key 无重复、不与 `.fragment` 撞、target 反解唯一），把本轮的手工自校验脚本固化为可复跑的守卫。

## 可沉淀项

1. **「可执行配置不塞多变体让用户自选」已沉淀为记忆**（`feedback_runtime_config_no_pick_one_yourself`，`/quick` 阶段被用户拦下时即写）：会被工具真实执行的配置（CI/构建/部署）不能「二选一自己删」，选择前移到初始化交互。本轮正是其落地——**这条本就是 claude-code-global 自身的机制，无需跨仓库提 issue**。
2. **「变体组」机制本身是本仓库的通用资产**，已直接落进 SKILL.md + SCHEMA.md，非需另提 issue 的候选——它就是本轮交付物。

→ 综上，本轮无需向 claude-code-global 跨仓库提新 issue（当前仓库即 claude-code-global，且沉淀项已随本轮代码落地）。Step 3 的自指守卫会命中，跨仓库 file 自动跳过。
