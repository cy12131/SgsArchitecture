# M3-P4 Dynamic Integration Checklist

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
