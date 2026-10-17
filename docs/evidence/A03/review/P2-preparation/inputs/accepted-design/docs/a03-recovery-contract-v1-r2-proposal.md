# A03 P1-R2：完整事件前缀成功样例

日期：2026-10-17（Asia/Shanghai）。状态：**P1 REVIEW / PROPOSED_NOT_IMPLEMENTED**。仅修 `A03-P1-R1-PREFIX-01` 的静态设计/样例矛盾；原 API 入口与资源引用修订的独立确认结论保留。没有运行数据库、恢复 API 或目标效果，P2 未批准。

基线 `ca4fba4f505467228a8164c3999e0cecc54ffc4e`，原 R1 设计 `095ed4aa18a56100ce3aabc4a0d6885ad37ab520`，workflow `a354f95f1d0b40a8f0847b57fa3978cac999e7a2`，A02 代码基线 `ec1b4defbfa3ec0f181d291106fb53313983e493` 均不变。本轮只新增正式任务指定的四个 P1-R2 路径。

权威副本：[R2任务](evidence/A03/execution/P1-R2/inputs/A03-P1-rework-R2.md)、[R1独立复验](evidence/A03/execution/P1-R2/inputs/A03-P1-R1-review-report.md)、[主调度反例](evidence/A03/execution/P1-R2/inputs/coordinator-check.json)。任务 SHA256=`7415a8e74b92e5ee92a52433343e0e92ed910a779b375f89cdc65c71f594ff1e`；报告 SHA256=`788de983f08c401de4e045ccd990b090aecd868bbe9148a3615446e59539c318`。原 [R1提案](a03-recovery-contract-v1-r1-proposal.md) 保持历史原字节。

## 1. 修前问题与修订边界

旧成功例的 C fact→basis→complete_uncalled_prefix 只有 PLAN_REGISTERED、A/B intent 和结果，缺少 PLAN_ACCEPTED、必经许可消费/派发和逐事件 hash 链。新样例补齐这些事实，不能用 complete=true、自报 gate、末项头摘要或仅改事件名来替代真实完整内容。

R2 独立可搬运候选、API、格式定义和检查入口见 [目录说明](../examples/a03/P1-R2/README.md)。原 69 例逐条保留映射、原文件 SHA 和语义触发；只更新前缀相关资源/派生引用。新增三类邻例：缺接受、APPLIED 前缺派发、hash 断链。它们是静态拒绝样例；未来 runtime 的实际拒绝仍为 NOT_EXECUTED。

## 2. 事件编码与可核对 hash 链

新增的 `a03-event-prefix-1` 是非 Artifact 的 JSON Resource，完整内容独立存储，不是另一份未绑定权威账本的摘要。

每条事件必有 `sequence,event,journal_id,target_key,plan_ref,owner_id,generation,recorded_at,payload,previous_hash,event_hash`。时间为带时区的 ISO8601；序号与实际事件顺序决定前后，不依赖按时间选择“最新”。payload 按事件种类固定完整计划/动作、intent、许可或事实绑定，具体形状由新 `event-prefix.schema.json` 定义。

`H(x)=SHA256(UTF8(canonical_JSON(x)))`，canonical JSON 为 sort_keys=true、ensure_ascii=false、separators=(',',':')、allow_nan=false；event_hash 计算仅移除该事件顶层 event_hash。`event[i].previous_hash=event[i-1].event_hash`，示例首事件前驱为 64 个零。不得只计算事件名称列表或把前一条业务摘要冒称事件头。

prefix 头固定 format_version、journal_id、target_key、plan_ref、scope_id、owner_id、generation、from_sequence、through_sequence、genesis_hash、head_hash 和 events；subject_action_id 指当前仍未提交未尝试事实的动作。首序号/末序号/事件数量连续一致，head_hash 精确等于最后一条事件摘要，basis.expected_event_head 精确等于此头。该示例从 PLAN_ACCEPTED=1 开始，选择没有插入其他运行事件的单书合成输入；它不证明 runtime 当前全书跨 scope 的账本完整性，后者仍由既有当前库事务扫描核验。

complete/design_only 字段不能替代验证。静态校验实际重算每条 hash、前驱、连续序号、头和所有身份绑定，并核对所需事件及合法顺序；不把 manifest 中的 expected 当作实际结果。

## 3. 成功事件序列与原始事实

| 序号 | 事件 | 必须绑定的事实 |
|---|---|---|
| 1 | PLAN_ACCEPTED | 精确计划 ref 及全部动作 ID/完整 action_digest；接受事务已经永久预留这些身份 |
| 2 | PLAN_ACTIONS_RESERVED | 同一接受事务的完整预留索引事件投影，与计划全部动作一致；不引入接受后尚未预留的窗口 |
| 3 | PLAN_STARTED | 计划进入 RUNNING；不授予跳过 intent 的效果权限 |
| 4 | WRITE_INTENT_COMMITTED(A) | 已持久 intent 精确 ref、动作/digest、义务；intent 序号4、其 journal_head_hash 为事件3的 hash |
| 5 | DISPATCH_PERMIT_ISSUED(A) | 精确 intent/action/digest 与唯一 permit_id |
| 6 | DISPATCH_PERMIT_CONSUMED(A) | 同一 permit/intent/action 单次消费 |
| 7 | DISPATCH_STARTED(A) | 同一绑定，位于目标效果之前；不单凭该事件推定效果 |
| 8 | ACTION_RESULT_COMMITTED(A) | 原执行 fact Resource、精确 intent/义务，APPLIED；fact 前驱为事件7的 hash |
| 9–12 | B 的 intent→许可发放→消费→派发 | 与 A 同样的严格绑定与顺序 |
| 13 | ACTION_RESULT_COMMITTED(B) | UNKNOWN，计划 INTERRUPTED；保留原 B 义务与整书暂停 |

当前 C 未尝试，无 intent/obligation/resolution/permit/dispatch。C 的 basis 引用事件1–13的完整前缀，CAS头为13；C 待提交 fact 序号14，predecessor_hash 精确为事件13的 event_hash。前缀没有包含尚未提交的 C fact/事件，不能给 C 补造历史调用。

另外两条原正例使用 A 首动作 UNKNOWN 的分支：事件1–8含完整 A intent/许可/派发/UNKNOWN，计划中断；B 的只读充分 ABSENT fact 可以在事件9登记 UNATTEMPTED_ABSENCE_COMMITTED，C 的前缀截止事件9、待提交 fact 序号10。B/C 都没有 intent；A 原 UNKNOWN/义务保持，不因只读尾部事实被解除。UNKNOWN 之后不允许再发新目标效果，只有既有专用只读事实路径。

`original-unknown-preserved` 与 `recovered-report-binding` 还保留原样例已有的终局 reconciliation 语义：C 的事件10之后，另以事件11 `RECONCILIATION_COMMITTED` 精确绑定原 A 义务及已有终局 resolution。这沿用原 P1 第106行的既有提交语义，不增加恢复入口。`runtime_claim.post_prefix_events` 引用可搬运的 `a03-post-prefix-events-1` Resource，含事件10/11、前驱9和最终头11；ledger/progress 的终局头为11。C 的准入前缀仍只到9；原 UNKNOWN receipt/fact 保持 UNKNOWN，只由另一个终局 resolution 投影解释解除。此后缀与准入前缀采用相同事件 hash 规则，但不冒充九种事件的 precommit-prefix Schema 输入。

## 4. 摘要依赖与闭包顺序

避免自引用的构造顺序为：稳定计划→接受/预留/启动事件→带前驱头的 intent→intent 提交事件→许可/派发→带前驱头的原执行 fact→结果事件→下一动作。义务摘要沿原公式使用重封后的精确 intent_ref，不能保留旧头的义务 ID。

未尝试事实的 basis 只引用它**之前**的完整前缀；前缀可以引用早已完成的 A/B fact，不能反指正在承载该 prefix 的当前 C basis/fact。事件 hash 绑定此前 fact Resource 的字节摘要，fact 自身只绑定事件前驱而不包含自己的结果事件 hash。因此形成有向无环依赖，不能删引用来避环。

同步范围包括 intent 序号/前驱/摘要/义务、fact 序号/前驱、每条事件及头、basis CAS头及资源、runtime_claim 中请求头、ledger 的 intent/义务/事件头/历史索引、receipt 的结果和 action_fact_refs、progress 的事实/回执引用、各消费者 input_refs、下游普通四元组和内容摘要。每个消费者仍必须声明所有递归 Resource 普通引用；同书/scope、跨版本和资源环规则不放宽。

语义负例的实际请求扰动继续保留：例如旧 generation、重复事实、错动作、旧 CAS 头、证据不全仍是各自未来门的反例；不会因为前缀修正变成实际可执行。主要结构/引用反例保持原先更早门拒绝，不被改写成新的成功记录。

## 5. 有针对性的静态检查

新检查只读取候选 JSON，重算事件链并对实际内容走读必经阶段：完整接受及预留、动作摘要一致、intent 先于 permit、issued→consumed→DISPATCH_STARTED、APPLIED/UNKNOWN 结果与相同 intent/permit 的对应、UNKNOWN 后中断、subject C 全程未调用。它不签发许可、不读取 SQLite、不模拟一次真实恢复。

三个新邻例的 `candidate_prefix_role=PRE_ADMISSION_INPUT` 指定实际受测前缀；正确 fact/basis 图仅保留作背景，以免删除事件引起的其他序号差异掩盖该缺陷。门的实际结果来自候选 Resource 字节和校验器；案例名称、expected 标签和 complete=true 都不决定是否通过。旧 incomplete-prefix 例保留原结构分类及主要语义触发，另报告其候选前缀实际静态错误。

缺 PLAN_ACCEPTED 或缺 DISPATCH_STARTED 的邻例，删除事件后重排序号并重算链，使可定位拒绝来自缺少必经事件；断链邻例单独破坏 previous_hash/event_hash 关系。正常值不是由 expected_code 生成，校验结果与预期是两份独立数据。缺接受、缺派发、断链均报告完整前缀检查层，不能因 complete=true 获准。

修前固定成功例及其递归资源保存在 `docs/evidence/A03/execution/P1-R2/before/`，旧反例依然能被新静态检查发现。新 69 映射与三邻例的实际命令/结果、字节保全和统一清单见 [R2执行报告](tasks/A03-P1-R2-execution-report.md)。原已确认的两项修订结论不被本轮重记为功能通过。

## 6. 交付与限制

候选仍是 A 内部未实施提案，R2 profile、确切 Git 和新 Schema SHA 明确选定，不混用 P1/R1 候选。旧 69 例及 P1/R1 所有证据/脚本字节保全；只在四个新路径写入，不改 src/tests/公共合同/根依赖/调度状态。

本轮只交 P1 REVIEW；独立复验和主调度批准前不启动 P2，不推送、不集成、不释放 I01。S01 真实完整性、D01/Pillow 根依赖、B 确认、真实平台恢复及真实质量/成本保持未解决。浏览器、网络、平台、凭据/profile、OCR、业务模型 API、数据库/恢复功能执行均为0；实际新观察、事实提交和所有运行时拒绝均 NOT_EXECUTED。
