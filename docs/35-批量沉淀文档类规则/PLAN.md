# PLAN — 批量沉淀文档类规则（8 条 issue）

纯文档轮，无代码逻辑、无 TDD。所有改动落在 4 个 `rules/*.md`（含 1 个新建）+ `GLOBAL_AGENTS.md` 指针。改完即时经 install.sh 目录级软链对两端 Agent 生效，无需重装。

## 1. `rules/python.md` —— 新增 §5「打包 · 发布 · 安装」

§1「环境与工具」的「禁止裸 pip」是**开发期**约束；本轮三条都是**打包/发布/安装期**主题，混进 §1 会污染语义，故收口为新 §5（追加在 §4 测试之后，不动既有编号）。三个子节：

- **§5.1 含前端(npm)产物的 Python 成员 wheel 化（#30）** —— 接续 §2.1 hatchling escape hatch，给出「按成员形态选打包路径」第二格：
  1. 构建后端切 hatchling；
  2. `[tool.hatch.build.targets.wheel] artifacts = ["src/<pkg>/_frontend/**"]` bundle 前端产物，**而非 `force-include`**（源缺失即报错、毁 editable `uv sync`；artifacts 存在即纳入、缺失不报错）；
  3. 包内路径「优先 bundled、回落 dev 源」：`_BUNDLED = Path(__file__).parent/"_frontend"`，`_FRONTEND = _BUNDLED if _BUNDLED.is_dir() else <dev 源>`；
  4. 构建顺序 + `--wheel`：`npm run build` → 拷 dist 进包 `_frontend/` → `uv build --wheel`（绕开 sdist→wheel 二段构建漏 artifacts 的坑）；
  5. 产物 `py3-none-any`。
- **§5.2 uv + 自托管 GitLab Package Registry（#31）** —— 两个固定坑 + 上传 URL：
  1. TLS：uv 默认 rustls + 内置 Mozilla 根、不读系统信任库 → 内部 CA 报 `invalid peer certificate: UnknownIssuer`；`export UV_SYSTEM_CERTS=true`（旧名 `UV_NATIVE_TLS` 已废弃），CA 自定义路径设 `SSL_CERT_FILE`；publish 与 install 都适用。
  2. `uv publish --check-url` 与 GitLab PyPI 不兼容（simple 索引 `Content-Type: text/plain`，uv 只认 JSON/HTML → `Failed to query check URL`）；GitLab 上别用 `--check-url`，重发先删旧版或 bump。
  3. 上传 URL：`${CI_API_V4_URL}/projects/${CI_PROJECT_ID}/packages/pypi`，user `gitlab-ci-token` + `$CI_JOB_TOKEN`。
- **§5.3 pip install --target 装本地开发 wheel（#26）** —— `--target` 对同版本号跳过覆盖、`--force-reinstall` 在 `--target` 下卸载不可靠 → 旧版残留、改动不生效；可靠解：装前 `rm -rf <dir>/<pkg>*` 删旧再装。

## 2. `rules/frontend.md` —— §1 补 worktree 门禁注记 + §4 新增 4.4

- **§1「环境与工具」末尾补一段（#34）**：worktree 缺 `node_modules`（gitignore 不随 worktree 来），跑 `tsc`/`biome`/`vite build` 前先备齐。两条路：① 主 checkout 软链 `node_modules`，跑完 `rm`；② worktree 内 `npm install`（npmmirror、增量幂等）。**警告**：软链法跑完必删且勿 commit——`node_modules/` 带斜杠的 gitignore 不匹配软链，会以 untracked 冒进 `git status`。
- **§4 新增 4.4「label 关联自定义输入组件用 htmlFor/id」（#29）**：根因——Biome `a11y/noLabelWithoutControl` 只认静态可识别的原生控件（`<select>`/`<input>` 放行），shadcn `Input` 是自定义组件看不穿。修法：`<label htmlFor="x">` + `<Input id="x">` 显式关联（自包含、a11y-correct，优于全局配 `inputComponents`）。

## 3. `rules/ros2.md` —— 新增「Python / pip 依赖」节

插在 §4（CMakeLists C++ 依赖）之后作为新 §5，**与 C++ 依赖节并列**（读者流：包类型→package.xml→C++ 依赖→Python 依赖→分层→测试→清单→构建），原 §5「纯逻辑分层」→§6、§6 测试→§7、§7 清单→§8、§8 构建→§9 顺延。内容：

- **默认**：`requirements.txt` + 一条 `pip install -r requirements.txt`；公网包走清华源，私有包加 `--extra-index-url`（含只读 token）+ `--trusted-host`。
- **rosdep 自定义 yaml 是重武器**：仅当确需 `rosdep install` 解析私有 key（如 CI 强制走 rosdep）才用；坑——rosdep pip installer 用 `sudo -H` 跑会剥 `PIP_CONFIG_FILE`/`PIP_TRUSTED_HOST`（需 sudoers env_keep 穿透），pip 配置文件的 trusted-host 不被采纳（需 `PIP_TRUSTED_HOST` env）。
- **一句话原则**：选型前先看兄弟仓既有做法，别凭「更正规」直觉上重机制。

> 顺延后核对：§6 测试内对「rules/python.md §4」「§3.7」均为外部引用、不受本文件改号影响；GLOBAL_AGENTS.md ros2 指针段描述的是内容关键词、不含本地章节号，无需改。

## 4. 新建 `rules/shell.md`（#28 + #25 合一）

两条都是「中文/全角字符 × shell 引号与变量名」，合成一篇新领域规则，结构同既有 `rules/*.md`（顶部 install.sh 双轨软链说明 + **触发条件**：CC 生成/编辑含中文注释或中文输出的 bash 脚本时先读入）。两节：

- **坑 1：双引号串内中文注释含字面半角 `"` → 提前闭合、静默截断命令**（#25）。最小复现 + 「前半段照常执行、后半段静默丢失」的阴险表现。修：注释用中文引号「」，禁字面半角双引号（确需转义 `\"`）。
- **坑 2：`$var` 紧贴 CJK/全角标点 → 非 UTF-8 locale 或 `set -u` 下并入变量名报 unbound**（#28 + #25 合并）。修：`$var` 后紧跟非 ASCII 一律 `${var}`；远端执行串只放 ASCII（中文进注释不进执行串）。
- 可选自检：grep 双引号 heredoc 注释里的字面 `"` / `$word` 紧贴非 ASCII（作为附注，不强制）。

## 5. `GLOBAL_AGENTS.md` —— 注册 shell.md 指针

- 「领域规则文档（rules/）」的「当前已沉淀」清单加一行 `- rules/shell.md — Shell 脚本（中文/全角字符 × 引号与变量名约定）`。
- 末尾 lark 节之后新增「## Shell 脚本开发规则」指针段（指针 + 触发条件两句，与既有各栈段同构）。

## 6. 收尾（/finish 阶段，本轮不做）

- commit 写 `Closes #34`、`Closes #33` …… `Closes #25`（8 条各一行），合并 master 自动关 8 个 issue。
- 这些 issue 均为跨仓自动沉淀、未进 BACKLOG，故 BACKLOG.md 无需改。
- DEVTREE 由 /finish/devtree 流程处理（Epic 结构作者维护），不在本轮手改。

## 验收清单

- [ ] python.md §5 三子节落地，与既有风格一致
- [ ] frontend.md §1 worktree 注记 + §4.4 落地
- [ ] ros2.md 新增 Python/pip 依赖节 + 顺延编号无残留错号
- [ ] 新建 rules/shell.md，头部双轨说明 + 触发条件齐备
- [ ] GLOBAL_AGENTS.md 清单 + 指针段两处都加
- [ ] 全程中文、WHY 优先、无 round/issue 历史标记混入正文（除引用块来源）
