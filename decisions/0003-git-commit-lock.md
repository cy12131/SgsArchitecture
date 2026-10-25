# ADR-0003: 资源包锁定 Git commit

- 状态：Accepted
- 日期：2026-10-25

## Decision

服务器安装注册表记录仓库 URL 和完整 commit object ID，并以该不可变标识生成要求清单。包 Manifest 不控制来源。

## Consequences

版本可复现且可回滚；管理员需显式升级，写入的 commit 只在下一次 SgsServer 正常启动时参与激活。分支、标签和缩写 commit 不可作为运行时锁定值。
