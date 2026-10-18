# A07-F01 调度有限接受：四选项恢复 W

2026-10-18。依据用户[一次差量纠正授权](../approvals/A07-F01-role-correction-approval.json)、[固定范围](A07-F01-role-correction.md)及[独立报告](A07-F01-review-report.md)，调度结论 **ACCEPTED：关闭 A07-F01，限固定 Q1 的 A 本地离线角色纠正**。原始六框正确，已将四普通选项 Q 修为 W；新实际序列为 `Q/W/W/W/W/A`。旧错误证据与此前漏检事实保留，不能回写旧回执为正确。

## 固定交付与复核

- 运行产品 `3d22524ff626fc7b0376b7312be6fe75f2e73aab`；作者交付 `6f8f1d6fa4c8db9678738673a54fa862df9a666e`。
- 独立交付 `71bf89251a3225a7e0defe5fc6feb84d0628dd85`；报告 raw SHA256 `f9bf28710f0e7e44ffb946b7e31359fb932be15b72b79937e6d5844bf4e8572f`；独立清单 raw SHA256 `061e29a1be1cf54c25ca5dbd140b1602459aea0774a1867f1f87b39e36e9f2dd`。
- [独立交付原字节核对](../evidence/coordinator/a07-f01-20261018/review-preflight-explicit-manifest.json)：55成员/10,178,441bytes、全部新报告/证据覆盖，候选29,437条路径完整保全。作者58成员/10,200,306bytes亦核对。
- 两处产品变更仅 `reader.py` 的 option→W 和 `q1_offline.py` 的 ordinary_choice/实际六角色前置门。两个新增窄检查文件、七条冻结前授权/门检查和新报告/证据均在白名单。所有其他工作流旧路径、原业务批准、配置政策、合同、A03 pins/A06/I01 与旧证据 mode/type/blob 保持。
- [调度对独立归档的只读复算](../evidence/coordinator/a07-f01-20261018/review-recorded-delta.json)重新验证C01完整资源/摘要/引用和计划准入，比较旧独立读回及新实际frame/projection/计划；四选项索引1–4的角色变化，其余六框内容、原图、坐标、身份、顺序不变。14个归档输入JSON与旧输入raw完全相同，原图身份与数据通过C01资源验证。
- PRE_APPLY实际五项、TARGET四项通过；正确W门通过，合法重封旧Q仍通过C01但在PRE_APPLY角色门FAIL/HOLD、阻断PLAN/APPLY，两门均零目标变更。独立期望直接来自原书面规则，不能只证明与计划自洽。
- 作者与独立新目标实例不同，固定业务效果相同；[释放与核对记录](../evidence/coordinator/a07-f01-20261018/release-and-scope-notes.json)确认七个登记PID均未运行、两对话completed/idle。候选HEAD守卫保持。

独立新回执 `a07-receipt-a07-f01-review-1` revision1，摘要 `6eef5b12bbc20b61f3d1cbb37f28fce4f184e6c72416c5edcf50f4d0e9b2325f`，APPLIED/MATCH；新读回raw SHA256 `5c1b51f0c5fd01c65876fe9904f08664f0598887a4614f4411b9e8619d7d0cd0`。六框题干Q、四选项W、答案A，无解析、无辅助额外框。

## 消耗与范围

作者和独立**各本轮1次正常尝试/1目标/1dispatch/1成功**，各正确/错误角色门一次（零写入），各原CLI附带一次重放拒绝（零新增变更）。各自历史一次正常尝试/成功保留，累计各2次，旧独立10拒绝亦保留。调度只核对固定Git/归档，**0次新增正常业务**。本次授权额度已用完，不自动追加试验。

调度第一次作者范围检查误漏冻结前证据，独立清单自动发现时同时发现原B内嵌清单；两次诊断保留并分别用任务已授权确切路径及显式交付清单纠正。这些都是静态预检路径选择问题，未更改产品或重跑业务。

本结论不扩大到 shared_material 等未触发题型，也不等于B共同验收或平台通过。源仍OBSERVED、目标/计划/回执SYNTHETIC/SIMULATED，A_INTERNAL_PROPOSAL/PROPOSAL_ONLY、NOT_SUBMITTED/PENDING保持。B原件/HOLD、原Check/账本保持；不推送、不联系B、不连接平台，A04真实阻断保持。接受后执行范围明确的本地集成，结果另记。
