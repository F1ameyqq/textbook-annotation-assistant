# A03 R9-R1 ownership 修复独立复验

2026-10-18（Asia/Shanghai）。**对 target `bfd7fe896a7eee663ea8e0b6cf967548d8dd8f39` 的 ownership 修复及 D1、standalone、borrow、原 D2 四项有界演示有限 ACCEPTED。** 四组各在全新独立 case 首轮完成，无功能失败/重跑。正式 SQL、Resource、当前包及 ownership 边界另用纯读取规则核对。整个 A03 仍为 REWORK，I01 未释放，不自记 INTEGRATED。

作者原 borrow **FAILED**、D2 **NOT_RUN** 原样保留，与本轮新增复验证据分开。作者首败是捕获底层sqlite3.IntegrityError的驱动预期错误；本次独立驱动在首次运行前已登记正确、具体的事务包装断言，没有修改原失败驱动或再次要求作者修改同一问题。

归档辅助采集器另有固定计数断言失败，保留且未作第二次元数据修正；其限制见末节，不将该采集器记为通过。

## 固定版本与字节保全

| 输入 | 提交或 raw SHA256 |
| --- | --- |
| base | `c83f956c5c29c64ab10735ba11c153201d3f3f4b` |
| 唯一 target | `bfd7fe896a7eee663ea8e0b6cf967548d8dd8f39` |
| 审阅 workflow | `eff3282de913452c0c63dff6f0bde16696a9e715` |
| 审阅交接单 | `254395485491738a0f8921ade760baf5c6740b9ba0a6b615e8eab4b516c00b27` |
| 执行 workflow | `2aabd591695e73ecd4024c95e06fe0b71a2a9267` |
| 执行任务 | `eb375839b834126f8a72be6a60a21d45b00fad83925de0e2d71cd6b0abe80191` |
| 执行报告 | `d4241688c338d988d122d177305b464ad7aa14e8531b0f6589b492f72cdf956e` |
| 作者 manifest | `fa79fc21f550ea5491d2e122fb39b46976f9850666fe503423195ae90cdfd7be` |
| 作者 process-release | `91b63555dcea1c1eff0be18138a510e03e1db4e9c8e91a701db25e42e02bb098` |
| 原 borrow child stderr | `bc895733e5e37d479f5da9c57f73b29f23694a30a5b09e02a833a11cc7436fb5` |

使用命令级 `git -c core.longpaths=true`、raw cat-file/ls-tree核对mode/type/blob、blob SHA1、长度和raw SHA256。491个变化路径（490个manifest条目加自身）吻合，487新增；31,665个旧条目中31,661个原样，仅四份获准产品文件改变。四份workflow原件及12项base引用逐项核对。见 [585项输入索引](../evidence/A03/review/P2-R9-R1-owner-lifecycle/input-index.json)、[完整交付字节核对](../evidence/A03/review/P2-R9-R1-owner-lifecycle/delivery-byte-index.json)。

旧7,383项A03审阅/报告文件共186,511,736字节保持原字节，有序 `[path,size,raw SHA256]` 摘要为 `43da522f7c5df481023e02891354dd098f6b2f4daf6597420c864db7dfdde4f0`，封存前再核对，见 [历史保全](../evidence/A03/review/P2-R9-R1-owner-lifecycle/historical-preservation.json)。未复制旧历史全集、合并调度分支、修改根state或执行工作树。

## 修复静态核对及作者首败分类

两份recovery改动闭合：run_plan显式传递当前owner/generation；publisher对完整pair先用既有_lease验证实例/PID/ACTIVE/owner/generation/时效，复用当前租约；部分参数拒绝。借用分支不claim、不停止外层keeper、不release；standalone分支自行claim且finally仅释放自有租约。原run_plan的keeper/finally保持。

报告读登记、报告快照、POST/Batch落库三个事务均在首个业务写前调用既有 `_lease(..., pending_ok=True)`，第二个事务补齐同一检查。保持原报告上下文pending/hold语义，未给普通写入增加资格；共享claim/OWNER_BUSY、普通pending/hold门禁、durable单次报告读和2秒观察限额不变。legacy分支函数体文本与base相同，仅作静态保全，不宣称动态legacy/兼容套件通过。

| 获准旧文件 | target raw SHA256 |
| --- | --- |
| recovery/__init__.py | `c62a558218e333e212a928a9bf0bb94a79a45e4bb91b08ee5a705e38bc12200d` |
| recovery/native_quality.py | `8038926e976da078625b9b095de40ba2eb994c1e670be3e0769f55629f7af100` |
| native profile.json | `741cadbfaaa622f2e24610026dcbfd6d68fd214dd1e4e1a1fb042df44b97445c` |
| native adoption.json | `2e0efa1e4538ce632b1cf3e5cae70c631ed0bbda7adb1ee22c5905ed5eb0aaac` |

profile仅两项implementation pins改变，adoption仅profile_sha256改变；全部6项schema pins和23项implementation pins与实际raw源核对，无其他字段/版本/依赖改动。详见 [静态差异](../evidence/A03/review/P2-R9-R1-owner-lifecycle/static-review.json)。

作者首败链明确为native_quality:33的唯一约束 `native_report_reads.plan_id` → storage.transaction:160–162 rollback并包装 `RuntimeFailure(STORAGE_TRANSACTION_FAILED)`。原驱动只捕获sqlite3.IntegrityError，故异常继续传播。自有immutable副本确认原borrow最终只有1个report-read、1对POST/Batch、1个effect，失败发生在第二次观察前。原合法借用证明文件未落盘的限制保留，不补造；见 [原失败独立分类](../evidence/A03/review/P2-R9-R1-owner-lifecycle/author-failure-classification.json)。

## 独立驱动、导入及四组首轮

新workspace：`D:/1800/docs/evidence/A03/review/P2-R9-R1-owner-lifecycle/isolation/workspace`；run id：**`review-owner-r1-7270b7d60b49`**。首次启动前无validation/SQLite文件。77项raw种子仅含68个完整产品包文件、原R1/R9/R3三个驱动/helper、5个固定32×32夹具文件及仅作登记摘要的inputs.json；没有复制作者库或validation作为起点。

另新增一份审阅者自己的完整驱动，SHA256=`71357a70360ddd9228ff20fce908c790be7935ebcc8b63b63aad15a84f2805b4`；原失败R1驱动SHA256=`ec8dc7064705c1f4408b212becf8686936dac70d4feca7f4630b17106a119d9f`保持原字节。改动仅为具体异常断言、合法证明提前落盘，以及只读计数/包/目标摘要核对；源及业务输入未改。完整 [驱动登记](../evidence/A03/review/P2-R9-R1-owner-lifecycle/independent-driver.json)、[逐行差异](../evidence/A03/review/P2-R9-R1-owner-lifecycle/independent-driver.diff) 在首轮功能前冻结，四组均使用同一摘要。

驱动正常import冻结R9 execute/restart及R3 setup helper，无AST/exec裁剪或产品monkeypatch；static ast.parse仅检查语法。各级实际__file__/SHA指向该workspace，产品使用target raw字节，未导入作者工作树。固定book/ledger/store/题目标签沿用原合成语言，真实新路径、PRE run、观察、intent/receipt及计划完整四元组新建；不把固定标签称为新UUID。全部78项源/驱动保持字节不变，产生403项新运行文件。

| 独立组 | 父 PID / exit / 实耗 | 实际子进程与结果 |
| --- | --- | --- |
| D1 | 11020 / 0 / 19.282秒 | execute63764/0，restart43756/0；FINISHED、正式报告及重开/旧计划拒绝。 |
| standalone | 54892 / 0 / 17.016秒 | execute59540/0；自行claim/publish/release。 |
| borrow | 63924 / 0 / 16.484秒 | execute38648/0；四项拒绝、合法借用、具体单次读拒绝。 |
| D2 | 65684 / 0 / 19.922秒 | execute60824/90，restart24196/0；真实故障、UNKNOWN、一次ABSENT、旧计划拒绝。 |

父watchdog90秒、direct child45秒，观察2秒及产品lease/PRE窗口原样；无timeout或alive。四组各一次，无功能失败后重跑。精确argv/cwd、输入/源/驱动摘要、PID、raw stdout/stderr、退出均在各runs和新run的processes/process-audit记录中；[单次启动器](../evidence/A03/review/P2-R9-R1-owner-lifecycle/scripts/run_group.py)以先前组成功作依赖，不运行旧R3/R4组、兼容套件或其他故障点。

## 正式SQL、Resource与ownership边界

作者3个最终case双库6份、本轮4个最终case双库8份，以及独立D1/D2执行前4份文件，共18份不同冻结库，用自有副本、stdlib SQLite `mode=ro&immutable=1`、query_only核对；quick_check=ok，源/副本前后SHA相同，副本删除。未连接作者活动库或在审阅读取阶段调用产品API。原执行前双库是顺序文件复制，不宣称跨库原子快照。

| 独立case | runtime raw SHA256 | target raw SHA256 |
| --- | --- | --- |
| D1 | `deb03112b59f774cae9fb12d51841b223ecfd7099741ac43aeea049daf04b9a2` | `9386ab42e03a08c74fd1941e6a4c2b584de26ea5036dc240c81f00f7c1a9050f` |
| standalone | `2efd529832dd5087a5991b66856c4a1354d98a2fbd00edcc3dc7cdcc5c626e4a` | `295056c33a5725e0ed13aba038766bda7a2d8320202b8ec9a6ff456e632a9492` |
| borrow | `3a6672dfc561b98b6889a47ea7c57e24a7ac4e3ffa60c970f7d33bd78f1ce78f` | `558ac5f6d074548df34792358bb2d04d4bb3e5c77ed495dcd0049744e9505378` |
| D2 | `c8a74fc14c9c6354d51f1ee6481394e3a62ee20090dc0fa2d891e61b398b1244` | `198a99697ca35f2d71f4b2945f7c063a6b87cab288410424f73b9812f5a05c1a` |

独立重算全部Artifact内容摘要；SQL artifacts.ref/path、实体和current bundle完整四元组对应。正常三例plan/action/intent/fact、正式receipt和material progress一致，ATTEMPTED/APPLIED、唯一CONSUMED permit、effect=1；PRE真实登记ADMITTED并绑定accepted_plan、五检查及run Resource。POST/Batch各1、report-read=1，报告快照/观察新鲜且与执行读回不同，绑定同一正式receipt/fact/action及目标观察表，内容PENDING、NOT_SUBMITTED、Batch CONTENT_PENDING。

各例完整plan/intent/receipt/fact/POST/Batch、逐实体摘要、SQL查询和事件hash链均在 [正式边界读回](../evidence/A03/review/P2-R9-R1-owner-lifecycle/case-boundaries-review.json)。POST绑定它正式生成时的不可变回执；不会把后续projection中“最新receipt”假定为它的唯一合法依赖。独立正常三例POST/Batch refs均revision1：

| case | POST id / content_hash | Batch id / content_hash |
| --- | --- | --- |
| D1 | `native-post-561e95665a1e42bf979db25f19e00f52` / `a7f974c256249776b92e627f25f8e6a1915435d7181cbf539ffd2f2247bba34a` | `native-batch-4e7c745707794632b80c3899aef6d34f` / `6660c804ef1bf58d246ceb5f31beb731ba7cfe0e3f14d795bc7bece5c6630f20` |
| standalone | `native-post-3be10c7c1daa4062a7871cd6fd935152` / `aa15aa5edb2778db107255133079d635ecb57cdb0e79aab55138c6c8a05bec1b` | `native-batch-124292a21e764cb4b30ee4f4e5f0c7dd` / `aa41398990af05a6219b708dd874c4d97d97a4f89256cbc268b1621a752e6faa` |
| borrow | `native-post-4e4a72b1442841f88b7472d92dc9cced` / `2beb2d932a3c2c62483cfb39868f09d2f5de0c2abd2059d5f6dd4b0f100a0b49` | `native-batch-1b6ade1569384ffe81167d697870646a` / `2691db06a381937a5ea8991af5b55006bacf6d917a929ec4b4bd4640c130d8da` |

D1执行报告阶段generation=1且正常finally释放；重开后经支持入口同计划REPLAY_FORBIDDEN，effect、intent/permit不增。其重复入口自己的claim/release使最终generation=2，不能算成报告额外claim。standalone从新合法完整receipt且report-read=0形成，原owner正常释放后自行claim到generation2；claim-reserved/active/released各增加一次，正式报告读增加1、effects不增。

borrow的仅owner、仅generation、过时generation、他属owner均具体RuntimeFailure/OWNER_GENERATION_STALE拒绝；前后counts/events/bundle/目标raw SHA和观察/效果不变，ACTIVE租约未释放。合法pair发布后generation仍1，无新claim/事件，keeper存活；合法证明**在**限额负控前落盘。第二次读具体断言外层RuntimeFailure、code=STORAGE_TRANSACTION_FAILED、消息为 `UNIQUE constraint failed: native_report_reads.plan_id`、__context__为同原因sqlite3.IntegrityError，非blanket catch。拒绝前后report-read=1、POST/Batch各1、目标观察/效果及raw SHA不变；外层owner/generation/ACTIVE和keeper保留，最终唯一release来自caller cleanup。见 [ownership与单次读证明](../evidence/A03/review/P2-R9-R1-owner-lifecycle/ownership-boundaries-review.json)。

## 原D2：真实exit90、一次完整ABSENT、保留尝试事实

固定单题在AFTER_INTENT_COMMIT真实退出90，marker PID60824与子完成记录相同；落盘action=INTENT、intent=PENDING、fact/receipt为空、permit/effect均0。新进程正常打开后持久化UNKNOWN progress；随后只调用原一次reconcile，max_attempts=1，得到一次RESOLVED_NOT_APPLIED/ABSENT，pending=0，效果始终0。

拒绝不能只由“effect日志为空”推出：新的完整目标观察 `native-observation-ee22cbfecaa14bf880a3a5274ddbb59e` 具有OK/完整scope、精确source/target/snapshot绑定，实际目标questions/frames及效果为空；与原prepared动作比较支持完整ABSENT。终局head `resolution-99737f312d9e468b893250881f81154f`（revision1，hash=`6738e43fcabb3689ada8bbdcdf14cb4f8fb4c22214958da3b431f7ce9b8b3230`）绑定同一plan/action/digest/intent、观察及快照，original_receipt_ref=null。

正式RECOVERY fact `assets/runtime/ec72997ac97d4a73627bd0252eef90b72b5da002c71fa5aa61966d8e8c683bb5.json` 与晚到receipt/material progress一致。尝试事实从原INTENT无结果fact的持久化语义得到 **MAY_HAVE_BEEN_ATTEMPTED**，前后projection及fact完全相同，未改为NOT_ATTEMPTED。通过支持入口再次尝试旧计划，具体REPLAY_FORBIDDEN，effect仍0、intent/permit不增。

原计划正确保留 **INTERRUPTED/cursor0**，action/intent已有NOT_APPLIED终局；不能把“对账已解决”当成旧计划可恢复执行。最终generation3分别来自原执行、正常恢复claim、旧计划拒绝入口claim，均最终释放。D2没有POST/Batch或报告读；没有执行新计划、不足ABSENT或混合尾段。

## 过程限制、封存和未释放范围

作者15个登记进程、原脚本/源快照、实际导入、raw输出、退出/timeout/alive逐项核对。原borrow父66208/child66792 exit1及D2 NOT_RUN保留；五个旧LF→CRLF表示逐文件核实，其余作者源为raw相同；本轮独立产品源全部raw相同。见 [作者过程核对](../evidence/A03/review/P2-R9-R1-owner-lifecycle/author-process-review.json)。

有一次执行后的审阅断言静态纠正：初稿把所有plan都要求FINISHED，D2正确的INTERRUPTED使纯读取检查exit1；纠正仅限该审阅断言及状态显式记录，随后case-boundaries-review-02通过，无产品/功能驱动重跑。首错脚本快照、PID41640、raw日志保留，见 [唯一纠正记录](../evidence/A03/review/P2-R9-R1-owner-lifecycle/metadata-audit-correction.json)。首次运行前的两条缺失静态路径查询只保留渲染转录限制，不伪造PID/raw过程证明。

额外归档采集脚本release-review-01（PID61204/exit1）假定六份退出imports文件，实际只有五份：D2真正os._exit90不执行finally，其实际PID/导入路径与SHA已在故障前cases/D2/before-run.json保留，PID与marker相同。按一次元数据纠正上限，**该采集脚本未再修改或运行，不把其失败记为通过**，也不补造退出日志。最终manifest直接覆盖现存目录全部原字节，释放证明直接依据原登记/完成记录，见 [采集限制原件](../evidence/A03/review/P2-R9-R1-owner-lifecycle/archive-collector-limitation.json)。

11个登记审阅检查子进程（含上述两个辅助失败）、16个功能/观察子进程（一个预期exit90）、5个Git子进程和1个封存包装均wait/退出，无OS/profile全局扫描。见 [进程释放证明](../evidence/A03/review/P2-R9-R1-owner-lifecycle/process-release.json)、[最终字节核对](../evidence/A03/review/P2-R9-R1-owner-lifecycle/final-verification.json)、[完整SHA256清单](../evidence/A03/review/P2-R9-R1-owner-lifecycle/sha256-manifest.json)。清单覆盖本报告、585项输入、403项新运行文件、78项源/驱动及全部本轮记录，仅排除自身，封存后再读每项body和目录集合核对。不会把辅助采集器失败掩盖成全检查exit0。

本结论只接受四项有限ownership行为。多动作/混合尾段、充分/不足ABSENT完整矩阵、新检查/新计划、scope/书隔离完整矩阵、竞争者/其他崩溃点、合格清hold/不同hold替换、版本/归档/真实来源/S01及报告/分母/次数等原P2缺口继续保留；legacy仅静态保全。原R3 N7 FAILED及其分类不变，B确认/真实平台/OCR内容等未验收，整个A03/I01不放行。

只新增获准R1审阅报告/目录，保留当前model/thinking；无子智能体、平台/浏览器/profile/凭据/付费模型、安装、推送、A05题22或书级送审/B联系。字段重置始终 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`，不复跑、变体、委派或建议重测。
