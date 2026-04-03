# Qcode 架构升级技术权衡笔记

这份文档整理了前面几轮对话里提到的各个阶段性技术方案，从 `s02` 到 `s09` 逐步分析：

- 每一轮引入了什么能力
- 它解决了什么问题
- 它的优点是什么
- 它会引入哪些新的复杂度和代价
- 在后期架构升级时需要重点考量什么

这份文档的目的不是简单说“哪个好”，而是帮助后续做工程决策：

> 每一种能力，都是在用新的复杂度换新的能力边界。

---

## 总览表

| 阶段 | 技术主题 | 核心收益 | 主要代价 |
| --- | --- | --- | --- |
| `s02` | Tool Use | 让模型能真正操作外部世界 | 安全、上下文膨胀、工具治理 |
| `s03` | Todo / 进度跟踪 | 让模型显式维护当前计划 | 只适合短期记忆，状态易丢失 |
| `s04` | Subagent / 上下文隔离 | 把局部探索从主上下文剥离 | 多一次模型调用，摘要质量依赖 child |
| `s05` | Skill / 按需知识加载 | 不把全部知识常驻 system prompt | 加载过多 skill 仍会撑爆上下文 |
| `s06` | Context Compaction | 长会话可持续运行 | 摘要有损，压缩策略难调 |
| `s07` | Persistent Task Graph | 任务状态脱离对话、可恢复 | 状态一致性、依赖维护、调度复杂度上升 |
| `s08` | Background Tasks | 长命令不阻塞主 Agent | 并发、通知、结果一致性、可恢复性问题 |
| `s09` | Agent Teams / Mailboxes | 多 Agent 协作与角色分工 | 协调成本、成本暴涨、调试难度激增 |

---

## s02 - Tool Use

### 引入了什么

`s02` 的核心是把模型从“只会说话”升级成“可以调用外部能力”。

典型工具包括：

- `bash`
- `read_file`
- `write_file`
- `edit_file`

### 解决了什么问题

在没有工具前，模型只能：

- 猜代码结构
- 凭上下文推断文件内容
- 无法真正改代码、跑命令、查仓库

引入工具后，模型才真正具备了“操作工作区”的能力。

### 优点

- 把模型从纯对话系统升级成可执行 Agent
- 工具接口统一，后续能力扩展成本低
- 主循环几乎不需要频繁改动，新增工具即可扩能力
- 为后续所有阶段打基础

### 缺点

- 安全风险明显上升，特别是 shell 执行
- 工具结果会迅速膨胀上下文
- 工具设计如果过粗，模型容易误用
- 工具 schema 和实际行为如果不一致，模型会困惑

### 后期架构升级考量

- 工具要分级：高风险、低风险、只读、可写
- 工具执行要有统一审计和 telemetry
- 工具结果要考虑压缩，否则 context 爆炸
- 工具治理最终会演变成权限系统和 policy 系统

---

## s03 - Todo / 进度跟踪

### 引入了什么

`s03` 引入的是：

- `todo` 工具
- `TodoManager`
- reminder 注入逻辑

目标是让模型显式维护“当前计划”和“当前在做什么”。

### 解决了什么问题

单纯工具调用容易让模型：

- 方向丢失
- 多步任务中途漂移
- 做了很多事但没有显式进度状态

Todo 机制让模型在多步任务里至少具备一个“当前工作面板”。

### 优点

- 显著提高多步任务的可见性
- 让用户能看到 Agent 当前计划
- 给 middleware 留下策略插槽，比如 reminder
- 非常适合短流程任务和单次 session 内协作

### 缺点

- 本质上是会话内的短期状态，不天然持久
- 原始版本通常是扁平列表，不能表达依赖图
- context 被压缩后，todo 容易只剩摘要而失真
- 如果模型不自觉维护 todo，系统仍要靠 nag reminder 拉回

### 后期架构升级考量

- Todo 更适合“短期工作记忆”，不适合长期协调状态
- 后续需要和外部持久状态结合，比如任务图
- reminder 应该放到 middleware，而不是掺在工具逻辑里

---

## s04 - Subagent / 上下文隔离

### 引入了什么

`s04` 的核心是：

- `task` 工具
- child agent
- fresh context
- summary-only return

也就是把局部探索交给一个新 session 的 child agent 去做。

### 解决了什么问题

主 Agent 如果自己做所有探索，会导致：

- `messages` 越来越臃肿
- 大量中间过程污染主上下文
- 一些局部搜索信息对主决策价值很低，但成本很高

Subagent 的目标是：

> 让主 Agent 保持“决策脑”，把局部脏活交给 child。

### 优点

- 主上下文更干净
- 局部探索可以独立运行，不污染 parent
- 非常适合 repo exploration、局部分析、信息采样
- 工程上非常容易和当前 runtime harness 对接

### 缺点

- 成本不是消失了，而是转移到了 child session
- 摘要质量高度依赖 child 最后的总结能力
- 如果 child 摘要差，parent 可能拿到不完整结论
- 如果 child 也疯狂调用工具，整体 token 仍可能很高
- 不是进程级隔离，只是 fresh conversation isolation

### 后期架构升级考量

- 需要决定：什么情况该起 subagent，什么情况 parent 自己做
- 子代理工具集最好裁剪，避免无限递归 delegation
- 长期看应当和 compaction、task graph 一起使用

---

## s05 - Skill / 按需知识加载

### 引入了什么

`s05` 引入的是：

- `skills/<name>/SKILL.md`
- `SkillLoader`
- `load_skill` 工具
- system prompt 只放 skill 元数据，正文按需加载

### 解决了什么问题

如果把所有规范、工作流、知识包都塞进 system prompt：

- 每轮请求都会付出全部 token 成本
- 大多数知识与当前任务无关
- system prompt 会越来越胖

Skill 机制的思想是：

> 不把所有知识常驻上下文，而是在需要时临时加载。

### 优点

- 显著降低 system prompt 固定成本
- 技能包结构清晰，易维护、易扩展
- 特别适合团队规范、工作流、代码审查规则等知识类内容
- 可以和工具层统一在 `tool use` 框架下暴露给模型

### 缺点

- 加载过的 skill 仍然会占上下文，并不会自动消失
- skill 太多、skill 正文太长，一样会导致 context 膨胀
- 模型必须先意识到自己需要哪个 skill，才能主动加载
- skill 如果切得太粗，加载一次就很重；切得太细，又容易管理复杂

### 后期架构升级考量

- skill 应该和 compaction 配套使用
- skill 正文未来需要支持摘要化、缓存、卸载策略
- skill 更适合“知识注入”，不适合承载长期状态

---

## s06 - Context Compaction

### 引入了什么

`s06` 引入的是三层上下文压缩：

- `Layer 1`: `micro_compact`
- `Layer 2`: `auto_compact`
- `Layer 3`: 手动 `compact` 工具

并增加：

- transcript 落盘
- continuity summary

### 解决了什么问题

Agent 工作越久：

- 工具输出越来越多
- skill 正文可能加载多次
- subagent 摘要越来越多
- 消息历史迅速膨胀

不压缩，长任务很快就会超窗口、变贵、变慢、变笨。

### 优点

- 长 session 能够继续跑下去
- 旧工具输出可以先微压缩，不必每次都做大摘要
- 大压缩前保留 transcript，便于恢复和审计
- 手动 `compact` 允许模型自己发起整理

### 缺点

- 压缩天然有损，不可能完全无损恢复原上下文
- 摘要质量高度影响后续连续性
- 压缩策略阈值难调，太早压缩会丢细节，太晚压缩又爆 context
- transcript 和 summary 之间的一致性也需要后期治理

### 后期架构升级考量

- compaction 是“记忆治理系统”，不是简单工具
- 要区分：可丢弃内容、可摘要内容、必须外存内容
- 需要和 task graph、skill lifecycle、subagent 策略一起考虑

---

## s07 - Persistent Task Graph

### 引入了什么

`s07` 从扁平 Todo 升级为：

- `.tasks/task_x.json`
- `TaskManager`
- `blockedBy` 依赖图
- `task_create / task_update / task_get / task_list`

它的本质是：

> 把任务状态从对话里搬到磁盘上，并显式建模依赖关系。

### 解决了什么问题

原始 todo 有两个大问题：

- 只是内存中的扁平清单
- 上下文一压缩，状态就容易变形或丢失

任务图系统解决的是：

- 长期状态持久化
- 任务依赖表达
- 并行与阻塞关系建模

### 优点

- 任务状态脱离对话，压缩后仍能保留
- 能表达顺序、并行、依赖、阻塞
- 天然适合作为多 agent 协调的事实源
- 后续 background、team、worktree 等都可以围绕它协调

### 缺点

- 状态一致性和依赖维护复杂度明显上升
- 如果多个执行者同时改任务图，容易出现竞争条件
- 需要定义更严格的状态迁移规则，否则会脏数据
- 简单文件系统 JSON 持久化虽然方便，但不适合高并发和强一致需求

### 后期架构升级考量

- task graph 是 orchestration backbone，很值得保留
- 未来可能要升级到数据库或带锁的持久层
- 需要和 team system、background execution、approval flow 对齐

---

## s08 - Background Tasks

### 引入了什么

`s08` 引入的是：

- `BackgroundManager`
- 后台线程跑长命令
- 通知队列
- `background_run / check_background`
- 在下一轮模型调用前注入 `<background-results>`

### 解决了什么问题

长命令阻塞会导致：

- 主 Agent 只能干等
- 用户要求“顺便再做点别的”时，系统无法并行推进
- 工具执行时间和模型思考时间绑定在一起

Background execution 的目标是：

> 把等待长命令的时间剥离出来，让主 Agent 继续工作。

### 优点

- 长命令不阻塞主 loop
- 能边等边做别的事情
- 允许多个后台命令并行运行
- 非常适合作为后续 worker / scheduler 的前置能力

### 缺点

- 引入并发、线程安全和通知一致性问题
- 结果不是立即推送，而是下一轮前 drain；如果系统停住，通知不会自动打断主流程
- 任务状态默认只存在进程内，不像 task graph 那样天然持久
- 如果后台任务很多，结果注入和日志治理会变复杂
- 如果共享同一工作区，后台进程可能和前台改文件发生冲突

### 后期架构升级考量

- background task 最好和 task graph 联动
- 未来需要 cancel、retry、heartbeat、超时治理
- 如果要更强可靠性，最终会往独立 worker / queue 演进

---

## s09 - Agent Teams / Mailboxes

### 引入了什么

`s09` 引入的是：

- `TeammateManager`
- `MessageBus`
- `.team/config.json`
- `.team/inbox/*.jsonl`
- `spawn_teammate / send_message / read_inbox / broadcast`

它的本质是：

> 让多个有身份的 agent 通过邮箱式消息总线协作。

### 解决了什么问题

`subagent` 是一次性的，`background task` 不会思考。真正的团队协作需要：

- 持久身份
- 生命周期管理
- agent 间通信

这一步开始让系统具备“团队”而不只是“工具”的形态。

### 优点

- 支持角色化分工，例如 `coder`、`tester`、`reviewer`
- lead 可以真正派工、收件、广播、调度队友
- 多 agent 协作模型比单 agent 能力边界更高
- 是未来 team orchestration、审批链、协同开发的基础

### 缺点

- 协调成本急剧上升，这是最大的代价
- token 和总成本会成倍增加，因为多个 agent 都在推理
- 信息会重复加载，整体上下文成本可能不降反升
- 当前实现只是“持久身份”，不是“持久认知”；线程结束后 private messages 仍会消失
- mailbox 是 drain-on-read，可靠性弱，存在消息丢失风险
- 多线程共享同一工作区，很容易互相覆盖和冲突
- 调试、回放、评估都比单 agent 难很多

### 后期架构升级考量

- team system 必须和 task graph 结合，否则很容易混乱
- 需要更强的消息可靠性、状态锁、角色权限和工作区隔离
- 长远看会向 actor runtime、scheduler、distributed workers 演进

---

## 这些技术之间的关系

这些阶段不是互相替代，而是逐层叠加：

- `Tool Use`：让模型能真正操作外部世界
- `Todo`：让模型有短期工作面板
- `Subagent`：让局部探索从主上下文剥离
- `Skill`：让知识按需注入，不常驻 system prompt
- `Compaction`：让长 session 能继续活下去
- `Task Graph`：让任务状态脱离对话、持久存在
- `Background Tasks`：让长命令可以时间并行
- `Agent Teams`：让多个有身份的 agent 协作

可以把它们统一理解为四种治理方向：

- **能力治理**：Tool Use / Skill
- **记忆治理**：Todo / Compaction
- **状态治理**：Task Graph
- **并行治理**：Subagent / Background / Teams

---

## 后期架构升级最需要谨慎的地方

### 1. 不是功能越多越好

每一轮引入的新能力，都会带来：

- 新状态
- 新上下文来源
- 新同步问题
- 新调试成本

所以升级不能只看“能不能做”，还要看“值不值得背这份复杂度”。

### 2. 上下文不是长期数据库

很多能力最终都在提醒同一个事实：

> 模型上下文应该只承载当前高价值工作记忆，而不是长期事实源。

长期状态应该逐步外置化：

- 技能在 `skills/`
- 任务在 `.tasks/`
- transcript 在 `.transcripts/`
- 团队状态在 `.team/`

### 3. 多 Agent 不是免费增益

多 agent 带来的不是“自动更聪明”，而是：

- 更强能力边界
- 更高协调成本
- 更复杂的调度问题

所以只有当任务确实需要分工、并行、角色化时，多 agent 才值得。

### 4. 任务图会成为后续骨架

越往后，越应该让更多机制围绕 `Task Graph` 协调，而不是靠聊天消息猜测当前状态。

未来合理的方向是：

- `Todo` 负责短期工作记忆
- `Task Graph` 负责长期事实状态
- `Background` 负责执行
- `Teams` 负责协作
- `Compaction` 负责记忆治理

---

## 当前对 Qcode 的启发

如果把这些经验映射到 `Qcode` 后续演进，比较合理的路线是：

1. 先把 runtime harness 打稳：`tools + todo + subagent + compaction`
2. 再引入持久任务图，作为外部协调骨架
3. 然后把 background task 绑定到任务图，而不是孤立存在
4. 最后再考虑 team system，把多 agent 建在任务图和消息治理之上

换句话说：

> 越往后，越不能只靠“对话里大家商量”，而要依赖外部状态系统来稳定整个架构。

---

## 最终结论

这些阶段共同说明了一件事：

> Agent 架构升级，本质上是在不断把“临时、隐式、全塞上下文”的东西，重构为“外置、显式、可治理”的系统结构。

每一轮升级都更强，但也都更重。

真正需要工程判断的地方，不是“能不能做”，而是：

- 这项能力解决的是不是当前的主要瓶颈？
- 它引入的新复杂度能不能被后续架构承接？
- 它应该留在对话里，还是应该被外置成状态系统或服务？

这才是后期架构升级最值得持续考量的地方。
