# Lua Runtime API v1 — Draft

状态：**Draft**。等待 Package Agent 的最小验证包基于 freekill-core/utility 机制完成生命周期、嵌套事件和协程请求验证后再冻结。

本草案抽取概念，不承诺 freekill 原始 API 可原样运行。适配层负责把 GameIPC 数据转换为 Lua 对象，并禁止包直接访问管道、网络连接或宿主文件系统。

## 入口和注册

`server.entry` 模块返回包描述表，通过只读 `Runtime` 注册：

- `registerPackage(definition)`：卡牌、角色、技能及翻译等内容注册；ID 在包命名空间内唯一。
- `registerGameMode(mode)`：模式 ID、人数范围、构建 `GameLogic` 的工厂及客户端 UI mode key。
- 注册只允许在初始化阶段；失败必须回滚该包全部注册。

`Game` 持有玩家、权威状态、确定性随机源和输出路由。生命周期为 `create → initialize → start → finish|fail → cleanup`；cleanup 幂等，终态后禁止新请求。

## 规则对象

- `GameLogic`：模式级状态机，负责初始状态、回合推进、胜负条件和合法动作。
- `GameEvent`：有父事件、阶段、数据、结果和清理栈的事件实例。
- `TriggerEvent`：按优先级和注册顺序确定性分发技能触发器。
- `Request`：异步玩家操作，包含 token、目标玩家、公开提示、每玩家私有数据、deadline 和默认/取消策略。

## 事件语义

事件以栈嵌套；子事件完成或清理后父事件才能恢复。中断是结构化结果，不是任意 Lua 错误：可取消当前阶段、当前事件或向父级传播。无论正常、取消、超时或异常，清理栈均以后进先出执行一次。Lua 异常转换为 `GameFailed`，不得跳过 cleanup。

触发器排序键暂定为 `(priority desc, package load order, registration order)`。触发器不得持有已结束事件的可变引用。所有会改变权威状态的操作必须在游戏调度器上下文执行。

## 异步请求与协程

规则协程调用 `game:request(spec)` 后 yield；Runtime 发出 `PlayerRequest` 并记录 token→协程。收到已验证的 `PlayerReply`、deadline、玩家离线或 Shutdown 时，Runtime 恢复一次，返回 reply 或结构化取消原因。未知/重复/过期 token 拒绝且不得二次恢复。不得在 Lua 主调度线程做阻塞 I/O。

私有选项放在 per-player 数据中；公共事件记录不得包含它。Runtime 只通过带 recipients 的 `GameOutput` 输出视图消息。

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

具体构造器、事件阶段枚举、序列化白名单和取消对象形状均未冻结。

## Open Questions

- freekill-core 的哪些事件阶段和 utility helper 应成为稳定最小面，哪些保留在兼容包内？
- skill/trigger 的热卸载是否支持；建议 M3 对局创建后冻结注册表。
- 确定性重放需要记录随机调用还是输入流；建议先记录 seed + 全部已验证输入并做交叉验证。
