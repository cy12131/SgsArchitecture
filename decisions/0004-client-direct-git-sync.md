# ADR-0004: 客户端直连 Git 仓库同步

- 状态：Accepted
- 日期：2026-10-25

## Decision

客户端通过 SGS/1 获取要求清单，然后从注册的远程 Git 仓库获取锁定 commit。SGS TCP 不承载大型资源。

## Consequences

服务端带宽与协议保持简单；客户端需要事务式下载、验证、切换和回滚。私有仓库凭据方案仍是 Open Question。
