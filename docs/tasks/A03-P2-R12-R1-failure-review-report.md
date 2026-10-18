# A03 P2-R12-R1 冻结失败及 UNKNOWN 引用链复核

2026-10-18（Asia/Shanghai）。结论：**失败及范围确认**。冻结库和原始栈共同确认：U1实际提交了UNKNOWN action fact及一次部分效果，但在正式receipt追加校验时因issue引用无归属而失败；没有完成合法UNKNOWN建立。当前候选只隔离了后面的旧POST策略，未闭合receipt→issue→native/legacy语义校验→progress→正式独立POST整条链。

本轮未导入或调用产品，未运行L1/U1–U5或作者run/archive。仅核查raw Git、AST/JSON，查询12份自有immutable数据库副本。**A03保持REWORK；不是功能ACCEPTED或INTEGRATED，I01未释放。**

## 固定身份、差异及来源边界

- 本轮workflow：`4abf5cc98290511fd4cd1112bd527c382ba09d76`；交接单raw SHA256：`037a88207fd595c8b34de2a47a6294775e344e8b10299375bda9f0baa2855484`。
- 唯一冻结交付：`6affc61d2ab0b1f0d96bb2497c5ae969ebaf1df2`。
- 功能开始前候选：`7694490ef25539d131b863bdcb2b21531c69dfae`；base：`394fe51f5ed14c5ed312073a20faac0f5cbb9990`。两层直接父子关系均核对；候选全部已有条目在交付中保持原样。
- 原修复workflow：`05ba526cbd8575edc778016cf25cee13661a65c6`；原任务SHA256：`ec269e977ed67276e5b4d1901c32c28acd75ba44870094fa0eb5fecf0cdc0076`，以冻结来源和交接单引用，不重跑原任务。

[raw输入索引](../evidence/A03/review/P2-R12-R1-failure/input-index.json)记录399份必要导出；[交付字节复核](../evidence/A03/review/P2-R12-R1-failure/delivery-byte-review.json)确认33028个受保护旧mode/type/blob条目未变、4个既有文件修改、320个新增文件及323项manifest成员加自身。没有复制历史大包或使用作者数据库作为运行种子。

| 冻结依据 | raw SHA256 |
|---|---|
| 作者报告 | `457d0f85e491ae9cefa757475918c6766cd527179b99aa3b07de06611db5e133` |
| 作者manifest | `b280ef782ee85f2c7f92485debc316a6bfae0902b078894e555df59afe904867` |
| 历史进程释放证明 | `6dd2da06a5212db39eaac95437dea5f44bc1e07072bbcb8a2ddc22f6cf1eced4` |
| failure-summary | `0c2050da2041d150bbdd871dc4521f322566d0154272f942f2609ff315ab2704` |
| U1-execute原始stderr | `1ccb41363eafc7980a8f602e084a4fb97519506b138ad0006cb495c859eb6d74` |

四文件边界成立：storage基类新增默认True的`_project_unknown_diagnostic_post`并扩展旧`if issues`条件；native子类覆盖为False；profile只修改这两项implementation pins；adoption只同步profile摘要。其余schema、oracle、verifier、发布器和历史证据未变。AST归一化去掉新增策略条件后，`_project_plan_locked`与base完全相同，UNKNOWN issue构造亦相同。

109项`examples/.../inputs.json`来自执行checkout的read_bytes，不能统称raw Git摘要。104项raw与checkout相同；以下5项只有raw LF与checkout CRLF的差异，已分别记录原始长度、raw SHA及checkout SHA：annotation/__init__.py、contracts/__main__.py、contracts/cli.py、contracts/integrity.py、contracts/models.py。129条实际导入记录按checkout摘要核对，并绑定到对应raw blob，未改旧索引。将来搬运时须明确采用原checkout表示或重新冻结新输入身份，不能沿用109项原摘要声称覆盖不同字节；本轮未为换行启动功能复现。

## 独立SQL与阶段原件

12份阶段二进制由target raw Git导出，先匹配capture摘要，再另写到本轮`databases/`目录的12个自有副本；只对这些副本使用`mode=ro&immutable=1`、query_only及SELECT/只读PRAGMA。全部quick_check为ok，schema、application_id/user_version、全表行集与冻结SQL记录一致；查询前后原导出和副本SHA不变。615项独立字节、事件链、登记文件、正式artifact/Resource及状态核对通过，见[完整数据库复核](../evidence/A03/review/P2-R12-R1-failure/database-review.json)。没有连接作者原件、活动库或runtime API。

| 场景/阶段 | runtime SHA256 | target SHA256 |
|---|---|---|
| L1 before-build | `7da87a9adc08cda6b6dcb90a7173850ee19677df83a6384dc1f4a3e4f06ec49f` | `f175ed441f93fcae63dffd2e1cc881c48c4aa728d15cbb0f670b2c7bc014794a` |
| L1 unknown-established | `e84cf5b7c2252c54901e4641c3557ac1c0bb5a82745e3e96aa6eee1b387dbf00` | `5864b98e2ecd801853f876542acff22ff90e696cf6d3c284af363718e9b493f4` |
| L1 after-release | `dfe53879c78dddd1f8da48ab87c19068241f2801c99203602d568e3f2e9e65d8` | `5864b98e2ecd801853f876542acff22ff90e696cf6d3c284af363718e9b493f4` |
| U1 before-build | `32ee5de524234534620a09e021a12a0a164338bd924607bc916f1869d8c5b76b` | `da7013796517d8a428b4964ed064ca256ba71752d05a00183fcf6b617e7e33cb` |
| U1 first-failure | `c3c996e147c81c23dbe30b524c7e8c8e34743fa08ebdf3805fa7ab35ba09fdb7` | `7d95cdce93e2418554f9482d74f85fc97459131fc983cab5796a4c5c6852ff3d` |
| U1 after-release | `9285873dbfeea889d47189fdb0e56862e67a30efbfe5e532f3de865b34e07c15` | `7d95cdce93e2418554f9482d74f85fc97459131fc983cab5796a4c5c6852ff3d` |

原capture逐库记录采集时刻、writer PID、keeper_alive、sidecar及source_after_copy。before-build/中间阶段仍有自有keeper的事实保留，after-release已释放；两个库顺序采集，不能称跨库原子快照。本轮副本为冻结后只读审计，不是重建原现场。

| 实际持久化项目 | L1 | U1 |
|---|---|---|
| before-build | action已预留，效果0 | action已预留，效果0 |
| 中间阶段 | UNKNOWN fact、PENDING intent、CONSUMED permit、INTERRUPTED plan | 相同状态，fact已提交 |
| 目标业务状态 | 效果行1、题1、框1；计划预期框2 | 效果行1、题1、框1；计划预期框2 |
| 正式产物 | receipt1、progress1、诊断POST1、Batch0；issue声明与receipt引用相符 | receipt0、progress0、POST0、Batch0；intent.receipt为NULL |
| native_report_reads | legacy库不存在该表，不能填作native计数0 | 表存在且行数0 |
| recovery calls/attempts/resolutions | 均0 | 均0，U1恢复未启动 |
| 释放后 | owner/PID为空、lease0、phase RELEASED；pending1、paused=true | 相同；UNKNOWN、permit、fact、目标状态未被清理 |

两例fact的attempt_fact均为MAY_HAVE_BEEN_ATTEMPTED、replay_allowed=false。DISPATCH_STARTED、消费permit、ACTION_RESULT_COMMITTED事件及target效果互相对应；没有将部分效果当成未调用。释放前后actions/intents/permits/plans与目标全表保持原状态，事件链正常追加释放记录。

U1正式plan为`plan-r12-r1-U1`，content_hash=`a878bf6b5111306ea82316f6e30d233fd579728255c8c30b8ef48ac7c0469a7e`；intent为`writeintent-289104bfd82f478f88818c7d383b3d84`，content_hash=`654004198bec94cdbcb11adb07ab7a9e59e3b1b7aa650e80b23f27034820c739`。UNKNOWN fact Resource为`assets/runtime/1c539a7e21cad8405cbf61cb958992af46cdbb24f618bda95f439d9c5f62e3f3.json`，SHA同文件名。独立规范化fact后计算出的issue ID为`issue-save-unknown-1c539a7e21cad8405cbf61cb958992af`，与真实异常完全相同，但已存正式CheckReport中没有此issue声明。

L1 receipt为`executionreceipt-6e0564aae3944fc2bb0e8cecf9662130` / `164a4211313e59a199c883cac67fb677806d0748556907b7449939391d472fe4`；progress为`executionprogress-a858a62e5cd34ccda4db1d2619997a0d` / `c6f8999813fb1aea8e9c2aeb9a28434ee21b0f3f958dda5613ebd9f75c769287`；诊断POST为`checkreport-952acd8fe6c348f491a8c6b35b7fb1bb` / `7568f1a8ba3fe4e8d0cbe3dfa43893f973ea4a932e7cd97889c6814003006739`。均revision1，完整四元组及原实体见数据库复核。这里只确认冻结的有限legacy对照现场，不外推全部legacy功能通过。

## 首错及整条引用链

[按类源码和合同复核](../evidence/A03/review/P2-R12-R1-failure/reference-chain-review.json)保留24个明确类/模块作用域函数、原文、行号和摘要；不是把模块级同名包装当作RuntimeStore入口。414项源码、pin、历史进程及实际导入核对无不一致，见[进程和来源复核](../evidence/A03/review/P2-R12-R1-failure/process-source-review.json)。

1. `RuntimeStore.commit_action_result`（storage/__init__.py:693–740）在其事务中持久化UNKNOWN fact、action/intent/plan及事件，:737才调用project_plan。冻结库证明前一事务的fact确实留存；不能因后一异常推断全部回滚。
2. `_project_plan_locked`（:764–830）从UNKNOWN facts局部生成SAVE_UNKNOWN issue对象，并把其ID写入receipt.unresolved_issue_ids；:792先`_append(receipt)`，:794才到报告策略条件，progress在更后面。此时issue只在局部变量中，没有已注册正式所有者。
3. `NativeRuntimeStore._append`（native.py:295–302）先验证合并后的包；`RuntimeStore._validate:109–111`的bridge参数求值，经native.bridge_for:239–240、NativeRegistry.context:56–59、native `_issue_context:111–118`进入`_validate_value:134–156`。
4. native语义校验调用`recovery._legacy_projection`（contracts/recovery.py:724–800）。该私有C01视图保留ExecutionReceipt和unresolved_issue_ids，移除新恢复产物、native POST（:733–737），并strip action_fact_refs、attempt等native细节（:753–759）。原native历史本身不被改写，但C01视图中没有承载该新issue的声明。
5. `validation.validate_bundle`（contracts/validation.py:640–690）在:661只从CheckReport.payload.issues收集all_issues；:680–682验证receipt.unresolved_issue_ids的子集；subset:40–43产生真实的MISSING_REFERENCE。实际路径为`$.artifacts[10].payload.unresolved_issue_ids[0]`，不是本轮猜测的外层错误。
6. 此失败早于policy hook、progress及显式独立POST发布。当前native POST.issues为字符串数组；C01 Issue则是含issue_id/code/scope/evidence/blocks/strategy等字段的对象，不能把native报告中的字符串当作完整声明。native桥也明确排除POST，故把issue归属拖到后续报告、或一次批量拼receipt+POST都不是已经证明的修复。

正式发布器`runtime/recovery/native_quality.py:12–85`先取得/投影合法receipt，再消耗受控报告读回并生成带report_snapshot_ref、report_observation、action_bindings的native POST/Batch；native `_reports:211–271`再校验这些精确绑定。若receipt必须等待该后续报告才有issue所有者，而发布器又必须先验证receipt，就会形成循环依赖。progress只引用fact/receipt，不是现有独立Issue声明所有者；不能用它掩盖缺口。

两个缺陷应分别记录：上一轮确认的旧POST形状与native schema冲突，成立于已经通过receipt追加并进入issues/报告分支时；本次实际失败是更早的receipt issue归属缺口。contracts/recovery.py、validation.py、native合同/_closure及native_quality原字节在base与target相同；UNKNOWN issue构造和receipt先追加顺序也未变。因此有证据确认这条更早路径原已存在，**不能声称由此次四文件策略改动新引入**；本轮没有在base动态复现或证明唯一剩余故障。

## 一个连贯、需调度确认的最小修复边界

只改“是否生成旧POST”的开关不够。建议调度先明确一个native内部语义决定：**允许经过完整fact/Resource/plan/action/intent验证的原UNKNOWN fact，作为确定性SAVE_UNKNOWN issue的派生所有者；issue归属必须能在receipt验证之前独立重建，且不依赖未来报告。** 当前合同只给出receipt ID数组和C01 CheckReport声明路径，没有把这种派生所有权定义完整；不能把它包装成无需审查的两行实现修复。本报告提出该单一建议，不采纳或实现。

若该规则获调度明确授权，建议一个整体修复单覆盖以下数据流，而非逐个追下一异常：

| 责任/位置 | 受限改动与顺序要求 |
|---|---|
| 纯Issue派生与原生闭包；`contracts/recovery.py`、`contracts/a03_native/__init__.py` | 统一确定性派生规则。按每份receipt的原action_fact_refs读取真实不可变UNKNOWN facts，核对资源SHA、plan/action/digest/intent、scope/source、证据和原尝试事实，独立重建完整Issue绑定。receipt.unresolved_issue_ids必须与其应有绑定精确一致，缺失、多出、外scope或仅自报ID均拒绝。纯合同逻辑不能反向依赖runtime或报告发布器。 |
| receipt投影；`runtime/storage/__init__.py` | 使用同一规则生成原ID和完整绑定，不把issue临时藏在未来POST内。原fact/事件已经提交时如实保留；receipt通过完整native闭包后登记，再生成精确引用fact/receipt的progress。保留UNKNOWN、PENDING/paused、消费permit、原attempt及不可重放。不要提前写一个尚不合法的receipt来绕过校验。 |
| 私有native→C01语义适配；`contracts/recovery.py::_legacy_projection`与`contracts/validation.py`的内部验证入口 | 在strip前完成native归属证明，把经严格核验的派生Issue声明带入私有C01检查上下文，与原CheckReport声明共同验证ID；原receipt ID仍保留，不能删除/清空以过关。不得接受任意调用者提供的ID白名单。C01公开默认路径仍只按既有声明规则验证，不改变legacy合同或放宽全局subset校验。接口与证明载体需在该修复单中明文定义。 |
| 历史与终局消费 | 归属以每份历史receipt自己的原fact refs为依据，不按当前action.fact或最新有效结论取代。后续reconcile产生late fact/新receipt时，原UNKNOWN issue、原receipt、intent、Resource及事件历史仍可独立验证；不能因新结果已解决就删除旧issue或让旧receipt失效。 |
| 报告职责；现有native策略和`native_quality.py` | 保持native不构造旧诊断POST，现有native子类hook可保留；正式POST只在明确发布入口取得合法、独立、新鲜观察后生成，继续绑定action/fact/intent/resolution和报告snapshot。不得为修receipt伪造report_observation、隐式消耗report-read预算，或用执行内存读回冒充独立报告观察。发布器本身不应先扩大修改来掩盖引用缺口。 |

以上建议主要涉及4个实现文件：storage/__init__.py、contracts/recovery.py、contracts/a03_native/__init__.py、contracts/validation.py；native.py已存在的False策略不必为此再改。四个实现均被profile绑定，后续固定提交需由责任人同步对应implementation pins和adoption.profile_sha256。若增加纯内部helper文件，也须纳入明确源码/pin闭包，不能扩大为未登记依赖。

该建议可保持现有序列化schema和公共API外形，但**改变了native issue所有权及桥接证明语义**，须调度明确审查其A内部合同边界，不能由本次诊断自行批准，更不代表B已确认。如果调度要求每个issue必须有独立、持久化、正式产物所有者，则应另定真正的诊断产物/类型及引用合同，再评估schema/registry/API/pins和版本影响；不能伪装成PRE/TARGET检查、塞入未经独立观察的POST，或静默让C01接受悬空引用。此替代方案超出上述最小派生归属建议，需另行界定。

后续验证要求应在新固定提交任务中覆盖原L1有限legacy默认行为、U1–U5正常建立及恢复、receipt/progress完整引用闭包、历史UNKNOWN保留、终局late fact消费、明确独立POST与读回预算，以及真实异常下的事务/文件/双库后果。原要求的四阶段二进制必须在现场保存，不能靠最终库重建。这里仅列原范围及受影响合同的验证要求，不执行、不委派、不自行发起下一轮；其他A03原矩阵、产品集成和B兼容性仍分别未完成。

## 历史进程、首错和本轮释放

23条作者历史Popen登记、原始stdout/stderr和completion逐项对应；U1-execute PID1944及watchdog PID34388实际exit1，其余exit0，无timeout。登记原expected_exit仍为0，没有把失败预期改写成成功。它们是历史wait证明，不是本轮当前PID扫描。129条被动导入记录及脚本摘要与109项checkout索引及raw/EOL边界吻合。L1的作者PASS只作有限现场说明；U1恢复与U2–U5均未运行。

作者将ledger files.path误按cwd解析的FileNotFoundError及一次元数据纠正原件均保留，没有视作产品重跑。另，本轮一次只读元数据清单命令发生PowerShell foreach管道ParserError，未运行SQL或产品；原工具错误和无PID/无分离流的边界见[first-tool-error](../evidence/A03/review/P2-R12-R1-failure/first-tool-error.json)。按授权仅纠正一次该只读命令，随后freeze/SQL/AST与来源审计均各运行一遍、exit0，无功能重跑或额外纠正。

本轮新静态脚本均先严格UTF-8解码和compile，再执行标准库Git/JSON/AST或自有immutable SQL审计；未执行产品、作者脚本或AST裁剪代码。实际新子进程的登记、原始流和wait保存在[本轮释放证明](../evidence/A03/review/P2-R12-R1-failure/process-release.json)。[Manifest](../evidence/A03/review/P2-R12-R1-failure/sha256-manifest.json)覆盖本报告、完整新脚本、必要raw来源、12份导出原件及12份自有审计副本、查询结果和错误/释放记录，仅排除自身。

未改产品、schema/pins、作者/旧证据、协调state或共享文档，未推送、联网、操作平台/profile/凭据、安装、OCR/付费模型、联系B或A05题22。用户model/thinking保持原设置，无委派。字段重置始终`NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`，不运行、不变体、不委派、不建议重测。

最终仅交付**失败及范围确认**。A03保持REWORK，I01及本地产品集成未释放；R11有限结论与其F2/F3作者历史原件缺口保持原记录。由调度核实诊断和内部合同选择后，决定是否另发一次有界修复。
