# QML Extension API v1 — Draft

状态：**Draft**。等待 SgsClient 对真实包的动态加载、销毁、错误回退和多分辨率测试后再冻结。

客户端从已验证 commit 的包根加载 `client.qml_entry`。包 QML 运行在受控引擎/导入路径中，不得自行决定 Git 来源或活动 commit。

## 注册与选择

宿主读取组件导出的元数据：`packageId`、`apiVersion`、`supportedModes`，并为每个 `(packageId, modeId)` 注册页面工厂。服务端模式描述给出 UI mode key；宿主只在当前锁定包集合中选择兼容项。重复注册、API major 不兼容或缺失模式组件进入通用错误页，不加载任意候选。

## 页面契约

根页面接收只读 `GameViewContext context`：

- `gameId`、`localPlayerId`、只读玩家公开信息和当前 mode key。
- `resolveResource(relativePath)`：仅返回当前包根内的 URL，应用与 Manifest 相同的路径逃逸/符号链接限制。
- `sendAction(actionType, payload)`：发送用户意图；宿主添加身份、序列和游戏 ID，QML 不能覆盖。
- `viewMessageReceived(message)`：仅投递服务端已定向给本地玩家的视图消息。
- `connectionStateChanged(state)` 和 `closing(reason)` 生命周期通知。

页面状态：`Creating → Active → Closing → Destroyed`。只有 Active 可发送动作。离开对局、断线、包集合变化或加载失败时，宿主先调用 closing，断开信号并取消页面计时器/待处理回调，再销毁对象；销毁必须幂等。页面不得在销毁后保留 context。

## 错误处理

组件缺失、解析失败、API 不兼容或初始化异常时：显示不泄露本地路径/凭据的通用错误页，禁止进入交互状态，记录结构化诊断并允许用户安全返回大厅。不得回退到来自不同 commit 或未在清单中的同名 QML。

## Open Questions

- 首版是否使用独立 QQmlEngine 隔离每个包，需用真实资源和插件导入测试后决定。
- 允许的 QML import 白名单、网络访问和本地存储能力尚需客户端安全评审。
- GameViewContext 的具体 Qt 类型（singleton、context property 或注入对象）未冻结；建议优先可测试的显式注入对象。
