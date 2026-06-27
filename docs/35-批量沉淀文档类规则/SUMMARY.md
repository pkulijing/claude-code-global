# SUMMARY — 批量沉淀文档类规则（8 条 issue）

## 开发项背景

claude-code-global 的 issue 列表里积压了一批 `type:docs` 的跨项目沉淀 issue —— 它们由外部项目（teleop / teleop-operator）的 `/finish` Step 3 反思自动跨仓提来，每条都是「某个领域规则文档里值得补一段约定」，互不耦合、单条体量小。逐条单开一轮收尾成本失衡，故本轮把性质同质（纯文档追加）的 8 条一次性消化：

- #31 / #30 / #26 → `rules/python.md`（打包 / 发布 / 安装期的坑）
- #34 / #29 → `rules/frontend.md`（worktree 门禁 / shadcn label a11y）
- #33 → `rules/ros2.md`（ROS 包怎么装 pip 依赖）
- #28 / #25 → 新建 `rules/shell.md`（中文 / 全角字符 × shell 引号与变量名）

**刻意排除**两条形似而质不同的：#27（split-repo + 多轮隔离方法论，是开放式探索而非一段规则追加）、#32（`.gitlab-ci.yml` YAML 锚点重构，`type:refactor` `area:template`，是模板代码改动而非纯文档）。

## 实现方案

### 关键设计

1. **按「目标文件」而非「按 issue」归并落点**。8 条先聚类到 4 个 rules 文件，再逐文件成段，避免同一文件被多次零散编辑、风格漂移。
2. **python 三条收口为新 §5「打包·发布·安装」**，而不是塞进 §1「禁裸 pip / 用 uv」。理由：§1 管的是**开发期**约束，而 #30/#31/#26 全是**打包 / 发布 / 安装期**主题（wheel 化、推 registry、装到目标），混进 §1 会污染语义层次。新 §5 还把 #30 与既有 §2.1 hatchling escape hatch 串成「按成员形态选打包路径」决策（纯 Python → uv_build；含前端产物 → hatchling artifacts；含 C 扩展 → 目标机原生 build）。
3. **#28 + #25 合并成新 `rules/shell.md`** 而非塞进 GLOBAL_AGENTS.md 的某段。两条同主题（中文 / 全角 × shell），单独成篇并写明触发条件，与既有 `rules/*.md` 同构；GLOBAL_AGENTS.md 只加「指针 + 触发条件」两句，遵循宪法「领域规则下沉、宪法只留指针」的既定机制。
4. **ros2.md 新节插在 §4（C++ 依赖）之后作为 §5，与 C++ 依赖节并列**（读者流：包类型→package.xml→C++ 依赖→Python 依赖→分层→测试→清单→构建），原 §5–§8 顺延为 §6–§9。选择「插入 + 顺延编号」而非「追加到文末」，是为保持「依赖」主题在文档里聚拢。

### 开发内容概括

- `rules/python.md`：新增 §5（§5.1 含前端产物 wheel 化 / §5.2 自托管 GitLab Registry 两坑 + 上传 URL / §5.3 pip --target 同版本不覆盖）。
- `rules/frontend.md`：§1 末补「worktree 缺 node_modules 跑门禁前先备齐」（软链勿 commit 警告）；§4 新增 4.4「label 关联自定义输入组件用 htmlFor/id」。
- `rules/ros2.md`：新增 §5「Python / pip 依赖」，§5–§8 顺延为 §6–§9。
- `rules/shell.md`：新建，含双轨软链说明 + 触发条件 + 两坑 + 可选自检。
- `GLOBAL_AGENTS.md`：「当前已沉淀的领域规则」清单加 shell.md 一行；末尾新增「## Shell 脚本开发规则」指针段。

### 额外产物

无（纯文档轮，无测试 / 脚本产物）。

## 局限性

- **未为 shell.md 配自动门禁**：#25/#28 在规则里附了「可选自检」grep 思路，但没做成 hook / pre-commit 检查，仍靠 Agent 写脚本时自觉遵守。
- 各 rules 文档里的版本相关事实（如 uv `UV_NATIVE_TLS` 已废弃、GitLab simple 索引 `text/plain`）会随上游演进过时，需偶尔人工复核。

## 后续 TODO

- 若中文 shell 脚本坑反复出现，可考虑把 shell.md 的「可选自检」升级为一个轻量 PostToolUse hook（编辑 `.sh` 后扫双引号 heredoc 注释里的字面 `"` 与 `$word` 紧贴非 ASCII），从「文档约定」升到「机器拦截」。
- python.md §5「按成员形态选打包路径」已成三格，未来若再撞到新形态（如含 Rust 扩展的混合包）可继续补格。

## 可沉淀项

本轮**自身**就是「跨项目沉淀」的消化轮，产物即沉淀。回看本轮过程，值得反向沉淀回流程的候选：

- **同质 `type:docs` issue 批量消化是一种可复用收尾模式**（跨项目通用 / 有落点 / ≥2 次可预期）。但落点模糊（要不要给 `/finish` 或新 skill 加「批量 close 多 issue」支持？还是保持现状靠人判断？），且本轮已用「自由描述 + 多 `Closes #N`」走通，机制上不缺能力。倾向**不**提 issue，记此即可。

除此之外无更强候选。本仓库即 claude-code-global，跨项目资产候选按 Step 3.3 自指守卫走本地 `/backlog`，本轮无需 file。
