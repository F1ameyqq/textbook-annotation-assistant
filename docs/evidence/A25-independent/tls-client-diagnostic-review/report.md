# A25 固定纯 TLS 诊断：有限独立实际结论

`ACCEPTED_FIXED_TLS_ONLY_DIAGNOSTIC_AND_OWN_RELEASE_ONLY`。仅接受本次两格TLS观测和自有释放，审查完成并释放；不是产品、浏览器、认证、来源或保存验收。

authority `9b092218-2a6a-4bf7-a1a5-5dc85e053982`；checkpoint SHA256 `add532eb7a0e386bb452fd444f5195c71857df2cec684b33a6983628cd28c537`；manifest SHA256 `c3bb08190dc000b8ba746a5aaa05860c4d083ea737bcba0d5f744ca907700810`。只从根提供的冻结目录复制并核对18成员（含checkpoint）和manifest自身，未读活跃作者输出。私有独立副本在 `D:/1800/.local/stages/a25-independent-20261023/tls-client-diagnostic-review-20261023/`。

## 实际观测

2026-10-23 **13:44:55—13:44:56（Asia/Shanghai）**，固定解释器记录为Python3.12.14 / OpenSSL3.5.8。执行argv使用指定bundled Python、`-I -B`、精确authority/script摘要，脚本记录在握手前核验解释器路径/bytes摘要、版本与启动期限。独立审查只核固定记录和脚本，没有额外读取或执行该解释器。

| 独立计划格 | 固定原件结果 |
| --- | --- |
| PY312_DIRECT_DEFAULT | 只取固定主机系统DNS返回的首个IPv4，1TCP/1TLS，TLS1.3 / TLS_AES_256_GCM_SHA384，匹配原leaf；socket及DNS线程释放 |
| PY312_CONNECT_DEFAULT | 只连127.0.0.1:7897，保留固定65-byte CONNECT请求和39-byte HTTP200响应，1TCP/1TLS，TLS1.3 / 同cipher，匹配原leaf；socket及线程状态释放 |
| PY312_CONNECT_TLS12 | `NOT_RUN / DEFAULT_EXPECTED_LEAF_OBTAINED`；没有第三格spent标记或握手证据被计为已运行 |

两格独立保存的leaf均为915 bytes，逐字节相同，SHA256 `52d8642145282846969a29b97c5c3aaae4c0203c4a6bc06906478f13445e3941`，与授权预期一致。这里验证的是精确leaf原bytes；不另宣称PKI链/主机名验证通过或独立重算SPKI。脚本在仅观察公开证书的TLS上下文使用CERT_NONE，未将该设置用于发送站点应用数据或修改产品。

除代理建立隧道所需的CONNECT控制请求外，两格TLS后的应用发送为0，站点HTTP/业务请求为0；没有浏览器、profile、凭据访问、登录或产品导入。两条路径是authority预先列明的两个独立观测，不是遇错后临时加测或自动换路。

## 固定脚本、消费和释放

脚本 SHA256 `8aa14b653a755d53ac3d1932a86345427783d452d627f4b4c0224b5faf7a845c` 与launch/实际argv一致。静态检查确认只含标准库导入，固定HOST/PORT/SNI；DIRECT仅选一个DNS地址，不轮询地址；每格一个socket.connect、一个显式do_handshake，wrap_socket关闭隐式握手，统一十秒期限；CONNECT仅固定目标、无凭据，响应头有8192上限。没有产品/HTTP客户端/Playwright或模型调用。

authority-before与authority.json相同，为不可变初始快照，仍写初始remaining3。实际消费由已绑定launch、独占`matrix-started-once.json`、两个case的独占`spent-once.json`、case/result及checkpoint共同证明；全局marker先于任何measure，每格marker先于该格网络代码。重复启动将因独占marker失败而不能重进网络。

实际已测两格，cases_spent=2；第三格NOT_RUN。checkpoint明确matrix_closed=true、additional_handshakes_authorized=0，**当前新增可用握手为0**，不能从初始authority的remaining3恢复额度，也不能把未运行第三格记成已执行。两个历史实际轮的remaining0继续保留。

matrix stdout原bytes的JSON与独立matrix-result完全相同，stderr0、进程exit0；各case独立result与matrix逐项一致，协议/leaf/计数/关闭状态相容。两个case均socket_closed=true、resolver_thread_released=true、errors=[]，每格耗时低于10秒。外层进程总耗时低于60秒，恢复前已入Windows Job，持有Python PID62472及conhost PID72948的creation FILETIME/镜像/句柄；均exit0且signaled，Job活动进程0，process/thread/Job和两个身份句柄关闭，errors=[]。仅接受这些持有身份与Job的释放。

## 因果和后续边界

本次证明指定现代客户端在这两个所测路径、这个时点取得原leaf。旧Python3.9失败发生在不同时间，本次没有同时同环境的3.9对照，不能区分运行库差异与随时间变化的网络因素，**旧失败根因仍UNKNOWN**，不能宣布运行库就是确证原因、具体缺文件已定位或整个应用已修复。

现代Python的Playwright运行路径、原profile复用、40GET和五题候选/保存/读回计划不在此固定包中，本次不提前验收或激活它们；可在同一对话收到固定计划后接续。没有重新握手或产品套件，未重开旧轮，未改根JSON/AGENTS/index、作者或原件。

`intake.py`和`verify.py`仅为独立输入拷贝/哈希及静态一致性helper，均exit0，未导入或运行被审TLS脚本。固定输入见`intake.json`、`raw-manifest.json`，机器结论见`result.json`，交付哈希见`review-files.sha256`。新产品检查/网络/模型/OCR/平台动作0，新激活0。
