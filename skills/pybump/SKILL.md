---
name: pybump
description: 升级 Python 项目版本号，更新 pyproject.toml，提交代码并打 tag
disable-model-invocation: true
---

用户调用此 skill 表示要发布 Python 项目的新版本。

## 参数说明

调用时可附带参数（args），支持以下几种形式：

| 参数 | 含义 | 示例 |
|---|---|---|
| （无） | patch +1 | `1.2.3` → `1.2.4` |
| `X.Y.Z` 等显式版本号 | 直接作为新版本号 | `/pybump 2.0.0` |
| `alpha` / `beta` [+ 修饰符] | 生成预发布版本 | 见下文 |
| `fix` | 生成 post-release 修正版 | `1.2.3` → `1.2.3.post1` |

### alpha / beta 详细规则

PEP 440 中 `X.Y.ZaN` / `X.Y.ZbN` 表示"某个正式版 X.Y.Z 的预发布"，排序上 `X.Y.ZaN < X.Y.ZbN < X.Y.Z`。因此生成预发布时，要先确定"目标正式版"。

**当前是正式版**（如 `0.5.2`）时，根据修饰符确定目标：

| 参数 | 目标正式版 | 新版本 |
|---|---|---|
| `alpha` 或 `alpha patch` | 下一个 patch | `0.5.2` → `0.5.3a1` |
| `alpha minor` | 下一个 minor | `0.5.2` → `0.6.0a1` |
| `alpha major` | 下一个 major | `0.5.2` → `1.0.0a1` |
| `alpha 0.6.0` | 显式目标版本 | `0.5.2` → `0.6.0a1` |
| `beta ...` | 同上，换成 `bN` | `0.5.2` → `0.5.3b1` 等 |

**当前已是预发布**（如 `0.6.0a2`）时，不接受 `patch` / `minor` / `major` / 显式目标，只做序号或级别变更：

| 当前 | 参数 | 新版本 |
|---|---|---|
| `0.6.0a2` | `alpha` | `0.6.0a3` |
| `0.6.0a2` | `beta` | `0.6.0b1` |
| `0.6.0b1` | `beta` | `0.6.0b2` |
| `0.6.0b1` | `alpha` | ❌ 报错（不允许从 beta 降级回 alpha） |

如需切换目标正式版，请改用显式版本号，例如 `/pybump 1.0.0a1`。

### fix 详细规则

`.postN` 用于已发布版本的小修正（如文档、打包问题），不含功能变更，排序上 `X.Y.Z < X.Y.Z.post1 < X.Y.Z.post2 < X.Y.(Z+1)`。

| 当前 | 参数 | 新版本 |
|---|---|---|
| `1.2.3` | `fix` | `1.2.3.post1` |
| `1.2.3.post1` | `fix` | `1.2.3.post2` |
| `1.2.3a1` | `fix` | ❌ 报错（预发布版不应使用 post） |

---

执行以下步骤：

## 1. 读取当前版本号

读取项目根目录下 `pyproject.toml` 的 `version` 字段，解析出当前版本号。

## 2. 按参数规则确定新版本号

按"参数说明"一节的规则推导新版本号。建议用 `uv run python` + `packaging.version.Version` 来解析和比较，避免自己写正则：

```python
from packaging.version import Version
v = Version("0.6.0a2")
v.is_prerelease        # True
v.pre                  # ('a', 2)
v.is_postrelease       # False
v.release              # (0, 6, 0)
```

如果项目没安装 `packaging`，临时在 skill 执行期用 `uv run --with packaging python ...` 即可，不要污染 `pyproject.toml`。

## 3. 校验版本号

新版本号必须满足以下条件，**任一不满足则中止并告知用户**：

1. **符合 PEP 440**（`Version("...")` 能成功解析）
2. **严格大于当前版本号**（用 `Version` 比较，自动遵循 PEP 440 排序规则）

## 4. 更新版本号

使用 Edit 工具将 `pyproject.toml` 中的 `version = "旧版本号"` 替换为 `version = "新版本号"`。

## 5. 同步依赖

运行 `uv sync` 确保锁文件和环境与新版本号一致。

## 6. 提交、打 tag、推送

1. 使用 `/commit` skill 提交所有变更（commit message 应体现版本升级，如 `release: 升级版本至 X.Y.Z`）
2. 创建 git tag：`git tag v<新版本号>`（tag 带 `v` 前缀，例如 `v0.6.0a1`、`v1.2.3.post1`）
3. 推送代码：`git push`
4. 推送 tag：`git push origin v<新版本号>`
