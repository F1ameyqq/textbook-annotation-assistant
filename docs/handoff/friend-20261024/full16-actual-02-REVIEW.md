# A30 full16 actual02：7题有限接受，Q12 未决及释放历史保留

结论：**ACCEPTED_FIXED_SEVEN_SAVES_FRESH_READBACKS_Q12_UNKNOWN_AND_LATER_IDENTITY_METADATA_ONLY**。

本次正式独立审查接受 printed 2/3/4/6/7/8/9 的各一次保存及各自完整、新鲜的独立读回。原 accepted 1/5/10/11 复用不变，本节已接受 **11/16**；Q12 为 **UNKNOWN_NO_RETRY**，Q13–16 为 **NOT_RUN**。全16原生导出、展示和最终客户交付尚未完成，`CUSTOMER_READY=false`，`1800-a PAUSED`。本结论不接受原运行的完整资源释放，也不激活续行。

## 固定输入与方法

- 主固定包 `D:/1800-private/a30-full16-actual-fixed-20261024-02`：manifest `2b4ce2bd85a6509e652cad1fc73296a8f866b904b500b88641bac2184adf0130`；summary `f805056a7ece4350708077d9c0006928f8d0c79ecde587421f56d01acfc99833`。10,774 raw 成员及3个顶层记录复制后逐一核对字节数与 SHA-256。
- 同轮索引补件 `D:/1800-private/a30-full16-actual02-index-fixed-20261024-01`：manifest `4af7c633e6732ebf54e1e71c2f95219372fdc8805b781236953343ceb8b55795`；summary `b9aef6a17100bf279f5130477c22c1c8f7ceb1f8aded7e02f92e87545a92b6f1`。9 raw 加2顶层记录私有复制核对。
- 合计 **10,788** 固定输入。仅读取副本及已接受的 post401/Union18 冻结基线，SQLite 使用只读 immutable URI；独立重建新读回快照、逐字段与原始字节比较。没有导入或启动产品入口，没有平台、浏览器、模型、OCR、进程状态探测或旧成功用例重跑。
- 接受的 launch04 entry `e3b0ec94e55ce441eba43d4faee114874ac9da70c1a486a5bd6505e70193c232`、binding `ffd10fda34a44459964c55b39a86db9d9a61c82c00d82350d0748b18423f449e` 与本次原件一致。新 authority `20b3230f-32de-40f2-8037-9b22897ad26e`，SHA `0c2badbb7529b234d1eb6c9759c14bb82a3caf6736f98f345d5062ddc90c73f8`，原 launch/child/outcome 均为 spent1/remaining0，无自动重试。

## 新保存与完整读回

| printed | native order | 新题框 | 保存后新鲜读回上下文 | 结果 |
|---|---:|---:|---:|---|
| 2 | 31 | 3 | 8 | ACCEPTED |
| 3 | 32 | 3 | 8 | ACCEPTED |
| 4 | 33 | 6 | 8 | ACCEPTED |
| 6 | 34 | 3 | 8 | ACCEPTED |
| 7 | 35 | 5 | 8 | ACCEPTED |
| 8 | 36 | 4 | 8 | ACCEPTED |
| 9 | 37 | 3 | 9 | ACCEPTED |

每题均核对：原审校内容哈希/来源框/来源原件、完整保存前快照及 writer prewrite 原件、send-intent、唯一一次 POST 的 context/native 两层记录、HTTP200 与原生 receipt、writer 退出后才启动的新鲜 GET、完整库存身份及正文、全部旧题/旧框保全、新框操作者哈希和发送窗口内时间戳、acceptance blob 和 ledger/head 链。两层 POST 记录代表同一次发送；没有把两层计为两次保存。新题 native node 的跨端点键序差异按已接受合同作字段比较，旧对象保持严格键序和字节身份。

7题新读回累计核对 **1,617 对旧题响应原始字节一致**，旧30题逐步增至37题。旧 accepted4 与 old9 均在该保全集合内。8个 writer（含Q12）共保留 1,940 个保存前业务响应；66个完整 capture 共保留 2,156 个业务响应，合计 **4,096 个已保留业务 GET 响应**。这是记录计数，不推定未完整记录批次的实际请求总量。另有1个启动但未留完整结果的 capture。8次保存包含7题接受加Q12未决，不是8题成功。

## Q12 与尚未执行部分

Q12 source key `56232bbf755aaf07eb1eecd41dfbebd13f4db25811d86e282ad82c828f5e2e82`；pending plan `6163be59a6823aa7a6cb03760a5737f775f8b6817daa8121bd6f81f31f20aac0`。一次 send-intent 时间 2026-10-24T13:26:31.679809Z，writer 完成时间13:26:32.121701Z，原 receipt SHA `435dfed039f5192aef6f6e988d4bc66f95ed2ea8ff04caf5f3e85bcd82ee6a45` 报告插入 native38/node `1792848391723`，HTTP200。writer 自身 context/runtime 及 holder 释放记录完整。

其后的两个完整读回批次保留48个响应：目录/全框/来源，以及 native1–6 的七类逐题响应；目录观察到38题及同一新节点。下一个 run `usense-readonly-20261024-132640-9a1597f5` 只留 claim 和 TLS probe，没有 capture-summary、目标 native38 正文、完整库存读回或最终比较。**目录节点及200 receipt不能替代完整读回**。原 ledger 为 INTENT、output=null，candidate 为 INTENT_UNKNOWN_UNTIL_READBACK；本次结论明确 UNKNOWN_NO_RETRY，保留原件，不补写状态、不重发。

Q13–16 没有新 save operation/intent/writer，保持 NOT_RUN。全16 export/display 未执行；原4题导出引用 `1aab5143b3dde526c843c2299eae636223002fc2a47a6a0acef4903b2e9f381c` 原字节仍保留，不能当作本次全16导出。

## 资源状态及原始失败

74个已完整留存的嵌套 holder 全部 exit0、Job active0、context/runtime 已关闭、持有句柄已关闭；1,054条不同进程身份记录均 exit_signaled=true。这个结论不覆盖未完整记录的最后一个 capture 的 context/runtime，其状态仍 UNKNOWN_NOT_RETAINED。

外层原件 SHA `b10af7428f190d286a38e7278bda50dc9feb46856d2941009740dba4daba873d`：exit126，`PermissionError winerror5`，无具体失败 API/traceback；stage/cause 均 UNKNOWN。Job已清空、launcher已退出、外层句柄已关闭，但1,210条持有身份中原3条 exit_signaled=false（PID72688/65820/39952，创建时间及映像见私有原件）。因此原 `owned_os_release_confirmed=false` 保留，不以Job0或cleanup-terminated推定完整释放。

同轮补件 release-readback SHA `b23f0bb58c569e657f6febc496c5b8c548f24be4fdd6146f982829b42c21e65b`，在 **13:29:23Z** 对这3个原身份对应PID作只读Windows元信息查询，记录全部 `PID_ABSENT/open_error87`，termination0、业务0。已核对目标与原3条一致、源记录哈希、helper/result/receipt绑定及有限只读查询分支。接受其**较晚时点的记录状态**；审查方没有重新探测进程，且不回填原exitfalse，不重建原退出时刻或错误原因。

## 保全与计数边界

旧3,831个workspace文件无缺失，仅state.sqlite变化；6,917个新增文件=30 blobs+6,887 native记录。旧77 operations和旧84 events完全不变；新8 save operations=7 COMPLETE+1 INTENT，新15 events=7组SAVE_INTENT/READBACK_ACCEPTED+Q12 SAVE_INTENT。16候选的原内容、审校及来源字段不变，没有新增识别operation。

原摘要的 `remaining_unaccepted_count=12`、job RUNNING、旧4题 native_export_status、business_result NOT_RETAINED、production_seconds=5.030138199999783 均保留。它们不是本轮逐题终态或本轮耗时；逐题证据为 **11已接受、1未决、4未运行**。外层记录区间为780.274148秒，仅为外层墙钟区间；本轮完整业务计时和客户总耗时未保留，61次既有review actions没有增加，不能换算为客户人工0。

本次审查保存两项 helper 问题：只读查看器误把 events.body 哈希当JSON；新核对脚本误把selection.zones列表当正文映射。第二项原始失败及后继NOT_RUN保存，新R2只修正字段读取假设后通过，未改产品/证据或放宽内容哈希。作者索引补件中的 SyntaxError、临时文件FileNotFoundError转录也保持原状，其推断原因不用于本审查。

本轮有限实际证据无待补件阻止7题接受。后续缺项是Q12在独立新授权范围内的完整只读对账、Q13–16首次保存及读回、全16导出展示与最终交付。原20b授权已耗尽；本审查不授权重发Q12、重跑成功/OCR、激活平台或恢复1800-a。
