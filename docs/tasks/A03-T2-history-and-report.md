# A03-T2：历史回执、恢复结果与报告链

适用[交接拆分约定](A03-redispatch-2026-10-18.md)。产品基线 `1330047dd29890dea0e433ff01b991f615bf78f4`，执行在派发的独立 worktree 新建 `codex/a03-t2-history` 分支。先静态梳理现有修复，业务取证必须等待调度提供T1已接受工具的确切提交；不能复制T1浮动文件或自行实现另一套取证器。

## 执行范围与依赖

本任务是 `src/annotation/runtime/storage/__init__.py`、`src/annotation/contracts/recovery.py`、`src/annotation/contracts/a03_native/__init__.py`、`src/annotation/contracts/validation.py` 四文件的唯一新产品写入者。仅在现有归属/历史消费缺陷有具体证据时做必要修复；对应四项implementation pins及adoption.profile_sha256可同步。其余产品、schema、发布器、根依赖、旧证据只读。不得预防性重写或扩大合同。

新增仅 `examples/a03/T2-history/`、`tests/test_a03_t2_history.py`、`docs/evidence/A03/T2/execution/`、`docs/tasks/A03-T2-execution-report.md`。第一阶段立即核对四文件完整链及H1实际API，形成一个简短准备段落/脚本静态检查；若无需改产品，明确沿用冻结1330047d。此阶段不跑新的业务或全套测试，也不把静态通过当功能通过。

T1工具经调度接受后，将指定工具范围正常集成到本工作树，不合并其全部历史包。冻结最终候选，完成原12个纯合同C用例及唯一H1：一次applied效果+unavailable执行观察→真实UNKNOWN receipt→正常释放→新进程一次正常完整reconcile得到RESOLVED_APPLIED→原UNKNOWN fact/receipt/issue仍可验证→一次显式现有publish入口使用独立新鲜读回→POST/Batch正确绑定原receipt/intent及当前resolution，native_report_reads恰为1，CONTENT_PENDING/HOLD及NOT_SUBMITTED保持。不额外dispatch、不重发、不重复报告读取。

用例和历史语义直接继承 [R12-R2](A03-P2-R12-R2-issue-ownership-repair.md)；只能使用固定真实不可变fact来源证明，公开C01仍拒绝悬空引用，私有桥不收任意ID白名单。T1六场景不在这里重跑；若四文件改变影响它们，提交影响清单由调度安排最终候选的必要检查，不自行扩大测试。

交付确切产品/工具基线、实际diff与pins、C/H1实测结果、适用历史/双库/报告原件与释放证明、受影响既有场景清单。允许一次本任务新增驱动纠正，范围依共同约定；产品错误保留最小反例，不改预期凑通过。

## 独立验收

新验收对话首次只准备后结束等待。输出仅自己的隔离副本及 `docs/evidence/A03/T2/review/`、`docs/tasks/A03-T2-review-preparation.md`、`docs/tasks/A03-T2-review-report.md`。调度固定完整target和T1依赖后，独立审核四文件改动及所有历史consumer、公开严格性和正式报告观察边界；C最多12项、H1一次，在全新目录运行。不能用作者通过、最终数据库或理论调用链代替中间原件。通过只关闭当前归属/历史报告链，不能代替T3整体覆盖或I01。
