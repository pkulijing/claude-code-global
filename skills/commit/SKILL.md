---
name: commit
description: 按照 git 规则自动分析变更并提交代码
disable-model-invocation: false
---

用户调用此 skill 表示要提交当前的代码变更。按照全局 CLAUDE.md 中的 git 规则执行以下步骤：

1. 运行 `git status` 查看当前变更状态
2. 运行 `git diff` 查看具体变更内容（包括已暂存和未暂存的）
3. 运行 `git log --oneline -5` 了解近期 commit 风格
4. **提交前 review loop**（防止 bug 随 commit 沉淀，尤其并发 / 复杂逻辑）：调 `/review-loop` 对当前工作树跑自动 review 迭代，**迭代到 clean 才继续往下**。判据与降级链**以 `/review-loop` 为单一真源**，本步不复述。两点本步需要知道的：① 它可能以「2 轮未收敛留痕放行」返回，此时会给出一行标注，第 7 步必须原样写进 message body；② **放在 lint 之前**，因为它会自动改代码，须让下一步 lint 覆盖到这些修复。
5. **commit 前 lint 检查**（防止把 lint 错误推上 CI 才发现；**放在 review-loop 之后**，好让 review-loop 的自动修复也被 lint 把关，不留绕过口子）：
   - 逐条判定下表，**命中几条跑几条**（多栈仓库会同时命中多条，如 Python 后端 + TS 前端、ros2 的 C++ + Python）。**只跑一条 = 另一条语言的问题静默溜到 CI** —— 那一条的绿灯看着和全绿一模一样：
     - Python + uv: 见到 `pyproject.toml` + `[tool.ruff]` 配置 → `uv run ruff check .`
     - Python（其他）: 见到 `pyproject.toml` 含 ruff/flake8/pylint → 用对应工具
     - Node.js: `package.json` 里有 `scripts.lint` → `npm run lint`（或 `yarn lint` / `pnpm lint`）；monorepo 要覆盖全部包：`npm run lint --workspaces` / `pnpm -r lint`（yarn 的 classic 与 berry 写法不同，用前先查）
     - Rust: `Cargo.toml` → `cargo clippy --all-targets -- -D warnings`
     - Go: `go.mod` → `go vet ./...`
     - **一条都没命中**（或命中但工具配置缺失）→ **跳过这一步**，继续往下走
   - **lint 失败时停止 commit 流程**，把错误原文给用户看，让用户决定：
     - 先修（推荐）：修完再调 `/commit`
     - 强制提交：用户明示后才用 `--no-verify` 等方式绕过
   - **不要静默修复**：lint 跑出来的错都得显式让用户知道再决策
6. **探测轮次 N**（决定是否加 `[round N]` 前缀，给跨轮追溯补一层约束）：
   - **主信号**：当前分支名匹配 `^round(\d+)(-|$)` → 取第一个捕获组为 N（`/start` 默认 worktree 模式的分支命名 `round<N>-<英文短描述>`；裸 `round<N>` 与历史的中文后缀一并命中）。
   - **兜底**（`--no-worktree` 等非 round 分支）：看本次变更涉及的文件里有没有 `docs/<N>-*/` 路径（`git diff --cached --name-only` 与 `git status --porcelain` 的并集），命中唯一的 `<N>` 则取之。
   - 两路都判不出 N → **不加前缀**，走普通 commit，不要硬凑。
7. 分析所有变更，生成 commit message：
   - 使用中文
   - 遵循 semantic commit message 规则（如 `feat:`, `fix:`, `refactor:` 等）
   - **若第 6 步探出 N**：在 semantic message 最前面加 `[round N] ` 前缀，形如 `[round 3] feat(skill): 支持 xxx`
   - **若第 4 步 `/review-loop` 以「未收敛留痕」放行**：在 message body 追加其给出的标注行（形如 `Review: 2 轮未收敛，遗留 N 条 finding，见 docs/<N>-*/REVIEW.md`），不得省略——这是遗留问题在 `/finish` 前唯一的显式可见性
   - **若第 4 步 `/review-loop` 走了降级路径**（未委派成功、改为本端结构化自审）：在 message body 追加一行标注写明「未经独立 context 把关」，**并附降级证据**（那次调用失败的实际表现 / 工具确实不在列表）——只写结论不算数，写不出证据说明本就不该降级
   - 简明扼要，聚焦于「为什么」而非「改了什么」
8. 将相关文件添加到暂存区（优先按文件名添加，避免 `git add -A`）
9. 执行提交，commit message 末尾必须**按当前执行的 Agent** 追加正确的 `Co-authored-by` trailer（详见全局 CLAUDE.md「git 规则」）：
   - CC（Claude Code）执行 → `Co-authored-by: Claude <noreply@anthropic.com>`
   - Codex（OpenAI Codex）执行 → `Co-authored-by: OpenAI Codex <noreply@openai.com>`
   - **判据**：你知道自己是哪个 Agent，据此选身份；**Codex 绝不写 Claude 身份，CC 绝不写 Codex 身份**。
10. 运行 `git status` 确认提交成功
