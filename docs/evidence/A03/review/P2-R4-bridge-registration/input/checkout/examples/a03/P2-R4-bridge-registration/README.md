# A03 P2-R4 接口与登记准备包

状态：`REVIEW_WITH_MINIMAL_RESIDUAL`。这是固定基线的接口方案与四包静态检查记录；正包未通过，原生资格仍关闭。接口表为 [bridge-interface-proposal.json](bridge-interface-proposal.json)，SHA256 `b57d0af5d72a03c4b16e6eeedc267bda50f1dfcf022728b1f107f5b158a22207`。现有 19 个入口的精确签名、源文件 Git blob/SHA256、函数源码摘要及后续改动点均在表中；第 20 项 PRE 接纳边界明确为尚不存在的提案。

## 输入输出与选择责任

这里的 exact ArtifactRef 是 `{artifact_id, revision, kind, content_hash}`，PolicyRef 是 `{policy_id, revision, content_hash}`；不能只按 ID 匹配。bundle 包含完整 artifacts、policies、evidence 及 Resource 字节。新 `BridgeContext`、`ValidatedA03Bundle`、`AdmittedPreRun` 等类型均未实现，定义见机器表。以下补充现有入口的数据形状，来源仅为固定源码文本，未 import 或执行产品。

| 机器表 id | 现有输入与输出形状 |
| --- | --- |
| contract_dispatch | 原始 exchange mapping / 已接纳 bundle，加可选 asset_root；返回 C01 ExchangeBundle 或 RecoveryExchangeBundle。没有 1.3 handler。 |
| contract_readiness | bundle、exact plan_ref/current_snapshot_ref；返回 exact ApplyPlan 节点，通过并不产生 permit。 |
| artifact_factory | 未封签 envelope mapping；返回带 content_hash 的 artifact mapping，按显式 namespace 选择当前 seal 分支。 |
| legacy_validator | C01 exchange mapping/model 与可选资源根；返回校验后的 ExchangeBundle；缺资源根时不能声称字节已核验。 |
| recovery_validator | 1.1 exchange mapping/record、asset_root、私有 archive 标志；返回 RecoveryExchangeBundle(data, root)。 |
| recovery_readiness | recovery bundle 和 exact plan/current refs；返回 plan 的 PublicRecord 视图。 |
| target_factory | kind/id、已解析 anchor、payload mapping、依赖 artifact 列表、config/version/时间；返回 sealed artifact mapping。版本来自 anchor。 |
| target_analysis | bundle、exact graph/snapshot/current refs、PolicyRef、带 version 的 config；返回 TARGET payload：subject/graph/policy/snapshot/receipt、coverage/checks/issues/decision/reason；1.1 额外 recovery_refs。 |
| target_producer | 上述分析输入与新报告 id/时间/run_id；返回追加真实计算 TARGET CheckReport 的完整 bundle。 |
| planner_create | 全包与 exact graph/PRE/TARGET/snapshot/current/policy refs、config、新 plan 身份、operation/previous_receipt；返回追加生成 ApplyPlan 的完整 bundle。 |
| planner_verify | 全包、plan mapping、current ref、config、可选 observation_binding；成功返回 None，失败抛异常；不签发当前写入资格。 |
| planner_observation_bridge | exact plan/action、fresh_observation mapping、config、完整 prepared_before、progress_refs；返回机器表列出的 19 个字段组成的 PublicRecord。 |
| state_comparison | planned/observed snapshot 与各自 target-state mapping；返回 PublicRecord：equivalent、两 exact snapshot refs、两 hash/version、reasons。 |
| target_create | 目标目录、bundle、exact snapshot/source refs、namespace、asset_root、expected_store_id/session；返回固定 descriptor 的 PersistentMockSession。 |
| target_open | 目录与预期 store/session/target_key/scope/source tuple；返回验证 descriptor 后的 PersistentMockSession。 |
| observation_credential | session 与观察 mapping；返回从独立持久观察行核验的 original record，核验资源路径/原始 SHA/深相等及完整读取。 |
| snapshot_producer | session 与上述可信观察；返回封签 snapshot mapping，保留真实观察时刻/hash/version 与固定 source。 |
| prepare | session、全包、exact plan/action/config/current snapshot、asset_root；返回本 session 实际签发且登记身份/摘要的 PreparedAction。 |
| prepare_verification | exact PreparedAction 对象、binding、预期 config/plan；返回 VerifiedPreparedAction，其字段绑定 attestation/config/plan/action/digest/target/store/session/source/scope/prepared_before/observation/read_sequence/hash/version。 |

新方案先由 contracts 按确切采用记录选择 codec/model/profile/pins，再做完整结构、字节、引用与业务规则校验。quality 计算实际检查并通过拟议的私有 `admit_a03_pre_run` 接纳真实 PRE 运行；质量 PASS 不能替代这个证明。runtime 独立验证真实登记行、owner/generation/fence、当前全书 head/pending/hold、持久预算、intent/permit 和 effect gate。JSON 标记、重新封签或 copied PreparedAction 都不产生原生能力。

旧 1.1 在新桥接方案中仅作不可变历史读取；当前 1.3/profile 只作静态检查。未来确切采用版本、完整 codec、实际 PRE/native producer 证明及 runtime 当前资格齐备后才可能派发。错版本/profile/pins、无运行证明、旧 hold、错观察或把历史派生视图用于当前资格均拒绝。这里没有改变旧产品已经存在的行为，也没有将当前 profile/oracle 记为已采用；B 的业务合同仍未确认。

## 算法与历史闭包

`create_plan` 的投影、action-id、目录/题序、依赖、policy 和事实比较语义保持原样。新增接纳与版本 codec 不能靠版本白名单、1.3→1.1 改标重封签或删 UNKNOWN/登记事件实现。必须先校验原始全包，历史重算再按 exact creation-input anchor 取得完整正式 EvidenceRecord/Resource/typed-frame 闭包；私有历史派生视图只能用于重算。

`observation_binding` 必须绑定 exact plan/action/digest、before/observed snapshots、observation_id/read_sequence、source/book/scope/target/session、基线与当前 hash/version、prepared_before、applied_prefix/effect_log_delta/comparator。progress 枚举同一 plan/scope 的完整 actions，前序为 ATTEMPTED+APPLIED 且 intent/fact 相符，尾部为 NOT_ATTEMPTED。不能恢复旧 attempted tail。prepare 的实际观察先消耗持久读取预算；verify 对已持久观察行的校验不偷偷增加业务观察。新增 snapshot/resources 必须在任何持久消费者提交前加入完整包及引用闭包。

固定单题的预期链已逐步列于机器表 `expected_chain_NOT_EXECUTED`：新 INITIAL 实际接纳 → 真实 TARGET → 真正 create_plan 的单动作 → 同一 intent 的 UNKNOWN 且原 receipt 尚不存在 → 只读恢复终局 head、original_receipt_ref=null → 同 intent/fact 的晚到完整 receipt → 独立报告读取与新 POST/Batch（PENDING/NOT_SUBMITTED）。本轮未执行该链；旧 fixture plan 只作事件前缀锚点，未手写新 READY plan，也未把旧多头静态值当成可达历史。

## 四包结果与冻结

完整包与资源在 [cases](cases/registration-positive/case.json)；共四个 case，每包 10 artifacts、6 个事件、重算全部 artifact/resource/event 摘要。planless TARGET_DRIFT_HOLD 的顶层及 payload.plan_ref 均为 null，frame 显式声明所消费 exact refs。观察与登记均明确标记静态合成值，未开 DB。

固定 R3 Package 类语义未改。加载器只把 R3 模块的 `base.EVID` 输出赋值 AST 节点指向新目录，Package 类 AST（含位置）前后完全一致；未调用 R2/R3 main 或旧 36 矩阵。输入与路由证明见执行目录。

| case | 修改 | 实际结果 | 可得结论 |
| --- | --- | --- | --- |
| registration-positive | Source/Snapshot 同书同 scope、target 一致 | FRAME_REGISTRATION_BINDING | 正包失败，不能接纳 |
| source-binding-negative | payload 使用 exact Source A，Snapshot/scope 保持 B | 同码 | 实际消费者的 scope 绑定拒绝 |
| snapshot-binding-negative | payload 使用 exact Snapshot A，Source/scope 保持 B | 同码 | 实际消费者的 scope 绑定拒绝 |
| target-tuple-negative | 重新封签 Snapshot.target_id 与登记 target 不同 | 同码 | 被全局扫描冲突遮蔽，未证明 target 校验有效 |

源码推理定位：继承的固定 R2 `check.py:70` 将 Source/Snapshot.book_id 与消费者 book 比较；`:87` 的全局 EvidenceRecord 资源扫描以 book=None 进入相同登记前缀。正包在实际消费者上下文的该谓词成立，在全局扫描上下文不成立。这个定位来自已产生四包与源码控制流，没有第 5 次 Package 调用。

局部选择均未实施：优先把无消费者上下文的全局字节/图遍历与实际 Artifact/frame 绑定校验分开，不能仅在 None 时豁免相等性；如改为 placement 约束，须另行确认正式直接 Resource 字段及新有限包。正包路径解开后再独立核对 Snapshot.target_id 与 canonical 登记 target。当前停止，不改 checker、不换放置路径重测。
