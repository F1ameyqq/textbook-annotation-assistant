# A03 R9-R1 调度收口

2026-10-18（Asia/Shanghai）。唯一 target `bfd7fe896a7eee663ea8e0b6cf967548d8dd8f39` 的 **ownership 修复及 D1、standalone、borrow、D2 四项固定单题演示有限 ACCEPTED**。整个 native A03 未完成，尚未整体集成，I01 未释放。

依据：[独立报告](A03-P2-R9-R1-owner-lifecycle-review-report.md)，SHA256 `e3963a6b8cd387e22eaa1a88008cde39f5ce5769488798f798dab2c2b8e61fd5`；[调度只读复核](../evidence/coordinator/heartbeat-20261018-0614/review-audit.json)。独立验收 turn `01a14bd7-7b4b-7610-92f8-72b112a82f70` 已 completed，cursor `abdea222-4697-4046-86b1-a5dc48889fac:50`。

## 接受的行为

- 正常运行传递当前 owner/generation，报告发布复用当前租约；不会再重复 claim 导致 OWNER_BUSY。正常单题效果一次，正式 POST/Batch 仍为 PENDING、NOT_SUBMITTED；另一进程重开及旧计划再次调用不增加效果。
- standalone 发布自行 claim/publish/release；借用发布不抢占、不释放外层 owner，也不停止外层 keeper。四类不合法 owner 参数拒绝，重复报告读在第二次观察前拒绝，效果和报告不增加。
- D2 在 AFTER_INTENT_COMMIT 真实退出90，重启先保留 UNKNOWN，再由一次完整、精确绑定的 ABSENT 观察得到 RESOLVED_NOT_APPLIED。效果始终0；MAY_HAVE_BEEN_ATTEMPTED 保留，旧计划仍 INTERRUPTED，不能自动重发。

独立四组均在全新隔离 case 首轮完成。作者原 borrow FAILED / D2 NOT_RUN 原样保留，独立新驱动只在首次执行前修正具体异常预期，不回写作者历史。

## 调度核对与限制

调度核对1124个manifest条目及清单自身、585份raw Git输入、33个已登记进程的原始登记/输出/退出，并另建18份自有immutable数据库副本核对全表、正式artifact摘要、plan/action/intent/fact/receipt与效果数量。复核首次通过；不连接原库、不导入产品、不重跑四组。

独立审阅的两次辅助失败继续保留：D2计划状态的只读断言修正一次后通过；额外采集器错误要求6份退出导入记录，但真正os._exit的D2只有故障前导入记录，该采集器仍FAILED且未重跑。D2实际PID、故障前导入、marker、退出90及其余5份退出导入记录可核对；完整清单与33个退出记录独立成立。因此不以辅助采集器失败推翻已核实的四组业务结果，也不把它记为成功。

本次只归档证据及范围接受，不把四份修复文件单独移植到缺少完整native依赖的主目录。产品集成仍待原P2必要范围闭合、明确依赖清单及集成检查；本地归档不等于推送或B确认。

## 下一步

续派原执行对话的[双进程占有权有界验证](A03-P2-R10-owner-fencing-validation.md)，对应原V06/R09中的两个明确子项。它是原范围补验证，不是本轮修复失败；不新增产品实现或扩展题型。

仍保留原多动作/混合尾段、充分/不足ABSENT完整矩阵、新检查/真正新计划、跨scope/run/书隔离、其他崩溃点、资格/身份/版本、归档转换与真实来源拒绝、报告/分母/次数等未覆盖项。当前PRE仅支持固定32×32单题两片段，多动作需另有明确采用范围。B包的版本映射仍待共同确认。字段重置保持 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`。
