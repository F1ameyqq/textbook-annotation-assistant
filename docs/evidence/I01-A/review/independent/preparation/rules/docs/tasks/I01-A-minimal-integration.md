# I01-A：三个固定桩路径的 A 侧离线集成

2026-10-18。执行任务，与[独立验收](I01-A-independent-review.md)配套。A03-R1 的原有限范围已由调度接受；本任务验证固定组合中的 A 侧消费与编排，不重新验收 A03，不要求先交设计评审。完成静态准备、冻结可运行候选后直接执行下列有界集成。

## 基线与启动条件

- 集成基线：`a1c3c3b2d452ecbdf5c57a8b7372e7d53de0f8d8`。调度完成46个路径的隔离组合检查后，替换为确切完整提交并明确释放 I01-A；占位符未替换或未释放时，只读准备，不运行测试、产品、SQL或业务。
- A03 产品身份：`6097a06de937fee8876feccedf46920510850b83`；最终交付：`19ab03c849bfab3dcde2dc86be37c59f3add1ebe`。组合中同时保留已集成的 A01/A02/D01；以调度给出的组合清单核对，不用作者旧树覆盖主线。
- 预计执行目录：`D:/1800-worktrees/i01-a`，独立分支及实际目录由调度登记。执行者只在该目录写自己的交付，不修改 `D:/1800` 产品、调度 JSON 或本任务单。执行与独立验收使用不同目录和自有状态。
- 先读主目录当前 AGENTS、[coordination](../coordination.md)、[development-plan](../development-plan.md)、[architecture](../architecture.md)、[contracts-v1](../contracts-v1.md)及本任务。引用 A03 的[最终差量独立报告](A03-R1-final-delta-review-report.md)及其调度接受边界，不唤醒退役 A03 对话。

## 写入范围与不可变依赖

唯一新增范围为 `examples/i01/`、`tests/fixtures/i01/`、`tests/test_i01*.py`、`docs/evidence/I01-A/execution/`、`docs/tasks/I01-A-execution-report.md`。可以在这些路径实现最小编排、固定夹具和结果核对；不建服务、通用工作台或新产品 API。

全部 `src/`、A03 implementation/schema/oracle/profile/adoption pins、根依赖与包配置、既有 A01/A02/A03 示例及测试、旧报告/证据只读。依赖与实际执行字节以固定 Git raw blobs 核对；所有 Git 命令带 `-c core.longpaths=true`，不推送。保留原换行和摘要，不通过改 pins、改预期、关闭验证、伪造 context/permit、monkeypatch 产品、直接 SQL 改状态或重标旧库来接通流程。

可引用已有函数/驱动实现并写薄编排；必须正常导入完整产品。若某个拟用驱动参数或 API 不存在，首次业务冻结前可以静态选择已存在、语义等价的 API，记录实际入口与选择依据，不另设设计审批。替代选择仍须实现本任务相同业务事实与次数上限。若现有产品无法支持，固定具体接缝/反例，停止依赖它的执行并交调度；不能为继续 I01 修改产品或重开 A03 M/L/G/F。

## 固定输入与两个消费边界

1. **A01 公共消费。** 从组合提交提取 `examples/a01/R3/bundles/46007447/` 的固定原件到本任务独立输入目录，记录整包清单、源提交和摘要。真实子进程各调用一次公共 C01 CLI 与现有 A01 消费者，校验资源 bytes、完整图像解码、书籍/页映射和两入口一致性；不重新导入来源、不联网、不调用 build/verify 全套：

   ```powershell
   # 在已登记的 I01-A 工作目录，source-copy 是从固定提交提取的完整单书包。
   $env:PYTHONPATH = (Join-Path (Get-Location).Path 'src')
   $env:PYTHONDONTWRITEBYTECODE = '1'
   python -X utf8 -B -m annotation.contracts.cli validate tests/fixtures/i01/source-copy/exchange.json
   python -X utf8 -B examples/a01/consume.py tests/fixtures/i01/source-copy/exchange.json --book-id 46007447
   ```

   不使用 `--structure-only`。保留 `coverage_eligible=false`，原书号在这里仅标识离线档案，不提供线上操作权限。执行路径以实际固定目录为准，不能把示例命令的输出补写为已运行。
2. **Native 固定桩。** 从已接受单题 synthetic 语言派生三个明确标为 SYNTHETIC 的独立固定夹具，每条路径一题、一张32×32 PGM、stem/answer两框，固定 SourceBundle/EvidenceBundle/QuestionGraph及政策，正常生成 PRE/TARGET/plan。产品仍为 `A_INTERNAL_FIXED_SYNTHETIC_ONLY`、fresh-native-only、LEGACY_INITIAL_ONLY；不把 A01 真实归档、B 输出或旧 UNKNOWN 改标为 synthetic。

报告必须分别列 A01 公共消费与 native 固定桩的版本、来源、真实入口和结果。这是 A 侧离线固定桩集成，**不宣称真实 A01→native 闭环、B 共同合同或联合联调通过**；S01、A04真实平台、OCR和内容验证不作为本任务阻塞，也不因本任务通过而变为通过。

用户转交的 B 侧状态中，A 公共消费者及接收/联调验证仍为 `PENDING_A`；本任务的固定桩通过不能关闭该状态。I01交付资料应列出本组合中可导入的A合同/校验器、固定消费者及实际调用方式和适用版本，供后续接收验证使用；B内部0.4/0.5/0.6/0.7的显式适配或拒绝方案等待调度补充或独立任务，不在本次修改/支持范围，不猜测版本语义，不以C01/native样例通过替代B包兼容性证明。

## 三条路径与累计硬上限

执行者整个任务最多 **3个 fresh native target、3次实际 dispatch**，每条路径最多1个target/1题/1次dispatch；失败、超时和纠正均不重置计数。target创建即计起点，不因未dispatch而删除记录。每条路径独立book/ledger/target身份；query/export/重开/恢复复用其同一状态，不新建业务起点。

| 路径 | 必须发生的事实 | 上限与完成条件 |
| --- | --- | --- |
| N 正常 | 固定桩→真实五检查/PRE→TARGET→正常planner→持久intent/permit→独立目标效果与读回→正式回执/报告。 | 1个fresh target、1次dispatch；一题两框与计划一致，正式结果APPLIED，pending=0。查询/导出不新增效果。 |
| E 可修正异常 | 在首次dispatch前生成真实旧候选并发现受控目标漂移或等价的可修正前置异常，保留拒绝/hold事实。通过既有正常API完成限定纠正；若进入hold，遵守只读候选、最终再读/CAS、清除后全新INITIAL/PRE/TARGET/plan。旧候选/证明不充当新执行许可。 | 1个fresh target；旧候选0次dispatch，真正新计划最多1次dispatch。新旧计划及依赖可区分，最终一题APPLIED；无新增题型、内容修正工作台或未生效后再发变体。 |
| U UNKNOWN恢复 | 一次真实dispatch已在自有synthetic目标产生效果，但响应丢失或执行读回unavailable使正式结果为UNKNOWN；持久原intent/receipt/progress和暂停。释放原进程后，新进程正常打开原身份，以新鲜独立完整读回得到MATCH并提交解决链。 | 1个fresh target、全路径1次dispatch；reconcile使用一个冻结call、max_attempts=1，MATCH后0次重发。最终pending=0，原UNKNOWN及其正式引用保留，不能改写成最初就成功。 |

E 首选使用现有受控synthetic目标变更和hold恢复API；静态检查若表明该组合有额外业务前提，可在首次冻结前选择已有等价前置拒绝/纠正入口，仍必须证明旧候选未dispatch和真新计划可执行。U 可使用现有“实际效果＋unavailable执行读回”接口表示丢失确认；不能强求不存在的 `response_lost` 参数，也不能直接写入一个UNKNOWN结果。实际故障层、目标效果、dispatch调用和独立读分别计数。

模拟operator变更单列，不冒充dispatch或隐去其影响；不额外运行旧动作拒绝、旧证明失败、另书隔离、预算耗尽等新业务矩阵。正式报告沿用已有入口；正常/纠正路径避免重复publish，U终局后需要报告时只做一次正式新鲜报告观察。所有报告保留完整分母、`content_check_status=PENDING`、`submission_status=NOT_SUBMITTED`。

## 冻结、一次运行与纠正边界

基线释放后先完成静态接线、输入/路径/pins/API核对和不创建target的测试。冻结业务候选提交、夹具/驱动/依赖清单、三路径顺序、故障选择及计数规则后，三路径首轮各运行一次；不为性能、录屏或取证追加业务。

采用子worker180秒、每阶段父240秒防挂死预算，在首次冻结前固定；这不是业务SLA。read2秒、entry8秒、gate5秒、lease10秒/renew2秒及产品PRE/currentness/恢复期限不放宽。一个父进程的总记录预算不能延长其内部阶段预算。超时保留现场并终止/回收自有进程，不静默延长重跑。

若首轮失败仅来自新驱动/集成胶水，允许**至多一次有界纠正**，最多两个冻结驱动候选。保留首次代码、输入、原始流、计数及状态；仅处理失败项和未执行后继，已成功且未受影响的路径不重跑。累计仍限3个target/3dispatch：已经创建的target及已调用的dispatch均消耗额度，不用新目录/新ID恢复次数。只有现有正常API和原身份允许安全继续、且剩余额度足够，才可继续同一自有状态；UNKNOWN先对账，不能再次dispatch。无法在这些约束内纠正，或第二次仍失败，固定交接，不自动第三包。

产品错误、合同不相容、pins不符或来源身份不符不是驱动修补授权。保全确切反例并停止依赖步骤，仍可完成不依赖该步骤的静态说明；不自修产品、不调用作者补跑、不变更通过标准。

## 必要证据、释放与交付

- 保存基线/候选提交、固定输入及SHA256/长度、A01包源身份、实际导入路径/bytes/pins、argv/cwd/PID/raw stdout/stderr/exit/timeout/wait，以及N/E/U逐阶段真实结果。
- 各路径记录target创建、plan/action/intent/permit、dispatch调用与实际目标变更、operator变更、正式/失败观察、reconcile及报告读次数；不以effects表行数等同新增题数。U保留UNKNOWN前后原件、不同PID和原历史引用，E保留旧候选0dispatch与新链依据。
- 沿用固定T1 capture，在自有写者和keeper真实静止边界保存必要双库原件；SQL只读自有静止immutable副本。顺序双库复制不称原子快照。不打开、恢复、迁移或清锁任何旧A03/T3/L1 pending现场。
- 记录全部自有进程退出/回收、keeper停止/join、owner/PID为空、lease=0及释放状态。pending/hold是业务事实，不能为释放删除。清单不纳入凭据/profile或未脱敏资料。
- 交付 `docs/tasks/I01-A-execution-report.md` 与 `docs/evidence/I01-A/execution/manifest.json`，列确切候选/交付提交、实际最短复现命令（已存在输出不可原地重跑）、输入输出、三路径逐项结果、预算、第一次失败及纠正、限制和释放。作者只交 `REVIEW` / `REWORK` / `BLOCKED`；独立验收和调度才决定接受及集成。

零平台/browser/profile/凭据/网络模型/付费/OCR/书级提交/A05题22，零B派单或外部消息，零旧业务恢复或旧A03全量重验。不得修改调度state、主目录Git索引或其他任务文件；执行只在自己的分支提交获准产物，不推送。
