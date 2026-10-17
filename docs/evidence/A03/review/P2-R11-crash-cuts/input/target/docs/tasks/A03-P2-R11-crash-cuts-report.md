# A03 P2-R11 四个崩溃切点执行交付

2026-10-18（Asia/Shanghai）。状态：**REVIEW**。F1→F2→F3→F4 四项功能检查各首轮一次通过，四个执行 child 均真实 exit90；F1/F4 新进程只查询，F2/F3 各正常 reconcile 一次、max_attempts=1，最终效果依次为0/0/1/1。产品和历史原件未改。

**保全限制：F2/F3 中间阶段漏存了独立 SQLite 二进制副本，只保留完整 SQL 行集、当时 raw SHA、事件/不可变 artifacts 和 Resource。运行前 raw 副本及最终双库原件都在；F1/F4 查询前后字节相同，最终文件也保留了切点原字节。未重跑、重建中间库或宣称原 raw SHA 可从归档中的中间二进制重新计算。** 独立验收需按此实际边界核定，不能把功能退出成功当作证据全部要求已关闭。

## 固定身份及范围

- 唯一 base：`1c26b4a8eb378af33e57668472d2071e9ea6afff`；接单时 HEAD 精确一致、工作树干净。
- workflow：`bc0074bc8b852ef14012ee338bf3153ccb1f932b`；工作树：`C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800`；分支：`codex/a03-runtime-recovery`。
- [确切任务原件](../evidence/A03/execution/P2-R11-crash-cuts/inputs/A03-P2-R11-crash-cut-validation.md) raw SHA256=`ef09227381b7b8f2f0e9c9f590b67fb63dd898ca9758cab490e3044c2cc3f500`；[R10 调度结论](../evidence/A03/execution/P2-R11-crash-cuts/inputs/A03-P2-R10-owner-fencing-coordinator-decision.md) 同样来自该 workflow raw Git。未合并浮动调度分支或复制历史全集。
- [输入登记](../evidence/A03/execution/P2-R11-crash-cuts/inputs.json) 保留4份必要原文和12份 base helper/产品/固定输入引用的路径、长度/raw SHA。每例使用首次不存在的路径和新 runtime/target，固定32×32单题两片段 SYNTHETIC，不以旧库为种子。
- 仅新增 [R11 驱动](../../tests/test_a03_p2_r11_crash_cuts.py)、[R11 归档工具目录](../../examples/a03/P2-R11-crash-cuts)、本报告和 R11 execution 证据。最终 exact commit/clean status 由交付消息和 Git 日志提供，避免文档自引用提交哈希。

正常 import R3 setup helper，真实建立 PRE/实际观察/接纳、目标检查、计划和 record_native_plan；每例 plan 只有一个 CREATE_FRAMES。R10 模块仅作为正常导入的文件/SQLite 读取工具，不执行其 C1/C2。没有 AST/exec 裁剪、产品 monkeypatch、SQL 写业务状态或手工资格/历史封签。

## 静态核对及冻结

既有 FaultController 的四个实际调用点和事务边界已在首次功能前核对：

| 组 | 既有点及代码位置 | 切点业务边界 |
| --- | --- | --- |
| F1 | BEFORE_INTENT_COMMIT，[storage/__init__.py](../../src/annotation/runtime/storage/__init__.py):615 | 已接受/预留计划与动作；intent 事务尚未开始 |
| F2 | AFTER_DISPATCH_STARTED，同文件:1101 | permit 消费及 DISPATCH_STARTED 已提交；尚未返回目标效果 authorization 并执行效果事务 |
| F3 | AFTER_READBACK_CAPTURE，[recovery/__init__.py](../../src/annotation/runtime/recovery/__init__.py):116 | 效果和执行读回已到达；尚未比较并 commit_action_result |
| F4 | AFTER_RECEIPT_COMMIT，storage:739 | 正式结果已提交、project_plan 产生完整 receipt；尚未发布 POST/Batch |

使用原 FaultController 的 point/marker 和默认 exit90；没有添加故障机制或以异常替代进程退出。[启动前冻结](../evidence/A03/execution/P2-R11-crash-cuts/driver-preregistered.json) 记录源码、输入和逐例预期，未预设额外 plan 状态、外层错误字符串或 attempt_fact：

| 执行文件 | 原始 SHA256 |
| --- | --- |
| `tests/test_a03_p2_r11_crash_cuts.py` | `0b58c6d589acfe6c81664e1d3940c7eb08e2b0ab77beab5b2a85194b0bae4abc` |
| `examples/a03/P2-R11-crash-cuts/audit_a03_p2_r11.py` | `6f2a7817727b60e214bd92477102a352c2e6acfef21968b5b99b11d848ceb216` |
| `examples/a03/P2-R11-crash-cuts/prepare_a03_p2_r11.py` | `5028e5dd3e61fa9ec523ad5288817f05171fd5e536b382f63286e2235476dc59` |

## 实际独立进程结果

每次由父进程 wait 确认 crash child 已退出90，保存 marker/PID/切点 SQL 后，再启动不同 PID 的查询/恢复 child。所有以下进程 timeout=false、alive=false；故障前导入、marker 和持久化数据共同证明切点。

| 组 | 父 PID / exit | crash PID / exit | 新进程 PID / exit | 原 owner/instance（generation1） |
| --- | --- | --- | --- | --- |
| F1 | 67116 / 0 | 26036 / 90 | 60716 / 0 | `process-b33999a8e6e844a2a821a85c3e6bb3a5` |
| F2 | 52736 / 0 | 30848 / 90 | 42044 / 0 | `process-6d0b375a68c741ce9a9c8b8cd8de0dda` |
| F3 | 69020 / 0 | 70132 / 90 | 16180 / 0 | `process-910ae6d011524dacb7c3733be10fb583` |
| F4 | 50288 / 0 | 22992 / 90 | 6448 / 0 | `process-b30cfa7689b64e908289aa0546b8a09f` |

每例 `cases/F*/before-run.json` 保留实际 PRE run、PRE/plan 四元组、owner、instance、PID、实际 imports。真实 executable=`C:/Users/ASUS/AppData/Local/Programs/Python/Python39/python.exe`；product module.__file__ 均在本工作树 src，helper 在本工作树 tests。原 os._exit 不运行 finally，故没有 crash-exit imports 文件；只使用实际存在的故障前 imports，未按预设数量补造退出记录。四个新查询进程的正常退出 imports 均实际保存。

### F1：intent 提交前

[F1 结果](../evidence/A03/execution/P2-R11-crash-cuts/validation/r11-01/cases/F1/result.json) 证明已接纳/预留 plan/action 各1，intents/permits/effects 均0，无 WriteIntent、ExecutionReceipt 或正式 result fact。新进程只 open/status/bundle/SQL/Resource 查询，不 project、不 reconcile、不派发或清锁；未伪造 NOT_ATTEMPTED receipt。

实际 plan 表状态为 RUNNING，原死进程 owner 行仍为 generation1/ACTIVE。它们按产品现状记录，未手工改成 READY/INTERRUPTED/RELEASED。新进程查询前后双库 raw SHA 相同。

### F2：dispatch started 后、效果前

[F2 结果](../evidence/A03/execution/P2-R11-crash-cuts/validation/r11-01/cases/F2/result.json) 与原事件证明：intent=1/PENDING、permit=1/CONSUMED，DISPATCH_PERMIT_CONSUMED 和 DISPATCH_STARTED 已持久化，无 ACTION_RESULT_COMMITTED；effects=0。效果为空没有被解释为“未调用”。

新进程先记录 status、原 bundle、完整 SQL，再经正常 project_plan 保留正式 UNKNOWN progress，原 receipt=null。随后只调用一次 reconcile、max_attempts=1；由完整精确绑定的新观察取得 ABSENT/RESOLVED_NOT_APPLIED。新 read_sequence=3，大于切点已有最大值2；store/session、target_key、scope/source、plan/action/intent、observation_id/snapshot 和 readback Resource 逐项绑定，见 [新终局读回](../evidence/A03/execution/P2-R11-crash-cuts/validation/r11-01/cases/F2/fresh-terminal-readback.json)。

原 UNKNOWN 保留，前后 attempt_fact 均为实际产品的 MAY_HAVE_BEEN_ATTEMPTED，没有把效果不存在改成 NOT_ATTEMPTED。最终 effects 仍0，plan 状态实际为 INTERRUPTED；未执行旧动作或新计划。

### F3：执行读回后、结果提交前

[F3 结果](../evidence/A03/execution/P2-R11-crash-cuts/validation/r11-01/cases/F3/result.json) 证明切点 effects=1、target observations=3，结果 fact/receipt 尚未提交，intent 仍未决。AFTER_READBACK_CAPTURE marker 位于执行 observe_target 返回之后；原目标观察行和源码位置证明执行读回已到达。

新进程先保存原未决和正式 UNKNOWN，再 reconcile 一次、max_attempts=1。依赖新 observation/read_sequence4（切点最大为3）取得 MATCH/RESOLVED_APPLIED；不是重用已退出进程的内存结果，见 [新终局读回](../evidence/A03/execution/P2-R11-crash-cuts/validation/r11-01/cases/F3/fresh-terminal-readback.json)。完整 read_status=OK、scope_complete=true、来源/目标/会话及正式解决绑定均核对。

effects 前后均1，没有再次派发。原 UNKNOWN 和 intent 保留，前后 attempt_fact 均为 MAY_HAVE_BEEN_ATTEMPTED。native late fact 后 plan 表实际为 FINISHED，如实记录，未预设必须 INTERRUPTED。

### F4：正式回执提交后

[F4 结果](../evidence/A03/execution/P2-R11-crash-cuts/validation/r11-01/cases/F4/result.json) 证明 effects=1，action/intent 为 APPLIED，正式 receipt 存在，plan/动作/intent/fact 精确绑定且 attempt_fact=ATTEMPTED。SQL intent.receipt、artifacts 和当前 bundle 的回执四元组相同；receipt.action_fact_refs 与真实 fact Resource 相同。

新进程只 open/status/query 和读取正式实体，不 project、不 reconcile、不生成 resolution 或重发。双库 raw SHA 查询前后相同。实际 plan 表为 FINISHED；原死进程 owner 行仍 generation1/ACTIVE，未为归档而清理业务状态。

四例实际 POST=0、Batch=0、native_report_reads=0。崩溃前尚未到达报告发布，本轮没有补报告或把缺失状态填成成功。F1/F4 没有 recovery call；F2/F3 各有且仅有一个 call/attempt/resolution，恢复结束正常释放 generation2。

## 正式四元组、Resource 与双库

下列正式产物均 revision=1，所有 plan/intent/progress/receipt/resolution 四元组和原实体详见 [全量 SQL/边界回查](../evidence/A03/execution/P2-R11-crash-cuts/database-and-boundary-readback.json)。当前 bundle refs 全部在 SQL artifacts 登记；facts/readback 的实际 Resource SHA 与实体一致。

| 产物 | artifact_id / content_hash |
| --- | --- |
| F2 resolution | `resolution-0b742a98aa6d4a2d8c50191a5ee6c7e3` / `91516afb9395736c2e9c3eabafd8c969d1ddb3a143602301e98b6bc700d683d5` |
| F2 late receipt | `executionreceipt-bfb73341ef9a4fbe9ace174772b72978` / `58abb35b6e1c405fc41f42aa03e70d7397ef0585136e27639bbe0735b05a6592` |
| F3 resolution | `resolution-4ba4f633a68d43679fa3acc78c0f2174` / `26070d9fbf86523241edda368b04942ec3b391899e15531b471db2df3f3d384d` |
| F3 late receipt | `executionreceipt-0254e094182045ecb627eecb5bc96a9a` / `2414d7ebc3d529fd528e9cc3247a49508b257965057549dec99063090c2fe52f` |
| F4 execution receipt | `executionreceipt-395943c176c145fb90a33ee6c3fa83a7` / `b2e958b77fcacb501eeaab992c78177e77378bef66662b67a429a294574c22e2` |

F2/F3/F4 的 fact Resource 分别为 `assets/runtime/22975d06dd81b7bb2d099c450b6846004bda7dd013c139c4f26ec3fd15bbf89b.json`、`assets/runtime/6397864fcf79508c4b32d6431f02d3e38f7821e49a6be8fd2aa06bc5444af297.json`、`assets/runtime/5c1c00cc34097197950e7494d830e953feb1059aa49a17235ae808d3f2dbc6fd.json`，SHA256 均与文件名相同。F2/F3 的 original_receipt_ref=null、replay_allowed=false，未改写原未知历史。

| 最终库 | runtime raw SHA256 | target raw SHA256 |
| --- | --- | --- |
| F1 | `e89b2e5e3e033fa9f776c1d300355765174a01d5eda88f0eea19d28830dd1148` | `8a4d94c3e91c49475a94f0a7c10591735526cee3d735128867bcd9e8f6d139ab` |
| F2 | `d0297cb8e42fbf42d43633bbed547a71612dcfe643e1786b62f517c8cddf458b` | `24a703cc70cb8fb161f33c52ba211dc243162580d702fe0d4c6357c065a681e4` |
| F3 | `5f21450e60456e311eed868d30a92f2ab5d908a821e3bfec4c83e39497d1c7b3` | `b16166c8614d7ac61aa0d1a8948fae1d86e57c6a5310cc65244a17b3b8b77c9f` |
| F4 | `0e7e3f9686c3175bec5077a54f2ca78503b8ef632557401f8e8eb1b02fa62ec0` | `a326603dd444724f40406c3342dabf9ac13792852a7087f119c6875408561ca1` |

## 中间二进制保全限制

运行前，合法计划形成后留存了两份实际 raw 副本；复制时自己的 keeper 存在，是顺序字节读取，不称跨库原子备份。每次 crash wait 后，父进程读取双库完整 SQL 行集、事件与 raw SHA；F2/F3 在 project UNKNOWN 后也留存完整双库状态及 SHA。

这些中间读取没有另存 SQLite 原字节。F2/F3 随后的正常恢复修改了原数据库，因此当前归档无法从那个中间 SQLite 文件重新计算原 raw SHA；这是本轮遗漏，不能用 SQL 重建文件冒充原件。当前仍保留完整中间行集、不可变 artifacts/Resource、marker/真实退出及原始驱动绑定。详见 [逐阶段保全声明](../evidence/A03/execution/P2-R11-crash-cuts/stage-binary-preservation.json)。F1/F4 原库未变，捕获的切点 SHA 与最终文件一致。

最后的 stdlib immutable/query_only 交叉回查读前读后字节相同，记录全部实际库/副本及 quick_check，并核对 marker/退出/新进程时序；没有调用产品、构造中间数据库或重新执行功能。该限制交独立验收核定，不自记证据完整验收通过。

## 可搬运命令与释放

在仓库根目录按实际顺序执行；默认输出根为 `docs/evidence/A03/execution/P2-R11-crash-cuts/validation/r11-01`，可通过 driver 的 `--output-root` 指向该 R11 证据下新的相对路径。已有输出 exclusive，不覆盖重跑。

```powershell
python -X utf8 -B examples/a03/P2-R11-crash-cuts/prepare_a03_p2_r11.py
python -X utf8 -B examples/a03/P2-R11-crash-cuts/audit_a03_p2_r11.py run F1 python -X utf8 -B tests/test_a03_p2_r11_crash_cuts.py F1
python -X utf8 -B examples/a03/P2-R11-crash-cuts/audit_a03_p2_r11.py run F2 python -X utf8 -B tests/test_a03_p2_r11_crash_cuts.py F2
python -X utf8 -B examples/a03/P2-R11-crash-cuts/audit_a03_p2_r11.py run F3 python -X utf8 -B tests/test_a03_p2_r11_crash_cuts.py F3
python -X utf8 -B examples/a03/P2-R11-crash-cuts/audit_a03_p2_r11.py run F4 python -X utf8 -B tests/test_a03_p2_r11_crash_cuts.py F4
```

prepare 仅用于指定 clean base/空输出准备。每例父 watchdog90秒、业务 child45秒；原观察2秒、屏障5秒、lease10秒和恢复期限不变。F2/F3 通过原 claim_current 等待死进程租约，不固定 sleep 假定接管、不清锁。没有旧动作重放、新计划、额外 reconcile 或 publish。

功能结束后只运行一次 file/SQL-only readback（PID58632/exit0）及归档审计。文件复核入口：`python -X utf8 -B examples/a03/P2-R11-crash-cuts/seal_a03_p2_r11.py check`。它不调用产品或测试。

[进程释放清单](../evidence/A03/execution/P2-R11-crash-cuts/process-release.json) 保存全部已登记自有进程的 wait/exit/timeout/alive；[系统 PID 回查](../evidence/A03/execution/P2-R11-crash-cuts/process-os-readback.json) 只读本轮登记 PID，不终止他人任务。F1/F4 落盘的旧 owner 行未清理，实际进程已退出；不能将进程退出证明写成所有业务 owner 行都已正常 release。

最终 raw Git mode/type/blob 逐项比较 base32413个旧条目，全部原样；产品 source index 与 base 相同，已执行驱动字节与启动前冻结一致。[范围/清洁门禁](../evidence/A03/execution/P2-R11-crash-cuts/scope-state.json) 记录旧 tracked 状态及最终 empty status 要求。manifest 覆盖本轮全部新增、报告、必要输入、脚本、原输出/marker、实际保存的数据库/资源和释放证明，只排除自身；入库后核对 raw blobs，clean commit 冻结。

[本轮结果](../evidence/A03/execution/P2-R11-crash-cuts/bounded-outcome.json) 和 [覆盖/限制](../evidence/A03/execution/P2-R11-crash-cuts/coverage-map.json) 仅对应原 V02/R03 的这四个单题切点及实际证据层级。旧 AFTER_INTENT_COMMIT、丢回执 N1、R9/R10、原 R3 N7 和全套矩阵未重跑。多动作/混合尾段、其他 ABSENT/冲突、资格/来源/归档/报告/次数等原缺口未自动豁免。

字段重置始终 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`。未修改用户 model/thinking、产品/schema/profile/pins/oracle/producer/verifier/依赖、旧原件或调度 state；无子代理、网络、平台/浏览器/profile/凭据/OCR/模型、安装、推送、B联系、A05题22或书级送交。仅交 REVIEW，A03/I01 未释放，B 映射未共同确认。
