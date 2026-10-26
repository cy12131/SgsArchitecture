# SGS Architecture & Contracts

SGS 跨仓库架构规范、协议契约、机器可验证 Schema、示例和架构决策记录。

当前规范版本：`0.3.1-draft`。本仓库只定义边界，不包含 SgsServer、SgsClient 或正式游戏包业务实现。

## 稳定性

- `Package Manifest v1`、`Package Sync v1`、`GameIPC/1`：M3 实现基线；破坏性修改必须记录 ADR 和 CHANGELOG。
- `Lua Runtime API v1`、`QML Extension API v1`：**Draft / Implementation Candidate**，已细化生命周期、Request Bridge 和宿主接口，但仍等待真实 Linux/Qt 集成测试，尚未冻结。
- M1/M2 的 SGS/1 四字节大端长度帧、UTF-8 JSON 和 `{protocol,type,request_id,data}` 信封保持不变；GameIPC/1 独立使用自己的 `ipc_version` 和 `payload`。

## 目录

- `contracts/`：人类可读契约。
- `schemas/`：JSON Schema Draft 2020-12。
- `examples/`：正例、反例和安全测试向量。
- `tests/`：Schema 与跨文件语义校验。
- `decisions/`：ADR。
- `progress/`：跨仓库阶段状态与归档索引。
- `reviews/`：阶段启动前的兼容性与实现边界审查。
- `contracts/m3-agent-interface-matrix.md`：三实现 Agent 与架构维护边界。

M3-A 已于 2026-10-26 完成真实 Windows/Linux 跨设备验收并归档；精确版本、测试证据和限制见 `progress/m3.md` 与 `tests/m3-a-acceptance-record.md`。M3-A 完成不代表 Lua GameIPC、动态 QML 或跨包皮肤运行时已经实现。

M3-B 启动前审查见 `reviews/m3-b-startup-review.md`，分阶段可执行门槛见 `tests/m3-b-acceptance-plan.md`。本轮沿用 GameIPC/1，不改 SGS/1 或 M3-A 包机制。

## 验证

```powershell
python -m pip install -r requirements-test.txt
python tests/validate.py
```

验证器检查 Schema 正反例、RFC 8785 官方向量，并补充 JSON Schema 无法表达的重复 ID、缺失依赖、循环依赖、`manifest_id` 和请求往返规则。

`examples/minimal-runtime-package` 是静态契约样例，不代表真实 Lua 子进程或 Qt/QML 端到端联调；动态门槛见 `tests/integration-checklist.md`。

## 范围边界

- SgsServer：网络、用户/房间、包注册、进程管理、IPC 与通用安全边界。
- SgsClient：SGS/1、包同步、通用壳层、QML 扩展宿主。
- packages：规则、卡牌、武将、技能、模式及游戏专属 UI。
- Package Agent 拥有规则逻辑；框架 Agent 不把复杂规则移入 C++。

包清单固定命名为 `manifest.json`；服务端 Lua、客户端 QML 和资源入口按包能力选填。仓库 URL 与锁定 commit 是服务器安装注册信息，不属于包自身 Manifest。

每条客户端连接必须在 EnterLobby 前确认当前资源包摘要；空清单也需确认。PackageManifestResult 必须适配 SGS/1 的 65536 字节单帧正文上限。

资源包采用 **restart-required activation**：管理员的添加、更新、启用和停用只修改磁盘注册表；SgsServer 在正常启动时验证并锁定一次有效清单，运行期间不热更新、热卸载、热替换或后台重载。客户端每次重连都重新获取并确认该启动 generation。

长期扩展边界要求独立皮肤资源包可通过稳定的跨包武将 ID，为其他包的既有武将注册额外立绘、技能语音、阵亡语音和动画。武将包与皮肤包保持独立 Git 仓库和锁定 commit，皮肤包以 Manifest 依赖声明目标武将包；具体 Registry 接口和资源命名仍为 Draft。

## Open Questions

见各 Draft 契约的 `Open Questions`。未决项不得被解释为已冻结 API。
