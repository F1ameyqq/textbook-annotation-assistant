# A20 专用登录态恢复与当前书源集中读取

## 目标与已知事实

基线为A19实际final `38e86a1c153eb0ad68ebd22d4403602ffaa6852b`。A19已正式独立及调度只接受固定失败及已证自有释放，原唯一live耗尽，不重启。HTTP200/DCL已证；后续原绑定主框Document被NAVIGATION_BLOCKED，readiness超时，书源读取0。固定path hash与现有同版本脚本明确 `/qieti/login` 路由匹配；这是调度新增静态比对，不回写A19正式报告。具体会话失效原因尚未证明。

本阶段完成一次可审查的专用登录态恢复实现和同context当前书源集中读取，不再单独制造网络诊断轮。当前仅离线开发、相关纯内存验证和独立预检；0真实浏览器/网络/profile/凭据文件/native/占用，0login/write/activation。允许正常必要本阶段代码迭代与相关测试，失败保留，不套一候选或一次开发测试上限，不跑旧suite。

新正式执行与独立分别create_thread，xhigh/model沿用；ID和workflow由根JSON/创建意图绑定，未登记前不冻结可执行身份。根协调文件只读。作者工作区D:/1800-worktrees/a20-authenticated-source，独立先D:/1800-worktrees/a20-review-preparation准备，固定交付后另给raw隔离；子代理不能代替正式独立。

## 可用固定来源

- A19冻结产品、实际结果与独立闭合；根docs/evidence/coordinator/a19-live-independent-closure/。
- 新静态准备 `.local/stages/coordinator/a19-navigation-followup-preparation/`，只是线索，作者/独立须按精确来源验证必要结论。
- 现有同版本Script仅允许离线静态读取原件：`D:/1800/.local/stages/a17-excluded-static-live/static-assets/1-d0a5ebce18bc92d7643662ecec2d078bb295214111e7cb32688f0b88e05bed41.bin`，SHA d0a5ebce18bc92d7643662ecec2d078bb295214111e7cb32688f0b88e05bed41，3065996 bytes。A19实际元数据报告同SHA。禁止执行、重新请求、复制原Script/来源sidecar到Git或输出任意敏感内容。
- 已定位静态线索：Ui=`/qieti/api/user_login`，登录函数Pze通过gn.post调用Ui+`/login`，JSON键username/password；成功组件调用后router.push('/')，不能据此假定已经在受保护viewer。两处login跳转与401分支应按来源核实，不能用静态存在反推本轮实际响应401。
- `docs/local-login.md` / `tools/usense_login.py`可静态复用既有本机配置和专用profile派生规则、固定登录页表单、凭据不回显及一次提交经验；不运行旧工具或其旧测试。历史本机配置使用授权不等于本阶段已获在TLS例外中重新发送凭据。

## 具体恢复路线

复用现有A19内核与精确资源释放，不另造通用业务执行系统。拟定本阶段未来唯一轮：同一个原专用context、最多900秒含释放；固定登录页 `https://www.usense.com/qieti/login` 和受保护页 `https://www.usense.com/qieti/annotateUnified`，最多2次获准Document主导航，分别限上述顺序各1次。先打开登录页，在原主框/原站HTTPS/无重定向/确切已知用户名密码表单成立后，才可从原本机配置读取并填写，一次官方UI登录提交。提交成功并核实必要响应/页面事实后，仅一次导航到原受保护页；真实身份成立后同context继续六个原固定业务GET、viewer14/173两原图与映射，均各最多一次。不能在登录成功处再拆一个读取轮。

最多1次登录POST，确切同源 `/qieti/api/user_login/login`，须由当前固定UI操作产生、关联原frame，且限username/password两键；不要手工注入token、复制其他profile状态、绕过页面校验或凭据重新尝试。具体JSON编码/额外字段/前端成功条件以固定脚本核实后收窄；若现有来源不足，先给出明确不可离线固定的缺口，不猜接口或自动运行探针。登录页若显示已经登录，必须依据明确的当前已认证标志决定0次凭据提交并转入同轮受保护页，不能仅靠URL/HTTP200。

UI若SPA router.push不产生Document，不冒充额外HTTP导航；其他Document目标、额外reload、跨源/重定向或不明身份仍停止。不为登录把整个域API/POST放开。既有六业务GET/原图、version至多1、原同源session/static范围和共享排除16保持；必要登录会话请求须具体列明、在方案内有界，不扩展新来源或未知API。任何正文保存、题框写入、上传/OCR、书级提交仍0。CDN仍拒绝；不可声称它非必要或下载替代脚本。

当前静态线索已确认共享响应拦截器含刷新POST及原请求重发，不能直接继承。网络层必须拒绝刷新API和第二次登录POST/原请求自动重发；不要在旧请求失败后靠新请求隐式继续。只对本轮本来就获准的登录POST/权限GET被动记录有限HTTP状态和来源关联、业务解码成功/拒绝类别，禁止输出自由detail/message或响应对象，0额外请求。明确预期失败立即退出，不再等一个完整readiness超时才发现需要登录；保留首次真实错误和最终guard状态。

凭据仅运行中直接读取原 `.local/usense-login.json`，禁止预检时读取真实值。用fake credentials测试；命令行/聊天/日志/异常/报告/截图均0用户名密码/token/cookie/header/body，禁止DEBUG/PWDEBUG继承暴露。派生profile必须与原非敏感指纹 `b4620cd9fe064121a916062126321b7bba3862185d8919bf228f1399097a0d00` 相符，不能创建新profile或替换日常Edge。填写前后origin/frame确认；点击前不可逆记本轮提交意图，原生与context双层各自预留一次实际POST，避免重复层误算成可再发送；异常、超时、验证码/MFA/错误口令/未知结果立即停止，不再点、不重新提交。

真实配置固定为 `D:/1800/.local/usense-login.json`，不能用新worktree内同名配置代替；原profile在根`.local/browser-profiles/`，仅获本阶段直接决定后运行中派生/核指纹并原位复用。离线只可核配置reader源码/格式说明，不检查或读取真实配置内容。

登录响应仅保留安全有限字段/HTTP状态/明确结果，绝不输出返回token或自由message。真实认证须受保护viewer及当前book身份/允许的读取证据，不能把登录POST200或router.push当成功。登录不明则后继NOT_RUN。所有失败/late guard/回调结清与自有释放按现有内核保持；不为顶层报告差异开无关修订，但登录结果UNKNOWN绝不重发。

## 独立预检、许可及冻结

A17“一直批准”持续许可只覆盖同类原专用context只读TLS例外，不自动扩展这次凭据发送。本阶段必须生成自己的scope/run_id/executor/workflow/candidate/报告/决定/activation/一次额度与路径，明确login_submission_limit=1而business_write/upload/OCR=0、nav_limit=2、context1、900秒。门禁要求本阶段额外直接决定明确允许本次登录提交及凭据在context证书例外中发送；未具备时拒绝，不借用A17或旧A19决定，不恢复旧额度。

先完成可运行具体候选、精确请求/导航计划、脱敏与拒绝控制、正式独立有限接受。然后调度将本阶段完整方案交用户决定，决定是最后一步；当前不要向用户索要账号密码或重复问平台许可/TLS旧批准。若有已存在的直接授权需要核实，列出来源供调度确认，作者不能自行认定已激活。

候选按必要性修改现有gate/policy/probe/launcher，可新增窄auth辅助模块；decode/js_wire和旧native/证据原bytes保持。新增tests/a20_authenticated_source/和docs/evidence/A20/authenticated-source/，只跑本阶段相关纯内存测试，禁止旧A19 18/3、A18/A17/A16等suite和真实产品子进程。保留作者失败及正确的原始raw。固定产品commit、final、所有运行依赖（含父包初始化文件）、raw导出、差量原结果、sha清单、报告和明确释放后交根；根机械核证再给同正式独立新隔离。

未来路径预留 `.local/stages/a20-authenticated-source-live`、`.local/stages/a20-authenticated-source-activation.json`；作者不得创建。独立机器报告根路径docs/evidence/coordinator/a20-independent-closure/independent-result.json，具体用户决定docs/approvals/A20-authenticated-source-user-decision.json。任何live由根另派，不自行承接。

## 后续主线

书46007447候选普通单选仍第2节《一定是直角三角形吗》基础印刷1，四组选项1,2,3/2,3,4/3,4,5/4,5,6，历史答案C，Q/W/W/W/W/A。当前未录入/目录/bbox须真实证据核实，不自动换题、不沿用旧Q1核准。当前sample0、正文/schemaUNKNOWN、R02未修、写入资格false。源目标确认后集中必要真实接线及具体题/政策/次数，首题保存、内容和题框刷新重开独立读回，再最多5题。其他三例HOLD、自然全量快照保留Q22但不导航/样题/重放、0B消息、无书级送交。截止2026-10-22日晚不变。
