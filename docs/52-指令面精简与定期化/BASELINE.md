# 开轮基线（master 38d3441 + 本轮阶段 0）

由 `python3 scripts/context_budget.py measure` 生成。token 估算的标定来源见
`scripts/context_budget.py` 模块 docstring（CC `/context` 实测两点解出）。

```
      字符   ~token  类别        文件
  17,032   12,416  lazy      playbooks/python.md
  16,501   11,875  lazy      skills/sync-project-config/SKILL.md
  14,311   11,238  lazy      skills/routine-docs/SKILL.md
  12,012    8,240  lazy      playbooks/ros2.md
  11,521    8,331  lazy      skills/bootstrap/SKILL.md
  10,731    8,693  lazy      skills/review-loop/SKILL.md
  10,476    7,673  lazy      skills/finish/SKILL.md
   9,922    8,000  resident  GLOBAL_AGENTS.md
   6,354    4,509  lazy      playbooks/cloud-routine.md
   6,280    4,796  lazy      skills/devtree/SKILL.md
   5,586    4,009  lazy      playbooks/frontend.md
   5,058    3,610  resident  CLAUDE.md
   4,821    3,669  lazy      skills/rebase/SKILL.md
   4,664    3,484  lazy      skills/start/SKILL.md
   4,001    3,003  lazy      skills/quick/SKILL.md
   3,462    2,658  lazy      playbooks/scheduled-agent.md
   3,229    2,274  lazy      skills/backlog/SKILL.md
   3,142    2,624  lazy      playbooks/shell.md
   2,944    2,258  lazy      playbooks/lark.md
   2,869    2,117  lazy      skills/commit/SKILL.md
   2,433    1,699  lazy      skills/pybump/SKILL.md
   2,249    1,893  lazy      skills/paper-read/SKILL.md
   2,149    1,591  lazy      playbooks/feishu-bot.md
     831      635  lazy      skills/finish/references/readme-review.md

常驻       14,980 字符  ~11,610 token（每会话每项目）
懒加载     147,598 字符  ~109,685 token
合计      162,578 字符  ~121,295 token
```

## 与 4 周前对比

```
基线 197840f7a046：72,511 字符 / ~52,952 token
当前          ：162,578 字符 / ~121,295 token
增长          ：+124.2%

变化明细（字符）：
   +17,032        0 →  17,032  playbooks/python.md
   +14,311        0 →  14,311  skills/routine-docs/SKILL.md
   +12,012        0 →  12,012  playbooks/ros2.md
   +10,731        0 →  10,731  skills/review-loop/SKILL.md
    +6,354        0 →   6,354  playbooks/cloud-routine.md
    +5,586        0 →   5,586  playbooks/frontend.md
    +4,273    5,649 →   9,922  GLOBAL_AGENTS.md
    +4,001        0 →   4,001  skills/quick/SKILL.md
    +3,462        0 →   3,462  playbooks/scheduled-agent.md
    +3,142        0 →   3,142  playbooks/shell.md
    +2,944        0 →   2,944  playbooks/lark.md
    +2,440   14,061 →  16,501  skills/sync-project-config/SKILL.md
    +2,149        0 →   2,149  playbooks/feishu-bot.md
    +1,604    3,454 →   5,058  CLAUDE.md
    +1,539    3,282 →   4,821  skills/rebase/SKILL.md
    +1,277    1,592 →   2,869  skills/commit/SKILL.md
      +831        0 →     831  skills/finish/references/readme-review.md
      +744    3,920 →   4,664  skills/start/SKILL.md
      +238   11,283 →  11,521  skills/bootstrap/SKILL.md
      +203   10,273 →  10,476  skills/finish/SKILL.md
      +112    6,168 →   6,280  skills/devtree/SKILL.md
    -1,251    4,480 →   3,229  skills/backlog/SKILL.md
    -3,667    3,667 →       0  skills/clean-local-setting/SKILL.md

阈值 +15%：超出，该动手
```
