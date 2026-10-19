# A08 / A09 发布回执

用户明确授权整理并推送A08/A09代码与验收材料，其他三例继续HOLD，暂不连接平台。本次已完成。

- 远端分支：`codex/a08-a09-q4-handoff`
- 已核实提交：`edf125961be9cdc1642652c038d99872b1c8cdc7`
- 发布树：`58bd1ff202d70ffacf1b9fbb90121e0cbfa70ef3`
- 唯一父：已发布A07 `e37606d74d7e538052c563d02df11c6c961b742f`
- 固定内容来源：`929ca1cb198b87a5efdd2723946f7bb69f316a1c`
- 操作：非强制、单引用推送，退出码0；随后单独ls-remote核实远端精确提交。

## 发布内容及检查

356来源成员、7生成成员及manifest；361新增、仅3元数据更新、0删除。四份作者/独立冻结清单共307成员及清单自身保持；完整源码树等于固定源。父树其余12,480路径与根依赖不变。

独立静态结论PASS_STATIC_PUBLICATION_SCOPE_ONLY。363个发布清单成员与307个冻结成员核验一致；155相对链接有效。冻结派发副本保留的6处搬移后失效链接已在新入口明确导向原位置，不改写旧证据。12个ZIP/288成员经归档路径及所列敏感模式静态检查，无命中。发布没有重跑接收、测试、模拟或产品业务。

[发布静态核证](../evidence/coordinator/a08-a09-publication-20261019/audit.json)、[独立审查](../evidence/coordinator/a08-a09-publication-20261019/independent-publication-review.json)、[归档核验](../evidence/coordinator/a08-a09-publication-20261019/archive-check.json)、[远端回执](../evidence/coordinator/a08-a09-publication-20261019/push-result.json)。

main、B、架构、stage1、stage2、A07六个既有远端引用在本次推送前后均未变化。没有合并main、修改B分支或发送B消息。

## 使用入口与剩余边界

[远端固定入口](https://github.com/F1ameyqq/textbook-annotation-assistant/blob/edf125961be9cdc1642652c038d99872b1c8cdc7/docs/a08-a09-q4-handoff.md)、[本地入口](../a08-a09-q4-handoff.md)、[用户可转发消息](../handoff/a08-a09-q4/message-to-b.md)。

A08证明固定四例只读接收；A09证明已核准第一课时第4题真实来源到四框本地离线模拟及独立读回。实际四框Q/image、Q/text、Q/text、A/text，答案13，类型/内容/坐标/顺序按批准表。运行产品仍29c82b09，发布HEAD不能冒充历史运行身份。

待B共同采用固定Q4版本/摘要及题答绑定、四框与单题政策、新C01/计划/实际读回/模拟回执引用。Q4业务核准已完成，不重复索取；Q1已采用的口径和已收样例/E0.1不再要求。远端可用不等于B已读取或共同采用。

其他三例继续HOLD；原B HOLD、proposal false、Check和账本保留；完整外部G0.8/Check0.8/plan0.3未加载。0平台、0新业务，A04真实阻断保持。发布不恢复任何验证额度。本回执是推送后的本地调度记录，不为增加此回执再次推送。
