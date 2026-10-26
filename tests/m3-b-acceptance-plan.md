# M3-B Executable Acceptance Plan

状态：启动前计划；任何阶段只有保存真实命令、revision、日志摘要和结果后才能标记 Passed。

## B1 — Process supervision and codec

- 同时启动多个协议 stub，每局仅继承自身 read/write 管道；game_id/room_id/child identity 一一对应。
- 将长度头和 JSON 拆成多次 partial read/write，验证正确重组；0、超过 1 MiB、非法 UTF-8、重复 key、Schema 错误均只失败目标游戏。
- 两方向独立验证 sequence 从 1 连续递增；覆盖重复、倒退、gap、`18446744073709551615` 和 overflow。
- 写队列分别触发 4 MiB 与 256 帧边界，产生 IPC_BACKPRESSURE；大厅的 Ping/Echo/房间请求保持响应。
- 覆盖 spawn 失败、初始化超时、EOF、非零退出、SIGKILL、Shutdown 宽限期和 async reap once；无泄漏句柄/timer/zombie。

## B2 — Runtime bootstrap and locked packages

- 使用真实独立 Lua Runtime 读取 InitGame，不在 SgsServer 进程执行包 Lua。
- 从启动时只读 generation 按依赖顺序加载 `org.sgs.testmode` 的 `server/init.lua`，完成 registerPackage/registerGameMode 和 Game/GameLogic 创建。
- GameReady 的 init token、mode、runtime version、完整 ordered loaded_packages 与启动记录一致。
- PlayerRequest token 来自宿主 CSPRNG，不消耗或影响游戏确定性 seed/RNG 序列。
- 分别注入 game_id、room_id、manifest_id、commit、mode、roster/seat 不匹配、入口错误和重复注册，全部在 Running 前确定性失败。
- 验证包不能访问 Session/socket、任意宿主对象、Git 凭据、未声明路径或用户 LUA_PATH/LUA_CPATH。

## B3 — Action, event, trigger, request

- headless 驱动注入已认证 PlayerAction；Runtime 覆盖/拒绝不匹配 player 身份。
- 运行 `org.sgs.testmode` 两玩家流程，验证嵌套事件、child-before-parent LIFO cleanup、确定性 trigger 顺序。
- PlayerRequest token 唯一，private/default keys 仅限 targets；覆盖 reply、cancel、timeout、disconnect、shutdown 和 default。
- 非目标、未知、重复、迟到回复不进入 Lua；all/first/quorum 聚合只恢复协程一次。
- 请求等待期间持续对另一连接执行网络请求，证明 Boost.Asio event loop 未被 Lua/pipe/waitpid 阻塞。

## B4 — Private views and hardening

- 为 A/B 分别生成 view_snapshot/view_delta；A 的帧、网络输出、日志和错误中均不存在 B 的私有选择。
- recipients 为空、陌生玩家、跨局玩家或重复玩家时拒绝；父进程只向目标当前 Session 路由。
- 固定 seed 与输入重复执行，比较 GameOutput/GameFinished；sequence 与时间性诊断字段除外。
- 在 action、request、cleanup、finish 各阶段注入 Lua error、进程退出和背压，验证通用失败通知、token 取消、幂等 cleanup/reap。
- 记录 Debug 与 ASan/UBSan 测试、峰值队列/内存、进程/FD 数和失败日志净化结果。

## 完成规则

B1→B2→B3→B4 串行放行；失败阶段不得以禁用测试、放宽 Schema 或改为主进程执行 Lua 绕过。B4 通过才可宣称 M3-B 完成。动态 QML、正式客户端游戏协议和皮肤绑定不属于本计划。
