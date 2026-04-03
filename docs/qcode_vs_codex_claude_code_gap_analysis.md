# Qcode 对比 Codex CLI 与 Claude Code：架构设计、优缺点与缺口分析

这份文档不是泛泛而谈，而是基于你本机可读到的项目资料做出的对比整理：

- `Qcode`：当前工作区实现
- `Codex CLI`：`/Users/qiushui/Documents/openCode/codex-main`
- `Claude Code`：`/Users/qiushui/Documents/openCode/claude-code/restored-src`

目标不是说谁更强，而是明确三件事：

1. 它们分别在解决什么问题
2. 你的 Qcode 现在已经走到哪里
3. 你距离成熟产品级系统还缺什么

---

## 1. 先给结论

### Qcode 当前最像什么

Qcode 现在最像：

- 一个 **正在从教学/实验 harness 向产品化 runtime 收敛** 的系统

### Codex CLI 更像什么

Codex CLI 更像：

- 一个 **本地优先、工程化成熟、TUI / app server / approvals / sandbox / state DB 完整化** 的产品级 agent 平台

### Claude Code 更像什么

Claude Code 更像：

- 一个 **会话体验、历史、记忆、远程桥接、权限交互、用户工作流打磨得更深** 的产品级 coding assistant

### 你现在最缺什么

一句话说：

> **Qcode 的 runtime 核心已经收敛得不错，但产品外壳、状态基础设施、权限系统、前端界面、长期记忆体系还远不够。**

---

## 2. 对比维度总表

| 维度 | Qcode 当前 | Codex CLI | Claude Code | Qcode 还缺什么 |
| --- | --- | --- | --- | --- |
| 会话模型 | history replay | 更成熟的状态与多客户端能力 | 历史与会话体验成熟 | durable session / resume |
| 流式协议 | SSE-first 已做 | 更完整流式/TUI管线 | 更完整消息适配/远程流 | 更丰富 UI streaming |
| 工具执行 | StreamingToolExecutor 已有骨架 | 工程化更成熟，exec/server 体系强 | tool/result 与权限桥成熟 | 更强的并发、回放、产物管理 |
| 权限/审批 | 只有 CLI harness 级别 | 完整 approval + sandbox | 完整 permission flow | 真正的权限系统 |
| 状态持久化 | 文件为主 | SQLite state DB | 历史/会话/记忆更成熟 | durable DB |
| 记忆能力 | compaction + identity re-injection | 有状态基础设施 | memory 系统成熟 | 结构化 memory |
| UI/交互 | 轻量 CLI | 成熟 TUI + app server | 成熟 CLI/bridge/remote | React 前端 / Web |
| 多代理/团队 | 已有 team/task 骨架 | 更偏单主代理 + 工具生态 | 更偏单代理 + remote/session | 更强调度与可视化 |
| 生态接入 | 本地工具为主 | MCP / connectors / app support | remote / skills / memory 生态 | MCP / integrations |
| 可观测性 | JSONL telemetry + CLI 状态 | tracing / logs / stream chunking | analytics / state / UI bridge | 可视化观测面板 |

---

## 3. Codex CLI 在解决什么问题

从你本机可读到的 Codex 项目来看，它不是只想做“一个能聊天的 CLI”，而是在解决 **产品级本地 agent 平台** 这件事。

## 3.1 多界面与多运行面

Codex 同时在做：

- CLI / TUI
- app server
- 非交互 exec 模式

这意味着它不把“终端聊天”当成唯一运行形态。

### 它解决的问题

- 一个内核，多种交互面
- CLI、TUI、app 都能共享能力

### Qcode 当前差距

- 你现在只有 CLI harness
- 还没有 app server
- 还没有 Web 前端

---

## 3.2 强权限与强沙箱模型

Codex 非常重视：

- approval policy
- sandbox mode
- managed requirements
- tool approval overrides

### 它解决的问题

- 工具型 agent 不能只会干活，还必须可控
- 在不同运行环境下，需要不同权限边界

### Qcode 当前情况

Qcode 目前更像：

- 一个能跑的 agent harness
- 不是一个权限系统完整的产品

### 你缺什么

- 统一 approval policy 模型
- 真正的 sandbox 抽象
- per-tool / per-surface 权限控制

---

## 3.3 状态数据库与持久状态基础设施

Codex 有：

- SQLite state DB
- state runtime
- rollout / thread / graph / log 等状态模型

### 它解决的问题

- 会话不是只存在内存里
- 日志、线程、任务、状态可以持久化、查询、恢复

### Qcode 当前情况

Qcode 现在是：

- `.tasks` JSON
- `.team` JSON / JSONL
- `.transcripts` JSONL
- telemetry JSONL

这套很适合原型和单机开发，但不适合产品级状态管理。

### 你缺什么

- state DB
- 查询层
- 持久 session index
- 更强恢复能力

---

## 3.4 TUI 流式渲染与显示策略

Codex 很明显在认真解决：

- 流式输出太快时 UI 如何不抖、不积压、不乱序

你本机的文档里已经能看到：

- `TUI Stream Chunking`
- catch-up / smooth 模式
- commit tick / queue age / hysteresis

### 它解决的问题

- 模型输出速度和终端显示速度不匹配
- 如果不做 chunking，用户看到的会非常糟糕

### Qcode 当前情况

你现在只做到了：

- 能正确流式显示
- 能显示“正在干什么”

但还没有：

- 自适应 chunking
- backlog 策略
- 多区域渲染控制

### 你缺什么

- 更成熟的前端 / TUI streaming render policy

---

## 3.5 app server / websocket / 多客户端架构

Codex 有明确的 app server 和 websocket 相关结构。

### 它解决的问题

- 不只是一个本地 REPL
- 还可以成为远端 UI / app / IDE 的服务端内核

### Qcode 当前情况

Qcode 目前还没有：

- Web server
- session API
- websocket / SSE chat endpoint
- browser 客户端

### 你缺什么

- API surface
- session router
- 前后端分离的服务层

---

## 3.6 工程化基础设施

Codex 明显更完整的地方包括：

- tracing
- install path
- binary distribution
- config schema
- requirements / constraints
- 多平台打包

### 它解决的问题

- 产品真正可安装、可发布、可维护

### Qcode 当前差距

- 还在项目级本地工具阶段
- 还没有产品发布面的成熟基础设施

---

## 4. Claude Code 在解决什么问题

Claude Code 的重点和 Codex 不完全一样。

Codex 更像“平台化、本地 agent 工程系统”；
Claude Code 更像“会话体验、权限交互、远程桥接、记忆与日常工作流极强”的 assistant 产品。

## 4.1 历史与会话体验

Claude Code 的 `history.ts` 明显不是随便写的。它处理的是：

- 全局历史
- 项目维度历史
- pasted content 引用
- 并发 session 之间的历史污染问题
- 当前 session 与历史搜索体验

### 它解决的问题

- 用户和 assistant 的日常交互体验
- 多 session 并存时的历史管理

### Qcode 当前情况

Qcode 有 `ConversationSession`，但它更偏 runtime state，不是成熟的历史产品层。

### 你缺什么

- prompt history
- history search
- persisted session catalog
- 当前项目 / 全局历史的分层机制

---

## 4.2 记忆系统（Memory）

Claude Code 明确区分：

- user memory
- feedback memory
- project memory
- reference memory

而且它非常强调：

- 什么该记
- 什么不该记
- memory 可能过期，要验证
- private 与 team scope 区分

### 它解决的问题

- 长期偏好不是靠上下文侥幸留下来
- 用户风格、项目规则、反馈约束可以跨会话保持

### Qcode 当前情况

你现在已经有：

- compaction
- identity re-injection

但这还不等于真正 memory system。

### 你缺什么

- 结构化 memory store
- memory read / write policy
- 用户偏好持久化
- team memory / private memory 区分

这件事和你之前说的“你必须记住我是激进派、支持重构”高度相关。

---

## 4.3 远程会话与权限桥

Claude Code 明显在做：

- remote sessions
- websocket 会话桥接
- permission request / response 桥
- SDK message adapter

### 它解决的问题

- 前后端 / 本地远程 / REPL 与服务端之间的消息协议统一
- 用户可以在 UI 里处理权限请求

### Qcode 当前情况

Qcode 还没有这层。

### 你缺什么

- Web session protocol
- permission bridge
- 远程 UI 与 runtime 的中间协议适配层

---

## 4.4 Compaction 边界可视化

Claude Code 不只是做 compaction，还把 compaction boundary 作为系统事件和 UI 消息处理。

### 它解决的问题

- 压缩不是偷偷发生
- 会话里知道哪里被 compact 过

### Qcode 当前情况

Qcode 现在 compaction 已经做得比原来强很多，但对用户仍然偏“后台发生”。

### 你缺什么

- 面向用户的 compact boundary 展示
- 更清晰的压缩元数据可视化

---

## 4.5 用户交互细节与工作流成熟度

Claude Code 很多复杂度其实不在模型，而在：

- 滚动与 event loop 协调
- 权限提示
- 历史搜索
- 远程消息适配
- setup / onboarding / trust dialog

### 它解决的问题

- 把 agent 变成“每天真能用”的工具

### Qcode 当前差距

你现在更强的是 runtime 内核收敛；
但产品交互打磨深度还远不如 Claude Code。

---

## 5. Qcode 现在已经追上的部分

不能只说差距，Qcode 现在已经追上甚至明确走对方向的地方也有。

## 5.1 统一事件模型

这点你现在方向是对的，而且很关键。

很多原型项目会把 provider 结果直接塞到业务里，后面很难救。Qcode 现在已经把这一层抽开了。

## 5.2 SSE-first 思路

你非常明确地要求：

- 现在模型就是流式优先
- 所以内核就应该围绕 SSE 设计

这个判断是对的，Qcode 现在已经按这个方向收敛。

## 5.3 工具编排从“后处理”升级到了 runtime 一等公民

`StreamingToolExecutor` 的存在说明 Qcode 已经不再把工具调用当作“message 尾巴上的补丁”。

## 5.4 ContextBudgeter + Compaction

这说明你已经开始把“长对话治理”当成一等问题。

## 5.5 多角色团队骨架

Codex 和 Claude Code 都不以“你这种队友分工系统”为主线；Qcode 在这一点上反而有你自己独特的方向。

也就是说：

- 你不是只在追别人
- 你也在走自己特有的团队协作路数

---

## 6. Qcode 目前最缺的东西，按优先级排

下面这份优先级，是从“最影响产品完成度”来排的。

## P0：Web/API 层

没有这层，你就始终只能在 CLI 里验证。

你需要：

- `POST /api/sessions`
- `POST /api/sessions/:id/chat`
- `GET /api/dashboard`
- 可选 `SSE / websocket stream`

## P0：React 前端

没有前端，你现在的“团队、任务、对话、状态”全都只能靠 slash commands 和日志脑补。

你需要：

- React + Vite
- 中央对话区
- 左侧 team/task
- 右侧 protocol/tool/status
- 流式输出和工作状态 UI

## P0：持久 session / 历史

没有这层，就还是“一次进程一个会话”的开发工具，而不是产品。

## P1：结构化 memory

这件事直接关系到：

- 用户偏好记忆
- 项目长期规则
- 你强调的“激进重构风格”持久化

## P1：权限 / 审批 / 沙箱模型

如果后面要把系统开给前端、多人、甚至远程执行，这个迟早要补。

## P1：前端测试与 E2E

现在你已经有 runtime smoke 了，但还没有 browser 级验证。

## P2：state DB

当 team/task/protocol/session/history/memory 都多起来时，JSON 文件会越来越难维护。

## P2：resident assistant 能力

如果你要走 OpenClaw 那条路，才需要补：

- heartbeat
- cron
- always-on runtime

这不是当前 P0，但会是下一阶段的重要方向。

---

## 7. Qcode、Codex、Claude Code 三者的优缺点对照

## 7.1 Qcode

### 优点

- 你现在的 runtime 收敛方向是对的
- SSE-first、history replay、tool orchestration、context governance 都走对了
- 团队协作和任务图是你的特色方向

### 缺点

- 产品外壳不够
- 状态基础设施不够
- 权限体系不够
- UI 不够

## 7.2 Codex CLI

### 优点

- 平台化强
- TUI / app server / state DB / sandbox / approvals 完整
- 工程化程度高

### 缺点

- 相比你的 team/task 协作方向，不是同一重点
- 产品很强，但不等于替你做了“自治团队系统”

## 7.3 Claude Code

### 优点

- 会话体验强
- 历史、记忆、权限桥、远程消息适配成熟
- 很多细节围绕“人每天用”打磨得很深

### 缺点

- 不是围绕你这种 task graph + teammate autonomy 做设计的
- 它强在单助手工作流和产品化交互，不是你的团队骨架方向

---

## 8. 最现实的演进建议

如果你现在要继续推进，我建议不是“继续抽象 provider”，而是：

### 第一阶段

- 保持当前 runtime 内核不乱动
- 增加 Web API
- 增加 React 前端
- 打通前后端全链路

### 第二阶段

- 增加 session/history 持久化
- 增加 memory store
- 增加前端测试 / E2E

### 第三阶段

- 再考虑 state DB
- 再考虑 resident assistant / heartbeat / cron

这条路线最稳。

---

## 9. 一句话总结

Qcode 现在和 Codex CLI、Claude Code 的差距，不是在“会不会调模型”，而是在下面这些产品级基础设施：

- 前端与多客户端
- 权限与审批
- durable state
- 历史与记忆
- 更成熟的交互体验

但 Qcode 已经做对的一点是：

> **你把内核先收敛到了正确方向。**

这意味着后面继续补产品层，是能接得住的；如果内核方向错了，前端做再多都只是漂亮外壳。

---

## 10. 附：如果要加入 OpenClaw 式能力，Qcode 还缺什么

虽然你这次重点问的是 Codex 和 Claude Code，但你前面明确提过 OpenClaw 式常驻助手，所以这里单独补一条：

如果要走 resident assistant 路线，Qcode 还需要：

- heartbeat scheduler
- cron / delayed tasks
- durable inbox / job queue
- resident process supervisor
- IM channel adapters
- memory-first context assembler

这部分当前 **还完全不在主链里**。
