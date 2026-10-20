# A15 正式独立静态预检

结论：`STATIC_SCOPE_CHECKS_COMPLETE_NO_BLOCKING_FINDING`。完整独立预检尚未完成，当前状态为 `WAITING_FOR_NEW_FIXED_RELEASED_AUTHOR_DELIVERY_AND_DELTA_DISPATCH`。独立 E1–E4 实际执行 0 次，原一次额度保持未用；本报告不能激活 live。

正式独立对话：`01a157fe-5cc9-7d91-8bbe-73b376cbe2a5`。调度：`01a15768-1e2d-7781-b29f-1f7376270216`。产品 `bef0204541eedd86e1fab849e8002a83f432cd7b`；失败 final `25f9083b2c8183196a7b2d7671efd40d2ef78713`；基线 `81fab23e3e7e9e32a36d3857a253afc69b5bd3e1`。

输入仅为 `D:/1800-worktrees/a15-independent-fixed` 的固定 31 raw 和 `r1-reference.py`，以及调度指定的权威任务和处置记录。没有读取作者活动目录。写入仅在本静态输出目录。

## 权威与原字节核对

执行任务从 workflow `ec69a4bfd72b64e3bd6c6435ef0ec780fd109249` 独立读取 raw，并以其字段和边界作为标准；未以作者自报替代要求。用户决定 SHA256 `36ffcbb42c030192313773b510c69598651b2c2ffe5fb54162c46b8041e40763`，提案 `eb6aea7ad9b01ccbcaf7710c9c45d7c5c3a80d6efcef4db857838d204d725656`，执行任务 `f7bdf3f43b0fb467dcb43e37ae97dfc77f69894292e54d2f16ab6d252590b4a6` 均匹配。原 task/proposal 摘要标签错误及纠正原件保持；此次未改权威文件。

附加处置任务 SHA256 `1513fa552dd25e1f51dc3ada1d28be936b67c22d96c3fa1165230e30399ab8a7` 已核对，来源为 workflow `077e6a6eda23d617d18bac835870d69aa3a75ee4`。其作用限于同一冻结候选原未执行的作者差量，不是独立或 live 启动指令。

交付清单 `835cdcb94e25bf5d3d1ae91a99a268f4e52035ab9b88e53439f9ea6bd311ba19` 与候选清单 `78382e0b484ad46ab497217683fa3022440a1f570589f538c3d355670d552652` 均匹配。30 个清单成员及清单本身共 31 raw 与失败 final 的固定 Git blob 一致。22 个候选成员在产品和失败 final 中保全。

基线 31,212 个成员在产品和失败 final 的 mode/type/blob 均无变化；产品新增 23、失败 final 新增 31，均在允许路径。R1 对照 SHA256 `3f1e4a425e18ed0e2a28893989f31677ba6b9b7f4b9c3da2800bc925443999c9` 与固定 Git blob 相等。两个 native 依赖亦与基线 raw 相等。详见 `raw-and-source-audit.json`。

## 静态语义核对

| 要求 | 固定源码与结论 |
| --- | --- |
| 默认严格校验 | probe 167–175：无批准返回 `ignore_https_errors=False`；main 851–856、launcher 22–26 默认仅静态验证。仅有效批准结果能启用专用 context 例外。 |
| 显式开关与批准摘要 | probe 215–237：先核 live、证书例外、固定 activation 路径和摘要语法，再核候选与激活 raw 摘要；没有 profile、占用、浏览器或网络动作。 |
| 全字段绑定 | probe 120–164：精确键集与类型，绑定任务、workflow、用户决定、提案、实际候选、调度 ID、run_id、固定目标、profile 指纹、固定输出、例外、各额度及独立预检字段；UTC 窗口大于 0 且至多 900 秒；重复键和未知键拒绝。独立报告 SHA 由受摘要绑定的调度激活记录承载，源码仅校验其格式；后续必须由调度绑定本对话的实际报告。 |
| 所有 live 入口前置门禁 | probe main 857、worker 820、occupancy 862、launcher 27：门禁先于实际资源分支；内部子入口在父 stdin 信号后重核。固定 CLI 不能覆盖任务/目标/输出/额度。 |
| 本轮一次性目录 | launcher 28–30 独占创建新输出和 launcher 标记；probe 197–203、878–882、820–822、862–864 逐层要求父标记并独占领取。标记绑定候选/profile/activation/run/target/额度；未见 A13 标记读写或清除。 |
| 逐跳、方法、WS、子 target | NativePolicy 273–315、NativeGuard 318–434 与 R1 函数体原文相同。只允许冻结同源 GET/HEAD 导航、静态及 session GET；CDP Request-stage 逐跳判定，WS 不 connect，子 target 在暂停态关闭。launch 初始 offline，安装守卫后转在线；service worker block、缓存禁用保持。这里只核源码保全，未重新证明真实网络行为。 |
| DOM 后最终 guard | observe_page 607–631 每个 DOM await 后重核；finalize 634–663 在关闭后收集回调/未完成任务，并在无 await 的序列化前执行最终 guard 判定。与 R1 原文相同，仅认证枚举改为 `AUTHENTICATED_VIEWER`。 |
| 各进程自身计时 | launcher 17–18 使用自身 monotonic 的 90 秒截止；probe main 844 的起点用于本产品 85 秒截止；worker 875 用本 worker 起点形成 75 秒截止；observe_page 610–614 共用一次 45 秒导航/就绪窗口。未通过 argv/stdin/文件传递跨进程 monotonic/perf_counter 起点。product supervise 与传入 hard_deadline 在同一进程比较。 |
| 精确资源释放 | launcher 保留自建 Popen 句柄的前后创建身份、OS 退出观测及 exit code，超时终止自己的 Job/子进程，等待并核 Job 活动数。其 RELEASED 要求前后创建身份相等、after.exit_observed、Job 为零及句柄关闭。product supervise 同样保留 OS 退出/Job 计数，身份不一致会记录错误且阻止成功退出。单独的 RELEASED 文本不能替代后续原始身份/错误/退出码核对。 |
| wrapper 自身边界 | launcher 36、116 明确保留自身 OS 退出身份 UNKNOWN，未把关句柄等同于 wrapper 退出。未沿用 A14 未接受的跨进程时基推断，未改写 A13 wrapper UNKNOWN。 |
| E1–E4 冻结层级 | 仅静态读取 10 个 E1 与 29 个 E2 变体及 E3/E4 驱动。纯门禁、合成目录、一次领取和原 bytes 比较路径符合任务层级；driver 对 subprocess/socket/thread/native/profile/占用/browser/live 入口设拦截，首异常后继 NOT_RUN。没有执行这些函数，也未证明实际差量通过。 |

独立逐项 raw 比较确认 21 个关键函数/类保全（观察/最终化仅上述枚举差别），其余变化围绕新批准门禁、本轮路径、显式启动、局部计时与 launcher。三个工具仅 AST 解析，未 import、未调用其 main、纯函数或测试。仅有一个 context 创建和一个 page.goto 调用点。

## 原打包失败与续派处置

独立从固定 R1 和新源码在内存重建统一差异，23,514 bytes 与原 `.diff` 完全相同，SHA256 `f70dca338aac1d9af8f9da4b9c7656f57d17e222c675e443626300b6137bc91e`。原列出的 17 行全部为 hex `20 0a`，确为 unified diff 上下文空行。本次没有执行原空白检查，也没有修改差异证据。

原单项检查退出码仍为 null，PowerShell 继续 commit 的流程错误、原停止、NOT_RUN 和释放原件全部保留。固定交付记录与树中未见 suite 已执行证据；此静态核对不扩张为对作者活动目录或外部进程历史的观察。该处置没有更换候选、修补产品或恢复已用 suite；它显式解除对原未用一次作者差量的打包阻断。未发现据此需要拒绝本次静态审查的额外额度或改后重跑行为，但原检查绝不能补记 PASS。

## 未证明与下一依赖

本次没有独立 E1–E4 结果，没有实际证书例外、计时、OS 超时释放、profile 占用或网络行为证明。没有认证、书籍读取或保存证明。静态源码检查完成不等于完整预检接受，更不等于 live 可执行。

等待作者首次差量的固定交付及释放，由调度核证并补给固定输入和独立输出白名单后，再处理原唯一独立 E1–E4；本轮不自动运行。之后仍须调度绑定实际报告与候选并另行固定 live activation。首题保存读回仍 NOT_RUN，其他三例 HOLD、Q22 不重放、0 登录提交/业务/B 消息/书级送交。

## 本次执行与释放

仅运行自编 `static_audit.py` 做标准库 hash、Git raw 只读、AST 和源文本比较，退出码 0；其中 14 次同步 Git 只读命令全部退出 0，每次设置 `GIT_NO_LAZY_FETCH=1` 且使用 `-c core.longpaths=true`。这不是产品或 E1–E4 执行，不声称零准备进程。

未产生产品子进程、浏览器、网络连接、profile 访问、native API 调用或实际占用检查。无保留产品句柄或会话需释放；所有分析读写句柄由同步、上下文管理操作完成。未扫描进程，未测量 shell/分析解释器自身的 OS 退出身份。固定输入封存前后摘要复核另见 `input-preservation-and-release.json`；输出清单见 `manifest.json`。
