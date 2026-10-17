# A03 P2-R8-R1 producer 有界修复交付

状态：**REVIEW，producer 缺口已修，N1 仍因新的 runtime 阻断未完成**。没有自行接受 A03、集成或释放 I01。当前不能给出可靠完工时间：本轮已到达终局只读对账及晚到 material fact，剩余首个问题已定位到 progress 的尝试分类；其修复与剩余验证尚未获本轮授权。

## 确切身份与修改范围

工作树 `C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800`，分支 `codex/a03-runtime-recovery`；唯一 base `fa6edeb7e9dd0c9502781747e5fce012931d9441`，workflow `b9889efd29baa364bdd0ce9e356a8cde7054f8d9`。产品与本轮测试/辅助源码提交 `613952f170167551b6f935d93cc9f007e6aa7221`；随后仅补充文件封存辅助、报告与证据，最终交付 tip 在交付消息中给出。

[固定任务原字节](../evidence/A03/execution/P2-R8-R1-producer/inputs/A03-P2-R8-R1-producer-rework.md) SHA256 `bc0063986d164bd0ca7caeddfb2ed358439fd14e3d9d80961f2f5c85f932ad7b`；[R8 独立报告原字节](../evidence/A03/execution/P2-R8-R1-producer/inputs/A03-P2-R8-native-bridge-review-report.md) SHA256 `66690c0e259635d770cc44d2265b979e813c7e72494c1cf9b87257ed5c8e5555`。[输入索引](../evidence/A03/execution/P2-R8-R1-producer/inputs.json) 记录 task/review/base 源文件摘要和原 tree 摘要。

旧产品路径仅修改三项：`quality/synthetic_precheck.py`，native `data/profile.json` 中的 producer implementation pin，以及 `data/adoption.json` 中的 profile SHA。公共 `coverage_for`、Schema、旧 API、R7、runtime、之前的整数/浮点投影修复、根依赖与全部旧失败/报告/测试/驱动均未改。新驱动/测试/夹具在独立 R1 命名空间，N1 使用新书籍/来源/作用域/登记/目标会话身份和新双库目录，没有复用旧失败库或历史成功前缀。

producer 通过私有 `_pre_coverage_decision` 显式解包公共 helper 的 `(coverage, complete)`：PRE 仅接收 coverage 对象，`complete=false` 保留为 coverage FAIL 和 HOLD；完整且五检查均 PASS 才选择 PASS。run resource 与 PRE 使用同一组有效检查结果，质量结果仍需真实 runtime 行及私有接纳。

更新后的 exact pins：

| 文件 | raw SHA256 |
|---|---|
| producer | `f1a212e4b7693362945da1843c14e13264d16f7187b612671bec0b9f4f010aef` |
| native profile | `0bcf724c66206784d8526b3b73b3ef0fde953295dd3ac689379135bde52fee26` |
| native adoption | `480ab1b902639630a9c0172a6178a7d9b07776656242cf918076641ff63d775c` |

其他 schema/API/interface/oracle/verifier/implementation pins 保持原值。产品正常导入 `src/annotation`，真实子进程的 `before-dispatch.json` 记录其实际导入目录；不依赖 examples/docs/Git 或 AST/exec 执行产品。

## 本轮实际验证

[最小检查 stdout](../evidence/A03/execution/P2-R8-R1-producer/runs/minimal/stdout.txt) 与 [stderr](../evidence/A03/execution/P2-R8-R1-producer/runs/minimal/stderr.txt) 显示一项测试中的两个输入均按实际 PGM 资源读取并比较：完整输入 coverage 为 dict、complete=true、五项 PASS、决策 PASS；只改变覆盖线索为 UNASSIGNED 的不完整输入 complete=false、coverage FAIL、其余四项 PASS、决策 HOLD。coverage 对象经过既有 Coverage schema；没有 mock 质量比较或伪造成功数据库行。这项最小检查不自行声明 PRE 接纳。

然后只执行了一次真实 N1，耗时约 24 秒。父 PID `56988` 最终 exit `1`；真实效果子进程 PID `36056` exit `87`，`barrier_released=true`，无 timeout/alive。[原始父 stderr](../evidence/A03/execution/P2-R8-R1-producer/runs/N1/stderr.txt) 和 [效果子进程完成记录](../evidence/A03/execution/P2-R8-R1-producer/validation/native-r1-01/processes/n1-child/completed.json) 原字节保留。

| 边界 | 实际结果 |
|---|---|
| INITIAL 五检查、PRE 封签 | 到达，coverage 为对象、decision=PASS |
| runtime 真实 PRE 接纳 | durable row 为 ADMITTED，pre_ref/run_sha/accepted_plan 均有确切绑定 |
| 真 TARGET / create_plan | 到达，单个 CREATE_FRAMES |
| 实际 PreparedAction、intent、单次 permit | 到达，唯一 permit 已消耗 |
| 目标效果、屏障、效果后崩溃 | 到达；屏障处父进程独立读 effects=1 后放行退出，冻结回看仍为 **1** |
| 原 UNKNOWN | 原始 progress 保留 UNKNOWN、MAY_HAVE_BEEN_ATTEMPTED，receipt_ref=null |
| 只读对账终局 head | 已提交 RESOLVED_APPLIED，original_receipt_ref=null |
| 晚到 material fact | 已持久化 RECOVERY/APPLIED，绑定同 plan/action/intent/head |
| 晚到完整 receipt / 新 progress | 新投影在合同守卫处失败，事务未完成；当前登记包没有 receipt，intent.receipt 仍 null |
| 独立 POST/Batch | 未到达，没有报告读或成功报告 |
| N2–N7 | `NOT_RUN_AFTER_NEW_INDEPENDENT_PRODUCT_BLOCKER` |

原 creation-input anchor 已记录完整创建包、输入 SHA 及 Resource 清单；准备时走过原生成算法的锚点核验。N1 后完整 UNKNOWN 历史下的 N6 重算未执行，不能提前接受 N6。目标内容/人工提交验收未发生。

## 新阻断的确切字段对照

实际失败为 `reconcile -> NativeRuntimeStore.commit_reconciliation -> project_plan -> _project_plan_locked -> _append -> _receipts_progress`，最后在 `contracts/recovery.py:663` 报 `$.progress: RECOVERY_CHAIN_INVALID: progress fact/action/attempt differs`。没有重跑或修复该产品路径。

[冻结数据库回看](../evidence/A03/execution/P2-R8-R1-producer/database-readback.json) 使用标准库 `mode=ro&immutable=1`、连接级 query_only；runtime/target 读前后 raw SHA256 不变。[字段绑定核对](../evidence/A03/execution/P2-R8-R1-producer/attempt-field-binding.json) 只比较已经保存的数据与实际执行的源码快照，没有调用 native API、重建/封签失败 progress 或新增测试。

这一例的身份如下：

| 字段 | 实际值 |
|---|---|
| plan Artifact | `plan-r8-r1-n1`, revision=1, kind=ApplyPlan, hash=`4d72f3e37cb94a1fe3a69f1f3ed2dce1321cf8f7cb8c0733e3e854184b630c65` |
| plans.id / actions.plan / intents.plan | `fdb845e8ed02016c16302fcce064cd19d5a63ba29cc1a052a3d49e8372055d58` |
| action_id | `action-a02-ed35e8b58ec2c814f28402e742c19299` |
| action_digest | `232d7bd293a7b9d76749182420c8c6d7783af008a81362b96f7b675e8af9c3a0` |
| intents.id / actions.intent | `intent-64fed260b0494869a09ed95b2fce3db1` |
| intent Artifact | `writeintent-ad781d79747d4fb09f14c351206b8bf0`, revision=1, kind=WriteIntent, hash=`ed09d9e5f450571c70d27a00980e2b68d162251b6359a77c2594ad392a6d7697` |
| terminal head | `resolution-f28027ba9bac41b68c203064915fb437`, hash=`bde0d3109f0685532f1c97ae2aa618a9d9b386ed662e73cb33091b13004d3322` |
| material fact resource SHA256 | `4e5473dd5ab4a21cd05ce7d62b45f92165015efd3749a9bb936539a63f3db375` |

guard 中四个不等式逐一核对：

| 守卫项 | material fact | 被拒绝投影所取值 | 是否不同 |
|---|---|---|---|
| plan_ref | 上述完整 ApplyPlan 四元组 | 同一 plans.ref / 原计划 | 否 |
| action_id | 上述 action_id | 同一 actions.id | 否 |
| intent_ref | 上述完整 WriteIntent 四元组 | 同一 actions.intent 对应 intents.ref | 否 |
| attempt_fact | `MAY_HAVE_BEEN_ATTEMPTED` | `ATTEMPTED` | **是** |

差异确实属于保存的本次失败。`runtime/storage/native.py:273` 在 RECOVERY material fact 中保留 `MAY_HAVE_BEEN_ATTEMPTED`；`:283–284` 已把同一个 action row 的 state 更新为 `APPLIED`。`runtime/storage/__init__.py:799` 对有 intent 且 state 不属于 INTENT/UNKNOWN 的该行选择 `ATTEMPTED`。这三个 runtime 文件及合同文件均与 N1 实际执行快照相同，且本轮未修改。

被拒绝的新 progress 没有持久化，表中该格的 ATTEMPTED 是由已保存 APPLIED row 和冻结源码唯一分支确定的值，不冒称读到了失败 progress 文件。实际 trace 正是在相同的四项 guard 失败；其余三项完全一致，仅 attempt_fact 不一致。

仍已持久化的两个 progress 分别为：`executionprogress-8ecc5056ff834b2985bab57c9d41d13d` 的 effective_outcome=UNKNOWN，以及 `executionprogress-e1cf78da009d4dcfbec9f179e743351f` 的 effective_outcome=APPLIED；两者 attempt_fact 均为 MAY_HAVE_BEEN_ATTEMPTED，result_fact/receipt_ref 均 null。没有删除或覆盖原 UNKNOWN。

当前登记 bundle 的 ExecutionReceipt 数为 **0**，intent.receipt=null。文件系统留有一个包含候选完整 receipt 的非当前 bundle 文件，是失败事务写出的残留；它不在当前登记包中，不能据此称 receipt 已正式完成。独立 POST/Batch 尚未到达。

本轮任务明确要求“若出现新的独立产品阻断，保留最短实际失败和冻结交付，不自行修第二个问题”。上述缺口位于 `runtime/storage/__init__.py` 与 `runtime/storage/native.py` 的投影/恢复衔接，超出本轮仅 producer 和受影响 pins 的范围，因此没有修改这两个路径、放宽 guard 或继续产品运行。

## 最终候选兼容与实际命令

C01 `test_contracts*.py` **70 项通过**，A02 `test_a02*.py` **52 项通过**，R7 `test_a03_r7_readonly_codec.py` **13 项通过**，各一轮。minimal、N1 与这三组的 product-source-index 完全相同，均为本次 producer/pins 修复后的候选，未沿用上轮修复前结果。

实际命令的 cwd 均为上述 worktree；这是已执行 argv，不在本轮再次运行：

```powershell
python -X utf8 -B examples/a03/P2-R8-R1-producer/audit_a03_r8_r1.py run minimal python -X utf8 -B tests/test_a03_r8_r1_minimal.py -v
python -X utf8 -B examples/a03/P2-R8-R1-producer/audit_a03_r8_r1.py run N1 python -X utf8 -B tests/test_a03_r8_r1_producer.py R8R1NativeBridgeTests.test_N1 -v
python -B examples/a03/P2-R8-R1-producer/audit_a03_r8_r1.py run C01 python -B examples/a03/P2-R8-R1-producer/compat_a03_r8_r1.py C01 test_contracts*.py
python -X utf8 -B examples/a03/P2-R8-R1-producer/audit_a03_r8_r1.py run A02 python -X utf8 -B examples/a03/P2-R8-R1-producer/compat_a03_r8_r1.py A02 test_a02*.py
python -X utf8 -B examples/a03/P2-R8-R1-producer/audit_a03_r8_r1.py run R7 python -X utf8 -B examples/a03/P2-R8-R1-producer/compat_a03_r8_r1.py R7 test_a03_r7_readonly_codec.py
```

每个实际验证父/子进程保留 preregistration、输入/脚本及产品源码摘要、argv/cwd、限时、原 stdout/stderr、PID、退出/timeout/alive。N1 子进程 87 是预期效果后退出；父进程 1 是新的真实产品失败。旧兼容测试中预期拒绝的非零子进程不能混记为兼容失败。[进程释放记录](../evidence/A03/execution/P2-R8-R1-producer/process-release.json) 在所有这些自有进程已 wait/退出后生成；停止后只进行了读取保存证据与文件审计，没有产品重跑。

[旧内容保全](../evidence/A03/execution/P2-R8-R1-producer/preservation.json) 与最终文件审计按 raw Git mode/type/blob 核对 base 旧内容，只有允许的三个旧路径改变；R7、旧 R8 证据和所有原始失败保留。`manifest.json` 覆盖本轮源码、输入、报告、日志、两库与实际链产物，仅排除清单自身；最终索引原始 blob 再逐项核对，工作树干净后交 REVIEW。

本轮没有委派、合浮动主树、更改用户 model/thinking、网络、浏览器、真实平台、凭据/profile、OCR、模型、付费 API、A05 题22重放、书级提交、push、B/验收者消息或调度 state 修改。原 P2 V01–V10/R01–R18 没有豁免，B 跨侧映射未因此确认，I01 继续关闭。字段重置专项保持 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`，没有变体、重跑、委派或重测建议。
