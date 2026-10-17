# A03 P2-R6 单一混合环控制独立复核

2026-10-17，Asia/Shanghai。**ACCEPTED_STATIC_LIMITED（仅R6修正后的单一混合环控制证明）**。先独立重算全部差量、数据摘要、内部头和消费者声明，没有发现本轮范围内新的输入残余；随后只运行一次冻结只读完整入口，在MIXED_DAG层得到MIXED_CYCLE，声明故障为空，五条环边实际存在。此结论关闭R5该控制的输入证明残余，不改写旧失败记录，不等于A03产品恢复或I01通过。

## 冻结输入与保全

| 项目 | 精确版本／SHA256 |
| --- | --- |
| 审阅workflow | `fbf7792b20f212f1d3b2a329cddba502fcfdc1b4` |
| 复验任务SHA256 | `47b7a464ab95689d9bc7fb91fa0d498c4079ef072c500c968b58e9713304d5d7` |
| base | `323013c4f0dbae75368e56db60147a8057368d1f` |
| target | `81d3ec7e42e0a1a76ad744bf59536fc5f68adee4` |
| 执行workflow | `77d3e123ab7247eae6f81f7acd669e3a69c934a0` |
| 执行任务SHA256 | `97211bd4dd86097ae2ed08c19f38f208c4a790432fe42875bb0d7901fff1f0cd` |
| 执行报告SHA256 | `efe831c7f11e7251e1f0cb9b78f66b72baa0ae7b9f630d1718bfe3aa9518e400` |
| 作者清单SHA256 | `7f8f17697370b0398af58d178bc0af18f6d9cc1e640c73ae7949907ca95ef3e8` |

按精确workflow raw Git先读[复验任务](../evidence/A03/review/P2-R6-mixed-control/input/workflow/docs/tasks/A03-P2-R6-mixed-control-review-handoff.md)、R6执行范围、R5调度决定/独立报告及前检。AGENTS/coordination、架构与公共合同沿用冻结字节。保留用户当前思考设置，未改档、委派或合浮动主树；根工作区原有coordination-state.json修改和mermaid-diagram.png保持他人所有，未读取或写入其内容。

[交付字节索引](../evidence/A03/review/P2-R6-mixed-control/delivery-byte-index.json)独立核对92清单项及清单自身共93个新增raw Git blob，长度/SHA1/SHA256一致；28,318旧路径的mode/type/blob不变，新增只在执行任务范围。46份raw Git pins及副本逐项核对。执行工作树干净、完成与七个退出记录来自冻结交付/前检，不冒充当前OS或profile扫描。

[输入索引](../evidence/A03/review/P2-R6-mixed-control/input-index.json)只隔离123份必要文件到本轮input目录；包括候选、R5 repair-01原件、固定加载源码/Schema、fallback Resources及失败留痕。没有历史证据全集、旧逐文件保全清单或产品源码副本。执行工作树未作写入。

## 先行独立数据核对

审阅者自己的stdlib JSON读取脚本先运行，没有导入R5/R3/R2、作者data_check/precheck/prepare或产品。作者precheck原件保留供冻结entry的输入guard使用，但其中true字段不作为独立依据。完整变更表、资源和消费者数据记录在[独立先行审计](../evidence/A03/review/P2-R6-mixed-control/independent-data-audit.json)。

| 候选 | SHA256 |
| --- | --- |
| bundle | `6a39c873de02dab04d3efd831cb1032b87ba8323c35bfd2a7a31f0b2e48dabd2` |
| prefix Resource | `d946006863bac1a8862ba2b3652f0b62e0914c36625541d463c342721e508e5f` |
| case | `2763198f4b68b9e636b00780cf5a28b8a89ac0dc117269c43fc6efc731bccab2` |

相对原R5 repair-01，逐叶比较得到**恰好15处prefix变化**：

- 第8事件payload.initial_event_head.hash：旧 `87f8f86767e923c8fe7eb351c45eb57df3d6d4ebfdf855249fc7f5be025bbf84` 改为实际第7事件hash `28ef8b468d67a04e9ba75fe3e41a45fb96f280deb95ddcef4cdc2097d6c195f9`。
- 第8—14事件的7个event_hash、第9—14事件的6个previous_hash随之更新。
- prefix.expected_book_head.hash更新1处。

bundle恰有 **`/evidence/1/resource/sha256`** 一处变化。16个Artifact的全部内容、内容hash和input_refs完全不变；两份JSON中所有ArtifactRef均未改变；return Resource逐字节相同；accepted_anchor仍为第5事件，值完全不变。未删UNKNOWN/登记历史、证据、普通ref、frame或声明，未更改书籍/scope/版本。

独立读取18个Resource并核对实际raw SHA；重算16个Artifact canonical内容hash及全部普通exact refs。两份prefix均从sequence1/zero前驱核对至expected head，逐条校验event_hash/previous_hash、journal/target key、accepted anchor；所有initial_event_head均与实际前驱一致。旧fact/basis仍引用原prefix，其initial/expected head单独核对相符，没有把新prefix的变化错误传进旧历史。

正式证据ID列表按固定Schema的类型/字段路径定位，唯一ID表与递归Resource展开分开处理。每个实际Artifact/frame数据消费者各用自己的found、input_refs、book/scope；typed prefix让frame使用自己的明确子上下文，外层仍只消费其元数据引用。44次独立消费者数据核对无声明或book/scope故障，两份prefix的全部frame均覆盖。这是数据检查次数，不是44次runtime或Package调用，也不声称该脚本替代完整Schema/业务校验器。

先行检查独立从Source正式字段、EvidenceRecord及两个Resource构造五边，再核对冻结entry使用的ring_edges恰好相同：

`Source A → E:proof-r5-mixed-cycle → cycle-prefix Resource → frame /F:4 → cycle-return Resource → 同Source A`。

Source自己的subject plan声明与frame自己的返回Source四元组声明均保留，同书同scope；return Resource与Source身份不变。数据审计完成时Package调用为0，之后才启动唯一只读入口。

## 冻结代码及一次实际入口

先读entry.py、files.py以及固定加载方式。entry只校对冻结pins、传入候选并作只读trace；--readonly不写entry-invocation或entry-result。files.py的Git/保全函数只是定义，没有调用。R5/R3/R2、Schema、预期和加载语义均未修改。

[实际源码pins](../evidence/A03/review/P2-R6-mixed-control/actual-source-pins.json)在运行前独立核对10份加载输入，其中包括：

| 加载源码 | SHA256 |
| --- | --- |
| 冻结R6 entry.py | `720bf543e5c83565d1c8ea4df76072902db43420aa5306ed19c2989a49990137` |
| R5 registration.py | `3f0281c5cfc9aeec99b11fa2de30ba40e9984a19dd0e651b747d99ebe29772ba` |
| R5 load_static.py | `734b8760b58f7778f4bd32608b77fc87f95a31c027ce457408d5fbdcf8166098` |
| R3 closure.py | `ff650507bca971f8c9418a09e6e4f8df7c7691016841ffe7bd15ff66382579a5` |
| R2 check.py | `7bf3ea27424f7afaf3d3b264d2ab3d0bfa0fdc8bba1c178e6f488bef09e6257b` |
| R2 schema_check.py | `9630d7e2e0d3700080f7a97a9c883877acf27929be82a41ed5a8f041240ccf7c` |
| 固定oracle_verifier.py依赖 | `6667659ccc71cf1c0769d2ca7c684021140046a71a2ca73e40699aa354afac2d` |

不重定向或改写冻结源码，直接在raw Git隔离输入上执行entry.py --readonly。原加载器仍仅重定向未使用EVID并移除初始化mkdir，R3 Package AST保持此前指纹。审阅者另用非修改式sys.setprofile观察调用，与冻结driver自身line trace同时存在，不改变参数、返回、异常或判定。

| 实际观测 | 独立结果 |
| --- | --- |
| R5 / R3 / R2 validate调用 | 各1；审阅者profile与冻结driver测量一致 |
| R3 entry counter | 0→1，增量1 |
| 到达层／拒绝 | MIXED_DAG／MIXED_CYCLE |
| 错误路径 | `A:760b541bec881e9d98abb75f38bc7e34a75d2ed047edbc8ac657091c70fdc320` |
| consumer_failures | [] |
| 实际消费者／None-book消费者 | 44／0 |
| 实际图节点／五条环边 | 64／全部实际存在 |
| full_entry_returned | false；预期在环检查拒绝 |

[一次原始stdout](../evidence/A03/review/P2-R6-mixed-control/runs/entry-readonly-01/stdout.log)、stderr、父进程退出及[独立计数](../evidence/A03/review/P2-R6-mixed-control/independent-call-counts.json)完整保留；[结果汇总](../evidence/A03/review/P2-R6-mixed-control/independent-entry-result.json)将独立数据、实际五边与计数绑定同一候选SHA。入口进程退出0表示指定层拒绝/计数匹配，结论还依赖先行独立数据证明，不能只以同码或退出0认定干净控制。

本轮据此接受修正后的单一混合环控制证明：在指定静态检查范围内，没有发现与目标环无关的输入残余。控制包本身仍应被拒绝，这不是把循环包接纳为可执行业务输入，也不是全模型或native历史正确性证明。没有使用helper代替完整入口。

## 作者首个SyntaxError与唯一调用核对

原entry-01注册脚本SHA为 `f15223c2543d6b6ba518c43302a0329e1fc24231959cb6a926d4c67e055965e3`，原脚本、stdout/stderr、PID/退出1保持。[静态失败审计](../evidence/A03/review/P2-R6-mixed-control/failed-driver-static-audit.json)只对源码作AST解析，独立得到第25行SyntaxError；差异仅为 `__code__and` 与 `__code__ and` 之间的一个分隔空格。当前冻结driver可解析。未执行失败驱动。

Python在执行模块前解析整文件，故这个错误在imports、invocation guard、Package构造/调用之前退出；该进程Package调用为0，空stdout和原SyntaxError stderr/退出1与此一致。作者之后syntax-01只作AST核对，entry-02才实际调用一次；冻结entry-result中的三个入口测量各1、counter增量1，和独立运行观测相符。没有把失败启动算为另一次Package运行，也没有把它隐藏成语义通过或修包重试。

七条作者运行记录原样保留，只有entry-01退出1，其余退出0；未重跑原失败。独立审阅三条登记运行依次为raw Git隔离、独立数据检查、一次入口，均wait退出0、未超时。每条启动前保存脚本/SHA、argv/cwd/限时并持久打开原始stdout/stderr，随后记录PID和退出/alive。PYTHONPATH移除，-X utf8 -B/PYTHONDONTWRITEBYTECODE=1；没有后台worker或native session。[释放记录](../evidence/A03/review/P2-R6-mixed-control/process-release.json)来自自有父进程wait/return，未扫描profile、全系统进程或终止他人任务。

## 冻结、复现及接受范围

只读复现入口如下，本轮封存不再执行Package：

```powershell
python -X utf8 -B D:/1800/docs/evidence/A03/review/P2-R6-mixed-control/input/checkout/examples/a03/P2-R6-mixed-control/entry.py --readonly

# 仅核对归档字节及已有记录，不运行校验器
python -X utf8 -B D:/1800/docs/evidence/A03/review/P2-R6-mixed-control/scripts/archive.py
```

只新增本报告及本轮审阅目录；123份隔离输入和3,108份旧审阅文件终检字节不变。完整[SHA256清单](../evidence/A03/review/P2-R6-mixed-control/sha256-manifest.json)覆盖必要输入、源码pins、独立审计、原始流/退出和报告，仅排除清单自身；[终检记录](../evidence/A03/review/P2-R6-mixed-control/final-verification.json)列确切版本与计数。旧R5首版/repair-01及历轮失败保留，不追溯改写为通过；未改state、提交、推送、集成或联系执行者/B/其他任务。

R5六项有限静态接受、R4有限设计及既有R3/SESSION-02/CONVERSION-07结论保持，均未重复执行。未运行作者prepare/precheck/data_check/freeze、六个已接受场景、旧36矩阵、session/conversion/oracle比较、产品/planner/SQLite/native/PRE ABI、网络/浏览器/平台/profile/凭据/OCR/模型/付费API或安装。固定oracle模块仅作静态依赖加载，采用未获批准。

A03持久恢复功能、R17真实调用链、产品ABI/原生资格、跨侧采用与I01均不在本轮接受范围。字段重置专项保持 **NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION**，未复跑、变形、委派或建议重测。单一控制证明到此冻结结束，不自行开始下一阶段。
