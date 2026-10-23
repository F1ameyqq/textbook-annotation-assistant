# A25 传输固定增量：正式有限独立结论

代码：`ACCEPTED_OFFLINE_ONLY`。具体新取源方案：`ACCEPTED_BOUNDED_READONLY_PLAN_FOR_ROOT_BINDING`，可由根协调者按用户当前继续实测的授权绑定并接续一次新只读轮；绑定时须同时纳入本报告列明的题号更正。此次没有激活或运行新轮，没有取源/五题保存成功结论，也没有要求另开诊断阶段。

正式独立对话 `01a166e8-3f23-7192-a560-4724adca74b1`，继续同一 A25 和原标准。前件 `b74e9865d0e77bab304f0e91fb0c5e839ae56079`；本次产品 `afc9d761294203e7cfb8086a82f1a7fdd8724372`，最终 `fef3638d5793347a2b70f21108f6c03ee7856bbc`。raw 清单 SHA256 `e6459fad81e5b222fe73a74161c0fbf710162bf8a4910528d5062c62f140d752`。

## 原字节和范围

独立核对 30 份源码的 Git blob、字节数、SHA256、作者冻结原件和最终提交一致，复制 23 份冻结私有输入/证据及 2 份最终报告。隔离为 `D:/1800/.local/stages/a25-independent-20261023/transport-review-20261023/`。未读作者活动树，所有 Git 均为确切 commit，只读调用设置 `GIT_NO_LAZY_FETCH=1` 和 `-c core.longpaths=true`。

旧冻结 27 份源码及 47 份私有原件共 74 个成员仍匹配原清单；前次 review 哈希清单原成员全部不变。根另增的 `.gitattributes` 不在该旧清单内，未视作原成员变更。前次导入错误、SSLEOF、`release:null`、验收工具错误和剩余 0 均未覆盖。新 diff 无删除，变更集中于显式 transport、配置/批透传、进入 context 前的失败原件与释放记录及相应文档/检查。

## 有限检查结果

原字节隔离的执行命令为 `python -B .../transport-review/suite.py` 和 `python -B .../transport-review/controls.py`；完整 argv、cwd、时间、exit、stdout/stderr 路径和 SHA256 见 `test-commands.json`。Python 3.9，两个进程均 exit0：

| 范围 | 实际结果 | 内容 |
| --- | --- | --- |
| 新 transport 文件 + 两个新 batch transport 案例 | 13/13 PASS，1.773s | 配置无探测、DIRECT/代理、固定 CONNECT、无凭据/远端/后备字符串拒绝、407/EOF/证书/原点/SPKI 拒绝、pre-enter 原异常与释放回填、批传输错配拒绝和 configure 透传 |
| 新增独立控制 | 6/6 PASS，2.276s | 代理响应只读到头尾、不吞 TLS bytes；读头期限耗尽；8192 上限；连接 Timeout 原异常；全部 writer 共同 helper；两目标 writer 和 reader 的每次 configure 均使用同一代理 |

所有 socket/TLS/browser 均为 fake。验收 guard 阻止真实 `socket.create_connection`、外部 DNS/外部或代理 connect、子进程；仅允许 Windows asyncio 的本地控制 socket。没有访问代理 7897、平台、浏览器或原 profile，没有 OCR/模型调用。没有重跑旧 16+8、194、旧首课时或历史 A suites。本增量未发生验收 helper 失败。

作者原件的 11 项新增、23 项受影响、2 项差量输出保持；它们有重叠，不合并成 36 个独立覆盖量。本次按变化范围选择 13 项，并新增 6 个独立控制。

## 代码结论的边界

v2 配置强制 transport 字段，DIRECT/null 或单一无凭据 loopback HTTP 代理。配置缺失/模式非法/用户名密码/远端/SOCKS/PAC/路径/query/后备字符串拒绝；运行时没有自动选择 WinINET、WinHTTP、环境代理或失败后换路。

当前精确证书模式的 helper 调用一次 socket 连接；代理模式只连配置的 loopback，发一个固定 `CONNECT www.usense.com:443`，不发送认证头，要求 HTTP/1.0 或 1.1 的 200 响应。读头有 8192 字节上限，逐次按同一个十秒截止时间更新 timeout，之后以原 SNI 进行 TLS 并核原 leaf DER。独立反例证明 deadline、头过长、connect 失败均不触发第二次连接或 TLS/直连后备。这里只证明 helper 的调用和协议边界，不把模拟结果计作真实 TCP/TLS 成功。

原 origin、TARGET、leaf DER 和 SPKI 常量与前件完全相同。`core.tls_launch_arguments` 统一转到新 helper，原 writer、insertion writer、finalize writer 导入的均为同一个函数；readonly owner 也使用它。返回的 Chromium proxy/no-proxy 与 probe 的明确 transport 一致；精确证书分支仍只有原 SPKI 参数，`ignore_https_errors` 仍 false。STRICT 分支不进行证书例外 probe，也不增加忽略证书参数。

批 preflight/execute 均要求命令 transport 与当前 capture.summary.transport 相等，在任何 configure 前拒绝错配；reader 和 writer 的 configure 共享闭包参数。本次独立合成两目标成功链核到四次 configure 均携带同一代理，原一次发送/读回/UNKNOWN 逻辑未重写。

capture 在进入前先持有 owner，TLS preflight 的原错误现在以私有 traceback/摘要/阶段记录，startup-error、capture-error 和独立 release 分开保留；context_created/runtime_started 明确区分未创建和已释放。合成进入前 SSLEOF 保留完整原文本、phase=TLS_PREFLIGHT、0 业务响应及未创建资源的 release。该修订不回填前次缺失 traceback，也不改变旧 `release:null`。

未发现阻挡本次有限离线接受的代码问题。实际代理连通性、真实证书握手及五题来源仍未证明。固定本机设置显示 WinINET loopback 代理与旧 Python 直连实现不一致，只是原件中的静态事实；原 EOF 因果继续 `UNKNOWN`。

## 具体只读方案及题号更正

原始方案 SHA256 `51ed313709d56bf7064a0a65e2bd41fe138ab8d185e3b1fb852ff7d988121313` 保持不变，包实现独立重算为 `5ddfe19c4cb0f2b98555c927a1d205f1165ab23ecac981896627445e29f3c2c8`，与该方案一致。

审查期间收到根的当前题号更正 `D:/1800/docs/tasks/A25-printed-number-correction-20261023.md`，已复制并登记 SHA256 `2e71e07509ef22ab46d1e23f1f358fd5d6b337b0f56a0b1ae59fb07eadfa1fc9`。当前解释必须为：

| 字段 | 范围 |
| --- | --- |
| 第 2 课时课内印刷题号 | 1—5 |
| Q7 拆分前历史全局序号 | 17—21 |
| 拟读取、仍待当前稳定身份核实的原生题序 | 18—22 |
| 当前服务器实际父目录 | 新 capture 决定，原归属保留，不迁移 |

原方案中的 `printed_questions=17—21` 是保留的历史标签错误，不能复制到新 authority 或真实批清单的 printed 字段。GET 集合、五题集合、产品均不因此变化，无需重跑测试。根激活时应将原方案 hash 与更正 hash 同时绑定；新 authority 写印刷 1—5，并单列历史全局序号。不得改写原冻结计划来隐去错误。

接受的有限范围为原专用 profile、显式 `http://127.0.0.1:7897`、1 context、1 inert 同源导航、900 秒、40 个逻辑业务 JSON GET：目录/全框/source，原生 18—22 各 7 项，viewer12/173 各 1 page JSON；加 inert document 规则共 41 条。该轮写入/登录/新 origin/图像下载均为 0。原 TLS leaf/SPKI/origin 不变。原轮 spent1/remaining0、config/claim/output 不重开。

这两张历史 JPEG 原件的 SHA256、大小、JPEG 格式和几何已独立复核，原下载命令的 URL bytes hash 与方案一致：viewer12 为 1220×1692，viewer173 为 1148×1621。它们仍是历史图像，尚未绑定当前题身份。只有新 JSON 返回后，精确 URL 摘要、viewer/原生页索引、几何及 frame 对应关系全部核对；元数据若给出内容摘要还须相符，才能标记 `HISTORICAL_BYTES_BOUND_TO_CURRENT_METADATA`。不能称当前远端 image bytes 已重新取得或保持不变。任一关系不符停止为 SOURCE_BINDING_BLOCKED，不另抓图/扩 origin/重复 OCR。

该只读轮不创建 ledger。A 侧账本首次初始化仍由根在取得五个 fresh stable key 后，绑定 A 既往 post0、B 已停止/已保存17题的稳定身份范围、目标不重叠与没有已知 UNKNOWN/前序 intent 的对账及初始化决定；不能仅凭题序不同创建空账本来绕过记录。当前 reviewer 未检查/创建原账本目录。

## 根可立即接续的边界

根按现有用户授权绑定本产品/包摘要、原方案 hash、题号更正 hash，生成唯一全新 authority/config/window/output/launch 记录，启动前复核原 profile 当前独占，便可派原执行者进行该一次新只读轮。无须增设辅助阶段，也无须重复已通过检查；本报告本身没有执行这些激活动作。

首错保留原 bytes、阶段/traceback 和 standalone release/外层 Job 原件，停止链并记后继 NOT_RUN，不延长旧窗口、不恢复旧预算、不自动重试。源成功后直接形成五题当前 node/info/真实父目录、完整基线、来源审校候选及具体保存计划，交同一独立对话接续。真实五题保存、新进程读回、原17题内容保全及导出继续 `NOT_RUN`，此次只读接受不提前放行保存或送审。

公开固定交付见 `result.json`、`plan-review.json`、`supplement-input.json`、`intake.json`、`test-commands.json`、`transport-review-files.sha256`；私有原件及运行输出索引见 `transport-review-raw-manifest.json`。未改作者、根 JSON/AGENTS、原 profile、旧原件或共享 index，未发送其他聊天/B 消息、未创建子智能体/聊天。由根选择收录固定报告。
