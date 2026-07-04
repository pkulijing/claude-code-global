# SUMMARY：废弃 docs/BACKLOG.md，云端 issue 单一真源

对应 [#40](https://github.com/pkulijing/claude-code-global/issues/40)。

## 开发项背景

`docs/BACKLOG.md` 与云端 open issues 是同一份信息的两处副本：`/backlog` 建完 issue 后手工往 BACKLOG.md 追一行、`/finish` 关 issue 时再手工删那一行——双写维护、易 drift（漏删 / 漏加就对不上）。而 GitHub / GitLab 本就提供按 priority / area label 过滤 open issues 的现成视图，BACKLOG.md 的「速览索引」职责完全冗余。

**希望解决**：需求管理只保留**一个真源——云端 issue**。删除 BACKLOG.md，open 项速览交给一个按 priority label 过滤 open issues 的 saved query 链接（README / GLOBAL_AGENTS.md 挂链接）。

## 实现方案

### 关键设计

1. **方向 A（彻底删）+ 去处 (a)（wontfix closed issue）**——两个待决点拍板后，方案与「云端单一真源」的主张最彻底一致：BACKLOG.md 直接删、不留薄壳；末尾 4 条「刻意不做」各归档为一个带 `wontfix` label 的 closed issue（可检索、可按 label 过滤），而非收进某个 docs 文件（那又引入一处要维护的本地文件、与主张矛盾）。

2. **先迁移、再删除**——4 条「刻意不做」先各建 closed issue（[#46](https://github.com/pkulijing/claude-code-global/issues/46) / [#47](https://github.com/pkulijing/claude-code-global/issues/47) / [#48](https://github.com/pkulijing/claude-code-global/issues/48) / [#49](https://github.com/pkulijing/claude-code-global/issues/49)）迁走信息，再 `git rm docs/BACKLOG.md`，保证零信息丢失。

3. **顺手消一处 drift**——探明 `wontfix` label 远端已存在（GitHub 内置）但本地 `.github/labels.yml` 缺，补进本地真源使二者一致；正好呼应本轮「消除 drift」的主题。因远端已有，建 issue 时可直接用，无需先同步。

4. **`/finish` Step 2 失落点重构**——废弃 BACKLOG.md 后，finish 里「扫 SUMMARY 补录『不再追踪』段」这个步骤失去落点。重构为「把刻意不做项归档为带 `wontfix` 的 closed issue」（建 issue + close），措辞对齐「issue 单一真源」。

5. **老项目迁移落 `/sync-project-config` 而非 `/finish`**（执行中经用户提示的关键补充）：本轮删的只是 claude-code-global 自己的 BACKLOG.md，其他已有 `docs/BACKLOG.md` 的老项目会留下「约定说无本地索引、文件却还在」的 drift。迁移逻辑放 `/sync-project-config`——它的本职就是「把 claude-code-global 的约定变更同步进老项目」，语义正好、触发时机对（老项目本就为拉新约定跑它），且不给每轮 `/finish` 加无谓探测（绝大多数轮次没有 BACKLOG.md）。新增一节「废弃 BACKLOG.md 一次性迁移」，定位类比既有「旧名 marker 自动迁移」：幂等、探测到才动、迁完即删。

### 开发内容概括

| 改动                                  | 内容                                                                                                                                        |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `.github/labels.yml`                  | 补 `wontfix` label（决策归档轴，三轴之外）                                                                                                  |
| 云端                                  | 建 4 个带 `wontfix` 的 closed issue（#46–#49）迁移「刻意不做」                                                                              |
| `docs/BACKLOG.md`                     | 删除                                                                                                                                        |
| `skills/backlog/SKILL.md`             | description + 开头职责 + Step 6（删 6.2 骨架初始化 / 6.3 追行）+ Step 7 反馈（改为打印 issue URL + saved query 链接）                       |
| `skills/finish/SKILL.md`              | description + Step 2（重构为归档 wontfix closed issue）+ Step 3 措辞（4 处）+ Step 4（去掉删 BACKLOG 行）+ Step 6/7（去掉 BACKLOG.md 提及） |
| `skills/sync-project-config/SKILL.md` | 新增「废弃 BACKLOG.md 一次性迁移」节（老项目遗留时引导迁云端后删）                                                                          |
| `GLOBAL_AGENTS.md`                    | 「需求管理」章 3 处（saved query 替代索引 / `/backlog` 只建 issue / wontfix 归档）                                                          |
| `README.md`                           | 段标题「Backlog 与开发项管理」→「开发项管理」+ 能力表 + 3 处 skill 描述 + saved query 链接                                                  |

### 额外产物

- 4 个 `wontfix` closed issue（#46–#49），本身即「刻意不做」决策的可检索归档。
- `/sync-project-config` 的迁移节，是给**任意老项目**复用的迁移流程（本轮 claude-code-global 自己走过的迁移动作的抽象）。

## 局限性

- **失去离线单文件快照**：open 项速览需网络 / `gh` / `glab` 才能看 saved query，不再有「一个文件看全 open 项」的本地快照。这是「云端为真源」的取舍（issue #40 已明确接受）。
- **老项目迁移未端到端实测**：`/sync-project-config` 的迁移节是文本约定，本轮没有真实老项目（带 `docs/BACKLOG.md` 的仓库）跑一遍验证。逻辑正确性靠 review，首次真机迁移时可能暴露边界（如 BACKLOG 行格式变体、无 issue 链接的裸条目处理）。
- **纯约定 / skill 文本改动，无自动化测试**：验证靠 grep 兜底（活文件无悬空 `BACKLOG.md` 引用，已清零）+ 人工连贯性 review。

## 后续 TODO

- 首次在真实老项目（如其他带 BACKLOG.md 的私有仓）跑 `/sync-project-config`，端到端验证迁移节，按暴露的边界回补。
- `wontfix` label 目前只在 claude-code-global 远端 + 本地 labels.yml；其他项目若要用「刻意不做归档」能力，需各自 `label-sync-from-file` 把 wontfix 同步到自己远端（`/sync-project-config` 迁移节已含此兜底，随迁移自然触发）。

## 可沉淀项

本轮本身就是在改 claude-code-global（约定 + skill），产出直接落地，无需再向本仓提沉淀 issue。唯一有「跨项目」性质的产物——`/sync-project-config` 的老项目迁移节——已在本轮直接实现，不必另开 issue。

一个可复用的**方法论模式**值得记一笔（但不单独 file，因它已体现在本轮做法里）：**「约定变更」类的跨项目迁移，天然归 `/sync-project-config` 而非 `/finish`**——凡「claude-code-global 改了某个全局约定、老项目需要一次性落地」的场景（本轮的废弃 BACKLOG，类比之前的「旧名 marker 自动迁移」），都应在 sync 里加一个「探测到才动、幂等、迁完即止」的一次性迁移节，而不是塞进 finish 给每轮加负担。
