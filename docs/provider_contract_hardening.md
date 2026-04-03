# Provider Contract Hardening

这次改造解决的不是“换一个 API 地址”这么简单的问题，而是把 Qcode 的模型接入层从“拿一坨 JSON 然后猜”升级为“基于流事件的正式协议层”。

补充一条原则：**供应商契约缺失默认按 bug / 不兼容处理，而不是静默兼容。**

当前 Qcode 已经收敛到一条主线：

- 会话策略采用 `history replay`
- 传输协议优先按 `SSE` 事件流处理
- 不再依赖 `previous_response_id` 这类 provider-managed thread 机制

也就是说，Qcode 现在借鉴的是 Claude Code 路线：**客户端自己管理连续性，provider 只负责稳定输出流事件。**

## 1. 问题到底是什么

Qcode 之前的路径更像这样：

`HTTP 请求 -> 尝试解析成单个 JSON -> 拼成 assistant message -> Engine 再看要不要执行工具`

这个路径对传统非流式接口够用，但对现代模型接口会有三个问题：

1. 很多供应商实际上返回的是 `SSE`，不是单个 JSON。
2. 现代模型接口普遍返回的是事件流，文本、工具调用、完成信号并不是同一种东西。
3. 流式文本、工具调用、完成事件、错误事件，本来就是不同阶段，不能被揉成一个“字符串响应”。

所以真正要修的不是“JSON 解析器”，而是 **Provider Contract**。

## 2. JSON 和 SSE 是什么关系

- `JSON`：数据格式。
- `SSE`：服务器推送事件的传输协议。

现代模型接口常见形态不是二选一，而是：

`SSE stream` 里连续发很多条 `JSON event`

比如：

- 一条 `created`
- 很多条 `output_text_delta`
- 若干条 `tool_call_delta`
- 一条 `completed`

所以你之前遇到的现象，不是“我做成 JSON 了，所以和 SSE 冲突”，而是：

- 上游在用 `SSE`
- 旧实现试图把它按“单个 JSON 响应”去理解
- 于是长对话、中文编码、工具续接、错误恢复这些地方都容易出边角问题

## 3. 这次改成了什么

### 统一事件模型

Provider 不再优先返回“拼好的 assistant message”，而是先产出统一的 `ResponseEvent`：

- `created`
- `output_text_delta`
- `reasoning_delta`
- `tool_call_delta`
- `tool_call_done`
- `completed`
- `error`

这一层的意义是：无论上游是 `responses` 还是 `chat/completions`，进入 Runtime 之前都先变成同一种内部语言。

### 响应状态管理

`ConversationSession` 仍然会记录最近一次 `response_id`，但现在它主要用于：

- 诊断和日志
- transcript / 审计
- 后续可能的调试关联

而不是作为主会话续接机制。

当前真正承担连续性的，是客户端维护的消息历史、任务状态、用户画像和后续的 compaction 结果。

### 工具执行解耦

`runtime/engine.py` 现在只做两件事：

1. 消费 provider 事件流
2. 在一轮 `completed` 后，把完成的 tool calls 交给 `runtime/tool_executor.py`

这意味着：

- 传输协议逻辑在 Provider
- 会话状态在 Engine / Session
- 工具执行逻辑在 Tool Executor

这就是借鉴 Codex / Claude Code 的核心方向：**流协议和工具执行必须解耦**。

Qcode 现在进一步引入了 `StreamingToolExecutor`：

- provider 只负责把 `tool_call_delta` / `tool_call_done` 事件吐出来
- `StreamingToolExecutor` 负责累积参数、去重、按顺序提交工具执行、并在 turn 结束后按稳定顺序产出 `tool_result`

这一步的目的不是“炫技并发”，而是把“模型在流里说了什么”与“本地工具何时、如何执行”拆成两个独立关注点。

### CLI 流式打印

主 CLI 现在会在收到 `output_text_delta` 时直接打印文本。

但工具输出仍然保持块级展示，这样不会把：

- 模型 token 流
- 工具日志
- 错误输出

混成一团。

## 4. 为什么这一步重要

如果没有这层 Provider Contract Hardening，后面很多能力都会很脆弱：

- 长对话续接
- 多轮工具调用
- 上下文压缩后的恢复
- teammate / subagent 的稳定性
- 未来 Web UI 的真流式展示

也就是说，**SSE 不是一个显示层小功能，而是后续架构的底座。**

## 5. 还没做什么

这次先完成的是 P0：

- 统一事件模型
- response_id 状态管理
- Provider SSE-first
- Tool Executor 解耦
- CLI 主通道流式打印

还没做完的是更强健的 P2 风格流式工具编排：

- abort 时 drain 剩余工具结果
- 旧流结果丢弃
- 多工具并发结果排序控制
- 更细粒度的工具进度事件

这一层更接近 Claude Code 的 `StreamingToolExecutor` 完整语义，可以在你确认要做 Web UI / 更复杂流控时继续补强。

## 6. 如果要升级成常驻助手，还缺什么

你前面提到的主动常驻助手，和这次改造是上下游关系：

- 这次改的是 **模型协议底座**
- 常驻助手改的是 **Harness 生命周期**

要从“临时会话”升级到“常驻助手”，建议按下面几层继续加：

### Heartbeat

Harness 定时给 agent 一个心跳事件，比如每 30 秒：

- 看 inbox 有没有新消息
- 看任务板有没有新任务
- 看 cron 有没有到点事项

### Cron

让 agent 可以登记未来任务，例如：

- 10 分钟后提醒我复查部署
- 今天晚上 8 点跑回归

### Resident Memory

不是只有对话压缩摘要，而是：

- 用户偏好
- 项目长期事实
- 尚未完成的承诺
- 角色人格设定

这些要放进持久记忆，而不是只留在当前会话里。

### IM / Web Channel Router

把同一个 agent core 接到：

- CLI
- Web UI
- Telegram / Discord / Slack

不同通道只决定输入输出方式，不改变 agent 内核。

### Soul / Persona

把长期稳定的行为准则单独配置，而不是塞在某一轮 prompt 里。

例如你的偏好：

- 可以接受大重构
- 倾向激进风格
- 做架构变更前先给出方案和利弊

这类内容未来更适合进入持久 Persona / Memory，而不是依赖当前上下文没被压缩掉。

## 7. 推荐的下一步顺序

如果继续往前走，我建议：

1. 先把当前 SSE-first Provider 跑稳
2. 再补 fixture 级流协议回归测试
3. 然后做 Web API / Web UI
4. 最后再上 heartbeat / cron / resident memory

原因很简单：如果协议底层还不稳，常驻助手只会把不稳定放大成“长期在线地不稳定”。
