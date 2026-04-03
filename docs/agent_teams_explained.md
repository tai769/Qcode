# Qcode Agent Teams 说明

这次接入的是 `s09` 这条线：把一次性的 `subagent`，升级为带身份、带邮箱、可反复协作的 `teammate system`。

## 这次落到代码里的结构

- `qcode/runtime/team.py`
  - `MessageBus`：负责 `.team/inbox/*.jsonl` 的追加写入与 drain-on-read
  - `TeammateManager`：负责 teammate 生命周期、线程、状态与 `config.json`
- `qcode/runtime/team_middleware.py`
  - 在每次模型调用前，把 inbox 里的消息注入成 `<inbox>...</inbox>`
- `qcode/tools/team_tools.py`
  - 暴露 `spawn_teammate`
  - 暴露 `list_teammates`
  - 暴露 `send_message`
  - 暴露 `read_inbox`
  - 暴露 `broadcast`

## 运行方式

主 Agent 现在具备这些能力：

- 创建具名 teammate
- 给 teammate 发消息
- 广播消息给所有 teammate
- 查看团队状态
- 读取 lead 自己的 inbox

teammate 本身也具备：

- 文件读写和 shell 工具
- `todo`
- `compact`
- `background_run`
- `send_message`
- `read_inbox`

## 实际运行流

### 1. Lead 通过工具派生 teammate

模型调用：

- `spawn_teammate(name="alice", role="coder", prompt="去检查路由实现")`

这时会做几件事：

- 在 `.team/config.json` 注册或更新成员
- 把 prompt 写入 `.team/inbox/alice.jsonl`
- 确保 `alice` 的后台线程已启动

### 2. Teammate 线程空转等待

每个 teammate 都有一个长期存活的线程：

- inbox 没消息时，状态是 `idle`
- inbox 有消息时，状态切到 `working`
- 然后进入自己的 `AgentEngine.run(...)`

### 3. Inbox 通过 middleware 注入给模型

teammate 真正开始推理前，会由 `TeamInboxMiddleware` 执行：

- 读取自己的 inbox
- 清空 inbox
- 把消息包装为 `<inbox>...</inbox>` 注入当前 session

这样模型看到的是一段标准用户消息，而不是 system prompt 被越塞越胖。

### 4. Teammate 可继续调用工具并回信

比如 `alice` 可以：

- `read_file`
- `bash`
- `todo`
- `background_run`
- `send_message(to="lead", content="我发现问题在 parser")`

### 5. Lead 在下一轮前收到 inbox 注入

主 Agent 也挂了同样的 inbox middleware：

- 每轮模型调用前，先读 `lead` 的 inbox
- 有消息就注入 `<inbox>...</inbox>`

所以 lead 可以自然地在下一轮看到 teammate 的回信。

## 和原先 `subagent` 的区别

`subagent`：

- 临时创建
- 干完即销毁
- 只回摘要
- 没有身份

`teammate`：

- 有固定名字
- 有固定 inbox
- 有生命周期状态
- 可以多次被唤醒继续工作

## 当前实现的边界

这版已经是工程化接入，但还不是最终态：

- teammate 的私有认知仍在进程内，不是落盘记忆库
- inbox 还是 drain-on-read，可靠性一般
- 多 teammate 共享同一工作区，仍可能发生文件冲突
- `shutdown_request` 等消息类型已经预留，但还没做完整治理闭环

## 当前 CLI 额外支持

交互模式里现在支持：

- `/team`：查看团队状态
- `/inbox`：立即读取 lead inbox

## 总结

这一步的本质，不是“多加几个工具”，而是把系统从：

- 单 Agent + 临时 delegation

推进到：

- 多 Agent + 显式通信 + 生命周期管理

也就是说，`Qcode` 现在已经开始具备真正的 team orchestration 雏形了。
