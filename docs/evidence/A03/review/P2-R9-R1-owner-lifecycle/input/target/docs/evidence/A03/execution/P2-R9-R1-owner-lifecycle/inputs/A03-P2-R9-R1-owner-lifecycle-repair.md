# A03 P2 R9-R1：报告发布复用当前租约

本任务是一次有界产品修复，处理已独立确认的 `OWNER_BUSY` 正常路径缺陷，随后提交独立复验。A03 原执行对话续接，保留用户设置，省略 model/thinking；不新增任务对话或子智能体。

## 输入与范围

- 唯一执行基线 `c83f956c5c29c64ab10735ba11c153201d3f3f4b`，工作树 `C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800`，分支 `codex/a03-runtime-recovery`。先确认 clean；不要合并浮动调度分支。
- 读取本次派发消息给出的调度提交中的 [调度判定](A03-P2-R9-failure-coordinator-decision.md)、[独立复核](A03-P2-R9-failure-review-report.md)，以及既有 [R9 原任务](A03-P2-R9-minimal-demos.md)。独立报告 SHA256 `8c8302ff0ca1e4adb69d4c22de4131ca8ba713494a485f02d7fd89d2448e3a0e`；清单 SHA256 `9940f5501acd392a5a29fbdddc7ffd249b6632d35a1ce7e370a95ae1d64f75a7`；释放证明 SHA256 `791686a788d9db5e33cb79c2b0fe89937f4956b1ea49f8e016cd8a75be00985a`。从 raw Git 读取确切输入，只复制需要的文档，不复制整个历史归档。
- 允许修改的已有产品文件仅 `src/annotation/runtime/recovery/__init__.py`、`src/annotation/runtime/recovery/native_quality.py`，以及 `src/annotation/contracts/a03_native/data/profile.json` 的上述两项 implementation_pins 摘要和 `adoption.json` 的 profile_sha256。其他 profile/adoption 字段、全部其他 pins、schema/API/interface/oracle/verifier/producer、storage.claim、根依赖均保持原样。
- 新增验证只放 `tests/test_a03_p2_r9_r1_owner_lifecycle.py`、`examples/a03/P2-R9-R1-owner-lifecycle/`、`docs/evidence/A03/execution/P2-R9-R1-owner-lifecycle/` 及 `docs/tasks/A03-P2-R9-R1-owner-lifecycle-report.md`。允许在该新目录建立最小 fixture，既有 helper/fixture/报告/证据逐字节保留。不得写根调度 state。

## 必须实现的行为

1. `run_plan → publish_quality → publish_native_quality` 显式传递当前 owner/generation。有效租约经现有实例、PID、ACTIVE、generation、lease 校验后供报告发布使用，不再重复 claim，不新增 generation。
2. 借用租约的报告函数不得停止外层 keeper 或释放外层租约；由 run_plan 既有 finally 负责结束。独立 publish 不带借用参数时仍自行 claim，并仅释放自己取得的租约。部分参数、过时 generation、他属 owner 必须拒绝，不得降级为重新 claim，不得释放调用者租约。
3. 保留每次报告落库前的事务租约检查、报告上下文原有 pending/hold 语义、durable 单次报告读与2秒独立观察预算；不扩大普通写入权限，不放松共享 OWNER_BUSY，不提前 release，不吞掉报告发布错误或补造成功。
4. 保持已有 legacy 调用行为；同步两项实现摘要及 profile/adoption 链，不通过放宽 pin 校验让变更运行。必要改动如超出上述范围，先交确切阻塞与建议，不自行扩大。

## 四项有界验证

实施与静态检查完成后，先冻结产品/驱动摘要，按下列顺序运行，每个组一次，使用首次不存在的新 case。功能首败即停止本轮剩余功能组，保留完整现场、实际到达范围和未运行项；不在同一交付中边改边循环到成功。新 metadata/路径错误可有一次静态修正，保留首错，不能借此重复产品执行。

1. **D1 正常路径**：固定32×32、单题两片段，经正常 PRE/admit/targetcheck/planner/record，独立执行进程 run_plan 成功返回 FINISHED；正式 POST/Batch 为 PENDING/NOT_SUBMITTED。新进程从落盘状态重开查询，并经支持入口验证同计划不重复效果，effect 始终1。不得用原失败库继续写、重放其动作或手工补报告。使用原 R9 要求的可搬运相对路径、实际引用和版本证据。
2. **独立 publish**：新的合法 case 经产品支持流程产生完整正式 receipt、尚未消耗 report-read；不直接 SQL 改业务状态、不借用已发布 D1 的读额度。验证 standalone 入口自行 claim/publish/release，正式报告与当前 receipt/fact/读回关联。
3. **借用参数边界**：合法借用不新 claim/generation、不提前 release；部分参数（仅 owner / 仅 generation）、过时 generation、他属 owner 均拒绝且调用方租约不被释放。观察报告读/写状态的实际变化，维持原读取限额与 fencing。无需新跑整套历史并发矩阵，不能 monkeypatch 产品或直接写数据库伪造通过。
4. **原 R9 D2**：全新 case，在原 AFTER_INTENT_COMMIT 真正退出90；后续新进程只读 UNKNOWN，再进行原授权一次有界完整 ABSENT 对账，保留实际 attempt_fact，旧计划不得重放。不借机实现新计划或不足 ABSENT/混合尾段等原未覆盖项。

不重跑原 R3/R4 已通过组、原 N7 失败或整套兼容测试；本修复若暴露已知范围外问题，应停止并具体报告。每个功能父进程 watchdog90秒、效果 child45秒，原观察2秒及产品 lease/PRE时限不改；超时记录准确退出与释放，不能后台继续。

## 交付和后续

交付确切 commit、上述报告、逐文件 SHA256 manifest、可复现命令、首次失败（若有）、新 case 原始 stdout/stderr、脚本与输入/实际导入摘要、PID/exit/timeout/alive 及自有进程释放。报告明确四项结果及没运行的部分，解释最小差异和两条 ownership 生命周期。与基线逐文件核对只改四份获准产品文件，其他旧文件保持原字节；新增证据做 raw Git blob 核对。避免扩大历史复制和全库测试开销。

执行者交付为 REVIEW，不自行记 ACCEPTED。独立验收对确切修复提交复验这四项，调度核对后才决定本范围是否接受；原 P2 广覆盖缺口和整个 A03/I01 依赖继续保留。不得将本次内部 pins 更新视为 B 共同确认。

字段重置仍为 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`，禁止重跑、变体、委派或建议重测。无真实平台、浏览器/profile、凭据、OCR、付费模型、原始视频、A05题22重放、书级送审、B联系、推送或强推。所有测试仅离线 SYNTHETIC，不扩充固定语言和题数。
