# QML Extension API v1 — Draft

状态：**Draft**。等待 SgsClient 对真实包的动态加载、销毁、错误回退和多分辨率测试后再冻结。

对于声明了 `client.qml_entry` 的包，客户端从已验证 commit 的包根加载该入口。未声明 QML 入口的服务端包或纯资源包不创建页面。包 QML 运行在受控引擎/导入路径中，不得自行决定 Git 来源或活动 commit。

## 参考适配边界

本轮实际抽查了 FreeKill RoomModel、RoomBase 页面、RequestHandler 和 RequestLifecycle。其模型分层、请求结束时清理 UI、弹窗与数据模型分离可作为参考；直接调用 `ClientInstance.notifyServer/replyToServer`、读取全局 Lua 状态或依赖单一 current request 的方式不得进入 SGS。SGS 页面只能访问宿主注入的 GameViewContext。

## 动态页面加载

1. Manifest/Package Sync 完成后，客户端建立当前锁定包集合的只读 generation；对局期间不切换 generation。
2. GameMode 注册给出 `ui_package_id` 和 `ui_mode`。宿主在该包的 `client.qml_entry` 创建组件，并核对导出的 `packageId`、`apiVersion`、`supportedModes`。
3. 基础 import 只允许 QtQuick、SGS 公开模块、当前包 QML 模块及其声明依赖。依赖根按 Manifest 拓扑顺序加入受控 import path；禁止环境变量或任意本地目录。
4. 组件经历 `Loading → Creating → Active`。解析、import、元数据或初始化失败进入 `Fallback`，显示框架错误页；不得尝试其他 commit 的同名组件。
5. 正常结束、返回大厅、断线或致命错误进入 `Closing → Destroyed`。宿主先撤销 context 能力和信号，再调用 `closing(reason)`，最后 `deleteLater`/销毁 engine 对象。

是否每包独立 QQmlEngine 仍为 Implementation Candidate；无论采用何种 engine，共享 singleton 不得泄漏跨对局可变状态。

## GameViewContext Draft 接口

建议实现为 C++ `QObject` 显式注入根组件的只读 `context` 属性。类型是跨 Agent 实现候选，行为契约如下：

### 只读属性

| 属性 | QML 类型 | 语义 |
|---|---|---|
| `gameId` | string | 当前 game_id |
| `localPlayerId` | string | 当前连接绑定玩家；观察者可为空 |
| `modeId` | string | 当前模式 ID |
| `packages` | list&lt;var&gt; | `{id,version,commit}` 的只读副本 |
| `viewRevision` | string | uint64 十进制字符串，避免 JS 精度损失 |
| `visibleState` | var/object | 仅本玩家可见的当前模型快照 |
| `activeRequests` | var/object | token→只读请求摘要；不含其他玩家 private_data |
| `connectionState` | string | `connected|reconnecting|disconnected|failed` |
| `lastErrorCode` / `lastErrorMessage` | string | 已净化的最近错误 |
| `active` | bool | false 后所有发送方法拒绝 |

### 方法

- `bool sendGameAction(string actionType, var data)`：仅 Active 可调用；宿主添加 game_id、player_id 和网络 request ID，并映射为 GameIPC PlayerAction。
- `bool replyGameRequest(string requestToken, var data, bool cancel)`：token 必须存在、属于本地玩家且未终结；宿主映射为 PlayerReply。返回值只表示本地受理，不代表规则接受。
- `url resolveResource(string packageId, string relativePath)`：只允许当前包或声明依赖，执行路径/符号链接检查后返回只读 `sgspkg://` URL。
- `void dismissError()`：只清理可关闭的展示错误，不改变网络/游戏状态。

### 信号

- `gameStarted()`
- `gameViewUpdated(string revision, bool fullSnapshot, var change)`
- `gameRequestReceived(string token, string requestType, var publicData, var privateData, int deadlineMs)`
- `gameRequestClosed(string token, string reason)`
- `connectionStateChanged(string state)`
- `gameEnded(var result)`
- `errorOccurred(string code, string message, bool fatal)`
- `closing(string reason)`

包 QML 不获得 QTcpSocket、GameClient、连接 Session、Git 凭据、任意文件路径或可变底层模型。方法参数在离开 QML 边界时深拷贝并做大小/类型/权限校验。

## 游戏视图模型

GameIPC GameOutput 使用两个约定 profile，无需新增 IPC 类型：

- `output_type="view_snapshot"`：data 为 `{revision,state}`，建立该接收者的完整可见状态。
- `output_type="view_delta"`：data 为 `{base_revision,revision,patch}`，只在 base_revision 等于本地当前 revision 时应用。

revision 是每个接收者视图独立的 uint64 十进制字符串。规则：

1. 首次进入或页面重建必须有已验证完整快照；客户端不能从 delta 猜测缺失状态。
2. revision 小于等于当前值的重复/迟到更新忽略。delta 出现 gap 或 base 不匹配时冻结交互并由框架请求重新同步；具体 SGS/1 resync 消息尚属 Implementation Candidate。
3. 应用 patch 必须事务化；失败保留旧模型并报告 `VIEW_UPDATE_INVALID`。
4. Lua 为每个 recipients 集合生成恰当视图。手牌、私有选项等只存在于对应玩家 snapshot/delta；客户端不能假定拥有权威全局状态。
5. 页面重建时宿主从缓存的当前可见模型创建新只读快照，并重新发出尚未终结的本地 activeRequests；不得重放已关闭 token。

## Request UI

GameRequest 来自 GameIPC PlayerRequest 的本地目标切片，只包含 public_data 和 `private_data[localPlayerId]`。客户端以 token 为主键，允许多个并发请求；同 token 只提交一次。deadline 到达、服务端关闭、断线或页面销毁时先从 activeRequests 移除，再发 `gameRequestClosed`，随后禁用相关 UI。迟到点击必须在 context 层拒绝，不能触达网络。

包可提供 request_type→QML Component 映射；缺失组件时显示通用 JSON/取消界面，若 cancel_policy 不允许则只显示等待/错误状态。页面不得把一个请求的私有数据复制到日志、全局 singleton 或其他请求。

## 生命周期时序

```text
GameStarted → load component → inject context → full snapshot → Active
Active → GameViewUpdate* / GameRequest* / GameAction|GameReply
Active → GameEnded|disconnect|fatal error → close requests → Closing
Closing → disconnect signals/timers → clear models → destroy page/context
```

- 网络短暂重连时 context 进入 reconnecting，禁用发送；恢复后必须由框架确认 game_id 和视图 revision，不能盲目继续。
- GameEnded 先关闭请求，再交付最终可见结果，随后 closing。
- 销毁后 C++ 不再调用 QML 对象；排队 signal 使用弱引用/guarded pointer，模型和 JS callback 全部释放。

## 资源与扩展

- 图片、声音和动画通过 `context.resolveResource(packageId,path)` 或 `sgspkg://<package-id>/<path>` 引用，不拼接 `file://`。
- 路径必须出现在 Manifest resources 或 QML 入口树下，并通过包根逃逸/符号链接检查。
- QML 组件由包内 `qmldir` 或显式相对 import 定位；模块 URI 必须在包命名空间内。依赖包只能按声明依赖访问。
- 缺资源返回无效 URL 和 `RESOURCE_NOT_FOUND`，不得静默回退到其他包同名文件。
- 活跃对局固定 package generation；资源包更新不热替换现有页面。退出对局并销毁旧 engine/component 后，新对局才使用新 generation。
- 武将皮肤、语音和动态立绘的最终命名/绑定规则本 Draft 不冻结。

## 错误处理

组件缺失、解析失败、API 不兼容或初始化异常时：显示不泄露本地路径/凭据的通用错误页，禁止进入交互状态，记录结构化诊断并允许用户安全返回大厅。不得回退到来自不同 commit 或未在清单中的同名 QML。

## Open Questions

- 首版是否使用独立 QQmlEngine 隔离每个包，需用真实资源和插件导入测试后决定。
- 允许的 QML import 白名单、网络访问和本地存储能力尚需客户端安全评审。
- GameViewContext 的具体 Qt 类型（singleton、context property 或注入对象）未冻结；建议优先可测试的显式注入对象。
