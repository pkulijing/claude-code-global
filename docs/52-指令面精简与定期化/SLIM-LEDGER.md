# 精简账本

> **这是本轮人工 review 的主要对象。** 删除型 diff 的麻烦在于「少了什么是看不见的」
> —— `git diff` 只能告诉你哪些行没了，告诉不了你那条信息是**搬走了**还是**蒸发了**。
> 本账本每条记三列回答后者：**删了什么 / 依据哪条判据 / 这条信息现在从哪读得到**。
>
> 判据编号见 `PLAN.md`「三板斧判据」：
>
> | 号 | 允许删除 |
> | --- | --- |
> | **A1** | 已在别处有单一真源的重复表述（必须留指针） |
> | **A2** | 成组的同向细则 → 上提为一句判断原则 |
> | **A3** | 事故 WHY 的过程叙事 → 压成结论一句 |
> | **A4** | 指向已删机制 / 文件 / 命令的失效引用 |
> | **A5** | Agent 已从系统提示 / 工具描述得知的重复 |
>
> 禁止删除：事故 WHY 的**结论**、安全禁令与硬边界、本仓特有的非标约定。拿不准就保留。

## 阶段 1 · `templates/MECHANICS.md`（-11,404 字符净）

`skills/bootstrap/SKILL.md` 11,521 → 4,788；`skills/sync-project-config/SKILL.md` 16,501 → 6,817；`CLAUDE.md` 5,058 → 4,593；新增 `templates/MECHANICS.md` 5,478。

**这一块是文档自己承认的双写**：sync 里原本写着「与 bootstrap Step 3.3.7 **同一份，改动时两处同步**」「逻辑**等同** bootstrap 的 Step 3.5」。

| 删了什么 | 判据 | 现在从哪读得到 |
| --- | --- | --- |
| `__root__` / `__subpath__` 落点语义、`_common` 的地位、`stack.yml` 的 `default_path` / `label`、冲突时 stack 优先 —— bootstrap 3.1/3.3 与 sync 2.4/4.1 各一份 | A1 | `templates/MECHANICS.md` §1 |
| `pyproject.toml.<section>.fragment` 的 section 映射表、TOML 段合并语义、数组段按 `name` union、无 `pyproject.toml` 时的四路分支 —— bootstrap 3.3.6 与 sync 2.4 各一份 | A1 | `templates/MECHANICS.md` §2.1 |
| `.vscode/*.json.fragment` 的 JSON 合并语义（`recommendations` 有序去重 union / `settings.json` 顶层键 union / 标量冲突问用户）、以及「为什么一定落项目根」 —— bootstrap 3.3.6、sync 2.4、`CLAUDE.md` 各一份 | A1 | `templates/MECHANICS.md` §2.2；`CLAUDE.md` 保留一句结论 |
| 变体组 `<target>.variant.<key>` 的落地规则、`.gitlab-ci.yml` 两个 key 的人话说明、「为什么选择前移到交互而不是都落地让用户删」、老项目补选、选中 key 被模板删除的处理 —— bootstrap 3.3.7、sync 2.4/4.3、`CLAUDE.md` 各一份 | A1 | `templates/MECHANICS.md` §3 |
| 后端可跑化四步（`uv init --package` / `uv add --dev` / `uv tool install pre-commit` / `pre-commit install`）、`python-uv-workspace` 绝不 `uv init` 的理由、清华源必须先合的理由、不强制 `pre-commit run --all-files` 的理由 —— bootstrap 3.5 与 sync 4.4 各一份 | A1 | `templates/MECHANICS.md` §4 |
| `react-vite` 的 `npm install` 与 `.npmrc` 镜像说明 —— bootstrap 3.5b 与 sync 4.5 各一份 | A1 | `templates/MECHANICS.md` §5 |
| 迁移去重两节（普通文件 → fragment、普通文件 → 变体组）的完整推导 —— 原只在 sync 2.4，但 bootstrap 侧也需要同一套判断 | A1 | `templates/MECHANICS.md` §6 |
| BACKLOG 迁移里「刻意不做项 → wontfix closed issue」的完整操作（`issue-create` 参数、`gh issue close -r not planned`、label 缺失先补 `labels.yml`） | A1 | `/finish` Step 2（本就是真源），sync 只留一句指针 |
| sync 2.3 的 `M/A/D` 示例输出三行 | A5 | 无需保留 —— `git diff --name-status` 的输出格式是模型已知的通用知识 |
| bootstrap 3.3 里指向 `docs/12-backlog改为issue驱动/SUMMARY.md` 的出处链接 | A1 | 约束本身（`_common` 与 stack 的边界）已写进 `templates/MECHANICS.md` §1，不再需要跳转看当初怎么定的 |
| `CLAUDE.md` 里 `templates/` 那条 1,100 字符的长条目 | A1 | 压成三句 + 指向 `templates/MECHANICS.md`；**两个非显然点保留在原地**（`ros2` 为何合并成单一 stack、`.vscode` 为何落根） |

**保留未动**（属禁止删除清单，逐条确认还在）：

- sync 的**三态收敛约定**（`len == 0/1/多` 与 skipped 读写位置）—— 本仓特有的非标约定
- sync 2.3 的 **⚠️ 不要省略 pathspec** —— 漏了会把未接入的 stack 变更带进来，是真会出事的硬约束
- sync 2.5 的 skipped「是否又变过」重检算法
- 旧名 marker 双存在 → **报冲突并停止，不猜哪个为准**
- bootstrap 的**不调用内置 `/init`** 及其理由
- bootstrap Step 4 的**不要复制一份 DEVTREE 骨架模板，单一真源在 `/devtree``**
- 三处**不自动 commit** 的约定
