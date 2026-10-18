# A07：真实第1题离线模拟本地集成

2026-10-18。在[调度接受](A07-Q1-coordinator-acceptance.md)后，作者交付和独立验收两支分别正常三方合并；原字节范围检查和有限导入/归档合同检查通过，记录 **INTEGRATED**。

- 集成前主线：`a3aa161bc1edd75a92a2f01d573513cb25140537`。
- 作者合并：`ee554db57fa7e26ed5938cc522f8f2ce7b6c7b9d`，纳入作者 `d2e710c817cf85505ac4fad4919dd51d1062d33a` 的64新增路径，运行产品仍为 `6dad9b9a40a10989c102d91cf7b54f19c012015f`。
- 完整集成：`07479d69edcbfe8c051f347d21bea714b085e70f`，另纳入独立 `efe440d07d3600ee9755f1709778a2a742bb2f52` 的55新增路径。
- 两份固定交付是同一产品候选的兄弟提交；保留两方证据，未以独立树覆盖作者树。

集成前29,303条主线路径的 mode/type/blob 全部保留，仅新增119路径，0更新、0删除；新增路径逐项等于各自固定交付。旧公共合同、A03 pins、A06/I01、根依赖和所有历史证据未改。未清理旧活库、pending或无关未跟踪文件。

有限集成检查从集成提交导出 raw 源码，成功导入 `annotation.source.b_q1`、`annotation.quality.q1_offline`、`annotation.delivery.q1_offline`；使用集成 C01 校验独立归档的完整 exchange/pre-execution 及资源，再执行只读 `assert_plan_ready`。结果见[集成检查](../evidence/coordinator/a07-acceptance-20261018/integration-check.json)及[脚本](../evidence/coordinator/a07-acceptance-20261018/check_integration.py)。没有新业务尝试、目标或dispatch，没有重跑原成功矩阵。固定运行候选的 HEAD 守卫保持；复现文档中的运行身份不能改写为此集成HEAD。

当前有限结果是用户核准的书46007447第1题真实 OBSERVED 来源，经过新的 C01 信封/摘要、五项 PRE_APPLY、显式模拟 TARGET，形成1题6框计划并实际变更内存、独立读回MATCH及SIMULATED回执。原件保持HOLD，A用户核准单列，政策仍为 A_INTERNAL_PROPOSAL / PROPOSAL_ONLY；NOT_SUBMITTED / PENDING 不变。

作者及独立各1次正常尝试和1次成功已闭合，不再续派或复跑；拒绝证据为9项窄检查加1次重放拒绝。新Q1确认、业务授权和A07尚未推送、未向B发送。B共同采用/共同验收未证明；A04真实平台仍BLOCKED，题22不重放，平台连接及书级送审不在本次范围。
