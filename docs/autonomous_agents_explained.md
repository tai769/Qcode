# Qcode Autonomous Agents 说明

这次接入的是 `s11` 这条线：让 teammate 不再只是“被指派才动”，而是进入真正的自治模式。

## 一句话理解

以前是：

- lead 指派一个活
- teammate 做完
- 然后等下一次指派

现在是：

- teammate 做完当前活
- 进入 idle phase
- 自己轮询 inbox
- 自己扫描任务图
- 发现 ready 且无人认领的任务，就自己认领并继续干

也就是说，它开始具备“自组织找活干”的能力。

---

## 为什么需要这层

如果没有自治，系统会卡在一个明显瓶颈：

- lead 必须逐个给队友写 prompt
- 10 个待做任务得人工分配 10 次
- 队友做完就闲置，不能自己往下接活

这在小 demo 里还能忍，在后面任务一多就扩展不了。

所以自治层解决的是：

- 减少 lead 的派工负担
- 让 teammate 可以持续产出
- 把 team system 从“被动执行”推进到“自组织执行”

---

## 这次落到代码里的结构

- `qcode/runtime/team.py`
  - teammate 运行循环升级为 `WORK / IDLE` 双相模型
  - idle 阶段会轮询 inbox
  - idle 阶段会扫描 task graph 并自动认领任务
  - 上下文被压缩后，会重注入身份块
- `qcode/runtime/task_graph.py`
  - 新增 `scan_unclaimed()`
  - 新增 `claim()`
- `qcode/tools/team_tools.py`
  - teammate 新增 `idle`
  - teammate 新增自用版 `claim_task`
- `qcode/runtime/session.py`
  - 新增 idle poll mode

---

## 运行流怎么变了

## 1. Work Phase

teammate 在工作阶段和以前一样：

- 调模型
- 调工具
- 改文件
- 跑命令
- 发消息

不同的是，工作阶段结束后，不再只是傻等下一次派工。

---

## 2. Idle Phase

当出现下面几种情况时，teammate 会进入 idle：

- 模型自然停止 `tool_use`
- 模型主动调用 `idle`
- 因计划审批进入等待态

进入 idle 以后，系统会轮询两类信息源：

### A. 收件箱

如果 inbox 有新消息：

- 把消息重新注入会话
- 立即恢复工作阶段

### B. 任务图

如果任务图里有：

- `status = pending`
- `owner` 为空
- `blockedBy` 为空

也就是 ready 且未认领的任务，teammate 就会自动：

- `claim`
- 把任务状态改成 `in_progress`
- owner 写成自己
- 把 `<auto-claimed>...</auto-claimed>` 注入会话
- 继续工作

### C. 超时

如果一段时间内：

- 没 inbox
- 没 ready 任务

那么 teammate 会进入 `shutdown`。

这说明它不是永久空转，而是“空闲一段时间后自行收缩”。

---

## 身份重注入是在干嘛

这是 `s11` 里一个非常好的细节。

上下文压缩之后，teammate 可能只剩很少几条消息。

这时虽然 system prompt 里仍然有身份，但为了让会话内部连续性更稳，我加了身份块重注入：

- 当消息条数很短时
- 在最前面插入 `<identity>...</identity>`
- 再插入一句 assistant acknowledgement

这样 teammate 在压缩后恢复工作时，更不容易“忘了自己是谁、在什么团队里、当前是什么角色”。

---

## 这层的优点

- 减少 lead 的微观派工负担
- 队友利用率更高，不容易闲置
- 和 task graph 天然形成闭环：ready 任务会被主动消化
- 比纯 mailbox 模式更接近真正的团队协作
- 身份重注入让 compaction 后的恢复更稳

---

## 这层的代价和缺点

### 1. 行为更难预测

以前队友只有被指派才动，现在队友会自己认领任务。

这意味着：

- 你必须接受系统有更强主动性
- 也必须承担更高的可预测性成本

### 2. 更依赖 task graph 质量

如果任务图脏了，比如：

- owner 没清干净
- status 不准确
- blockedBy 有误

自治 teammate 就可能抢错活或者错过活。

### 3. 更容易出现争抢

虽然这版 `claim()` 做了锁和校验，但只要多 teammate 并发扫描任务图，抢占问题天然会变多。

### 4. 空闲轮询会引入后台活动

teammate 在 idle 时会周期轮询：

- 这比完全静止更耗资源
- 也意味着系统正在持续“活动着”

### 5. 协议等待态和自治态需要区分

比如：

- 提交计划审批后

这时候 teammate 不应该马上去抢别的活。

所以这版特意区分了：

- 普通自治 idle
- `approval_wait` 等待审批 idle

这是必要的，但也让状态机更复杂了。

---

## 现在你该怎么理解它

`s09` 是：

- 队友能通信

`s10` 是：

- 队友能按协议协商

`s11` 是：

- 队友能自己找活干

所以它本质上是在把多 Agent 系统从：

- 被动执行团队

推进到：

- 自组织团队

---

## 当前实现边界

这版已经能跑通自治主线，但还不是最终态：

- 现在是轮询，不是事件驱动调度器
- 自动认领策略还比较简单，只拿第一个 ready task
- 还没有优先级、技能匹配、负载均衡
- 还没有把 plan approval 和 auto-claim 做更细粒度联动

所以这一步是“自治雏形”，不是最终调度系统。

---

## 总结

这一步的关键变化是：

- teammate 不再只是接活的人

而是开始变成：

- 会观察任务板
- 会判断有没有现成工作
- 会主动认领并继续推进

这也是 `Qcode` 从“多 Agent”走向“自治多 Agent”最关键的一步。
