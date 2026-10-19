# A08 新批次只读接收执行

2026-10-19。用户已授权本任务及新的执行/独立验收对话，见[授权原文](../approvals/A08-readonly-reception-approval.json)。直接实施可运行接收器；不设置额外设计先行评审。

## 固定输入与版本

- 产品起点：A已发布 `e37606d74d7e538052c563d02df11c6c961b742f`，包含已修复A07。调度主线现有源码应与该起点相应路径一致；本任务只新增路径，旧证据/源码/pins/公共合同/根依赖不改。
- 最新任务工作流提交、执行工作目录/分支、对话ID和cursor以主线 `docs/coordination-state.json` 的A08为准；独立工作目录由调度建立。管理工具不能切换主线或复用旧冻结活源。
- B固定提交 `a76e5a925fec76f20818dfdefa4145aa132ec8a8`。输入 `handoffs/b/46007447/B-46007447-Q4-Q9-Q16-next-batch-HOLD-2026-10-19.zip`，SHA256 `b646fad9008e03e79a3dddfb4ead912d7ceadefbcee331c2e2af2415abf6f673`，1,440,149 bytes。调度提供的本地原件及详细绑定见 [输入登记](A08-inputs.json)。只从固定Git raw blob导出，不运行包内代码。
- ZIP顶层清单schema `b-complex-batch-evidence-package/0.1`，含23成员；内层 `staging/batch.json` 为 `ComplexCaseBatchProposal` / `b-complex-batch-proposal/0.1`，内层manifest含9成员。
- **包中没有G0.8/Check0.8/plan0.3完整原件**，只有案例快照、固定引用与声明。本次不取得/遍历Q15原包、不重建B流水线；保留 `DECLARED_ONLY/EXTERNAL_NOT_LOADED` 等明确状态。不得把本任务记成通用G0.8/Check0.8消费者通过。

## 实现及交付范围

1. 新增可导入 `annotation.source.b_batch` 和命令行 `python -m annotation.source.b_batch`。具体参数可合理设计，必须支持输入ZIP、优先案例 `q4-first-lesson` 和JSON报告输出；明确支持矩阵、错误码、调用示例。报告是A本次只读接收诊断，不冒充C01执行准入或业务回执。
2. 核对包/成员摘要、清单覆盖、大小、路径边界、内外层批次/案例一致性、原图SHA和尺寸；拒绝未支持schema/kind。完整读取资源用既有可用依赖，不安装依赖。包内工具、DeepSeek记录和历史测试只作为数据，不执行、不借用其结果作A验收。
3. 产出四案例分离结果及实际观察的原值/引用。第一课时Q4优先展示稳定题答身份、章节/课时、题干原文/片段、答案候选13与 `4.13` 来源跨度、每图/区域坐标、候选关系及阻断项。保留 `UNVERIFIED`、`FIGURE_EXTENT_UNVERIFIED`、内容/区域/逐题政策未核准，不能自行修OCR或确认13正确；`selected_answer_id`只标为B来源中的候选声明，不新建A的SELECTED关系。
4. Q4小专题、Q9、Q16返回 `ANSWER_EVIDENCE_ONLY/HOLD`，题ID/题快照保持null。保留Q9跨页顺序与未解决状态、Q16 11个结构化LaTeX runs/原片段、Q4裁边前后记录；只保留和检查输入结构，不新增公式解析/裁边/题型框策略或业务评判。
5. `viewer-173`为resource index172、1148×1621；`resource-173`是另一图1145×1620，viewer页码null。不得别名合并或推算页号。真实来源只读保留，接收成功不消除任何案例HOLD。
6. 新接收实现不接受Q1授权转移；不导入delivery/runtime执行路径、不创建目标/计划/新C01执行对象/模拟回执、不启SQLite/浏览器/平台。输出只读报告到本任务新目录是允许的。原输入、旧源码、Q1授权及全部旧证据字节保持。
7. 对B N01–N08输出范围矩阵：本次只实现固定stage包的显式只读路由、案例/来源/缺口诊断及有限拒绝；完整G/Check/计划原件接收、内容/公式/图形政策核准、新PRE_APPLY/TARGET/模拟等保留PENDING，不用宽泛SUPPORTED掩盖范围。

实现注意：batch没有payload包装；案例没有独立schema字段。Q4答案0个render_regions不能因此拒收。Q9的source_fragment_order只列10个文字片段，余23项为图像覆盖，不强求该数组等于33项全部原片段；latex_runs=0也不等于没有数学内容。保留已有完整片段及覆盖，按实际结构判断。

## 最多八组有限验收场景

| ID | 实际验证的边界 |
|---|---|
| R0 | 原固定包公共入口，4案例/3资产，优先Q4；结果1题答候选+3答案证据，全部HOLD；外部图谱/检查声明与已读取对象区分 |
| R1 | 未知batch schema/kind被实际版本门拒绝，保留具体层/字段 |
| R2 | 坏资源或清单成员摘要不一致，明确输入完整性拒绝 |
| R3 | 同号跨章节/课时替换Q4题答身份或关系，不能被当作优先Q4 |
| R4 | 给原无题ID案例伪造题/关系，不准转成完整题答案例或执行资格 |
| R5 | 混淆viewer-173/resource-173、覆盖未知viewer映射，拒绝或明确身份冲突 |
| R6 | Q9续接区或Q16 LaTeX run被删除的各一个固定变体，定位实际快照绑定/结构缺失，不能静默缩短来源 |
| R7 | Q1审批/30项排除或外加已批准标记不能提升新批资格；所有输出仍无计划/目标/派发 |

负例可在新临时副本中重新封装非破坏的外层清单，使版本/身份/结构检查真正可达；不得修改原输入或生产pins。区分整包hash、快照绑定与语义门：如果实际只到绑定门，就如实报告该门，不能声称后层已测；实现应含显式schema和case身份/HOLD检查。可用纯函数窄单元核对支撑公共入口证据，但不能仅全部依赖同一个外ZIP hash拒绝就声称R1/R3等语义通过。不添加无限随机/组合矩阵，安全解析常规实现不需要逐helper派单。

作者最多两次冻结实现候选；每候选一次原包完整接收加上述有限差量，保留首次失败，独立仅对固定候选复验。只读接收/单元检查不计为旧A07正常业务额度，也不恢复任何业务额度。本轮计划/模拟/平台次数必须一直为0。第二冻结仍失败则固定收口并交调度，不改名追加。

## 文件白名单与报告

只新增 `src/annotation/source/b_batch/`、`tests/test_a08_*.py`、`tests/fixtures/a08/`、`examples/a08/`、`docs/a08-batch-readonly-reception.md`、`docs/tasks/A08-execution-report.md`、`docs/evidence/A08/execution/`。任务单和批准记录由调度维护，作者不修改主线coordination-state。根依赖、旧源码/合同/pins以及B原件不改；确有公共代码阻断则提供固定反例给调度，不私自绕过。

交付确切产品与最终提交、可复现命令/退出码、输入/产品raw Git摘要、固定场景结果、逐例HOLD和范围矩阵、原件不变证明、进程/资源释放。报告显式区别接收结构符合与内容未核准。独立报告未完成前作者状态只能FIXED_DELIVERY/REVIEW_READY；主调度核证后才ACCEPTED，范围集成后才INTEGRATED。未授权推送或向B发送消息。

使用 `core.longpaths=true`、`GIT_NO_LAZY_FETCH=1` 和raw Git bytes；换行转换不改变绑定依据。仅使用既有本地依赖，不联网补件、调用付费模型或读取凭据。旧A07/A06/A03/I01不重开、不复跑。
