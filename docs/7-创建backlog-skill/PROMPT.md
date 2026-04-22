# 需求：创建 /backlog skill

## 背景

第 6 轮在本仓库新增了 `docs/BACKLOG.md`（见 e7d9c7d），用来登记待启动的开发项；同时 `/finish` skill 已经承担了「开发项来自 BACKLOG 时顺手从表中删除条目」的职责。

但现在**没有任何工具支持「添加」一个 backlog 条目**——每次都要手动编辑 `docs/BACKLOG.md`，也没有统一的模板约束新条目的格式，未来其他项目复用这套流程时会各自为战。

与此同时，我在 `whisper-input` 项目里已经写过一份质量较高的 `BACKLOG.md`（`/Users/jing/Developer/whisper-input/BACKLOG.md`），它的**开头（标题下的介绍 + 工作流说明 + "条目没有固定优先级"那段）** 是可以作为所有项目 backlog 的通用骨架继承下来的。

## 目标

新增一个全局 skill `/backlog`，专门用于**向 backlog 追加条目**（只添加，不删除；删除走 `/finish`）。

### 功能要求

1. **位置固定**：backlog 文件一律放在项目的 `docs/BACKLOG.md`。其他项目已有的 backlog 文件位置，由用户自己迁移，skill 不做兼容。
2. **接收一个参数**：参数内容就是本次要追加的 backlog 条目的主体内容（用户写的自然语言描述/模板填充）。
3. **懒初始化**：如果当前项目的 `docs/BACKLOG.md` 不存在，就新建一个；新建时的**开头部分**（标题、"本文件是权威来源"那段说明、"工作流"列表、"条目没有固定优先级..."那段）**参考 `whisper-input/BACKLOG.md` 的开头抄过来**作为通用骨架。
4. **只追加，不重构**：已有的 BACKLOG.md 不动其既有内容，新条目追加到文件末尾（或合适的位置）。

### 不做的事

- 不做删除（那是 `/finish` 的职责，已实现）
- 不做条目的修改、重排、优先级整理（避免 skill 膨胀）
- 不做跨项目的 backlog 聚合视图

## 参考

- `whisper-input/BACKLOG.md` 开头部分（标题 + 介绍 + 工作流 + 目录 + "条目没有固定优先级"段）
- 现有 `docs/BACKLOG.md`（只有一个条目，没有通用开头，本轮借机补齐）
- `skills/start/SKILL.md`、`skills/finish/SKILL.md`、`skills/commit/SKILL.md` 的 frontmatter 和行文风格
