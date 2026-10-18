# A03-T3 M 首例超时：独立静态复核

2026-10-18。续派已登记 T3 独立验收对话 `01a14ccf-b8c3-7941-a80f-73594e7859a5`，明确 xhigh、model 沿用。**只复核固定失败现场与超时调用边界，不重跑 M1 或其余四例，不做 M 整体功能验收。** 执行者已 completed/idle，工作树干净，当前状态 REWORK。

## 固定输入

- 已采用任务：workflow `4fa7237d1114ed2c89f65cbb28579a8956812062` 内 `docs/tasks/A03-T3-M-implementation-handoff.md`；范围/上限继续适用，不加新标准。
- K=`62a023a1c88c20d884a61f38d1ad995b0908b74c`；首次业务前候选=`c73070884476dc2edcb952d88e4f6ed356b74ae8`。
- 最终交付 **`3f39a117b1b98e85c5a449a07f13b3490ef77e18`**，在 `D:/1800-worktrees/a03-t3`。用该确切 Git 对象，不能只依赖分支名或浮动 checkout。
- 目标内 `docs/tasks/A03-T3-M-execution-report.md` raw SHA256=`7d9c35308b594c2d73d9327556f1d77b09be3cbe30b89f211df29c12758bc522`。
- 目标内 `docs/evidence/A03/T3/execution/M/manifest.json` raw SHA256=`f88adb018dc19bcae5c7fcce4b566a374773207e9c6e192e0404dd8fa6e14708`，263 成员。[调度入审检查](../evidence/coordinator/heartbeat-20261018-0437/T3-M-delivery-preflight.json)已一次 raw Git 核对，白名单内差异、候选后产品/输入/业务驱动未变、注册子进程已退出及 owner 释放。仅接纳失败材料，不接受功能。
- 原采用/首错/静态准备/进程/崩溃 DB+journal/清理前后记录均在该目标内。调度检查器首次误将作者数值0与空列表比较，原记录及唯一纠正保留于同一调度证据目录；该错误未涉及业务/SQL。不要把它派给作者或当作产品缺陷。

## 已知事实与本轮问题

M1 execute PID 54532 在 45.031 秒达到子进程上限后 kill/wait，父 watchdog 45.25 秒退出；stderr 为空，未保留终止前 Python 栈。实际1个目标、2次DISPATCH_STARTED、2条effect、6条observation。最后已提交事件 sequence15 为第二次 ACTION_RESULT_COMMITTED；第三 action RESERVED、无intent/fact。没有完整三动作receipt/report。M2-sufficient、M2-insufficient、M3-new-plan、M3-final-drift 均 NOT_RUN。

原崩溃 runtime DB+journal 与 target DB 先逐字节保全，不能当成跨库原子快照。原journal阶段没有独立standalone SQL。正常native open/claim/release后取得的SQL是清理后状态：owner=null/lease=0/RELEASED/generation2，计划cursor2/INTERRUPTED，动作和effect未新增。不能把pending=0解释为M1完成，不把清理状态冒充崩溃原时点。

请一次集中回答：

1. 固定调用链与现有事件/产物时间线能否定位最后已完成调用、下一待完成调用及停顿范围？沿 `run.py` execute 的逐动作路径、capture边界、keeper/gate/事务、合同递归校验和目标读取逐项缩小；明确哪些是证据、哪些仅是假设。不要凭45秒直接断言“机器慢”或“死锁”。
2. 是否能从固定代码证明具体实现/驱动缺陷，或发现明显重复读取/递归工作、锁边界相互等待？给最小文件/函数/行号、因果链和建议修复，不改产品或预期。只看与超时有关的必要差异；M2/M3及全28项不在本次复审范围。
3. 若不能静态确定根因，给**一个**最小有界诊断方案：需要何种调用前后计时/栈证据、应加在哪些位置、如何在既定时限内停止并保全；列清是否需要新的业务起点/dispatch及其具体上限。仅提出方案，由调度固定修复/诊断任务后执行，不能本轮自行运行。禁止直接增加45/90秒或门禁期限来取得通过。
4. 明确既有失败与缺口中哪些影响后续安全诊断，哪些只须保留为历史限制。给下一轮有限修复与验收范围；不要重开已有限接受的T1/T2或把归档包装层缺日志变成无限补证任务。

## 只读边界与交付

只读固定 Git blobs、原文件与已有JSON/SQL导出；必要时可读已封存、无journal的清理后DB副本（immutable read-only），禁止打开或恢复崩溃原DB/journal、触及作者活目录状态。**零产品导入、业务/目标初始化、dispatch/reconcile/报告发布、旧脚本执行、安装/网络/平台/profile/凭据/模型/OCR/推送。** 原件和原失败字节不变，field reset=`NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`。

优先直接读现成证据，批量Git而非逐文件进程；Git显式 `-c core.longpaths=true`，Python `-X utf8`。无需重新封存263成员、编写大审计器或自引用manifest。本轮最多新增 `D:/1800/docs/tasks/A03-T3-M-timeout-review-report.md` 及必要的 `D:/1800/docs/evidence/A03/T3/review-M-timeout/` 小型引用/检查记录；不要写协调JSON、Git索引或提交。记录实际读/进程及限制即可，不为补包装层日志重跑任何失败工具。

结论使用 REWORK（具体缺陷/诊断仍需修复），或 BLOCKED（确切外部缺项）并区分静态复核完成；不能判整个M ACCEPTED。附确切目标、必要引用和下一最小行动、全自有进程退出说明，然后结束等待调度。不得联系B、旧A03或派发/委派产品工作。
