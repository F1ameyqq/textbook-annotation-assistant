# A03 P2-R8-R2：恢复事实的进度投影修复

2026-10-18（Asia/Shanghai）。继续原执行对话 `01a145aa-2fea-7942-97f9-ad260acf4e30`，工作树 `C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800`，唯一 base `a0c40886f3076f84c46377e03fc2206d2fdc5585`。保留用户当前 model/thinking，不委派、不合浮动主树、不修改根调度状态或推送。

依据：[R8-R1 独立报告](A03-P2-R8-R1-producer-review-report.md)，SHA256 `37ad11cbecefcfc97c2c1487786f66418bd231c79e7b7654bd9d6c7a8fbf9cbf`；[调度收口](A03-P2-R8-R1-producer-coordinator-decision.md)。上一轮 coverage 修复已关闭该缺口，不再重做；整个 A03 与 I01 尚未通过。

## 已确认的一个产品缺口

真实 N1 已越过 PRE 接纳、计划、单次 permit、效果后子进程退出、UNKNOWN 与只读终局 head。native `commit_reconciliation` 保留晚到 material fact 的 `attempt_fact=MAY_HAVE_BEEN_ATTEMPTED`，并提交 action.state=APPLIED；随后共享 `_project_plan_locked` 却仅依据该状态推导 `ATTEMPTED`。四项守卫仅此项不一致，正式 receipt/progress 的事务回滚，留下未登记的候选文件，独立 POST/Batch 未到达。

修复已有确切 material fact 的进度投影，使尝试分类及其证据来源于正确绑定的原 fact，保留 plan/action/intent 的校验。效果结论 APPLIED 与历史尝试分类分别表达，不把 fact 改成 ATTEMPTED，不放宽四项守卫或 Schema，不删原 UNKNOWN、终局 head 或 null original_receipt_ref。没有 material fact 的既有状态仍须按原语义处理。

## 允许改动与归档

- 产品：`src/annotation/runtime/storage/__init__.py` 的 `_project_plan_locked` 及必要的同文件私有辅助；若该投影衔接确有必要，允许 `src/annotation/runtime/storage/native.py::commit_reconciliation` 的最小配套修正，交付逐项理由。不得修改已持久历史或扩大到其他状态机重构。
- 更新 `src/annotation/contracts/a03_native/data/profile.json`、`adoption.json` 中受这些确切源码字节影响的 pins。合同守卫、Schema、版本语义、producer、算法与根依赖保持不变。
- 本轮新增测试/驱动/夹具以 `a03_r8_r2` 命名或放在新的 `P2-R8-R2-projection` 目录；不改旧测试、驱动、报告、证据和失败字节。
- 交付新增 `docs/tasks/A03-P2-R8-R2-projection-report.md` 与 `docs/evidence/A03/execution/P2-R8-R2-projection/`。保全旧树用 raw Git 差分，不复制历史全集。

## 一轮修复与验证顺序

1. 对上述确切缺口作最小修复、更新 pins。先检查共享投影对有 fact/无 fact 的来源分支和身份一致性；必要的小检查只围绕本次缺口，不扩大矩阵，不人为写 SQL 行伪造接纳或成功事实。
2. 用全新合成运行目录与双库执行原 **N1 完整标准一次**，不得复用 R8-R1 的失败库或候选文件。真实资源读取、PRE ADMITTED、计划/permit、一次目标效果、实际子进程屏障及崩溃、原 UNKNOWN/原回执缺失、只读终局 head、同 intent 的晚到完整 receipt、独立 POST/Batch 均需实际经过。
3. 针对修复直接检查：reconcile 正常返回；正式 SQL artifacts、当前登记包、intent.receipt 中的回执一致；新 progress 与 material fact 的 plan/action/intent/attempt 四项相同；原 UNKNOWN 和 original_receipt_ref=null 保留；目标效果仍恰好一次，无自动重发。只存在文件系统候选不算成功。原 N1 对内容 PENDING、NOT_SUBMITTED 的边界继续有效。
4. **N1 成功后继续原 N2–N7 各一轮**，标准沿用 [R8 任务](A03-P2-R8-native-bridge-implementation.md)：POST_HOLD 生命周期、五项语义比较、缺少/他属运行、旧版本与角色、创建输入及历史、新双库生命周期。依赖未满足的条目如实标 NOT_RUN，不能用旧成功前缀顶替。
5. 对最终候选执行 C01 `test_contracts*.py`、A02 `test_a02*.py`、R7 `test_a03_r7_readonly_codec.py` 各一轮，绑定实际导入路径与产品摘要。只报告实际通过范围，不将兼容数量当成新恢复链验收。

本任务授权这一个已确认的投影修正。发现新的独立产品阻断时，保留最短真实失败和实际到达边界，停止依赖它的组，冻结交付；不要在同轮修第二个问题、反复重跑失败组或扩大候选。记录脚本自身错误可以修记录脚本，但保留首次输出，不能借此重复已经失败的产品路径。范围外必要改动给出确切位置与原因，交调度划定。

原 P2 V01–V10/R01–R18 没有被 N1–N7 自动替代或豁免；本次完成后按证据核定未覆盖项，不自行宣称 A03 全部完成。字段重置专项保持 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`，不复跑、变形、委派或建议重测。零网络、浏览器、平台、凭据/profile、OCR、付费模型、A05 题22重放或书级提交。

## 冻结交付

提供 exact commit、产品 diff、实际命令/导入路径、来源及 pins、N1–N7 到达边界、正式登记与残留文件的区别、每组原始结果和限制。父/子进程登记 argv/cwd、脚本/输入摘要、PID、限时、原 stdout/stderr 与退出/timeout/alive；所有自有进程 wait/退出后给释放记录。

清单覆盖本轮修改/新增文件及原始日志，只排除自身；旧失败不动。工作树干净后冻结为 REVIEW，待原独立验收对话核验，不自行记 ACCEPTED/INTEGRATED 或释放 I01。B 原生包只读/HOLD 接收不依赖本轮通过，跨侧映射仍需双方确认。
