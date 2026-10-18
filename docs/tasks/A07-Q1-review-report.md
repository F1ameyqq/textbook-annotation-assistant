# A07 固定 Q1 首候选独立验收

2026-10-18（Asia/Shanghai）。独立结论建议 **PASS，仅限 A 本地固定单题离线模拟**。本报告不自行将任务记为 ACCEPTED 或 INTEGRATED；调度核证后决定接受及范围集成。未修改产品、主调度 JSON、作者目录或 B 原件。

## 固定版本与独立环境

- 任务工作流：`b1c84db9d1d5603a4fd6aa5487d7c45ec6fca50a`；正式派发工作流：`505bac6195186a5dda45fb6bc56ec97f901ae4ab`。
- 产品基线：`2e71462dda8d225e4f41e8c6cd03a9ce7b88046a`。
- 审查最终交付：`d2e710c817cf85505ac4fad4919dd51d1062d33a`，tree `e96d1d546d9cd2158126d3fc36a4a6014cdf1aa6`。
- **实际正常运行 HEAD 和 `--expected-candidate`：`6dad9b9a40a10989c102d91cf7b54f19c012015f`**，tree `77f0761d050061a037ade088266f68ead4c6d930`。最终交付只通过 Git blob 读取报告和证据，未替代运行候选。
- 独立目录：`D:/1800-worktrees/a07-q1-review`；分支：`codex/a07-q1-review`。全新短路径 sparse worktree，`--no-checkout` 后 `read-tree -mu HEAD` 初始化。所有 Git 调用设置 `GIT_NO_LAZY_FETCH=1`、`core.longpaths=true`。
- 运行环境：Windows、CPython 3.9.13、Pydantic 2.12.5、Pillow 11.3.0，使用现成环境，无安装/网络补件。
- 本报告所在验收交付提交只新增报告和独立证据；确切提交 SHA 在最终交付回复提供。[验收 raw Git 成员清单](../evidence/A07/review/review-raw-git-manifest.json)排除清单自身，避免自引用；提交后再从实际 Git blob 核对。

## 原字节、输入和授权

[独立原字节核对](../evidence/A07/review/candidate-1/static-review.json)使用 `ls-tree -rz` 比较模式/对象 ID，以 `cat-file --batch` 读取成员原字节。29,296 条工作流旧路径在候选及最终交付中全部保全；产品只新增11条授权路径；最终交付只新增64条，其中清单列出自身以外63成员，共10,217,431 bytes，逐项 SHA256、字节数和 blob OID 一致。既有 src、公共合同、A03 pins、A06/I01 源码和证据未变；未因 checkout 换行表示修改 pins。自己的运行完成后、提交报告前，`git diff --quiet HEAD --` 返回0。

原交付清单 raw SHA256 为 `111918592d83446bba6d485f4d3f49d797787e925ed630f31f149c14c1ddcdcf`；原执行报告 raw SHA256 为 `404e3795d99b13312783fc8cfc46575a3d0b60c7050488ae62d54fb2724044df`。全部原成员独立核对结果保存在[被审交付 raw 成员](../evidence/A07/review/candidate-1/reviewed-delivery-raw-members.json)，不是沿用调度预检结论。

从任务指定原件新复制输入至自己的 `.local/a07/review-inputs`；授权从固定工作流 Git blob 导出。独立审计代码只读取 ZIP 成员，不执行包内脚本、生产者或 SQLite。

| 固定输入 | 独立核对 SHA256 |
|---|---|
| 原 B ZIP | `b2bed674f87cde7fb2df4fdf31dec9ede08f494fc6190f654abda51dd4dae89d` |
| 新 Q1 ZIP | `3039645ca69c2604f542c479cb180049604788a3ca28ffac1b5063dee533afac` |
| candidate.json | `0ce9ffb0f468ba0cc07f37978121e7f9b991b07b94335d117da3e8ea241aea5c` |
| 新包 manifest | `240622443df3c1f31cf76dc490fb7b2cedb9cecb09f47f086909cbe9e9fbd345` |
| scope proposal | `289269e3e2ea3961d565c49f9078a5e273fe2517356832bcbdc3fe8636fc3019` |
| 历史 E0.1 | `a763af50c0515f863eeb6dbaf533f4215535591096dd06b81632cec4acbb4493` |
| A 用户授权 raw Git blob | `cf6f675cfd98d438d7d465fc553e0ebbf1bfff71bd62f8453854f8527015cb6c` |
| A07 单题政策 raw Git blob | `1954726fa502b0a7c0a8d5705a3ca1ecfe35bd94e67a2131dc9b707115ad745b` |

[输入与政策独立核对](../evidence/A07/review/candidate-1/input-binding-review.json)核实 B 提交 `ef6ba4dd083e7fd5378e80123b2b038dd11d7052` 对应的固定包：原包104成员、新包25成员，各自 manifest 完整覆盖；B 三元引用、payload 摘要、历史 E0.1 身份、原题答快照和 `1.D` 的 `[2,3]` 跨度均匹配。候选保持 `QuestionSourceReviewCandidate / b-question-source-review-trial/0.1`，ID `b-q1-source-review-08f4a1948c7f26003795e797`、revision 1、payload SHA256 `08f4a1948c7f26003795e797acd7d2d9069f4b2ddde77d2968a05945f249df30`。

两原图分别为 viewer-10 `1217×1691`、viewer-173 `1148×1621`，原字节/摘要/尺寸匹配；13裁片逐像素与原图裁剪比较、回投矩阵核对通过。严格采用候选六ID白名单；7个原题答片段各映射一次，括号嵌入题干，不以7个 `context_only=false` 生成7框。

正文去 `1.`，原编号/换行视图独立保存；正文连行与批准文本一致，末尾为 `U+FF08 U+3000 U+3000 U+FF09`；选项 `A.2/B.3/C.4/D.5`、答案D，无解析。原31项范围问题、原Check的127项及19条未归属账本保持。30条排除逐项比较原 issue、条目摘要、理由和78个依据指针/值，并核对空间不相交或其他答案身份；业务复核项单独关联本次 A 授权。完整两页资源不产生全页/整章通过声明。

## 执行任务1–7逐项判断

| 项 | 独立结论及依据 |
|---|---|
| 1 来源与业务授权 | PASS。固定包、manifest、候选、原图、历史及授权原字节绑定独立核对；新 C01 信封使用自身完整对象摘要和合法 scope/ID。原 B 引用和新六组映射可追溯。 |
| 2 内容与区域 | PASS。正文/编号换行视图、四选项、D及原答案跨度匹配；严格六组、无辅助框或解析框。正常读回框逐项比较原图身份、摘要、尺寸、bbox、角色及fragment/region投影，无差异。 |
| 3 单题政策与覆盖 | PASS。30条排除与78依据实核；原31问题、127项Check、19条账本保留。新scope仅本题，6组全归属/7原片段全映射。业务项仅在固定 A 离线授权下处置，未删除原问题。 |
| 4 来源与模拟身份 | PASS。Source/Evidence/Graph/PRE_APPLY为OBSERVED、原图ORIGINAL；Snapshot/TARGET/Plan/Receipt为SYNTHETIC，执行SIMULATED；政策仍为A_INTERNAL_PROPOSAL/PROPOSAL_ONLY，B HOLD/非人工/非业务字段未回写。 |
| 5 五项检查与写前复算 | PASS。自己运行生成的source_integrity、structure、answer_matching、coverage、policy及四项TARGET逐个比较实际计算记录，全部PASS。当前空目标、固定scope/book/directory、CREATE_FRAMES及同会话读回明确绑定。执行锁内重算来源/报告/目标/计划并比较整个bundle；C01合法重封七框计划仍在PLAN_RECOMPUTATION拒绝。C01 validate_bundle/assert_plan_ready及独立全信封hash计算通过。 |
| 6 正常内存闭环 | PASS。自己的新目标、run_id `a07-review-1`，1题/1计划/1个CREATE_FRAMES动作，0框→6框；读取序号1→2、同实例、目标实际摘要改变。读取函数只收self并读取目标state；执行顺序为实际公开内存apply后重新observe，不接收计划作为读回。模拟回执APPLIED/MATCH/POSTCHECK，replay_allowed=false；NOT_SUBMITTED/PENDING保持。 |
| 7 有限拒绝 | PASS。9项独立拒绝调用与正常闭环后的1次实际重放拒绝，全部零新增目标变更；换候选先完成payload/ZIP/manifest重封并通过封装校验，随后在AUTHORIZATION/INPUT_BINDING拒绝。无新增业务矩阵。 |

以上不是复述作者测试数：独立实现[原字节/输入/有限拒绝审计](../evidence/A07/review/candidate-1/review_checks.py)，并用[独立读回核对](../evidence/A07/review/candidate-1/readback_checks.py)读取自己的正常产物、独立计算全信封与状态摘要、按固定来源逐框比对。未重复运行作者单元套件或旧 C01/A03/A06/I01 成功矩阵；旧模块证据只在原字节不变的已接受范围沿用。

## 实际正常回执与读回

[独立正常摘要](../evidence/A07/review/candidate-1/normal/run/summary.json)、[模拟回执](../evidence/A07/review/candidate-1/normal/run/receipt.json)、[完整 C01 exchange](../evidence/A07/review/candidate-1/normal/run/exchange.json)、[写前exchange](../evidence/A07/review/candidate-1/normal/run/pre-execution.json)、[独立二次核对](../evidence/A07/review/candidate-1/readback-review.json)均来自本验收目录。

- 计划 `a07-plan-a07-review-1`，revision 1，hash `085db1af2db83282603a655150099b9fdc79ff9a6c28879f725753e6cc307456`。
- 回执 `a07-receipt-a07-review-1`，revision 1，hash `e9c63fcbc8fa3571dcb1d943d1a30be627e193efc061ceb501e7cb537d6921d3`。
- [写前状态](../evidence/A07/review/candidate-1/normal/run/assets/before.json)摘要 `a0d98e5b89efec908033b39fb0561e7ecd3ee0e5d4e17fe686213ca3b23911e1`；[实际读回](../evidence/A07/review/candidate-1/normal/run/assets/readback.json)摘要 `9a8e9daada136cd8fd71b664f99e254d8ffa640a1c602ac217b7806fb006dcec`。业务状态与作者相同是相同固定题的预期效果；目标实例ID独立且与作者不同。
- 两次读取序号 `[1,2]`，1个目标题与6个唯一框，内部题ID绑定为 `q-e92a499995ca1bbd570a2a09`；辅助裁片和括号未额外成框。公共比较结果MATCH，另行逐框比较差异 `[]`。

| 语义 | 原图 | 实际读回 bbox，右下半开 | 角色 |
|---|---|---|---|
| stem | viewer-10 | `[70,332,590,445]` | Q |
| option A | viewer-10 | `[96,453,153,486]` | Q |
| option B | viewer-10 | `[207,453,262,486]` | Q |
| option C | viewer-10 | `[320,453,374,486]` | Q |
| option D | viewer-10 | `[430,453,486,486]` | Q |
| answer D | viewer-173 | `[72,239,88,258]` | A |

## 拒绝层级、消耗与释放

[9项独立拒绝原记录](../evidence/A07/review/candidate-1/negative-calls.json)及[已消费计划重放记录](../evidence/A07/review/candidate-1/normal/run/replay-rejection.json)：

| 调用 | 到达层 / 拒绝码 | 新目标变更 |
|---|---|---|
| 缺授权 | AUTHORIZATION / APPROVAL_MISSING | 0 |
| 伪造扩大授权 | AUTHORIZATION / APPROVAL_FORGED | 0 |
| 换选项、重算payload并重封ZIP/manifest | AUTHORIZATION / INPUT_BINDING，封装先通过 | 0 |
| 换关联历史身份 | AUTHORIZATION / INPUT_BINDING，包封装有效 | 0 |
| 平台模式 | TARGET / PLATFORM_MODE_FORBIDDEN | 0 |
| 错目标 | TARGET / TARGET_IDENTITY | 0 |
| 越出批准scope | TARGET / TARGET_IDENTITY | 0 |
| 当前目标漂移 | TARGET / TARGET_CHANGED | 0 |
| C01合法重封七框效果计划 | EXECUTION / PLAN_RECOMPUTATION | 0 |
| 实际已执行计划重放 | EXECUTION / PLAN_REPLAY | 0 |

独立累计消耗：正式候选1、正常完整尝试1/2、成功闭环1（已达成功上限）、业务dispatch 1；拒绝调用10，额外业务dispatch 0。正常成功后未重跑，也没有第二候选或补改产品。此前准备轮0业务/0写入不消耗完整尝试。作者原候选/运行证据全部保留，作者消耗仍按原报告记录，不从独立额度扣除或恢复。

[监督回收](../evidence/A07/review/candidate-1/normal/supervisor.json)：子进程PID41552、监督进程PID59684，exit0/reaped，无超时；本体9.516秒、监督10.468秒，180秒/240秒外层未触发，这些耗时不构成业务SLA。[释放证明](../evidence/A07/review/candidate-1/process-release.json)检查上述PID及有限负控PID73044均无存活，未发现本目录自有A07 Python进程。所有工具命令均已返回退出结果；零长期服务、浏览器、平台及付费模型调用。原件在运行后再次与自己的初始复制摘要和字节比较一致。

## 本次实际命令

以下为已经执行的命令记录。正常命令仅执行一次，成功后不再执行；未来业务复现须遵守调度指定的候选及剩余额度。工作目录均为本报告所列独立目录。

```powershell
$env:GIT_NO_LAZY_FETCH='1'
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONPATH='src'
python docs/evidence/A07/review/candidate-1/review_checks.py static
python examples/a07/stage_inputs.py --destination .local/a07/review-inputs
python docs/evidence/A07/review/candidate-1/review_checks.py inputs
python docs/evidence/A07/review/candidate-1/review_checks.py negative
python examples/a07/run_once.py --input-dir .local/a07/review-inputs --output docs/evidence/A07/review/candidate-1/normal --run-id a07-review-1 --expected-candidate 6dad9b9a40a10989c102d91cf7b54f19c012015f
python docs/evidence/A07/review/candidate-1/readback_checks.py
```

独立脚本拒绝覆盖已有结果；保留[负控输出](../evidence/A07/review/candidate-1/negative-output.txt)、[正常子进程输出](../evidence/A07/review/candidate-1/normal/process-output.txt)及[读回核对输出](../evidence/A07/review/candidate-1/readback-output.txt)。本轮无产品失败、UNKNOWN、验收失败或未解决的本任务阻断项；未自行纠正产品或增加试验。

## 结论边界

PASS建议只覆盖书46007447的固定Q1、6组/6框、A用户核准单题范围和明确内存模拟。原B HOLD、human_verified=false、business_acceptance=false、原Check/问题/账本保持；A用户核准不等于B共同采用或独立人工视觉复核。真实平台文本呈现/去号、OCR/内容最终质量、全页/整章覆盖、通用B版本、持久化恢复、部署/发布均未由本次证明。NOT_SUBMITTED/PENDING和A04真实平台阻断保持。未向B或其他对话发消息、未推送、未连接平台；后续接受与集成由主调度处理。
