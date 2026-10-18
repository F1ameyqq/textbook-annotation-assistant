# A03 P2-R12-R2：UNKNOWN 问题归属与回执闭包整体修复

2026-10-18。原执行对话 `01a145aa-2fea-7942-97f9-ad260acf4e30` 续接；冻结交付后交原独立验收对话。保留用户model/thinking，不委派。A03整体REWORK，I01未释放。

## 固定版本与授权边界

唯一base为 `6affc61d2ab0b1f0d96bb2497c5ae969ebaf1df2`，原目录 `C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800`，分支 `codex/a03-runtime-recovery`。workflow为派发消息提供的确切调度提交，不合并移动的主目录。派发键 `A03:execution:P2-R12-R2-issue-ownership:6affc61d2ab0b1f0d96bb2497c5ae969ebaf1df2`。

先读[调度决定](A03-P2-R12-R1-coordinator-decision.md)及[独立失败复核](A03-P2-R12-R1-failure-review-report.md)。后者SHA-256 `145412bb9b81958d4615ff47d0943956552da3e73649cd5afc0c8731934ba227`；报告、原件和来源已归档到workflow。本任务明确授权决定中的**原始UNKNOWN fact派生问题归属**，只适用于A内部固定synthetic native候选，不代表B确认。

允许修改的既有实现恰为：

1. `src/annotation/runtime/storage/__init__.py`：使用共享纯派生规则形成receipt/问题绑定，保持既有native报告策略及legacy默认行为。
2. `src/annotation/contracts/recovery.py`：纯派生规则、每份receipt历史fact的归属证明、私有native→C01语义适配。
3. `src/annotation/contracts/a03_native/__init__.py`：在native闭包验证中落实归属证明与检查顺序。
4. `src/annotation/contracts/validation.py`：必要的内部C01语义消费入口；公开 `validate_bundle` 默认行为保持，不能添加宽松开关或任意允许ID参数绕过引用检查。

调度作为pin负责人，另授权执行者只更新 `contracts/a03_native/data/profile.json` 中上述实际改动文件的implementation pins及 `data/adoption.json` 的profile_sha256。schema pins、其他pins和字段不变。不增加helper文件或外部依赖；纯helper放在上述合同文件内，不能依赖runtime/browser/delivery。

新增范围仅 `tests/test_a03_p2_r12_r2_issue_ownership.py`、`examples/a03/P2-R12-R2-issue-ownership/`、`docs/evidence/A03/execution/P2-R12-R2-issue-ownership/`、`docs/tasks/A03-P2-R12-R2-issue-ownership-report.md`。其他产品/原生schema/API/oracle/verifier/producer、native.py、native_quality.py、旧测试/样例/证据、依赖和协调文件只读。超过范围时交确切缺口，不顺手扩展。

## 一次完成的语义要求

在receipt校验之前，从receipt自己的action_fact_refs读取真实不可变Resource并验证完整内容、SHA、source/scope/book、plan/action/digest/intent、result、attempt及证据引用；用统一纯规则生成完整Issue与稳定ID。UNKNOWN问题不能只存在于runtime局部变量或未来报告中。

receipt.unresolved_issue_ids须与其应有UNKNOWN绑定精确一致；空缺、额外ID、重复、跨consumer借用、错plan/action/intent/scope、资源缺失或字节篡改均拒绝。私有C01检查携带的是经过完整验证且绑定确切receipt的证明，不是调用者自报的ID集合。C01公开默认语义和其他artifact的相关问题检查不被放宽；不得删除receipt中的原ID或构造假的CheckReport帮助过检。

投影顺序保持真实fact/事件 → 合法receipt → progress。遇到异常如实保留已经提交的fact/动作效果、PENDING/暂停、permit与原attempt，不清理或自动重发。后续late fact/新receipt不能替换历史receipt的原fact refs；完整历史重新校验时，原UNKNOWN及其Issue来源仍成立。原issue没有因为当前效果已解决而消失。

native投影仍不生成旧诊断POST、不消费报告读回；正式POST/Batch仍通过现有 `publish_native_quality` 的独立新鲜观察和精确action/fact/intent/resolution绑定产生。不得把执行读回直接当报告观察，不改发布器掩盖循环依赖，不以CONTENT_PENDING/HOLD当恢复或内容验收成功。

新驱动及测试要使用真实公共/受支持入口。冻结前完成静态API/引用链/源码输入/错误语义核对、UTF-8严格解码和compile；记录内部证明载体及调用边界，四文件diff与pin表齐全后提交代码/驱动/输入，形成确切候选代码版本。109项旧索引含5项CRLF/LF差异，新轮分别记录raw Git身份与实际执行字节身份，不修改旧索引或假装两者相同。

## 冻结后仅一轮有界验证

先做一个纯合同反例批次C，随后顺序L1、U1→U5、H1；任何非预期失败、超时或证据缺失即停止所有后续组，封存REWORK，不在同轮改产品/驱动/预期再跑。不跑整个测试集、旧成功组、R11 crash cuts或field reset。

| 批次 | 内容与上限 |
| --- | --- |
| C | 同一固定输入族的纯合同验证最多12个具名用例：合法native UNKNOWN归属；去掉应有ID；增加/重复ID；错误plan/action或intent；跨scope/consumer借用；缺失/篡改fact Resource；仅ID白名单不能取得校验权限；C01公开入口原悬空引用仍拒绝。可在一个用例里表达同一失配的组合，但运行前列清所有输入、预期错误层及数量，不用首个不相关schema失败冒充目标校验通过。不创建运行数据库、dispatch或报告观察。 |
| L1 | 原R12-R1唯一legacy单动作partial/正常读回对照，在全新目录执行一次，保留原合法诊断POST/receipt/progress、UNKNOWN和不可重放。 |
| U1–U5 | 完整继承[原R12五例](A03-P2-R12-inconclusive-readback-validation.md)：partial/正常读回，及unavailable建立后分别duplicate、contradictory、truncated、unavailable恢复。每例一次dispatch；建立正式UNKNOWN及合法receipt/progress，正常释放后独立进程仅一次max_attempts=1 reconcile。读回异常仍未决，恢复新增效果为0，不补片或重发，native_report_reads为0，不发布POST/Batch。 |
| H1 | 仅一个受本次归属语义改动直接影响的历史消费场景：全新单题两片段输入，正常applied效果、unavailable执行读回建立真实UNKNOWN receipt；释放后新进程一次max_attempts=1正常完整reconcile得到MATCH/RESOLVED_APPLIED，保留原UNKNOWN fact/receipt/issue和late fact/新receipt。再从合法当前投影显式调用现有发布入口一次，独立新读回恰好消费1条native_report_reads，正确绑定原receipt/intent及当前resolution，得到原定义的POST/Batch、CONTENT_PENDING/HOLD、NOT_SUBMITTED。无额外dispatch或第二次报告读取。 |

H1是这次历史归属与正式报告链的单一受影响验证，不是重跑旧演示或替代剩余A03矩阵。若现有API不能表达该边界，应在冻结前报告确切限制；不得现场改标准或增加变体。C批次只运行一次、最多60秒；7个业务场景各父watchdog90秒、业务子进程45秒、观察2秒、屏障5秒、lease10秒。总数最多12个纯合同用例和7个业务场景；本轮不追加新压力、长时间或随机测试。

C可以调用真实的纯native内部值校验入口验证内部语义，不伪造registry/BridgeContext、不裁剪AST或复制业务判断；C01公开默认拒绝项仍走公开入口。C的结论仅为纯合同校验，实际registry准入、runtime持久化和跨进程消费必须由后面的业务场景证明。

每次实际Popen先登记真实入口/argv/cwd/时限/预期、源码与输入摘要，保存start/completion/raw流及实际导入路径。正常释放keeper/owner有wait和记录后才跨进程恢复，不靠sleep猜测。首次业务错误只收集现场、正常释放、封存；不运行任何“补证据”功能命令。

现场保留各例建立前、UNKNOWN建立后/释放后、reconcile前/后双库原件与capture；L1保留适用阶段，H1另保留显式报告前后。相同字节可明确指向同一原件，不伪造未到达阶段，不用最终库重建中间现场。逐库复制记录writer/keeper状态，不称跨库原子快照；SQL仅自有immutable副本，原件不动。正式JSON/Resource、事件、receipt/progress/recovery/报告引用和实际目标效果均能对应到原字节。归档最多一次新元数据静态纠正，保留首错；再次失败即交REWORK，不重调产品。

## 交付与后续

交clean exact commit，区分候选代码提交和最终证据提交。报告给出采用的派生规则/内部证明入口、六文件实际diff、pin变化、可搬运命令、C/L1/U1–U5/H1实际与未运行项、历史原件保全、双库阶段原件、实际错误和完整进程释放。manifest覆盖实际改动文件及全部新增产物/报告，仅排除自身；旧证据按确切提交引用，不复制全集。

执行者只交REVIEW。调度检查冻结范围与释放后，原独立验收对同一候选复验同一有界矩阵；通过仅关闭本轮归属/桥接缺口、原五例及有限兼容/历史报告链，不自动宣布全A03或I01完成。若再次失败，先交现场和具体缺口，由调度判断剩余任务是否仍在此修复边界，不自行无限续轮。

零平台/浏览器/profile/凭据、网络、安装、付费模型、OCR、B联系、推送、A05题22或书级送交。field reset固定 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`，不执行、不变体、不委派、不建议重测。
