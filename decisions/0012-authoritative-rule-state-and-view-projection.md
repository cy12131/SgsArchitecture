# ADR-0012: Lua 权威规则状态与按玩家裁剪的表现投影

- 状态：Accepted
- 日期：2026-10-27

## Context

M3-B3 需要支持基础牌、锦囊、装备、回合、判定、伤害、濒死、死亡和连环机制，同时允许资源包持续增加普通卡牌和装备。如果 C++ 主服务器或客户端按具体卡牌解释规则，框架会重新与内容耦合；如果 QML 从本地资源或动画反推规则状态，则会产生权威性和隐藏信息风险。

Agent 3 对 FreeKill 的研究表明，其可复用价值主要是统一事件层上的行为分层与顺序；原始 `Room`、`Fk`、`ClientInstance`、CBOR、目录扫描和全局资源查找不适合 SGS 的独立进程、GameIPC 和包隔离边界。

## Decision

- 每局 Lua Runtime 持有唯一权威 Game、Player、Card Instance、区域、事件、请求和规则状态。SgsServer C++ 只负责进程监管、身份/目标验证、计时、IPC 和网络路由，不解释具体牌效。
- 资源包在初始化期注册不可变 Card Definition、GameMode、Skill 和展示元数据；具体杀、闪、锦囊、武器、防具、坐骑及宝物行为属于规则包。
- 客户端只消费 Lua 按观察者权限生成的 `view_snapshot`/`view_delta`。装备、判定区、连环标记和阶段 UI 均由可见状态投影驱动，不能成为第二份规则真相。
- GameIPC/1 继续使用现有九种消息。基础游戏状态放在版本化的 `sgs.foundation-view/1-draft` view profile 内；新增普通卡牌不得增加 C++ 专用消息或硬编码名称。
- 资源引用使用 package ID 与包内相对路径，并由当前 generation 的 `(package-id, commit, package-root)` 映射解析，遵守 ADR-0009、ADR-0010、ADR-0011。

## Consequences

- 新卡牌、装备和模式原则上只修改资源包；框架提供通用状态、事件、请求、视图和资源解析能力。
- Lua 必须生成每玩家视图，C++ 必须验证 recipients 并精确路由；客户端不能获得未授权手牌或私有候选。
- M3-B3 可用 headless 驱动验证规则闭环；私有投影与异常加固归 M3-B4，正式客户端协议与动态 QML 渲染归 M3-C。
- View profile 在 Draft 期可版本化演进；若未来只改变 `state`/`patch` 业务形状，优先升级 profile，而不是改变 GameIPC 外层信封。
