# A03-R1：等价内部替代实现

2026-10-18。用户已明确批准“开始执行”：保留 A03 全部既定功能，替换复杂的校验与恢复编排。此任务是实施授权，直接交可运行候选；不新增设计先行审批阶段，不按 helper 拆单。它替代 T3 下一轮补丁派发以及旧任务的窄文件白名单、45/90秒外层限制，原业务标准和内部安全期限继续适用。

## 1. 基线、隔离与交付

- 固定起点：`d5f777590e72eb070af0497afdb144d60c61b95d`，其中产品候选为 `b8c75119c556b61e36b0cc1f817dbc53044cce41`。基线仍 REWORK，不是已接受产品。
- 工作目录、执行/独立验收对话和 cursor 以 `D:/1800/docs/coordination-state.json` 的 `A03-R1` 为准。仅在登记的独立分支/工作目录写产品，不修改 D:/1800 主目录产品或 T3 目录。
- 先读主目录最新 AGENTS.md、coordination.md、development-plan.md、本任务及独立验收任务，再读固定起点中的架构/公共合同、T3余量矩阵和集成计划。工作树里的旧派发规则不能覆盖本次用户授权。
- T3 执行已冻结并释放，禁止再向它续派产品；正在进行的旧 T3 验收只做固定失败交付的只读收口，不阻塞本实现。原 A03 两个退役对话保持退役。
- 交付 `docs/tasks/A03-R1-execution-report.md`，必要的新设计说明可并入该报告；新证据仅 `docs/evidence/A03/R1/execution/`。提供确切实现/最终提交、最短复现命令、实际导入和进程退出、范围映射及限制，冻结并释放后只交 REVIEW/REWORK。调度才决定 ACCEPTED/INTEGRATED。

## 2. 要替换的内部结构

保留现有 SQLite 账本、delivery 接口和公共产物合同。统一私有验证入口，减少反复 bundle/bridge 重建、JSON复制、schema构造、资源解析和递归完整校验；以明确的命令/状态转换组织接纳计划、intent落盘、permit、目标调用、真实读回、结果提交、恢复和报告。

纯计算可以在受控、实际验证的稳定输入上复用；实际资源 bytes、实现 pins、root、registry、逐消费者引用声明与依赖变动仍须被发现。增量校验或跨调用复用必须有实际依赖身份/变化检测和对应拒绝验证，不能用 caller 的“已验证”、只读标签、全局 PASS 缓存或 skip 开关代替。外部入口仍进行其所需验证。实现者可选择足以达到本目标的最小内部结构，不强迫重写未受影响模块。

实时资格与纯计算分开：owner/generation/fence、head/pending/hold、目标 currentness、permit、能力/授权/政策/期限等仍在实际 gate/事务/效果边界检查，不因提前校验而省略。长事务不能替代新鲜目标观察，也不能把独立目标效果与运行回执塞进同一 SQLite 事务。

## 3. 一次开放的实现范围

- `src/annotation/runtime/storage/`、`src/annotation/runtime/recovery/`：A03 内部实现及必要私有辅助模块；保留对外行为、现有账本语义与恢复数据，不做DB迁移或另起服务。
- `src/annotation/contracts/a03_native/`、`src/annotation/contracts/a03_bridge/` 的 Python 内部验证实现，以及 `src/annotation/contracts/recovery.py` 的 A03 内部接缝。既有公开合同/legacy归档与拒绝语义保持；不得顺便重写 C01。
- 对上述改动同步真实 `profile.json`/`adoption.json`/`readonly-adoption.json` 的 implementation pins，以及必要的私有 `api.json` 绑定。schema、oracle、接口产物语义不放宽，不为了通过测试改预期。
- 现有 `examples/a03/T3-closure/run.py`、`tests/test_a03_t3_closure.py`，可新增 `examples/a03/R1/`、`tests/test_a03_r1*.py`、`tests/fixtures/a03/R1/`，复用已接受 T1 capture，不另建通用取证框架。
- 根依赖、delivery/planner/mock/reconciler、quality/targetcheck、source/geometry、浏览器/B模块、旧样例和证据、调度状态均只读。若确有不可避免的外部接缝，交一个具体反例及精确路径，继续独立部分，不扩张业务合同。

## 4. 功能等价，不能删减

原 `A03-runtime-recovery.md` V01–V10、`A03-independent-review.md` R01–R18 是功能标准；沿用 `A03-T3-remaining-matrix.md` 与 `A03-T3-integration-plan.md` 已接受的有限映射，不创造无限新矩阵。

1. 持久 intent 在外部效果之前提交，实际独立读回支持结果；同动作本地去重，不能宣称平台 exactly-once。
2. UNKNOWN/重启未决先对账，整书后续写入暂停；不同run/scope/新action不得绕过。MATCH不重发，ABSENT也须新检查/新计划，STILL_UNKNOWN保停；另一书隔离。
3. 多动作区分成功、未知和未尝试，不能为未尝试项造intent/permit/dispatch，也不能从无日志推定未生效。
4. 保留写锁、代次、当前账本完整性、错误库/资产/身份拒绝、有限只读恢复次数，以及旧证明失效。
5. 活动hold的只读候选、最终再读/CAS、清除后新INITIAL/PRE/TARGET/plan链完整；清hold证据不能直接变成执行许可。
6. 保留原UNKNOWN历史、解决链、正式receipt/progress/report与完整分母；内容仍PENDING、NOT_SUBMITTED，不把模拟或框一致写成内容/平台通过。

## 5. 一个直接实施和验证包

先实现并形成固定可运行候选，直接完成原 M1–M3 五例：正常三动作/重开去重，UNKNOWN后充分与不足ABSENT两支，重新规划继续与最终漂移保停两支。每个冻结业务候选最多5个M起点/11次dispatch；不增加“为测性能而额外重放”的业务场景。

同一包按原映射完成剩余 L/G 与 F 收口，优先复用确切未受影响证据。新路径实际影响的重启、跨scope/书隔离、旧资格拒绝、资源/pins/身份变化、报告链必须有对应差量验证；不能宣称“原来通过”就自动适用于新实现，也不要求未受影响旧场景整套重跑。报告逐行列明继承、实测、失败/未运行和依据。

允许正常开发和有界修复，不要求每次编辑先经调度许可。本包最多两次冻结业务候选：首个候选若失败，保全精确失败后允许一次针对性纠正和受影响场景复验；第二次仍失败则固定反例、退出并交接，不换名重复直到通过。无需为了用满次数而重跑。相同候选已经成功且未受影响的场景不重复执行；独立负控可继续，不让首例超时掩盖所有静态/拒绝证据。

**超时重新分层。** 旧45秒不是业务SLA。新业务验证初始外层预算为子进程180秒、父240秒：这是较原三动作45秒留出4倍观察空间的防挂死工程预算，不是性能合格线。实现者可在首次正式业务候选冻结前，根据实际工作量一次调整并记录理由，外层子进程绝对上限300秒、父360秒；冻结后不边运行边延长、不为同一候选超时而改数重跑。原内层读回、entry、gate、lease/renew、PRE/currentness和核对次数不延长、不暂停时钟。外层超时记功能证据未完成；实际内层拒绝或语义不符另列。记录关键阶段wall/CPU及完整校验次数，不以“没超时”冒称结构优化有效。

沿用capture，在自有业务和keeper静止的说明边界留存必要双库原件；SQL只读静止副本。保存最小可审证据：输入/固定候选、真实命令/导入、结果、关键边界和实际调用效果计数、自有进程/owner释放、SHA256索引。旧证据按提交引用，不复制或重封旧全集；不因附属封存工具不足再新增业务运行。

## 6. 切换边界

所有运行仅新建、明确SYNTHETIC的离线库。旧T3三个失败起点及其pending/paused现场永久保留，不打开恢复、不清锁、不迁移。当前仍fresh-native-only、LEGACY_INITIAL_ONLY；旧无intent UNKNOWN不获得新资格。

不联网、不接触平台/profile/凭据、付费模型/OCR/视频，不推送，不向B发消息，不重放A05题22。此任务不包含I01或真实平台验收；实现/独立验收/调度接受与集成后才释放后继。执行阶段无需用户再批准常规内部实现选择。
