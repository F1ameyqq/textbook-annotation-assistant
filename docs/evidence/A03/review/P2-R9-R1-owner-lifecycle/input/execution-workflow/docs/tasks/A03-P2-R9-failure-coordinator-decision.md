# A03 R9 首败调度判定

2026-10-18。固定目标 `c83f956c5c29c64ab10735ba11c153201d3f3f4b` 的 **正常执行→报告发布 ownership 衔接缺陷已确认，结论 REWORK**。不是合同歧义，也不能靠提前释放驱动租约解决。

依据为 [独立故障复核](A03-P2-R9-failure-review-report.md) 及 [调度只读复核](../evidence/coordinator/heartbeat-20261018-0529/review-audit.json)。调度复核 351 个 manifest 条目、273 份 raw Git 输入、10 个审查登记进程退出，并从四份冻结库建立自己的 immutable 副本核对全部表与正式 receipt/fact 绑定。未调用候选产品或重演 D1/D2。调度辅助脚本第一次误用导出路径，按已核对 input-index 修正映射后通过；原脚本及错误说明保留，不计为产品失败或产品复跑。

原 D1 已产生唯一效果，正式 APPLIED/ATTEMPTED 回执存在；POST/Batch/report-read 均为0，最终租约已释放。源码显示 run_plan 持有自己的有效租约时进入 native 报告入口，该入口再次 claim，被 storage.claim 的既有 OWNER_BUSY 门禁正确拒绝。

批准原执行对话按 [R9-R1 有界修复](A03-P2-R9-R1-owner-lifecycle-repair.md) 处理两份 recovery 模块及对应两项 implementation pins/profile/adoption 摘要链，保留并发与报告读取门禁。只在新的离线 case 验证四项既定范围，不对已有成功效果重新执行。

本轮仅归档故障证据和派发修复，没有产品 ACCEPTED/INTEGRATED；整个 A03/I01 未释放。先前 R3/R4 有限验收保持，原 P2 更广覆盖缺口、B 版本映射与共同合同确认不变。没有推送或共享给 B。
