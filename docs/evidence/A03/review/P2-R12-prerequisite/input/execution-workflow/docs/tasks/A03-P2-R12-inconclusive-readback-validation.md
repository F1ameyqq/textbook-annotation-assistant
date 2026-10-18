# A03 P2-R12：原 V03/R05 异常读回五例

2026-10-18（Asia/Shanghai）。原 A03 执行对话 `01a145aa-2fea-7942-97f9-ad260acf4e30` 续接；冻结交付后使用原独立验收对话。唯一 base `cc5966dc58c62017a27266c40ca0cedc5c68485c`；原工作目录 `C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800`，分支 `codex/a03-runtime-recovery`。workflow 为派发消息给出的确切调度提交。保留用户 model/thinking，不委派，不合并浮动主目录。

## 范围与固定准则

仅完成[原执行任务](A03-runtime-recovery.md) V03、[原验收标准](A03-independent-review.md) R05 中尚未覆盖的部分生效、重复身份、矛盾、截断、不可用读回。MATCH/ABSENT 已有有限证据，[R11 四切点](A03-P2-R11-crash-cuts-coordinator-decision.md)已收口，均不重跑。本轮不修改产品，不新增故障机制或合同，不扩大为整个 A03 验收。

沿用固定 32×32 单题两片段 SYNTHETIC 语言；每例用全新空目录、原始固定输入及正常 init/register/PRE begin/produce/admit/targetcheck/planner/record，保持同一合法 owner/generation/PRE 上下文。只用已有 `effect_fault` / `read_fault` 公开接缝。首次功能运行前，静态核对当前源码的真实 API、错误包装及各分支，再冻结驱动、输入和预期；入口不支持或准则冲突时记录具体位置并停止，不写产品或改标准。

每例先经受支持的 accept/prepare/commit_intent/issue_first_dispatch/dispatch/observe/commit_action_result/project 流程形成一个真实未决动作和正式 UNKNOWN，不复制旧库、不自行构造运行证明。可正常 import 冻结 helper，不复制业务判断。这里有意将单动作建立与恢复拆开；不调用 POST/Batch 报告发布。每例只 dispatch 一次，然后正常停止/释放自有 keeper/owner，保存退出记录，再由另一个独立进程正常 open/status/reconcile。旧场景仅可提供代码和固定输入，不重放其数据库或结果。

| 组 | 新鲜未决动作的建立 | 本轮唯一 reconcile 读回 | 必须保留的结果 |
| --- | --- | --- | --- |
| U1 部分生效 | `effect_fault=partial`，正常完整执行读回；核对实际只产生两片段中的一部分 | `read_fault=None`，完整新读回 | 不能判为 MATCH 或 ABSENT；保留未决/暂停，原效果与缺失片段不变，不补写剩余片段。 |
| U2 重复身份 | 正常一次 applied 效果，执行读回用 `unavailable` 形成 UNKNOWN | `read_fault=duplicate` | 证明读回包含实际重复身份而不是空表降级；不据重复证据解除暂停，目标存储不因读回造重复。 |
| U3 矛盾 | 同 U2 的合法新鲜建立流程 | `read_fault=contradictory` | 矛盾证据不能形成已解决结果；保留 UNKNOWN 与暂停。 |
| U4 截断 | 同 U2 的合法新鲜建立流程 | `read_fault=truncated` | 不完整范围不能形成已解决结果；完整性标记与原始读回相符，保留 UNKNOWN 与暂停。 |
| U5 不可用 | 同 U2 的合法新鲜建立流程 | `read_fault=unavailable` | 无充分读回时不伪造 snapshot、MATCH、ABSENT 或解除暂停；保留实际失败/不可用记录和未决状态。 |

每例 reconcile 恰好一次，`max_attempts=1`。全部五例恢复期间目标新增效果为 0，目标业务状态保持不变，调用/消费事实不回退，旧 UNKNOWN/intent/permit 保留，不自动重发。对账可按既有语义留下 STILL_UNKNOWN/CONFLICT/INDETERMINATE 或有正式失败记录的未决状态；首次运行前须从当前实现登记各分支预期，不能在运行后为未捕获错误改写成功定义。任何越过合同的异常、错误解除、额外效果或证据缺失均为失败，不以“最终仍暂停”掩盖非预期崩溃。

每例保存恢复前后实际 plan/action/intent/receipt/resolution/attempt、整书 paused/pending、owner/generation、观察状态及完整性、源/目标/scope/store/session/plan/action/digest 精确绑定、Resource 和事件链。有新观察时核对实际 read_sequence 与原持久化观察，不把 UNKNOWN 元数据改时间当新读回；不可用时如实保留 null 字段。无 snapshot/结果的分支不得为齐表补造。目标效果表条数还需与实际业务状态和调用事实共同解释。

## 执行上限与证据保存

顺序 U1→U2→U3→U4→U5，每例一轮；首先功能失败或超时即停止后续组，保留全部原始现场。不给本轮追加产品修复、成功后重跑或 timeout 变体。父 watchdog 每例 90 秒，业务子进程 45 秒；既有观察 2 秒、屏障 5 秒、lease 10 秒及恢复限额不变。正常释放后再 open，不通过固定 sleep 假定占有权；只 wait/清理本轮登记的自有进程。

冻结前做脚本 UTF-8 严格解码和 compile 静态检查，列全实际执行入口及 raw SHA、argv/cwd/时限/预期。实际 Popen 都保留 preregistration/start/completion、raw stdout/stderr、源码快照和导入路径；记录真实 exit/timeout/回收。功能后最多一次只涉及新归档元数据的静态纠正，保留首错，不重调产品。再次归档失败则停止交 REWORK，不自行续轮。

必须在现场仍存在时保存 **每例建立前、UNKNOWN 建立后/释放后、reconcile 前、reconcile 后**的 runtime/target 二进制原件及 capture 记录（可将字节相同的阶段用明确同一原件引用，不能只留摘要）。逐库顺序复制并注明 writer/keeper 是否存活，不能称为跨库原子快照；只读 SQL 审计使用自有 immutable 副本，原始库字节不变。保存所有被正式引用的 JSON/Resource、事件和实际文件摘要；不可在结尾用最终库追构中间现场。

## 允许新增、交付与后续独立验收

仅新增 `tests/test_a03_p2_r12_inconclusive_readback.py`、`examples/a03/P2-R12-inconclusive-readback/`、`docs/evidence/A03/execution/P2-R12-inconclusive-readback/`、`docs/tasks/A03-P2-R12-inconclusive-readback-report.md`。旧产品、schema、profile/adoption/pins、oracle/producer/verifier、依赖、旧测试/样例/证据及调度 state 只读。不要复制历史归档全集。

交付 clean exact commit、base/workflow、可搬运命令、全部五例实际或未执行状态、失败原件、双库阶段原件/SQL、正式引用及 Resource、输入/脚本/导入 provenance、所有自有进程释放证明。统一 SHA256 manifest 覆盖完整新交付及报告，仅排除自身；只交 REVIEW，不自行记 ACCEPTED/INTEGRATED，不推送。

原独立验收在 exact target 新隔离目录按同样五例各一次验证，不增加业务标准，不改产品或回放作者库。调度先核对完整冻结交付及释放证明，再派独立验收；通过后只关闭这五个原 V03/R05 子项。其他原 P2 覆盖、有限集成以及 B 版本映射确认仍分别记录，不将这些子项通过外推为最小联调完成。

字段重置 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`，不运行、变体、委派或建议重测。零网络、平台/浏览器/profile/凭据、OCR、付费模型、安装、B 联系、A05 题22及书级送交；不运行旧 N7、旧成功组或全套回归。
