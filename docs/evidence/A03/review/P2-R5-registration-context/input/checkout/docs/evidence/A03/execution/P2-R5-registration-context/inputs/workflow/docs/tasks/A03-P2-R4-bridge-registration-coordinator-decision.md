# A03 P2-R4 调度收口

2026-10-17。冻结交付 `e608b54b973b14ff55dd2c4530153f5fe7c931f4`。独立验收对话 `01a145aa-8d59-7c70-8d81-731712103a9a` 已完成 turn `01a14944-39bf-71e1-a194-17b714c8f009`。整体记录 **REWORK**；接口方案单列 **ACCEPTED_DESIGN_LIMITED**，登记分支未接受。

依据：[独立报告](A03-P2-R4-bridge-registration-review-report.md)、[198 项清单](../evidence/A03/review/P2-R4-bridge-registration/sha256-manifest.json)、[调度复现](../evidence/coordinator/heartbeat-20261017-1014/A03-R4-review-check.json)。报告 SHA256 `46d2d7aa43eb5a055827ecbacfe9db67ab959575098e52378a1fe9bfa1574049`；清单 SHA256 `311f1fb987c111b21a92ddb7ea00ec36938f6d45be1b1d56dc64a13f59f555ac`。

调度核对全部 198 清单项及清单自身、133 份隔离输入与精确 raw Git blob。归档复核退出 0；仅对原正包再运行一次只读总入口，得到 `FRAME_REGISTRATION_BINDING`、`REWORK_FALSE_REJECTION`、实际消费者随后全局无上下文的两次 guard 路径，期待退出 1。复现前后归档字节不变，两条同步运行均结束；未重跑完整矩阵、未执行产品/数据库/native。独立审阅的归档入口错误及作者历史错误原样保留。

| 范围 | 调度决定 |
|---|---|
| 19 个现有接口与 1 个拟议 PRE 边界 | ACCEPTED_DESIGN_LIMITED；源文件/签名/版本与资格责任盘点可作为下一份实现任务的依据，尚不是可执行 ABI、采用记录或功能通过。 |
| R4-REG-GLOBAL-CONTEXT-01 | REWORK_CONFIRMED；合法登记正包在真实上下文通过后，被全局 evidence 扫描传入的 book=None 错误拒绝。 |
| Source / Snapshot 直接负控 | 独立证据支持实际消费层拒绝；不以错误码相同替代语义定位。 |
| target 元组负控 | BLOCKED_MASKED；尚不能证明正确的目标绑定拒绝，亦无完整入口错误接受证据。 |

批准下一步的局部修复方向：将全局无上下文的字节/引用/图遍历和真实 Artifact/frame 的绑定检查分开，保留全部 Resource、正式证据 ID、消费者声明、typed frame 与混合 DAG 验证。在同一登记分支按已有字段核对 target 元组，沿用 R4 四个完整冻结包，另限三个直接防回归控制。任务见 [R5 有界修复](A03-P2-R5-registration-context-rework.md)。本轮不选择绕开 Resource 放置、把 None 当通配符或修改旧样例来消除失败。

接口方案中的三项具体 ABI 决定留给后续单独的产品实现任务冻结：BridgeSelection/BridgeContext 的字段、角色与精确采用 pins；AdmittedPreRun 的唯一签发/验证及 INITIAL/POST_HOLD 生命周期；历史 creation-input anchor 与非导出派生视图闭包。产品实现不能只采用概念字符串，不能降版重封签、把 PASS/JSON 当当前资格或删 UNKNOWN/登记历史。

R3 消费者闭包、SESSION-02、CONVERSION-07 的有限静态接受继续保留。A03 持久恢复功能、R17 真实调用链、oracle/native profile/跨侧采用及 I01 均未释放。本轮只本地归档、未集成产品、未推送或向 B 发消息。B 输出包仍为已核对字节的 HOLD 交接，映射问题独立保留。字段重置专项仍为 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`。
