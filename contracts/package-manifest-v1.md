# Package Manifest v1

状态：M3 实现基线。Schema：`schemas/package-manifest.schema.json`。

Manifest 文件名固定为包根目录的 `package.json`，编码为 UTF-8 JSON。未知字段拒绝。包自身不得声明仓库 URL 或锁定 commit；两者由服务器安装注册表管理。

## 字段

| 字段 | 类型 | 必填 | 规则 |
|---|---|---:|---|
| `schema_version` | integer | 是 | 固定为 `1` |
| `id` | string | 是 | 反向域名式小写标识，`^[a-z][a-z0-9]*(\\.[a-z][a-z0-9_-]*)+$` |
| `name` | string | 是 | 1–80 个 Unicode 字符，展示用途，不参与解析 |
| `version` | string | 是 | SemVer 2.0.0 |
| `api_version` | string | 是 | 包所需框架 API，格式 `MAJOR.MINOR` |
| `dependencies` | array | 是 | `{id, version}`；同一 ID 最多一次，`version` 为 SemVer 范围 |
| `server.entry` | string | 是 | Lua 入口，相对包根路径，必须以 `.lua` 结尾 |
| `client.qml_entry` | string | 是 | QML 页面入口，相对包根路径，必须以 `.qml` 结尾 |

依赖范围只允许空格分隔的比较器（如 `>=1.0.0 <2.0.0`）、精确 SemVer 或 `*`。v1 不接受 Git URL、分支或标签作为依赖范围。

## 路径限制

入口路径使用 `/`，不得为空、以 `/` 开头、包含 `\\`、NUL、`.`/`..` 段或 URI scheme。解析后路径必须仍在包根目录内。符号链接目标也必须在包根内；加载器应拒绝逃逸链接。文件名大小写按 Manifest 精确匹配，保证跨平台一致性。

## 加载与依赖

1. 先对每份 Manifest 做 Schema、路径和 API 兼容性验证。
2. `id` 在启用集合中必须唯一；重复 ID 使整组解析失败，不采用“最后一个获胜”。
3. 每个依赖必须存在，且版本满足范围；否则启用失败并报告依赖链。
4. 对依赖图做拓扑排序；任何循环（包括自依赖）使相关启用事务失败。
5. 依赖先于依赖者加载；停用顺序相反。

失败不得留下部分启用状态。

## 兼容性

框架支持某 `api_version`，当且仅当 major 相同且框架 minor 大于等于包要求 minor。包版本只用于依赖解析，不代替 API 兼容检查。服务端和客户端都必须验证；任一端不兼容即不得进入游戏。未知 `schema_version` 必须明确报 `UNSUPPORTED_PACKAGE_SCHEMA`。

## 安全

Manifest 是不可信输入。限制文件大小、字段长度和依赖数量；在执行 Lua/QML 前完成 commit、内容哈希和路径验证。Manifest 验证成功不代表包代码可信。
