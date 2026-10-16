# A03：恢复合同扩展准备

日期：2026-10-16。状态：**DRAFT_WAITING_A02**。以下全部是 A 内部候选方案，未实施、未接受、未获 B 共同确认；不是 A03 正式派发或 A02 验收结论。

依据：[项目约定](../../AGENTS.md)、[调度](../coordination.md)、[A03 准备](A03-preparation.md)、[合同设计](../contracts-v1.md)、[公共入口](../../src/annotation/contracts/__init__.py)、[类型](../../src/annotation/contracts/models.py)与[校验器](../../src/annotation/contracts/validation.py)。A02 报告只读自冻结提交 `5c9285720c8628c5198bedeadfc9f6bc7826a914` 的 `docs/tasks/A02-execution-report.md`，实现提交为 `3fe492ce10bf93711ce57d305bc716f8b29345b7`；正式验收仍在进行。

## 1. 当前缺口和最小边界

C01 `1.0.0-a-proposal / c01-exchange-1` 只有完整 ExecutionReceipt，没有 intent、部分执行事实或 ReconciliationResult；`assert_plan_ready` 遇任何同书 UNKNOWN 拒绝，BatchReport 根据原回执要求保持未知。现有 ArtifactRef 限同书同 scope，不能靠换包、删历史、改数据库布尔值或混入跨 scope 引用解锁。

A02 作者报告存在“首动作失败后，后续未派发动作以完整 ABSENT 读回生成 NOT_APPLIED”的路径。提案区分执行事实和效果结论；不凭本草案判定该尚未验收实现对错。A03 首轮仅模拟恢复，保留旧 UNKNOWN 字节；不纳入真实平台写入、算法、复杂工作台或新的开发阶段。

S01 来源完整性门禁见同批准备的[独立候选提案](S01-eligibility-preparation.md)；两份文档摘要及归档提交记录于[调度状态](../coordination-state.json)。本文件不复制其规则，恢复成功不能替代来源资格；统一版本边界仍待正式冻结。

## 2. 候选对象、身份和责任

拟在新版本合同中增加三个同 scope 产物；名称和字段仍须合同负责人确认。沿用信封、精确 ArtifactRef、政策引用、资源相对路径/摘要和 SYNTHETIC/OBSERVED 分界，不在原 schema 下偷偷接受新字段。

| 对象 | 最小字段提案 | 谁生产 / 谁验证 |
|---|---|---|
| WriteIntent | `plan_ref, action_id, action_digest, target_key, question_id, source_entity_ids, before_snapshot_ref, execution_mode, journal_id, journal_sequence, writer_epoch` | runtime 在效果调用前持久化；contracts 验精确身份/引用，runtime 验已提交事务及当前占有权 |
| ExecutionProgress | `plan_ref, journal_id, journal_head_sequence, journal_head_hash, actions[]`；每项 `action_id, intent_ref?, attempt_fact, attempt_evidence_refs, receipt_ref?, resolution_head_ref?` | runtime 从追加日志投影；contracts 验每个计划动作恰好一项及引用闭合；独立复核核对进程/目标证据 |
| ReconciliationResult | `plan_ref, intent_ref, action_id, original_receipt_ref?, previous_resolution_ref?, observed_snapshot_ref, observation, resolution, platform_ids, evidence_refs, readback?, comparator_version, reason_code, replay_allowed=false` | delivery.reconciler 比较独立读回；contracts 验状态/证据/链，runtime 决定是否仍有书级未决项 |

`target_key={platform_namespace,target_id,book_id}`；不含 run/scope、题号或会话 PID。intent 唯一键为该书键＋精确计划引用＋action_id；action_digest 覆盖规范化完整动作，同键不同摘要拒绝，同一动作不能另造 intent 绕过去重。内部题/片段与外部平台 ID 分别绑定，不能用 bbox/印刷题号代替身份。

intent 中 `before_snapshot_ref` 必须等于计划当前有效前置事实依据；不能拿另一个新快照为旧动作补资格。前序动作合法变化沿用已接受 A02 规则，不在 runtime 再实现一套比较逻辑。journal 序号/摘要提供定位，不单独证明效果发生或历史完整。

原 receipt 存在时，resolution 必须指向其中同一 plan/action 的 UNKNOWN；无 receipt 时指向已持久化且无有效终局的 intent。两者同时存在须一致。旧材料缺 intent 不得补造“历史已写入”的 intent；其迁移资格见第 6 节。

## 3. 执行事实与多动作中断

`attempt_fact` 候选为 `NOT_ATTEMPTED / MAY_HAVE_BEEN_ATTEMPTED / ATTEMPTED / LEGACY_UNRECORDED`。它记录调用事实，不替代 APPLIED/NOT_APPLIED/UNKNOWN 效果分类；NOT_ATTEMPTED 不能从“没找到日志”直接推出，必须有受控 journal 和占有权边界证明。

1. 效果前事务提交 intent，再提交“可能跨入调用”的持久边界；intent 或 DISPATCH_STARTED 本身都不证明调用已发出或未发出。两者之间及边界后崩溃均先按未知恢复、独立核对，不能保证本地事务与外部效果原子化。
2. 多动作计划完整列出所有 action；未尝试、依赖未满足、调用后未知分别保留。ExecutionProgress 可以在没有完整回执时导出，不伪装成 ExecutionReceipt 或 BatchReport。
3. 若未尝试动作有完整独立 ABSENT 证据，候选新合同可允许 NOT_APPLIED，但必须保留 `attempt_fact=NOT_ATTEMPTED` 及其证据；是否采用该兼容方式待正式评审。没有充分读回时不得为凑齐完整回执编造任何效果结论。
4. 部分计划先用 progress/异常查询表达，当前 BatchReport 仍要求完整回执；本草案不把 receipt 改为可选。完整回执形成后可生成新 BatchReport，旧 progress、intent 和原始回执继续保留。
5. 重启先注册未决集合，再允许受控入口取得新写入资格。回执、证据落盘或事务失败时仍阻断；锁释放、超时或新进程启动本身不改变效果结论。

## 4. Resolution 链与继续行为

每条 resolution 是新不可变产物，保持原 plan/action/intent 和书 scope 不变；链首 previous=null，后续精确引用前项。不得覆盖旧 UNKNOWN；不按最大时间戳或 revision 任选分支。重复同一证明只幂等登记，不触发效果。

| observation | resolution | 必要证据与行为 |
|---|---|---|
| MATCH | RESOLVED_APPLIED | 原动作相关效果完整、身份唯一且平台 ID/读回匹配；进入后置检查，旧动作不重发 |
| ABSENT | RESOLVED_NOT_APPLIED | 相关范围完整、确证无效果；重新取当前目标并 targetcheck/规划，旧动作仍不可自动重发 |
| CONFLICT | STILL_UNKNOWN | 部分生效、重复或身份/内容矛盾；保留冲突证据、暂停并报告异常，不自动修删目标 |
| INDETERMINATE | STILL_UNKNOWN | 无法读回、范围不全或归属不足；有限只读重查，到限保持暂停 |

MATCH/ABSENT 必须有非空证据及 readback，MATCH 还需实际平台 ID；空列表或返回成功不证明 ABSENT。读回与原相关事实、平台版本、观测范围及比较器版本绑定；消费者校验资源字节，无法验证完整性不得解锁。

同一前项出现矛盾后继、错 action、错 intent/receipt、缺摘要、证据失效或跨书/scope 都拒绝资格。STILL_UNKNOWN 后可用新观察继续一条链；已解决后出现冲突不能重写原历史结论，新增目标变化/未决事件并再次暂停。

一次解决只覆盖精确原未决项；同书其他 action 或新 UNKNOWN 不被旧 resolution 消除。解决后的新动作还需当前快照、政策、能力、授权和两阶段 PASS；模型质量/最终文字/公式不能由框读回推定。

## 5. 跨 scope 账本与资格门

同 scope 的 WriteIntent/Progress/Resolution 继续使用 C01 风格引用闭包。书级账本是独立 runtime 导出格式候选 `BookRecoverySnapshot`，不是伪造 scope 的普通 Artifact；不放宽现有通用 ArtifactRef 的跨 scope 规则。

账本最小字段：`format_version, ledger_id, target_key, generation, head_sequence, head_hash, observed_at, scopes[], obligations[]`。`scopes[]` 含 scope_id、相对交换包路径及文件 SHA256；`obligations[]` 含 scope_id、精确 plan/action/intent/receipt 定位、resolution 链头及有效状态。scope 包各自校验，跨包定位显式声明命名空间，不直接混入普通 `input_refs`。

外部摘要可证明提供的文件一致，不能证明未漏掉 scope/日志。runtime 必须从唯一受控持久库完整扫描该书的所有 run/scope；对照注册表、连续事件和未决集合，在事务/CAS 中核对当前 generation 与 owner 后才作资格决定。手工构造空清单、换库、旧账本或只提供当前 scope 均不获得资格；代次隔离只限受控 mock/同机入口，不能宣称阻止任意真实平台外部写者。

候选调用分两层：公共纯函数只验证同 scope 引用、恢复链及当前计划；runtime 资格入口另读当前账本和占有权。拟扩展 `assert_plan_ready(..., recovery_context=...)`，其中只放同 scope 的 progress/解决链，不接受调用方账本 JSON 授予整书许可；effect 前仍在同书占有权下核对当前 generation/owner。必需上下文缺失默认拒绝，不回退为无历史模式。

新门禁只将合法解决链覆盖的 UNKNOWN 从“当前未决集合”排除，不从输入/账本删原记录。账本尚有 intent 无结论、任何 scope 的 UNKNOWN/CONFLICT、未验证链或失效占有权时继续 BOOK_WRITE_PAUSED；另一本书不因无关事项全局暂停。

拟给新 BatchReport 增加同 scope `execution_progress_ref`，其链头精确指定所采用的 resolution；POST_APPLY CheckReport 同样绑定该恢复依据，不能复用原 UNKNOWN 上的旧后置报告。报告由确定性有效结果投影计算，不能手写状态绕过原 receipt；原 receipt 字节及引用保留。

新报告的 UNKNOWN 约束按“尚未解决”计算；NOT_APPLIED/未尝试题不能成为 VERIFIED，resolved APPLIED 也须后置检查才可前进。书级其他 scope 仍未决时当前 scope 的框事实可展示，但运行状态保持书暂停。分母、PENDING 内容、NOT_SUBMITTED 及 COMPLETED 的现有独立条件不得放宽。

## 6. 版本、迁移与拒绝规则

- 新 schema/exchange/recovery-format 名称由合同负责人显式冻结；不沿用 `1.0.0-a-proposal` 悄悄改变资格含义。旧解析器拒绝新类型/字段，新解析器按版本选择完整规则，不猜测最新版。
- C01/A02 旧合成样例继续按原版本读取和复现，不自动获得持久化、恢复或平台资格；缺 intent/账本事实保持 LEGACY_UNRECORDED。不能仅填默认值、重封签或重新命名运行就产生“已解决”结论。
- 新 resolution 若引用原版本 receipt/plan，跨版本解析与引用验证必须有显式规则；不能改旧 schema_version 或重封签后宣称原 UNKNOWN 字节保留，也不能默认旧产物取得新资格。具体兼容入口仍待冻结。
- 迁移工具如获批准，应保留旧文件摘要/版本和显式迁移映射，生成新文件；纯结构迁移不补历史执行证据。首轮恢复演示优先在新合同下重新做明确模拟运行，产生真实本地 intent，再注入故障；不是重放旧平台动作。
- 先完成 A02 原基线正式验收，再固定其 API、指定唯一合同写入者；合同扩展及消费适配单独提交并回归 C01/A02，最后固定 A03 基线。不得在 A02 验收期间替换被验合同，亦不借扩展宣布 B 已采用。
- 旧 UNKNOWN 的完整解除、跨 scope 账本和新报告若未实现/未复验，A03 只可声称已完成相应离线子范围，不得记录整项恢复 ACCEPTED；不扩大当前路线或平台授权。

## 7. 最小验收矩阵提案

| 用例 | 应观察到的结果 |
|---|---|
| 原 UNKNOWN＋完整 MATCH 链 | 历史字节不变；解析、资源和身份校验通过；只移除该项当前未决；旧动作效果次数不增加 |
| intent 无 receipt，效果前/后两个崩溃窗口 | 分别读回 ABSENT/MATCH；不捏造旧 receipt；先核对后生成后续产物 |
| APPLIED / UNKNOWN / NOT_ATTEMPTED 三动作 | progress 保留三种调用事实；无充分证据不拼完整 receipt；充分 ABSENT 路径依冻结规则验证 |
| 完整 ABSENT 后继续 | 旧 action 不重发；新快照、检查、计划缺一均拒绝；不能只换 ID 克隆旧动作 |
| 部分生效、重复 ID、矛盾/截断读回 | CONFLICT/INDETERMINATE → STILL_UNKNOWN；保持暂停，不变成 NOT_APPLIED |
| scope A 已解决、scope B 尚未决 | 纯局部链可有效，书级入口仍拒绝；换 run/scope/action 无法绕过 |
| 同书两未决只解决一项；新 UNKNOWN 晚于旧 resolution | 均不整书解锁；另一书可独立模拟 |
| 错书/目标/计划/动作/摘要；缺 intent；链分叉/循环 | 可定位拒绝；无有效资格；不靠排序选择“看起来最新”的结果 |
| 旧 generation、漏 scope、换空库、并发追加未决事件 | runtime 当前账本/CAS 拒绝，效果调用次数为 0 |
| resolution 已解决但当前目标又变化 | 旧事实保留；旧计划失效，新冲突再次暂停，不覆写历史 |
| 原 UNKNOWN 报告直接改 VERIFIED 或省略恢复依据 | 校验失败；即使 MATCH 也不能跳过新 POST_APPLY / 内容检查 |
| 旧样例加字段、默认迁移、SYNTHETIC 改 OBSERVED | 旧版本拒绝扩展；新版本拒绝证据升级与虚构历史，旧样例不新增资格 |

本次只写本草案并检查本地链接/文档差异；没有实施上述对象、运行测试或取得验收结果。派发前未决：A02 接受版本与可用接口、NOT_ATTEMPTED＋ABSENT 映射、合同版本与三对象字段、跨包账本格式/受控库身份、恢复上下文与后置报告绑定、跨版本引用和迁移允许范围、有限重读上限，以及 S01 与恢复扩展的统一版本边界。
