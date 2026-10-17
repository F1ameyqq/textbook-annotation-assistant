# A03 P2-R11：四个剩余崩溃切点有界验证

2026-10-18（Asia/Shanghai）。原A03执行对话 `01a145aa-2fea-7942-97f9-ad260acf4e30`续接；冻结交付后由原独立验收对话复验。唯一base `1c26b4a8eb378af33e57668472d2071e9ea6afff`，在原 `C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800` / `codex/a03-runtime-recovery` 工作。workflow以派发消息的确切提交为准。保留用户当前model/thinking，不委派、不合并浮动主目录。

## 已有证据与本轮范围

[原执行](A03-runtime-recovery.md)V02和[原独立标准](A03-independent-review.md)R03要求若干明确崩溃切点。正常单题/重启防重复与AFTER_INTENT_COMMIT后的完整ABSENT已有限接受，见[R9-R1结论](A03-P2-R9-R1-owner-lifecycle-coordinator-decision.md)；效果后丢回执N1见[R8-R4结论](A03-P2-R8-R4-remaining-coordinator-decision.md)；双进程占有权见[R10结论](A03-P2-R10-owner-fencing-coordinator-decision.md)。这些旧案例不重跑。

只增加下列四个**已有产品故障点**的新独立进程案例，沿用固定32×32单题两片段SYNTHETIC语言、同一书/注册scope。产品、schema、profile/adoption/pins、oracle/producer/verifier、依赖均只读。本轮不是多动作实现、目标字段重置、旧N7重演或新的故障注入机制。

每例从全新空路径正常init/register、PRE begin/produce/admit、targetcheck/planner/record建立合法单动作。保持同一合法owner与PRE运行上下文，使用既有FaultController由正常run_plan到达指定点后真实os._exit（默认90），不以捕获异常代替进程终止。冻结驱动前核对当前故障点位置、持久化边界及错误包装；若入口不可用，提供最小路径/原因，停止对应子项而不改产品。

| 案例 | 唯一故障点 | 崩溃及新进程核对的结果 |
| --- | --- | --- |
| F1 | BEFORE_INTENT_COMMIT | 证明尚无已提交intent、permit或目标效果；区别已接纳/预留的plan/action与不存在的intent，不凭marker伪造未尝试receipt。新进程正常open/status/query并核对正式记录和两库；不派发效果、不手工改成READY，不要求不存在的UNKNOWN或完整回执。 |
| F2 | AFTER_DISPATCH_STARTED | intent及permit消费/DISPATCH_STARTED已持久化，但目标效果仍0。新进程先记录实际未决/UNKNOWN和原事件，再正常reconcile一次，max_attempts=1，由完整、精确绑定的新独立读回得出ABSENT/NOT_APPLIED；调用事实按真实证据保留，不能把效果不存在改成从未调用。对账新增效果0，旧动作不重发。 |
| F3 | AFTER_READBACK_CAPTURE | 效果已发生且当时执行读回已经到达，结果提交尚未完成；新进程先记录未决，再正常reconcile一次、max_attempts=1，依赖新的独立读回而不是丢失的内存结果。MATCH解决后目标效果仍恰好1；原intent/历史保留，原动作不重发。 |
| F4 | AFTER_RECEIPT_COMMIT | 效果与正式结果/回执已经持久化后退出。新进程只open/status/query、读取正式artifact/Resource及双库，确认结果及精确动作/intent绑定仍在、目标效果1；不回退成未执行、不重发、不伪造恢复resolution。不要求崩溃前尚未执行的POST/Batch自动出现，报告实际存在和缺失产物。 |

按F1→F2→F3→F4各一轮。新进程的open会按既有语义记录中断时如实核对，不为猜测的plan状态、外层错误字符串或attempt_fact改产品。F2/F3须以当前完整观察和正式解决引用证明结果；F1/F4不为“统一流程”调用额外reconcile。仅这两次被授权的reconcile，不追加旧计划重放、真正新计划、多scope、多题、字段重置或其他故障组。

## 时序、资源与证据

runtime与target使用不同SQLite文件/事务；每次崩溃后先wait确定执行进程退出，再由新的独立进程打开。保存实际PID、store/instance/owner/generation、故障marker、argv/cwd/timeout/exit与真实导入。故障点到达必须同时由代码位置、原marker、真实exit和持久化记录证实；单个日志标记或空效果表不能替代调用事实。

允许正常import冻结helper及薄驱动，用参数指向新目录；不AST/exec裁剪、不monkeypatch、不SQL写业务状态、不修改时钟/PID判断/lease或直接私有字段伪造资格。新驱动先静态检查并登记源码/输入/预期。每例父watchdog90秒、每个业务子进程45秒；原观察2秒、屏障5秒、lease10秒及恢复期限不变。死进程租约等待遵守现有claim_current有界路径，不固定sleep后假定已经接管，也不提前清锁。

首个功能失败、超时或与冻结标准不符后停止后续组，保留原始现场；不给本轮追加产品修复，不改驱动重跑到成功。首次功能前可静态准备；执行后仅归档/元数据错误最多一次静态纠正并保留首错，不重调产品。对os._exit只记录实际存在的导入/退出证据，不按预设计数补造文件。只wait/释放自有登记进程。

## 允许新增与交付

仅新增 `tests/test_a03_p2_r11_crash_cuts.py`、`examples/a03/P2-R11-crash-cuts/`、`docs/evidence/A03/execution/P2-R11-crash-cuts/`、`docs/tasks/A03-P2-R11-crash-cuts-report.md`。不改旧产品/测试/夹具/报告/失败证据或调度state；不要复制历史全集或旧成功库作为种子。

交付确切clean commit、base/workflow、可搬运命令、每例输入/脚本/raw源摘要、全部自有进程记录、故障前后/恢复前后双库、正式引用/Resource、效果数、实际尝试事实及缺失产物。每例说明其证明的事务边界；未知仍按UNKNOWN，缺证据不写成功。统一manifest覆盖报告、必要输入、完整脚本、raw输出/marker、数据库/资源、进程释放，只排除自身。仅交REVIEW，不自记ACCEPTED/INTEGRATED。

冻结后独立验收使用exact target的新隔离目录按相同四例各一次，检查故障点、真实新进程、双库事实及解决链，不增加测试标准。调度核验后只关闭本次四个切点；完整A03及I01仍需原清单其他覆盖和范围明确的集成。

字段重置始终 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`，不运行、变体、委派或建议重测。不执行旧R3 N7/旧四组/旧R10或整套回归。零网络、平台/浏览器/profile/凭据、OCR、付费模型、安装、推送、B联系、A05题22或书级送交。B版本映射仍未共同确认。
