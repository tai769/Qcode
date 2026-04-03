# Background Tasks Explained

这份文档解释后台任务为什么重要，以及它在当前工程中的职责边界。

## 核心问题

有些命令会跑很久：

- `npm install`
- `pytest`
- `docker build`

如果所有工具都是阻塞式执行，agent 在这些命令运行期间只能干等。

## 当前方案

当前项目通过三部分把后台执行接进 runtime harness：

- `qcode/runtime/background.py`：负责后台线程、任务状态表、通知队列
- `qcode/runtime/background_middleware.py`：负责在下一次模型调用前注入结果
- `qcode/tools/builtin_tools.py`：暴露 `background_run` 和 `check_background`

## 运行机制

1. 模型调用 `background_run`
2. Harness 立刻创建后台线程并返回 `task_id`
3. 后台线程运行命令
4. 完成后把结果摘要放进通知队列
5. 下一次模型调用前，middleware 先 drain 队列
6. Runtime 把结果以 `<background-results>` 的形式注入会话

## 为什么它有价值

- 让主 agent 不被长命令卡住
- 支持边等边做其他事情
- 为未来的后台 worker / scheduler 打基础

## 它和 epoll 的关系

这个模式在思想上接近事件驱动：

- 后台线程产生“任务完成事件”
- 主线程在合适时机消费这些事件

但它不是 `epoll`：

- `epoll` 是操作系统级 I/O 多路复用
- 这里是进程内线程 + 通知队列 + polling/drain

所以更准确的类比是：

- 思想上像一个轻量的 event loop / reactor
- 实现上是线程通知，不是内核事件复用
