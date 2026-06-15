# Python 开发规则

> 本文档由 `claude-code-global` 仓库的 `rules/python.md` 提供，经 `install.sh` 双轨软链到 `~/.claude/rules/python.md`（CC 端）与 `~/.codex/rules/python.md`（Codex 端）。修改请回到 `claude-code-global` 仓库，不要直接编辑软链目标。
>
> **触发条件**：Coding Agent 在本轮任务涉及 Python 代码、`pyproject.toml`、依赖管理、Python 风格判断时，**必须先把本文件读入上下文**，再开始动手。

## 1. 环境与工具

- 使用 **uv** 管理项目依赖：用 `uv add <pkg>` 添加，依赖记录在 `pyproject.toml`（uv 天然支持）。**禁止使用 `pip install` 或 `uv pip install`**。
- 使用 **`uv run`** 运行 Python 脚本，如 `uv run some_script.py`、`uv run python -m ruff check .`。**禁止直接调用 `python` / `python3`**。
- **让 uv 全权管 python**：在 `pyproject.toml` 设 `[tool.uv] python-preference = "only-managed"`，强制 uv 只用自己托管的 standalone python、忽略系统 python。uv 默认 `python-preference=managed` 只在**已装**解释器间排序、会优先复用满足版本要求的系统 python；而系统 python 常缺 dev 头文件（无 `Python.h`），导致含 C 扩展的依赖（如 `evdev`）编译失败、且容易误判为编译器问题。托管 standalone python 永远自带头文件，配合默认 `python-downloads=automatic`，缺托管版时会自动下载。python-uv 模板已默认带此设置，手工建项目请照抄；机器级一劳永逸可在 `~/.config/uv/uv.toml` 设同名键（`claude-code-global` 的 `install.sh` 在该文件缺失时会自动 seed）。
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

## 3. 开发风格

下列 7 条来自跨项目实战沉淀（详见 issue #12），是 Python 代码层面的硬性偏好。

### 3.1 偏好面向对象，避免"满文件的 free functions"

**rule**：当一个文件里聚集了多个相互关联的 free function，强烈倾向把它们抽成一个类的方法（实例方法 / `@staticmethod` / `@classmethod`）。

**为什么**：一堆松散函数之间一定有隐含关系（共享 profile、共享 schema 概念、共享 ROS 消息形状）；既然有关系，让它们作为同一个类的方法能把这层关系**显化**。新人读 `Schema.parse_pose` 比读 `schema.parse_pose` 更能把握"这是 schema 概念下配套的 parser"。

**适用边界**：纯无状态算法（如 `bisect`）当然可以 free function。但发现"这堆函数都围绕同一对象 / 同一概念在转" —— 就该抽类。

### 3.2 包内绝对 import

**rule**：包内文件互相 import 用绝对路径（`from mypackage.X import Y`），而不是相对路径（`from .X import Y`）。

**为什么**：

- PEP 8 默认推荐；
- 大型项目（numpy / pandas / Django / SQLAlchemy / Requests / FastAPI）一致用绝对；
- 读：路径完整，一眼看出"来自哪个包"；
- 写：错误消息带完整路径，定位快；
- 重构：grep / sed 全局一致字符串。

**反驳"相对让改包名更简单"**：现实里频繁改的是**文件名**而非**包名**，相对 import 在我们的工作流里不省事。

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

**真实事故案例**：曾经一次 session 中 formatter 误判删了 `from mcap2lerobot.mcap_bag import McapBag`，但 `pytest tests/ -q` 全 86 项过。原因：`tests/test_converter.py` 只测 `_effective_profile` / `align_frames` 两个模块级 free function，**没有任何测试**真正 `Converter(...).run()`。missing import 直到真实 CLI 跑数据才会暴露。

**rule**：每个**编排器 / facade-level 类**至少有 **1 条 happy-path integration test**：

- 最小 fixture（tiny profile + 几帧假数据 + 内存假相机 / 假数据库 / 假 HTTP）；
- 端到端跑一遍主入口方法（`.run()` / `.execute()` / `.process()`）；
- 不必断言细节正确，**只要"跑通不报错"就行** —— 抓的不是"算式算错"，而是 missing import / 参数顺序对换 / `self.X` 没初始化 等**装配错误**。

**判断"是否是编排器"的启发**：类的 `__init__` 接受外部资源（文件路径、URL、profile…）+ 有一个主入口方法（`run` / `execute` / `process`）+ 调用 3+ 个其他模块 —— 基本就是编排器。

## 4. 测试

呼应全局宪法的 TDD 章节，落到 Python 的具体姿势：

- **TDD 适用范围**：业务逻辑 / 纯函数 / 算法 / 有清晰输入输出契约的接口或模块。这类场景测试用例就是需求的具体表达，先写测试能强迫想清楚边界。
- **例外**：探索性原型、UI / 视觉效果、与外部系统的集成（数据库 schema、第三方 API 对接）可以先跑通再补测试。**但实现稳定后必须补齐单测，不允许长期裸奔**。
- **编排器 / facade 必有 ≥ 1 条 integration test**（见 §3.7），即使其他业务规则都按 TDD 走过，编排层也不能省略 happy-path smoke。
- **测试目录结构**：`tests/` 与 `src/` 同级（不嵌进 `src/<pkg>/`），由 `pyproject.toml [tool.pytest.ini_options] pythonpath = ["src"]` 解决 import；测试文件命名 `test_<被测对象>.py`。
- **运行**：`uv run pytest`（带覆盖率：`uv run pytest --cov=src/<pkg>`）。
