# Qoder 前端测试方案

当前仓库还没有 Web 前端实现，所以这里先交付一份**可直接落地的前端完整测试规格**。等前端页面开始开发后，这份方案可以直接映射到 `Vitest + Testing Library + Playwright`。

## 目标页面范围

- 对话主页面
- 团队面板
- 任务看板
- 协议/审批面板
- 工具输出时间线
- 设置与连接状态区

## 测试分层

### 1. 单元测试

- `MessageRenderer`：普通文本、Markdown、代码块、错误块、工具结果块
- `StreamBuffer`：SSE 增量文本拼接、结束态收口、异常中断复位
- `TaskBoardStore`：任务列表排序、状态切换、owner 展示、筛选
- `TeamStore`：成员状态更新、idle/working/shutdown 展示
- `CompactionBanner`：出现/隐藏、点击 transcript 引导、摘要块展示

### 2. 组件测试

- `ChatComposer`：发送、禁用态、回车发送、多行输入
- `ChatTimeline`：用户消息、助手消息、工具消息混排
- `ToolCallCard`：运行中、成功、失败、耗时展示
- `TaskCard`：`pending / in_progress / completed` 样式
- `TeamMemberCard`：角色、状态、头像/名称、最近动态
- `ProtocolPanel`：plan review / shutdown request 的展示与操作

### 3. 集成测试

- 输入问题后，UI 正确发起请求并流式展示回答
- 模型发出工具调用后，时间线先出现工具卡，再出现工具结果，再出现最终回复
- 长对话触发 compaction 后，UI 显示“已压缩上下文”的提示块
- 任务状态变化后，任务看板与团队面板联动刷新
- 协议审批消息到达后，收件箱与主对话同步提示

### 4. 端到端测试

- 新开会话 → 连续三轮提问 → 模型记住前文
- 长对话 → 自动 compaction → 仍能回答最近需求
- 触发 `read_file`/`todo` 等工具 → UI 正确显示完整链路
- 打开任务看板 → 新任务出现 → teammate 状态变化
- 网络断开 / 超时 → 错误提示、可重试、输入区恢复

## 关键断言

### 聊天流式

- token 逐步出现，而不是等整段完成才显示
- 中途中断不会把半条消息标记为完成
- 新一轮开始时不会污染上一轮流式内容

### 工具链路

- `tool_call` 与 `tool_result` 必须成对显示
- 多工具时结果顺序按调用顺序，而不是按完成先后
- 工具失败要显示错误态，不得吞掉

### 长对话 / compaction

- 触发压缩后要出现压缩提示
- 最近关键需求仍应能在 UI 的“当前上下文”里看到
- transcript 入口可点击或可复制路径

### 团队 / 看板

- teammate 状态变化实时刷新
- 任务 owner、requiredRole、状态标签显示一致
- 空任务、空团队、空收件箱状态都有兜底 UI

## 建议的自动化落地

### `Vitest`

- 负责 store、utils、纯组件单测

### `Testing Library`

- 负责组件交互与集成测试

### `Playwright`

- 负责端到端流程：多轮对话、工具调用、任务看板联动、长对话 compaction

## 最小前端测试清单

如果前端刚起步，优先先写这 8 条：

- 发送消息并渲染用户气泡
- SSE 文本流式追加
- 工具调用卡片渲染
- 工具结果卡片渲染
- 任务看板状态切换显示
- 团队成员状态显示
- 自动 compaction 提示渲染
- 三轮连续对话记忆回归
