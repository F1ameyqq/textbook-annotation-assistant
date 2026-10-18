# A03-R1 最终差量独立验收

2026-10-18（Asia/Shanghai）。**ACCEPTED，仅本次既定 L/G/F 差量及与既有接受共同构成的原28项有限映射。** 独立十阶段各运行一次，新增2个native目标、3次dispatch，其中2次产生动作效果；没有业务失败、外层超时、冻结后修复或重跑。原 M/L1/G4、legacy生成均为0新增业务。未发现本轮固定输入的产品反例，原有限清单没有必须再派作者补跑的项目；本结论不自行改变 A03 整体/集成/I01 状态。

## 固定对象与原件

| 对象 | 确切身份 |
| --- | --- |
| 本次正式调度规则 | `41d46cee79ccb4235f7e2f9bd7dcaff6668bb0ba`，`A03-R1-final-delta-review-dispatch.md` |
| 最终交付 | `19ab03c849bfab3dcde2dc86be37c59f3add1ebe` |
| 唯一第二/最终冻结运行包 | `9992cd8aba10987d25dd0dc0d0874abec02b27ef` |
| 产品原字节 | `6097a06de937fee8876feccedf46920510850b83`，src到最终差异0 |
| 首包交付 | `54e86adfaf144093a688b62fe0dad5190ceb2fa6` |
| 作者报告SHA256 | `40f030a5c4a1f538c35dcd196b7375f8b8f86d5029a59be41b8bb19d1dc0659e` |
| 作者manifest SHA256 | `22614eaeeaeb6ae6a14e9846e4ab552d3b9eed0ce5602c9dcbb044044e4ee405` |
| 独立新执行副本 | `D:/1800-worktrees/a03-r1-final-review-19ab03c8` |
| 自己获准承接的既有L1 | `D:/1800-worktrees/a03-r1-review-54e86adf/docs/evidence/A03/R1/review/business/cases/M2-sufficient` |

重新核对445个作者成员、9292341 bytes，长度/SHA256全部相符；相对首包494个路径均在本轮白名单。固定包至最终的产品、实际业务driver和fixture无变动。使用 `git -c core.longpaths=true`、raw blobs 和新本地仓库；没有读取浮动作者代码。implementation/schema pins与实际执行字节相符，真实模块导入和执行视图索引均核对。见 [准备索引](../evidence/A03/R1/final-review/preparation.json) 与 [独立审计](../evidence/A03/R1/final-review/audit.json)。

沿用[首包独立报告](A03-R1-review-report.md)及[调度有限接受](A03-R1-coordinator-acceptance.md)的 M 五例/L1/依赖拒绝；T1 capture与六例、T2 C12/H1、旧切点/owner仍严格限原确切版本和原范围。产品src/pins/消费者字节未改，未重新泛化旧结论或重跑未受影响全集。旧独立报告/manifest及其1204个保留成员全部重新散列相符；原失败与历史缺件继续保留。

## 合法承接、冻结与实际运行

运行前，自己的 L1 runtime/target 活源 bytes 均与上轮最后静止capture相同；anchor仍指原绝对位置，owner/PID为空、lease=0、RELEASED，legacy未决2项。只通过新路由工程内的3个junction访问自己原 M1静止材料、M2活源及L1静止材料；`Path.resolve()`仍落在原身份，不复制/改标数据库获取正向资格。作者活源从未访问。

新包装只设 `A03_R1_PROJECT`、读取固定fixture摘要和自有continuation路由。`launch.py`、driver及路由checks的SHA256在 [preregistered.json](../evidence/A03/R1/final-review/preregistered.json) 先固定，随后调用未修改的 `final.py --batch --candidate 9992cd8a...`；没有替换业务函数、预期、守卫、顺序或时钟。运行期raw-view重新从冻结Git构建，fixture PGM为3579 bytes及原正确摘要。原作者preparation/checks与本轮新路由checks分别保留。

子worker180秒、每阶段父240秒不变；聚合记录器2500秒仅容纳十个父预算，未放宽任何阶段。read2秒、entry8秒、gate5秒、lease10秒/renew2秒、PRE/currentness及恢复期限保持。既有Windows CPython3.9.13，无安装/联网。实际聚合wall55.891秒。

| 阶段 | 独立worker wall/CPU秒 | 实际结论与次数 |
| --- | --- | --- |
| L2含G1 | 10.500/8.750 | B新目标/一次dispatch/一次效果；A.pending=2、B.pending=0；A未决集合和target bytes不变。B单书/合法B＋H-A1多书表示各一次公开C01读取，B consumer/ref相同；不声称mixed-native执行。 |
| L3-execute | 6.219/4.938 | 新目标；第一次not_applied调用，执行读回unavailable，真实UNKNOWN/正式receipt与progress；一次dispatch、0效果。 |
| L3-reconcile | 3.687/2.828 | 新PID，max_attempts=1、一次完整读，ABSENT/RESOLVED_NOT_APPLIED，pending=0；无dispatch。 |
| L3-second | 15.437/11.969 | 真新INITIAL/PRE/TARGET/plan及不同action/intent，一次dispatch/一次效果、执行回执UNKNOWN；旧resolution为OBSERVATION_NOT_FRESH，新INITIAL为BOOK_WRITE_PAUSED，pending=1。 |
| G6-first | 7.609/1.453 | 复用第二intent、同call三次实际FAILED_READ，均为原2秒故障超时读取并回收；不是三次成功观察，无新目标/dispatch。 |
| G6-reopen | 1.453/1.391 | 新PID同intent/call；RECONCILE_ATTEMPT_LIMIT、0补读；calls.created、attempt_windows.started和三条attempt逐字相同，pending=1。 |
| L4 | 0.891/0.891 | 三差量、4门、0业务，分叉/环/错原receipt均阻断；到达层如下。 |
| G2/G3 | 0.453/0.469 | 7存储/格式＋4角色/转换调用，均在自己的新负控副本/目录，无业务效果。 |
| G5 | 0.422/0.422 | 2个既定值层负控，0新report read/publisher。 |
| F | 4.093/4.094 | 既有query/export实际只读；双库前后SHA256相同，claim/reconcile/publish/dispatch均0。 |

作者和独立各6阶段/12份raw库重新以 `mode=ro&immutable=1` 查询，SQL.json、表值、事件hash/head、动作/intent/permit、目标调用与实际变更均相符，前后bytes不变。每组L2为B独立目标，L3最终effects=2而mutated=1；不能把调用表行数当新增题数。两组的G6均三次故障尝试、跨进程0补读，原intent终局和第二pending分离，正式native报告读计数仍0。未知和原receipt历史没有因恢复被删除。不是跨库原子性、断电或任意外部写者证明。

## 负控到达层及是否足够原有限key

**L4有限拒绝接受。** 独立结果与作者一致：fork=`RESOLUTION_FORK`；自回指cycle=`EXACT_REF`；错原receipt完整入口=`EXACT_REF`；额外 `_resolutions` 值门=`REFERENCE_HASH_MISMATCH`。原V07/R06及既定L4要求这三个固定错误链保持阻断，没有规定必须命中某个更深的专有错误码。自回指及所选后继receipt经过重封后不能满足精确不可变引用，真实native入口已拒绝，不能接纳为资格；因此这些固定key的fail-closed要求得到证据。**没有证明“通过精确引用检查后的所有环/错误receipt内容绑定”已被动态覆盖**，第四门也未到后层内容条件。该限制保留，不据它新造合法环、换receipt无限变异或扩大矩阵；旧T2归属/历史consumer接受及不变源码另按原范围继承。

**G1：15项按层接受。** plan/question为MISSING_REFERENCE、action为ACTION_DIGEST_MISMATCH、graph/snapshot revision为EXACT_REF、policy为POLICY_CONFLICT；漏登记、run、authorization实际到运行门 `REGISTRATION_BINDING_MISMATCH`、`NATIVE_PLAN_HISTORY_CHANGED`、`NATIVE_CREATION_CONFIG_CHANGED`。五个缺字段为 `SHAPE_oneOf`，仅 `REJECTED_AT_STRUCTURE`；能力UNKNOWN由实际pure check_target产生非PASS，仅QUALITY_VALUE。原有限key要求缺前置不获资格，并保留公共/运行准入分工；结构拒绝证明对应缺字段不能进入后续，运行身份/配置门有上述独立差量及原M3旧proof拒绝支撑。没有把五个结构失败算成五次runtime检查，也未要求对已经被公共入口拒绝的同一输入再到runtime制造效果。

**G2/G3：按本次7＋4原key接受。** runtime目录重绑/未知anchor、target未知user_version/目录、未知exchange均失败关闭；保留实际外层错误与内层原因。文件父路径被固定文件阻塞，真实FileExistsError。无效SELECT在自有静止负控副本经实际transaction wrapper成为STORAGE_TRANSACTION_FAILED，rollback后DB与源capture字节相同；仅证明该wrapper失败分支，未声称写提交故障/所有I/O原子性。1.1包只作ARCHIVE_ONLY读取、无native context，作为1.4输入拒绝。合法C01初始转换先写INCOMPLETE，随后实际资源复制文件/目录冲突；无bundle，重开JSON_INPUT，marker保持。保留旧converter成功有限证据、LEGACY_INITIAL_ONLY/fresh-native-only/迁移BLOCKED，不要求或宣称新COMMITTED格式与DB迁移。

**G5：两个值层key接受。** 用真实旧recovery read替代正式report read为NATIVE_REPORT_READ_NOT_FRESH；两真实终局head、不同实际snapshot的错误head映射为RECOVERY_CHAIN_INVALID。按原批准的值层表达，无新正式POST/Batch、跨书/跨计划runtime多头聚合或报告读取。原正式报告、三分母纯diagnostic及VERIFIED结构拒绝的层次没有改变。

**F：同字节三路径继承及只读增量接受。** 正常=M1、新规划=M3、UNKNOWN历史恢复=L1，沿用首包确切有限接受；本次L2/L3/G6实际运行/核对消费同一产品入口，query/export只读摘要不变。L1历史遗留未决仍HOLD，框结果不变成内容验证。没有为F新增场景、重新reconcile/publish或借导出省略pending。

上述是批准的有限coverage key结论；结构、引用和值层的真实到达层是结论的一部分，不升级为未执行的后层证明。原任务没有要求全交错、所有不同wrong-receipt构造、实际改写目标能力、mixed-native执行或任意规模性能，故不把这些另列成本轮阻断。S01、真实来源/平台/OCR/内容、B共同合同、DB迁移仍在范围外。

## 原28行映射

本表“闭合”均指原已接受的有限映射，不表示各项全部在本轮重跑。首包/T1/T2和E04/E07/E08/E09等旧确切边界、旧失败及field reset排除继续适用。

| ID | 既有接受＋本次证据及限制 |
| --- | --- |
| V01 | M1继承；L2正常B独立运行/回执/目标持久化，有限闭合，固定synthetic语言。 |
| V02 | 原六类单动作切点与未改守卫继承；L3新PID差量，不重跑/推广所有交错。 |
| V03 | T1异常五类、M3 ABSENT/L1 MATCH继承；L3一次真实ABSENT后新链，有限闭合。 |
| V04 | M2充分/不足两支继承；尾项无intent/permit/dispatch，本轮零M业务。 |
| V05 | L1跨run/scope扫描继承；L2 A.pending=2/B.pending=0，A不变；合法B＋H-A1多书值，mixed-native不在证明内。 |
| V06 | 旧owner/换代和M3旧proof继承；L3新UNKNOWN拒旧resolution/新INITIAL，有限闭合；field reset不执行。 |
| V07 | 既有依赖/consumer拒绝＋本轮G1/L4，按结构/引用/值/运行层有限闭合，不改称后层全部实测。 |
| V08 | 旧初始化/首包四存储拒绝继承；G2七项/G3实际中断有限闭合，无DB迁移能力。 |
| V09 | legacy保停及G4原六槽/receipt结构拒绝继承；G3角色/中断补齐原有限key，S01单列。 |
| V10 | 既有正式报告与分母诊断继承；G6持久三尝试耗尽、新PID0补读，有限闭合。 |
| R01 | 固定对象/白名单/raw输入/实际导入/原件/清单/释放核清；旧记录和本轮两个静态工具错误均保留。 |
| R02 | 已接受依赖拒绝＋本轮15项G1；公共缺字段结构拒绝与实际身份/配置运行门分别核清，有限闭合。 |
| R03 | 原六单动作切点继承；产品与相关guard原字节不变，未造新崩溃矩阵、未补旧F2/F3缺件。 |
| R04 | L2/L3跨进程独立runtime/target及12份本轮双库原件核清，独立事务/真实效果保留。 |
| R05 | T1/M2/M3/L1继承；L3 ABSENT和G6故障保持UNKNOWN/暂停、零重发，有限闭合。 |
| R06 | L3旧UNKNOWN→ABSENT→新UNKNOWN/旧证明拒绝；L4三负控保持阻断，环/错receipt止于引用层，有限闭合。 |
| R07 | L1全书两历史扫描继承；L2未决不漏、另一书不误停；普通scope规则未放宽。 |
| R08 | 既有身份/依赖拒绝＋本轮action/run/漏登记、目录/格式门；未以结构失败替换runtime通过，有限闭合。 |
| R09 | 原竞争/换代有限证据与效果前guard继承；本轮owner/keeper/进程均释放，无任意外部写者或效果竞争新证明。 |
| R10 | 同书两历史继承；B单/合法多书两表示各一次、B一次native执行/A不变；A02原失败不改写，不合并冲突HA1/HA2 evidence registry。 |
| R11 | M2充分/不足、C未尝试与receipt/progress界限继承，本轮不重做。 |
| R12 | M3/L1继承；L3真新INITIAL/PRE/TARGET/plan/不同action，G1缺字段不授资格及实际run/config门，有限闭合。 |
| R13 | M3 hold最终读/CAS/漂移继承；G1版本/授权及能力值差量，限原key，无新hold变体。 |
| R14 | 首包四项＋旧初始化继承；本轮7存储/格式和转换中断有限闭合，不清原状态或开放未知库升级。 |
| R15 | C01/1.3/旧converter接受继承；1.1 archive/native分工、INCOMPLETE不接纳、L1无intent legacy不解除，原字节不重封。 |
| R16 | 原G4六槽及独立负控继承，receipt仍仅结构拒绝；归档不授native/真实源资格，S01独立。 |
| R17 | M/L1正式历史报告继承；本轮旧read/不同snapshot错误head两个值层拒绝；PENDING/NOT_SUBMITTED，不推广runtime聚合。 |
| R18 | 三分母纯diagnostic/状态守卫继承；本轮同intent/call三故障尝试耗尽、跨进程0补读，不借M2entry计数，有限闭合。 |

## 次数、活源与释放

作者第二包2新目标/3dispatch；作者累计native7起点/13dispatch，legacy首次失败1＋纠正2保持。旧L两次驱动冻结/失败和本次第二最终包均不重置。本轮独立另为2/3，连同独立首包累计7/13；独立不算作者第三包。L3首intent ABSENT一次实际读与第二intent G6三次故障读分开计数；G1=15、L4=4门/三差量、G2=7、G3=4、G5=2，未用满一般上界去追加测试。

作者32业务/读进程，另1冻结前noop；独立32业务/读进程均有真实退出/回收。六次G6故障子读（作者3、独立3）各按原timeout终止，是预期FAILED_READ；其余业务父/worker均exit0、timeout=false。固定native observer源码的wait/poll与完成记录相符；独立顶层batch亦已wait、exit0。所有worker结束仅MainThread，静止capture owner/PID为空、lease=0、RELEASED，自有登记PID最后无存活项。pending/hold作为业务状态保留，没有为释放清除。

作者55份continuation保留文件在固定Git副本重新核对，并将索引DB SHA与L2最终runtime capture绑定；不沿其source字段访问作者活源。自己的原绝对L1 runtime已合法增加B，当前primary与新L2 capture逐字相同，A目标bytes保持；旧文件/不可变artifact保留，新增46份资源/锁文件另存 [continuation-files/index.json](../evidence/A03/R1/final-review/continuation-files/index.json)。没有回滚自己的活源以恢复“干净”，也不把现活源当首包静止证据。L3第二UNKNOWN与三次计数现场同样保留。

## 工具限制、命令和归档

两次**验收静态工具错误**保留：`audit.py` 首次索引遗漏m.raw_view额外导出的两份测试文件；`coverage_and_continuation.py` 首次把ledger-relative `files.path` 当cwd相对路径。均在业务十阶段全部完成后发生，零产品/driver/预期修改、零业务重跑或新目标；只补固定Git字节身份、正确的原runtime路径解析和静态收口。原脚本分别留为 `audit-first-source.py`、`coverage-first-source.py`，失败记录对应 `*-first-failure.json`；首次静态调用只有exec返回trace，没有独立OS raw stderr/PID，不伪造这些字段。它们不是第三业务候选或对阶段失败的修后重跑。

实际一次运行入口如下；输出排他且已存在，不可原地重跑：

```powershell
python -X utf8 -B D:/1800/docs/evidence/A03/R1/final-review/prepare.py
python -X utf8 -B D:/1800/docs/evidence/A03/R1/final-review/launch.py
```

包装实际执行固定 `examples/a03/R1/final.py --batch --candidate 9992cd8aba10987d25dd0dc0d0874abec02b27ef`，各worker的argv/cwd/PID/raw streams和180/240记录见 [runs/run](../evidence/A03/R1/final-review/runs/run/)，输入和实际导入bytes见 [audit.json](../evidence/A03/R1/final-review/audit.json)。到达层、counts、continuation绑定见 [coverage-audit.json](../evidence/A03/R1/final-review/coverage-audit.json)。必要新原件/输出封存，固定raw-view可按Git重建，旧全集不复制；SHA256/长度索引见 [manifest.json](../evidence/A03/R1/final-review/manifest.json)。

本轮仅新增本报告和 `docs/evidence/A03/R1/final-review/`，不改旧报告/索引、产品、调度JSON/Git索引，不提交或联系作者/B/其他对话。零平台/profile/凭据/网络模型/OCR/付费/推送/书级送审/A05题22。建议调度接受既定离线有限范围；整体接受、本地集成、受影响集成检查和I01-A释放仍由调度另行决定，不自动宣称B或真实平台接受。
