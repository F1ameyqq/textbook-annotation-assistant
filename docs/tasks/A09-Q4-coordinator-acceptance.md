# A09 第4题调度有限接受

2026-10-19。调度结论 **ACCEPTED_FIXED_Q4_OFFLINE_FOUR_FRAMES**：用户批准的第一课时第4题已完成真实来源到A本地离线模拟的固定链。独立验收建议PASS，经调度核对固定证据、释放和适当归档复算后有限接受；范围集成另记。

- 唯一实际运行产品：`29c82b0997be3080f53dfde2afbb1d7457b04197`。
- 作者最终交付：`439423ebf4277e3825aba24fed6f56546ef66a2b`。
- 独立固定交付：`25fcf2171df87bd7da97528efbe5bc24399d336a`，见[独立报告](A09-Q4-review-report.md)。
- [用户授权](../approvals/A09-Q4-offline-business-approval.json) SHA256 `5c73af50262f6bd7e48e2b0d46148026c1c3a953d1ee93c8262e356733d99010`；原proposal `e8146fc7a4fe2e16c1fc1194d49de1caa1fe029dd6907848bbaa6c9082dc0bbe`保持。

[调度核证](../evidence/coordinator/a09-acceptance-20261019/verification.json)逐项核对独立清单92成员、5,104,118 bytes，另有清单自身；清单SHA256 `68653cd9a562b05daf996ca963c26cb72f1ff1656bda5c43116d47a7d05d685c`。独立仅新增93路径，作者交付29,817条旧路径mode/type/blob全保留；102运行成员仍等于固定产品。原ZIP、全部24成员、授权/proposal/输入登记及原图raw身份通过。作者95成员及清单自身的预检证据保留。

调度从raw Git导出公共校验器和独立归档，重新验证准备包、最终包、合法重封反例的C01资源、摘要、引用及归档计划准入；没有创建新目标或运行业务。另有[辅助静态核对](../evidence/coordinator/a09-acceptance-20261019/static-review.json)，未发现有限接受阻碍。

实际读回直接与用户批准表比较，恰好1题4框，类型与角色如下：

| 顺序 | 角色/类型 | 原图 | 坐标 | 内容 |
|---|---|---|---|---|
| 1 | Q/image | viewer-10 | [334,975,581,1077] | 完整几何图，text=null |
| 2 | Q/text | viewer-10 | [100,1118,592,1193] | 去题号的前两行题干 |
| 3 | Q/text | viewer-10 | [99,1202,220,1235] | ____ cm. |
| 4 | A/text | viewer-173 | [324,239,342,257] | 13 |

真实内存由0题0框/epoch0变为1题4框/epoch1；基础frame角色/坐标/题绑定与frame_projections类型/文本/原图/顺序逐项相符。一个逻辑题，无W/E；fill_blank映射C01 free_response并保留来源，题干同页cross_page=false。五项PRE_APPLY与显式模拟TARGET有实算记录。合法重封image→text通过C01，但在原类型语义层HOLD；原10拒绝逐份零新增题/框/dispatch，非同一个外摘要门冒充全部语义。

独立新回执 `a09-receipt-a09-q4-50888` revision1、content_hash `82346ba80d6b44bd5d609464b7b9de58e9404d08f05ab6bdca94b579172e2bef`，APPLIED/MATCH、不可重放。读回raw SHA256 `5c568274409cd7740d879bb5d0482e54282c752381dd90e84ed30a5cdf0df048`。这是SIMULATED效果，NOT_SUBMITTED/PENDING保持。

作者、独立各1冻结候选/1正常尝试/1成功/1dispatch，各10拒绝零新增变更；成功额度均耗尽，不再重跑补证或恢复额度。独立PID61820/50888原句柄均exit0，本次查询均不存在，已完成释放；未终止其他进程。调度0新业务、0新目标、0产品测试。

调度初次归档选择器误把既有C01 `payload.stage`写成`payload.phase`，已按原合同纠正并保留[检查器记录](../evidence/coordinator/a09-acceptance-20261019/checker-correction.json)。该问题没有修改产品或回执、重跑业务或消耗候选；原预检的Git引用选择器纠正也保留。

接受仅限固定书46007447、题`q-260d10c51f2b7c16fb6fefb5`、答案`a-92c4d2164ab878c8e6d4c88d`及批准四框。来源OBSERVED，目标/计划/回执SYNTHETIC/SIMULATED，A_INTERNAL_PROPOSAL/PROPOSAL_ONLY；新A核准与旧proposal false、B HOLD/UNVERIFIED、原账本分开保留。其他三例继续HOLD；完整外部G0.8/Check0.8/plan0.3未加载，不声称B共同采用、公共合同冻结、OCR或平台资格。未推送、未向B发消息、未连接平台，A04真实阻断保持。
