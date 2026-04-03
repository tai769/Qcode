# Qcode 已解决的细节问题与根因清单

这份文档专门回答两个问题：

- 这一路到底修掉了哪些真实问题？
- 每个问题的根因是什么，不是什么？

这不是功能列表，而是 **问题清单 + 根因 + 修法 + 影响**。

---

## 1. `responses` 接口返回 SSE，但系统按 JSON 解析

### 表现

你实际遇到过：

- `API returned invalid JSON`
- 响应状态码是 200
- `content-type` 却是 `text/event-stream`

### 根因

根因不是“接口坏了”，而是：

- 上游 provider 已经走 SSE 流
- 下游实现仍在等一个完整 JSON body

这是 **协议层错位**。

### 修复方式

- 引入 `qcode/providers/sse.py`
- provider 优先按 SSE 解析
- 统一映射成 `ResponseEvent`
- JSON 只作为 fallback，不再是主路径

### 解决效果

- `responses` 风格流式接口可以被正确消费
- engine 不再因为拿不到完整 JSON 直接崩溃

### 这件事的重要性

这不是小 bug，而是 provider contract 的根修。

---

## 2. `previous_response_id` 不被供应商支持

### 表现

你遇到过：

- `Unsupported parameter: previous_response_id`

### 根因

根因不是“参数名写错了”，而是：

- 你接入的 provider 只兼容了 Responses 的一部分
- 不支持服务端 continuation 语义

### 修复方式

不是继续堆兼容逻辑，而是直接做架构收敛：

- 去掉对 `previous_response_id` 的核心依赖
- 统一走 `history replay`
- 会话连续性由 Qcode 本地自己负责

### 解决效果

- provider 兼容面大幅提升
- 供应商方言差异不再卡死主链

### 副作用

- 每轮需要重放更多上下文
- 于是必须引入 compaction / budgeter

---

## 3. 流式响应解码时触发 `'NoneType' object has no attribute 'readline'`

### 表现

你遇到过这种堆栈：

- 读取 SSE 过程中爆到 `requests` / `urllib3`
- 最终报 `NoneType.readline`

### 根因

根因不是模型超时，而是早期实现里为了猜编码，间接触发了对 `response.content` 的访问。

对 streaming response 来说，这会把原本应该逐行消费的流，又走到一次性读取 body 的路径上，从而破坏流式读取状态。

### 修复方式

在 `qcode/providers/sse.py` 里：

- 优先使用明确的 UTF-8 / UTF-8-SIG 解码
- 只参考 `response.encoding`
- 不再去碰可能触发全量 body 读取的 `apparent_encoding`

### 解决效果

- 流式响应不再被错误地“二次读取”
- SSE 消费稳定性明显提高

---

## 4. 中文乱码

### 表现

你实际看到过：

- `ä½ å¥½...` 这种乱码

### 根因

根因是文本解码策略不稳：

- 流式数据没按 UTF-8 正确落地
- 响应文本 fallback 逻辑不够明确

### 修复方式

在解码层统一：

- 优先 UTF-8
- 其次 UTF-8-SIG
- 再考虑明确声明的 encoding
- 最后用 UTF-8 replacement，而不是放任错误解码

### 解决效果

- 中文输出恢复正常
- SSE 文本和普通 JSON 文本都走统一解码路径

---

## 5. provider 返回了流，但 runtime 没有“完成事件”约束

### 表现

如果流中断，早期实现可能出现：

- 输出半截
- 没有明确报错
- 会话状态不完整

### 根因

以前 provider 和 engine 之间没有“必须收到完成信号”的硬约束。

### 修复方式

在统一事件模型下：

- `COMPLETED` 成为协议要求
- `ResponseAccumulator` 如果没看到 `COMPLETED`，会抛 `ProviderProtocolError`

### 解决效果

- 断流不再静默成功
- 错误更早暴露

---

## 6. 工具调用只是 message 尾巴，不是 runtime 一等公民

### 表现

早期简单实现里，工具调用逻辑容易出现：

- 多工具顺序不稳
- 中断时 tool_result 不完整
- 参数流式拼接不可靠

### 根因

把工具执行当作“assistant message 之后的后处理”太脆弱。

### 修复方式

引入 `StreamingToolExecutor`：

- 观察 `TOOL_CALL_DELTA / TOOL_CALL_DONE`
- 累积参数
- 完整后再提交执行
- finalize 时稳定输出
- abort 时 drain 已启动工具

### 解决效果

- 工具执行链更稳定
- runtime 和 tool execution 解耦更清楚

---

## 7. compaction 可能拆散 assistant/tool 配对，导致真实 provider 报错

### 表现

你已经实际遇到过这类问题：

- 压缩后保留了 `tool_result`
- 却没保留对应的 assistant `tool_call`
- 下一轮请求时 provider 报：
  - `No tool call found for function call output with call_id ...`

### 根因

tail budget 回收逻辑之前按单条 message 截断，没有把 assistant/tool 当成一个协议块看待。

### 修复方式

在 `qcode/runtime/compaction.py` 中改成：

- 尾部预算裁剪按“块”保留
- 如果保留 tool result，就追溯保留配对 assistant tool call

### 解决效果

- 压缩后协议仍然自洽
- 真实 provider smoke 已验证通过

### 这类问题的本质

这不是“压缩细节小问题”，而是 **消息协议完整性问题**。

---

## 8. 长对话没有治理，history replay 很容易失控

### 表现

如果只做 history replay，不做治理，会出现：

- token 越来越大
- 成本变高
- 上下文开始丢失
- 模型看起来“记忆不稳定”

### 根因

history replay 的优点是稳定；缺点是上下文会持续膨胀。

### 修复方式

引入两层：

- `ContextBudgeter`：负责预算决策
- `ConversationCompactor`：负责摘要 + 最近原文锚点保留

### 解决效果

- Qcode 不再把长对话问题留给运气处理
- 有明确的压缩策略和预算治理逻辑

---

## 9. 任务自治会乱抢，不符合多角色团队现实

### 表现

你一开始就指出：

- 如果 PM 能抢 tester 的任务
- 这种自治就是错的

### 根因

“谁空谁抢”只适合同质 worker，不适合角色分工团队。

### 修复方式

任务图增加：

- `requiredRole`

claim 时校验：

- 角色不匹配就拒绝认领

auto-claim 时：

- 只扫描自己 role 可接的任务 lane

### 解决效果

- 自治开始受角色约束
- 分工型团队至少不会最基本地乱抢任务

---

## 10. Context Compact 之后 agent 可能“忘了自己是谁”

### 表现

压缩后，如果会话只剩很少消息，teammate 可能忘了：

- 自己是谁
- 自己的角色是什么
- 当前团队上下文是什么

### 根因

压缩会减少显式身份信息。

### 修复方式

加入：

- identity re-injection

当上下文过短时：

- 自动重新插入 identity block

### 解决效果

- teammate 在压缩后还能延续角色身份

---

## 11. CLI 长时间静默，看起来像卡死

### 表现

你明确指出：

- 用户看不到它在干嘛
- 一会儿才突然出结果

### 根因

runtime 内部其实在工作，但 CLI 没把阶段状态显示出来。

### 修复方式

CLI 新增：

- 真实工作状态提示
- tool 阶段提示
- compaction 阶段提示
- 模型已接入提示

### 解决效果

- CLI 从“黑箱等待”变成“可见工作”

---

## 12. `qoder` 启动体验不顺滑

### 表现

你之前经常需要手动写长命令：

- `./.venv/bin/qcode --workdir ...`

### 根因

缺少一个稳定快捷入口。

### 修复方式

增加：

- `qoder`

### 解决效果

- 启动体验更接近真正产品工具

---

## 13. 真实 provider 不是“看起来能跑”，而是已经 smoke 过

### 现状

现在不是停留在“理论上应该行”，而是已经通过：

- 多轮记忆 smoke
- `read_file` 工具链路 smoke

### 意义

这说明修掉的不只是单元逻辑，而是真实端到端链路上的问题。

---

## 14. 还没有解决的，不要假装已经解决了

下面这些事情目前 **还没有真正解决到位**：

- Web/API 层
- React 前端
- durable memory store
- durable state DB
- 更细粒度权限/审批体系
- 完整 TUI
- resident assistant heartbeat / cron

这部分仍属于下一阶段，不该假装已经完成。

---

## 15. 一句话总结

Qcode 目前已经解决的核心，不是“样式问题”，而是这些 **会直接导致系统不可靠、不可持续、不可演进** 的根问题：

- provider 协议错位
- continuation 不兼容
- 流式解码不稳
- 工具协议不完整
- compaction 破坏 tool 配对
- 长对话无治理
- 多角色任务乱抢
- CLI 黑箱不可见

这些问题一旦不解决，前端做得再漂亮，底层也不稳。
