# A25 现代 runtime 首次目录 HTTP401：有限独立实际结论

`ACCEPTED_FIXED_FAILURE_AND_OWN_RELEASE_ONLY`，失败子类为首个目录 GET 的 HTTP401/空正文。runtime 准备记录有限接受为 `ACCEPTED_FIXED_RUNTIME_PREPARATION_EVIDENCE_ONLY`。本轮已跨过TLS并创建浏览器，但当前来源、稳定身份及保存均未取得；精确token/session原因仍为UNKNOWN。审查完成并释放。

authority `60d7e214-9db5-49e5-bd48-fd1747754750`，产品保持已验 `afc9d761294203e7cfb8086a82f1a7fdd8724372` / 实现 `5ddfe19c4cb0f2b98555c927a1d205f1165ab23ecac981896627445e29f3c2c8`。

## 固定输入和 runtime

| 冻结包 | checkpoint SHA256 | manifest SHA256 | 核对数量 |
| --- | --- | --- | --- |
| modern-source-http401 | `0cc09b14db9f7cdd03e141e7b619a4dfc69c71615ff8cbce1610125fc6a20a22` | `8c6ee5e6de171ab537071c55406014667ac4e8f5c189176e51e7bd9644d319de` | 26成员+self |
| runtime-py312 | `bf68beff4671bed8890981829ced17a47769cd2ce049214fd8636b8752bef358` | `0041f98318fad2200f4eb6cd817bd14621bd420e7d4ea87c033d4ef83a70ec2e` | 18成员+self |

两包均只读根提供的冻结副本并独立复制、逐项核大小/SHA256。未读作者活动树、venv现状、profile内容或认证准备目录。隔离在 `D:/1800/.local/stages/a25-independent-20261023/modern-source-http401-review-20261023/`；输入清单见 `intake.json`。

runtime原件记录任务专用venv为Python3.12.14/OpenSSL3.5.8，Playwright1.58.0、Pillow11.3.0、greenlet3.5.6、pyee13.0.1、typing_extensions4.16.0；`route_web_socket`、当前read/writer imports及实现摘要检查成功，准备阶段未启动浏览器。venv-create、修正后install、readiness进程均exit0，原过程stdout/stderr及自有Job释放记录吻合。实际启动前的runtime-binding重新记录了相同版本、可执行摘要及包实现，与authority/launch一致。

首次pip使用历史精确greenlet3.2.5 pin，exit1及原stderr `No matching distribution found` 保留。第二次使用保持Playwright/Pillow顶层版本的requirements-top-level，传递依赖按声明范围解析，exit0；最终实际版本由readiness原件冻结。`requirements-pinned.txt`仍是首次失败输入，不能作为最终安装环境的lockfile。这里只接受固定准备/导入与实际绑定证据，不宣称完整wheel环境可重建，也没有重跑安装或导入。

固定计划SHA256 `a22034a5b1654738c8940d7c48bee2496fbe17aa48bdb5f13f5656379608b23e` 与runtime checkpoint和新authority相符。计划维持原profile、DIRECT、1context/1inert导航/900秒/40JSON，课内印刷1—5、历史全局17—21、拟native18—22，viewer12/173。冻结启动前检查记录显示执行Python成员与已验实现一致，只有非运行文档docs/status/a.md状态更新；验收者未读取活动树或另建离线检查阶段。

## 实际链路

2026-10-23 **14:04:23—14:04:27（Asia/Shanghai）**，指定venv以`-I -B`执行已验入口，exit2。配置SHA256 `0ce39a4342f7ead089caefd2e235ce4c26ce86e72df58b03a39edc73054f8abf` 与config-binding、launch、claim、summary/release相符。source计划/运行环境/配置摘要均在启动前绑定，authority原件0/1保留，launch先于进程启动，原子消费后本轮1/0；执行在配置900秒窗口内。两个旧实际轮和已关闭TLS矩阵仍remaining0。

| 层 | 原件事实和有限解释 |
| --- | --- |
| TLS | DIRECT探测attempts1，status=EXACT_LEAF_CONFIRMED，leaf摘要匹配`52d8642145282846969a29b97c5c3aaae4c0203c4a6bc06906478f13445e3941`，无CONNECT/后备。本轮包只保留leaf摘要，没有另存本轮DER或TLS协议版本；不把历史诊断DER/协议当本轮新bytes/版本。原leaf/SPKI配置未改变。 |
| inert document | 目标文档由本地fulfill响应，viewer_rendered=false；仅为采集器同源执行上下文，不证明平台页面渲染或认证通过。 |
| 第一个业务GET | 书46007447的directory GET收到HTTP401；directory.json原件确为0 bytes，SHA256为空bytes摘要。业务JSON未取得，成功业务响应0，保留响应1。 |
| guard | 原审计3事件：native文档1；directory在native/context各1，均GET、allowed=true、redirected=false。两个guard是同一业务GET的两层记录，不是两次目录请求。cap.request_counts与事件一致。 |
| 首错与停止 | 完整455-byte traceback、metadata和summary吻合：BindingError/CAPTURE_HTTP_FAILURE，phase=GET_directory；在HTTP状态检查处停止。其余39业务GET未运行，未自动登录/重试/写入。 |

HTTP401仅支持“本次目录请求未被接受”的结论，不能确定token过期、session失效、账号权限或其他具体原因。包内未导出token/凭据值，本验收没有查询它们。

## 自有释放和后继

summary.release与独立release.json完全一致：context_created/runtime_started=true，context_closed/runtime_stopped=true，pending_callbacks=0、errors=[]、context_runtime_release_confirmed=true；没有自动登录，save0。进程stdout的JSON与summary相同，stderr原件0 bytes。

外层Job在恢复执行前已接管。实际capture持有12个不同身份：任务venv Python launcher、base Python、conhost、Playwright node及8个Edge进程；均有creation FILETIME/镜像/句柄，已signaled、句柄关闭，Job活动进程0，process/thread/Job句柄关闭、errors=[]。Python launcher/base退出码2对应固定失败，其余持有身份退出码记录保留。只接受这12个持有身份和Job的释放，不扩大为未观察进程的全局结论。固定前后profile观察均无匹配进程或锁名，验收者未查询当前系统。

本轮spent1/remaining0、retry=false、save0、login0；余39GET及五题来源绑定、候选、保存计划、保存、新进程读回、导出逐项NOT_RUN，node/info/实际父目录未取得，ledger初始化NOT_RUN。课内印刷1—5与拟native18—22仍分开，未用历史图像补造当前身份。

原profile一次官方登录/用户手动登录的具体方案不在本包内，本报告没有授权新登录、凭据配置读取或重新取源；未读取作者活跃认证准备。所有旧失败和预算保持，不新增实际激活。

## 固定交付

`intake.py`、`verify.py`只执行独立拷贝/哈希和静态一致性核对，均exit0；没有产品测试、TLS握手、平台/网络/模型/OCR操作。未修改作者、根JSON/AGENTS/index或原件，未发送其他聊天/B消息。

机器结论为`result.json`，两个冻结包的输入与副本索引为`intake.json`、`raw-manifest.json`，公开交付哈希为`review-files.sha256`。runtime准备checkpoint中的“尚未激活”是原冻结时点记录；本次新authority的实际消费结果由本轮launch/summary/checkpoint决定，不改写旧准备原件。
