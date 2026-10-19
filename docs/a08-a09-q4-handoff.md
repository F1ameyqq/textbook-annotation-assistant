# A08 / A09 交接：新批次只读接收与第一课时第4题离线模拟

2026-10-19。**A08固定四案例只读接收、A09第一课时第4题离线模拟均已完成独立验收、调度有限接受及本地集成。** 本次发布代码、冻结验收材料与当前范围说明；其他三个案例继续HOLD，不连接平台。

发布分支：[codex/a08-a09-q4-handoff](https://github.com/F1ameyqq/textbook-annotation-assistant/tree/codex/a08-a09-q4-handoff)。唯一父为已发布A07 `e37606d74d7e538052c563d02df11c6c961b742f`，内容来源固定本地 `929ca1cb198b87a5efdd2723946f7bb69f316a1c`。这是选择性代码/证据交接，不推送整个本地研发历史。

## 阅读入口

- [可转发给B的消息](handoff/a08-a09-q4/message-to-b.md)：已完成内容及本题仍需共同采用的技术口径。
- [接受范围、版本和证据索引](handoff/a08-a09-q4/acceptance-summary.md)。
- A08：[独立报告](tasks/A08-review-report.md)、[调度接受](tasks/A08-coordinator-acceptance.md)、[本地集成](tasks/A08-local-integration.md)。
- A09：[独立报告](tasks/A09-Q4-review-report.md)、[调度接受](tasks/A09-Q4-coordinator-acceptance.md)、[本地集成](tasks/A09-Q4-local-integration.md)。
- Q4：[单页核准图](reviews/q4-first-lesson/review.pdf)、[原proposal](reviews/q4-first-lesson/proposal.json)、[用户新授权](approvals/A09-Q4-offline-business-approval.json)。
- [新C01最终包](evidence/A09/review/archive/candidate-1/trial/normal/final-bundle.json)、[独立实际读回](evidence/A09/review/archive/candidate-1/trial/normal/assets/readback.json)、[独立模拟回执](evidence/A09/review/archive/candidate-1/trial/normal/receipt.json)。
- [发布成员清单](handoff/a08-a09-q4/manifest.json)、[只读完整性检查](handoff/a08-a09-q4/verify_archive.py)。

## 当前完成的范围

A08提供可导入 `annotation.source.b_batch` 与CLI，只读消费固定B PR #3 `a76e5a925fec76f20818dfdefa4145aa132ec8a8` 的stage包，保留一个题答候选与三个答案证据案例的区分。作者和独立各完成1原包、11个原有限负例。接收原件仍为HOLD；完整外部G0.8/Check0.8/plan0.3未加载，不能将stage接收当作这些外部完整对象通过。R6只证明观察库存删除被结构门拒绝。

A09在用户对第4题的独立业务核准下，完成真实OBSERVED来源→新C01→五项实算PRE_APPLY→显式模拟TARGET→一题四框计划→实际内存变更→独立读回/模拟回执。新增入口为 `annotation.source.b_q4`、`annotation.quality.q4_offline`、`annotation.delivery.q4_offline`。四框为Q/image、Q/text、Q/text、A/text，内容、精确坐标、原图及顺序与批准表一致，答案13，无W/E；fill_blank映射C01 free_response并保留来源，题干三片段同页cross_page=false。作者和独立各1正常尝试/1成功/1dispatch，各10次拒绝零新增变更。

两项任务均已释放，成功及有限验收额度不因发布恢复。本次只做静态发布完整性、成员、链接及范围核对，0新增接收或模拟业务。

## 核验发布完整性

在此分支检出目录执行以下只读命令，使用Python标准库与Git：

```powershell
python docs/handoff/a08-a09-q4/verify_archive.py --ref HEAD
```

脚本读取raw Git对象，检查发布成员与四份冻结作者/独立清单；不导入产品、不创建目标/计划、不运行B脚本或模拟。这只能证明归档完整性，不替代功能验收。

冻结证据中的派发副本 `docs/evidence/A09/review/dispatch/A09-Q4-review-dispatch.md` 保留了原文件的六处相对链接；副本搬入归档后这些链接不再相对成立。请使用[原位置派发说明](tasks/A09-Q4-review-dispatch.md)中的对应链接查看任务、输入和预检资料，原冻结副本不改写。

历史 `examples/a08/`、`examples/a09/`、测试与审计脚本按原字节保留。它们可能依赖当时本机路径、原输入及历史Git对象；这些历史提交不随选择性单父发布自动可达。A09实际运行HEAD仍为 `29c82b0997be3080f53dfde2afbb1d7457b04197`，发布HEAD不能替代它。不要修改pins、ExpectedHead、预算文件或绕过守卫复跑。此次不新增跨机器业务复现、安装包或平台验收结论。

## 仍未闭合的事项

B尚需确认是否共同采用固定第4题的版本/摘要、题答关系、四框语义和本题政策，并确认能够读取新C01、计划、实际读回及模拟回执的引用绑定。业务方已核准本题，无需重复业务批准；已收样例、历史E0.1和Q1共同采用无需再次补交或确认。

原B HOLD、原proposal false、原检查/账本与新A授权分别保留；旧冻结报告中的“待核准/未推送”等为形成时点，本次不回写。来源OBSERVED，目标/计划/回执SYNTHETIC/SIMULATED，A_INTERNAL_PROPOSAL/PROPOSAL_ONLY、NOT_SUBMITTED/PENDING保持。Q1固定技术采用已由[B接收记录](tasks/B-update-reception-2026-10-19.md)确认，不转移为Q4共同采用。

其余三个答案证据案例——小专题“方程思想”Q4、反思跨页Q9、第二单元Q16——继续HOLD，无题ID时不造题答关系；N01–N08未全部闭合。A04真实平台仍BLOCKED。本次未连接平台、未送审、未向B发送消息；由用户转发说明。
