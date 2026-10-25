# ADR-0002: 每个活跃对局独立 Lua 进程

- 状态：Accepted
- 日期：2026-10-25

## Decision

每个活跃对局使用独立 Lua 子进程。C++ 父进程创建、监控、终止和回收；Lua 持有权威规则状态并推进事件与技能结算。

## Consequences

崩溃和状态按局隔离，代价是进程/IPC 开销。框架必须异步监管、限制资源和背压；PlayerRequest 只暂停该局 Lua 协程，父进程以 token/timer 异步桥接，绝不阻塞 Boost.Asio。复杂技能规则不得迁入 SgsServer C++。
