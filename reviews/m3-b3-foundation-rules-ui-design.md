# M3-B3 完整基础规则与 UI 接口设计

- 状态：Approved for staged implementation / Draft interfaces
- 日期：2026-10-27
- 架构基线：SgsArchitecture `55991cd4265678d9df2bd1adb61f73e91164cdde`
- 实现基线：SgsServer `05f4a16155e7a5dbae14c6702c0e4d7a606ed524`；SgsClient `80f525e542fd08ff7232b8fda39fe1d230e32444`（均已核验为 origin/main）
- 研究来源：通过 Agent 3 任务的只读共享记录取得完整、未截断的 `M3-B3-FreeKill-core-pre-port-analysis.md` 与 `M3-B3-FreeKill-base-rules-ui-port-analysis.md` 文件变更内容；未直接访问其独立工作目录。

## 1. 结论

M3-B3 采用“通用规则内核 + 资源包内容”的分层：Lua Runtime 提供权威状态、区域移动、事件、触发、请求和确定性执行能力；资源包注册卡牌身份、条件、目标、效果、技能和展示元数据。SgsServer/SgsClient 不为杀、闪、某件武器或某张锦囊增加专用 C++ 分支。

GameIPC/1 的九种消息和 Schema 足以承载本阶段：PlayerAction、PlayerRequest/Reply 和 GameOutput 已提供通用 data。基础游戏视图进入现有 `view_snapshot`/`view_delta` 的 `sgs.foundation-view/1-draft` profile，不新增顶层消息，也不修改 SGS/1。业务 profile 尚未冻结；外层 `ipc_version: "1"` 保持不变。

## 2. FreeKill 研究结论如何进入 SGS

### 可借鉴的行为与设计

- 父子 GameEvent、child-before-parent、LIFO cleanup、prepare/run/cleanup/exit 生命周期。
- Trigger 的 refresh → normal → late-refresh、优先级、重复次数和 break/cost 语义。
- 多目标 Request、逐玩家私有数据、默认回复、all/first/quorum 和只恢复一次。
- CardUse/CardResponse/CardEffect、MoveCard、Judge、Damage/Recover/Dying/Death 的职责分层。
- 装备安装/卸载、距离/攻击范围修正、延时锦囊判定及属性伤害连环的行为顺序。
- UI 由公开装备区、判定区和 chained 状态驱动；短名称来自元数据。

### 必须适配或重新实现

- Lua 调度器、Game facade、注册表、确定性 RNG、事件错误/终态、Request token 和私有视图。
- FreeKill Lua 中紧耦合 `Room`/`RoomInstance`、`Fk/fk`、serverplayer、C++ timer、CBOR、AI 与客户端对象的部分。
- SgsServer 的 IPC/进程/计时/身份/路由，以及 SgsClient 的 Qt 模型、GameViewContext、QML 宿主和 ResourceResolver。
- 目录扫描、全局资源枚举和“先找到者覆盖”必须替换为 Manifest 依赖、owner package 和当前 generation 的精确根映射。

研究确认基础牌、普通与延时锦囊、11 件武器、4 件防具、7 匹坐骑及通用事件链均有参考实现；宝物类型与 UI 槽存在，但研究范围内没有实际宝物牌。参考归档只有三张测试武将图片，没有可直接交付的正式卡面、装备、延时锦囊、锁链、音频或动画素材。

## 3. 状态所有权与最小对象关系

```text
locked package generation
  └─ immutable registries: GameMode / CardDefinition / Skill / Event / Trigger
       └─ Game (one Runtime process, one authoritative instance)
            ├─ ordered roster: Player[2..8]
            │    ├─ hand (private)
            │    ├─ equipment[EquipSlot] (public)
            │    └─ judge area (public)
            ├─ draw pile / discard pile / processing / void
            ├─ turn + phase + event stack + cleanup stack
            ├─ active requests and deterministic RNG
            └─ observer-specific view projection
```

| 对象 | 所有者与最小关系 | 扩展边界 |
|---|---|---|
| GameMode | generation registry；声明 ID、2–8 人范围、logic factory、UI package/mode | 胜负、阵营、牌堆构建等由模式/规则包扩展；具体 Lua 签名不冻结 |
| Game | 单个 Lua 进程唯一；持有 roster、区域、回合、事件、请求、RNG 和终态 | 不持有 Session/socket；C++ 保管身份绑定 |
| Player | Game 持有；`id`/seat 只读且唯一；规则状态含 alive、hp/max_hp、phase、chained、区域引用 | 连接状态由 C++ 转换为输入或 Request resolution |
| Card Definition | 初始化期由 owner package 注册并冻结；包含稳定 definition ID、种类/子类、行为与展示元数据 | 新牌和新装备只注册 definition/skill，不要求改 C++ |
| Card Instance | Game 在牌堆构建时创建；局内唯一 instance ID，引用 definition，包含花色/点数和当前 zone | 虚拟/转化牌使用 definition + subcard IDs 的瞬时 CardRef，不伪造持久实例 |
| GameEvent | GameLogic 创建；含 event ID、parent、类型、状态和类型化 data | 事件 data 由注册事件定义；外部只获得只读投影 |
| TriggerEvent | 当前事件的确定性触发调度对象 | condition/cost/effect 是包逻辑，C++ 不解释 |
| Request | Runtime token 表和等待协程持有；父进程镜像目标/deadline 权威表 | request_type/data profile 可由包扩展，但必须经大小、目标和权限验证 |

稳定 definition ID 必须可跨包无歧义引用，但本轮不冻结其字符串语法。注册项始终携带 owner package；跨包扩展必须有 Manifest 依赖。

## 4. 卡牌区域和移动

最小区域集合：

| Zone | 所有权/顺序 | 可见性 |
|---|---|---|
| `draw_pile` | Game，有序 | 数量公开；顺序和牌面隐藏 |
| `hand` | Player，有序 | owner 可见实例；其他玩家只见数量 |
| `equipment` | Player，按 EquipSlot 唯一占位 | 公开 |
| `judge` | Player，有序 | 公开，用于延时锦囊 |
| `processing` | Game/event，有序 | 由事件决定公开范围；不能泄露仍属私有选择的牌 |
| `discard_pile` | Game，有序 | 公开 |
| `void` | Game/规则内部 | 默认不展示，用于移出游戏或尚无区域的实例 |

所有区域变更必须由通用 MoveCards 事件完成，并记录稳定 move/event ID、来源、目的、原因、可选 actor/skill/card-use 关联。批量移动原子验证后提交；失败不得留下卡牌同时存在于两个区域。装备替换、判定牌进入 Processing、实体牌清理和弃置都使用同一移动能力。

## 5. 通用规则与卡牌扩展

### 通用 Runtime 能力

- Turn/Phase：开始、阶段转换、跳过和结束；具体阶段集合由 GameMode 注册，首个标准 profile 至少支持 Start/Judge/Draw/Play/Discard/Finish。
- CardUse：验证使用者、CardRef、目标和次数，创建逐目标 CardEffect，并在终态清理实体牌。
- CardResponse：在既存请求/效果上下文中提供响应牌或技能产生的 CardRef。
- CardEffect：处理抵消、响应与具体 definition effect；无懈链属于通用锦囊效果流程的可扩展响应。
- Damage/Recover：结构化来源、目标、数值、属性、card/skill/event 关联；任何修正后再提交权威状态。
- Dying/Death：hp 进入阈值后发起救援序列，成功则退出濒死，失败则死亡和清理；桃/酒只参与通用流程。
- Judge：判定牌进入 Processing、改判、最终结果、清理，以及延时锦囊的弃置/转移/阶段跳过。
- Equip：替换同槽装备、旧装备 uninstall、新装备 install；失效状态影响技能但不改变区域事实。
- Distance/AttackRange：基于存活座次环和稳定 modifier 顺序；+1/-1 马分别修正目标/来源，武器提供声明范围，技能可做受控修正。
- ChainState：Player 的权威 `chained` 布尔状态；可传导属性伤害按稳定座次生成子 Damage，每个子事件仍完整经过伤害/濒死/死亡链。

### 资源包注册职责

资源包为杀、闪、桃、酒、普通锦囊、延时锦囊、武器、防具、+1/-1 坐骑和未来宝物注册 definition、目标/使用条件、效果和技能。Runtime 只提供上述通用原语与安全边界。武器技能、防具技能、ViewAs/Trigger/Distance/AttackRange modifier 都是注册扩展，不进入 SgsServer/SgsClient 专用代码。

`EquipSlot` 的语义集合进入 Implementation Candidate：`weapon`、`armor`、`offensive_ride`（-1 马）、`defensive_ride`（+1 马）、`treasure`。包可注册未来装备子类，但新增会影响通用布局时必须先版本化 view profile。

## 6. 客户端表现 profile

权威 Lua 状态先按观察者裁剪，再放入 GameOutput。Draft profile 标识为 `sgs.foundation-view/1-draft`；它位于 `view_snapshot.data.state.profile`，不是新的 IPC 消息或版本。

最小 snapshot 语义：

```json
{
  "profile": "sgs.foundation-view/1-draft",
  "mode_id": "standard",
  "turn": {"player_id":"p1","phase":"play"},
  "card_definitions": {
    "opaque-card-id": {
      "owner_package_id":"org.example.cards",
      "display_name":"青龙偃月刀",
      "short_name":"青龙刀",
      "card_type":"equipment",
      "equip_slot":"weapon",
      "weapon_range":3,
      "icon":{"package_id":"org.example.cards","path":"client/images/cards/blade.png"}
    }
  },
  "players": [{
    "player_id":"p1","seat":1,"alive":true,"hp":4,"max_hp":4,
    "hand_count":2,"hand_cards":[],"equipment":[],"judge":[],"chained":false
  }]
}
```

- `hand_cards` 只允许出现在有权观察该手牌的 projection；其他玩家始终只有 `hand_count`。不得以空数组模糊“无牌”和“不可见”。实现应使用显式可见性或直接省略私有字段，最终形状在 B4 信息流测试后冻结。
- equipment/judge 项至少包含 instance ID 和 definition ID；展示元数据由 `card_definitions` 提供，避免客户端按特定卡牌 ID 硬编码。
- ResourceRef 固定语义为 `{package_id,path}`；commit 来自当前 GameViewContext 的只读 packages/generation 映射，不在业务 payload 中接受客户端选择。解析前验证依赖、活动 commit、包根、声明路径和逃逸规则。
- `weapon_range` 是武器 definition 的声明范围，用于装备条展示；当前是否可攻击某目标只由服务器合法动作/请求决定，客户端不得据此自行授权。
- `view_delta.data.patch` 必须能事务更新同一 profile，具体 patch 编码仍为实验项。破坏性业务形状变化使用新的 profile 字符串；只有外层帧/信封/消息语义不兼容时才考虑新 `ipc_version`。

## 7. 指定武将框 UI

### 延时锦囊

判定区中的每个公开 Card Instance 显示 definition 提供的图标/标记。权威 MoveCards 将其移出、转移或结算后，下一个 snapshot/delta 必须移除对应实例，QML 不维护独立副本。资源缺失使用框架安全占位并记录非致命诊断。

### 装备矩形栏

视觉顺序按“从底至上”定义：

- 无宝物：`-1 马 → +1 马 → 防具 → 武器`。
- 有宝物：`宝物 → 合并坐骑栏 → 防具 → 武器`。

合并坐骑栏只是 QML 布局容器，仍包含两个独立 slot/instance。矩形装备项使用资源包提供的 display/short name 和图标；武器额外显示声明 `weapon_range`。雌雄双股剑→雌雄剑、青龙偃月刀→青龙刀属于包元数据示例，不得进入客户端 C++ 名称表。

### 铁索连环

武将框中央锁链标记只绑定玩家公开 `chained`。状态变 false 时随同一视图事务消失；动画不能延迟权威状态，也不能触发规则。锁链资源可由基础规则包或框架 fallback 提供，但必须是显式 ResourceRef，不能全局扫描同名文件。

## 8. M3-B3 最小实施步骤

| 步骤 | 输入 | 输出 | 最低验收 |
|---|---|---|---|
| B3.1 状态与区域 | B2 Game/roster/generation、确定性 RNG | Player 状态、Card Definition/Instance/CardRef、七类 zone、原子 MoveCards | 固定 seed 构建牌堆；抽/弃/手牌私有；重复实例或非法区域移动拒绝；2–8 roster 不硬编码 2 |
| B3.2 Event 与阶段 | B3.1 | GameEvent 生命周期、Turn/Phase、CardUse/Response/Effect、Damage/Recover/Dying/Death/Judge 骨架 | child-before-parent、LIFO cleanup、阶段跳过、伤害至死亡链；异常仍 cleanup once |
| B3.3 Trigger 与 Request | B3.2、现有 PlayerRequest/Reply | 稳定触发顺序、condition/cost/effect、all/first/quorum、协程桥 | reply/cancel/timeout/disconnect/shutdown/default；未知/非目标/重复/迟到拒绝；只恢复一次；网络循环不阻塞 |
| B3.4 基本牌闭环 | B3.3 | 杀/闪/桃/酒规则包接入 | 使用→响应→伤害/回复/濒死救援；实体牌清理正确；无 C++ 卡牌分支 |
| B3.5 锦囊与判定 | B3.4 | 普通锦囊公共流程、无懈响应、延时锦囊/Judge/改判/阶段跳过/转移 | 单目标、AOE、五谷/Processing、无懈链、闪电/乐/兵粮；判定区状态随移动一致 |
| B3.6 装备、距离与连环 | B3.5 | 五槽 Equip、install/uninstall、Distance/Range、装备技能、属性/连环伤害 | 武器/防具/坐骑替换与失效；宝物空槽可扩展；连环传播顺序稳定且无重复伤害；生成 headless foundation snapshot |

每一步只运行覆盖新增风险的定向测试。8 人架构边界在 B3.1/B3.3 验证，完整 8 客户端真实对局仍是最终功能验收，不在每个子步骤重复。

## 9. B3/B4/M3-C 分界

- **M3-B3**：Lua 权威状态、规则原语、事件/触发/请求、基础卡牌规则包接入，以及 headless snapshot 生成。允许设计表现 profile，但不要求 Windows QML 页面运行。
- **M3-B4**：逐玩家 snapshot/delta 信息流证明、recipient 路由、确定性、异常退出、背压、日志净化和资源回收；在此阶段冻结足够稳定的 foundation view profile 候选。
- **M3-C**：SGS/1 客户端游戏动作/请求/视图协议、Qt 模型、动态 QML、delta/resync、重连/观察者、武将框实际布局、ResourceResolver 和皮肤绑定运行验证。

## 10. Agent 职责

| Agent | 职责 | 禁止越界 |
|---|---|---|
| Agent 1 / Linux | GameIPC bridge、C++ token/deadline/身份/recipient 校验、非阻塞管道、失败回收、通用 Runtime 宿主 | 不实现具体卡牌/技能或在主进程跑 Lua |
| Agent 2 / Windows | M3-C 的 GameViewContext、模型、ResourceResolver、矩形装备/判定/锁链 QML 生命周期 | 不计算牌效/距离/伤害，不硬编码卡牌名或跨包扫描 |
| Agent 3 / Package | GameLogic/Event/Trigger/Request 的 Lua 内容适配、基础规则/卡牌/装备包、展示元数据、headless 规则测试 | 未获授权不得复制 FreeKill 源码/素材；不得构造 IPC 信封或访问 Session |
| Agent 4 / Architecture | 状态机、数据边界、profile、职责、许可决策和验收证据 | 不替其他 Agent 开发业务代码或提前冻结实验接口 |

## 11. FreeKill 许可路线决策清单

### 路线 A：GPLv3 条件下适配复用源码

成本/限制：行为接近参考实现且初期规则开发较快，但需要逐文件确定来源、上游 URL、精确 commit/tag、版权作者、许可证和改动记录；分发衍生代码时保留通知、GPLv3-or-later 条款及相应源码义务，并评估与同仓库其他代码/链接边界的许可证影响。当前 ZIP 只有 SHA-256、没有 commit，**在补齐来源并获得用户确认前不得复制**。代码许可也不能证明图片、音频、字体或动画可用，素材仍需逐项授权。

### 路线 B：依据行为需求独立实现 SGS

成本/限制：需要自行实现并用行为测试追平规则顺序，工作量和初期偏差风险更高；优点是对象模型、IPC、安全边界与许可证可由 SGS 自主控制。应保存需求报告、设计记录和独立测试证据，避免逐行、机械翻译或保持原实现独特结构。必要时由独立实现人员只消费行为规格而不复制源码。

共同要求：建立 provenance/NOTICE 清单；素材与代码分开审计；任何正式移植任务先向用户列出具体文件、来源 revision、许可证、目标文件和替代方案并等待确认。本文件不是法律意见，疑难事项由维护者或法律顾问判断。

## 12. 尚未冻结与风险

- Lua registerCard/registerEvent/registerTrigger 的最终函数签名、definition ID 语法、事件 data 结构和 modifier API。
- foundation view 的私有字段表达、delta patch 编码、卡牌翻译键/文本分发方式和客户端 resync。
- 虚拟牌/CardRef、无懈多层交互、完整事件历史、AI/托管、投降和观察者行为。
- 通用锁链/占位图归框架还是基础资源包，实际素材授权和 NOTICE。
- GPL 衍生适配或独立实现路线尚未由用户选择；现阶段只允许接口设计和行为研究。

上述未决项不阻塞按 B3.1→B3.3 建立通用状态、事件和 Request 基础，但在开始复制 FreeKill 源码或冻结客户端 profile 前必须解决相应决策。
