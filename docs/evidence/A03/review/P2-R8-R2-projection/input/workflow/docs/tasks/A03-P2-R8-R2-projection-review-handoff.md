# A03 P2-R8-R2：投影修复、完整 N1 与 POST_HOLD 阻断独立验收

2026-10-18（Asia/Shanghai）。继续原独立验收对话 `01a145aa-8d59-7c70-8d81-731712103a9a`；保留用户 model/thinking，不委派、不联系 B 或执行者，不改执行工作树。固定 target `58d8a64734271d15654bb00b03d760f0f3eccd10`，base `a0c40886f3076f84c46377e03fc2206d2fdc5585`，产品/辅助源码提交 `002c26795822fe8518117793f59598b3eceab02e`。

本轮执行者称 N1 已完整通过；N2 在真实 hold 后启动 POST_HOLD PRE 时被默认 lease 守卫拒绝。分别核定投影缺口是否关闭、N1 有限功能是否通过、N2 具体缺口及整个 A03 仍未完成的范围。不要把前缀或作者汇总替代验收，也不要为已经确认未通过的 N2 重新跑整套链路。

## 固定输入与已完成前检

- 执行 workflow `016e048669e5af1f193e71968d03bf3000cf16d1` 的 [R8-R2 任务](A03-P2-R8-R2-projection-rework.md)，SHA256 `c76ef2a47fa9bbfecb83b05e02cfe56a6599c68600786d2a86eb9547c35fb3e0`。
- target 的 `docs/tasks/A03-P2-R8-R2-projection-report.md`，SHA256 `8fd88d3f19de8a853f8649412ecbef9cae4c453c689b2540413d206db0178421`。
- target 的 `docs/evidence/A03/execution/P2-R8-R2-projection/manifest.json`，SHA256 `5b5a3cc998c05fbe4ac3d044bac8bfd1b468b24d7b3e71adb7b78a7db397684c`。
- 同目录 `process-release.json`，SHA256 `6119e12e0b7b35c09c60b89eb32aa4445c4806c6fd73b365adb1394910425875`；`bounded-outcome.json` SHA256 `e20b2567885408ea6edbc37ea51952cfdcccb5ca3ab44036e782ed3b10212bfe`；`database-readback.json` SHA256 `b5564cad9c89fcbf2c158989505a61f6a7fbd543984164c93d8f7ca942db34f5`。
- [调度前检](../evidence/coordinator/heartbeat-20261018-0127/A03-R8-R2-delivery-preflight.json)已核对 581 条清单及自身、582 个确切变化路径、base 的 29,703 个未变旧条目，以及 26 组登记/PID/完成/输出；工作树干净且执行 turn completed。这是交付前检，尚非功能验收。

## 有界核验范围

1. **产品修复及身份。** 仅共享 storage `_project_plan_locked`/私有 `_progress_attempt` 与对应 profile/adoption pins 改变。有 fact 时完整 plan/action/digest/intent 绑定后使用原尝试分类与证据副本；无 fact 分支保持旧语义。合同守卫、Schema、native commit_reconciliation、producer、旧失败等保留。核对源码、最小正负分支记录及实际使用的 pins，不放宽守卫或补造事实。
2. **作者 N1 的正式边界。** 从原 stdout/stderr、屏障、PID/退出、必要的自有 immutable SQLite 副本和实际 Artifact/Resource 原件，核对 PRE ADMITTED、单次 permit、目标效果一次、子 exit87、原 UNKNOWN/原回执缺失、终局 head.original_receipt_ref=null、晚到正式 receipt/progress 的四项一致及尝试证据、独立新 POST/Batch 的正式登记。SQL artifacts、当前包与 intent.receipt 须一致；区分历史副本与未登记候选。内容仍 PENDING、NOT_SUBMITTED。
3. **独立完整 N1 复现一次。** 从 exact target 原始 blob 导出必要产品、Schema/pins、固定合成输入及有限驱动到自己的隔离目录，用全新双库、全新 run id 正常导入产品。可以静审后采用 target 的固定 N1 测试作驱动，只调用 `R8R2NativeBridgeTests.test_N1`，另以独立只读查询/原件比较核对正式登记、四项一致、原 UNKNOWN 和效果数。不得从执行树 import、修改产品、补数据库行或依赖作者成功库/当前证据；记录实际源码身份及导入路径。只运行一次，不顺带执行 N2–N7、原静态全矩阵或兼容全套。出现失败即保留原始失败并收口，不修改候选或重复功能运行。
4. **N2 首次失败的只读定位。** 不重跑 N2。核对受控目录变更产生的真实 hold 与旧 INITIAL 拒绝；从失败原栈、`begin_native_pre`、`_lease` 及持久状态确认 POST_HOLD 分支是否被默认 `pending_ok=False` 的 hold 守卫提前拒绝，是否没有新 POST_HOLD run/接纳/清除。指出最小修复所在接口和必须保留的普通写入守卫；不得尝试清 hold、改字段或授权恢复写入。N3–N7 未运行须保留。
5. **兼容与释放。** 只核对最终候选 C01 70、A02 52、R7 13 的原始日志及相同产品摘要，不重跑。26 个登记进程退出记录与 N1 预期子 exit87、N2 真失败、C01 预期拒绝分别对齐。另有一次封存辅助命令 PowerShell SyntaxError：只有工具 chunk/exit 与明确标注的转录，未提供 PID/raw 分流日志；报告如实记录该证据限制，不伪补原始日志，也不把它当作 N1/N2 产品结果。

独立运行的父子进程先登记 argv/cwd、脚本/输入/产品摘要和限时，原始 stdout/stderr、PID、退出/timeout/alive 全部保留并 wait。复制原数据库后仅以 `mode=ro&immutable=1` 与 query_only 检查，读取前后摘要保持；不打开执行者原库。只导出必要输入，旧历史用 raw Git mode/type/blob 差分保全，不复制全集。

## 输出与限制

新增 `docs/tasks/A03-P2-R8-R2-projection-review-report.md` 与 `docs/evidence/A03/review/P2-R8-R2-projection/`；不改根 state、旧报告或旧证据。给出 exact inputs、静态结论、独立 N1 实际结果及产物绑定、N2 最小缺口、未覆盖项、进程释放和只排除自身的清单。若 N1 通过可明确其有限功能范围；N2 未通过则整个 R8/A03 仍为 REWORK，不自行 INTEGRATED 或释放 I01。原 P2 V01–V10/R01–R18 未豁免。

字段重置专项始终 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`；N1 复现不授权该专项或其变体。零网络、浏览器、真实平台、凭据/profile、OCR、模型/付费 API、A05 题22重放、推送或 B 消息。新发现的其他独立问题只报告，不扩大矩阵、修产品或另起任务。
