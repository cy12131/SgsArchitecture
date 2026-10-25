# Package Sync v1 over SGS/1

状态：M3 实现基线。Schema：`schemas/package-sync.schema.json`。

本协议增加包协商消息，不改变 M1/M2 的 SGS/1 四字节大端长度帧、UTF-8 JSON、连接/认证/房间消息和既有错误行为。SGS TCP 不传输 Git 仓库内容。

## 消息

请求/响应使用 `{type, request_id, payload}`。`request_id` 是客户端生成的非零 uint64 十进制字符串；同一连接内尚未完成的请求不得复用。响应原样回显。通知不含 `request_id`。

- `GetPackageManifest`：客户端请求当前要求集合，可带已缓存的 `known_manifest_id`。
- `PackageManifestResult`：返回 `manifest_id`、有序 `packages` 和 `sync_timeout_ms`。
- `PackageReady`：客户端完成本地切换后回报 `manifest_id`。
- `PackageReadyResult`：`ready=true`，或返回结构化错误。
- `PackageManifestChanged`：服务端要求重新协商；只携带新 `manifest_id`，客户端再发请求获取详情。

错误结构统一为 `{code, message, retryable, details?}`。旧客户端不能支持包协商时，服务端发送已有 SGS/1 错误通道中的 `PACKAGE_PROTOCOL_REQUIRED`，包含 `required_protocol: "PackageSync/1"`，随后有序关闭；不得伪装为空清单。

## manifest_id

服务器将 `packages` 按 `id` 的 Unicode code point 升序排列，只保留 Schema 中定义的字段，然后按 RFC 8785 JSON Canonicalization Scheme 序列化 UTF-8 字节，计算 SHA-256，表示为 64 位小写十六进制。空数组也按同一规则计算。服务端注册表变更必须生成新 ID。

每项 `commit` 必须是完整的 40 位 SHA-1 或 64 位 SHA-256 小写对象 ID，不接受分支、标签或缩写。`manifest_sha256` 是该 commit 中 `package.json` 原始字节的 SHA-256。Git URL 与 commit 来自服务器安装注册表。

## 客户端事务

1. 比较 `id`、`version`、`commit`、`manifest_sha256` 和 `api_version`；仅目录同名不算已安装。
2. 在应用专用临时目录获取缺失 commit；禁止凭据写入日志。设置总超时 `sync_timeout_ms`，单仓库失败不延长总期限。
3. 验证 commit 对象、Manifest 哈希、Manifest Schema、包 ID/版本/API 和完整依赖图。
4. 在同一文件系统内原子切换活动集合，保留上一集合用于回滚。
5. 加载探测成功后删除过期临时状态并发送 `PackageReady`；失败则回滚并发送/记录对应错误。

`PackageReady.manifest_id` 必须等于连接当前要求值。否则返回 `MANIFEST_ID_MISMATCH`，`ready=false`，客户端不得进入需包的房间/对局。

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
