# 总结：创建 rebase skill

## 开发项背景

在多开发项并行时（例如同一仓库的 `master` 与 `feat/xxx` 分支分别推进，其中一个放在独立 worktree 内），两个分支会发生本地分叉，需要通过 rebase 整理成直线历史。

rebase 属于重写历史的操作，第一次遇到容易忙中出错：可能覆盖远程他人 commit、丢失未提交改动、在 worktree 目录里跑错地方、或冲突解决到一半不敢继续。因此希望把处理流程沉淀为 skill，让 CC 每次都按稳定步骤引导。

## 实现方案

### 关键设计

- **诊断 + 清单，而非一键自动**：skill 不替人类决策，先读出当前状态（分支、worktree、工作区干净度、分叉 commit 数），再输出清单按阶段引导。避免"一键 rebase"在冲突时失控。
- **只处理本地**：不 `fetch` / `pull`，远程同步由人类在调用前完成。这样避免推送阶段 `--force-with-lease` 的租约被刷新的陷阱。
- **所有合并必须 FF**：rebase 完成后用 `git merge --ff-only`；若 FF 失败，继续 rebase 直到能 FF，**严禁 fallback 到普通 merge**。历史保持直线。
- **分段强制确认**：四阶段（诊断 → 前置检查 → 执行 → FF 合并/推送/验证），每段结束必须停下等人类确认，不允许一口气跑完。
- **安全网固化**：rebase 前强制打备份 tag（`backup/<branch>-<timestamp>`）、工作区必须干净、推送只用 `--force-with-lease`。
- **参数设计简化**：无参数默认 `rebase 到 master`；支持 `<base>` 显式指定、`abort` / `continue` 处理中间状态。交互式 rebase (`-i`) 一期不支持。

### 开发内容概括

- 新增 `skills/rebase/SKILL.md`：六条核心原则 + 参数说明表 + 四阶段流程。
- 运行 `install.sh` 将 skill 符号链接到 `~/.claude/skills/rebase/`。
- 在 `docs/3-创建rebase-skill/` 下完成 `PROMPT.md` / `PLAN.md` / `SUMMARY.md` 三件套。

### 额外产物

无（未产生脚本、测试用例或样例文件）。

## 局限性

1. **未经实战验证**：skill 是根据理论设计的，还没在真实分叉场景（如 whisper-input 的 master vs feat/installsh）跑过一次。步骤的疏漏只有实操才能暴露。
2. **不支持交互式 rebase**：`-i` 的合并/重排 commit 场景需要人类手动处理。
3. **不支持多层 rebase 链**：只针对"当前分支 rebase 到单一 base"，没考虑一次处理多条 feature 分支。
4. **冲突规模无预警**：分叉 commit 数很大时没有自动提醒"这次 rebase 可能很痛"，全靠人类从诊断报告的 commit 数自行判断。
5. **假设 base 默认是 `master`**：不是所有项目主干都叫 `master`（有些叫 `main` / `develop`），默认值未来可能需要可配置。

## 后续 TODO

- [ ] 在 whisper-input 的实际分叉场景跑一次 `/rebase`，把踩到的坑补回 SKILL.md。
- [ ] 考虑加"分叉规模预警"：诊断阶段若 commit 数 > N 或预估冲突文件多，给人类一个心理准备提示。
- [ ] 考虑把默认 base 做成项目级可配置（例如读取 `.git/config` 或 CLAUDE.md 里的约定字段），而不是硬编码 `master`。
- [ ] 如果后续确实有交互式 rebase 需求，评估是否新增 `/rebase-interactive` 而不是把复杂度塞进当前 skill。
