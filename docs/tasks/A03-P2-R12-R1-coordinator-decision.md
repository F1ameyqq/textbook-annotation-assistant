# A03 P2-R12-R1 失败收口与内部问题归属决定

2026-10-18。A03整体仍为 **REWORK**，本轮结论为 `FAILURE_AND_REPAIR_BOUNDARY_CONFIRMED`，没有新增功能ACCEPTED或产品INTEGRATED，I01仍未释放。

[独立复核报告](A03-P2-R12-R1-failure-review-report.md) SHA-256 `145412bb9b81958d4615ff47d0943956552da3e73649cd5afc0c8731934ba227`，复核冻结目标 `6affc61d2ab0b1f0d96bb2497c5ae969ebaf1df2`（代码 `7694490ef25539d131b863bdcb2b21531c69dfae`）。[调度核对](../evidence/coordinator/heartbeat-20261018-0945/r12-r1-failure-corroboration.json) SHA-256 `1a3f5218867ff5e7ab1c08db246e16451c1dd95b83736cc74cd132a3aef74049`：481项manifest成员、399份raw Git来源、9个复核子进程退出记录一致；调度另外查询了12份自己的immutable阶段库副本。未导入产品、未运行功能、未连接作者或复核者原库。

U1确有UNKNOWN fact、PENDING intent、CONSUMED permit、INTERRUPTED plan和一次部分目标效果；receipt/progress未形成，报告读回未消费。释放后owner/PID为空、phase为RELEASED，未清除事实或目标效果。类限定AST再次确认receipt追加位于792行、报告策略条件位于794行。调度查询最初误以为目标按questions/frames表存储，首错与脚本已保留；按实际meta.state.target改正后复核通过，只有自有副本只读查询，无功能重跑。

问题来自原有native投影闭包：runtime局部生成SAVE_UNKNOWN issue，却没有在receipt校验前建立可验证归属；native到C01视图排除正式POST并去掉fact细节，C01只能从CheckReport取问题声明。显式POST又先需要合法receipt。上一轮报告格式缺陷仍需隔离，但隔离报告不能解决这个更早的问题；不得宣称本轮四文件改动新引入了缺口或已证明只有此一处故障。

## 调度作为A内部合同负责人作出的决定

采用独立复核提出的**事实派生归属**，仅用于当前A内部固定SYNTHETIC native profile。经过完整Resource字节、来源/范围、plan/action/digest/intent、结果和尝试事实验证的原UNKNOWN action fact，是确定性SAVE_UNKNOWN issue的来源。每份receipt使用其自身不可变action_fact_refs计算归属，不能依赖未来报告、数据库当前action指针或最新恢复结论。

- 现有issue ID规则 `issue-save-unknown-` 加 canonical fact digest前32位保留；完整Issue内容也按同一纯规则推导，包含真实证据、action范围、blocking、APPLY/COMPLETE及RECONCILE策略，不只生成ID白名单。
- native receipt的未决绑定必须与其原始UNKNOWN facts严格一致；缺项、多项、重复、外plan/外scope、伪造或篡改fact/Resource均拒绝。历史receipt不能因后续解决而丢失原issue来源。
- 私有C01语义检查可以消费上述已证明的绑定，但必须保留receipt中的原ID并绑定确切消费者；不得放宽C01公开默认校验、接受任意调用者传入的允许ID集合，或让一个receipt借用另一receipt的问题来源。
- 该派生内容是原始事实的确定性解释，不是新的质量报告或独立平台观察。不会自动创建POST/Batch，也不消费报告读回预算。正式报告继续由现有独立新鲜观察入口生成。
- 本决定不新增序列化产物类型，不改公共schema/API形状，不把这些A内部规则写成B已接受的共同合同。候选代码、输入及对应implementation/profile/adoption摘要须重新冻结；旧包、旧pin、旧失败记录保持原字节。

不采用另建正式Issue诊断产物的替代方案，避免本轮扩展schema/registry/API。若实现证明上述规则在所列4个实现文件内无法安全表达，须交具体不相容点，由调度另行收口，不能自行发明更多类型或放宽标准。

下一步为[一次有界整体修复](A03-P2-R12-R2-issue-ownership-repair.md)，复用原执行与原验收对话。固定候选通过必要合同反例及原L1/U1–U5、受影响历史/报告链验证后，再由独立验收和调度核对。当前没有完成时间保证；以冻结交付及独立结果为准，不再以“一个策略开关修好”描述剩余工作。

本地记录未推送、未共享B。保留此前R11有限通过和作者F2/F3历史原件缺口，剩余A03原验收项、范围明确的集成及B版本映射确认仍分别未完成。field reset维持 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`，不运行、不变体、不委派、不建议重测。
