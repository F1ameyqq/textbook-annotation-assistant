# A17 已观察外部脚本的显式排除适配

2026-10-20。状态：新正式阶段，仅离线实施与独立验收，0 新 live 激活。用户要求持续推进、尽快以真实反馈调整且新阶段分别新建执行/验收聊天；调度据此明确自己的下一工程范围。A16 实际失败归档与已证自有释放已正式独立及调度有限接受，见 `docs/evidence/coordinator/a16-live-independent-closure/coordinator-result.json`。独立 REPORT SHA `e4ef189da21b22890ba4e9875a061d5a55ac475767b894290801509451294955`，manifest SHA `335641c6417a6cab8031ea5ea429d52072e4d2141a682821d2cdb62fadc468da`，18成员+清单及42输入原bytes核证。认证和当前书籍仍未证明。A16 已耗1、余0，旧批准不覆盖本阶段。

执行目录 `D:/1800-worktrees/a17-static-exclusion`，分支 `codex/a17-static-exclusion`，固定 base `003f862065a2d630e666323c0d158e33bcee91e9`；该版本产品仍为已接受的 observation-only dd22193a，另含 A16 实际失败原件。独立准备目录 `D:/1800-worktrees/a17-review-preparation`；正式隔离 raw 待固定交付后另给。确切 threadId/host/cursor 和本任务 workflow 以 `docs/evidence/coordinator/a17-excluded-static-dispatch/creation-intent.json` 及根调度 JSON 为准，创建后登记，不自行猜造。

## 具体问题与拟定行为

A16 在原专用无头 context 的唯一导航中，把 `https / cdn.bootcdn.net /443 / GET / Script` 拒绝后作为致命错误停止。固定记录没有路径、发起方、脚本内容或必要性证据；不能据此放行整个 CDN，亦不能判断该脚本不必要。

本阶段增加一个明确的排除类别：上述精确来源、方法、资源类型、非重定向请求仍在发送前被拒绝，拒绝成功时允许主页面继续加载。外部脚本没有被取回、执行、替换成本地副本或另走网络。只有后续导航、登录态、当前书身份、业务响应与源图校验成功，才分别记录所得事实。脚本若实际必要而导致失败，则保留失败和 UNKNOWN，不修后自动重连。

这是新的工程处置，不追认原 A16 策略错误或把其失败改为成功；也不称脚本为“被动”或“已证非必要”。原 R02 仍 REWORK，sample0，正文/schema UNKNOWN，production_ready/write_eligible=false。

## 最小修改面

复用既有 current_readonly 内核及专用 launcher/worker 生命周期。仅修改与新排除策略、双层守卫分类、有限计数及新阶段绑定有关的代码。固定 A16 Git 版本、全部证据/raw-checkout/失败及已用标记保持原 bytes；不得重跑任何旧任务或旧 suite。

产品白名单：`src/annotation/source/usense/current_readonly/gate.py`、`policy.py`；`tools/a16_current_state_probe.py`、`tools/a16_current_state_launcher.py`。确有需要可新增 `tools/a17_*.py` 的小型阶段入口/打包工具，但不得复制出另一套业务执行系统。新相关测试仅 `tests/a17_excluded_static/`；新候选、计划、模板、报告、完整 raw 交付与失败记录仅 `docs/evidence/A17/`。其余源码、公共合同、根依赖、旧 evidence 全部不改。若此边界不能正确实施，先说明具体缺口，由调度在同阶段明确处理，不偷偷扩大。

- policy 返回独立的 `EXPECTED_EXCLUDED_STATIC_DENIAL`。名称不能成为调用者伪造的放行/继续开关；分类必须由受控完整请求字段导出。
- native 与 context 层均明确拒绝这类请求，拒绝调用失败、异常、未完成任务或后到终止仍硬停止。默认/未知拒绝仍致命。
- 上限为全轮两层合计最多 16 次排除拒绝事件，放在同一个守卫共享状态，任何 await 前扣额；同一请求出现双层事件保守计两次，不猜跨层去重，也不混称真实发送次数。第 17 次仍拒绝并停止。纯 policy 判断、capture/get_once 等查询不扣此事件额。两层都不得允许该 HTTP 请求继续；不把这一证明扩大为操作系统 DNS/TCP/TLS 活动为零。
- 仅精确 HTTPS 主机和有效端口 443、GET、Script、非重定向可归入该类别。保留 URL 结构校验和零用户信息/fragment/control 等约束。其他域、子域、拼写诱饵、方法、资源类型、API/登录路径、重定向、WebSocket、主导航与错误分类不能借用此处置。
- 保留六个业务 GET 各一次、两原图各一次、同源 session/static 原有白名单。无新增 CDN 下载、探针、HTTP 客户端或 source discovery 请求。
- native 排除分支也要证明请求属于原页面/主框，不能依赖未必出现的 context 回调补判身份；缺失或不匹配身份仍 fatal。复用已有 CDP 守卫内部信息或无 HTTP 的身份绑定，不另导航或扫描真实系统资源。
- context/native 的在途回调必须有界结清，关闭期间、结清期间后到 fatal 或未完成回调进入最终 ERROR/UNKNOWN，不吞首错、不等无限时间。不得改写冻结的历史 native 参考文件；需要覆写时在新适配代码中完成并纳入候选。
- 如现有响应回调观察到被排除脚本的 response，立即记录“排除边界未证明”并停止，不读其 body。不能略过响应后仍声称零 HTTP 发送。
- 新 scope、候选清单、workflow、stage/run_id、decision/report、activation 路径及输出一次性标记必须相互绑定，不能接受 A16 或 A15 的决定/activation/报告。原专用 profile 继续沿用，当前阶段不得读取它。
- 新报告如实记录排除拒绝、后继是否实际完成、剩余 UNKNOWN；不能因预期拒绝或离线 PASS 声称认证/取数成功。

## 当前实施范围与验证

当前仅离线开发及独立审查，0 browser/network/profile/凭据/native 真实调用/占用扫描/登录/业务。可做正常必要代码修正和相关新离线测试，失败保留，不人为设“一候选/一测试”开发上限；不运行旧 suite。

相关控制至少覆盖：已观察形态在两层发送前拒绝且不触发停止；相邻非法形态仍拒绝并停止；拒绝失败或异步后到错误不可丢失；有限计数和未知发送数口径；排除后导航/身份/数据失败仍停止；旧 activation/决定/scope/候选不兼容；0 样题与原业务 GET、源图范围不扩大。测试只能用合成请求/响应和 fake transport，不执行真实 native/browser/product 子进程。

新正式执行与独立验收各建一个聊天，xhigh、model 沿用，先落盘去重意图后登记确切 threadId/host/cursor。独立先准备标准，作者固定产品/final/raw/报告/释放后，调度核证并给新 raw 隔离再验收。不能读取活动作者目录。

新 `task=A17`，`scope=CURRENT_BOOK_SOURCE_INVENTORY_EXCLUDED_STATIC_OBSERVATION_ONLY`，候选应绑定本任务实际 workflow。新预留输出为 `D:/1800/.local/stages/a17-excluded-static-live`、activation为 `D:/1800/.local/stages/a17-excluded-static-activation.json`，当前都不得创建、访问原 profile 或启动 live。新 run_id 与正式执行 ID 绑定。A16 和所有旧一次性标记不动。产出具体可审查的计划/默认拒绝的门禁与模板，而非先生成获准决定。

交付必须有产品 commit、final commit、完整候选依赖清单（含包初始化）、本轮相关测试/必要失败原记录、固定 raw 复现命令、模式/type/blob旧成员保全、精确释放和限制。raw diff的正常空行仅属证据，不以其任意空白报警中断已允许的离线开发；命令失败保留并核退出码。不要为了树干净清理或改写旧内容。所有 Git 首先设 `GIT_NO_LAZY_FETCH=1`，每条 `-c core.longpaths=true`；不 reset/clean/stash/全量add，不向 B 发消息或推送。

## 后续路线

离线独立及调度接受后才固定这一次 A17 的具体只读提案。若仍需本次 context TLS 例外，必须在完整可审查方案就绪后获得本阶段明确决定；A16 的“仅此轮”批准已经用完。

拟定新 live 仍只有一次原专用 context、一次主导航、900 秒含释放，六个固定业务 GET 和 viewer14/173 原图各一次，0 样题、登录提交、业务写入。当前 0 activation、0 新 live 权限。首个非预期失败停止，不重试、不延期、不清标记。

取得当前认证书、目录、全量题框、映射和原图后，集中完成普通单选首题真实适配、固定内容/坐标/政策和写入次数、唯一保存及内容/题框刷新重开独立读回。其他三例 HOLD，Q22 不重放，0 B 或外部联系人消息，无书级送交。
