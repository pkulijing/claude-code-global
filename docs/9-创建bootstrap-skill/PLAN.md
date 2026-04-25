# 实现计划：新增 /bootstrap skill + 修改 /start 前置检查

## 一、新建 `skills/bootstrap/SKILL.md`

### Frontmatter

```yaml
---
name: bootstrap
description: 为空项目搭建骨架：README.md / CLAUDE.md / DEVTREE.md 三个核心文件的初始化，仅在项目首次开发前调用一次
disable-model-invocation: true
---
```

`disable-model-invocation: true` 与 `/start` `/finish` 一致 —— 只允许用户显式触发，避免模型在已初始化项目里误调。

### 正文结构

#### 1. 用途说明

一句话点明：为**全新空项目**搭建文档骨架，是一次性脚手架，不用于已有 `docs/` 历史的项目。

#### 2. 前置检查

按顺序检查，**任一命中就停止并报告**：

- `docs/` 下存在 `N-xxx` 形式的开发轮次目录
- `CLAUDE.md` 已存在
- `DEVTREE.md` 已存在

全部通过才继续。这是「不要覆盖用户已有内容」的硬保险。

#### 3. 信息收集（一次问全）

- 项目名称（默认取当前目录名）
- 项目一句话描述
- 是否已有第一个待启动开发项的初步想法（仅用于决定收尾时是否提示运行 `/backlog`）

#### 4. 执行流程

**Step 1: README.md** —— 写入 `# {项目名}` + 一句话描述 + 「目录结构」「开发流程」两个占位段。「开发流程」段引用全局 Constitution。

**Step 2: CLAUDE.md** —— 写入项目级最小骨架：标题 + 一句话描述 + 「目录结构」「开发注意事项」占位段。**不**调用 `/init`（空项目无可扫的代码）。

**Step 3: DEVTREE.md** —— 直接调用 `/devtree`。配合下文「修改 `skills/devtree/SKILL.md`」一节让 `/devtree` 自身支持「文件不存在 / Epic 结构为空」时落初始骨架，bootstrap 不再重复一份骨架模板。**单一事实来源在 `/devtree`。**

**Step 4: 收尾反馈**

- echo-back 三个文件路径
- 给出下一步建议清单：
  1. 检查并补完 README.md 与 CLAUDE.md 的「待补充」段
  2. （若用户第三问回答「有」）运行 `/backlog` 登记第一个开发项
  3. 准备好后运行 `/start` 开启 round 0
- 不调用 `/commit` —— 是否立即提交由用户决定（与 `/backlog` 一致）

## 二、修改 `skills/devtree/SKILL.md`

让 `/devtree` 支持「冷启动」：当 `docs/DEVTREE.md` 不存在，或文件中没有「Epic 结构」区块，或 Epic 结构区块只有作者占位说明（无任何叶 Epic）时，写入初始骨架而不是报错。

具体改动：

1. 在「执行步骤」节首部新增「## 第零步：冷启动处理」段：
   - 检查 `docs/DEVTREE.md` 是否存在并解析得到至少一个叶 Epic
   - 不满足时：直接写入完整骨架（分类图例 + 可视化占位 + 节点索引占位 + Epic 结构占位），骨架中两处占位文案统一为「> Epic 结构尚未填写，待作者添加叶 Epic 后再次调用 /devtree 渲染。」，写完即返回
   - 满足时：继续走第一步～第四步原流程
2. 同步在文件开头「核心原则」段补一句说明：冷启动是例外路径，仅在 Epic 结构尚不存在时落骨架；只要 Epic 结构非空，仍严格遵循「从 Epic 结构完全重建」原则

「输出格式模板」节中的骨架已经能直接当冷启动产物用，无需再造模板。

## 三、修改 `skills/start/SKILL.md`

在第 5 行（frontmatter 后）插入「前置检查」段：

```markdown
**前置检查**：若 `CLAUDE.md` 与 `DEVTREE.md` 都不存在，停下来提示用户先运行 `/bootstrap`，**不要**自己兜底建文档骨架。
```

判定条件用 `CLAUDE.md` + `DEVTREE.md` 双缺，比单测一项更稳（避免误判半初始化的项目）。不检查 `docs/` 是因为 `/start` 自己就要建 `docs/N-xxx`，存在与否不构成可靠信号。

## 四、运行 install.sh

`install.sh` 通过 `for skill_dir in "$REPO_DIR/skills"/*/` 自动遍历所有 skill 目录创建软链接，新增 `skills/bootstrap/` 后只需 `bash install.sh` 即可生效。无需改 `install.sh`。

## 五、不做的事

- **不修改 `skills/backlog/SKILL.md`**：它本身已经处理「文件不存在时初始化骨架」，bootstrap 不重复一份骨架模板，避免双向同步压力
- **不动 `settings.base.json`**：本轮不涉及权限或 hook
- **不写测试**：skill 是 Markdown 提示词，行为靠对话验证

## 六、验收标准

1. `bash install.sh` 后 `~/.claude/skills/bootstrap` 是指向仓库的软链接
2. 在一个空目录里手动模拟调用 bootstrap 流程（cd 进空目录，对照 SKILL.md 步骤检查输出文件齐全且骨架正确，DEVTREE.md 由 `/devtree` 落盘）
3. 在已有 `CLAUDE.md` 的目录里调用 bootstrap 应当被前置检查拦下
4. 修改后的 `/start` 在空目录里应当提示用户先跑 `/bootstrap`
5. 单独调用 `/devtree`：在没有 DEVTREE.md 的目录里应能落骨架；在有 Epic 结构的目录里行为不变

## 七、风险与遗留

- **首次提示用户用 `/bootstrap` 的入口在 `/start` 里**：若用户从一开始就没用过 `/start`（直接手写文档），就感受不到提示。可接受，bootstrap 本来就是给「按 Constitution 走流程」的用户准备的。
- **`/devtree` 多了一条冷启动路径**：未来如果模板演变，要确保冷启动产物与正常渲染产物的非占位结构（即分类图例与文件区块顺序）保持一致。
