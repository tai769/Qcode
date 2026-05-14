# Qcode Roadmap

## 已完成

- [x] Agent 引擎 (runtime/engine.py) — 同步 + 异步生成器
- [x] Tool 执行器 (runtime/tool_executor.py) — permission hook
- [x] Session 持久化 — ~/.qcode/sessions/ JSONL
- [x] Textual TUI — 聊天面板 + 侧栏 + 输入框
- [x] Provider 系统 — openai / anthropic 两种协议
- [x] 配置系统 — ~/.qcode/config.toml
- [x] Setup 向导 — 交互式配置 provider/key/model
- [x] CLI 入口 — TUI / 一次性 / 续聊 / stdin pipe
- [x] Slash 命令 — /help /clear /compact /model /todo /team /task /save /load /config
- [x] @ 文件补全 — Tab 循环选择
- [x] Todo 侧栏 — 实时显示任务状态
- [x] Team 侧栏 — 显示队友状态
- [x] Permission 系统 — 框架就绪，弹窗待接入
- [x] 项目记忆 — ~/.qcode/projects/<hash>/memory.md
- [x] pip 安装 — pyproject.toml + install.sh

---

## P0 — 核心体验

### Permission 弹窗接入
- [ ] 用 queue.Queue 桥接 ThreadPoolExecutor → Textual UI
- [ ] bash/write/edit 调用前弹窗确认
- [ ] session 级白名单 (本次不再问)
- [ ] 全局白名单 (写入 config.toml)

### 流式渲染优化
- [ ] RichLog 支持增量 markdown 渲染
- [ ] 代码块语法高亮
- [ ] 长输出自动滚动 vs 用户上滚停住

### 状态栏增强
- [ ] token 计数 (input/output)
- [ ] 当前轮次
- [ ] 工具执行时间

---

## P1 — 差异化功能

### Subagent 面板
- [ ] 显示活跃 subagent 列表
- [ ] 每个 subagent 的任务描述
- [ ] 打开/折叠详情

### Verification Loop 进度
- [ ] coder-tester 循环状态
- [ ] 测试证据展示
- [ ] 失败重试提示

### Task DAG 视图
- [ ] /task 命令展示任务列表 + 依赖
- [ ] 状态标记 (pending/in_progress/completed)
- [ ] 角色认领显示

### Team 编排
- [ ] /team 命令展示完整团队状态
- [ ] spawn_teammate TUI 入口
- [ ] inbox 消息查看

---

## P2 — 体验打磨

### 复制文本
- [ ] Textual 鼠标选择复制
- [ ] Ctrl+C 复制选中文本 (非退出)

### Cost 跟踪
- [ ] 每轮 token 统计
- [ ] /cost 命令显示总消耗
- [ ] 按 provider 计费

### 图片支持
- [ ] 文件选择器上传图片
- [ ] base64 编码发送
- [ ] multimodal provider 支持

### 快捷键
- [ ] Ctrl+K 命令面板
- [ ] Ctrl+S 会话列表
- [ ] Ctrl+O 模型快速切换

---

## P3 — 生态

### Web UI
- [ ] FastAPI 后端 (已有 api/server.py)
- [ ] React/Vue 前端
- [ ] SSE 流式聊天

### VSCode 扩展
- [ ] 侧栏面板
- [ ] spawn qcode --json 子进程
- [ ] 渲染输出

### 包发布
- [ ] PyPI 发布
- [ ] Homebrew formula
- [ ] Docker 镜像

---

## 技术债

- [ ] Permission 弹窗的 call_from_thread 问题
- [ ] StreamingToolExecutor 子线程 asyncio 兼容
- [ ] Anthropic provider 的 thinking/reasoning 完整支持
- [ ] session 序列化版本兼容
- [ ] 错误信息国际化
