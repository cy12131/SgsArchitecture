# ADR-0011: 资源包内容按包与 commit 隔离存储

- 状态：Accepted
- 日期：2026-10-26

## Context

Manifest 中的入口与资源路径都相对于单个包根目录。若把多个包的 Lua、QML 或资源文件复制到共享目录，文件名冲突、来源追踪、commit 校验、回滚和跨包权限都会依赖隐式覆盖顺序，与 Git commit 锁定及显式依赖相冲突。

SgsServer 与 SgsClient 当前实现已经分别以 `installed/<package-id>/<commit>/` 保存 Git checkout，并使用独立 staging 目录。两端的激活模型不同：服务端使用持久化注册表和启动 generation；客户端使用 `active.json` 原子发布当前集合。因此不需要为了目录外观重写两端为同一套实现。

## Decision

每份已安装包内容必须拥有唯一包根：`installed/<package-id>/<commit>/`。`manifest.json`、Lua、QML、图片、声音、动画及包内其他文件均保留在该根下；不同包即使包含相同相对路径也不得合并、复制或以加载先后覆盖。

资源加载必须从已验证的 `(package-id, commit) → package-root` 映射开始，再解析 Manifest 相对路径。禁止扫描 `packages` 根目录寻找入口，也禁止把共享文件名当作包归属。依赖拓扑只决定注册/加载顺序，不改变目录归属。

两端保留各自生命周期：

- SgsServer 保留 `registry.json`、`.registry.lock`、`.staging/`、启动时 generation 锁定及 ADR-0009 的重启生效语义。
- SgsClient 保留 `installed/<package-id>/<commit>/`、`.staging/<uuid>/`、`active.json` 原子发布和上一激活索引回滚能力。

注册表、锁、临时目录、缓存索引和激活元数据不是资源包内容，不能暴露给 Lua/QML ResourceResolver。

旧的平铺或混合目录不得就地猜测归属。迁移只能依据可信注册/激活元数据及锁定 commit 建立候选目录并重新完成 Git HEAD、Manifest 摘要、Schema、依赖和路径验证；无法无歧义证明来源时，重新获取锁定 commit。全部候选成功后才切换注册表或 `active.json`。未知或人工修改文件保留并报告/隔离，不能被加载，也不能由自动迁移静默删除。

## Consequences

- 包内同名文件不会产生跨包覆盖，来源可由 package ID 与 commit 审计。
- package ID、commit、Manifest 摘要、依赖图、加载顺序和 `manifest_id` 算法均不改变；SGS/1、GameIPC/1 和 Manifest Schema 无需变更。
- 已验证的规范目录缓存可以复用；不规范或被修改的缓存不能直接激活。
- 两端需增加或保留目录审计、失败回滚和旧布局迁移测试，但不需要统一 PackageManager 与 PackageInstaller 的实现细节。
