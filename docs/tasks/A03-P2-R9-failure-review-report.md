# A03 R9 首败独立故障复核

2026-10-18（Asia/Shanghai）。**确认产品 ownership 生命周期衔接缺陷，维持 REWORK。** 正常动作和正式回执已提交；`run_plan` 在自己的有效租约内调用报告发布，而 native 发布再次 claim 同一本书，正确触发 OWNER_BUSY。此结论来自固定源码、首次 traceback 和自有 immutable DB 副本，未重新执行 D1/D2，未调用或修改产品。D1 演示未完成，D1 重开/重复保护、D2 仍 NOT_RUN；A03/I01 不记通过或 INTEGRATED。

## 固定输入与保全

| 输入 | 提交或 raw SHA256 |
| --- | --- |
| target | `c83f956c5c29c64ab10735ba11c153201d3f3f4b` |
| base / 未变产品 | `435aaee2d140e82d3237ce8902d594a1aee70aad` |
| 审阅 workflow | `d9c0be133ac86919bea1f9caec29120e0ea650b3` |
| 审阅交接单 | `685cdf4ba3433e28680a092cdd60b97056db9d04265e503a39f5aa5a063efd41` |
| 执行 workflow | `11300250bef18d4bdf7220111cf82232c7d5e0f3` |
| 执行报告 | `6f68b69ed13cbdc3194346181054eef70b9abc45c1a714ab35b60ab847b3c72d` |
| 作者 manifest.json | `7712cad90e09e0883dc4dc95d36608a066d76ca62aa10a2664df0b7a48917c86` |
| 作者 process-release.json | `f64486a952a14bf62589f4ae12d63681811bfafdbc6fcaf69d1b81d4f7271273` |
| 首败 child stderr | `0db6947c2321a6a6fe42b68486f7dc0f0cd7e5340a50a6f412f013fe9fc4852d` |

以命令级 `git -c core.longpaths=true`、raw `cat-file --batch` 和 tree/blob 身份核对：182个manifest条目加自身共183个新文件、5份workflow原件和11份base引用均相符；31,482个旧tree条目全部原样。仅导出本轮证据和必要源码/依据273项，不合并调度分支、不复制旧历史全集。见 [输入索引](../evidence/A03/review/P2-R9-failure/input-index.json)、[交付字节核对](../evidence/A03/review/P2-R9-failure/delivery-byte-index.json)。

7,030项旧A03审阅/报告文件共156,577,683字节保持原字节，有序路径/长度/raw SHA256集合摘要为 `cf681152d911e43219f15371e238ce9c7c72a3c9a60fb05185888e3a1c4f3194`，封存前复核，见 [历史保全](../evidence/A03/review/P2-R9-failure/historical-preservation.json)。原R3/R4有限接受、原R3 N7失败与全部旧边界均保持。

## 原因定位

冻结 [recovery/__init__.py](../evidence/A03/review/P2-R9-failure/input/target/src/annotation/runtime/recovery/__init__.py) 的83–95行接受并校验显式owner/generation，启动自己的LeaseKeeper；117行提交正常结果，121–123行仍在try内执行project_plan和publish_quality。直到129–131行finally才stop/release。

publish_quality的26–30行直接进入 [native_quality.py](../evidence/A03/review/P2-R9-failure/input/target/src/annotation/runtime/recovery/native_quality.py)：12–21行没有借用当前租约的参数分支，无条件claim_current；此时尚未到25行的durable report-read登记。claim_current的recovery:63–71进入 [storage/__init__.py](../evidence/A03/review/P2-R9-failure/input/target/src/annotation/runtime/storage/__init__.py):405–416；owner存在，lease未过期或PID仍活即OWNER_BUSY。storage:378–380明确同PID为存活，因此它不会等待自己退出。

原trace精确命中driver:88→recovery:123→publish_quality:30→native_quality:21→claim_current:64→storage:416。共享claim门禁正确生效，失败发生在产品从执行到报告的编排衔接，**不是新增外层诊断码断言或现有合同歧义**。

[驱动](../evidence/A03/review/P2-R9-failure/input/target/tests/test_a03_p2_r9_minimal_demos.py):69、80、87–88正常setup/record后传递原owner/generation，D1 fault=None，没有注入效果故障、伪造他属owner或直接SQL造业务状态。setup外层keeper与run_plan内层keeper共同更新同一租约有冗余，但删掉外层keeper也不能消除run_plan自身95–123行的持有租约再claim冲突；不应通过驱动提前release使其通过。见 [源码行号与故障判定](../evidence/A03/review/P2-R9-failure/fault-review.json)。

## 独立SQL与正式绑定

只从raw Git导出的四份冻结文件复制到自有审阅目录，标准库SQLite `mode=ro&immutable=1`、query_only读取；quick_check均ok，原件/副本读前后SHA相同，临时副本已删除。没有连接执行工作树DB或调用其API。

| 冻结库 | raw SHA256 |
| --- | --- |
| before runtime | `21a04c566e9c989f0696a6449af0b339774e91574254ac611eeedaeb99b75ac9` |
| before target | `d544641e1dddf3797d0a48e1916452426de5280fcdeb3e222456ee722cc352ec` |
| after runtime | `192cea9caee1b34223045beb5fa016b7735f64ae32ecbf179ebb42bd08869b61` |
| after target | `44ba882aecab97831995c12d21fa728c034c0ab42e66114d6799bbe415b628ec` |

before两文件是作者按顺序复制，keeper当时存在，**不称跨库原子快照**。各冻结文件分别有效：before plans/actions/intents/permits=0、effect=0，正式计划已在artifacts；after对应四表各1，artifacts=14、resolution=0、report read=0，target observations=3、effect=1。

独立核对当前登记bundle、SQL artifacts和intent.receipt，所有artifact摘要重算相符，receipt三处完整四元组一致。以下均revision1：

| 正式产物 | artifact_id / content_hash |
| --- | --- |
| plan | `plan-r9-D1` / `c0d5e99d98ea3133abc22daee14a1f14589932ae1f6fae3259ad5ff3799c4779` |
| intent | `writeintent-819a78b2783c441b88762ed4ab72e1e4` / `964edea5968f3172a6dc818e1ade5a2ae40a53a61164a89b1b4b73b1d6e8ce06` |
| receipt | `executionreceipt-5df5825e40a94c7c8495836773f1d3a5` / `dfffa7ffc87929ef888be3a608e688860dcbf398b06968ce8eb26b884681d8d1` |

唯一action=`action-a02-b5a2d38e753b8c778e4482bc131d5513`，digest=`e0fb5074b54ac08ca957e5124bc9df5143eb23a32cb9ec98389b12fbb8feaaf9`。SQL action/intent为APPLIED，permit为CONSUMED，plan表为FINISHED；这不代表run_plan正常返回或演示完成。正式fact `assets/runtime/20deadc332558d19736b4925002c683d545a8db1678295d755f621d906f2f009.json` 实体SHA相同，origin_phase=EXECUTION、APPLIED/ATTEMPTED，plan/action/intent、receipt.results、material progress与实际唯一effect均对齐，resolution_ref=null。前置/读回/尝试资源另核对实体摘要。

POST=0、Batch=0、native_report_reads=0，normal-run-result.json未生成。before owner为执行child61832、ACTIVE、generation1，绑定同一intent/effect；最终books为RELEASED，owner/pid=null、lease=0、hold=null，与外层finally一致。见 [独立数据库证据](../evidence/A03/review/P2-R9-failure/database-review.json)。不将已生效后发布失败视为可以重发动作。

## 一次有界修复建议及必要复验

后续授权修复限于`run_plan → publish_quality → publish_native_quality`的ownership传递与报告函数生命周期：显式传入当前owner/generation，成对校验并复用当前有效租约；借用分支不再claim，不stop/release外层keeper/租约，由run_plan既有finally收尾。独立publish不带借用参数时仍自行claim/release；部分、过时、他属参数不得静默降级为重新claim，也不得释放调用方租约。

保留ACTIVE、PID、instance、generation、lease的校验与每次报告落库前的事务检查；保持现有报告上下文pending/hold适用语义，不能把报告读取变成普通写入资格。共享OWNER_BUSY条件、普通写入pending/hold门禁、durable单次报告读与2秒观察预算均不放宽。不得提前释放执行锁、掩盖发布异常或把缺失报告补成成功。两份现有recovery模块已被implementation pins绑定，未来交付须同步对应两项摘要及profile/adoption链；本轮未改源码或任何pins，schema/producer/oracle不在修复范围。

后续仅需有界复验以下项目，本轮均不执行：

1. 原D1正常FINISHED返回与正式POST/Batch PENDING/NOT_SUBMITTED，独立进程重开及支持入口重复保护，effect始终1。
2. 独立publish在“完整正式回执、报告读尚未消费”的状态自行claim/publish/release，不对已发布D1重复读。
3. 借用合法ownership不新增claim/generation、不提前释放；部分/过时/他属ownership拒绝且不释放调用方租约，既有fencing/读预算不变。
4. 原R9 D2一次：真实intent后退出、一次有界ABSENT恢复及旧计划不重放，保留实际尝试事实。

不新增整套P2回归。原多动作/混合尾段/不足ABSENT/新检查新计划、scope/书隔离、竞争及其他既有覆盖缺口继续保留；D1/D2和A03均不记ACCEPTED，I01未释放。

## 过程与封存

原登记四进程逐项核对：父42924/执行child61832均exit1，观察21684/只读补证22652均exit0，无timeout/alive；源/脚本快照、argv/cwd、PID及原stdout/stderr摘要可追踪。65项作者.py/.json源码索引及实际导入摘要另核对；仅五个已存在LF→CRLF表示逐文件显式验证，其余raw bytes一致，不作宽泛归一化。

作者首次封存准备TypeError、原stdin脚本和combined tool transcript完整保留；该元数据动作无PID/分流原输出，仅按转录记录，不伪造过程证明。审阅自身首轮只读断言也保留：误认为OWNER_RELEASED事件含旧owner，实际release源码先清owner再记事件；纠正后仅重查同四冻结库/源码，无产品调用。两次检查的脚本快照、PID、raw日志及退出记录均在目录中，见 [过程审查](../evidence/A03/review/P2-R9-failure/process-and-source-review.json)、[审阅辅助纠正](../evidence/A03/review/P2-R9-failure/reviewer-preparation-note.json)。

本轮4个登记审阅检查子进程（含一次辅助断言失败）、5个Git子进程、1个封存包装子进程均wait退出，未扫描OS/profile，见 [进程释放证明](../evidence/A03/review/P2-R9-failure/process-release.json)。[最终字节核对](../evidence/A03/review/P2-R9-failure/final-verification.json) 与 [逐文件SHA256清单](../evidence/A03/review/P2-R9-failure/sha256-manifest.json) 覆盖本报告及本轮全部输入/脚本/输出/原失败，仅排除清单自身，落盘后再读取全部body和目录集合核对。

只新增获准R9审阅报告/证据，保留用户model/thinking；零产品调用、D1/D2重演、子智能体、平台/浏览器/凭据/付费模型、推送或B联系。字段重置保持 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`，不变体、复跑、委派或建议重测。结论是故障确认与修复边界，修复派发及集成决策留给调度。
