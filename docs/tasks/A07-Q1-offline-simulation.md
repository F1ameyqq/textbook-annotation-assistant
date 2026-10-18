# A07：已核准第1题的真实来源到离线模拟

2026-10-18，执行任务。产品基线 `2e71462dda8d225e4f41e8c6cd03a9ce7b88046a`；实际工作目录、工作流提交和对话 ID 以 [调度状态](../coordination-state.json) 为准。直接交付可运行实现，不增加设计先行评审。独立标准见 [A07 独立验收](A07-Q1-independent-review.md)。

## 授权与目标

用户明确回复“核准上述内容与范围，仅用于离线模拟”。[独立业务授权记录](../approvals/A07-Q1-offline-business-approval.json)绑定固定候选、题答内容、六组区域和30条单题排除政策。此前 [六项技术确认](../b-q1-a-side-confirmation-2026-10-18.md)继续作为来源证据。

只实现书 `46007447`、题 `q-e92a499995ca1bbd570a2a09`、答案 `a-b22c88c763b7dfb917d02d18` 的 A 侧离线闭环：固定 B 原件和旁文件 → 新 C01 Source/Evidence/Graph → 实算五项 PRE_APPLY → 显式模拟 TARGET → 新计划 → 一题六框内存目标变更 → 独立读回及模拟回执。不连接平台、不碰题22。不要求 B 再补已经收到的样例或 E0.1。

这是 A 用户核准后的 A 本地离线试验，未证明 B 采用共同合同、联合接受或独立人工视觉复核。B 原文件的 HOLD、human_verified=false、business_acceptance=false 和原问题账本保持；新的 A 授权单独引用，不能改写这些历史事实。只有本任务技术门实际满足才产生 READY/PASS；不得手填预期成功。

## 固定输入

- B PR #3 提交：`ef6ba4dd083e7fd5378e80123b2b038dd11d7052`。
- 原包：`D:/1800/.local/stages/coordinator/b-handoff-0e5434f/B-46007447-Q16-offline-HOLD-2026-10-17.zip`，SHA256 `b2bed674f87cde7fb2df4fdf31dec9ede08f494fc6190f654abda51dd4dae89d`。
- 新包：`D:/1800/.local/stages/coordinator/b-q1-ef6ba4dd/handoffs/b/46007447/B-46007447-Q1-source-candidate-v1-HOLD-2026-10-18.zip`，SHA256 `3039645ca69c2604f542c479cb180049604788a3ca28ffac1b5063dee533afac`。
- candidate.json SHA256 `0ce9ffb0f468ba0cc07f37978121e7f9b991b07b94335d117da3e8ea241aea5c`；候选 ID `b-q1-source-review-08f4a1948c7f26003795e797` / revision 1 / payload SHA256 `08f4a1948c7f26003795e797acd7d2d9069f4b2ddde77d2968a05945f249df30`。
- 新包 manifest SHA256 `240622443df3c1f31cf76dc490fb7b2cedb9cecb09f47f086909cbe9e9fbd345`；scope proposal SHA256 `289269e3e2ea3961d565c49f9078a5e273fe2517356832bcbdc3fe8636fc3019`。
- 已取回历史材料在 `D:/1800/.local/stages/coordinator/b-q1-ef6ba4dd/handoffs/b/46007447/single-question-q1/`；E0.1 原件 SHA256 `a763af50c0515f863eeb6dbaf533f4215535591096dd06b81632cec4acbb4493`。原件与必要性已核对，直接消费冻结快照不重建历史生产链。
- 新授权记录以本工作流 Git blob 原字节 SHA256 固定；实现核对精确授权摘要和包绑定，不能仅信任调用方传入的布尔值。

上述路径只读。允许将需要的原字节复制到自己的隔离输入目录并记录清单；不执行 ZIP 附带脚本、B 生产者或 SQLite，不读取凭据/profile，不网络补件。所有命令使用现成环境；`GIT_NO_LAZY_FETCH=1`、`git -c core.longpaths=true`。原件与旧证据不修改。

## 最小实现边界

只新增 `src/annotation/source/b_q1/`、`src/annotation/quality/q1_offline.py`、`src/annotation/delivery/q1_offline/`、`config/policies/a07-q1-offline-v1.json`、`examples/a07/`、`tests/test_a07_*.py`、`tests/fixtures/a07/` 和本任务报告/证据。按需要选择这些路径，不为目录齐全创建空模块。不得修改既有 src 文件、公共合同/schema/pins、根依赖、旧 examples 或旧验收记录。调度文件由主调度写。

旧 `quality/targetcheck/__init__.py` 属于 A03 固定源码清单，不能为支持真实输入直接改它。旧 `MockSession.execute` 会重新进入旧 synthetic-only 门，不能强行复用、调用私有 `_write` 或 monkeypatch。新增明确命名的 Q1 离线入口和小型内存目标，复用既有 C01 `validate_bundle` / `seal_artifact` / `assert_plan_ready`、纯坐标投影与效果比较函数。可使用公开 `apply_synthetic_action` 对调用方内存状态变更；不得实例化持久化 runtime、打开旧库或迁移 A03。执行前复算新入口自己的计划/目标/授权绑定，而非仅检查格式。

新入口仅处理固定批准输入；不是通用 B 版本升级，不扩展 A06 支持矩阵。实现若在这些范围内确有不可消解的合同冲突，应固定最小反例交接调度，不擅改公共合同或另造通过标志。

## 有限功能与验收事实

1. 来源与业务授权：核对原包/新包/清单/候选/原图资源及授权绑定；新旁文件保持 `QuestionSourceReviewCandidate / b-question-source-review-trial/0.1` 身份。原 B 三元引用、raw 文件摘要、原编号换行视图与新 C01 对象之间有可追溯映射。C01 用新的有效 ID/scope/完整信封摘要，不把 B payload hash 当 C01 hash。
2. 内容与区域：正文去编号，按授权保留括号及规范化空格；A.2/B.3/C.4/D.5，D 答案，无解析。严格采用候选六个 `proposed_semantic_region_ids`，不是七个 `context_only=false`；括号嵌在题干，辅助裁片不成框。原图尺寸、SHA、坐标保持真实，六组各有明确映射。框模拟不等于真实平台文本呈现通过。
3. 单题政策与覆盖：原31项/78依据、19未归属账本与原 Check 保留引用。新政策逐项绑定30条排除依据，只限本题；BUSINESS_REVIEW_REQUIRED 由新 A 授权在本次政策下处置，不删除原问题。新单题 coverage 不继承整页/整章通过，不能把上下文裁片变成待交付孤立区域。所有必需且未解决问题仍阻断。
4. 新 C01 来源、证据、图谱及真实来源 PRE_APPLY 使用 OBSERVED，原图资源真实可验。模拟目标、TARGET、计划及回执标记 SYNTHETIC / SIMULATED；不得把真实题或图重新标为 synthetic。使用现有 `A_INTERNAL_PROPOSAL / PROPOSAL_ONLY` 政策枚举并引用 A 用户授权，不能冒称 JOINT_CONFIRMED；平台执行仍拒绝。
5. PRE_APPLY 五项 source_integrity、structure、answer_matching、coverage、policy 由实际输入计算。TARGET 明确固定 mock target/scope/book/directory、当前 snapshot、CREATE_FRAMES 能力和本次离线授权。新执行器在写前重新验证授权/目标当前性/计划内容；不依赖任意手工 PASS；C01 `assert_plan_ready` 通过。
6. 一个正常闭环：全新模拟目标，一道真实来源题形成一个计划和六框效果；执行器真实改变内存目标，读回从目标状态独立取得，不能把计划复制成读回。生成带来源/授权/目标/写前/写后证据的 C01 模拟回执，显示实际结果；不得升级为平台、全书、B 联合业务或持久化恢复通过。回执保留未提交状态。
7. 有限拒绝检查：缺少/伪造授权；候选或其关联输入已换而仍沿用本授权（在可验证的封装层之后验证授权绑定）；平台模式/错误目标或越出已准范围；已执行计划重放。拒绝须零新目标变更，指明到达哪层。窄单元检查可覆盖这些分支，不扩张为旧 A03/A06/I01 矩阵或泛化攻击矩阵。

## 运行与交付额度

先完成实现与上述窄单元检查，再冻结业务候选提交。每候选只进行一个正常完整离线试验；执行侧累计最多两次冻结实现、两次完整试验（用于一次有界修正），最多一次成功闭环，不为多次跑成功证据另造候选。拒绝调用不计成功业务，但记录调用及零写入。外层单次试验180秒、整进程回收240秒是看门狗，不是业务SLA；不更改既有内部安全规则。异常/UNKNOWN 保留失败和现场、停止该目标，不能重发解锁。第二冻结失败后固定交接，无第三轮自动额度。独立侧额度和阶段见验收单。

交付 `docs/tasks/A07-Q1-execution-report.md`、`docs/evidence/A07/execution/`、可复现 CLI/固定样例、产品候选和最终提交、raw Git bytes 成员清单、确切输入/授权摘要、每项结果/限制/消耗、所有自有进程退出证明。长期运行服务与浏览器应为零；不能用 Python/测试数代替业务回执和独立读回。退出后不继续改浮动代码，状态仅 READY_FOR_REVIEW；主调度核验后才派独立验收。

不推送、不评论 PR、不向 B 发消息、不操作平台、不调用付费模型。旧 A03/A06/I01 已收口，不能重开或借名重跑。A04 真实平台、B 共同采用、发布共享仍是其他边界。
