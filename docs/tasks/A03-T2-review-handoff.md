# A03-T2 固定 C12/H1 独立验收交接

2026-10-18。继续已有独立验收对话 `01a14ccf-a5c1-71f2-a6eb-90ea011d8705`，xhigh；不新建、不联系作者或旧A03/B、不委派。沿用[T2任务](A03-T2-history-and-report.md)、[准备范围](A03-T2-review-preparation.md)及[拆分约定](A03-redispatch-2026-10-18.md)。本交接提供此前缺少的固定交付与已接受依赖，现在开始一次完整有界验收，不再停留于准备。

| 输入 | 固定值 |
| --- | --- |
| 完整代码与证据 target | `699f748a124162b3118e3996c03757725daac363` |
| 执行前冻结候选 | `f111eb609d065a2506da52007c3b283928d537aa` |
| 产品基线 | `1330047dd29890dea0e433ff01b991f615bf78f4`；target的src/根依赖相对它无改动 |
| 已接受T1工具的T2集成 | `86ae44b27e7d4825bd05d54701072f4068151bb9`；仅 `examples/a03/T1-capture/capture.py` |
| 工具raw SHA256 | `3e07d56f409d8203c42f252f7a2900e902e31f56e1ff5fc7475335d33d0b042b` |
| target执行报告 | `docs/tasks/A03-T2-execution-report.md`，从target读取，不以主目录旧报告代替 |
| target manifest | `docs/evidence/A03/T2/execution/manifest.json`；SHA256 `a64c32a7607d86eab259540e31e061c200c4db4e10a13db4d62b234fa60cf08e` |
| target释放证明 | `docs/evidence/A03/T2/execution/sealing/final-release-proof.json` |

调度[交付准入核对](../evidence/coordinator/heartbeat-20261018-0322/checks.json)已从raw Git复核317个manifest成员，无摘要/长度差异；冻结候选后212项变化限本轮证据/静态封存及报告，执行文件和产品未变。作者工作树干净、执行对话completed/idle；15个完整登记Popen退出且无timeout，三个keeper均停止，最后owner/PID为空、lease=0、phase=RELEASED。准入不是功能验收。

作者的C12和唯一H1为PASS_AUTHOR_ONLY。H1七阶段14份双库原件、UNKNOWN历史及一次新鲜报告已封存。特别保留 `sealing/process-recording-limit.json` 披露的三次同步静态Git调用元数据/流缺口：不得补造历史PID/原流；独立判断它是否影响本范围的版本与业务证明，并在结论中限定。不能因作者报告声称通过而跳过真实业务/导入/阶段原件复核，也不将这个静态记录缺口自动升级为无限新测试。

在自有 `D:/1800/.local/A03-T2-independent-review` 下新建create-only副本/输出，用target的raw Git与冻结 `examples/a03/T2-history/inputs.json` 明确的实际执行字节物化；原src checkout为CRLF，实际执行使用固定runtime-view。逐项核对输入及23pins/profile/adoption和真实导入路径，不能改pins或用换行差异迁就。旧准备manifest绑定旧准备提交的报告，不能拿它的历史SHA去要求本次报告相同。T1工具接受依据见[调度报告](A03-T1-coordinator-acceptance.md)。不用作者的最终库作独立输入，不复制旧历史全集。

审查四文件现有归属修复与受影响历史consumer、公开C01严格性/私有证明及报告观察边界；然后原C最多12项一次批次、唯一H1一次，具体冻结命令和输入见target报告。H1一次dispatch建立applied+unavailable的真实UNKNOWN，释放后新进程一次max_attempts=1完整reconcile，保留原UNKNOWN事实/回执/Issue且终态链绑定原receipt/intent；再一次现有publish入口独立新鲜读回，native_report_reads=1，零恢复/报告新增效果，HOLD/CONTENT_PENDING/NOT_SUBMITTED。原预算、取证静止边界及一次有界驱动纠正规则不变。只重跑明确新增驱动首错及未运行后继，产品错误直接给反例；不重跑T1六例/旧全套，不加业务起点，不修改产品/工具/预期。

输出仅自有隔离目录、`docs/evidence/A03/T2/review/`、`docs/tasks/A03-T2-review-report.md`。保留准备报告与首错；不操作主目录Git索引/提交或协调JSON。交一个明确有限ACCEPTED/REWORK/BLOCKED结论、确切版本/实际执行摘要、实测结果与适用原件、真实退出及最终释放。完成后结束等待调度；A03整体、T3组合与I01不由本轮宣告完成。

全部离线，无网络/平台/browser/profile/凭据/安装/模型/OCR/推送/书级送审/A05题22。每条Git显式 `-c core.longpaths=true`；field reset保持 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`。
