# Changelog

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
