# PLAN — 修复 Linux 自动同步的两个缺陷

## 缺陷 A：systemd timer 燃尽

### 方案

`scheduler/systemd.timer.template` 改为绝对时钟周期触发：

```ini
[Unit]
Description=Claude Code Global config auto-update timer

[Timer]
OnBootSec=1min
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
```

要点：

- `OnCalendar=hourly`（= 每个整点 `*-*-* *:00:00`）是**绝对墙钟周期触发**，每个整点都有下一个触发点，永不进入 `elapsed`。这是替代会燃尽的 `OnUnitActiveSec` 链式触发的关键。
- `Persistent=true` 对 calendar timer 生效：把上次触发时间持久化到磁盘，睡眠/关机错过的触发在下次 timer 启动时补跑一次。
- 保留 `OnBootSec=1min`：开机后 1min 首跑一次，与 macOS launchd 的 `RunAtLoad` 对齐，成本极低（脚本内 30min 节流兜底，不会与整点触发重复跑）。删掉 `OnStartupSec`（相对 user manager 启动、一次性、已被 `OnBootSec` + `OnCalendar` 覆盖）。

`scheduler/install.sh` 无需改动——它已经做 `daemon-reload` + `disable --now` + `enable --now`，重跑即可让坏掉的 live timer 用新模板重建。

### 验证（集成性质，经验验证）

模板 + systemd 属「与外部系统集成」，按 Constitution TDD 例外，先实现再经验验证：

1. 本机重跑 `bash install.sh`（或 `bash scheduler/install.sh`）。
2. `systemctl --user list-timers claude-code-global-auto-update.timer` → `NEXT` 应显示下一个整点的真实未来时间、`LEFT` 非空。
3. `systemctl --user status ...timer` → `Trigger:` 应显示具体时间，不再是 `n/a`，`Active` 不再是 `elapsed`。

## 缺陷 B：untracked 文件撞名预检

### 方案

`git pull --ff-only` 做 fast-forward 时会新建「REMOTE 相对 LOCAL 新增的文件」；若这些路径在本地已存在为 untracked 文件，git 直接 abort。现有预检只覆盖 dirty（已追踪文件被改），漏了这种情况。

在 `scripts/auto-update.sh` 的 fast-forward 校验（`merge-base --is-ancestor`，现 163-167 行）**之后**、`git pull`（现 169 行）**之前**插入撞名预检：

```bash
# untracked 撞名预检:fast-forward 会新建 REMOTE 相对 LOCAL 的新增文件,
# 若这些路径本地已存在为 untracked 文件,git pull 会 abort。预检识别 → 跳过。
COLLISIONS=""
while IFS= read -r f; do
    [ -n "$f" ] || continue
    if [ -e "$REPO_DIR/$f" ]; then
        COLLISIONS="${COLLISIONS:+$COLLISIONS, }$f"
    fi
done < <(git diff --name-only --diff-filter=A "$LOCAL" "$REMOTE")

if [ -n "$COLLISIONS" ]; then
    log "skip: untracked files would be overwritten: $COLLISIONS"
    SKIP_REASON="untracked files would be overwritten: $COLLISIONS"
    finish 0
fi
```

要点 / 边界判断：

- `git diff --name-only --diff-filter=A "$LOCAL" "$REMOTE"`：只取「REMOTE 相对 LOCAL 新增（A）」的路径。这类路径不在 LOCAL tree 里，本地若存在文件必为 untracked → `[ -e ]` 即可判定撞名，无需额外查 untracked 状态。
- 只需关心 `A`：被修改（M）的文件本就被追踪、由 dirty 预检覆盖；被删除（D）的文件不会撞名。rename 在新路径侧体现为 A，已覆盖。
- 命中后走统一的 `finish 0` 跳过路径，**不更新节流时间戳**（与 dirty-wt 跳过一致：用户清理 untracked 文件后，下次 timer/SessionStart 自动续上）。
- `SKIP_REASON` 含具体撞名文件列表 → `--session` 模式下用户一眼看到要处理哪些文件，比笼统的 `git pull failed` 可操作。
- 不引入自动 stash/clean——untracked 文件可能是用户未提交的工作，自动删除有数据丢失风险（见 PROMPT 约束）。

### 验证（测试先行）

撞名检测是有清晰输入输出契约的逻辑，按 Constitution 走 TDD。本仓库无 bash 测试框架，落地为一个自包含、自清理的回归脚本，作为本轮额外产物：

`docs/19-修复Linux自动同步缺陷/verify-untracked-collision.sh`：

1. `mktemp -d` 造三个隔离目录：fake `$HOME`、bare origin repo、工作 clone。
2. 在 origin 造历史：基础 commit → 再一个 commit 新增文件 `foo.txt`。
3. clone 到工作目录，`git reset --hard` 回退一个 commit（使 LOCAL 落后 REMOTE 一个可 ff 的 commit）。
4. 在工作目录手动建一个 untracked `foo.txt`（制造撞名）。
5. 把当前 `scripts/auto-update.sh` 拷进工作目录的 `scripts/` 下，以 `HOME=<fakehome>` 运行它（覆盖 `$HOME` → 隔离日志与 30min 节流时间戳，避免命中真实节流而提前 return）。
6. 断言：fake `$HOME` 日志含 `skip: untracked files would be overwritten`，且工作目录 HEAD 未变（未被 pull）。

流程：

- 先写 `verify-untracked-collision.sh`，对**当前未修复**的 `auto-update.sh` 运行 → 应失败（当前日志是 `error: git pull failed`，断言不通过）= 红。
- 再加预检块 → 重跑 → 转绿。

## 实施步骤

1. 写 `docs/19-.../verify-untracked-collision.sh`，对当前脚本运行确认其失败（红）。
2. 在 `scripts/auto-update.sh` 加 untracked 撞名预检块；重跑 verify 脚本转绿。
3. 改 `scheduler/systemd.timer.template`（`OnBootSec` + `OnCalendar=hourly` + `Persistent=true`）。
4. 本机重跑 `bash install.sh`；`systemctl --user list-timers` / `status` 验证 timer 有真实 `NEXT`、不再 `elapsed`。
5. 更新 `docs/16-自动同步全局配置/SUMMARY.md`「局限性」第 5 条 + 「验证」表 Linux 行的状态（已实测 + 本轮修复）。

收尾（SUMMARY.md、commit）走 `/finish`，不在本轮提前 commit。

## 影响范围

- 改动文件：`scheduler/systemd.timer.template`、`scripts/auto-update.sh`、`docs/16-.../SUMMARY.md`。
- 新增文件：`docs/19-修复Linux自动同步缺陷/{PROMPT,PLAN,verify-untracked-collision.sh}`（+ /finish 阶段的 SUMMARY.md）。
- macOS launchd 模板不动、不受影响。
- 改动需在 Linux 机器重跑 `install.sh` 才能让 live timer 生效；其它设备下次自动同步拉到新模板后，各自的 `scheduler/install.sh` 会重建 timer。
