# A03 P2-R5 调度收口

2026-10-17。冻结交付 `323013c4f0dbae75368e56db60147a8057368d1f`。原独立验收对话 `01a145aa-8d59-7c70-8d81-731712103a9a` 已完成 turn `01a14979-29b0-7472-83f4-5a7a3010963f`。整体 **REWORK_CONTROL_INPUT_PROOF**，六项指定静态范围记录 **ACCEPTED_STATIC_LIMITED**。这轮剩余问题是混合环控制输入的内部头引用，不把它记为已证实的实现缺陷。

依据：[独立报告](A03-P2-R5-registration-context-review-report.md)、[审阅清单](../evidence/A03/review/P2-R5-registration-context/sha256-manifest.json)、[调度复核](../evidence/coordinator/heartbeat-20261017-1059/A03-R5-review-check.json)。报告 SHA256 `f4831a2f8274f3cad718b440b0bd647ccd726ba997dafb5e0089028d2fb5ab5f`，清单 SHA256 `bff7b99b110f8c104317357460a41b05de72ec73f997d3c6c7dd19f65e60f496`。

调度核对全部 309 个清单项及清单自身、225 份隔离输入与确切 raw Git blob，并运行只读归档校验。只复现完整正包和 target 负控两次入口：正包返回 STATIC_ACCEPTED，经过混合图、消费者声明/book/scope、Artifact 摘要及固定 R2 尾段；target 负控返回 FRAME_REGISTRATION_TARGET。复现前后审阅归档字节不变。审阅方九条自有同步运行及调度三条同步运行均已结束；释放证据来自父进程 wait/return 记录，不冒充当前 OS/profile 扫描。

| 指定静态范围 | 调度决定 |
| --- | --- |
| registration-positive | ACCEPTED_STATIC_LIMITED；完整入口接受，16 个真实消费者、6 个全局 frame，None-book 真实消费者为 0。 |
| source-binding-negative / snapshot-binding-negative | ACCEPTED_STATIC_LIMITED；两个冻结反例在实际登记消费者层按预期拒绝。 |
| target-tuple-negative | ACCEPTED_STATIC_LIMITED；目标字段不一致被对应 target 绑定检查直接拒绝。 |
| 原 R3 未声明正式 evidence / 全局 Resource 摘要损坏 | ACCEPTED_STATIC_LIMITED；两项既定防回归拒绝成立。 |
| artifact-resource-frame-mixed-cycle repair-01 | REWORK_CONTROL_INPUT_PROOF；观察到 MIXED_CYCLE，但控制中仍有独立的内部头不一致。 |

调度只读重算 mixed-cycle prefix 的事件链与摘要，确认第 8 条 READONLY_ABSENCE_STARTED 的 initial_event_head.sequence=7，但 hash 仍为 `87f8f86767e923c8fe7eb351c45eb57df3d6d4ebfdf855249fc7f5be025bbf84`；实际第 7 条事件及第 8 条 previous_hash 为 `28ef8b468d67a04e9ba75fe3e41a45fb96f280deb95ddcef4cdc2097d6c195f9`。prefix 原始 SHA256 为 `4d153e82f0a75d233bb77bb7028a2a3dc2bdbcd4f22bda6514a15d0be4450de0`。本次没有再次执行这个不合格控制，也没有改动它。

批准 [R6 单一控制输入修正](A03-P2-R6-mixed-control-rework.md)：原执行对话在新路径复制这一冻结输入，只修已定位的内部头及必然传递的摘要/引用，先做数据一致性核对，再用未修改的 R5 完整入口执行一次。已通过六项不重跑，校验器不修改；出现新的独立缺口即保留最短失败停止，不自动派生下一轮。R5 的首版失败和 repair-01 原样保存。

R4 有限接口设计接受、R3 消费者闭包及 SESSION-02/CONVERSION-07 有限静态接受保留。A03 持久化/未知保存恢复产品功能、R17 实际调用链、原生 PRE/版本桥接与 I01 仍未通过。三个 ABI 决定仍须在单独的产品实现任务中冻结，不能因静态检查通过而开放当前写入资格。本轮仅本地归档，不集成产品、不推送、不联系 B。字段重置专项继续 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`。
