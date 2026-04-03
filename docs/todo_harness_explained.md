# Todo Harness Explained

这份文档解释两个关键概念：

- `Tool Dispatch`：模型可以触达哪些能力
- `Todo + Reminder`：模型如何维护自己的任务状态，并在忘记更新时被提醒

## 1. Tool Dispatch 属于哪一层

你贴的第一段 `s02_tool_use.py`，本质上不是“工具类”，而是 **工具层 + 调度层**。

它做了三件事：

1. 定义工具实现，例如 `run_bash`、`run_read`
2. 用 `TOOL_HANDLERS` 把工具名映射到 Python 函数
3. 在 agent loop 里根据模型返回的 tool name 做分发

所以它在工程上对应的是：

- 工具实现：`qcode/utils/workspace.py`
- 工具定义与注册：`qcode/tools/builtin_tools.py`
- 工具调度：`qcode/tools/registry.py`
- 运行时调用工具：`qcode/runtime/engine.py`

## 2. Todo + Reminder 属于哪一层

你贴的第二段 `s03_todo_write.py` 分成两部分：

- `TodoManager`：属于 **运行时状态管理**
- reminder 注入：属于 **runtime middleware / policy**

所以在当前项目里映射成：

- Todo 状态：`qcode/runtime/todos.py`
- 会话承载 Todo 状态：`qcode/runtime/session.py`
- reminder 策略：`qcode/runtime/todo_middleware.py`
- 工具暴露给模型：`qcode/tools/builtin_tools.py`

## 3. 为什么不能把 reminder 放到 Tool 层

因为 reminder 不是一个“被模型主动调用的能力”，而是一条 **运行时策略**：

- Tool 层回答“模型能做什么”
- Middleware 层回答“模型在什么时候被提醒、被约束、被修正”

这就是两者最核心的职责边界。

## 4. 现在项目里怎么工作的

### `todo` 工具

模型在多步任务时可以调用：

```json
{
  "items": [
    {"id": "1", "text": "Inspect repo", "status": "completed"},
    {"id": "2", "text": "Refactor engine", "status": "in_progress"},
    {"id": "3", "text": "Run validation", "status": "pending"}
  ]
}
```

然后 `TodoManager` 会：

- 校验数量上限
- 校验 `status`
- 保证最多只有一个 `in_progress`
- 渲染成文本，回给模型和终端

### reminder 中间件

如果模型连续多轮工具调用都没有更新 `todo`：

- `AgentEngine` 会累计 `rounds_since_todo`
- `TodoReminderMiddleware` 会在下次模型调用前插入一条提醒

提醒文本默认是：

```text
<reminder>Update your todos.</reminder>
```

## 5. 这一套适不适合你的项目

适合，而且很适合。

因为你现在做的不是普通 CLI，而是一个正在走向工程化的 agent harness。Todo 机制能帮你：

- 让 agent 的执行进度可见
- 让多步任务更稳定
- 给 middleware / policy 留出清晰插槽
- 为以后做 evaluation、回放和调试打基础
