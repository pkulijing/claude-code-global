# Development Constitution

所有项目都要遵循以下规则。

## 称呼

对话中的 CC 代表 Claude Code

## 核心开发模式

人类开发者与 Coding Agent 合作，分为需求 - 计划 - 执行 - 总结四步

### 开发模式详解

- 需求：结合当前现状，针对一个待解决的问题，给出明确详细的开发需求。人类主导，提供需求内容
- 计划：结合项目现状，分析需求，给出可行的详细计划。Agent 主导，人类 Review，**在 Plan 模式下输出**。
- 执行：按照计划，完成开发。Agent 主导，人类适当干预辅助。**执行前必须先完成 PROMPT.md 和 PLAN.md 的撰写并确认，再开始写代码。**
- 总结：开发完成后，总结开发项，输出总结文档，Agent 主导。包含以下内容：
  - 开发项背景
    - 针对BUG：BUG的表现和影响
    - 针对正向开发：希望解决的问题或实现的功能
  - 实现方案
    - 关键设计
      - 针对BUG：最终发现的关键问题
      - 针对正向开发：设计方案中的关键点（简要概括，详细方案在PLAN.md里）
    - 开发内容概括
    - 额外产物：除核心代码外的额外贡献，如测试用例、调试脚本、样例文件
  - 局限性：当前方案的遗留问题
  - 后续TODO：可以针对上面的遗留问题，也可以是发现的新问题、启发的新方向

### 文档记录规范

基于以上开发模式，每个由人类发起的开发需求，都要在 `docs` 文件夹下做文档记录。具体规范如下：

- **所有文档一律用中文撰写**
- 文件夹名称：用数字前缀+中文描述便于排序（如 `0-初始灵感`、`1-数据收集与清洗`），数字代表开发的轮次，文字简要描述开发内容。
- 文件夹内容：
  - `PROMPT.md`：需求文档，如果人类直接提供了，就直接使用，否则生成一个简要的文档描述。
  - `PLAN.md`：Agent 生成的实现计划
  - `SUMMARY.md`: Agent 生成的开发总结
  - 其他补充文档：如数据库设计、API 设计等后续需要参考的重要信息
  - 如果需要图片等资源辅助，把图片放到 `assets` 文件夹下

## git 规则

- `.gitignore` 按目录拆分：每个目录维护自己的 `.gitignore`，不要把子目录的忽略规则写到根目录的 `.gitignore` 里。
- commit message 要求：
  - 使用中文，除非明确要求用英文
  - 内容遵循 semantic commit message 规则
  - 由 AI 协助完成的提交，commit message 末尾必须包含 `Co-authored-by` trailer，例如：

  ```
  Co-authored-by: Claude Sonnet <noreply@anthropic.com>
  ```

## 环境变量管理

- 项目依赖环境变量时，统一在项目根目录下创建两个文件：
  - `.env.local`: 保存真实的环境变量，需要添加到 gitignore 中
  - `.env.example`: 示例，对于敏感变量（如密钥、api key），只包含占位符；对于非敏感变量，可以给推荐值，commit 到 git 上，**不得包含密钥、api key等敏感信息**。示例：

  ```bash
  DEEPSEEK_API_KEY=your_deepseek_api_key
  DEEPSEEK_BASEURL=https://api.deepseek.com
  ```

## Python 开发规则

- 使用 uv 管理项目依赖，使用 `uv add` 添加依赖，在 `pyproject.toml` 中记录 (`uv add` 天然支持) 依赖列表，**禁止使用 `pip install` 或 `uv pip install`**
- 使用 `uv run` 运行 python 脚本，如 `uv run some_script.py`, `uv run python -m ruff xxxx`，**禁止直接调用 python 或 python3**
- 使用 ruff 做代码格式化和 python 语法检查
- pypi index指南：为了提高中国的下载速度，我们使用两个指定的源
  - 普通库从[清华源](https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple)下载
  - `torch/torchaudio/torchvision` 等 `torch` 相关的库从[aliyun镜像站]( https://mirrors.aliyun.com/pytorch-wheels/cu121/) 下载. 你这个进程并不是一个完整的pypi源，需要使用 `extra` 方式在 `pyproject.toml` 中指定
  - `torch` 使用 2.5.1 版本，cu121
