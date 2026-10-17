# A03 P2-R1 合同补充提案独立静态审阅

日期：2026-10-17（Asia/Shanghai）。结论：**REWORK**。按本次xhigh续派做一次有界静态审阅；未派发子智能体或其他对话。

新版本表达方向可以供调度采用，但当前候选仍缺跨scope消费者闭合、session/CAS一致性、预算/锁与接纳版本门裁定，以及初始PRE/转换的完整边界。独立新增三个静态诊断值证实检查器覆盖缺口。**不将本提案记为合同批准或功能接受，不授权实现，不释放I01。** P1设计接受及原P2 REWORK等历史结论保持。

## 1. 精确版本和独立输入

| 项目 | 固定值 |
|---|---|
| 本次workflow | `c135542791cb9172dd3163bf593273814a556968` |
| handoff SHA256 | `d0ef157bcb1dfc828db30682694b83c3e418e427eeacaea25720f29b2e40585f` |
| 被验提案 | `7fdbde8f16569fd3bc399013115e13269d5d33fa` |
| base | `c30526958e313141bf64152627591b0907b04aa8` |
| 唯一候选 | `examples/a03/P2-R1-proposal/candidate-v2/` |
| 执行报告 SHA256 | `0f70c125dbbfa2f4897a43cef9762e9aef6bfcc65d8708ca50d9b11813fc4cf4` |
| 作者清单 SHA256 | `2eea068aba8b1e678cc8e8984165cd0025ac8a21f6cfdfebc439aeb08d2010ab` |
| 候选 API supplement SHA256 | `91bc8a911b8e72906c0b9e941d90ec2f46698cdb8e63fc3e9521f4555b7b0239` |
| candidate-v2 profile SHA256 | `a7ede7800a50bf4ff151a53eafe7f7c9971cb85cb69a862271547a108cd3425c` |

只读固定workflow的 [handoff](../evidence/A03/review/P2-R1-proposal/input/workflow/docs/tasks/A03-P2-R1-proposal-review-handoff.md)、[任务](../evidence/A03/review/P2-R1-proposal/input/workflow/docs/tasks/A03-P2-R1-amendment-proposal.md)、[预检](../evidence/A03/review/P2-R1-proposal/input/workflow/docs/evidence/coordinator/heartbeat-20261017-0619/A03-proposal-delivery-preflight.json)及规则。已独立核对501项raw Git长度/SHA256，27,168个旧Git路径/blob未改，502新增均在授权三处。[字节索引](../evidence/A03/review/P2-R1-proposal/delivery-byte-index.json)保留这些事实，不复制全部历史树。

[输入索引](../evidence/A03/review/P2-R1-proposal/input-index.json)隔离269份必要输入，当前candidate-v2为214文件；另含静态检查器、生成器源文件（未运行）、显式负值/必要记录、冻结Schema/API和workflow文件。未导出或运行产品Python模块；旧P2 storage仅以精确base读取两个函数形成文本诊断，没有import或打开DB。根下早期草稿不参与选型或覆盖统计。

新profile=`a03-p2-r1-amendment-1-PROPOSAL`，exchange=`a03-exchange-2-proposal`，新Artifact=`1.2.0-a03-amendment-proposal`。16项pin包含8份新Schema、旧七Schema与旧API；完整集合和API supplement字节均匹配，旧原件逐字节不变。profile的UNIMPLEMENTED/implementation_authorized=false真实保留。

## 2. 实际静态检查与最小反例

读完475行检查器后，仅运行其stdlib格式/摘要/引用逻辑，将EVIDENCE重定向到本轮新目录，未改候选或检查器原件。检查器没有产品、数据库、网络或原生会话导入。作者32项结果可复现：13项静态PASS、17项预期拒绝、2项旧R17等式逻辑见证，**不是32项功能通过**。完整命令、原始流与退出0见 [static-command](../evidence/A03/review/P2-R1-proposal/static-command/completion.json) 和 [复现结果](../evidence/A03/review/P2-R1-proposal/author-reproduction/static-check-result.json)。有限Schema解释器不构成完整JSON Schema标准认证。

独立代码另外重算两前缀共37条事件的canonical hash/前驱/序号/头，subject接受序号分别3、8，真实genesis及前计划保留。两个包的Artifact与frame正例都只有synthetic-scope，不能充当跨scope正例。两个报告值包的Artifact摘要与head-before/head-after原字节一致；晚到receipt有1个null原receipt头，另一包有2头/2个action snapshot。两包的 `validation_layers.global_fact_journal_consistency` 都是NOT_ASSERTED_ISOLATED_FACT_WITNESSES，POST=HOLD/frame=UNAVAILABLE，未成为原生历史。详见 [独立结果](../evidence/A03/review/P2-R1-proposal/independent-static-results.json)。

| 新诊断值 | 独立要求 | 静态检查实际结果及含义 |
|---|---|---|
| [不同readonly_session_id](../evidence/A03/review/P2-R1-proposal/diagnostics/readonly-session-does-not-match-gate-binding.json) | basis会话必须等于gate_binding及STARTED/READ记录 | basis_check接受。当前只检查形状/读序列等，未关闭同一会话绑定 |
| [不在前缀的initial head](../evidence/A03/review/P2-R1-proposal/diagnostics/initial-head-not-in-canonical-prefix.json) | initial H应是本session STARTED前真实CAS头，随后只允许本session事件 | basis_check接受任意不匹配hash的初始头；expected final head正确不能替代initial→final的证明 |
| [新1.2 Source类型](../evidence/A03/review/P2-R1-proposal/diagnostics/amended-source-kind-coverage.json) | 新转换类型须被同一新profile的结构/语义层一致处理 | exchange-v2 Schema通过，artifacts()报unregistered new kind。该诊断是允许类型的单节点值，不是完整转换包或执行资格 |

这三项只构造新静态JSON，未创建native handle、未调用产品或权限验证器，也不证明运行时可被绕过。它们说明作者静态自洽统计不足以支持设计已闭合；本轮在这些明确缺口处结束，没有无限扩大反例搜索。

## 3. 可采纳设计、必须补齐/裁定、后续功能验收

下表“可采纳”是供主调度决定采用的设计部分，**本报告不作采用批准**。“必须”列区分当前静态语义缺口与新合同选择；最后列的运行项全为NOT_EXECUTED。机器可读表见 [decision-table.json](../evidence/A03/review/P2-R1-proposal/decision-table.json)。

| 主题 | 可采纳设计 | 必须补齐或裁定（推荐最小范围） | 后续功能验收 |
|---|---|---|---|
| VERSION | 显式exchange2/Artifact1.2/profile+16pins+API SHA；旧七Schema/API原字节保留，旧节点只读输入。 | 新提案仍须明确批准；新版本类型的Schema/语义检查覆盖一致后才可采用。不得按latest或重复版本字符串混选旧草稿。 | 新旧入口/profile选择/历史原件与显式转换实测。 |
| SCOPE-01 | 全书genesis到真实head、accepted_anchor与真实前驱、逐事件保留old body/hash、全账本原生等值证明。 | 必须补齐typed journal frame如何终止外层递归消费、frame自己声明/推导scope和DAG规则。当前artifacts()平铺Resource refs到外层scope，prefix_check()另按frame scope验；全包跨scope正例缺失。最小为同书两scope完整静态包及错误frame/漏声明反例，非frame仍严格同scope，planless事件无scope依据时用null。 | 原生全书扫描、漏scope/删事件/CAS变化、固定session不能切scope清历史。 |
| SESSION-02 | 只读能力与dispatch分离、真实已接受/永久预留、无intent/permit、保留UNKNOWN与原INTERRUPTED。 | 两个新诊断值（会话不一致、初始头不在链）仍被basis_check接受。须显式核对initial H为STARTED前真实头、H到final只允许本session记账、session/owner/generation/registration/target/read记录一致及唯一fact key；补最小静态拒绝。 | 真实三读、持久计数、崩溃/接管/UNKNOWN提交查询、fact/event/index原子性与资源保全。 |
| BUDGET-03 | 第三次读明列total_read_calls=3、每读2s/入口8s/父60s/retries0，不伪装免费校验。 | 这是从旧专用固定2读且全程持闸到3读+逻辑session的新决定，须明批。推荐读前持久计数、同entry/call重启不重置、独立无intent计数、最早绝对期限截短每步；第三读在最终短gate内，随后校验和CAS，不暗加第四次业务读。session需由所有受控目标写入口和takeover共同执行。 | lease/续租/其他writer/死亡session/超时边界，未访问项与当前全书暂停。 |
| ADOPTION-04 | 只接纳已知DB1、追加profile事件、旧行/hash不改、未知库失败关闭。 | 只追加新事件不能充分定义旧writer拒绝的持久门。基线verify_integrity按精确四键meta和user_version1核对，并只验证事件hash/head。推荐明确adoption事务增加profile判别meta键+事件（或显式新格式），新open核对两者；旧严格meta比较将拒绝。崩溃时fail-closed、target fence/owner需一致；此为静态建议未实测。 | 接纳前后中断、旧writer重新open、fence不一致、profile与索引不一致。 |
| R17-05 | 分开原receipt和后到聚合receipt、per-action snapshot/head/fact、独立report级新读，旧头字节不改。 | 两个包是孤立fact值见证，不是原生合法全书历史；同计划首UNKNOWN即停，不能自然有两行动恢复头。推荐先提出由原A02 planner真实生成的最小一动作或其他可达单头晚到receipt路径；多头仍为无原生资格的值模型。调度必须明确这与完整R17的关系；若要求真实多头，另批可达历史模型及正例，不能自行删R17、续旧尾或扩跨计划/scope聚合。 | 合法原生晚到receipt、独立report读、历史头/当前头区分及后续漂移；多头按裁定角色验收。 |
| PRE-06 | 注册的A侧合成fixture verifier、五项实际比较、私有run接纳、HOLD/UNAVAILABLE诚实保留，不冒充B质量。 | 需批准exact oracle/实现digest及独立来源。当前唯一新producer与run Schema强制post-hold hold_id/head，但转换后的初始执行也要求fresh PRE，未定义无hold bootstrap。推荐显式INITIAL/POST_HOLD上下文或另列已批准initial producer，不能制造hold或复制旧PRE stub。 | 实际五检查/接纳、新PRE/新TARGET/新plan清hold及最终第二次变化，均NOT_EXECUTED。 |
| CONVERSION-07 | 仅已知全合成初始输入、原字节保全、新namespace和完整映射、追加状态链、未知DB不自动迁移。 | 新1.2 Source通过exchange Schema但静态语义检查报unregistered new kind；mapping仍null且无完整目标包。须补一致的初始类型覆盖、完整静态目标/双向映射。另选定completion manifest rename与COMMITTED谁是唯一接纳点、rename后未COMMITTED时只读重开如何判定，避免记录/manifest自引用。 | 真实完整转换及各中断点/重开只读/新目录重做，当前未运行。 |
| RETENTION | 历史NOT_RETAINED继续保留；新持久root/流式原始stdout stderr/预登记/失败finally/不可覆盖run id与完整清单。 | 历史丢失不能重建；当前探索性原输出缺失也不改称齐备。是否接收历史限制需调度明确。新运行的保全计划可采用，不要求静态阶段证明运行harness已实现。 | 故障/timeout/断言后原件、完成回执与进程释放，统一原字节清单。 |

### 3.1 全书跨scope消费者边界：阻止完整前缀段直接实现

当前 [check_static.py](../evidence/A03/review/P2-R1-proposal/input/checkout/examples/a03/P2-R1-proposal/check_static.py) 212–219行把Resource所有普通ref递归计入外层Artifact声明并要求外层scope；252–267行另按frame声明/scope核对。foreign frame的引用在两层下不能同时满足。只有同scope包未暴露这一差异，假scope负例也不替代合法正例。

建议先明确定型的账本frame消费者，而不是通用Resource豁免：只有确切profile/format和通过结构/内容验证的prefix.frames才能开启子消费者；scope由exact indexed plan/登记资源推导，planless控制事件没有scope根据时应为null。外层只消费其声明的外层refs和有字节约束的prefix Resource，frame各自声明其递归ordinary refs，统一DAG仍须发现跨frame/Resource混合环。非frame位置仍严格原同书同scope。补一份同书两scope、含真实不同plan及嵌套Resource的完整静态包，并让全包入口通过；错误frame、漏声明、他书和伪装frame拒绝。

这是新消费者边界的合同选择，影响contracts/recovery.py及版本化前缀校验/Schema、共享Exchange消费者。不能由A内部同意推定B接受，也不能以“全账本可信”放宽普通引用。本轮不生产替代候选或改这些文件。

### 3.2 三读、逻辑session、lease和最终CAS：须先裁定的协议变更

原专用入口是固定两读/零重试/全程同书gate；新提案为2次证据读+1次currentness读及中途释放OS gate。两者不能默认为兼容解释。若采用，推荐：

- 独立持久计数绑定book/plan/action/parent-call/entry/session；读前记账，崩溃也耗次，同entry/call重开不重置。无intent不得借用attempts.intent，普通intent的每call最多3读与其余pending额度不变。
- parent60s、entry8s及各2s/busy1s/gate5s均以最早绝对期限截短；lease按原节奏续期，失败/死亡session只能按明确ABORTED和已耗额度收口，不能自动换call循环。
- 所有受控目标写入口、claim/takeover共同执行active logical session排他；纯JSON或一个producer方法里的布尔检查不够。第三次实际业务读放在最终短gate内，随后核对owner/fence/当前全书集合/完整prefix及CAS；不暗加一次免费业务再读。
- initial H、STARTED、全部READ_STARTED/FINISHED/FAILED和final H需同一session/owner/generation/登记/target；窗口内其他事件拒绝。只有本session记账变化可解释H0→H，资源先持久、fact/index/event原子提交，旧永久唯一键和UNKNOWN提交后只查不重提的规则不能丢。

这些条件须写入规范性API/Schema语义及最小静态控制，不只列未来测试。两个已冻结诊断值分别缺失会话一致性与initial头绑定。对应拟路径为contracts新版本校验、runtime/storage与common，以及recovery observation/lease编排；只有调度批准后才谈实现和竞态验证。

### 3.3 已知DB接纳与旧writer拒绝：明确持久判别

[只读基线分析](../evidence/A03/review/P2-R1-proposal/base-profile-adoption-analysis.json)显示旧verify_integrity精确比较四键meta/user_version1，并验证事件hash/head；它没有解释新profile-adoption语义。仅“追加事件并要求旧writer退出”还没有说明以后旧二进制重新open应在哪里失败。

推荐最小选择是已知格式的显式接纳事务同时追加事件和持久profile判别meta键，新open要求它们一致；旧四键比较在静态上会拒绝额外键。另一可选是明确新格式/版本并保留原库。二者均须由调度选择具体持久标志、事务/故障状态与新target fence约束，未知库仍拒绝。本轮没有修改meta、运行旧writer或查询数据库，静态推导不当作实际兼容性证明。

### 3.4 R17的值表达与真实可达性：不自行删标准

按action分别绑定immutable head/intent/fact/snapshot，另取report级真实新读，可以消除旧的null-vs-receipt与多个snapshot强制相等等式；这部分表达方向可采用。当前两包明确是孤立fact见证，导入头/未尝试依据并非一条原生合格全书历史，因此不能把包能解析称为当前恢复报告正例。

推荐调度先要求一个由未改A02 planner真正生成的最小一动作（或其他已证明可达）计划：UNKNOWN→新终局头且original_receipt=null→后来完整receipt→独立report读→新POST/Batch；不裁剪旧plan或凑未尝试结果。多头值模型可以保留，但首UNKNOWN即停、旧尾不恢复的当前执行器不能自然产生两行动UNKNOWN头。主调度必须明确R17中这个多头组合的验收角色：保持为无原生资格的值层模型，还是另批可达历史模型。若要求原生多头，须另给正例来源和完整账本规则；不得偷偷跨计划/跨scope聚合或续发旧尾。无论如何，本文不豁免/缩窄R17，也不先验接受功能。

### 3.5 合法合成PRE与转换的初始接纳

当前oracle是待批准的author fixture oracle；graph hash相同不能替代source/structure/answer/coverage/policy五项实际比较。五项UNAVAILABLE、PRE=HOLD及无native run是恰当状态，**不是要求静态阶段先运行出PASS**。需调度批准独立审阅的exact oracle/实现digest，限定A侧固定合成fixture，不冒充B算法或真实来源完整性。

[协议诊断](../evidence/A03/review/P2-R1-proposal/protocol-decisions.json)还指出bootstrap边界：新run Schema强制非空hold_id/head，API只描述post-hold producer；转换后初始输入又不能使用旧PRE stub取得新资格。需明确定义INITIAL和POST_HOLD两种不同校验上下文，或指明另一个已批准initial producer。不能为初始执行制造一个hold，亦不能复制旧PRE改时间/ID。post-hold路径仍需新实际snapshot、新五检查/接纳PRE、新TARGET/plan、最终再读/CAS，正向清除与第二次变化都留待实际验收。

转换当前只有CREATED/COPYING/VALIDATING/INCOMPLETE、null新hash和无目标bundle。这个未实现状态真实保留；必须先补结构/语义一致的完整静态目标/映射，并定唯一完成接纳点及rename后未COMMITTED的只读重开规则。完成manifest与COMMITTED记录须有向无环、无自签依赖；缺项/半成品不取得资格，重做必须新目录/新id。未知DB失败关闭不等于迁移完成，也不要求自动迁移未知库。

## 4. 对下一段有界工作的影响和跨侧边界

静态修订应优先补SCOPE-01、SESSION-02和CONVERSION-07的最小正/反值与一致校验，再由调度裁定BUDGET-03、ADOPTION-04及R17-05验收角色、PRE-06初始来源。不能在这些关键协议仍悬空时把整套提案直接送入runtime实现。

可单独决定采纳的部分包括：旧原件保全、显式profile/pins、新旧receipt分离与每action独立观察的值模型、合成五检查/注册接纳框架、append-only转换/retention原则。主调度可拆分这些设计决定与后续实现授权，当前REWORK不表示每个未运行项目都是设计错误。

拟改路径须再次精确授权：contracts/recovery_schema.py、版本化Schema及新前缀校验、recovery.py；runtime/storage/__init__.py/common.py/holds.py与recovery observation/lease/cli/quality；新增quality/synthetic_precheck.py仅用于批准的固定合成oracle。公共Exchange、引用消费者边界、POST/Batch/Receipt新语义如被B消费，需列影响并取得共同确认；本报告不联系B、不替其确认，不修改任何这些文件。保留当前candidate-v2，后续修订应另有确切版本/pins，不能覆盖旧输入来更新通过数。

未来功能验收依次核对原生全书前缀/跨scope扫描、真实三读与session/lease/CAS、无intent充分/不足ABSENT、真实可达晚到receipt及report级读取、获批PRE/bootstrap/hold正向及第二变化、转换各中断/重开和原件保全。全部须新的冻结实现、报告、清单和会话释放后另续派；当前均NOT_EXECUTED。多头按调度明确的角色验收，不靠手写值取得native资格；不请求被拒字段重置专项。

## 5. 证据、限制与释放

历史P2动态失败原件NOT_RETAINED、hold总体流缺失及本提案探索性原输出缺失均保留原声明；清单只证明现存文件，不恢复原件。新运行应先建持久root/预登记、启动即流式保存原始stdout/stderr、失败finally和进程回执/retention inventory，禁止TemporaryDirectory自动清理。计划足以作为设计原则，但harness是否落实仍待运行证据，历史限制是否被接收由主调度明确决定。

本轮一次文件读取在freeze尚运行时提前请求stage路径，退出1/FileNotFoundError；[原失败记录](../evidence/A03/review/P2-R1-proposal/input-read-attempt-01.json)保留，改为等导出完成或只读原Git后再继续，没有重建候选或掩盖产品失败。freeze及其同步Git读取全部结束；静态runner父记录显示PID52488退出0、超时60s、alive=false，runner无自己的子进程/后台任务/原生会话。释放见 [static-process-release](../evidence/A03/review/P2-R1-proposal/static-process-release.json)，没有全系统进程扫描或终止他人进程。

结束核对旧审查/准备文件1856项长度/SHA256保持一致；501项提案清单全部raw Git核对，27,168个旧Git文件未改。全部本轮输入、脚本、诊断、日志、失败记录及报告列 [统一清单](../evidence/A03/review/P2-R1-proposal/sha256-manifest.json)，仅排除清单自身，Git忽略项明确列入；终检见 [final-verification.json](../evidence/A03/review/P2-R1-proposal/final-verification.json)。


```powershell
# 只读核验本轮档案及冻结输入；不运行产品/DB/旧场景
python -B D:/1800/docs/evidence/A03/review/P2-R1-proposal/scripts/verify_archive.py
```

产品运行、DB查询、原生session、浏览器、网络、平台、凭据/profile、OCR、业务模型/收费API和真实书籍动作均0。旧DB文件仅为保全计算字节SHA，未作为SQLite打开。未安装包、未改产品/合同/依赖/state、未提交/集成/推送、未联系执行者/B/其他chat、未创建轮询或自动化。真实质量/成本未测。

既有自动安全审查拒绝的字段重置专项保持 **NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION**，没有复跑、变形、委派，也不列入下一轮测试请求。所有新诊断均为普通静态JSON值。

结论 **REWORK**：当前未达到整体DESIGN_READY_FOR_COORDINATOR_DECISION，具体可采纳设计与待裁定最小选项已交付。合同/实现批准、B确认和后续功能验收由对应负责人决定，整体A03功能仍未接受，I01不释放。本轮结束等待调度。
