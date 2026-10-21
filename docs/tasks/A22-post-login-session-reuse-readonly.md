# A22 原专用会话只读复用与当前书源读取

A21实际轮已由正式独立和调度有限收口：一次登录POST/HTTP200、有限业务码接受且检测到返回凭据，UI转换未确认后TimeoutError/UNKNOWN停止。受保护认证、profile持久化和实际超时根因均未证明。A21本轮批准和额度已消费，不重派A21、不重发登录。新阶段依据这一新事实准备原profile只读复用，先离线开发及有限独立预检，当前0新live。

## 最小实现

复用现有current_readonly内核和双层守卫，不另造浏览器/请求/恢复系统。A22固定为VIEWER单阶段，唯一导航 https://www.usense.com/qieti/annotateUnified；一个原专用persistent context，900秒总期限含释放。0本机用户名密码配置读取、0登录表单填写或点击、0登录POST、0refresh/自动重发，0业务写入/上传/OCR/样题/书级提交。不要仅跳过authenticate：auth状态、policy与gate须同步缩为本次reuse-only边界。

auth.py新路径从VIEWER开始，唯一TARGET导航意图，两层各1预留且关联同一实际导航；不能预设reused或authenticated为真。read_credentials/arm_submit/reserve_login及本轮登录入口在任何文件I/O/表单动作/网络预留前硬拒绝，无运行时开关重新启用。固定policy不再准入LOGIN_POST；POST及其他写方法、LOGIN Document、额外主导航/reload/redirect仍硬拒绝。不要修旧/home等待路径；本阶段不登录，不需要该条件。旧A21静态路由差异保留为历史分析，不能称已证实际根因。

沿用同context原主框、精确TARGET、可见受保护viewer容器、无登录/密码表单、当前获准session响应关联和有限业务投影作为viewer准入组合证据。URL、HTTP200、本地token存在或A21历史receipt不能单独证明认证。沿用原admit_viewer当前session语义并缩为一次导航；不人为新增必须发profile诊断请求的门槛。若缺少本轮组合证据、401/403、登录跳转/表单或UNKNOWN，立即停止，后继NOT_RUN，不自动登录或补请求。viewer准入后同context继续首个book GET核46007447，身份通过才继续目录/框/来源/页映射/两图；分别报告viewer访问、账户身份字段是否可用及书籍身份，不能混称。

原session仅三路径 /qieti/api/user_login/profile、/qieti/api/user_login/config/permissions、/qieti/api/user_login/config/teams（以冻结SESSION实际字面为准，先核实路径，不按本文缩写猜）；单VIEWER阶段每路径最多一次，总最多3，按原前端请求观察，不新增诊断补发。六固定业务GET各最多一次、viewer14/173两原图各最多一次、version至多1、共享排除16；原来源与注册原图路径、窄静态图片准入规则、CDN和未知同源拒绝/有界继续条件均保持。两个守卫、await前预算记账、身份/逐跳/WS/未知API和晚到fatal/未结清进入ERROR/UNKNOWN保持。导航成功即在同轮集中书源读取，不拆新的书/目录/图片诊断轮。

准确表述会话复用：原站页面内部既有GET_JSON可使用本机浏览器已有会话token发送已准GET，token不能导出到Python/日志/文件，也不注入/复制其他会话。禁止的是读取本机用户名密码配置和重新登录，不能宣称浏览器不使用已有认证材料。原profile指纹 b4620cd9fe064121a916062126321b7bba3862185d8919bf228f1399097a0d00；静态核冻结profile_binding依赖无需读取本机用户名密码即可定位原profile。保留Edge/原profile，不新建替换或清锁/批量kill。

## 新范围、权限与交付

scope POST_LOGIN_SESSION_REUSE_CURRENT_SOURCE_READONLY。A22 task/run_id/executor/workflow/candidate/report/decision/activation/output/单次标记全部新绑定；拒绝A21或更早候选/批准/activation。候选与完整scope/template精确同类型同值绑定，字段数按实际新范围，不机械套47项。明确local_credential_config_read_limit=0、login_submission_limit=0、navigation_limit=1、navigation_sequence仅TARGET、session_phase_limit=1，其余实际字段与报告一致。不能保留旧凭据授权true来通过gate。

用户A17“一直批准”的同类原专用context临时TLS只读持续许可仍适用：D:/1800/docs/approvals/A17-excluded-static-user-decision.json SHA f5ceacf9028f773ead882f3e6601004c2c3e28171be31abb85c5be99a1d67b46。独立及调度有限预检通过后，调度直接将该已有许可绑定A22完整具体范围/候选/机器报告/profile/一次额度/900秒窗口；无需再问同类TLS或平台连接许可。它不授权新增登录/业务/来源，不恢复旧轮数。作者不能自激活。

预留 D:/1800/.local/stages/a22-session-reuse-live、a22-session-reuse-activation.json，决定D:/1800/docs/approvals/A22-session-reuse-user-decision.json，机器报告D:/1800/docs/evidence/coordinator/a22-independent-closure/independent-result.json；当前不得创建。新live最多1，当前未激活；首异常/未知停并精确释放，不重试/延期/清标记/换目录。

工作区 D:/1800-worktrees/a22-session-reuse，branch codex/a22-session-reuse，base29a243227893cdbd8e7d235a8c787b4d721ed8e2，根已建初始干净短路径worktree，勿重建。正式ID/workflow见根JSON和creation-intent/threads-created（如登记尚未到，按当前聊天确切ID绑定并等根登记，不自行猜）。产品修改白名单：src/annotation/source/usense/current_readonly/auth.py、policy.py、gate.py、tools/a16_current_state_probe.py、tools/a16_current_state_launcher.py；仅上述reuse-only缩减和必要身份绑定。decode/js_wire/native/reference/OS释放与时间守卫原bytes不改。新tests/a22_session_reuse/和docs/evidence/A22/session-reuse/。根协调文件不改。

允许正常必要的新纯内存fake测试和相关修正，保留失败，不人为套一候选/一次开发测试；0真实产品/launcher/native子进程、browser/network/profile/真实配置/占用。有限新差量集中核成功模拟同context贯穿、凭据读取/fill/click/提交spy为0、单导航/单session阶段、历史receipt拒绝、登录/401/403/未知停止、两层POST和旧授权拒绝、late fatal和范围绑定。未改部分以raw同一性引用原有限证据，不跑旧A21 16/5或其他suite，不刷历史NOT_RUN。报告微小差异且正确停止原件完整时列限制，不无关返工。

冻结产品/final、所有候选依赖Git raw、有限新测试和失败记录、清单及精确释放。用raw导出验证，不能比较Windows普通checkout与Git raw的CRLF/LF相等；父包完整。只提交白名单；Git先GIT_NO_LAZY_FETCH=1且每条-c core.longpaths=true，禁reset/clean/stash/全量add。根核固定交付后给同正式独立隔离输入，作者不能自行接受或启动live。

根已核准备docs/evidence/coordinator/a22-session-reuse-preparation/和A21实际闭合docs/evidence/coordinator/a21-live-independent-closure/。这些不是新平台证明。其他三例HOLD、Q22不导航/样题/重放、0B/外部联系人消息、无书级提交。目标仍2026-10-22日晚普通单选首题保存和刷新重开读回后最多5题。先取得当前书源再集中首题接线，不拆无关诊断。
