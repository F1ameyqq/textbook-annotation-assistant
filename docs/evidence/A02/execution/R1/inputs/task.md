# A02 R1：跨书暂停隔离修复

日期：2026-10-16。状态：READY。只修已证实的当前内存会话隔离缺陷；交付进入REVIEW，由原独立验收对话复验。

## 基线与输入

继续 `C:/Users/ASUS/.codex/worktrees/a02-planner-mock/1800` 的 `codex/a02-planner-mock`，R1基线为 **`5c9285720c8628c5198bedeadfc9f6bc7826a914`**；原代码 `3fe492ce10bf93711ce57d305bc716f8b29345b7`，base/workflow `39341c98d73c354d639f3beeb55429f55d0e9be5`。不合并浮动主分支。

从主工作目录只读[正式验收报告](A02-review-final-report.md)、[最小反例脚本](../evidence/A02/review/formal/probe_crossbook.py)、[原观察](../evidence/A02/review/formal/counterexamples/crossbook/observations.json)、[调度复现](../evidence/A02/coordinator/R1/coordinator-check.json)。主调度已核对10个冻结源码blob并重放此反例，确认REWORK。原报告、旧样例和既有证据字节不变，不能直接重跑默认输出目录覆盖它们。

## 必修 R1（P2）

`MockSession.is_paused(book_id)` 遍历保存在当前书历史中的完整ExchangeBundle时，未筛选其中ExecutionReceipt自己的book_id；其他书的UNKNOWN因此污染当前书暂停状态。

最小输入是通过公共资源与引用验证的多书包：另一书已有UNKNOWN；当前书先执行无动作BLOCKED诊断，产生NOT_EXECUTED空回执，没有本书UNKNOWN/intent/效果。当前书暂停却从false变为true；随后READY三动作计划已通过公共资格门，仍被mock拒绝BOOK_WRITE_PAUSED，目标和动作日志不变。

修复须让暂停依据仅来自查询书的pending或UNKNOWN；保留完整原历史。不能删其他书的产物、清UNKNOWN、仅允许单书输入来规避已有合法公共包，也不能通过新ID/scope绕过同书保护。

最小回归组：

1. 上述多书包诊断后当前书仍未暂停；当前书合法READY能实际执行，独立目标读回/日志/回执一致。
2. 同书UNKNOWN在换action/run/question/scope、调用者省略历史后仍暂停；原历史保留，效果不重复。
3. 另一书单独包和含外书UNKNOWN的合法混合包都可独立运行；交换书籍角色后结论相同。
4. 两书各有未决项时分别保留各自阻断；一书仅APPLIED/NOT_APPLIED或NOT_EXECUTED不会消除另一书UNKNOWN。
5. 三类旧计划不可重放、明确ABSENT后新检查/新计划可执行、正常多动作及未派发项的ABSENT证据不退化。

只对声明支持的合法输入构造案例，不要求实现A03持久化、跨进程恢复或正式解暂停。原反例脚本以“缺陷发生”为成功断言，修复后需在新目录使用符合本任务接受条件的验证器；不得修改冻结验收脚本/结果来伪造通过。

## 允许范围与保留边界

允许 `src/annotation/delivery/mock/` 和必要的专属 `tests/test_a02*.py`；新样例/复现器用 `tests/fixtures/a02/R1/`、`examples/a02/R1/`。新证据仅 `docs/evidence/A02/execution/R1/`，新报告 `docs/tasks/A02-rework-R1-report.md`。若确需planner/targetcheck变化，先给最小原因由调度明确范围，不扩大为一般重构。

不改contracts、公共政策、C01固定样例、根依赖、父入口、source/geometry/runtime/B模块、旧执行报告/证据或主目录调度文件。零浏览器、网络平台、凭据、OCR、模型，不重放A05，不推送或集成。

N1排除区域关联、N2证据注册标签准入仅作为已有集成限制保留，不能借修复放宽覆盖门或声称解决真实来源S01。报告继续区分模拟、平台、内容和提交状态。验收发现作者复现器在无.git导出目录可能读到父仓库HEAD：新R1复现证据必须绑定指定交付及实际源码摘要，无法取得可靠Git身份时明确写unknown/外部指定，不能把父仓库版本冒充被验源码；不要求改写旧证据或旧verify.py。

## 交付

保留修复前失败和修复后结果，给出上述回归及A02/C01受影响套件、正常和故障演示的实际命令、cwd、导入位置、退出码、目标状态/动作日志/历史。重跑命令写新目录，完整摘要清单覆盖本轮证据与报告。

报告列确切实现提交、最终冻结提交、API/样例版本、范围和限制；最终工作树干净，无待释放浏览器会话。只标REVIEW，等待原独立验收；本轮为有界R1，不因自测通过释放A03。
