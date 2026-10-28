# A25 传输修订冻结包

产品 `afc9d761294203e7cfb8086a82f1a7fdd8724372`，前件 `b74e9865d0e77bab304f0e91fb0c5e839ae56079`。这是同一 A25 的离线修订，待同一独立对话作增量验收；没有新 live、browser 或平台写入。原轮 1/0 不变。

[修订报告](../../a25-transport-revision-20261023.md)、[机器摘要](../../../evaluation/a25-transport-revision-20261023.json)、[原字节清单](raw-manifest.json)及其 `raw-manifest.sha256` 共同交付。清单绑定 30 个源码/检查/文档成员（逐字节等于产品 Git blob）和 23 个私有输入/证据成员；每个成员均有私有冻结 raw_path、长度及 SHA256。

关键增量是精确证书探测与所有浏览器调用共享显式代理/直连配置，五题 writer/reader 的 configure 透传且与当前 capture transport 一致。错误 traceback、阶段、原 CONNECT 头和 pre-context release 进入新证据；原 EOF 原因仍 UNKNOWN，旧 release:null 不改。

新 transport 11/11、受影响23/23、原始头差量2/2均通过（有重叠）。私有原件保留真实命令、原 stdout/stderr、PID/时间/exit 和 Job 释放。不得将 fake socket/浏览器检查当作代理可达、凭据或平台能力证明；无需重跑旧194或旧第一课时。

私有 `next-capture-plan.json` 的 SHA256 为 `51ed313709d56bf7064a0a65e2bd41fe138ab8d185e3b1fb852ff7d988121313`。它提出原 profile、显式 loopback HTTP proxy、原 leaf/SPKI、40 个 JSON GET、1 context/1 inert 导航/900秒；新 authority、窗口、配置和单次启动记录都必须在增量接受后由调度绑定，当前未生成/激活。

计划已准备并冻结两个历史原图及其 A05 下载命令 URL 引用，列明当前元数据/索引/几何绑定条件，不声称新图像已捕获。还列明五个当前 stable key 的 A 侧首次 ledger 初始化/前序对账依据，必须由根显式绑定；batch 继续拒绝隐式新建空账本。新源成功后直接接来源审校、具体一次保存计划及逐题新进程读回。
