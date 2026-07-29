# Python 开发规则

> 本文档由 `claude-code-global` 仓库的 `rules/python.md` 提供，经 `install.sh` 双轨软链到 `~/.claude/rules/python.md`（CC 端）与 `~/.codex/rules/python.md`（Codex 端）。修改请回到 `claude-code-global` 仓库，不要直接编辑软链目标。
>
> **触发条件**：Coding Agent 在本轮任务涉及 Python 代码、`pyproject.toml`、依赖管理、Python 风格判断时，**必须先把本文件读入上下文**，再开始动手。

## 1. 环境与工具

- 使用 **uv** 管理项目依赖：用 `uv add <pkg>` 添加，依赖记录在 `pyproject.toml`（uv 天然支持）。**禁止使用 `pip install` 或 `uv pip install`**。
- 使用 **`uv run`** 运行 Python 脚本，如 `uv run some_script.py`、`uv run python -m ruff check .`。**禁止直接调用 `python` / `python3`**。
- **让 uv 全权管 python**：`pyproject.toml` 设 `[tool.uv] python-preference = "only-managed"`，强制 uv 只用托管 standalone python、忽略系统 python。默认 `managed` 会复用系统 python，而系统 python 常缺 dev 头文件（无 `Python.h`）→ 含 C 扩展的依赖（如 `evdev`）编译失败、且易误判为编译器问题；托管 standalone python 永远自带头文件、缺版自动下载。python-uv 模板已默认带此设置；机器级一劳永逸可在 `~/.config/uv/uv.toml` 设同名键（`install.sh` 缺失时会 seed）。
- 使用 **ruff** 做代码格式化与语法检查（`uv run ruff check` / `uv run ruff format`）。
- **pypi index 指南**（为提高国内下载速度，固定两个源）：
  - 普通库走[清华源](https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple)
  - `torch` / `torchaudio` / `torchvision` 等 torch 系列走 [aliyun pytorch-wheels 镜像](https://mirrors.aliyun.com/pytorch-wheels/cu121/)。这并非完整 pypi 源，必须在 `pyproject.toml` 用 `extra` 方式指定。
- 如无特殊要求，`torch` 默认 `2.5.1` 版本，CUDA 编译版 `cu121`。

## 2. 项目骨架（src 布局）

新建 Python 包必须使用标准 **src 布局**，避免把包目录平铺在仓库根：

- 包目录落在 `src/<pkg>/`，**不要**直接放在仓库根。
- 顶层 `configs/` / `tests/` 与 `src/` **平级**。
- `pyproject.toml` 关键字段：
  - `[build-system]` 默认用 uv 自家 `uv_build`（`uv init --package` 的默认产物，零配置，src 布局自动识别）。
  - `[tool.pytest.ini_options]` 配 `pythonpath = ["src"]` 和 `testpaths = ["tests"]`，让 `pytest` 在 src 布局下能干净 import。
- `uv sync` 即把本包按可编辑模式装好；`uv run python -m <pkg>` / `uv run pytest` 都能干净 import。
- bootstrap / sync-project-config skill 已自动落该布局；**手工新建包请遵循同样结构**。

### 2.1 escape hatch：何时切换为 hatchling

`uv_build` 只支持纯 Python。如果项目落入以下任一情形，把 build backend 切换为 **hatchling**：

- 含 C / C++ / Rust 扩展模块；
- 需要自定义 build 脚本 / build hooks；
- 项目布局不符合 uv_build 的约定（多 wheel、动态 packages、非标 src 等）。

切换方法：修改 `pyproject.toml`：

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/<pkg>"]
```

其余 src 布局约定不变。

### 2.2 escape hatch：多包 uv workspace（单仓多包）

§2 的单包 src 布局覆盖「一个仓库 = 一个包」。当一个仓库要装**多个可独立发布、又互相依赖**的包（典型：`proto` + 多个 service 共用一份 lockfile）时，切换为 **uv workspace 多包单仓**。配套脚手架是 `python-uv-workspace` stack（与单包 `python-uv` **互斥**，`bootstrap` / `sync-project-config` 二选一），落点仍是仓库根。模板需固化的要素：

- **虚拟根**：根 `pyproject.toml` **无 `[project]`**，仅 `[tool.uv.workspace] members = ["packages/*"]`。**绝不对虚拟根跑 `uv init --package`**（会写出 `[project]` + `src/` 破坏 workspace 形态）。
- **共享配置上提到根**：`[tool.uv]`（`python-preference="only-managed"`）/ 清华 index / `[tool.ruff]` / `[tool.pytest.ini_options]` 都在根，各成员不重复。dev 依赖 `uv add --dev pytest pytest-cov ruff` 在根写入 `[dependency-groups] dev`、并触发把各成员 editable 装入。
- **各成员独立 `pyproject.toml`** 落 `packages/<member>/`（标准 src 布局 + `[build-system] uv_build`）。跨成员依赖：成员 `dependencies = ["<dep>"]` + `[tool.uv.sources] <dep> = { workspace = true }`，解析到本仓源码而非去 index 拉。
- **测试**：仓根一条 `uv run pytest` 跑全树，根 `[tool.pytest.ini_options]` 必带 `addopts = ["--import-mode=importlib"]`，否则多个成员同名 `tests` 包碰撞（`No module named 'tests.test_xxx'`）；配套各成员 `tests/` **不放 `__init__.py`**。`pythonpath` / `testpaths` 列全各成员的 `src` / `tests`，新增成员时追加。
- **生成码**（如 protobuf `_pb`）入库时 `ruff` `extend-exclude` 豁免。
- **VSCode**：`.vscode/settings.json` 带 `python.analysis.extraPaths` 指向各成员 `src`（Pylance 静态解析跨成员 import 不稳，extraPaths 显式喂才认 `from <other_member> import ...`）+ `python.defaultInterpreterPath` 钉死 workspace 根 `.venv`。

> 与 §2.1 hatchling 是正交的两个 escape hatch：2.1 换 **build backend**（含 C 扩展 / 自定义 build），2.2 换 **仓库布局**（单包 → 多包 workspace），可叠加（workspace 里某个含 C 扩展的成员自己切 hatchling）。

### 2.3 src 布局命名撞车（排障）：顶层同名目录遮蔽 src 真包

src 布局下，顶层 `<pkg>/`（装 `pyproject.toml` / `package.xml`、**无 `__init__.py`**、本身不是 Python 包）常与 `src/<pkg>/` 里的真包**同名**（uv workspace 多包、colcon + Python 混合仓最易撞）。当仓库根被塞进 `sys.path` 时（`python -m pytest` 会把 CWD 塞进去、或 `cd` 到仓根直接跑 `python`），`import <pkg>` 会**先命中顶层目录**：

- 顶层目录无 `__init__.py` → Python 当它是 **PEP 420 namespace package**，`import <pkg>` **成功**（看起来没事）；
- 但 `import <pkg>.<submodule>` **失败** `ModuleNotFoundError` —— namespace 机制不再往下解析到 `src/` 的真包。

**误导点**：顶包 import 成功、只子模块挂，报错像"子模块没装"，完全不会让人联想到"顶层同名目录遮蔽了 src 真包"。**判据**：`<pkg>.__file__` 为 `None`（真包会是具体路径）+ `<pkg>.__path__` 同时含顶层项目目录与 install/editable 真包**两个 portion**。

**两场景两命运**：测试期（pytest 在仓根跑）触发；生产运行期（site-packages import、CWD 不在仓根）**天然不触发**——是开发 / 测试期问题、非部署问题。

**解法**：仓根 `conftest.py` 把仓根从 `sys.path` 剔除，配合 `--import-mode=prepend`：

```python
import os, sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path[:] = [p for p in sys.path if p and os.path.abspath(p) != _ROOT]
```

与 §2.2「多成员同名 `tests` 包碰撞」是「src 布局命名撞车」的两个**不同**坑、**不同**解：那条靠 `--import-mode=importlib` + `tests/` 不放 `__init__.py`，这条靠剔仓根出 `sys.path`；别混用。

## 3. 开发风格

下列 7 条来自跨项目实战沉淀（详见 issue #12），是 Python 代码层面的硬性偏好。

### 3.1 偏好面向对象，避免"满文件的 free functions"

**rule**：当一个文件里聚集了多个相互关联的 free function，强烈倾向把它们抽成一个类的方法（实例方法 / `@staticmethod` / `@classmethod`）。

**为什么**：一堆松散函数之间一定有隐含关系（共享 profile、共享 schema 概念、共享 ROS 消息形状）；既然有关系，让它们作为同一个类的方法能把这层关系**显化**。新人读 `Schema.parse_pose` 比读 `schema.parse_pose` 更能把握"这是 schema 概念下配套的 parser"。

**适用边界**：纯无状态算法（如 `bisect`）当然可以 free function。但发现"这堆函数都围绕同一对象 / 同一概念在转" —— 就该抽类。

### 3.2 包内绝对 import

**rule**：包内文件互相 import 用绝对路径（`from mypackage.X import Y`），而不是相对路径（`from .X import Y`）。

**为什么**：PEP 8 默认推荐、大型项目（numpy / pandas / Django / FastAPI）一致；路径完整一眼看出来源、错误消息带完整路径好定位、重构时 grep/sed 是一致字符串。反驳「相对让改包名更简单」：现实里频繁改的是**文件名**而非包名，相对 import 不省事。

**硬规则**：单个文件内绝不混用两种风格 —— 一致性比选哪种更重要。

**适用边界**：包深度 ≥ 3 层 + 频繁 vendor / 包重命名场景下相对可接受，但单层结构默认绝对。

### 3.3 文件名 = 核心类名的 snake_case

**rule**：当一个文件的"核心"是一个类，文件就以这个类命名（PascalCase ↔ snake_case 一对一映射）：

- `class McapBag` → `mcap_bag.py`
- `class LerobotWriter` → `lerobot_writer.py`
- `class TickGrid` → `tick_grid.py`

**为什么**：文件名直接揭示"这个文件的核心责任"，新人扫文件树即能猜到内容。

**边界条款**：

- 一个文件多个紧密协作的类（如 `CameraStream` + `StreamingFramePicker`，后者由前者 `open_picker()` 产生）：文件名取**主导类**名或概念名。
- "父包名已含 context、文件名可省冗余前缀" 这条**例外**要慎用 —— 除非 stutter 严重（如 `LeRobotWriter` 这种品牌名 stutter），否则维持机械一致更省心。

### 3.4 注释 / docstring 写"当前真相"，不写"演化历史"

**rule**：

- ❌ 禁用：注释里引用 `round-XX` / `PLAN.md §X` / `issue #N` / "旧脚本" / "spike-N" / "codex review" 等开发历史标记。
- ❌ 禁用：硬编码 dataset-specific 维数（如"81 维 state"、"32 关节"、"36 维 action"）—— 改用动态引用（`sch.action_labels`）。
- ✅ 偏好：注释回答 **"WHY"**（非显然的设计动机 / 隐藏约束 / workaround 原因）。
- ❌ 不写：注释回答 "WHAT"（代码自身已说清楚）。

**为什么**：开发历史会过时（哪一轮做的、哪个 issue 来的对未来读者无关），引用 PLAN / round 会让代码读起来像"考古遗址"。dataset 维数会变（换 profile 就失效）。注释的责任是**让未来读者理解"为什么这么写"**，而代码本身负责说清楚"做了什么"。

**仅有的合理例外**：注释里出现历史标记可以是"为什么这么写"的一部分（如"workaround for upstream issue #N"），但即使如此也建议用通用语言（"避免上游 X 行为"），不要直接绑定 issue 号。

### 3.5 Protocol 鸭子型契约 > Any，用于外部不可靠类型

**适用场景**：外部库返回的"鸭子型"对象 —— 典型如 ROS 消息（mcap_ros2 解码出的 `mcap_ros2._dynamic.JointState` 不是真正的 `sensor_msgs.msg.JointState`）、JSON dict、自定义 mock。

**rule 三段**：

1. **不要为类型标注引入重型外部依赖**（如 ROS Python 包）—— pip 装不干净 + 装上后 isinstance 也不通过；
2. **不要相信"导入真类做标注"** —— 动态类与真类的 isinstance 会失败，标注是骗局；
3. **自定义 `Protocol` 鸭子型** —— 把"期望形状"固化成结构化契约，mcap_ros2 动态类、SimpleNamespace mock、真 ROS 类全都自动通过结构匹配。

**配套硬规则**：声明了 Protocol 就**别再写防御性 `getattr`** —— "信不过自己的契约"是反 pattern。让 Protocol 是真理之源；缺字段就让代码自然炸出 `AttributeError`，而不是默默兜底。

**例外**：用 `getattr(obj, name, default)` 做**反射查找**（`name` 来自运行时字符串）依然合法，那是 Python 唯一的"按字符串取属性"机制，不是防御性。

### 3.6 dict-of-dicts 是 OO 重构的强信号

**rule**：见到这种 pattern ——

```python
state[key] = {
    "fp": ...,
    "path": ...,
    "ts": [],
    "ext": None,
    "fps_hist": {},
}
# 后续：state[key]["fp"].write(...), state[key]["ts"].append(...)
```

强烈考虑封装成对象：

```python
class XxxStream:
    def __init__(self, ...): self.fp, self.path, self.ts, self.ext = ...
    def append_packet(self, data, ts, encoding, fps): ...
```

**为什么**：

- 重构后状态有了**明确 owner**（不再是字典 + 字符串 key）；
- 字段名错误能被**静态检查**（typo `state[key]["fp"]` 写成 `["pf"]` 不会爆，类属性会）；
- 可加 **context manager**（`__enter__` / `__exit__`）安全管理资源；
- 字段意义有 docstring 可写。

**特别看**：dict 里既有 mutable container（list / dict）又有句柄（文件 / socket）—— 100% 该重构。

### 3.7 整合类必须 ≥ 1 条 happy-path integration test

**现象**：项目里常常出现这种覆盖结构 ——

- 模块级 helper / 纯函数 / 算法类：测得很全（容易测、好覆盖）；
- 编排器 / facade-level 类（拼装多个组件做端到端流程的）：**0 单测**或仅 smoke test。

**真实事故案例**：formatter 误判删了 `from mcap2lerobot.mcap_bag import McapBag`，但 `pytest -q` 全 86 项过——因为测试只覆盖模块级 free function，**没有任何测试**真正跑 `Converter(...).run()`，missing import 直到真实 CLI 跑数据才暴露。

**rule**：每个**编排器 / facade-level 类**至少有 **1 条 happy-path integration test**：

- 最小 fixture（tiny profile + 几帧假数据 + 内存假相机 / 假数据库 / 假 HTTP）；
- 端到端跑一遍主入口方法（`.run()` / `.execute()` / `.process()`）；
- 不必断言细节正确，**只要"跑通不报错"就行** —— 抓的不是"算式算错"，而是 missing import / 参数顺序对换 / `self.X` 没初始化 等**装配错误**。

**判断"是否是编排器"的启发**：类的 `__init__` 接受外部资源（文件路径、URL、profile…）+ 有一个主入口方法（`run` / `execute` / `process`）+ 调用 3+ 个其他模块 —— 基本就是编排器。

### 3.8 用 rich 打印外部文本：一律 `escape()` + `highlight=False`

凡把**外部程序的输出、用户输入、透传参数**喂给 `rich` 打印，都要当作不可信文本处理：

```python
from rich.markup import escape

console.print(escape(text), highlight=False)
```

两个坑各对应一个开关，缺一不可：

- **`escape()` 防 `MarkupError` 与标记注入**：rich 把 `[...]` 当标记语法解析，外部文本里只要出现 `[/x]` 这种形状的子串就直接抛 `rich.errors.MarkupError`，把整个报告打崩。
- **`highlight=False` 防自动高亮器污染逐字输出**：转发别的程序的逐字输出（如 `xxx -h` 的帮助文本）时，rich 的 `ReprHighlighter` 会往 `[OPTIONS]` 的方括号与内容之间插 ANSI，「逐字转发」就不再逐字了。

只有**自己写的、可信的** markup 才享受解析与高亮。

## 4. 测试

呼应全局宪法的 TDD 章节，落到 Python 的具体姿势：

- **TDD 适用范围**：业务逻辑 / 纯函数 / 算法 / 有清晰输入输出契约的接口或模块。这类场景测试用例就是需求的具体表达，先写测试能强迫想清楚边界。
- **例外**：探索性原型、UI / 视觉效果、与外部系统的集成（数据库 schema、第三方 API 对接）可以先跑通再补测试。**但实现稳定后必须补齐单测，不允许长期裸奔**。
- **编排器 / facade 必有 ≥ 1 条 integration test**（见 §3.7），即使其他业务规则都按 TDD 走过，编排层也不能省略 happy-path smoke。
- **测试 fixture 不要复用被测代码的同一套约定假设**（呼应 §3.4「注释写当前真相」——§3.4 管注释，这条管 fixture）：当测试输入由「与生产代码相同的约定」生成（坐标系、单位、字节序、编码…），测试只验证「代码自洽于该约定」、**无法证伪「约定本身对不对」**——生产代码与 fixture 一起错时单测照样全绿、真机才炸。对这类「外部约定 / 物理映射」逻辑，fixture 应来自**独立来源**：真实采集数据、手算的地面真值、或不同推导路径的等价构造，让「假设错了」也能被测出。
- **「声明式 schema + 自然语言 prompt」双写处必须加结构性防漂移测试**（上一条在 LLM 场景下的具体化）：凡代码里存在一份「能力 / 工具清单」的数据结构，同时又有一段散文在向模型描述这份清单（最典型是 LLM function calling 的 `TOOLS_SCHEMA` + `_SYSTEM_PROMPT`），两处**必然漂移**——schema 是数据、prompt 是散文，没有任何机械约束把它们绑在一起，改 schema 的 diff 里也看不到 prompt。而用 `FakeLlm` 直接返回决策的单测**跳过了 prompt 这一环**，两边一起错也照样全绿，只有真机才炸（漏改 prompt 的后果是：模型被系统提示引导为「不能选这个新工具」，该能力在生产上直接失效）。把「两处必须一致」变成机械约束：

  ```python
  def test_system_prompt_mentions_every_tool_in_schema() -> None:
      missing = [
          t["function"]["name"]
          for t in TOOLS_SCHEMA
          if t["function"]["name"] not in llm_client._SYSTEM_PROMPT
      ]
      assert missing == [], f"这些 tool 没写进 system prompt：{missing}"


  def test_system_prompt_tool_count_matches_schema() -> None:
      """prompt 里写死的「N 个工具」必须与 TOOLS_SCHEMA 实际长度一致。"""
      assert f"{len(TOOLS_SCHEMA)} 个工具" in llm_client._SYSTEM_PROMPT
  ```

  第二条尤其要紧：**prompt 里但凡写死了数量（「下面 8 个工具」），就等于埋了一个必然过期的常量**——要么别写数量，要么用测试钉死它。

- **测试涉及环境变量时必须在 fixture 里显式清场，别依赖「我这儿没设」**（与上面两条同族：测试环境不独立于被测对象的假设）：`CliRunner(env=...)` 与 `subprocess(env=...)` 的语义都是在**父进程环境之上追加 / 覆盖**，不是替换成一个干净环境。于是测试里「不设置某变量」= 什么都不做，开发者本地 `export` 过的值原样漏进被测代码，让「未设置该变量时应报错」这类用例**假绿**。最坏的是它的暴露时机——**写测试的人本地必然设过该变量**（否则没法联调），所以作者永远看不到它变红，等别人机器上或 CI 里改动这条逻辑时才发现测试根本没在守护它。

  ```python
  @pytest.fixture(autouse=True)
  def _clean_env(monkeypatch):
      monkeypatch.delenv("MY_APP_APIKEY", raising=False)   # 显式清场


  def run(*args, key=None):
      # 要表达「没有」时喂空串，而不是「不传」
      env = {"COLUMNS": "200", "MY_APP_APIKEY": key or ""}
      return runner.invoke(app, [*args], env=env)
  ```

  这类测试值得**在带变量、不带变量两种环境下各跑一遍全量**，两次都绿才算数。

- **测试目录结构**：`tests/` 与 `src/` 同级（不嵌进 `src/<pkg>/`），由 `pyproject.toml [tool.pytest.ini_options] pythonpath = ["src"]` 解决 import；测试文件命名 `test_<被测对象>.py`。
- **运行**：`uv run pytest`（带覆盖率：`uv run pytest --cov=src/<pkg>`）。

## 5. 打包 · 发布 · 安装

§1「禁裸 pip / 用 uv」管的是**开发期**；下面几条管**打包、发布、安装期**——把库做成 wheel、推到 registry、再装到目标处时的固定坑，跨项目通用、配一次就能绕开。

### 5.1 含前端（npm）产物的成员 wheel 化

monorepo 里「可独立发布、自带 npm 前端产物」的 Python 成员（典型：FastAPI daemon 静态托管 SPA），wheel 化时前端 `dist/` 在包外、默认不进 wheel，且包内按仓库布局解析的路径装机后失效。与 §2.1 hatchling 互补，是「按成员形态选打包路径」决策的第二格（第一格：纯 Python 成员 `uv build` 即得 `py3-none-any`）：

1. **构建后端切 hatchling**（§2.1 已覆盖「自定义 build / 非标布局」触发）。
2. **用 `artifacts` glob bundle 前端产物，而非 `force-include`**：

   ```toml
   [tool.hatch.build.targets.wheel]
   packages = ["src/<pkg>"]
   artifacts = ["src/<pkg>/_frontend/**"]
   ```

   关键差异——`force-include` 在源路径缺失时**报错**，会让 editable `uv sync`（前端常未构建）整个失败；`artifacts` glob 存在即纳入（含 VCS-ignored），不存在不报错，editable 安装照常。

3. **包内路径「优先 bundled、回落 dev 源路径」**：`_BUNDLED = Path(__file__).parent / "_frontend"`；`_FRONTEND = _BUNDLED if _BUNDLED.is_dir() else <dev 源路径>`。使 wheel 装的进程与源码/dev 跑都能定位前端。
4. **构建顺序 + `--wheel`**：build 脚本先 `npm run build` → 拷 dist 进包 `_frontend/` → `uv build --wheel`。用 `--wheel` 直接从源构建，避开 `uv build` 默认 sdist→wheel 二段构建时 artifacts 漏进 sdist 的坑。
5. 产物仍是 `py3-none-any`（前端是静态数据，跨架构无忧）；二进制 Python 依赖装机时由 index 拉对应平台 wheel。

> 与「含 C 扩展 / 复杂 build → 退回目标机原生 build」一条互补，三者合成「按成员形态选打包路径」决策。

### 5.2 uv + 自托管 GitLab Package Registry

把 uv 项目发布 / 安装到**自托管 GitLab** 时有两个固定坑（同实例的项目大概率复现）：

1. **TLS：内部 CA → `invalid peer certificate: UnknownIssuer`**。uv 默认走 rustls + 内置 Mozilla 根、**不读系统信任库**，故对内部 CA 签的证书报错（即使 git / glab over https 正常）。解法：`export UV_SYSTEM_CERTS=true`（旧版用已废弃的 `UV_NATIVE_TLS`），让 uv 用平台原生证书库；CA 在自定义路径时设 `SSL_CERT_FILE`。对 `uv publish` 与从该 registry `uv pip install` 都适用。
2. **`uv publish --check-url` 与 GitLab PyPI 不兼容**。GitLab 的 PyPI simple 索引返回 `Content-Type: text/plain`，uv 的 `--check-url` 只认 JSON / HTML → `Failed to query check URL`。故对 GitLab **不要**用 `--check-url` 做幂等跳过；重复版本由 GitLab 侧拒，重发须先删旧版或 bump version。

项目级上传 URL：`${CI_API_V4_URL}/projects/${CI_PROJECT_ID}/packages/pypi`，user `gitlab-ci-token` + 密码 `$CI_JOB_TOKEN`。

**补充 · 程序化查询该 registry 最新版本**：GitLab 项目级 PyPI **simple 索引**（`.../packages/pypi/simple/<pkg>/`）返回 PEP 503 锚点 HTML、**非 JSON**。查「有没有新版本」一律拉该页、正则从 wheel 文件名（`<pkg>-<version>-*.whl`）提版本、按 `packaging.version.Version` 取最高 stable（过滤 prerelease），别指望 JSON。整套骨架见 §5.4。

### 5.3 `pip install --target` 装本地开发 wheel：同版本号不覆盖

用 `pip install --target <dir> <本地 wheel>` 把自家纯 Python 库以受控方式装进某目录（避免污染系统）时：开发期 wheel 版本号常恒定（不会每改一次就 bump），而 `--target` 见到目标里已有同版本 → **跳过不覆盖**，装的还是旧 wheel；`--force-reinstall` 在 `--target` 模式下卸载不可靠（实测不更新文件，pip 已知行为）。后果：契约改动不生效、下游 `ModuleNotFoundError`，且 wheel 是新的、目标目录是旧的，极难排查。

**可靠解**：装前 `rm -rf <dir>/<pkg>*` 删旧目录再装。

### 5.4 应用内更新自检的标准骨架

凡用 `uv tool install` 分发的应用（CLI / 带 UI 的 daemon）都可能要「运行时查新版本 + 一键升级」。骨架不变部分（差异点：版本源 / 凭证 / UI 框架按项目填）：

1. **查最新版本**（PyPI 走 JSON `info.version`；GitLab 走 simple 索引 HTML 提 wheel 文件名，见 §5.2）——下方代码。
2. **`Version` 比较 + 过滤 prerelease**（`is_prerelease`，否则 `rc`/`dev` 被误当最新）。
3. **拼 `uv tool upgrade <pkg>`**：`shutil.which("uv")` 定位 uv；私有 registry 追加 `--extra-index-url <含只读 token>` + `--allow-insecure-host <host>`（内部 CA，呼应 §5.2 TLS 坑）。
4. **后台线程 + TTL + 失败静默**：查询放后台、TTL 缓存不拖慢启动；网络 / 解析失败返 `None`、不抛异常、不打断主流程。
5. **不自动重启**：`uv tool upgrade` 覆盖 venv 的 `.py` 但不影响已在跑的进程；只提示用户手动重启，别自作主张。

两个版本源的最小解析片段：

```python
import re

import requests
from packaging.version import Version


def latest_pypi(pkg: str) -> str | None:
    """公共 PyPI：JSON API，直接读 info.version。"""
    info = requests.get(f"https://pypi.org/pypi/{pkg}/json", timeout=5).json()["info"]
    return info["version"]


def latest_gitlab(simple_url: str, pkg: str) -> str | None:
    """自托管 GitLab simple 索引：PEP 503 HTML，从 wheel 文件名提最高 stable。"""
    html = requests.get(simple_url, timeout=5, verify=False).text  # verify=False 跳内部 CA
    vers = re.findall(rf"{re.escape(pkg)}-(.+?)-py3-none-any\.whl", html)
    stable = [v for v in vers if not Version(v).is_prerelease]
    return max(stable, key=Version) if stable else None
```

有无更新 = `Version(latest) > Version(current)`；升级交给用户点击执行、执行完提示重启。
