# PROMPT：`.gitlab-ci.yml` 模板按 runner 类型选变体

> 来自 [#32 shell-runner .gitlab-ci.yml 模板：用 YAML 锚点而非 !reference（避免 check-yaml 卡住）](https://github.com/pkulijing/claude-code-global/issues/32)
> Labels: `type:refactor` `area:template` `priority:P2`

## 背景

`teleop-operator` round 16（CI 跑通与三包发布）沉淀：公司流水线常是**本地 shell runner（非 docker executor）**。当前 `bootstrap` / `sync-project-config` 落的共享 `.gitlab-ci.yml` 模板（[templates/python-uv/**root**/.gitlab-ci.yml](../../templates/python-uv/__root__/.gitlab-ci.yml)）写死了 `image: ghcr.io/astral-sh/uv:...` 的 **docker-executor 写法**，在 shell runner 上根本跑不了——runner 没有 docker executor，`image:` 被忽略、job 在宿主机直接跑，而宿主机可能没有 uv。

shell-runner 变体的正确写法是：不指定 `image:`，`before_script` 里检测 uv 缺失则用官方脚本装（uv 自带 standalone Python，装完即可用）。

issue 里还带了一个**具体的坑**：做 shell-runner 变体时若用 GitLab 的 `!reference [...]` 复用 `before_script`，会被项目里 pre-commit 的 `check-yaml` 卡住——通用 YAML 解析器不认 `!reference` 自定义 tag，报 `could not determine a constructor for the tag '!reference'`，commit 直接失败。改用**标准 YAML 锚点**（`&anchor` / `*anchor`）复用即可，GitLab 同样支持、且通用解析器能过。（当前模板只有一个 job、无复用需求，此坑是「未来若加 job」的前瞻约束。）

## 核心洞察：这不只是「加一份 shell 变体」，而是「引入一类新模板机制」

最初想当作 `/quick` 小改，把 docker + shell 两个 job 都写进同一份 `.gitlab-ci.yml`、留一句「用哪个删哪个」——**这是错的**。`.gitlab-ci.yml` 是**会被 GitLab 真实解析执行**的运行时配置，不是给人看的文档。用户一旦没删干净，就得到一份两个 job 都在跑的错误 CI（地雷）。

正确做法：**docker 变体与 shell 变体是一组互斥变体，选择必须前移到模板初始化（bootstrap / sync adopt）时的交互**，让 skill **只落用户选中的那一份**为最终 `.gitlab-ci.yml`。用户任何时候看到的都是干净、可直接跑的单一版本。

这是模板体系里**第一个「需按用户环境选变体」的文件**——现有模板要么无脑直落（`__root__` / `__subpath__` 普通文件），要么 fragment 合并（`*.fragment`），都没有「一组文件里交互选一个」这条路。故本轮要引入一类**新的模板机制约定**，而非给 gitlab-ci 打的一次性补丁。

## 目标

1. **模板侧**：把 `python-uv` 的 `.gitlab-ci.yml` 拆成一组互斥变体（docker-executor 版 + shell-runner 版），用一种**通用、可复用**的机制声明「这是一组需选一的变体」——不强依赖 stack.yml 存在（python-uv 无 stack.yml）。
2. **shell-runner 变体内容**：去 `image:`；`before_script` 检测 uv 缺失则脚本装；即便当前单 job、也在注释里固化「未来复用 before_script 用 YAML 锚点、不用 `!reference`」的约定，回应 issue 的坑。
3. **skill 侧**：`bootstrap`（Step 3）与 `sync-project-config`（adopt + normal sync）消费到「变体组」时，向用户提问选一个，**只落对应那一份**为最终目标文件（`.gitlab-ci.yml`）。normal sync 还要处理「已落地项目侧、模板变体内容更新」的同步。
4. **机制文档化**：把新约定写进两个 skill 的 SKILL.md（单一真源），并在需要处更新 SCHEMA / 相关 docs 引用。

## 约束

- **不改任何真实业务代码**——这是纯模板 + skill 流程约定的调整。
- **双轨兼容**：机制走 SKILL.md 文字流程（现有模板消费就是 AI 照 SKILL.md 执行），CC / Codex 两端共读，不引入任何需要代码运行时的引擎。
- **向后兼容**：已 bootstrap 过、marker 里没有变体选择记录的老项目，sync 时要能优雅处理（询问补选，而非报错）。
- **最小惊喜**：变体机制要尽量类比已有的 fragment 机制（命名约定 + SKILL.md 处理段），不发明过重的新概念。

## 待决问题（PLAN 阶段敲定）

- 变体组的**声明形式**：靠文件名命名约定（类比 `*.fragment`）？还是靠一个 sidecar 声明文件（类比 stack.yml）？两者取舍见 PLAN。
- 变体选择是否要**记进 marker**（`.agent-template.yml`），以便 normal sync 知道用户当初选了哪个变体、后续只同步那一支。
- docker 与 shell 两个变体各自的落点文件名（模板里叫什么、落地后统一叫 `.gitlab-ci.yml`）。
