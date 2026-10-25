# ADR-0008: Package Sync 大厅门禁与单帧原子性

- 状态：Accepted
- 日期：2026-10-25

## Context

M2 客户端不了解资源包同步，但 SGS/1 的 Hello、诊断消息和错误语义必须保持兼容。PackageManifestResult 同时受 SGS/1 65536 字节 JSON 正文上限约束。

## Decision

每条连接在成功确认当前 `manifest_id` 前处于 NotReady。Hello、Ping、Echo 不受影响；EnterLobby 以标准 `PACKAGE_PROTOCOL_REQUIRED` Error 拒绝且默认不关闭连接。空清单也必须显式确认，断线清除 Ready；预留的 `PackageManifestChanged` 若在未来启用也必须清除 Ready，但 M3 管理操作不触发它。

PackageManifestResult 必须是单个 SGS/1 帧。服务端按实际 UTF-8 JSON 正文字节检查上限；超限的下次启动候选以 `PACKAGE_MANIFEST_TOO_LARGE` 拒绝激活并保留上一 last-known-good 有效清单。v1 不截断、分片或分页；有效清单的重启生效时机由 ADR-0009 规定。

## Consequences

旧客户端可连接和诊断，但不能绕过 M3 包门禁。清单规模受实际编码而非固定包数量约束；未来若确需更大清单，必须另行版本化分页协议。
