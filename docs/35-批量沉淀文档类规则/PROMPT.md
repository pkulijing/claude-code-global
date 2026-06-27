# 批量沉淀文档类规则（8 条跨项目坑位 issue）

本轮一次性消化 8 条 `type:docs` 的跨项目沉淀 issue —— 它们都来自外部项目（teleop / teleop-operator）的 `/finish` 反思，自动跨仓提到 claude-code-global，内容皆为「往领域规则文档追加一段约定」，互不耦合、可在一轮内批量落地。

刻意**不**纳入本轮：

- **#27**（split-repo 协同 + 多轮隔离开发缺方法论）—— 是开放式方法论探索，需单独成轮设计，不是一段规则追加。
- **#32**（shell-runner `.gitlab-ci.yml` 用 YAML 锚点）—— `type:refactor` `area:template`，是模板代码改动而非纯文档。

## 落点分组（按目标文件归并）

### A. `rules/python.md`（3 条）

> 来自 [#31 rules/python.md 补「uv + 自托管 GitLab Package Registry」两个固定坑](https://github.com/pkulijing/claude-code-global/issues/31) · `type:docs` `area:doc` `priority:P2`
> 来自 [#30 含前端(npm)产物的 Python 成员 wheel 化部署（hatchling artifacts + bundled-first 路径）](https://github.com/pkulijing/claude-code-global/issues/30) · `type:docs` `area:doc` `priority:P2`
> 来自 [#26 pip install --target 装本地开发 wheel 需删旧重装（同版本号不覆盖坑）](https://github.com/pkulijing/claude-code-global/issues/26) · `type:docs` `area:doc` `priority:P2`

- **#31 — uv + 自托管 GitLab Package Registry**：新增一小节，钉死两个坑：
  1. TLS：uv 默认 rustls + 内置 Mozilla 根、**不读系统信任库**，内部 CA 签证书报 `invalid peer certificate: UnknownIssuer` → `export UV_SYSTEM_CERTS=true`（旧版废弃名 `UV_NATIVE_TLS`），CA 自定义路径设 `SSL_CERT_FILE`；对 `uv publish` 与 `uv pip install` 都适用。
  2. `uv publish --check-url` 与 GitLab PyPI 不兼容：GitLab simple 索引返回 `Content-Type: text/plain`，uv `--check-url` 只认 JSON/HTML → `Failed to query check URL`。GitLab 上别用 `--check-url`；重发须删旧版或 bump version。
  3. 顺手固化项目级上传 URL：`${CI_API_V4_URL}/projects/${CI_PROJECT_ID}/packages/pypi`（user `gitlab-ci-token` + `$CI_JOB_TOKEN`）。
- **#30 — 含前端(npm)产物的 Python 成员 wheel 化部署**：落部署节，补「按成员形态选打包路径」决策表的第二格：
  1. 构建后端切 hatchling（§2.1 escape hatch 已覆盖该触发）。
  2. 用 `artifacts` glob bundle 前端产物而非 `force-include`（后者源缺失即报错、毁掉 editable `uv sync`；前者存在即纳入、缺失不报错）。
  3. 包内路径「优先 bundled、回落 dev 源路径」：`_BUNDLED = Path(__file__).parent/"_frontend"`，`_FRONTEND = _BUNDLED if _BUNDLED.is_dir() else <dev 源路径>`。
  4. 构建顺序 + `--wheel`：`npm run build` → 拷 dist 进包 `_frontend/` → `uv build --wheel`（直接从源构建，避开 sdist→wheel 二段构建时 artifacts 漏进 sdist 的坑）。
  5. 产物仍 `py3-none-any`。
- **#26 — pip install --target 装本地开发 wheel**：补一段：`--target` 对同版本号跳过覆盖、`--force-reinstall` 在 `--target` 下卸载不可靠 → 旧版残留、改动不生效；可靠解：装前 `rm -rf <dir>/<pkg>*` 删旧再装。

### B. `rules/frontend.md`（2 条）

> 来自 [#34 worktree 内跑前端门禁需先备齐 node_modules（gitignore 不随 worktree 来）](https://github.com/pkulijing/claude-code-global/issues/34) · `type:docs` `area:doc` `priority:P2`
> 来自 [#29 rules/frontend.md 补：shadcn Input 包在 label 里触发 Biome noLabelWithoutControl，用 htmlFor/id 关联](https://github.com/pkulijing/claude-code-global/issues/29) · `type:docs` `area:doc` `priority:P2`

- **#34 — worktree 内跑前端门禁**：补一段「worktree 缺 `node_modules`（gitignore 不随 worktree 来），跑 `tsc`/`biome`/`vite build` 前先备齐」。两条路子：① 从主 checkout 软链 `node_modules`，跑完 `rm`；② worktree 内 `npm install`（npmmirror、增量幂等）。**警告**：软链法跑完务必删且**勿 commit**——`node_modules/` 带斜杠的 gitignore 模式不匹配软链，软链会以 untracked 冒进 `git status`。
- **#29 — shadcn Input 触发 Biome noLabelWithoutControl**：§4 风格细则补一条。根因：Biome `a11y/noLabelWithoutControl` 只认静态可识别的原生控件（`<select>`/`<input>` 放行），shadcn 的 `Input` 是自定义组件看不穿它内部渲染原生 `<input>` → label 判「无关联控件」。修法：`<label htmlFor="x">` + `<Input id="x">` 显式关联（自包含、a11y-correct，优于全局配 `inputComponents`）。

### C. `rules/ros2.md`（1 条）

> 来自 [#33 rules/ros2.md 增补「Python/pip 依赖」小节：默认 requirements.txt + pip，rosdep 自定义 yaml 仅必须时用](https://github.com/pkulijing/claude-code-global/issues/33) · `type:docs` `area:doc` `priority:P2`

- 新增「Python / pip 依赖」小节：
  - **默认**：`requirements.txt` + 一条 `pip install -r requirements.txt`；公网包走团队源（清华），私有包加 `--extra-index-url`（含只读 token）+ `--trusted-host`。
  - **rosdep 自定义 yaml 是重武器**：仅当确需 `rosdep install` 解析私有 key（如 CI 强制走 rosdep）才用；注意 rosdep pip installer 用 `sudo -H` 跑会剥 `PIP_CONFIG_FILE`/`PIP_TRUSTED_HOST`（需 sudoers env_keep 穿透），且 pip 配置文件的 trusted-host 不生效（需 `PIP_TRUSTED_HOST` env）。
  - 一句话原则：**选型前先看兄弟仓既有做法**，别凭「更正规」直觉上重机制。

### D. 新建 `rules/shell.md`（2 条合一）+ GLOBAL_AGENTS.md 指针

> 来自 [#28 中文 bash 脚本：$var 紧贴 CJK 在非 UTF-8 locale 吞字节，约定一律 ${var}](https://github.com/pkulijing/claude-code-global/issues/28) · `type:docs` `area:doc` `priority:P2`
> 来自 [#25 沉淀：CC 写含中文/全角字符的 shell 脚本的两类坑（注释字面双引号截断 / 全角字符并入变量名）](https://github.com/pkulijing/claude-code-global/issues/25) · `type:docs` `area:doc` `priority:P2`

两条都关于「中文/全角字符 × shell 引号与变量名」，合并成一篇新领域规则 `rules/shell.md`：

- **坑 1（#25）**：双引号字符串里的中文注释含字面半角 `"` → 提前闭合、静默截断命令（前半段照常执行、后半段静默丢失，极难归因）。修：注释用中文引号「」，禁字面半角双引号（确需转义 `\"`）。
- **坑 2（#28、#25 合并）**：`$var` 后紧贴 CJK / 全角标点，在非 UTF-8 locale（C/POSIX，CC 的 Bash 工具常处于此）或 `set -u` 下，CJK 首字节被并入变量名 → `unbound variable`。修：`$var` 后紧跟非 ASCII 字符一律 `${var}` 花括号定界；远端执行串只放 ASCII（中文进注释、不进执行串）。
- 文件头部写明**触发条件**（CC 生成/编辑含中文注释或中文输出的 bash 脚本时先读入），与既有 `rules/*.md` 同构。
- GLOBAL_AGENTS.md 加并列指针段（指针 + 触发条件两句），呼应「领域规则文档（rules/）」机制。

## 验收

- 4 个 rules 文件（含新建 shell.md）各段落落地、风格与既有章节一致（中文、WHY 优先）。
- GLOBAL_AGENTS.md 新增 shell 规则指针段。
- `/finish` 时 commit 写 `Closes #34 #33 #31 #30 #29 #28 #26 #25` 一并关闭 8 个 issue。

## 性质说明

纯文档轮，不涉及代码逻辑，TDD 章节不适用。rules 经 install.sh 目录级软链，合并入 master 后即时对两端 Agent 生效，无需重装。
