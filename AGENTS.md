# 项目开发约定

2026-10-20 用户对固定A17提案直接回复“一直批准”。本轮及后续同类专用context临时TLS例外持续获准，不再逐轮询问；不扩展登录/写入/新来源或恢复旧额度。A17唯一activation及派发意图已固定，见docs/tasks/A17-approved-single-live-dispatch.md、docs/evidence/coordinator/a17-live-dispatch/dispatch-intent.json；原执行承接一次真实只读，原独立等待固定结果。18候选依赖与候选raw一致，范围1context/1导航/900秒、六GET+两原图、sample0/0登录写入不变；下方等待TLS决定为历史。实际启动与结果以JSON及固定交付为准。

2026-10-20 A17修订版已正式独立及调度有限接受，产品1168a75e/final8bffd88d，候选4ed38cb1…；结论ACCEPTED_OFFLINE_ONLY/BOUNDED_READONLY_PREFLIGHT。新11/11、两个小控制无阻断失败，19报告成员+清单及56输入核证，见docs/evidence/coordinator/a17-independent-closure/。R01保留顶层fallback归因残留，不全关闭；原21组NOT_RUN和旧REWORK保持。依用户“不要太保守”不为此再开修订。具体本轮提案docs/tasks/A17-bounded-readonly-tls-decision-proposal.md已固定：1原专用context/1导航/900秒、六GET+两原图各一次、排除CDN事件16、0样题登录写入。仅待本轮适用TLS直接决定；原A16“仅此轮”已用，不能借用。当前无decision/activation/live；作者和独立均释放，原scope/记录/Edge与profile保持。

2026-10-20 用户最新要求“不要太保守”，按docs/tasks/A17-practical-readonly-preflight-disposition.md缩减本次独立预检：重点核不误写/不越界/有界停止及绑定；具体首因原件仍在且正确拒绝/ERROR的顶层报告差异可保留限制，不再单独阻断真实只读。A17-R01已冻结产品1168a75e/final8bffd88d，作者新11/11、1328ms；18依赖/42交付+self去重56raw至D:/1800-worktrees/a17-first-cause-r1-review，31529旧成员和30306旧evidence核证，仅probe/gate变化。原独立复核新差量及必要安全事实，可明确引用未改源码的原有限证据，不为把历史21个NOT_RUN刷成PASS重造全套测试。原报告/失败保留，0TLS决定/activation/live；派发状态和cursor见JSON。

2026-10-20 A17 首次正式独立已固定 REWORK 并释放：产品e7ee2424/final1d2ba376，原34项suite通过，独立反例1FAIL/78ms、后续21组NOT_RUN。A17-R01为final drain把顶层具体首错ORIGIN_BLOCKED写成通用NETWORK_GUARD_STOPPED，嵌套首错、拒绝及ERROR保持；不能扩称网络放行。19输出成员+清单及61输入原bytes核证，见docs/evidence/coordinator/a17-independent-rework/。按docs/tasks/A17-first-cause-reporting-correction.md在原执行01a158fd-281c-7282-a3b4-db876697686c同阶段窄修错误选择及新相关离线差量；同独立01a158fd-cbeb-7a31-a3e6-661c7d4c95d4等待新固定交付。确切派发状态/cursor以JSON为准，不新建聊天、不重跑旧34/30项或旧反例原入口。旧包/失败全部保留，0TLS决定/activation/live；A16原批准已用。下方A17开发/验收进行中为历史。

2026-10-20 A16实际失败已正式独立及调度有限收口，见docs/evidence/coordinator/a16-live-independent-closure/：18报告成员+清单、42输入原bytes核证，只接受固定失败归档和已证自有释放；认证/书源库存仍未证明，live1耗尽/余0、launcher OS身份/辅助发送总数/导航HTTP状态UNKNOWN保持。新A17按docs/tasks/A17-excluded-static-readonly-adaptation.md派发，workflow811c3ac9；正式执行01a158fd-281c-7282-a3b4-db876697686c、独立01a158fd-cbeb-7a31-a3e6-661c7d4c95d4均xhigh/model沿用且已接单。仅离线适配已观察cdn.bootcdn.net的GET Script：仍发送前拒绝，精确条件下有限排除后继续；双层合计16事件、native主框身份与回调结清/late fatal集中验证。不能假称脚本非必要或放行CDN。作者D:/1800-worktrees/a17-static-exclusion，base003f8620；独立仅D:/1800-worktrees/a17-review-preparation准备，等固定交付另给raw，不读活动作者目录。允许正常必要新离线修正/测试，旧suite/失败原件/已耗额度不动；0新TLS/activation/live。A16旧批准仅本轮已用，未来新具体方案完成后另落实适用决定。其他三例HOLD、Q22不重放、0B消息。下方A16独立进行中为历史。

2026-10-20 A16唯一live已耗1/余0，final003f8620已固定释放：18:37:27—18:37:37北京时间，一次启动/context/导航尝试，首个阻断为https cdn.bootcdn.net:443 Script ORIGIN_BLOCKED，后NETWORK_GUARD_STOPPED；业务GET/原图/样题0、后继NOT_RUN、认证未证明。调度核24成员+自身/31454旧成员保全，42raw隔离D:/1800-worktrees/a16-live-review；同正式独立按docs/tasks/A16-single-live-fixed-independent-review.md已接单核失败与释放，尚未接受实际结果。8审计不等于请求数、辅助发送总数UNKNOWN、launcher OS创建身份UNKNOWN保持。不重启/延期/清标记，原本轮批准已用；下一适配须依据新证据另明确范围。

2026-10-20 A16本轮已获用户直接批准“批准，仅此轮有界只读观测”，决定docs/approvals/A16-observation-only-tls-user-decision.json。唯一activation窗口10:35:37.215014—10:50:37.215014 UTC，原执行已按docs/tasks/A16-observation-only-single-live-dispatch.md接单；实际启动和结果待固定报告，勿据预留当成功。只一次固定launcher，无重试/延期/换目录/清标记；0样题、登录提交、业务。原独立等固定结果再核证。下方“等待本轮TLS决定”已关闭，不重复询问。

2026-10-20 A16只读观测版已正式独立及调度有限接受：产品dd22193a/final2453c71c，机器结论ACCEPTED_OFFLINE_ONLY仅限observation-only/sample0。独立新18/18（500ms）及9组控制（250ms）通过；38报告成员+清单、59输入raw核证，见docs/evidence/coordinator/a16-observation-independent-closure/。作者/独立均释放，原R02仍REWORK而能力停用，旧证据保全，真实平台仍NOT_RUN。具体本轮TLS提案docs/tasks/A16-observation-only-tls-decision-proposal.md已固定，待用户直接决定；仅1原专用context/1导航/900秒、六GET/两图/0样题，包含获准OSS同受例外影响，0登录提交/业务。未答前0activation/live，不借用A15批准或重跑旧任务。

2026-10-20 A16只读观测版已固定交原独立验收：产品dd22193a/final2453c71c，候选SHAe66e9f96197871f7123ebe2ed981a587262c50fb3f6e62cdc300f8e96be5a63f。作者新18项及raw18项通过，调度核50交付成员/16依赖，59去重raw导出D:/1800-worktrees/a16-observation-review，31259旧成员及136旧A16证据保全；仅机械通过。正式独立01a15841-0d44-7272-9740-40d013839869按docs/tasks/A16-observation-only-fixed-independent-review.md已接单，原作者释放。sample0、六业务GET/两图范围不扩大，R02未修复而能力停用；旧8ab09441正式REWORK已封存40成员。当前独立尚未接受，A16 TLS未批准/live0；新的observation-only TLS草稿待固定验收后定稿。下方“原独立正封存/作者修订中”为历史。

2026-10-20 用户提出先上真实平台验证再调整，调度已按docs/tasks/A16-real-evidence-first-disposition.md调整A16工程顺序：当前8ab09441复核确认R01/R03/R04相关控制通过，但R02仍把语法无效脚本认作接口证据，原独立正封存REWORK。原作者已续派同阶段observation-only候选：停用自动schema资格判定并在策略层拒绝五个样题GET，sample_limit=0；先取得书籍/目录/全量题框、viewer14/173原图映射及现有获准静态脚本真实证据。原R02不重标关闭、不继续完善通用解析器；原证据保全。新候选范围/安全复核后再固定A16 TLS决定和激活，目前仍0live/未批准TLS；不是跳过守卫或授权直接写入。

2026-10-20 A16 R01–R04 修订已冻结释放并交原独立复核：产品cb26282a/final8ab09441，候选SHA071340237c76a7159bd90485e17a774c2f870114baef0199172a2fc5f9547efc。作者新修订raw suite75/75、2906ms；调度核104增改/19依赖，111去重raw已导出D:/1800-worktrees/a16-r1-review，31259基线及原39证据保全。正式独立01a15841-0d44-7272-9740-40d013839869按docs/tasks/A16-revision-fixed-independent-review.md复核，原作者已释放，不再重跑旧suite。R02仅支持窄native-fetch来源关系，当前平台适用性未证明；新旧失败及无OS创建身份的释放限制保留。当前未接受、A16 TLS未批准/live0；旧TLS草案须按新候选接受结果更新，不能直接执行。

2026-10-20 A16 首次正式独立已 REWORK 并释放，31 raw 成员及清单核证，报告见 docs/evidence/coordinator/a16-independent-rework/。已复现 R01 样题同 ID 改角色/顺序仍接受；静态 R02 schema 词汇共现不足、R03 原图未完整解码为阻断，R04 释放状态缺创建身份条件需修正。补件后的作者 suite 33/33，独立 12 PASS/1 FAIL/3 NOT_RUN，初次父包导入失败及原结果保留。原执行01a15840-7766-7533-818d-cc016aa0a60b已开始同阶段修订，正式补充任务 docs/tasks/A16-formal-findings-correction-supplement.md；原独立等待新固定交付，不重建聊天。允许本阶段必要纯离线迭代，不重跑旧任务或恢复旧额度。A16 TLS未批准、live0，待新候选独立接受后再固定具体决定与激活。

2026-10-20 A16已进入正式独立离线验收：作者产品2a604c2d/final4fe417d5，最新33/33 PASS（516ms）并释放；调度核47新增白名单、31259旧成员保全，导出49raw至D:/1800-worktrees/a16-independent-fixed。原独立01a15841-0d44-7272-9740-40d013839869已按docs/tasks/A16-fixed-offline-review-dispatch.md接单，当前尚未接受。run01/run05完整traceback不在包内、CRLF/LF原失败等限制保留。0新live，A16的TLS决定/激活仍待固定验收结果；不唤醒作者重跑旧任务。下方“开发/标准准备”为历史。

2026-10-20 A15已独立及调度有限收口：唯一live已耗1/剩0，final49e5ab4e，ORIGIN_BLOCKED后NETWORK_GUARD_STOPPED；只接受固定失败及已证自有释放，认证未证明、阻断域名未记录、launcher自身OS退出身份UNKNOWN保留。74作者raw及11独立raw核证，见docs/evidence/coordinator/a15-live-independent-closure/。A16合并当前书籍/source/target/接口和一道普通单选准备，已新建执行01a15840-7766-7533-818d-cc016aa0a60b、独立01a15841-0d44-7272-9740-40d013839869，均xhigh/model沿用且已接单，任务docs/tasks/A16-current-book-source-target-readonly.md。当前A16只离线开发/标准准备，允许必要的新代码修正和相关纯离线验证并保留失败，不重跑旧suite或恢复旧额度。A15证书例外不转移，A16新live未激活；先准备完整可审查方案，再落实本阶段TLS边界。其他三例HOLD、Q22不重放、0B消息。

2026-10-20 A15离线预检已独立及调度有限接受：产品bef02045/final7432122b，作者E1-E4 4/4（16ms）、独立4/4（32ms），双方额度耗尽并释放。47作者raw、27独立清单成员及旧成员保全；报告见docs/evidence/coordinator/a15-independent-closure/。本次唯一live已绑定批准/候选/独立报告/原专用profile指纹，窗口07:16:59至07:31:59 UTC，见docs/evidence/coordinator/a15-live-dispatch/。仅本次专用context证书例外、1context/1导航、0登录/业务，等待实际结果；原失败保留、旧额度不恢复。

2026-10-20 最新调度调整：B PR3/分支新head 6d3d29f1已只读接收22文本raw，42题索引、8份答案证据及18项待核清单可供后续内容准备；ZIP未取得，其他三例HOLD，不改变普通单选首题主线，见docs/tasks/B-update-usefulness-reception-2026-10-20.md。A15产品bef02045/final25f9083b在原始diff空白诊断后停止，E1-E4实际0次；31raw/31212旧成员保全通过。调度已明确有限处置正常diff上下文空行，保留原失败和未知检查退出码，续派同候选原未用的首次E1-E4，独立并行只读固定raw，见docs/tasks/A15-packaging-disposition-first-delta.md。不新增候选/恢复旧额度，live仍未激活。按用户关于过度保守的纠正，减少诊断与元数据串行等待，后续集中核当前源目标及接口并同步准备首题；真实保存UNKNOWN停书及首题读回门槛保持。

2026-10-20 A14已独立有限收口：公开证书SAN不覆盖www.usense.com且已过期，根因UNKNOWN；仅接受本次失败/公开字段及两项已证自有释放，A14-TIMING-01通用截止守卫不接受。A13/A14各1次均耗尽。用户现明确批准A15新有界只读阶段：仅本次专用context证书例外，新增1候选、双方各1纯离线门禁差量、通过后另固定至多1新复用观测；0登录提交/业务，旧额度不恢复。先新建正式执行/验收，独立预检及调度激活前0新live，见docs/tasks/A15-certificate-exception-reuse.md和JSON。首题保存读回仍NOT_RUN，其他三例HOLD、Q22不重放、0B消息。

2026-10-20 A13唯一复用观测已耗1/剩余0：首次导航ERR_CERT_COMMON_NAME_INVALID，0登录/书籍/业务，认证未证明。正式独立仅接受固定失败归档和已证自有释放，wrapper自身OS退出身份UNKNOWN保留；见docs/evidence/coordinator/a13-observation-closure/。旧轮不重跑、不忽略证书。下一步A14仅一次严格验证的公开TLS证书诊断（0目标HTTP/浏览器/profile），新正式执行/验收对话ID以JSON为准。其他三例HOLD、Q22不重放、0B消息，首题保存读回仍NOT_RUN。

2026-10-20 A12-R1正式独立D1-D8 8/8、562ms已核证，R01/R02仅在固定产品d45ed25a/final81fab23e有限范围关闭；作者/独立均释放且差量耗尽。依用户本轮明确要求，按docs/tasks/A13-single-reuse-observation.md登记原尚未使用的唯一reuse-only无头观测，新阶段分别新建执行/验收对话，确切ID以JSON为准。只复用原专用profile、0登录/业务/书籍读取，首次异常或LOGIN_REQUIRED停止，原共享标记不可重置。当前还未启动live，真实认证和首题保存读回未证明。

2026-10-20 A12-R1固定交付已到：产品d45ed25a、final81fab23e，作者D1-D8自报8/8并释放；调度raw核31新增、31181旧成员保全及精确子进程释放通过，未作语义接受。正式独立01a157a5-495a-7bf3-bc17-299ad85c48a7已接单，在D:/1800-worktrees/a12-r1-independent核固定53raw并执行唯一D1-D8纯离线差量；原N1-N3不重跑，作者额度耗尽不恢复。下一依赖为独立固定报告/原始结果/清单/释放，当前0新live/登录/业务。见docs/evidence/coordinator/a12-review-delta-dispatch/independent-run-intent.json。

2026-10-20 A12正式独立验收已固定REWORK并释放：R01为Windows占用输出CRLF/LF不兼容，R02为DOM异步期间守卫停止未进入最终判定；原产品7f3d42e3/final0c30b365不得live。原三例网络suite及释放证据有限保留，旧1候选/1suite耗尽不恢复。调度已明确安排A12-R1两项纯离线差量，分别新建正式执行/验收对话；最多新增1候选、双方各1次D1-D8，0浏览器/平台/原profile，不重跑N1-N3。实际派发ID以docs/coordination-state.json为准；其他三例HOLD、Q22不重放、0B消息。

2026-10-20 用户再次纠正：新阶段必须分别新建正式执行和验收对话，不能以当前对话子代理代替。A12此前错误使用子代理已保留历史；现正式执行01a15792-ed1f-7911-b1b4-d5ed6ca9020d仅接收固定交付，正式独立验收01a15794-ad3e-7653-8f77-237fe06f8898核固定raw，均xhigh、model沿用。产品7f3d42e3、final0c30b365，原1候选/1suite已耗尽且作者释放；创建新对话不重跑或恢复额度。后续正式阶段使用create_thread，子代理只作必要辅助。见docs/evidence/coordinator/a12-native-reuse-dispatch/formal-chat-dispatch-intent.json。

2026-10-20 A12已派发：独立目录D:/1800-worktrees/a12-native-reuse、作者/root/a12_headless_native_probe_author、workflow5e31abf7，见docs/tasks/A12-headless-reuse-native-transport-probe.md。仅1新候选/1次本地三例guard suite，作者0平台。固定raw交付释放后另派静态独立，不复跑suite；证明逐跳/方法/WS守卫后主调度才可另登记最多1次reuse-only无头观测，0登录/业务。当前未启动A12平台轮。托管worktree长路径失败保留，显式longpaths短目录已成功，不是产品或live尝试。

2026-10-20 接任最新：调度ID为01a15768-1e2d-7781-b29f-1f7376270216；唯一1800-a已转移至本对话、ACTIVE/30分钟。现有Playwright MCP经官方扩展人工选中Usense登录标签后，17ms标签验证通过；不再把MCP超时作为当前未解阻断。当前仅证明Default登录页，未证明认证书籍或专用无头会话；原A04/A10专用无头profile与日常Default分离。见docs/tasks/A10-successor-mcp-session-recovery.md。原两超时及本次第三超时保留，新握手后一次验证通过不恢复旧轮数；0登录提交/业务写入/进程终止。扩展chrome-extension页面工具URL策略拒绝后已停止自动操作，由用户正常选页，无绕过。下一步固定仅复用专用登录态的新有界只读观测，原native/代理driver不复跑；其他三例HOLD、Q22不重放、不向B发消息。下方交接待接任/MCP具体层UNKNOWN为历史时点。

2026-10-20 调度交接：用户将自行新开对话接替。接任先读 docs/handoff/coordinator-20261020/HANDOFF.md 与 PROMPT.md，再核实际Git/JSON；交接前基线20ed7aa0。旧heartbeat 1800-a已暂停，项目未完成、平台许可保持；新对话登记真实ID后再接管唯一自动化。当前首要仍是现有Playwright MCP会话检查超时（具体阻塞层UNKNOWN），不是重新等待连接许可/开关/Q4确认；旧成功与失败额度不恢复。旧对话交接后不再主动推进，其他三例HOLD。

2026-10-20 11:27最新：用户明确要求排查现有 Playwright MCP 服务连接和浏览器会话。本轮只读核对发现现有 MCP 能立即返回 -32601 协议响应，Edge Default 已装 Playwright 扩展0.4.0且协议2匹配；唯一新标签检查仍120秒超时，当前会话未建立。完整进程快照未观察到 MCP 本地 relay，但具体等待层仍 UNKNOWN。见 docs/tasks/A10-existing-playwright-mcp-diagnosis.md。下一步优先精确识别并单独重连本对话MCP，保留Edge登录态，尚未重连/重启/写入；不再重复询问开关或平台许可，不把此前电脑操控URL策略停止混为同一原因。其他三例HOLD。

2026-10-20 11:02最新：显式系统代理诊断已固定失败收口，最终0f7777ca、运行候选72cb7d6d；原导入失败保留，累计2启动/1GET意图，Error/UNKNOWN/http=null。独立与调度仅接受失败归档和精确自有释放，不证明平台访问或根因，不追加探测。用户已找到并开启“设置→配置→工作→使用本地浏览器”，不再索要开关或连接许可；随后Playwright标签列表120秒工具超时，电脑操控能列出Edge窗口，但因无法可靠确认浏览器URL而强制停止本轮。已请用户把Usense标签置前台后回复继续，尚未收到该上下文。未导航/登录/写入，未绕过工具策略。下一步须依据用户新上下文重新核对可用工具；其他三例HOLD。下方“开关关闭/普通浏览器待答/代理静态审查中”为历史。


2026-10-20 07:08最新用户上下文：用户回复普通浏览器“可以正常打开”。旧等待该答复已关闭，自动化访问仍未证明。按 [有界诊断](docs/tasks/A10-browser-context-diagnosis-2026-10-20.md) 先核对固定源码和本机非敏感代理元数据；当前仅静态/本地读取，旧失败/额度保留，不启动浏览器或真实写入。Windows系统代理启用且为无认证loopback，旧API是否采用该路径待源码核实；不得据此先定根因。其他三例HOLD。
- 2026-10-20 00:35最新A11已收口：产品8ff44619、作者541d6b76、独立87831407，原17项历史证明及本轮作者/独立各一次六项6/6 PASS已核证，调度87730c9e有限接受后本地集成582257248878c91ef0f9b87d43927e312ba19eb9。见 `docs/tasks/A11-local-integration.md`。1099新增、29981旧路径原bytes保全，7模块仅导入通过，0新业务。R01/R02关闭，原错误/REWORK及旧request兼容变化保留；不冒称新版本全回归或平台通过。作者/独立均释放、额度耗尽，不重开/补跑。当前无活动执行验收，平台访问原因仍UNKNOWN，既有普通浏览器上下文问题待答；连接许可持续有效，不重复索取。当前只外部待输入，自动化恢复30分钟静默检查。下方实施/REVIEW是历史，以JSON为准。

- 2026-10-20最新：A10公开传输诊断 `fc81de1b` 固定GET/Error/UNKNOWN，无HTTP状态，12成员及自有资源释放已独立/调度核对，只接受失败归档与释放，原native轮及GET额度均不恢复。A11独立 `1522d1b6` 原17项PASS但静态REWORK：单选资格与对账释放报告。主调度依据用户“持续推进”对自己的工程上限作明确增量修订，按 `docs/tasks/A11-review-findings-correction.md` 在原作者续派最多1冻结候选/1次六项离线差量、后续独立1次，原两候选/旧suite不重跑，不声称用户另回复额度批准。工作流73ded167、原作者已确认ACTIVE；真实平台接线/首题范围仍未完成。浏览器工具库存报Work设置关闭，未绕过；已问普通浏览器能否访问，等待上下文不重复问连接许可。实际以JSON为准。

- 2026-10-19 持续推进路线最新：B `2455fa4f` 已含 `186330f5` 对固定Q4离线技术口径的明确采用，原等待关闭；其他三例仍HOLD，Q16有未选定候选但未获执行资格。A10唯一平台轮固定 `7dbe786d` 在首次导航TRANSPORT失败，0登录/业务，精确自有资源释放已独立核对，只接受失败归档/释放，原driver不再跑。另行固定一次无凭据公开GET诊断，见 `docs/tasks/A10-public-transport-diagnostic.md`，不恢复旧轮数。A11录入内核按 `docs/tasks/A11-limited-live-runner-offline-core.md` 已派发，先离线实现/有限验收；真实接口、文本写入/读回、当前目标和具体新题清单仍待核实。三天路线见最新计划和JSON；旧“等待Q4/禁止连接/无活动”为历史，不重复询问连接许可。

- 2026-10-19 三天交付与平台许可最新纠正：用户要求三天内优先争取限定题型、小批量真实平台试用版，并明确“**一直允许连接平台**”；不再重复询问平台连接或测试书许可。见 `docs/delivery-72h-plan-2026-10-19.md` 与调度JSON `deadline_delivery_plan`。A10已按 `docs/tasks/A10-platform-readiness-preflight.md` 派发一次新只读前检，书46007447、至多viewer10/14/15/173、1轮/15分钟、首次意外失败停止，零业务写入/OCR/送审/Q22重放；自有会话独占释放。旧任务不重开，其他三例HOLD。新写入题目清单和次数在当前现状核对后固定，不能把三天目标当全书/复杂题/最终提交授权。下方暂不连接平台和仅等待B为历史时点，当前以A10/最新JSON为准。

- 2026-10-19 最新A08/A09发布优先：用户明确授权的代码和验收材料已非强制单引用推送 `codex/a08-a09-q4-handoff`，远端 `edf125961be9cdc1642652c038d99872b1c8cdc7` 已独立核实。入口 `docs/a08-a09-q4-handoff.md`、回执 `docs/tasks/A08-A09-publication-receipt.md`、转发消息 `docs/handoff/a08-a09-q4/message-to-b.md`。固定来源929ca1cb、唯一父已发布A07 e37606d；361新增/3元数据更新/0删除，四冻结清单307成员保全，独立静态发布审查通过。0新业务/0平台，main/B/架构/stage1/stage2/A07本次均不变。A未发送B消息，B对固定Q4版本/映射/单题政策/C01回执共同采用仍待确认；其他三例HOLD，A04真实阻断保持。下方A08/A09仅本地/无推送授权为历史时点，不重复推送、派发或恢复额度。

- 2026-10-19 最新A09收口优先：固定产品 `29c82b09`、作者交付 `439423eb`、独立交付 `25fcf217` 已完成独立及调度有限接受，并在 `4fdfebd80f6efc3097e3d92c2659f3055d48f55b` 本地集成，见 `docs/tasks/A09-Q4-local-integration.md` 与调度JSON。固定第4题实际四框Q/image、Q/text、Q/text、A/text与批准内容/坐标/顺序一致，作者和独立各1正常尝试/1成功/1dispatch、各10拒绝零新增变更，均释放且成功额度耗尽，不重派/复跑。189新增路径、29,733旧主线路径原bytes保全；其他三例HOLD，原B HOLD/proposal false分开保留。A08/Q4/A09仅本地、未推送/发送B/连接平台，B对Q4共同采用与A04真实阻断保持。下方实施或REVIEW描述为历史。

- 2026-10-19 最新A09授权优先：用户对固定第4题核准页回复“确认”，本题内容/关系/四框政策及离线模拟已批准，见 `docs/approvals/A09-Q4-offline-business-approval.json` 和 `docs/tasks/A09-Q4-offline-simulation.md`。按Q:image/Q:text/Q:text/A:text四框新建执行与独立验收；旧proposal/B HOLD原件保持，新授权单独引用。其他三例仍HOLD，不沿用Q1，不重跑A08，不推送/连接平台。下方第4题待核准为历史；实际派发/版本/cursor以调度JSON为准。

- 2026-10-19 最新A08收口优先：固定候选 `04762d78`、作者交付 `83f119fa`、独立交付 `c4b75758` 已完成有限独立验收及调度接受，并在 `abc45f49532d8001be8441b54cedefab32c91e87` 本地集成。见 `docs/tasks/A08-local-integration.md` 和调度JSON。作者/独立各1原包+11负例已释放，不重复接收、补测或派发。122新增路径、29,586旧路径原bytes保全；四例仍HOLD，完整外部G/Check/plan未加载。第4题内容/图形边界/关系/分框及政策、专门模拟授权与适配仍待明确，4题片段+1答案来源区不等于执行框数，不沿用Q1。新资料未推送、未向B发送、未连接平台；下方实施/REVIEW描述为历史。

- 2026-10-19 最新A08范围优先：用户已授权新批次只读接收，第一课时第4题优先；执行与独立验收分别新建。按 `docs/tasks/A08-batch-readonly-reception.md` / `A08-independent-review.md` 和调度JSON推进。只消费固定B a76e5a9的stage包，外部G/Check/计划完整对象未加载；四例均保留HOLD，其他三例不造题关系，不沿用Q1授权。0计划/目标/模拟/平台/推送/B消息。旧A07等已收口任务不重开。下方“无新任务/范围待定”为历史时点。

- 2026-10-19 B最新推送已只读核对：PR #3固定 `a76e5a925fec76f20818dfdefa4145aa132ec8a8` 包含 `5970f15a` 的Q1三项明确共同采用确认。固定Q1离线技术口径等待已关闭，见 `docs/tasks/B-update-reception-2026-10-19.md`；不回写旧归档或升级公共合同/平台资格。新Q4/Q9/Q16实际4案例、1题答候选+3答案证据，仍HOLD；N01–N08仅登记待明确范围，本次没有新增实施/模拟/费用授权。旧Q1额度不恢复、不再索要其确认；A04真实平台阻断保持，未向B发消息或推送本次接收记录。

- 2026-10-18 A07修复后源码和验收材料已按用户新授权发布至 `codex/a07-q1-handoff`，远端 `e37606d74d7e538052c563d02df11c6c961b742f` 已核实。入口 `docs/a07-q1-handoff.md`，回执 `docs/tasks/A07-publication-receipt.md`，给B消息 `docs/handoff/a07-q1/message-to-b.md` 由用户转发。下方“不推送/仅本地”为历史时点；本次仍0新业务、未连接平台、未向B发送消息，B共同采用与A04阻断保持。不重复推送或恢复已用完的验证额度。

- 2026-10-18 A07-F01已修复并完成独立差量、调度接受和本地集成 `0a0b3ed5ae044706b633ff767f1b7bd6211a9039`，见 `docs/tasks/A07-F01-local-integration.md`。四选项恢复W，实际六框Q/W/W/W/W/A，数量/内容/坐标保持。作者和独立本轮各一次已用完并释放，旧证据保全，不追加业务；暂不推送/连接平台。下方HOLD及待修复描述为历史。本轮不覆盖未触发shared_material等角色，B共同采用/A04真实阻断保持。

- 2026-10-18 A07-F01修复已获用户明确授权：四个选项Q改W，六框数量/内容/坐标不变；执行与独立验收各新增一次离线差量验证，旧额度不重置。按 `docs/tasks/A07-F01-role-correction.md` 续派现有A07对话，固定交付释放后才验收。保留旧证据，不推送、不连接平台；下方“尚无修复授权”为此前时点。未完成新独立核验前有效接受仍HOLD_OPTION_ROLE_MISMATCH。

- 2026-10-18 A07复核纠正优先：用户追问六框规则后发现普通选项实际映射Q，原规则应为W。六框数量正确，应为Q/W/W/W/W/A；现存回执为Q/Q/Q/Q/Q/A。见 `docs/tasks/A07-Q1-role-mapping-finding.md`。保留既有集成/冻结证据，但当前有效接受为HOLD_OPTION_ROLE_MISMATCH；此前“接受/集成”不得扩展为符合原角色规则。尚未修产品或新增执行额度，不自动唤醒原任务、重跑、推送或连接平台。

- 2026-10-18 A07最新收口：用户核准的真实Q1到A本地模拟已独立验收、调度接受，并在 `07479d69edcbfe8c051f347d21bea714b085e70f` 本地集成。见 `docs/tasks/A07-Q1-local-integration.md` 及最新六项确认。作者/验收均释放，各一次成功，不重复派发或重跑。新材料未推送；B共同采用和A04真实平台仍未证明，下方“正在推进A07”为历史。

- 2026-10-18 最新用户核准：固定Q1内容/区域/单题范围政策已获用户核准，仅用于离线模拟。按 `docs/tasks/A07-Q1-offline-simulation.md` 及独立验收推进，授权记录见 `docs/approvals/A07-Q1-offline-business-approval.json`。新代码走全新增路径，保留旧 A03 pins/A06/I01 与 B 原件。业务核准不等于B共同采用、模型复核变成人工复核或平台资格。下方对应待核准记录为历史。

- 2026-10-18 发布状态优先：用户已授权的阶段二交接与进展架构图已推送至 `codex/a-stage2-handoff`，远端提交 `37089f9e0229da76ae1c45461b7e63929590be56` 已核实。见 `docs/a-stage2-handoff.md`、`docs/tasks/A-stage2-publication-receipt.md`。下方“新材料未推送”为历史时点；A未向B发送消息，不代表B已读取或确认。共同映射/准入/真实单题与A04真实平台阻断仍保持。

- 2026-10-18 当前优先状态：A03-R1、I01-A有限离线范围已接受并本地集成；A06最终交付 `d7873781` 已完成独立及调度接受，并在 `61695306a97e90ea2d69b21c9dfe096f8a641081` 本地集成。见 `docs/tasks/A06-local-integration.md` 与调度JSON。A06作者/验收均释放，不再续派修复或重跑；下方旧待验收段落为历史。B共同映射、准入和合格单题仍待确认，新材料未推送/未发送B；A04真实平台阻断未因此解除。

- 公共技术语义见 `docs/architecture.md` 和 `docs/contracts-v1.md`。A 侧任务另读 `docs/coordination.md`，以任务号、基线和改动范围确定本次工作；B 侧参考 `docs/b-side-handoff.md`，自行管理开发流程。
- 当前主对话仅负责 A 侧开发调度与验收，不向 B 派单、安排排期或做其内部研发验收。A 侧任务交付确切提交、复现命令、样例及限制，执行者不能自行把“写完”记为“验收通过”。
- 2026-10-18 A03-R1 最终候选已交付 `19ab03c849bfab3dcde2dc86be37c59f3add1ebe`（冻结驱动 `9992cd8a`、产品 `6097a06d` 不变）。当前仅按 `docs/tasks/A03-R1-final-delta-review-dispatch.md` 续派现有独立验收，预检及释放后最多2新目标/3dispatch，不重跑M/L1。作者不再修后重跑，无第三包；旧证据与获准L1活源区分，不能为工作树干净回滚活源。整体及I01仍待调度结论。
- 2026-10-18 A03-R1 首包的 M 五例/L1/实测依赖拒绝已有限接受，整体仍 REWORK。当前一次续派为 `docs/tasks/A03-R1-final-bounded-correction.md`：第二次、最终整包，保留产品原 bytes 与已耗 L 尝试；不重跑 M/L1，不恢复驱动纠正额度，冻结后失败不再改后重跑，无第三整包。实际版本和回执见调度 JSON。
- 2026-10-18 用户批准 A03 等价内部替代实施，当前主线为 `docs/tasks/A03-R1-equivalent-runtime.md` 及其独立验收；保留全部原业务功能。T3 已完成的固定失败现场保留，其执行不再续派产品，正在进行的只读验收仅收口旧交付。新任务替代旧窄修复白名单与45秒外层预算，原业务标准、内部安全期限及旧A03退役约定保持。
- 2026-10-18 用户要求原 A03 执行/验收对话停止并交接，剩余任务转交新建的 A03-T1/T2/T3 执行与独立验收对话，见 `docs/tasks/A03-redispatch-2026-10-18.md`。旧任务单“原对话续派”仅为历史规则，不能再唤醒旧对话做产品/验收；新对话默认 xhigh，旧对话设置保持不变。
- 用户于2026-10-17指定：后续子智能体及执行/验收对话派发默认明确使用极高推理强度 `xhigh`，不要使用 `ultra`；不为改强度中断正在执行的任务。例外：用户随后手动调整了 A03 的思考强度，要求保留其设置。向 A03 现有执行/验收对话续发消息时省略 `thinking`，不得按默认规则调回 `xhigh`，也不猜测用户设置的具体档位；其他任务仍遵守默认规则。
- 对 B 提供接口、样例、平台已知行为与变更说明；只检查交接兼容性及 A 侧集成结果。跨侧合同须双方确认，不把 A 的内部通过当作 B 已接受。
- 每个共享改动范围协调主要写入者并保留他人改动；公共合同与根依赖由指定负责人整合。A 侧执行者使用独立分支/工作目录，B 侧工作方式由 B 自定。
- 算法模块不依赖浏览器或 delivery；quality 只报告检查结果；runtime 编排流程但不包含题型规则。
- 内部身份独立于印刷题号和平台题序；通用坐标绑定原始图像、尺寸及摘要。
- 区分离线测试、模拟执行、真实平台验收。保存结果 UNKNOWN 时先核对实际状态，不自动重发。
- 线上操作遵守用户已明确的书籍、范围和允许操作。开发任务不隐含扩大线上写入权限；最终提交人工负责。已经获得的授权不重复索取。
- 当前后续写入测试书为 `46007447`《名校课堂八年级数学上册》，具体约定见 `docs/coordination.md` 的“当前测试用书与授权”。旧样书 `46006966` 继续作为离线参考，不能混用书籍状态或测试证据。
- `.local/` 中的凭据和 profile 不输出、不入库；不要把 token、未脱敏请求或原始视频加入任务单或提交。用户授权的本地登录工具见 `docs/local-login.md`。
- 仅在明确要求时使用当前运行的证书忽略参数，不修改全局设置或变成默认行为。
- 根据改动风险执行相关验证；文档变更检查链接与差异即可。未运行、失败或无法验证的部分如实记录。
