# Examples and expected results

| 文件 | Schema | 语义 | 预期 |
|---|---|---|---|
| `package-manifest/valid-base.json` | 合法 | 合法 | 接受 |
| `package-manifest/valid-server-only.json` | 合法 | 合法 | 只加载服务端 Lua |
| `package-manifest/valid-client-only.json` | 合法 | 合法 | 只加载客户端 QML |
| `package-manifest/valid-resources-only.json` | 合法 | 合法 | 不执行代码，只暴露资源 |
| `package-manifest/invalid-missing-name.json` | 非法 | 未运行 | 因缺少 `name` 拒绝 |
| `package-manifest/invalid-no-content.json` | 非法 | 未运行 | 因没有入口或资源拒绝 |
| `package-manifest/cycle-a.json`, `cycle-b.json` | 各自合法 | 非法 | 因 A↔B 循环拒绝整组 |
| `package-sync/empty-manifest.json` | 合法 | 合法 | 接受空要求并可 Ready |
| `package-sync/multi-package-manifest.json` | 合法 | 合法 | core 先于 standard 加载 |
| `package-sync/ready-mismatch.json` | 合法 | 非法 | 返回 `MANIFEST_ID_MISMATCH`，不得进入游戏 |
| `package-sync/get-package-manifest.json` | 合法 | 合法 | 接受 SGS/1 最大合法请求 ID |
| `package-sync/manifest-changed.json` | 合法 | 预留 | 通知使用 `request_id: 0`，M3 管理操作不触发 |
| `package-sync/restart-required-activation.json` | 场景 | 合法 | 磁盘变更不影响当前 generation，重启后才激活 |
| `package-sync/invalid-legacy-envelope.json` | 非法 | 未运行 | 拒绝字符串 ID、缺少 protocol 和 payload 信封 |
| `package-sync/package-protocol-required.json` | 合法 | 合法 | 未 Ready 的 EnterLobby 返回标准 Error 且不断线 |
| `package-sync/package-manifest-too-large.json` | 合法 | 合法 | 超限启动候选激活失败并保留上一有效清单 |
| `package-sync/empty-manifest-ready.json` | 合法 | 合法 | 空清单仍需显式 PackageReady |
| `rfc8785/section-3.2.2-vector.json` | 标准向量 | 合法 | 规范 UTF-8 字节及 SHA-256 必须精确匹配 |
| `rfc8785/section-3.2.3-sorting-vector.json` | 标准向量 | 合法 | 属性按 RFC 8785 UTF-16 规则排序 |
| `game-ipc/init-game.json`, `game-ready.json` | 合法 | 合法 | token 匹配，完成正常初始化 |
| `game-ipc/m3-b-review-cases.json` | 场景 | 混合 | 固化 room/generation/roster 绑定及 sequence uint64 边界 |
| `game-ipc/player-request.json`, `player-reply.json` | 合法 | 合法 | token、game_id 匹配，完成一次往返 |
| `game-ipc/process-exit.json` | 场景文件 | 合法场景 | 进入 Failed，取消请求并异步回收 |
| `game-ipc/hidden-info-safe.json` | 合法 | 安全 | 私有手牌仅发给 `player-a` |
| `game-ipc/hidden-info-unsafe.json` | 合法 | 安全策略非法 | 测试因隐藏字段广播给多人而拒绝 |

“Schema 合法但语义非法”是刻意的测试向量；跨消息状态和信息流策略由自动化语义校验覆盖。

`minimal-runtime-package/` 提供双人 Init→Action→Event/Request→Reply→定向视图→Finished 静态流程，以及超时、重复回复、非目标回复、断线和 Lua 进程退出向量。其 Lua/QML 文件是契约伪实现，不是动态联调结果。
