# A03 P1 恢复合同 v1 提案

日期：2026-10-17（Asia/Shanghai）。状态：**P1 REVIEW / PROPOSED_NOT_IMPLEMENTED**。本文件冻结供设计审查的候选语义，不表示独立设计通过、P2 开工、功能验收、集成或 B 确认。

代码基线 `ec1b4defbfa3ec0f181d291106fb53313983e493`；派发/工作流基线 `a354f95f1d0b40a8f0847b57fa3978cac999e7a2`；A02 被接受交付 `38aca9dcc8d027409b95193e9cc142c2336b76d3`。既有 52+70+8 集成结果属于主调度历史事实，本 P1 没有重跑或把它们作为恢复功能证据。

依据：[正式任务](tasks/A03-runtime-recovery.md)、[独立标准](tasks/A03-independent-review.md)、[架构](architecture.md)、[公共合同](contracts-v1.md)、[S01 候选](tasks/S01-eligibility-preparation.md)。机器可审查定义及样例见 [P1 文件说明](../examples/a03/P1/README.md)、[候选交换 Schema](../examples/a03/P1/recovery-exchange.schema.json)、[候选账本 Schema](../examples/a03/P1/ledger-export.schema.json)、[API 提案](../examples/a03/P1/api-proposal.json)、[案例清单](../examples/a03/P1/case-manifest.json)。JSON 结构/引用检查与预期语义拒绝分开；候选 API 尚不可导入运行。

## 1. D01–D08 决策表

| 决策 | P1 具体选择 | P2 前的审查条件 |
|---|---|---|
| D01（本任务接口项） | 固定上述 A02/base/workflow；保持已接受规划/事实比较规则。A02 适配只允许 `src/annotation/delivery/mock/__init__.py`、`src/annotation/delivery/planner/__init__.py`、`src/annotation/quality/targetcheck/__init__.py` 三个既有文件；持久目标实现可新建 `src/annotation/delivery/mock/persistent.py`。精确 API 见第 7 节及 JSON | 独立审查确认四组接缝，不通过私有属性导出状态；不触碰根依赖。此 D01 不解决调度另记的 Pillow 依赖 D01 |
| D02 | 三个新产物 WriteIntent / ExecutionProgress / ReconciliationResult；schema `1.1.0-a-recovery-proposal`、exchange `a03-exchange-1`；runtime DB `a03-runtime-db-1`，user_version=1 / application_id=0x41303352；目标 DB `a03-mock-state-1`，user_version=1 / application_id=0x41303354；账本导出 `a03-ledger-export-1` | 完整候选 Schema、身份与引用表；账本不是普通 Artifact |
| D03 | 旧版本仅显式归档加载/复现。新恢复只接受同新版本完整闭包和真实本地提交的 intent。旧无 intent UNKNOWN 分类 LEGACY_UNRECORDED，永不被本版本 resolution 解除 | 不补造历史、不改原字节或原 schema；显式转换只生成新的模拟设计/运行输入 |
| D04 | 完整动作清单 progress 为部分计划唯一默认输出。完整独立 ABSENT 可将 NOT_ATTEMPTED 映射成 NOT_APPLIED，必须同时保留事实与证据；无充分证据无完整 receipt/BatchReport | POST_APPLY/BatchReport 绑定新 progress、原 receipt 与精确 resolution 链；旧对象不变 |
| D05 | 稳定书键、唯一受控库、跨全部 run/scope 未决扫描；owner+generation+事务及跨进程效果闸；每书 target session 固定 SourceBundle/scope，实际切换拒绝；新读产生新时间/id/read_sequence | caller JSON 不证明完整性；夺权和效果序列化；换目录、旧代次失败关闭 |
| D06 | 新版只实现 A03 的全合成准入：SYNTHETIC_COMPLETE/FIXTURE、所有资产及证据 SYNTHETIC、执行 SIMULATED；任何 ORIGINAL/OBSERVED/真实来源拒绝 | S01 独立完整性生产者、真实证据资格仍未实现；不释放 I01 真实资格；B 未确认 |
| D07 | 目标独立 `target.sqlite3`、独立连接/事务和效果日志；runtime 的 `runtime.sqlite3` 不原子覆盖目标效果。复用 A02 比较器 `a02-facts-1`，只新增公共观察/单动作/历史接缝 | 两个独立进程的 P2 复现尚未执行；本 P1 不创建目标或运行库 |
| D08 | 每 intent 每次 reconcile 调用最多 3 次实际只读尝试。单读 2s；单 intent 8s；整次调用 60s；SQLite busy 1s；效果闸/屏障等待各 5s；无自动旧动作重发 | 使用 monotonic 期限、持久计数/调用 ID、有界退出及明确退出码；数值须主调度批准 |

所有决定都是 A 内部 P1 候选。D02–D07 经独立设计验收和主调度批准后，才能由原执行对话进入 P2；超时数值也待批准。执行者不能自行采用提案绕过批准条件。

## 2. 版本、引用、解析与转换

新版本保留 C01 公共信封的字段、严格额外字段拒绝、时区时间、相对资源路径、摘要算法及内部身份语义。普通 ArtifactRef 的四元组仍为 `(artifact_id, revision, kind, content_hash)`，不增加跨书或跨 scope 例外；目标/计划/action 内容由语义校验核对。每个新闭包内只允许一种 schema 版本；run 可不同，但同一普通引用须同书同 scope。不可变 ID/revision 不允许同身份不同摘要或不同内容。

内容摘要：UTF-8、JSON sort_keys=true、ensure_ascii=false、separators=(',',':')、allow_nan=false；artifact 排除顶层 content_hash 后 SHA256，与 C01 `content_digest` 一致。原文件字节 SHA256 单独记录，不以规范化摘要替代字节保全。action_digest 覆盖完整 Action，包含 target、source_entity_ids、expected_before/after、operation、depends_on。plan_dependency_digest 固定公式为 `H({plan_dependencies_digest:H({graph,precheck,targetcheck,snapshot,policy,execution_mode,session_mode,required_capabilities}),source_ref,target_session_id,comparator_version:'a02-facts-1',prepared_before_sha256})`；H 是上述 canonical JSON 的 SHA256，各引用使用完整四元组。配置、授权、能力变动另外经公共资格门精确核对，任一变化使资格失效，不能只凭该摘要绕过检查。

| 输入/用途 | 公共候选入口 | 可读取 | 新恢复/新效果资格 |
|---|---|---|---|
| `1.0.0-a-proposal / c01-exchange-1` 原归档 | `load_archive_bundle(path, verify_assets=True)`，仍调用旧规则与原资源校验 | 是，原样复现旧行为并标 ARCHIVE_ONLY | 无；旧 UNKNOWN 不因可解析获得解除资格 |
| 新版完整闭包 | `load_recovery_bundle(path, *, asset_root=None)` | 结构、资源、精确引用、恢复链及合成声明校验 | 仍需 runtime 当前库、owner/generation、未决全量与真实本地 intent 校验 |
| 新旧混合普通闭包、新 resolution 引用旧 plan/receipt | 新版加载 | 拒绝 RECOVERY_VERSION_UNSUPPORTED / CROSS_VERSION_REFERENCE | 无，不定义跨版本恢复桥 |
| 未知 exchange/schema/DB/目标格式 | 相应 open/load | 拒绝 RECOVERY_VERSION_UNSUPPORTED / LEDGER_VERSION_UNSUPPORTED / TARGET_STORE_VERSION_UNSUPPORTED | 无，不猜最新版或自动降级 |
| 旧纯合成 fixture 的显式转换 | `convert_synthetic_fixture(source_path, output_dir, *, conversion_id, expected_input_sha256)` | 核对旧闭包资源和全合成资格后，生成全部新引用/摘要及迁移映射 | 只生成新的初始模拟输入；之后由新运行真实创建 intent |
| 旧 UNKNOWN / receipt / intent缺失材料 | 归档及完整账本登记 | 原字节可读；登记为 LEGACY_UNRECORDED | 本版本不可解除，不允许补默认 intent、改标签重封签或过滤旧记录 |

转换输出目录必须新建，记录旧路径/字节 SHA256/原 schema/旧 ref 到新 ref 的映射；旧素材不变。转换不得携带旧执行 receipt/resolution 作为新运行证明，不复制 UNKNOWN 历史成“新已记录 intent”。测试输入转换是新 fixture，绝非重放 A05 或其他真实动作。中断保留转换现场及未完成清单，不把半成品标为可执行。

JSON Schema 负责形状；contracts 负责资源/引用/同 scope 链/语义/来源；runtime 负责当前库完整性及真实事务事实。三层不能互相替代。candidate 样例即使字段写有 intent_committed_at，也只是 DESIGN_ONLY 数据，不能证明本地提交。

## 3. 三种新产物及字段约束

所有字段必填；明确 nullable 的字段才可为 null。列表无默认推定，空与缺失不同。三个产物均使用公共信封，producer.evidence_mode=SYNTHETIC；运行效果只能 SIMULATED。字段具体 JSON 形状以候选 Schema 为结构权威，本节冻结附加语义。

### 3.1 WriteIntent

payload：`plan_ref, action_id, action_digest, target_key, target_session_id, source_ref, question_id, source_entity_ids, before_snapshot_ref, prepared_before, execution_mode, journal_id, journal_sequence, journal_head_hash, owner_id, generation, intent_committed_at, plan_dependency_digest`。

- `target_key={platform_namespace,target_id,book_id}`；稳定书键不含 run/scope/action/question/PID，不能以题号/bbox/平台序号替代。
- 唯一 intent 键为 `(target_key, exact_plan_ref, action_id)`；SQLite UNIQUE 永久保留。重复内容只返回现有登记，不重新 dispatch；同身份不同 action_digest 拒绝 INTENT_CONFLICT / ACTION_ID_CONFLICT。另外永久保留 plan 登记键与 `(target_key,action_id)` 的书级去重记录；planned 仅表示已受理身份，不等同 ATTEMPTED。计划生命周期 ADMITTED→RUNNING→FINISHED 或 INTERRUPTED，执行游标及每步事实持久化；进程中断后旧计划永久 INTERRUPTED，未尝试 tail 也不得续发。解决后必须新快照/检查/规划及新动作 ID，不能重用已消费 ID 或只改 ID 克隆旧动作。改 plan ID 也不能绕开同书暂停及目标身份检查。
- plan_ref 必须是新版本有效计划；action_id/question_id/source_entity_ids/digest 与该动作完全一致。before_snapshot_ref 等于计划的有效初始快照，不为旧动作换新前置资格。target_session_id/source_ref 精确绑定固定会话及来源；prepared_before 是必填 Resource，绑定本动作相关完整事实、prepare时实际观察及合法前序动作摘要/结果，由 A02 prepare/compare 生产和解释，runtime 不复制比较规则。多动作实际派发前的事实区别于计划初始快照。
- journal_sequence 是本地 intent 提交事件的序号，journal_head_hash 是该事件的前驱链头，避免把包含自身引用的新头写回 intent 造成摘要循环。事务包含 intent 文件索引、完整书键、owner/generation、唯一键、前驱核验与事件；文件写完校验后才提交索引。
- intent_committed_at 是事务约定的提交时间标签；只有当前库内实际 committed 事件和链/索引核验成立才有资格。序列化时间或 hash 不是事务证明。文件先落盘而事务失败只留下 orphan，目标效果次数必须为 0。
- intent / DISPATCH_STARTED 均不能证明效果发出或未发出。崩溃后任何没有有效终局的已提交 intent 均先作 UNKNOWN 处理，先核对，不续发。
- 正常首发资格只允许当前 ACTIVE owner/generation、RUNNING 计划与当前游标的这一个刚提交 intent，且当前全书没有其他未决/hold。当前 intent 不是清除其他未决的豁免；runtime 在效果闸内以事务一次性消费 permit 并追加 DISPATCH_STARTED，再授权同一目标事务。重复调用、已消费 permit、重启/接管、INTERRUPTED 计划或任何其他未决均拒绝。即使 intent 已提交但从未跨调用边界，重启后也只能 reconcile，不能重新首发。

### 3.2 ExecutionProgress

payload：`plan_ref, journal_id, journal_head_sequence, journal_head_hash, actions[]`。actions 必须按计划动作顺序完整且无重复，一项包含 `action_id, intent_ref?, attempt_fact, dependency_status, attempt_evidence_refs[], result_fact?, receipt_ref?, resolution_head_ref?, effective_outcome`。

| 字段 | 值 | 依据 |
|---|---|---|
| attempt_fact | NOT_ATTEMPTED | 受控完整事件前缀及调度顺序证明未跨调用边界；不能从“无日志”推断 |
| attempt_fact | MAY_HAVE_BEEN_ATTEMPTED | 已提交 intent/调用边界后无确证；即使目标无效果也保留可能调用事实 |
| attempt_fact | ATTEMPTED | 有实际进入目标调用的持久证据；效果仍可能 UNKNOWN |
| attempt_fact | LEGACY_UNRECORDED | 旧材料无新本地 intent；不可推断调用历史或新资格 |
| dependency_status | READY / SATISFIED / BLOCKED | 来自计划依赖与前序有效结论；不由 runtime 自造题型规则 |
| effective_outcome | APPLIED / NOT_APPLIED / UNKNOWN / UNDETERMINED | 已提交逐动作事实、原 receipt 与合法链的当前投影；UNDETERMINED 用于尚无充分效果依据的未尝试项 |

intent_ref/receipt_ref/resolution_head_ref 可以为空，但存在时必须准确绑定同一 action；分叉、缺原件或跨 scope 引用拒绝。progress 自身的头指向事件前缀，不把自身写入该前缀造成循环；后续产物只引用既有不可变版本。未尝试且 dependency BLOCKED 的项仍须列出，异常/跳过/未入图谱题仍由范围清单保留。

正常多动作的逐动作收口：目标效果后实际独立读回，由 A02 公共比较器产生 ActionResult；runtime 先保存 `a03-action-fact-1` 资源，再以当前 ACTIVE owner/generation、RUNNING 计划及游标的事务追加 ACTION_RESULT_COMMITTED 事件。资源绑定 plan/intent/obligation/action摘要、prepared_before、独立 snapshot/readback、比较器和完整新 ActionResult、事件序号及前驱 hash。资源另外必填 `origin_phase=EXECUTION / RECOVERY` 和 nullable `resolution_ref`；普通执行为 EXECUTION/null。`result_fact` 精确指向它；这不是第四种 Artifact。APPLIED/NOT_APPLIED 的事实与证据充分且事务提交后，才能终结该 intent 义务；UNKNOWN 继续暂停。事实提交失败保留未决，不能靠内存比较结果推进。

progress.effective_outcome 只能由这些已提交事件、回执及合法链投影，公共校验实际读取并验证 fact 资源，不能自报 APPLIED 解锁。A 的正常结果在完整 receipt 形成前已由该事件收口，所以同一 RUNNING 计划可继续 B；只有 APPLIED 前序满足依赖。NOT_APPLIED/UNKNOWN 会中断旧计划，尾动作不续发。重启/接管后的 intent 禁止用正常结果提交入口补终局，必须显式 reconcile。最终完整 receipt 汇聚同一批原事实；不要求每个正常动作调用 reconcile。充分 ABSENT 的未尝试项可有 result_fact，但其中 intent/obligation 均为 null，事实为 NOT_ATTEMPTED，不能冒充真实调用。

### 3.3 ReconciliationResult

payload：`plan_ref, intent_ref, obligation_id, action_id, action_digest, original_receipt_ref?, previous_resolution_ref?, observed_snapshot_ref?, observation_id, recovery_call_id, attempt_index, observed_at, read_sequence, target_state_version, target_state_hash, observation, resolution, platform_ids[], evidence_refs[], readback?, comparator_version, reason_code, replay_allowed=false`。

- obligation_id 固定为 `obl-` 加 `H({journal_id,target_key,intent_ref,journal_sequence,journal_head_hash})`，字段取原 intent 及其精确四元组引用，绑定真实提交产生的唯一未决义务。账本事件另有 event_id；原 intent 不写自身 ref 或 obligation_id，避免摘要循环。旧无 intent 历史使用独立 legacy 事件 ID，不能生成此类 resolution。新 UNKNOWN 必须有新 intent 和新义务，旧终局不会消除它。
- 必须有新版本真实本地 intent；有原 receipt 时精确指向原 UNKNOWN 项，必须保留原 receipt 字节。没有 receipt 的崩溃路径以 intent 为原事实，不捏造一个旧 receipt。原 receipt 的其他正常动作不受解决影响。
- 链首 previous_resolution_ref=null；后继只能指向同一 plan/action/intent/obligation 上一个 STILL_UNKNOWN。唯一后继约束、闭包缺引用、分叉及环都拒绝；不按时间戳/revision 挑选有利分支。终局没有后继；终局后出现目标变化新增 TARGET_DRIFT_HOLD 事件，旧结论保留，不能给旧 intent 重开链。该 hold 仅由新实际 snapshot、PRE_APPLY/TARGET 及新 plan 验证，在当前 owner/generation 和全书未决扫描事务中解除，不能凭旧 resolution 解锁。新的保存 UNKNOWN 必须关联另一个真实新 intent/obligation。
- 每次实际恢复读回都有新 observation_id、实际 observed_at、严格递增 read_sequence 和新 snapshot artifact/hash。target_state_version/hash 可以保持不变（目标效果未变），read_sequence 仍递增；调用者不能给观察器指定时间，也不能读旧 snapshot 再改时间。
- snapshot 的 observed_version/hash 绑定 target_state_version/hash；独立 readback 资源同时绑定 observation_id/read_sequence、book/target/scope、完整相关实体身份、internal_bindings/frame_projections、实际读取范围及完成性。业务状态摘要精确为 `H({target_key,source_ref,scope_id,platform_version,capabilities,directories,questions,frames,internal_bindings,frame_projections})`；排除观察时间/read_sequence/owner/fence/日志，读取与夺权不能改变业务摘要。新版本公开 helper 计算此摘要，旧 A02 hash 规则保持原样。读取失败也持久化新尝试与失败资源；无有效 snapshot 时 observed_snapshot_ref/readback/read_sequence/target_state_version/target_state_hash 必填但可为 null，仅 INDETERMINATE/STILL_UNKNOWN；不得为失败读捏造目标序号或版本。MATCH/ABSENT 的这些字段必须非空。
- comparator_version=`a02-facts-1`。完整性、唯一外部 ID、相关事实、版本/摘要及无矛盾均满足，才能 MATCH/ABSENT。单纯空列表、数量相同、成功响应、bbox一致或部分生效均不足。

| observation | resolution | 后续行动（旧 action 永不自动重发） |
|---|---|---|
| MATCH | RESOLVED_APPLIED | 必有 snapshot/readback/非空证据及实际 platform_ids，进入新 POST_APPLY |
| ABSENT | RESOLVED_NOT_APPLIED | 必有完整相关范围的明确无效果依据；重新 snapshot、PRE_APPLY/TARGET、规划新动作 |
| CONFLICT | STILL_UNKNOWN | 部分生效、重复身份、矛盾；保留异常与书暂停，不修删目标 |
| INDETERMINATE | STILL_UNKNOWN | 失败/截断/归属不明；有界只读重查，到限退出 |

不能用上次调用的旧观察充当新尝试；幂等登记同一 resolution 不增加效果，也不重复解除事件。有效状态是原事实加链的投影，不把 UNKNOWN 原结果改成 APPLIED。

## 4. D04：部分计划、完整回执与报告

多动作按 A02 冻结顺序/依赖处理。A 已 APPLIED、B UNKNOWN、C/D NOT_ATTEMPTED 时，立即持久并导出全动作 progress。B 即使无 receipt 也绑定已提交 intent；C/D 保留 dependency BLOCKED 和具体调度事实。

只有每个计划动作都具备其结果类别所需的事实与证据时才能生成完整 ExecutionReceipt；已尝试动作可凭实际调用/失败或矛盾读回证据记录 UNKNOWN，并不要求每项均已知生效与否。新版每个 ActionResult 另外必含 `attempt_fact, attempt_evidence_refs, intent_ref?`；ReceiptPayload 必含 `action_fact_refs[]`，逐结果精确汇聚同一批 fact 资源，其 result 与 receipt result 完全一致。NOT_EXECUTED 的空 results 才可空清单。NOT_ATTEMPTED 的 intent_ref 必为 null，不造 intent。若 C/D 确有完整独立 ABSENT，可记 NOT_APPLIED + NOT_ATTEMPTED + 明确事实证据；任一未尝试项缺充分读回则只出 progress，不能为未尝试项补 UNKNOWN/NOT_APPLIED 凑回执。已尝试项的真实 UNKNOWN 与这种无证据补项不同。对后续动作的 ABSENT 使用其实际相关 pre-dispatch 状态和合法前序效果，不能硬用计划初始全局快照误判前序正常变化。

新 receipt 不覆盖旧 UNKNOWN；从 resolution 计算的是有效投影，不制造“原执行就已确认”的历史。对已有原 receipt 的恢复仍引用原 receipt 和解决链；缺 receipt 路径只有各动作均有相应调用事实和完整结果类别证据后才产生新的完整事实 receipt。ActionResult 的 APPLIED/NOT_APPLIED 仍满足 A02/C01 原完整读回条件。

恢复事实的提交使用独立 `runtime.storage.commit_reconciliation`，事务追加 RECONCILIATION_COMMITTED，精确核对本次 observation/obligation/链头/全书集合；可生成 RECOVERY fact，其 resolution_ref 非空绑定已提交 resolution，原 attempt_fact 保留。它表示新观察下的有效结果，不能冒称原执行已确认。原 UNKNOWN receipt/fact 仍原字节保存；BatchReport 可以直接消费原 receipt 加合法链，不必重造旧 receipt。资源内部的普通引用也须同书同 scope、摘要一致并由消费产物声明，不能借 Resource 绕过引用闭包。

新版 CheckReport 增加 `recovery_refs[]`，仅 POST_APPLY 可非空；精确绑定所消费的 resolution 链头及原 plan/receipt，不允许跨 scope。新版 BatchReport 增加 `recovery_refs[]`、`progress_refs[]`；需要完整 receipt 及每项可追溯的有效投影（含 UNKNOWN）才能生成完整批次报告；含 UNKNOWN 的批次保持 NEEDS_RECONCILIATION。只有 progress 时使用进度导出而不伪造 BatchReport。报告校验跟随链追溯原 UNKNOWN，逐动作求有效状态，与全部范围项核对。新 POST_APPLY 必须在最新合法读回基础上生成，旧检查/旧报告不复用为新证明。

框和身份 MATCH 只证明框结构；内容保持 `PENDING`，submission 保持 `NOT_SUBMITTED`。禁止输出 COMPLETED。未知分母只在 Source/诊断进度用 null/UNKNOWN，零题用 [] 且明确 NO_ACTIONS；保留 BatchReport 非空分母约束，这两种情况不生成计划或完整批次报告，不计算 0/0 为 100%；异常、跳过、未入图谱项仍保留在 scope_manifest 和汇总中。真实来源的完整性/分母不得由恢复成功推导。

## 5. D05：唯一库、完整账本与效果闸

本机受控安装配置保存 canonical state directory、expected ledger_id、expected target store_id 和版本；初始化必须显式 `init` 并使用新的空目录，anchor 以独占新文件写入。之后 `open` 必须验证安装 anchor、规范化实际路径、DB身份/version/完整性/文件索引。配置另指空目录、缺库/anchor、替换 ID、未知 DB 或损坏均失败关闭；open 不调用 init，不重建空库。信任边界不包含恶意同时篡改 anchor/config/数据库的用户，也不承诺多机安全。

运行库至少保存：meta/书登记与固定会话、run/scope完整索引、不可变 artifact索引、全量 append-only book events、intent唯一键与事实、receipt/resolution边、owner/generation、pause及外部question/frame ID映射。配置版本和 event链亦被索引。所有已登记书的全部 run/scope 未决必须扫描；caller提交的局部包、空清单、旧账本 JSON、resolved=true 均不能证明完整性。

账本独立导出 `a03-ledger-export-1`；记录 ledger_id/version、book_key、owner/generation、书 event_head_sequence/hash、每 scope 的 source/session登记、全部 unresolved 原因/原 plan-intent-receipt与 scope/run、完整 history/pending/pause/ID状态。它是诊断快照，只记录精确 scope 分组的引用，不能混入普通 ArtifactRef 闭包或直接作为许可。书键稳定，跨 scope导出不放宽 contracts 普通同scope验证。

跨 scope 未决即使当前 target 不支持读取该 scope，仍被扫描并保留。保守历史登记可增加阻断项，不能凭导入 JSON 声称 commit 便取得新 intent 解除资格；只有受控原库可核验的真实本地提交才能进入新恢复链，其余归 LEGACY_UNRECORDED 或 UNVERIFIED_HISTORY 并维持暂停。每书首轮持久 target session 的 SourceBundle/scope 固定且 create/open 比较精确摘要；变更 SourceBundle、scope、target_id 或重新 register 均拒绝 TARGET_SCOPE_SWITCH_UNSUPPORTED/TARGET_SESSION_BINDING_MISMATCH，不能清历史。其他 scope 材料可作归档历史登记；普通导入不得制造新历史。无法在现有固定 target 上独立读取的项维持 UNKNOWN。跨 scope 案例的完整账本是明确构造的设计输入，不表示 P1 已执行两个 scope；P2 必须用保全的受控历史/确定性故障输入证明扫描，不能靠 session 切换删除记录。

owner_id 是启动时生成的进程实例 UUID，另记 PID/启动标识；generation 是每书单调递增代次，不依赖 PID 唯一性。领取/续期/回收、intent提交和解除暂停均为显式 SQLite 事务及CAS。owner lease 10s、2s续期；存活占有者不盲抢，回收需lease过期并已记录的进程实例已退出或显式受控交接。无法确定则 OWNER_BUSY。锁释放、超时和夺权都不消除未决。

SQLite 跨连接事务本身不足以关闭“检查owner后、目标效果前被夺权”的竞态。受控实现增加按稳定书键的 OS 跨进程效果闸（Windows标志字节文件锁/等价受控平台锁，进程退出自动释放）：claim/takeover和dispatch都持有该闸。dispatch在闸内重新验证当前owner/generation/事件头/未决集合，再调用独立目标事务，直至目标commit结束才释放。runtime和target不共享事务，仍保留效果已提交而receipt未提交的崩溃窗口。领取协议在同一效果闸内先由runtime事务预留generation并记CLAIMING，再由独立target事务持久activate_fence，最后runtime事务记ACTIVE。任何阶段中断保持暂停；恢复须核对两库fence一致，不复用旧代次。目标每次效果事务内核对已激活generation并拒绝旧代次；无可核验runtime授权回调或两库fence不一致则不发效果。无法取得闸5s退出，不能延长成无限等待。reconcile 仅有观察能力，绝不派发目标业务效果。

这里“只读核对”限定目标业务效果为 0。观察器允许独立事务记录观察元数据及递增 read_sequence，不得修改 questions/frames/业务映射/效果日志；此元数据不进入业务状态摘要，也不与 runtime receipt 共用事务。

解除暂停：事务中读取当前全书未决事件集合和链，逐一验证实际文件/资源、当前链头和 generation、obligation_id、事件头 CAS。只移除精确覆盖且终局成立的项；任何其他 scope、新 UNKNOWN、遗留无 intent、缺损证据或 CAS 变化均仍暂停。旧 resolution 不能授权新 UNKNOWN。新工作必须取得新 runtime 许可和新快照/检查/规划；另一书独立运行，合法多书包中的外书 UNKNOWN 不误阻当前书。

## 6. D06：全合成准入与 S01

新版 SourceBundle 的 scope_manifest 允许 null / [] / 非空清单；新增 scope_integrity={status,basis,proof}。status 为 UNKNOWN / REFERENCE_ONLY / INDEPENDENT_COMPLETE / SYNTHETIC_COMPLETE；basis 为 UNKNOWN / METADATA / HISTORICAL_REFERENCE / PLATFORM_RECORDS / INDEPENDENT_SCOPE_REVIEW / INDEPENDENT_SCOPE_SCAN / FIXTURE；proof 为 nullable Resource。

A03自动模拟入口只接受 SYNTHETIC_COMPLETE + FIXTURE、非空有效proof，检查独立合成fixture清单的 book/scope/pages/assets尺寸和摘要/逐页结果/完整题清单，null不获得自动资格。[]可作为零题检查导出，返回NO_ACTIONS，不造非空计划。INDEPENDENT_COMPLETE即使声称完整，在A03仍拒绝SYNTHETIC_ONLY。

新版本所有 Resource增加必填origin=SYNTHETIC/ORIGINAL/OBSERVED；Asset仍带provenance，两者均需SYNTHETIC。遍历整包和所有精确依赖/资源：producer.evidence_mode=SYNTHETIC，region.source及coverage clue来源均SYNTHETIC，实际图像provenance=SYNTHETIC，proof/readback/history/patch/检查/能力证据origin=SYNTHETIC，执行SIMULATED。任何ORIGINAL/OBSERVED/真实或缺失来源均拒绝SYNTHETIC_ONLY，不允许只给最外层换标签。标记和字节校验证明受控fixture的一致性，不证明恶意伪标签的真实来源；仅受控fixture生产链可进入运行。

迁移不能把已有真实A01来源追加合成PASS变为模拟资格；原S01反例保留。A03只实现合成门和版本隔离，不实现真实独立完整性proof生产/验证标准。S01真实完整性、Pillow根依赖D01、B确认继续未解决；I01仍需A01/A03实际验收与调度集成，真实来源自动资格另行阻断。本P1不变更公共合同文档，也不代表跨侧共同确认。

## 7. 四组 A02 最小公开适配

逐项当前路径/签名/行号、建议签名、责任、输入输出和具体失败码由 [api-proposal.json](../examples/a03/P1/api-proposal.json) 固定。以下是审查摘要，均为未实施接口。

| 组 | 当前入口及缺口 | 建议公共接缝 | 责任及兼容影响 |
|---|---|---|---|
| 1 会话/持久目标 | MockSession.register_target/read_target/read_snapshot；只有内存状态，register可重建上下文且source绑定需加强 | PersistentMockSession.create/open，固定store_id/source_ref/scope/target，显式init与open分离 | A03在mock白名单新增持久适配；旧MockSession仍明确只用于旧内存模拟，不宣称跨进程保证 |
| 2 单动作/intent | execute是整计划循环，直接私有_write，无runtime提交接缝；used_actions预登记全部动作 | prepare_action → PreparedAction；dispatch_action(...committed_intent,dispatch_permit,authority,effect_fault=None) → DispatchResponse | mock保留A02计划/相关事实规则；runtime提交intent和门禁。planned与started分开，未尝试不记成调用；不复制planner规则 |
| 3 新观察/比较 | read_snapshot在无效果变化时返回旧快照，时间不刷新；_compare私有 | observe_target(...observation_id,read_fault) → TargetObservation；compare_action(action,before,observation) → EffectComparison | 目标独立观察事务产生时间、read_sequence、snapshot/readback/失败资源；公开比较器复用原规则；reconciler只消费比较结果 |
| 4 完整历史/ID | receipt_history/action_log/is_paused只有部分投影；pending/serial/used/外部ID私有 | export_book_context/import_book_context（runtime受控完整读）；新资格投影消费合法同scope链 | 导出包含原件、pending、pause、去重身份、generation及全部外部ID；import只恢复受控全量历史不清target。原UNKNOWN三道门一起适配 |

适配必须同步处理 mock.is_paused、targetcheck.analyze_target、contracts.assert_plan_ready 三处原UNKNOWN阻断：新版仅通过公共contracts有效链投影覆盖精确同scope原项，再由runtime跨scope门决定全书可写。targetcheck/planner不接收自报账本JSON授予完整性，也不能过滤外书/历史artifact来绕过同书保护。旧版本继续原UNKNOWN规则。planner维持已接受计划生成/再验证；新接口仅传入合法版本/有效链和持久公开目标事实。

新观察与规划引用桥接：新计划的 PRE_APPLY/TARGET、计划 snapshot/current_snapshot 必须仍绑定同一次新观察的精确 ref。派发前的另一次实际观察不直接替换计划 snapshot。新版新增 planner 公共 `snapshot_state_equivalent`、`bind_plan_observation` 及 `PlanObservationBinding`；比较固定书键/source/scope/平台/能力和上述业务状态，而不把观察 ID/时间本身当作业务变化。没有已生效前序时要求实际业务版本/摘要等价；有前序时，由同一 A02 公共 facts/comparator 核对完整合法 APPLIED 前缀、当前动作 expected_before 和独立效果日志 delta，任何其他变化拒绝。新版 `verify_generated_plan(..., observation_binding=None)` 在派发路径必须验证这个 binding，再以原计划 snapshot 重算历史计划形状；这一步明确是历史派生验证，不冒充本次实际读取。runtime 只传精确引用，不能自行剥 metadata/计算等价。效果闸内还需重核实际相关事实，防止 prepare 后变化。旧版原签名默认行为与精确 ref 规则保留。

故障注入点：intent事务前、提交后、DISPATCH_STARTED提交后、目标实际效果commit后/响应前、独立readback后、receipt索引commit后。每点有稳定标识、有限屏障和明确退出码；P1只是接口定义，未启动进程故障试验。

## 8. D08：有界恢复、并发复现与退出码

一次恢复调用生成并持久化recovery_call_id与待处理intent队列。每intent attempts从1到3递增；读前持久登记尝试（失败/崩溃也耗一次），调用不能通过进程重启复用同call_id重置额度。新显式恢复调用可获得新call_id，但必须新实际读，不是自动循环调度。到3次仍未知则退出本次并保留暂停。结构/版本/摘要/引用等确定性错误立即拒绝，不通过重读来尝试放行。

单读2s、单intent8s、整调用60s三重monotonic期限，取最早到期；SQLite busy1s；效果闸5s；测试屏障5s。lease10s、续期2s。数值是P1待批准候选。超时/崩溃时保留已登记尝试和原现场；不为取得成功删除目录重新生成证据。未到队列项显式NOT_VISITED，不能在输出省略。

| 退出码 | 名称/使用 |
|---|---|
| 0 | 完成本次查询/核对；所有当前书未决解决或NO_ACTIONS。并不自动执行下一计划或表示质量通过 |
| 2 | INVALID_INPUT：结构、版本、摘要、引用或配置错误 |
| 3 | HOLD_PENDING：仍有UNKNOWN/LEGACY_UNRECORDED、冲突、未支持scope或读取上限 |
| 4 | OWNER_BUSY_OR_STALE：锁竞争、旧owner/generation、CAS失败 |
| 5 | STORAGE_FAILURE：文件/库/索引损坏、事务失败、未知DB版本、状态目录替换 |
| 6 | DEADLINE_EXCEEDED：单读/intent/整调用/屏障超时，暂停保留 |
| 7 | ADMISSION_REJECTED：真实/ORIGINAL/OBSERVED、来源不足或S01边界 |
| 90 | INJECTED_PROCESS_EXIT：P2测试专用受控子进程到指定断点退出；不作为功能成功 |

P2竞争用例以明确事件/屏障使两个自有Python进程同时到claim或dispatch检查点，记录PID/实例ID/代次/屏障事件和目标效果次数；不能用固定sleep推断串行性。只终止用例自己启动的进程。本P1自有后台/平台会话为0。

## 9. 预期校验层、错误与交付边界

候选case manifest给每例标注最早预期校验层和稳定错误码：STRUCTURE（类型/版本/字段）、RESOURCE（真实资源字节摘要）、REFERENCE（精确引用/身份/同scope）、SEMANTIC（链/效果事实/观察新鲜度）、SYNTHETIC_ADMISSION（来源）、RUNTIME_TRANSACTION（完整账本/真实intent/owner generation）。P1只能实际执行JSON/Schema形状、摘要、引用和文档设计一致性检查；恢复分类、链解除、真实本地commit、并发、进程崩溃和资格门结果均EXPECTED_NOT_EXECUTED。

最少覆盖新intent正常与无receipt的MATCH/ABSENT、部分计划充分/不足ABSENT、跨scope只解决一项、legacy无intent拒绝、错版本/摘要/身份、分叉/环、旧观察复用、真实/OBSERVED拒绝，以及目录/代次错误。语义错误案例应保持其他结构/摘要正确，以便P2未来能定位预期层；资源/摘要反例才刻意破坏对应hash。

执行报告为 [A03-P1-execution-report.md](tasks/A03-P1-execution-report.md)，证据与SHA256清单位于 `docs/evidence/A03/execution/P1/`。所有旧实现/样例/失败证据/调度状态字节保全；仅四处任务授权的新路径交付。最终只交付P1 REVIEW，等待独立审查和主调度批准；不推送、不集成、不释放I01、不自行继续P2。
