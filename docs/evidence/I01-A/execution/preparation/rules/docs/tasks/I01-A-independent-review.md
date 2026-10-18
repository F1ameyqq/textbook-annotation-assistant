# I01-A：固定三路径的独立验收

2026-10-18。配套[执行任务](I01-A-minimal-integration.md)。只判断固定组合上的 A 侧离线消费与三条单题路径，不写产品、不重新验收旧A03、不管理B。A03-R1原有限接受不自动成为I01通过；I01通过也不扩展到真实来源/平台、内容、OCR或联合联调。

## 等待条件与固定对象

- 组合基线：`a1c3c3b2d452ecbdf5c57a8b7372e7d53de0f8d8`，由调度替换并释放；预计作者目录 `D:/1800-worktrees/i01-a`，不在作者目录运行或修改文件。
- 交付前读取主目录当前AGENTS、coordination、development-plan及两份I01任务，只确认边界并回复 `WAITING_FIXED_DELIVERY`；不审浮动代码、不启动测试/产品/SQL、不自行轮询或联系作者，也不创建准备报告。
- 仅收到调度给定的确切组合提交、作者固定候选/最终交付提交、报告与manifest路径/SHA256、实际运行入口及自有资源释放证明后开始。缺一项时说明缺件；执行completed或一份成功日志不替代释放与固定交付。
- 在自己的新隔离目录取固定raw Git对象，核对允许路径、产品/pins与组合基线、既有A01/A02/D01保全，以及A03产品 `6097a06de937fee8876feccedf46920510850b83` 的固定身份。所有Git命令带 `-c core.longpaths=true`；不读取作者活源，不将已存在作者状态复制/改标为自己的正向起点。

## 独立检查范围

先核对作者真正执行的对象、计数、首次失败/纠正及语义，再运行自己的同一有限路径。自己的完整运行使用独立book/ledger/target身份，最多 **3个fresh native target、3次dispatch**，每路径1题、最多1target/1dispatch；作者和独立消耗分别记录，不能互借。每个具名路径只一次，不运行旧M/L/G/F或额外场景，也不因上限有余量而跑满其他矩阵。

| 项目 | 必要独立证据与判断 |
| --- | --- |
| A01公共消费 | 从固定组合提交取同一完整单书包，自己的真实子进程各运行一次公共C01 CLI和已有A01消费者；验证真实资源bytes、完整图像解码、书籍/页绑定、两入口一致以及coverage_eligible=false。不得以结构校验或作者输出替代。 |
| Native来源边界 | 固定native夹具明确SYNTHETIC，独立记录其SourceBundle/EvidenceBundle/QuestionGraph、政策、版本/pins及实际入口。A01公共消费与native桩分别判断，不把两组成功拼成真实A01→native闭环或B共同接受。 |
| N正常 | 既有真实PRE/TARGET/planner→先持久intent/permit后独立目标效果→正式读回/回执/报告。一题两框、APPLIED、pending=0、最多1dispatch。 |
| E可修正异常 | 真实旧候选在首次dispatch前遇到固定前置异常；原拒绝/hold与纠正有事实，旧候选0dispatch。若用hold，保留只读候选、最终再读/CAS及清后新INITIAL链。真正新PRE/TARGET/plan后最多1dispatch，不能拿旧proof或静默改旧plan当新规划。 |
| U UNKNOWN恢复 | 真实一次dispatch已有效果，执行确认丢失/读回unavailable使正式UNKNOWN/暂停持久化；先释放原进程，再由新PID正常重开原身份。一个冻结call、max_attempts=1的新鲜完整观察得到MATCH；恢复/报告不dispatch，原UNKNOWN、intent/receipt及解决链继续存在，最终pending=0。 |
| 报告与分母 | 三路径正式/诊断报告角色真实，完整分母及原失败/未决事实不遗漏；content_check_status=PENDING、submission_status=NOT_SUBMITTED。记录实际报告读次数，不能为了证据重复publish。 |
| 次数与释放 | target创建、dispatch调用、实际目标变化、operator变更、观察/reconcile/report分开计数；作者的失败/纠正不重置消耗。自有进程已真实wait/回收、keeper已stop/join、owner/PID为空、lease=0，业务pending/hold不因释放而删除。 |

执行任务允许首次冻结前以既有等价API完成驱动选择。按实际已冻结入口核对同一业务语义，不因参数名不同制造新要求；`response_lost`没有专用参数时，“真实效果＋unavailable执行读回→UNKNOWN→新进程MATCH”可满足本任务。不能把凭空构造UNKNOWN、直接写SQL或跳过产品守卫当等价。

用户转交的 B 侧状态仍将A公共消费者及接收/联调验证列为 `PENDING_A`。检查作者交付的可导入A接口/校验器、固定消费者调用与适用版本说明是否准确，但本次固定桩通过不能关闭该状态。B内部0.4/0.5/0.6/0.7的显式适配/拒绝方案由调度补充或独立任务处理；不自行解释或支持这些版本，也不扩大本轮三路径、target或dispatch预算。

## 运行、证据与停止条件

独立运行消费已冻结的输入、驱动和正常产品入口；可以增加自己的外部记录/断言和隔离路由，不替换产品业务函数、故障语义、预期或守卫，不修作者候选。执行前固定自己的路由、身份、输入摘要和三个路径顺序。

子worker180秒、每阶段父240秒及原产品内部期限保持。记录真实wall/CPU与退出，不把未超时等同完整功能正确。遇业务失败、语义不符、产品/依赖缺件或超时即保留确切现场，停止依赖步骤，不改产品/驱动后自行再跑业务。自己的纯静态索引/记录工具错误可保留首次错误后修正静态收口，不能借机新建target、重跑已执行业务或补造未记录的PID/raw流。

复核作者最多一次驱动纠正是否在原3target/3dispatch累计上限内，并且只处理失败项/未执行后继；已成功路径不得重跑。不能因为作者执行或本次独立失败就自动给第三包、追加A03矩阵或重新释放旧pending库。

必要双库原件沿用固定T1 capture，在自有业务/keeper静止边界留存；SQL只读自己的静止immutable副本，保留原件前后摘要。按提交/manifest引用作者与旧A03证据，不打开作者primary、不访问旧T3/L1活源、不复制旧活源取得正向资格，不回滚活源以得到干净工作树。

结论逐项区分实际复现、静态继承、作者固定证据、结构/引用/值层拒绝和未执行；只到前层就只报告前层。源身份、pins与实际导入必须一致，不能只用测试数量、HTTP/exit0或多代理一致当验收。

## 交付和结论边界

仅新增 `docs/tasks/I01-A-review-report.md` 与 `docs/evidence/I01-A/review/`，不改作者文件、旧证据、产品、pins、根依赖、调度JSON或主目录Git索引，不提交、不推送、不发对话消息。报告及SHA256/长度manifest至少包含：

- 确切组合/候选/交付身份、输入与实际执行字节、正常导入/pins核对。
- A01两次实际CLI消费与native固定桩分别列出的版本、边界和结果。
- 独立N/E/U真实命令、进程/原始流、关键产物/静止双库及逐项判断；作者/独立各自target、dispatch、效果、operator和读计数。
- 原UNKNOWN与解决链、E旧候选0dispatch及新计划依据、完整分母和PENDING/NOT_SUBMITTED。
- 首次工具/业务失败、未执行项及原因、实际资源释放与限制，最短复现说明标明既有输出不可原地重跑。

给出有限 `ACCEPTED` / `REWORK` / `BLOCKED` 结论；有问题须指出确切输入、提交、到达层和缺失行为。A03内部原有限接受保持原边界，I01整体调度接受、主目录集成与对外表述由调度决定。不能自行把作者REVIEW改为接受，不能把A侧离线结果写成B开发接受或双方共同联调。

本任务零平台/browser/profile/凭据/网络模型/付费/OCR/书级提交/A05题22，零B管理、旧A03重验或旧pending恢复。A04真实平台、B算法、OCR/内容、S01与DB迁移保持范围外；不拿这些未获授权的工作阻塞本任务已明确的有限离线结论。
