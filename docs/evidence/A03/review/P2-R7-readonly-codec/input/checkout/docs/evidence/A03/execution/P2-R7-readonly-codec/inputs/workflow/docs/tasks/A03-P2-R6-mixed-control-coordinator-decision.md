# A03 P2-R6 调度决定：单一混合环控制收口

2026-10-17。结论：**ACCEPTED_STATIC_LIMITED**，仅接受修正后的混合环控制证明。目标提交 `81d3ec7e42e0a1a76ad744bf59536fc5f68adee4`，base `323013c4f0dbae75368e56db60147a8057368d1f`。本轮结束静态控制输入修复；旧失败记录保持原样。

依据[独立报告](A03-P2-R6-mixed-control-review-report.md)及[调度复核](../evidence/coordinator/heartbeat-20261017-1144/A03-R6-review-check.json)：

- 独立报告 SHA256 `bd0735fde3f6980d7b38315a4aa9511c197e5c70617524626cfddb68e8ff4d25`；清单 SHA256 `d8a220955728b327301c2602b7b0fe42d3dc5a65c0eef8964a025b18724744e7`。调度核对 157 个清单项及 123 份 raw Git 输入。
- 调度独立数据差分确认：prefix 恰好 15 处变化，bundle 仅一处 Resource 摘要变化；事件链、内部头、accepted anchor 及原有 Artifact/ref 保持约定。新数据没有删 UNKNOWN 或登记历史。
- 一次只读完整入口实际到达 MIXED_DAG 并拒绝 MIXED_CYCLE；R5/R3/R2 各调用一次，44 个真实消费者、0 个 None-book 消费者、consumer_failures 为空，五条环边均实际存在。复现后审阅归档字节不变。
- 独立审阅 3 个和调度 2 个自有子进程均退出。作者最初 SyntaxError 的原脚本、日志和退出 1 保留，其发生在模块执行前；没有掩盖失败或补跑该失败脚本。释放证明只覆盖已登记自有进程，不冒充 OS/profile 扫描。

R5 六项有限静态接受、R4 有限接口设计、R3 消费者闭包及 SESSION-02/CONVERSION-07 原结论保留。本轮不重复旧矩阵，不取得 oracle、PRE 签发、native、SQLite 恢复、R17 或 I01 资格；A03 P2 整体仍未验收或集成。字段重置专项仍为 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`。

下一步按[R7 产品只读 codec 实现](A03-P2-R7-readonly-codec-implementation.md)派给原 A03 执行对话。范围是把已验证的结构/引用/消费者/混合 DAG 校验迁入可安装产品模块，消除产品依赖 examples 的临时加载方式，并冻结一个明确无写入资格的接口。它是原 P2 的一个有界产品实现切片，不再扩展静态控制修复系列。

R7 后仍须完成实际 PRE 签发与 CURRENT 采用、历史 creation-input 派生边界、原生单动作 UNKNOWN→只读对账→迟到回执→新 POST/Batch 调用链，再按原 P2 验收矩阵核对实际持久化/故障/恢复行为。各自需要产品证据，不能用本轮静态通过替代。B 输出包接口映射另待共同确认；本轮无 B 消息、在线操作、产品集成或推送。
