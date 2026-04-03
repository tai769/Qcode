# Verification Loop Protocol

这份文档说明 Qcode 新加的 `verification loop` 是在解决什么问题、为什么要这样设计、它和现有 team/task/runtime 的关系是什么，以及它的边界在哪里。

## 1. 它在解决什么问题

你要的不是“coder 写完发一句消息给 tester”，而是：

- `coder` 写代码
- `tester` 跑冒烟 / 验收 / 回归
- 如果失败，`tester` 把具体 bug 打回 `coder`
- `coder` 修复后再次提测
- 一直循环到通过
- `lead` 能看到最终结果，而且中途不丢目标

如果只靠自由文本消息，这条链路会有几个天然问题：

- 没有 durable state：一旦上下文压缩、会话中断、agent idle，再回来时不知道“这是第几轮提测”
- 没有 loop identity：tester 发回来的 bug 可能无法和某次提交对应起来
- 没有 status machine：系统不知道当前是在 `awaiting_test`、`changes_requested` 还是 `passed`
- 没有 task linkage：测试通过后，关联任务不会自动完成；失败后也不会稳定回到修复状态
- 没有 deterministic handoff：全靠模型自由发挥，很容易出现“说了但没真正进入下一步”的假流转

所以这不是单纯 prompt 问题，而是 runtime orchestration 问题。

## 2. 方案概述

Qcode 现在新增了一层持久化的 `verification loop` 协议：

- 模块：`qcode/runtime/verification_loops.py`
- 工具：`qcode/tools/verification_tools.py`
- CLI 查看：`/loops`

核心思路是：

- 每次 coder 提测，都生成或续用一个 `loopId`
- loop 记录落盘到 `.team/verification_loops/loop_<id>.json`
- tester 报结果时，不是随便回一句话，而是更新这个 loop 的状态
- loop 会把状态从：
  - `awaiting_test`
  - `changes_requested`
  - `passed`
  持久化下来
- 如果关联了任务 `task_id`：
  - 提测 / 打回时保持或回到 `in_progress`
  - 测试通过时自动更新为 `completed`

也就是说，`verification loop` 是 coder/tester 之间的“交接协议层”，不是聊天技巧。

## 3. 现在用了什么技术

### 3.1 Durable State Machine

每条 loop 都是一个小状态机，包含：

- `loopId`
- `subject`
- `owner`（通常是 coder）
- `tester`
- `lead`
- `taskId`
- `status`
- `attempts[]`

每一次提测都会新增一个 attempt：

- 第几轮提测
- 谁提交的
- 提测说明
- tester 的结果
- 结果时间

这让系统不再靠“聊天历史”记住测试循环，而是靠独立的 durable record。

### 3.2 Message-Driven Wakeup

loop 自己不运行模型；它只做状态更新和消息路由。

真正唤醒 agent 的还是现有 team runtime：

- `team_manager.send_message(...)`
- idle teammate 收到消息后被唤醒
- 继续自己的工作相位

这点很关键：

- 协议层负责“该谁接棒”
- team runtime 负责“怎么把那个人叫醒”

### 3.3 Task Graph Linkage

如果 loop 绑定了 `task_id`：

- coder 提测时，任务保持 `in_progress`
- tester 打回时，任务仍保持 `in_progress`
- tester 通过时，任务自动 `completed`

这让“测试结果”和“项目任务状态”终于连起来了。

### 3.4 Goal Persistence Compatibility

这条链路和前面已经落下去的 `GoalStore + GoalMiddleware` 是配套的：

- `lead` 的主目标长期落在 `.qcode/active_goal.md`
- teammate 即使经过 idle / compaction / 多轮交接，也可以通过 `get_goal` 重新对齐

所以现在不是只多了一个测试协议，而是：

- 主目标不丢
- coder/tester loop 有 durable state
- task graph 有最终落点

## 4. 为什么这样设计

### 优点

#### 4.1 把“测试循环”从 prompt trick 变成系统能力

以前：

- coder 要记得自己去叫 tester
- tester 要记得把 bug 发回 coder
- coder 要记得复用原来的上下文继续修

现在：

- 用 `request_verification`
- 用 `report_verification_result`
- loopId 和状态由系统保存

更接近真正的工程调度。

#### 4.2 更抗 compaction / idle / 长对话

长对话压缩时，聊天内容会被摘要；
但 loop record 不在聊天消息里，而是在独立文件里。

这意味着：

- 会话可以压缩
- teammate 可以 idle
- 甚至 CLI 重开

只要文件还在，交付闭环就不会完全失忆。

#### 4.3 更适合后续接 Web UI

Web 前端最怕“状态只存在模型脑子里”。

现在有 loop record 后，前端就可以很自然地展示：

- 当前有哪些提测循环
- 哪些在等 tester
- 哪些被打回
- 哪些已经通过
- 每一轮 bug 是什么

这对你后面做 `qcoder` 的前端是有帮助的。

### 代价 / 缺点

#### 4.4 多了一层状态管理复杂度

任何 durable 协议都会带来：

- 文件结构维护
- 状态迁移约束
- 出错恢复逻辑

这是复杂度上升，但属于“必要复杂度”，不是花哨设计。

#### 4.5 还没有完全自动决定“怎么测试”

当前 loop 解决的是：

- 谁提测
- 谁回结果
- 状态怎么流转

它还没有替 tester 自动生成完美测试计划，也没有自动挑选最优测试命令。

这一步仍然依赖 tester agent 自己调用：

- `bash`
- `read_file`
- `task_get`
- 其他工具

换句话说：

- orchestration 稳了
- testing intelligence 还可以继续加强

## 5. 和 Codex / Claude Code 的关系

这条路更接近 Claude Code 的“runtime orchestration 要强于 provider 假状态”的思路：

- provider 只负责出流
- engine 负责工具编排
- runtime 负责 durable state 和 handoff

它不是照抄 Codex 或 Claude Code 的某个现成模块，而是结合你自己的 team/task 体系补出来的。

更准确地说：

- `StreamingToolExecutor` 解决“流式工具执行编排”
- `GoalStore` 解决“主目标持久化”
- `VerificationLoopManager` 解决“coder/tester 交付闭环”

这是三个不同层次的问题。

## 6. 当前边界

现在已经具备：

- durable verification loop
- coder -> tester -> coder -> lead 的消息流转
- linked task 完成态更新
- CLI `/loops` 可查看 loop 状态

但还没有完全具备：

- 自动根据项目类型选择最佳测试矩阵
- reviewer 自动插入 loop
- 多个 tester 并发分片测试
- artifact 级别的测试证据管理（日志、截图、diff、录屏）
- 失败重试策略、超时策略、升级到 lead 的策略

这些是下一阶段可以继续做的。

## 7. 下一步建议

如果继续往你想要的“全自动交付”走，推荐优先级是：

### P0

- 先把 `verification loop` 跑在真实任务上
- 观察 coder/tester 是否会稳定使用这些工具

### P1

- 给 lead 增加一个“监督器策略”：
  - loop 超时未回复时提醒 tester
  - 多次失败时自动拉 architect / reviewer 介入

### P2

- 给 tester 增加“测试计划模板”能力：
  - 冒烟
  - 回归
  - 验收

### P3

- 接 Web UI：
  - loops 面板
  - task board
  - team status
  - 对话区
  - 运行中状态

## 8. 一句话总结

`verification loop` 的本质不是“多一个工具”，而是把 coder/tester 之间反复提测、打回、修复、再提测这条链路，从不可靠的自由聊天，升级成了可落盘、可追踪、可恢复、可和 task graph 联动的 runtime 协议层。
