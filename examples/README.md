# Examples and expected results

| 文件 | Schema | 语义 | 预期 |
|---|---|---|---|
| `package-manifest/valid-base.json` | 合法 | 合法 | 接受 |
| `package-manifest/invalid-missing-name.json` | 非法 | 未运行 | 因缺少 `name` 拒绝 |
| `package-manifest/cycle-a.json`, `cycle-b.json` | 各自合法 | 非法 | 因 A↔B 循环拒绝整组 |
| `package-sync/empty-manifest.json` | 合法 | 合法 | 接受空要求并可 Ready |
| `package-sync/multi-package-manifest.json` | 合法 | 合法 | core 先于 standard 加载 |
| `package-sync/ready-mismatch.json` | 合法 | 非法 | 返回 `MANIFEST_ID_MISMATCH`，不得进入游戏 |
| `game-ipc/init-game.json`, `game-ready.json` | 合法 | 合法 | token 匹配，完成正常初始化 |
| `game-ipc/player-request.json`, `player-reply.json` | 合法 | 合法 | token、game_id 匹配，完成一次往返 |
| `game-ipc/process-exit.json` | 场景文件 | 合法场景 | 进入 Failed，取消请求并异步回收 |
| `game-ipc/hidden-info-safe.json` | 合法 | 安全 | 私有手牌仅发给 `player-a` |
| `game-ipc/hidden-info-unsafe.json` | 合法 | 安全策略非法 | 测试因隐藏字段广播给多人而拒绝 |

“Schema 合法但语义非法”是刻意的测试向量；跨消息状态和信息流策略由自动化语义校验覆盖。
