# A03-T3 M1 超时独立静态复核

2026-10-18（Asia/Shanghai）。**REWORK；本轮静态复核完成，超时根因尚未证明。** 能把执行位置缩至第三动作prepare的资源落盘之后、第三intent提交之前；没有足够证据指定一个产品修复。下一最小行动是下文一轮有界计时/栈诊断，须调度另行采用，本轮未执行。整个M、A03和I01均未通过。

## 固定身份与证据层

- 复核workflow：`94844ddf1af3264f7fad5a3cd5db0b7a0f3a7964` 中 `docs/tasks/A03-T3-M-timeout-review-handoff.md`。
- 固定交付T：`3f39a117b1b98e85c5a449a07f13b3490ef77e18`；首次业务前候选C：`c73070884476dc2edcb952d88e4f6ed356b74ae8`；原K：`62a023a1c88c20d884a61f38d1ad995b0908b74c`。
- 实施范围仍按 `4fa7237d1114ed2c89f65cbb28579a8956812062:docs/tasks/A03-T3-M-implementation-handoff.md`，不增加45/90秒或产品gate/lease期限。
- 交付报告raw SHA256：`7d9c35308b594c2d73d9327556f1d77b09be3cbe30b89f211df29c12758bc522`；原manifest：`f88adb018dc19bcae5c7fcce4b566a374773207e9c6e192e0404dd8fa6e14708`。本轮只核对这两个身份及必要引用，不重验/重封263成员。

下文源码行号均指C。现场读取均为T中的既有JSON、资源JSON和SQL导出；**没有连接任何数据库，没有打开、恢复或复制崩溃DB/journal**。引用身份与静态Git读取记录见[read-record](../evidence/A03/T3/review-M-timeout/read-record.json)，提炼后的时间线见[timeline](../evidence/A03/T3/review-M-timeout/timeline.json)。

SQL.json来自 `validation/author-01/cases/M1/captures/after-cleanup-release-02/`，是正常open/claim/release后的导出；不是崩溃瞬间SQL。`failure-closure-02/before-owner-release.json`也是kill后正常native open后的public读取，不能把文件名中的before理解为未发生journal恢复。原崩溃DB+journal与其缺少standalone SQL的限制保持原记录。

## 最后完成与下一待完成步骤

worker PID54532的记录起点为12:24:00.603889，45.031秒被watchdog终止。下表时间为Asia/Shanghai；相对时间由记录的wall-clock差计算，不是各API的独立耗时测量。event.recorded_at也不等于函数返回时刻。

| 已有事实 | 本地时间 / 约相对起点 |
| --- | --- |
| PLAN_STARTED，三动作已预约 | 12:24:09.879475 / +9.276秒 |
| 第1动作prepare观察，read_sequence=2 | 12:24:10.768575 / +10.165秒 |
| 第1intent提交；第1结果提交 | 12:24:15.335299 / +14.731秒；12:24:22.194232 / +21.590秒 |
| 第2动作prepare观察，read_sequence=4 | 12:24:23.739999 / +23.136秒 |
| 第2intent提交；第2结果sequence15提交 | 12:24:28.864418 / +28.261秒；12:24:37.616388 / +37.012秒 |
| 第3动作prepare观察，read_sequence=6、epoch2 | 12:24:40.116259 / +39.512秒 |
| 强制终止 | elapsed=45.031秒；start wall clock加elapsed约12:24:45.634889，并非独立kill时间戳 |

更强的定位证据是T中M1包内 `assets/runtime/607f608edbd244d2363e18dc5cce5d217e6ff50f1cf0432eae130c0d3eed8faa.json`：format为 `a03-prepared-before-1`，绑定第三动作 `action-a02-492fda42c9320721d4da6f1ebffa148c`、观察 `prepare-2911e4696fd544039458ecfa4b26c7d0` 和read_sequence6。完整路径/摘要见read-record。它由 `delivery/mock/persistent.py:537–544` 的正常prepare路径产生，证明第三次observe_target、snapshot_from_observation及prepared-before写入已完成。

实际M1使用的是 `examples/a03/T3-closure/run.py:209–231` 的手工API编排 `execute_api`，**不是**导入后未在M1调用的 `runtime.recovery.run_plan`。该顺序证明：第二次commit_action_result已经返回并判APPLIED，随后第三轮load_book_context、import_book_context、显式_validate、prepare前段均已到达；第二次结果后的progress也已在导出中。不能仅把停顿泛指为“第二次结果提交”。

现在不能区分以下两个正常路径子区间：

1. `persistent.py:545–575`：第三prepare的context读取、append_artifacts、bind_plan_observation、PreparedAction摘要/登记及返回；
2. 若prepare已经返回，`run.py:218`调用的 `storage/__init__.py:619–665`：commit_intent的守卫、gate/事务、verify_prepared_action、资源/快照闭包和intent提交前工作。

第三intent/action更新未提交：第三action仍RESERVED，intent/fact为空；没有第三DISPATCH_STARTED或effect。journal存在不能证明它属于哪个线程/事务，更不能证明第三intent曾完整提交后回滚。没有终止前栈及prepare/commit_intent返回标记，以上边界不能继续收窄成某一行。

常规路径中，下一尚未完成的持久步骤是第三个WRITE_INTENT_COMMITTED，不是第三dispatch或publisher。execute_api返回后才写execution.json、调用before-report capture及publish（run.py:258–265）；没有证据指向这些后继。异常处理/清理若在kill时进行，仍须栈或异常标记才能识别，不能据空stderr绝对排除。

## 静态开销、锁与可证明范围

**重复整包验证是可定位事实，是否主耗时仍是假设。** `storage/__init__.py:109–111` 的一次_validate先调用bridge_for：`native.py:68–71`→`a03_native/__init__.py:111–117`，其中_issue_context先执行完整_validate_value；随后 `contracts/recovery.py:1011–1015` 又进入validate_native_bundle，后者在 `a03_native/__init__.py:170–175` 再执行一次_validate_value。每次完整校验包含StaticPackage、另一套恢复闭包、scope/intent/resolution/receipt/progress与legacy投影（134–156行）。prepare及verify_prepared_action还重复调用公共校验/计划绑定（persistent.py:523、527、560–563、601、624–627）。它们是优先计时点，不能凭源码重复次数换算出本例秒数。

其他相关重复读取：`a03_native/__init__.py:100–103,72–90` 每次_registry都重新选择codec、读并哈希schema/implementation/API/oracle等pins；NativeSchemas.check（161–167行）重新读取六份schema文档。`_closure.py:372–377`逐消费者扫描再扫描evidence，恢复 `_Closure.check:200–203`也明确逐消费者独立遍历。历史增长可使工作增多，但没有CPU/调用计数，不能宣布“递归爆炸”或无限环；逐消费者声明/book/scope检查本身不能因优化而共享豁免。

**不成立的删校验捷径**：native.py:518–525在追加前做完整_validate，而父类 `storage/__init__.py:514–521`只是索引/保存，没有再做一次完整验证。不能误认父类会兜底，直接删掉native._append的验证。该模式在K已存在，不是本轮新增的已证语义回归。

锁的静态边界是：BookEffectGate使用同路径RLock及重入深度（persistent.py:113–181），取锁上限5秒；SQLite连接busy_timeout=1000ms、BEGIN IMMEDIATE与commit/rollback/finally关闭（storage:142–167）；keeper每2秒走gate/事务renew，stop/join最多7秒（lease.py:15–35）。commit_intent/结果/projection会在gate/写事务中进行较重校验，可能阻塞renew或等待I/O；但没有锁拥有者/等待栈，不存在可据本材料证明的闭环死锁。第三prepare观察后只剩约5.519秒，时间窗口既容得下部分校验也容得下锁等待，45秒不能决定分类。

驱动另有静态差异：execute_api不逐动作检查LeaseKeeper.error，也没有调用前后计时；产品run_plan则有keeper.check/renew。前者不足以解释本次超时，更不证明lease绕过或额外效果；动态owner/fence守卫仍存在。下一诊断应记录当前keeper状态，不先改调度顺序来“修复”未经证明的根因。

**本轮可确定的问题是诊断缺口**：run.py:30–49在45秒kill前不采栈；209–231没有阶段返回标记。尚无可直接采纳的产品语义修复。若后续计时确认重复校验占主导，可在私有的同一次调用内复用完整验证结果/不可变schema解析，最小关注 `a03_native/__init__.py::_issue_context/validate_native_bundle/NativeSchemas` 与storage的桥接调用；须保持实际字节/pins、当前owner/head/fence和每消费者闭包，不能跨调用缓存“已通过”或放宽guard。此处是待证优化方向，不是本轮修复授权。

## 一个待调度采用的最小诊断方案

只针对新建的一个M1诊断现场；产品、输入、预期继续固定C原字节，另冻结新增诊断驱动的提交与实际执行摘要。**新增fresh target≤1，dispatch≤3、实际effect≤3；reconcile=0、旧库恢复=0，不进入M2/M3或其后继。** 三动作是复现原顺序所需上界，不能为凑数或补旧现场发效果。这是另待采用的诊断范围，本轮没有运行。

1. 仅在新诊断驱动run.py加入轻量JSONL：worker开始、导入/init/claim、pre_plan与两次原capture边界，以及execute_api每动作的context-load/import、validate、prepare、commit_intent、permit、dispatch、observe、compare、commit_action_result的ENTER/EXIT/ERROR。每行保存action/index、time_ns、monotonic_ns、process_time_ns、thread_time_ns及当前keeper状态；立即flush。计时包围真实原API，不monkeypatch产品、不复制算法、不加目标观察或重试。CPU/wall差只作等待线索，不单独证明死锁。
2. 在before-execute capture完成后、进入execute_api前，对预先以xb打开的独立stack日志启用标准库faulthandler.dump_traceback_later(5, repeat=True, file=stack_stream, exit=False)；周期输出全部线程栈，45秒内最多9次，因而能在kill前留到主线程及renewal线程。正常/异常退出时先cancel再关闭日志。先做无业务的标准库可用性/路径检查；不可用就停止，不安装替代工具。避免新增Python计时线程干扰已接受capture的写者边界。
3. 保持现有子45秒、父90秒、gate/lease/PRE/读期限；watchdog仍到点kill/wait。日志采集计入同一45秒，不另给“诊断宽限”。父在kill前后记录已刷日志长度/摘要；保留首次失败。不因加探针后超时就直接判原调用更慢，也不把诊断运行完成当M1功能通过。
4. 若被终止，先按已接受静止边界保全新的DB和所有sidecar，再走另行批准的原正常释放路径；清理前后分别标记，不打开旧崩溃现场，不删journal。一次诊断后即交调用区间、最后ENTER/EXIT、实际栈及计数；不自动修代码再跑、不追加第二个起点或其他例。

调度据此仅需一次固定上述诊断驱动与预算。后续功能修复/复验应只针对该诊断证实的热点或等待点，沿M原不变量和时限给最小路径；在确切修复target前，其余四例仍NOT_RUN，不自动续跑。

## 历史限制、结论与释放

缺少终止栈/逐调用计时直接阻止根因判定，须在新诊断补取；旧journal阶段没有standalone SQL、外层batch/辅助包装层缺完整流、旧U2/F2/F3缺件仅保留限制，不从清理后SQL反造，也不为包装日志重跑工具。已封存原DB+journal及本例1目标/2dispatch/2effect、原45.031秒失败均不得改写。pending=0和owner释放不是业务完成。

本轮只新增本报告与小型引用/时间线记录，没有运行产品、旧脚本、目标初始化、dispatch/reconcile/publisher或SQL，没有修改产品、原263成员、协调JSON、Git索引/提交或执行者工作树。所有自有只读Git批处理均communicate/wait结束；无自有业务进程、owner、keeper、后台或浏览器/profile会话待释放，不是全机PID扫描。

field reset保持 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`；无网络、平台、凭据、费用/模型、安装、OCR、推送、书级提交、A05题22、B/旧A03联系或委派。结论为REWORK，等待调度采用上述单一诊断；不重开T1/T2、不扩大原28项。
