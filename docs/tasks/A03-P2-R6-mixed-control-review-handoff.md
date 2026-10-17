# A03 P2-R6：单一混合环控制独立复核

2026-10-17。继续原独立验收对话 `01a145aa-8d59-7c70-8d81-731712103a9a`，保留用户当前设置，不设置 thinking/model、不委派。只复核下列冻结交付，不更改执行工作树或输入，不扩张原验收标准。

| 项目 | 固定值 |
| --- | --- |
| base | `323013c4f0dbae75368e56db60147a8057368d1f` |
| target | `81d3ec7e42e0a1a76ad744bf59536fc5f68adee4` |
| 执行 workflow | `77d3e123ab7247eae6f81f7acd669e3a69c934a0` |
| 执行任务 SHA256 | `97211bd4dd86097ae2ed08c19f38f208c4a790432fe42875bb0d7901fff1f0cd` |
| 执行报告 | `docs/tasks/A03-P2-R6-mixed-control-delivery.md` |
| 执行报告 SHA256 | `efe831c7f11e7251e1f0cb9b78f66b72baa0ae7b9f630d1718bfe3aa9518e400` |
| 执行清单 | `docs/evidence/A03/execution/P2-R6-mixed-control/sha256-manifest.json` |
| 执行清单 SHA256 | `7f8f17697370b0398af58d178bc0af18f6d9cc1e640c73ae7949907ca95ef3e8` |

本次审阅 workflow 由调度消息给出。先按 raw Git 读取本单、[R6 执行范围](A03-P2-R6-mixed-control-rework.md)、[R5 调度决定](A03-P2-R5-registration-context-coordinator-decision.md)、[R5 独立报告](A03-P2-R5-registration-context-review-report.md)和[交付前检](../evidence/coordinator/heartbeat-20261017-1129/A03-R6-delivery-preflight.json)。前检核对了 92 项清单及清单自身共 93 个新增文件、46 项 raw Git pins、28,318 个旧路径 mode/type/blob 与七条自有运行退出记录，没有执行交付代码或作功能接受。

执行对话已 completed，实际 HEAD 为 target、工作树干净。首个驱动启动曾在整文件解析阶段 SyntaxError 退出 1，作者保留该脚本和日志；补空格并 AST 核对后执行唯一一次 Package 调用。需要独立核对这一计数和失败留痕，不把退出 0 当验收证据，也不重跑失败的旧驱动。

## 唯一复核范围

1. 核对执行任务、93 个新增文件与精确 raw Git、46 项输入 pins；旧路径及不变 R5/R3/R2/Schema/oracle 源码保持。原材料只读；只提取本轮必要输入，不复制历史证据全集、旧保全清单或产品代码。保留既有根工作区改动，不修改调度 state。
2. 独立读取候选、原 R5 repair-01、Resource 原字节和实际代码，重算语义差异与数据一致性，不能只运行作者 data_check 或照抄 precheck 的 true 字段。核对第 8 条 initial_event_head、后续事件 hash/previous_hash、accepted/expected head、全部 Artifact 内容摘要、Resource SHA、普通 exact refs 和各 frame/外层声明、book/scope。确认控制唯一语义修正及其传递变化；原混合环、历史与声明保留。
3. 作者声称 prefix 只有 15 处叶字段变化，bundle 仅 evidence[1].resource.sha256 变化，16 个 Artifact、所有 ArtifactRef、return Resource、accepted_anchor 不变。核对后独立给出结果。候选 bundle SHA256 `6a39c873de02dab04d3efd831cb1032b87ba8323c35bfd2a7a31f0b2e48dabd2`，prefix SHA256 `d946006863bac1a8862ba2b3652f0b62e0914c36625541d463c342721e508e5f`，case SHA256 `2763198f4b68b9e636b00780cf5a28b8a89ac0dc117269c43fc6efc731bccab2`。
4. 检查新 driver 仅传入候选并做只读 trace；完整入口 R5 registration.py SHA256 必须为 `3f0281c5cfc9aeec99b11fa2de30ba40e9984a19dd0e651b747d99ebe29772ba`，load_static.py 必须为 `734b8760b58f7778f4bd32608b77fc87f95a31c027ce457408d5fbdcf8166098`。不能修改 loader/校验器/Schema/输入或重定义预期。
5. 数据检查无残余后，在隔离的精确字节输入副本上只运行一次冻结 `examples/a03/P2-R6-mixed-control/entry.py --readonly`。保留真实 stdout/stderr、argv/cwd/PID/限时/退出、输入和源码 SHA；核对 R5/R3/R2 实际调用各一次、R3 entry counter 增量 1、MIXED_DAG 到达层、MIXED_CYCLE 路径、consumer_failures 和五条实际环边。不得运行作者 prepare/precheck/freeze 或非 readonly entry，不重写冻结证据。

本轮只接受或拒绝这个修正后的混合环控制证明。R5 六项 ACCEPTED_STATIC_LIMITED、R4 有限接口设计、既有 R3/SESSION-02/CONVERSION-07 结论保持，不重复执行。若输入仍有独立缺口，给最短定位并冻结为 REWORK；若尚未运行完整入口，明确 NOT_RUN。一次入口后不修包、不重跑、不构造新变体，不自行派生下一轮。

## 输出与边界

只新增 `docs/evidence/A03/review/P2-R6-mixed-control/` 和 `docs/tasks/A03-P2-R6-mixed-control-review-report.md`。输出包含精确输入索引、独立数据差异/核对、代码检查、一次只读入口实际结果、作者原失败与唯一实际调用核查、过程退出与释放证明、完整新文件 SHA 清单（只排除清单自身）。最小输入副本必须匹配 raw Git；旧文件保全用简洁摘要与精确版本，避免重复复制历史全集。报告和清单完成后冻结，停止并向本对话交付路径和 SHA。

不运行或修改产品、SQLite/native/PRE ABI/planner，不访问网络/浏览器/平台/profile/凭据/OCR/模型/付费 API，不安装、推送或联系 B/执行者。A03 恢复功能、R17 实际调用链、原生资格、跨侧采用与 I01 均不在本轮接受范围。字段重置专项保持 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`，不复跑、变形、委派或建议重测。
