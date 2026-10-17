# A03 P2-R8-R1 producer 有界独立复核

2026-10-18（Asia/Shanghai）。**原 coverage producer 缺口已关闭；R8-R1 整体结论仍为 REWORK。** 本次确实推进到 PRE 接纳、一次目标效果、原 UNKNOWN、终局只读 head 与 RECOVERY material fact 持久化；随后 progress 状态投影产生 attempt_fact 不一致，reconcile 抛出异常，完整 receipt、独立 POST/Batch 仍未完成。不能将已落库的终局 head 等同于整个恢复调用正常完成。

被审 target 为 `a0c40886f3076f84c46377e03fc2206d2fdc5585`，派发键 `A03:review:P2-R8-R1-producer:a0c40886f3076f84c46377e03fc2206d2fdc5585`。本报告只做冻结字节、静态源码、原始日志和必要 SQLite 自有 immutable 副本核验；**未重跑 N1、N2–N7、最小测试、native API 或兼容套件，未修产品或重放效果**。R7 已接受的内部只读范围保留，整个 A03 未接受，I01 不释放。

## 确切输入、原字节和范围

| 输入 | 提交或 raw SHA256 |
| --- | --- |
| 审阅 workflow | `f09233d9ea7eb02d8f487fbda2e96b14d7902037` |
| 审阅交接单 | `4a2ebdb6f0b557781901c1134c36f76cb73a8efff269fbec53e1082954daa006` |
| base | `fa6edeb7e9dd0c9502781747e5fce012931d9441` |
| 产品修复提交 | `613952f170167551b6f935d93cc9f007e6aa7221` |
| target | `a0c40886f3076f84c46377e03fc2206d2fdc5585` |
| 执行 workflow | `b9889efd29baa364bdd0ce9e356a8cde7054f8d9` |
| 执行任务 | `bc0063986d164bd0ca7caeddfb2ed358439fd14e3d9d80961f2f5c85f932ad7b` |
| 执行报告 | `e9b99a31b5958f184ef9bea63f5b26a9765fac767af9ef21918929673c6df199` |
| 执行 manifest | `5d5bf3de95c8e6bd335e8ec1e014a627f9346837df2ff243ae1c63c719bd60ad` |
| 作者 process-release | `c051dbc4c821874f45c0e5a213391fd3f7c42a4e04ebcca12c8c6ae207031a77` |
| 作者 bounded-outcome | `734525b4a1a46b3a69e3ae930168eb904610f2d590f91c8cc4d2634202684381` |
| 作者 attempt-field-binding | `2c325f6044ae76493da4b6521b6fdf6139eb87d920c8779a32300a95bcf00771` |

按 `git -c core.longpaths=true ls-tree` 和二进制 `cat-file --batch` 核对 mode/type/blob、长度、blob SHA1 及 raw SHA256，不经 checkout 换行转换。未改变全局 Git 设置、未合浮动主树，未导入执行工作树的候选。

[交付字节索引](../evidence/A03/review/P2-R8-R1-producer/delivery-byte-index.json) 证明：507 个 manifest 条目与 manifest 自身全部吻合；29,201 个 base 旧条目中，29,198 个原样保留，仅修改下述三个允许产品路径。总计 508 个改动路径，其余为本轮独立命名空间的新测试、驱动、夹具、报告与证据。作者五项输入 pins 也逐项 raw Git 核对，包含原 R8 独立报告的 `66690c0e259635d770cc44d2265b979e813c7e72494c1cf9b87257ed5c8e5555`。

公共 `coverage_for`、Schema、旧 API、runtime、R7、原整数/浮点修复、根依赖、全部旧失败/测试/报告未变。仅导出本次必要的 339 个文件，见 [exact 输入索引](../evidence/A03/review/P2-R8-R1-producer/input-index.json)，没有复制历史全集。根工作区 4,252 个旧 A03 审阅/报告文件用有序路径/长度/raw SHA256 集合摘要保全并在封存前再次核对，见 [历史保全](../evidence/A03/review/P2-R8-R1-producer/historical-preservation.json)。原 `mermaid-diagram.png` 保留。

## coverage 缺口的关闭依据

[producer](../evidence/A03/review/P2-R8-R1-producer/input/checkout/src/annotation/quality/synthetic_precheck.py) 的 `_pre_coverage_decision` 明确解包 `coverage, complete = coverage_for(...)`，复制检查结果；complete 为 false 时将 coverage 置 FAIL，只有 complete 且全部检查为 PASS 才选择 PASS，否则 HOLD。生产器将 coverage 对象传入 PRE，run resource 和 PRE 使用同一组有效检查结果及 decision。没有改公共 helper 返回值或放宽对象 Schema。

独立逐字段对比 profile/adoption，确认除受影响的 producer pin 和 profile pin 外全部相同；当前六份 Schema 及 23 项 implementation pins 均与实际原文件字节一致。

| 唯一允许产品变更 | target raw SHA256 |
| --- | --- |
| `quality/synthetic_precheck.py` | `f1a212e4b7693362945da1843c14e13264d16f7187b612671bec0b9f4f010aef` |
| native `data/profile.json` | `0bcf724c66206784d8526b3b73b3ef0fde953295dd3ac689379135bde52fee26` |
| native `data/adoption.json` | `480ab1b902639630a9c0172a6178a7d9b07776656242cf918076641ff63d775c` |

冻结 [最小测试源码](../evidence/A03/review/P2-R8-R1-producer/input/checkout/tests/test_a03_r8_r1_minimal.py) 实际调用完整 PGM 比较、公共 helper、producer 私有决策和既有 Coverage schema，不 mock 质量结果。原 stdout 的两个输入均记录实际 PGM SHA256 `1f82898615c67c676c532b17a8bd8e801c73eb6e7e2ba5a7f685bf1c3582cc7a`，与本次原资源吻合：

| 原始输入 | complete | coverage | 检查与决策 |
| --- | --- | --- | --- |
| 完整输入 | true | dict | 五项 PASS，PASS |
| 仅将覆盖线索置 UNASSIGNED 的不完整输入 | false | dict | coverage FAIL，其余四项 PASS，HOLD |

最小检查本身不证明 runtime 接纳；本次另有实际 PRE 原件和 ADMITTED 行，见下文。修复 diff、原最小记录、Schema/pins 及实际失败源码核对均在 [独立静态核对](../evidence/A03/review/P2-R8-R1-producer/static-review.json)。没有重跑该最小测试。

## 实际已到达的持久边界

仅将冻结 runtime/target SQLite 原 blob 复制到自有临时目录，使用标准库 `mode=ro&immutable=1` 与连接级 query_only；未连接执行原库。两库读取前后、副本与原导出的 SHA256 相同，quick_check 均为 ok，临时目录已删除。完整 SQL、选定原始行和计数见 [独立数据库核对](../evidence/A03/review/P2-R8-R1-producer/database-review.json)。

| 冻结库 | raw SHA256 | 关键计数 |
| --- | --- | --- |
| runtime | `8460da84ace3b2d0376ea644b2938f8d0ce7c2f83021cf5d8658fcefa1e75765` | plans/actions/intents/permits/resolutions/native_pre_runs/creation_anchors 各 1；artifacts=14，events=13，native_report_reads=0。 |
| target | `ba44cc6289e6c0166cad309989957684f32cf049146341b76e6b96969e1243d2` | effects=1，observations=3。 |

两库 application_id 分别为 1093678162、1093678164，user_version 均为 4；这里只证明此冻结运行身份，不构成 N7 新库生命周期验收。

[直接产物与字段核对](../evidence/A03/review/P2-R8-R1-producer/boundary-and-binding-review.json) 从 SQL 当前 bundle_path、package_root、Artifact 路径及 Resource 字节重新定位，而非依赖作者汇总布尔值，确认：

- PRE `pre-r8-r1-N1` 的完整 ref hash 为 `104b68c5fd31800e17a0238480b401a8044c7d66cc029c9c7748234684431b84`，coverage 为对象、decision=PASS；五项结果与实际 run resource 一致。其 raw run SHA256 为 `02bd8ce00709dc4c9bec0e78089b33bec22ce23c0c6d28ee2a25871a1700f2f1`，producer 实现 SHA 与最终源文件一致。
- 唯一 native_pre_runs 行为 **ADMITTED**，pre_ref、run_sha 和 accepted_plan 均绑定实际 PRE、运行原件和该计划，已越过上轮 PRE 封签前阻断。
- 真实计划只有一个 CREATE_FRAMES；Prepared 中的 WriteIntent 与 SQL/current bundle 的确切 intent 相同。唯一 permit 为 **CONSUMED**。target 唯一效果的 plan_ref/action_id/action_digest 与该计划和 actions 行逐项相同，mutated=true，来源为合成 SIMULATED。
- 原效果子 PID **36056** exit **87**，真实 AFTER_TARGET_EFFECT_COMMIT marker 的 PID 相同，barrier_released=true。原父脚本在屏障处用独立 target 连接确认 effects=1 后放行，冻结 target 仍为 1。父 PID **56988** 后来 exit **1**，这是后段真实错误，不是预期崩溃成功。
- 原 UNKNOWN progress 仍存在，attempt_fact=MAY_HAVE_BEEN_ATTEMPTED，receipt_ref/result_fact 均 null。之后另一个已持久 progress 为有效 APPLIED，仍是 MAY_HAVE_BEEN_ATTEMPTED，result_fact/receipt_ref 也为 null；其有效结论绑定已提交终局 head。
- 终局 head 为 **RESOLVED_APPLIED**，original_receipt_ref=null；同 intent 的 RECOVERY material fact 已持久化，result.outcome=APPLIED、attempt_fact=MAY_HAVE_BEEN_ATTEMPTED。

这证明实际合成前缀，不等于 N1 完成：plans.status 仍为 **INTERRUPTED**，intent.receipt=null，当前登记包/SQL artifacts 无 ExecutionReceipt，native_report_reads=0，无独立 POST/Batch。reconcile 在后续投影抛错，未正常返回完整链结果。

## P1 剩余缺陷：效果状态被投影为尝试分类

实际原始 [N1 父 stderr](../evidence/A03/review/P2-R8-R1-producer/input/checkout/docs/evidence/A03/execution/P2-R8-R1-producer/runs/N1/stderr.txt) 的失败链是：

`reconcile → NativeRuntimeStore.commit_reconciliation → project_plan → _project_plan_locked → _append → _receipts_progress`

在 [contracts/recovery.py](../evidence/A03/review/P2-R8-R1-producer/input/checkout/src/annotation/contracts/recovery.py) 第 **663** 行报 `$.progress: RECOVERY_CHAIN_INVALID: progress fact/action/attempt differs`。该守卫同时比较 plan_ref、action_id、attempt_fact、intent_ref，不能只凭异常文字认定是哪一项不同。

此次从实际保存的行和原件取得身份如下：

| 身份 | 已保存实际值 |
| --- | --- |
| plan ref | `plan-r8-r1-n1` / revision 1 / ApplyPlan / `4d72f3e37cb94a1fe3a69f1f3ed2dce1321cf8f7cb8c0733e3e854184b630c65` |
| plans.id = actions.plan = intents.plan | `fdb845e8ed02016c16302fcce064cd19d5a63ba29cc1a052a3d49e8372055d58`；独立重算为该完整 plan ref 的 canonical SHA256。 |
| action_id | `action-a02-ed35e8b58ec2c814f28402e742c19299` |
| action_digest | `232d7bd293a7b9d76749182420c8c6d7783af008a81362b96f7b675e8af9c3a0` |
| actions.intent = intents.id | `intent-64fed260b0494869a09ed95b2fce3db1` |
| intent ref | `writeintent-ad781d79747d4fb09f14c351206b8bf0` / revision 1 / WriteIntent / `ed09d9e5f450571c70d27a00980e2b68d162251b6359a77c2594ad392a6d7697` |
| terminal head ref | `resolution-f28027ba9bac41b68c203064915fb437` / revision 1 / ReconciliationResult / `bde0d3109f0685532f1c97ae2aa618a9d9b386ed662e73cb33091b13004d3322` |
| material fact raw SHA256 | `4e5473dd5ab4a21cd05ce7d62b45f92165015efd3749a9bb936539a63f3db375` |

三个关键源文件与实际 N1 快照及最终源一致，且相对 base 未修改：

- [storage/native.py](../evidence/A03/review/P2-R8-R1-producer/input/checkout/src/annotation/runtime/storage/native.py) 第 **273** 行为晚到 RECOVERY fact 保留 MAY_HAVE_BEEN_ATTEMPTED；第 **283–284** 行将同一 action 的 fact 和 state=APPLIED 提交；第 285 行再发起 project_plan。
- [storage/__init__.py](../evidence/A03/review/P2-R8-R1-producer/input/checkout/src/annotation/runtime/storage/__init__.py) 第 **799** 行：有 intent 且 state 不属于 INTENT/UNKNOWN 时，attempt_fact 选择 ATTEMPTED。保存行恰为 intent 非空、state=APPLIED，因此该分支的值确定为 ATTEMPTED。
- 合同第 663 行要求 progress 与不可变 material fact 的四项一致。此例逐项独立比较结果为：

| 比较项 | 保存的 material fact | 失败投影分支确定的值 | 不同 |
| --- | --- | --- | --- |
| plan_ref | 上述完整 ApplyPlan 四元组 | 同一 plans.ref | 否 |
| action_id | 上述 action_id | 同一 actions.id | 否 |
| intent_ref | 上述完整 WriteIntent 四元组 | 同一 actions.intent 对应 intents.ref | 否 |
| attempt_fact | MAY_HAVE_BEEN_ATTEMPTED | ATTEMPTED | **是** |

右列 ATTEMPTED 是由保存行与实际冻结源码分支作出的静态推断，**不是读到了已存在的失败 progress Artifact**。本轮只记录这四个比较字段，没有构造或封签新 progress、没有调用投影函数。

## 提交、回滚和文件残留的区别

终局 head 先由正常只读对账提交；随后 native 的独立事务已提交 material fact 和 action.state=APPLIED。新的 project_plan 事务尝试追加 receipt/progress，native `_append` 在调用上层持久化前验证新 bundle，progress 在四项守卫处失败。`transaction` 对 BaseException 执行 rollback，因此这个投影事务未完成。

从当前 SQL artifacts 与当前登记包逐项比较，均只有原先 14 个 Artifact，无新的 receipt 或失败 progress。两个真实持久 progress 的 ref 分别为：

- `executionprogress-8ecc5056ff834b2985bab57c9d41d13d`，hash `11a822ad78b5b954f64aff99c23ba00b347ce77e710c2576b8b37fb249ab0284`，有效 UNKNOWN。
- `executionprogress-e1cf78da009d4dcfbec9f179e743351f`，hash `2aa642cca7e5e147aa8ebab96c2933d9b35064001f785f4164c289131c524006`，有效 APPLIED。

扫描本次冻结对象和包文件中的 progress，唯一 ref 集合仍是这两个，均无 result_fact；没有新增失败 progress 文件。原 UNKNOWN 未删除、未覆盖。

文件系统确有**同一个**候选 ExecutionReceipt 的两处残留：独立 object 文件及非当前 bundle 文件；候选 ref 为 `executionreceipt-d94ccbda67b1454cbf914f5ef200bc20`，hash `53bef60c302ffd7618c2a268baae6077b85bdc5466e090c01a1a8b68157d0b7f`。这两处都不在当前登记包或 SQL artifacts 中，intent.receipt 仍 null。SQLite 回滚不撤回已写普通文件，故不能把文件存在算作正式完整回执。原文件只读保留，没有清理、移入当前包或补造接纳。

完整 creation-input anchor 已存在，保存输入 raw SHA 与 anchor 行相同，包含 7 个 Artifact 和 6 项资源清单。本报告只核对原保存数据，没有在 UNKNOWN 历史下重算计划；N6 仍未验收。

## 最终候选兼容与过程核对

[独立进程核对](../evidence/A03/review/P2-R8-R1-producer/process-review.json) 覆盖 23 个原进程的 preregistered/started/completed、argv/cwd、脚本/输入与产品摘要、限时、原 stdout/stderr、PID、退出与 timeout/alive；有原日志摘要的逐项比对，其余日志由 raw manifest 和独立摘要绑定。全部历史记录均已 wait/退出，无 timeout/alive；未扫描当前 OS 或 profile。

minimal、N1、C01、A02、R7 的 product-source-index 原字节完全相同，SHA256 为 `376e37bcc60f1e5fc3a2c62bd920d158e497a36b5d3961db0c5c49ea40e630c7`；逐组另核对 producer/profile/adoption、公共 helper 和三个守卫 runtime/contract 文件的实际快照与最终源身份。

三组兼容原 stderr 分别是 C01 **70**、A02 **52**、R7 **13** 项，均 OK、无失败或 skip，绑定本次最终 producer 修复候选。C01 的三个非零子进程均是主动缺失引用的预期 CLI 拒绝，原 JSON stderr 为 valid=false/MISSING_REFERENCE，符合旧测试非零与定位断言；没有混记为兼容失败。N1 子进程 87 为预期效果后崩溃，N1 父进程 1/ERROR 则是真实新阻断。

这些回归记录支持对应旧入口兼容，不能代替 N1 完整恢复链、N2–N7 或整个 A03 功能验收。本轮没有重新运行任何一组。

## 下一次最小产品修复边界

应由下一份明确任务限定 `runtime/storage/__init__.py::_project_plan_locked` 的尝试分类来源，并按必要性协调 `runtime/storage/native.py::commit_reconciliation` 的投影衔接及相应 implementation/profile/adoption pins。当前 producer 修正范围只有三个旧产品文件，不能在本轮继续修改这些 runtime 路径。

对已有确切 material fact 的 action，progress 的 attempt_fact 应与原 fact 和尝试证据一致；不能仅凭 action.state=APPLIED 推断为 ATTEMPTED。保留 fact 中的 MAY_HAVE_BEEN_ATTEMPTED、原 UNKNOWN、终局 head、original_receipt_ref=null 和精确 plan/action/intent 关联；不把 material fact 改成 ATTEMPTED、不放宽四项守卫、不改 Schema 或削减历史来消除异常。

新冻结返工须证明该同一投影路径能够形成一致、正式持久的 receipt/progress，区分当前登记与文件残留，再证明独立 POST/Batch 及原 N1 其余标准。任何必要实际验证须按新任务使用新的合成运行，不继续使用本轮失败库重放效果；不得把一次效果变成重发授权。本次没有执行上述修复或验证，也不预判修完此字段后整个 A03 会通过。

N2–N7 均保持 `NOT_RUN_AFTER_NEW_INDEPENDENT_PRODUCT_BLOCKER`；原 P2 V01–V10/R01–R18 未被豁免。R7 原 ACCEPTED 只读边界与 R8/R8-R1 的 REWORK 分开保留，跨侧合同未共同确认，I01 继续关闭。字段重置专项保持 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`，不复跑、变形、委派或建议重测。

## 封存

只新增本报告和 `docs/evidence/A03/review/P2-R8-R1-producer/`，保留独立脚本/输入/原输出、自有进程限时与退出及完整摘要清单。见 [自有进程释放](../evidence/A03/review/P2-R8-R1-producer/process-release.json)、[最终核对](../evidence/A03/review/P2-R8-R1-producer/final-verification.json)、[完整 SHA256 清单](../evidence/A03/review/P2-R8-R1-producer/sha256-manifest.json)，只排除清单自身；封存后重新核对完整目录集合和各文件字节。

未委派、未联系 B/执行者，未改变用户 model/thinking、执行工作树、旧证据或调度 state；零网络、浏览器、真实平台、凭据/profile、OCR、模型、安装、付费 API、A05 题22重放、提交或推送。未自记 INTEGRATED。最终结论是**仅原 coverage 缺口关闭，R8-R1 整体 REWORK，I01 不释放**。
