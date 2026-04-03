# Context Compaction Explained

这份文档解释当前项目里的三层上下文压缩机制。

## 为什么需要 compaction

Agent 的上下文窗口是有限的，而工具输出非常容易膨胀：

- 读取大文件
- 搜索多个目录
- 跑测试与命令日志

如果所有历史都永久保留，主 `messages` 很快会失控。

## 三层机制

### Layer 1: `micro_compact`

- 每轮模型调用前静默执行
- 把较旧的工具输出替换成短占位符
- 默认保留最近几条工具结果
- 默认保留 `read_file` 结果，因为它往往是引用材料

### Layer 2: `auto_compact`

- 当上下文估算 token 超过阈值时自动触发
- 先把完整 transcript 写入 `.transcripts/`
- 再调用 LLM 生成 continuity summary
- 最后用“summary + 最近几轮原文锚点”替换大段历史，而不是只剩一句摘要

现在这层前面多了一步 `ContextBudgeter`：

- 它只负责算账，不负责看消息语义
- 输入包括：上下文窗口、system prompt 估算、当前消息 token、目标比例和安全余量
- 输出包括：要不要压缩、摘要预算、最近原文预算

补充几个关键参数：

- `QCODE_MAX_CONTEXT_WINDOW`：Budgeter 的上下文总窗口
- `QCODE_CONTEXT_TARGET_RATIO`：最多使用窗口的多少比例
- `QCODE_CONTEXT_SAFETY_MARGIN_TOKENS`：安全余量
- `QCODE_COMPACTION_SUMMARY_RATIO`：压缩预算里分给 summary 的比例

`QCODE_COMPACTION_TOKEN_THRESHOLD` 仍然保留在配置里，但不再是自动触发的主裁决器。

### Layer 3: `compact` tool

- 模型可以主动调用 `compact`
- Runtime 会在下一次模型调用前执行完整压缩
- 适合模型自己判断“上下文太乱，需要整理”时使用

## 当前工程中的落点

- `qcode/runtime/compaction.py`：压缩服务本体
- `qcode/runtime/compaction_middleware.py`：自动触发入口
- `qcode/tools/builtin_tools.py`：`compact` 工具接口
- `qcode/app.py`：把 compaction 组装进 parent 与 child runtime

## 设计意图

这套机制的目的不是“记住一切”，而是：

- 保留最近的细节
- 保留长期连续性的摘要
- 把完整原文归档到磁盘，便于恢复与审计

换句话说，它是在给 agent 增加一套记忆管理系统。
