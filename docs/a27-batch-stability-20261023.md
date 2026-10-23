# A27：批处理有限键序验收与关闭失败后的只读恢复

执行交付，等待本任务独立验收。基线 `389d2e7a282d21efa25db8d01c02d115ce9e83b7`；仅在 A27 隔离分支开发。A25 已完成的五题没有重存、重读或改 ledger；本次没有浏览器、网络、OCR、真实 profile/ledger 操作、自动化变更或推送。A26 产品工作区和根历史源码/state 未改。

## 正常批处理的有限比较

`compare_batch_readback` 首先调用未改的严格比较器。只有新建题干/答案区直接 `data` 恰为 `rect_ids,ocr_result,success` → `success,ocr_result,rect_ids`、字段类型/值/数组完整相等，且其余完整快照比较通过时，才复用 A25 已接受的纯对账规则。原严格比较和原输入摘要随新结果保留。其他区域、新字段、内容、数组、已有区域顺序和非规定键序仍失败。

正常 runner 以 `ACCEPTED_CREATED_ZONE_ORDER` 明确标记该结果，可以继续下一个已准备目标；不写标准 `.accepted.json`。严格成功仍走原标准路径。`revision.py` 未改，新结果的状态及缺失标准 marker 均阻止它作为 revision 前驱；`revision_predecessor_eligible=false` 只是描述，绝不是放行门。历史第三、第四题记录不迁移、不补写。

## 关闭有界性

writer 在清理前记录 `business_status_before_release`，通过精确回执及双层 POST 守卫后另记 `receipt_exact_success`；原 `save_success=false` 和独立读回 PENDING 语义保持。清理前关闭 POST arming 并封锁 policy。

新 `close_framework` 保持原 15 秒 context、5 秒 callback、15 秒 runtime 限额，改为 deadline 观察任务，超时只发一次取消，不无限等待被取消协程完成。每阶段异常、未完成 callback/cleanup 数分别保留。独立 writer 入口退出事件循环时不进入 `asyncio.run` 的无限取消 join。合成抗取消 close/stop 和子进程退出检查证明此调用路径。

这仅对可调度异步协程给出有限清理；同步阻塞或运行时底层线程仍须既有外层 OS/Job 截止兜底。没有替代或放松原监管器，实际使用继续要求外层监管。framework false 不会被 OS 已退出覆盖；A25 原两个 TimeoutError 的完整根因仍 UNKNOWN，没有声称本修复解释了该根因。

## 单独的只读恢复入口

正常批处理遇关闭失败仍停止。原外层 holder 完成后，可用新的准备入口自动收集固定引用：

```text
python -I -B tools/run_usense_postsave_readback.py prepare --writer-target-dir <原target目录> --holder <已验外层process.json> --holder-sha256 <固定摘要> --output-root <全新输出目录> --request <全新request.json>
```

准备仅输出 `UsensePostsaveReadbackRequest/v1`，没有权限和 dispatch。它核同一原计划、原成功回执、intent/send-intent、writer stdout/stderr/result/config、完整 before 和双层网络计数、外层 Job0、全部持有 PID+creation_filetime 的退出/句柄关闭。writer PID 的创建/观察时间必须处于原进程区间；不能用一个 `owned_os_release_confirmed` 布尔替代整条链。只支持原稳定身份的首次 intent，revision 恢复不在此增量范围。

根独立审查后，必须另行固定新的 `UsensePostsaveReadbackAuthority/v1`，再由既有外层监管执行：

```text
python -I -B tools/run_usense_postsave_readback.py --request <request.json> --request-sha256 <摘要> --authority <新authority.json> --authority-sha256 <摘要>
```

新 authority 必填 `operation=READONLY_POSTSAVE_RECOVERY`、`status=AUTHORIZED`、唯一 `authority_id`、`request_sha256`、UTC `not_before`/`expires_at`（最多900秒，开始晚于旧 holder 释放），以及精确 `limits={readers:1,contexts:1,posts:0,login:0,business_gets:<原端点数>,retries:0}`。本次没有创建任何真实 authority。旧 A25 authority 不能满足该 schema/request 绑定，也没有旧预算复用。

执行前核 profile 目录指纹、锁、原完整 ledger 摘要，并在 configure 前及 capture 前只读检查当前 Windows Edge 进程。命令行未知或包含该 profile 即停止；原命令行不落公开报告。authority 所在目录原子创建 spent，输出目录只建一次。入口只分派 `configure` 和 `capture`，没有 writer/POST 分支。capture 前及完成后重核固定输入，原 ledger 必须逐字节不变。

新 reader 必须具有不同 PID/run、新 context、晚于旧 writer/holder 结束，全部端点的原 bytes/HTTP200/code0/摘要/双层计数/观察时间完整，context/runtime 释放且进程 exit0。最后完整比较所有 native 状态与 source/pages；可使用同一有限键序规则。结果为单独 `UsensePostsaveReadonlyRecovery/v1`，不写标准 accepted marker，不成为 revision 前驱，不覆写旧失败。未知保存结果、错误回执、占用/释放未证、任一读回变化都停且不重发。

## 验证及限制

新增20项合成检查（含数据驱动反例），受影响9项边界通过；旧194套件没有重跑。固定 A25 原件回放只读取四个指定独立 intake 清单内的副本，逐 bytes/SHA 核证51件：第三题原 strict false、新有限路径 true；第四题原回执/失败释放/外层释放及后来 reader 由新纯链验证通过。它是旧固定原件的离线回放，不是新真实测试。

保留首次固定回放 `RECOVERY_NETWORK_COUNTS` 失败：原 capture 的惰性 document 经 page route 先履行，context 不记 document，native 记1；产品原先错误要求两层 document，现仅精确修正此已证计数，业务 GET 两层各1未放松。保留两次新检查夹具失败：执行/验收身份重复、profile 与 output 祖先关系。分别修正夹具，先前原始输出/脚本保留，未刷成 PASS。

运行原件、命令/退出码、依赖和最终冻结清单位于 `D:/1800/.local/stages/a27-batch-stability-20261023/`。最终产品 commit、raw blob 清单摘要及冻结后结果由执行交付另给。新代码真实平台效果、OS 进程枚举实测、真实抗取消场景及任何新的保存/恢复实际运行均 NOT_RUN。独立验收未代填；sole1800-a 保持 PAUSED。
