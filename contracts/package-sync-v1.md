# Package Sync v1 over SGS/1

状态：M3 实现基线。Schema：`schemas/package-sync.schema.json`。

本协议只增加 SGS/1 消息类型，不改变 SgsServer `v0.3.0-m2` 的传输和公共信封。权威基线为 SgsServer `docs/protocol.md`：四字节无符号大端长度帧，JSON 正文 1–65536 字节、UTF-8 且无 BOM。SGS TCP 不传输 Git 仓库内容。

## SGS/1 信封

每条消息严格包含且只包含以下公共字段：

```json
{"protocol":1,"type":"GetPackageManifest","request_id":21,"data":{}}
```

- `protocol`：整数，固定为 `1`。
- `type`：区分大小写的字符串。
- `request_id`：客户端请求为整数 `1..2147483647`；响应原样回显请求值；服务端主动通知固定为整数 `0`。
- `data`：JSON 对象。

客户端不得发送 `request_id: 0`，同一连接内尚未完成的请求不得复用 ID。Package Sync 不使用 `payload`，也不把 request ID 编码成字符串。公共字段非法时沿用 SGS/1 的关闭/错误规则。

## 消息

- `GetPackageManifest`：请求，`data.known_manifest_id` 可选。
- `PackageManifestResult`：响应，返回 `manifest_id`、有序 `packages` 和 `sync_timeout_ms`。
- `PackageReady`：请求，客户端完成原子切换后回报 `manifest_id`。
- `PackageReadyResult`：响应，`data.ready=true`；失败时 `ready=false` 并带结构化 `error`。
- `PackageManifestChanged`：预留服务端通知，`request_id=0`；只携带新 `manifest_id`。M3 保留 Schema，但管理员包操作不会触发该消息。

PackageReady 内嵌错误结构为 `{code, message, retryable, details?}`。SGS/1 公共错误继续使用标准 `Error` 信封和 `{code,message}` data，不混用内嵌错误结构。

## 服务端有效清单生命周期

Package Sync 遵循 **restart-required activation**。SgsServer 明确区分三类状态：磁盘注册表中的“下次启动期望配置”、当前进程的“启动时有效清单”、客户端本地缓存。管理员添加、更新、启用或停用包，只原子更新第一类状态；不得改变当前进程的有效清单或 `manifest_id`。

正常启动时，服务器读取一次期望配置，验证 commit、Manifest、依赖、API 兼容性和单帧大小，计算 `manifest_id`，然后锁定不可变 package generation。所有 Package Sync 响应及本进程创建的 Lua 游戏均只引用该 generation。运行期间不轮询目录/注册表，不热加载、热卸载、热替换或后台自动重载。新配置只在下一次正常重启并通过完整验证后生效。

`PackageManifestChanged` 仅为未来版本预留。本版本不会因为管理操作发送它，也不会在运行时产生新的有效清单。若未来版本启用该通知，必须另立 ADR 并定义 generation 切换与在局安全语义；不得把预留消息解释为已有热更新能力。

## 连接兼容性与大厅门禁

每条新连接的包状态从 `NotReady` 开始，并与临时用户身份一样只属于该 TCP Session：

1. 原有 `Hello`、`Ping`、`Echo` 行为不变；未同步客户端仍可完成握手、Ping 和 Echo。
2. 新客户端在 `EnterLobby` 前必须完成 `GetPackageManifest → PackageManifestResult → PackageReady → PackageReadyResult`。
3. 服务端只在收到与当前有效清单相同的 `PackageReady.data.manifest_id` 后把连接标记为 `Ready`。摘要不匹配返回 `MANIFEST_ID_MISMATCH`，状态保持 `NotReady`。
4. 空清单也必须完成同一往返；不能因为 `packages` 为空而隐式 Ready。
5. `NotReady` 客户端发送 `EnterLobby` 时，服务端返回标准 SGS/1 `Error`，回显该请求 ID，`data.code` 为 `PACKAGE_PROTOCOL_REQUIRED`。写完错误后默认保持 TCP 连接，允许客户端继续协商。
6. 未 Ready 的连接不得进入大厅、创建房间或加入房间。CreateRoom/JoinRoom 仍需原有大厅状态，并额外要求当前清单 Ready。
7. 断线立即清除该 Session 的 Ready 状态；重连从 NotReady 开始，不复用旧连接确认。
8. 客户端每次重连都从 NotReady 开始，重新获取启动时有效清单并执行版本同步；本版本不依赖缓存摘要直接恢复 Ready。
9. 预留语义仍规定：若客户端收到合法 `PackageManifestChanged`，必须置为 NotReady 并重新协商；但 M3 服务端不发送该通知。

该门禁使不知道 Package Sync 的旧客户端仍可使用原有握手和诊断消息，但无法进入 M3 大厅，不需要修改 Hello 信封或主动关闭连接。

## manifest_id

摘要输入仅为 `PackageManifestResult.data.packages` 的规范副本，每项必须且只能包含以下七个字段：`id`、`version`、`api_version`、`repository_url`、`commit`、`manifest_sha256`、`dependencies`。

计算步骤固定如下：

1. 验证所有字段、包 ID 唯一性和依赖 ID 唯一性。
2. 因 package ID 被限制为 ASCII，将 `packages` 按 `id` 的 ASCII 字节升序排列；将每项 `dependencies` 同样按 ASCII 字节升序排列。
3. 不加入 SGS/1 信封、`manifest_id`、`sync_timeout_ms` 或任何本地状态。
4. 使用 RFC 8785 JSON Canonicalization Scheme 生成规范 JSON 字节。字符串输出编码固定为 UTF-8 且无 BOM；对象键排序和数字序列化完全遵循 RFC 8785，不允许用普通 pretty printer 或仅设置 `sort_keys` 代替。
5. 对规范字节计算 SHA-256，输出 64 位小写十六进制。

空清单的输入是两个 ASCII 字节 `[]`，预期 SHA-256 为 `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`。

跨端实现必须采用通过 RFC 8785 官方序列化向量的实现：Linux C++ 可使用通过相同向量验证的 JCS 库，Windows Qt 不得依赖 `QJsonDocument` 的默认输出格式。仓库测试使用专用 `rfc8785` 实现，并把 RFC 8785 第 3.2.2 节输入同时与公开预期规范字节及预期 SHA-256 比较。

每项 `commit` 必须是完整的 40 位 SHA-1 或 64 位 SHA-256 小写对象 ID，不接受分支、标签或缩写。`manifest_sha256` 是该 commit 中 `manifest.json` 原始字节的 SHA-256。Git URL 与 commit 来自服务器安装注册表。

## SGS/1 单帧大小

`PackageManifestResult` 必须放入一个 SGS/1 帧，Package Sync v1 不分页、不分片：

1. 服务端先完成清单 Schema/依赖验证和 `manifest_id` 计算。
2. 随后使用实际发送所采用的 JSON 序列化器，编码完整 `{protocol,type,request_id,data}` 消息。
3. 只计算 UTF-8 JSON 正文字节，不含四字节长度头；结果必须在 `1..65536` 字节。
4. 若超过 65536 字节，禁止发送、截断或拆帧；该下次启动候选不能成为有效清单，`PACKAGE_MANIFEST_TOO_LARGE` 记入管理/启动诊断，并保留上一份 last-known-good 有效清单及其摘要。
5. 若请求处理阶段仍检测到该内部配置错误，服务端返回能够放入单帧的标准 SGS/1 `Error`，code 为 `PACKAGE_MANIFEST_TOO_LARGE`；连接保持可用。

大小取决于完整 JSON 的实际 UTF-8 编码，包括信封、仓库 URL、包 ID、依赖和转义字符，不得仅以包数量估算。管理员工具应在写入下次启动期望配置前执行同一编码检查；服务器启动激活仍必须复验。本版本不引入分页协议。

## 客户端事务

1. 比较 `id`、`version`、`commit`、`manifest_sha256` 和 `api_version`；仅目录同名不算已安装。
2. 在应用专用临时目录获取缺失 commit；禁止凭据写入日志。设置总超时 `sync_timeout_ms`，单仓库失败不延长总期限。
3. 验证 commit 对象、`manifest.json` 哈希、Manifest Schema、包 ID/版本/API 和完整依赖图。
4. 在同一文件系统内原子切换活动集合，保留上一集合用于回滚。
5. 加载探测成功后删除过期临时状态并发送 `PackageReady`；失败则回滚并发送/记录对应错误。

`PackageReady.data.manifest_id` 必须等于连接当前要求值。否则返回 `MANIFEST_ID_MISMATCH`、`ready=false`，客户端不得进入需包的房间/对局。

## 生命周期和故障

- 空 `packages` 是合法要求；客户端应原子切换到空的服务器要求集合（内建框架资源不受影响）并 Ready。
- 超时、Git 失败、哈希失败、依赖失败或不兼容均使事务失败，不破坏上一个可用集合。
- 客户端断线时，服务端取消该连接的待处理请求/计时器和 Ready 状态；客户端清理未提交临时目录，已验证缓存可保留。
- 当前进程的有效清单不变，因此管理员操作不取消已 Ready 连接或进行中的同步；`PackageManifestChanged` 的失效语义仅为未来协议预留。
- 重启会关闭旧连接；客户端重连后必须重新 Get/同步/Ready，即使本地缓存的 `manifest_id` 与新响应相同。
- 错误可重试仅由 `retryable` 指示；协议/schema/API 不兼容通常不可重试。
- 同步工作必须在工作线程/异步任务中进行，不阻塞客户端 UI 或服务端网络事件循环。

## Open Questions

- 私有仓库凭据分发机制尚未确定；建议 M3 首先只支持管理员预配置的公开仓库或系统凭据助手。
- Git SHA-256 仓库的端到端工具链支持需实测；Schema 已预留 64 位对象 ID。
