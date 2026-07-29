---
name: commit
description: 按照 git 规则自动分析变更并提交代码
disable-model-invocation: false
---

用户调用此 skill 表示要提交当前的代码变更。按照全局 CLAUDE.md 中的 git 规则执行以下步骤：

1. 运行 `git status` 查看当前变更状态
2. 运行 `git diff` 查看具体变更内容（包括已暂存和未暂存的）
3. 运行 `git log --oneline -5` 了解近期 commit 风格
4. **提交前 review loop**（防止 bug 随 commit 沉淀，尤其并发 / 复杂逻辑）：调 `/review-loop` 对当前工作树跑自动 review 迭代，**迭代到 clean 才继续往下**。细节以 `/review-loop` 为单一真源，简言之：**委派一个独立 context 的 review orchestrator 子 agent**（不复用开发 context，不依赖 CC 内置 `/code-review`），按档位并行扇出 3 个（默认，全 sonnet）或 5 个（diff 命中并发 / 多线程 / 跨进程重试 / 状态机 / 难复现 / 跨 3+ 模块编排等复杂特征时，深审角度用 opus）独立 reviewer 角度，去重 + 置信打分（<80 过滤）+ 探针验证后返回单一 finding 列表。发现**高置信 correctness 问题**（附 file:line 证据、真会触发）自动修复→**跑测试 + happy-path 验证**→复审，迭代到「运行验证通过 + 无高置信 correctness 问题」才 clean（pre-existing / pedantic / 推测式 corner case 不阻断）。琐碎改动自动跳过（配置 / 指令文件不跳）；自动修复满 2 轮未收敛→停环，把剩余 finding 留痕到 `docs/<N>-*/REVIEW.md` 后照常放行（commit message 加标注行，人工兜底在 `/finish`），全程无人在环。降级链：委派失败→主会话结构化自审并显著标注，绝不静默跳过。`/review-loop` 自动修复不停下逐条等用户确认，并把迭代留痕到 `docs/<N>-*/REVIEW.md`（如有）。放在 lint 之前，是因为 review-loop 会自动改代码——须让下一步 lint 覆盖到这些修复。
5. **commit 前 lint 检查**（防止把 lint 错误推上 CI 才发现；**放在 review-loop 之后**，好让 review-loop 的自动修复也被 lint 把关，不留绕过口子）：
   - 探测项目类型并跑对应的 lint 命令：
     - Python + uv: 见到 `pyproject.toml` + `[tool.ruff]` 配置 → `uv run ruff check .`
     - Python（其他）: 见到 `pyproject.toml` 含 ruff/flake8/pylint → 用对应工具
     - Node.js: `package.json` 里有 `scripts.lint` → `npm run lint`（或 `yarn lint` / `pnpm lint`）
     - Rust: `Cargo.toml` → `cargo clippy --all-targets -- -D warnings`
     - Go: `go.mod` → `go vet ./...`
     - 都不匹配 / 找不到工具配置 → **跳过这一步**，继续往下走
   - **lint 失败时停止 commit 流程**，把错误原文给用户看，让用户决定：
     - 先修（推荐）：修完再调 `/commit`
     - 强制提交：用户明示后才用 `--no-verify` 等方式绕过
   - **不要静默修复**：lint 跑出来的错都得显式让用户知道再决策
6. **探测轮次 N**（决定是否加 `[round N]` 前缀，给跨轮追溯补一层约束）：
   - **主信号**：当前分支名匹配 `^round(\d+)-` → 取捕获组为 N（`/start` 默认 worktree 模式的分支命名）。
   - **兜底**（`--no-worktree` 等非 round 分支）：看本次变更涉及的文件里有没有 `docs/<N>-*/` 路径（`git diff --cached --name-only` 与 `git status --porcelain` 的并集），命中唯一的 `<N>` 则取之。
   - 两路都判不出 N → **不加前缀**，走普通 commit，不要硬凑。
7. 分析所有变更，生成 commit message：
   - 使用中文
   - 遵循 semantic commit message 规则（如 `feat:`, `fix:`, `refactor:` 等）
   - **若第 6 步探出 N**：在 semantic message 最前面加 `[round N] ` 前缀，形如 `[round 3] feat(skill): 支持 xxx`
   - **若第 4 步 `/review-loop` 以「未收敛留痕」放行**：在 message body 追加其给出的标注行（形如 `Review: 2 轮未收敛，遗留 N 条 finding，见 docs/<N>-*/REVIEW.md`），不得省略——这是遗留问题在 `/finish` 前唯一的显式可见性
   - 简明扼要，聚焦于「为什么」而非「改了什么」
8. 将相关文件添加到暂存区（优先按文件名添加，避免 `git add -A`）
9. 执行提交，commit message 末尾必须**按当前执行的 Agent** 追加正确的 `Co-authored-by` trailer（详见全局 CLAUDE.md「git 规则」）：
   - CC（Claude Code）执行 → `Co-authored-by: Claude <noreply@anthropic.com>`
   - Codex（OpenAI Codex）执行 → `Co-authored-by: OpenAI Codex <noreply@openai.com>`
   - **判据**：你知道自己是哪个 Agent，据此选身份；**Codex 绝不写 Claude 身份，CC 绝不写 Codex 身份**。
10. 运行 `git status` 确认提交成功
