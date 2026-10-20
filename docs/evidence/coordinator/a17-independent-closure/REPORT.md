# A17 修订版有限独立预检

结论：**ACCEPTED_OFFLINE_ONLY**。接受依据 **BOUNDED_READONLY_PREFLIGHT**，仅限本次精确候选的有界只读离线准入。不是平台通过，不批准TLS、activation或live。原独立REWORK、原21组NOT_RUN及原R01历史保留；R01尚有报告归因残留，不标为全关闭。

正式独立 `01a158fd-cbeb-7a31-a3e6-661c7d4c95d4`；执行 `01a158fd-281c-7282-a3b4-db876697686c`。固定base `1d2ba3766558fe9cc911756666d962184cc1de57` → 产品 `1168a75eb35f319c3ced270b6c515adbdb38603f` → final `8bffd88dacc146fc3f061ed0863b299fa5dabd30`。产品workflow `d137a1bba49550f661b110ee14c9541a1dc4fb19`，独立派发workflow `962586be2729912a2b5bfadd8a78fd0d375cc106`，两者不混用。

候选SHA256 `4ed38cb1f703c3d0b5e94d601f2f267c05ead871b9a26004e2e44e5d6eeb31dd`；任务SHA256 `4bac1b884cee0602458469aa05f8676ba391853dbf7f3df8759ca50b575362ac`；56输入清单SHA256 `2b503c83d7c5f050ac52e2b85a5f77719f3f5e5e5280c225a6435347d01ecd53`。唯一产品读取根为 `D:/1800-worktrees/a17-first-cause-r1-review`，未读活动作者目录，未在内嵌raw-checkout运行。

## 适用标准与证据来源

本次按固定任务 `A17-practical-readonly-preflight-disposition.md` 的最新明确标准评定：只影响主错误名称而具体首因、拒绝/停止原始事实完整的报告问题可登记为非阻断残留；改变拒绝、写入、身份、停止、期限或误报成功仍阻断。该调整不追认旧包通过，也不把旧21组升级为动态PASS。

| 准入事项 | 本次证据 | 有限结论 |
|---|---|---|
| 固定输入/依赖/历史保全 | 本次机械核56成员size/SHA/Git blob及mode/type；18依赖；Git父链和完整树raw | 通过，见intake/static-result/input-preservation-final。 |
| CDN拒绝、精确形态/主框、共享16事件、API/login/WS硬停、六GET/两图/sample0 | policy、CurrentGuard等未改；本次AST/不可变Git核对；引用原独立34项有限证据 | 本次未放宽；未重新运行旧34/30或旧反例。 |
| 截止、回调结清、关闭与误报成功边界 | 相应节点未改；observe_live差异仅error选择；新11项与独立2项包含晚到fatal的实际fake拒绝/ERROR | 与原有限证据结合，可接受本轮只读离线预检；不声称覆盖全部异步交错或真实生命周期。 |
| 新候选/workflow/run_id/scope与决定/报告/activation/输出绑定 | 新11项的候选/模板及旧workflow拒绝；gate除workflow外AST相同 | 新绑定可用，模板仍未批准且NOT_REVIEWED；未创建任何真实决定或activation。 |
| 原R01首因 | 本次新11项及独立2项 | 原final-drain包装归因场景已有修正；当前except fallback尚有残留，仅报告层，R01不全关闭。 |

历史引用入口为本固定包 `docs/evidence/A17/revisions/first-cause-r1/authority-independent-REWORK.md`，SHA256 `356fbc2f2dcf5e80f86c53dbe1080e00d8c50bd57bd10d03f253c0508921347d`，与原独立报告原bytes相同。其中记录的是旧独立34/34、3766ms及1个反例FAIL/78ms；不是本次重新执行。policy、守卫拒绝/身份/计数、settle_callbacks、collect、open_owned、supervise、worker_main、launcher、冻结native参考均未因本次修订变化。本次不补造其原21组控制。

## 本次动态结果

先静态读新runner/test和import链，确认只定义惰性API、运行时真实入口被阻止、open/collect/close/save均由fake替代；输出检查为新隔离根run01不存在后，执行一次：

```powershell
cd D:/1800-worktrees/a17-first-cause-r1-review
python -B tests/a17_excluded_static/first_cause_r1/run.py
```

结果11/11，0失败/0错误，1078ms，工具exit0。原件在隔离根 `docs/evidence/A17/revisions/first-cause-r1/runs/run01/`，与内嵌作者run01分开；后者11/11、1328ms仅作作者记录。没有旧suite/旧反例入口运行。

仅针对新helper的关键区别补充两个独立内存控制：

```powershell
python -B docs/evidence/A17/independent-r1-review/small-controls.py
```

本次2项，阻断失败0，报告残留1例，78ms，工具exit0。两例均实际调用fake `Fetch.failRequest`一次，无continue/fulfill；最终ERROR、exit2、production_ready/write_eligible=false、sample0/NOT_RUN；嵌套`ORIGIN_BLOCKED`首因完整，剩余fake任务/回调0。控制源码、意图、实际命令、原stdout/stderr及完整结果均在本目录，未调用旧helper。

## R01残留：当前except fallback与既有顶层错误仍被混同

状态 **RESIDUAL_REPORT_ONLY_NONBLOCKING / NOT_FULLY_CLOSED**，位置 `tools/a16_current_state_probe.py:688–699`。

第一独立小控制先使可信原主框的未知来源Script被拒绝，`guard.failure=ORIGIN_BLOCKED`，随后当前主执行抛出具体的`SYNTHETIC_LATER_EXECUTION_FAILURE`。进入except时尚无顶层error；helper把新fallback当成recorded具体错误，主结果保留较后的执行错误。原首因仍在shutdown前/序列化快照和拒绝审计中，最终ERROR/exit2且没有放行或写入资格。

第二控制先记录较早的`SYNTHETIC_EARLIER_BUSINESS_FAILURE`，再在finally drain产生守卫首因。该既有顶层业务错误保持，嵌套守卫首因也保持。两者应与第一种“当前except才产生的fallback”区别理解。

因此不能声称R01已完全修复。但依据本次明确处置，残留只影响主错误显示，关键原始事实与实际停止完整，不单独阻断这一次有界只读预检，也不据此自动重开产品修订或追加测试。

## 机械核证与限制

本次只读不可变Git核31529旧成员：31527原mode/type/blob保持，2个获准变化仅probe和gate；新增45、删除0；30306旧evidence全保全，base/product完整树raw与Git原bytes相同，产品树在final中保全。probe除MANIFEST/observe_live外AST相同；gate除WORKFLOW外AST相同。7个只读Git元数据子进程均exit0，不是产品子进程。56输入初次和末次原bytes/SHA保全，18依赖及初始化/namespace声明核对通过。

本报告没有重新验证全部业务、旧21组、实际native API/浏览器会话/平台网络或真实期限。离线fake通过不能证明CDN非必要、认证、当前书库存/目录/题框/两原图已取得，亦不能证明首题保存与刷新重开读回。body/schema UNKNOWN，自动schema能力停用，原R02仍REWORK，production_ready/write_eligible=false。事件上限16不是实际HTTP发送数或DNS/TCP/TLS零活动证明。

作者旧首次中断缺原buffered完整traceback的限制保留，未重演或重建；全部测试进程仅工具退出观察，无OS创建身份，不补采或冒称原生身份退出证明。A16批准已耗1/余0，不借用；旧launcher OS创建身份UNKNOWN等限制保持。

## 释放与下一依赖

本独立完成并释放：0真实browser/network/profile/凭据/native API/占用/产品子进程/登录/业务，0新TLS决定/activation/live，fake任务/回调0，未持有真实产品资源。输出仅本独立目录和指定新run01；根调度文件及56输入未写，不推送，0B/外部联系人消息。见release.json。

允许调度接收本固定有限预检结论，并固定这一次具体只读方案和适用context TLS决定。该后续决定仍由本阶段适用授权另行落实，本报告不启动live。其他三例HOLD、Q22不重放，无书级送交。
