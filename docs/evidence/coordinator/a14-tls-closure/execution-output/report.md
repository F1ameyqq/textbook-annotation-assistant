# A14 单次公开 TLS 诊断交付

作者状态：**REVIEW**。仅提交本次固定失败证据与精确释放，尚未独立接受。

2026-10-20 14:07:42（UTC+08）经固定 `127.0.0.1:7897` 代理向 `www.usense.com:443` 发起唯一严格 TLS 握手意图。目标、SNI、verify_hostname 同名，启用 verify_return_error；OpenSSL 退出码 **1**，首个校验错误及返回码均为 **62 / HOSTNAME_MISMATCH**。叶证书公开 SAN 仅含 `qt.lingshubao.cn`，未覆盖目标。

叶证书公开字段显示 notAfter 为 **2026-08-30 00:16:04 UTC**，早于本次观测时点。由于首个校验错误为62，不能声称后继链或有效期校验全部完成。共提取4张唯一服务端公开证书；showcerts 输出不能视为已经验证的证书链。完整公开字段与指纹见 [public-certificate-results.json](public-certificate-results.json)，证书见 certificate-01.pem 至 certificate-04.pem。

本次只证明该代理路径返回了上述证书和严格验证失败。网站、代理、DNS或其他环节的根因仍 **UNKNOWN**。Git OpenSSL 的既有 PEM CA 与 Windows/Edge 信任库不同，不能直接认定 Edge 的根因；认证、书籍访问与首题保存读回均未执行。

握手额度 **1/1已耗尽，剩余0**。目标 HTTP 请求0、stdin 应用字节0、浏览器/profile/登录/业务0、重试/回退0。存在必要的代理 CONNECT 意图，故不宣称“任何HTTP字节均为0”。原A13/A10额度不恢复，后续网络步骤 NOT_RUN。

OpenSSL PID 71152：保留的进程句柄确认创建身份一致、OS退出、退出码1、wait已触发；两路输出均EOF并排空，线程join、私有文件关闭，stdin/stdout/stderr及进程句柄关闭后均观察到 ERROR_INVALID_HANDLE。wrapper PID 59584：外层保留句柄确认相同创建身份、OS退出码0、wait已触发、句柄关闭与重定向文件关闭。见 [process-result.json](process-result.json) 和 [wrapper-os-release.json](wrapper-os-release.json)。

**计时限制 A14-TIMING-01 保留：**冻结实现将父进程的 perf_counter 值传入子进程，原记录出现启动差值 **-4.862ms**。公共跨进程时基未获证明，子进程的相对数值及22秒断言不能证明通用共享截止守卫。外层同一进程独立测得 wrapper 完整OS退出用时 **1140.204ms**，本次实际在22秒以内。该异常发现后未修改冻结wrapper、未补跑、未建立第二连接，交由独立验收判断。

原始 stdout 12575 bytes、stderr 241 bytes及wrapper空流留在私有 .local，仅交付长度和SHA256。共享目录只含公开证书、白名单字段、代码、冻结intent、进程元数据和报告；未导出Session-ID、Master-Key、票据、keylog或未脱敏原文。见 [private-raw-hash-manifest.json](private-raw-hash-manifest.json)。

冻结入口：[launch-intent.json](launch-intent.json)、[static-review.json](static-review.json)、[preflight.json](preflight.json)。原始字节清单：[raw-output-manifest.json](raw-output-manifest.json)。所有冻结代码/二进制/CA摘要复核一致。未改主线、产品、代理/信任配置或profile；其他三例HOLD、Q22不重放、0B消息、无书级提交。

本轮执行已经停止并释放。下一步仅为已登记独立对话对固定公开raw的静态核证，不能将交付理解为新握手、证书例外、配置修复或平台操作授权。
