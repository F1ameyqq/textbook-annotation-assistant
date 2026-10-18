# I01-A 调度有限离线接受

2026-10-18。结论：**ACCEPTED，仅限 A01 公共离线消费与 N/E/U 三条固定 synthetic 路径**。本记录先于本地集成；集成提交及检查另见集成记录。I01 跨侧正向业务未通过。

作者交付 `3fdc5d37e221fc73410f197605f5d7b8878182d5`，实际运行候选 `be68b8d7c645de556d601458d1d493258f063721`；组合基线 `a1c3c3b2d452ecbdf5c57a8b7372e7d53de0f8d8`。独立验收对话 `01a14e1c-1d38-7fb3-83f2-015b0380ea56` 已 completed/idle，交付 [固定报告](I01-A-review-report.md) 和释放证据，未自行集成。

| 原件 | SHA256 |
|---|---|
| 独立报告 | `3ce68d3843f872e2a55c096836db777ab39edb89270e9c24ddc7dd485a98c7df` |
| 独立678成员清单 | `e29721fb92487c9e6c13a6108ad2bb4c0821b69ae7ed8269e7dadbdacdbfbbe3` |
| 独立释放记录 | `c1eda7b0e93b5e002f2cbf8aedc38d41e6b8617251c709592e06dc74e39a823d` |

调度复算全部678成员长度/SHA，零不符，并核对固定报告、运行身份、原始矩阵与释放；辅助只读审计复核34个候选成员、91个基线原件、30 pins、140实际导入记录，以及正式回执/事件/解决链。调度实际从 Git raw blobs 取固定 `check_freeze.py`、support 和输入身份，独立运行其纯静态检查，输入摘要零不符，未导入产品、未打开SQL、未创建target或dispatch。记录在 [本轮调度证据](../evidence/coordinator/heartbeat-20261018-0854/)。实时核对19个登记业务PID均不再占用；未终止任何进程。

接受事实：A01两公共入口各一次，完整资源校验，coverage_eligible=false；N/E/U各1 target、1 dispatch、1题两框。E旧链TARGET_CHANGED，旧plans/intents/permits/dispatch/effects为0，新链独立生成。U保留原UNKNOWN及暂停，原进程退出后一次MATCH/RESOLVED_APPLIED，恢复前后effects不变、旧事件前缀及原回执保留、零重发，pending归零。正式POST/Batch保留内容PENDING与NOT_SUBMITTED。19个业务进程完成，五组静止capture的owner/PID为空、lease=0，keeper已停止。

作者两次冻结及打包纠正、独立四项静态错误均保留，不重置次数、不重跑成功业务。主索引在并发调度期间发生变化是已披露事实，不作为恢复索引理由；独立运行身份与其无关。静态错误缺少独立OS PID/raw stderr仍如实保留，业务及顶层原始流齐全。root的59项Git状态缓存提示经raw字节核对与HEAD全相同，没有据此重写产品。

后续仅范围明确地本地合入作者666个新增路径和本次独立证据，保留产品/合同/pins/依赖原件；合入后再做原字节和静态冻结检查。运行驱动的 `HEAD == --candidate` 守卫保持，集成HEAD不能冒充原运行候选。

此接受不证明真实A01→native、B原生可执行映射、共同合同、内容/OCR/平台或联合业务。B接收仍由A06独立处理，未推送、未向B发送新材料。
