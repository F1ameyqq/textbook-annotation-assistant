# A03 P2-R9：正常与明确未生效的最小独立进程演示

2026-10-18（Asia/Shanghai）。原 A03 P2 的有界续接，使用既有执行对话 `01a145aa-2fea-7942-97f9-ad260acf4e30` 和独立验收对话 `01a145aa-8d59-7c70-8d81-731712103a9a`，不重复新建。唯一 base `435aaee2d140e82d3237ce8902d594a1aee70aad`；工作目录 `C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800`，分支 `codex/a03-runtime-recovery`。workflow_commit 由调度派发消息给出。保留用户的当前 model/thinking，不委派、不联系 B，不合浮动主目录。

## 目标和边界

沿用 R8/R4 已冻结的原生产品及固定单题合成语言，补原 [P2 任务](A03-runtime-recovery.md) 第5节三条演示中的正常与明确未生效两条。已生效后丢回执的 N1 静态引用 R4 独立证据，不重跑。只有下述两例，不把原 V01–V10/R01–R18 全部装入本轮，不自行宣布整体通过或释放 I01。

当前 PRE producer 固定单题，正常多动作 V01、混合尾段 V04/R11 等仍是未完成项。本轮不改题数、oracle、producer、schema/profile/adoption/pins，不通过自报 PASS、替换比较器、字段重置或降级入口取得资格。

## 两个固定案例

1. **D1 正常单题执行与重启读回。** 全新路径、runtime/target 双库，从固定原生输入经正常 begin/produce/admit PRE、targetcheck、planner 和 record_native_plan，得到一个 CREATE_FRAMES。独立子进程正常 run_plan，无注入；进程退出后另一独立进程正常打开同一库，查询正式回执、动作/intent/permit、目标独立读回与 POST/Batch。再在支持入口尝试同一计划/动作一次，要求拒绝或幂等结束且目标效果不增加；保留真实返回，只有要求的业务结果固定，不凭空规定一个新的精确外层错误码。记录第一次效果恰好一次、重启后仍一次、正式资源与 SQL 绑定、PENDING/NOT_SUBMITTED。不要伪称此例覆盖多动作。
2. **D2 intent 已提交、效果前退出后的明确 ABSENT。** 从另一个全新案例正常构建固定单题原生计划，使用已有 `AFTER_INTENT_COMMIT` 故障点、正常 FaultController 和确定退出码（默认90），让自有子进程真实退出；保存 marker、PID、argv/cwd、实际导入与日志。目标效果必须未发生，但恢复不能仅凭效果日志为空推定未调用。另一个独立进程正常打开，先保存原未决 intent/UNKNOWN/progress；正常 reconcile 一次、max_attempts=1，由完整、精确绑定的新独立读回支持 RESOLVED_NOT_APPLIED。核对新增 observation、resolution 与原 plan/action/intent、存在或缺失的 receipt、尝试事实及正式输出；attempt_fact 按既有真实记录保留，不能把“效果不存在”改写成“从未尝试”。reconcile 前后目标效果新增0；旧动作不自动重发。通过支持入口尝试旧计划一次也不得产生效果。真正新检查/新计划及不足 ABSENT、未尝试尾段留在原 R12/V04 后续范围，不在本轮继续执行新效果。

只使用既有公开正常入口和既有故障点。允许在新驱动正常 import 旧 helper 并显式路由新输出目录；旧驱动/夹具字节不改，不用 AST/exec 裁剪、产品 monkeypatch、直接 SQL 造业务状态或手工重封旧历史。所有首轮记录与失败现场保留。

## 写入范围与资源约束

仅新增 `tests/test_a03_p2_r9_minimal_demos.py`、`examples/a03/P2-R9-minimal-demos/`、`docs/evidence/A03/execution/P2-R9-minimal-demos/`、`docs/tasks/A03-P2-R9-minimal-demos-report.md`。复制必要固定输入须逐项列来源提交/路径/raw SHA256；不要复制旧证据全集或成功数据库作为种子。可以引用并正常导入旧测试 helper，必须记录实际模块位置与字节；不得覆盖旧文件。

产品与依赖只读。每个案例首轮一次；每个产品父/子进程设有界 watchdog（父最多90秒、效果子45秒，既有观察2秒与 lease/产品期限保持原值），只 wait/释放自己登记的进程。前一例失败即冻结本轮，不继续产品路径或改驱动到成功。若现有入口不能完成，交付最小原始失败、确切路径/行号和所需最小产品变更建议，等待有界修复派发；不自行追加功能/场景/重跑。元数据或路径准备错误可局部修正一次，保留首个脚本/日志；不得借此重跑已启动的功能组。

全程 SYNTHETIC/SIMULATED，无网络、平台、浏览器、凭据/profile、OCR、模型、安装、推送、书级送交或 A05题22。字段重置专项保持 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`，不复跑、变形、委派或建议重测。原 R3 N7 失败及旧目标拒绝路径不运行。

## 交付和独立验收

报告给出确切 base/workflow/交付 commit、环境、最短可搬运命令与文件参数、实际导入、每个父子 PID/屏障/退出码、每步前后 DB 摘要与作用范围、正式产物四元组/Resource、效果数与尝试事实。命令不得依赖个人绝对路径；已有输出 exclusive，不覆盖重跑。统一 manifest 覆盖报告、脚本、必要输入、原始 stdout/stderr、产物、清洁状态和 process-release，仅排除自身。执行完成只交付 REVIEW，不改调度 JSON、不自记 ACCEPTED/INTEGRATED。

冻结并核对清单、确切提交及进程释放后，再由原独立验收对话在隔离目录复现这两个案例各一次，核对 SQL/正式资源/目标效果和原失败保全；验收不与作者同时使用案例输出。审查标准按上文可观察结果，有限接受不等于 V01 多动作或整体验收。下一步原有限覆盖缺口见 R4 的独立覆盖表与 [调度结论](A03-P2-R8-R4-remaining-coordinator-decision.md)。
