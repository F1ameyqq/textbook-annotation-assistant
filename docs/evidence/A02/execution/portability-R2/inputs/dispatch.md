# A02 R2：来源身份工具的无 Git 环境处理

日期：2026-10-17。本次是一次具体、有限的集成依赖修复；原 A02 R1 功能接受与本地集成记录保留。当前 A01 integration-R1 独立结论为 REWORK，A04 继续阻断。不得通过更改无Git要求、跳过或吞掉失败来收口。

## 失败和精确基线

[A01复验报告](A01-integration-R1-review-report.md)的唯一阻断 I1-GIT-01：无 `.git` 且 PATH 没有 Git 可执行程序时，A01 常规集成入口运行 A02 discovery，`test_export_subdirectory_cannot_borrow_enclosing_git_head` 调用 `examples/a02/R1/identity.py` 抛 `FileNotFoundError`。同一字节恢复有Git PATH后通过。

主调度用固定集成对象 `3bda6c2307e93601a574c9979c35fd1b25da3f58` 的原字节副本复现该单例：无Git退出1、有Git退出0；没有重跑整套。见 [原始回执](../evidence/A01/coordinator/integration-R2-preflight/coordinator-check.json)。这不是来源/geometry或A02规划规则错误，仍须修复组合验证入口的实际依赖。

继续原 A02 执行对话 `01a144cc-23e9-7c80-9a90-02162ef99b64`，工作树 `C:/Users/ASUS/.codex/worktrees/a02-planner-mock/1800`，分支 `codex/a02-planner-mock`，确切 base=`38aca9dcc8d027409b95193e9cc142c2336b76d3`。本任务工作流提交由派发消息指定。不要合并浮动主目录或A01；根集成由主调度负责。

## 授权修复

唯一允许修改的既有文件是 `examples/a02/R1/identity.py`；新增只限 `tests/test_a02_portability_r2.py`、`examples/a02/portability-R2/`、`docs/evidence/A02/execution/portability-R2/`、`docs/tasks/A02-portability-R2-execution-report.md`。A03并行负责恢复公共接缝；本任务不得改任何src、已有测试、旧输入/报告/清单/失败日志、根依赖/属性或调度文件。

`git_identity` 在无法启动Git时必须返回明确 UNKNOWN / `checkout_commit=null`，不可借用祖先仓库HEAD、声明受验证或跳过测试。正常checkout有Git仍须验证toplevel再取HEAD；raw export即使位于其他仓库中也不能取得父HEAD。两次Git调用之间可执行文件失效也不能造身份。`source_binding` 需要外部身份仓库做真实blob核验时仍失败关闭，不能因未知身份返回成功绑定。不要把所有错误都包装成已验证，也不放宽原字节比较。

复现原失败后做最小修复；至少包括真实独立子进程无Git PATH的raw副本、正常有Git checkout、嵌套导出不借父身份、需要Git的source_binding拒绝以及第二次调用缺失的有限负例。保存实际argv/cwd/PATH是否含Git/退出码/实际导入和源码SHA，原失败与修后对照分开。运行受影响A02测试即可；不要重跑未改C01/登录/630几何矩阵，不复制大型历史归档。不得将仅mock了subprocess的测试宣称为无Git环境实测。

最终报告与统一清单绑定确切补丁/最终提交、所有新证据与日志，说明旧代码改变仅一处、旧样例/证据保持；冻结干净工作树并释放自有进程后交 REVIEW。不集成、不推送、不自动重试下一轮。

## 独立验收与后续依赖

原独立验收对话 `01a144cc-2eae-7a23-b299-03f533e30951` 现在仅在 `docs/tasks/A02-portability-R2-review-preparation.md`、`docs/evidence/A02/review-portability-R2-preparation/` 做一次有界准备后结束等待。收到主调度确切冻结交付后才正式验收，输出 `docs/tasks/A02-portability-R2-review-report.md` 与 `docs/evidence/A02/review-portability-R2/`。

独立复验检查真实noGit路径、身份不可伪造、外部Git绑定失败关闭及受影响A02回归；功能通过后由主调度接受/局部集成该补丁。随后原A01验收对话以新的固定集成父版本加冻结A01 `5f872150a237b195f73c78e02e13a91d2f4f46a7` 复验相关双形态入口，成功后再由主调度实际集成A01。不能因A02单项通过提前释放A04或D01。

全程离线，零浏览器/平台/凭据/profile/网络/OCR/模型调用；不管理B，不重放A05题22。旧A01 R3接受、integration-R1失败、I04标签限制及新夹具LF/CRLF双摘要均原样保留。本次根调度明确授权A02示例工具改动，A01执行者继续冻结，不承担超出其白名单的修复。
