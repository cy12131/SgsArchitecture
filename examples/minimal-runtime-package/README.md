# Minimal Runtime Bridge Contract Example

状态：静态规范样例，不是真实 Linux Lua 子进程/Qt 客户端端到端结果。

预期流程：父进程 InitGame；Runtime 加载锁定包并 GameReady；A 发 `simple_action`；Lua 创建 GameEvent 并触发规则；Lua 对 B 发 PlayerRequest；B 的 QML 用同一 token 回复；Lua 协程只恢复一次并修改权威状态；Lua 分别向 A/B 发不同 view snapshot；最后 GameFinished。

`edge-cases.json` 覆盖 timeout、重复回复、非目标回复、断线和 Lua 进程异常退出。真实集成仍需验证 Lua coroutine、Boost.Asio timer/pipe、QQmlEngine 生命周期和 UI 交互。
