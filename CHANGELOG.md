# Changelog

## 0.3.3-draft - 2026-10-26

- 审查 SgsServer `PackageManager` 与 SgsClient `PackageInstaller` 的真实安装路径，确认新安装均已使用 `installed/<package-id>/<commit>/` 隔离目录。
- 规定注册表、锁、staging、缓存和激活元数据不得作为资源包内容或被 Lua/QML 扫描加载。
- 补充旧平铺/混合布局、重复与未知文件、污染缓存、事务迁移和失败回滚策略；无法证明归属时从锁定 commit 重新获取，不按文件名猜测。
- 明确目录规范不改变 Manifest Schema、SGS/1、GameIPC/1、`manifest_id`、依赖拓扑或重启生效机制。

## 0.3.2-draft - 2026-10-26

- 正式记录单局最多 8 名玩家、具体人数由模式决定；`org.sgs.testmode` 的两人约束不代表框架限制。
- 确认现有 GameIPC roster/seat、Request 和 GameOutput 上限已覆盖 8 人，无需新增消息类型或修改信封。
- 收紧 M3-B2 范围：真实 Runtime、generation、Init/GameReady、模块宿主和有界 stdout/stderr；完整 GameLogic/Event/Trigger/Request 留给 B3。
- 新增 8 人 InitGame 与 8 目标 quorum Request 正例，并加入最终 8 客户端功能验收和风险驱动性能测试约束。

## 0.3.1-draft - 2026-10-26

- 完成 M3-B 启动前接口审查，划分 B1 进程监管、B2 Runtime 启动、B3 Request/Event Bridge、B4 私有视图与加固。
- 为 InitGame 补充 uint64 十进制字符串 `room_id`，明确 game/room/generation/roster 启动绑定。
- 澄清双向 sequence、token 所有权、相对 deadline、PlayerAction/PlayerReply 身份规则、GameReady 转 Running 和私有视图路由。
- 使 GameIPC Schema 校验 view_snapshot/view_delta profile，并新增绑定/sequence 边界向量。
- 记录 `org.sgs.testmode` Mock 与真实 Runtime 的适配差异、M3-B/M3-C 分界、职责和逐阶段验收门槛。

## 0.3.0-draft - 2026-10-26

- 归档 M3-A 双端真实跨设备集成验收；SgsServer/SgsClient 阶段标签 `v0.4.0-m3a` 已核验指向各自给定 main。
- 记录 CNB `org.sgs.testmode` 公开仓库、锁定 commit、首次下载、重复连接缓存复用和 PackageReady 门禁结果。
- 记录双 GUI 大厅/房间/准备状态回归，以及服务端 Debug、ASan/UBSan 和客户端 Debug、Release 全通过计数。
- 明确 Lua GameIPC、动态 QML、跨包皮肤运行时仍未完成，以及 CNB IPv6 TLS、下载超时/资源配额和真正服务器驱动版本升级联调等后续事项。
- 新增 M3 架构进度文档、M3-A 验收记录和对应静态一致性检查。

## 0.2.2-draft - 2026-10-25

- 确立独立皮肤包可通过稳定跨包武将 ID 扩展其他包中既有武将的长期架构要求。
- 在 Lua/QML 草案中规划 GeneralRegistry、SkinRegistry 和 ResourceResolver 能力及冲突、依赖、加载和安全回退语义。
- 明确不冻结武将 ID 语法、皮肤文件命名、动态皮肤格式或具体方法签名。
- 增加 M3-C 独立皮肤包动态验收项和静态文档一致性检查。

## 0.2.1-draft - 2026-10-25

- 采用 restart-required package activation；管理操作只写磁盘期望配置，不改变当前服务器进程的有效清单。
- 规定 SgsServer 启动时验证并锁定单一 package generation，所有 Lua 对局均使用该 generation。
- 将 `PackageManifestChanged` 保留为协议预留消息，但 M3 不因管理操作发送，也不实现热卸载、热替换或后台自动重载。
- 增加重启生效状态向量和静态一致性检查。

## 0.2.0-draft - 2026-10-25

- 细化独立 Lua 进程启动、Game/GameEvent/TriggerEvent、Content 注册和清理语义。
- 定义多玩家 Request Bridge 状态机、超时/default/断线/重复回复及协程一次恢复规则。
- 细化 QML 动态加载、GameViewContext、snapshot/delta、并发请求、资源和销毁生命周期。
- 扩展 GameIPC InitGame、GameReady、PlayerRequest 和 PlayerReply 字段，并确认九种消息覆盖 Draft API。
- 新增最小双人桥接包、失败场景、三 Agent 接口矩阵和动态集成清单。

## 0.1.2-draft - 2026-10-25

- 明确旧客户端仍可 Hello/Ping/Echo，但在 PackageReady 前以 `PACKAGE_PROTOCOL_REQUIRED` 阻止 EnterLobby 且不断开连接。
- 明确空清单、断线和清单变化的 Ready 状态规则。
- 规定 PackageManifestResult 按实际 UTF-8 JSON 正文字节执行 65536 字节单帧限制，超限以 `PACKAGE_MANIFEST_TOO_LARGE` 拒绝启用。
- 增加正常边界、超限、兼容性错误和空清单确认测试。

## 0.1.1-draft - 2026-10-25

- 修复 Package Sync 信封以严格匹配 SGS/1：整数 `protocol: 1`、整数 request ID、对象 `data`、通知 ID 0。
- 统一包清单文件名为 `manifest.json`，允许双端、仅服务端、仅客户端和纯资源包。
- 使用专用 RFC 8785 实现并加入 RFC 官方序列化与排序向量。
- 增加跨契约字段冲突、请求 ID 边界和入口组合测试。

## 0.1.0-draft - 2026-10-25

- 建立 Package Manifest v1、Package Sync v1、GameIPC/1。
- 建立 Lua Runtime API v1 Draft 与 QML Extension API v1 Draft。
- 增加三份 JSON Schema、正反例、语义测试和七份 ADR。
- 明确 Draft API 尚未冻结，等待最小包和真实 UI 加载验证。
