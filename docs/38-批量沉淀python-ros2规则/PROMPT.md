# round38 · 批量沉淀 5 条跨项目文档规则（Python × ROS 2）

本轮把 5 条「跨项目自动沉淀、未进任何 BACKLOG」的文档类 issue 一次性落进领域规则文档
（`rules/python.md` / `rules/ros2.md`）。均为 `type:docs` / `area:doc` / `priority:P2`，
清一色「往 rules/\*.md 追加一段规则」的同质工作，与 round35「批量沉淀 8 条文档类规则」同模。

> 与 #40（废弃 `docs/BACKLOG.md`、改云端 issue 单真源）**不在本轮**——那是 skill + 宪法 + labels
> 的结构性改动、含未定设计决策，单开一轮（round39）处理。

## 本轮涵盖的 issue

| issue                                                            | 落点              | 一句话                                                                                                                                     |
| ---------------------------------------------------------------- | ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| [#36](https://github.com/pkulijing/claude-code-global/issues/36) | `rules/python.md` | 测试 fixture 不要复用被测代码的同一套约定假设（坐标系/单位/字节序…），否则测试只验证「代码自洽于自己的错误假设」、丧失证伪能力             |
| [#38](https://github.com/pkulijing/claude-code-global/issues/38) | `rules/python.md` | 「应用内 uv tool 更新自检 + 一键升级」标准骨架（5 点可抄清单）+ 扩充 §5.2「程序化查 GitLab simple 索引最新版本」                           |
| [#43](https://github.com/pkulijing/claude-code-global/issues/43) | `rules/python.md` | src 布局下顶层项目目录与包同名 → 遮蔽 src 真包（PEP420 namespace 坑）；症状/判据/解法排障小节                                              |
| [#37](https://github.com/pkulijing/claude-code-global/issues/37) | `rules/ros2.md`   | 纯 Python 节点需 source-time hook 时 `ament_python` 做不到、必须 `ament_cmake_python`（`ament_environment_hooks`）                         |
| [#42](https://github.com/pkulijing/claude-code-global/issues/42) | `rules/ros2.md`   | 纯 Python 包双链路：同一包既作 uv workspace 成员（`uv_build` 发 wheel）又作 colcon 包（`ament_cmake` 原生 import），两套构建元数据物理隔离 |

Labels 均为：`type:docs` `area:doc` `priority:P2`。

## 每条的详细需求（原 issue body 提炼）

### #36 — 测试 fixture 独立来源

- **现象（teleop round17 真实事故）**：`test_head_planner.py` 用 `_quat_z(theta)` 构造「左右转头」输入、断言驱动
  yaw 关节；而生产代码 `_quat_to_yaw_pitch` **也**假设「左右=绕 Z(yaw)」。fixture 与被测代码复用**同一套（错误的）
  坐标系约定** → 单测 7/7 全绿但真机方向全错。真相：Pico 头显左右转头让 qy 主导、绕 Z 几乎不动，约定从根上就错。
- **通用命题**：凡「测试输入由被测代码同一套约定假设生成」（坐标系/单位/编码/协议字节序…），测试即自我循环论证，
  无法发现「假设错了」这类 bug。是 §3.4「注释写当前真相」的邻域新变体（§3.4 管注释，这条管测试 fixture）。
- **落点**：§3.4 邻域或 §4 测试段补一条：这类「外部约定/物理映射」逻辑，fixture 应来自**独立来源**——真实采集数据、
  手算地面真值、或不同推导路径的等价构造，使「假设错了」能被测出。

### #38 — 应用内 uv tool 更新自检骨架

- **背景**：已在 daobidao（r25 更新检查+一键升级、r34 TTL）与 teleop-operator（r27）两个项目独立从零实现同一套骨架，
  差异只在「版本源」和 UI 框架。第三个项目（凡 `uv tool install` 分发的应用）很可能再遇到。
- **骨架不变部分（5 点可抄清单）**：
  1. 查最新版本：PyPI JSON 读 `info.version`；GitLab simple 返 PEP 503 HTML，从 wheel 文件名正则提版本。
  2. `packaging.version.Version` 比较 + 过滤 prerelease（`.is_prerelease`，否则 rc 被误判为最新）。
  3. `uv tool upgrade <pkg>` 命令拼装（`shutil.which("uv")` 找 uv；私有 registry 带 `--extra-index-url` +
     `--allow-insecure-host`）。
  4. 后台线程 + TTL（stale-while-revalidate）+ 失败静默（不拖启动、不抛异常、网络失败返 None）。
  5. 不自动重启：upgrade 覆盖 venv `.py` 不影响正在跑的进程；提示用户手动重启。
- **落点**：①`rules/python.md` 新增一节「应用内更新自检的标准骨架」，5 点固化，版本源按 PyPI JSON / GitLab simple
  两种分别给解析片段；②扩充 §5.2，补「程序化查询最新版本」——GitLab simple 索引返 PEP 503 HTML（列 wheel 文件名，
  正则提版本取最高 stable），与 §5.2 已有「`--check-url` 不兼容」同层知识的自然延伸。

### #43 — src 布局顶层同名目录遮蔽 src 真包

- **症状（teleop round21 踩两次，误导性强）**：src 布局下顶层 `<pkg>/`（装 `pyproject.toml`/`package.xml`、**非**
  Python 包、无 `__init__.py`）与 `src/<pkg>/` 真包同名。仓库根进 `sys.path` 时（`python -m pytest` 塞 CWD、或 `cd`
  仓根跑 python），`import <pkg>` 先命中顶层目录 → 当作 PEP420 namespace 包 → 顶包 import **成功**（`__file__` 为 None）
  但 `import <pkg>.<submodule>` **失败** `ModuleNotFoundError`。误导点：看起来像「子模块没装」，不会联想到「顶层同名目录遮蔽」。
- **判据**：`<pkg>.__path__` 同时含顶层项目目录路径 + install/editable 真包路径（两 portion 拼接），`__file__` 为 None。
- **两场景两命运**：测试时（pytest 仓根跑）触发；生产运行时（site-packages import、CWD 不在仓根）天然不触发。
- **解法**：仓根 `conftest.py` 把仓根从 `sys.path` 剔除 + `--import-mode=prepend`：
  ```python
  import os, sys
  _ROOT = os.path.dirname(os.path.abspath(__file__))
  sys.path[:] = [p for p in sys.path if p and os.path.abspath(p) != _ROOT]
  ```
- **落点**：`rules/python.md` §2 / §2.2 加排障小节（症状+判据+解法），与 §2.2 已有「同名 tests 碰撞」并列成「src 布局
  命名撞车」两个已知坑。

### #37 — ament_python 无法注册 source-time hook

- **背景（teleop round18「source 时装依赖」）**：需求是 `source install/setup.bash` 时自动 `pip install -r
requirements.txt`。`teleop_gateway` 纯 Python 落 `ament_python`，初版赌「setup.py `data_files` 铺
  `ament_index/resource_index/environment/<pkg>` marker，colcon 就会 source 这个 hook」。
- **双重证伪**：colcon-ros 的 ament_python build task 生成包 `package.dsv` 时，要 source 哪些 hook 是**写死的**——
  只有 `pythonpath` + `ament_prefix_path`，**不扫** `share/<pkg>/environment/`、**不读** `resource_index/environment`
  marker、**不调**任何 hook 发现函数。那套 `environment/` + marker 是 **ament_cmake** 的 `ament_environment_hooks()`
  宏专属。现象：纯 ament_python 版 `package.sh` 里没有 source hook 的行 → source 很快结束、不触发。
- **正解**：包从纯 `ament_python` 改 **`ament_cmake_python`**（加 CMakeLists、`build_type=ament_cmake`，用
  `ament_python_install_package` 装模块 + `install(PROGRAMS)` 装 entry + `ament_environment_hooks()` 注册 hook）。
  这是唯一能让「source 时自动跑自定义脚本」的 ROS 官方机制。已在 aarch64 真机验证 source 真触发 pip。
- **落点**：①§2 包类型表给 `ament_python` 行加边界注，或新增 `ament_cmake_python` 行（纯 Python 节点 + 需 source-time
  hook / 其它 CMake 能力）；②§4 或新小节点明 `ament_environment_hooks(<name>.sh.in)` 是注册 source-time hook 的正道，
  纯 ament_python（setup.py + data_files / ament_index marker）**不被 colcon source**；可附最小骨架。

### #42 — 纯 Python 包双链路（uv 成员 ∩ colcon ament 包）

- **背景（teleop round21「operator 整仓迁入与两仓合并」）**：同一仓库同时是 uv workspace 与 colcon workspace，共享
  契约包 `teleop_proto` 需**同时**：作 uv 成员用 `uv_build` 打 wheel/发 PyPI/macOS editable 跑测试；作 colcon 包被端侧
  `colcon build` + source 后**原生 import**、零运行期 pip。
- **通用命题**：任何「PC 端 uv 工具 + 端侧 ROS2 节点共享一份 protobuf/契约/纯逻辑」的项目都会遇到。当前 §5 只覆盖
  「ament_python 包怎么装 pip 依赖」，没覆盖「同一包如何同时满足 uv 成员 + colcon 包两种消费」。
- **做法（双链路 = 两套构建元数据物理隔离，各读各的）**：uv 侧不动（`pyproject.toml` 保留 `[build-system] uv_build`）；
  colcon 侧同目录新增 `package.xml`（`ament_cmake` + `ament_cmake_python`）+ `CMakeLists.txt`：
  ```cmake
  cmake_minimum_required(VERSION 3.8)
  project(teleop_proto NONE)   # 纯 Python 无编译，NONE 跳过编译器探测
  find_package(ament_cmake REQUIRED)
  find_package(ament_cmake_python REQUIRED)
  ament_python_install_package(${PROJECT_NAME} PACKAGE_DIR src/${PROJECT_NAME})
  ament_package()
  ```
  隔离关键：colcon 只读 `package.xml`/`CMakeLists.txt`，uv 只读 `pyproject.toml`；选 `ament_cmake`（而非 `ament_python`）
  正是为避免 `setup.py` 布局与 `uv_build` 的 src 布局抢同一目录的元数据。下游运行期 import 靠 `<exec_depend>` 声明。
- **落点**：①`rules/ros2.md` §5 旁增一节「ROS2 包同时作 uv workspace 成员 / PyPI 发布（双链路）」，固化 CMake 骨架 +
  「两套元数据物理隔离」原则，与 §5 互补（一个装依赖、一个同包双消费）；②可选：`ros2` stack 模板加双链路样例包。

## 验收标准

- 5 条规则分别落进对应 `rules/*.md` 的合适章节，风格、密度、编号与既有条目一致（沿用 round35 的呈现方式）。
- 不引用 round-XX / issue# / PLAN.md 等开发历史标记进规则正文本身（遵 §3.4「注释写当前真相」）；来源信息只在 commit /
  SUMMARY / issue 回链里。
- `rules/python.md` / `rules/ros2.md` 顶部指针章节（触发条件）如涉及新增小节需相应更新目录感。
- 不改任何代码 / skill / 模板（#38、#42 的「可选模板样例」按取舍决定，默认**不做**，只落规则文字）。
- commit 描述含 5 条 `Closes #36 #38 #43 #37 #42`（`/finish` 收尾时统一处理）。

## 备注

- 本轮为纯文档（prose）改动，无代码、无测试，TDD 章节不适用（同 round35）。
- 5 条来源全部为 GitLab 自托管 `gitlab.anyverse.work` 的 teleop / teleop-operator（外部不可达，仅作来源标注）。
