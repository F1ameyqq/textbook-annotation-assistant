# A20 一次专用登录恢复与同轮书源读取：具体决定提案

状态：`READY_FOR_DIRECT_USER_DECISION`。正式独立与调度已完成有限离线预检；本提案尚不是用户决定，也未创建 activation 或启动真实会话。

## 本次请求

允许在原专用无头 context 中临时忽略 HTTPS 证书校验，并在运行时直接使用本机已有配置，最多提交一次官方登录表单。登录成功且受保护页面/当前会话事实成立后，在同一 context 读取书 46007447 的书籍、目录、全量题框、源页及 viewer14/173 两张原图与映射。总计最多一次启动、一个 context、两次固定 Document 导航、一次登录提交、15分钟含释放。

本次新增许可是**发送既有用户名和密码**。此前“一直批准”的同类只读 TLS 许可继续有效；它未包含这次凭据提交。已观察的主站证书不覆盖 www.usense.com 且过期，当前证书状态未追加探测，本轮按无法可靠确认服务端身份处理。context 例外影响主站和原已准 OSS；用户名和密码仅提交给下述固定主站登录接口，既有会话信息也可能随获准请求发送。无需用户提供、复制或在聊天中显示密码。

业务写入、正文/题框保存、上传、OCR、样题和书级送交均为 0。验证码/MFA、拒绝、未知登录结果、意外错误或窗口/占用冲突即停止，不重发、不换 profile、不重开旧轮。

## 固定范围

| 项目 | 本轮界限 |
| --- | --- |
| context / 时间 | 原专用 context 1 个，900 秒包含启动、登录、读取和释放 |
| 导航 | 先 `https://www.usense.com/qieti/login`，再 `https://www.usense.com/qieti/annotateUnified`，各最多一次 Document；其他 Document、reload、redirect 拒绝 |
| 登录 | 原主框、原站、确切表单校验后，官方 UI 最多点击一次；发送前写不可逆意图 |
| 登录接口 | `POST https://www.usense.com/qieti/api/user_login/login`，JSON 仅 `username` / `password` 两键，值与本轮内存配置一致 |
| 配置 | 获准 live 时才直接读 `D:/1800/.local/usense-login.json`；不使用 worktree 替代文件，不输出值、不手工注入 token |
| 原 profile 指纹 | `b4620cd9fe064121a916062126321b7bba3862185d8919bf228f1399097a0d00`；另核用户名派生目录相符，不新建或复制 profile，不改日常 Edge |
| session GET | `/qieti/api/user_login/profile`、`/qieti/api/user_login/config/permissions`、`/qieti/api/user_login/config/teams`；无 query/redirect，每路径在 LOGIN、VIEWER 两阶段各至多一次，总上限六次 |
| 书源 GET / 原图 | 下表六个 GET 各一次；viewer14/173 原图各一次，必须由本轮源响应注册真实路径 |
| 原图 origin | 仅原站或 `https://oss-ef-bd-2026-gz.oss-cn-guangzhou.aliyuncs.com`，路径限 `/upload_images/46007447/` 且符合当前源绑定；不猜未取得的图 URL |
| version | 原站 `/qieti/version.json?t=<原样13位时间戳>` 静态 GET 至多一次 |
| 其余请求 | 原冻结同源 static 范围保持；CDN Script 仍拒绝发送。既有限定排除合计16事件，含双层保守记账，第17次停止。总 HTTP 请求数不等同六业务GET加两图 |
| 重发 / 写入 | refresh POST、重复登录、自动重发、未知 API、其他写方法均拒绝；业务写入/上传/OCR/样题/送交0 |

六个业务 GET 的 origin 均为 `https://www.usense.com`，精确路径与 query：

1. `/qieti/api/claim_book/books?page=1&pageSize=10&id=46007447`
2. `/qieti/api/annotate_ocr/directory/get?file_id=46007447`
3. `/qieti/api/annotate_pic/get_manual_annotations_unified/46007447`
4. `/qieti/api/annotate_pic/pre_annotation_source/46007447?annotationType=mr_pre`
5. `/qieti/api/annotate_pic/pre_annotation/46007447?pageNum=14&annotationType=mr_pre`
6. `/qieti/api/annotate_pic/pre_annotation/46007447?pageNum=173&annotationType=mr_pre`

原生与 context 各一次 POST 预留用于约束同一实际请求，不授权发送两次。登录页若出现候选可验证的当前已认证事实，可使用 0 次凭据提交分支；URL、HTTP200、登录POST200或 SPA 跳转本身不构成认证证明。受保护容器、当前会话与 book 身份分别报告。认证后直接完成同轮读取，不另拆登录后的诊断轮。

## 已完成的核证与限制

正式独立新 suite 35/35（2250ms）、独立控制5/5（641ms）；调度核25报告成员及清单自身、114固定输入、39项完整scope绑定。有限结论为 `ACCEPTED_OFFLINE_ONLY / BOUNDED_OFFLINE_AUTHENTICATION_AND_SAME_CONTEXT_SOURCE_PREFLIGHT`。调度接受提交 `feeb5dc89cb9a66b649860c2d47e92276066f587`。

这些结果证明固定离线流程与控制。真实 DOM、CDP postData、会话时序和当前服务端响应尚未实测；成功链中未变的读取器使用 fake 对象，不是新的真实图像/库存验收。任何实际偏差按上述停止规则处理。作者假时钟失败、首包装缺路径和独立封存工具解码失败全部保留；A19 的实际401原因、launcher自身OS身份及旧限制不因此关闭。

实际读取成功后仍须另完成首题真实接线、具体新题/政策/写入次数与独立刷新重开读回。本提案不授权首题保存或最多5题阶段；其他三例HOLD、Q22不导航/样题/重放、0B及外部联系人消息保持。

## 精确绑定

| 绑定 | 值 |
| --- | --- |
| task / scope | `A20` / `AUTHENTICATION_RECOVERY_AND_CURRENT_BOOK_SOURCE` |
| run_id | `A20-authenticated-source-01a159aa-42b4-7103-bfaa-9767969d9b8e` |
| 执行 / 独立 | `01a159aa-42b4-7103-bfaa-9767969d9b8e` / `01a159ab-01ba-7093-89a6-69e7ce572c38`，host `local` |
| 产品 workflow | `52be34a72c43a7331976aba4b286138b9183856b` |
| 产品 / final | `28203196b4f2dae27b1de4213b27da9a41ae3139` / `b41e88d7756fde9d7f1b348ce5a300d1104e765b` |
| 候选 SHA256 | `91db377e44b5b864208cc27a078d25266b3375bba2fdee18b9c648f37b572a7b` |
| 作者完整清单 SHA256 | `bc8d386edaae3560774ed3082d8e1e79ef81107a39ac4d17b8c3071f3615777a` |
| 固定输入清单 SHA256 | `5db4d9768e77b72fd06995bdce321d2c1eac706ce0e01926c2f45fc0f964c5b4` |
| 精确计划 SHA256 | `0fda06e72c3cc43a664a4981c1c230df9f8304cfae65599e721a187951b9fe4a`，final 的 `docs/evidence/A20/authenticated-source/plan.md` |
| 独立机器报告 | `D:/1800/docs/evidence/coordinator/a20-independent-closure/independent-result.json` |
| 机器报告 SHA256 | `93da76c7dcd34c55b80ac6d408a328096a714d1a574876986a149d3347fd58fd` |
| 独立报告 / 清单 SHA256 | `570ee549c671da51c1c0185957abd2e314f4562c27b97f848e1c1fa6ffdfdb2d` / `7ae40c4e7626623a19d301a469f9b752ae283f026c80c7c8a05af6adf78e228a` |
| 独立释放 SHA256 | `064868fe0ae5b1666c7255371e855b338957b2c504cf5596c00cbb1e24090d81` |

后续直接决定路径固定为 `D:/1800/docs/approvals/A20-authenticated-source-user-decision.json`，activation 为 `D:/1800/.local/stages/a20-authenticated-source-activation.json`，输出为 `D:/1800/.local/stages/a20-authenticated-source-live`。三者当前均未创建。

用户明确同意后，调度保存原问题与原答复，将直接决定和上述机器报告 raw hash 绑定到本 A20 activation；使用原 profile 指纹及自己的新一次性标记，固定从获准派发时开始的900秒窗口。执行仅从固定 raw 代码启动原外层 launcher 一次，不先跑静态launcher/旧suite或额外探测；不延长窗口、不清标记、不补发。完成后仍由同正式独立对实际结果与释放核证。
