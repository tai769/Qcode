# Qcode 当前架构总览

这份文档只描述 **当前已经落地到仓库里的真实架构**，不混入未来设想。

## 1. 先给结论

Qcode 现在已经不是“一个把 prompt 丢给模型然后等结果”的小脚本了，而是一套 **CLI-first、本地工作区优先、SSE 流式驱动、支持工具调用、支持团队协作、支持上下文压缩** 的 agent runtime。

它当前的核心形态是：

- 一个本地 CLI 入口：`qoder` / `qcode`
- 一个可复用的运行时内核：`Harness + Runtime + Provider + Tooling + Team/Task`
- 一个 **history replay** 会话模型：每轮把会话消息重新发给模型，而不是依赖 provider 的服务端会话状态
- 一个 **SSE-first** 的 provider 层：模型流式事件先标准化，再由引擎消费
- 一个 **工具编排层**：支持模型输出工具调用、执行工具、把结果回灌给下一轮
- 一个 **上下文治理层**：通过 `ContextBudgeter + Compaction` 避免长对话失控
- 一个 **团队协作层**：支持 lead、teammate、任务图、收件箱、审批协议

换句话说，现在的 Qcode 更像一个 **可演进的 agent runtime 内核**，而不只是一个聊天 CLI。

---

## 2. 当前分层

## 2.1 入口层

### `qoder`

你现在实际使用的快捷入口是：

- `qoder`

它会优先走虚拟环境里的 `qcode` 可执行文件；如果没有，再退回 Python 入口。

相关文件：

- `qoder`
- `agent_loop.py`
- `qcode/harness/cli.py`

### 这层解决什么问题

- 让你不用每次手敲 `./.venv/bin/qcode --workdir ...`
- 固定工作区根目录
- 提供一个统一 CLI 交互面

### 当前局限

- 还没有 Web 前端
- 还没有 app server / browser UI
- 还是终端优先，而不是多客户端优先

---

## 2.2 装配层（Composition Root）

Qcode 的真实装配中心在：

- `qcode/app.py`

这一层负责把下面这些东西组装起来：

- provider
- engine
- middleware
- compactor
- budgeter
- background manager
- task graph
- message bus
- protocol manager
- teammate manager
- tool registry
- CLI harness

### 这层解决什么问题

如果没有装配层，CLI、未来 Web、子代理、队友代理都会各自 new 一堆对象，最后系统会散掉。现在 `app.py` 让整个系统至少有了一个统一的装配中心。

### 当前优点

- CLI 和子代理共享同一套 runtime 设计
- 后续做 Web API 时能继续复用
- provider / middleware / team / task 都是可插拔的

### 当前缺点

- 目前还没有继续抽成 `build_runtime_services()` 这种更稳定的 service graph
- Web 层还没建起来，所以复用能力还没完全兑现

---

## 2.3 Harness 层

当前主要是 CLI harness：

- `qcode/harness/cli.py`

它做三件事：

- 维护交互式命令行循环
- 处理 slash commands，比如 `/help`、`/team`、`/tasks`、`/protocols`
- 接收 engine 的流式事件和 runtime telemetry，把它显示给用户

### 最近刚补上的能力

CLI 现在不再是“安静地卡住，最后突然吐出答案”，而是会显示真实工作状态：

- `思考中`
- `请求模型`
- `模型已接入，等待输出`
- `准备调用工具 xxx`
- `运行工具 xxx`
- `压缩长对话上下文`

这意味着 CLI 现在终于具备了最基础的 **可观察性**。

### 这层解决什么问题

- 人机交互
- slash command 控制面
- 输出呈现
- 用户对“它是不是卡住了”的感知问题

### 当前局限

- 还是轻量 CLI 展示，不是完整 TUI
- 没有左中右面板
- 没有任务看板可视化
- 没有 token 级高级渲染策略

---

## 2.4 Runtime 核心层

这是现在最关键的一层。

核心文件：

- `qcode/runtime/engine.py`
- `qcode/runtime/session.py`
- `qcode/runtime/middleware.py`
- `qcode/runtime/tool_executor.py`

### 核心对象

#### `ConversationSession`

负责保存：

- 当前 messages
- 当前 session_id
- todo manager
- compaction 请求
- stop 请求
- idle poll 请求
- 最近一次 response_id（仅记录，不再依赖服务端 continuation）

#### `AgentEngine`

引擎是调度器。它的职责是：

1. 在每轮模型调用前执行 middleware
2. 调用 provider 获取 **流式 ResponseEvent**
3. 一边消费事件，一边累积文本 / 工具调用
4. 如果模型要求工具调用，则执行工具
5. 把工具结果回写到 session
6. 继续下一轮，直到模型不再要求工具

#### `StreamingToolExecutor`

这层不是“多余复杂度”，而是为了把工具调用从“整包 message 后处理”升级为“基于流式事件的可靠编排”。

它负责：

- 观察 `TOOL_CALL_DELTA / TOOL_CALL_DONE`
- 累积工具参数
- 在参数完整后提交执行
- 保证 turn 结束时工具结果按稳定顺序回灌
- 异常中断时 drain 已启动的工具，避免半套协议

### 当前 runtime 的真实运行方式

#### 单轮大致流程

1. 用户输入进入 `ConversationSession`
2. middleware 先运行
3. provider 开始 SSE 流
4. provider 输出统一的 `ResponseEvent`
5. engine 消费事件，更新 `ResponseAccumulator`
6. 如果有工具调用，`StreamingToolExecutor` 负责执行
7. 工具结果作为 `tool` message 进入 session
8. engine 再发下一轮，直到模型完成

### 这层解决什么问题

- 模型流和工具执行解耦
- provider 和 runtime 解耦
- 多轮工具调用闭环
- 中断时尽量不丢状态

### 当前优点

- 已经从“整包 JSON 直连引擎”升级到“事件流驱动引擎”
- 已经具备 Claude Code 风格的一部分流式工具编排思想
- runtime 主链已经能承载后续 Web / TUI / resident harness

### 当前缺点

- 还没有真正做到边收边在 UI 层富交互显示工具进度
- 还没有更细粒度的 turn state machine 可视化
- 没有 durable execution journal

---

## 2.5 Provider 层

当前 provider 选择器在：

- `qcode/providers/factory.py`

支持两条线：

- `responses`：`qcode/providers/responses_compatible.py`
- `chat_completions`：`qcode/providers/openai_compatible.py`

但从现在的架构收敛来看，系统核心已经转向：

- **history replay + SSE-first**
- 不再依赖 `previous_response_id` 这类 provider continuation 能力

### 关键设计

provider 不再直接返回“拼好的 assistant message”，而是返回统一事件：

- `CREATED`
- `OUTPUT_TEXT_DELTA`
- `OUTPUT_TEXT_DONE`
- `REASONING_DELTA`
- `TOOL_CALL_DELTA`
- `TOOL_CALL_DONE`
- `COMPLETED`
- `ERROR`

事件协议定义在：

- `qcode/providers/base.py`

SSE 解析集中在：

- `qcode/providers/sse.py`

### 这层解决什么问题

- 不同 provider 的协议差异被收束成统一内部事件模型
- 解决了“上游返回 SSE，但下游按 JSON 解析”的错位问题
- 为 CLI 流式显示和工具编排提供统一入口

### 当前优点

- provider contract 更硬，不再靠模糊兼容蒙混过关
- SSE 和 JSON 回包都能处理
- 对错误流、未知事件、非标准 body 的容忍度更高

### 当前缺点

- 仍然是本地 requests + 轻量 provider 适配，不是完整 provider SDK 框架
- 对不同供应商的 Responses 方言兼容仍有边界
- 没有统一 provider capability negotiation

---

## 2.6 上下文治理层

相关文件：

- `qcode/runtime/context_budgeter.py`
- `qcode/runtime/compaction.py`
- `qcode/runtime/compaction_middleware.py`

### 当前设计是两段式

#### 第一段：`ContextBudgeter`

它只负责算账，不负责压缩。

输入：

- 最大上下文窗口
- system prompt 预算
- 当前 messages token 估算
- 目标使用比例
- safety margin

输出：

- 要不要压缩
- 可用消息预算是多少
- 摘要预算是多少
- 最近原文预算是多少

#### 第二段：`ConversationCompactor`

它负责执行压缩：

- 保存 transcript
- 摘要旧消息
- 保留最近原文锚点
- 对 tool result 做 micro compaction
- 必要时对最终消息集做 budget fit

### 这层解决什么问题

- 长对话不至于静默失忆
- 不再依赖固定“保留最近 3 轮”这种死阈值
- 压缩不是全删，而是“摘要 + 最近原文锚点”

### 当前优点

- 比最早那种“超了就粗暴砍消息”要强很多
- 预算决策和压缩执行职责分离了
- 已经修复 assistant/tool 配对被拆散的问题

### 当前缺点

- 还是近似 token 估算，不是真 tokenizer
- 还没有结构化 memory store
- 还没有“用户偏好 / 架构决策 / 长期规则”这种持久记忆层

---

## 2.7 工具层

相关文件：

- `qcode/tools/builtin_tools.py`
- `qcode/tools/task_graph_tools.py`
- `qcode/tools/team_tools.py`
- `qcode/tools/task_tool.py`

### 当前工具能力大类

- 文件工具：读写编辑
- shell / background 执行
- todo 管理
- 任务图工具
- 团队消息与审批工具
- 子代理工具

### 这层解决什么问题

- 把“模型输出意图”变成“系统执行动作”
- 把任务、团队、后台命令纳入统一工具协议

### 当前优点

- 工具体系已经不只停留在 read/write/bash
- task graph 和 team protocol 已经是系统级能力，而不是 prompt trick

### 当前缺点

- 还没有 MCP 生态接入
- 还没有更强的工具权限模型
- 还没有统一 artifact / binary / image 产物管理

---

## 2.8 团队协作层

相关文件：

- `qcode/runtime/team.py`
- `qcode/runtime/team_protocols.py`
- `qcode/runtime/task_graph.py`
- `qcode/team_defaults.py`

### 当前团队角色

默认团队成员包括：

- `ld` / `tech_lead`
- `pm` / `product_manager`
- `architect`
- `ui_designer`
- `coder`
- `reviewer` / `code_reviewer`
- `tester`

### 当前能力

#### `MessageBus`

基于 JSONL inbox 的消息总线：

- 发消息
- 广播
- drain-on-read 收件箱

#### `TaskGraphManager`

基于 `.tasks` 持久文件的任务图：

- 创建任务
- 更新任务
- 设置 blockedBy
- claim task
- 支持 `requiredRole`

#### `TeammateManager`

支持：

- spawn teammate
- teammate work / idle 生命周期
- 收件箱唤醒
- 自动扫描可认领任务
- 根据角色自动 claim lane 内任务
- compression 后 identity re-injection

#### `TeamProtocolManager`

支持：

- plan approval request / response
- shutdown request / response
- 协议请求持久化

### 这层解决什么问题

- 从“单代理”升级到“多角色协作”
- 从“领导手写 prompt 分发任务”升级到“至少部分自治”
- 防止无差别抢单，靠 `requiredRole` 做 lane 约束

### 当前优点

- 你的角色分工已经落库，不只是 prompt 文案
- 任务可以约束角色，不是人人乱抢
- lead、review、test 的协作骨架已经有了

### 当前缺点

- 还没有更高级的队列/调度策略
- 还没有超时降级分配机制
- 还没有 Web 可视任务看板
- 还没有真正的队友绩效/成本/结果追踪

---

## 2.9 持久化层

当前主要是文件系统持久化：

- `.team/config.json`
- `.team/inbox/*.jsonl`
- `.team/protocols/*.json`
- `.tasks/task_*.json`
- `.transcripts/*.jsonl`
- 可选 telemetry JSONL

### 这层解决什么问题

- 系统至少具备了基础持久化，而不全靠内存
- 任务、团队、收件箱、对话压缩档案都能落盘

### 当前优点

- 简单、可读、好调试
- 对本地单机工具很合适

### 当前缺点

- 没有 SQLite / Postgres 级别的查询能力
- 没有统一 state DB
- 没有事件索引和历史回放能力

---

## 3. 当前真实请求路径

你在终端输入一句话后，系统当前的真实路径大致是：

1. `qoder` 启动 CLI
2. CLI 读入用户输入，写进 `ConversationSession`
3. `AgentEngine` 调用 middleware
4. `ContextBudgeter` 决定是否需要 compaction
5. 如需要，`ConversationCompactor` 执行压缩
6. provider 发起 API 请求
7. provider 将 SSE / JSON 统一映射成 `ResponseEvent`
8. engine 消费事件，累积文本、捕获工具调用
9. 如有工具调用，`StreamingToolExecutor` 执行工具
10. 工具结果追加到 session
11. engine 继续下一轮，直到模型完成
12. CLI 把流式内容和状态输出显示出来

---

## 4. 当前系统最重要的架构选择

## 4.1 选择了 `history replay`

这是你当前最关键的架构收敛之一。

为什么重要：

- provider continuation 兼容性太差
- `previous_response_id` 这种能力并不稳定
- 一旦换供应商，很容易炸

现在 Qcode 选择：

- 会话状态自己持有
- 每轮重放消息历史
- provider 只负责生成，不负责“记忆你是谁”

这让 provider contract 明确了很多。

## 4.2 选择了 `SSE-first`

这是第二个关键架构选择。

为什么重要：

- 你当前接的模型接口本身就是流式优先
- 如果内部还按单包 JSON 思维写，就会一直出错

现在 Qcode 的设计是：

- 先把上游流式事件吃对
- 再把它转换成内部统一事件
- engine 消费的是事件流，而不是 provider 的私有格式

## 4.3 选择了“预算治理 + 摘要压缩”

这意味着 Qcode 不再靠“消息越来越长，祈祷别爆”来工作，而是开始有上下文治理能力。

## 4.4 选择了“角色约束自治”而不是“人人抢单”

这解决了最开始你指出的核心问题：

- 自治不是无差别抢任务
- 自治应该是 lane 内自治

现在通过 `requiredRole`，这件事已经开始进入结构化实现。

---

## 5. 当前还不是的东西

很重要的一点：当前 Qcode **还不是** 下面这些东西。

- 不是 Codex 那种成熟 TUI + app server 多端系统
- 不是 Claude Code 那种带成熟 memory / remote bridge / permission UI 的产品化系统
- 不是 OpenClaw 那种常驻型 heartbeat + cron + IM 路由助手
- 不是 Web-first 产品
- 不是完整的可恢复 state machine 平台

它当前的定位更准确地说是：

> 一个已经完成核心 runtime 收敛、具备继续向 TUI / Web / 常驻代理演进能力的本地 agent 内核。

---

## 6. 当前最值得肯定的部分

如果只看已经做成的部分，最有价值的是这几条：

- 从“provider 直出 JSON”升级到了“统一事件模型 + 流式引擎”
- 从“工具结果后处理”升级到了“流式工具编排”
- 从“长对话放任增长”升级到了“预算决策 + 压缩执行”
- 从“无差别自治抢单”升级到了“角色约束任务认领”
- 从“CLI 静默卡死感”升级到了“可见工作状态”

这几条不是表面 patch，而是方向性的架构收敛。

---

## 7. 当前最明显的缺口

如果从产品级系统角度看，你现在最缺的是：

- Web/API 层
- React 前端
- durable state DB
- 更强的权限 / 沙箱 / 审批模型
- 结构化 memory 系统
- 可恢复 session / session list / resume
- 更强的 observability
- 更完整的前端和端到端测试体系

这些不是现在不存在，而是还没进入产品化阶段。

---

## 8. 一句话总结

Qcode 当前的架构，可以一句话概括为：

> **一个 CLI-first、history-replay、SSE-first、支持工具流式编排、带上下文治理和团队协作骨架的本地 agent runtime。**
