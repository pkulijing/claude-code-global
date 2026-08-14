# PROMPT：修复自动同步调度器的自杀式重注册

> 来自 [#129 自动同步的调度器重注册会杀死自己：launchctl unload 端掉正在运行的 job，每次 pull 成功即停摆](https://github.com/pkulijing/claude-code-global/issues/129)
> Labels: `type:bug` `area:install` `priority:P0`

## 背景

本仓的多设备自动同步链路是：

```
launchd (com.claude-code-global.auto-update)
  └─ scripts/auto-update.sh          # fetch → 判断是否有更新 → pull
       └─ install.sh                 # 双轨部署软链 / 合并 settings / seed 配置
            └─ scheduler/install.sh  # 注册 OS 调度器（本轮的问题所在）
```

`scheduler/install.sh` 的 macOS 分支为了保证幂等，采用「先 unload 再 load」：

```bash
launchctl unload "$plist_dst" 2>/dev/null || true
launchctl load -w "$plist_dst"
```

问题在于，当这条链是**由 launchd 自己拉起**时，`unload` 要卸载的 job 正是承载着当前整条进程链的那个 job。launchd 的 unload 会终止该 job 名下的全部进程，于是执行 `unload` 的 shell 当场被杀，下一行 `load -w` 永远执行不到。

## 现象

- `launchctl list` 中 `com.claude-code-global.auto-update` **整个消失**，自动同步彻底停止。
- 只有下次登录（`~/Library/LaunchAgents/` 在登录时被重新加载）才会恢复一次，然后再次拉到更新时又自杀。
- 实测 2026-08-10 16:26 → 2026-08-14 10:56 连续四天零运行。
- **仅在 auto-update 真的拉到更新时触发**：没有更新时 `auto-update.sh` 走 `already up to date` 分支直接 exit，根本不会跑 `install.sh`。这是它潜伏两个月未被发现的直接原因。
- macOS 独有。

## 已查证的根因与证据

根因确定为上述自杀路径（`scheduler/install.sh` 的 `launchctl unload` 一行）。三条独立佐证：

1. **日志断点一致**：5 次自杀的输出逐字断在同一位置 —— 「系统级 uv 配置」之后、调度器注册之前。没有 `安装完成`、没有 `error: install.sh exited`（`install.sh` 对调度器注册失败走的是 `|| warn` 路径，会打印 warn 后继续跑完）。**是被杀，不是报错。**
2. **成功率 0/5**：全日志 6 次 `pulling`，只有第一次（2026-06-28 02:52，彼时 launchd job 尚未注册）走到了 `ok: updated to`；此后由 launchd 拉起、且有更新可拉的运行 **5 次全部死在同一位置**。
3. **节流戳时序**：`~/.claude/.auto-update-last-run` 停在 2026-08-10 15:26，而 16:26 那次 pull 明明已经改变了 HEAD —— 正是死在写戳之前。

Linux 不受影响：`systemctl --user disable --now <timer>` 停的是 timer 单元，正在运行的 `Type=oneshot` service 不会被带走。

## 需求

1. **消除自杀路径**：`scheduler/install.sh` 在由 launchd 自身拉起的场景下重注册调度器，不得杀死正在运行的自己。
2. **保持既有语义不回退**：
   - 首次安装（plist 不存在）必须仍能正常注册；
   - 人工跑 `bash install.sh`（不在 job 内）时，plist 内容有变更必须真正生效；
   - 幂等性不变 —— 重复跑不产生副作用。
3. **消除静默失败**：本次故障全程无任何异常输出，日志里连一行都没有。需要让「同步被中途杀死」这件事留下痕迹，而不是完全无声。
4. **补齐测试**：`scheduler/` 目前无任何单测。按宪法「环境是被测行为的输入，不是测试环境的属性」，`launchctl` 的存在与否、job 是否已加载、plist 内容是否变化，都必须在用例内**显式改写**、各分支各测一遍，不得跟随宿主环境，也不得按环境静默跳过。

## 约束与范围

- **范围内**：`scheduler/install.sh`、`scripts/auto-update.sh`、以及新增的测试。
- **范围外**：不改 `scheduler/launchd.plist.template` 的调度语义（`RunAtLoad` / `StartInterval 3600` 保持不变）；不改 `install.sh` 主体的部署逻辑；不动 Linux 分支的调度语义（除非测试暴露出对称问题）。
- **对存量机器友好**：修复必须对「已经装好旧版 plist」的机器立即生效，不能要求用户先手动做一次什么操作才能脱困。这一条会直接影响方案选型（见 PLAN）。

## 待确认项

- 无「只有人知道」的参数。所有涉及的外部行为（launchctl 的 unload 语义、`launchctl list` 输出格式、重复 load 的返回值）都有客观唯一答案，按 `/start` 的「外部行为断言先实证」在 PLAN 阶段用最小沙盘实测，不靠推断。
