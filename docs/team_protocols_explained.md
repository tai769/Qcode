# Qcode Team Protocols 说明

这次接入的是 `s10` 这条线：给 `team mailbox` 再往上加一层“结构化协商协议”。

它解决的不是“能不能发消息”，而是：

- 消息发了以后，双方怎么确认这是同一件事
- 哪些协作要先审批，不能直接开干
- 关机这种敏感动作，怎么做到优雅收尾而不是硬停

---

## 一句话理解协议

协议就是：

> 不是靠随便一句话来协商，而是靠带 `request_id` 的 request-response 握手来协商。

也就是：

- 发起方先创建一个请求
- 这个请求有唯一 `request_id`
- 对方回复时必须引用同一个 `request_id`
- 系统根据这个 `request_id` 更新状态机

状态机很简单：

```text
pending -> approved
pending -> rejected
```

但它非常重要，因为它把“聊天”变成了“可追踪的协作动作”。

---

## 如果没有协议，会发生什么

### 1. 关机会很脆弱

如果 lead 直接把 teammate 线程杀掉：

- 可能文件写到一半
- 可能 shell 命令还在跑
- 可能 `.team/config.json` 还没更新
- 可能 teammate 的最后状态根本没同步出去

也就是说，你看到的是“线程停了”，但系统事实状态未必收干净。

### 2. 计划审批会全靠自由文本猜测

如果 teammate 说：

- “我准备重构认证模块”

lead 回复：

- “可以”

这里马上会出现几个问题：

- 这个“可以”到底对应哪一个计划
- 如果同时有两个计划在飞，回复到底归谁
- 后面回放日志时，系统怎么知道这次审批是否真的发生过

没有 `request_id`，系统就只能靠上下文猜。

### 3. 多请求并发时会乱

只要一旦出现：

- 同时两个 shutdown request
- 同时两个 plan approval
- 广播消息和点对点消息交错

没有协议的话，回复和请求之间的关联会迅速混乱。

---

## 这次落到代码里的结构

- `qcode/runtime/team_protocols.py`
  - `TeamProtocolManager`
  - 持久化到 `.team/protocols/request_<id>.json`
- `qcode/tools/team_tools.py`
  - lead 侧工具：
    - `shutdown_request`
    - `check_protocol_request`
    - `list_protocol_requests`
    - `review_plan`
  - teammate 侧工具：
    - `shutdown_response`
    - `request_plan_approval`
- `qcode/runtime/session.py`
  - 增加 `request_run_stop()`
- `qcode/runtime/engine.py`
  - 支持工具执行后优雅停止当前 run

---

## 为什么这次要改 `session` 和 `engine`

这是很关键的一点。

### 计划审批不是“发完消息继续干”

如果 teammate 提交了计划审批请求，正确动作应该是：

- 发请求
- 暂停当前 run
- 等 lead 的批准或拒绝消息回来

所以我加了：

- `ConversationSession.request_run_stop()`
- `AgentEngine` 在工具执行后检查 stop request

这样 teammate 在 `request_plan_approval` 之后，不会继续往下执行危险改动。

### 关机也不是“回一句话算完”

如果 teammate 批准 shutdown：

- 先通过 `shutdown_response` 回复 lead
- 再请求停止当前 run
- 最后线程自然退出，状态进入 `shutdown`

这才叫“优雅关机”。

---

## 两个协议怎么跑

## 1. Shutdown Protocol

### Lead 发起

工具：

- `shutdown_request(teammate="alice")`

系统会：

- 创建一个 `kind=shutdown` 的协议请求
- 生成 `request_id`
- 写到 `.team/protocols/request_<id>.json`
- 向 `alice` 的 inbox 发 `shutdown_request`

### Teammate 响应

工具：

- `shutdown_response(request_id="abc123", approve=true)`

系统会：

- 校验这个请求确实存在
- 校验它确实是 `shutdown`
- 校验它的目标确实是当前 teammate
- 更新状态为 `approved` 或 `rejected`
- 发 `shutdown_response` 回 lead
- 如果批准，则请求当前 run 停止，并把 teammate 状态标为 `shutdown`

---

## 2. Plan Approval Protocol

### Teammate 发起

工具：

- `request_plan_approval(plan="准备重构认证模块，先拆中间件，再补测试")`

系统会：

- 创建一个 `kind=plan_approval` 的协议请求
- 生成 `request_id`
- 向 lead inbox 发 `plan_approval_request`
- 然后停止当前 run，等待审批结果

### Lead 审批

工具：

- `review_plan(request_id="xyz789", approve=true, feedback="先别动数据库层")`

系统会：

- 找到对应请求
- 更新状态为 `approved` 或 `rejected`
- 给请求发起者发 `plan_approval_response`

之后 teammate 收到批准或拒绝消息，再决定是否继续工作。

---

## 当前实现比原始 `s10` 更工程化的地方

你贴的 `s10` 示例里，`shutdown_requests` 和 `plan_requests` 是内存字典。

这次我接到 `Qcode` 里时，做了一个更稳的版本：

### 1. 请求状态落盘

协议请求不只在内存里，而是存到：

- `.team/protocols/request_<id>.json`

这意味着：

- 更容易调试
- 更容易回放
- 不会因为上下文压缩而丢掉

### 2. 一个统一的 ProtocolManager

不是 shutdown 一套、plan 一套，而是：

- 一个统一的 `TeamProtocolManager`
- 两种 `kind`
- 一套统一的 `request_id + status` 模式

这更符合你说的那句：

> 一个 request-response 模式驱动所有协商。

### 3. 真正暂停 / 退出当前 run

原始示例更像“发了消息，逻辑上表示停了”。

现在是：

- 提交计划后会真的暂停当前 run
- 批准 shutdown 后会真的优雅退出当前 run

这一步非常关键，因为它把“协议”从文档层变成了 runtime 行为。

---

## 现在你该怎么理解它

在 `s09` 里，team system 解决的是：

- 有人
- 能通信
- 能协作

在 `s10` 里，protocol 解决的是：

- 哪些动作必须先握手
- 请求和响应如何一一对应
- 协商状态如何可追踪

所以 `s10` 本质上不是“又多几个工具”，而是：

- 给多 Agent 协作加上规则层

也就是从：

- “大家可以聊天”

升级为：

- “大家按协议协商”

---

## 当前 CLI 额外支持

现在交互模式里还可以用：

- `/protocols`

直接查看当前所有协议请求。

---

## 总结

如果没有协议，模型之间只是“会说话”。

有了协议以后，模型之间才开始具备：

- 可审计的协商
- 可追踪的审批
- 可关联的请求与响应
- 可安全执行的暂停与关机

所以这一层是 team orchestration 从“消息系统”走向“治理系统”的关键一步。
