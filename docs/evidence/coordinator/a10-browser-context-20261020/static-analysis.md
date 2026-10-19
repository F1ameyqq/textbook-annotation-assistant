# A10 浏览器上下文差异：一次只读静态分析

日期：2026-10-20。状态：STATIC_ANALYSIS_COMPLETE / RELEASED。本报告不是新网络观察的启动信号。

## 结论

存在一个具体、可区分的传输配置差异：冻结公开探针没有显式 `proxy`；绑定的 Playwright 1.58 APIRequestContext 不读取 Windows Internet Settings，而是使用自己的 Node DNS/TLS 连接路径。冻结原浏览器会话的导航被 `route.fetch` 接管；该方法同样委托 APIRequestContext，并不通过 Edge 自身的导航网络栈完成这次请求。原会话基线也没有显式 `proxy`。

主调度本轮报告的当前元数据为：Windows 用户系统代理启用、仅 loopback 端口 7897、无 userinfo、无 PAC；列出的代理/TLS环境变量不存在。用户报告普通浏览器可以正常打开 Usense。两项新信息与上述源码差异共同支持优先观察“给独立 APIRequestContext 显式配置当前本机代理后是否能取得 HTTP 状态”。它们尚未证明旧失败由代理造成，也没有证明普通浏览器本次实际用了该代理。

旧两次失败仍分别为 `TRANSPORT` 与 `GET / Error / UNKNOWN`。归档未保留原异常，不能从现有静态资料复原具体 DNS、TCP、TLS 或响应体故障。没有证据支持把平台判定为不可用、把凭据判定为失效，或放宽 TLS 校验。

## 范围、读取方式与计数

- 已读工作区 `AGENTS.md` 与 `docs/tasks/A10-browser-context-diagnosis-2026-10-20.md`。新上下文和配置元数据来自主调度消息；本子 agent 没有读取注册表、环境值或元数据文件。
- Git 读取仅使用本地固定提交 `fc81de1bf8e3ee10e4d9f9da1aa99f34afbe5f23` 与 `7dbe786da0d6ff86eef8ca9c05bccdc2d5583204` 的树/原始 blob。从第一条 Git 调用设置 `GIT_NO_LAZY_FETCH=1`，每条使用 `git -c core.longpaths=true`。`cat-file blob` 由 Python 以 bytes 捕获、散列，展示时才解码；未 checkout、fetch、修改 Git 配置或写索引。
- 只读必要已安装依赖源码，没有导入/启动 Playwright、Node 或旧诊断代码。AST 只用于定位公开函数签名，未执行任何旧测试或业务代码。Python/Git/搜索工具进程均已正常退出。
- 本次新增网络调用 0、浏览器启动 0、profile/凭据读取 0、OS 进程扫描 0、旧诊断/测试重跑 0、业务操作 0。没有修改产品、主调度 JSON、系统设置、旧证据或旧次数。
- 唯一新增输出为本报告。历史 memory 快速检索没有提供本轮 A10 原因证据，未用于结论。

## 确定事实与源码依据

### 1. 公开 GET 实参兼容，重定向 0 不是已发现的故障

`fc81de1b:docs/evidence/A10/public-transport/probe.py:69-78` 创建独立 request context，参数为 `ignore_https_errors=False, timeout=30000`；唯一 GET 为固定公开路径 `/qieti/annotateUnified`，带 `timeout=30000, ignore_https_errors=False, max_redirects=0, max_retries=0, fail_on_status_code=False`，无显式 proxy、credentials 或 storage_state。

本机 `_generated.py` 的 `APIRequest.new_context`（18982-19079）及 `APIRequestContext.get`（18467-18560）均支持这些参数；`_impl/_fetch.py:66-99, 335-361, 410-430` 将它们转换为服务端字段，并允许 redirect/retry 为 0。这四个关键已绑定源码文件的当前 raw SHA256 均与旧 `input-bindings.json` 一致：`_generated.py`、`_fetch.py`、`_transport.py`、`fetch.js`。没有 Python 关键字不兼容的静态证据；旧结果也是 `Error`，而不是白名单中的 `TypeError`。

`fetch.js:122-123` 将 `maxRedirects=0` 转为内部 `-1`，`282-328` 因此不进入跟随分支。不能误读 `283-284` 的 “Max redirect count exceeded” 为本次正常 3xx 的必然结果。`failOnStatusCode=False` 也不会因普通 4xx/5xx 自动抛 HTTP 状态异常（140-152）。这些结论只确认接口语义，不确认网络成功。

### 2. 显式代理缺失形成确定的应用层路径差异

完整链条为：

`probe.new_context(no proxy)` → `_fetch.py:new_context` → `playwrightDispatcher.js:67-69` → `GlobalAPIRequestContext` → `fetch.js` → `createProxyAgent` → 默认 Happy Eyeballs agent。

- `fetch.js:498-518` 的 Global context 只保存传入的 `options.proxy`；`118-128` 只从 defaults 取得它。
- `server/utils/network.js:136-156` 的 `createProxyAgent` 在没有 proxy 时直接返回，未访问注册表、PAC、Windows系统设置或环境代理变量。
- `fetch.js:225-228` 在没有该 agent 时选 `httpsHappyEyeballsAgent`；`happyEyeballs.js:62-75, 116-169` 使用 `dns.promises.lookup` 和 `tls.connect` 建立目标连接，没有系统代理发现。
- 同一 `network.js:57` 虽有 `getProxyForUrl`，它属于另一个 `httpRequest` helper，不在本次 APIRequestContext 的调用链上。不能因为共享文件中出现这行就声称本探针继承环境/系统代理。

这里的“默认直连”仅指应用层未显式使用 HTTP/SOCKS 代理。没有检查 OS 路由、透明隧道或安全软件，不能据此断言数据包绕过了所有系统转发。

### 3. 原浏览器前检也经过 APIRequestContext

固定 `7dbe786d` 内存在原始 session 副本：

`docs/evidence/A04/review/coordinate-R3-raw-bytes/inputs/raw product with spaces/src/annotation/runtime/browser/session.py`

其 size=10721、SHA256=`224f3fc6143976c564adaca0b40d65cbca079e057a66e320a804cf13a6bb04c9`，与 native `input-raw-manifest.json` 绑定的原 session 完全一致。未读取实际 profile 或 `.local` 登录配置。

- 原 session `134-140` 启动 Edge persistent context，未传 proxy，并注册 `context.route("**/*", self._route)`。
- `58-90` 的允许请求调用 `route.fetch(max_redirects=0, max_retries=0, timeout=...)` 后 `route.fulfill`；原生观察 `observation.py:25-40` 调用这个父实现并将首次 BLOCK 封存。
- 已安装 `_impl/_network.py:465-486` 显示 `Route.fetch` 委托 `self._context.request._inner_fetch`。
- `fetch.js:476-485` 的 browser-context request 代理来自 Playwright context/browser 的显式 proxy options；它不是从 Edge 的 Windows 系统代理运行状态反向取得的值。
- 固定任务 `docs/tasks/A10-native-readonly-preflight.md:17` 明确三处 session 差量仅接入 checker，路由/登录/关闭主体保持；固定准备/执行记录记载这三处差量。实际 derived session 原 bytes 不在本次两棵树的该路径，本次未读取其他提交或运行目录来重建它。因此“路由保持”的证据层为冻结任务、清单与交付记录；原基线和依赖调用链已直接核对。

这解释了为什么“用了 Edge”不足以推出“请求走用户日常 Edge 的代理路径”。实际普通浏览器类型、profile、当时代理选择、TLS信任和旧轮当时环境均未读取；用户报告仅证明其当前可访问体验。

### 4. 最小环境的实际差别与已排除范围

公开 `probe.py:159-164` 给 worker 固定四个环境键：SystemRoot、WINDIR、NODE_TLS_REJECT_UNAUTHORIZED=1、PYTHONIOENCODING=utf-8，且 Python 用 `-I -B`。没有继承代理、NODE_OPTIONS、额外 CA、DEBUG 或凭据变量。`_driver.py:36-41` 只是复制这个 worker 环境并补充 Playwright 语言版本信息；`_transport.py:104-130` 把它传给 Node。

原 native driver `152-154` 的 Popen 未提供 env 参数，承接父环境；仅有源码中显式关闭 DEBUG/PWDEBUG 的行为。旧归档没有保留当时环境值，本轮也没有读取。不能用今天变量不存在证明旧轮环境相同。

公开结果已到 `GET`，且 context/runtime 释放成功记录存在，因此“整个 Playwright runtime 无法启动”与“new_context 未成功”的解释不符合固定阶段证据。严格 TLS 下 Node 与浏览器信任路径可能不同，但本轮没有证书链证据，不把它升级为原因，也不建议忽略 TLS。

## 错误压缩遗漏与证据边界

1. 原 session `82-90` 捕获范围同时包含 `route.fetch` 和 `route.fulfill`。它只识别 `ERR_CERT_`、Timeout、ECONN/ERR_CONNECTION，其余一律 TRANSPORT。Node TLS 代码不必含 `ERR_CERT_`，所以 TRANSPORT 不能排除 TLS；也不能仅凭这一分类排除响应完成后 fulfill 层失败。
2. 已安装 `server/errors.js:46-49` 对 Error 只序列化 message/stack/name，没有结构化 `code` 或 `cause`。Python `_helper.py:344-355` 重建 Error；`_connection.py:419-426, 556-559` 再添加调用上下文。底层 Error.code 即使原来存在，也不保证在 Python 字符串中出现。把 `getattr(python_error, "code")` 加到旧分类器不能恢复这个已丢字段。
3. 公开 `probe.py:15-29,45-55` 只查 `str(error)` 的固定代码和三个证书短语，未命中即 UNKNOWN。源码内已能确认会漏的 Error 文本类别包括 `aborted`（fetch.js:340）、`failed to decompress ...`（371-375）、`Request context disposed.`（385-387）、`Connection timeout`（happyEyeballs.js:154-156）以及 `Unsupported TLS certificate.`（socksClientCertificatesInterceptor.js:306-314）。这些是分类器缺口的例子，不是旧失败实际发生了这些错误。
4. `fetch.js:340-380` 先接收、可能解压并收完响应体，才 fulfill APIResponse；probe 之后才读 `response.status`。因此“仅显式读取 status”不等于底层没有接收正文；`http_status=null` 也不能证明没有收到响应头。后续方案必须如实标注这一层区别。
5. 公开首结果时间与 GET 意图时间约差 0.373 秒；原 native 第一次 route 至失败约 1.074 秒。它们不符合“30秒期限已耗尽”的叙述，但时间很短仍不能区分连接拒绝、TLS、传输中断或内部错误。

不能事后还原的部分：原完整异常、结构化底层错误码、准确报文数量、实际代理路径和失败的具体传输阶段。旧 UNKNOWN、失败归档和已耗额度保持。

## 唯一建议的最小后续观察（未执行）

建议主调度若登记新观察，只做一次新建、独立 APIRequestContext 的同一公开 GET，唯一传输配置增量是显式使用当前已核对的 loopback 系统代理；不以“再次原样直连”作第二个对照。目标为 `https://www.usense.com/qieti/annotateUnified`，不带 query/fragment；无浏览器、profile、登录、cookies、storage_state、HTTP credentials 或业务调用。代理 endpoint 只由主调度在内存按元数据核准，不回显地址，不读取或复制其他环境值。

固定参数：TLS校验保持开启，GET timeout=30000ms，max_redirects=0，max_retries=0，fail_on_status_code=False。一次应用层 GET 意图；不能把它写成一个底层报文或一个 TCP/TLS 尝试。Playwright 会内部接收/可能解压正文，诊断代码只保留状态，不调用 body/text/json/headers/url 等响应读取 API，不注册请求/响应日志，也不保存 trace、正文、证书、堆栈、Location 或自由异常文本。若“底层也不得接收正文”被确定为约束，则此 API 不符合该约束，应在登记前另行选择传输，不能运行后改口。

输出限定为固定阶段、整数HTTP状态或 null、固定异常类型、固定错误类别、耗时、GET调用意图计数和自有资源释放结果。异常只在内存匹配当前白名单及上节可核验的短语类别；可增加 `SOCKET_HANG_UP` / `TLS_HANDSHAKE_DISCONNECTED` 等明确文本类别时，必须先在新冻结观察源码中列出准确匹配及归类局限，不保存原文。未匹配继续 UNKNOWN。不得通过 DEBUG、原 stderr、trace、任意环境或证书内容扩大诊断。

结果解释预先固定：

- 得到HTTP状态：证明新时点、显式代理、严格TLS的公开API路径得到响应；支持“旧应用层代理缺失值得修正”的假设。受时间变化、环境差异和无同时对照限制，不能独立证明历史根因，更不能证明登录、目标书、浏览器路由或业务可用。
- 连接/隧道错误：只定位该新代理路径；不能重试、换代理、直连回退或重放旧轮。
- TLS错误：保留严格验证的失败，不能自动忽略证书。
- UNKNOWN或释放不明：首结果原样封存并停止，不补发。

资源方案：新观察使用独立一次性标记与新冻结源码，不能复用旧 run-once 标记、重跑/修改旧 probe。父进程先持有创建得到的 Popen 原句柄和 Job、绑定成功后放行；50秒运行截止、57秒释放轮询、60秒总预算。只处理自有 Job/原句柄，不扫描进程、不按名称结束进程、不打开 profile。独立执行 context.dispose、runtime.stop、原 worker退出/Job active=0核对及句柄关闭；每项失败单独保留，关闭成功不能代替退出证明。普通浏览器、代理服务和系统设置均保持。

本子 agent 只提出该一个观察；没有生成可运行观察文件、发起观察、登记新次数或派发其他 agent。是否采用及新一次性启动范围由主调度固定。

## 关键原字节摘要

本机依赖根：`C:/Users/ASUS/AppData/Local/Programs/Python/Python39/lib/site-packages/playwright/`。只核对源码，未运行依赖；原绑定 node.exe 二进制没有在本轮重新执行或散列。

| 来源 | SHA256 |
|---|---|
| fc81de1b public-transport/probe.py | 6bf0b3a3aecaf07df9ab7a8595dbeb0cc2b1364fc7283e82dcebe83e4e68d888 |
| fc81de1b public-transport/input-bindings.json | 9e01203b1285768043d894737ab31392ddfa6ae61128a990665f8354608ba97f |
| fc81de1b public-transport/first-outcome.json | a4f65ab7be574889cc46f893e2d7e1f2269d1d05c6ba83fca9751df3ce809207 |
| 7dbe786d native-preflight/input-raw-manifest.json | 14135b8b59e0921d924b035ae44cc852d554f00b46bcc0ef552578625982b4b4 |
| 7dbe786d native-preflight/observation.py | ae33ddee987a7e36622f1ace24d46045436b50310b88d39911afa411ecb2c048 |
| 7dbe786d native-preflight/result.json | f34843d2396fa7f4e450d1fb2c5785924e5a58eb9c1c9dcd8e13b3844e5a31e7 |
| 7dbe786d 原 session 副本（完整路径见正文） | 224f3fc6143976c564adaca0b40d65cbca079e057a66e320a804cf13a6bb04c9 |
| sync_api/_generated.py | 666f99ee867ce46d2f70198b595100a2156388e865168c126aaf9bf3e8f8c388 |
| _impl/_fetch.py | a7ac7d7cf02a8a8ccda0eea3a8d8a9b6308075dd67292592b5292c9deb4dc3c6 |
| _impl/_transport.py | 896dda8a25b612f46119fa25bcaed0f026ee719a85bd7b47972612ae47b6d00f |
| _impl/_driver.py | 9a15469de4b0e15773169d32df12a2a694298a8b03ee68655c504532a27d4eaa |
| _impl/_network.py | c2528eaf76b59e45cc86c03152abfafcf694d3c39f6a4c8a55ce8f0ecb270926 |
| _impl/_helper.py | 1bb682d7e5d0d2c61306b0206307075a94bc6b680f12269cd3e241f35161434c |
| _impl/_connection.py | bc474593abd8cf676156b3e0c16d463edd027c61cf715462bb6f3c96ffdad9cc |
| driver/package/lib/server/fetch.js | 4763a8d6e07088d702b667f6ed9c54eb0a92328032df6ff4d8fc806e1db53f04 |
| driver/package/lib/server/utils/network.js | 46a49a1c43e939051f2cf9fb3d19d3e2766d871878833166dca5fc70a0c855b5 |
| driver/package/lib/server/utils/happyEyeballs.js | 09b06ef645ea809df49f26aa5c10d703b38abac286536c27672cfb709efacc42 |
| driver/package/lib/server/errors.js | 883a5e30085bb7a39f003bca462da5191ee3e9e002298d3ad5250296896afa5b |
| driver/package/lib/server/socksClientCertificatesInterceptor.js | efa8de1d21be81f9e27515de9abb0d507e5269341d0cc14d722fa3df0d97c2a9 |
| driver/package/lib/server/dispatchers/playwrightDispatcher.js | 0105dbd04d075ba0e12abae7ce7b463538a9b2f70ce3040b815488d9ed66a0b9 |

## 释放声明

静态任务交付并释放。本次没有建立 browser/context/Playwright runtime/Job/profile租约，也没有活跃观察或后继业务任务。旧额度、旧失败、原文件与其他服务均未由本子 agent 改动。报告的最终 raw SHA256 由交付消息给出，避免自包含摘要。
