# ADR-0009: 资源包变更在服务器重启后生效

- 状态：Accepted
- 日期：2026-10-25

## Context

运行时切换资源包会同时影响大厅 PackageReady 状态、客户端 QML generation、Lua 对局版本和依赖图。支持热加载还需要定义在局迁移、失败回滚、并发连接以及跨平台文件占用语义，超出 M3 范围并增加权威状态不一致风险。

## Decision

采用 **restart-required package activation**。管理员添加、更新、启用或停用资源包时，只原子写入磁盘安装注册表中的下次启动期望配置，不改变当前 SgsServer 进程的有效清单。

SgsServer 正常启动时读取、验证并锁定一次 package generation。验证包括 commit、Manifest、依赖/API 兼容性、`manifest_id` 和 SGS/1 单帧大小；成功后该 generation 在整个进程生命周期内不可变。所有 Package Sync 响应和 Lua 游戏进程只使用它。M3 不监视注册表或包目录，不实现热更新、热卸载、热替换或后台自动重载。

`PackageManifestChanged` 保留为未来协议预留消息，但本版本不因管理员操作触发。若未来需要运行时 generation 切换，必须通过新的 ADR 和版本化契约明确连接、对局和回滚语义。

## Consequences

- 新配置只有在服务器正常重启并通过完整验证后才生效；运行中的连接和对局不受管理操作影响。
- 客户端在重启导致的重连后重新获取 Manifest、同步锁定 commit 并发送 PackageReady；缓存不能替代连接级确认。
- 启动候选验证失败不得产生部分激活或混合 generation，并保留上一份 last-known-good 有效清单供运维恢复。
- 运维升级需要安排服务器重启和连接中断，但版本边界可复现、可审计。
