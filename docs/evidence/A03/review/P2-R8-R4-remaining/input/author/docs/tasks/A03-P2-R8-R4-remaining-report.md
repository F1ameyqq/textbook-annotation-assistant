# A03 P2-R8-R4 剩余验证交付

2026-10-18（Asia/Shanghai）。状态：**REVIEW**。本轮全新 N1 前序、N6 完整创建输入/UNKNOWN 历史重算及明确缺失依赖负控、N7 尚未到达的 runtime 初始化中断控制，各一轮成功。只新增验证与证据；产品、pins 和全部历史原件未改。A03 整体和 I01 未释放，执行成功不等于独立验收。

## 固定身份与范围

- 工作树：`C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800`；分支：`codex/a03-runtime-recovery`。
- 唯一 base/产品版本：`d9ed692db9ab8e9277f8ffd09e040451e8b8f65f`，接单时 tracked/untracked 状态干净。
- workflow：`cb9c8f76e9eae40a8fda042c196705d7258b5107`；派发键：`A03:execution:P2-R8-R4-remaining:d9ed692db9ab8e9277f8ffd09e040451e8b8f65f`。
- [任务原件](../evidence/A03/execution/P2-R8-R4-remaining/inputs/A03-P2-R8-R4-remaining-validation.md) raw SHA256：`5a93ea9012ad8d9d2f69e622235051cbf1ced23922e1e6fc021c4443657e184b`。
- [R3 独立报告原件](../evidence/A03/execution/P2-R8-R4-remaining/inputs/A03-P2-R8-R3-post-hold-review-report.md) raw SHA256：`a39afab68c15837122a34fb0f75dca7cae339dd2ba1be13dde007971b99b9a17`；[调度结论原件](../evidence/A03/execution/P2-R8-R4-remaining/inputs/A03-P2-R8-R3-post-hold-coordinator-decision.md)。采用其中 POST_HOLD/local/N1–N5 有限接受及原 N7 诊断断言过强的分类，不重跑其旧 target 入口或变体。
- 最终交付提交为本报告、R4 新驱动及证据所在 clean HEAD，确切 SHA 由交付消息/Git 日志提供，避免报告自引用提交哈希。没有合并浮动主树、推送或修改根 state。

新增代码仅 [R4 测试入口](../../tests/test_a03_r8_r4_remaining.py) 和 [R4 驱动目录](../../examples/a03/P2-R8-R4-remaining)。没有新建 fixture；使用已接受的固定合成 R3 夹具。未运行 local/N2–N5、兼容套件、旧矩阵或字段重置专项。

## 启动前冻结与路由

[输入登记](../evidence/A03/execution/P2-R8-R4-remaining/inputs.json) 保留6份确切 workflow raw 文档、base tree 摘要和旧驱动/产品/原 N7 stderr 引用摘要；只导出必要文档，没有复制审阅历史全集。[启动前驱动登记](../evidence/A03/execution/P2-R8-R4-remaining/driver-preregistered.json) 在产品运行前完成语法与字节冻结。

| 新执行文件 | 实际执行/最终字节 SHA256 |
| --- | --- |
| `tests/test_a03_r8_r4_remaining.py` | `27d1969548011b044c21b77a121c53b5bef90d4aa0b19aef95f65b8d692f9a3d` |
| `examples/a03/P2-R8-R4-remaining/audit_a03_r8_r4.py` | `0c86b9fc9e6fde9f447ccb58563bd7af1b6b45f3a5aa8d30304cc75740fd087e` |
| `examples/a03/P2-R8-R4-remaining/prepare_a03_r8_r4.py` | `f09be00c2e2cfcdb24d9e3ed9c0f6c868cb5151404fbff631a8317984680fd2e` |

[路由登记](../evidence/A03/execution/P2-R8-R4-remaining/routing.json) 明确：正常 import `test_a03_r8_r3_post_hold`，调用原 `R8R3NativeBridgeTests.test_N1`，只把测试模块 `EVIDENCE`、`BASE_EVIDENCE` 显式指向本轮新目录。原方法、child 入口和文件字节不改，无 AST/exec 裁剪导入、产品 monkeypatch 或 SQL 伪造。child 接受显式 R4 case 路径；它写入新 R4 双库，不写旧 R3 输出。

固定 fixture 的逻辑标签（例如 `plan-r8-r3-n1`、ledger/store 标签）沿用原方法；实际 run、observation、intent、receipt、resolution ID 及计划完整四元组均在首次不存在的 R4 目录中生成。没有复制或继续旧数据库。新产物位置为 `docs/evidence/A03/execution/P2-R8-R4-remaining/validation/r4-native-01/`。

## 一轮实际结果

| 组 | 父 PID / exit | 实际范围 |
| --- | --- | --- |
| N1 | 64524 / 0 | 原完整 N1 方法；25.142秒；新双库、真实屏障/child exit87、唯一效果、原 UNKNOWN/null 原回执、正式晚到 receipt/progress/POST/Batch |
| N6 | 66384 / 0 | 3.360秒；完整20-artifact 历史，正常 verifier 内实际重建计划；明确缺失正式 PRE EvidenceRecord 一次，闭包层拒绝 |
| N7 初始化 | 45008 / 0 | 0.384秒；既有 `before_completion` 钩子同进程受控异常一次，正常 open fail closed |
| 冻结只读回查 | 18444 / 0 | stdlib SQLite immutable/query_only；不导入或调用产品，不复跑任何组 |

三组均无 timeout、alive=false；原始父/子 argv/cwd、脚本与输入摘要、产品索引、启动 PID、原二进制 stdout/stderr、exit/timeout/alive 均在 `runs/`、`validation/r4-native-01/processes/` 和各目标 `process-audit/`。没有产品语义失败或失败后重跑。

### N1 必要前序

[N1 结果](../evidence/A03/execution/P2-R8-R4-remaining/validation/r4-native-01/N1-result.json) 保持原完整标准。实际效果 child PID=60488，exit=87，barrier_released=true、timeout=false、alive=false。父进程在目标 SQLite 效果已提交而 child 尚在屏障时独立计数为1；后续恢复只读核对，最终 effects=1。

原 UNKNOWN progress 保留、原 receipt_ref=null；正式晚到回执四元组与 SQL artifacts、intent.receipt、current bundle 一致；material progress 的 plan/action/intent/attempt、原 fact 和尝试证据一致。新 POST/Batch 正式登记，内容仍 PENDING、NOT_SUBMITTED。关键正式引用均 revision=1：

| kind / artifact_id | content_hash |
| --- | --- |
| ApplyPlan / `plan-r8-r3-n1` | `f72f0c1688ba5e7d2e9388bc7baece5cda759f369907730a08ea8f3e6565e435` |
| ExecutionReceipt / `executionreceipt-4b3810d747fe452cb20c27fabb0abcbf` | `7ad64cc31359c90cbc67e2d47a6a96a275036d7b91cda7177942e216287ebd5f` |
| ReconciliationResult / `resolution-3452cf8e9d5c4e079895de4397934a4d` | `825650c877afeac21feb38bb5a2bf0103ba2f76af914507ebe5b343f690c4f7b` |
| CheckReport / `native-post-94aefc2629be453ca54a09c12c0e03a2` | `28cfd252ee5be44185b24ebc5ac85377a47fa9b35f9218be591dc01dbd2eb6c2` |
| BatchReport / `native-batch-461053ffc2e3458dac6f963e589253f7` | `fc9995e67a0c3b896497469e07a84eb20c84e7f53e578b805d35c8fdc7c588f8` |

### N6 正常重算与一个明确依赖负控

[N6 结果](../evidence/A03/execution/P2-R8-R4-remaining/validation/r4-native-01/N6-result.json)、[完整当前历史](../evidence/A03/execution/P2-R8-R4-remaining/validation/r4-native-01/N6/full-current-history.json) 和 [creation anchor 正式 SQL 行](../evidence/A03/execution/P2-R8-R4-remaining/validation/r4-native-01/N6/creation-anchor-SQL.json) 保留了完整20个 artifact：原 UNKNOWN、晚到 receipt、resolution 和新 POST/Batch 均未裁剪。未过滤后代、重封签或降级版本。

正常 `verify_generated_plan` 从登记的 creation input 重算同一个 plan；该历史创建输入本就属于产品正式 anchor，和传入 verifier 的完整当前历史分别保存。使用只观察 return 的 `sys.setprofile` 捕获这一次产品内部 `create_plan` 的真实返回及 `resource_manifest`，不改参数/结果、不额外调用 planner。只有一个实际重算计划。

- anchor canonical 原字节 SHA256：`3d9b5f62304ed6c01e33c6dd7867a4775892106927937210afc6f6b861bacc9a`，与 SQL input_sha 及 objects 原件一致。
- [原计划 canonical](../evidence/A03/execution/P2-R8-R4-remaining/validation/r4-native-01/N6/original-plan-canonical.json) 和 [实际重算计划 canonical](../evidence/A03/execution/P2-R8-R4-remaining/validation/r4-native-01/N6/recomputed-plan-canonical.json) 字节相同，SHA256=`ff6805e33e3b3f02239cfe00d426f7b660c2ff1414b9d46f487dcb21238d503f`；完整四元组及全部 action 内容相同。这里的完整 JSON SHA 与四元组 content_hash 是两个不同摘要口径，未混用。
- SQL manifest 的6份 Resource 与实际消费清单相同，逐份读实体核对长度与 SHA，见 [资源读回](../evidence/A03/execution/P2-R8-R4-remaining/validation/r4-native-01/N6/consumed-resource-readback.json) 和 [实际 return 捕获](../evidence/A03/execution/P2-R8-R4-remaining/validation/r4-native-01/N6/actual-recompute-returns.json)。

负控明确删除 PRE `pre-r8-r3-N1` 的 `checks[0]`（`source_integrity`）通过 evidence_refs 正式消费的 EvidenceRecord：`native-pre-proof-d0e80e8eb13991aa42ff69695819e20ead02923b`。其 Resource 为 `assets/native-pre/d0e80e8eb13991aa42ff69695819e20ead02923b74cc4fa1de0ff2e873592c89.json`，SHA 与文件名相同。[消费者登记](../evidence/A03/execution/P2-R8-R4-remaining/validation/r4-native-01/N6/missing-dependency-consumer.json) 记录完整 PRE 四元组与该 record；[缺失副本](../evidence/A03/execution/P2-R8-R4-remaining/validation/r4-native-01/N6/missing-dependency-input.json) 只在新内存输入中移除这个 record，原 anchor 和 Resource 不改。

正常 native historical context 入口在闭包层拒绝 `StaticCodecError/EVIDENCE_ID_MISSING`，实际 path=`pre-r8-r3-N1/checks/0/evidence_refs[native-pre-proof-d0e80e8eb13991aa42ff69695819e20ead02923b]`。依据现有闭包合同选择断言，原异常及 traceback 保留于 [负控原输出](../evidence/A03/execution/P2-R8-R4-remaining/validation/r4-native-01/N6/missing-dependency-refusal.json)，没有新增任意外层错误码要求。

N6 正例和负控前后双库 raw SHA 相同，permits=1、effects=1，新增 permit/effect=0；原 anchor bytes 相同。

### N7 尚未到达的初始化中断

另一个首次不存在的 `cases/N7-before-completion/` 中正常调用 `init_native_state(..., before_completion=stop)`。钩子恰好调用一次，抛出并原样传播 `ControlledStop`，见 [受控原异常](../evidence/A03/execution/P2-R8-R4-remaining/validation/r4-native-01/N7/original-controlled-interruption.json)。这是既有钩子的同进程受控异常，不是进程崩溃证明。

保留的 runtime.sqlite3 已建表，但 meta=0，无 initialization=COMPLETE，anchor.json 不存在。随后正常 `open_native_state` 一次，以 `STATE_DIRECTORY_IDENTITY_MISMATCH` 拒绝，原因保留为缺失该 anchor 的 FileNotFoundError，见 [open 原拒绝](../evidence/A03/execution/P2-R8-R4-remaining/validation/r4-native-01/N7/normal-open-refusal.json)。没有创建 anchor、续写完成标记或恢复初始化再试成功。

该 runtime 的 plans/intents/permits 表存在且行数均0；target 目录/数据库未创建，效果记 **NOT_CREATED**，不伪造不存在表的零行查询。runtime 在 open 前后字节一致，详见 [N7 结果](../evidence/A03/execution/P2-R8-R4-remaining/validation/r4-native-01/N7-result.json)。本例只覆盖 runtime 的这个钩子，未证明目标库全部初始化中断点；迁移仍 `NOT_IMPLEMENTED_BLOCKED`。

原 R3 N7 FAILED/stdout/stderr 永久原样保留，仅静态引用 [原 stderr](../evidence/A03/execution/P2-R8-R3-post-hold/runs/N7/stderr.txt)，SHA256=`0c5670e4e345ad9c55020d83851ea971c0dbc4a865899b425c15241847706fc5`。本轮未重跑原旧 target 入口或变体、未改 persistent.py、未把原 FAILED 改为 PASS。

## 原始双库及导入身份

[纯读取 SQL 回查](../evidence/A03/execution/P2-R8-R4-remaining/database-readback.json) 使用标准库 `mode=ro&immutable=1`、connection-local `query_only`，读前读后字节相同，三个实际库 quick_check 均 ok，未调用产品。正式关键 artifacts refs 均与完整当前历史相同。

| 库（相对 validation/r4-native-01） | 原始 SHA256 / 状态 |
| --- | --- |
| `cases/N1/runtime/runtime.sqlite3` | `46e9bb060b4b06ce1c5c76b81e29ee42df187fbc457fb90f90e2af7324c01199` |
| `cases/N1/target/target.sqlite3` | `97016773ba0265a0625c54a38c06c9b0ceeade4368f55e9f25db046005d82126` |
| `cases/N7-before-completion/runtime/runtime.sqlite3` | `dd19ba8a492195879043099bb964c4a086aa6bc8077193c139fe2bfad5aecf0d` |
| `cases/N7-before-completion/target/target.sqlite3` | NOT_CREATED |

主 runtime 有20个 artifacts、1 creation anchor/PRE/plan/action/intent/permit/resolution/report read；target 有4次实际观察及唯一效果。没有 N2 hold 生命周期产物。

实际 Python 为 `C:/Users/ASUS/AppData/Local/Programs/Python/Python39/python.exe`；[N6 实际导入登记](../evidence/A03/execution/P2-R8-R4-remaining/validation/r4-native-01/imports/N6.json) 及各组 imports 记录 module.__file__ 和原 SHA。native.py 实际路径为本工作树 `src/annotation/runtime/storage/native.py`，SHA=`c3e2f01ccbfb7b64c49a5272eb51ffbe2f6af8c8abb5a51c4c9c6965166b902a`；profile=`023078c2a8bdfd1f3cc80eb6effdfc31010284464584218cbb77f3c4583c921a`，adoption=`24d6529f2fcb9a386b0c52ab46f7551ee8c8701350351c88b241621fdec4477f`，均与 base 原字节相同。这是源码执行记录，不是安装验收。

## 命令、保全与覆盖

以下为已执行的一轮命令记录；cwd 为上述工作树，各组父 watchdog=60秒，原 N1 child=45秒，产品观察/租约参数未改：

```powershell
python -X utf8 -B examples/a03/P2-R8-R4-remaining/prepare_a03_r8_r4.py
python -X utf8 -B examples/a03/P2-R8-R4-remaining/audit_a03_r8_r4.py run N1 python -X utf8 -B tests/test_a03_r8_r4_remaining.py N1
python -X utf8 -B examples/a03/P2-R8-R4-remaining/audit_a03_r8_r4.py run N6 python -X utf8 -B tests/test_a03_r8_r4_remaining.py N6
python -X utf8 -B examples/a03/P2-R8-R4-remaining/audit_a03_r8_r4.py run N7 python -X utf8 -B tests/test_a03_r8_r4_remaining.py N7
python -X utf8 -B examples/a03/P2-R8-R4-remaining/audit_a03_r8_r4.py run frozen-readback python -X utf8 -B examples/a03/P2-R8-R4-remaining/readback_a03_r8_r4.py
```

已存在的输出根使用 exclusive 创建，原路径不能直接再运行；命令用于独立验收在新输出根准备时复现，不在本轮原目录复跑。只做文件复核可运行 `python -X utf8 -B examples/a03/P2-R8-R4-remaining/seal_a03_r8_r4.py check`，它不执行产品或测试。

最终文件审计以 raw Git mode/type/blob 逐项比较 base 全部31167个条目，无旧文件例外；再核对当前工作树、实际执行驱动摘要和三个相同产品索引。manifest 包含本轮全部新增、证据及原输出，只排除自身，入库时再次验证 raw Git blobs。没有复制历史全集。提交后以 clean status 冻结。

[进程释放清单](../evidence/A03/execution/P2-R8-R4-remaining/process-release.json) 记录全部自有父子进程已 wait/退出；[系统 PID 只读回查](../evidence/A03/execution/P2-R8-R4-remaining/process-os-readback.json) 仅检查本轮已登记 PID，未终止其他任务进程。

[小型覆盖映射](../evidence/A03/execution/P2-R8-R4-remaining/coverage-map.json) 按原 N1–N7 和原 P2 V01–V10/R01–R18 逐项更新：本轮仅新增完整创建输入/历史重算、一个明确缺失依赖及 runtime before_completion 中断分支；R3 有限接受静态引用。原 N7 FAILED 保留。多动作/ABSENT、native 多 scope/多书、双 owner 竞争、其他崩溃点、不同 hold-id/合格清 hold、archive-validator/转换、真实/ORIGINAL/OBSERVED/S01 否定矩阵、旧报告/VERIFIED 篡改及分母/重试上限等未覆盖要求未豁免，没有塞入本轮执行。

字段重置专项始终 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`。未委派、修改用户 model/thinking、使用网络/浏览器/真实平台/凭据/profile/OCR/模型或付费 API、A05 题22重放、书级送审、联系 B/验收者、推送或改根调度 state。最终仅交 REVIEW，独立验收、集成和 I01 决策留给调度。
