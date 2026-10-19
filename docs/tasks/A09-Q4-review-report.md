# A09 第4题离线模拟独立验收报告

2026-10-19。独立结论：**建议 PASS，仅限本次固定第4题有限离线链**。调度 ACCEPTED、范围 INTEGRATED 均尚未决定。本报告不是 B 联合采用、公共合同冻结、OCR、平台图片控件或真实平台验收。

本侧实际完成1个冻结候选、1次正常尝试、1次成功、1次实际业务 dispatch，以及原10次有限拒绝；拒绝均零新增题/框/dispatch。成功后未再运行模拟、扩大矩阵或修改产品。其余三个案例保持 HOLD。

## 固定身份与独立目录

| 项目 | 固定值 |
|---|---|
| 原执行工作流 | `0a9c634d160ac7b39f68a1fb3555f409dd408f49` |
| 本次独立派发工作流 | `1cb8768000ed1dc2828a469b91fffa30e401d6ad` |
| 实际运行产品、驱动及 ExpectedHead | `29c82b0997be3080f53dfde2afbb1d7457b04197` |
| 作者最终交付、报告目录初始 HEAD | `439423ebf4277e3825aba24fed6f56546ef66a2b` |
| 产品 tree | `240729ac2e07709434df15b5707995ab0cce1f93` |
| 实际运行目录 | `D:/1800-worktrees/a09-q4-review-run`，detached HEAD 固定上述产品 |
| 报告目录 | `D:/1800-worktrees/a09-q4-review`，`codex/a09-q4-review` |
| 独立输入、输出、消费及启动记录 | 运行目录的 `.local/a09-review/`，未使用作者目标、预算或输出作为独立结果 |
| 环境 | Windows、CPython 3.9.13、Pydantic 2.12.5、Pillow 11.3.0，已有依赖，无安装 |

本报告及其证据的最终提交只封存验收材料，不能替代实际运行 HEAD。固定派发、调度预检、检出记录的 raw 副本见[派发文件](../evidence/A09/review/dispatch/A09-Q4-review-dispatch.md)、[调度预检](../evidence/A09/review/dispatch/preflight.json)、[检出记录](../evidence/A09/review/dispatch/review-checkouts.json)。预检只是放行，本侧另行复核和运行。

## 原字节与输入绑定

本侧直接比较固定 Git 树：原工作流29,721条路径在产品及作者最终交付中的 mode/type/blob 全部保持；产品29,737条路径在作者最终交付全部保持。作者新增96路径，清单自身以外95成员共3,350,434 bytes逐项通过，清单 raw SHA256为 `5dae17727efd65e98ef9df94ab34abdc95c6faee1caa6b4bd3fc5156bd9eb541`。本侧未改既有源码、公共合同/schema/pins、根依赖、B原件、历史证据或调度状态。

两处稀疏检出实际存在的1,052份报告目录文件、972份运行目录文件逐个等于冻结 raw Git blob；各自28,765条未物化路径仍在固定 Git 树，不能算作删除。运行清单102成员再次绑定产品，运行后磁盘字节和 HEAD 仍一致。[独立预检](../evidence/A09/review/preflight/result.json)、[报告目录清单](../evidence/A09/review/preflight/a09-q4-review-raw-members.json)、[运行目录清单](../evidence/A09/review/preflight/a09-q4-review-run-raw-members.json)。

| 输入 | raw SHA256 |
|---|---|
| 原 ZIP，1,440,149 bytes | `b646fad9008e03e79a3dddfb4ead912d7ceadefbcee331c2e2af2415abf6f673` |
| 固定 proposal | `e8146fc7a4fe2e16c1fc1194d49de1caa1fe029dd6907848bbaa6c9082dc0bbe` |
| 新 A 用户业务授权 | `5c73af50262f6bd7e48e2b0d46148026c1c3a953d1ee93c8262e356733d99010` |
| A09输入登记 | `aa4f2f7119ef71f70367e3bf7b3c3ed61e05e8a1643572aca92969d05cc1f9bf` |
| A09政策 | `0764136893bc44dae37b884cf52ceffe9756224fb6ddcb417ea9255cc9233f6c` |
| Q1授权，仅用于拒绝 | `cf6f675cfd98d438d7d465fc553e0ebbf1bfff71bd62f8453854f8527015cb6c` |
| B原始本题case | `11aa94a8748b60136aab66eb652682fb7910fc0d3203f9d2b65022b269df8e0c` |

自己的 ZIP 从登记本地原文件只读复制，其他输入取原工作流 raw Git blob。ZIP完整成员清单及各成员bytes/SHA全部核对，不执行包内程序；原case等于proposal保存的快照。两图尺寸与摘要通过：viewer-10为1217×1691、`eb7cc17e6b58a55a005ce1cdef5bd5058ad258c3dd44dc891b3d830ed3db3626`；viewer-173为1148×1621、`a231f0247cd0444cc34ed699c4cca99245d2ac6cfda5ef10a38ca3f8164510be`。保存与输出的JPEG均等于原成员，无重编码；viewer-173为resource index172，没有混同resource-173。[独立输入来源及清单](../evidence/A09/review/preflight/input-raw-manifest.json)、[原ZIP成员核对](../evidence/A09/review/preflight/input-original-members.json)。

原proposal false审批字段、B HOLD/UNVERIFIED/FIGURE_EXTENT_UNVERIFIED、原OCR框/片段和原receipt引用保持；新A授权单独引用。本次未加载完整外部G0.8/Check0.8/plan0.3；其他三例只保留HOLD、无题关系、无执行。没有将用户业务核准改称独立人工视觉证明或B共同采用。

## 正常一次与逐字段独立比较

新 C01 SourceBundle、EvidenceBundle、QuestionGraph、PRE_APPLY 均保留 OBSERVED。五项 source_integrity/structure/answer_matching/coverage/policy 的计算明细全部为真；TARGET由当前内存身份、快照、目录、能力和政策计算。目标/快照/TARGET/计划/回执为 SYNTHETIC，执行 SIMULATED，政策 A_INTERNAL_PROPOSAL/PROPOSAL_ONLY。C01 assert_plan_ready在实际试验成功返回；本侧对已归档准备包、最终包及合法重封反例再次只读调用公共验证器，并校验准备包的计划准入，不创建新目标或dispatch。[完整独立分析](../evidence/A09/review/independent-analysis.json)。

固定代码审阅确认：`execute`在目标锁内先复核raw授权、未消费状态、固定目标、当前快照，重新计算来源/五项检查/TARGET/计划并比较，再执行C01门和公开 `apply_synthetic_action`。该公开函数直接修改内存题列表、框列表、frame_projections及epoch；没有实例化持久化runtime、调用旧MockSession.execute、私有_write或monkeypatch。`observe(self)`不接收plan参数，防御复制真实内存状态。

自己的正常目标实际由0题0框/epoch0变成1题4框/epoch1，before/readback序列1→2、同一instance、两状态摘要不同且各自重新计算一致。基础frame核对角色、坐标、题绑定，实际frame_projections核对image/text类型和文本。独立比较器从固定授权及输入登记重新构造期望表，未使用实现计划或其自带oracle作为期望来源。

| 顺序 | 实际角色/类型 | 原图 | 半开坐标 | 实际内容 |
|---|---|---|---|---|
| 1 | Q/image | viewer-10 | [334,975,581,1077] | text=null，图像身份和原图摘要绑定 |
| 2 | Q/text | viewer-10 | [100,1118,592,1193] | 如图，在△ABC中，AB⊥AC，BD是边AC上的中线，AB=5 cm，AD=6 cm，则BC的长是 |
| 3 | Q/text | viewer-10 | [99,1202,220,1235] | ____ cm. |
| 4 | A/text | viewer-173 | [324,239,342,257] | 13 |

四框角色、类型、内容、精确坐标、原图SHA/尺寸、区域/片段身份、顺序全部匹配。一个逻辑题、一个选定题答关系，无W/E；fill_blank显式映射C01 free_response并在provenance保存原类型。题干三组全部在viewer-10、cross_page=false；答案在viewer-173。印刷4.与第4题图仅定位，未进框；____为实际填空线的文本表示，没有生成原书解析。

[准备包与计划](../evidence/A09/review/archive/candidate-1/trial/normal/prepared-bundle.json)、[实际写前](../evidence/A09/review/archive/candidate-1/trial/normal/assets/before.json)、[实际读回](../evidence/A09/review/archive/candidate-1/trial/normal/assets/readback.json)、[比较记录](../evidence/A09/review/archive/candidate-1/trial/normal/comparison.json)、[新C01回执](../evidence/A09/review/archive/candidate-1/trial/normal/receipt.json)、[最终包](../evidence/A09/review/archive/candidate-1/trial/normal/final-bundle.json)。回执APPLIED/MATCH、不可重放、POSTCHECK，仅证明本次模拟效果；内容PENDING、NOT_SUBMITTED保持。

## 原十项有限拒绝

| 调用 | 实际达到层 / 结果 | 新增题/框/dispatch |
|---|---|---|
| 缺授权 | AUTHORIZATION / APPROVAL_MISSING | 0/0/0 |
| 改授权 | AUTHORIZATION / APPROVAL_BINDING | 0/0/0 |
| 错用Q1授权 | AUTHORIZATION / APPROVAL_BINDING | 0/0/0 |
| 替换ZIP | AUTHORIZATION / INPUT_BINDING | 0/0/0 |
| 替换proposal | AUTHORIZATION / INPUT_BINDING | 0/0/0 |
| 合法重封image→text | C01通过；PRE_APPLY结构/政策类型语义门HOLD | 0/0/0 |
| 平台模式 | TARGET / PLATFORM_MODE_FORBIDDEN | 0/0/0 |
| 错目标 | TARGET / TARGET_IDENTITY | 0/0/0 |
| 陈旧目标 | TARGET / TARGET_CHANGED | 0/0/0 |
| 同计划重放 | EXECUTION / PLAN_REPLAY | 0/0/0 |

10份单项记录与summary逐个一致，每份实际before/after目标摘要相同。唯一重封反例在Evidence及Graph中将第一个image改text、合法重封并重绑引用；公共C01校验真实通过，source_integrity/answer_matching/coverage仍PASS，只有 `structure.types_match_approval` 和 `policy.image_text_text_text` 为false，得到HOLD。外层摘要门的五次拒绝仅报告各自命中层，没有当作内容/类型语义覆盖。[逐项原结果](../evidence/A09/review/archive/candidate-1/trial/summary.json)、[合法重封后包](../evidence/A09/review/archive/candidate-1/trial/semantic/legally-resealed-checked-bundle.json)。

驱动共创建3个自己的内存对象：正常、错目标、陈旧目标。只有正常对象执行1次业务变更；陈旧对象仅注入epoch变化用于原有拒绝，未恢复它或重跑。没有追加题型、随机矩阵、A07/A08回归或合同设计要求。

## 消耗、释放、归档与复现

实际消费1候选/1正常尝试/1成功/1业务dispatch，10拒绝单列；无业务失败、UNKNOWN、超时或第二候选。成功额度已耗尽，不再使用名义剩余尝试。worker与有限拒绝共2.5秒，180秒试验及240秒回收外层满足，内部守卫未改。[开始消费](../evidence/A09/review/archive/budget/attempt-1-start.json)、[结束消费](../evidence/A09/review/archive/budget/attempt-1-finish.json)。

本侧看门狗PID61820：北京时间19:19:19.8558221创建，19:19:23.2320246实际退出，原Process句柄exit0。worker PID50888：19:19:20.725707创建，原Popen句柄wait于19:19:23.219915确认exit0；后者是等待返回记录，不冒称精确内核退出时间。结束后19:19:35查询两PID均不存在。`pid_reuse_or_absent=false`是原句柄持有时仍可查询原PID，不影响原句柄wait确认退出。无长期服务、浏览器、其他进程终止。[看门狗](../evidence/A09/review/archive/launch-1.json)、[worker释放](../evidence/A09/review/archive/candidate-1/release.json)、[退出后查询](../evidence/A09/review/post-release-query.json)。

两进程退出后顺序复制自己的76份输入/输出/消费/启动文件，共4,460,930 bytes；源文件、归档文件逐份bytes/SHA相同，保留原输出，没有称为跨库原子快照。[归档清单](../evidence/A09/review/archive-copies.json)。原驱动summary的 `AUTHOR_TRIAL_PASS_NOT_INDEPENDENT_ACCEPTANCE` 是冻结驱动固定文字，原样保留；本侧建议PASS来自单独的独立分析与本报告。

本次独立交付的全部新增成员由[raw成员清单](../evidence/A09/review/review-member-manifest.json)逐项列出bytes/SHA及Git blob身份，清单排除自身避免循环；[收口检查](../evidence/A09/review/closure-checks.json)记录范围、链接、运行身份和复制稳定性。

实际必要命令如下；均已执行，作者候选与本侧成功试验均不得再次执行。Git从首条设置GIT_NO_LAZY_FETCH=1，所有本侧Git命令均用 `-c core.longpaths=true`；没有用CRLF改pins。

```powershell
$env:GIT_NO_LAZY_FETCH='1'
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONDONTWRITEBYTECODE='1'
# 以下在报告目录执行，只读预检，不创建目标
python -B docs/evidence/A09/review/review_audit.py preflight
# 以下在固定产品运行目录执行，只复制自己的输入
python -B examples/a09/stage_inputs.py --stage D:/1800/.local/stages/a08-inputs/B-46007447-Q4-Q9-Q16-next-batch-HOLD-2026-10-19.zip --destination D:/1800-worktrees/a09-q4-review-run/.local/a09-review/inputs
# 以下在报告目录核对副本
python -B docs/evidence/A09/review/review_audit.py staged
# 以下是运行目录唯一一次完整调用，ExpectedHead保持实际产品
& examples/a09/launch.ps1 -ExpectedHead 29c82b0997be3080f53dfde2afbb1d7457b04197 -Inputs D:/1800-worktrees/a09-q4-review-run/.local/a09-review/inputs -Output D:/1800-worktrees/a09-q4-review-run/.local/a09-review/candidate-1 -BudgetDir D:/1800-worktrees/a09-q4-review-run/.local/a09-review/budget -LaunchRecord D:/1800-worktrees/a09-q4-review-run/.local/a09-review/launch-1.json
# 原句柄退出及PID查询后，在报告目录顺序归档并只读分析
python -B docs/evidence/A09/review/review_audit.py archive
python -B docs/evidence/A09/review/review_audit.py analyze
```

报告审计辅助脚本仅在本侧证据目录新增，不属于被验收产品。[脚本](../evidence/A09/review/review_audit.py)、[固定源码审阅](../evidence/A09/review/source-inspection.json)、[辅助查询纠正记录](../evidence/A09/review/reviewer-tooling-observation.json)。一次只读源码定位误查了公开函数的再导出文件，出现StopIteration；随后找到 `.persistent` 中的纯函数定义，没有改产品、候选或重跑业务，不属于业务失败。归档产物分析不创建目标、计划、负例或消费记录。

仅新增本报告及 `docs/evidence/A09/review/`。未写主调度目录、作者目录或调度JSON；0平台、0推送、0B消息、0题22、0付费模型、0联网安装、0凭据读取、0B脚本/SQLite执行。A04真实平台阻断、其他三例HOLD、整页/新批/其他题型覆盖未证明的边界保持。固定提交后释放；由主调度核证后决定接受及范围集成。
