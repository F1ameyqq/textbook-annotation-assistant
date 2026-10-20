# A14 独立静态核证

结论：`ACCEPTED_FAILURE_ARCHIVE_PUBLIC_CERTIFICATE_AND_EXACT_OWNED_RELEASE_ONLY`。仅接受固定公开失败归档、公开证书字段与两项自有进程的精确释放。通用截止守卫仍为 `NOT_ACCEPTED_A14_TIMING_01`，不释放平台或业务后继。

独立对话 `01a157e7-1425-7f53-8e84-1382566ffce6`；执行对话 `01a157e6-628a-75d2-b685-6cb98e5fb0af`；工作流 `cae8275555a7a77b303dae50fe9d8d3a3b4ce2c9`。作者清单 SHA256 `aaf8a90ed9b82d707d6f736deb1f6ba9c409ab582c8dc2bf89cdac58d07bba8d`。

隔离输入23项、101468 bytes：19执行输出、2标准、2历史A13报告，size/SHA256全匹配，无缺失、额外或reparse/symlink；作者18项非自身清单和清单自身匹配。[前检](input-precheck.json)、[后检](input-postcheck.json)保留全部23项摘要；[独立计算](independent-checks.json)包含AST、PEM字段、时序和释放核对。

固定argv采用严格目标 `www.usense.com:443`，SNI/verify_hostname同名、verify_return_error、固定CA、shell=False；无reconnect、弱化验证、凭据或回退。冻结代理 `127.0.0.1:7897`；源码拒绝禁用/PAC/非loopback/认证语法/歧义或端口异常，单一固定代理与明确https项区分。未重查registry；二进制/CA摘要仅核包内intent/preflight/audit一致及执行前摘要守卫，未重读本机安装文件。

单次声明由一个OpenSSL和一个TLS wrapper保留句柄生命周期支持，独占x-mode claims在源码中固定；私有claim内容未读，不作全系统启动/连接计数证明。TLS stdin无write调用，本次明确验证失败后EOF；目标HTTP0、应用字节0，另记必要代理CONNECT意图1，不称所有HTTP字节0。1/1额度耗尽、剩余0，A13/A10额度不恢复。

4张公开PEM独立解码，subject/issuer/SAN/日期和DER/PEM指纹一致。叶证书唯一DNS SAN为 `qt.lingshubao.cn`，不覆盖目标。公开notAfter `2026-08-30 00:16:04 UTC`早于观测 `2026-10-20 06:07:42.316294 UTC`。固定脱敏提取记录错误/返回码62、进程exit1；验收未重读私有错误原文。issuer/subject名称相接不等于签名/信任通过；showcerts的8次PEM出现对应4张唯一证书，不由此推断额外握手或完整已验证链。后继有效期/链校验阶段未证明完成。根因UNKNOWN，不归因网站、代理、DNS；Git OpenSSL的PEM CA不等同Windows/Edge信任。

OpenSSL PID71152同一保留句柄创建FILETIME匹配退出记录，exit1、wait触发；两流EOF/排空、文件关闭、线程join，stdin/stdout/stderr及进程句柄关闭后记录invalid handle。TLS wrapper PID59584同一创建身份exit0、wait触发，句柄和重定向文件关闭。仅接受这两项已观察生命周期及其资源，不扩称最外层launcher/工具壳或整个会话所有进程均有OS退出证明。验收未作实时进程扫描。

`A14-TIMING-01`保持开放。父进程同一时基1140.204ms；OS FILETIME独立重算wrapper1136.5958ms、TLS974.7273ms且后者寿命包含于前者。本次已有限退出且低于22秒。子进程以父perf_counter数值相减却得到启动-4.862ms，共享时基未证明，子进程within22断言不能证明通用守卫。另核[外层源码](../execution-output/launch_once.py)29–38行：超时只记UNKNOWN并关闭wrapper句柄；[子层源码](../execution-output/tls_wrapper.py)219–224行：最终kill/wait以尚未超过继承deadline为条件。父层wait不能单独证明超时清理。该分支未执行或补测，冻结码未改，未补握手。

脱敏代码只导出公开PEM/字段、数值错误、长度和摘要；23项输入无实际私钥、Session-ID/Master-Key/keylog/票据值模式。私有原文未读、提取未重放，原流摘要仅核包内跨记录一致。`first_failure=null`/REVIEW只表示监督器取得结果，不表示TLS成功。

A13历史wrapper PID31208的OS退出身份仍UNKNOWN，A14不覆盖。认证、书籍、首题保存及内容/题框刷新重开读回均NOT_RUN；其他三例HOLD、Q22不重放、0B消息、无书级提交。

验收只做本地文件/JSON/AST/hash及4张公开PEM解码：0作者代码导入/运行、0TLS/HTTP/浏览器/profile/凭据/进程扫描、0私有原文、0主线写入。报告生成曾因PowerShell管道编码在Python解析阶段exit1，未写任何报告或执行Python语句；仅改用UTF-8报告生成文件，失败记录保留在JSON。静态检查器exit0，无子进程或后台线程、自有平台资源0；输出文件使用关闭上下文，完成后停止。全部23项输入前后原bytes保全。完整限制见[报告](report.json)，固定输出见[清单](raw-output-manifest.json)。不授权修复、重跑、证书例外或后续连接。
