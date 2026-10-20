# A16 唯一live：固定失败归档与自有释放独立核证

**result=ACCEPTED_FIXED_FAILURE_AND_OWN_RELEASE_ONLY**。只有限接受本次固定失败归档和逐项已证自有释放；**实际live仍失败，不是平台通过**。额度已耗1、余0，不重开窗口、不重试。

`task=A16`，作者final `003f862065a2d630e666323c0d158e33bcee91e9`，直接父/运行final `2453c71c070c153a22a49b772bb2696b3858f5d4`；产品 `dd22193a30e969aaf90043365f31f84a5a50df59`，候选 `e66e9f96197871f7123ebe2ed981a587262c50fb3f6e62cdc300f8e96be5a63f`。本核证派发workflow `6041eecb7ad0a7da4954d18b5a0dc871c33951bc`，产品scope/workflow仍为已接受的observation-only/afed9807。本次全程静态读取固定JSON、raw和必要源码/散列，无产品import或运行。

## 输入、授权与唯一调用

42输入逐一与新final Git blob相等，24交付成员及清单、16候选依赖及候选清单一致；31,454旧成员mode/type/blob保持，25新增仅在live-delivery。12运行输出与归档清单的长度、摘要和路径相符；候选和源码未变。见 [raw-preservation.json](raw-preservation.json)、[input-raw-manifest.independent.json](input-raw-manifest.independent.json)。

activation、用户决定、原独立预检的原bytes摘要和task/run/workflow/candidate/scope/sample0/count6+2相符；用户决定明确只批准本次专用context例外，不恢复额度、不授权重试或后续阶段。四份排他claim及profile指纹记录相符。这里核的是归档绑定，没有访问profile或真实activation文件，也不以指纹相符证明认证。

派发READY_TO_SEND/actual_started=false、作者intent的launch_calls0是原意图时点；后来的author-launch-started和author-tool-wait记launch_calls1、retries0及launcher PID69228、wait完成/exit2，不能用前一快照否定后续实际调用。cwd/argv与固定派发完全一致，带本次明确的live/certificate-exception及同一activation/candidate/报告/决定参数。product子命令路径仅作纯字符串核对，未读取作者目录。

实际起止北京时间 **18:37:27.216871—18:37:37.689469**；作者duration字段为 **10469ms**。UTC窗口10:35:37.215014—10:50:37.215014，所有归档事件及释放位于窗口内。原起止墙钟差精确为 **10472.598ms**，与duration字段差3.598ms，归档不足以确定差因；作者wait记录未注明该duration的时钟来源，分别保留，不强行相等。辅助解析以整秒时区加Decimal fraction处理，支持7位fraction，FILETIME按整数100ns处理；原时间字段不改、不跨进程比较monotonic绝对值。

见 [authorization-and-single-call.json](authorization-and-single-call.json)、[timeline.json](timeline.json) 及原 [author-tool-wait.json](../current-readonly/revisions/observation-only/live-delivery/author-tool-wait.json)。本次过去批准不转化为新例外或新窗口。

## 首错与实际计数

独立依据原 [current-state.json](../current-readonly/revisions/observation-only/live-delivery/runtime-raw/current-state.json) 的第5条审计确认首个BLOCK：

| 字段 | 原记录 |
|---|---|
| 北京时间 | 18:37:37.210693 |
| scheme / hostname / port | https / cdn.bootcdn.net / 443 |
| method / resource | GET / Script |
| 守卫层 / 原因 | FETCH_REQUEST_STAGE / ORIGIN_BLOCKED |
| redirect / expected passive | false / false |

Script属于活动资源，固定策略的非必要被动资源例外为Image/Font/Media，不能用来放过此请求。guard_pre_shutdown与guard_at_serialization均保留ORIGIN_BLOCKED，terminal_stopped=true、pending_tasks0；最终外层错误为NETWORK_GUARD_STOPPED，navigation FAILED，后续15项全NOT_RUN。两层代码只是描述不同判定层次，不把最终停止码覆盖为未知首因。

这是**当前候选对外部Script的策略拒绝**。它不证明CDN不可用、DNS/TLS故障或全平台根因，不证明该素材是否必需，也不推断放行后即可完成读书。完整脚本URL/路径/版本没有留存，本核证不扩大白名单。

| 计数 | 本固定记录支持的结果 |
|---|---|
| launcher / context / 主导航尝试 | 1 / 1 / 1 |
| 固定业务GET / 原图GET / 样题GET | 0 / 0 / 0 |
| 登录提交 / 业务写入 / upload/OCR / 重试 | 全部0 |
| 静态原件保存 | 0 |
| 审计事件 | 8：Fetch阶段5、context阶段3 |
| 辅助资源实际网络发送总数 | **UNKNOWN** |
| 主导航HTTP状态 | **UNKNOWN** |

一次主导航在两层各有ALLOW事件，不能当两次导航；同源Script/Stylesheet在Fetch阶段ALLOW，随后在context层因STOPPED拒绝，不能据ALLOW计作发送成功或HTTP200。原记录缺完整request ID关联，8事件不能折算8请求。NOT_RUN本身也不证明UI此前毫无自动请求；这里同时核事件中无BUSINESS/REGISTERED_ORIGINAL放行、无source/static输出，与固定路径未进入这些步骤及零计数一致，不扩展为全浏览器抓包结论。

细节见 [network-and-counts.json](network-and-counts.json)。

## 逐项自有释放

| 资源 | 证据与有限结论 |
|---|---|
| 专用context/runtime | context_created/close_attempted/closed及runtime_stop_attempted/stopped均true，errors=[]、RELEASED |
| 占用子进程PID64472 | 前后created_filetime均134369662489331243，exit0已观察、handle_closed=true；只证明该次前检匹配数0，不是后置/全机无进程 |
| worker PID28560 | 前后创建时间134369662482697759、pid相同，exit2已观察，creation_identity_match=true、handle关闭、errors=[] |
| product PID34812 | 外层held handle前后创建时间134369662477193440、pid相同，exit2已观察、handle关闭、errors=[] |
| 两个自有Job | 均job_assigned=true，最终清理前active1，清理后active0，job_closed=true；不是声称清理前无残余 |
| 外层launcher PID69228 | author工具wait完成/exit2可核；**OS创建身份UNKNOWN_NOT_CAPTURED保持** |

held_identity原固定实现针对保留的Popen handle核GetProcessId/GetProcessTimes/WaitForSingleObject与exit code；JSON的整数FILETIME精确比较，没有转成浮点。三个子进程前后pid/创建时间相等，退出FILETIME晚于创建并位于本窗口内。stream关闭没有单独runtime bool，但固定finally路径逐流关闭后才关闭handle并置其closed标记，保存的release已越过该位置；将这一项明确记为源码路径支持的推导，不冒充额外原生管道观测。

OwnedJob只指派已门禁的自有child及后代，设置KILL_ON_JOB_CLOSE、清理时使用TerminateJobObject，两个Job最终active0/关闭有原记录。没有全机kill或本核证新增占用扫描。worker/product两层release errors为空只说明清理/身份记录没有错误；其业务/观测仍由exit2和current-state ERROR判为失败，不能把stdout的errors:false误读为live成功。

原product stdout只留90bytes及SHA，未单独保留raw stream；外层author stdout135bytes和stderr0已按原bytes核SHA。缺失的raw不重建、不伪称读过。见 [owned-release-ledger.json](owned-release-ledger.json) 及原 [worker-release](../current-readonly/revisions/observation-only/live-delivery/runtime-raw/worker-release.json)、[launcher-release](../current-readonly/revisions/observation-only/live-delivery/runtime-raw/launcher-release.json)、[occupancy](../current-readonly/revisions/observation-only/live-delivery/runtime-raw/occupancy.json)。

## 未接受项和交付

认证未证明；书/目录/全量题框/源元数据、viewer14/173页/原图/映射均NOT_RUN。无当前图或库存就不作图片/数据验收，亦未另取资料。static_assets和sources为空，归档运行文件集合只有12份非敏感JSON/流，无真实脚本、完整source sidecar、原图、未脱敏请求、认证值或视频新增入Git。正文/schema UNKNOWN、样题NOT_RUN、production_ready/write_eligible=false。原R02仍REWORK且能力停用，先前有限离线结论不变，首题保存及内容/题框刷新重开读回仍NOT_RUN。

逐项证据索引 [evidence-index.json](evidence-index.json)，未知/边界 [unknowns-and-boundaries.json](unknowns-and-boundaries.json)，机器结论 [review-result.json](review-result.json)。外层身份、辅助发送总数、HTTP状态等UNKNOWN不因有限接受而关闭。

本核证0产品/suite/launcher/import执行，0浏览器/网络/profile/凭据/native/占用或新平台连接；只运行本地静态JSON/散列/报告工具和只读Git，未访问.local、作者活动目录、旧验收目录或真实系统资源。不修改42输入、作者报告、根JSON或旧成员，不新增CDN许可、TLS例外或activation。

状态 **FIXED_FAILURE_AND_PROVEN_OWN_RELEASE_ACCEPTED_LIMITED**。本独立静态准备资源说明 [reviewer-release.json](reviewer-release.json)，最终保全 [final-preservation.json](final-preservation.json)，原字节清单 [raw-manifest.json](raw-manifest.json)。实际live1已耗、余0；下一步仅由调度依据具体失败准备必要适配新方案，本轮不重启、不重试、不延伸到业务。其他三例HOLD、Q22不重放、0B或外部联系人消息。
