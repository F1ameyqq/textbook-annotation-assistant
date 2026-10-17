# A04 coordinate-R3：主调度限定接受

2026-10-17。固定交付 `6c8137a4fadddc01a47906d564ab3460277c8958` 的 **OFFLINE_R3=ACCEPTED**；**A04_OVERALL=BLOCKED，产品尚未集成**。

原 [R3独立报告](A04-coordinate-R3-review-report.md) 的输入来源描述有误，保留原件；[原始字节补充报告](A04-coordinate-R3-raw-bytes-review-report.md) 已明确更正。主调度核对补充602项清单、原355项及原清单自身未变；新212项运行输入逐字节等于目标Git blob，object ID、SHA256和大小一致，也与主调度此前精确反例复现所用212项原字节相同。见 [本轮核对](../evidence/coordinator/heartbeat-20261017-0734/A04-raw-byte-supplement-check.json)。

关键缺行反例已由主调度在原始Git导出上复现拒绝：wrapper 0、公共CLI 2，无输出目录/历史/有效包。补充验收在未改脚本和预期上完成70项相关回归、26项独立检查，三张原始PGM经发布与搬运后的资源hash均正确；28个记录的自有进程身份已结束。没有新的产品差异，本轮不重复整套测试。首次字节核对失败、旧archive表示及两次运行原始记录完整保留。

接受范围仅为本次PNG行完整性修复、受检静态布局、发布前原图复查、正常PNG/JPEG/PGM搬运及有界资源行为。APNG和尾随字节明确拒绝；未证明所有PNG元数据语义、配置极限性能、图像内容正确或全书来源完整性。新清单SHA256为 `391d604ba305236f0ae6aa8dee778c5ae3157e5a89b32e96d3c1e6d25ad4a47d`；补充报告SHA256为 `1c22916038bc6d788c8f321f3c9c2fdca3803a0b9f9cdede2ccaa645c16773ba`。

暂不合并产品：当前主树只有 `source/static`，尚无 `source/usense`。单独应用R3补丁缺少其被修改的parser；整分支合并会同时带入未接受的browser/session/collector与真实坐标代码。不能用PNG修复的有限接受覆盖那些范围。后续集成须有明确的离线子集及其依赖检查，或完成原A04范围后再合并；此处只归档验收材料，不记INTEGRATED。

真实R01～R06、当前14/15/173原图/翻页/目录题框/坐标/会话释放与S01仍未通过。没有服务或输入变化证据，本轮不重试旧GET；恢复真实验证时另给具体有界范围和当次独占检查。A04不阻塞A/B接口包的离线试接；I01仍等A03功能验收，B确认、模型费用和内容质量未解决。

本轮无平台、浏览器、profile、凭据、OCR或模型动作，无推送或B消息。文档和证据的本地归档不等于产品集成或向搭档发布。
