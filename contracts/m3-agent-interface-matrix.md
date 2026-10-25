# M3 Agent Interface Matrix

状态：`0.2.0-draft` 协作边界。Stable 表示已有冻结上游契约；Implementation Candidate 表示需真实实现验证，不代表 API 冻结。

| 能力/接口 | Linux Server Agent | Windows Client Agent | Package Agent | Architecture Agent | 状态 |
|---|---|---|---|---|---|
| SGS/1 帧与 M1/M2 消息 | 实现/保持兼容 | 实现/保持兼容 | 不接触 | 维护契约 | Stable baseline |
| Package Sync 信封、门禁、64 KiB | 实现清单/Ready 状态和错误 | 实现事务同步/Ready | 提供合法 manifest | 维护 Schema/向量 | Stable M3 baseline |
| 重启生效、Git commit 锁定与只读 generation | 管理操作写磁盘；启动验证并锁定一次；不热重载 | 每次重连获取、验证、原子切换 | 发布不可变 commit | 维护 ADR/边界 | Stable M3 policy / implementation candidate |
| Lua 子进程创建/监管 | 实现双管道、参数、超时、reap | 不接触 | 不接触 | 维护 GameIPC | Implementation Candidate |
| GameIPC 编解码/背压 | 父端实现 | 不直接使用 | Runtime 适配层配合 | 维护 Schema/向量 | Implementation Candidate |
| Lua Runtime 宿主适配层 | 提供进程启动数据，不解释规则 | 不接触 | 实现/验证 Lua 适配包 | 维护 Draft API | Implementation Candidate |
| GameLogic/GameEvent/TriggerEvent | 不实现具体规则 | 不接触 | 实现规则与触发 | 定义生命周期/安全语义 | Implementation Candidate |
| Request Bridge | 异步 token、timer、身份验证 | token UI、回复、关闭 | Lua 请求/默认/策略 | 定义状态机与向量 | Implementation Candidate |
| QML GameViewContext | 提供已定向数据 | 实现 QObject/模型/生命周期 | 编写包页面/组件 | 维护 Draft API | Implementation Candidate |
| view snapshot/delta | Lua 输出后校验 recipients | revision 去重、事务应用 | 生成玩家可见视图 | 定义 profile | Implementation Candidate |
| Card/General/Skill/GameMode | 不写业务规则 | 不写业务规则 | 拥有内容实现 | 只维护注册契约 | Package ownership |
| 动态资源命名（皮肤/语音等） | 不冻结 | 不冻结 | 与用户后续确定 | 记录 Open Question | Deferred |

## 交付门槛

- Linux Agent：证明管道非阻塞、写队列受限、进程异常不阻塞 Boost.Asio、token timer 可取消。
- Linux Agent：证明包管理操作不改变运行 generation，正常重启才加载候选注册表，所有 Lua 子进程只取得启动 generation。
- Windows Agent：证明 QML 加载/回退/销毁无 use-after-free，私有数据不跨玩家，多个 token 可并发。
- Package Agent：以最小双人包证明事件嵌套、触发顺序、Request 超时/default 和定向视图。
- Architecture Agent：保持 Markdown、Schema、示例与测试一致；真实验证前不把 Lua/QML Draft 标成 Stable。
