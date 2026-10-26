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
- 从启动时只读 generation 按依赖顺序加载 `org.sgs.testmode` 的 `server/init.lua`，完成 registerPackage/registerGameMode、最小只读 Game/roster 宿主与模式绑定；完整 GameLogic 生命周期留给 B3。
- 使用模式无关 Runtime 宿主夹具构造 8 个唯一 player_id/seat，证明 roster 接口不硬编码为 2；`org.sgs.testmode` 仍只以自身声明的 2 人运行。
- GameReady 的 init token、mode、runtime version、完整 ordered loaded_packages 与启动记录一致。
- PlayerRequest token 来自宿主 CSPRNG，不消耗或影响游戏确定性 seed/RNG 序列。
- 分别注入 game_id、room_id、manifest_id、commit、mode、roster/seat 不匹配、入口错误和重复注册，全部在 Running 前确定性失败。
- 验证包不能访问 Session/socket、任意宿主对象、Git 凭据、未声明路径或用户 LUA_PATH/LUA_CPATH。
- stdout/stderr 与 GameIPC 分离并有字节/速率上限；连续输出不会阻塞管道或无限占用内存，日志经过净化。
- B2 只要求最小 Game/roster 宿主可完成 Init/GameReady，不提前验收完整 GameLogic、GameEvent、TriggerEvent 或 Request。

## B3 — Action, event, trigger, request

- headless 驱动注入已认证 PlayerAction；Runtime 覆盖/拒绝不匹配 player 身份。
- 运行 `org.sgs.testmode` 两玩家流程，验证嵌套事件、child-before-parent LIFO cleanup、确定性 trigger 顺序。
- PlayerRequest token 唯一，private/default keys 仅限 targets；覆盖 reply、cancel、timeout、disconnect、shutdown 和 default。
- 覆盖 1–8 个目标、all/first/quorum 聚合，以及同一规则协程依次等待多个 Request。
- 非目标、未知、重复、迟到回复不进入 Lua；all/first/quorum 聚合只恢复协程一次。
- Request pending 时结束游戏，验证全部 token 终结、默认/取消策略只执行一次，随后到达的回复按迟到回复拒绝。
- 请求等待期间持续对另一连接执行网络请求，证明 Boost.Asio event loop 未被 Lua/pipe/waitpid 阻塞。

## B4 — Private views and hardening

- 为 2–8 名玩家分别生成 view_snapshot/view_delta；任一玩家的帧、网络输出、日志和错误中均不存在其他玩家的私有选择。
- recipients 为空、陌生玩家、跨局玩家或重复玩家时拒绝；父进程只向目标当前 Session 路由。
- 固定 seed 与输入重复执行，比较 GameOutput/GameFinished；sequence 与时间性诊断字段除外。
- 在 action、request、cleanup、finish 各阶段注入 Lua error、进程退出和背压，验证通用失败通知、token 取消、幂等 cleanup/reap。
- 记录 Debug 与 ASan/UBSan 测试、峰值队列/内存、进程/FD 数和失败日志净化结果。

## 完成规则

B1→B2→B3→B4 串行放行；失败阶段不得以禁用测试、放宽 Schema 或改为主进程执行 Lua 绕过。B4 通过才可宣称 M3-B 完成。动态 QML、正式客户端游戏协议和皮肤绑定不属于本计划。

跨 M3-B/M3-C 的最终功能验收另行使用 8 个独立客户端完成一局真实游戏，覆盖完整流程、断线、超时和私有信息隔离；该验收不前置到 B2。性能基准单独立项，在真实流程完成前不重复开展没有新风险假设的压力实验。
