# A03-T3 C1–C4 修订独立复核交接

2026-10-18。继续已有独立验收对话 `01a14ccf-b8c3-7941-a80f-73594e7859a5`，xhigh；不新建、不联系旧A03/B/作者、不委派。本次仅复核[一次合并修订范围](A03-T3-plan-revision-handoff.md)的C1–C4及受影响引用；既有[28项映射有限接受](A03-T3-review-report.md)沿用，不重复全量审查，不导入产品、不运行业务或SQL。

完整固定target为 `765aef597a93fe36060fce65e17b22fe1c3408b8`；前一文档target为 `3fcdb73416142a0a85dfb951a7f839849871c549`，产品基线仍 `1330047dd29890dea0e433ff01b991f615bf78f4`。从固定target读取两份 `docs/tasks/A03-T3-remaining-matrix.md`、`docs/tasks/A03-T3-integration-plan.md` 与 `docs/evidence/A03/T3/execution/plan-R1/`，不要审浮动分支或主目录旧副本。

调度[准入核对](../evidence/coordinator/heartbeat-20261018-0322/checks.json)确认仅两份文档和七份新证据变化，manifest的8个成员raw摘要/长度一致；旧4个execution文件原字节保留，产品diff=0，作者已completed/idle且工作树干净。manifest SHA256=`02b80200878ddf09a08c603dc2a2c45bef4917764d978fc0019d58655f8b7937`。作者一次静态摘录越界及纠正原件在first-static-failure中，不改写旧失败记录。

一次完成四项判断：C1是否准确区分legacy初始converter有限语义、条件性COMMITTED版本提案、fresh-only native及未批准DB迁移；C2是否给出选定native驱动、POST_HOLD候选仅用于clear、final-read/CAS后重新INITIAL PRE资格、未尝试只读session及全部守卫/精确路径的完整拟议顺序；C3是否明确同书原生UNKNOWN与两份legacy历史的来源/身份/pending及B表示、独立起点/dispatch分别有界；C4是否按真实consumer递归执行字节和原要求去重，明确run/reconcile/query/export及三条F路径，且不预填T2接受或重跑已接受场景。

D-CONV与D-M是作者明确保留给调度的采用决定；本轮评价方案是否足够明确可裁定、是否满足已有C1–C4修订标准，不代调度采用、不要求为了计划通过先实施产品。若有实质未闭合项，一次汇总精确反例/引用与最小修订，不发明新标准。计划有限通过不等于产品、K组合、M/L/G、A03或I01已完成。T2在本次heartbeat仅新交REVIEW，独立验收已另行安排，不因文档的历史“待交付”表述反复返工；K在T2接受/释放后由调度固定。

在自有 `D:/1800/.local/A03-T3-independent-review` 下新建本轮隔离目录。为了保留旧验收原件，本轮输出改用新的 `docs/evidence/A03/T3/review-plan-R1/` 与 `docs/tasks/A03-T3-plan-R1-review-report.md`；旧review目录和旧报告只读。只保留必要的差异/引用/hash及结论证据，不复制全历史。不得操作主目录Git索引/提交、协调JSON、执行者worktree或产品。完成后给有限ACCEPTED/REWORK/BLOCKED并结束等待。

全部离线，无网络/平台/browser/profile/凭据/安装/模型/OCR/推送/A05题22；Git显式 `-c core.longpaths=true`。field reset保持 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`。
