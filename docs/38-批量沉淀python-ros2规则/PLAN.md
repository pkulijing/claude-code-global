# round38 · 实现计划

纯文档（prose）改动：把 5 条规则落进 `rules/python.md`（#36/#38/#43）与 `rules/ros2.md`（#37/#42）。
无代码、无测试，TDD 不适用（同 round35）。下面逐条给**落点 + 内容提要 + 关键骨架**，末尾列需拍板项。

## 全局原则（5 条都遵守）

- 规则正文**不引用** round-XX / issue# / PLAN.md 等开发历史标记（遵 `rules/python.md §3.4`）；来源信息只进 commit /
  SUMMARY / issue 回链。示例里的 `teleop_proto` 等具体包名可保留（作为具象骨架），但叙述用通用语言。
- 风格、密度、编号、代码块 fence 语言标注与既有条目一致；每条落在最贴近的现有章节，尽量**不renumber**已有小节。
- 章节顶部「触发条件」指针不动（新增的都是既有触发面内的细化）。

---

## A. `rules/python.md`（3 条：#36 / #43 / #38）

### A1 · #36 → 新增 §4 一个 bullet「测试 fixture 独立来源」

- **落点**：§4「测试」段末尾追加一个 bullet（**不**塞进 §3 的 7 条编号列表——§3 intro 明确「下列 7 条…详见 issue
  #12」，加第 8 条会破坏该 attribution；而 §3.7 已是测试类规则的先例、但它归属 issue #12，故新条走 §4 更干净）。
- **内容提要**（bullet 文字，约 3~4 句）：
  > **测试 fixture 不要复用被测代码的同一套约定假设**（呼应 §3.4「注释写当前真相」——§3.4 管注释，这条管 fixture）。
  > 当测试输入由「与生产代码相同的约定」生成（坐标系、单位、字节序、编码…），测试只验证「代码自洽于该约定」、
  > **无法证伪「约定本身对不对」**——生产代码和 fixture 一起错时单测照样全绿，真机才炸。对这类「外部约定 / 物理映射」
  > 逻辑，fixture 应来自**独立来源**：真实采集数据、手算的地面真值、或不同推导路径的等价构造，使「假设错了」能被测出。

### A2 · #43 → 新增 §2.3「src 布局命名撞车（排障）」

- **落点**：§2 下新增 §2.3。§2.1 / §2.2 是「escape hatch」，§2.3 定位为「排障」小节，明确与 §2.2 已提的
  「多成员同名 `tests` 碰撞」并列成「src 布局命名撞车」两个已知坑（§2.3 里回指 §2.2 那条）。
- **内容提要**：症状 → 判据 → 解法三段。
  - 症状：顶层 `<pkg>/`（装 `pyproject.toml`/`package.xml`、无 `__init__.py`、非 Python 包）与 `src/<pkg>/` 真包同名；
    仓库根进 `sys.path` 时（pytest 塞 CWD / `cd` 仓根跑 python），`import <pkg>` 先命中顶层目录 → 当 PEP420 namespace
    包 → **顶包 import 成功但 `import <pkg>.<sub>` 报 `ModuleNotFoundError`**。误导点：像「子模块没装」。
  - 判据：`<pkg>.__file__` 为 `None` + `<pkg>.__path__` 同时含顶层目录与真包两 portion。
  - 场景/命运：测试期（pytest 仓根跑）触发；生产运行期（site-packages import、CWD 不在仓根）天然不触发。
  - 解法（代码块，`python` fence）：仓根 `conftest.py` 剔仓根出 `sys.path` + `--import-mode=prepend`：
    ```python
    import os, sys
    _ROOT = os.path.dirname(os.path.abspath(__file__))
    sys.path[:] = [p for p in sys.path if p and os.path.abspath(p) != _ROOT]
    ```
  - 注：与 §2.2 的 `--import-mode=importlib` 是**不同**撞车的**不同**解——那条治「同名 tests 包」，这条治「顶层目录遮蔽
    src 真包」；点明区别避免读者混用。

### A3 · #38 → 新增 §5.4「应用内更新自检的标准骨架」+ 扩充 §5.2

- **落点 1**：§5「打包·发布·安装」下新增 §5.4（§5 已有 5.1/5.2/5.3，自然续 5.4）。「应用运行时查更新 + 一键 `uv tool
upgrade`」是分发 / 安装期知识，归 §5 恰当。
- **§5.4 内容**：一句定位（凡 `uv tool install` 分发的应用都可能要，已两个项目独立重造）+ 5 点可抄清单：
  1. 查最新版本，按 registry 两分支：PyPI JSON 读 `info.version`；GitLab simple 返 PEP 503 HTML，正则从 wheel 文件名提版本。
  2. `packaging.version.Version` 比较 + 过滤 prerelease（`.is_prerelease`，否则 rc 被当最新）。
  3. `uv tool upgrade <pkg>` 拼装（`shutil.which("uv")`；私有 registry 带 `--extra-index-url` + `--allow-insecure-host`）。
  4. 后台线程 + TTL（stale-while-revalidate）+ 失败静默（不拖启动 / 不抛异常 / 网络失败返 `None`）。
  5. **不自动重启**：upgrade 覆盖 venv `.py` 不影响在跑进程；提示用户手动重启。
  - 两个版本源各给一小段解析片段（`python` fence）：PyPI JSON（`requests.get(.../pypi/<pkg>/json).json()["info"]["version"]`）
    与 GitLab simple（拉 HTML、正则 `<pkg>-(\d+\.\d+\.\d+...)-.*\.whl` 提所有版本、`max` by `Version` 且过滤 prerelease）。
- **落点 2**：§5.2 末尾补一小段「程序化查询最新版本」——GitLab simple 索引返 PEP 503 HTML（`Content-Type: text/html`，
  列全 wheel 文件名，正则提版本取最高 stable），与 §5.2 已有「`--check-url` 不兼容（GitLab simple 返 text/plain）」同层。
  与 §5.4 骨架第 1 点互指（§5.2 讲「GitLab 这一侧怎么查」，§5.4 讲「更新自检整套骨架」）。

---

## B. `rules/ros2.md`（2 条：#37 / #42）

### B1 · #37 → §2 包类型表加 `ament_cmake_python` 行 + 新增 §4.6「source-time environment hook」

- **落点 1**：§2「包类型」表新增一行：
  | Python 包（需 source-time hook / 其它 CMake 能力） | `ament_cmake` + `ament_cmake_python` | 纯 Python 节点，但要在 source 时跑逻辑 |
  并给现有 `ament_python` 行加一句边界注（「纯 Python 节点；**若需 source-time hook 见 §4.6**」）。
- **落点 2**：§4 下新增 §4.6「source-time environment hook（`ament_environment_hooks`）」：
  - 结论先行：想让「`source install/setup.bash` 时自动跑一段逻辑」（装依赖 / 设 env / 起辅助进程），唯一 ROS 官方机制是
    `ament_cmake` 的 `ament_environment_hooks(<name>.sh.in)`；**纯 `ament_python` 做不到**。
  - 为什么：colcon-ros 的 ament_python build task 生成包 `package.dsv` 时，source 哪些 hook 是**写死的**——只有
    `pythonpath` + `ament_prefix_path`，**不扫** `share/<pkg>/environment/`、不读 `resource_index/environment` marker、
    不调任何 hook 发现函数。那套 `environment/` + marker 是 `ament_cmake` 的 `ament_environment_hooks()` 宏专属。现象：
    纯 ament_python 版 `package.sh` 里根本没有 source hook 的行。
  - 正解骨架（`cmake` fence）：包改 `build_type=ament_cmake`，`ament_python_install_package` 装模块 +
    `install(PROGRAMS)` 装 entry（console_scripts 不被处理，需手写 entry）+ `ament_environment_hooks(hook.sh.in)`；
    附一句 pytest.ini 接替 setup.cfg 作 rootdir 锚。

### B2 · #42 → §5 追加子节「双链路：同一 Python 包既作 uv 成员又作 colcon 包」

- **落点**：`rules/ros2.md` §5「Python / pip 依赖」**末尾追加一个 `###` 子节**（标题不带编号，如
  `### 双链路：同一 Python 包既作 uv workspace 成员、又作 colcon 包`）。
  - **为什么不 renumber 成新 §6**：§5 之后是 §6/§7/§8/§9，插新 §6 要整体后移且改 §8 检查清单等标号，churn 大、易留悬空。
    §5 当前是扁平 bullet 段，追加一个 `###` 子节既满足 issue「§5 旁增一节」、又零 renumber。**（此点在「需拍板」列出）**
- **内容提要**：
  - 命题：ROS2 + Python 混合仓里，一个纯 Python 包既要走 uv/PyPI 链路、又要走 colcon/ament 原生 import 链路（PC 端 uv
    工具 + 端侧 ROS2 节点共享一份 protobuf / 契约 / 纯逻辑），与 §5「ament_python 装 pip 依赖」互补（一个装依赖、一个同包双消费）。
  - 原则：**双链路 = 两套构建元数据物理隔离，各读各的**。uv 侧不动（`pyproject.toml` 保留 `[build-system] uv_build`）；
    colcon 侧同目录新增 `package.xml`（`ament_cmake` + `ament_cmake_python`）+ `CMakeLists.txt`。
  - 骨架（`cmake` fence）：
    ```cmake
    cmake_minimum_required(VERSION 3.8)
    project(teleop_proto NONE)   # 纯 Python 无编译，NONE 跳过编译器探测
    find_package(ament_cmake REQUIRED)
    find_package(ament_cmake_python REQUIRED)
    ament_python_install_package(${PROJECT_NAME} PACKAGE_DIR src/${PROJECT_NAME})
    ament_package()
    ```
  - 隔离关键：colcon 只读 `package.xml`/`CMakeLists.txt`，uv 只读 `pyproject.toml`；选 `ament_cmake`（而非 `ament_python`）
    正是为避免 `setup.py` 布局与 `uv_build` 的 src 布局抢同一目录元数据。下游运行期 import 靠 `<exec_depend>` 声明。

---

## 变更文件清单

- `rules/python.md`：+§2.3、+§4 一 bullet、+§5.4、§5.2 补段。
- `rules/ros2.md`：§2 表 +1 行 & 注、+§4.6、§5 末 +1 `###` 子节。
- `docs/38-批量沉淀python-ros2规则/`：PROMPT.md（已）、PLAN.md（本）、后续 SUMMARY.md（`/finish` 出）。
- **不动**：任何 skill / 模板 / 代码 / GLOBAL_AGENTS.md。

## 执行顺序

1. 改 `rules/python.md`（A1→A2→A3）。2. 改 `rules/ros2.md`（B1→B2）。3. 通读两文件校对编号连续、fence 语言标注、
   与上下文风格一致。4. 交回人类 review diff。5. `/finish` 出 SUMMARY + `Closes #36 #38 #43 #37 #42`。

## 需拍板 / 默认取舍

1. **#42 落点形式**：默认「§5 末追加无编号 `###` 子节」（零 renumber）。若倾向「起正式 §6、把现 §6~§9 顺移到 §7~§10」，
   请指出——更「正规」但 churn 大。**默认取前者。**
2. **#38 / #42 的「可选模板样例包」**：PROMPT 已定**默认不做**（本轮只落规则文字，不碰 `ros2` stack 模板 / 不加更新自检
   样例）。若要连模板一起加，会扩到「改模板」范畴、建议单开轮。**默认不做。**
3. **#36 落点**：默认 §4 新 bullet（非 §3 第 8 条），理由见 A1。若坚持进 §3 编号列表，需同步改 §3 intro「7 条」表述。
   **默认 §4。**
4. **草稿粒度**：本 PLAN 给到「落点 + 提要 + 关键骨架」；最终 prose 在批准后直接写进 `rules/*.md`，措辞细节走 diff review。
