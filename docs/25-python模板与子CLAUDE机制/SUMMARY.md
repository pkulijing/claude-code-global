# SUMMARY

> 本轮一次性吃掉 [#11](https://github.com/pkulijing/claude-code-global/issues/11) 与 [#12](https://github.com/pkulijing/claude-code-global/issues/12) 两条 issue。归并的理由：两件事共同重塑"Python 项目模板"这份资产 —— 一侧改"项目骨架"（src 布局 + 可编辑安装），一侧改"领域规则文档"（沉淀 Python 风格 7 条 + 抽离子 CLAUDE.md），分开做会反复触碰相同文件（`GLOBAL_AGENTS.md` / `templates/python-uv/` / `bootstrap` / `sync-project-config` / `install.sh`）。

## 开发项背景

两个并行的"正向开发"需求：

- **#11 标准 src 布局**：来自 `wujie-data-format` 第 14 轮（mcap → LeRobot v2.1 转换器）实操中，新建 Python 包被纠正"遵循 src 布局"的反思。希望把它固化进共享 Python 模板，让所有新建 Python 包都自动落到 `src/<pkg>/`，配合 `pyproject.toml` 的 build-system / pytest 字段，避免每轮重复纠正。
- **#12 子 CLAUDE.md 机制 + 7 条 Python 风格**：来自一次 `mcap2lerobot` OO 改造 review 沉淀的 7 条跨项目可复用 Python 准则（OO 偏好 / 绝对 import / 文件命名 / 注释纪律 / Protocol 鸭子型 / dict-of-dicts 信号 / 整合类覆盖盲区）。期望沉淀到全局规范，并借这次机会引入"子 CLAUDE.md"机制 —— 让"宪法本体"不再随每条领域规则一起膨胀。

## 实现方案

### 关键设计

1. **`rules/` 目录承载领域规则文档**。仓库顶层新增 `rules/`，本轮只放 `rules/python.md`，未来按 `rules/<topic>.md` 拓展（git-hooks / release / 其他语言栈等）。`install.sh` 把整目录双轨软链到 `~/.claude/rules/` 与 `~/.codex/rules/` —— 与 `templates/` 同款目录级软链，新增 md 不需重跑 install。
2. **`GLOBAL_AGENTS.md` 的"指针 + 触发条件"约定**。顶层宪法不再内联具体语言细节，相应章节只留两句话：路径指针 + Agent 命中触发条件时**必须主动 Read**。**显式不依赖 CC/Codex 的 `@mention` 自动展开** —— 两端解析行为不一致，显式 Read 才是稳的契约。
3. **`uv init --package` 替代 `uv init --bare`** 落 src 布局。`uv init --bare` 当年是为"避免 hello world 文件"；`uv init --package` 的产物已是 `src/<pkg>/__init__.py` 空文件 + 含 build-system 的 `pyproject.toml`，干净度等价，并额外得到 src 骨架。这条选择**完全回避了包名占位符问题** —— 包名由 uv 在用户机器上根据目录动态生成，模板侧根本不出现 `<pkg>` 字面，无需任何渲染机制。
4. **接受 uv 默认的 `uv_build` 作 build backend，而非 `hatchling`**。smoke 验证发现 uv 0.11+ 默认产物用 `uv_build`，不是 issue #11 字面要求的 hatchling；用户拍板后接受默认（uv_build 纯 Python 零配置自动识别 src 布局，覆盖 99% 用例），并在 `rules/python.md` §2.1 给出 escape hatch："含 C/C++/Rust 扩展 / 自定义 build 脚本 / 不规范布局" 时切回 hatchling 的具体 toml 改法。
5. **#12 七条规则 1:1 原文搬入 `rules/python.md` §3**。`rules/python.md` 作为独立可任意长度的文档，承得起 issue 原文的"规则 + 为什么 + 边界 + 反例"密度；如果压缩成 bullet 反而损失说服力。

### 开发内容概括

**新增**：

- `rules/python.md` —— 4 节：环境与工具（uv / ruff / pypi index / torch 默认版） / 项目骨架（src + uv_build + hatchling escape hatch） / 开发风格（#12 七条原文） / 测试（呼应全局 TDD + pytest 目录约定）
- `templates/python-uv/__subpath__/pyproject.toml.pytest.fragment` —— 让 sync-project-config 合并 `[tool.pytest.ini_options] pythonpath=["src"] testpaths=["tests"]`
- `templates/python-uv/__subpath__/tests/__init__.py` + `test_smoke.py` —— 给 #12 第 7 条 "整合类至少 1 条 happy-path smoke" 一个最小起点
- `templates/python-uv/__subpath__/configs/.gitkeep` —— 与 `src/` `tests/` 平级的 configs 目录占位
- `docs/25-python模板与子CLAUDE机制/PROMPT.md` + `PLAN.md` + `SUMMARY.md`

**修改**：

- `GLOBAL_AGENTS.md` —— 加"领域规则文档（rules/）"小节（说明指针+触发条件契约）；Python 章节正文 8 行 → 4 行指针
- `install.sh` —— `deploy_agent()` 内增 `rules/` 整目录软链段，紧随 `templates/` 之后；`bash -n` 通过
- `skills/bootstrap/SKILL.md` —— Step 3.5.1 `uv init --bare` → `uv init --package` + 旁注更新；Step 5 收尾建议第 4 条同步改；新增第 10 条"Python 规范走 rules/python.md，无需项目根再放指针 md"
- `skills/sync-project-config/SKILL.md` —— Step 4.4.1 同步改 `uv init --package`
- `CLAUDE.md`（项目级）—— "目录结构"段补 `templates/` 与 `rules/` 两条（templates/ 是历史漏列，顺手修复）；"开发注意事项"段加 rules/templates 软链规则

**未实施**（PLAN §9.1 用户决策不做）：`templates/python-uv/__root__/CLAUDE.md.fragment` —— 不引入"项目级 CLAUDE.md 指针注入"机制，全靠 GLOBAL_AGENTS 顶层指针 + 触发条件搞定。

### 额外产物

- **PLAN §9.2 的硬规则被实际触发并验证**：smoke 时 `uv init --package` 默认用 uv_build 而不是 PLAN 假设的 hatchling，按 §9.2 "产物有 gap 当场停下汇报"流程，把决策权交回用户而不是擅自 fallback —— 这套"假设 → smoke → 汇报 → 用户拍板"的流程被实战验证一遍。
- **rules/python.md §2.1 的 escape hatch 文案**：对未来"项目需要 C/Rust 扩展时怎么办"给出明确切换路径，未来其它项目踩到这条会少走一段路。

## 局限性

1. **`rules/` 机制本轮只产出 `python.md` 一份**，没有立刻迁移其他可能的领域规则（git-hooks / release / TDD 细化等）；机制 + 范例都齐了，但单点样本无法证明这套约定对多 topic 都 robust。
2. **已有 Python 项目不会被自动迁移到 src 布局**：模板里**不含** src 骨架（uv init 在用户机器上动态生成），所以 `sync-project-config` 不会侵入式改老项目结构 —— 这是有意设计（避免破坏现有工作），但代价是老项目要拿到 #11 收益需要人工迁移。
3. **`uv_build` 仅支持纯 Python**：模板默认路径下，含 C/Rust 扩展的项目必须手动切回 hatchling（`rules/python.md` §2.1 已说明）。如果一个项目大半路才发现需要扩展，会触发一次 build-system 段重写。
4. **smoke 测试覆盖深度有限**：本轮验证 `uv init --package` 产物结构、`install.sh` 语法 / rules 段插入位置，但**没有**端到端跑 bootstrap → uv init → pytest smoke 的完整链路。如果 bootstrap 流程在 `uv init --package` 切换后有隐藏副作用（例如与已有 fragment 合并顺序冲突），要等首个走 bootstrap 的新项目暴露。
5. **rules/python.md §3 体量较大**（#12 原文 1:1 搬入）：Agent 每次触发条件命中都要 Read 全文，token 开销略高于"压缩版"。若实战发现命中过频，可考虑拆分细则（§3 单独成 `rules/python-style.md`），但本轮不预先拆。

## 后续 TODO

1. **观察 `rules/` 机制在多 topic 下的表现**：等积累 ≥ 2 条领域规则文档（如再加 `rules/git-workflow.md`）后，回顾"指针 + 触发条件"约定是否够用、是否需要在 GLOBAL_AGENTS 加一个"已沉淀的领域规则列表"的常驻索引。
2. **跑一次完整 bootstrap → pytest smoke**：找一个全新空目录走一遍 `/bootstrap` python-uv，验证 `uv init --package` → 自动合并 pytest fragment → `uv run pytest tests/` 通过。若发现 fragment 与 `uv init --package` 输出格式冲突（uv 用 inline table 而我们的 fragment 是 table heading），追加 fragment 合并逻辑修复。
3. **考虑给 `rules/python.md §3` 的 7 条加 commit-hook 校验**：尤其 §3.4（禁注释引 round-XX / issue #N）可以用 ruff 自定义规则或 grep-style hook 在 pre-commit 阶段卡掉，避免规则只停留在文档层。
4. **判断是否要给 `pyproject.toml.pytest.fragment` 加 ruff/coverage 配套字段**：目前 fragment 只配了 pytest 路径，没有 coverage 默认源路径 / ruff isort first-party 段；下次跑 sync 实战时如发现缺，补一刀。

## 可沉淀项

按 finish skill 的判定标准（跨项目通用 + 有具体落点 + ≥ 2 次模式或明显通用）和"宁缺毋滥"原则筛选，本轮可沉淀候选：

1. **"领域规则文档"机制本身就是为这种需求设计的**。本轮把"Python 规则"从 GLOBAL_AGENTS 抽出来放进 `rules/python.md`，未来其他语言 / 流程的细则也应该走同一通道。**去向**：已沉淀到本仓库（自指仓库），机制 + 范例都在；下一条具体的 `rules/<topic>.md` 由实际触发它的 round 添加，不预先 file。
2. **"假设 → smoke → 汇报 → 用户拍板"的 PLAN §9 模式**。`uv init --package` 默认 backend 与原 issue 字面假设有 gap 是被实际触发的 case；PLAN 里预先列"待验证假设 + fallback 方案 + 走偏时如何中断"这一节，让执行阶段无需临场判断。**去向**：建议未来 PLAN 模板默认含一个"假设清单 + 触发什么 fallback"段。但这是 plan/start skill 内部结构调整，非本轮范围；记在此处供未来回顾。
3. **本仓库 `CLAUDE.md` 在加新条目时"并列项应平等呈现"**：本轮加 `rules/` 时顺手发现 `templates/` 历史漏列，按 memory 中的同名 feedback 一并补齐。**去向**：已经在本轮变更里完成补漏，无需另开 issue。这条 memory 准则继续有效，未来加目录条目时记得扫一眼。

**自指守卫触发**：本仓库就是 claude-code-global 本身（`$HOME/.claude/global-repo` 即指向本仓库），按 finish skill §3.3，跨项目资产候选**不**走跨仓库 file API，本步剩余跳过。上述 3 条已就地落地或留作回顾。
