# A09：已核准第4题的图文混排离线模拟

2026-10-19。产品基线 `846662f4aab08a75d6ad0482edeced4550e1a1ab`。用户对固定核准页回复“确认”，新授权见 [A09业务核准](../approvals/A09-Q4-offline-business-approval.json)，摘要 `5c73af50262f6bd7e48e2b0d46148026c1c3a953d1ee93c8262e356733d99010`。输入见 [A09-inputs](A09-inputs.json)，独立标准见 [独立验收](A09-Q4-independent-review.md)。实际工作流、目录、对话和cursor由调度JSON登记。

## 本次目标与准入

只处理书46007447第一章第1课时第4题 `q-260d10c51f2b7c16fb6fefb5` 与答案 `a-92c4d2164ab878c8e6d4c88d`。直接交付可运行入口：固定B stage包和A核准页/授权 → 新C01 Source/Evidence/Graph → 实算五项PRE_APPLY → 显式模拟TARGET → 一题四框计划 → 真实内存变更 → 独立读回 → SIMULATED回执。不是设计先行或逐helper派单。

新授权只允许本题A侧离线模拟。原proposal的false批准字段、B HOLD/UNVERIFIED/FIGURE_EXTENT_UNVERIFIED、原账本与A08历史记录全部保留。用新的A授权明确处置本次内容/几何/关系/单题政策阻断，不回写B的事实。用户业务核准不等于B共同采用或独立人工视觉证明。完整G0.8/Check0.8/plan0.3未加载，直接使用已接收stage快照与固定原图建立新对象，不冒称取得原完整图谱或重建B历史。

## 已核准且必须精确比较的结果

一个逻辑题，物理顺序为题页自上而下，然后答案页，恰好四框：

| 序号 | 角色/内容类型 | 原图及半开坐标 | 内容 |
|---|---|---|---|
| 1 | Q / image | viewer-10 [334,975,581,1077] | 完整几何图，含A/B/C/D、直角和BD线 |
| 2 | Q / text | viewer-10 [100,1118,592,1193] | 题干前两行，去印刷4.，合并排版换行 |
| 3 | Q / text | viewer-10 [99,1202,220,1235] | 填空线及cm，避免第5题图；____仅表示实际空线 |
| 4 | A / text | viewer-173 [324,239,342,257] | 13，不含4.及相邻答案 |

正文：如图，在△ABC中，AB⊥AC，BD是边AC上的中线，AB=5 cm，AD=6 cm，则BC的长是____ cm.

无W、无E，不把辅助数学核对生成原书解析。印刷题号和“第4题图”只为定位证据，不进框；这是一题特定政策，不推广到所有混排题。不能套用Q1六框、选项、30条排除或其授权。其他三个案例保持HOLD、无题关系、无执行。来源图viewer-173/resource-173不可混同；本题使用viewer-173（resource index172）。两原图SHA/尺寸及新四框必须绑定，不把原4题片段+1答案区当执行框数。

C01既有题型没有fill_blank，明确映射为free_response，并在来源说明中保留proposal原fill_blank。三个stem片段全部同题，题干只在viewer-10，cross_page=false；答案在viewer-173不把题干误记为跨页。image框的类型需核对内存frame_projections实际读回（基础目标frame只有角色/坐标），不能用计划替代读回，也不因此声称平台图片控件或OCR已验。

## 实现白名单

只新增 `src/annotation/source/b_q4/`、`src/annotation/quality/q4_offline.py`、`src/annotation/delivery/q4_offline/`、`config/policies/a09-q4-offline-v1.json`、`tests/test_a09_*.py`、`tests/fixtures/a09/`、`examples/a09/`、`docs/a09-q4-offline-simulation.md`、`docs/tasks/A09-Q4-execution-report.md`、`docs/evidence/A09/execution/`。无需为了目录齐全制造空文件。主调度管理任务/授权/inputs/coordination，不由执行者改。

既有src（含A07/F01、A08）、合同/schema/pins、根依赖和全部历史证据原Git bytes保持。可以参考Q1实现结构，但不要调用其绑定Q1身份/六框/旧授权的准备与执行入口。复用C01公开validate_bundle/seal_artifact/seal_policy/assert_plan_ready、纯projection_frames/action_facts/compare_action_effect、公开apply_synthetic_action；新建Q4自身内存目标和准入编排。不得调用旧MockSession.execute进入synthetic-only路径，不monkeypatch或调用私有_write，不实例化持久化runtime、不打开旧数据库。若现有公共合同无法表达已批准输入，在范围内交最小静态反例，不擅自改合同或伪造PASS。

固定包/授权/候选/原图/原始B case及A08输入清单只读。新入口可在一次A09试验内部读取验证所需固定原字节，不重跑A08接收CLI/R0-R7，不加载外部G/Check/plan、不执行B脚本/SQLite/生产者、不联网补件或装依赖。保存原始case快照、旧OCR框与新A区域映射，并绑定A授权；原图不重编码。Q:image应使用C01支持的image内容类型，真实OBSERVED，不用伪造OCR文本代表几何图。

## 有限验收边界

1. 来源/权限：验证ZIP、清单、所需成员、原图尺寸/SHA、proposal raw SHA、授权raw SHA和单题身份；授权必须与冻结任务输入一致，不能信任调用方布尔值。新A授权单独引用，保留B原引用/缺少完整外部对象的事实。
2. 内容/角色/范围：新证据、图谱、计划、实际框、读回与批准表逐字段比较，角色Q/Q/Q/A、image/text/text/text、精确坐标/图像/顺序/内容、一个题答关系；不只比较计划与自身读回。将旧B图形未核准和内容标记与本次授权处置并列记录；其余三案例不晋级。
3. 质量：五项source_integrity/structure/answer_matching/coverage/policy均由输入计算，角色/内容类型/边界门不能漏掉。coverage只证明本固定单题批准图文完备，不声称整页/新批/公式/复杂题型覆盖。没有从缺失G/Check借用PASS。真实Source/Evidence/Graph/PRE_APPLY保留OBSERVED；政策A_INTERNAL_PROPOSAL/PROPOSAL_ONLY，不虚构JOINT_CONFIRMED。
4. 目标/计划：固定book/scope/directory/target/current snapshot/CREATE_FRAMES能力和新A授权，TARGET及目标/计划SYNTHETIC；执行模式SIMULATED，C01 assert_plan_ready实际通过。写前在目标锁内复算授权、来源、准入、当前目标和计划，拒绝替换输入或陈旧目标。
5. 正常一次：fresh memory target实际新增一个题、四框。读回从真实内存状态独立取得，无plan参数替代观测；保存完整写前/写后/比较证据和新C01回执，零差异、NOT_SUBMITTED/PENDING、不连接平台。运行身份冻结，不用最终交付/集成HEAD冒充实际运行候选。
6. 有限拒绝：缺授权、改授权、误用Q1授权；替换本次输入/proposal；合法重封错角色或image/text类型的一个固定反例；平台模式；错目标；陈旧目标；同计划重放。仅这些有界组，记录实际命中层、拒绝次数和零新增变更。可用纯函数窄检查证明原摘要门后语义门，合法重封不要修改生产pins，不以同一个ZIP外hash拒绝冒充所有语义检查。内容/坐标/题答身份正例需精确比对；无需新增任意题型或随机安全矩阵。

## 冻结、消耗和交付

先完成代码和本次窄静态/单元检查，再冻结产品与驱动。执行侧最多2冻结实现候选，每候选最多1正常完整试验，累计最多2次尝试、1次成功；首失败保留现场，只允许一次有界修正，第二失败固定交接。成功不重复跑补证；拒绝单独记录且零新增变更。新额度只属于A09，不恢复A07/A08。单次180秒/进程回收240秒外层看门狗，原内层规则不放宽；UNKNOWN或超时保留停止，不重发解锁。

每侧使用自己的隔离目录/输入副本/输出/目标。进程不长期存活、不启浏览器/服务；收口保存自有PID+创建/结束时间/退出码，按实际子进程结束比对防PID复用误判，不终止无关进程。交付固定产品及最终提交、可复现命令、raw Git成员清单、输入授权原字节摘要、有限结果/消耗/限制、旧字节保全、自有进程释放。初轮失败以后另存差量，旧包不覆盖。固定提交并释放后作者状态READY_FOR_REVIEW，主调度预检后才续派独立；未经独立+调度不声明ACCEPTED/INTEGRATED。

不推送、不发B消息、不评论PR、不连接平台、不操作题22、不调用付费模型、不读凭据。当前用户核准已经足够，不重复询问内容/坐标/政策。
