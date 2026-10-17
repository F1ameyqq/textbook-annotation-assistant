# A03 P2-R11 四个崩溃切点独立验收

2026-10-18（Asia/Shanghai）。原独立验收对话 `01a145aa-8d59-7c70-8d81-731712103a9a` 续接。保留用户现有 model/thinking，不委派。依据[已冻结执行任务](A03-P2-R11-crash-cut-validation.md)的原 V02/R03 四个切点验收，不增加业务标准、不改候选产品。

## 固定输入与交付预检

- base `1c26b4a8eb378af33e57668472d2071e9ea6afff`；唯一 target **`cc5966dc58c62017a27266c40ca0cedc5c68485c`**，直接父子关系。
- 执行目录 `C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800` 仅供读取冻结交付；不得在作者目录运行案例、修改或接续原库。本任务单从派发消息指定的 workflow commit 读取，不合并浮动主目录。
- target 报告 `docs/tasks/A03-P2-R11-crash-cuts-report.md`，SHA256 `87f76010b1b8bfe229279ad6f72dcf6f804ad903c20f5137a96becbbff8ec051`。
- target 证据前缀 `docs/evidence/A03/execution/P2-R11-crash-cuts/`；`manifest.json` SHA256 `d9c2b748934c65c03f464a38c8a52740936f8df66736ab3a1c5d64af1ed82d40`；`process-release.json` SHA256 `a552f8e1981801a92e54d7ae79ac1705060d0d5e17d06b91a1273f680ec2cac3`。
- [调度预检](../evidence/coordinator/heartbeat-20261018-0730/delivery-preflight.json) 已检查 580 个新增 raw blobs、579 个 manifest 条目、32413 个旧 mode/type/blob 条目不变、确切任务身份、19 条进程登记/完成/释放记录（四个 crash exit90），当前登记 PID 均不存在。作者工作树干净。预检没有导入产品、重跑功能或作验收结论。

作者报告四例各首轮通过，最终 effects 为 0/0/1/1；但 **F2/F3 切点及恢复前中间 SQLite 没有另存二进制原件**，只有完整 SQL 行集、当时 raw SHA、事件及不可变 artifacts/Resource。其运行前副本和最终原库存在；F1/F4 最终库与切点字节相同。保全声明在 `stage-binary-preservation.json`。该遗漏不可从 SQL 重建补称原件，不能从不存在的文件重新核验当时 raw SHA，也不能因作者功能退出成功就判证据完整。

请分别判断作者现有证据的支持范围和独立运行的结论。下述四例独立运行已在原任务中授权；它们形成新的独立证据，不能追溯填补作者原件。无需让作者重跑，也不追加“补测”轮数。如果原标准某项最终仍缺证据，给出具体条款和有限结论，不绕过标准。

## 独立执行及证据边界

从 exact target raw Git 导出必要 src/config/固定 fixture/helper 到自己的新隔离目录，登记输入路径、原始字节摘要和实际导入；不复制历史全集或作者数据库为种子。产品、schema、profile/adoption/pins、oracle/producer/verifier、依赖只读。沿用固定32×32单题两片段 SYNTHETIC、同书注册 scope。

允许正常 import 冻结 helper 或编写薄驱动。首次功能前静态核对既有故障点、事务边界、正常入口及证据采集路径，冻结完整驱动/输入/预期/超时。可在薄驱动中补足原任务要求的阶段双库保全；不得通过修改产品、AST/exec 裁剪、monkeypatch、直接 SQL 业务写入、伪造时钟/PID/lease/私有资格来制造结果。原旧 helper 仅正常 import 需要的工具，不运行其旧案例。

每例使用首次不存在的路径，经正常 init/register、PRE begin/produce/admit、targetcheck/planner/record 建立合法单动作。由同一合法 owner/PRE 上下文正常 run_plan，在原 FaultController 指定点真实 os._exit90。父进程 wait 确认执行 PID 已退出，才启动不同 PID 的新查询/恢复进程。

| 案例 | 切点 | 核验范围 |
| --- | --- | --- |
| F1 | BEFORE_INTENT_COMMIT | 已接纳/预留 plan/action 与尚无 intent/permit/effect 分清。新进程仅 open/status/query、正式记录与双库核对；不 project、不 reconcile、不派发、不伪造 UNKNOWN、receipt 或未尝试结论。记录实际 plan/owner 状态，不为清理改写。 |
| F2 | AFTER_DISPATCH_STARTED | intent、消费 permit 和 DISPATCH_STARTED 已持久化，effect=0。新进程先保存原未决/事件，正常正式投影 UNKNOWN；仅一次 reconcile、max_attempts=1，由完整精确绑定的新独立观察取得 ABSENT/NOT_APPLIED。保留真实 attempt_fact，不能将效果不存在解释为未调用。效果始终0，原动作不重发。 |
| F3 | AFTER_READBACK_CAPTURE | effect=1、执行读回已到达，但正式结果未提交。新进程保留原未决/UNKNOWN，再一次 reconcile、max_attempts=1，凭新独立观察取得 MATCH/APPLIED；不得重用退出进程的内存结果。效果保持1，原 UNKNOWN/intent/尝试事实保留，无重发。 |
| F4 | AFTER_RECEIPT_COMMIT | effect=1，正式结果/回执及精确 plan/action/intent/fact 绑定已持久化。新进程仅 open/status/query 与实体/双库读取，不 project、不 reconcile、不生成 resolution 或重发，不回退为未执行。POST/Batch 尚未执行则如实记缺失。 |

按 F1→F2→F3→F4 各一次。仅 F2/F3 两次 reconcile 获授权。核对原 marker、真实 exit90、故障点源码位置、持久化事实及新进程顺序；不能以单个日志或空效果表替代调用事实。核对新观察序列、会话/实例、target/source/scope、plan/action/intent、观察/快照、正式解决和 Resource 绑定。F1/F4 查询前后字节应按事实记录；F2/F3 原历史不可改写。plan 状态、attempt_fact、正式产物缺失等遵循既有产品语义，不猜测状态后再改代码。

原任务要求的故障前后/恢复前后双库须在发生后续修改前实际保全：特别是 wait 后切点原字节，以及 F2/F3 原未决和正式 UNKNOWN 阶段。记录每份实际文件的路径、SHA、采集时序、当时是否有自有 writer/keeper；两个库顺序读取不称原子快照。保留 SQL 全行、原事件、正式引用及 Resource，与实际原字节交叉核对；禁止重建中间库冒充现场。只读后验检查使用自有副本/immutable，不能污染冻结原件。

父 watchdog90秒、业务 child45秒；产品观察2秒、屏障5秒、lease10秒及恢复期限不改。死进程 lease 只走原 claim_current 有界路径，不清锁、不固定 sleep 猜接管。保存 PID/instance/owner/generation、argv/cwd/imports、timeout/exit、实际原始输出和进程释放。os._exit 没有 finally 记录时如实记录，不按预设数量补造证据。只等待/释放本轮已登记自有进程。

首个功能失败/超时即停后续组，保留现场和未执行项，不改驱动后重跑到成功。首次功能前允许静态准备；执行后仅归档/元数据错误最多一次静态纠正，保留首错，不重调产品。不重跑旧 AFTER_INTENT_COMMIT、丢回执 N1、R9/R10、旧 R3 N7、其他故障组或整套回归。

## 交付

报告 `docs/tasks/A03-P2-R11-crash-cuts-review-report.md`；全部独立驱动、raw 输入、命令、原始输出/marker、实际各阶段双库/资源、进程登记/释放及 `sha256-manifest.json` 仅放 `docs/evidence/A03/review/P2-R11-crash-cuts/`。manifest 覆盖报告及本轮所有必要文件，只排除自身。不要改产品、作者目录、历史证据或调度 state。交付确切 target、各例独立判定、作者证据限制、独立证据支持范围、未执行项、命令和释放证明。

只对这四个原 V02/R03 单题切点给出 `ACCEPTED_FOUR_CRASH_CUTS_ONLY` / `REWORK` / `BLOCKED`，必要时逐例列出有限判定。whole A03、其他原清单覆盖、产品本地集成及 I01 均未放行，最终由调度核验登记；B 版本映射仍未共同确认。

字段重置始终 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`，不运行、变体、委派或建议重测。零网络、平台/浏览器/profile/凭据、OCR、付费模型、安装、推送、B 联系、A05题22、书级送交；保留用户 model/thinking。
