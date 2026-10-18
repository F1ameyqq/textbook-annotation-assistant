# A03-T1：取证同步与异常读回闭环

适用[交接拆分约定](A03-redispatch-2026-10-18.md)。产品基线 `1330047dd29890dea0e433ff01b991f615bf78f4`，执行在派发的独立 worktree 新建 `codex/a03-t1-capture` 分支；不得在原 A03 或主目录工作。交接证据提交另见派发。新对话 xhigh。

## 执行范围

修复的是新取证驱动，不改产品。只新增 `examples/a03/T1-capture/`、`tests/test_a03_t1_capture.py`、`docs/evidence/A03/T1/execution/`、`docs/tasks/A03-T1-execution-report.md`。旧 R12-R2 驱动、失败包和所有 src/pins/schema 只读。工具需以小模块/API供T2导入，不能把runtime规则复制进测试。

先用无业务效果的临时 SQLite 夹具验证写线程同步、连接关闭/事务结束与原字节复制；明确取证时所有自有写者状态、边界及生命周期，不能靠 sleep 猜测，不能删除 journal/WAL/SHM 或在活动写入时用 immutable 审计。若采用新复制技术而非原始字节副本，必须说明其证据含义，不能标作 raw 原件；本任务业务阶段仍需可核对的静止原件。

冻结工具/输入/预期后，做受取证改动直接影响的 L1、U1 对照以及 U2–U5，各一个新目录、各一次。原含义和观察故障见 [R12 五例](A03-P2-R12-inconclusive-readback-validation.md) 与 [R12-R2](A03-P2-R12-R2-issue-ownership-repair.md)。L1是唯一legacy对照，U1部分效果；U2重复身份、U3矛盾、U4截断、U5不可用均以真实正常applied+unavailable先建立UNKNOWN，再释放并由新进程对账。每次只dispatch一次、reconcile max_attempts=1；目标恢复新增效果为0，保持合法未决/暂停、原receipt/progress及历史，不发布POST/Batch，native_report_reads=0。不重跑C、R9–R11或field reset。

保留建立前、UNKNOWN建立后、释放后、恢复前后适用阶段的双库原件及真实正式产物；相同字节允许引用同一原件，不能省略逻辑阶段。小夹具与业务错误分开记录。新增驱动错误最多一次有界修正，规则见共同约定；不把采样失败直接归为产品失败，也不把业务返回当作完整通过。

交付干净代码提交与证据提交、最短命令、工具导入说明、六场景实际矩阵、原件/摘要、全部自有进程和owner释放。本任务产品固定不变；若产品缺陷阻挡，交确切输入/调用/错误给调度，不能自己修改src或要求T2随意改。

## 独立验收范围

新验收对话只写自己隔离副本及 `docs/evidence/A03/T1/review/`、`docs/tasks/A03-T1-review-preparation.md`、`docs/tasks/A03-T1-review-report.md`。首次核对任务与固定已知失败，准备后结束等待；调度交完整 target/manifest/release 后，从该确切提交建立独立副本，检视同步机制并在新目录复验同一有界六场景，不复用作者数据库，不增加业务标准。确认不是靠丢证据、改时限或更改产品通过。只有范围全部满足才建议有限 ACCEPTED，工具先经调度接受再供T2消费。
