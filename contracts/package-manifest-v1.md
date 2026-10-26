# Package Manifest v1

状态：M3 实现基线。Schema：`schemas/package-manifest.schema.json`。

Manifest 文件名固定为包根目录的 `manifest.json`，编码为 UTF-8 JSON。该名称直接表达 SGS 包清单用途，并避免与 Node/npm 的 `package.json` 混淆。未知字段拒绝。包自身不得声明仓库 URL 或锁定 commit；两者由服务器安装注册表管理。

## 字段

| 字段 | 类型 | 必填 | 规则 |
|---|---|---:|---|
| `schema_version` | integer | 是 | 固定为 `1` |
| `id` | string | 是 | 反向域名式小写标识，`^[a-z][a-z0-9]*(\\.[a-z][a-z0-9_-]*)+$` |
| `name` | string | 是 | 1–80 个 Unicode 字符，展示用途，不参与解析 |
| `version` | string | 是 | SemVer 2.0.0 |
| `api_version` | string | 是 | 包所需框架 API，格式 `MAJOR.MINOR` |
| `dependencies` | array | 是 | `{id, version}`；同一 ID 最多一次，`version` 为 SemVer 范围 |
| `server.entry` | string | 否 | 存在 `server` 时必填；Lua 入口，相对包根路径，必须以 `.lua` 结尾 |
| `client.qml_entry` | string | 否 | 存在 `client` 时必填；QML 页面入口，相对包根路径，必须以 `.qml` 结尾 |
| `resources` | string[] | 否 | 包含资源文件或目录的相对路径；非空、唯一 |

`server`、`client`、非空 `resources` 至少存在一个。不得用空对象假装入口；没有对应可执行入口时应省略整个 `server` 或 `client` 字段。

## 包形态与加载行为

| 形态 | 合法字段 | 加载行为 |
|---|---|---|
| 双端包 | `server.entry` + `client.qml_entry`，可带 `resources` | 服务端在 Lua 子进程加载入口；客户端在匹配模式需要时加载 QML |
| 仅服务端 | 只有 `server.entry`，可带 `resources` | 客户端只验证/同步清单，不尝试加载 QML；服务端加载 Lua |
| 仅客户端 UI | 只有 `client.qml_entry`，可带 `resources` | 服务端不执行包代码；客户端按模式加载 QML |
| 纯资源包 | 只有非空 `resources` | 双端均不执行入口，仅通过受控资源解析器按需访问文件 |

依赖包可以属于任一形态。解析依赖图与兼容性检查不因包没有可执行入口而跳过。

跨包内容扩展必须显式声明依赖。例如，独立皮肤包为武将包中的既有武将增加立绘、技能语音、阵亡语音或动画时，皮肤包必须依赖定义该武将的包；不能依靠安装目录扫描、同名文件覆盖或未声明的可选加载。武将包和皮肤包可以位于不同 Git 仓库，并分别由服务器安装注册表锁定 commit。现有 `dependencies` 字段已能表达该关系，本阶段不增加皮肤专用 Manifest 字段。

依赖范围只允许空格分隔的比较器（如 `>=1.0.0 <2.0.0`）、精确 SemVer 或 `*`。v1 不接受 Git URL、分支或标签作为依赖范围。

## 路径限制

入口路径使用 `/`，不得为空、以 `/` 开头、包含 `\\`、NUL、`.`/`..` 段或 URI scheme。解析后路径必须仍在包根目录内。符号链接目标也必须在包根内；加载器应拒绝逃逸链接。文件名大小写按 Manifest 精确匹配，保证跨平台一致性。

每个锁定版本的物理包根固定为该端安装区中的 `installed/<package-id>/<commit>/`。`manifest.json`、入口及资源保持在该 checkout 内；不得把多个包的 Lua、QML 或资源复制到共享目录后按文件名区分。不同包可以拥有相同相对路径，因为解析必须先由当前 generation/active 索引取得 package ID 与 commit 对应的独立根，再解析 Manifest 相对路径。依赖加载顺序不授予文件覆盖权，也不改变资源 owner。

注册表、锁、staging、激活索引和缓存管理文件不是包内容，不能出现在资源解析视图中。目录布局只属于本地安装/激活实现，不加入 Manifest 字段，也不参与 `manifest_sha256` 或 Package Sync `manifest_id`。

## 注册、启动激活与依赖

本节采用 **restart-required activation**。磁盘安装注册表中的启用标志、仓库 URL 和 commit 是“下次启动期望配置”，不是当前运行状态。管理员添加、更新、启用或停用包时只原子写入该注册表；不得因此加载/卸载入口、改变当前 `manifest_id` 或影响已经运行及随后创建的对局。

SgsServer 每次正常启动时只执行一次激活流程：读取磁盘期望配置，解析锁定 commit，并按下列规则验证；全部成功后生成不可变的启动 generation 和有效资源包清单。该 generation 在整个服务器进程生命周期内冻结。验证失败时不得部分激活，且不得覆盖持久化的上一份 last-known-good 有效清单；具体启动失败/回退运维策略由 SgsServer 实现记录，但绝不能混合新旧包。

1. 对每份 `manifest.json` 做 Schema、路径、声明文件存在性和 API 兼容性验证。
2. `id` 在启用集合中必须唯一；重复 ID 使整组解析失败，不采用“最后一个获胜”。
3. 每个依赖必须存在，且版本满足范围；否则启用失败并报告依赖链。
4. 对依赖图做拓扑排序；任何循环（包括自依赖）使启动候选激活失败。
5. 依赖先于依赖者加载。停用只修改下次启动期望配置；运行中不执行卸载顺序。

因此，目标武将必须先注册，皮肤包才能按稳定跨包武将 ID 绑定扩展资源。目标包缺失、版本范围不满足或目标武将未注册时，皮肤包激活失败；不得创建悬空绑定。皮肤包的添加、更新、启用和停用同样遵循 restart-required activation。

失败不得留下部分激活状态。M3 不监视注册表或包目录，也不实现热加载、热卸载、热替换或后台自动重载。

## 兼容性

框架支持某 `api_version`，当且仅当 major 相同且框架 minor 大于等于包要求 minor。包版本只用于依赖解析，不代替 API 兼容检查。服务端和客户端都必须验证；任一端不兼容即不得进入游戏。未知 `schema_version` 必须明确报 `UNSUPPORTED_PACKAGE_SCHEMA`。

## 安全

Manifest 是不可信输入。限制文件大小、字段长度和依赖数量；在执行 Lua/QML 前完成 commit、内容哈希和路径验证。Manifest 验证成功不代表包代码可信。
