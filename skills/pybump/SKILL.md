---
name: pybump
description: 升级 Python 项目版本号，更新 pyproject.toml，提交代码并打 tag
disable-model-invocation: false
---

用户调用此 skill 表示要发布 Python 项目的新版本。

**参数处理**：调用时可能附带参数（args），参数是用户指定的新版本号。
- 若有参数：以参数作为新版本号
- 若无参数：读取 `pyproject.toml` 中当前版本号 X.Y.Z，将 Z 加 1 作为新版本号

执行以下步骤：

## 1. 读取当前版本号

读取项目根目录下 `pyproject.toml` 的 `version` 字段，解析出当前版本号。

## 2. 确定新版本号

- 若用户传入了版本号参数，使用该参数作为新版本号
- 若未传入，将当前版本号的 patch 位（Z）加 1，例如 `1.2.3` → `1.2.4`

## 3. 校验版本号

新版本号必须满足以下条件，**任一不满足则中止并告知用户**：

1. **符合 PyPI 版本规范**（[PEP 440](https://peps.python.org/pep-0440/)）：格式为 `X.Y.Z`，其中 X、Y、Z 为非负整数，也允许 pre-release（如 `1.0.0a1`）、post-release（如 `1.0.0.post1`）等 PEP 440 合法格式
2. **不可回退**：新版本号必须严格大于当前版本号。使用 PEP 440 的版本排序规则判断（例如 `1.0.0a1 < 1.0.0 < 1.0.1`）

校验方法：使用 `uv run python` 执行以下 Python 代码来校验：

```python
from packaging.version import Version
current = Version("当前版本号")
new = Version("新版本号")
assert new > current, f"新版本号 {new} 必须大于当前版本号 {current}"
```

如果 `packaging` 未安装，直接用正则 + 手动比较即可，但要确保逻辑正确。

## 4. 更新版本号

使用 Edit 工具将 `pyproject.toml` 中的 `version = "旧版本号"` 替换为 `version = "新版本号"`。

## 5. 同步依赖

运行 `uv sync` 确保锁文件和环境与新版本号一致。

## 6. 提交、打 tag、推送

1. 使用 `/commit` skill 提交所有变更（commit message 应体现版本升级，如 `release: 升级版本至 X.Y.Z`）
2. 创建 git tag：`git tag vX.Y.Z`（注意 tag 带 `v` 前缀）
3. 推送代码：`git push`
4. 推送 tag：`git push origin vX.Y.Z`
