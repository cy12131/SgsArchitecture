# M3-B Startup Interface Review

- 状态：Approved for staged implementation
- 日期：2026-10-26
- 审查基线：SgsArchitecture `05c98184c427660033063f1517c6077d45eee9b1`
- 参考包：CNB `org.sgs.testmode` commit `9d38a4a970448ca17bfbf7c61f20ab77f6f12451`

## 结论

GameIPC/1 的独立版本、双匿名管道、大端长度帧、九种消息和失败边界兼容 M3-B，无需重设协议或改动 SGS/1。现有实现尚未部署 GameIPC，因此本轮给 InitGame 增加 `room_id`、收紧 view profile 属于 Implementation Candidate 的实现前补全，继续使用 `ipc_version: "1"`。

M3-B 只建立“房间开局 → 独立 Lua 进程 → 权威规则 → 定向输出”的服务端/Runtime 闭环。客户端游戏消息、动态 QML、断线重连视图恢复、观察者和皮肤扩展属于 M3-C，不应塞入 M3-B。

## 阶段与依赖

```text
M3-A locked package generation
        ↓
M3-B1 process supervision + GameIPC codec
        ↓
M3-B2 standalone Runtime bootstrap + package loading
        ↓
M3-B3 GameLogic/Event/Trigger + Request bridge
        ↓
M3-B4 private outputs + failure/backpressure hardening
        ↓
M3-C client game protocol + dynamic QML/extensions
```

| 阶段 | 交付边界 | 明确不包含 | 最低可执行验收 |
|---|---|---|---|
| M3-B1 | GameProcessManager 边界、每局子进程、双管道 codec、启动记录、sequence、deadline、背压、异步 reap | Lua 规则加载、客户端游戏 UI | 协议 stub 完成 Init/GameReady；partial I/O、错帧、超长、序列 gap、队列溢出、崩溃均只失败该局且大厅继续响应 |
| M3-B2 | 独立 Lua Runtime、受控环境、只读 generation、依赖顺序加载、Runtime.registerPackage/registerGameMode、Game/GameLogic 创建 | Request 协程完整桥接、动态 QML | 真实 Runtime 加载锁定 `org.sgs.testmode`，校验 room/game/manifest/packages/roster，回送匹配 GameReady；任一不匹配确定性失败 |
| M3-B3 | PlayerAction、GameEvent/TriggerEvent、PlayerRequest/Reply、异步 timer、重复/迟到/非目标拒绝、协程一次恢复 | 正式客户端动作/回复协议和页面 | 两玩家 headless 流程完成 action→嵌套 event→request→reply/timeout/disconnect→finish；网络 event loop 全程可服务其他连接 |
| M3-B4 | per-player snapshot/delta、recipient 路由、终态、Shutdown、异常/压力/确定性/净化日志测试 | QML 渲染、客户端 resync、观察者、皮肤 | A 看不到 B 私有选择；SIGKILL/EOF/backpressure/cleanup error 不崩大厅；资源/句柄/timer 恰好回收一次；固定 seed/input 输出可复现 |

B2 依赖 B1，B3 依赖 B2，B4 依赖 B3。不得以 Mock 单元测试替代前一阶段的真实进程/管道门槛。

## 启动绑定与职责

父进程创建不可变记录 `game_id → {room_id, manifest_id, ordered packages, mode_id, roster/seats, child identity}`。room_id 来自 M3-A `uint64` 房间，在 IPC 中转为十进制字符串。开局后 roster/seat 对该游戏冻结；Session 重连或离线只改变 C++ 连接绑定，不允许 Lua 修改身份。

Linux Agent 负责：可信 Runtime 可执行文件的启动/监管、句柄继承、GameIPC codec、异步队列/timer/reap、身份与 recipient 校验、generation/roster 绑定、通用错误转译。不得在 SgsServer 进程执行包 Lua，也不得解释具体卡牌/技能规则。

Package Agent 负责：使 `org.sgs.testmode` 及后续普通包只使用公开 Runtime API，实现 GameLogic/GameEvent/Trigger/Request 和定向视图，提供默认/超时策略及 headless 验证。不得访问 pipe/socket/Session、生成 wire sequence、绕过 Runtime 或要求框架加入包专用分支。

Architecture Agent 维护 Schema、状态机、向量和验收证据；Windows Client Agent 在 M3-B 不承担动态游戏页面实现。

## 接口澄清清单

| 接口 | 审查决定 | 状态 |
|---|---|---|
| InitGame.room_id | 必填；SgsServer uint64 的无前导零十进制字符串 | Implementation Candidate，可实现 |
| game/room/generation/roster | 在 spawn 前形成不可变启动记录；Init/GameReady 必须匹配 | 可实现 |
| packages/loaded_packages | 使用该模式可访问的完整 Runtime package closure 有序列表（含依赖）；GameReady 必须精确回显已挂载集合 | 可实现，需真实包验证 |
| sequence | 每方向独立从 1 连续增长；uint64 上限、禁止 gap/回绕 | 可实现 |
| PlayerAction | 单向认证意图，不使用 request_token；网络 ack/retry 留给 M3-C | 可实现 |
| request_token | Init 由父进程生成，PlayerRequest 由 Runtime 生成；局内永不复用 | 可实现 |
| deadline_ms | 父进程接受请求时用单调时钟启动的相对毫秒数，不因排队/回复/重连延长 | 可实现 |
| PlayerReply | C++ 验证 game/token/target/first terminal；系统 resolution 不接受客户端伪造 | 可实现 |
| private_data/GameOutput | Lua 生成每玩家视图；C++ 验证 recipients 并精确路由，不做字段猜测 | 可实现，需信息流测试 |
| GameReady→Running | Runtime 准备好首个动作后发 Ready；父进程验证后直接 Running，无新消息 | 可实现 |
| room/game 结束后的大厅/房间策略 | GameFinished 后房间保留、销毁或返回 waiting 的产品规则 | 仍需实验/后续产品决定，不阻塞 B1–B3 |

### 三条父→子消息的实现格式

- `InitGame`：公共字段加 init `request_token`；payload 必须且仅含 `room_id, manifest_id, mode_id, seed, players, packages, settings`。players 项为 `{player_id,seat,display_name}`，packages 项为 `{id,commit}`。
- `PlayerAction`：公共字段且无 request_token；payload 必须且仅含 `{player_id,action_type,data}`。player_id 由 C++ 的已认证连接绑定产生。
- `PlayerReply`：公共字段加原 PlayerRequest token；payload 必须且仅含 `{player_id,resolution,data}`。父进程在写 IPC 前完成目标、首个终态和 resolution 来源检查。

上述 payload 都受完整帧 1 MiB 上限及每方向 sequence 约束；JSON `null`、数组或标量是否可出现在业务 `data` 中由对应 action/request profile 决定，不能绕过外层 Schema 与大小限制。

## GameIPC/1 兼容性审查

- 保持四字节大端长度、UTF-8 JSON、1 MiB 单帧、每方向 4 MiB/256 帧写队列和九种消息。
- SGS/1 与 GameIPC/1 仍不可透传；网络 request_id 不进入 IPC request_token。
- InitGame 新增 room_id，Schema 对 view_snapshot/view_delta 与文档对齐；所有仓库内向量同步更新。
- Schema 只能限制 sequence/room_id 的十进制形状和 20 位长度，`≤ 2^64-1`、连续性、玩家/座位唯一性、包列表匹配仍由语义验证和实现检查。
- 未发现需要 `ipc_version: "2"` 的已部署兼容性理由；首个真实实现必须以本审查后的 Schema 为基线。

## `org.sgs.testmode` Mock 适配差异

| Mock 表面 | GameIPC/Runtime 契约 | 适配责任 |
|---|---|---|
| `MockGame:new()` 自造 game/players，无 InitGame | 父进程提供 game_id、room_id、seed、roster、generation | Runtime 从 InitGame 构造只读 Game |
| Lua Player 使用 `id` | wire 使用 `player_id` | Runtime 映射为 `Player.id`，包不看 wire 表 |
| request 使用 `players`、`timeout_ms` | PlayerRequest 使用 `recipients`、`deadline_ms` | Runtime 规范化并生成 token/sequence |
| coroutine.resume 直接注入 `{status,replies}` | 父进程逐目标发送带 resolution 的 PlayerReply | Runtime 聚合策略后只恢复一次 |
| emit 只写 Lua 数组 | GameOutput 需 Schema、1 MiB、队列和 recipient 校验 | Runtime 编码；C++ 校验/路由 |
| revision 由 MockGame 递增 | 每玩家 uint64 十进制 revision | 机制可复用，需 overflow/gap 测试 |
| GameEvent 只有 Running/Cleaning/Completed/Failed | Draft 还有 Preparing/Exiting/Interrupted、嵌套清理传播 | Package/Runtime 在 B3 补齐并验证 |
| Trigger 只按 priority/registration index | Draft 还含 package load index、refresh phases、cost/repeat | B3 先实现确定性最小面，其余以实验结果冻结 |
| 无 pipe/sequence/token/backpressure/crash | GameIPC 强制这些边界 | Linux Agent，不由包实现 |
| QML GameTable | 属于 M3-C 动态页面 | M3-B 不以其运行作为验收条件 |

Manifest `api_version: "1.0"` 是包/框架兼容版本；GameReady `runtime_api_version: "1.0-draft"` 是当前 Runtime Draft 标识，两者不是同一字段，首个实现应分别校验，后续冻结时再统一版本策略。

## Implementation Candidate 与实验项

可立即进入实现：进程/管道边界、GameIPC 帧与九种消息、启动绑定、Init/GameReady 字段、双向 sequence、Request token/target/deadline/first-terminal 规则、写队列上限、失败/reap、recipient allow-list、Game/GameLogic 基本生命周期。

必须通过实验再冻结：Runtime 可执行文件路径/CLI 与 FD 传递细节、Lua 解释器及模块白名单、CPU/内存/文件描述符限制、协程调度实现、堆栈净化格式、Trigger refresh/cost/repeat 的最小稳定 API、quorum 聚合边界、GameFinished 后房间产品状态。

明确留给 M3-C：SGS/1 游戏动作/回复/视图消息、客户端确认/重试、动态 QML GameViewContext、snapshot/delta resync、重连/观察者、General/Skin/ResourceResolver 运行时验证。M3-B 可用 headless 驱动注入 PlayerAction/Reply，但不得借此冻结客户端协议。

## ADR 与契约影响

ADR-0002（每局独立进程）、ADR-0005（协议分离）、ADR-0006（双端职责）和 ADR-0009（启动 generation）已覆盖本轮决定，不新增 ADR。若后续要改变“一局一进程”、允许包网络/文件系统、运行时切换 generation 或引入进程池，必须另立 ADR。

本轮需要且已规划的契约调整：GameIPC InitGame room_id、sequence/deadline/identity/view 语义、Schema view profile、绑定/序列测试向量、Lua wire/API 适配说明及 B1–B4 验收计划。
