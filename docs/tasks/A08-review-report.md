# A08 固定候选1独立验收报告

2026-10-19，Asia/Shanghai。独立结论：**PASS_INDEPENDENT_FINITE_READONLY / REVIEW_COMPLETE**。固定 stage 包的新只读消费者在原 R0–R7 有限范围符合任务；无 REWORK 项。本报告交主调度核证、决定接受与范围集成，未自行记录项目 ACCEPTED/INTEGRATED。

## 固定身份及独立性

- 唯一验收写入目录：`C:/Users/ASUS/.codex/worktrees/a08-readonly-review/1800`；分支 `codex/a08-readonly-review`；独立对话 `01a1527d-a541-76c2-949a-00818e322499`。
- 正式派发工作流：`88c89cf3d855f4d01b13e6e3c98079fc9827e8ad` 的 `docs/tasks/A08-review-dispatch.md`；原任务/输入/批准按 `265b7d61fc6916fda835bb10d3cb372898b106a3` 固定文档，不扩大矩阵。
- 原已发布产品基线：`e37606d74d7e538052c563d02df11c6c961b742f`；作者执行起点 `6fac939cf6cae0df88fab12d9669090c325897fc`。
- **实际运行产品候选：`04762d78eae18449d7fcf3c0de20aec23b1f6881`**。独立起始检出/作者交付 `83f119fae8e84b30332ac50288b74049514c9b4e`；其9条产品/驱动/说明路径与产品提交、raw Git 清单、实际磁盘字节逐条相等。未以主线或后续报告提交替换运行候选。
- 作者固定报告、raw 清单、12子进程 join 释放材料与调度 preflight 已读取。独立另核作者51成员、525,774 bytes raw 清单，52新增路径和12,491旧路径原 Git 对象不变。这些是交付身份检查，未作为独立运行结果。
- 新增独立驱动 [independent_review.py](../evidence/A08/review/independent_review.py)，未导入/执行作者驱动，也未使用其结果作断言来源。11个负例均从固定原包重新解析、独立生成；重封采用独立 JSON 序列化和确定 ZIP 元数据。运行前驱动摘要已固定在 [provenance.json](../evidence/A08/review/provenance.json)，运行后未改驱动或产品。

初始 Git 缓存将 `examples/a08/receive.py`、`tests/test_a08_reception.py` 标为 M，但 diff 内容/numstat 为空，磁盘 SHA 与冻结 raw blob 完全相同。未 reset、重写或借助换行规范化通过检查。这两条起始状态保留，不计为本次产品修改。

## 实际独立运行

Python 3.9.13 / 已有 Pillow 11.3.0；`GIT_NO_LAZY_FETCH=1`、Git `-c core.longpaths=true`、UTF-8、禁止写 pyc。未安装依赖、联网补件或读取凭据。

固定 B `a76e5a925fec76f20818dfdefa4145aa132ec8a8` 输入原件：`D:/1800/.local/stages/a08-inputs/B-46007447-Q4-Q9-Q16-next-batch-HOLD-2026-10-19.zip`。独立核对1,440,149 bytes、SHA256 `b646fad9008e03e79a3dddfb4ead912d7ceadefbcee331c2e2af2415abf6f673`、Git blob `4f49f37d81427e9aa8d2acf1c1919c1df8f10ce2`。ZIP实际24成员，外清单23条非自身成员、内清单9条；两层覆盖、长度/摘要及单例与批次一致，3张JPEG独立完整解码且原图SHA/尺寸一致。

本轮仅 **12次公共 CLI 调用**：原包完整接收1次 exit0，固定11负例各1次 exit2；全部 stderr 为空，每次 stdout 与独立新建 JSON 文件解析相等。公共 `-m annotation.source.b_batch` 路径实际调用公开 API；未另加一次原包/API或作者驱动运行。各次完整命令、PID、退出码、耗时、输入摘要、实际层/字段见 [finite-results.json](../evidence/A08/review/finite-results.json)，stdout/stderr/JSON均在同目录。

| 场景 | 独立观察的结果及实际定位 |
|---|---|
| R0 原固定包 | `RECEIVED_READONLY_HOLD`，4案例/3资产；第一课时Q4优先，1题答候选+3答案证据，全部HOLD |
| R1 未知schema / kind | 两例均 `VERSION / UNSUPPORTED_BATCH_VERSION`，分别定位 `staging/batch.json/schema_version`、`/kind` |
| R2 资源1 byte损坏 | `MANIFEST / MEMBER_DIGEST`，定位 `staging/assets/viewer-173.jpg` |
| R3 同号跨课时替换Q4答案并同步候选声明 | `IDENTITY / CROSS_SCOPE_OR_CASE_IDENTITY`，定位 `cases/0/answer_id` |
| R4 给Q9伪造题ID/快照及完整题答模式 | `IDENTITY / FABRICATED_QUESTION_OR_RELATION`，定位 `cases/2` |
| R5 resource-173冒充viewer-173 / 未知viewer填174 | 两例均 `SOURCE / ASSET_IDENTITY_CONFLICT`，定位 `assets/2` 及其 `external_refs` |
| R6 删除Q9后页图7区域 / Q16首个LaTeX run并同步声明计数 | 两例均 `STRUCTURE / FIXED_COUNT_MISMATCH`，定位 `cases/2/observed_counts/render_regions`、`cases/3/observed_counts/latex_runs` |
| R7 Q16附加Q1批准引用与30项排除 / Q4外加已批准标记 | 两例均 `AUTHORIZATION / CASE_APPROVAL_ESCALATION`，定位 `cases/3/approval_ref`、`cases/0/business_approved` |

每个负例均保留本次实际 ZIP 和 `*.recipe.json`：记录变更成员/原与新摘要、批次receipt摘要更新、内外清单重封验证。R2是在完成清单核对后故意损坏资源，其余负例包装完整，因此版本/身份/来源/授权门确实可达，未把相同外ZIP hash拒绝充作全部门通过。生产 pins 未改。

**R6判断严格限于原任务的结构缺失拒绝。** Q9实际移除 `resource-173` 的 `reflection-q9-figure-7`，render库存15→14；Q16实际移除首行首个LaTeX run，库存11→10，并同步声明计数。固定库存层已定位并拒绝删除，没有静默缩短接收来源，满足本次有限R6。未到后续完整快照绑定门，亦未证明公式内容、续接空间关系或业务语义正确；没有为此新增测试标准或运行。

## 原包逐例及来源结论

独立将四例完整 `source_snapshot` 与原ZIP的batch和单例逐值比较，均相等；来源原文、flags、原坐标、裁边记录、数学原片段、引用和未完成状态均保留。详见 [R0原始报告](../evidence/A08/review/R0-original.json)、[独立观察](../evidence/A08/review/original-observations.json)及[坐标台账](../evidence/A08/review/coordinate-ledger.json)。坐标台账只读取已保存R0结果，0新增接收调用；120处坐标出现分别绑定 viewer-10 4处、viewer-173 65处、resource-173 51处，逐处在各自原图边界内，重复表示不被计作新框。

| 案例 | 独立核对 | 保持的结论 |
|---|---|---|
| 第一课时Q4 | 题 `q-260d10c51f2b7c16fb6fefb5` / 答案 `a-92c4d2164ab878c8e6d4c88d`，第一章→1探索勾股定理→第1课时；4题片段含图题文字、1答案来源区 | `QUESTION_ANSWER_CANDIDATE/HOLD`；题干/13/图形范围/逐题政策均未批准 |
| 小专题Q4 | 答案 `a-35b5bc7421c65d9fcaa47e33`；3原片段、1LaTeX run、两条裁边前后及原像素声明完整 | `ANSWER_EVIDENCE_ONLY/HOLD`；题ID/题快照/A关系均null，不重算像素或核准裁边 |
| 反思跨页Q9 | 答案 `a-9a6c21dd0fe88b1059b7919e`；33原片段、15呈现区、10个文字顺序+23个图区覆盖片段、完整续接引用与未解决flags | `ANSWER_EVIDENCE_ONLY/HOLD`；无题关系，`ANSWER_SPATIAL_GAP_UNRESOLVED`保留，后页viewer未知 |
| 第二单元Q16 | 答案 `a-7302d4870826c53aea0bcd16`；17原片段、3行、11个结构化LaTeX runs逐run原值/索引/路径匹配，含`60 61`及外围符号/幂次 | `ANSWER_EVIDENCE_ONLY/HOLD`；无题关系，不做公式解析或内容核准 |

Q4答案保留 `13`、来源 `4.13`、`text_span=[2,4)`、原框 `[308.667,241.667,340.0,254.333)` 和 `viewer-173/ocr/10/detail/5`。0答案render_regions是原合法结构。题/答 `UNVERIFIED`、`FIGURE_EXTENT_UNVERIFIED` 保留；B `selected_answer_id`仅展示为 `B_DECLARED_CANDIDATE_ONLY`，`a_selected_relation_created=false`。上述4题片段+1答案区只是来源记录，不是获批执行框数。

viewer-173独立绑定resource index172、1148×1621、SHA `a231f0247cd0444cc34ed699c4cca99245d2ac6cfda5ef10a38ca3f8164510be`；resource-173是另一图，resource index173、1145×1620、SHA `8380f9a1872c830b1cf4fba12fa00e3b6d9c50ddaed357587de7333086e9cdbf`，printed_page26、viewer_page仍null。没有别名合并、推算页码或扩大内容前缀覆盖。

版本只接收外包 `b-complex-batch-evidence-package/0.1`、stage `ComplexCaseBatchProposal / b-complex-batch-proposal/0.1`，内嵌投影仅快照。外部图谱/检查/计划/续接/图形引用均保留为声明；`complete_G_Check_plan_objects_loaded=false`、`DECLARED_ONLY_EXTERNAL_NOT_LOADED`。本轮未取Q15原包，不能记为完整G0.8/Check0.8/plan0.3消费者通过。

## N01–N08有限处置

| 项 | 本次独立确认的范围 | 仍待后续任务 |
|---|---|---|
| N01 | PARTIAL：固定stage路由/版本/来源诊断 | 完整G/Check/plan及新C01 |
| N02 | 固定stage只读候选/答案证据分离 | 其余三例题身份/关系 |
| N03 | PARTIAL：保留顺序/逐图坐标/未知映射 | 续接内容核准与非前缀覆盖 |
| N04 | PARTIAL：保留原文/LaTeX runs/图形记录 | 公式解析、内容/图形/角色政策 |
| N05 | PARTIAL：保留原始/修订几何及B像素声明 | 新裁图、像素重算与变换政策核准 |
| N06 | PENDING | 完整Check、逐题适用性/政策/内容核准 |
| N07 | PENDING | PRE_APPLY/TARGET/计划/模拟及授权 |
| N08 | PARTIAL：本次有限拒绝和分例HOLD诊断 | 执行读回及逐框业务比较 |

## 保全、释放和交付

[保全核对](../evidence/A08/review/preservation.json)：本隔离检出的全部12,543既有路径、390,893,680 bytes在独立运行前后逐路径SHA/长度相同；包含全部旧产品、作者证据、Q1授权、合同/根依赖、pins和历史材料。另保留[逐文件基线](../evidence/A08/review/baseline-files.json)。原输入SHA前后不变，产品/作者驱动/说明未改。本轮只新增本报告和 `docs/evidence/A08/review/`；未编辑D:/1800主线或其他工作树。

[进程释放](../evidence/A08/review/process-release.json)：本轮12个接收子进程均communicate完成并join，驱动run阶段退出码0，未启动服务或终止其他进程。每进程30秒上限，本轮无超时、失败或重跑。负例ZIP保留于review证据目录，仅作为离线变体，未写入B原件。后续坐标/保全/链接检查只分析文件，接收调用总数仍为1+11。

独立新证据的 raw Git 成员/长度/SHA/对象清单见 [review-raw-manifest.json](../evidence/A08/review/review-raw-manifest.json)，显式排除清单自身；[交付检查](../evidence/A08/review/delivery-checks.json)记录链接/范围/whitespace检查。最终确切独立提交在交付回复登记，报告不自包含自身提交ID。

可复现的三个命令如下，限另行获派的固定检出和全新证据目录；本轮已完成，不再次执行本轮 `run`。驱动对既有结果拒绝重用，完整12条实际CLI命令以finite-results为准。

```powershell
$env:GIT_NO_LAZY_FETCH='1'
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONDONTWRITEBYTECODE='1'
python -B docs/evidence/A08/review/independent_review.py preflight
python -B docs/evidence/A08/review/independent_review.py run
python -B docs/evidence/A08/review/independent_review.py preserve
```

所有实际接收输出八项actions均为0；本轮 **0计划、0目标、0新C01执行对象、0模拟派发、0平台、0付费模型、0推送、0B消息**。未运行B脚本/SQLite或旧A07/A06/I01/A03，旧业务额度未恢复，第二产品候选未使用。该独立通过仅为固定stage有限只读结构接收，四例HOLD、内容/区域/政策待批保持；不构成新批共同业务验收、平台资格或A04真实平台解除。主调度接受/范围集成仍待其独立决定。
