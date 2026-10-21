# A22 原专用会话复用：最小方案准备

**PREPARATION_ONLY / 非候选、决定或正式验收。** 本次仅静态读取 `D:/1800-worktrees/a21-live-review` 中固定的 auth/policy/gate/probe/launcher 与 live-result。实际基线为 `29a243227893cdbd8e7d235a8c787b4d721ed8e2`，正式独立正在核 A21 实际结果；本辅助不代替其结论，不读取活动目录、profile或配置。

## 当前证据支持什么

固定作者 live-result 记载 A21 已用唯一轮、无重试：实际登录POST1、HTTP200、有限响应投影 ACCEPTED_NUMERIC_CODE 且 credential_return_present=true；UI转换及 protected_viewer_authenticated=false，phase仍LOGIN，唯一当前session收据为permissions，六GET/两图均NOT_RUN。它还记录 context/runtime关闭及自有资源释放。**这些不证明浏览器已把会话持久化，也不证明下一轮认证。** 可准备使用原profile的新只读尝试；不能恢复A21额度或将旧响应移入新轮认证证据。

既有代码 `probe.py` 691–715 用原路径启动 persistent context、先offline安装两层守卫再online；1248–1264及1292–1294调用既有 profile_binding、比对固定指纹，保留原精确占用和自有释放流程。原指纹为 `b4620cd9fe064121a916062126321b7bba3862185d8919bf228f1399097a0d00`。不新建/复制/替换profile、不清锁、不读取用户名密码来重新推导路径。profile_binding的依赖实现不在本次获准六文件内，未复审；正式作者应在原冻结依赖中静态核其无凭据配置读取，不运行它来补准备证据。

## 最小路径与必要改动

目标是一个原context、一轮最多900秒含释放、**只一次 `https://www.usense.com/qieti/annotateUnified` 主导航**，在同context核当前受保护事实后继续既有六GET及viewer14/173两图；0本机用户名密码配置读取、0表单填入/点击、0登录POST/refresh/自动重发，0业务写入/上传/OCR/样题。原来源、图片规则、version≤1、排除总16与原图注册绑定保持。

| 原模块及行号 | 最小必要修改方向 |
| --- | --- |
| auth.py 91–128、167–186 | 原类硬编码初始LOGIN、LOGIN→TARGET两导航及每层2次；缩为固定VIEWER单阶段、唯一TARGET意图和每层1次。认证必须来自本轮当前事实，不能预设reused/authenticated为真；快照明确零凭据/提交及复用尝试与确认的区别 |
| auth.py 39–54、130–150 | 新范围的凭据读取、arm_submit、reserve_login路径须不可达或在I/O/预留前无条件拒绝；不保留运行时开启登录的开关。不能仅依靠“不打算调用” |
| policy.py 164–177 | 删除本轮LOGIN_POST特例，POST和其他写方法硬拒绝；Document仅原TARGET GET一次，LOGIN、其他页面、reload/redirect均拒绝。原分类/框身份/来源规则不放宽 |
| probe.py 795–856、984–1001 | 替换本轮入口对authenticate的依赖：直接arm TARGET一次，沿用导航、readiness、drain、书籍和后继collect；不访问登录页，不运行known_form/read_credentials/fill/click。无需修旧 `/home` 等待条件 |
| gate.py 87–188 | 新A22身份/候选/报告/决定/标记；navigation_sequence只TARGET、navigation_limit1，凭据读取/填入/登录提交/refresh/resend为0，session只VIEWER阶段。完整新scope与模板精确同类型绑定；新字段总数以冻结方案为准，不机械沿用A21的47项及凭据授权true |
| probe.py 221–257、1248–1306；launcher.py 16–124 | 仅必要A22身份/门禁/新路径绑定；原deadline、Job、持有创建身份、marker原子性、context/runtime及回调结清保持。不另造driver或释放系统 |

**不能只跳过 `authenticate()`。** 那样AuthFlow仍等两导航和旧登录/复用条件，policy仍准入登录POST，gate仍要求A21直接凭据授权，状态与网络边界不一致。

## 当前受保护证据与停止条件

沿用现有同一context的可见viewer容器、精确TARGET、原主框关联和当前已准session响应投影；本轮唯一导航响应若缺失/非200或出现401/403则停止，200本身不是认证。可将已有 `admit_viewer` 的VIEWER阶段关联、当前session及导航计数口径缩为一次导航，明确去掉对本轮凭据POST的依赖，并仅在上述当前事实成立后准入既有首个book GET。`book_identity` 仍必须核46007447才继续余下书源读取，viewer访问与book身份分别报告。

当前session须按原固定路径、原主框、两层预留及有限业务投影关联，不采用A21历史permissions收据。未出现本轮可用session事实、出现登录页/密码框、LOGIN_REQUIRED、401/403或其他UNKNOWN时停轮，不自动登录。profile身份字段若未出现，不能报告“账户身份已核”；permissions投影、HTTP200或本地token存在各自都不能单独替代受保护证据。不为补证增加profile请求、额外导航或探针。

原session集合仅 `/qieti/api/user_login/profile`、`config/permissions`、`config/teams`；改为单VIEWER阶段每路径至多一次，总上限3，比A21两阶段缩减，按已准当前前端请求观察，不新增补发。原六业务GET各1、两原图各1保持；若前端本轮行为不能在这些界限内证明，就报告实际缺口，不临时扩大次数。

**“0凭据读取”需准确表述。** 原 `probe.py` 859–888 的GET_JSON会在原站页面内部读取已有localStorage会话token，为已准GET构造Authorization；token不返回Python、日志或文件。复用会话仍会使用既有认证材料，不能声称浏览器完全不使用token/cookie。本方案禁止读取本机用户名密码配置、表单填写、登录提交及令牌导出/注入，保留原站内部的既有GET方式和缓存/原生捕获对账。

## 有限新离线控制建议

仅正式新执行可做必要相关fake测试；本辅助没有运行任何测试。无需重跑A20/A21或其他旧suite。

1. 成功模拟仅TARGET一次、每层一次、当前受保护容器和合法session收据后，既有六GET两图同context推进；凭据文件读取、known_form/fill/click/login函数spy若被调用立即失败，计数必须0。
2. 登录页/密码框、session缺失或401/403、导航未知/错误书号、第二导航/redirect：立即停止，后继NOT_RUN，无登录或补发；历史A21收据不能用作当前证明。
3. 两层POST/refresh/login GET或错误主框/来源始终拒绝；不得用旧登录意图、旧批准或人为改flow属性绕过固定reuse-only边界。
4. 单VIEWER session重复、version重复及共享排除第17事件保持原停止语义；原窄静态图片规则、六GET与两图限额不扩张，只测与本差量有关的边界。
5. 新scope/template/decision/report完整绑定、旧A21 activation/候选/许可拒绝；窗口/原profile指纹/一次性标记错误在任何真实资源动作前拒绝。用fake/native替身，不查真实profile/占用。
6. 有限相关late fatal/pending与释放传播仍进入最终ERROR/UNKNOWN；未改截止和OS释放实现以raw同一性引用原有限证据，不扩成全回归或全机释放证明。

## 后续门禁与限制

先由根完成A21实际收口，再固定A22新正式执行/独立任务、产品/候选/完整依赖raw和有限预检。新task/run_id/workflow/执行ID/输出/决定/activation/report/标记/窗口均PENDING，本准备不创建。真正reuse-only范围可由根引用适用的持续只读context TLS许可再绑定本阶段具体范围；不借用A21已耗单轮决定，不把持续许可扩大为新登录或写入。独立及调度通过前0live。

旧A21等待`/home`条件差异原件保持，新轮不登录则不修这条无关路径。A21真实超时原因、profile持久化与当前认证仍各自UNKNOWN。只据本次获准固定六文件给出准备，未读其他活动目录、实际profile、配置或网络；没有新候选、决定、activation、根状态改动或提交，辅助已释放。
