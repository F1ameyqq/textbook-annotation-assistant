# A03-P1 静态候选合同与设计样例

**DESIGN_ONLY / NOT IMPLEMENTED / P1 REVIEW 候选。** 这里的 JSON、状态、观察和本地事务字段全部是手工构造的设计输入，没有发生 intent 提交、目标派发、目标读取或恢复。结构检查成功不产生任何执行许可。P1 通过也不代表 A03 功能通过；P2、I01 和真实平台均未开放。

代码基线 `ec1b4defbfa3ec0f181d291106fb53313983e493`；workflow commit `a354f95f1d0b40a8f0847b57fa3978cac999e7a2`。完整设计见 [恢复合同提案](../../../docs/a03-recovery-contract-v1-proposal.md)，公开接口见 [api-proposal.json](api-proposal.json)。B 尚未确认。

| 文件 | 用途 |
|---|---|
| `recovery-exchange.schema.json` | 完整候选 `1.1.0-a-recovery-proposal / a03-exchange-1` 的结构定义，含现有全部类型及三个新增类型 |
| `ledger-export.schema.json` | 独立 `a03-ledger-export-1` 书级诊断导出；不是 Artifact、跨 scope 普通引用或写入许可 |
| `archive-v1.schema.json` | 从当前公共 `schema()` 只读导出的完整旧版结构，用于原字节归档读取 |
| `case-file.schema.json` | 仅设计样例包装：`design_only=true`、完整 bundle、诊断账本、假设的 runtime 条件 |
| `action-fact.schema.json` | 非第四种 Artifact 的 `a03-action-fact-1` 事件资源结构，供逐动作结果保存和最终回执聚合 |
| `case-manifest.json` | 每例精确路径、预期校验层、预期代码和静态预期；语义结果统一 `EXPECTED_NOT_EXECUTED` |
| `migration-map.json` | 显式新样例转换的原文件摘要、逐产物新旧映射及不迁移的结果产物 |
| `cases/`、`assets/` | 完整 JSON 与共享的相对资产；运输时一起复制本目录，资产根明确为本目录 |
| `archive/` | 原文件及其资源的逐字节副本；归档文件自身保持原样，不能加 DESIGN_ONLY 字段后声称原字节保全 |
| `build_design_examples.py` | 仅构造静态设计文件；读取现有公共 Schema 和指定归档，不调用 A02 mock/planner 或 A03 功能 |
| `check_design.py` | 仅 JSON、结构、资源字节、摘要、同书同 scope 引用、DAG 与手写 fixture 声明一致性检查 |

生产候选 Envelope/Exchange/账本不要求 `design_only=true`，否则 P2 的真实本地事务产物无法符合合同。未实施标记位于 Schema 注释、本说明、样例包装和新造资产。复制的历史图片/文本字节由新 Resource 的 `origin=SYNTHETIC` 与本说明标记；它们仍不是真实平台证据。

从工作树根运行，只检查交付的静态设计：

```powershell
python -B examples/a03/P1/check_design.py
```

脚本使用标准库，不安装依赖、不访问网络或浏览器。其结构评估器只支持交付 Schema 实际使用的断言关键字；遇到未知关键字直接失败。它不替代完整 JSON Schema 标准实现，也不实现新合同的语义验证、全合成准入、事务资格、账本许可或恢复比较。`PASS` 仅表示该案例的**静态预期**相符；所有 `semantic_actual` 仍为 `NOT_EXECUTED`。

需要重新构造设计文件时，指定本目录内一个尚未使用的子目录，再给检查脚本该资产根；不要覆盖已交付证据：

```powershell
python -B examples/a03/P1/build_design_examples.py --output examples/a03/P1/reproduced-new-directory
python -B examples/a03/P1/check_design.py --root examples/a03/P1/reproduced-new-directory
```

`--replace-draft` 仅供冻结前的本任务作者替换自己尚未交付的生成草稿，不能用于重做失败证据。README、API 和检查脚本不会由生成器覆盖。报告/证据与最终 SHA256 总清单由 A03 执行主对话统一归档。

## 精确摘要与观察形状

令 `H(x)` 为 SHA256，输入为 UTF-8 编码的 canonical JSON：`sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False`。普通产物及 policy 的 `content_hash` 计算时只去掉其顶层 `content_hash`。`action_digest=H(完整 Action)`。

```text
plan_dependencies_digest = H({graph,precheck,targetcheck,snapshot,policy,
                             execution_mode,session_mode,required_capabilities})
plan_dependency_digest = H({plan_dependencies_digest,source_ref,target_session_id,
                           comparator_version:'a02-facts-1',prepared_before_sha256})
obligation_id = 'obl-' + H({journal_id:intent.payload.journal_id,
                          target_key:intent.payload.target_key,
                          intent_ref:exact_ref(intent),
                          journal_sequence:intent.payload.journal_sequence,
                          journal_head_hash:intent.payload.journal_head_hash})
```

`journal_sequence` 是 intent 事务事件序号；`journal_head_hash` 是该事务前驱头摘要。Intent 不含自身 ref 或其自身纳入后的事件头，避免摘要循环。新 `ReconciliationResult.obligation_id` 精确绑定已提交 intent；旧无 intent 的事件使用独立 legacy obligation ID，不产生可解决的 intent。

WriteIntent 必含 `target_session_id/source_ref/prepared_before`。`before_snapshot_ref` 仍精确等于计划初始快照；`prepared_before` 则保留单动作派发前相关事实、完整性声明、合法前序 action 的摘要和结果，以及新实际观察的 `observation_id/read_sequence/observed_at/target_state_version/target_state_hash/view`。这里的 prepared 资源只是静态假设，不能作为实际 prepare/read 或本地 commit 证据。

新版业务目标摘要固定为以下对象的 `H`，普通旧版 A02 摘要规则保持原样：

```text
{target_key,source_ref,scope_id,platform_version,capabilities,directories,
 questions,frames,internal_bindings,frame_projections}
```

它排除观察时间、observed_version/hash、read_sequence、owner/fence 和日志。新观察资源的 `view={target:SnapshotPayload,internal_bindings,frame_projections}`；同时保留每动作的 action 摘要、内部题目身份、原实体、平台题/框 ID、完整相关范围声明和预期前后事实摘要。读取完整性或平台身份缺失时不能根据空列表给 ABSENT。本设计资产从已有计划的静态投影构造，不调用比较器，也不证明比较器结果。

`read_sequence` 属于独立目标的持久观察元数据，每次实际读事务完成严格递增；业务 state version 无变化也产生新的序号、观察 ID 和时间。Observer 可以在目标自己的 SQLite 观察记录事务里增加该序号；reconcile 的“只读”表示题/框/业务效果日志变化次数为 0，并非 SQLite 元数据完全无写。读取失败且没有实际快照时，`read_sequence/target_state_version/target_state_hash` 必填但均为 null；不能造一个读序号。MATCH/ABSENT 要求非空新快照、独立 readback、三项读值、完整相关范围与匹配身份。每 intent 每次恢复调用最多核对 3 次。

## 版本、合成准入与部分计划

新运行必须由 P2 当前受控库真实本地 commit 产生新版本 intent，再由当前 owner/generation 事务验证。调用者 JSON、封签、静态账本、旧文件改版本或清空状态目录均不授予资格。账本候选版本为 `a03-runtime-db-1`，SQLite `user_version=1`、`application_id=0x41303352`；账本 JSON 仅诊断展示，跨 scope 完整性由当前库事务核对。

显式转换只采用归档 normal 的 Source/Evidence/Graph/初始 Snapshot/PRE/TARGET/Plan，生成新文件和新摘要。旧 receipt、POST_APPLY 和 BatchReport 保留在归档；新的 normal receipt/report 仅以旧正常 payload 为结构模板重新构造静态设计，不迁移任何历史结果或资格。旧 UNKNOWN 原字节位于 `archive/legacy/input.json`，账本保留其原 plan/receipt 的四元组与归档字节摘要，始终 LEGACY_UNRECORDED，不补造 intent、不解除。

新 Source 允许未知或空 `scope_manifest` 作为诊断。全合成自动入口仅接纳 `SYNTHETIC_COMPLETE + FIXTURE` 及具体 fixture proof，且完整依赖闭包的 producer/evidence mode、Asset provenance、Resource origin、region/coverage 来源及 policy 都须符合合成限定。ORIGINAL、OBSERVED、真实执行模式或 policy 真实适用性拒绝；Archive 可读取不等于新运行可接纳。`fixture-scope-proof.json` 具体列出书/scope、页、资产尺寸与 SHA、逐页题目清单；这是人为制造的 fixture 范围声明，S01 真实完整性生产者仍未实现。

`partial-without-absent` 保留每个 action 的 progress，未尝试尾部是 UNDETERMINED，不造全计划 receipt。有完整独立 ABSENT 且有 NOT_ATTEMPTED 事实时，才可形成 NOT_APPLIED/NOT_ATTEMPTED；前序合法变化需按 A02 原事实规则处理。新 ActionResult 的 `attempt_fact/attempt_evidence_refs/intent_ref` 与效果 outcome 分开。新 CheckReport `recovery_refs`、BatchReport `recovery_refs/progress_refs` 精确引用同 scope 解决链与进度；旧报告不修改。框一致仍保持内容 PENDING、NOT_SUBMITTED，不输出 COMPLETED。

正常执行无需每动作都调用 reconcile。每次效果后独立读回与公开比较完成，runtime 才可实际提交 `ACTION_RESULT_COMMITTED` 及对应 ActionFact；充分 APPLIED/NOT_APPLIED 事实仅终结该 intent 义务，UNKNOWN 继续未决。Progress 每动作 `result_fact` 精确指向该资源；尚无充分结果时为 null，不能靠自报 `effective_outcome` 清除义务。最终 receipt 必填 `action_fact_refs`，每个 result 与同位置的 `fact.result` 完全一致，空 NOT_EXECUTED receipt 对应空列表。normal 的 prepare 观察序号为 1/3/5、动作结果观察为 2/4/6，最后范围观察为 10；intent 事件序号 2/4/6，普通结果事件 3/5/7。每个前序结果先于下一动作，避免用最终快照倒造此前的放行依据。P1 的事件资源仍没有实际事务资格。

ActionFact 必填 `origin_phase=EXECUTION/RECOVERY` 与 `resolution_ref`。EXECUTION 的 resolution_ref 为 null，走原 run 的正常结果提交入口；RECOVERY 的 resolution_ref 必须精确绑定已提交的本次解决链，并由独立 `commit_reconciliation` 产生 `RECONCILIATION_COMMITTED` 与可选恢复事实，不能回送正常结果入口。恢复事实保留原 attempt_fact，以新的观察表达有效 outcome，不把原执行 UNKNOWN 改写为当时已确认。已有 UNKNOWN receipt/fact 原样保留，Batch 可以直接消费原 receipt＋resolution；无 receipt 的两个恢复正例只展示 progress＋resolution，没有伪造恢复 receipt。

未知分母不造自动计划/Batch；完整合成零题例只有 Source 诊断和专门零题 proof，预期 NO_ACTIONS。Batch 既有非空清单和正数已知分母约束保持原样。

本版每 book 固定一个 target session 的 Source/scope，不支持的切换返回 SCOPE_SWITCH_UNSUPPORTED 并保持暂停。跨 scope 案例展示人为构造的完整历史账本：当前范围有解决链，另一范围仍未决且无受支持当前读取入口，整书仍暂停；不能以 register 替换目标或清空历史。终局 resolution 不再追加后继。已解决后目标变化产生 TARGET_DRIFT_HOLD；新实际快照、PRE/TARGET、新计划及当前 owner 事务重新检查，旧 resolution 不授予许可。

## 案例与实测界限

每例都是完整 JSON bundle 与实际资源，反例没有只给伪代码或 patch。`runtime_claim` 是设计输入，用于展示 P2 独立场景需要构造的库事实，P1 不将它当作已存在的库事务。首个不满足的校验门以主提案固定次序为准；manifest 的语义预期是待实现门的目标，不能把更早的 P1 无 commit 事实隐瞒成可执行资格。

静态例涵盖 normal、无 receipt 的 MATCH/ABSENT、混合动作有/无完整 ABSENT、原 UNKNOWN 保留、新读取但效果版本不变、读取失败、跨范围未决、旧无 intent、错版本/动作摘要/目标身份/书/scope/资产、链分叉/循环/终局后继、旧观察复用、真实/OBSERVED 来源、owner/generation/状态目录/自报空账本/伪 intent，以及未知/零题范围。引用自循环由于内容寻址不能形成一致固定点，样例明确在 DAG 层先拒绝，不伪造“有效摘要的循环”。

无 browser/profile/credential/network/platform/model/session 被创建；不存在待释放会话。未执行 P2 功能、并发、跨进程、故障恢复、语义资格、真实质量或成本测试。
