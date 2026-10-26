# Lua Runtime API v1 — Draft

状态：**Draft**。等待 Package Agent 的最小验证包基于 freekill-core/utility 机制完成生命周期、嵌套事件和协程请求验证后再冻结。

本草案抽取概念，不承诺 freekill 原始 API 可原样运行。适配层负责把 GameIPC 数据转换为 Lua 对象，并禁止包直接访问管道、网络连接或宿主文件系统。

## 参考实现与适配边界

本轮实际抽查了本地 `freekill-core-master.zip` 和 `freekill-asio-static` 中的 `lua/server/request.lua`、`gameevent.lua`、`gamelogic.lua`、`lua/core/trigger_event.lua`、`package.lua`、`game_mode.lua`、`request_handler.lua` 及 QML RoomModel/RequestLifecycle。可借鉴点包括逐玩家请求数据和默认回复、协程让出、事件/cleaner 双栈、优先级触发、重复触发计数和 UI 请求清理。

以下内容不直接兼容：FreeKill 的全局 `RoomInstance`/`ClientInstance`、目录扫描加载、CBOR/内部命令、直接 QML→ClientInstance 调用以及具体卡牌/技能类。SGS 使用显式 GameIPC、锁定 commit、依赖拓扑顺序和能力受限宿主；适配包不得假定 FreeKill 模块名或对象布局存在。

## 独立进程入口与启动

Implementation Candidate 命令行：

```text
sgs-lua-runtime --game-id <id> --package-root <immutable-dir> --ipc-read <handle> --ipc-write <handle>
```

- 父进程为每局创建专用工作目录；不得把 Git 工作树或可写安装目录作为 cwd。
- `package-root` 是父进程从本次 SgsServer 启动时锁定 generation 为当前 `manifest_id` 准备的只读、不可变视图，只包含锁定 commit。Lua 进程没有 Git 凭据、网络下载能力，也不得解析分支/标签。
- 父进程按 Manifest 依赖拓扑顺序生成允许的 Lua 搜索路径；只加入各包根和框架运行时目录。禁止继承用户 `LUA_PATH`/`LUA_CPATH`。
- 进程启动后首先等待 `InitGame`。`game_id` 必须匹配启动参数；`manifest_id`、包 ID/commit、玩家 ID/座位必须与父进程的启动记录一致。
- Runtime 按依赖顺序加载声明了 `server.entry` 的包，完成注册后选择唯一 `mode_id`，创建 Game/GameLogic，再回送关联 Init token 的 `GameReady` 和实际加载包列表。
- 缺包、commit 不符、入口异常、重复注册、模式缺失或玩家设置非法时发送 `GameFailed`（若 IPC 可用）并以非零码退出；不得发送 GameReady。
- `Shutdown` 停止接收新动作，取消所有 Request，运行幂等 cleanup，发送不了终态时也必须退出。EOF、父进程消失或写队列失败走相同清理路径。
- Runtime 不自行拉取“最新版本”，也不在启动后改变包集合；同一 SgsServer 进程内随后创建的新对局仍使用服务器启动时锁定的 generation。包变更只能在 SgsServer 正常重启后影响对局。

## Game API

`Runtime.createGame(init)` 仅由适配层调用，返回当前进程唯一 Game：

| 成员 | 类型 | 权限/语义 |
|---|---|---|
| `game.id` | string | 只读，与 GameIPC game_id 相同 |
| `game.room_id` | string | 只读，SgsServer uint64 room_id 的无前导零十进制表示；仅用于关联/诊断，不能访问 Room 对象 |
| `game.mode_id` | string | 只读，必须已注册 |
| `game.players` | ordered Player[] | 只读集合，按 seat；ID→连接绑定由 C++ 保管 |
| `game.settings` | read-only table | 来自 InitGame，规则包不得改写原表 |
| `game.state` | table | Lua 权威规则状态，只能在调度器协程中修改 |
| `game.random` | deterministic RNG | 由 InitGame seed 创建，禁止 `math.randomseed` 重置 |
| `game:emit(spec)` | function | 生成定向 GameOutput；必须明确 recipients |
| `game:request(spec)` | yielding function | 创建 Request 并等待结构化结果 |
| `game:finish(result)` | function | 一次性进入 Finished 并发送 GameFinished |
| `game:fail(error)` | function | 一次性进入 Failed 并发送 GameFailed |

生命周期：`Created → Initializing → Ready → Running → Finishing → Finished|Failed → Cleaned`。终态和 cleanup 幂等；终态后拒绝动作、事件和新 Request。

房间名称、房主、Ready、连接 Session 和网络身份属于 C++ 框架；Lua 只收到不可伪造的 `player_id`、seat、展示名和模式设置。Lua 权威负责牌堆、手牌、技能、回合、胜负和派生视图。玩家离线由父进程转换为 Request resolution 或框架动作；模式只能选择已声明的离线策略，不能接管 socket。

Wire/API 适配由 Runtime 承担：InitGame 的 `players[].player_id` 暴露为只读 `Player.id`；`game:request{players, timeout_ms, ...}` 规范化为 PlayerRequest 的 `recipients`、`deadline_ms`；PlayerReply 的多目标 resolution 由 Runtime 聚合为 `{status,replies,...}` 后恢复协程。资源包不得自行构造 GameIPC 信封、sequence 或 request_token。

## GameEvent 状态与清理

`game.logic:pushEvent(type, data)` 创建事件并分配局内单调 `event_id`、`parent_id` 和深度。状态机：

`Created → Preparing → Running → Cleaning → Exiting → Completed`

`Preparing|Running` 也可进入 `Interrupted` 或 `Failed`，但仍必须经过 `Cleaning → Exiting` 后成为终态。

- 子事件在父事件 Running 中创建；父协程暂停，直到子事件完成全部清理。
- 事件数据由事件类型定义；外部只能得到只读快照，不能持有终态事件的可变引用。
- `interrupt(scope, reason)` 的 scope 为 `current`、`through_parent(event_id)` 或 `game`；Runtime 标记目标而非直接丢弃协程。
- 每个事件的 cleanup 回调按注册的后进先出顺序恰好执行一次；随后执行 exit 回调。cleanup 中创建的子事件必须先完成。
- 规则错误附加 event_id 和安全堆栈摘要，向父事件传播；未被模式明确恢复的错误使 GameFailed。不得留下半弹出的事件栈。
- `result` 为 `{status="completed|interrupted|failed", value?, reason?}`，父事件只在结果固定后恢复。

## TriggerEvent 调度

包通过 `registerTrigger{event, skill_id, priority, condition, cost?, effect, max_invocations?}` 注册。具体 condition/cost/effect 均为 Lua 规则，C++ 不解释。

1. 先运行只读 refresh trigger，再运行普通 trigger，最后运行 late refresh；refresh 不得消费玩家回复。
2. 普通 trigger 排序键为 `priority desc → package load index asc → registration index asc → target seat asc`。
3. 每次执行前重新检查 condition；cost 取消只取消该次触发。effect 可返回 `continue`、`break_trigger` 或结构化事件中断。
4. Runtime 为 `(trigger_event_id, skill_id, player_id)` 计数；默认最多一次，显式 `max_invocations` 受运行时上限约束。已完成或被取消的 invocation 不会因列表重算而无限重复。
5. 触发器异常走当前 GameEvent 的 Failed/cleanup 路径。包不得跨事件缓存内部 TriggerEvent 对象。

## Request Bridge（最高优先级）

`game:request(spec)` 的 spec：

| 字段 | 规则 |
|---|---|
| `request_type` | 非空稳定字符串，由包/QML 协商 |
| `players` | 1–8 个唯一且属于本局的 player_id |
| `public_data` | 所有目标可见的对象 |
| `private_data[player_id]` | 只交付对应玩家；不得出现在其他玩家日志或输出 |
| `timeout_ms` | 1–600000 |
| `reply_mode` | `all`、`first` 或 `quorum` |
| `required_replies` | 与 reply_mode/目标数一致 |
| `default_replies[player_id]` | 超时、允许取消或断线策略使用的合法默认值 |
| `cancel_policy` | `allow`、`use_default`、`reject` |
| `disconnect_policy` | `use_default`、`wait`、`cancel_request`、`fail_game` |

Runtime 生成 128 位以上随机熵的 URL-safe `request_token`，局内永不复用。父进程维护 token→game/targets/deadline 表并使用异步 timer；Lua 维护 token→Request/协程表。两者都设置并发上限，超限以 `REQUEST_LIMIT` 失败，不能无限排队。

### 状态机

`Created → Dispatched → Waiting → Resolving → Completed`

Waiting 可进入 `TimedOut`、`Cancelled`、`Disconnected` 或 `Shutdown`，这些分支先按策略生成每玩家 resolution/default，再统一经过 Resolving，最后 Completed；内部错误进入 `Failed`。每个目标子状态为 `Pending → Replied|Defaulted|Cancelled|Disconnected`，终态不可逆。

- 有效 PlayerReply 必须匹配 game_id、未完成 token 和目标 player_id。非目标、未知、迟到或重复回复拒绝，不能恢复协程，也不能覆盖首个结果。
- 多玩家请求按 `reply_mode` 完成；未被采用的 pending 目标收到 request-closed 通知并使用 default/ignored 状态。
- 同一玩家可有多个 token 并发；客户端按 token 分离 UI。模式可自行串行化，但框架不靠“当前唯一请求”关联回复。
- 父进程 deadline 到达时为每个 pending 目标发送 `PlayerReply(resolution="timeout")`；Lua watchdog 只用于父进程失效保护，不与正常 timer 竞争。
- 断线转换为 `resolution="disconnect"`。`wait` 仍受原 deadline；其他策略立即处理。
- Shutdown/游戏终态关闭全部 token，恢复每个等待协程至结构化取消结果或直接进入 cleanup；协程最多恢复一次。

### 时序

```text
Lua rule coroutine   Lua Runtime       C++ parent/Asio       Client/QML
      | request(spec)     |                    |                  |
      |------ yield ----->| PlayerRequest --->| GameRequest ---->|
      |                   |                    |<-- token reply --|
      |                   |<-- PlayerReply ----|                  |
      |<-- resume once ---|                    |-- close token -->|
```

管道读写、deadline 和客户端 I/O 都由异步队列处理；任何 `game:request` 等待都只暂停该游戏的 Lua 协程，绝不阻塞 SgsServer 的 Boost.Asio 网络事件循环。

## Content 注册

注册只在 Initializing 阶段开放，并以当前包为隐式 owner；失败回滚该包本次全部注册。支持：

- `registerGameMode{id,min_players,max_players,create_logic,ui_package_id,ui_mode}`
- `registerCard(definition)`、`registerGeneral(definition)`、`registerSkill(definition)`
- `registerEvent{id,create,run,cleanup?}`、`registerTrigger(definition)`
- `registerTranslation{locale,entries}`
- `registerData{kind,id,value}`：Schema 验证的其他扩展数据

依赖包先注册；同一 registry 的 `(owner_package,id)` 必须唯一。对局进入 Ready 后 registry 冻结。卡牌、武将、技能 ID 的最终命名规则本 Draft 不冻结，由后续 Package Agent 评审决定。

### 跨包武将与皮肤能力（Draft）

未来 Content 层必须提供以下概念能力；名称用于架构讨论，不是已冻结的 Lua 方法名或参数格式：

- **GeneralRegistry**：注册武将并按稳定跨包武将 ID 查询。ID 必须在同一启动 generation 内无歧义，且不能依赖本地路径或加载顺序偶然生成；其具体命名语法尚未冻结。
- **SkinRegistry**：允许当前皮肤包以目标武将 ID 注册额外皮肤描述，包括立绘、技能语音、阵亡语音和动画的逻辑引用。注册不得修改目标武将 definition，也不得取得目标包的写权限。
- **ResourceResolver**：把带来源包身份的逻辑资源引用交给客户端受控解析；Lua 不拼接客户端文件路径，也不读取 QML 资源文件。

皮肤包必须通过 Manifest 依赖目标武将包，按拓扑顺序在目标武将注册后执行。目标武将不存在、依赖未声明或不满足时拒绝皮肤注册。SkinRegistry 必须检测同一目标武将下的皮肤 ID 冲突；M3-C 默认拒绝冲突，不采用加载较晚者覆盖。冲突键的序列化格式、皮肤 ID 语法和 Registry definition 形状仍为 Draft。

皮肤选择不得改变武将规则、技能实现或权威状态。皮肤项不可用时，运行时只保留/恢复目标武将的默认资源语义；具体选择状态归属和跨局持久化协议尚未确定。皮肤包停用只修改下次启动配置，正常重启后新 generation 不再注册其皮肤，武将包无需修改。

## 最小接口草案

```lua
local pkg = Runtime.registerPackage{ id = "org.example.base", version = "1.0.0" }
pkg:registerGameMode{
  id = "standard",
  min_players = 2,
  max_players = 8,
  create_logic = function(game) return GameLogic:new(game) end,
  ui_mode = "standard"
}
return pkg
```

具体 Lua 方法签名、序列化白名单和注册 definition 形状仍为 Implementation Candidate；上文状态与安全语义是实现必须满足的契约。

## Open Questions

- freekill-core 的哪些事件阶段和 utility helper 应成为稳定最小面，哪些保留在兼容包内？
- skill/trigger 热卸载已由 ADR-0009 排除；本 Draft 只保留静态注册与清理 API，不得据此实现运行时包卸载。
- 确定性重放需要记录随机调用还是输入流；建议先记录 seed + 全部已验证输入并做交叉验证。
- 稳定武将 ID 与皮肤 ID 的具体命名语法、皮肤 definition 字段和选择状态归属尚未冻结。
