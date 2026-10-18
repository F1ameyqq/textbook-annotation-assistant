# A07 第1题离线交接：选项角色修复后

2026-10-18。本次交接包含修复后的源码、固定输入政策、作者与独立验收的原字节证据、调度接受和本地集成记录。**固定第1题的 A 侧离线模拟已完成，四选项已恢复 W；B 共同采用与真实平台验收仍待完成。**

发布分支为 [codex/a07-q1-handoff](https://github.com/F1ameyqq/textbook-annotation-assistant/tree/codex/a07-q1-handoff)，以已发布阶段二 `37089f9e0229da76ae1c45461b7e63929590be56` 为唯一父。源码与记录固定取自本地 `23c9caa57fb3ec602bc3498b02b3819558ab4251`；本分支是选择性源码/证据交接，不是整个本地研发历史的推送。

## 先看这些

- [给 B 的可转发消息](handoff/a07-q1/message-to-b.md)：完成项及仍需双方确认的事项。
- [验收摘要与证据导航](handoff/a07-q1/acceptance-summary.md)：新旧证据、固定身份、有限通过范围。
- [当前独立验收报告](tasks/A07-F01-review-report.md)、[调度接受](tasks/A07-F01-coordinator-acceptance.md)、[本地集成](tasks/A07-F01-local-integration.md)。冻结报告中的“未推送”是报告形成时点；本次发布不改写原文。
- [当前独立模拟回执](evidence/A07/F01/review/normal/run/receipt.json)、[实际读回](evidence/A07/F01/review/normal/run/assets/readback.json)、[完整 C01 信封](evidence/A07/F01/review/normal/run/exchange.json)。
- [发布成员清单](handoff/a07-q1/manifest.json)：路径、来源、Git blob、字节数和 SHA256；[只读核验脚本](handoff/a07-q1/verify_archive.py)。

## 已完成什么

固定来源为 B PR #3 的 `ef6ba4dd083e7fd5378e80123b2b038dd11d7052`，书46007447第一章第1课时第1题，内部题号 `q-e92a499995ca1bbd570a2a09`，选项 A.2/B.3/C.4/D.5，答案 D，无解析。A 另存用户的[单题离线业务核准](approvals/A07-Q1-offline-business-approval.json)，不修改 B 原件中的 HOLD 或业务核准字段。

已完成真实来源→新 C01 信封/摘要→五项 PRE_APPLY→显式模拟 TARGET→单题计划→六框实际内存变更→独立读回/模拟回执。最终六框为**题干 Q、四个选项各 W、答案 A**，数量、内容、原图、坐标、题答身份和顺序保持。修复还增加普通题角色检查，合法重封后的旧 Q/Q/Q/Q/Q/A 在语义门得到 HOLD，不能仅靠计划与读回互相一致获得通过。

F01 本轮作者与独立各使用一次离线差量验证且成功，已释放；原成功记录、旧错误回执及漏检发现全部保留。此次发布只核对原字节、清单、依赖和链接，**没有新增业务尝试、正常 dispatch、平台连接或 B 侧执行**。不扩展到未触发的 shared_material、其他题型、整书、持久化恢复或真实平台。

## 如何读取本发布包

在此分支的 Git 检出目录，仅需 Python 标准库和 Git，即可只读校验归档成员：

```powershell
python docs/handoff/a07-q1/verify_archive.py --ref HEAD
```

该脚本读取 Git 原始对象而非经换行转换的工作副本，不导入产品模块，不生成计划或模拟回执，不执行 B 脚本。它核验的是发布内容的完整性，不能替代已归档的功能验收。

`examples/a07/` 和测试文件以原字节保留为历史实现记录。`stage_inputs.py` 绑定当时本机原件路径和授权提交，`role_delta_check.py` 绑定旧工作流/旧独立提交，`run_once.py` 有实际 HEAD 守卫。**本发布 HEAD 不等于原运行候选 `3d22524ff626fc7b0376b7312be6fe75f2e73aab`**，历史提交不因发布此单父分支自动可达。不要替换 pins、改 expected-candidate、绕过 CLI 或照历史 README 重新运行；本轮作者/独立额度已用完。本次不新增 wheel 安装或跨机器业务复现结论。

已发布公共依赖和根依赖保持原字节，新增 A07 六个源码文件及其配套。原 B ZIP 不重复打包；归档信封所需的固定原图和输入 JSON 随证据保留，保留原生引用及摘要。没有凭据、profile、原始视频、活库或未决数据库。

## 还需确认什么

B 仍需确认是否共同采用本次固定版本/摘要、题答关系和 Q/W/W/W/W/A 映射，以及只针对本题的文本规范、六区域及30项范围排除口径；并确认能读取新 C01/模拟回执、引用绑定和历史 E0.1 的使用解释。可返回明确同意或具体字段/证据差异，不需要再次提供同一样例或 E0.1。

来源保持 OBSERVED，目标/计划/回执保持 SYNTHETIC/SIMULATED，政策 A_INTERNAL_PROPOSAL/PROPOSAL_ONLY，状态 NOT_SUBMITTED/PENDING。用户业务核准不等于 B 共同确认或人工视觉验收。B 原包、HOLD、旧 Check、生产题答关系和未归属账本不改；A06 旧回执不改。A04 真实平台仍 BLOCKED；**本次不连接平台、不送审**。A 未向 B 发消息，由用户转发。
