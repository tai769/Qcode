# Qcode 架构演进图

这份文档把前面提到的 `s02` 到 `s11` 画成一张演进图，帮助你从“单 Agent 调工具”一路看到“多 Agent + 外部状态系统 + 协议治理 + 自治协作”的工程化方向。

---

## 一条总演进线

```text
s02 Tool Use
   |
   v
s03 Todo
   |
   v
s04 Subagent
   |
   v
s05 Skill Loading
   |
   v
s06 Context Compaction
   |
   v
s07 Persistent Task Graph
   |
   v
s08 Background Tasks
   |
   v
s09 Agent Teams
   |
   v
s10 Team Protocols
   |
   v
s11 Autonomous Agents
```

不要把它理解成“前面的都废弃了”。

更准确地说，是：

- 前一层提供基础能力
- 后一层解决前一层暴露出来的新问题

---

## 按治理方向看

```text
能力治理:   Tool Use ---------> Skill Loading
记忆治理:   Todo -------------> Context Compaction
状态治理:   Persistent Task Graph
并行治理:   Subagent -> Background Tasks -> Agent Teams
协议治理:   Team Protocols
自治治理:   Autonomous Agents
```

这五条线合在一起，才构成完整的 Agent Runtime。

---

## 每一层在系统里的位置

### 1. Tool Use

```text
Model
  |
  v
Tool Registry
  |
  +--> bash
  +--> read_file
  +--> write_file
  +--> edit_file
```

这是最底层的“手脚”。

---

### 2. Todo

```text
Model
  |
  +--> todo tool
          |
          v
      TodoManager
          |
          v
   当前 session 的短期工作面板
```

这是“短期工作记忆”。

---

### 3. Subagent

```text
Parent Agent
   |
   +--> task(prompt="...")
             |
             v
         Child Session
             |
        做局部探索
             |
             v
        只把摘要回给 Parent
```

这是“上下文隔离”。

---

### 4. Skill Loading

```text
System Prompt
  |
  +--> 只放 skill 名称和描述

Model 需要时
  |
  +--> load_skill("...")
             |
             v
        tool_result 注入完整 skill 正文
```

这是“按需知识注入”。

---

### 5. Context Compaction

```text
messages
   |
   +--> Layer 1: micro compact
   |
   +--> Layer 2: auto compact
   |
   +--> Layer 3: manual compact
   |
   v
更小的 working context + 落盘 transcript
```

这是“记忆治理”。

---

### 6. Persistent Task Graph

```text
Main Agent / Subagent / Teammate
           |
           +--> task_create / task_update / task_get / task_list
                          |
                          v
                   TaskGraphManager
                          |
                          v
                     .tasks/task_*.json
```

这是“长期协调状态”。

---

### 7. Background Tasks

```text
Main thread                     Background thread
    |                                   |
    +--> background_run("...")         |
                     |                  |
                     v                  v
                BackgroundManager --> subprocess.run(...)
                     |
                     v
              notification queue
                     |
                     v
         middleware 注入 <background-results>
```

这是“时间并行”。

---

### 8. Agent Teams

```text
                   +-------------------+
                   |   lead agent      |
                   +-------------------+
                     |    |       |
                     |    |       +--> .team/inbox/lead.jsonl
                     |    |
                     |    +--> spawn_teammate("alice")
                     |
                     v
          +-------------------------+
          | TeammateManager         |
          +-------------------------+
             |                |
             v                v
      alice thread       bob thread
             |                |
             v                v
      alice inbox         bob inbox
```

这是“角色化并行协作”。

---

### 9. Team Protocols

```text
Lead / Teammate
      |
      +--> shutdown_request / shutdown_response
      |
      +--> request_plan_approval / review_plan
                       |
                       v
               TeamProtocolManager
                       |
                       v
            .team/protocols/request_*.json
```

这是“结构化协商治理”。

它解决的不是能不能发消息，而是：

- 请求和响应如何关联
- 审批状态如何追踪
- shutdown 和 plan review 如何真正落成 runtime 行为

---

### 10. Autonomous Agents

```text
                   +----------------------+
                   |   teammate thread    |
                   +----------------------+
                              |
                     WORK / tool_use loop
                              |
                 no more tool_use or idle tool
                              |
                              v
                   +----------------------+
                   |      IDLE PHASE      |
                   +----------------------+
                     |               |
                     |               +--> scan task graph
                     |                        |
                     |                        v
                     |                  auto-claim task
                     |
                     +--> read inbox
                              |
                              v
                      resume work or timeout
```

这是“自组织执行治理”。

它解决的是：

- 领导不需要逐个给队友手动派工
- 队友空闲后会自己找未认领任务继续做
- 上下文压缩后还能通过身份重注入记住“我是谁、我在干嘛”
- 团队协作从“能通信”升级到“能持续运转”

---

## 当前 Qcode 的实际组合图

```text
                         +----------------------+
                         |      CLI Harness     |
                         +----------------------+
                                   |
                                   v
                         +----------------------+
                         |     Agent Engine     |
                         +----------------------+
                                   |
        +--------------------------+--------------------------+
        |                          |                          |
        v                          v                          v
+---------------+        +-------------------+       +------------------+
| Middleware    |        | Tool Registry     |       | Chat Provider    |
+---------------+        +-------------------+       +------------------+
| inbox inject  |        | bash/read/write   |       | OpenAI-compatible|
| bg inject     |        | todo              |       +------------------+
| compaction    |        | task(subagent)    |
| todo reminder |        | task graph        |
| identity reinj|        | claim task        |
| idle resume   |        | idle              |
+---------------+        | team tools        |
                         +-------------------+
                                   |
          +------------------------+------------------------+
          |                        |                        |
          v                        v                        v
   +---------------+       +---------------+       +----------------+
   | .tasks/       |       | .team/        |       | .transcripts/  |
   | task graph    |       | inbox/config  |       | compaction log |
   | owner/status  |       | protocols     |       +----------------+
   +---------------+       +---------------+
                                 |
                                 v
                         +----------------+
                         | .team/protocols|
                         | request_*.json |
                         +----------------+
```

---

## 现在最重要的结构理解

你可以把系统分成三层：

### 第一层：会话内能力

- `todo`
- `subagent`
- `background`
- `compact`

这些能力主要处理“当前这轮或当前这个 session 怎么工作”。

### 第二层：会话外状态

- `skills/`
- `.tasks/`
- `.team/`
- `.transcripts/`

这些能力主要处理“什么东西不能只放在上下文里”。

### 第三层：编排与治理

- middleware
- tool registry
- telemetry
- lifecycle manager

这些能力主要处理“系统怎么稳定运行，而不只是能跑”。

---

## 推荐的后续演进方向

```text
现在:
  Tool + Todo + Subagent + Compaction + Background + Team + Task Graph + Protocols + Autonomy

下一步更稳的方向:
  Task Graph <-> Background 绑定
  Task Graph <-> Team 派工/认领绑定
  Owner claim / retry / cancel
  更可靠的 mailbox / queue
  worktree 或沙箱隔离
```

也就是说，后面不是“继续堆功能”，而是开始做：

- 任务调度
- 状态一致性
- 执行隔离
- 可靠性治理

---

## 一句话总结

```text
Qcode 的架构演进，本质上就是：

把原来隐式放在上下文里的能力、知识、状态、协作，
一步一步外置成可治理的 runtime system。
```

这也是你后面做工程化时最该盯住的主线。
