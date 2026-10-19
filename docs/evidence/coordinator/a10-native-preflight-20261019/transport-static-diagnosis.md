# A10 首次导航失败：固定归档静态诊断

2026-10-19。仅分析固定 Git 原始字节；本报告未发起任何网络、浏览器、profile或OS进程探针，没有运行旧测试、修改实现或重试A10。报告不入提交，原独立清理结论不在本次重审范围。

## 结论

可以确定最早可见失败进入了 A04 `_route` 的异常分支，随后失败被压成 `TRANSPORT:1`；**不能从现存归档恢复具体底层错误码，也不能确定异常发生在 route.fetch 还是 route.fulfill**。原因信息在原调用现场已经被丢弃，再分析同一组脱敏归档不会恢复它。

最小下一步建议是另行固定、登记一个无凭据、无profile、无浏览器的 Playwright `APIRequestContext` 单跳GET诊断，至多一次请求公开固定VIEWER入口。它能观察同类API传输路径的错误码/HTTP状态，不能替代原导航、登录、书籍现状或几何验收。它不是重启或修后重放旧A10 driver；旧唯一平台轮仍已耗尽。本报告只提出方案，没有执行。

## 固定事实与源码证据

归档：`7dbe786da0d6ff86eef8ca9c05bccdc2d5583204`。路径前缀 `docs/evidence/A10/native-preflight/`。

| 固定证据 | 可支持的结论 |
|---|---|
| `network-audit.json`：15:16:47.733035Z GET/NAVIGATION/ALLOW；15:16:48.800697Z GET/NAVIGATION/BLOCK；两项status均null | 请求先通过本地策略，随后记录异常阻断；ALLOW不等于HTTP发送/接收已证实 |
| `result.json`：first_network_failure.transport为TRANSPORT:1；SESSION_FAILED/open_viewer；rounds=1，retries=0 | 最早保留的传输分类只有兜底值；不能据此定DNS、代理、证书或站点根因 |
| `session-release.json`：auth_mode=UNCONFIRMED，ignore_https_errors_this_run=false；local_empty_bootstrap_count=0 | TLS校验开启；登录与受保护页面未确认；没有空bootstrap掩盖此次导航结果 |
| result中login_attempted=false，后续目标书/目录/题框/原图/几何NOT_RUN | 不能把本次称为凭据拒绝、书籍缺失或几何失败；这些步骤未执行 |

以上为归档时点证据，不是本次重新观察。

原A04源码固定 `6c8137a4fadddc01a47906d564ab3460277c8958`，`src/annotation/runtime/browser/session.py`：

- 第70行：在发起fetch之前写入ALLOW审计，因此该条本身只是策略决定。
- 第75–82行：同一个try覆盖第76行 `route.fetch(max_redirects=0, max_retries=0, timeout=self.timeout_ms)`、读取response.status、重定向分支abort以及第81行 `route.fulfill(response=response)`。故异常分支的TRANSPORT不唯一指向底层fetch。
- 第84–89行：`detail=str(error)`仅用于判断 `ERR_CERT_`、`TimeoutError`/`Timeout`、`ECONN`/`ERR_CONNECTION`；其余统归TRANSPORT。写入计数与BLOCK后，异常类型、底层码、原调用子阶段均未保留。
- 第89行没有把已取得的response.status传入审计。若fetch取得2xx后fulfill发生异常，仍可能只看到status=null。因此null不能证明没有收到HTTP响应。
- 第90行主动abort；之后page.goto的失败可能是该abort的次生错误，不能拿次生ERR_FAILED/ERR_ABORTED当作原始根因。
- 第148–156行：open_viewer包含首次goto及可见marker等待，之后才进入login。第180–184行又把非TimeoutError压成SESSION_FAILED，并使用`from None`丢弃原异常链。

同一A04的 `guard.py` 第199–220行：NetworkAudit仅保留method/category/decision/status/time，接口没有错误码/异常类型/阶段字段。`BrowserSafetyError` 第39–60行只允许固定code/stage，这保证秘密不外泄，但无法还原此前原因。

本轮固定 `observation.py` 第26–40行：调用 `super()._route`，从新审计记录取首个BLOCK，仅复制time/category/status和已有transport计数。第130–133行只保存异常code/stage；没有另存底层异常。第142–144行保存上述脱敏结果。因此不是另一个归档文件可以补回原错误。

本轮input清单绑定原session SHA-256 `224f3fc6143976c564adaca0b40d65cbca079e057a66e320a804cf13a6bb04c9`，派生session SHA-256 `7b6fac9132fa30d6fdb5883c2925e3518bd596377da44dc3087c560b8303c16a`；派生仅为既有三处checker注入，不改变这些传输分支。

登录辅助源码按input清单固定为 `65e1b56f52f2ee642fae5f35f23116df3a058600:tools/usense_login.py`，SHA-256 `5d8544963d10dd15254ccc44b7a14a609109021e61564229faac8f261db91de3`。本次只读其Git源码，没有读本地配置或profile数据：

- 第83–110行 `browser_failure` 也只作固定摘要，证书判断仅在第96/98行匹配net::ERR_CERT类。但A04 session自己管理启动/goto/异常，不调用该helper的`login()`及`browser_failure()`，所以这些分支不能为本轮补充诊断。
- helper第73–79行用于页面标记确认；第113行起的独立login流程不是本轮实际使用的会话控制器。
- 本轮driver第52–57行核对固定输入和实际helper源码摘要；第80–86行加载独立派生session。本报告没有检查或读出任何凭据、token、cookie、运行时authURL。

## 证据与假设的界线

TRANSPORT仅说明原字符串没有命中上述有限判断。DNS错误码ENOTFOUND/EAI_AGAIN、代理错误码ERR_PROXY_CONNECTION_FAILED、某些不含ERR_CERT_的证书错误字样，都可能落到TRANSPORT；这是从分类条件推出的静态可能性，**不是这些错误已经发生的证据**。异常也可能来自fulfill或其他本地API调用。不能因TLS=true便认定证书必然正常，也不能根据约1秒的首错耗时断言DNS/代理/证书中的某一种。

旧资料未保留原错误码，不能用增加离线猜测矩阵来提升根因置信度。需要新的、范围明确的观察。

## 最小下一步：一次独立API传输探针

建议主调度单独登记一份新的诊断范围，并在执行前固定短脚本及脱敏规则。无需改写原driver、原session或清理实现，也不恢复原A10平台轮数。用户既有连接与测试书许可保持；本诊断自身不取得额外业务写入许可。

1. 使用现有Playwright运行时，仅创建一个 `APIRequestContext`。不创建浏览器/browser context、不读凭据/profile/storage_state、不设置http_credentials、不导入helper执行登录；不读取代理配置或任何token/authURL。
2. 目标只取固定helper源码中的公开VIEWER入口常量；冻结时确认是既有允许origin/path、无查询参数/fragment。不使用动态登录跳转地址，不读取Location。
3. 恰好至多一次GET：`max_redirects=0`、`max_retries=0`、`ignore_https_errors=False`、请求期限30000ms、`fail_on_status_code=False`。不改系统/全局代理、TLS、证书或环境；不安装依赖。总诊断期限建议60秒，包含启动与自有资源收口。
4. 仅记录下面允许的诊断字段。得到首个HTTP状态或首个异常即结束，不跟随重定向、不请求其他端点/静态资源、不登录、不读取/保存/散列response body或headers。
5. finally只dispose该request context并停止自己创建的Playwright运行时。清理失败记录为失败，不能因HTTP状态已获得而宣告整体成功。启动/固定依赖/目标绑定不符、超时、未知错误或资源未释放均停止；没有第二请求、fallback、换TLS开关、换代理或自动复跑。

允许输出：固定阶段枚举 `START_RUNTIME / NEW_REQUEST_CONTEXT / GET / DISPOSE / STOP_RUNTIME`；固定异常类型枚举 `Error / TimeoutError / OSError / TypeError / ValueError / OTHER`；HTTP状态整数或null；耗时、尝试计数和自有释放布尔值；最多四个命中的固定错误码（未命中为UNKNOWN）。不输出自由文本异常、堆栈、URL、IP、请求/响应头、body、环境、证书主体或代理地址。

建议码白名单：`ENOTFOUND`, `EAI_AGAIN`, `ECONNREFUSED`, `ECONNRESET`, `ETIMEDOUT`, `ENETUNREACH`, `EHOSTUNREACH`, `ERR_NAME_NOT_RESOLVED`, `ERR_PROXY_CONNECTION_FAILED`, `ERR_TUNNEL_CONNECTION_FAILED`, `ERR_CERT_AUTHORITY_INVALID`, `ERR_CERT_COMMON_NAME_INVALID`, `ERR_CERT_DATE_INVALID`, `ERR_TLS_CERT_ALTNAME_INVALID`, `CERT_HAS_EXPIRED`, `UNABLE_TO_VERIFY_LEAF_SIGNATURE`, `UNABLE_TO_GET_ISSUER_CERT_LOCALLY`, `DEPTH_ZERO_SELF_SIGNED_CERT`, `SELF_SIGNED_CERT_IN_CHAIN`。只输出白名单完整常量，不按任意大写字符串提取。若需要兼容常见无码证书文字，可在内存匹配固定短语并只输出 `TLS_CHAIN_UNVERIFIED / TLS_ISSUER_UNAVAILABLE / TLS_SELF_SIGNED`，原短语和原消息均不输出/落盘。

结果边界：获得3xx/401/403/2xx均可证明该探针观察到HTTP响应，但不证明原浏览器导航/登录通过，也不跟随或读响应内容。得到明确固定码后再针对该码制定一个具体修复动作；本轮不边诊断边改配置。UNKNOWN仍停止并保留，不能扩大为无界诊断矩阵。

该无状态request context与原route.fetch属于同类API请求方向，但不是原共享浏览器context的完整重现，身份状态和上下文设置可能不同。若探针成功，原fulfill/页面导航故障仍未排除；如果失败，其固定错误码可为下一步提供直接线索。不要把独立探针成功改记为原A10重试成功。

## 本次只读取证摘要

| 归档对象 | SHA-256 |
|---|---|
| network-audit.json | fae69101758bde4a2500d9747a98ab43f48b095dfde95d489d1406b4f88752bf |
| result.json | f34843d2396fa7f4e450d1fb2c5785924e5a58eb9c1c9dcd8e13b3844e5a31e7 |
| session-release.json | 1d09a80bbf103bd5b2cc4f6eb5f0e1d0d14e3544b08e96a7caebd08e7114f7ae |
| observation.py | ae33ddee987a7e36622f1ace24d46045436b50310b88d39911afa411ecb2c048 |
| driver.py | 9fb0118804948803bc6ddb109ddc983e1e45609a26d963da646587e11bbe74c2 |

本轮只使用 `GIT_NO_LAZY_FETCH=1`、`git -c core.longpaths=true` 读取上述本地固定对象，并新增本.local报告。网络/平台请求、浏览器、profile访问、OS进程查询、旧测试、安装、全局网络/TLS修改均为0。原失败与原轮次记录保持。
