# A03 P2-R3 调度收口与剩余范围

2026-10-17。交付 `87606b73e0754fa670491d9fb958a416c26bfe88`，独立验收对话 `01a145aa-8d59-7c70-8d81-731712103a9a` 完成 turn `01a14904-e53b-7132-a8a2-3c942c4b625e`。主调度记录 **ACCEPTED_STATIC_LIMITED：EvidenceRecord 消费者闭包**。A03 整体仍未获功能验收，未做产品集成，I01 不释放。

证据见[独立报告](A03-P2-R3-evidence-closure-review-report.md)、[249 项清单](../evidence/A03/review/P2-R3-evidence-closure/sha256-manifest.json)、[调度复核](../evidence/coordinator/heartbeat-20261017-0859/A03-R3-review-check.json)。报告 SHA256 `4da6e53d451875b285c0ee24e9fafa83d35e6dbcfc0f9af9c592958fe3fd992b`；清单 SHA256 `676db217f198842bb8f2f5e0222b295d876815bf6b633da9dab44083372eedaf`。

调度逐项核对 249 项及清单自身、161 份输入与精确提交 raw Git blob。只读归档复核退出 0；固定原反例完整入口再次得到 `UNDECLARED_REFERENCE`，并观察到新 1.3 receipt 的正式证据消费路径。期待拒绝匹配的退出码为 0。复现前后审阅归档字节不变，没有重跑完整矩阵。两条自有同步运行均结束。审阅者两次驱动失败及其控制流恢复限制原样保留；调度脚本生成时 Python 3.9 的 newline 参数错误另记 setup-error.json，发生在复现开始前，改为文件 open 后只执行一次复现。

| 范围 | 当前决定 |
|---|---|
| EvidenceRecord 消费者闭包 | ACCEPTED，仅有限静态入口、原反例和相关合法/非法控制。 |
| SESSION-02 / CONVERSION-07 | 保留 R2 有限静态接受；真实会话、持久化与转换未通过。 |
| R17 新旧版本桥接 | 进入下述有界接口准备；实际新初始派发仍阻断。 |
| 无计划登记的 scope 推导 | 补一份完整静态正包及直接不一致控制；原生登记行等值另待功能验证。 |

选择 [R2 独立报告](A03-P2-R2-proposal-review-report.md) 的第二条桥接路线：明确 A 侧 contracts 版本/资格与 A02 bridge 的兼容边界，再安排实现。方向是为新的 A03 版本定义显式接纳接口，保留 A02 的计划生成和事实比较规则；不把新 1.3 候选改标签成旧 1.1 来绕过入口。旧 1.1 仍为不可变只读输入，旧 UNKNOWN 尾部不恢复。此决定只批准接口方案与静态样例准备，不批准产品实现、oracle 采用或公共合同发布。

下一步为 [P2-R4 桥接接口与登记样例](A03-P2-R4-bridge-registration-preparation.md)，继续原执行/独立验收对话，消息省略 thinking 和 model，保留用户设置。交付一次后冻结；独立审阅与主调度确认确切接口/pins 后再派有界实现。无法在范围内闭合时报告具体矛盾及选择，不自行追加大候选或下一轮。

既有字段重置专项维持 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`。没有平台、模型、凭据或 B 消息。B 新输出包的[接收记录](../b-handoff-receipt-2026-10-17.md)独立保留：字节已核对、业务 HOLD、映射待确认；这不解除 A03/I01 的恢复依赖。本轮归档与决定只在本地，未推送。
