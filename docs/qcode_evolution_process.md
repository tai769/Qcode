# Qcode 架构演化过程

说明：你前面提到“烟花进程”，这里我按 **架构演化过程 / 推进过程** 来整理，因为从上下文看你关心的是系统怎么一步步从原型收敛到当前形态。

## 1. 总体判断

Qcode 的演化主线，不是“加了很多功能”，而是 **不断把不稳定的隐式假设，改造成稳定的显式契约**。

它的演化方向大致是：

- 从单脚本原型
- 到可运行 CLI
- 到 provider contract 收敛
- 到流式引擎
- 到工具编排
- 到上下文治理
- 到多角色团队骨架
- 到用户可见的运行状态

这是一次从“能跑”向“可演进”收敛的过程。

---

## 2. 演化阶段一：从单次调用脚本到可复用 CLI Harness

### 原始问题

最早的形态，本质上更接近：

- 用户输入一句
- 调模型一次
- 打印结果

这种形式的问题是：

- 会话状态不稳定
- 工具调用很难形成多轮闭环
- 入口散乱
- 没有统一运行时

### 演化后的结果

Qcode 把入口收束成：

- `qoder`
- `qcode/harness/cli.py`
- `qcode/app.py`

### 解决了什么

- 有了统一 CLI 入口
- 有了统一装配层
- 有了统一 `ConversationSession`

### 代价

- 架构层次增多了
- 调试不再只是一个文件能看全

---

## 3. 演化阶段二：从“整包结果”到“统一事件流”

### 原始问题

你之前碰到的核心 bug，其实都和这个阶段有关：

- provider 回来的是 SSE
- 下游却按 JSON 解析
- 结果就出现 `API returned invalid JSON`

更深层的问题是：

- provider 和 runtime 之间没有明确契约
- engine 看到的是 provider 私有格式，而不是统一格式

### 演化后的结果

引入了统一 `ResponseEvent` 协议：

- `CREATED`
- `OUTPUT_TEXT_DELTA`
- `REASONING_DELTA`
- `TOOL_CALL_DELTA`
- `TOOL_CALL_DONE`
- `COMPLETED`
- `ERROR`

### 解决了什么

- provider 输出标准化
- engine 不再绑定具体供应商的包格式
- 流式文本、工具调用、错误、完成信号都有明确语义

### 这是架构上的本质变化

这一阶段不是修 bug，而是把“provider 和 runtime 的边界”重新定义了。

---

## 4. 演化阶段三：从“兼容 continuation”到“history replay 收敛”

### 原始问题

你遇到了这个典型错误：

- `Unsupported parameter: previous_response_id`

这说明一个问题：

- 不是所有 Responses 兼容接口都真的兼容完整 Responses 契约

如果架构继续建立在 `previous_response_id` 这种服务端 continuation 之上，Qcode 就会长期受制于供应商方言。

### 演化后的结果

Qcode 现在收敛到：

- 自己保管完整会话消息
- 每轮做 history replay
- provider 只负责单轮生成

### 解决了什么

- 摆脱 provider continuation 不一致问题
- 降低多 provider 接入复杂度
- provider contract 更明确

### 代价

- 每轮都要重发更多上下文
- 对上下文治理提出更高要求

也正因为这个代价，后面必须补 `compaction` 和 `budgeter`。

---

## 5. 演化阶段四：从“工具后处理”到“StreamingToolExecutor”

### 原始问题

过去简单做法是：

- 模型整包返回 message
- message 末尾带 tool call
- runtime 再统一去执行工具

这个做法在简单情况下能跑，但在复杂情况下有几个隐患：

- 工具调用参数可能是流式拼出来的
- 中断时可能只收到一半工具事件
- 多工具调用时顺序和配对容易乱
- UI 无法知道当前是“模型在想”还是“工具在跑”

### 演化后的结果

引入了：

- `StreamingToolExecutor`

它做的是：

- 监听工具调用相关事件
- 累积参数
- 参数完整后提交执行
- 按稳定顺序产出 tool results
- 异常时 drain 已启动工具，防止半套协议

### 解决了什么

- 流式 tool call 更可靠
- 中断时不容易出现工具结果丢失
- 工具阶段变成 runtime 一等公民，而不只是 message 尾巴上的附属品

### 代价

- 引擎复杂度明显提高
- 需要更多测试来保正确性

---

## 6. 演化阶段五：从“长对话自然增长”到“ContextBudgeter + Compaction”

### 原始问题

history replay 跑起来之后，新的问题马上就出现：

- 多轮对话会越来越长
- 不压缩就会撞 token 上限
- 更糟的是，可能不是直接报错，而是静默丢早期上下文

### 演化后的结果

分成两层：

#### `ContextBudgeter`

负责：

- 算预算
- 决定要不要压缩
- 算摘要预算和最近原文预算

#### `ConversationCompactor`

负责：

- 保存 transcript
- 摘要历史
- 保留最近原文锚点
- 缩短过长 tool results

### 解决了什么

- 长对话开始有治理机制
- 压缩决策和压缩执行分离
- 不是只保摘要，而是保“摘要 + 最近原文”

### 代价

- 会增加一层 compaction provider 调用
- 压缩质量依赖摘要质量

---

## 7. 演化阶段六：从“无差别自治抢单”到“角色约束任务认领”

### 原始问题

你一开始就指出了自治模式最危险的地方：

- 如果所有角色都去抢同一个队列
- 那产品经理可能抢到测试任务
- reviewer 可能抢到架构设计任务
- 最后自治反而变成混乱

### 演化后的结果

Qcode 没继续走“人人抢单”这条路，而是加了：

- `requiredRole`
- `claim` 时角色校验
- teammate auto-claim 时按 role 扫 lane

### 解决了什么

- 自治不再等于无序
- 多角色团队有了最基本 lane 约束
- 任务图从“任务列表”升级成“带角色约束的任务图”

### 代价

- 还需要后续补超时降级机制
- 还没有更复杂的 role matching / capability matching

---

## 8. 演化阶段七：从“黑盒等待”到“用户可见工作状态”

### 原始问题

这个问题非常真实：

- 你发一句话
- CLI 什么都不显示
- 过几秒甚至十几秒才出结果
- 用户完全不知道是在思考、在调用工具、在压缩上下文，还是已经卡死

### 演化后的结果

CLI 现在增加了阶段状态展示：

- 思考中
- 开始处理请求
- 请求模型
- 模型已接入
- 准备调用工具
- 运行工具
- 压缩长对话上下文

### 解决了什么

- 至少用户能知道系统正在工作
- 工具执行阶段不再是黑盒
- 运行时可观测性往前走了一步

### 代价

- 目前还是 CLI 级可见性，不是完整 TUI 可视化

---

## 9. 演化阶段八：从“能对话”到“能验证”

### 原始问题

如果没有测试，你永远只能自己手点 CLI 猜是否可用。

### 演化后的结果

现在已经有：

- context budgeter 测试
- streaming tool executor 测试
- compaction 测试
- real provider smoke 测试
- CLI progress 测试

### 解决了什么

- 关键 runtime 能回归
- 真实 provider 接口不再只能靠人肉试

### 当前不足

- 还没有 Web API 测试
- 还没有 React 前端测试
- 还没有真正浏览器 E2E

---

## 10. 这条演化主线到底意味着什么

Qcode 目前最重要的不是“功能数量”，而是已经完成了下面几次关键收敛：

- provider contract 收敛
- session 模型收敛
- 工具编排收敛
- 上下文治理收敛
- 多角色任务分工收敛
- CLI 交互可见性收敛

这说明它已经从“实验脚本”进入“可演进 runtime”阶段了。

---

## 11. 还没完成的演化阶段

当前还没有真正进入但你已经明确需要的阶段有：

- Web/API 层
- React 前端
- 可视任务面板
- durable state DB
- 结构化 memory 系统
- resident assistant（heartbeat / cron）
- 更完整的权限 / 审批 / 沙箱控制

这些会是下一阶段的主线。

---

## 12. 一句话总结

Qcode 的架构演化，不是“补功能”，而是：

> **不断把脆弱的临时兼容，替换成可测试、可替换、可持续演进的运行时契约。**
