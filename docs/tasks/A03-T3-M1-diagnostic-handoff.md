# A03-T3 M1：一次有界计时与线程栈诊断

2026-10-18。调度采用[独立静态复核](A03-T3-M-timeout-review-report.md)中的单一诊断建议，续派现有 T3 执行对话 `01a14ccf-afa4-7260-a2a2-a47633772ae5`，xhigh、model 沿用。**本轮交付诊断事实和最小修复建议；不改产品、不续跑其他业务例，不把诊断完成判为 M1 通过。** 独立复核对话继续保留，待固定交付和释放后另行续派。

## 依据与调度判断

- 工作目录 `D:/1800-worktrees/a03-t3`，分支 `codex/a03-t3-closure`；起点必须为干净的 `3f39a117b1b98e85c5a449a07f13b3490ef77e18`。产品与固定输入仍为首次候选 `c73070884476dc2edcb952d88e4f6ed356b74ae8` 的原始字节；capture 工具保持已接受 raw SHA256 `3e07d56f409d8203c42f252f7a2900e902e31f56e1ff5fc7475335d33d0b042b`。
- 独立报告 SHA256 `538fdea9afed67640149ee83b8406725086f7e36d266a56b9fa118a619feb85a`。调度核对报告摘要和六个必要 Git blobs，复核 `execute_api` 顺序、第三动作 prepared-before 资源及 prepare/commit_intent 边界，记录见[调度检查](../evidence/coordinator/heartbeat-20261018-0452/timeout-review-check.json)。
- 已确定：第二结果返回后进入第三 prepare，第三 prepared-before 资源已落盘；未确定 prepare 是否返回、是否进入 commit_intent 的哪一段。重复验证、schema/pin 读取及 gate/事务等待是候选原因，均不能当作已证根因。**静态复核已收口，功能仍 REWORK，允许开展下述一次诊断。**
- 旧 M1 的45.031秒失败、1目标/2dispatch/2effect、崩溃 DB+journal、清理后 SQL 与缺少终止栈等限制保持原样。禁止对旧现场执行 open/recover/claim/reconcile 或重封原263成员。旧包装日志缺口不成为本轮补跑理由。

## 唯一诊断与预算

只在**新目录、新目标**重现原 M1 三动作顺序一次，输入、planner、API 顺序、预期、故障选项与原候选一致。新增 fresh target/业务起点 **≤1**、dispatch **≤3**、实际 effect **≤3**，是上限，不凑数。reconcile=0、旧库恢复=0、M2/M3=0、publisher=0、finish/query/旧计划重放检查=0。M1 execute_api 返回后只保留结果、静止取证并释放，不进入原正常报告/finish 后继。

总计本分支历史与本次诊断最多2个起点、5次dispatch；历史2次效果不被抹去。诊断同样失败也到此停止，不换名、不委派、不新增第二起点，不自动优化产品再跑。没有新用户决定等待点；完成下面驱动静态准备、冻结后即可执行授权的一次诊断。

唯一允许的驱动变化：`examples/a03/T3-closure/run.py` 中显式诊断模式及小型计时/日志辅助；若释放路径确需参数适配，可新增该目录下 `diagnostic_release.py`，只针对本次目录使用原正常释放 API。不要改原 `failure_closure.py`、产品 `src/`、pins/schema/oracle、输入、capture、根依赖、旧证据或旧执行报告。不得 monkeypatch 产品、复制产品算法或通过减少校验取得完成。交付前后核对禁止改动路径的 raw Git 字节一致。

1. 增加逐步 JSONL，记录 worker 开始、导入、init/claim、pre_plan、原两个 capture 的前后，以及 execute_api 的 accept_plan 和每个动作 context-load/import、validate、prepare、commit_intent、permit、dispatch、observe、compare、commit_action_result 的 ENTER/EXIT/ERROR。使用 `time_ns`、`monotonic_ns`、`process_time_ns`、`thread_time_ns`、PID/thread/action/index；立即 flush。只读 keeper 内存状态，不额外调用 keeper.check/renew、目标观察或验证来生成日志，不改变控制流。异常只记录后原样抛出。
2. 在 before-execute capture 完成后、execute_api 前，对预先 `xb` 打开的独立日志启用标准库 `faulthandler.dump_traceback_later(5, repeat=True, file=..., exit=False)`。正常或异常退出先 cancel，再关闭日志，后续取证前取消；无需新增 Python 定时线程。先做一次不导入产品、无业务的标准库/路径检查与 AST 静态检查；不可用就交缺口，不安装替代工具。探针本身的开销作为限制记录。
3. 保持原**子45秒、父90秒**和 gate/lease/读/PRE 期限；原父预算覆盖原准备与执行，不把加日志时间排除。到期仍 kill/wait，日志采集不延长时限。父在 kill 前后记录已刷日志长度/摘要，注明前者为活动日志非原子快照。不得循环等待补齐日志。
4. 首次业务前冻结诊断候选，按 raw Git 生成运行视图，记录代码/输入/capture/pins 和实际 imports。候选后不得继续改正在运行的代码。只启动显式诊断模式，不执行原五例 batch。路径必须为新 `docs/evidence/A03/T3/execution/M1-diagnostic/`，使用排他创建，发现已存在现场则停止核对，不覆盖或换路径续跑。静态准备错误只可在确认零业务起点后修正一次，保留首错；业务开始后无重试预算。
5. 本轮同时授权**新诊断现场**的原正常释放路径：超时先确认自有 worker kill/wait，按静止边界逐字节保全 runtime DB、全部 sidecar 和 target DB，记录这不是跨库原子 SQL 快照；随后最多一次 normal open/claim/release，不 dispatch/reconcile/publish。有 journal 时先保留原件，再正常释放，最后采用原 capture，不重复此前“先 capture 拒绝 journal”的尝试。若正常路径失败，保留错误、记录残留状态并停止，不强清 owner/锁/DB。成功与失败都区分原终止现场和正常清理后状态。所有自有 keeper/进程退出及 owner 释放状态如实交付。

## 交付与独立复核边界

交付 `docs/tasks/A03-T3-M1-diagnostic-report.md`：确切起点、候选、最终提交、运行命令、逐调用 wall/CPU、最后 ENTER/EXIT/ERROR、实际全部线程栈对应的固定代码位置、实际 init/dispatch/effect/read/pending 计数和释放、根因的证据与推测、一个最小产品修复建议及它实际需要的文件/验证范围。若仍无法归因，明确不足，不自动追加试验。

保留小型新证据索引、原始日志/流/进程实际退出、必要现场文件和固定运行字节。索引只针对本轮新增内容，避免自引用，沿用旧263成员的已验身份。无需另建大型审计器或重新跑历史矩阵；不以 checker PASS 代替业务事实。

调度收到固定候选和释放后，仅续派现有独立验收者复核诊断差异、产品/输入不变、计时/栈解释及预算，不重复本轮业务起点。根据具体证据另固定产品修复/剩余 M 验证任务。T1/T2、原28项、L/G/F 和 I01 不在本次复验范围；A03 仍 REWORK、I01 未释放。

所有 Git 调用显式 `-c core.longpaths=true`；Python `-X utf8`。field reset=`NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`。无网络、平台/profile/凭据、安装、付费模型、OCR、原始视频、推送、A05题22或书级提交。不得联系 B、旧 A03 对话或另行委派。仅提交自身白名单改动，完成后结束等待。
