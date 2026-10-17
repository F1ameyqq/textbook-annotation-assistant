# A03 P2-R9-R1 ownership 生命周期修复交付

2026-10-18（Asia/Shanghai）。状态：**REVIEW_BORROW_READ_LIMIT_EXCEPTION_EXPECTATION_FAILED**。本轮实现了报告借用当前租约的修复；全新 D1 正常/重启防重复和独立 publish 各一轮通过。借用组的四项参数拒绝、合法发布及其后 owner/generation/keeper 断言已到达；随后限额负控因驱动错误预期底层异常类型而失败。按首败规则冻结，D2 未运行，不修改驱动或产品重跑。A03 整体和 I01 未释放。

## 固定输入与提交

- 唯一 base：`c83f956c5c29c64ab10735ba11c153201d3f3f4b`，接单时 clean HEAD 精确一致。
- workflow：`2aabd591695e73ecd4024c95e06fe0b71a2a9267`；工作树：`C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800`；分支：`codex/a03-runtime-recovery`。
- [确切任务原件](../evidence/A03/execution/P2-R9-R1-owner-lifecycle/inputs/A03-P2-R9-R1-owner-lifecycle-repair.md) raw SHA256：`eb375839b834126f8a72be6a60a21d45b00fad83925de0e2d71cd6b0abe80191`。
- [独立故障复核原件](../evidence/A03/execution/P2-R9-R1-owner-lifecycle/inputs/A03-P2-R9-failure-review-report.md) SHA256：`8c8302ff0ca1e4adb69d4c22de4131ca8ba713494a485f02d7fd89d2448e3a0e`；[调度判定](../evidence/A03/execution/P2-R9-R1-owner-lifecycle/inputs/A03-P2-R9-failure-coordinator-decision.md) 和原 R9 任务同样从该 workflow raw Git 取得。没有合并调度分支或复制历史归档全集。
- 最终交付提交为本报告与修复/证据所在 clean HEAD，确切 SHA 由交付消息/Git 日志提供，避免提交自引用。

## 最小产品差异与两种生命周期

只改变两份 recovery 文件及其 profile/adoption 摘要链：

1. [recovery/__init__.py](../../src/annotation/runtime/recovery/__init__.py) 给 publish_quality 增加可选 keyword-only owner_id/generation，native 分支显式传递；run_plan 调用报告时传入当前 owner/generation。原 run_plan keeper/finally/release 不变。
2. [native_quality.py](../../src/annotation/runtime/recovery/native_quality.py) 将成对参数视为借用。部分参数以 OWNER_GENERATION_STALE 拒绝；完整参数先调用既有 `_lease(..., pending_ok=True)` 验证实例、PID、ACTIVE、owner/generation 和 lease 时效，发生在 projection 与读额度消费之前。随后复用该 pair，不 claim；finally 不停止外层 keeper，也不 release。
3. 不带借用参数的独立 publish 继续自行 claim，finally 仅释放自己取得的租约。原“无完整回执”的诊断行为保留。报告 durable read 登记、快照落库、最终 POST/Batch 落库三个事务均调用原 `_lease(..., pending_ok=True)`；其中快照事务补充同一检查。

共享 storage.claim、OWNER_BUSY、普通写入 pending/hold、报告单次读和2秒观察限额未改。没有提前 release、吞掉报告错误、补造成功或扩大派发权限。legacy 报告分支函数体的 AST 与 base 相同；本轮没有跑 legacy/兼容全套，不将静态保全称为动态 legacy 验收。

| 获准旧文件 | 候选/最终原字节 SHA256 |
| --- | --- |
| `src/annotation/runtime/recovery/__init__.py` | `c62a558218e333e212a928a9bf0bb94a79a45e4bb91b08ee5a705e38bc12200d` |
| `src/annotation/runtime/recovery/native_quality.py` | `8038926e976da078625b9b095de40ba2eb994c1e670be3e0769f55629f7af100` |
| `src/annotation/contracts/a03_native/data/profile.json` | `741cadbfaaa622f2e24610026dcbfd6d68fd214dd1e4e1a1fb042df44b97445c` |
| `src/annotation/contracts/a03_native/data/adoption.json` | `2e0efa1e4538ce632b1cf3e5cae70c631ed0bbda7adb1ee22c5905ed5eb0aaac` |

profile 只更新上述两项 implementation_pins，adoption 只更新 profile_sha256；其他字段、pins、Schema、oracle/producer/verifier、版本语义和根依赖不变。最小 diff 可用 `git diff c83f956c5c29c64ab10735ba11c153201d3f3f4b HEAD -- src/annotation/runtime/recovery src/annotation/contracts/a03_native/data/profile.json src/annotation/contracts/a03_native/data/adoption.json` 查看。

## 冻结候选与真实执行

[候选冻结登记](../evidence/A03/execution/P2-R9-R1-owner-lifecycle/candidate-frozen.json) 在第一次功能执行前完成语法、legacy AST、范围、全部 implementation pins 校验；记录产品及驱动原字节。之后产品和已执行驱动没有改变。新主驱动 [test_a03_p2_r9_r1_owner_lifecycle.py](../../tests/test_a03_p2_r9_r1_owner_lifecycle.py) SHA256=`ec8dc7064705c1f4408b212becf8686936dac70d4feca7f4630b17106a119d9f`；runner SHA256=`7024385b144f80cddc0d4f5b4bb8ea406e49e1a1ed2a5a9aac71f40350fc46fc`。

正常 import 原 R9 execute/restart 与 R3 setup helper，显式传入首次不存在的 R1 case 路径；必要固定 fixture 的源提交、路径、长度/raw SHA 逐项列于 [输入登记](../evidence/A03/execution/P2-R9-R1-owner-lifecycle/inputs.json)。逻辑 fixture 标签沿用固定单题语言，实际产物完整四元组/运行身份和双库全新生成，没有复制旧成功/失败库、重放旧效果、AST/exec 裁剪或产品 monkeypatch。

四项顺序和实际结果：

| 组 | 父 PID / exit | child PID / exit | 到达范围 |
| --- | --- | --- | --- |
| D1 | 2932 / 0 | execute 17556 / 0；restart 40824 / 0 | run_plan 返回 FINISHED；POST/Batch 正式落库；新进程重开及旧计划拒绝，effect 始终1 |
| 独立 publish | 50148 / 0 | 59644 / 0 | 新合法完整 receipt、未消费报告读；自有 claim/publish/release 成功 |
| 借用参数组 | 66208 / 1 | 66792 / 1 | 四项参数拒绝、合法借用返回及后置断言通过；追加单次读限额检查的异常类型捕获错误导致组失败 |
| D2 | NOT_RUN | 无进程、case 或 marker | 首败后未启动；没有 intent 后 exit90、ABSENT 或旧计划保护结果 |

所有已登记进程 timeout=false、alive=false。D1/standalone/borrow 各首轮一次，未重跑原 R3/R4 组、原 N7 失败、原 R9 失败库或兼容全套。

### D1 与独立 publish

[D1 正常返回](../evidence/A03/execution/P2-R9-R1-owner-lifecycle/validation/owner-r1-01/cases/D1/normal-run-result.json) 为 FINISHED，正式 POST/Batch 为 PENDING/NOT_SUBMITTED。执行结束时 generation=1，报告没有额外 claim/generation；run_plan 正常 finally 释放。

另一个进程正常 open/project/独立观察后，经 run_plan 支持入口尝试同一计划一次，[真实返回](../evidence/A03/execution/P2-R9-R1-owner-lifecycle/validation/owner-r1-01/cases/D1/duplicate-result.json) 为 REPLAY_FORBIDDEN / `accepted plan is permanently reserved`。效果仍1、intent/permit 不增加。该重复尝试自身的正常 claim/release 使最终 generation=2；不能把它当报告阶段新增 generation。

独立 publish 的新 case 经 accept/prepare/commit_intent/first permit/dispatch/observe/commit_result/project 支持流程形成正式 APPLIED receipt，report-read=0，没有 SQL 改业务状态或拦截 run_plan。驱动正常停止并释放其原执行租约后，standalone publish 从 generation1/RELEASED 自行 claim generation2，发布后 RELEASED。claim-reserved/active/released 各增加一次，见 [独立 ownership 原记录](../evidence/A03/execution/P2-R9-R1-owner-lifecycle/validation/owner-r1-01/cases/standalone/standalone-owner-proof.json)。

### 借用参数、首次失败及证据限制

同样的新合法 receipt case 保持原 generation1/ACTIVE 和外层 keeper。以下控制均真实调用 publish_quality，逐项以 OWNER_GENERATION_STALE 拒绝；每份记录保存前后 owner/phase、计数与事件，未消费 report-read、未释放调用者：

- [仅 owner](../evidence/A03/execution/P2-R9-R1-owner-lifecycle/validation/owner-r1-01/cases/borrow/control-owner_only.json)
- [仅 generation](../evidence/A03/execution/P2-R9-R1-owner-lifecycle/validation/owner-r1-01/cases/borrow/control-generation_only.json)
- [过时 generation](../evidence/A03/execution/P2-R9-R1-owner-lifecycle/validation/owner-r1-01/cases/borrow/control-stale_generation.json)
- [他属 owner](../evidence/A03/execution/P2-R9-R1-owner-lifecycle/validation/owner-r1-01/cases/borrow/control-foreign_owner.json)

随后合法 pair 实际 publish 成功；驱动在下一次调用前已经通过 owner/generation/ACTIVE 不变、事件无新增、外层 keeper.thread.is_alive 及 keeper.check 断言。正式库中有对应 POST/Batch、native_report_reads=1、effects=1。

**驱动的异常类型预期写错了。** 为核对原单次读 fence，下一次 publish 的 INSERT 触发 SQLite UNIQUE constraint；共享 transaction 在 storage/__init__.py:158–162 将 sqlite3.IntegrityError 转为 RuntimeFailure(STORAGE_TRANSACTION_FAILED)。驱动只捕获底层 sqlite3.IntegrityError，实际包装异常继续传播，child exit1。完整 [首次 stdout](../evidence/A03/execution/P2-R9-R1-owner-lifecycle/validation/owner-r1-01/processes/borrow-execute/stdout.txt)、[首次 stderr](../evidence/A03/execution/P2-R9-R1-owner-lifecycle/validation/owner-r1-01/processes/borrow-execute/stderr.txt) 和父原输出均保留；child stderr SHA256=`bc895733e5e37d479f5da9c57f73b29f23694a30a5b09e02a833a11cc7436fb5`。

这次实际限额拒绝没有增加第二份报告读/观察/效果；失败原因是驱动没有按现有事务包装接口捕获异常，不能把它描述为限额被绕过或重复 claim 缺陷仍在。**整个借用组仍保持 FAILED，不改成 PASS。** 原候选、驱动和首次现场均冻结，未修复该捕获或重新执行本组，未继续 D2。

合法发布后的 state 在驱动内已取得，但 `borrowed-owner-proof.json` 的写入安排在限额检查之后，未到达；没有补造该文件。合法借用的到达依据是已落盘正式产物、四项前置控制记录、首次 traceback 到达驱动第二次 publish 以及此前已执行后置断言的源码路径。最终 owner 释放来自驱动 finally 的正常 cleanup；最终 generation1、仅一个 OWNER_RELEASED 与此一致。该记录限制供独立验收核定，不以新的产品重放补齐。

## 正式资源及冻结双库

[纯读取 SQL/实体回查](../evidence/A03/execution/P2-R9-R1-owner-lifecycle/database-readback.json) 使用 stdlib SQLite `mode=ro&immutable=1`、connection-local query_only，不导入产品。三个新 case 的库读前读后字节相同、quick_check=ok；当前 bundle refs 全部正式登记，POST 与 Batch 绑定同一正式 receipt，fact Resource 实体摘要吻合。每例 effect=1、report-read=1、POST/Batch 各1，内容 PENDING、NOT_SUBMITTED。

| case | runtime raw SHA256 | target raw SHA256 |
| --- | --- | --- |
| D1 | `e13196eaaa910281b52086904f6ec495b2940426921d51aecc887df9e71ae7ec` | `aa6746f7d1b4d954e099cba72e660ef48e9c36a347f4ff85c80291cf1b0b83b0` |
| standalone | `1ecfde4fd8242db1dfa49dd8f434f34066a5ce6d4b50dd673866ab4bde5d26d3` | `d2b7dfec0777daabcdcda591b1cac3ec64b1b75426ba770521f7af57902c32f5` |
| borrow | `e8dfad802e5dec7e4740e297e7d50115c8b9cbf3a04962b87feacfb56a2b522f` | `4fca4a9514a395a644a78e2d818c3eab35a8f14b86e84c3d102fb7b793b2aa1e` |

报告所绑定的关键正式四元组均 revision=1；全部 plan/intent/receipt/progress/fact/POST/Batch 及 Resource 在上述回查和原 package 中：

| case | POST artifact_id / content_hash | Batch artifact_id / content_hash |
| --- | --- | --- |
| D1 | `native-post-6f7b991f5ae743aebe93cfdcce30036c` / `d6fa3e1e9af804023b6157cc5d4f52e6b4d5525e93326bb547e10871f9aaea20` | `native-batch-cfde58288f2249d7b65a20cf78e1d4d4` / `953a77fc06f3434894b7c1b499309ca58cdb5da2614ad906c4c68624746ec5d7` |
| standalone | `native-post-8638d8459af04aa6954639346ef184fc` / `3cab99ae17f4a2ba172ef2d5522bbf829e075fff0b4bb32c2a7f25f7f2fd2ce1` | `native-batch-6600d3ad4c2c40e78a75f8993fdfbcbf` / `b3f4093f4fbc64598a5079d46c2ab29539b54bec8064ed938ec077d8b01de030` |
| borrow | `native-post-f56d57cbd4db49888e007c38c19a44a1` / `50142b6264c577117be7ff49acc2cf8c05f7245f4312d78f4345123ec8061cf8` | `native-batch-4130aaba2a374caabc31afbf354e457f` / `2963215c7e99a23c665dedc55639277685fd7c3cfdb8f52b33c14cedf47c5532` |

D1 重启 project 可能新增正式 receipt/progress；原 POST/Batch 仍绑定其执行阶段的不可变回执，不将其改称绑定后续最新回执。原 R9 及 R3/R4 失败/成功证据均未改。

## 可搬运命令、进程与封存

在仓库根目录，实际按下列顺序执行；默认输出根为 `docs/evidence/A03/execution/P2-R9-R1-owner-lifecycle/validation/owner-r1-01`，可通过 `--output-root` 显式指定该 R1 证据目录下新的相对路径。已有输出 exclusive，不覆盖重跑。

```powershell
python -X utf8 -B examples/a03/P2-R9-R1-owner-lifecycle/prepare_a03_p2_r9_r1.py
python -X utf8 -B examples/a03/P2-R9-R1-owner-lifecycle/freeze_a03_p2_r9_r1.py
python -X utf8 -B examples/a03/P2-R9-R1-owner-lifecycle/audit_a03_p2_r9_r1.py run D1 python -X utf8 -B tests/test_a03_p2_r9_r1_owner_lifecycle.py D1
python -X utf8 -B examples/a03/P2-R9-R1-owner-lifecycle/audit_a03_p2_r9_r1.py run standalone python -X utf8 -B tests/test_a03_p2_r9_r1_owner_lifecycle.py standalone
python -X utf8 -B examples/a03/P2-R9-R1-owner-lifecycle/audit_a03_p2_r9_r1.py run borrow python -X utf8 -B tests/test_a03_p2_r9_r1_owner_lifecycle.py borrow
```

D2 无 invocation。功能父 watchdog90秒、child45秒，既有观察2秒与产品 lease/PRE时限未变。各级 argv/cwd、脚本/输入/产品摘要、实际 imports、PID、原二进制 stdout/stderr、exit/timeout/alive 在 `runs/`、`validation/owner-r1-01/processes/` 和各目标 `process-audit/` 中保存。实际 Python 为 `C:/Users/ASUS/AppData/Local/Programs/Python/Python39/python.exe`；[D1 child imports](../evidence/A03/execution/P2-R9-R1-owner-lifecycle/validation/owner-r1-01/imports/D1-execute.json) 等记录的 product module.__file__ 均在本工作树 src。此为源码执行，不是安装验收。

首败之后仅运行文件/SQL-only readback（PID6672/exit0）及 final sealer，没有新产品调用。文件复核入口：`python -X utf8 -B examples/a03/P2-R9-R1-owner-lifecycle/seal_a03_p2_r9_r1.py check`。

[进程释放清单](../evidence/A03/execution/P2-R9-R1-owner-lifecycle/process-release.json) 保存所有已登记自有进程的 wait/退出；[系统 PID 回查](../evidence/A03/execution/P2-R9-R1-owner-lifecycle/process-os-readback.json) 只读本轮已登记 PID，不终止他人任务。最终 raw Git 差分逐项保全 base31665个条目中除获准4文件外31661个旧条目；再校验冻结候选与各组 source index。manifest 覆盖本轮全部改动/新增、报告、必要输入、原输出、失败现场和释放证明，只排除自身；入库后复核 raw blobs，最终 clean status 冻结。

[范围结果](../evidence/A03/execution/P2-R9-R1-owner-lifecycle/bounded-outcome.json) 和 [覆盖/未达映射](../evidence/A03/execution/P2-R9-R1-owner-lifecycle/coverage-map.json) 保留 D2 及原 P2 广覆盖缺口。没有把单题演示替代多动作、混合尾段、充分/不足 ABSENT、新计划、跨 scope/书、竞争者、其他崩溃点、合格清 hold、版本/来源/归档与报告/预算完整矩阵。

字段重置始终 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`。没有更改用户 model/thinking、委派、安装、网络/真实平台/浏览器/profile/凭据/OCR/模型、原始视频、A05题22、书级送审、B/验收者联系、推送或改根 state。本轮仅交 REVIEW，不自记 ACCEPTED/INTEGRATED，内部 pins 更新不构成 B 共同确认。
