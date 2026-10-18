# A07 固定 Q1 离线模拟执行交付

2026-10-18，状态 **READY_FOR_REVIEW**。执行者已完成首个冻结候选的一次正常离线闭环，交付独立验收；不自行记 ACCEPTED 或 INTEGRATED。

- 工作目录：`D:/1800-worktrees/a07-q1`，分支 `codex/a07-q1-offline`。
- 产品基线：`2e71462dda8d225e4f41e8c6cd03a9ce7b88046a`；工作流基线：`b1c84db9d1d5603a4fd6aa5487d7c45ec6fca50a`。
- 唯一冻结产品候选：`6dad9b9a40a10989c102d91cf7b54f19c012015f`；tree `77f0761d050061a037ade088266f68ead4c6d930`，新增11个实现/政策/样例/测试文件。
- 本报告所在后续交付提交只增加报告和执行证据，产品与上述候选原 Git bytes 相同。最终提交 SHA 在交付回复中给出，亦可 `git -c core.longpaths=true rev-parse HEAD` 核对。
- [产品 raw Git 成员清单](../evidence/A07/execution/candidate-1-raw-git-manifest.json)与[最终交付 raw 清单](../evidence/A07/execution/delivery-raw-git-manifest.json)按 Git blob 取字节；后者明确排除自身以避免自引用摘要。工作流全部29,296条旧路径原 blob 保全。

## 实际结果与消耗

[正常试验摘要](../evidence/A07/execution/candidate-1/run/summary.json)：`a07-author-1`，1题、1计划、1个 CREATE_FRAMES 动作，目标实际从0框变成6框。五项 PRE_APPLY 与四项 TARGET 均由代码实算 PASS，C01 `validate_bundle / seal_artifact / assert_plan_ready` 通过。

[模拟回执](../evidence/A07/execution/candidate-1/run/receipt.json)为 `APPLIED / MATCH / POSTCHECK / replay_allowed=false`，回执 ID `a07-receipt-a07-author-1`，revision 1，C01 全信封 content_hash `695ffe04e616cf207b14badecd90ac8381e3fa3b5e4c8f2331b36b2d4cced966`。计划 hash `92d44aa9c566aa5ff0d16d9eb345b101798e0544e62f4eb24a016af4f59c42a9`。

[写前读数](../evidence/A07/execution/candidate-1/run/assets/before.json)与[独立读回](../evidence/A07/execution/candidate-1/run/assets/readback.json)分别是同一内存实例的读取序号1、2；读取函数只接触目标状态，不接收计划。目标业务摘要由 `a0d98e5b89efec908033b39fb0561e7ecd3ee0e5d4e17fe686213ca3b23911e1` 变为 `9a8e9daada136cd8fd71b664f99e254d8ffa640a1c602ac217b7806fb006dcec`。[公共比较结果](../evidence/A07/execution/candidate-1/run/comparison.json)核对真实状态中的题目、六框原图坐标、角色及投影，未把计划直接当读回。

| 角色 | 原图 | 实际读回 bbox，右下半开 |
|---|---|---|
| stem/Q | viewer-10 | [70,332,590,445] |
| option A/Q | viewer-10 | [96,453,153,486] |
| option B/Q | viewer-10 | [207,453,262,486] |
| option C/Q | viewer-10 | [320,453,374,486] |
| option D/Q | viewer-10 | [430,453,486,486] |
| answer D/A | viewer-173 | [72,239,88,258] |

执行侧额度累计：1/2冻结实现候选，1/2完整正常尝试，1次成功，1次业务 dispatch。成功后没有第二次正常业务。试验本体7.5秒，监督进程8.25秒，未触发180秒试验/240秒回收看门狗；这不是业务 SLA。后续只读取现有产物验证、整理清单。

10项窄单元检查在冻结前通过，包含一个只规划正控及9个拒绝调用；两次通过的窄套件累计18个拒绝调用均零目标变更。第一次准备测试时测试字段 `run` 遮蔽 unittest 方法，runner 在派发测试前失败；已在冻结前改为 `run_id`，[诊断原记录](../evidence/A07/execution/pre-freeze/first-test-harness-failure.json)保留，没有消耗正常业务额度。[最终窄检查输出](../evidence/A07/execution/pre-freeze/unit-output-final.txt)和[逐调用层级](../evidence/A07/execution/pre-freeze/unit-calls-final.json)均保留，未用新证据覆盖前一套件。正常闭环后另有1次[真实已消费计划重放拒绝](../evidence/A07/execution/candidate-1/run/replay-rejection.json)，`EXECUTION / PLAN_REPLAY`，零变更、零新增业务 dispatch。

## 固定输入、授权与实现对应

输入均从任务指定主目录原件只读复制至自有 `.local/a07/inputs`。原ZIP/历史原件在试验前后摘要一致，详见[静态交付核对](../evidence/A07/execution/static-delivery-checks.json)。未执行 ZIP 附带脚本、生产者或 SQLite，没有网络补件。

| 输入 | SHA256 |
|---|---|
| 原 B ZIP | b2bed674f87cde7fb2df4fdf31dec9ede08f494fc6190f654abda51dd4dae89d |
| 新 Q1 ZIP | 3039645ca69c2604f542c479cb180049604788a3ca28ffac1b5063dee533afac |
| candidate.json | 0ce9ffb0f468ba0cc07f37978121e7f9b991b07b94335d117da3e8ea241aea5c |
| 新包 manifest | 240622443df3c1f31cf76dc490fb7b2cedb9cecb09f47f086909cbe9e9fbd345 |
| scope proposal | 289269e3e2ea3961d565c49f9078a5e273fe2517356832bcbdc3fe8636fc3019 |
| 历史 E0.1 | a763af50c0515f863eeb6dbaf533f4215535591096dd06b81632cec4acbb4493 |
| 用户授权 raw Git blob | cf6f675cfd98d438d7d465fc553e0ebbf1bfff71bd62f8453854f8527015cb6c |
| 新 A07 单题政策 raw Git blob | 1954726fa502b0a7c0a8d5705a3ca1ecfe35bd94e67a2131dc9b707115ad745b |

固定B提交 `ef6ba4dd083e7fd5378e80123b2b038dd11d7052`。原候选保持 `QuestionSourceReviewCandidate / b-question-source-review-trial/0.1`，ID `b-q1-source-review-08f4a1948c7f26003795e797`、revision 1、B payload hash `08f4a1948c7f26003795e797acd7d2d9069f4b2ddde77d2968a05945f249df30`；新 C01 用合法新 scope、信封身份与自己的全对象摘要，不把 B payload hash 当 C01 hash。

| 任务事实 | 实现及实际证据 |
|---|---|
| 来源与独立业务授权 | 新 `source/b_q1/reader.py` 先验证两ZIP完整manifest，再核固定授权/政策/所有输入 raw 摘要、B三元引用、E0.1、原题答快照。原图尺寸/摘要与13裁片像素/变换实核；[provenance](../evidence/A07/execution/candidate-1/run/assets/input/provenance.json)保留映射。 |
| 内容及区域 | 正文去 `1.`，原编号/换行视图另存，中文行连接无新增空格，保留全角括号及两个U+3000；A.2/B.3/C.4/D.5、答案D、无解析。严格六ID白名单，括号裁片含在题干内，不增加第七框；保留七个原片段与新六组映射及新旧跨度。 |
| 单题覆盖与政策 | 新政策逐条绑定30条排除条目摘要及78个依据指针，并对照原对象/空间或其他答案身份实算。6组必须全部归属，七个原题答片段必须全部映射；不是仅凭空间排除就给coverage通过。BUSINESS_REVIEW_REQUIRED单独引用新A用户授权，仅限本题离线；原127项Check、31项范围问题及19条未归属账本保留。 |
| 来源/目标分离 | Source/Evidence/Graph/PRE_APPLY为OBSERVED、原图ORIGINAL；Snapshot/TARGET/Plan/Receipt为SYNTHETIC且执行SIMULATED。政策为A_INTERNAL_PROPOSAL/PROPOSAL_ONLY，未冒称JOINT_CONFIRMED。 |
| 实算五项PRE/TARGET/计划 | `quality/q1_offline.py` 对实际输入、资源、结构、选答关系、批准库存/排除与政策计算；新执行入口复算整个来源/报告/当前目标/动作，并逐对象比对。公共C01准入检查与 `projection_frames/action_facts/compare_action_effect` 复用，旧targetcheck和MockSession未改。 |
| 实际内存变更和回执 | 新小型MemoryTarget持有自有dict，公开apply_synthetic_action只修改此dict；无私有_write、monkeypatch、持久化库。新鲜读回后比较效果并产生C01模拟回执，摘要明确NOT_SUBMITTED/PENDING。 |
| 有限负控 | 缺授权/伪授权到AUTHORIZATION层；重算payload、重封ZIP与manifest的换候选及换历史在有效封装后到INPUT_BINDING；平台、错目标、越scope、目标漂移拒绝；重封七框计划在C01结构合法后到PLAN_RECOMPUTATION；已执行计划到PLAN_REPLAY。全部零新增目标变更。 |

原始 B `HOLD / human_verified=false / business_acceptance=false / a_accepted=false` 未回写。新 A 授权不证明 B 采用共同合同或独立人工视觉复核。完整 [C01 exchange](../evidence/A07/execution/candidate-1/run/exchange.json)及[写前exchange](../evidence/A07/execution/candidate-1/run/pre-execution.json)提供确切依赖。

## 精确复现与释放

入口与独立检出方法见 [A07 CLI 样例](../../examples/a07/README.md)。作者本次完整命令（仅记录，成功后不重跑）：

```powershell
$env:GIT_NO_LAZY_FETCH='1'
$env:PYTHONPATH='src'
$env:PYTHONIOENCODING='utf-8'
python examples/a07/run_once.py --input-dir .local/a07/inputs --output docs/evidence/A07/execution/candidate-1 --run-id a07-author-1 --expected-candidate 6dad9b9a40a10989c102d91cf7b54f19c012015f
```

独立验收应按调度指定提交检出，建立自己的新输入/输出目录、run_id和证据，每候选最多一次正常完整尝试。后续交付提交的产品blob与上述候选一致，可由raw清单核对；不得把本报告当独立接受。

[监督回收记录](../evidence/A07/execution/candidate-1/supervisor.json)：业务子进程PID75456、监督进程PID26148均已退出，子进程exit0且已reap；[释放核对](../evidence/A07/execution/process-release.json)再次查询无存活自有A07 Python进程。全程零长期服务、零浏览器、零平台、零付费模型。工作树在最终交付提交后干净，作者停止改产品及运行业务。

## 限制

仅 A 本地固定书46007447/Q1、六框的离线模拟。真实平台文本呈现、重复题号处理、最终OCR/内容验证、全页/整章覆盖、B共同采用、平台资格、持久化恢复、部署及发布均未由本次证明。`NOT_SUBMITTED / PENDING` 保持。A04真实平台阻断、旧A03 pins/A06/I01源码与证据均不改变；未推送、未评论PR、未联系B或其他对话。等待主调度固定提交核验后另行派独立验收。
