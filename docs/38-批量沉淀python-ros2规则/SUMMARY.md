# round38 · 开发总结：批量沉淀 5 条跨项目文档规则（Python × ROS 2）

## 一、开发项背景

5 条「跨项目自动沉淀、未进任何 BACKLOG」的 `type:docs` / `area:doc` / `priority:P2` issue，来源全部是 GitLab 自托管
`gitlab.anyverse.work` 的 teleop / teleop-operator 项目（外部不可达，仅作来源标注）。它们各自记录了一条在真实项目里踩过、
且**跨项目通用**的坑或骨架，希望落进领域规则文档供未来任何项目直接抄，避免第 N 次去兄弟仓考古。本轮把这 5 条一次性沉淀，
与 round35「批量沉淀 8 条文档类规则」同模。

涵盖 issue（本轮一次收 5 个，`Closes` 各占一行）：

| issue | 落点                          | 一句话                                                                                          |
| ----- | ----------------------------- | ----------------------------------------------------------------------------------------------- |
| #36   | `rules/python.md` §4          | 测试 fixture 不复用被测代码的同套约定假设，否则测试只验证「代码自洽于错误假设」、丧失证伪能力   |
| #43   | `rules/python.md` §2.3        | src 布局下顶层同名目录遮蔽 src 真包（PEP420 namespace 坑）：顶包 import 成功、子模块挂          |
| #38   | `rules/python.md` §5.4 + §5.2 | 应用内 uv tool 更新自检 + 一键升级标准骨架；GitLab simple 索引程序化查最新版本                  |
| #37   | `rules/ros2.md` §2 表 + §4.6  | 纯 Python 节点需 source-time hook 时 `ament_python` 做不到、必须 `ament_cmake_python`           |
| #42   | `rules/ros2.md` §5 子节       | 纯 Python 包双链路：同一包既作 uv 成员（`uv_build`）又作 colcon 包（`ament_cmake` 原生 import） |

> #40（废弃 `docs/BACKLOG.md` 改云端 issue 单真源）是 skill + 宪法 + labels 的结构性改动、含未定设计决策，**不在本轮**，
> 已约定单开 round39。本轮开轮时（`/start 36 37 38 40 42 43`）经 `AskUserQuestion` 确认「拆两轮」后把 #40 剥离。

## 二、实现方案

### 关键设计

1. **落点「贴最近的现有章节、尽量不 renumber」**：
   - #43 → 新增 `python.md §2.3`（§2.1/§2.2 是 escape hatch，§2.3 定位「排障」，与 §2.2 已有「同名 tests 碰撞」并列成
     「src 布局命名撞车」两坑，且**显式点明两者是不同坑、不同解、别混用**——§2.2 用 `--import-mode=importlib`，§2.3 用
     剔仓根 `sys.path` + `--import-mode=prepend`）。
   - #36 → `python.md §4` 新增一条 bullet（**不**塞进 §3 的 7 条编号列表——§3 intro 明确「详见 issue #12」，加第 8 条会
     破坏该 attribution；§4 本就是测试段，落点更干净）。
   - #38 → `python.md` 新增 §5.4（§5 已有 5.1/5.2/5.3，自然续）+ §5.2 末补一段，并把 §5 intro 硬编码的「下面三条」改
     「下面几条」（避免加了第 4 条后计数失真）。
   - #37 → `ros2.md §2` 表加 `ament_cmake_python` 行 + 给 `ament_python` 行加边界注（指向 §4.6）；新增 §4.6。
   - #42 → `ros2.md §5` 末追加**无编号 `###` 子节**「双链路」。**刻意不 renumber 成新 §6**：§5 之后是 §6~§9，插正式新
     §6 要整体后移并改 §8 检查清单等标号、churn 大、易留悬空引用；追加无编号子节零 renumber、又满足 issue「§5 旁增一节」。
2. **规则正文不带开发历史标记**：遵 `python.md §3.4`，规则本身不写 round-XX / issue# / PLAN.md；来源信息只进本 SUMMARY /
   commit / issue 回链。示例里保留 `my_proto` / `my_pkg` 等通用占位名（原 teleop_proto 换成通用名）。
3. **一处事实冲突的诚实调和**：#38 原文称 GitLab simple 索引 `Content-Type: text/html`，而 `python.md §5.2` 既有条目
   （`--check-url` 坑）记的是 `text/plain`——同一 section 内两处相互矛盾。自托管实例外部不可达、无法现场实测，故没有硬塞
   矛盾断言，而是在新增「补充」段统一为「随 GitLab 版本可能是 `text/html` 或 `text/plain`，**要点一致：不是 JSON**，一律
   拉页面正则解析 wheel 文件名」，抓住两者都认同的不变核心。

### 开发内容概括

- `rules/python.md`（+64 行）：§2.3（新）、§4 一条 bullet、§5.4（新）、§5.2 补段、§5 intro 计数措辞。
- `rules/ros2.md`（+55 行）：§2 包类型表 +1 行 & 边界注、§4.6（新）、§5 末 +1 无编号子节；§6~§9 保持不动。
- 每条含最小可抄骨架：§2.3 conftest 剔仓根片段、§5.4 两版本源解析 `latest_pypi` / `latest_gitlab`、§4.6 与双链路各一段
  `ament_cmake_python` CMakeLists。

### 额外产物

- 无（纯文档轮，无代码 / 无测试 / 无脚本）。计划与需求文档 PROMPT.md / PLAN.md 已就位。

## 三、局限性

1. **#38 的 Content-Type 事实未现场实测**：`text/html` vs `text/plain` 的冲突按「两者都可能、抓不变核心」写。若日后能实测
   目标 GitLab 实例的真实返回，可回来收紧 §5.2 补段与既有 `--check-url` 条目的措辞、消除同 section 内的表述并存。
2. **骨架的正则假设纯 Python wheel 命名**：§5.4 `latest_gitlab` 与文中示例用 `<pkg>-<ver>-py3-none-any.whl` 正则，若某包
   发平台特定 wheel（含 C 扩展）则需放宽正则——文中未展开这一变体。
3. **#38 / #42 的「可选模板样例包」本轮未做**：按开轮取舍只落规则文字，未给 `ros2` stack 模板加双链路样例包、也未给更新自检
   加样例。规则里有可抄骨架，但没有「跑得起来的样例工程」。

## 四、后续 TODO

1. **#40 单开 round39**：废弃 `docs/BACKLOG.md`、需求管理改云端 issue 单真源（含方向 A/B 与 4 条「刻意不做」去处的设计决策）。
   收尾 round38 后 `/start 40`。
2. **（可选）实测 GitLab simple 的 Content-Type** 后回收紧 §5.2 措辞（见局限性 1）。
3. **（可选）给 `ros2` stack 模板加双链路样例包**：`pyproject uv_build` + `package.xml`/`CMakeLists` 并存的可构建样例
   （见局限性 3）；若做，属「改模板」范畴，建议单开一轮。

## 五、可沉淀项

**自指守卫命中**：本轮工作树 `common-dir-owner` == `~/.claude/global-repo`，即当前仓库就是 claude-code-global 本身。按
`/finish` Step 3.3，跨项目资产候选不跨仓库 API file，改走本地 `/backlog`。

反思本轮，有 1 条**流程层**候选（跨项目通用、有具体落点、已 ≥2 次出现），达标：

- **「批量沉淀同质文档 issue」应固化为 `/finish` 的一个显式支路 / `/start` 的批量取舍提示**。现象：round35（8 条）、round38
  （本轮 5 条）都是「一次 `/start` 收多个同质 doc issue → 拆轮取舍 → 逐条落 rules → 一个 commit 多个 Closes」。这套已重复
  ≥2 次、且每次都靠人临场用 `AskUserQuestion` 决定拆分。落点候选：`/start` skill 在「多 issue 参数」时给标准化拆分提示；或
  `/finish` 对「一轮多 Closes」的 commit body 生成做模板化。**去向：本地 `/backlog` 起 issue**（claude-code-global 内部待办，
  遵本项目「issue 进 BACKLOG」约定），不在本轮替 file。

其余观察（Content-Type 调和手法、落点不 renumber 原则）属**本轮特异或已隐含在既有规则里**，不单独沉淀，避免噪音。
