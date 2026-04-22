# 实现计划

## 阶段 A：沉淀权限写法规范

### A1. 写 `docs/8-*/REFERENCE.md`（权限写法小抄）

以后查规则不用再上网。内容结构：

- 匹配机制小结（glob、`:*` 末尾等价、中间 `:` 字面、精确等值）
- 优先级（deny > ask > allow）和 settings 合并顺序
- 常见命令的推荐写法表：git / uv / npm / 文件操作 / 只读探查
- "别这么写"反例清单（引自本仓库旧配置）
- 来源链接

### A2. 重写 `settings.base.json`

从当前的

```json
{ "permissions": { "allow": ["Skill(*)"] } }
```

扩展为覆盖「所有项目都该有」的规则集：

```jsonc
{
  "permissions": {
    "allow": [
      "Skill(*)",

      // Git 只读
      "Bash(git status:*)", "Bash(git diff:*)", "Bash(git log:*)",
      "Bash(git show:*)", "Bash(git branch:*)", "Bash(git blame:*)",
      "Bash(git rev-parse:*)", "Bash(git remote:*)",

      // Git 低风险写
      "Bash(git add:*)", "Bash(git commit:*)", "Bash(git mv:*)",
      "Bash(git rm:*)", "Bash(git reset:*)", "Bash(git checkout:*)",
      "Bash(git restore:*)", "Bash(git stash:*)", "Bash(git tag:*)",
      "Bash(git fetch:*)", "Bash(git merge:*)", "Bash(git rebase:*)",

      // 跨仓库 —— 核心痛点
      "Bash(git -C:*)",

      // 包管理
      "Bash(uv:*)", "Bash(npm run:*)", "Bash(pnpm:*)", "Bash(bun:*)",

      // 只读探查
      "Bash(ls:*)", "Bash(cat:*)", "Bash(wc:*)",
      "Bash(find:*)", "Bash(grep:*)", "Bash(rg:*)",
      "Bash(jq:*)", "Bash(file:*)", "Bash(which:*)", "Bash(head:*)", "Bash(tail:*)"
    ],
    "deny": [
      "Bash(git push --force:*)",
      "Bash(git push -f:*)",
      "Bash(rm -rf /:*)",
      "Bash(rm -rf ~:*)",
      "Bash(rm -rf ~/:*)",
      "Read(./.env)",
      "Read(./.env.local)"
    ]
  }
}
```

注意：不放 `git push`（整条）进 allow，保留弹窗；不放 `rm -rf *`（通配），因为太危险。

### A3. 重跑 `install.sh` 确认合并效果

合并后 `~/.claude/settings.json` 应同时保留旧内容 + 新基线，数组并集无重复。

## 阶段 B：实现 `/clean-local-setting` skill

### B1. Skill 骨架

目录：`skills/clean-local-setting/SKILL.md`，遵循仓库现有 skill 写法（参考 `skills/commit/SKILL.md`）。

### B2. 分类规则（skill 内判断逻辑的描述）

Skill 的工作流（Claude 按 SKILL.md 指引执行，不是脚本）：

1. **读取** 当前 CWD 下 `.claude/settings.local.json`
2. **读取** 仓库 `settings.base.json`（通过软链接 `~/.claude/` 可达）或让用户提供路径
3. **逐条分类**：
   - 含 `/tmp/` / `/private/tmp/` 的路径 → DELETE（一次性）
   - 含具体版本号如 `0.5.2`、`v0.6.0a1` 的 whl / tag → DELETE
   - `python3 -c "..."`、`bash -n /abs/path`、`otool -L /abs/...` 类一次性调试 → DELETE
   - 命中 base 里已覆盖的前缀 → PROMOTE（建议从 local 移除）
   - 写死引号的 git commit 规则（如 `git commit -m ':*`、`git commit -m ' *`）→ REWRITE 为 `git commit:*`
   - 写死绝对路径 + 写死子命令的 `git -C /abs/path status` 类 → REWRITE 为 `git -C:*`（或直接 PROMOTE）
   - 其余命令特征不符合"一次性"且不在 base 里 → KEEP
4. **输出分类报告**（markdown 表格），每条给出：原规则 / 分类 / 建议动作 / 理由
5. **交互确认**：用户可 "全部 apply" / "跳过某几条" / "手动编辑再 apply"
6. **备份 + 写回**：先 `cp settings.local.json settings.local.json.bak.<timestamp>`，再写入清理后的结果；末尾数组去重，保留项目专属 KEEP 项

### B3. Skill 在仓库注册

- 新增 `skills/clean-local-setting/SKILL.md`
- `install.sh` 已自动处理 `skills/*` 目录的软链接，无需修改脚本

## 阶段 C：用 skill 清理 5 个真实项目

按脏度顺序处理，每个都先 dry-run 报告、用户确认、再写回：

1. `claude-code-global` —— 项目本身，样本量适中（34 条），先拿它跑通
2. `novel-writing`（4 条）、`MIT6.S978-Deep-Generative-Models`（3 条）—— 小样本，快速验证 skill 对"少量条目"的表现
3. `avatar-generator`（12 条）—— 中等，验证 skill 对 `git *` 这类已合理条目的"KEEP"判断
4. `whisper-input`（≈170 条）—— 压力测试。预期大量 DELETE，完成后条目数应下降至 20–30 条量级

每个项目清理完，记录前后条目数。

## 阶段 D：验证 + 总结

### D1. 验证

- 重跑 `install.sh`，检查 `~/.claude/settings.json` 合并结果
- 挑几条典型命令手工测试是否还弹窗：
  - `git commit -m "test"` （双引号）
  - `git commit -m 'test'` （单引号）
  - `git -C /tmp/some-repo status`
  - `uv sync`
  - `rg foo src/`

### D2. SUMMARY.md

按 Constitution 模板写，重点记录：
- 权限匹配规则调研的关键结论（指向 REFERENCE.md）
- 两个交付物的核心设计
- 5 个项目清理前后条目数对比
- 局限性（skill 依赖 Claude 判断，未来若规则爆炸可能需要更结构化的配置）
- 后续 TODO（如 deny 清单还能扩充哪些；是否需要给 skill 加"从 git 历史里抓一次性命令"的启发式）

### D3. 同步 DEVTREE

在 `docs/DEVTREE.md` 节点索引新增第 8 轮（所属 Epic：配置治理，新 Epic 或并入基础搭建由作者定）。

## 执行顺序

A1 → A2 → A3 → B1 → B2 → B3 → C1 → C2~C4 → D1 → D2 → D3

其中 A 阶段完成后，B 阶段可并行设计 skill 骨架；C 阶段必须在 A、B 都完成后进行。

## 风险 / 注意

- **误删风险**：clean-local-setting 默认 dry-run，不自动写；所有写操作必须用户显式确认
- **备份策略**：每次写回前 `cp` 一份带时间戳的备份到同目录，用户可随时回滚
- **base 与 local 的边界**：如果某条规则是"项目专属但看起来像通用"，保留给用户判断，不替他做决定
- **循环依赖**：清理 `claude-code-global` 时 skill 还没装到 `~/.claude/skills/`，需要先跑一次 `install.sh` 把新 skill 软链接上去，再调用
