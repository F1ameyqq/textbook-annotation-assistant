# A09 第4题作者执行报告

状态：**READY_FOR_REVIEW**。候选1的有限作者试验完成，尚未经独立验收、调度接受或集成。成功后未重跑、补证试验或修改产品/驱动。

## 固定身份与准入

产品基线 `846662f4aab08a75d6ad0482edeced4550e1a1ab`；派发工作流 `0a9c634d160ac7b39f68a1fb3555f409dd408f49`。**实际运行产品及驱动候选为 `29c82b0997be3080f53dfde2afbb1d7457b04197`**，tree `240729ac2e07709434df15b5707995ab0cce1f93`。最终交付提交仅追加报告/证据，不能替代运行身份。

分支 `codex/a09-q4-offline`，实际运行目录 `D:/1800-worktrees/a09-q4`，原输出 `.local/a09/candidate-1`。作者未写主调度目录、任务/授权/inputs或调度JSON。实现入口及职责见[使用说明](../a09-q4-offline-simulation.md)。

范围仅书46007447第一章第1课时第4题 `q-260d10c51f2b7c16fb6fefb5`，答案 `a-92c4d2164ab878c8e6d4c88d`。B固定提交 `a76e5a925fec76f20818dfdefa4145aa132ec8a8`。

| 输入 | raw SHA256 |
|---|---|
| stage ZIP，1,440,149 bytes | `b646fad9008e03e79a3dddfb4ead912d7ceadefbcee331c2e2af2415abf6f673` |
| proposal | `e8146fc7a4fe2e16c1fc1194d49de1caa1fe029dd6907848bbaa6c9082dc0bbe` |
| 新A用户授权 | `5c73af50262f6bd7e48e2b0d46148026c1c3a953d1ee93c8262e356733d99010` |
| A09输入清单 | `aa4f2f7119ef71f70367e3bf7b3c3ed61e05e8a1643572aca92969d05cc1f9bf` |
| 本题政策 | `0764136893bc44dae37b884cf52ceffe9756224fb6ddcb417ea9255cc9233f6c` |
| B原case | `11aa94a8748b60136aab66eb652682fb7910fc0d3203f9d2b65022b269df8e0c` |

原ZIP从登记的本地只读路径复制至作者自己的输入目录。proposal、授权、输入清单及负例用Q1授权直接取固定工作流Git blob。仅解读所需原包/阶段manifest、本题case、原receipt和两原图；不运行A08 CLI/R0–R7或B生产者。完整外部G0.8/Check0.8/plan0.3未加载，原receipt中引用只保存为declared-only事实。

viewer-10为1217×1691，SHA `eb7cc17e6b58a55a005ce1cdef5bd5058ad258c3dd44dc891b3d830ed3db3626`；viewer-173为1148×1621，SHA `a231f0247cd0444cc34ed699c4cca99245d2ac6cfda5ef10a38ca3f8164510be`。原JPEG bytes复制，无重编码。viewer-173明确为resource index172，未混同resource-173。

[输入原字节清单](../evidence/A09/execution/input-raw-manifest.json)、[固定产品raw Git清单](../evidence/A09/execution/product-raw-members.json)、[运行依赖raw Git清单](../evidence/A09/execution/candidate-1/runtime-members.json)。

## 实算链及真实读回

新C01 Source/Evidence/Graph/PRE_APPLY均OBSERVED。source_integrity、structure、answer_matching、coverage、policy五项由实际输入计算并PASS，包括原图/坐标、角色、image/text类型、文本、顺序、唯一题答关系、同页题干、单题覆盖、历史HOLD和新A授权。fill_blank显式映射现有C01 free_response，原类型来源保留在provenance；三个stem均在viewer-10，cross_page=false。

目标、TARGET、ApplyPlan及ExecutionReceipt为SYNTHETIC，执行SIMULATED，实际C01 assert_plan_ready成功返回。execute在同一目标锁内重算授权、来源、五项准入、当前目标、计划及C01门，再调用公开apply_synthetic_action。未调用Q1绑定入口、旧MockSession.execute、私有_write、monkeypatch、持久化runtime或SQLite。

正常一次实际内存由0题0框/epoch0变为1题4框/epoch1，读回序列1→2。observe无plan参数，独立读取target/frame_projections。实际投影的类型/文本、基础框的角色/坐标分别对照raw授权表，零差异，没有只比较计划与自身读回。

| 顺序 | 实际角色/类型 | 原图 | 半开坐标 | 实际内容 |
|---|---|---|---|---|
| 1 | Q/image | viewer-10 | [334,975,581,1077] | image，text=null；原图摘要及区域绑定 |
| 2 | Q/text | viewer-10 | [100,1118,592,1193] | 如图，在△ABC中，AB⊥AC，BD是边AC上的中线，AB=5 cm，AD=6 cm，则BC的长是 |
| 3 | Q/text | viewer-10 | [99,1202,220,1235] | ____ cm. |
| 4 | A/text | viewer-173 | [324,239,342,257] | 13 |

无W/E。印刷4.和第4题图图注仅定位，不进框。原4题片段+1答案片段、旧浮点OCR框完整保留，另列到新A四区域的映射。辅助数学核对未变成原书解析。C01基础target frame无类型字段，image依据实际frame_projections读回；没有声称平台图片控件或OCR已验。

[准备后bundle](../evidence/A09/execution/candidate-1/trial/normal/prepared-bundle.json)、[写前实际观测](../evidence/A09/execution/candidate-1/trial/normal/assets/before.json)、[写后实际读回](../evidence/A09/execution/candidate-1/trial/normal/assets/readback.json)、[批准表比较](../evidence/A09/execution/candidate-1/trial/normal/comparison.json)、[模拟回执](../evidence/A09/execution/candidate-1/trial/normal/receipt.json)、[最终bundle](../evidence/A09/execution/candidate-1/trial/normal/final-bundle.json)。

## 固定有限拒绝

| 调用 | 实际达到层/结果 | 新增题/框/dispatch |
|---|---|---|
| 缺授权 | AUTHORIZATION / APPROVAL_MISSING | 0/0/0 |
| 改授权 | AUTHORIZATION / APPROVAL_BINDING | 0/0/0 |
| Q1授权 | AUTHORIZATION / APPROVAL_BINDING | 0/0/0 |
| 替换ZIP | AUTHORIZATION / INPUT_BINDING | 0/0/0 |
| 替换proposal | AUTHORIZATION / INPUT_BINDING | 0/0/0 |
| 唯一合法重封image→text | C01真实验证通过；PRE_APPLY.structure.types_match_approval / policy.image_text_text_text失败，HOLD | 0/0/0 |
| 平台模式 | TARGET / PLATFORM_MODE_FORBIDDEN | 0/0/0 |
| 错目标 | TARGET / TARGET_IDENTITY | 0/0/0 |
| 陈旧目标 | TARGET / TARGET_CHANGED | 0/0/0 |
| 同计划重放 | EXECUTION / PLAN_REPLAY | 0/0/0 |

每次拒绝实际before/after状态摘要相同。类型反例合法重封Evidence/Graph并重绑依赖，不改生产pins；source_integrity/answer_matching/coverage仍PASS，仅structure/policy为FAIL，证明真实到达摘要门后的语义层。外层摘要拒绝仅证明其实际到达层。未扩展随机/其他题型矩阵或旧A07/A08完整回归。

本次3个内存实例：正常目标、错目标拒绝对象、带自己冻结计划的陈旧目标拒绝对象；只有正常目标发生业务变更。陈旧目标只注入epoch变化，拒绝后不恢复。其他三案例均HOLD，无题关系/无执行。[逐项运行摘要](../evidence/A09/execution/candidate-1/trial/summary.json)、[合法重封反例](../evidence/A09/execution/candidate-1/trial/semantic/legally-resealed-checked-bundle.json)。

## 消耗、释放与保全

用了1个冻结候选、1次正常完整尝试、1次成功、1个实际业务dispatch，10次拒绝单列。无业务失败/UNKNOWN/超时，无第二候选；成功上限1/1已耗尽，不再运行剩余名义尝试。worker含正常与拒绝共3.813秒，180秒试验/240秒回收外层满足，内层守卫未放宽。

看门狗PID27428，创建2026-10-19 18:39:57.3544227+08:00、实际退出18:40:02.9781447+08:00，exit0。worker PID38360，创建18:39:59.140054+08:00，原Popen句柄wait在18:40:02.951123+08:00确认exit0（等待返回时间，不冒称精确内核退出时间）。两者均释放，后续只读查询两PID均不存在。无服务/浏览器/长期进程，无终止无关进程。release的pid_reuse_or_absent=false只表示原句柄尚持有时PID仍可查询，退出事实依据原句柄wait，结束后查询另存。

[看门狗实际退出](../evidence/A09/execution/candidate-1/launch-1.json)、[worker释放](../evidence/A09/execution/candidate-1/release.json)、[结束后查询](../evidence/A09/execution/post-release-query.json)、[开始消费](../evidence/A09/execution/candidate-1/consumption/attempt-1-start.json)、[结束消费](../evidence/A09/execution/candidate-1/consumption/attempt-1-finish.json)。

worker及看门狗结束后，顺序复制71份输出/看门狗/消费原文件并核对bytes/SHA，原输出不覆盖，不称跨数据库原子快照。[复制清单](../evidence/A09/execution/archive-copies.json)。冻结前1次窄单元检查PASS，0目标/0计划/0完整业务；使用现有Python3.9.13/Pydantic2.12.5/Pillow11.3.0，无联网安装。[窄检查](../evidence/A09/execution/preflight/static-checks.json)。

工作流29,721条既有Git路径全部mode/kind/blob一致；实际检出956份旧文件逐个raw bytes一致，稀疏缺少的28,765份仍在原Git树，未删除。相对产品基线29,717条旧路径，29,713条一致；AGENTS.md、coordination-state.json、coordination.md、development-plan.md四份管理文件差异已在派发工作流继承，作者未改。全部既有源码、合同/schema/pins、根依赖、历史证据保持。[磁盘原字节审计](../evidence/A09/execution/preflight/old-working-bytes.json)。

成功后的打包审计曾把“产品基线所有路径不变”作为断言，因上述四份继承管理文件差异触发AssertionError。[审计观察](../evidence/A09/execution/packaging-audit-observation.json)保留；已改为对派发工作流全路径比较并单列继承差异。此次仅打包元数据口径纠正，0产品/驱动改动、0业务重跑，不作为第二候选或隐藏业务失败。

## 精确复现和交接

以下命令仅供调度向独立验收派发固定候选后，在它自己的raw检出、输入/输出/消费目录执行。作者成功试验不得再跑。

```powershell
$env:GIT_NO_LAZY_FETCH='1'
python -B examples/a09/stage_inputs.py --stage D:/1800/.local/stages/a08-inputs/B-46007447-Q4-Q9-Q16-next-batch-HOLD-2026-10-19.zip --destination <own-input-dir>
& examples/a09/launch.ps1 -ExpectedHead 29c82b0997be3080f53dfde2afbb1d7457b04197 -Inputs <own-input-dir> -Output <own-fresh-output-dir> -BudgetDir <own-budget-dir> -LaunchRecord <own-fresh-launch.json>
```

实际作者调用的Inputs为`D:/1800-worktrees/a09-q4/.local/a09/inputs`，Output为`D:/1800-worktrees/a09-q4/.local/a09/candidate-1`，BudgetDir为`D:/1800-worktrees/a09-q4/.local/a09/budget`，LaunchRecord为`D:/1800-worktrees/a09-q4/.local/a09/launch-1.json`；ExpectedHead为上述产品SHA。驱动起动核对冻结HEAD和所有运行成员raw bytes，拒绝以最终文档提交替换。

NOT_SUBMITTED/PENDING保持；政策A_INTERNAL_PROPOSAL/PROPOSAL_ONLY。旧proposal false、B HOLD/UNVERIFIED/FIGURE_EXTENT_UNVERIFIED保持。新A业务核准与独立人工视觉、B联合采用分开。本报告不宣称独立/调度ACCEPTED、INTEGRATED、公共合同冻结、整页/全书/其他题型覆盖、OCR或真实平台资格。A04阻断保持。0平台、0推送、0B消息、0题22、0付费模型、0联网安装、0凭据读取。产品写入已结束，等待主调度预检和现有独立对话固定复验。
