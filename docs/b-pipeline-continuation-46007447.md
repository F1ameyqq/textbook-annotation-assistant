# 跨页续接接入持久流水线与当前图谱重检

后续更正（2026-10-17）：本页记录历史版本。下文开发参考中的`√625`是当时的目视误读；当前原图观察为`625=25²`，新增v2参考保留旧参考及更正链，未改写本轮历史评估或原始OCR。当前包绑定v2，说明与新运行见 [行内数学补读](b-inline-math-46007447.md)。

2026-10-17，基线`445cebab615f4556b8916349dcddf6a5d60c9e67`。继续长期L1复杂内容、L2恢复处理和L5可交接运行。实际对象为46007447原5张来源及resource173的既有前缀观察，没有新增OCR、网络访问或网站标注操作。公共合同仍是草案，A接收验证仍PENDING_A。

## 本轮解决的问题

此前回补链能生成0.3图谱及检查，Q9的0.4续接另行重放。不能给新图谱附上旧检查，或把针对旧实体ID的历史续接证明直接套在当前OCR版本上。本轮将来源扩展、证明重建、本地应用和新质量检查接到同一持久流水线；`final_outputs`只有全部阶段完成才给出实际E6、G4及Check04引用。

| 新阶段 | 输入与结果 |
|---|---|
| continuation_prepare | 核对当前E/G和冻结的原Q9来源快照，生成明确扩展范围的E6/G6；归档完整当前E5/G5 |
| continuation_proof | 从当前实体重新生成相邻来源、图区域、组合标题和续接证明；不消费历史证明ID |
| continuation_apply | 生成新0.4图谱、独立应用检查及外部版本回执；验证精确回滚 |
| continuation_quality | 对实际E6/G4重做题目、配答、标量、来源片段/跨度/归属/账本和局部回补检查，生成b-check-trial/0.4 |

缓存E0.2加回补包为9阶段，已恢复E0.3不重复回补为7阶段；显式live OCR加回补为10阶段。本轮实际运行9阶段及7阶段，未重新运行live模型。未提供`--continuation`时保留原链；包和相邻原图必须一起显式提供，默认几何路径仍在细化前等待OCR授权参数。

## 来源与当前版本

`continuation-package.json`绑定四份既有/新增观察文档、原图SHA、实际裁片及RGB像素、组合标题和完整Q9原始快照。原8行OCR对象和8片段除版本相关fragment_id外逐字段核对，包括分数、位置、文字跨度、OPEN边界和首尾来源；只匹配页面SHA不够。当前图谱payload须与当前E的组装一致，其他题目的合法回补可以保留。路径分别相对包manifest和source manifest，不能依赖旧工作目录。

新的三个阶段封套及E6/G6不加入生成时间。续接启用时，仅对尚未发布的新assemble结果使用显式`EXECUTION_TIME_IN_STAGE_JOURNAL/0.1`策略；运行时间保留在wrapper和SQLite，历史输入/归档的时间及引用原样保存。文本内容身份与实际文件字节回执分开；换行规范化不放宽原图、裁片或像素核对。

四阶段缓存绑定所有嵌入产物的源码依赖，包括完整offline、answer_assembly和policy；还记录NumPy/Pillow、OpenCV入口及实际native模块二进制SHA。规则或底层像素实现变化会失效受影响阶段，旧产物留存。来源只扩展为6资产，其中resource173只采集前缀、图形及标题边界；未核准viewer页号，不宣称完整第6页或整书OCR。

## 新检查与实际结果

实际9阶段完成后，原5页仍为34题、66答案候选和34个唯一同范围候选链接。Q9有33来源片段、15呈现区（10正文、5图片）；23个图内OCR仅诊断，不再重复作为文本呈现。扩展账本202行=154 CONSUMED+29 EXCLUDED+19 UNASSIGNED；全图195答案片段。候选数量不是准确率，19条数学内容未被强行分配。

Check04重检当前图谱，保留115项问题。只对有当前独立应用证据的Q9旧文字投影规则和精确两条标题排除作显式替代处置，并记录结构边界已解决；空间缺口、未归属、公式候选、OCR争议及业务审核要求仍保留。派生审核的预期来自冻结来源快照和证明指向的续行，不从待检图谱复制答案作为预期。独立消费者另行核对全部来源、引用、规则处置、当前问题及计数，不执行续接或组装生产者。

逐像素检查续页另冻结5条MODEL_VISUAL开发参考，含6处差异：`AB²`/`20²`/`5²`漏上标、`√625`漏根号、`+`误为`十`及“蚂蚁”误字。Check04逐条保留`CONTINUATION_DEVELOPMENT_TRANSCRIPTION_DISAGREEMENT`，不回写OCR，也不冒充人工盲标或业务金标准。因此结构续接成功没有把正文转写标为通过；新旧问题数量也不表示识别准确率升降。

实际缓存链检查包括：

- 依次停在prepare、proof和apply，再续跑到quality；partial时`final_outputs=null`。
- 冻结代码后9阶段完整重跑及全9缓存；相同当前E3/审核的7阶段链与9阶段链三个最终业务引用一致。
- 仅改变审核元数据，7阶段中只有两次质检重做，其他5阶段缓存。
- 故意损坏apply的immutable物件，独立审计先拒绝；修复仅重做apply/最新quality，5阶段缓存、1项损坏失效，旧坏字节保留；后续全7缓存。
- 构造样本中的真子进程在apply物件发布、SQL成功前退出；旧attempt记INTERRUPTED、孤立物件保留但不消费，恢复重做apply及quality。
- 构造样本只改变OpenCV native摘要时，仅4个续接阶段失效。原图变化、换白裁片、当前源行变化、伪人工核准、漏诊断/标题、篡改问题及跨度均有拒绝回归。

全部6张实际原图SHA保持相同；本轮新OCR、模型推理、网站请求/动作、上传、下载和额外付费调用均为0。运行时曾更新独立审计的坏输入保护，旧Check04被正确拒绝；原失败回执保留，最终冻结版本重新运行并通过，不能将那个旧产物称为当前通过。

## 复现与交接

普通离线入口使用已经存在、SHA匹配的本地原图及当前E0.2；大原图不随局部重放fixture交付。下面路径名为本地输入占位符，不是下载入口：

```sh
python tools/run_pipeline_b.py --source SOURCE_JSON --context tests/fixtures/book46007447/context.json --review tests/fixtures/book46007447/review.json --evidence CURRENT_E2_JSON --recovery tests/fixtures/book46007447/recovery-package.json --continuation tests/fixtures/book46007447/continuation-package.json --adjacent-source ORIGINAL_RESOURCE_173_JPG --workdir data/runs/continuation-current --stop-after continuation_apply
```

同样命令去掉`--stop-after`续跑。已有当前E0.3时省略`--recovery`，并提供对应派生审核。CLI将完整性审计的拒绝作为非零退出；READY只说明离线阶段完成，所有业务产物仍HOLD、transcription_verified=false、business_acceptance=false、platform_actions=[]。

```sh
python -m unittest discover -s tests -q
```

工作目录671项完整回归通过（188.489秒），Git导出目录671项同样通过（188.978秒）；实际9阶段重放在NumPy2.3.5/OpenCV4.10.0/Pillow12.2.0及NumPy1.26.4/OpenCV4.11.0/Pillow12.3.0下最终E/G/check引用相同，导出后重复全9缓存。包JSON的CRLF/LF字节SHA不同，规范化内容一致，真实原图与裁片核对保留。完整源码/输入/产物摘要见`evaluation/book-46007447-pipeline-continuation.json`。本轮新增52项回归：生产14、独立质量18、CLI18、真实进程/依赖控制2。A需适配新三阶段封套、Check04当前引用、typed render_regions与前缀范围；接收方验收由A自行记录。

后续继续改善这些已定位的正文/公式转写，接入公式候选而不按开发参考自动选择；补齐19条内容的对应题页/目录身份，再扩展全书来源清点、独立留出评估和A/B消费者联调。长期目标并未因这一个跨页例通过而完成。
