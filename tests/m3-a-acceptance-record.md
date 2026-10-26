# M3-A Cross-device Acceptance Record

- 状态：Passed / Archived
- 归档日期：2026-10-26
- 范围：Package Manifest、Git 安装/锁定、Package Sync、PackageReady 门禁及 M2 大厅/房间回归

## 版本证据

| 组件 | 已验收 revision | 标签/来源 |
|---|---|---|
| SgsServer | `8e3b941e24f995f2f4ef1efe8b60bfe0fb134662` | `v0.4.0-m3a`；远程 annotated tag peeled commit 已核验一致 |
| SgsClient | `eb5f584c06193195103ee81fbd537e92970675c9` | `v0.4.0-m3a`；远程 annotated tag peeled commit 已核验一致 |
| 测试包 | `9d38a4a970448ca17bfbf7c61f20ab77f6f12451` | CNB `https://cnb.cool/sgs-project/sgs-test-mode.git` main/HEAD |

测试包 Manifest ID：`org.sgs.testmode`。三个 revision 均为完整 Git commit；验收记录不以分支或可移动标签代替锁定值。

## 已通过场景

1. 服务端从公开 CNB Git 仓库安装测试包并锁定指定 commit。
2. 服务端验证 `manifest.json`，持久化安装注册表，并执行包 ID、版本和依赖检查。
3. 管理变更不影响运行 generation；SgsServer 正常重启后新配置生效，符合 ADR-0009。
4. Windows 客户端首次连接下载包；再次连接识别已验证的相同 commit 并复用缓存。
5. 客户端完成 GetPackageManifest、下载/验证和 PackageReady 后才通过 SGS/1 大厅门禁。
6. Windows 客户端与 Linux 服务端完成真实网络联调。
7. 两个 GUI 客户端完成进入大厅、创建/加入房间和准备状态回归。

首次下载和相同 commit 的缓存复用证明了两个不同路径，但**不等同于服务器驱动版本升级**。本次没有把服务器清单从已缓存旧 commit 推进到新 commit 并验证客户端事务切换；该场景必须后续单独联调。

## 测试计数

- SgsServer Debug 6/6：通过。
- SgsServer ASan/UBSan 6/6：通过。
- SgsClient Debug 4/4：通过。
- SgsClient Release 4/4：通过。
- 跨设备人工/集成流程：上述 7 项全部通过。

## 已知限制

- Lua GameIPC 运行时尚未实现。
- 动态 QML 游戏页面尚未实现。
- 皮肤跨包绑定已有架构要求，但尚未进入运行时验证。
- CNB IPv6 TLS 路径存在环境兼容问题。
- Git 下载超时、取消/重试策略和资源配额仍需后续加固。
- 真正的服务器驱动版本升级联调不在本次首次下载/缓存复用覆盖范围内。

这些限制不否定 M3-A 已验收范围，但继续约束下一阶段，不得把本记录解释为整个 M3 完成。
