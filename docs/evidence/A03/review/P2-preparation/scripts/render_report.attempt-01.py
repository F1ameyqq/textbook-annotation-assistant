"""Render a documentation-only P2 preparation report from frozen document extracts."""
from pathlib import Path
import json
ROOT=Path('D:/1800');OUT=ROOT/'docs/evidence/A03/review/P2-preparation'
REPORT=ROOT/'docs/tasks/A03-P2-review-preparation.md'
def load(name):return json.loads((OUT/name).read_bytes())
def cell(t):return t.replace('|','\\|').replace('\n','<br>')
api=load('accepted-api-schema-map.json');matrix=load('acceptance-matrix.json')
text='''# A03 P2 独立验收准备

日期：2026-10-17（Asia/Shanghai）。本轮状态：**PREPARED / AWAITING_FROZEN_IMPLEMENTATION**；全部 V01–V10、R01–R18 功能结果为 **NOT_RUN**，未作 A03 功能接受判断。

P1 设计已由主调度接受，P2 实现已获批准。当前验收对话仅获准做这一次准备；准备完成即结束，等待主调度另发冻结实现提交、执行报告、统一清单、会话/进程释放声明及正式复验续派。**I01 不释放**。未读取或运行浮动实现，未启动恢复、目标、SQLite 或功能测试。

## 1. 固定依据和适用次序

| 依据 | 精确版本 |
|---|---|
| 本次工作流 | `6b77c436742cf2826083b109d8ed86b85539cba6` |
| P2 实现 base / 已接受 P1 最终提交 | `940a5de33a24b1a3a9ded6e69ade1dd0609ed83a` |
| P1-R2 设计提交 | `a250a76dc0b3f13b9dee3bcd2c3d7414032b9768` |
| A02 代码依赖 | `ec1b4defbfa3ec0f181d291106fb53313983e493` |
| 冻结 API SHA256 | `e2b0865fc1a25206181f3094155b059a6d34eb851afc750e813f0c2e89960f85` |
| R2 提案 SHA256 | `acd67720e905a45b85c0943648b239b2dfd1fdb36eaf3095e56803c1de564f9d` |

权限及数值以该 workflow 的 [P2 派单](../evidence/A03/review/P2-preparation/inputs/workflow/docs/tasks/A03-P2-dispatch.md) 和 [P1 主调度收口](../evidence/A03/review/P2-preparation/inputs/workflow/docs/tasks/A03-P1-coordinator-acceptance.md) 为准。原 [执行任务](../evidence/A03/review/P2-preparation/inputs/workflow/docs/tasks/A03-runtime-recovery.md)第4–6节及 [独立标准](../evidence/A03/review/P2-preparation/inputs/workflow/docs/tasks/A03-independent-review.md) 的 V/R 条件继续适用。归档提案中 REVIEW/UNIMPLEMENTED/待批准等历史标签保留，不能据此否定新授权，也不能据新授权把旧静态图当作已执行事实。

[输入索引](../evidence/A03/review/P2-preparation/input-index.json) 固定20份相关文档、API和Schema的原始Git字节、blob、长度及SHA256；另核验已接受R2独立报告和清单的Git摘要，仅记录元数据。没有复制历史证据全集、实现源码、测试或fixture，也没有创建临时实现导出。

正式选包必须同时固定提交、R2 profile、完整清单和以下七个pin。schema=`1.1.0-a-recovery-proposal`、exchange=`a03-exchange-1`、profile=`A03-P1-R2`；重复的顶层版本字符串不决定最新版。profile中的 `source_git_commit=ca4fba4f505467228a8164c3999e0cecc54ffc4e` 是冻结R1输入，不能用作R2包自身身份。

| Schema（相对 examples/a03/P1-R2/） | SHA256 |
|---|---|
'''
for s in api['schemas']:
 text+=f"| `{s['source_path'].removeprefix('examples/a03/P1-R2/')}` | `{s['sha256']}` |\n"
text+='''
## 2. 接受的 API、责任与 D01–D08

[精确 API/Schema 映射](../evidence/A03/review/P2-preparation/accepted-api-schema-map.json) 保留四组全部19条 proposed 记录（G3末条包含两个纯helper签名）、contracts五入口、RuntimeAuthority八条协议的原签名、入参、输出、责任和错误码。该映射来自接受版本的JSON实际字段，不是实现导入结果。正式验收将逐项对照真实公开入口；历史 current 私有接口只用于兼容背景，不能作为恢复实现偷取私有状态的许可。

| API 组 | 主要接口与责任 | 对应检查 |
|---|---|---|
| G1（4条） | PersistentMockSession.create/open、runtime.storage.open_state、activate_fence；显式初始化与只重开分开；固定anchor/ledger/store/session/SourceBundle/scope | V01/V06/V08；R04/R08/R09/R14 |
| G2（5条） | prepare_action、commit_intent、dispatch_action、commit_action_result、commit_unattempted_absence；真实intent先提交，单次许可消费后才有独立目标效果，正常执行与恢复事实分开 | V01/V02/V04/V06；R02/R03/R09/R11/R12 |
| G3（6条记录、7签名） | observe_target、snapshot_from_observation、compare_action、snapshot_state_equivalent、bind_plan_observation、planner.action_facts/compare_action_effect；共享a02-facts-1纯规则，新实际读不改时间冒充 | V03/V04/V07；R05/R11/R13 |
| G4（4条） | load_book_context、import_book_context、export_book_context、import_history_archive；受控当前事务全书扫描，公开append/verify，不重建目标或清历史 | V05/V06/V08/V09；R06/R07/R08/R10/R14/R15 |
| contracts（5条） | load_archive_bundle、load_recovery_bundle、convert_synthetic_fixture、assert_recovery_plan_ready、effective_recovery_outcomes；归档、转换、同scope资格与当前runtime权力分开 | R02/R12/R15/R16/R17 |
| RuntimeAuthority（8条） | verify_claim、issue/consume_first_dispatch、verify_target_authorization、verify_context、clear_target_drift_hold、commit_reconciliation、commit_unattempted_absence | R03/R06/R07/R08/R09/R11/R12/R13 |

普通引用仍为精确四元组，持久身份含显式schema/exchange namespace与book/scope/id/revision。同一namespace不得同身份改kind/hash。逐消费者递归遍历所有JSON Resource中的普通引用，检查声明、字节、同书scope、路径、普通/资源混合环；一个消费者声明不替代其他消费者。公共validator只验声明图，当前跨scope全书许可必须来自runtime事务，序列化 `complete=true`、`gate_held`、`pending=[]`、`resolved=true`、封签及旧账本均不提供许可。

| 决策 | 已接受边界及未来核对 |
|---|---|
| D01 接口 | 仅派单白名单的三个A02既有文件及新增mock/persistent.py；复用原规划/比较规则，不改根依赖。本D01不解决Pillow依赖D01 |
| D02 版本 | 三新Artifact及严格版本；runtime a03-runtime-db-1 / user_version=1 / application_id=0x41303352；target a03-mock-state-1 / 1 / 0x41303354；ledger-export不是普通Artifact |
| D03 迁移 | 旧仅归档，显式转换生成新文件与映射；旧无intent UNKNOWN=LEGACY_UNRECORDED，永不补造历史解锁 |
| D04 部分计划 | 完整动作progress为默认；未尝试须充分ABSENT才可NOT_APPLIED，缺证不凑完整receipt/BatchReport；原UNKNOWN不变 |
| D05 权力 | canonical target_key={platform_namespace,target_id,book_id}，排除run/scope/action/question/session；唯一库、全scope扫描、owner/generation、效果闸、固定source/scope及新读 |
| D06 准入 | 全闭包SYNTHETIC_COMPLETE/FIXTURE/SYNTHETIC、SIMULATED；真实/ORIGINAL/OBSERVED或缺来源拒绝；S01、B确认保持未完成 |
| D07 独立效果 | 两个独立SQLite文件/连接/事务；目标业务状态、ID、效果日志跨进程保存；reconciler只比较，不直接改runtime或发效果 |
| D08 有界性 | 采用已批准数值及原退出码；普通intent最多3读与专用未尝试固定2读分开；额度持久、monotonic最早期限、无自动旧动作重发 |

## 3. 原 V01–V10 与 R01–R18 的逐项映射

以下是未来检查方法，全部 **NOT_RUN**。原条款原文、精确来源和两向映射在 [28行矩阵](../evidence/A03/review/P2-preparation/acceptance-matrix.json)；多对多关系只分配证据，不删除或替代任何原项。作者命令复跑与独立构造分别记录，不让同一状态函数生成expected和actual。

| V项 | 原场景 | R映射 |
|---|---|---|
'''
for row in matrix['rows']:
 if row['id'].startswith('V'):text+=f"| {row['id']} | {cell(row['original_check'])} | {'/'.join(row['related_checks'])} |\n"
text+='''
| R项 | V映射 | 独立方法及所需证据类 |
|---|---|---|
'''
for row in matrix['rows']:
 if row['id'].startswith('R'):text+=f"| {row['id']} | {'/'.join(row['related_checks'])} | {cell(row['independent_method'])}（{','.join(row['evidence_classes'])}） |\n"
text+='''
## 4. 独立进程、故障和实际效果证据

正式复验每例使用新且保留的自有case目录；固定输入/资产及SHA，明确runtime与target路径和物理文件身份，绝不使用执行者活动库。父harness只启动有限自有Python进程，用事件/屏障安排交错并记录PID、启动标识、owner实例、代次、到达/释放顺序和退出码。故障进程结束后，由另一个新进程重开原存储观察/恢复；捕获同进程异常或线程模拟仅为补充。固定sleep和日志标记不能证明并发正确或效果发生。只终止本例自有PID，退出时逐个join/wait并留释放收据。

六个必需断点取自冻结API，不能把注入退出90记为成功。下表0/1是单个受测动作在精确受控断点下的目标业务效果预期；若屏障/终止位置未被证实，则记录未知，先独立核对，不用日志反推未生效。

| 冻结断点 | 独立取证及未来判定 |
|---|---|
| BEFORE_INTENT_COMMIT | intent提交失败不调用目标，效果0；预写orphan无索引、无许可，原状态可追溯 |
| AFTER_INTENT_COMMIT | 已提交intent、尚未发目标，效果0；新进程先核对，不因无dispatch日志直接续发旧动作 |
| AFTER_DISPATCH_STARTED | 该事件已提交、目标commit前断点效果0；仍按未决先观察，充分ABSENT方可终局 |
| AFTER_TARGET_EFFECT_COMMIT | 目标效果1但响应/receipt可缺；结束worker后新进程实际读MATCH，恢复后仍1 |
| AFTER_READBACK_CAPTURE | 效果1，分别记录fact/receipt是否已提交；未终局必须产生新观察，不复用旧readback改时间 |
| AFTER_RECEIPT_COMMIT | 效果1、完整持久事实/receipt重开可读；重复提交及reconcile业务效果增量0 |

此外观察接受事务全部动作永久预留的原子性、permit发放/单次消费、CLAIMING→target.activate_fence→runtime ACTIVE各中断窗口、未尝试两读/预写资源/最终CAS、reconciliation提交和attempt预登记后崩溃。它们是原R/V不变量的证据窗口，不新增对任意外部平台写者或断电安全的保证。

并发必须同时覆盖竞争claim和临近目标效果的交错。dispatch与claim/takeover使用同一稳定书键的OS效果闸，闸内重验当前owner/generation/头/全书集合，持有至独立target事务commit；target事务核持久fence。存活owner不得因固定sleep或仅lease超时盲抢，回收按已接受“lease过期且原进程实例已退出或受控交接”，不确定则OWNER_BUSY。中断claim不授ACTIVE许可；两库fence不一致保持暂停，旧owner/许可不可继续。

目标计数由独立进程在worker退出后通过目标只读查询取得，核对实际questions/frames/业务映射、目标业务投影、独立效果日志及每action/plan增量；不能只读runtime receipt或让receipt反造目标。runtime与target不得共享SQLite事务。reconcile的目标dispatch和业务效果增量必须为0；允许独立观察事务增加观察元数据/read_sequence，但这些字段不进入业务hash，不能把整个DB文件hash变化当成业务效果。

书级完整性证据必须来自当前受控库的全部run/scope事件、预约、intent、receipt、progress、resolution、pending/hold和资源索引，包含当前交换包未列出的scope；与独立行查询及导出集合对照。保持当前target固定source/scope，跨scope使用保全历史/确定性故障输入，不能切session或register新目标删除旧项。同书解决一项后其他未决仍暂停；合法多书包保留完整历史但不让外书UNKNOWN误停当前书。不得把旧静态R2手写成功图直接导入冒充真实执行链。

## 5. 未尝试专用事务、次数和期限

`commit_unattempted_absence(bundle, request, *, owner_id, generation, asset_root, observer)` 是专用只读事实入口。在另一动作UNKNOWN及BOOK_WRITE_PAUSED下仍可收集事实，但必须当前ACTIVE owner/fence、真实原子PLAN_ACCEPTED/永久预留、INTERRUPTED、受控当前完整事件/hash前缀、精确CAS和动作永久未调用。不能经prepare_action/bind_plan_observation/assert_recovery_plan_ready等写就绪条件绕回派发；无intent/obligation/resolution/permit。

持同书闸完成初检、两次新独立实际读、不可变证据和最终事务；读一生成专用readonly prepared_before，读二须新observation ID/更大read_sequence和实际时钟，可有相同业务version/hash。比较器仍为a02-facts-1；未知前序可能影响C的身份/order/相关完整性时，拒绝CONCLUSIVE_READBACK_REQUIRED，保留progress。完整充分ABSENT方可原子提交UNATTEMPTED_ABSENCE_COMMITTED及fact/event/resource索引，C字段保持null，不解除B UNKNOWN或复活旧计划。

重复相同永久key拒绝UNATTEMPTED_FACT_DUPLICATE，改绑定拒绝CONFLICT，不能作幂等成功。若提交结果UNKNOWN，只能按 `(journal_id,canonical_target_key,action_id)` 查询当前全书context并核对事件/精确资源；不重提探测。CAS漂移不得刷新头自动重试，超时/失败没有已提交fact/event/index，预写orphan和已独立提交观察可保留诊断。

[期限及故障计划](../evidence/A03/review/P2-preparation/deadline-and-fault-plan.json) 记录全部接受值和原API断点。

| 约束 | 批准值及需证实的边界 |
|---|---|
| 普通intent reconcile | 每intent每恢复call最多3次实际只读尝试；读前持久登记，失败/崩溃亦耗次；同call_id重启不重置 |
| 单读 / 单intent / 整call | 2s / 8s / 60s，monotonic绝对最早期限 |
| SQLite busy / 效果闸 / 测试屏障 | 1s / 5s / 5s，均截短到上层剩余预算 |
| owner lease / 续期 | 10s / 2s；不能仅凭lease过期抢存活owner |
| 专用未尝试入口 | 固定2次新读、自动重试0、整入口8s包含闸/两读/文件IO/最终事务，父call60s；不造intent、不消耗或重置其他intent额度 |
| 确定性错误 | 结构/版本/摘要/引用立即拒绝，无重读尝试 |

正式方法须覆盖第3次仍未知与第4次企图、attempt登记后崩溃/同call重启、未到队列项NOT_VISITED、各层实际超时和资源释放。记录真实monotonic起止与剩余期限；harness有界保护，调度误差如实记录，不静默提高批准期限，不把各分步上限叠加为更长许可。显式新call可新预算但必须新实际读，不能自动循环恢复。

原退出码：0=本查询/核对完成或NO_ACTIONS；2=INVALID_INPUT；3=HOLD_PENDING；4=OWNER_BUSY_OR_STALE（含CAS）；5=STORAGE_FAILURE；6=DEADLINE_EXCEEDED；7=ADMISSION_REJECTED；90=INJECTED_PROCESS_EXIT。0不代表下一计划自动执行、质量通过或A03整体接受；原API细错误码与CLI退出码分别记录。

## 6. 正式证据目录和拒绝自证的方法

| 类别 | 正式复验时须保留的证据（本轮均未产生功能实际值） |
|---|---|
| E0 输入/环境 | exact Git提交/blob/长度/SHA、实现允许路径、合同/API/Schema pins、不可变case输入及所有资源；Python/SQLite/依赖/平台、argv/cwd/PYTHONPATH和实际模块__file__ |
| E1 进程 | 父子PID/实例/启动结束、屏障事件和顺序、故障位置与终止方式、退出码/stdout/stderr、各自有限deadline、所有自有进程释放 |
| E2 独立目标 | 两库物理文件/身份/事务窗口、目标业务前后投影与hash、ID/实际效果日志和每action次数、独立读入口与观察ID/序列 |
| E3 当前runtime | anchor/ledger、完整book-key事件/hash链、全部scope/run/预约/intent/义务/原UNKNOWN/receipt/progress/resolution/hold/pending、索引与资源、owner/fence/CAS/attempt队列 |
| E4 独立断言 | 与作者复跑分离的expected/actual、输入扰动及主拒绝层/错误码、效果增量和差异；独立oracle不调用同一实现函数制造expected |
| E5 时序/预算 | monotonic起止/余量、持久call/attempt、读取次数、NOT_VISITED、lease/续期、busy/gate/barrier和跨进程期限证据 |
| E6 范围/报告 | 独立完整scope清单、异常/跳过/未入图谱/未知或零题；新POST_APPLY/BatchReport的精确链、PENDING/NOT_SUBMITTED和progress-only分支 |
| E7 保全/归档 | 原UNKNOWN、原样例/报告/失败/权限拒绝/CRLF字节；转换新旧映射；新脚本错误的原版本与失败日志；统一长度/SHA清单含.log与忽略项、自身排除 |

每例先记录固定初态和独立预期，再经支持的公开入口取得actual；负例尽量只改变受测约束并重算合法摘要，避免只在更早hash错误处被挡住。原69静态案例和3邻例可作覆盖线索，不是P2结果；接受前缀13→14及8→9→10→11只作结构参照，真实完整账本由运行事务生成并独立核对。作者原测试数量、HTTP成功、封签、日志或多个助手一致都不能替代效果边界证据。

## 7. 正式复验等待门与停止条件

正式启动前须由主调度续派全部具体交付：

1. 冻结干净的精确实现提交、实现base/workflow及独立合同版本/验证提交；runtime/公开接缝和报告/证据分别可定位。
2. 执行报告逐项V01–V10通过/失败/未运行、正常/效果后丢响应退出/明确未生效三条可搬运最短命令、环境/实际导入路径及限制。
3. 覆盖报告、脚本、输入/资产、输出、原始日志及忽略文件的统一长度/SHA256清单，自身排除并列说明；旧样例/UNKNOWN/失败证据保全证明。
4. 执行者自有进程/会话已释放声明及主调度前检；提供明确的未来验收隔离导出目录、复验范围和正式授权。

缺项不读取浮动实现填补、不自行轮询。正式收到后先验证原始Git字节及交付门，再复跑作者命令和独立矩阵；最小反例、关键功能未运行或只能永久暂停而不能完成批准继续路径，不能记整项通过。届时仅向 `docs/tasks/A03-review-report.md`、`docs/evidence/A03/review/P2/` 交 ACCEPTED/REWORK/BLOCKED 建议；独立验收者不集成、不推送、不改调度状态，不替B确认或自行释放I01。

允许实现路径以冻结派单为准，先检diff而不追加实现范围；不接受根依赖/父入口/source/geometry/浏览器/A02身份示例工具或旧证据改动。A02并行Git可用性修复不是本P2依赖。真实来源S01、Pillow依赖、B共同确认、真实平台恢复/识别/质量/成本继续未解决，A05题22不重放。

## 8. 本轮已做的文档核验与释放

本轮实际只运行有界Git/Python文档工具：20份冻结输入raw blob/摘要、2份接受溯源摘要、七Schema pins、28行原文映射/全NOT_RUN状态、链接、清单及旧审查文件保全检查。准备脚本不import业务模块、不打开任何SQLite/目标；这些检查不属于V/R功能结果。详见 [准备核验记录](../evidence/A03/review/P2-preparation/preparation-check.json)、[范围声明](../evidence/A03/review/P2-preparation/scope-declaration.json) 和 [统一清单](../evidence/A03/review/P2-preparation/sha256-manifest.json)。

```powershell
# 仅核对本准备档案及输入/旧证据字节，不导入或执行实现
python -B D:/1800/docs/evidence/A03/review/P2-preparation/scripts/verify_preparation.py
```

两个只读文档助手已完成；本轮测试/目标worker启动0、剩余自有后台进程0、未终止他人进程。浏览器、网络、平台、凭据/profile、OCR、业务模型API、数据库/恢复/效果执行均0；真实质量和模型成本未测。未派单、未联系执行者/B/其他chat、未改源码/合同/状态/旧证据、未提交/集成/推送、未创建轮询或自动化。准备交付后结束等待，P2功能验收仍未开始。
'''
assert all(not s.endswith((' ','\t')) for s in text.splitlines())
with REPORT.open('x',encoding='utf-8',newline='\n') as f:f.write(text)
print(json.dumps({'result':'P2_PREPARATION_REPORT_WRITTEN','path':str(REPORT),'functional_actuals':'ALL_NOT_RUN'}))
