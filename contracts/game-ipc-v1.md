# GameIPC/1

状态：GameIPC/1 帧、信封、九种消息、进程隔离和安全边界为 M3 实现基线；经 M3-B 启动前审查，Init/Request/view profile 字段可进入 **Implementation Candidate**。Schema：`schemas/game-ipc.schema.json`。

GameIPC/1 是 SgsServer C++ 父进程和每个活跃对局的独立 Lua 子进程之间的私有协议，与 SGS/1 独立演进。父进程创建两条单向匿名管道，组成全双工通道；句柄只继承给目标子进程。

## 帧与信封

每帧为 `uint32_be length` + `length` 字节 UTF-8 JSON。长度不得为 0，最大 `1,048,576` 字节；超限、非法 UTF-8、重复 JSON key 或不符合 Schema 均为协议错误。不得把 SGS/1 消息直接透传进 IPC。

所有消息含：`ipc_version: "1"`、`type`、不可变 `game_id`、从每个发送方各自从 `1` 严格递增的 `sequence`（uint64 十进制字符串）和 `payload`。两个方向分别计数；新进程均从 `1` 开始，重复、倒退、跳号、超过 `18446744073709551615` 或回绕均为协议错误。需要关联的操作含不可预测且在对局内唯一的 `request_token`（16–128 个 URL-safe 字符）；响应必须回显。

消息类型：

- 父→子 `InitGame`：不可变 `room_id`、SgsServer 本次启动时锁定的 `manifest_id` 与包、模式、玩家/座位、设置和确定性 seed；不得从磁盘待生效注册表取值。
- 子→父 `GameReady`：初始化完成；必须关联 Init token，并回报 Runtime API 版本和实际加载包。
- 父→子 `PlayerAction`：已经过连接身份绑定的玩家动作。
- 子→父 `PlayerRequest`：向一个或多个明确玩家请求操作，含 deadline、完成/取消/断线策略、默认回复和公开/私有提示。
- 父→子 `PlayerReply`：响应 token；父进程验证回复玩家在目标集合内，并以 `resolution` 区分 reply、cancel、timeout、disconnect、shutdown 和 default。
- 子→父 `GameOutput`：面向明确 `recipients` 的视图增量，禁止用空 recipients 表示广播。
- 子→父 `GameFinished` / `GameFailed`：终态。
- 父→子 `Shutdown`：请求有序终止。

错误使用 `{code, message, retryable, details?}`。错误消息不得携带其他玩家隐藏信息。

## 父进程启动绑定

父进程在创建子进程前生成一条只读启动记录：`game_id → {room_id, manifest_id, packages, mode_id, players/seats, child identity}`。`game_id` 在本次 SgsServer 进程内不得复用；`room_id` 对应 M3-A `uint64` 房间 ID，但在 GameIPC 中编码为无前导零的 uint64 十进制字符串，避免 Lua/JSON 数字精度差异。该转换不改变 SGS/1 的数值 `room_id`。

启动时房间必须已冻结开局名单和座位。父进程从已认证 Session 绑定复制 `player_id`，Lua 不接收 session ID、socket、房主权限或可写 Room 对象。`InitGame`、子进程参数与启动记录的 game/room/generation/roster 任一不一致均以 `IPC_BINDING_MISMATCH` 失败，不允许子进程请求改绑。

框架单局 roster 为 2–8 名唯一玩家，seat 为 1–8 且局内唯一；实际人数必须满足所选 GameMode 的 `min_players..max_players`。两人测试模式只约束自身。每个 game_id 拥有独立 roster、请求表、序列号、状态和可见视图，不得与其他游戏实例共享可变规则状态。

父进程只把目标子进程所需的两个管道句柄设为可继承，关闭其他继承句柄，使用专用工作目录与受控环境启动可信 Runtime 可执行文件。包 Lua 不是进程入口，不能在 SgsServer 主进程执行；Runtime 从只读启动 generation 按依赖顺序加载入口。stdout/stderr 不是 GameIPC，必须独立限流并净化后记录。

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

M3-B3 基础游戏状态使用 `state.profile="sgs.foundation-view/1-draft"` 的业务 profile。它在现有 `state`/`patch` 内表达模式/回合、按玩家裁剪的状态、卡牌展示定义、装备、判定区和 `chained`，不改变 GameOutput 外层字段或 GameIPC Schema。破坏性业务形状变化必须采用新 profile 标识；只有帧、信封、消息方向或公共字段发生不兼容变化时才考虑升级 `ipc_version`。父进程仍把业务状态视为不可信但不猜测字段，只执行 Schema/大小、recipients 和路由边界；具体 profile 由 Runtime 与客户端宿主验证。

`PlayerAction` 是父→子单向、按序交付的已认证意图，不带 `request_token`；`sequence` 只用于 IPC 顺序/重复检测，不作为业务 action ID。客户端游戏动作的网络消息、确认和重试属于 M3-C，届时由 C++ 将认证后的连接身份覆盖为 `payload.player_id`，不得采用客户端自报身份。`PlayerReply` 仅用于回答既存 PlayerRequest：客户端只能产生 `reply|cancel` 意图，`timeout|disconnect|shutdown|default` 只能由父进程按状态合成。

## Request 关联规则

- request_token 在单局内不可复用。Init token 由父进程创建；PlayerRequest token 由 Runtime 使用与确定性游戏 RNG 隔离的宿主 CSPRNG 创建。父进程维护异步 deadline 和目标集合，Lua 维护 token→等待协程；任何一方都不得阻塞网络事件循环。
- `deadline_ms` 是相对时限，不是 Unix 时间戳；父进程在完整验证并接受 PlayerRequest 时以单调时钟启动该时限。排队、部分回复或客户端重连不得延长期限，转发客户端时只发送计算后的剩余时间。
- PlayerRequest 的 `required_replies` 必须不大于 recipients 数量；`reply_mode=all` 时必须等于目标数，`first` 时必须为 1。
- private_data/default_replies 的 key 必须是 recipients 子集；缺失默认值只有在对应策略不会使用默认值时才合法。
- 每个目标仅接受首个终态 PlayerReply。未知、非目标、重复或迟到回复是语义错误，不转交 Lua。
- 父进程在 timeout/disconnect/shutdown 时合成相应 resolution 的 PlayerReply；Lua 按 Request 策略聚合，并只恢复等待协程一次。
- 单目标、多目标和多个按顺序发起的 Request 使用相互独立 token/状态；前一个请求完成并恢复协程后可以创建下一个请求。游戏结束会终结所有 pending token，之后到达的回复按迟到回复拒绝。

## 状态机

`Created → Starting → Initializing → Ready → Running → Finishing → Finished → Reaped`。

任意非终态可进入 `Failed → Terminating → Reaped`。父进程启动后在超时内发送 `InitGame`；只有 init token、mode 和按依赖顺序排列的完整 `loaded_packages` 都与启动记录一致的 `GameReady` 可进入 Ready。Runtime 在完成 Game/GameLogic 构造、已可接收首个动作后才发送 GameReady；父进程验证成功即进入 Running，不增加 StartGame 消息。Ready/Running 后才能转发动作。`GameFinished` 触发结果持久化/广播和有序回收；`GameFailed`、协议错误、管道 EOF、非零退出或超时进入 Failed。`Shutdown` 后给短暂宽限期，再终止并回收。回收必须关闭所有管道和计时器，且只执行一次。

## 超时与背压

- 启动、初始化、玩家请求、关停均有独立 deadline；超时生成稳定错误码。
- 管道必须使用非阻塞/异步读写。网络事件循环不得等待子进程、管道 I/O 或进程退出。
- 每方向写队列默认上限 4 MiB 或 256 帧（先达到者）；超限标记 `IPC_BACKPRESSURE` 并按失败路径回收，不允许无限缓存。
- 部分读写必须继续完成当前帧；写队列保持帧顺序。
- 玩家离线策略由模式决定，但等待协程必须最终得到回复、超时或取消，不能永久悬挂。

## 安全边界

Lua 子进程是权威规则状态持有者，但仍视为受限组件。C++ 绑定网络连接与 `player_id`，不接受 Lua 指定连接句柄。`GameOutput.recipients` 在转发前验证属于本局。隐藏牌、私有技能选项等必须分别定向；参见安全示例。

私有视图由 Lua 按玩家生成，而不是由 C++ 猜测字段并过滤。C++ 的强制边界是：验证 recipients 非空、均属于启动 roster，并且只路由到这些 player_id 当前绑定的 Session；不得把 GameOutput 原样广播。`view_snapshot`/`view_delta` 必须符合 Schema，其他 output profile 在 M3-B 不进入客户端网络。观察者、重连 resync 和动态 QML 展示属于 M3-C。

foundation profile 中手牌实例、私有候选和未公开 processing 内容只能存在于有权观察者的 projection；其他玩家至多收到公开数量。equipment、judge 和 `chained` 属公开状态，但仍必须随每个 recipient 的完整 projection 生成，不得先构造含全部私有字段的广播对象再依赖客户端删除。

## 进程异常

EOF/崩溃样例的期望处理：停止接收该局新动作、取消所有未完成 token、向受影响客户端发送通用游戏失败通知、记录不含秘密的诊断、关闭句柄并异步 reap。绝不在网络线程调用阻塞式 wait。
