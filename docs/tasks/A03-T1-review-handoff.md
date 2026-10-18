# A03-T1 冻结交付独立验收

2026-10-18。继续已登记 T1 独立验收对话，不新建对话，不唤醒旧 A03。基础范围仍为 [T1任务](A03-T1-capture-and-inconclusive.md) 与 [拆分约定](A03-redispatch-2026-10-18.md)，产品只读，原 xhigh 新任务规则保持。

- 产品基线：`1330047dd29890dea0e433ff01b991f615bf78f4`。
- 冻结代码：`73f21654adb8ee86e33381a3ff3bf1a179303928`。
- 完整交付 target：`ed90664ab15afd1938725441e2bc86db7884f784`。
- target 内报告：`docs/tasks/A03-T1-execution-report.md`。
- manifest：`docs/evidence/A03/T1/execution/manifest.json`；SHA256 `3fe14986f26b058c200cc75c2922be811dc1d31a98e60fefd9ab986d34036063`。
- 退出/释放及首错索引：同目录 `delivery/state.json`。调度已核对865项 raw Git 摘要、56份业务阶段库原件存在、37个登记Popen完成记录和六组owner最终释放记录，产品相对基线无改动；工作树干净、作者对话completed。此项仅交付预检，未作独立业务验收。

作者实际六例 L1/U1–U5 均完成一次，报告为 PASS_AUTHOR_ONLY。第一次静态 pin 失败来自 checkout CRLF；唯一工具纠正改用固定基线 raw Git 执行视图，不改产品或 pins。六例之后的内联汇总对 legacy L1 读取不存在的 native_report_reads 表而 KeyError；冻结 seal.py 有同一错误假设，未运行。两次失败保留，统一语义 seal 未完成；作者正确停止并建议REWORK，调度尚未作功能结论。

本次验收一次完成以下有界工作，不先增加一轮作者“seal通过”审批：

1. 在自己的隔离副本核对固定源代码、manifest、raw执行视图、全部必要阶段原件和真实退出/释放；独立只读审计自己的 immutable 原件，区分 legacy 无该表与 native 计数0。核对实际 Resource 闭包、场景与阶段，不以作者 SQL.json/断言替代独立检查。不可追构旧失败原件。
2. 评估 capture.py 同步/事务关闭/keeper stop-join-restart 边界及小夹具。原任务要求可验证证据、可消费工具及六场景，并未指定作者自选 seal.py 必须成功；不要把该脚本成功额外设为业务门槛。其缺陷仍必须记录，不能隐瞒或称已修复。若必要原件实际齐全且工具适用，可由本验收的只读核查建立语义证据；若真有缺件/错误则列确切缺口，不能降标准。
3. 前述前置满足时，按原任务在新目录独立跑相同六例各一次，不消费作者业务库；使用固定 raw 产品字节，不改 pins 迁就 CRLF。保留同步夹具、适用阶段库、实际执行身份与释放；原观察/屏障/lease及子/父时限保持，native_report_reads=0，恢复效果增量0。采用自己的必要审计/报告逻辑，禁止调用已知必错的作者 seal 或修改作者原包来伪造通过。不得重跑 C/H1/R9–R11/field reset。
4. 给出原范围的有限 ACCEPTED/REWORK/BLOCKED 建议，分别说明取证模块是否可供T2使用、六例是否成立、归档脚本缺陷是否影响必要交付。如果需修复，只列一份合并的最小路径/缺口清单；不要逐辅助函数滚动增加标准，不自行安排第二次作者修复。

输出仍限 `D:/1800/.local/A03-T1-independent-review`、`docs/evidence/A03/T1/review/` 和 `docs/tasks/A03-T1-review-report.md`；主目录索引/提交、产品、调度状态不写，由调度归档。真实失败保留；独立新增驱动错误的一次有界纠正遵守共同任务约定，第二次停止。所有已知限制及旧失败保留；不把本次范围外推到T2、A03整体、I01、平台或B确认。
