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
- `PackageManifestChanged`：服务端通知，`request_id=0`；只携带新 `manifest_id`，客户端随后发送新请求获取详情。

PackageReady 内嵌错误结构为 `{code, message, retryable, details?}`。不支持包协商的客户端触发必须依赖包的操作时，服务端使用 SGS/1 `Error` 信封，回显该操作的合法 request ID，`data.code` 为 `PACKAGE_PROTOCOL_REQUIRED`，并在 `data.message` 中说明需要 `PackageSync/1`；不得伪装成空清单。是否关闭连接由将来的能力协商设计决定，M3 不擅自改变 SGS/1 Error 的公共字段。

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
- `PackageManifestChanged` 使旧 Ready 状态失效；进行中的旧事务可取消，其结果不得提交。
- 错误可重试仅由 `retryable` 指示；协议/schema/API 不兼容通常不可重试。
- 同步工作必须在工作线程/异步任务中进行，不阻塞客户端 UI 或服务端网络事件循环。

## Open Questions

- 私有仓库凭据分发机制尚未确定；建议 M3 首先只支持管理员预配置的公开仓库或系统凭据助手。
- Git SHA-256 仓库的端到端工具链支持需实测；Schema 已预留 64 位对象 ID。
- 客户端能力协商和 `PACKAGE_PROTOCOL_REQUIRED` 后是否关闭连接尚未纳入 M2；建议 M3 实现前单独形成兼容性决策。
