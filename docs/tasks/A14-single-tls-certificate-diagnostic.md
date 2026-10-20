# A14：单次公开证书链诊断

2026-10-20。A13原唯一复用观测在首次导航返回 `ERR_CERT_COMMON_NAME_INVALID`，0登录/书籍/业务，已停止释放。该明确TLS错误是本任务的新依据；A13次数已耗尽，不能重跑或恢复。用户持续授权连接平台和推进首题路线，但当前没有新的忽略证书参数授权；本任务保留严格验证，仅取得公开证书证据以选择修复方向。

先等A13正式独立核证固定失败/释放，由调度明确派发后执行。新阶段分别新建正式执行、正式独立验收对话，xhigh/model沿用，先落盘去重意图再登记确切ID。验收只在作者固定释放后处理原证据，0新连接。不得用子代理替代正式阶段。

## 唯一范围和边界

- 写入白名单仅两处：执行目录 `D:/1800-worktrees/a14-tls-diagnostic/execution-output/` 保存公开脱敏交付；`D:/1800/.local/stages/a14-tls-diagnostic` 保存不入库的私有原始流。不改产品、主线、浏览器/profile、系统代理或信任库。
- 仅1个新的无凭据TLS诊断进程/至多1次TLS握手意图，目标严格 `www.usense.com:443`，SNI与verify_hostname均同名。不发送目标HTTP请求、不附加Cookie/Authorization，不使用任何账号/profile/登录配置。
- 使用已有 `C:/Program Files/Git/mingw64/bin/openssl.exe`（已只读查询3.5.5）及既有 `C:/Program Files/Git/mingw64/etc/ssl/certs/ca-bundle.crt`，先固定两者size/SHA256。OpenSSL信任库与Windows/Edge不同必须注明，不能把它的链错误直接认作Edge根因。
- 只读HKCU Internet Settings的ProxyEnable/ProxyServer/AutoConfigURL元数据；只接受已启用且无PAC、无认证的固定loopback HTTP代理（127.0.0.1、localhost或[::1]及有效port）。若分协议，只取明确https项；单一host:port按Windows固定代理语义使用。不得输出原ProxyServer串；记录脱敏类别、host/port与路径摘要即可。遇PAC、非loopback、认证、歧义或关闭则BLOCKED，0握手，不猜代理、直连或换候选。
- 代理仅允许为这一次公开TLS建立必要CONNECT隧道；这是HTTP代理握手，不是向平台发送HTTP请求。无proxy_user/proxy_pass。不复跑原A10公开GET/代理driver。

## 固定命令与一次性记录

执行者准备最小wrapper并冻结raw摘要，在exclusive `launch-intent.json`中固定目标、代理元数据、二进制/CA摘要、命令、执行ID、UTC/本地时间和一次额度后，只调用一次：

```text
openssl.exe s_client -connect www.usense.com:443 -servername www.usense.com -verify_hostname www.usense.com -verify_return_error -showcerts -prexit -CAfile <固定既有CA> -proxy <核实的loopback host:port> -no_ign_eof
```

禁用 `-reconnect`、任何回退/第二候选、弱化校验、忽略验证错误或另发浏览器请求。stdin仅保持一个不写任何字节的PIPE，收到明确验证失败/握手结果或进程退出后关闭为EOF，不能发送Q、GET或任何应用数据；避免从启动即EOF导致TLS1.3过早关闭。stdout/stderr持续排空到私有文件，不打印全文。验证失败可自然退出；无明确信号到20秒按确切句柄停止。若该工具/代理/链验证失败或无证书输出，保留该失败，不改参数补跑。版本/help/本地PEM解析属于离线读取，不算握手，也不得借此增加网络测试。

命令行为依据已读取的 [OpenSSL 3.5 s_client官方说明](https://docs.openssl.org/3.5/man1/openssl-s_client/)：`verify_return_error`遇验证错误中止；`showcerts`只是服务端发送证书列表，不是已验证链；非交互初始EOF可能提前关连接。`prexit`只增加退出信息，不改变验证策略。所有新增wrapper行为冻结前静态核对，不预跑网络。

采用Popen参数数组、shell=False；代理端口必须为1–65535，不能将代理字段拼接到shell。本轮总22秒包含进程启动、最多20秒等待、结果信号后EOF退出、管道排空与最多2秒精确保留Popen句柄清理；收到结果不能重新开始等待时限。创建与退出身份/退出码、timeout和管道/句柄关闭需保留；不扫描或结束其他进程。冻结后wrapper只启动一次，首异常停，后继NOT_RUN。无预跑握手。

## 证据与结论

原始s_client stdout/stderr可能含TLS session细节，先保留在 `.local` 私有目录（任务固定 `D:/1800/.local/stages/a14-tls-diagnostic`），0外发，不直接输出全文或入库。可入报告的仅公开服务端PEM证书、公开subject/issuer/SAN/有效期/证书指纹、校验返回类别/错误码、进程与时间元数据及原stdout/stderr长度摘要。不要导出Session-ID、Master-Key、票据、keylog、密钥或系统/用户配置内容；不启用任何-keylogfile/-sess_out/-trace/-msg。

允许对取得的证书运行本地无网络openssl x509文本/摘要解析；不得再建连接补完整链。核SAN是否覆盖www.usense.com、链/有效期及验证结果，区分HOSTNAME_MISMATCH、CHAIN/TRUST_ERROR、TRANSPORT_ERROR、NO_CERTIFICATE_EVIDENCE和UNKNOWN。只有观察到的证书字段能支持相应判断；不能凭错误名推断代理劫持或网站故障，也不能把OpenSSL成功等同Edge/认证/书籍可用。

交付 `execution-output/report.json`、`report.md`、公开证书与脱敏结果、wrapper/冻结intent、精确释放及raw清单。作者仅REVIEW/BLOCKED，释放后停止。新诊断1次耗尽后不自动追加；原A13与其他旧额度保持。独立验收只核固定raw、命令边界、一次握手及具体结论/释放，无新TLS/HTTP/浏览器。后续若需修复配置或临时证书例外，另依据证据和用户明确约束决定，不能借本任务修改。

项目仍按2026-10-22日晚、书46007447、限定普通单选首题保存与内容/框刷新重开读回→总量最多5题→独立交接。当前0真实业务写入；其他三例HOLD、Q22不重放、0B及外部联系人消息、无书级送审送交。
