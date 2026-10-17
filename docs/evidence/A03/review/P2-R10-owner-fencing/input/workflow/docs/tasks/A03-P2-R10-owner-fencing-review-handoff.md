# A03 P2-R10 双进程占有权与旧代次独立验收

2026-10-18（Asia/Shanghai）。原 A03 独立验收对话 `01a145aa-8d59-7c70-8d81-731712103a9a` 续接。保留用户现有 model/thinking，不委派。只复验[执行任务](A03-P2-R10-owner-fencing-validation.md)已冻结的两个案例，不增加验收标准，不修改候选产品。

## 固定输入

- base `bfd7fe896a7eee663ea8e0b6cf967548d8dd8f39`；唯一 target **`1c26b4a8eb378af33e57668472d2071e9ea6afff`**，两者直接父子关系。
- 执行目录 `C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800` 只供读取冻结交付；不得运行其中原案例或访问活动库。本任务单从消息指定的 workflow commit 读取，不能合并浮动主目录。
- target 报告 `docs/tasks/A03-P2-R10-owner-fencing-report.md`，SHA256 `a718ddf8b3969dd8b44d81fb22f4ee86b30400c9d85f7226194a6136613e86d4`。
- target 证据前缀 `docs/evidence/A03/execution/P2-R10-owner-fencing/`；`manifest.json` SHA256 `7372f10d785322d949a29ea4b28c730ea90411f05ddc2448a39f4e6d2b9bc9a7`；`process-release.json` SHA256 `b7d20a8254ba93b815b40066724a23c75a1206c0f826df90aa9838da4dc1fbd2`。
- [调度预检](../evidence/coordinator/heartbeat-20261018-0629/delivery-preflight.json) 已核实新增261个 raw blobs、260个 manifest 条目、32152个旧 mode/type/blob 条目不变、确切任务身份、8条进程退出记录与当前登记PID不存在。预检只查文件/进程记录，未运行产品功能；它不是独立验收。

作者两例均报告首轮通过、effects=0，无产品改动或功能重跑。请独立检查驱动、实际结果与范围，不能以作者断言代替结论。R9-R1四组有限接受保留，原 borrow FAILED/D2 NOT_RUN及旧R3失败不改、不重演。

## 独立检查

从 exact target 导出必要 src/config/固定 fixture/helper 到自己新的隔离目录，记录 raw Git来源、实际导入路径/摘要；不复制整个历史或作者数据库为种子。产品、schema、profile/adoption/pins、oracle/producer/verifier和依赖全部只读。沿用固定32×32单题两片段 SYNTHETIC语言和同书注册scope。可以正常import冻结helper或编写薄驱动；先静态检查并登记完整脚本、输入、预期、超时，再首次运行。禁止AST/exec裁剪、monkeypatch产品、直接SQL写业务状态、时钟/PID/lease伪造。

1. **C1 同书两个真实存活进程竞争 claim**。两方各到显式ready和原BEFORE_CLAIM屏障，父进程核对PID/存活后共同放行。成功者保持ACTIVE与keeper，失败者明确受拒；双方结果和同时存活观察已保存后才允许正常release/退出。核对只有一个当前owner、instance/PID/generation与target fence一致、事件及effects准确。不得将成功者先退出的串行接管当作并发。允许没有业务计划/效果，结论只涵盖claim互斥。
2. **C2 实际 A release/B claim 后旧 A 从 run_plan 入口被拒**。全新case中A通过正常PRE/admit/targetcheck/planner/record建立真实有效计划和旧claim，尚未accept/intent/dispatch；A正常stop keeper/release但保持原进程和store存活。B正常接管并保持ACTIVE，generation实际增加、target fence同步。父进程确认双方存活后，A用原pair从正常run_plan入口尝试一次；应在新增intent/permit/效果前因旧资格受拒，B的owner/generation/ACTIVE保持。核对实际包装错误及根因，不能把无关错误算作通过。A不得在移交后renew/release/覆盖B；最后B正常清理。此例不代表死进程回收或其他崩溃点通过。

核对屏障与完整时序，不以固定sleep猜测先后。记录各阶段实际PID、instance、owner/generation、lease、target fence、SQL/事件/正式Resource引用；检查冻结双库与各阶段记录一致。两个库的顺序读取不冒称原子快照。C2的PRE/计划必须真实存在且由支持流程形成，不能只传任意generation制造拒绝。结果中区分已记录计划artifact与尚未接纳的plans/actions行，以及零效果验证与实际保存成功。

两组各一次，父 watchdog90秒、每个业务child45秒；产品BEFORE_CLAIM5秒、lease10秒、观察2秒不改。首个功能失败/超时即停剩余组，保存现场并报告未到达点；不修改驱动后重跑功能，不扩大测试矩阵。首次执行前允许静态准备；执行后仅元数据/封存断言最多一次静态纠正，保留首错，不因此重调产品。只按实际存在的导入/退出文件登记，不凭预设数量生成证据。仅终止和释放自己登记的进程。

## 交付与边界

报告 `docs/tasks/A03-P2-R10-owner-fencing-review-report.md`；所有新审查驱动、输入、原始输出、双库/资源、PID/argv/cwd/exit/timeout/alive、进程释放与 SHA256 manifest 只放 `docs/evidence/A03/review/P2-R10-owner-fencing/`。提供确切 target、raw输入来源、两例单独判定、失败或未执行项及复现命令。不要改产品、作者目录、旧证据或调度state；报告与manifest互引时避免自引用，清单可以只排除自身。完成后冻结交付并说明会话释放。

仅对原V06/R09的两个子项给出 `ACCEPTED_OWNER_FENCING_TWO_CASES_ONLY` / `REWORK` / `BLOCKED`。whole A03、完整并发/崩溃矩阵、产品本地集成及I01仍未放行，最终状态由调度核验登记。

字段重置保持 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`；禁止运行、变体、委派或建议重测。无旧功能组/整套回归、网络、平台/浏览器/profile/凭据、OCR/付费模型、安装、推送、B联系、A05题22或书级送交。不改变用户的model/thinking。
