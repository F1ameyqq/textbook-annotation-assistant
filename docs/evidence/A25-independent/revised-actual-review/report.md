# A25 修订取源轮：固定实际独立结论

`ACCEPTED_FIXED_FAILURE_AND_OWN_RELEASE_ONLY`。本结论仅接受固定失败及自有资源收口；没有取源、TLS 成功、真实身份、保存或根因结论。当前轮 spent **1**、remaining **0**，不重开或重试。

固定 checkpoint SHA256 `1b1a98a1a4ac1fa90e74d9dc79aec521531cda461106affe7424d8340e4ab22b`；authority `9a6bed2d-3025-4dec-b719-6c7762476134`。产品保持已验 `afc9d761294203e7cfb8086a82f1a7fdd8724372` / final `fef3638d5793347a2b70f21108f6c03ee7856bbc`。独立复制并逐项核对 checkpoint 的 21 份 raw 成员；前次隔离的 30 份源码和前次报告清单成员也仍匹配。本次没有产品变更审查或产品检查重跑。

2026-10-23 **13:12:13—13:12:14（Asia/Shanghai）**：原 CONNECT 请求为固定 `www.usense.com:443`，代理原始响应为 `HTTP/1.1 200 Connection established`，39 bytes，SHA256 `f55260227c507b4e203ec14ceb78ce8e64d11734111bed9bd18936a3bd4d48f3`。它只证明收到该代理响应。随后 TLS 探测原 traceback 到达 `ssl.do_handshake()` / `_sslobj.do_handshake()`，抛 `FileNotFoundError: [Errno 2] No such file or directory`，未取得 leaf。细阶段为 **TLS_HANDSHAKE**，startup/capture 外层阶段为 **TLS_PREFLIGHT**，两层记录一致，没有将外层标签误作精确子步骤。

三份 traceback 均有完整原件且与各自 metadata 的大小/哈希吻合：probe 704 bytes、startup 1411 bytes、capture 1563 bytes。probe traceback SHA256 `d84721f78bda03fac710451d69f0319ddb3ddf24298c91785cee155b7e3f8dbc`。其中没有给出具体缺失文件名；**缺失文件路径和实际根因均为 UNKNOWN**。异常类名不证明实际缺文件、本地代码缺陷、代理原因、服务端原因或证书原因。

配置 SHA256 `e7db1b2469bc9fbb843f5e9b255f2282dc05f934853ce17d1646a361b05bf5d5`，包摘要 `5ddfe19c4cb0f2b98555c927a1d205f1165ab23ecac981896627445e29f3c2c8` 与已验代码、authority、launch、claim、summary、release 一致。authority 保留启动前 0/1 原 bytes；单次 launch 先于进程启动，当前记录为 1/0、retry=false、save 授权0，执行在新配置 900 秒窗口内。原计划及印刷题号更正 hash 均已绑定；旧轮没有恢复。

实际 exit2、`CAPTURE_FAILED_NO_RETRY`、`captures={}`、业务响应0、save_attempts=0、浏览器网络审计 `[]`。进程 stdout 原 bytes 的 JSON 与 capture summary 相同，stderr 原 bytes 为0；完整错误保存在上述独立 traceback 中。CONNECT/TLS 流量不能被网络审计 `[]` 改写为实际网络操作0。

summary.release 与独立 release.json 完全一致：context_created=false、runtime_started=false、context_closed/runtime_stopped=true、pending0、errors=[]、release_confirmed=true；这是未创建浏览器/runtime 的收口，不能称关闭过已创建浏览器。外层 Windows Job 在恢复执行前已接管进程，持有 Python PID **52748**、conhost PID **20684** 的 creation FILETIME/镜像/句柄；二者已 signaled，Job 活动进程0，进程/线程/Job 句柄关闭、errors=[]。只接受这两个持有身份和 Job 的释放。固定 postrelease 观察的匹配 profile 进程和锁名为空；本验收未查询当前系统或触碰 profile。

五目标标签正确区分：课内印刷1—5、历史全局17—21、待当前身份核实的原生18—22；node/info/ledger key/实际父目录均未取得。来源绑定、候选、计划、保存、独立读回、导出逐项 `NOT_RUN`，ledger 初始化 `NOT_RUN_NO_CURRENT_ID`。

协调者另报两个预建目录的 mkdir 准备错误；它们不在此21份固定 raw 内，本报告只登记该限制，等待作者另行归档，不替换本次首次 TLS 错误，也不调整本轮1/0。没有扩大诊断、重测、平台动作或新轮激活。

`intake.json` 与 `raw-manifest.json` 给出固定原件清单；`result.json` 为机器结论，`review-files.sha256` 为本交付哈希。独立私有隔离在 `D:/1800/.local/stages/a25-independent-20261023/revised-actual-review-20261023/`。只执行输入拷贝/哈希和静态一致性 helper，均 exit0；未导入/运行产品，未改作者、根 JSON/AGENTS/index 或原证据，未联系其他聊天/B。
