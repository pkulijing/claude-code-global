# SUMMARY — 修复 Linux 自动同步的两个缺陷

## 背景

开发项 16（自动同步全局配置）的 Linux systemd 分支当时无 Linux 环境，SUMMARY「局限性」第 5 条标注为「未实测」。本轮在 Ubuntu 上首次实跑该 workflow 做验证，发现两个真实缺陷：

- **缺陷 A：systemd timer「燃尽」**——`systemctl --user status` 显示 `active (elapsed)` + `Trigger: n/a`，timer 所有触发点都已成过去、不再有未来触发，**自动同步实际已停**。日志显示 19:18~23:22 还连跑 5 次，00:03 重装后彻底没再跑。
- **缺陷 B：untracked 文件撞名反复报错**——日志里每小时一行 `error: git pull failed`，根因是本地 `docs/17/{PLAN,PROMPT}.md` 是 untracked 文件，与 fast-forward 即将拉入的同名新增文件相撞，`git pull` 直接 abort。脚本只记笼统错误、不更新节流时间戳，导致每小时重试、每小时再失败、每小时再刷日志。

## 实现方案

### 关键设计

**缺陷 A 根因**：timer 模板用了两个「相对单调时钟的一次性触发」——`OnStartupSec`（相对 user manager 启动）+ `OnUnitActiveSec`（相对 service 上次 active）。后者是链式触发：service 跑完 active → +1h → 再触发。一旦链断（`install.sh` 重新 `enable --now` 重置 timer、或系统睡眠致单调时钟错位），两个条件同时燃尽，timer 进入 `elapsed` 永不再触发。

修复：改用**绝对墙钟周期触发** `OnCalendar=hourly`——每个整点都有确定的下一个触发点，永不燃尽；配 `Persistent=true` 在睡眠/关机错过后补跑；保留 `OnBootSec=1min` 做开机首跑（对齐 macOS launchd 的 `RunAtLoad`）。对照：macOS launchd 用 `StartInterval=3600`（真·周期），从一开始就不受此 bug 影响——缺陷 Linux 专属。

**缺陷 B 关键问题**：`auto-update.sh` 的预检只覆盖 dirty（已追踪文件被 `git diff` 检出），完全没考虑「untracked 文件与 ff 拉入的新增同名文件撞名」这一类。fast-forward 会新建「REMOTE 相对 LOCAL 新增（diff-filter=A）」的文件，这些路径不在 LOCAL tree 里、本地若存在必为 untracked，`git pull` 遇到即 abort。

修复：在 ff 校验后、`git pull` 前加预检——`git diff --name-only --diff-filter=A LOCAL REMOTE` 列出新增路径，逐个 `[ -e ]` 判存在即撞名，命中则走统一的「跳过」路径，`SKIP_REASON` 报告具体撞名文件、不更新节流时间戳（与 dirty-wt 跳过完全一致：用户清理后下次自动续上）。**刻意不做**自动 stash/clean——untracked 文件可能是用户未提交的工作，自动删除有数据丢失风险。

### 开发内容概括

修改：

- [scripts/auto-update.sh](../../scripts/auto-update.sh) — ff 校验后新增 untracked 撞名预检块（约 14 行）
- [scheduler/systemd.timer.template](../../scheduler/systemd.timer.template) — `OnStartupSec` + `OnUnitActiveSec` 换成 `OnBootSec` + `OnCalendar=hourly`
- [docs/16-自动同步全局配置/SUMMARY.md](../16-自动同步全局配置/SUMMARY.md) — 局限性第 5 条与验证表更新为「已实测 + 已修复」

`scheduler/install.sh` 无需改动——它本就做 `daemon-reload` + `disable --now` + `enable --now`，重跑即用新模板重建坏掉的 live timer。

### 额外产物

- [verify-untracked-collision.sh](verify-untracked-collision.sh) — 自包含、自清理的回归脚本：`mktemp` 造隔离的 `$HOME`/origin/工作 clone，模拟 untracked 撞名场景，断言脚本走「跳过」而非 `git pull failed`。缺陷 B 按 TDD 落地——先对未修复脚本跑出红，加预检后转绿。

### 验证

- 缺陷 B：`verify-untracked-collision.sh` 修复前 `FAIL`、修复后 `PASS`。
- 缺陷 A：本机重跑 `bash scheduler/install.sh` 后，`systemctl --user list-timers` 显示 `NEXT=01:00:00`（下个整点真实未来时间）、`status` 显示 `Active: active (waiting)` + `Trigger` 有具体时间——不再是 `elapsed`/`n/a`。

## 局限性

1. **回归覆盖只到缺陷 B**：缺陷 A 是 systemd 模板，属系统集成，靠经验验证（`list-timers` 观测），无自动化测试——这类与 OS 调度器的集成本就难单测。
2. **其它设备需各自重装**：本轮修了模板，但 macOS / 其它 Linux 设备要等下次自动同步拉到新模板后、各自 `scheduler/install.sh` 重建 timer 才生效；正在 `elapsed` 的 Linux 设备在重建前不会自动同步（靠 SessionStart hook 兜底）。
3. **撞名仍是「跳过」不是「解决」**：与 dirty-wt 一致，长期不清理 untracked 撞名文件会让日志每小时多一行——可接受，沿用开发项 16 局限性第 3 条的判断。

## 后续 TODO

- 开发项 16 SUMMARY 已有的「日志旋转」（P2）未动，长期 skip 刷日志的问题依旧——真实触发后再做。
- `Persistent=true` 的补跑行为本轮靠文档推断，未在真实睡眠/关机场景实测——后续自然观测确认。
