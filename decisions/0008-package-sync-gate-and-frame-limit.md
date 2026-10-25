# ADR-0008: Package Sync 大厅门禁与单帧原子性

- 状态：Accepted
- 日期：2026-10-25

## Context

M2 客户端不了解资源包同步，但 SGS/1 的 Hello、诊断消息和错误语义必须保持兼容。PackageManifestResult 同时受 SGS/1 65536 字节 JSON 正文上限约束。

## Decision

每条连接在成功确认当前 `manifest_id` 前处于 NotReady。Hello、Ping、Echo 不受影响；EnterLobby 以标准 `PACKAGE_PROTOCOL_REQUIRED` Error 拒绝且默认不关闭连接。空清单也必须显式确认，断线或清单变化清除 Ready。

PackageManifestResult 必须是单个 SGS/1 帧。服务端按实际 UTF-8 JSON 正文字节检查上限；超限启用事务以 `PACKAGE_MANIFEST_TOO_LARGE` 失败并保留上一有效清单。v1 不截断、分片或分页。

## Consequences

旧客户端可连接和诊断，但不能绕过 M3 包门禁。清单规模受实际编码而非固定包数量约束；未来若确需更大清单，必须另行版本化分页协议。
