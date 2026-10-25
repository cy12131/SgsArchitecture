# ADR-0005: SGS/1 与 GameIPC/1 独立

- 状态：Accepted
- 日期：2026-10-25

## Decision

客户端网络协议 SGS/1 与父子进程协议 GameIPC/1 使用独立版本和 Schema。SGS/1 严格使用整数 `protocol: 1`、整数 `request_id` 和对象 `data`；GameIPC/1 使用自己的 `ipc_version`、`sequence`、`request_token` 和 `payload`。二者虽都采用大端长度帧与 UTF-8 JSON，但消息不可直接透传。

## Consequences

外部网络兼容性与内部运行时可独立演进；C++ 必须执行身份绑定、字段映射和安全过滤。QML GameAction/GameReply 只能经宿主映射为 PlayerAction/PlayerReply，包页面不直接接触任一传输层。
