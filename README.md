# Qcode

Qcode 是一个面向本地工作区的 CLI Coding Agent。

这版重构后的重点不是“把单文件拆碎”，而是把它整理成一套可演进的 `runtime harness`：

- `Harness`：承载 CLI 入口、交互和运行时宿主
- `Runtime`：承载会话、消息中间件、工具循环编排
- `Subagent`：承载子代理运行与上下文隔离
- `Background`：承载长命令的后台执行与结果回流
- `Task Graph`：承载持久任务状态、依赖关系和团队协调骨架
- `Teams`：承载持久 teammate、邮箱总线与多 Agent 协作
- `Protocols`：承载队友间的 request-response 协议与审批握手
- `Autonomy`：承载 teammate 的空闲轮询、自主认领和自组织工作流
- `Compaction`：承载上下文压缩与 transcript 归档
- `Providers`：承载不同模型后端的统一接入层
- `Tools`：承载本地工具定义、注册和执行分发
- `Telemetry`：承载运行事件记录，便于回放与排障
- `Utils`：承载工作区访问和环境加载等基础设施

## 项目结构

```text
.
├── agent_loop.py
├── pyproject.toml
├── README.md
├── .env.example
└── qcode/
    ├── app.py
    ├── config.py
    ├── prompts.py
    ├── harness/
    │   └── cli.py
    ├── providers/
    │   ├── base.py
    │   ├── responses_compatible.py
    │   ├── sse.py
    │   └── openai_compatible.py
    ├── runtime/
    │   ├── background.py
    │   ├── background_middleware.py
    │   ├── compaction.py
    │   ├── compaction_middleware.py
    │   ├── context.py
    │   ├── engine.py
    │   ├── middleware.py
    │   ├── session.py
    │   ├── subagent.py
    │   ├── task_graph.py
    │   ├── team.py
    │   ├── team_protocols.py
    │   ├── team_middleware.py
    │   ├── tool_executor.py
    │   ├── todo_middleware.py
    │   ├── todos.py
    │   └── types.py
    ├── telemetry/
    │   └── events.py
    ├── tools/
    │   ├── builtin_tools.py
    │   ├── registry.py
    │   ├── task_graph_tools.py
    │   ├── task_tool.py
    │   └── team_tools.py
    └── utils/
        ├── env_loader.py
        └── workspace.py
```

## 分层说明

### Harness 层

- `qcode/harness/cli.py` 负责参数解析、交互输入输出和终端展示
- 它不直接拼装底层依赖，而是通过 `qcode/app.py` 获取组装好的 Harness

### Runtime 层

- `qcode/runtime/session.py` 负责对话会话状态
- `qcode/runtime/middleware.py` 负责消息预处理和运行时策略挂载点
- `qcode/runtime/background.py` 负责长命令的后台执行与通知队列
- `qcode/runtime/background_middleware.py` 负责把后台完成结果注入回当前会话
- `qcode/runtime/compaction.py` 负责三层 context compaction 服务
- `qcode/runtime/compaction_middleware.py` 负责每轮微压缩和自动压缩触发
- `qcode/runtime/subagent.py` 负责在 fresh session 中运行 child agent
- `qcode/runtime/task_graph.py` 负责持久任务图、依赖关系和状态解除
- `qcode/runtime/team.py` 负责 teammate 生命周期、邮箱总线、空闲轮询和自主认领
- `qcode/runtime/team_protocols.py` 负责带 `request_id` 的 request-response 协议跟踪
- `qcode/runtime/team_middleware.py` 负责把 inbox 消息注入到 lead 或 teammate 会话
- `qcode/runtime/todos.py` 负责结构化 Todo 状态
- `qcode/runtime/todo_middleware.py` 负责 todo reminder 注入策略
- `qcode/runtime/engine.py` 负责模型调用、工具循环和事件发射

像你前面提到的“定期插入 todo reminder”这类逻辑，就属于 `runtime middleware` 这一层，而不是 Provider 层或 Tool 层。
而 `task -> subagent` 这种能力则是 Tool 接口暴露、Runtime 编排落地的典型例子。
而 context compaction 则是 Runtime 对有限上下文窗口的记忆管理机制。
而 background execution 则是 Runtime 对长耗时命令的时间并行机制。

### Provider 层

- `qcode/providers/base.py` 提供统一的 `ResponseEvent` 事件模型、结果组装器和 provider 协议
- `qcode/providers/sse.py` 负责 SSE 解码与事件解析辅助逻辑
- `qcode/providers/openai_compatible.py` 负责兼容 `chat/completions` 风格 API，并统一映射到内部事件流
- `qcode/providers/responses_compatible.py` 负责兼容 `responses` 风格 API，并统一映射到内部事件流

现在 Qcode 的 Provider 是 `SSE-first` 的：

- Provider 不再优先返回“拼好的整块 message”，而是先产出统一的内部事件流
- `Runtime Engine` 消费事件流，等一轮 `completed` 后再执行工具
- `Tool Executor` 单独负责工具执行，和传输协议解耦

后续如果加 Anthropic、本地 vLLM、Ollama，都应该接在这一层。

这一步的意义是：`JSON` 只是数据格式，`SSE` 是传输方式。很多现代模型接口其实是“用 `SSE` 连续推送多条 `JSON` 事件”。Qcode 现在把这件事显式建模了，而不是把流式响应当作普通字符串硬解析。

### Telemetry 层

- `qcode/telemetry/events.py` 提供运行事件 sink
- 当前支持可选 JSONL 事件日志，便于追踪一次 session 中的模型请求、工具调用和结果

### Tools 层

- `qcode/tools/registry.py` 负责工具描述与分发
- `qcode/tools/builtin_tools.py` 负责装配内置工具
- `qcode/tools/task_tool.py` 负责暴露 parent-only 的 `task` 工具
- `qcode/tools/task_graph_tools.py` 负责暴露 `task_create`、`task_update`、`task_get`、`task_list`
- `qcode/tools/team_tools.py` 负责暴露 `spawn_teammate`、`idle`、协议工具等 team 协作工具
- `qcode/utils/workspace.py` 负责工作区约束、文件读写和 shell 执行

## 快速开始

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

然后在 `.env` 中填好模型配置：

```env
QCODE_API_BASE_URL=https://api.openai.com/v1
QCODE_API_KEY=your_api_key_here
QCODE_MODEL=gpt-4
QCODE_API_WIRE_API=chat_completions
QCODE_MODEL_REASONING_EFFORT=
QCODE_MODEL_VERBOSITY=
QCODE_DISABLE_RESPONSE_STORAGE=false
QCODE_MAX_TOKENS=8000
QCODE_REQUEST_TIMEOUT=60
QCODE_SHELL_TIMEOUT=120
QCODE_TOOL_OUTPUT_PREVIEW_CHARS=200
QCODE_TODO_REMINDER_INTERVAL=3
QCODE_SUBAGENT_MAX_ITERATIONS=30
QCODE_BACKGROUND_TIMEOUT=300
QCODE_BACKGROUND_NOTIFICATION_PREVIEW_CHARS=500
QCODE_MAX_CONTEXT_WINDOW=128000
QCODE_CONTEXT_TARGET_RATIO=0.7
QCODE_CONTEXT_SAFETY_MARGIN_TOKENS=12000
QCODE_COMPACTION_TOKEN_THRESHOLD=50000
QCODE_COMPACTION_KEEP_RECENT_TOOL_RESULTS=3
QCODE_COMPACTION_SUMMARY_RATIO=0.3
QCODE_TEAMMATE_MAX_ITERATIONS=50
QCODE_TEAM_IDLE_SLEEP_SECONDS=0.5
QCODE_TEAM_IDLE_TIMEOUT_SECONDS=60
QCODE_TRANSCRIPT_DIR=.transcripts
QCODE_TASK_DIR=.tasks
# QCODE_TEAM_DIR=.team
# QCODE_EVENT_LOG_PATH=.qcode/events.jsonl
```

如果你接的是 `responses` 风格接口，而不是传统 `chat/completions`，把 `QCODE_API_WIRE_API` 设为 `responses` 即可。当前 Qcode 采用 Claude Code 风格的 `history replay`：仍然使用 `SSE`，但每轮由客户端显式重放必要历史，不依赖 `previous_response_id` 这类 provider-managed thread 机制。像 `gpt-5.x` 一类模型若支持 reasoning / verbosity，也可以通过 `QCODE_MODEL_REASONING_EFFORT` 和 `QCODE_MODEL_VERBOSITY` 传入。

如果你想像很多中转站那样维护多个模型配置，Qcode 现在也支持工作区本地的：

- `.qcode/config.toml`
- `.qcode/auth.json`

其中：

- `config.toml` 放 profile、模型名、base URL、wire API 和默认参数
- `auth.json` 放独立认证信息
- `.env` 仍然保留兼容；没有 TOML profile 时会继续按 `.env` 运行

示例：

```toml
version = 1
active_profile = "default"

[defaults]
max_tokens = 8000
request_timeout = 60

[profiles.default]
base_url = "https://right.codes/codex/v1"
model = "gpt-5.2"
api_wire_api = "responses"
reasoning_effort = "xhigh"
verbosity = "high"
disable_response_storage = true
auth = "default"

[profiles.fast]
base_url = "https://right.codes/codex/v1"
model = "gpt-4o-mini"
api_wire_api = "responses"
reasoning_effort = "low"
verbosity = "low"
disable_response_storage = true
auth = "default"
```

```json
{
  "version": 1,
  "auth": {
    "default": {
      "api_key": "your_api_key_here"
    }
  }
}
```

当前 compaction 已经升级成“摘要 + 最近原文锚点”模式：

- `QCODE_MAX_CONTEXT_WINDOW`：Budgeter 计算时使用的上下文窗口上限
- `QCODE_CONTEXT_TARGET_RATIO`：最多使用多少比例的上下文窗口，例如 `0.7`
- `QCODE_CONTEXT_SAFETY_MARGIN_TOKENS`：给输出、工具 schema 和估算误差预留的安全余量
- `QCODE_COMPACTION_SUMMARY_RATIO`：压缩预算里分给摘要的比例；剩余预算自动留给最近原文锚点

`QCODE_COMPACTION_TOKEN_THRESHOLD` 目前保留为兼容参数和 fallback 安全栅栏，但自动触发的主决策已经改由 `ContextBudgeter` 负责。

现在“保留最近几轮”不再是静态配置，而是 Budgeter 先算出最近原文能占多少 token，Compaction 再从最新 turn 往回倒推，能保留几轮就保留几轮。

如果你的供应商返回的是 `text/event-stream`，这并不是“接口错了”，而是它本来就在走 `SSE` 流。Qcode 现在会优先按 `SSE` 处理，再映射成内部统一事件模型。

## 运行方式

交互模式：

```bash
python agent_loop.py
```

或：

```bash
qcode
```

现在主 CLI 已经支持 assistant 文本的流式打印；工具结果仍然按块展示，避免把 token 流和工具日志搅在一起。

如果你的 shell 会把 `qcode` 解释成同名目录跳转，可以改用不冲突的别名：

```bash
qoder
```

或者直接在仓库根目录运行：

```bash
./qoder
```

单次执行：

```bash
qcode --once "先看看这个项目现在实现到哪了"
```

可选参数：

```bash
qcode --workdir /path/to/project
qcode --profile fast
qcode --list-models
qcode --model gpt-4o-mini
qcode --max-tokens 12000
```

交互模式下还支持：

- `/models`：列出可用 profile
- `/model`：查看当前模型
- `/model fast`：切换到某个 profile
- `/model gpt-5.2`：如果某个 profile 的模型名唯一，也可以按模型名切换

## 当前内置工具

- `bash`：执行 shell 命令
- `read_file`：读取工作区文件
- `write_file`：写入工作区文件
- `edit_file`：替换文件中的指定文本
- `todo`：维护结构化任务列表，约束多步任务进度
- `task_create`：在持久任务图里创建任务
- `task_update`：更新任务状态、依赖、owner 或描述
- `task_get`：读取单个任务的完整 JSON
- `task_list`：按 ready / in-progress / blocked / completed 查看任务图
- `claim_task`：认领一个 ready 且未被占用的任务；如果任务设置了 `requiredRole`，只有匹配角色才能认领
- `task`：启动 fresh-context subagent，只回传摘要
- `background_run`：在后台执行长命令，立即返回任务 id
- `check_background`：查看当前会话的后台任务状态
- `spawn_teammate`：启动或唤醒具名 teammate，在独立线程里工作
- `list_teammates`：查看团队成员与状态
- `send_message`：向 teammate 或 lead 收件箱发消息
- `read_inbox`：立即读取并清空当前 inbox
- `broadcast`：向所有 teammate 广播消息
- `shutdown_request`：发起优雅关机握手，返回 `request_id`
- `check_protocol_request`：查看某个协议请求的当前状态
- `list_protocol_requests`：查看当前协议请求列表
- `review_plan`：审批 teammate 提交的计划请求
- `idle`：teammate 主动进入 idle 轮询阶段，等待 inbox 或自动认领任务
- `compact`：请求立即压缩当前会话上下文

## 默认团队角色

首次启动且工作区中还没有 `.team/config.json` 时，Qcode 会自动预置一个工程团队：

- `ld`：技术负责人，作为主控 lead，负责指挥与协调全队
- `pm`：`product_manager`，负责需求澄清与验收标准
- `architect`：`architect`，负责技术方案和系统边界
- `ui_designer`：`ui_designer`，负责交互流程、页面结构、视觉层级和前端实现说明
- `coder`：`coder`，负责前后端代码实现
- `reviewer`：`code_reviewer`，负责代码审查并和 coder 沟通
- `tester`：`tester`，负责功能验证与回归测试

这些 teammate 初始状态为 `idle`，会在你用 `spawn_teammate` 或 `send_message` 唤醒后开始工作。

## 深入设计

- `docs/provider_contract_hardening.md`：解释为什么要把 Provider 改成 SSE-first、事件流驱动、工具执行解耦

## 角色约束任务

现在可以在任务图里直接声明角色约束，用最小成本避免“乱抢任务”：

```json
{
  "subject": "验证登录流程",
  "requiredRole": "tester"
}
```

行为规则很简单：

- `requiredRole` 为空：任何角色都可以认领
- `requiredRole` 已设置：只有同角色 teammate 可以认领
- teammate idle 自动认领时，也只会拿匹配自己角色的任务

## 当前工程化边界

这版已经完成的是 runtime harness 的基础设施化：

- 入口、编排、Provider、工具和会话状态解耦
- 加入 middleware 挂载点，便于扩展 reminder、guardrail、policy
- 加入 `todo` 工具和 `TodoManager`，让模型能写入结构化进度状态
- 加入 `task` 工具和 `SubagentRunner`，让主 agent 把局部探索委托给 child agent
- 加入持久任务图，让长期状态脱离对话、跨压缩和跨 teammate 保持稳定
- 加入后台命令执行与通知注入，让长命令不阻塞主 agent
- 加入持久 teammate、邮箱总线和 team lifecycle，让多 Agent 协作有落地骨架
- 加入 request-response 协议，让高风险协作不再只靠自由文本消息
- 加入自治 idle cycle，让 teammate 可以自己看任务板、自己认领工作
- 加入三层 context compaction，让长会话可持续运行
- 加入 telemetry sink，便于记录运行事件
- 保留 `agent_loop.py` 兼容入口，同时支持 `qcode` 命令

下一步适合继续做的方向：

- Provider 工厂与多后端切换
- 更细粒度的工具权限和审批策略
- Prompt 模板管理与策略注入
- Evaluation Harness 与回归基准集
- CI/CD 下的自动化回归验证
