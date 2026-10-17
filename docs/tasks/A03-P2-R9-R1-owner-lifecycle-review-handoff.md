# A03 R9-R1 租约修复独立复验

原 A03 独立验收对话续接，保留用户的模型与思考强度。目标是复验已派发的四项有限范围，不扩展 P2 标准。本轮允许独立功能检查，不修改候选产品；这与上一轮只读故障分类不同。

## 冻结版本与交付

- base `c83f956c5c29c64ab10735ba11c153201d3f3f4b`；唯一 target **`bfd7fe896a7eee663ea8e0b6cf967548d8dd8f39`**。
- 执行 workflow `2aabd591695e73ecd4024c95e06fe0b71a2a9267`；执行任务 [A03-P2-R9-R1-owner-lifecycle-repair.md](A03-P2-R9-R1-owner-lifecycle-repair.md)。本复验单使用消息指定的调度提交读取。
- 执行报告：target 的 `docs/tasks/A03-P2-R9-R1-owner-lifecycle-report.md`，SHA256 `d4241688c338d988d122d177305b464ad7aa14e8531b0f6589b492f72cdf956e`。
- 执行证据前缀 `docs/evidence/A03/execution/P2-R9-R1-owner-lifecycle/`；manifest SHA256 `fa79fc21f550ea5491d2e122fb39b46976f9850666fe503423195ae90cdfd7be`；process-release SHA256 `91b63555dcea1c1eff0be18138a510e03e1db4e9c8e91a701db25e42e02bb098`。
- 调度 [交付预检](../evidence/coordinator/heartbeat-20261018-0544/delivery-preflight.json) 核实 491 个变更/新增 raw blobs、490 个 manifest 条目、31661 个旧条目不变、仅4份获准旧文件改变、15个登记进程退出。profile 仅两项 implementation pins 改变，adoption 仅 profile_sha256 链改变。预检没有调用产品或验收功能。

## 已知结果与独立判断

执行者 D1 正常返回/独立重开/防重复和 standalone publish 各首轮 exit0。borrow 组前置的四项非法参数拒绝、合法发布及 owner/generation/keeper 断言已经到达；随后驱动捕获 `sqlite3.IntegrityError`，实际共享事务包装为 `RuntimeFailure(STORAGE_TRANSACTION_FAILED)`，导致父/child exit1。原借用组保持 FAILED，`borrowed-owner-proof.json` 未写入，D2 NOT_RUN；不能补造旧证明或把作者失败改为通过。

先独立核对失败 traceback、驱动、storage transaction 包装和冻结双库，判断是驱动异常预期错误还是产品缺陷。若确认只是预期错误，**直接在本轮独立审查驱动中按现有接口写正确断言**，并在首次功能执行前登记源码/输入/预期；不用将明确的历史驱动问题来回派给作者才开始独立复验。不得修改 target 中原失败测试，不可 blanket catch 后当通过；须确认错误码及原因来自该唯一约束，核对没有第二次观察/报告/效果、借用者未释放外层租约。若诊断不同，应按证据报告而非套用作者结论。

## 静态范围与四项实际复验

从 exact target 取必要 src/config/固定 fixture/helper，使用自身隔离目录、全新 case；raw 字节与实际导入路径/摘要可核对。不要复制作者成功或失败数据库充当新运行，不复制整个旧证据历史，不接触作者工作目录中的活动库。产品、pins/profile/adoption、schema/oracle/verifier/producer 全部冻结。

静态检查两份 recovery diff、现有 `_lease` 适用语义与三个报告写入事务、standalone/borrowed 释放责任。保持 ACTIVE/PID/instance/generation/lease、pending/hold、单次报告读和2秒观察限额；legacy 分支保全可静态核对，不宣称全套动态 legacy 验收。

下列每组只在独立新 case 运行一轮。可以正常 import 冻结 helper 或写自己的薄驱动；不得 AST/exec 裁剪、monkeypatch 产品或 SQL 改业务状态。若复用作者驱动，静态核对其断言，不照搬已知错误期待；审查改动只能在自己的新驱动文件，完整记录差异和理由。

1. **D1**：原固定32×32单题两片段，正常 PRE/admit/targetcheck/planner/record → 独立进程 run_plan FINISHED → 正式 POST/Batch PENDING/NOT_SUBMITTED。另一进程重开及支持入口同计划拒绝，effect 始终1；区分报告阶段 generation 与重复入口自身 claim/release 的 generation。检查正式 plan/action/intent/receipt/fact/POST/Batch 及资源绑定，不能仅看返回码。
2. **standalone**：全新合法完整 receipt、报告读尚未消耗的 case，通过既有产品支持流程形成。原 owner 正常释放后，独立 publish 自行 claim/publish/release；报告读、正式产物及事件次数准确。
3. **borrowed**：仅 owner、仅 generation、过时 generation、他属 owner 均拒绝且无报告读/效果/释放；合法 pair 发布成功，无新增 claim/generation，外层 keeper 和 ACTIVE 租约保留。先落盘合法借用证明，再做同一计划单次报告读负控；按当前接口核实包装错误及完整前后计数，不能用错误异常捕获掩盖结果。
4. **D2**：原 R9 已授权的全新 AFTER_INTENT_COMMIT 真正 exit90，后续新进程读出 UNKNOWN，然后原一次有界完整 ABSENT 对账和旧计划不重放；从持久化事实核对 attempt_fact，不能为预期字符串改事实。只检查原 D2 范围，不实现新计划、不扩展不足 ABSENT/混合尾段。

父 watchdog90秒、child45秒；观察2秒及 lease/PRE时限保持。功能首败或超时即停剩余组，保留原现场，报告确切未到达点，不改产品或驱动循环重跑。首轮运行前的静态准备可以修正；执行后单纯元数据封存错误最多一次静态纠正，保留首错，不能借此重跑产品。无整套旧组回归、原 R3/R4 重演、额外故障点或新增验收轮次。

## 交付与状态

报告 `docs/tasks/A03-P2-R9-R1-owner-lifecycle-review-report.md`，证据仅 `docs/evidence/A03/review/P2-R9-R1-owner-lifecycle/`。提供每组独立结果、正式引用与原库快照、raw stdout/stderr、冻结脚本/输入/实际产品摘要、登记 PID/exit/timeout/alive、进程释放和 SHA256 manifest；报告保留作者原 borrow FAILED/D2 NOT_RUN，与本轮独立结果分开。

只对这次 ownership 修复及四项有限演示给 ACCEPTED/REWORK/BLOCKED；整个 native A03、原 P2 广覆盖和 I01 不因此放行。执行测试原失败证据不覆盖、不篡改为成功；若独立新驱动通过，其自身为新增复验证据。最终集成与状态由调度决定。

字段重置 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION` 原样保留，禁止重跑、变体、委派或建议重测。不新建子智能体，不访问平台、浏览器/profile、凭据、B 对话、付费模型，不推送，不重放 A05题22，不书级送审。保留用户现有 model/thinking 和所有旧证据字节。
