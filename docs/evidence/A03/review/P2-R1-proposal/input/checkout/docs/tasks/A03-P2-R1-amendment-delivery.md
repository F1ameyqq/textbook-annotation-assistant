# A03 P2-R1 合同补充提案交付：等待独立审阅

日期：2026-10-17（Asia/Shanghai）。状态：**PROPOSAL / UNIMPLEMENTED，合同及功能变更均未批准**。本轮按 `xhigh` 处理，未派发子智能体。I01 不释放。本报告所在提案提交的确切 SHA 在最终交付消息中给出；不存在本报告自行宣告验收通过的含义。

工作树 `C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800`，分支 `codex/a03-runtime-recovery`；基线 `c30526958e313141bf64152627591b0907b04aa8`。只读工作流输入来自 `e1b1475597f80d46c5ace5c004f5091d139ac6cc`。本轮只新增本报告、`docs/evidence/A03/execution/P2-R1-proposal/`、`examples/a03/P2-R1-proposal/`。未修改主树、产品、公共合同原件、根依赖、调度 state 或旧证据；未运行产品/旧场景，未查询 DB，未访问网络、浏览器、平台、profile 或模型，未安装包、推送或联系 B/验收者。

独立 P2 结论仍为 REWORK。提案回答五项返修问题；静态检查不能关闭相应运行验收。已有自动审查拒绝的字段重置专项保持 **NOT_EXECUTED**，不复跑、不变形、不另派，也不列入下一轮测试请求。

## 1. 输入、候选版本与审阅入口

输入原字节及 SHA 见 [input-index](../evidence/A03/execution/P2-R1-proposal/input-index.json)，内含独立复核的 330 项清单、报告、静态定位及 final-verification 原件。冻结输入的相对链接仍表示原工作流提交中的位置，不表示本工作树存在这些独立执行现场；新报告链接使用本工作树内真实文件。

**当前候选只选 `candidate-v2/`**。根样例目录中的早期 `schemas/`、`cases/`、`profile.json`、`event-catalog.json` 是未批准草稿，已原样保留；[draft-retention](../evidence/A03/execution/P2-R1-proposal/draft-retention.json) 和归档记录其原字节，不能混选草稿 pins。

| 项目 | 本次独立新版本 | 原件处理 |
| --- | --- | --- |
| profile | `a03-p2-r1-amendment-1-PROPOSAL` | 必须同时匹配完整 schema pins 与 API supplement SHA；不按 latest/版本字符串猜测 |
| exchange | `a03-exchange-2-proposal` | 新 [exchange-v2.schema](../../examples/a03/P2-R1-proposal/candidate-v2/schemas/exchange-v2.schema.json) 明确容纳旧不可变输入节点与新 1.2 节点 |
| 新 Artifact | `1.2.0-a03-amendment-proposal` | Source 等继承原字段形状；Receipt、PRE/POST、Batch 增加本报告规定的消费语义 |
| 前缀 / 新事件 / 消费帧 | `a03-runtime-event-prefix-1` / `a03-runtime-event-2` / `a03-journal-consumer-frame-1` | 旧 runtime 事件使用 `FROZEN_EVENT_1` 原 body/hash，不补字段、不重算旧链 |
| 事实 / 未尝试依据 | `a03-action-fact-2` / `a03-unattempted-basis-2` | 新文件；旧七 Schema/API/profile 不改字节 |
| PRE run / 转换记录 | `a03-synthetic-precheck-run-1` / `a03-explicit-conversion-state-2` | JSON 值均不授予 native authority |

[候选 profile](../../examples/a03/P2-R1-proposal/candidate-v2/profile.json)、[API supplement](../../examples/a03/P2-R1-proposal/candidate-v2/api-supplement-proposal.json)、[严格事件目录](../../examples/a03/P2-R1-proposal/candidate-v2/event-catalog.json) 是审阅的规范性候选输入。新 Schema 是完整结构提案；语义、native 类型及生产/接纳仍待批准与实现。冻结 R2 七份 Schema 和 API 的副本也纳入 pins，静态检查与产品原件逐字节比较。

未知 profile、缺/多 pin、未知事件或额外 payload 字段必须拒绝。不能靠 reseal、复制 producer 字符串、`complete:true` 或签名把旧执行节点变成新执行资格。1.1 节点作为只读输入仍按自身版本检查；既有已接纳计划的原 refs/永久预留保持原身份，不能升级后重放旧尾部。

## 2. 全书事件前缀、原生完整性与只读未尝试事实

### 2.1 全局序号和逐事件闭合

新 [runtime-event-prefix Schema](../../examples/a03/P2-R1-proposal/candidate-v2/schemas/runtime-event-prefix-v1.schema.json) 的真实起点固定为全书 genesis：`from_sequence=1`、`predecessor={sequence:0,hash:64个0}`。`accepted_anchor` 单独指向 subject 的真实 `PLAN_ACCEPTED`，`accepted_predecessor` 保留它的真实前驱。`expected_book_head` 指全书链末尾；不能改成 subject 投影的末尾。

两个完整静态前缀包分别见 [首个计划](../../examples/a03/P2-R1-proposal/candidate-v2/cases/first-unattempted-prefix/package.json) 和 [前有其他计划](../../examples/a03/P2-R1-proposal/candidate-v2/cases/later-plan-prefix/package.json)。前者 subject accepted 是 3，后者是 8；后者保留先前计划及 owner/control 事件。两者都保留全部动作的 `PLAN_ACTIONS_RESERVED`，subject 没有 intent、permit、dispatch 或 action fact。事件 hash 为去掉 `event_hash` 后的规范 JSON 摘要，序号和 previous_hash 连续；旧事件不增加 `event_version`。

事件公共 envelope：sequence、event、journal_id、target_key、plan_ref（可 null）、owner_id（可 null）、generation、recorded_at、payload、previous_hash、event_hash；新事件另有固定 event_version。带 plan 的 envelope/payload 必须绑定同 exact plan，ACCEPTED/RESERVED 的 action IDs/digests 必须逐项等于该不可变 plan。新事件目录 24 类及旧实际 body 的 15 类均为封闭 payload：

| 类别 | 事件及新增语义 |
| --- | --- |
| owner | RESERVED / ACTIVE 带 process instance、PID、generation、lease、target session、fence Resource；RELEASED 带离开者身份。旧 owner payload 原来是 `{}`，必须原样保留 |
| profile / 状态 | `RUNTIME_PROFILE_ADOPTED` 绑定旧 head、已知 DB 版本及 native index 快照；`PLAN_STATE_AT_ADOPTION` 只证明接纳时现状，不伪造旧 INTERRUPTED 发生时间；新 `PLAN_INTERRUPTED` 明记原因 |
| 计划 | ACCEPTED 绑定 plan/source/scope 和所有 action 摘要；ACTIONS_RESERVED 永久绑定 action IDs/digests；STARTED 绑定 RUNNING |
| 写入 | WRITE_INTENT_COMMITTED、PERMIT_ISSUED/CONSUMED、DISPATCH_STARTED、ACTION_RESULT_COMMITTED、RECONCILIATION_COMMITTED。新 permit 明带 action_digest/obligation；旧 permit 实际只有 plan/action/intent/permit，不能补写 |
| archive / hold | HISTORY_ARCHIVE_IMPORTED、TARGET_DRIFT_HOLD、HOLD_CLEARED 均封闭绑定实际资源/refs。旧 archive_sha256 是 parsed-value digest，新 archive_raw_sha256 明指原字节，不能混称 |
| 专用只读 | READONLY_ABSENCE_STARTED、READ_STARTED、READ_FINISHED、READ_FAILED、ABORTED、UNATTEMPTED_ABSENCE_COMMITTED。call/session/action 绑定封闭、次数持久化，不能混入写 intent/permit |

普通 ArtifactRef 继续同 book/scope、精确四元组、逐消费者 `input_refs`、递归 Resource bytes/hash/refs、DAG 无环规则。**全书账本可能含别的 scope，因此引入一个需明确批准的新消费者边界**：每个 journal frame 是显式嵌套消费者，frame 的 `consumer_scope_id` 必须由其 exact indexed plan/资源推导并核对，不能由调用者任写。其 event 内嵌 Resource 的每个普通 ref 都在该 frame 的 scope 中闭合、声明且属于同一 canonical book；非 frame 区域仍按外层 scope 处理。不得用“整个前缀可信”豁免递归检查。

当前正样例覆盖同 scope 的其他计划；跨 scope 正包尚未提供，本轮只包含假 frame scope 的拒绝负例。若调度不批准这个嵌套消费者边界，跨 scope 全书前缀仍有合同缺口，不能偷偷放宽普通 ref 规则。这是明确未闭合项。

### 2.2 离线 hash 链和真实全书完整性分开

结构完整不证明调用者没有自造/删行后重封一条链。未来入口必须在 canonical book gate 下，从**已知 DB** 当前所有 events、plans、actions、intents、permits、pending、holds、registrations 及 target identity 获取原生视图，将完整排序事件与候选 serialized bytes 逐项比较，核对索引和当前 head，再绑定 private `CompleteBookPrefixAttestation`。caller JSON、native_index_snapshot Resource 和 expected head 都不能代替该检查。跨 scope/其他计划的 pending 必须参与全书暂停判断。

提议仅对已知 `a03-runtime-db-1` 追加显式 profile-adoption 事件，不改旧行/旧 hash，不自动升级未知 DB。接纳应由新 generation 的唯一 writer 在旧 writer 已退出、目标 fence 已匹配后进行；旧 writer 不得在新 profile 接纳后继续追加旧语义事件。是否可在不变 SQL schema 下仅凭追加事件持久化 profile/session/index，仍须下一轮对真实存储结构做实现审阅与故障验证；本轮未打开 DB。

### 2.3 专用 ReadOnlyPrepared 路由

1. 校验 subject 已接纳、计划 INTERRUPTED、永久动作预留存在、当前 owner/generation/store/session/source/scope 正确；全书扫描证明该 action 从未有 intent/obligation/permit/dispatch/result，不是仅查一个表。UNKNOWN 前序若可能影响该 action 的相关事实而无法排除，返回 `PREDECESSOR_EFFECT_UNPROVEN`，不造 ABSENT。
2. 在 gate 下 CAS entry head，追加 book 级 `READONLY_ABSENCE_STARTED` 并登记 call/session。active session 阻止本书目标写入；其他书继续独立运行。它没有 `issue_dispatch`/`consume_dispatch` 能力。不能借用 attempts.intent 字段造假 intent。
3. 每次真实读前持久化 READ_STARTED，成功后 READ_FINISHED，失败后 READ_FAILED；即使崩溃也不能免费重试。前两次独立新 read 具有不同 observation ID、递增 native read_sequence/time，第一读产生 private `ReadOnlyPrepared`，第二读执行 A02 相关事实比较，必须 complete ABSENT。
4. 提议第三次真实目标读取作为最终 currentness assertion，**计入总共 3 次 target read**；不称作免费校验。`observer_calls=2` 专指两次证据读，`total_read_calls=3` 明示总数。每读≤2s、入口≤8s、父调用≤60s、retries=0；预算/父 call_id 持久化，换 call_id 不能自动刷新失败调用。该解释涉及既有预算边界，必须由调度明确批准。
5. 最终短 gate 下检查 owner/fence、本书所有 pending、native prefix 等值及 final read currentness；initial head 到 commit_expected_head 之间只能有本 session 记账事件，其他变化拒绝。basis 的 expected_event_head 是读结束后的真实 H；fact 的 journal_sequence=H+1、predecessor_hash=H.hash。先落盘 immutable resources/fact，再事务 CAS 更新唯一 action index、追加 COMMITTED；失败留 orphan 可诊断资源，不留半个已提交事实。
6. 全程无 dispatch 或目标 effect；本书其他 UNKNOWN/hold 不被清除，旧计划不恢复 RUNNING/旧尾部不重放。失败/死 owner 使用明确 ABORTED 收口；继任者核对遗留 session/attempt 消耗后才可开始另一次明确调用。

提议用逻辑 read session 阻止写入，不在两次长读之间占着 OS gate；lease keeper 可按原节奏续租，最终再取短 gate + native currentness/CAS。需要后续验证续租、其他 writer、目标状态变更之间的真实竞态；当前纯 JSON basis 不证明任何 gate 已持有，故移除了新版本的 caller `gate_held:true`。

## 3. 晚到完整 receipt、独立 action snapshot 与 R17

两个完整**值/引用层**包及逐消费者关系：

| 包 | 组合 | 引用明细 |
| --- | --- | --- |
| [late-receipt](../../examples/a03/P2-R1-proposal/candidate-v2/cases/late-receipt/package.json) | 原 R2 head 的 original_receipt_ref=null；新建完整三 action receipt，引用 exact intent/head/facts | [consumer-closure](../../examples/a03/P2-R1-proposal/candidate-v2/cases/late-receipt/consumer-closure.json) |
| [different-snapshots](../../examples/a03/P2-R1-proposal/candidate-v2/cases/different-snapshots/package.json) | action A 的 MATCH 头与 action B 的 ABSENT 头各保留独立 snapshot；另有报告级 snapshot | [consumer-closure](../../examples/a03/P2-R1-proposal/candidate-v2/cases/different-snapshots/consumer-closure.json) |

每个包包括所有 Source/Evidence/Graph/Plan/Intent/Snapshot/Head/Receipt/POST/Batch Artifact、它们引用的原始图片与 JSON Resource、完整 action facts 及无 intent action 的专用依据；无悬空 refs。旧 null head 在包中的 `head-before.json` / `head-after.json` 字节完全相同，旧输入完整另存 `imported-r2-case.json`。新对象是本轮编写的全合成设计值，不是旧现场恢复件。

新 receipt 的完整 results/action_fact_refs 必须与 exact plan 的每个 action 同序一一对应。新 POST 新增 `action_bindings`：action_id、action_digest、intent_ref、fact_ref、resolution_head_ref、head_original_receipt_ref、observed_snapshot_ref、effective_outcome；每个字段都与 exact head/fact/intent/plan 相等。RECOVERY fact 原 prepared_before 仍来自 exact intent，obligation 仍按 journal/target/sequence/head/intent 五项计算。

**原 receipt 和当前聚合 receipt 分开**：head.original_receipt_ref 为空时，旧 head 继续为空；后来完整 receipt 通过 exact 同 intent/action 的 recovery fact 消费该 head，不能把 null 填成后来 receipt。若 original 非空，仍须解析该原 receipt 并核对原 UNKNOWN、intent、plan/action；后来 receipt 与其并不因同 action 自动相同。每个 action 保留自己的 observed_snapshot_ref，不强制它们相等。

POST 的 `report_snapshot_ref` 是另一次真实报告级完整读取，必须有其 native observation；不能合并旧 head 视图拼成一次不存在的观察。frame_structure=PASS 需要在该真实完整读取上核对所有选定事实和框结构。已解析头是历史事实，若报告时目标又变，报 HOLD/EXCEPTION 并走 drift hold，不能给 terminal 头再追加 successor 来追新状态。样例没有运行读取/框检查，因此 POST 为 HOLD、frame_structure=UNAVAILABLE、content=PENDING；Batch 引用同 receipt/post/report snapshot/head 列表，覆盖全部 scope_manifest，包括异常/跳过，NOT_SUBMITTED，不冒报 COMPLETED/0/0。

历史报告只能消费其当时已声明的合法 head 链前缀；“当前报告/可写门禁”另须以全书当前唯一 head/index 为准。重复分叉、断链、跨 intent、过期 head 用作 current、遗漏其他 pending，都必须拒绝。

**可达性与已知未闭合项：**

- 原 R2 head 是静态设计输入，不是原生 P2 全局账本。包中未尝试依据是各自独立的 fact 序列化见证；它们与导入头不组成一个获得原生接纳的全书历史。样例根明确 `global_fact_journal_consistency=NOT_ASSERTED_ISOLATED_FACT_WITNESSES`；任何 runtime 注册必须拒绝。静态检查没有把这些包称为合法运行历史。
- 当前执行器在首个 UNKNOWN 后中断，同一计划不能自然产生两个不同 action 的 UNKNOWN 恢复头。第二个包只证明新版本能完整表达这类引用，不能作为当前运行时正向验收。不得为凑样例而恢复旧尾部、跳过规则或隐式引入跨计划/跨 scope 聚合。若业务验收要求真实多头链，调度须先明确是否仍要求同计划、或另批跨计划报告投影及其精确 source/scope 规则；本提案没有扩展此范围。
- 新版本修正的是两条不可满足的等式，不意味着 R17 已满足。旧 R17 的 null-vs-ref、S1-vs-S2 是本轮静态逻辑见证，未调用旧 validator/quality 运行整个组合。R17 仍待新的有界实现范围及原生样例独立验证；不能自行缩窄验收。

## 4. 全合成 PRE 的合法来源与 hold

提议新增 A 侧的**注册合成 fixture verifier**，只核对已批准的 exact fixture oracle，不能承担 B 的 OCR、题意理解、真实答案匹配或真实书籍完整性保证。

[PRE/hold 设计包](../../examples/a03/P2-R1-proposal/candidate-v2/cases/pre-and-conversion-design/package.json) 包含明确页/题/答案关系 oracle、输入原图片摘要、run Resource、新 PRE 1.2 envelope、生产/接纳接口及正向/二次变化步骤。oracle 是待独立审查的全合成作者声明，不从真实书推断；本轮没有批准 registry，也没有执行 verifier。因此五项检查均 UNAVAILABLE，新 PRE=HOLD，接纳预期为拒绝。旧 PRE 的 PASS stub 保留只读身份，不能复制 ID/time/producer 后使用。

未来 `produce_synthetic_precheck` 必须重新读取并 hash exact source/graph/policy/oracle：source_integrity 核对原图片/尺寸/页清单；structure 核对 exact fixture IDs/关系/区域；answer_matching 比较 oracle 中独立写明的答案关联；coverage 保留每页/每题/区域及异常分母；policy 核对 exact policy 和映射。每项产生新比较摘要与原件证据，不靠一个 PASS 字符串。run 绑定 hold id/head、真实新 snapshot/observation、起止时间、implementation digest、全部 input hashes 和五项结果。

新 PRE 的 `synthetic_run_ref` 是该 run Resource；`admit_synthetic_precheck` 还须验证当前批准 registry、private run handle 的真实身份和不可复用状态、实现/输入 bytes、实际运行记录及结果。JSON、producer 字符串或签名只作可审计值，不成为 native handle。缺 oracle/任一检查 unavailable 或输入改变，保持 HOLD/EXCEPTION。

未来正向清 hold：hold 之后的新 actual snapshot → 新五项检查/接纳 PRE → 新 TARGET → 新候选 plan → 最终 canonical gate/current owner/full pending scan → 独立最终再读、target fence 和 ledger CAS → 追加 HOLD_CLEARED。所有输入必须绑定同 book/scope/session/source；old PRE 改名、重封、旧 snapshot 或未接纳 PRE 均拒绝。本书仍有未解决 UNKNOWN 时不得借 clear 解除写暂停；当前是否允许多 registration/scope 的 hold 流程不是本提案自动支持项。

第二次变化用未来隔离 fixture，在候选计划之后、最终再读之前引入真实目标变化，必须 `TARGET_CHANGED`、hold 保留、无 permit/effect/terminal successor。正向解除及此负例均 **NOT_RUN**。当前代码中存在相关 guards 不能替代这些证据。

## 5. 显式转换、失败、中断和重开

未知 DB 继续 fail-closed；不要求、也不提议自动迁移任意未知版本。提议转换范围只含 exact 原字节 SHA、已知版本、全合成**初始** fixture：独立完整页/题枚举、原 assets/refs/DAG、无执行历史。来源含真实 provenance、receipt/Batch、intent/recovery/action fact/UNKNOWN 或缺少枚举时拒绝；legacy no-intent UNKNOWN 永远 LEGACY_UNRECORDED。

新 namespace 下重新计算所有普通 refs、嵌套 Resource、受影响 Artifact hash 和完整映射；source scope/target fixture identity 明确新建。旧 PRE stub/计划只能归档，不能因此授予新执行资格；新执行仍需合法 fresh PRE/TARGET/plan 和 runtime 注册。原件保留原路径记录、raw SHA、字节数及只读归档，不能覆盖旧原件。

转换记录是追加链：CREATED → COPYING → VALIDATING → COMMITTED，失败则追加 FAILED/INCOMPLETE。每条 previous_record_sha256 指上一条原 bytes；不覆写前一条状态。完整 artifact ID/revision/hash 映射及 Resource old/new path/raw SHA 不能缺项。完成协议：先落盘并 fsync originals、全部新资源、映射和合法新 initial bundle；最后 atomic rename 完成 manifest，核对其内容后追加 COMMITTED。崩溃在 completion manifest 之后、COMMITTED 之前，只能只读验证并追加诊断/完成判定，不重做目标写入或覆盖旧记录；具体跨平台 fsync/rename 语义须后续验证。

现有目录重开一律诊断只读。INCOMPLETE/FAILED 或 null mapping/hash 不能成为可执行输入；要重新转换须显式新 conversion_id/新目录，不能沿用半成品身份。已提交的已知包只能按 exact 完成 manifest 读取，不能重跑转换来解锁。

[转换策略和记录](../../examples/a03/P2-R1-proposal/candidate-v2/cases/pre-and-conversion-design/conversion-policy.json) 给出完整的 CREATE/COPY/VALIDATE/INCOMPLETE 记录链及 FAILED 分支。原文件是本轮新建的静态初始设计输入，**不是历史丢失原件**；mapping-plan 的 new hashes 为 null，明确 `UNIMPLEMENTED`，无 target bundle、无 COMMITTED。这里没有伪造成功转换样例。完整提交、故障中断/重开测试均 NOT_RUN，完成映射/新包的字节证据仍须下一轮补齐。

## 6. 历史失败原件和下一轮留证

独立报告指出：first-quality-failure 的 TemporaryDirectory 动态原件由原质量 index 明确标记 NOT_RETAINED；hold 汇总两次原始总体 stdout/stderr 缺失。这些状态保持 **NOT_RETAINED**，原声明在冻结输入中可查。当前清单完整只能保护现存原件，不能补回丢失文件；本轮没有重建、没有重跑旧场景，也没有把新静态成功算作旧失败已恢复。是否接受此历史限制须由调度另作判断。

下一轮被批准的新运行应在启动任何 child/断言前建立持久 evidence root 和预登记 case：exact input/pins/source commit/命令/cwd/env allowlist/PID/进程树及预算；stdout/stderr 从进程启动起直接写不可覆盖文件，保留子进程和原生存储/目标前后快照、事件、资源、receipts、readback、durable exits。失败/timeout/kill/断言也应在 finally 留退出状态及 retention inventory，禁止用临时目录自动清理。Windows Job Object 或等价有界进程容器需要未来实际验证；本轮 runner 仅用于快速静态脚本，不能冒称该运行 harness 已实现。

失败目录不覆盖，修正和新成功使用新 run id；原失败清单、原 exit/status、missing 原因保留。manifest 必须包括全部失败与成功 raw 文件（即便日志被 Git ignore），最后由独立读取者校验原字节/refs/业务结果。UNKNOWN 保存先核实际状态，不能自动重发。

## 7. 受影响消费者和拟变更源码路径（本轮均未修改）

| 精确路径 | 待批准后的最小职责 |
| --- | --- |
| `src/annotation/contracts/recovery_schema.py` | 明确选择新 profile 与 pins，保留旧版本，不覆盖旧七 Schema |
| `src/annotation/contracts/schemas/runtime-event-prefix-v1.schema.json`、`exchange-v2.schema.json`、`action-fact-v2.schema.json`、`unattempted-basis-v2.schema.json`、`report-payloads-v2.schema.json`、`receipt-payload-v2.schema.json`、`synthetic-precheck-run-v1.schema.json`、`conversion-state-v2.schema.json`（拟新增） | 新结构版本与严格字段；不把本提案文件直接拷进生产当作批准 |
| `src/annotation/contracts/recovery.py` | 新版本逐消费者闭合/帧边界、fact/basis/current-head/report关联、显式转换；保留旧版本等式与 archive-only 语义 |
| `src/annotation/runtime/storage/__init__.py` | 已知 DB 显式 profile 接纳、全书前缀原生比较、永久预留、专用 read session/index/fact/CAS；替换无条件 GAP 需单独批准 |
| `src/annotation/runtime/storage/common.py` | 私有 native ReadOnlySession/ReadOnlyPrepared/完整前缀证明/预算及拒绝语义 |
| `src/annotation/runtime/storage/holds.py` | 新 PRE/run 的接纳校验、全书 pending/final native reread/currentness/CAS；保留旧 terminal 头 |
| `src/annotation/runtime/recovery/observation.py`、`lease.py`、`__init__.py`、`cli.py` | 两新读+最终读的统一预算、续租、隔离只读入口/输出；CLI 不能自行构造权威 handle |
| `src/annotation/runtime/recovery/quality.py` | 新 exact per-action binding + 真正报告级读取 + 完整 POST/Batch；不可达组合继续诚实诊断 |
| `src/annotation/quality/synthetic_precheck.py`（拟新增） | 仅固定已注册合成 fixture 的五项实际检查，只产检查结果，不编排/实现 B |
| `tests/test_a03_runtime_authority.py`、`tests/test_a03_hold.py`、`tests/test_a03_amendment.py`（最后一项拟新增） | 获批后的层次测试及故障证据；本轮未改或运行 |

算法/题型规则仍归 delivery/quality 对应模块，runtime 只编排原生流程。若未来 A02 的私有 Prepared 或 TARGET 接纳边界需要变化，须另列精确接口并协调主要写入者，不把本提案视为已批准改它们。根依赖、浏览器入口、真实书籍、B 内部研发均不在建议实现范围内。

## 8. 有界后续测试矩阵与停止点

后续 **12 组**最小矩阵见 [future-test-matrix](../evidence/A03/execution/P2-R1-proposal/future-test-matrix.json)。除本轮静态层之外全为 NOT_RUN；应先批准版本/未闭合条件，再另派最小实现范围和冻结验收基线。

| 组 | 后续所需证据 |
| --- | --- |
| PFX | 首 action intent 前退出的真实全局 anchor=3、owner/其他计划/其他 scope 事件不删不改；native DB 全量比较；跨 scope 每 frame 闭合 |
| ABS | 两个独立新读+第三最终读、真实 readonly prepare、完整 ABSENT、唯一 H+1 fact、effect/intent/permit=0 |
| NEG | 自封完整前缀、删事件后重封、旧/外国 owner/store/session、过期 CAS、重复 fact、其他 scope pending/书隔离、前序影响不明、目标二次变化拒绝 |
| CRASH | 在 read-start/finish、fact文件、事务/CAS/index/event 的前后有界故障；预算不复位、不半提交、不自动重试 |
| REPORT1 | 原 null 头→晚到完整 receipt 的真实同 intent/fact 历史，头字节不变、完整 source 分母/POST/Batch 与刷新 readback |
| REPORT2 | 两不同 snapshot 的合同消费者 fixture；真实运行层先明确可达性/聚合范围，不能用不可达静态历史顶替 |
| REF | 缺声明/嵌套 Resource ref、错版本/pins、普通跨 scope、伪造 frame、断链/分叉/旧头充 current、遗漏 receipt action 等负例 |
| PRE | 新已注册 oracle/verifier 的五项真实重执行和 native admission；旧 PRE/ caller PASS/缺页/答案错误/输入替换拒绝 |
| HOLD | 真实新 PRE/TARGET/plan 正向清除；候选之后第二次目标变化保留 hold；无 terminal successor/effect，其他 pending 仍暂停 |
| CONVERT | 支持的 known synthetic initial 的完整原件/映射/新包/完成 manifest；执行历史/未知 DB 拒绝 |
| INTERRUPT | 六个转换故障点、FAILED/INCOMPLETE 重开只读、新 id 重做、完成 marker/记录间崩溃；原件不变 |
| RETAIN | 人为早失败/超时/子进程断言，所有新 raw stdout/stderr/exit/进程与存储证据持久保存；不能修改历史 NOT_RETAINED |

本轮复现（工作目录为本工作树，均 stdlib、`-B`、纯新静态文件）：

```powershell
python -B examples/a03/P2-R1-proposal/check_static.py
python -B examples/a03/P2-R1-proposal/verify_delivery.py --check
# 可选：在另一个隔离导出副本内，用尚不存在的新子目录重编写静态值
python -B examples/a03/P2-R1-proposal/build_static.py --output-dir review-reproduction
python -B examples/a03/P2-R1-proposal/check_static.py --data-dir review-reproduction
```

检查覆盖候选全部新/旧结构、完整 pins、原件摘要、所有 Artifact 和递归 Resource 引用、逐 Artifact/frame 声明、同 book/scope 和 DAG、全局 anchor/链/永久预留、receipt/action/fact/head/snapshot/报告关系及预期静态拒绝。它没有实现 native index/current target、比较算法、跨 scope 正例或转换恢复算法。

实际命令与原始 stdout/stderr/exit 在 [runs](../evidence/A03/execution/P2-R1-proposal/runs/check-05/exit.json)。author-01 因新脚本缩进错误退出 1，保留原始 stderr；修复后 author-02 编写早期草稿，author-03 编写当前候选。check-01/02 是早期草稿静态检查，check-03/04/05 是当前候选；05 新增链重封后错误 ACCEPTED action digest 的拒绝，并绑定最终 checker/profile SHA。本轮当前候选共 32 项静态记录：13 项结构/引用通过、17 项预期拒绝、2 项旧 R17 等式逻辑见证。verify-01 在写出自身结果前检查其链接而退出 1，原件保留；后续仅在首次写入阶段明确允许该输出链接和最终 manifest 暂缺，冻结后的只读检查不豁免。所有结果单独保留，不能把 wrapper/静态 exit=0 当成功能通过。清理新草稿的命令被工具策略拒绝，未执行，随后采用新的 candidate-v2 目录，原草稿仍在。

[静态结果](../evidence/A03/execution/P2-R1-proposal/static-check-result.json)、[范围与保全核对](../evidence/A03/execution/P2-R1-proposal/delivery-verification.json) 与 [统一清单](../evidence/A03/execution/P2-R1-proposal/sha256-manifest.json) 提供冻结依据。清单只排除其自身；包括原失败日志、早期草稿及归档、输入原件、静态负例和报告。27,168 个基线 tracked 文件逐一 hash 比较。

**停止点：冻结本提案后结束，等待主调度独立审阅。** 需明确裁定的新消费者帧边界、总读次数解释、已知 DB/profile/session 接纳方式、fixture oracle/verifier 权威、R17 真实多头可达性/聚合范围、后续完整转换/留证验证均没有被执行者自行批准。没有实现派单、B 接受、平台验收或 I01 释放结论。
