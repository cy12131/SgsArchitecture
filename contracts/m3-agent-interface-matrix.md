# M3 Agent Interface Matrix

状态：`0.3.3-draft` 协作边界。Stable 表示已有冻结上游契约；Implementation Candidate 表示需真实实现验证，不代表 API 冻结。M3-A Package Manifest/Sync 已完成跨设备验收；M3-B 已完成启动前审查但尚未实现，该结果不提升 Lua/QML Draft 的稳定级别。

| 能力/接口 | Linux Server Agent | Windows Client Agent | Package Agent | Architecture Agent | 状态 |
|---|---|---|---|---|---|
| SGS/1 帧与 M1/M2 消息 | 实现/保持兼容 | 实现/保持兼容 | 不接触 | 维护契约 | Stable baseline |
| Package Sync 信封、门禁、64 KiB | 已通过 M3-A 跨设备验收 | 已通过 M3-A 下载/缓存/Ready 验收 | `org.sgs.testmode` 已验证 | 维护 Schema/归档证据 | M3-A accepted |
| 重启生效、Git commit 锁定与只读 generation | 管理操作写磁盘；启动验证并锁定一次；不热重载 | 每次重连获取、验证、原子切换 | 发布不可变 commit | 维护 ADR/边界 | Stable M3 policy / implementation candidate |
| 独立包目录与路径解析 | 保留 registry/lock；`installed/<id>/<commit>`；Runtime 使用精确 owner root | 保留 staging/active.json；QML/资源只解析活动 owner root | 每个仓库保持完整包内树，不复制到共享目录 | 维护 ADR-0011、迁移与验收规则 | Required layout / migration implementation pending |
| M3-B1 Lua 子进程创建/监管 | 实现双管道、启动绑定、超时、reap | 不接触 | 不接触 | 维护 GameIPC | Ready to implement |
| M3-B1 GameIPC 编解码/背压 | 父端实现并提供协议 stub 测试 | 不直接使用 | 不构造信封 | 维护 Schema/向量 | Ready to implement |
| M3-B2 Lua Runtime 宿主适配层 | 实现受限 Runtime、2–8 roster/seat、Init/GameReady、有界日志；不移植完整规则 | 不接触 | 验证两人 testmode 入口，不把 2 人限制扩散到宿主 | 维护 Draft API | Implementation Candidate |
| GameLogic/GameEvent/TriggerEvent | 不实现具体规则 | 不接触 | 实现规则与触发 | 定义生命周期/安全语义 | Implementation Candidate |
| M3-B3 Request Bridge | 异步 token、timer、身份验证 | M3-B 不接入正式 UI | Lua 请求/默认/策略与 Mock 对齐 | 定义状态机与向量 | Implementation Candidate |
| QML GameViewContext | 提供已定向数据 | 实现 QObject/模型/生命周期 | 编写包页面/组件 | 维护 Draft API | Implementation Candidate |
| view snapshot/delta | Lua 输出后校验 recipients | revision 去重、事务应用 | 生成玩家可见视图 | 定义 profile | Implementation Candidate |
| Card/General/Skill/GameMode | 不写业务规则 | 不写业务规则 | 拥有内容实现 | 只维护注册契约 | Package ownership |
| 跨包 General/Skin 注册 | 提供通用注册宿主，不写专用皮肤逻辑 | 提供通用解析/回退宿主，不写包专用组件 | 武将包与皮肤包独立实现、声明依赖 | 维护长期要求与 Draft 边界 | Required capability / Draft API |
| 皮肤/语音/动画命名格式 | 不冻结 | 不冻结 | 参与 M3-C 验证 | 记录 Open Question | Deferred |

## 交付门槛

- Linux Agent：证明管道非阻塞、写队列受限、进程异常不阻塞 Boost.Asio、token timer 可取消。
- Linux Agent：证明包管理操作不改变运行 generation，正常重启才加载候选注册表，所有 Lua 子进程只取得启动 generation。
- Linux Agent：证明 Runtime 只取得 generation 中各包独立根；旧平铺迁移持锁、失败不改注册表且不加载未知文件。
- Windows Agent：证明 QML 加载/回退/销毁无 use-after-free，私有数据不跨玩家，多个 token 可并发。
- Windows Agent：证明 `active.json` 只引用规范隔离目录，staging/未知/非活动缓存不可解析，发布失败保留旧索引。
- Package Agent：以最小双人包证明事件嵌套、触发顺序、Request 超时/default 和定向视图。
- 三实现 Agent：在 M3-C 以两个独立仓库证明无需修改武将包或框架专用代码即可跨包绑定皮肤，并验证冲突与默认资源回退。
- Architecture Agent：保持 Markdown、Schema、示例与测试一致；真实验证前不把 Lua/QML Draft 标成 Stable。
