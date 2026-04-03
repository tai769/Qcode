# Subagent Harness Explained

这份文档解释 `task -> subagent` 这一层为什么重要，以及它在当前工程结构里落在哪。

## 核心问题

Agent 工作越久，主 `messages` 会越来越臃肿。

例如一个简单问题：

- 这个项目用什么测试框架？

模型可能需要：

- 读多个配置文件
- 搜仓库内容
- 看文档和脚本

但父 Agent 最后真正需要记住的，可能只有一个词：

- `pytest`

所以更合理的做法是：

- 父 Agent 发起一个 `task`
- 子 Agent 在 fresh context 里完成探索
- 子 Agent 只返回摘要
- 子 Agent 的中间上下文被丢弃

## 思想本质

`task` 看起来像一个工具，但它的本质是 **runtime orchestration entrypoint**。

- 在接口层，它是一个 tool
- 在系统层，它是在启动一个 child agent session

所以它天然跨了两层：

- Tool 层：暴露 `task` 这个能力给模型
- Runtime 层：真正执行 subagent 会话和 fresh-context 隔离

## 当前工程中的落点

- `qcode/tools/task_tool.py`：定义 `task` 工具 schema 与 handler
- `qcode/runtime/subagent.py`：运行 child agent，并只返回 summary
- `qcode/app.py`：组装 parent engine 与 child engine

## 当前实现如何工作

### Parent

Parent 拥有完整工具集：

- `bash`
- `read_file`
- `write_file`
- `edit_file`
- `todo`
- `task`

### Child

Child 拥有基础工具，但没有 `task`：

- `bash`
- `read_file`
- `write_file`
- `edit_file`
- `todo`

这样可以避免无限递归委托。

## 为什么它有价值

- 降低主上下文污染
- 保持 parent agent 聚焦决策和汇总
- 让 child agent 承担局部搜索、阅读和探索任务
- 为未来的多代理协作打基础

## 运行流程

1. Parent agent 收到用户任务
2. Parent model 决定调用 `task`
3. `task` handler 调用 `SubagentRunner`
4. `SubagentRunner` 创建 fresh `ConversationSession`
5. Child engine 在自己的上下文里跑工具循环
6. Child 返回最后的 assistant summary
7. Parent 只收到 summary，不接收 child 全量上下文
