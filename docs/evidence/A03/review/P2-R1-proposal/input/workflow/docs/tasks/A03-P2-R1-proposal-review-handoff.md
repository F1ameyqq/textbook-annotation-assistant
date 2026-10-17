# A03 P2-R1：合同补充提案独立审阅

2026-10-17（Asia/Shanghai）。继续原独立验收对话，明确 `xhigh`。本次只审阅冻结的静态提案，**不批准或实施功能，不运行产品、DB 或旧功能场景，I01 不释放**。

## 固定输入

- 执行工作目录：`C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800`。
- base：`c30526958e313141bf64152627591b0907b04aa8`；提案交付：`7fdbde8f16569fd3bc399013115e13269d5d33fa`。
- 执行报告：该交付中的 `docs/tasks/A03-P2-R1-amendment-delivery.md`，SHA256 `0f70c125dbbfa2f4897a43cef9762e9aef6bfcc65d8708ca50d9b11813fc4cf4`。
- 完整清单：`docs/evidence/A03/execution/P2-R1-proposal/sha256-manifest.json`，SHA256 `2eea068aba8b1e678cc8e8984165cd0025ac8a21f6cfdfebc439aeb08d2010ab`。
- 当前候选仅 `examples/a03/P2-R1-proposal/candidate-v2/`；早期草稿保留为历史，不混用 pins。
- 任务依据：[提案任务](A03-P2-R1-amendment-proposal.md)、[P2复验](A03-review-report.md)。[调度预检](../evidence/coordinator/heartbeat-20261017-0619/A03-proposal-delivery-preflight.json)已核对501项清单原字节、27,168个旧Git文件未改、新增范围和工作树干净；执行对话已结束。

从确切 Git 对象隔离读取必要输入，不导入浮动主树或执行者环境。执行的32项静态记录是作者自检；不能称为功能验证或合同批准。自身可以运行已读过的纯静态格式/摘要/引用检查，必要反例仅用全新静态文件，不调用产品、DB、原生会话或旧场景脚本。

## 有界审阅问题

1. 新版本是否保持旧七份 Schema/API/profile 原字节、明确 pins/选择规则和消费者影响；全局事件起点、真实前驱、owner/control/其他计划事件、永久预留与完整账本/CAS 是否有闭合且可实现的语义。新消费者 frame 的跨 scope 边界是否保留逐消费者引用规则；作者承认缺少跨 scope 正例，应明确其阻塞影响，不把同 scope 样例算作覆盖。
2. 专用未尝试路由是否可在没有 intent/permit/dispatch 的情况下产生真实只读事实，同时保留 UNKNOWN 全书暂停。区分候选值、原生权限和实际当前账本。特别审阅第三次读计入总共3次、持久次数/父调用预算、逻辑读 session、lease 和最终 CAS 的边界；不能默认为已获批准的新预算或已验证的竞态防护。
3. 晚到完整 receipt 与原 null receipt、不同行动 snapshot 的新报告模型是否消除旧矛盾而不篡改旧 head。作者样例明确不是原生可接纳全书历史；请检查当前首个 UNKNOWN 即停的状态机与多头正例可达性，给主调度具体可选范围及影响，不自行删除 R17、放宽旧计划重放或扩成跨计划/跨 scope 聚合。
4. 合成 fixture PRE 的 oracle、五项实际检查、原生 run 接纳、清 hold 与第二次变化是否定义充分；不借 A 内部 fixture verifier 冒充 B 算法质量。当前 PRE=HOLD/UNAVAILABLE 和未实现的转换 mapping 应维持其真实状态，检查后续正向验收需要哪些具体输入。
5. 已知全合成初始输入的显式转换、失败/中断/重开、原字节保全是否有可执行验收边界。未知 DB 拒绝不等于迁移已通过；不要求自动迁移任意未知库。
6. 历史失败原件 NOT_RETAINED 及本轮探索性原输出缺失继续如实保留，新的保全计划是否足以避免再次丢失。不要重建旧原件或用新运行改写旧失败。

输出一张“可采纳设计 / 必须补齐或裁定 / 后续功能验收”表。对必须裁定项列精确语义、推荐的最小范围、影响及是否涉及跨侧合同；判断哪些事项阻止下一段有界实现，哪些只是运行证据待补。不要为了消除静态差异扩张任务，也不把所有未运行项目笼统当作设计错误。若有明确阻断，冻结最小证据后结束，避免无边界反复验证。

## 交付与限制

只新增 `docs/tasks/A03-P2-R1-proposal-review-report.md` 和 `docs/evidence/A03/review/P2-R1-proposal/`，保留旧报告与证据。报告写确切候选版本、独立检查、反例、缺口、建议及清单；结论用 `DESIGN_READY_FOR_COORDINATOR_DECISION / REWORK / BLOCKED`，并明确整体 A03 功能仍未接受。主调度随后决定设计采用和下一段实现授权，本报告不能代替 B 确认。

禁止改产品、公共合同、根依赖、调度state或原提案；不提交、集成、推送，不联系执行者/B，不访问网络、浏览器、平台、profile、凭据或模型。已有自动审查拒绝的字段重置专项继续 **NOT_EXECUTED**，不复跑、变形或委派，也不列入下一轮测试请求。临时静态文件只写自己的隔离目录；所有子进程结束并保留退出记录后交付，等待主调度。
