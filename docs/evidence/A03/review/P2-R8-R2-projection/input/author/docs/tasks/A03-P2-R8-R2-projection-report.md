# A03 P2-R8-R2 恢复进度投影交付

状态：**REVIEW；已确认的投影缺口经完整 N1 验证，N2 遇到新的 POST_HOLD 准入阻断，整体 A03 尚未通过**。按本轮停止条件冻结，没有追加第二项产品修复或重跑失败组。I01 未释放。

## 身份与唯一修复

2026-10-18（Asia/Shanghai）。工作树 `C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800`，分支 `codex/a03-runtime-recovery`。唯一 base `a0c40886f3076f84c46377e03fc2206d2fdc5585`，workflow `016e048669e5af1f193e71968d03bf3000cf16d1`。产品及测试/辅助源码提交 `002c26795822fe8518117793f59598b3eceab02e`；报告、证据随后提交，最终交付 tip 在交付消息给出。

[确切任务](../evidence/A03/execution/P2-R8-R2-projection/inputs/A03-P2-R8-R2-projection-rework.md) SHA256 `c76ef2a47fa9bbfecb83b05e02cfe56a6599c68600786d2a86eb9547c35fb3e0`；[R8-R1 独立报告](../evidence/A03/execution/P2-R8-R2-projection/inputs/A03-P2-R8-R1-producer-review-report.md) SHA256 `37ad11cbecefcfc97c2c1487786f66418bd231c79e7b7654bd9d6c7a8fbf9cbf`；[调度收口原件](../evidence/A03/execution/P2-R8-R2-projection/inputs/A03-P2-R8-R1-producer-coordinator-decision.md) 及三份 base 产品输入的长度和 raw SHA256 均在 [inputs.json](../evidence/A03/execution/P2-R8-R2-projection/inputs.json)。没有合浮动主树、委派或更改用户的 model/thinking。

产品仅修改 `runtime/storage/__init__.py::_project_plan_locked` 及同文件私有 `_progress_attempt`，另更新对应 implementation/profile/adoption pins。没有修改 native `commit_reconciliation`，因为原 fact 无需改变：

- 有 material fact 时，先核对完整 plan_ref、action_id/action_digest、外层和 result 内的 intent_ref/action_id，然后使用原 fact.result 的 attempt_fact 与 attempt_evidence_refs；返回证据副本。
- 无 material fact 时，保留原 NOT_ATTEMPTED / MAY_HAVE_BEEN_ATTEMPTED / ATTEMPTED 推导及空尝试证据。
- 效果结论继续使用既有 resolution/action 状态；没有将 APPLIED 转写为历史尝试分类，没有修改 fact、原 UNKNOWN、终局 head、null original_receipt_ref 或四项合同守卫。

公共 helper、Schema、版本/API/角色语义、producer、算法、根依赖和旧文件原件均不变。新的两库/目录与 book/source/scope/registration/session 身份均为 R2，未使用 R8-R1 失败库或候选文件作为新链前缀。

| 更新文件 | raw SHA256 |
|---|---|
| storage 实现 | `93cb82da040346cfba95a312f3615b8bfc5c47edee01ba69584ac338882cfa3a` |
| native profile | `46dba6f9c33d84daa8149a77afbe86952fc08ff835ed180828d7ab307cdd9d47` |
| native adoption | `a1c8b6e1f85a603b107163d618985b127c9157050b1977f4fd626f7021eec760` |

profile 仅上述 storage implementation pin 改变，adoption 僅 profile SHA 改变；其他全部 pins 保持原值。产品从实际 `src/annotation` 正常导入，实际路径见 [before-dispatch](../evidence/A03/execution/P2-R8-R2-projection/validation/native-r2-01/cases/N1/before-dispatch.json)，不通过 examples/docs/Git 或 AST/exec 运行产品。

## 小检查与完整 N1

[最小检查](../evidence/A03/execution/P2-R8-R2-projection/runs/minimal/stdout.txt) 只检查私有纯值投影分支：APPLIED 行有 material fact 时保留 MAY_HAVE_BEEN_ATTEMPTED 和原证据；证据返回副本；无 fact 的 pending/reserved 分支保持原语义；错绑 intent 明确拒绝。没有造 SQL 行或成功接纳，这项检查不是效果证明。

N1 真正执行一次，父 PID `57904` exit **0**，约 27.424 秒，原 [stderr](../evidence/A03/execution/P2-R8-R2-projection/runs/N1/stderr.txt) 为 OK。效果子 PID `13392` exit **87**、barrier_released=true，无 timeout/alive；父进程在真实效果提交后的屏障处独立查询 effects=1 后放行。PRE、TARGET、计划、PreparedAction、intent/permit 均来自正常产品链。

[N1 原结果](../evidence/A03/execution/P2-R8-R2-projection/validation/native-r2-01/N1-result.json) 和 [冻结 SQL/资源回看](../evidence/A03/execution/P2-R8-R2-projection/database-readback.json) 相互印证：

| N1 标准 | 实际边界 |
|---|---|
| 真实资源与 PRE | 五检查、PRE 封签及 durable ADMITTED；完整 INITIAL context |
| 真 TARGET / create_plan | 单个 CREATE_FRAMES，完整创建锚点已记录 |
| 真 prepare / intent / permit | 实际会话签发；唯一 permit 为 CONSUMED |
| 效果后崩溃 | 实际子进程、明确屏障、预期 exit87；效果恰好 **1** |
| 原 UNKNOWN / 原回执缺失 | 初始真实 progress 为 UNKNOWN，receipt_ref=null；原件仍保留 |
| 只读对账 | reconcile 正常返回 RESOLVED_APPLIED；终局 head.original_receipt_ref=null 保持 |
| 晚到正式 receipt/progress | SQL artifacts、当前登记包、intent.receipt 完整四元组一致；两个 material progress 的 plan/action/intent/attempt 及尝试证据均与同一个原 fact 一致 |
| 独立 POST/Batch | 新的实际报告读、正式 POST 与 Batch 均已登记；frame_structure=PASS，content_check_status=PENDING，submission_status=NOT_SUBMITTED |
| 无重发 | 当前目标 effects 仍为 1；未自动重发、未重写原 UNKNOWN 或终局 head |

关键正式引用如下，均 revision=1；kind 和 content_hash 见原结果完整四元组：

| 产物 | artifact_id / content_hash |
|---|---|
| plan | `plan-r8-r2-n1` / `e0581a174480ec5c1c0eefc3d0ab53cc2d95bac95e14d746429f6f857555b8d6` |
| receipt | `executionreceipt-376adae14660420cac6f962a2a08eef6` / `59e66571edc2f2392ea2bb5118c466f871ecd2e04ed6bb9d6bd024e7ec0c6238` |
| terminal head | `resolution-996874d48b7f42cbbb8ef48a9e05a806` / `6d7ba5258af1a2b808214aa08c8e48aced6afb176e937d1c02ab133c25b31ebe` |
| POST | `native-post-02920f2cc62b45c2af88d0271d19b32f` / `a60326ab77e6512b9bb140e98a0933c0a82aba9d6efe1925d51f77264734bd89` |
| Batch | `native-batch-066ebc803be4422ab51fb3f4d5025dd7` / `5492238b1222893e3e86a1e21954919ea6d1aeac95d200aee81a0b093bb7dd84` |

正式 material progress 为 `executionprogress-8713940545f249c09643dbc8c3312850`（hash `bb9ce17b3b5760b91d7d5348e399e557cc3c9ae921d8903f05f1254f2e86f15a`）与后续报告前投影 `executionprogress-f59314f6b47f4074aadb9b0cd185fb99`（hash `38a57cc1138a0f787cb63abcf37d3f2837d0ed79e03be0bc35834e106139ea16`）。回看分别核对 SQL ref、当前包、fact、receipt 及尝试证据，没有把文件存在当作正式提交。

N1 已验证的正式 receipt 在 intent.receipt 中、SQL artifacts 中且在当前登记包中；文件系统其他历史 bundle/object 的同 ref 副本只是这同一份正式产物。R1 那种只有未登记候选文件的失败没有被当成这次成功依据。

## N2 新阻断及冻结边界

N1 完成后只执行一次 N2。正常受控合成目录变更后，detect_target_drift 产生真实 hold：`target-drift-hold-347994b72519469fa107efe6d613fa22`；原 hold 事件与 books.hold 一致。没有字段重置或题目效果重放。旧 INITIAL 证明的拒绝断言已经过，随后 POST_HOLD 正例未能启动。

父 PID `54044` exit **1**，约 3.076 秒，原 [N2 stderr](../evidence/A03/execution/P2-R8-R2-projection/runs/N2/stderr.txt) 的真实失败链为：

`test_N2 -> begin_native_pre(kind='POST_HOLD') -> _lease -> TARGET_DRIFT_HOLD`。

[独立位置与保存状态](../evidence/A03/execution/P2-R8-R2-projection/post-hold-blocker.json) 明确：

- `runtime/storage/native.py:318` 在区分 INITIAL/POST_HOLD 之前调用 `_lease(connection, book, owner, generation)`，未给其他选项。
- `_lease` 的既有默认是 `pending_ok=False`；`runtime/storage/__init__.py:346–347` 对非空 row.hold 直接拒绝，异常字符串正是上述实际 hold id。
- `native.py:319–320` 的 POST_HOLD context 条件尚未到达；没有新的 POST_HOLD run 行、检查、接纳或 hold 清除。

这不是新的 attempt 投影不一致，也不是记录脚本误判。新的产品缺口位于 POST_HOLD PRE 与普通写入 lease/hold 守卫的接口衔接，超出本轮 `_project_plan_locked`/必要投影辅助及可选 `commit_reconciliation` 配套的范围；没有修改 `_lease`、begin_native_pre 或放宽当前写入守卫，没有第二项产品修复。

| 组 | 本轮最终结果 |
|---|---|
| N1 | 完整真实合成链完成；包含本轮新增正式登记及 provenance 直接断言 |
| N2 | 真实 hold 已产生，POST_HOLD run 前被默认 lease hold 守卫阻断 |
| N3–N7 | `NOT_RUN_AFTER_NEW_INDEPENDENT_PRODUCT_BLOCKER`，未用旧结果或候选测试源码顶替 |

回看时唯一 INITIAL run 仍 ADMITTED，POST_HOLD run 数为 0；plans.status=FINISHED、唯一 permit CONSUMED、native_report_reads=1、current formal receipt=1，当前 book 由 N2 正常 finally 释放为 RELEASED/owner=null/generation=4，但 hold 原样保留。当前 hold 不意味着可以继续写入或沿用历史 proof。N6 的 UNKNOWN 历史下锚点重算、其他原 N2–N7 标准尚未取得本轮成功证据。

## 数据、兼容与原始过程

冻结回看使用 `mode=ro&immutable=1` 和连接级 query_only，读取前后两库 raw SHA256 不变；没有调用产品、修复行或补做接纳。

| 库 | raw SHA256 / 记录边界 |
|---|---|
| runtime | `0f32ca20b0a2cf9b7a66c434994c845e921d5a5701d20ea6265a3ca95b4915ea`；plans/actions/intents/permits/resolutions/pre_runs/creation_anchors/report_reads 各 1，artifacts=21，events=20 |
| target | `9ee1fb878a0b65bed21b893ff242072d8d0775671518d9dae4810070cce4b25e`；效果一次，包含 N1 与 N2 正常观察的完整历史 |

最终候选 C01 `test_contracts*.py` **70** 项、A02 `test_a02*.py` **52** 项、R7 `test_a03_r7_readonly_codec.py` **13** 项各一轮，原 stderr 均 OK。minimal、N1、N2 和三组兼容的实际 product-source-index 相同，绑定本轮最终 storage/profile/adoption；没有沿用旧候选的回归结果。

实际 argv 的 cwd 均为上述 worktree，以下只记录本轮已执行命令：

```powershell
python -X utf8 -B examples/a03/P2-R8-R2-projection/audit_a03_r8_r2.py run minimal python -X utf8 -B tests/test_a03_r8_r2_projection_minimal.py -v
python -X utf8 -B examples/a03/P2-R8-R2-projection/audit_a03_r8_r2.py run N1 python -X utf8 -B tests/test_a03_r8_r2_projection.py R8R2NativeBridgeTests.test_N1 -v
python -X utf8 -B examples/a03/P2-R8-R2-projection/audit_a03_r8_r2.py run N2 python -X utf8 -B tests/test_a03_r8_r2_projection.py R8R2NativeBridgeTests.test_N2 -v
python -B examples/a03/P2-R8-R2-projection/audit_a03_r8_r2.py run C01 python -B examples/a03/P2-R8-R2-projection/compat_a03_r8_r2.py C01 test_contracts*.py
python -X utf8 -B examples/a03/P2-R8-R2-projection/audit_a03_r8_r2.py run A02 python -X utf8 -B examples/a03/P2-R8-R2-projection/compat_a03_r8_r2.py A02 test_a02*.py
python -X utf8 -B examples/a03/P2-R8-R2-projection/audit_a03_r8_r2.py run R7 python -X utf8 -B examples/a03/P2-R8-R2-projection/compat_a03_r8_r2.py R7 test_a03_r7_readonly_codec.py
```

产品/测试及已登记证据进程的原 argv/cwd、脚本/输入摘要、源码快照、PID、限时、raw stdout/stderr、退出/timeout/alive 均保留，见 [进程释放记录](../evidence/A03/execution/P2-R8-R2-projection/process-release.json)。N1 子 exit87 是预期效果后退出，N1 父 exit0 是完整链成功，N2 父 exit1 是独立产品失败；C01 的预期 CLI 拒绝子进程不混记为回归失败。

另有一次**文件封存辅助生成命令**在 PowerShell 引号传递处 SyntaxError，未创建目标文件或运行产品。[失败记录与证据限制](../evidence/A03/execution/P2-R8-R2-projection/preparation-command-failure.json) 保留工具 chunk id、exit1 和明确标注的错误转录摘录；该已完成的直接 exec 响应未提供 PID 或分流原始 stdout/stderr，不能把转录冒充 raw 进程日志。随后通过单独、预登记的 prepare_sealer 脚本生成文件辅助，原输出保留。没有以此重跑 N2 或任何已失败产品路径。

[旧字节保全](../evidence/A03/execution/P2-R8-R2-projection/preservation.json) 按 raw Git mode/type/blob 比较：base 29,706 项中，除允许的三个旧路径外，29,703 项保持原样，包含 R7、R8、R8-R1 原证据/失败/测试/报告。没有复制历史全集。最终 `manifest.json` 覆盖本轮所有修改/新增源码、输入、报告、过程日志、两库及实际链产物，只排除清单自身；索引原始 blob 再逐项核对，工作树干净后交 REVIEW。

本次没有委派、推送、修改根 state/AGENTS、联系 B/验收者、更改 model/thinking，零网络、浏览器、真实平台、凭据/profile、OCR、模型、付费 API、A05 题22重放或书级提交。N1 不替代原 P2 V01–V10/R01–R18；跨侧映射仍待双方确认，I01 继续关闭。字段重置专项仍为 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`，没有复跑、变形、委派或重测建议。
