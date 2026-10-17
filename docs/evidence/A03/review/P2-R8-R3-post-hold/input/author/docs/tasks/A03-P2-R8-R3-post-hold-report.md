# A03 P2-R8-R3 POST_HOLD 执行交付

2026-10-18，Asia/Shanghai。状态：`REVIEW_N7_DIAGNOSTIC_ASSERTION_FAILED`；A03 整体未验收，`I01=NOT_RELEASED`。本报告是执行者交付，不作独立验收结论。

本轮已完成唯一授权的 POST_HOLD 只读 PRE 接口修复。新场景 N1 完整链、N2 两次实际 POST_HOLD 接纳及真实超时、N3/N4/N5、局部控制和 C01/A02/R7 回归成功。N7 在旧目标入口拒绝 native 库时，精确外层错误码断言失败；保留首次输出并冻结。N6 未运行，N7 中断初始化控制尚未到达。

## 固定输入及提交

- 工作树：`C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800`；分支 `codex/a03-runtime-recovery`。
- 唯一产品 base：`58d8a64734271d15654bb00b03d760f0f3eccd10`。
- 产品及驱动提交：`13c8a766124ac45a91fa3edfa22de7df1e033c3e`。最终冻结提交是在此提交上新增本报告和 R3 证据的交付 HEAD；确切 SHA 由交付消息及 Git 日志提供，避免报告自引用提交哈希。
- workflow：`b79b12fe6a82f9d88b6533b54aea016c4f67f60b`；未合并或 cherry-pick 浮动主树。
- [任务原件](../evidence/A03/execution/P2-R8-R3-post-hold/inputs/A03-P2-R8-R3-post-hold-rework.md) SHA256：`8bb76c2cd713ec9af5386f3dcd547f443bbef42d6d4d19fc603ef0fcf5bd6a29`。
- [R2 独立报告原件](../evidence/A03/execution/P2-R8-R3-post-hold/inputs/A03-P2-R8-R2-projection-review-report.md) SHA256：`0cd36afd8409ec75ef04be9baf1602dc089d85a0bc5e187b393aece17a519565`；[调度结论原件](../evidence/A03/execution/P2-R8-R3-post-hold/inputs/A03-P2-R8-R2-projection-coordinator-decision.md) SHA256：`22be3239df20dfe880588c32e9fa94dbb501ad8689f3788792bce824aee7409f`。
- [输入登记](../evidence/A03/execution/P2-R8-R3-post-hold/inputs.json) 保留以上 raw blobs、三个旧产品文件及 base tree 摘要。

## 唯一产品改动

[native.py](../../src/annotation/runtime/storage/native.py) 只调整以下三个衔接点，并新增同文件小型私有辅助：

1. `begin_native_pre`：经 `_pre_lease` 核验当前租约和全书 pending，再从当前不可变事件取得 POST_HOLD 上下文。
2. `NativeRegistry._current`：按 durable binding 的 INITIAL/POST_HOLD 类型校验；POST_HOLD 始终绑定登记时的 exact hold/head。
3. `_dispatch` 的 `admit_pre` 提交事务：重复上述当前性、pending、hold/head 核验，不能只依赖事务外检查。

`_pre_lease` 仍调用未改动的共享 `_lease`，保留 ACTIVE、PID/instance、owner/generation 校验。POST_HOLD 的只读例外显式检查全书未解决义务；存在 pending 即 `BOOK_WRITE_PAUSED`。它要求实际当前 hold，校验不可变事件的 target key、registration、source、scope、store、session；已登记运行还核验 hold Resource 实体及 exact head。未清 hold，未增加计划、intent、permit 或目标效果权限。

INITIAL 继续使用原普通 hold 禁令；普通计划/写入路径继续拒绝 held book。未改变共享 `_lease`、projection、producer、合同守卫、Schema、版本、根依赖或其他状态机。新测试、驱动和夹具只位于本轮命名空间。两个 JSON 只更新受实现字节影响的 pins：

| 文件 | 最终原始字节 SHA256 |
| --- | --- |
| `src/annotation/runtime/storage/native.py` | `c3e2f01ccbfb7b64c49a5272eb51ffbe2f6af8c8abb5a51c4c9c6965166b902a` |
| `src/annotation/contracts/a03_native/data/profile.json` | `023078c2a8bdfd1f3cc80eb6effdfc31010284464584218cbb77f3c4583c921a` |
| `src/annotation/contracts/a03_native/data/adoption.json` | `24d6529f2fcb9a386b0c52ab46f7551ee8c8701350351c88b241621fdec4477f` |

最小产品 diff：`git diff 58d8a64734271d15654bb00b03d760f0f3eccd10 13c8a766124ac45a91fa3edfa22de7df1e033c3e -- src/annotation/runtime/storage/native.py src/annotation/contracts/a03_native/data/profile.json src/annotation/contracts/a03_native/data/adoption.json`。

## 实际执行及边界

以下均为最终相同产品字节的一轮实际执行。每组的 `runs/<组>/preregistered.json`、`started.json`、`completed.json`、`stdout.txt`、`stderr.txt` 是原始依据；N3/N4/N5/N7 为 N2 成功后预先启动的独立进程，N4 完成时间晚于 N7 首次失败。之后未重新执行任何产品路径。

| 组 | PID / exit | 实际到达点 |
| --- | --- | --- |
| local | 32476 / 0 | 正常 API；无 hold 的 POST_HOLD、旧 generation、真实 pending 逐项精确拒绝；pending=1，permit/effect=0 |
| N1 | 45132 / 0 | 全新独立双库，完整原标准，真实 child exit87 / 屏障，正式 receipt/progress/POST/Batch，effect=1 |
| N2 | 47480 / 0 | 正常目录漂移生成 hold；两次实际 POST_HOLD 读取、五检查和 ADMITTED；正常 release/claim 推进及真实过期拒绝 |
| N3 | 68016 / 0 | 五个 schema-valid、重算摘要的语义不匹配控制 |
| N4 | 51516 / 0 | 缺失、序列化、他属 run/observation 精确拒绝；独立控制库无目标效果 |
| N5 | 43480 / 0 | 实际读取 1.1 历史 JSON、验证 R7 静态 1.3 对象及 native authority 拒绝；不声称 1.1 archive validator 接纳 |
| N6 | NOT_RUN | N7 失败后未启动创建输入锚/UNKNOWN 历史完整控制 |
| N7 | 13512 / 1 | native 严格 reopen 成功、旧 runtime 入口拒绝、旧 target 入口拒绝后外层 code 断言失败；中断初始化未到达 |
| C01 | 30380 / 0 | `test_contracts*.py`：70 tests |
| A02 | 37648 / 0 | `test_a02*.py`：52 tests |
| R7 | 55864 / 0 | `test_a03_r7_readonly_codec.py`：13 tests |

### N1 正式链及双库

[N1 结果](../evidence/A03/execution/P2-R8-R3-post-hold/validation/native-r3-01/N1-result.json) 和 [SQL/实体只读回查](../evidence/A03/execution/P2-R8-R3-post-hold/database-readback.json) 保留原 UNKNOWN、null 原回执、terminal head、独立 MATCH、正式登记及材质化进度一致性。回查使用 stdlib SQLite `mode=ro&immutable=1` 与 connection-local `query_only`，不导入或执行产品；读前读后数据库字节相同。

- runtime：`validation/native-r3-01/cases/N1/runtime/runtime.sqlite3`，SHA256 `fc712e89f6468dfbb32523198fd8c39c1a21a27b93b22bf413b6d1ccb06b8e03`，application_id=1093678162、user_version=4；1 registration / 1 plan / 1 intent / 1 permit / 1 resolution / 3 native PRE runs。
- target：`validation/native-r3-01/cases/N1/target/target.sqlite3`，SHA256 `d65c27010afb010237cc3192c1b83e30245c94ea1335bb09607e4336b88c1f57`，application_id=1093678164、user_version=4；1 effect / 7 observations。
- 原始创建输入为全新 R3 fixture；固定 32×32 PGM SHA256 `1f82898615c67c676c532b17a8bd8e801c73eb6e7e2ba5a7f685bf1c3582cc7a`。未复制或延续旧成功/失败库。
- 正式 `ExecutionReceipt`：`executionreceipt-44e1516a56f3464d8d01ec251f3b673d`，revision=1，hash=`868c4c1fce6090b22d932b91a91f6be8febbfb14855ab9323294c7fa2fe035e4`。
- terminal `ReconciliationResult`：`resolution-e20f5c52b24347b7840efc62a9a3e7fa`，revision=1，hash=`590963fb81be064b8fcccbf78d6972d6a59f4d9278332ecf3cb773189402021c`。
- 新独立 POST：`native-post-e9514e53ef3948ccb7c5b24c8bb05c19` / `d41ee4f596af30475e9f502fd92bbe697ab5dc71e2e8048f97c31f06ea7cc92e`；Batch：`native-batch-eea404ef99b148b395c023b608b4d3fd` / `accb2830b8164f2dc1da1f15a7944459fd40dd9e131b6d5f4ae6a1959b2382a1`。二者 revision=1，保持 `content_check_status=PENDING`、`submission_status=NOT_SUBMITTED`。
- [真实写入子进程记录](../evidence/A03/execution/P2-R8-R3-post-hold/validation/native-r3-01/processes/n1-child/completed.json)：PID=31132，exit=87，barrier_released=true，timeout=false，alive=false。独立目标效果恰好一次；恢复核对没有再次写入。
- [写入前登记](../evidence/A03/execution/P2-R8-R3-post-hold/validation/native-r3-01/cases/N1/before-dispatch.json) 记录实际 `annotation` 导入根为本工作树 `src/annotation`。真实 child executable 为 `C:/Users/ASUS/AppData/Local/Programs/Python/Python39/python.exe`。各组运行器设置 `PYTHONPATH=<本工作树>/src`，产品索引与快照在启动前保存；此为源码运行证据，不是安装验收。

### N2 POST_HOLD 生命周期

[N2 完整结果](../evidence/A03/execution/P2-R8-R3-post-hold/validation/native-r3-01/N2-result.json) 记录两个实际接纳运行；SQL 正式行及观察/输入见 `database-readback.json` 的 `admitted_run_details`。

当前 hold=`target-drift-hold-f1a072d7cddb466e917b5c8724ffb338`。两次均绑定不可变 Resource `assets/runtime/7c0b219306dc9bd3004581f159f088b33bce017af2690f3331234551ad23a279.json`，其 SHA256 与文件名相同。

| 项目 | 第一次 | 正常 release/claim 后第二次 |
| --- | --- | --- |
| run | `native-pre-4dd87b75baac48cdb8325e5ccc5c9841` | `native-pre-c068e95bc1c84ed186db3752e1aefcb5` |
| generation / read_sequence | 4 / 6 | 5 / 7 |
| hold head sequence | 19 | 22 |
| hold head hash | `446cdb89321f87e8d04f9132fa28c9d0ac8b80d9949b012c14dc979321956b9a` | `9e70fa8c71077e4f880aa4d35f1b9adcf1644fe932914cb8eb8232a5f9860317` |
| PRE id | `pre-r8-r3-post-hold-1` | `pre-r8-r3-post-hold-2` |
| PRE hash | `b700b3e80d5f63d88e697190e6efd48eb080248261f0cf4a7ff8b4f7b63be4e1` | `15f47af69d5bf7fe5649a8d1949402e97c41e7dfee8dbdf61224f943fd31b91a` |
| observation | `native-observation-7a0d29d07e6a4fbca129660f3c093f53` | `native-observation-51b021a543ba4cb7a565e184ffb2ec02` |

owner id 均为 `process-5fe535be71354e0d84b783f42f5f7815`，中间通过正常 release/claim 改变 generation 和全书 head。旧 hold run 控制覆盖同一个实际 hold 下旧 owner/generation/head 的失效；未执行不同 hold-id 的替换，也未执行合格流程清 hold。

精确拒绝输出：

| 控制 | 实际 code |
| --- | --- |
| registry reopen 后旧 INITIAL 私有证明 | `NATIVE_ADMITTED_RUN_REQUIRED` |
| held book 上 INITIAL | `TARGET_DRIFT_HOLD` |
| held book 普通计划接纳 | `TARGET_DRIFT_HOLD` |
| 正常 owner/head 推进后旧 POST_HOLD run | `OWNER_GENERATION_STALE` |
| POST_HOLD 已接纳后普通写入 | `TARGET_DRIFT_HOLD` |
| 当前 hold 的 PRE 真实过期 | `NATIVE_PRE_DEADLINE_EXCEEDED` |

第二次 PRE 的 created=1792261121.8564236，实际等待至 created+60.1 后核验。N2 父进程 watchdog 单独设为120秒，以容纳产品原有60秒窗口的真实等待；未改变产品预算、单读上限、重试数或时钟，未 SQL 伪造资格。全过程 hold_clear_calls=0，permit/effect 总数仍各1，最终 owner 正常释放，hold 保持。

### N7 首次失败与冻结

[首次 stdout](../evidence/A03/execution/P2-R8-R3-post-hold/runs/N7/stdout.txt)、[完整 traceback](../evidence/A03/execution/P2-R8-R3-post-hold/runs/N7/stderr.txt) 及 [进程结果](../evidence/A03/execution/P2-R8-R3-post-hold/runs/N7/completed.json) 不改写。

`PersistentMockSession.open` 在 `src/annotation/delivery/mock/persistent.py:335` 先拒绝 `TARGET_STORE_VERSION_UNSUPPORTED`，随后 :342 的广义 ValueError catch 包装为外层 `TARGET_STORE_CORRUPT`；`ContractError` 属于 ValueError。R3 驱动依据显式版本拒绝分支增加的精确断言期望前者，实际得到后者，test exit1。该精确外层 code 预期尚未被独立确认成合同要求，因此本轮记录为诊断分类/断言差异；不能据此宣称 native 数据损坏，也不能宣称旧入口采用或重置了新库。旧入口实际拒绝是已经发生的事实。

在失败前，native runtime init/reopen 身份一致，旧 runtime 入口精确拒绝 `STATE_DIRECTORY_IDENTITY_MISMATCH`，native target 正常 reopen/adoption 一致。失败后未修改 `persistent.py` 或断言、未重跑 N7、未启动 N6；N7 中断初始化控制 `NOT_REACHED`。不因旧入口拒绝已发生而将 N7 改记 PASS。数据库 `migration=NOT_IMPLEMENTED_BLOCKED` 保持。

## 实际命令与复核入口

下面是已执行命令的记录，**不是本轮冻结后重跑指令**。cwd 均为上述工作树；每个 label 的原始 argv/cwd、脚本/输入/产品摘要、超时、PID 和二进制 stdout/stderr 均存于对应目录。

```powershell
python -X utf8 -B examples/a03/P2-R8-R3-post-hold/audit_a03_r8_r3.py run local python -X utf8 -B tests/test_a03_r8_r3_local.py -v
python -X utf8 -B examples/a03/P2-R8-R3-post-hold/audit_a03_r8_r3.py run N1 python -X utf8 -B tests/test_a03_r8_r3_post_hold.py R8R3NativeBridgeTests.test_N1 -v
$env:A03_R8_R3_TIMEOUT_SECONDS='120'
python -X utf8 -B examples/a03/P2-R8-R3-post-hold/audit_a03_r8_r3.py run N2 python -X utf8 -B tests/test_a03_r8_r3_post_hold.py R8R3NativeBridgeTests.test_N2 -v
Remove-Item Env:A03_R8_R3_TIMEOUT_SECONDS
```

N3、N4、N5、N7 分别使用相同 runner，label 与 `R8R3NativeBridgeTests.test_N3` / `test_N4` / `test_N5` / `test_N7` 对应，各一轮。N6 无 invocation。其余实际命令：

```powershell
python -B examples/a03/P2-R8-R3-post-hold/audit_a03_r8_r3.py run C01 python -B examples/a03/P2-R8-R3-post-hold/compat_a03_r8_r3.py C01 test_contracts*.py
python -X utf8 -B examples/a03/P2-R8-R3-post-hold/audit_a03_r8_r3.py run A02 python -X utf8 -B examples/a03/P2-R8-R3-post-hold/compat_a03_r8_r3.py A02 test_a02*.py
python -X utf8 -B examples/a03/P2-R8-R3-post-hold/audit_a03_r8_r3.py run R7 python -X utf8 -B examples/a03/P2-R8-R3-post-hold/compat_a03_r8_r3.py R7 test_a03_r7_readonly_codec.py
```

C01 保持普通 Windows Python 文本编码，以原始二进制方式保存子进程输出并按调用原有编码返回；未为其添加 `-X utf8`。兼容组的内部 subprocess 原输出及退出登记见 `nested-processes/`。观察子进程登记见各 `target/process-audit/`。原始运行日志不以 exit0 或测试数量代替业务边界。

文件复核入口：`python -X utf8 -B examples/a03/P2-R8-R3-post-hold/seal_a03_r8_r3.py check`。它只校验文件集合、pins、基线 raw Git 对象、报告链接、manifest 和已暂存 raw blobs，不执行产品或测试。

## 保全、释放与未覆盖范围

[原始保全结果](../evidence/A03/execution/P2-R8-R3-post-hold/preservation.json) 对基线30285条 raw Git mode/type/blob 逐项比较，除授权三个旧文件外30282条保持一致；旧证据、旧失败、旧夹具和驱动均未改。各实际组的产品 source index 相同，SHA256=`e78f63e7d4f05f8e132cb24e61c4072bb897d49243e173376998fd397505c5ae`。最终文件审计与 manifest 在本报告完成后生成，manifest 覆盖本轮全部改动/新增及原始输出，只排除自身；入库后核对 raw blobs，避免 EOL 转换影响证据。

[进程释放清单](../evidence/A03/execution/P2-R8-R3-post-hold/process-release.json) 汇总父子进程的 wait/exit/timeout/alive 登记；[系统 PID 回查](../evidence/A03/execution/P2-R8-R3-post-hold/process-os-readback.json) 只查本轮已登记 PID。未终止其他任务进程。最终冻结时工作树须干净。

[V01–V10 / R01–R18 逐项覆盖映射](../evidence/A03/execution/P2-R8-R3-post-hold/p2-coverage-map.json) 按同一 workflow 原定义登记，未将 R8 的单一完整 N1 或本轮成功控制替代原 P2 标准。主要剩余边界包括：多动作未尝试尾段、ABSENT 充分性、native 多书/多 scope、双 owner 竞争、其他崩溃点、合格清 hold/不同 hold-id、旧版 archive-validator、真实/ORIGINAL/OBSERVED 否定矩阵、S01、分母/跳过/重试极限及旧报告/VERIFIED 篡改。N6 和 N7 未达项明确未运行。

字段重置专项：`NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`。本轮零网络、浏览器、平台、凭据/profile、OCR、模型或付费 API、A05 题22重放、书级送交；未委派、推送、联系 B 或验收者，未修改根调度 state。B 包只读/HOLD 准备及双方映射确认保留独立边界。本轮仅交 REVIEW，后续独立验收和 I01 决策由调度负责。
