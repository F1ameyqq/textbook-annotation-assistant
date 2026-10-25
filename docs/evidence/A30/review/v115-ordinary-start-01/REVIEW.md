# v1.1.5 唯一普通START：独立验收

结论：**ACCEPTED_FIXED_V115_ORDINARY_START_VISIBLE_RESPONSIVE_OWN_WINDOW_AND_OWN_RELEASE_ONLY**。只接受一次精确普通START、自有可见/未最小化/响应窗口、正常关闭、本轮原句柄释放及声明工作区索引保全。不是截图、任务列表目视或普通GUI业务全流程验收；customer_ready=false，1800-a保持PAUSED。评审不授权再启动。

固定02 manifest `751c1f085dde172a3aba7e7db5710af998d2f78607a8f02595e92318bd962bc3`，48成员全sha/bytes/集合匹配。原START固定01 manifest c491a48e…列43成员，实际45文件（含自身），唯一漏列raw/preparation/manifest.json。原件一直存在；02正确纳入它、父manifest及补充，45条01→02字节链全部一致，原01不改，40条live来源映射只核其冻结目标，不读live原路径。修复只补成员覆盖，没有重启START。

## 精确入口与一次性

ZIP `d3abd4e5670fe82a103aad14b3f69774b92944da5bca74ff6853aff223805bf3`/2741285字节，release `66c811ba…`，已接受源码02 `0095d385…`；START、customer.py、holder、observer、binding及17成员准备manifest逐项命中。实际启动确为cmd.exe /d /c本包START_CUSTOMER.cmd，没有以直接Python GUI替代。Python命令是外层观察器，它内部调用真实START。

新本机授权c316e6f8…只绑定一次零业务启动，spent1/remaining0、无retry。北京时间2026-10-25 17:19:02—17:23:02总窗口240秒，观察上限180秒+自身释放60秒；经前置核验后动态观察预算105秒。全部操作记录在窗口内；唯一executor attempt、唯一launch intent与原命令/exit一致。未借用已spent的业务authority。

## 窗口与释放

原窗口与本轮holder的同一PID+creation身份匹配；可见、未最小化、精确标题、原句柄仍活。关闭前observer用同一原held handle重新核HWND/PID/creation，WM_NULL响应成功，再发一次WM_CLOSE并break；原close回执及正常退出相符。一次控制器close由固定源码成功路径+原回执支持，没有独立低层message trace。

本轮4个原身份为cmd/conhost/python/python，全部原handle OBJECT_0、exit0、exit_signaled及handle_closed。原launcher另wait0，thread/process/Job handle均关闭、Job active0，无skip/error/timeout/强制cleanup。observer顶层原Popen handle取得creation、完成wait并Close也已证；不以exit0/进程不存在或旧六身份/业务183身份结论替代。

6.8225918秒是worker启动前到holder返回及关闭后snapshot结束的观察流程计时，不是窗口持续可见或客户总耗时；holder原时间跨度3.872866秒，整个observer命令10.4837152秒；ready到close回执相隔2.002627秒，不外推连续可见时长。客户总工时/人工仍NOT_MEASURED。

## 保全、无业务范围及限制

41项保全/默认路径离线检查通过。before/after除观察at外完全一致：head eaea1053…、jobs/104 operations/108 events全表、16接受ref、settings56f07eb9…及state.sqlite字节索引保持。11,674声明索引的路径/bytes/SHA全相同，增删改0，且before与已接受实际的固定after状态/索引相同。此索引明确排除__pycache__/.pyc，这些缓存没有补读/复核；不声称整个机器或未索引文件字节均未变。

默认customer源路径只创建GUI、注册回调、只读refresh/jobs列表并mainloop，没有立即业务动作；observer仅WM_NULL/WM_CLOSE，没有业务按钮、浏览器或OCR/model调用路径。四个owned身份中未记录浏览器。无独立network trace，零动作请求/源码/owned process/状态保全是有限证据，不外推全机零网络或全机无浏览器。任务列表目视和截图均NOT_RUN，不把窗口响应当业务完成。

原01漏项完整保留，02只补覆盖。START本轮独立解析无执行错误；探索输出截断和一次PowerShell缺失issues属性被@($null).Count显示为1的诊断口径均单独记录，实际保全failed=[]、41/41，窗口issues=[]；准备日志中的6项mock测试OK仅引用未重跑。旧代码/业务helper失败不被本次清除。

本次是同模型家族、独立新会话，内部2个只读子审计协助窗口/释放及保全，主审负最终结论；共享本机环境，不是外部或异模型独立。仅自写标准库/AST解析固定原件，无产品、START、窗口探测、UI、浏览器、网络或model再执行，无真实workspace/profile/live路径读取、无产品修改/commit/push。

绑定使用的业务自身释放intake59f3…与后来的正式actual根接受058d23a3…是不同回执，均核原件；不倒写旧准备/dispatch的PENDING状态。现在只剩root接收START并写外置ZIP-bound最终sidecar，无需新业务。最终CUSTOMER_READY仅由root限定当前机器、本书当前16题及已接受层级；客户下一步查看现有已完成成果，不照旧包准备步骤重放恢复或生产。
