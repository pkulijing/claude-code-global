# 废弃 docs/BACKLOG.md，需求管理全部以云端 issue 为单一真源

> 来自 [#40 废弃 docs/BACKLOG.md，需求管理全部以云端 issue 为单一真源](https://github.com/pkulijing/claude-code-global/issues/40)
> Labels: `type:docs` `area:doc` `priority:P2`

## 背景 / 动机

`docs/BACKLOG.md` 与云端 open issues 是同一份信息的两处副本：

- `/backlog` 建完 issue 后手工往 BACKLOG.md 追一行；
- `/finish` 关 issue 时再手工删那一行。

双写维护、易 drift（漏删 / 漏加就对不上）。而 GitHub 本就提供按 priority / area label 过滤 open issues 的现成视图，BACKLOG.md 的「速览索引」职责完全冗余。

## 希望达到

需求管理只有一个真源 —— **云端 issue**。删除 `docs/BACKLOG.md`，「速览下一轮挑哪个」由一个按 priority label 过滤的 **saved issue query 链接**（README / GLOBAL_AGENTS.md 里挂链接）承担。`/backlog`、`/finish`、GLOBAL_AGENTS.md「需求管理」章相应去掉对 BACKLOG.md 的读写与描述。

## 已定方案（两处待决已拍板）

- **方向：A —— 彻底删 BACKLOG.md**。速览完全交给「保存的 issue 搜索链接」（按 priority 排序 open issues）。README / GLOBAL_AGENTS.md 挂该链接。改动最干净、零 drift。取舍：失去「一个文件看全 open 项」的离线快照（需网络 / gh CLI 才能看 issue query）—— 这正是「云端为真源」的取舍。
- **「刻意不做」4 条去处：(a) —— 每条建一个带约定 label 的 closed issue**。与「issue 是真源」最一致、可检索、可加 label。需新增一个约定 label（`wontfix`）并补进 `.github/labels.yml`。

## 待迁移的「刻意不做」4 条（当前存于 BACKLOG.md 末尾）

删文件前，这 4 条必须先各自落成一个带 `wontfix` label 的 closed issue（正文保留原因 + 引用原 SUMMARY）：

1. **平台双兼容下的「对端死文件清理」opt-out**（`area:template`）—— round 14 决定项目根永久同时落 GitHub + GitLab 两套文件，不引入 opt-out 机制。详见 `docs/14-模板支持GitLab双轨/SUMMARY.md` §5.3
2. **python-uv 模板内置 torch / aliyun pytorch wheels 索引**（`area:template`）—— round 17 决定模板仅落清华源默认 index，不默认追加 torch 镜像段。详见 `docs/17-python-uv模板自动bootstrap/SUMMARY.md`「关键设计」#8
3. **「会话标题可定位轮次」能力**（`area:skill`）—— round 24 查实 CC 会话标题机制上无法携带轮次前缀，删除该约定且不再追求。详见 `docs/24-精简宪法与会话标题约定排查/SUMMARY.md`
4. **Codex 双装端到端实测**（`area:install`）—— issue #8 主链已落地，唯验证性收尾刻意不再追踪。详见 `docs/22-CC与codex双兼容主链/SUMMARY.md` §局限性

## 影响面（触及多处，漏改一处会留悬空引用）

- `skills/backlog/SKILL.md`：description + 开头职责段 + Step 6.2（BACKLOG 骨架初始化）+ Step 6.3（追行）+ Step 7 反馈文案
- `skills/finish/SKILL.md`：description + Step 2（扫 SUMMARY 补录「不再追踪」段——失去落点，需重构或删除）+ Step 4（删 BACKLOG 行动作）+ Step 6 判定数据源里对 BACKLOG.md 的忽略提及
- `GLOBAL_AGENTS.md`「需求管理」章：3 处 BACKLOG.md 描述
- `README.md`：4 处 BACKLOG.md 描述（含「Backlog 与开发项管理」整段）
- `docs/BACKLOG.md`：删除
- `.github/labels.yml`：新增 `wontfix` label（+ 远端同步）
- **云端**：建 4 个带 `wontfix` 的 closed issue

## 约束 / 注意

- 唯一在追踪的 open 项是 [#7](https://github.com/pkulijing/claude-code-global/issues/7)（skills/hooks plugin 化）——它已是云端 open issue，删 BACKLOG.md 不丢信息，saved query 天然覆盖。
- `platform_issue.py` 里出现的 `backlog/start` 是指调用方 skill 名，**非** BACKLOG.md 文件，不改。
- `bootstrap` / `start` / `sync-project-config` 里的 `/backlog` 是指 skill 命令本身，保留。
- 本轮当前仓库就是 claude-code-global，`/finish` Step 3 自指守卫会把可沉淀项引导走本地 `/backlog`，不 API 自 file。

## scope

小-中。改 2 个 skill（backlog / finish）+ GLOBAL_AGENTS.md 一节 + README 一段 + 删 1 个 doc + 新增 1 个 label + 建 4 个 closed issue 迁移「刻意不做」。无代码逻辑，纯约定与 skill 文本。
