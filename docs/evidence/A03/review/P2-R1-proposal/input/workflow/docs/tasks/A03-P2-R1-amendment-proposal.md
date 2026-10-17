# A03 P2-R1：先收口最小合同补充提案

2026-10-17，Asia/Shanghai。继续原执行对话，明确 `xhigh`。原目录 `C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800`；基线冻结交付 `c30526958e313141bf64152627591b0907b04aa8`。本轮是一次有界设计返修，**尚未批准合同或功能实现变更**。

[独立P2报告](A03-review-report.md)结论REWORK；主调度已验证330份归档及冻结源码中的无条件 `EVENT_PREFIX_CONTRACT_GAP`。真实已接受/永久预留、intent前退出场景没有两新读及未尝试事实；I01不释放。

请只新增 `docs/tasks/A03-P2-R1-amendment-delivery.md`（执行树内）、`docs/evidence/A03/execution/P2-R1-proposal/` 以及必要的 `examples/a03/P2-R1-proposal/` 静态样例，交付以下可审阅提案：

1. 单独版本的runtime事件前缀：明确实际全局起点/前驱、每类事件及严格payload、永久动作预留、完整书账本和CAS关系；列出拟变更精确源码路径。不得删owner/control/其他计划事件、重编号、修改旧七Schema/API/profile原字节，或用complete布尔替代完整性。
2. 报告关联：给出无原receipt但后来有完整receipt、各action恢复头引用不同snapshot两种组合的最小完整静态包和逐消费者引用关系，明确新版本如何消费，保持旧头不可变；不自行豁免R17。
3. 新PRE/hold：给出合法全合成PRE生产/接纳入口、来源与正向清hold及最终二次变化测试计划；不实现B模块，不伪造真实检查。
4. 显式合成转换与失败/中断：说明批准版本的支持范围、原件保全、INCOMPLETE和重开处理。未知DB继续拒绝，不扩大自动迁移。
5. 历史失败原件缺失保持NOT_RETAINED；说明下一轮如何完整保存新运行。不能重建冒充旧原件或将新成功写成旧失败已恢复。

静态样例允许体现PROPOSAL/UNIMPLEMENTED，不伪装成运行验收。给出版本、字段语义、完整样例及预期拒绝、受影响消费者和后续最小测试矩阵。设计存在无法自洽之处时具体列出，不无限展开或自行放宽标准。冻结提案提交、报告和清单后结束；主调度将独立审阅并在有明确批准后另发实现范围。

不得改产品/根依赖/公共入口/调度state/任何旧证据；不运行产品或旧场景，不安装包、访问网络/平台/浏览器/profile或调用模型。已有自动审查拒绝的字段重置专项继续NOT_EXECUTED，禁止复跑、变形或另派。全程离线，不推送，不联系B或验收者。
