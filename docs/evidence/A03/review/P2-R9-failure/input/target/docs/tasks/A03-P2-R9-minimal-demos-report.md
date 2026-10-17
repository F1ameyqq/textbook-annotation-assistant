# A03 P2-R9 最小演示执行交付

2026-10-18（Asia/Shanghai）。状态：**REVIEW_FIRST_D1_OWNER_BUSY_FAILURE**。D1 首轮在正常动作/回执已提交后、native POST/Batch 发布前失败。已依任务停止：不修产品、不改驱动到成功、不重跑、不执行 D1 重启/重复保护或 D2。A03 整体仍未验收，I01 未释放。

## 固定身份与改动范围

- 唯一 base/产品版本：`435aaee2d140e82d3237ce8902d594a1aee70aad`。接单时 HEAD 精确一致，tracked/untracked 状态干净。
- workflow：`11300250bef18d4bdf7220111cf82232c7d5e0f3`；派发键：`A03:execution:P2-R9-minimal-demos:435aaee2d140e82d3237ce8902d594a1aee70aad`。
- 工作树：`C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800`；分支：`codex/a03-runtime-recovery`。
- [确切任务原件](../evidence/A03/execution/P2-R9-minimal-demos/inputs/A03-P2-R9-minimal-demos.md) raw SHA256：`2d4a813262460325b7cee31876c45874f70465787489132c3d097c9052a3231b`。
- [R4 调度结论](../evidence/A03/execution/P2-R9-minimal-demos/inputs/A03-P2-R8-R4-remaining-coordinator-decision.md) 与 [独立报告](../evidence/A03/execution/P2-R9-minimal-demos/inputs/A03-P2-R8-R4-remaining-review-report.md) 均来自同一 workflow；后者 SHA256=`4666400a3bc1f9227601bcc1d47b4335e33a8ebf427a3dc72872221dda4d5945`。此前已接受的丢回执 N1/N6/初始化控制仅静态引用，没有重新执行。
- 最终交付提交为本报告与 R9 新文件所在 clean HEAD，确切 SHA 由交付消息/Git 日志提供，避免文档自引用提交哈希。

仅新增 [R9 验证入口](../../tests/test_a03_p2_r9_minimal_demos.py)、[驱动/文件审计目录](../../examples/a03/P2-R9-minimal-demos)、本报告和 R9 execution 证据。未合浮动主目录，产品、oracle、producer、Schema、profile/adoption/pins、依赖和所有历史原件均未改；未修改根调度 state。

## 最短真实失败与原因

[D1 执行子进程原 stderr](../evidence/A03/execution/P2-R9-minimal-demos/validation/r9-01/processes/D1-execute/stderr.txt) 保留完整首次 traceback，raw SHA256=`0db6947c2321a6a6fe42b68486f7dc0f0cd7e5340a50a6f412f013fe9fc4852d`。调用路径：

1. 新固定单题经正常 begin/produce/admit PRE、targetcheck、planner、record_native_plan；生成恰好一个 CREATE_FRAMES。
2. 独立 child 正常调用 `run_plan`，fault=None，未使用效果故障点、屏障、计时器或 SQL 造业务状态。
3. [recovery/__init__.py](../../src/annotation/runtime/recovery/__init__.py):121–123 先查询状态并 project_plan，再在仍持有自己的 ACTIVE lease 时调用 publish_quality。
4. [native_quality.py](../../src/annotation/runtime/recovery/native_quality.py):21 无条件调用 claim_current。它进入 [storage/__init__.py](../../src/annotation/runtime/storage/__init__.py):413–416；当前 owner 仍有效且 PID 活着，按既有门禁拒绝 `OWNER_BUSY`，原消息为 `lease expired AND previous process exited required`。
5. run_plan 的 finally 在 recovery/__init__.py:129–131 停止自有 keeper 并正常 release。child exit1；外层只记录冻结 SQL 后退出，不启动下一功能路径。

这是正常执行到报告发布的 owner 编排冲突。共享 claim 的拒绝条件在此正常生效；本轮没有把它放宽或绕开。原 helper 的正常 setup/claim 和 run_plan 显式 owner/generation 入口与既有已接受路径相同，未注入他属 owner。

如另行派发最小产品修复，可在 `run_plan → publish_quality → publish_native_quality` 衔接显式传递并校验当前 owner/generation，使在当前有效 lease 内发布报告的调用复用该已验证租约；独立报告入口仍自行 claim/release，只有实际取得租约的一方释放。应保留 ACTIVE/PID/instance/generation、pending/hold、报告读预算及事务校验，不全局改变 claim 的 OWNER_BUSY 规则。**这里只交建议，本轮未实现或尝试该修复。**

## 实际到达与未达项

| 项目 | 实际结果 |
| --- | --- |
| D1 执行父进程 | PID=42924，exit1，timeout=false，alive=false |
| D1 效果子进程 | PID=61832，exit1，timeout=false，alive=false；预期正常 exit0，实际失败 |
| D1 PRE/planner/record | 正常完成；单题单动作，未扩大题数 |
| D1 目标效果 | 执行前0，失败后1；执行子进程确实产生唯一效果 |
| D1 action / intent | APPLIED / APPLIED；permit=1，状态 CONSUMED；正式回执存在 |
| D1 尝试事实 | `ATTEMPTED`，从实际正式 fact 读取；未改成 NOT_ATTEMPTED 或 UNKNOWN |
| D1 POST / Batch / report read | 0 / 0 / 0；尚未进入报告独立观察 |
| D1 正常 FINISHED 返回 | 未返回，`normal-run-result.json` 未生成 |
| D1 重启独立查询及同计划重复保护 | NOT_RUN_AFTER_FIRST_EXECUTE_FAILURE；没有重启产品进程替代原失败 |
| D2 intent 后真实退出 / ABSENT / 旧计划保护 | NOT_RUN_AFTER_D1_FAILURE；没有创建 D2 case/进程/marker，也没有调用 reconcile |

因此本轮未完成正常可搬运演示，不能据此声称重启后效果保持一次、重复保护通过或明确 ABSENT。D1 的 POST/Batch 未生成，要求的 PENDING/NOT_SUBMITTED 报告输出也未完成；没有将缺失报告填成通过。正式计划仍为 SIMULATED/HUMAN_ONLY，没有书级送交。

## 冻结 SQL、正式四元组与 Resource

[首次失败父进程 SQL 原记录](../evidence/A03/execution/P2-R9-minimal-demos/validation/r9-01/D1-first-failure-SQL.json) 在效果 child 已退出后以 stdlib immutable/query_only 读取；[封存只读交叉核对](../evidence/A03/execution/P2-R9-minimal-demos/first-failure-readback.json) 再核对文件、正式 SQL 与当前 bundle，没有导入或调用产品。

| 库/记录 | 原始 SHA256 |
| --- | --- |
| 执行前 runtime raw copy | `21a04c566e9c989f0696a6449af0b339774e91574254ac611eeedaeb99b75ac9` |
| 执行前 target raw copy | `d544641e1dddf3797d0a48e1916452426de5280fcdeb3e222456ee722cc352ec` |
| 失败后 runtime/runtime.sqlite3 | `192cea9caee1b34223045beb5fa016b7735f64ae32ecbf179ebb42bd08869b61` |
| 失败后 target/target.sqlite3 | `44ba882aecab97831995c12d21fa728c034c0ab42e66114d6799bbe415b628ec` |

执行前两份文件是 child 在 run_plan 前、自己的 lease keeper 已存在时逐文件读取保存的原字节，不声称是跨库原子备份。现有冻结副本 quick_check 均 ok。失败后读取前后库字节相同。执行前 runtime 的 plans/actions/intents/permits 均0（计划已在 artifacts 中正式记录），target effects=0；失败后 runtime 有14个 artifacts、1 plan/action/intent/permit、1 PRE/creation anchor、0 resolution/report read；target 有3次观察和1个效果。最终 books.phase=RELEASED、owner/pid=null、lease=0，hold=null。

关键正式引用均 revision=1，SQL artifacts、当前 bundle 和 intent.receipt 中的回执四元组相同：

| kind / artifact_id | content_hash |
| --- | --- |
| ApplyPlan / `plan-r9-D1` | `c0d5e99d98ea3133abc22daee14a1f14589932ae1f6fae3259ad5ff3799c4779` |
| WriteIntent / `writeintent-819a78b2783c441b88762ed4ab72e1e4` | `964edea5968f3172a6dc818e1ade5a2ae40a53a61164a89b1b4b73b1d6e8ce06` |
| ExecutionReceipt / `executionreceipt-5df5825e40a94c7c8495836773f1d3a5` | `dfffa7ffc87929ef888be3a608e688860dcbf398b06968ce8eb26b884681d8d1` |

正式 action=`action-a02-b5a2d38e753b8c778e4482bc131d5513`；其 fact Resource=`assets/runtime/20deadc332558d19736b4925002c683d545a8db1678295d755f621d906f2f009.json`，SHA 与文件名相同。实体的 plan/intent/action 绑定和 APPLIED/ATTEMPTED、正式 progress、原 before/readback Resource 均保留于只读回查及原 package。没有因首败删除效果或回执，也没有调用任何恢复或重发路径。

## 输入、实际导入与命令

[输入登记](../evidence/A03/execution/P2-R9-minimal-demos/inputs.json) 保存5份 exact workflow 文档和11份 base 原件引用摘要。D1 正常 import `test_a03_r8_r3_post_hold.setup_pre`，使用其中固定32×32、单题、两片段语言。逐项源提交/路径/raw SHA 已列；helper 只向首次不存在的 R9 case 复制必要固定 fixture，没有复制成功库、旧 PRE/plan 或历史全集，没有改 helper/fixture、AST/exec 裁剪或产品 monkeypatch。

[启动前驱动冻结](../evidence/A03/execution/P2-R9-minimal-demos/driver-preregistered.json) 与各级 preregistered.json 在功能进程启动前保存：

| 执行文件 | SHA256 |
| --- | --- |
| `tests/test_a03_p2_r9_minimal_demos.py` | `a453d34a434a1cefd9912e95ee0619ad9c3184356c88b38831a0e7634772df76` |
| `examples/a03/P2-R9-minimal-demos/audit_a03_p2_r9.py` | `8cd23b32e9409a2ee559e223466df4e8ede41d8e4471d6ec2ccb35ad62b7d50f` |
| `examples/a03/P2-R9-minimal-demos/prepare_a03_p2_r9.py` | `3f40f91125a3751b08952cf4a756a65f5975b1886dc862efa3bb4f257ba1412d` |

实际 child executable=`C:/Users/ASUS/AppData/Local/Programs/Python/Python39/python.exe`；[child 导入原记录](../evidence/A03/execution/P2-R9-minimal-demos/validation/r9-01/imports/D1-execute.json) 保留每个实际 module.__file__/SHA。storage/native.py 实际在本工作树 src 内，SHA=`c3e2f01ccbfb7b64c49a5272eb51ffbe2f6af8c8abb5a51c4c9c6965166b902a`。全部产品 source index=`e78f63e7d4f05f8e132cb24e61c4072bb897d49243e173376998fd397505c5ae`，与 base 相同。profile=`023078c2a8bdfd1f3cc80eb6effdfc31010284464584218cbb77f3c4583c921a`，adoption=`24d6529f2fcb9a386b0c52ab46f7551ee8c8701350351c88b241621fdec4477f`，未改变。这是源码执行记录，不是安装证明。

以下为实际命令，均在仓库根目录运行；参数不依赖个人绝对路径。已有输出 exclusive，不覆盖重跑：

```powershell
python -X utf8 -B examples/a03/P2-R9-minimal-demos/prepare_a03_p2_r9.py
python -X utf8 -B examples/a03/P2-R9-minimal-demos/audit_a03_p2_r9.py run D1 python -X utf8 -B tests/test_a03_p2_r9_minimal_demos.py D1 --output-root docs/evidence/A03/execution/P2-R9-minimal-demos/validation/r9-01
```

功能父 watchdog=90秒、效果 child=45秒；既有观察2秒、PRE/lease 期限未改。D1 restart 和 D2 没有 invocation。父/child 原 argv/cwd/输入/脚本摘要、PID、stdout/stderr、exit/timeout/alive 和子观察记录均保留。

停止后的唯一进程化复核是文件/SQL-only：

```powershell
python -X utf8 -B examples/a03/P2-R9-minimal-demos/audit_a03_p2_r9.py run frozen-readback python -X utf8 -B examples/a03/P2-R9-minimal-demos/readback_a03_p2_r9.py
```

其 PID=22652、exit0，不调用产品。最终 `seal_a03_p2_r9.py check` 也只校验 raw Git、manifest、pins/源字节和报告链接。

## 保全、过程限制与释放

封存准备的一个 stdin 元数据脚本在 Python3.9 中误用 `Path.write_text(newline=...)`，TypeError exit1；此前 outcome/coverage/scope 三份文件已经写入。保留 [首次脚本](../evidence/A03/execution/P2-R9-minimal-demos/metadata/first-seal-preparation/stdin-script.py.txt) 与 [工具原转录及限制](../evidence/A03/execution/P2-R9-minimal-demos/metadata/first-seal-preparation/tool-transcript.json)。只做一次静态文本修正，移除新 sealer 的重复目录项；未再运行该脚本、未碰功能组或已执行驱动。该 tool 级动作没有提供 PID 与分离二进制 stdout/stderr，所存为 combined tool transcript，未伪造进程登记；此限制独立于已完整登记的功能失败。

[进程释放清单](../evidence/A03/execution/P2-R9-minimal-demos/process-release.json) 汇总所有已登记自有产品/审计父子进程的 wait/exit/timeout/alive；[系统 PID 回查](../evidence/A03/execution/P2-R9-minimal-demos/process-os-readback.json) 只读本轮已登记 PID，未终止他人进程。[范围/清洁门禁](../evidence/A03/execution/P2-R9-minimal-demos/scope-state.json) 记录旧 tracked 文件干净及最终提交后必须 empty status 的检查要求。

最终以 raw Git mode/type/blob 逐项比较 base 的31482个条目，产品和所有旧证据/报告/测试原件不变。manifest 包含本轮全部新增、报告、必要输入、失败原输出、产物、清洁门禁和 process-release，只排除自身；暂存/提交后再核对 raw blobs 与工作树。最终 exact commit/clean status 见交付输出。

[覆盖/未达映射](../evidence/A03/execution/P2-R9-minimal-demos/coverage-map.json) 引用固定 R4 原覆盖表，R9 未完成 D1/D2 演示；不替代 V01 多动作、V04/R11 混合尾段、充分/不足 ABSENT、新检查/新计划、跨 scope/书、竞争者及其他原缺口。原 R3 N7 FAILED 及旧 target 入口未运行，R3/R4 已通过组未重跑，兼容套件未重复。

字段重置专项始终 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`。保留用户 model/thinking，未委派、安装、使用网络/平台/浏览器/凭据/profile/OCR/模型、推送、书级送交、A05题22重放或 B/验收者联系。执行冻结只交 REVIEW；产品修复、独立验收、集成及 I01 由后续有界派发决定。
