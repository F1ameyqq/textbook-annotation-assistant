# A03 P1-R1：未尝试事实提交与资源引用闭包修订

日期：2026-10-17（Asia/Shanghai）。状态：**P1 REVIEW / PROPOSED_NOT_IMPLEMENTED**。本轮只修 A03-P1-API-01、A03-P1-REF-01；迁移身份附带澄清。未实现恢复、未取得独立设计通过、未授权 P2。

修订基线 `2d5ae2a53945a7fa20ef60a6b61e7b31c91dbea9`；原设计提交 `6ac0256f05169570605fcb921a773ff2ae0f4aef`；原 workflow `a354f95f1d0b40a8f0847b57fa3978cac999e7a2`；A02 代码基线 `ec1b4defbfa3ec0f181d291106fb53313983e493` 均不变。不合并浮动主分支，不改旧 P1 文件。

本工作树保全的权威输入为 [R1任务](evidence/A03/execution/P1-R1/inputs/A03-P1-rework-R1.md)、[独立 REWORK](evidence/A03/execution/P1-R1/inputs/A03-P1-review-report.md) 和 [主调度静态核对](evidence/A03/execution/P1-R1/inputs/coordinator-check.json)。任务 SHA256=`5e868e4b84fc1c138ff96806a4ae205522c465b09d238999d43070f5ee610dab`；报告 SHA256=`df3faccf4be93335517a3f319fc356f3d568db44202e56a6a35e5153f54f2b8b`。

原 [P1 提案](a03-recovery-contract-v1-proposal.md) 为历史设计。R1 的完整候选结构、案例、递归资源闭包和新接口分别由 [新目录说明](../examples/a03/P1-R1/README.md)、[候选 API](../examples/a03/P1-R1/api-proposal.json) 及 `examples/a03/P1-R1/data/` 固定。本文件只覆盖以下两项修订；其余 D01–D08、旧无 intent UNKNOWN 不解除、固定 target session、全合成边界和核对上限沿用原 P1。

## 1. API-01：专用未尝试 ABSENT 事实提交

最小输入仍为 A APPLIED、B UNKNOWN、C NOT_ATTEMPTED，原计划 INTERRUPTED。C 没有 intent/obligation，不能调用原 RUNNING 正常结果提交，也不能补造 intent/resolution 调用恢复提交。R1 新增独立只读事实入口，不改变原两条入口的要求。

```text
runtime.storage.commit_unattempted_absence(
    bundle, request, *, owner_id, generation, asset_root, observer
) -> UnattemptedAbsenceRecord

request = {
  registration_id,
  plan_ref,
  action_id,
  action_digest,
  expected_event_head: {sequence, hash}
}
```

生产者为 runtime.storage；observer 仅为受控目标观察能力，不具有 dispatch/save 接口。delivery 的公共 `action_facts/compare_action_effect` 保持 A02 冻结比较规则；contracts 只验证声明、字节与引用。request 中的 ID、摘要和期望头是待比对输入，不是权限凭证。调用者不得传一份自报 prepared、ABSENT 或完整账本 JSON 当作事实。

### 1.1 准入与未调用证明

仅允许受控当前库已经登记且状态 **INTERRUPTED** 的精确计划/动作。计划登记、完整动作清单、永久身份预留、执行游标和事件前缀必须可从原 PLAN_ACCEPTED 一直核验到当前头；C 仍有 NOT_ATTEMPTED 事实，且全库没有该动作的 intent、义务、DISPATCH_STARTED、授权消费或目标效果归属。仅“没有找到某条日志”不够；缺失、截断、断链、错库、跨 scope 遗漏、未核验导入材料都不能证明未调用。

使用当前 ACTIVE owner/generation，可与原执行 owner 不同；必须核对固定 anchor/ledger/target store、canonical target_key、target_session_id、SourceBundle 精确版本和 scope。拿到同书效果闸后，runtime 当前事务扫描该书全部 run/scope；B 的 UNKNOWN 和其他未决都保留。这里允许在暂停书上只读核对 C，不表示获得写入目标资格。

若 C 的真实相关范围/身份或独立基线因 B 的未决效果而不能明确，拒绝，不把 B 假设为 APPLIED/ABSENT；A 的已确认正常变化则按原 A02 事实规则保留。尤其不能删除 `next_order` 等字段，或拿计划初始全局快照误判合法前序变化。

### 1.2 两次真实新观察与专用只读准备

新入口不调用会拒绝 INTERRUPTED/BOOK_WRITE_PAUSED 的 `prepare_action` 或派发 `bind_plan_observation`。它在同书效果闸内执行一条专用只读分支：

1. 在第一 runtime 事务核对 owner/generation、完整未调用前缀、计划/action 摘要、固定会话和 expected_event_head，保留当前一致扫描依据。
2. observer 第一次实际独立读取目标，产生新的 observation ID、时间、read_sequence、scope 完整性和业务视图。公共事实函数生成只读 prepared_before，明确这是本次观察基线，不能冒充从未发生的 C 派发前历史。
3. observer 第二次独立新读回，再由同一公共比较器比较完整相关事实。必须是充分 ABSENT：身份唯一、相关范围完整、无相关框且与第一观察的相关事实一致。两次读回序号/身份各自独立，不能复制同一次读取改时间。业务版本未变可以合法，两次读仍必须真实。
4. 返回 CONFLICT/INDETERMINATE、读取失败/截断、旧观察、缺身份或相关事实变化均不生成可提交终局；只保留失败观察/进度，旧计划和暂停状态不变。

每次入口最多 **2 次**独立目标读取、单读 **2s**、整个入口 **8s**，无自动重读；若处于父恢复调用内，还受父调用 **60s** 的最早期限约束。观察尝试用该 registration/动作/调用的独立观察记录计数，不为 C 补造 intent/obligation，也不改变原“每 intent 每恢复调用最多 3 次”的规则。确定性准入错误在读前拒绝。

### 1.3 不可变事实、事件与事务

ActionFact 仍为资源而非第四种 Artifact；R1 新增 `origin_phase=UNATTEMPTED_ABSENCE`。`intent_ref`、`obligation_id`、`resolution_ref` 和 `result.intent_ref` 必须全部为 null；result 必为 NOT_ATTEMPTED / NOT_APPLIED / ABSENT / RECHECK_TARGET / replay_allowed=false，不能宣称发生调用。

新增必填但 nullable 的 `unattempted_basis` Resource：UNATTEMPTED_ABSENCE 必须非空，EXECUTION/RECOVERY 必须 null。它绑定完整未调用事件前缀资源、登记/书/计划/action、固定来源与会话、当前 owner/generation、captured expected_event_head、第一观察、只读 prepared、第二观察和比较器。小型 Resource Schema 及字段定义随新完整候选交付。`gate_held`、`complete` 等设计字段仅表示所需事实，不构成现实中的锁/事务证明。

在闸内先完整写入并核对两观察、prepared、basis 和事实文件及其递归引用，再提交 runtime 索引与 **UNATTEMPTED_ABSENCE_COMMITTED** 事件；事实的 journal_sequence=expected head.sequence+1，predecessor_hash=expected head.hash。第二 runtime 事务重核当前 owner/generation、当前完整未调用前缀/同书未决集合、精确绑定、永久唯一性及事件头 CAS；不把目标观察与 runtime 事务当成一个原子提交。任何文件/事务/CAS失败，未索引文件只是 orphan，不能投影成已提交事实。

永久唯一键为 `(journal_id, canonical_target_key, action_id)`，不含 owner/generation 或 registration。stored binding 同时记录完整 plan_ref/action_digest；接管不会再产生第二份终局。相同绑定已提交再 submit 返回 **UNATTEMPTED_FACT_DUPLICATE**；不同绑定/不同内容返回 **UNATTEMPTED_FACT_CONFLICT**，都不追加提交事件、不变更暂停。已有结果只能通过独立只读查询取得，不提供以重提交成功绕过代次/新鲜度的分支。

具体拒绝包括：PLAN_STATE_INVALID、PLAN_ACTION_MISMATCH、ACTION_DIGEST_MISMATCH、EVENT_PREFIX_INCOMPLETE、ACTION_ALREADY_ATTEMPTED、OWNER_GENERATION_STALE、EVENT_HEAD_CAS_MISMATCH、OBSERVATION_NOT_FRESH、CONCLUSIVE_READBACK_REQUIRED、PREPARED_BEFORE_MISMATCH、UNATTEMPTED_FACT_DUPLICATE/CONFLICT 和存储失败。准确归属和 DTO 以新 API 文件为准；这些是预期错误码，P1 没有执行这些拒绝。

### 1.4 进度与完整回执

只将 C 的已提交事实投影到 ExecutionProgress。A 原 APPLIED、B 原 UNKNOWN 的事实/回执保持原件，B 的义务及书暂停不清除，原计划继续 INTERRUPTED，旧 tail 永远不 dispatch。

如果 A/B/C 每项都已有其类别所需的完整事实，新的完整 ExecutionReceipt 可聚合原 A、原 UNKNOWN B 和新 C 的 action_fact_refs；每个 result 与对应 fact.result 精确一致。含 B UNKNOWN 的批次仍为 NEEDS_RECONCILIATION，内容 PENDING、NOT_SUBMITTED。缺任一必要事实只输出全动作 progress，不能为凑回执补造 C UNKNOWN/NOT_APPLIED，也不能补造 C 的 intent/resolution。

## 2. REF-01：每个消费者的递归资源声明

普通 ArtifactRef 仍是四元组 `(artifact_id, revision, kind, content_hash)`，同一消费产物只可引用同书同 scope 的目标。R1 对消费关系作明确机械定义，不降低旧规则：

1. 对每个产物分别扫描其 payload 直接普通引用、直接 Resource，以及该产物正式 evidence_refs 所解析的 Resource；Resource 先验证 portable 相对路径、media_type 和真实字节 SHA256，再解析 JSON。非 JSON 仍验证字节。
2. 对 JSON Resource 递归展开所有嵌套 Resource 和普通引用，不能只展开 action-fact。observation、prepared、basis、scope proof 和所有嵌套资源都适用。路径以显式资产根为基准，不相对资源文件重新猜测。
3. 每个发现的 ordinary ref 都必须：目标实际存在，四元组精确一致，book/scope 与当前消费者相同，且完整四元组出现在**当前消费产物**的 input_refs。另一个产物已声明、全包已知目标、能通过资产定位找到对象都不等于本消费者声明。
4. 可缓存已验字节和解析结果；但引用授权/声明检查按 consumer 单独执行，不能因 receipt 已检查同一 fact 而跳过 progress。每 consumer 以规范化路径+精确 SHA 去重重复展开，DFS active stack 拒资源环。
5. 资源发现的所有 ordinary refs 同时加入消费产物依赖图；自引用、产物环和 Artifact→Resource→Artifact 混合环拒绝。不存在为避免循环而豁免资源内部引用的规则。资源本身不反向引用消费它的事实/产物。

修订生成器仅做静态转换：从旧 P1 读取固定案例，按依赖顺序补声明；重新计算被影响的资源字节 SHA、产物 content_hash、下游精确引用及迁移映射。不得通过删除 fact、删 snapshot 或放宽普通 scope 来让正例通过。旧恶意反例按原覆盖保留，新增反例在已修正正例上单点构造；代码不会给语义失败例授予资格。

原修前 normal 和部分计划输入及所有所需资源已逐字节保留在 `docs/evidence/A03/execution/P1-R1/before/`，同时保留独立最小反例。新静态 checker 和独立资源审计分别记录修前漏声明与修后声明闭包；只有实际形状/字节/引用结果可称静态实测，提交事实/ABSENT/暂停行为全部 EXPECTED_NOT_EXECUTED。

## 3. 候选版本与迁移身份澄清

顶层候选字符串仍为 `1.1.0-a-recovery-proposal / a03-exchange-1`，这是尚未实施/确认的候选，R1 用 `proposal_revision=A03-P1-R1`、本次确切 Git 提交及新 Schema SHA256 固定审查版本。旧 P1 是历史输入，不与 R1 候选混装或靠字符串自动选择；P2 开始前必须采用主调度明确批准的确切候选，不能运行时猜“最新”。R1 新 origin/unattempted_basis 属候选修订兼容变化，不是已发布版本的无声兼容扩展。

“新身份”准确指版本命名空间中的产物身份。namespace=`(schema_version,exchange_version)`；身份键为 `(namespace,book_id,scope_id,artifact_id,revision)`，kind 及 content_hash 为该身份必须唯一的不可变绑定。旧 `c01-exchange-1` 与新 `a03-exchange-1` 可在映射中保留相同本地 artifact_id/revision/kind，但属于不同 namespace；不能在同一 namespace 的同一身份下覆盖另一个 kind/hash。未来库索引键必须包含该 namespace 和 book/scope；普通四元组引用由所属闭包的唯一 namespace 解释，仍禁止跨版本普通引用。

迁移生成新文件、新摘要和显式映射，原文件与 UNKNOWN 原回执字节保全。新目录包含新旧 namespace 的映射与未来索引键说明。此处仅澄清原设计表述，不把它记为第三项已证明功能缺陷，更不允许旧无 intent UNKNOWN 获得解除资格。

## 4. 验证与交付边界

原 42 案例在新修订集合逐项映射，新增 API-01 分支及资源漏声明/错摘要/跨书/scope 邻近反例。新最短检查命令、实际命令/退出码、修前/后结果和所有 SHA256 由 [R1执行报告](tasks/A03-P1-R1-execution-report.md) 与 `docs/evidence/A03/execution/P1-R1/` 固定；旧 P1 的作者 PASS 已被独立 REWORK，不能据此认定新设计通过。

本轮没有修改 src/tests/公共合同实现/根依赖/调度状态、没有网络/浏览器/平台/凭据/profile/OCR/业务模型调用、没有 SQLite/恢复实现或进程故障试验。S01 真实来源完整性、Pillow 根依赖、B 确认、真实平台恢复与 I01 仍未解决。最终只交 P1 REVIEW，原独立验收复审与主调度批准前不启动 P2。
