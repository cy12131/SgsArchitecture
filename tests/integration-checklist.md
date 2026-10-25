# M3 Dynamic Integration Checklist

这些项目无法由静态 JSON/Schema 测试证明，完成前 Lua Runtime API 和 QML Extension API 保持 Draft。

## Linux / Lua / Boost.Asio

- 在真实 Linux 子进程验证双匿名管道的 partial read/write、EOF、1 MiB 帧和 4 MiB/256 帧背压。
- 证明 Lua `game:request` yield 时 SgsServer 网络 event loop 持续处理其他连接。
- 用真实 timer 竞争测试 reply/timeout/disconnect/Shutdown，只恢复协程一次。
- 注入 Lua error、SIGKILL、父进程关闭和 cleanup error，验证事件栈清空与异步 reap。
- 验证只读 package generation、LUA_PATH 隔离及无 Git/网络获取。
- 运行中执行添加/更新/启用/停用，确认当前 `manifest_id`、Ready 连接和新建 Lua 对局均不变；正常重启后才选择并锁定已验证候选 generation。
- 以固定 seed/输入重复运行，比较 GameOutput 和 GameFinished 的确定性。

## Windows / Qt / QML

- 真实 QQmlEngine 加载包入口、qmldir 依赖、缺失 import 和 fallback 页面。
- 多 token 并发、timeout 后点击、重复点击和非目标 token 均不发送越权回复。
- snapshot/delta 重复、乱序、gap、页面重建和重连后的 resync。
- GameEnded/断线/服务器重启后重连并切换包 generation 时销毁页面，使用 QPointer/queued signal 检查无失效对象调用；管理员操作本身不得触发切换。
- 验证 `sgspkg://` 路径逃逸、符号链接、跨依赖访问以及图片/声音/动画加载。
- 检查私有 state/request 数据不进入其他玩家模型、日志、singleton 或错误页面。

## 端到端

- 运行 examples/minimal-runtime-package 对应真实双人流程，包括正常回复、超时、断线、异常退出和不同玩家视图。
- 记录 Linux/Windows 版本、锁定 commit、manifest_id、消息 trace 和测试结果；静态样例不得替代该报告。

## M3-C 跨资源包皮肤扩展验收

以下项目必须使用相互独立、分别锁定 Git commit 的武将包仓库和皮肤包仓库完成；不得为样例增加 SgsServer/SgsClient 专用分支代码：

1. 武将包通过 GeneralRegistry 候选接口正常注册武将及默认资源。
2. 声明 Manifest 依赖的独立皮肤包通过 SkinRegistry 候选接口，为已有稳定武将 ID 添加额外皮肤、技能语音、阵亡语音和动画。
3. 完成绑定时武将包内容和 commit 保持不变；只更新皮肤包即可增加扩展资源。
4. 注入缺失/损坏的立绘、语音和动画，ResourceResolver 安全回退到武将默认资源；不得越权解析其他未声明包或本地路径。
5. 管理员停用皮肤包时当前 generation 不变；SgsServer 正常重启并由客户端重新同步后，SkinRegistry 不再含该包注册项，武将恢复默认资源。
6. 运行 trace 同时记录武将包与皮肤包各自的仓库 URL、锁定 commit、manifest_id、依赖拓扑及实际资源 owner。

另需覆盖目标武将不存在、未声明依赖、重复皮肤 ID 和循环依赖；均应确定性拒绝且不得以加载顺序覆盖。
