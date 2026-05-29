# 实现计划 · 引入用户可配置项机制（首例：git init 默认分支）

> 对应 issue [#10](https://github.com/pkulijing/claude-code-global/issues/10) · `type:refactor` `area:install` `priority:P1` · **Spike**
> 本计划已经人类确认。下方为执行依据，实际偏离见 `SUMMARY.md`。

## 关键调研结论（已查实）

1. **现有合并机制不可直接复用**：`install.sh` 的 `merge_settings` 是「标量**仓库**胜出」（repo wins），适合 repo 管控的 hook，但与用户偏好需要的「**用户**值优先」相反。新机制要用**相反语义**（缺省才填默认、绝不覆盖用户已设值），是一段新逻辑。
2. **sync 安全的现成范式**：`auto-update.sh` 做 `git pull master` + 跑 `install.sh`。进仓库的文件会被 pull 覆盖；落在 agent home / 仓库外的文件（如 `~/.claude/settings.json`）能存活。→ 用户真实配置必须落在仓库外。
3. **首例是干净绿地**：当前**没有任何 skill 调 `git init`**。PoC 直接走 issue 指定路径：配置 → `install.sh` 读取 → `git config --global init.defaultBranch <值>`，配置 git 本身，任何未来 `git init` 都自动遵守。
4. **其余硬编码偏好候选**（本轮不做）：commit trailer 署名（`skills/commit/SKILL.md:36` 写 `Claude`，`GLOBAL_AGENTS.md:80` 例子写 `Claude Sonnet`，**两处不一致**）、基础对话语言、pypi 镜像、torch 版本。

## 设计（扁平 env + example 基线）

| 维度         | 决定                                                                                             |
| ------------ | ------------------------------------------------------------------------------------------------ |
| 载体格式     | 扁平 `KEY=value` env 文件（shell 直读、LLM 可读、CC/Codex 共享）                                 |
| 仓库内基线   | `user.config.example.env`（committed，扮演 `.env.example`）                                      |
| 用户真实配置 | `~/.claude-code-global/config.env`（仓库外 → `git pull` 不触碰；CC/Codex 单一真源）              |
| seed 语义    | 缺文件才 seed；已存在绝不覆盖；example 新增 key 逐 key 补缺追加（user-wins）                     |
| 读取方       | shell（install.sh / 未来 hook）安全解析（grep+剥注释/引号，不 blind source）；LLM 直接读对应 key |
| 与 sync 关系 | 真实配置在仓库外 + seed 缺省才填 → auto-update 反复跑 install.sh 安全幂等                        |

## 落地内容（TDD：先验证脚本红，再实现绿）

1. `scripts/user-config.sh`（新增，可 source 库）：`ccg_user_config_path`（允许 `CCG_USER_CONFIG` 覆盖）/ `ccg_read_config` / `ccg_seed_user_config` / `ccg_apply_git_default_branch`。
2. `user.config.example.env`（新增，仓库根）：首个 key `GIT_INIT_DEFAULT_BRANCH=master`，注释说明置空 = opt-out。
3. `install.sh`（改）：双轨部署后、调度器注册前 source 库并调用 seed + apply，`|| warn` 不阻塞。
4. `docs/27-用户可配置项机制/verify-user-config.sh`（新增，回归测试）：沙箱跑 T1 seed / T2 不覆盖 / T3 补缺 / T4 apply / T5 空值不写。
5. `docs/27-用户可配置项机制/DESIGN.md`（新增）：Spike 核心交付——配置位置 + schema + 消费方约定 + 与同步关系 + 「为何不复用 merge」+ 候选项盘点。
6. 文档同步（最小）：`CLAUDE.md`、`README.md`、（计划含 `GLOBAL_AGENTS.md`，实际改为不动，见 SUMMARY）。

## 验证

```bash
bash docs/27-用户可配置项机制/verify-user-config.sh   # T1–T5 全绿
bash -n install.sh                                    # 集成块语法
# 真实 install 冒烟需在 merge 回 master 后从主仓库跑（从 worktree 跑会把全局软链指向临时 worktree）
```

## 不在本轮范围（派生后续 feat）

- commit trailer 署名可配置（并修署名不一致）。
- 基础对话语言 / pypi 镜像 / torch 版本等其余偏好。
