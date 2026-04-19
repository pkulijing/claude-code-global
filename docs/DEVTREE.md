# 开发树

> 项目：claude-code-global | 最后更新：2026-04-19 | 共 5 轮

## 分类图例

| 图标 | 类型 | 说明 |
|------|------|------|
| 🌱 | 初建 | 某功能域首次从零建立 |
| ✨ | 功能 | 扩展用户可感知的能力 |
| 🐛 | 修复 | 纠正缺陷或回归 |
| 🏗️ | 重构 | 内部结构改善，用户行为不变 |
| 📦 | 工程 | 打包/CI/分发/工具链 |
| 🔬 | 探索 | 调研，可能被搁置 |

## 可视化

```mermaid
graph TD
  classDef genesis  fill:#d4edda,stroke:#28a745,color:#155724
  classDef feature  fill:#cce5ff,stroke:#0d6efd,color:#003d8f
  classDef bugfix   fill:#f8d7da,stroke:#dc3545,color:#721c24
  classDef refactor fill:#fff3cd,stroke:#ffc107,color:#664d03
  classDef infra    fill:#e2d9f3,stroke:#6f42c1,color:#3d1a78
  classDef research fill:#e2e3e5,stroke:#6c757d,color:#383d41

  N0["🌱 0 · 安装脚本"]:::genesis
  N1["✨ 1 · 创建commit-skill"]:::feature
  N2["🏗️ 2 · 重构项目CLAUDE文件结构"]:::refactor
  N3["✨ 3 · 创建rebase-skill"]:::feature
  N4["✨ 4 · 创建devtree-skill"]:::feature

  N0 --> N1
  N0 --> N2
  N1 --> N3
  N1 --> N4
```

## 节点索引

| # | 名称 | 类型 | 父节点 | 一句话描述 |
|---|------|------|--------|-----------|
| 0 | 安装脚本 | 🌱 初建 | — | 通过符号链接将 CLAUDE.md 与 skills 部署到 ~/.claude/ |
| 1 | 创建commit-skill | ✨ 功能 | 0 | 创建 /commit skill，补全 /finish 流程的最后一环 |
| 2 | 重构项目CLAUDE文件结构 | 🏗️ 重构 | 0 | 分离全局规范与项目说明，解决 CLAUDE.md 语义错位 |
| 3 | 创建rebase-skill | ✨ 功能 | 1 | 创建 /rebase skill，诊断+分段引导本地分叉整理 |
| 4 | 创建devtree-skill | ✨ 功能 | 1 | 创建 /devtree skill，可视化开发树并集成到 /finish 流程 |
