# A03 P2 实现与合同补充提案

状态：REVIEW；最终实现 `fa645ac8fd70688f3293edc5cfb1077fc7bd9daa`，功能实现有明确阻断，不能作为验收通过。主调度已批准P2；基线 `940a5de33a24b1a3a9ded6e69ade1dd0609ed83a`，workflow `6b77c436742cf2826083b109d8ed86b85539cba6`。历史P1/R1/R2文件不改。

## 需主调度补充的最小前缀合同

已冻结R2 `event-prefix.schema.json` 的 `from_sequence=1`、`genesis_hash=64zero` 是常量，逐事件只允许同一plan_ref的九种事件。它完整描述了P1的单计划静态输入，无法表示P2当前书真实全量journal中的owner领取/激活、后续PLAN_ACCEPTED的全局序号或已有RECONCILIATION_COMMITTED；原R2提案也明确样例没有插入其他运行事件。

严格实现时，领取事务已记录OWNER_CLAIM_RESERVED/OWNER_ACTIVE，再接受计划的PLAN_ACCEPTED实际为3；不能重编号事件、改变intent/fact序号/前驱、丢弃控制/其他计划事件或把另一个摘要称为完整权威前缀。把owner独立移到另一日志只能掩盖首例，不能解决后续多计划/终局事件。

最小建议：保留七份R2 Schema及旧profile原字节，在 `src/annotation/contracts/` 增加单独明确选用的P2事件前缀profile和Schema（建议format `a03-runtime-event-prefix-1`）。精确采用实际PLAN_ACCEPTED全局起点及其真实前驱，末点为当前书实际head；完整保留期间事件，用封闭事件种类及逐类payload定义解释owner/control/reconciliation和其他计划。动作未调用判断针对已接受计划/动作的永久身份预留；完整book账本和当前owner/generation/CAS仍只由runtime受控事务证明。新profile选择不能依据“最新版”或只复用旧顶层字符串。

批准前，专用未尝试事实入口保持失败关闭，不以自报complete或序列投影通过。该补充影响合同语义，当前没有改旧schema或自行放宽；其余已批准P2实现继续。最小静态见证与实际规则错误保留于 `docs/evidence/A03/execution/P2/prefix-contract-gap/`，不宣称它是恢复功能验收。

## 本地运行与公开入口

实现使用现有 Python/Pydantic 与标准库 SQLite。运行库 `runtime.sqlite3` 和独立目标 `target.sqlite3` 分别提交；目标在效果事务中保存业务状态及效果计数，运行库不能用 receipt 反向重建目标。显式 `init_state` 创建新库；`open_state` 只打开已有固定 anchor、ledger/store/目录及版本，缺失或损坏均关闭。

`annotation.runtime.storage` 提供冻结 API 的 intent、结果、reconciliation、book context、归档、专用未尝试事实和 hold 入口；后者未尝试事实目前返回 `EVENT_PREFIX_CONTRACT_GAP`。`annotation.runtime.recovery` 编排 `run_plan`、`reconcile` 与纯报告投影。局部 CLI 是 `python -B -m annotation.runtime.recovery.cli --request <JSON>`，操作包括 `init/run/status/export/target-status/reconcile/replan/quality/detect-drift/clear-hold/import-history/tail-absence`。

每个书键为固定 platform_namespace/target_id/book_id，与 run/scope/action 无关。接受事务永久预留所有动作；效果前 native PreparedAction 必须通过当前 observer 的真实观察与不可变摘要回调，再依次取得、消费单次许可。复制字典、反序列化对象、真值 binding、旧进程对象及旧 generation 不能重建权限。跨 scope 未决由当前受控账本扫描，普通 validator 仍只验证同 scope 引用与链。

owner lease 为10秒，运行及恢复期间每2秒续租；占用 gate/屏障最长5秒、SQLite busy1秒。只读恢复在每次读取前持久登记尝试，同 call_id 重启不清空额度；每intent最多3次、单读2秒、intent窗口8秒、整次调用60秒，采用最早截止时间。超时只终止自己启动的读取进程并回收句柄，保存失败 Resource，不派发旧动作。CLI 超时为6、仍有未决为3、指定进程故障默认90，独立目标效果提交后故障为87；以每次实际日志为准。

新报告保留原 UNKNOWN/intent/fact/result 字节，通过精确解决链头计算有效状态。完整 receipt 才能产出新 POST_APPLY/BatchReport；部分 progress、未知或零分母只输出诊断。内容保持 PENDING，提交保持 NOT_SUBMITTED，不生成 COMPLETED 或 0/0=100%。归档未知分母诊断明确是 ARCHIVE_ONLY，不取得运行准入。

## 交付边界与尚未证明的部分

终局解决后的外部业务状态漂移可追加 TARGET_DRIFT_HOLD；正常受控 APPLIED 前缀用于更新比较基线。hold 阻断效果许可，保留原解决结论。冻结的 `clear_target_drift_hold` 要求真正新快照、新 PRE_APPLY/TARGET 和候选计划，并持闸重新读取及 CAS。现有 CLI 能做新快照/TARGET/计划，但没有新的 PRE_APPLY 生产者；不会将旧 PRE 改 ID/时间充数。合法外部新 PRE 的正向解除尚待独立验证。

冻结 POST_APPLY 合同还有两个可表示性限制：若原解决结果产生时没有 receipt，随后新完整 receipt 不能通过改写历史结果补上；多个恢复头绑定不同实际 snapshot 时，单一 POST snapshot 也不能同时等于全部头。producer 对这些输入输出 `REPORT_CONTRACT_GAP` 诊断，不生成伪报告，不解除运行库暂停。正常完整 receipt 和可表示的精确链仍可产出报告。

旧 exceptions 样例的未入图谱题缺独立页枚举，新全合成准入拒绝转换；其完整分母只在原字节归档诊断验证，不宣称已通过运行时执行。来源完整性 S01、真实书籍/平台、OCR/模型/费用表现、任意外部平台写者、断电耐久和最终人工提交均未测。本次被测系统网络、浏览器、OCR、模型及收费API调用为0。

最短新目录演示和完整过程命令见 [P2 README](../examples/a03/P2/README.md)。报告与全部失败记录在 [执行报告](tasks/A03-execution-report.md) 和 [P2证据](evidence/A03/execution/P2/)。长路径证据在 Windows Git 中需对本次命令使用 `git -c core.longpaths=true`；没有修改全局设置。已有状态目录故意绑定绝对身份，跨目录复现应重新生成全新状态，不能移动旧库冒充同一目录。
