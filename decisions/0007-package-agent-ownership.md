# ADR-0007: Package Agent 拥有规则逻辑

- 状态：Accepted
- 日期：2026-10-25

## Decision

Package Agent 对规则、卡牌、武将、技能、模式和对应游戏 UI 的实现负责。架构仓库定义契约但不代写正式技能。

## Consequences

Lua Runtime/QML API 必须由真实最小包反馈验证。架构 Agent 不在缺少验证时宣布 Draft 冻结。
