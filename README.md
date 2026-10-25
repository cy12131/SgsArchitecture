# SGS Architecture & Contracts

SGS 跨仓库架构规范、协议契约、机器可验证 Schema、示例和架构决策记录。

当前规范版本：`0.1.0-draft`。本仓库只定义边界，不包含 SgsServer、SgsClient 或正式游戏包业务实现。

## 稳定性

- `Package Manifest v1`、`Package Sync v1`、`GameIPC/1`：M3 实现基线；破坏性修改必须记录 ADR 和 CHANGELOG。
- `Lua Runtime API v1`、`QML Extension API v1`：**Draft**，分别等待最小规则包验证和真实动态加载测试，尚未冻结。
- M1/M2 的 SGS/1 四字节大端长度帧、UTF-8 JSON 和已有基础消息语义保持不变。

## 目录

- `contracts/`：人类可读契约。
- `schemas/`：JSON Schema Draft 2020-12。
- `examples/`：正例、反例和安全测试向量。
- `tests/`：Schema 与跨文件语义校验。
- `decisions/`：ADR。

## 验证

```powershell
python -m pip install -r requirements-test.txt
python tests/validate.py
```

验证器检查 Schema 正反例，并补充 JSON Schema 无法表达的重复 ID、缺失依赖、循环依赖、`manifest_id` 和请求往返规则。

## 范围边界

- SgsServer：网络、用户/房间、包注册、进程管理、IPC 与通用安全边界。
- SgsClient：SGS/1、包同步、通用壳层、QML 扩展宿主。
- packages：规则、卡牌、武将、技能、模式及游戏专属 UI。
- Package Agent 拥有规则逻辑；框架 Agent 不把复杂规则移入 C++。

仓库 URL 与锁定 commit 是服务器安装注册信息，不属于包自身 Manifest。

## Open Questions

见各 Draft 契约的 `Open Questions`。未决项不得被解释为已冻结 API。
