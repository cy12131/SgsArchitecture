# GameIPC/1

状态：GameIPC/1 帧与进程边界为 M3 实现基线；M3-P4 的 Init/Request/view profile 字段为 **Implementation Candidate**。Schema：`schemas/game-ipc.schema.json`。

GameIPC/1 是 SgsServer C++ 父进程和每个活跃对局的独立 Lua 子进程之间的私有协议，与 SGS/1 独立演进。父进程创建两条单向匿名管道，组成全双工通道；句柄只继承给目标子进程。

## 帧与信封

每帧为 `uint32_be length` + `length` 字节 UTF-8 JSON。长度不得为 0，最大 `1,048,576` 字节；超限、非法 UTF-8、重复 JSON key 或不符合 Schema 均为协议错误。不得把 SGS/1 消息直接透传进 IPC。

所有消息含：`ipc_version: "1"`、`type`、不可变 `game_id`、从每个发送方各自从 `1` 严格递增的 `sequence`（uint64 十进制字符串）和 `payload`。重复、倒退或跳号均失败。需要关联的操作含不可预测且在对局内唯一的 `request_token`（16–128 个 URL-safe 字符）；响应必须回显。

消息类型：

- 父→子 `InitGame`：当前 `manifest_id`、锁定包、模式、玩家/座位、设置和确定性 seed。
- 子→父 `GameReady`：初始化完成；必须关联 Init token，并回报 Runtime API 版本和实际加载包。
- 父→子 `PlayerAction`：已经过连接身份绑定的玩家动作。
- 子→父 `PlayerRequest`：向一个或多个明确玩家请求操作，含 deadline、完成/取消/断线策略、默认回复和公开/私有提示。
- 父→子 `PlayerReply`：响应 token；父进程验证回复玩家在目标集合内，并以 `resolution` 区分 reply、cancel、timeout、disconnect、shutdown 和 default。
- 子→父 `GameOutput`：面向明确 `recipients` 的视图增量，禁止用空 recipients 表示广播。
- 子→父 `GameFinished` / `GameFailed`：终态。
- 父→子 `Shutdown`：请求有序终止。

错误使用 `{code, message, retryable, details?}`。错误消息不得携带其他玩家隐藏信息。

## Lua/QML Bridge 映射

| Runtime/QML 操作 | GameIPC/1 表达 | 前置条件 |
|---|---|---|
| Runtime 创建游戏 | InitGame | 进程处于 Initializing，game_id/启动记录匹配 |
| Runtime 初始化完成 | GameReady | Init token 匹配且尚未 Ready |
| QML `sendGameAction` | PlayerAction | 对局 Running，连接绑定 player_id |
| Lua `game:request` | PlayerRequest | 对局 Running，token 新且 recipients 属于本局 |
| QML `replyGameRequest` / timer / disconnect | PlayerReply | token Waiting 且 player_id 是目标 |
| Lua 可见状态 | GameOutput | recipients 非空且属于本局 |
| 正常/异常终态 | GameFinished / GameFailed | 尚无终态 |
| 父进程停止 | Shutdown | 任意非 Reaped 状态 |

当前 Lua/QML Draft 所需交互均可由现有九种消息表达，不新增消息类型。GameOutput 约定 profile：`view_snapshot` 使用 `{revision,state}`，`view_delta` 使用 `{base_revision,revision,patch}`；revision 为 uint64 十进制字符串。Profile data 仍受接收者权限检查。

## Request 关联规则

- request_token 在单局内不可复用。父进程维护异步 deadline 和目标集合，Lua 维护 token→等待协程；任何一方都不得阻塞网络事件循环。
- PlayerRequest 的 `required_replies` 必须不大于 recipients 数量；`reply_mode=all` 时必须等于目标数，`first` 时必须为 1。
- private_data/default_replies 的 key 必须是 recipients 子集；缺失默认值只有在对应策略不会使用默认值时才合法。
- 每个目标仅接受首个终态 PlayerReply。未知、非目标、重复或迟到回复是语义错误，不转交 Lua。
- 父进程在 timeout/disconnect/shutdown 时合成相应 resolution 的 PlayerReply；Lua 按 Request 策略聚合，并只恢复等待协程一次。

## 状态机

`Created → Starting → Initializing → Ready → Running → Finishing → Finished → Reaped`。

任意非终态可进入 `Failed → Terminating → Reaped`。父进程启动后在超时内发送 `InitGame`；只有匹配的 `GameReady` 可进入 Ready。Ready 后才能转发动作。`GameFinished` 触发结果持久化/广播和有序回收；`GameFailed`、协议错误、管道 EOF、非零退出或超时进入 Failed。`Shutdown` 后给短暂宽限期，再终止并回收。回收必须关闭所有管道和计时器，且只执行一次。

## 超时与背压

- 启动、初始化、玩家请求、关停均有独立 deadline；超时生成稳定错误码。
- 管道必须使用非阻塞/异步读写。网络事件循环不得等待子进程、管道 I/O 或进程退出。
- 每方向写队列默认上限 4 MiB 或 256 帧（先达到者）；超限标记 `IPC_BACKPRESSURE` 并按失败路径回收，不允许无限缓存。
- 部分读写必须继续完成当前帧；写队列保持帧顺序。
- 玩家离线策略由模式决定，但等待协程必须最终得到回复、超时或取消，不能永久悬挂。

## 安全边界

Lua 子进程是权威规则状态持有者，但仍视为受限组件。C++ 绑定网络连接与 `player_id`，不接受 Lua 指定连接句柄。`GameOutput.recipients` 在转发前验证属于本局。隐藏牌、私有技能选项等必须分别定向；参见安全示例。

## 进程异常

EOF/崩溃样例的期望处理：停止接收该局新动作、取消所有未完成 token、向受影响客户端发送通用游戏失败通知、记录不含秘密的诊断、关闭句柄并异步 reap。绝不在网络线程调用阻塞式 wait。
