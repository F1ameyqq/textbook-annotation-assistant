# A06 F01：第二、最终候选的有界纠正

2026-10-18。调度核对[第一候选独立报告](A06-review-report.md)、507成员清单、释放证据和固定源码后确认 **REWORK / F01**。这是[原任务](A06-b-native-receiver.md)中 wrapper 与 payload.result 各自版本/身份要求未完整实现，未增加标准。现明确使用原最多两次冻结实现中的第二次、最后一次额度，续派原执行对话 `01a14e1e-23fe-7c30-81cc-74a786c6559a`。

## 固定起点与缺口

起点为作者交付 `761d9afed8b9d3d33851ad3d79b0bee7c294089d`；第一实现候选 `9076d35e81678cdba8ad8651e95a44265fdc345c`。工作目录仍 `D:/1800-worktrees/a06`。公共基线仍 `a1c3c3b2d452ecbdf5c57a8b7372e7d53de0f8d8`；不要合入浮动主线或I01资料来扩大产品差量。

`src/annotation/source/b_handoff/reader.py` 原SHA256为 `241b2de4b82e84e12f5067bb8079d4cad6925339e0f9a343587fff5f2f2428f3`。303–304行校验wrapper版本/kind；306–307行对result只有引用核对，48–49行ref不含版本/kind。F01为静态确认，第一验收没有运行额外中间版本变体，不能改写成已动态证明绕过。

固定报告SHA为 `fdefde2e92095b9e922ae264a6b9595af5d93ee4c6dd5f5f980e941a031c0ae4`，清单SHA为 `b3842a023b39c1f26ba42db6eab93329adfae4ad084e756b09cb67a780af5624`，释放SHA为 `3917bf27b1d013dad625b2bfdb9b779fcc877dabe15380b147f8405399f64ea9`。原件在主目录 `docs/evidence/A06/review/candidate1-761d9afe/`；只读使用，不改写。

## 唯一产品纠正与原样保留

只在原A06产品白名单补齐固定14个stage对应result的明确kind/schema校验，保留既有引用、规范化摘要、资源、当前绑定和历史未决规则。可由 `original-inspection.json` 的 `wrapper_result_versions` 与原ZIP核对建立有限stage→kind/version表；不能仅凭字段相似接受未知版本，不能以payload摘要替代外层schema/kind。

原包中E0.2、G0.3、Check0.3/.4/.5及独立trial kinds只在其确切stage历史诊断语境处理，不扩展当前顶层允许版本、执行资格或公共合同。输出能区分结果层版本已经核验和历史诊断用途；未知或错配明确拒绝并给result路径/版本层。原current E0.3/G0.7/Check0.7仍HOLD，历史0.4/.5 archive规则、0.6拒绝不变。

允许范围为原 `src/annotation/source/b_handoff/` 中该缺口所需最小实现、`examples/a06/` 的新差量配方/记录和必要说明、`tests/test_a06*.py` 的窄版本检查；不改公共contracts/native/delivery/runtime/pins/根依赖。旧测试配方、报告、证据均保留。新报告为 `docs/tasks/A06-second-final-execution-report.md`，新证据目录 `docs/evidence/A06/second-final/`，避免覆盖首包manifest和报告。

## 一次差量运行与退出条件

先完成静态接线、已观察14组stage kind/version与拒绝分支的窄检查，再冻结第二实现候选。无需额外设计评审。冻结后作者本次只实际运行以下两个完整接收入口，各一次：

1. 原固定ZIP：HOLD、原事实/历史引用未决及全部既有绑定不变，14项结果层核验可定位。
2. 将原“未知版本”场景定位到一个非最终stage的 `payload.result.schema_version`。在新副本确定性变更，重算必要wrapper、pipeline和manifest摘要与绑定，确保到达结果层版本门并明确拒绝；保留配方、前后身份及原始流，不把最外层hash拒绝算通过。

上述是原未知版本场景在F01处的差量定位，不新增业务场景矩阵。窄字段检查仅覆盖已观察14组明确分派，以及一个未知版本、一个错kind的拒绝；不生成其他完整包或补造0.6正例。坏资源、陈旧Check、原顶层版本/历史矩阵和C01三消费者，在实现相关路径原字节未变的前提下引用第一独立证据，不重跑全集。若修复不可避免影响这些路径，冻结前报告确切影响，由调度决定差量，不能自行扩大。

原ZIP SHA256仍 `b2bed674f87cde7fb2df4fdf31dec9ede08f494fc6190f654abda51dd4dae89d`，仅用既存本地包。零B脚本/生产者/SQL、平台/profile/凭据、网络/安装/模型、外部联系或push。不能改变UNRESOLVED_HISTORY_REFERENCE、UNCONFIRMED_REQUIREDNESS、optional=null及c01_execution_eligible=false。

交付第二固定提交、报告、原字节SHA/长度清单、实际入口和自有进程释放后，调度再续派已登记独立验收做同样两项差量；独立不能现在审浮动代码。第二候选冻结后失败保留并停止，不改后重跑、不第三包或改名恢复额度。作者不能自行记ACCEPTED或INTEGRATED。
