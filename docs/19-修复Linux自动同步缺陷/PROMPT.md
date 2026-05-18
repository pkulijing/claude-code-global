# PROMPT — 修复 Linux 自动同步的两个缺陷

## 背景

开发项 16（自动同步全局配置）的 Linux systemd 分支在 SUMMARY「局限性」第 5 条标注为「未实测」。本次在 Ubuntu 上首次实跑该 workflow，验证时发现两个真实缺陷。

### 缺陷 A：systemd timer「燃尽」，不会持续每小时触发

`scheduler/systemd.timer.template` 当前内容：

```ini
[Timer]
OnStartupSec=1min
OnUnitActiveSec=1h
Persistent=true
```

实测现象：

```
$ systemctl --user status claude-code-global-auto-update.timer
Active: active (elapsed) since Tue 2026-05-19 00:03:18 CST
Trigger: n/a

$ systemctl --user list-timers claude-code-global-auto-update.timer
NEXT  LEFT  LAST                         UNIT
-     -     Mon 2026-05-18 23:22:21 CST  claude-code-global-auto-update.timer
```

`active (elapsed)` + `Trigger: n/a` 表示 timer 所有触发点都已成为过去、不再有未来触发——**timer 已死，不会再自动跑**。

根因：两个触发条件都是「相对单调时钟的一次性触发」——

- `OnStartupSec` 相对 user manager 启动，开机后过了 1min 即失效；
- `OnUnitActiveSec` 靠「service 上次 active」滚动续期，是一条链式触发；一旦链断（`install.sh` 重新 `enable --now` 重置 timer、或系统睡眠导致单调时钟错位），两个条件同时燃尽，timer 进入 `elapsed` 永不再触发。

19:18~23:22 能连跑 5 次靠的就是这条尚未断的链；00:03 重装后链断，之后再没跑过。

对照：macOS launchd 用 `RunAtLoad` + `StartInterval=3600`（真·周期触发），不受影响。本缺陷 Linux 专属。

### 缺陷 B：untracked 文件撞名时 `git pull` abort，脚本未归入「跳过」而是反复报错

实测日志（19:18~23:22 每小时一次）：

```
[2026-05-18 20:19:26] pulling: b6c549b → 0461ab8
error: The following untracked working tree files would be overwritten by merge:
	docs/17-python-uv模板自动bootstrap/PLAN.md
	docs/17-python-uv模板自动bootstrap/PROMPT.md
Please move or remove them before you merge.
Aborting
[2026-05-18 20:19:30] error: git pull failed
```

`scripts/auto-update.sh` 的预检只覆盖 **dirty（已追踪文件被改）**（`git diff` / `git diff --cached`），没有检测「本地存在 untracked 文件，与即将 fast-forward 拉入的新增同名文件相撞」的情况。于是脚本一路走到 `git pull --ff-only`，被 git abort，仅记一行笼统的 `error: git pull failed`，且按现有逻辑不更新节流时间戳 → 每小时重试、每小时再失败、每小时再刷一行错误日志。

期望行为：与 dirty-wt 一致——**预检阶段就识别这种撞名情况，归入「跳过 + 报告可操作原因」**（`SKIP_REASON` 写明具体撞名文件），而不是笼统的 `git pull failed`。同样不更新时间戳（用户清理后下次自动续上）。

## 需求

修复上述两个缺陷：

1. **缺陷 A**：改 `scheduler/systemd.timer.template`，让 timer 用绝对时钟周期触发、永不燃尽，并能在睡眠/关机错过后补跑。
2. **缺陷 B**：在 `scripts/auto-update.sh` 预检阶段增加 untracked 撞名检测，命中则走统一的「跳过」路径，`SKIP_REASON` 报告具体文件，行为与 dirty-wt 跳过一致（不更新时间戳）。

## 范围与约束

- 只动 Linux 侧：`scheduler/systemd.timer.template` 与 `scripts/auto-update.sh`。macOS launchd 模板不受影响、不改。
- 不引入「自动清理 / stash untracked 文件」的逻辑——撞名时本地 untracked 文件可能是用户尚未提交的工作，自动删除有数据丢失风险。本轮坚持「检测 + 跳过 + 报告，交人类处理」，与 dirty-wt 策略保持一致。
- 修完需在本机重跑 `bash install.sh`（或 `scheduler/install.sh`）让坏掉的 live timer 恢复，并验证 `list-timers` 显示真实的 `NEXT`。
- 顺带把开发项 16 SUMMARY 的局限性第 5 条状态更新（Linux 分支已实测 + 修复）。

## 待决问题

- timer 是否保留「开机后首跑」？SessionStart hook 已覆盖大部分「登录即同步」场景，但保留一个 `OnBootSec` 首跑成本极低、与 launchd 的 `RunAtLoad` 对齐——倾向保留，PLAN 中确认。
