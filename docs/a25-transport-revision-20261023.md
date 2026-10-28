# A25 同阶段显式传输修订交付

执行/验收沿用原 A25 对话和 B 基线；原产品 b551dcea、固定交付 b74e9865 已获有限独立/根接受（离线代码、原失败及自有释放各自限定），见根 `docs/evidence/coordinator/a25-independent-closure/receipt.json`。原 SSLEOFError 轮 spent 1/remaining 0、config/authority/claim/output、旧 first-lesson 成功和 OCR 均保持。本页是新修订作者交付，尚未获得本次增量独立接受或新 live 激活。

## 已观察与推断

本机非敏感设置记录：WinINET ProxyEnable=1，单一无凭据 HTTP proxy `127.0.0.1:7897`，无 PAC；没有 HTTP_PROXY/HTTPS_PROXY/ALL_PROXY 环境值，WinHTTP 报告直连。旧 Python `socket.create_connection((www.usense.com,443))` 不查询这些系统代理设置，而旧 Edge 启动没有显式 transport。

这是静态路径不一致的依据。旧失败实际未进入浏览器，没有网络包、完整原异常文本或成功代理连接证据；不能证明 EOF 是代理、服务器或证书造成。旧根因仍 UNKNOWN。本轮实际网络、浏览器、凭据配置/profile 内容读取和平台操作均为 0。

## 最小修订

- 新 readonly 配置为 `UsenseLiveReadConfig/v2`，必须明确 `transport`：DIRECT/null，或 HTTP_CONNECT_PROXY/无凭据的 `http://127.0.0.1:port`。运行时不读取/选择系统代理、PAC、环境变量或其他端点。配置、实现及原 profile 身份仍哈希绑定。
- 证书探测对单一 loopback 代理发一个固定 `CONNECT www.usense.com:443`，要求 HTTP 200；之后以原 SNI 握手，核原精确 leaf DER。代理失败、407、EOF、超时、证书改变均停止，没有直连后备或第二代理。整个探测使用一个十秒期限。原 origin、leaf 和 SPKI 常量均未改。
- 所有现有调用者共享 `tls_launch_arguments`，其返回值同时包含明确的 Chromium proxy（或 no-proxy）参数和原 SPKI 参数。普通 writer、insertion/finalize writer 及 readonly owner 都消费同一个 helper；没有只修改 capture 的连接方式。`ignore_https_errors` 仍 false。
- 批入口要求 `--proxy-server` 与当前 capture.summary.transport 严格一致；每个 writer/reader 的 configure 都透传这个参数。省略参数意为明确 DIRECT，不能默默继承 WinINET。缺失或变化在首个 configure 前拒绝，不隐式创建账本。
- 新私有证据记录 CONNECT 请求/响应头原 bytes、探测阶段、错误原 traceback、leaf 摘要和无后备策略。owner 在进入 context 前即持有；TLS 前置异常现在同时出现在 capture 摘要、独立 startup-error、release.json 和原 traceback 中，分别记录 context_created/runtime_started。旧 release:null 摘要不改写。

## 有限检查

新增 transport 检查 11/11：本机配置无网络生成；精确 CONNECT 与浏览器参数一致；严格 TLS 不附证书例外；远端/凭据/SOCKS/PAC/后备字符串拒绝；407/EOF/leaf/SPKI/origin 错配无后备；pre-enter SSLEOF 原异常与释放进入摘要。正向 pin 分支仅在合成测试注入合成 DER 摘要，生产常量保持。

受影响检查 23/23：2 个新批传输透传/拒绝案例、3 个涉及新 summary 字段的现有批编排边界、13 个配置/owner 边界、5 个配置/原字节采集边界。随后只跑 CONNECT 原始头新增落盘断言的 2 项差量，2/2；与前述有重叠，不累加为不同覆盖量。所有 socket/browser 均为 fake；没有重跑旧194或第一课时真实流程。原检查输出、argv、PID、exit 和 Job 释放保存在新的 transport-revision/evidence。

## 下一次具体取源与保存依赖

私有 `transport-revision/next-capture-plan.json` 是未激活计划。待本修订同一独立增量接受及根绑定新 authority 后，才生成全新 v2 配置/900秒窗口/输出和单次启动记录，使用原 profile 与明确 `http://127.0.0.1:7897`。1 context、1 inert 同源导航，40 个既有逻辑 JSON GET：目录、全框、source，原生 18—22 各7项，以及 viewer12/173 两个 page JSON。仅原 www.usense.com 精确业务路径；CONNECT 是证书前置探测，不能据此授予业务写入。新轮额度未激活，原轮不重开。

来源图无需先做重复 OCR：已核历史 viewer12 JPEG 为 467691 bytes/1220×1692/SHA256 `774c8a29bbdcaa35fcb88479129d2b523ec077edfa4e0ac3db6f11e9bcae9b87`，viewer173 为 428192 bytes/1148×1621/`a231f0247cd0444cc34ed699c4cca99245d2ac6cfda5ef10a38ca3f8164510be`。两份 bytes 已在本次私有输入冻结；173 与旧 A24 对应原件相同。A05 原下载命令也已冻结，包含两个既有资源 URL 的原字节摘要。它们是历史来源，不能先充作当前题身份或新图像捕获。

新 page/source JSON 返回后立即比对历史命令中的精确 URL 摘要、viewer/服务器索引映射、来源图几何及当前 frame 对应关系。只有关系一致才复用已冻结图像做五题审校，标记 HISTORICAL_BYTES_BOUND_TO_CURRENT_METADATA，不声称重新获取图像或其远端 bytes 当前未变。如果当前元数据给出内容摘要还须核图像 bytes。当前 URL/几何/页索引不一致时明确 SOURCE_BINDING_BLOCKED，不猜源、不扩外部 origin 或重复 OCR；这个剩余关系已在启动前列明，两个图像文件本身均已准备。

取源成功后直接形成五个当前 stable node/info/原生序号/实际父目录、完整原生基线、来源及内容审校文件和一次保存计划；不会迁移目录、插入/删除帧或回放已成功第一课时。

另一个已知写入输入是原 profile 父目录的 `usense-existing-ledger` 不存在。程序保持拒绝自动创建。具体计划须由根绑定五个当前稳定 ledger key，结合 A 从未业务保存、B 明确停止及 B 已完成原生1—17范围，核它们与第一课时身份无重叠、没有已知 UNKNOWN/前序 intent；再由根明确允许首次 A 侧账本目录/初始化记录。若稳定身份落入已保存或未解决分支，先对账，不以空账本绕过。初始化尚未执行，也不把它另立为诊断阶段。

五题保存及各自新进程读回仍须来源候选和具体一次保存计划的独立/根接续。下一步同一 batch 的每个 writer/reader 使用同一明确 transport，新 config/run；UNKNOWN 首错后其余 NOT_RUN。sole1800-a 保持 PAUSED，本修订未推送、未联系 B 或其他对话、未自验收。
