# SGS 资源包目录结构规范审查

- 日期：2026-10-26
- 审查基线：SgsServer `24034d0c14949bb22c2a0b1a8c79a737650ca900`；SgsClient `eb5f584c06193195103ee81fbd537e92970675c9`
- 结论：现有新安装路径已经按 `package-id/commit` 隔离。缺口是架构仓库未明确目录分类、加载解析和旧平铺布局迁移规则；本轮不需要修改协议或 Manifest Schema。

## 实现证据与当前结构

SgsServer 的 `PackageManager` 以配置的 package state root 为根，生产默认值由 `SGS_PACKAGE_ROOT`、`XDG_STATE_HOME` 或用户 state 目录决定。安装先克隆到独立 staging，验证后 rename 到 `installed/<package-id>/<commit>`；注册表记录相对于 `installed/` 的目录，跨进程锁覆盖读取、安装、验证和原子注册表替换。

```text
<server-package-state>/
├── installed/                         # 已安装内容容器，不是一个包根
│   └── <package-id>/
│       └── <full-commit>/             # 单一、不可变 package root
│           ├── manifest.json
│           └── server|client|assets|...  # 该包自己的 Git checkout
├── .staging/<unique-install>/          # 临时 Git checkout
├── registry.json                       # 下次启动期望配置及目录映射
├── .registry.lock                      # 跨进程管理事务锁
└── registry.json.tmp.*                 # 原子写临时文件；成功后不得残留
```

SgsClient 的 `PackageSyncManager` 默认使用 `QStandardPaths::AppLocalDataLocation/packages`。`PackageInstaller` 验证已存在 checkout 的 HEAD、clean 状态与 Manifest；缺失版本先进入 UUID staging，再原子 rename。激活集合由 `active.json` 发布。

```text
<client-app-local-data>/packages/
├── installed/
│   └── <package-id>/
│       └── <full-commit>/              # 单一、不可变 package root/cache
│           ├── manifest.json
│           └── client|server|assets|...
├── .staging/<uuid>/                    # 未提交下载/校验目录
├── .empty-hooks/                       # Git 安全辅助元数据，不是包内容
├── active.json                         # 当前原子激活索引
└── active.previous.json                # 上一激活索引/回滚证据
```

因此，“多个导入包散落在 packages 根目录”不是上述已审查新安装代码的行为。若真实环境存在根目录散落文件，应作为旧版本、人工复制或未受当前安装器管理的布局处理，不能把它当成当前 canonical layout。

## 目标结构与目录职责

目标结构保持上述两端现有设计，不强行统一实现。目录分类如下：

| 类别 | 服务端 | 客户端 | 可由 Lua/QML 加载 |
|---|---|---|---:|
| 包内容 | `installed/<package-id>/<commit>/` | `installed/<package-id>/<commit>/` | 仅当前 generation/active 索引指向且 Manifest 允许的文件 |
| 注册/期望配置 | `registry.json` | 无 | 否 |
| 激活元数据 | 启动内存 generation | `active.json`、`active.previous.json` | 否 |
| 临时文件 | `.staging/*`、`registry.json.tmp.*` | `.staging/<uuid>` | 否 |
| 锁/工具元数据 | `.registry.lock` | `.empty-hooks/` | 否 |
| 非活动缓存 | 未被启动 generation 引用的规范 checkout | 未被 `active.json` 引用的规范 checkout | 否 |
| 旧/未知内容 | 报告或隔离的 legacy/unknown 区域 | 报告或隔离的 legacy/unknown 区域 | 否 |

Package root 是完整 commit checkout 的根，不是 `packages/`、`installed/` 或 `<package-id>/`。一个 `<package-id>/<commit>` 目录只能归属一个注册项；同一 ID 的不同 commit 可以并存作为缓存，但一次 generation/active 集合最多引用其中一个。

## 路径解析影响

1. 先从服务端启动 generation 或客户端 `active.json` 取得精确 `(id, commit, root)`；不得扫描目录猜测当前版本。
2. 再把 `server.entry`、`client.qml_entry` 或 `resources` 的相对路径解析到该 root，并执行规范已有的 `..`、绝对路径、大小写和符号链接逃逸检查。
3. 跨包访问先验证 Manifest 依赖和调用能力，再切换到目标包自己的 root；不得以 `../other-package`、共享搜索目录或同名文件覆盖实现。
4. 依赖拓扑决定入口注册顺序，但解析结果始终保留 owner package；不同包的 `server/init.lua`、`client/Main.qml` 或 `assets/icon.png` 可以合法共存。
5. Lua 搜索路径和 QML import path 可包含多个独立 package root，但不能把文件复制到一个合成的可写目录。框架目录与包目录也必须保持不同信任域。

这些规则不改变 package ID、锁定 commit、Manifest 原始字节摘要、依赖关系、拓扑顺序或 Package Sync `manifest_id` 字段集合。

## 兼容迁移方案

迁移必须在不使用旧运行 generation/active 集合的维护窗口执行；服务端新配置仍只在正常重启后生效。

1. **盘点且只读分类**：识别保留名、规范 checkout、注册/激活引用、旧平铺内容和未知文件。第一阶段不移动、不删除。
2. **建立候选映射**：以注册表或 `active.json` 的 package ID、仓库 URL、完整 commit 和 Manifest 摘要为权威。目录名、文件名或内容相似不能单独证明归属。
3. **规范缓存复用**：只有 HEAD 等于锁定 commit、工作树无修改、`manifest.json` 摘要/身份/API/依赖/声明路径全部通过时，才复用既有 `installed/<package-id>/<commit>`。
4. **旧独立目录迁移**：能证明是完整单包 checkout 时，先复制/移动到同文件系统 staging，完成同等验证，再 rename 到 canonical destination；目的目录已存在时必须比较完整身份，不覆盖。
5. **旧平铺或混合目录**：若多个包内容已混合，无法可靠恢复文件 owner。不得按文件名分拣或“后者覆盖前者”；应从各自仓库重新获取每个锁定 commit，原目录保留为只读 legacy/quarantine 供人工核对。
6. **重复与未知文件**：两个包的同相对路径在各自 root 中均合法。canonical destination 内出现额外/修改文件则视为污染，不覆盖、不激活；根目录未知项不参与加载，记录诊断并等待用户处置。自动迁移不得静默删除用户文件。
7. **事务切换**：服务端在持有 `.registry.lock` 时原子替换候选注册表，当前运行 generation 不变；客户端仅在所有包成功后以 `QSaveFile`/等价方式替换 `active.json`，并保留上一索引。任何失败都保留旧注册表/active 索引。
8. **失败清理与恢复**：当前事务创建且尚未发布的 staging 可删除；已发布但未被索引引用的有效目录只作为非活动缓存。崩溃遗留 staging 应在确认没有活动安装任务后清理。legacy、unknown 或人工修改目录不自动删除。

## 所需代码改动范围

现有全新安装路径无需布局重构。后续实现工作限于：

- **SgsServer / PackageManager 与管理工具**：增加只读布局审计和显式迁移流程；迁移期间继续使用跨进程锁；迁移完成后可收紧新注册项的 `directory == <package-id>/<commit>` 校验；Runtime generation 暴露独立 package-root 映射而不是共享目录。不要改变启动 generation 或重启生效语义。
- **SgsClient / PackageInstaller 与加载宿主**：保留现有安装、staging 和 `active.json` 机制；增加 stale staging/legacy 诊断与显式迁移；QML/ResourceResolver 只从活动索引映射解析。已修改 canonical cache 继续报错并保护用户文件，不就地覆盖。
- **Package Agent**：保持每仓库完整 `manifest.json` 和包内相对路径；不要求通过复制到框架共享目录发布内容。

若现场没有旧平铺数据，只需目录审计与解析测试，不需要运行迁移或移动任何文件。

## 验收标准

1. 安装两个都含 `server/init.lua`、`client/Main.qml` 和同名资源的包，磁盘上分别位于各自 `<id>/<commit>`，内容互不覆盖。
2. 服务端注册表与客户端 `active.json` 分别指向精确目录；依赖拓扑、package ID、commit、Manifest 摘要和 `manifest_id` 与目录调整前一致。
3. Lua/QML 入口和资源解析以 owner package root 为起点；未声明跨包访问、根目录散落文件和未知目录均不可加载。
4. 服务端安装/迁移失败时注册表和当前启动 generation 不变；客户端失败时 `active.json` 及上一可用集合仍可用。
5. 已验证 canonical 缓存复用；被修改、重复冲突或身份不符的缓存不覆盖且不激活。
6. 旧的完整单包 checkout 可事务迁移；旧混合平铺内容触发重新获取锁定 commit，并保留未知文件供人工处理。
7. 管理员变更和迁移不热切换运行资源；SgsServer 正常重启后才锁定新 generation，客户端重连后重新同步。
8. 测试覆盖空包集合、多包同名文件、同包多 commit、staging 中断、索引/注册表写失败、未知文件、路径逃逸和回滚。

## 未决事项

- legacy/quarantine 的具体目录名、诊断命令名和缓存回收配额属于两端实现细节，不在协议中冻结。
- 自动清理非活动有效缓存的保留期限与磁盘配额尚未确定；在明确策略前不得删除当前或上一活动集合。
- 客户端首次真实动态 QML 加载与服务端 M3-B Runtime 尚需分别证明它们不扫描共享根目录。
