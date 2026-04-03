# Qcode Task Graph 说明

这次接入的是 `s07` 这条线：把原来只存在于会话里的 `todo`，升级为落盘持久化的 `task graph`。

## 为什么要有它

`todo` 很适合短期工作记忆，但它有天然边界：

- 会话一压缩，细节可能丢失
- teammate 切换时，状态只能靠消息转述
- 依赖关系无法显式表达

`task graph` 解决的是长期协调状态：

- 什么可以做
- 什么被卡住
- 什么已经做完

## 这次落到代码里的结构

- `qcode/runtime/task_graph.py`
  - `TaskGraphManager`
  - `.tasks/task_<id>.json`
  - `blockedBy` 依赖关系
- `qcode/tools/task_graph_tools.py`
  - `task_create`
  - `task_update`
  - `task_get`
  - `task_list`

## 数据长什么样

每个任务是一个独立 JSON 文件，例如：

```json
{
  "id": 4,
  "subject": "实现登录接口",
  "description": "补上鉴权和错误处理",
  "status": "pending",
  "blockedBy": [2, 3],
  "owner": "alice",
  "createdAt": "...",
  "updatedAt": "..."
}
```

## 运行流

### 1. 创建任务

模型调用：

- `task_create(subject="实现登录接口", owner="alice")`

会在 `.tasks/` 下创建一个新文件。

### 2. 添加依赖

模型调用：

- `task_update(task_id=4, addBlockedBy=[2, 3])`

表示任务 `4` 要等 `2` 和 `3` 完成后才能开工。

### 3. 查看任务图

模型调用：

- `task_list()`

会得到按四类分组的视图：

- `Ready`
- `In Progress`
- `Blocked`
- `Completed`

### 4. 完成任务会自动解锁后继任务

当模型调用：

- `task_update(task_id=2, status="completed")`

系统会自动扫描其他任务，把它们 `blockedBy` 里的 `2` 去掉。

这就是“完成前置任务 -> 自动解锁后续任务”的关键逻辑。

## 这版做了哪些工程化保护

### 1. 持久化到磁盘

任务状态不放在会话里，而是放在 `.tasks/`。

所以：

- context compaction 不会把它压掉
- teammate handoff 不会把它丢掉
- 进程内多个 agent 可以共享同一个事实源

### 2. 线程内加锁

因为 teammate 是多线程的，这版 `TaskGraphManager` 做了进程内锁保护，避免多线程同时改一个任务文件时把状态写乱。

### 3. 原子写入

保存时先写临时文件，再替换正式文件，尽量减少脏写风险。

### 4. 循环依赖检查

`blockedBy` 不是随便加的。

这版会检查：

- 不能依赖自己
- 不能把依赖图写成环

因为一旦有环，任务图就不再是 DAG，后面的调度就会混乱。

## 它和 todo 的关系

最重要的一点是：

- `todo` = 当前 agent 的短期工作面板
- `task graph` = 整个系统的长期协调状态

它们不是互相替代，而是分工不同。

## 它和 team 的关系

现在 teammate 也能直接调用：

- `task_list`
- `task_get`
- `task_update`

所以团队协作不必只靠消息猜状态，而是可以读写同一个任务图。

这就是为什么说：

> task graph 是后续 orchestration 的骨架。

## 当前 CLI 额外支持

交互模式下新增：

- `/tasks`：直接查看当前任务图摘要

## 当前边界

这版已经够用，但仍然不是最终态：

- 只做了进程内锁，不是跨进程强一致
- 仍是文件系统 JSON，不适合更高并发
- 还没把 background task 与 task graph 自动绑定
- 还没做 owner claim / retry / cancel 这些更强的调度能力

## 总结

这一步的本质是：

- 把“聊天里口头维护的任务”

升级为：

- “磁盘上显式存在、可恢复、可协调的任务状态系统”

所以它不是普通工具增强，而是在给整个 `Qcode` 增加一个真正的外部状态骨架。
