# Python 打包 · 发布 · 安装规则

> 本文档由 `claude-code-global` 仓库的 `playbooks/python-packaging.md` 提供，经 `install.sh` 双轨软链到 `~/.claude/playbooks/python-packaging.md`（CC 端）与 `~/.codex/playbooks/python-packaging.md`（Codex 端）。修改请回到 `claude-code-global` 仓库，不要直接编辑软链目标。
>
> **触发条件**：Coding Agent 在本轮任务涉及把 Python 库 / 应用做成 wheel、发布到 registry（PyPI / 自托管 GitLab）、或安装到目标机（`pip install --target` / `uv tool install`）时，**必须先把本文件读入上下文**，再开始动手。日常写 Python 代码只读 `playbooks/python.md` 即可。

`playbooks/python.md` §1「禁裸 pip / 用 uv」管的是**开发期**；下面几条管**打包、发布、安装期**——把库做成 wheel、推到 registry、再装到目标处时的固定坑，跨项目通用、配一次就能绕开。

## 1. 含前端（npm）产物的成员 wheel 化

monorepo 里「可独立发布、自带 npm 前端产物」的 Python 成员（典型：FastAPI daemon 静态托管 SPA），wheel 化时前端 `dist/` 在包外、默认不进 wheel，且包内按仓库布局解析的路径装机后失效。与 `playbooks/python.md` §2.1 hatchling 互补，是「按成员形态选打包路径」决策的第二格（第一格：纯 Python 成员 `uv build` 即得 `py3-none-any`）：

1. **构建后端切 hatchling**（`playbooks/python.md` §2.1 已覆盖「自定义 build / 非标布局」触发）。
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

## 2. uv + 自托管 GitLab Package Registry

把 uv 项目发布 / 安装到**自托管 GitLab** 时有两个固定坑（同实例的项目大概率复现）：

1. **TLS：内部 CA → `invalid peer certificate: UnknownIssuer`**。uv 默认走 rustls + 内置 Mozilla 根、**不读系统信任库**，故对内部 CA 签的证书报错（即使 git / glab over https 正常）。解法：`export UV_SYSTEM_CERTS=true`（旧版用已废弃的 `UV_NATIVE_TLS`），让 uv 用平台原生证书库；CA 在自定义路径时设 `SSL_CERT_FILE`。对 `uv publish` 与从该 registry `uv pip install` 都适用。
2. **`uv publish --check-url` 与 GitLab PyPI 不兼容**。GitLab 的 PyPI simple 索引返回 `Content-Type: text/plain`，uv 的 `--check-url` 只认 JSON / HTML → `Failed to query check URL`。故对 GitLab **不要**用 `--check-url` 做幂等跳过；重复版本由 GitLab 侧拒，重发须先删旧版或 bump version。

项目级上传 URL：`${CI_API_V4_URL}/projects/${CI_PROJECT_ID}/packages/pypi`，user `gitlab-ci-token` + 密码 `$CI_JOB_TOKEN`。

**补充 · 程序化查询该 registry 最新版本**：GitLab 项目级 PyPI **simple 索引**（`.../packages/pypi/simple/<pkg>/`）返回 PEP 503 锚点 HTML、**非 JSON**。查「有没有新版本」一律拉该页、正则从 wheel 文件名（`<pkg>-<version>-*.whl`）提版本、按 `packaging.version.Version` 取最高 stable（过滤 prerelease），别指望 JSON。整套骨架见 §4。

## 3. `pip install --target` 装本地开发 wheel：同版本号不覆盖

用 `pip install --target <dir> <本地 wheel>` 把自家纯 Python 库以受控方式装进某目录（避免污染系统）时：开发期 wheel 版本号常恒定（不会每改一次就 bump），而 `--target` 见到目标里已有同版本 → **跳过不覆盖**，装的还是旧 wheel；`--force-reinstall` 在 `--target` 模式下卸载不可靠（实测不更新文件，pip 已知行为）。后果：契约改动不生效、下游 `ModuleNotFoundError`，且 wheel 是新的、目标目录是旧的，极难排查。

**可靠解**：装前 `rm -rf <dir>/<pkg>*` 删旧目录再装。

> 同族问题的另一个形态见 §5——`uv tool install` 见同版本同样跳过不装，解是恒带 `--reinstall`。

## 4. 应用内更新自检的标准骨架

凡用 `uv tool install` 分发的应用（CLI / 带 UI 的 daemon）都可能要「运行时查新版本 + 一键升级」。骨架不变部分（差异点：版本源 / 凭证 / UI 框架按项目填）：

1. **查最新版本**（PyPI 走 JSON `info.version`；GitLab 走 simple 索引 HTML 提 wheel 文件名，见 §2）——下方代码。
2. **`Version` 比较 + 过滤 prerelease**（`is_prerelease`，否则 `rc`/`dev` 被误当最新）。
3. **拼 `uv tool upgrade <pkg>`**：`shutil.which("uv")` 定位 uv；私有 registry 追加 `--extra-index-url <含只读 token>` + `--allow-insecure-host <host>`（内部 CA，呼应 §2 TLS 坑）。
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

## 5. 把工具装进隔离目录（调试版与正式版并存）

场景：**把一个自家 CLI / daemon 装到某台机器上，但不能顶掉那台机器上已装好的正式版**——典型是联调 / 试装，想在采集 PC 上跑一版带调试改动的 daemon，而同事正用着 registry 发出来的正式版。`uv tool install` 默认把 entry point 写进 `~/.local/bin`、环境写进 `~/.local/share/uv/tools`，装上去就是**顶替**，没有并存一说。

配方（uv 0.11.29 实测跑通）：

```sh
export PATH="$HOME/.local/bin:$PATH"; cd <部署目录> && \
  UV_TOOL_DIR="$PWD/tools" UV_TOOL_BIN_DIR="$PWD/bin" \
  uv tool install --reinstall --find-links "$PWD/wheels" --default-index <index> <包名>
```

五个要点：

1. **`UV_TOOL_DIR` + `UV_TOOL_BIN_DIR` 成对设**，把 tool 环境与 entry point 整体搬进目标目录。只设前者不够——可执行文件仍会落进 `~/.local/bin` 把正式版顶掉。可用 `uv tool dir` / `uv tool dir --bin` 回显确认路径已被改写。
2. **先 `cd` 再用 `$PWD` 派生绝对路径**，而不是在本机拼 `$HOME`。落点用相对路径（相对目标机 `$HOME`）才能跨 user 自适应，而 uv 要绝对路径——`cd` 后取 `$PWD` 一步到位。
3. **`--reinstall` 恒带**。开发期版本号常长期不变（一直是 `0.3.0`），`uv tool install` 见同版本会**跳过不装**：命令全绿、日志漂亮、跑的还是旧代码，是联调里最阴的一种失败。这与 §3「`pip install --target` 同版本不覆盖」是**同一族问题的另一个解**，踩到其中一个时另一个大概率也在附近。
4. **uv 会 warn「bin 目录不在 PATH」——那正是预期行为**。这套装法的语义就是「只有跑那条绝对路径才是这一版」；别为了消 warning 把它加进 PATH（加了就等于又顶替了）。
5. **不需要动用 `uv pip install`**（`playbooks/python.md` §1 已禁用），全程仍在 `uv tool` 语义内。
