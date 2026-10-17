# A03 P2-R8-R4：创建输入与初始化中断的剩余验证

2026-10-18（Asia/Shanghai）。继续原执行对话 `01a145aa-2fea-7942-97f9-ad260acf4e30`、工作树 `C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800`、分支 `codex/a03-runtime-recovery`。唯一 base `d9ed692db9ab8e9277f8ffd09e040451e8b8f65f`。保留用户当前 model/thinking，不委派、不合浮动主树、不改根调度 state、不推送。

依据：[R3 调度结论](A03-P2-R8-R3-post-hold-coordinator-decision.md)、[独立报告](A03-P2-R8-R3-post-hold-review-report.md)（SHA256 `a39afab68c15837122a34fb0f75dca7cae339dd2ba1be13dde007971b99b9a17`）、原 [R8 实施任务](A03-P2-R8-native-bridge-implementation.md) 的 N6/N7。POST_HOLD 和有限 local/N1–N5 已接受；本轮补未运行的既有标准，不重做设计。

## 范围与固定判据

1. 产品、profile/schema/adoption、旧测试和旧证据原字节保留。只新增 `tests/test_a03_r8_r4_remaining.py`、必要的 `tests/fixtures/a03/P2-R8-R4-remaining/`、`examples/a03/P2-R8-R4-remaining/`、`docs/evidence/A03/execution/P2-R8-R4-remaining/`、`docs/tasks/A03-P2-R8-R4-remaining-report.md`。必要时可新增一个同前缀独立辅助测试文件；列入交付。允许正常导入原 R3 测试辅助与产品，禁止 AST/exec 裁剪导入，不改既有驱动。
2. **N1 前序一次**：全新合成目录/双库/ID，用 exact base 已接受的最终驱动路径生成 N6 所需完整单动作恢复历史。可以调用原 N1 方法并把本轮输出根显式指向新的 R4 目录；不得写旧 R3 输出、复制旧成功/失败库、变更产品或跳过失败。完整 N1 标准保持，真实子进程屏障、一次效果、原 UNKNOWN/null 回执、晚到 receipt 和新 POST/Batch。这是剩余 N6 的必要前序，不重新跑 N2–N5。
3. **N6 正例一次、缺失依赖负控一次**：基于上一步完整且未裁剪的正式历史，正常 API 验证 creation anchor 并重算同一 plan 四元组/action 内容；记录 anchor canonical bytes、消费资源摘要、正式 SQL 登记、原始与重算计划对照，保留 UNKNOWN 及后来 receipt/resolution/POST/Batch。负控明确选择一个被正式引用的 EvidenceRecord 或 Resource，不能任意删除“最后一项”而不知道消费者。只在新的测试副本/内存输入做缺失，记录实际拒绝层与原因，确认没有新增 permit/效果。不得改原 anchor、过滤历史、重封签或用旧版本降级通过。错误断言依据现有合同语义与实际可定位原因，不凭空新增外层错误码要求。
4. **N7 未到达的初始化中断一次**：在另一个全新目录调用既有 `init_native_state(..., before_completion=...)`，使用原有明确钩子在正式完成点前产生受控中断，然后调用正常 open 证明 fail closed。记录正式完成标记/anchor 是否存在、可保留中间文件的摘要、原异常、拒绝原因和计划/intent/permit/效果为零。未生成表/目标库记为未创建，不伪造零行查询。允许此处沿用已有初始化钩子的同进程受控异常，不把它称作真实进程崩溃证明。不得直接 SQL 改字段、重置资格或恢复初始化后再试到成功。

原 R3 N7 的严格重开身份与旧入口拒绝已达边界由冻结证据静态引用；**不要重跑原失败的旧 target 入口或它的变体，不要求修改 persistent.py**。本轮只证明上述未到达分支。旧库迁移继续 NOT_IMPLEMENTED/BLOCKED。不把一项 runtime 初始化中断称作目标库所有中断点通过。

## 停止条件与交付

先检查新驱动路由/输入/输出根，再冻结驱动摘要后执行每组一次，顺序 N1 → N6，N7 初始化中断独立。任何新的产品语义失败保存完整首次记录、停止依赖组、冻结交付；本轮**不授权产品修复或失败产品路径复跑**。纯记录/路径脚本错误可纠正并保留首次记录，不借此重试失败产品调用。未到达项如实 NOT_RUN。产品未变，不重复 C01/A02/R7 兼容套件或 local/N2–N5。

报告同时更新一份小型覆盖映射：原 N1–N7、本轮实际新增覆盖、仍未覆盖的原 P2 V01–V10/R01–R18；引用已冻结接受记录，不能把后者全部要求塞进本轮。字段重置专项仍为 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`，不复跑、不变形、不委派。

交付 exact commit、复现命令、实际产品导入路径/摘要、新验证驱动摘要、原始证据与限制。所有父/子进程预登记 argv/cwd、脚本/输入摘要、限时并保存 stdout/stderr、PID、exit/timeout/alive；结束后 wait/释放证明。manifest 覆盖本轮所有新增/修改及日志，仅排除自身；用 raw Git diff 证明产品/历史未变，不复制历史全集。工作树干净后冻结 REVIEW，不能自行 ACCEPTED/INTEGRATED 或释放 I01。由调度核对后交原独立验收对话。

零网络、真实平台、浏览器、凭据/profile、OCR、付费模型、A05 题22、书级送审及 B 联系。
