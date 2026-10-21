# A23 当前会话响应结清与同轮书源读取

用户明确要求加速。调度修订自己的工程顺序：A22固定实际失败归档与A23必要离线修正并行，不再等待报告归档才开发下一步。A22实际final3517982bd416ff77fdf596e80c502a75d780f2b9已由作者固定释放；一次导航HTTP200、DCL、标注容器就绪47ms，随后PROTECTED_AUTHENTICATION_UNPROVEN。permissions两层仅预留，session_receipts为空；尚不能断定认证失败或响应为何缺失。A22 live1已耗尽，原件与原轮保持。本任务是有新范围与实现的新阶段，不能启动旧A22。

固定源码显示collect在drain后立即admit_current_viewer，drain只等已登记回调任务，不等尚未返回的网络响应；admit_viewer要求session_responses非空，所有BUSINESS_*又在此之前拒绝。不要把这一时序缺口泛化成新的认证框架。最小修正是在原context内完成当前会话响应，再直接六GET和两图。当前只离线开发，0真实浏览器/网络/profile/配置/native占用/live。

## 具体实现和范围

复用原current_readonly内核，VIEWER单阶段、原TARGET https://www.usense.com/qieti/annotateUnified、原专用profile，一个context/一次主导航/900秒含释放。0用户名密码配置读取/解析、填写、点击、登录POST、refresh、自动重发、业务写入、上传、OCR、样题、书级提交。原auth禁登录入口继续在I/O/预留前拒绝，无启用开关。原profile指纹b4620cd9fe064121a916062126321b7bba3862185d8919bf228f1399097a0d00保持；页面内部原有认证材料只用于既定GET，不能返回Python或日志、复制会话或注入。

先核原page/main_frame、精确TARGET、可见受保护viewer、无登录/密码表单和当前guard无失败。会话完成的唯一新逻辑：

1. 已有本轮关联且完整成功的session有限投影则复用。若某个获准session已被任一层预留或正在发送，先在一个不超过20秒的统一等待期限内等待该原请求及body投影完成；必须关联原request/原frame/两层预留，不只等现有callback队列为空。无新增请求，等待中及时响应401/403、网络失败、身份错误或晚到guard失败。不重置等待期限、不重发已预留请求。
2. 只有没有本轮成功投影、也没有任何session在途/已预留未明结果时，才允许明确主动读取现有白名单中的精确 `/qieti/api/user_login/profile` GET最多一次。使用原三session路径总预算中的profile名额，不增加总请求额度。调用前同步预留唯一主动意图，双层请求关联和await前记账，前端并发同路径不能导致第二发送。已有失败或UNKNOWN不能靠此补救，不轮询三个接口、不替换路径。
3. 主动GET仅在原页面内携带已有认证材料；返回Python前只输出固定HTTP/有限业务结果/身份字段是否存在，不返回完整profile/body/用户名/token。原有被动session响应也只保留有限投影。若主动profile成功但字段或业务语义不足以支持当前准入，明确UNKNOWN停止；不要凭HTTP200/token存在冒充身份。若复用原permissions/teams有限投影准入，账户身份仍可NOT_OBSERVED，不人为额外发送profile来补齐账户字段。
4. 当前组合证据成立后，按原顺序同context执行book GET核46007447，接目录/全量框/来源/page14/page173/两原图及映射。book HTTP200或正确ID不能单独改写为账户身份已证明。成功不在“认证已证”处提前结束再拆书源阶段。原一次性GET捕获复用保持，禁止发送后UNKNOWN重发。

三条session精确路径为 `/qieti/api/user_login/profile`、`/qieti/api/user_login/config/permissions`、`/qieti/api/user_login/config/teams`，VIEWER每路径最多1、总最多3；主动只可profile，其他只观察原前端。六业务GET各1、viewer14/173两注册原图各1、version最多1、共享排除16，原静态窄Image/来源/逐跳/方法/WS/API身份/晚到fatal/pending结清边界保持。未知API、写方法、登录跳转/表单、401/403和结果不明仍停止。原图URL只从本轮源响应注册，禁止猜URL。完整Script及来源sidecar仅受控.local，不执行或复制Git。

## 交付和节奏

scope CURRENT_SESSION_COMPLETION_AND_SOURCE_READONLY。新task/run_id/executor/workflow/candidate/模板/报告/decision/activation/output绑定自身范围，明确session_completion_timeout_seconds=20、active_session_get_path为精确profile、active_session_get_limit=1且计入session总3、credential_config_read/login/write=0。不套旧A22 scope、不借旧activation或已耗额度。预留D:/1800/.local/stages/a23-session-completion-live、a23-session-completion-activation.json；决定docs/approvals/A23-session-completion-user-decision.json、机器报告docs/evidence/coordinator/a23-independent-closure/independent-result.json；当前不得创建，不自激活。

已有A17用户“一直批准”同类只读TLS持续许可有效，原件docs/approvals/A17-excluded-static-user-decision.json SHA f5ceacf9028f773ead882f3e6601004c2c3e28171be31abb85c5be99a1d67b46。有限独立与调度预检通过、A22实际释放核证后，根直接绑定A23具体候选/报告/profile/唯一预算/900秒窗口，不再问同类TLS/平台连接许可。这不扩大登录、写入或新来源。A22原轮不重开。

作者D:/1800-worktrees/a23-session-completion、branch codex/a23-session-completion、base3517982bd416ff77fdf596e80c502a75d780f2b9；根创建短路径worktree。只改src/annotation/source/usense/current_readonly/auth.py、policy.py、gate.py、tools/a16_current_state_probe.py、tools/a16_current_state_launcher.py中必要会话时序/主动只读及新身份绑定；decode/js_wire/native/reference/OS释放和总时间守卫原bytes不改。新增tests/a23_session_completion/和docs/evidence/A23/session-completion/。不改根协调文件。

先做可运行最小差量，正常必要纯fake离线迭代允许并保留失败，不人为限制一候选/一次测试。集中证明：延迟原session响应可完成；没有session时唯一profile读取；已预留/UNKNOWN不得补发；并发前端与主动不能双发；401/错frame/晚到失败停止；原禁登录/无凭据泄露；成功同轮六GET两图及完整scope。只跑新相关测试，不刷A22或旧suite/历史NOT_RUN，不做通用解析器/重构。作者约30分钟提供固定交付或明确阻断，时间为工作目标而非通过保证。

固定产品/final、完整Git raw依赖、差量结果与失败、清单、精确释放。所有Git先GIT_NO_LAZY_FETCH=1、每条-c core.longpaths=true；不用reset/clean/stash/全量add。raw导出验证不比较Windows CRLF checkout。根核固定包后同正式独立有限预检。报告微小差异且实际正确停止、原件完整者列限制，不为格式重跑产品。

首题保存仍未运行。取得真实书源后集中必要真实sender/receipt接线、固定具体新题/政策/次数并完成保存和内容/题框刷新重开独立读回，再最多5题。其他三例HOLD、Q22不导航/样题/重放、0B/外部联系人消息。截止2026-10-22日晚不重起算。
