# ADR-0001: 通用框架与 packages 分层

- 状态：Accepted
- 日期：2026-10-25

## Context

SGS 需要持续增加模式、卡牌、武将、技能和专属 UI，同时保持网络与房间框架稳定。

## Decision

SgsServer/SgsClient 只提供通用网络、用户/房间、运行时、资源加载和扩展接口；游戏内容与专属 UI 主要位于独立 packages。每个包以根目录 `manifest.json` 声明能力，服务端 Lua、客户端 QML 和纯资源可以独立或组合存在，不要求无关入口。

## Consequences

新增常规内容无需修改双端主程序。通用 API 变更、安全修复或底层缺陷才进入框架仓库；包兼容性成为发布门槛。
