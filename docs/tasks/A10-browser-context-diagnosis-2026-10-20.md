# 普通浏览器可访问后的有界诊断

用户已回复既有访问情况问题：“可以正常打开”。这是一条用户报告的新上下文，不是自动化已通过，也不证明此前失败原因。连接许可继续有效，旧A10失败、启动标记及已用额度原样保留。

本阶段先只读核对旧API诊断的实际源码、错误分类和最小环境，与本机当前系统代理/证书相关配置的非敏感元数据比较。目标是在任何新网络调用之前确定具体差异和可验证假设。不得重跑旧driver、启动浏览器/profile、读取凭据/证书私钥/cookie、读取或输出环境值、改系统设置或进行业务操作。

- 主调度：仅检查明确列出的代理/TLS环境变量是否存在，以及当前用户Internet Settings的代理启用/PAC存在/代理类型等元数据。地址、PAC内容、认证信息、任意环境值均不输出或入库；不请求PAC或自动发现。
- 静态分析子agent：只读本地固定Git对象 `fc81de1bf8e3ee10e4d9f9da1aa99f34afbe5f23`、`7dbe786da0d6ff86eef8ca9c05bccdc2d5583204`、既有相关任务/诊断资料与已安装依赖源码；确认调用参数兼容性、固定错误码分类遗漏及与日常浏览器可能不同的执行路径。零网络、零OS进程扫描、零旧测试。只在 `.local/stages/coordinator/a10-browser-context-20261020/` 写静态报告，不改产品/旧证据/主调度文件。
- 子agent一次静态分析交付，报告列清确定事实、推测、最小可区分观察与资源/错误脱敏方案，交回后释放。不得自行启动观察或续派。
- 主调度结合固定报告与本地元数据，再登记最多一次具体只读网络诊断的目标/传输方式/超时/输出边界；若无可区分假设则不发请求。本任务自身不登记已发生网络请求、不扩大原平台/登录/写入次数，也不解除Work浏览器功能设置。

新诊断服务于书46007447的三天有限试用，其他三例HOLD，Q22不重放、B不发消息、A10/A11不推送。新题清单/真实写入范围仍须在当前事实明确后固定。

## 本地证据支持的唯一后续观察

本机元数据已确认Windows用户代理开启、loopback端口7897、无PAC和userinfo；列出的代理/TLS环境变量均不存在。静态分析确认已绑定Playwright API transport只使用显式`options.proxy`，旧探针未传该参数，使用直接DNS/TLS连接，不读取Windows Internet Settings。此差异支持一次可区分观察，但尚不能断言旧失败由代理导致。

主调度在既有连接与持续推进授权内，登记一个新的、有具体路径差异的只读观察：只在`docs/evidence/A10/system-proxy-observation/`冻结新代码；沿用旧公开端点、最小环境、严格TLS、错误分类和自有Job清理实现，仅增加当前代理前提核对并显式使用`http://127.0.0.1:7897`。这不是修改旧日志规则后重放，也不恢复旧启动额度。

- 一次新启动，至多一次API GET意图；请求30秒，总收口60秒。无重定向、重试、fallback、第二请求或第二候选。调用数不冒称网络包精确次数。
- 启动前固定候选、raw清单与独立静态检查；主调度登记唯一启动凭据后才运行。冻结代码不允许修改后继续本轮。
- 在GET前再次检查代理启用、无PAC、且配置仍为同一个无认证loopback端口；变化或未知即零GET停止。
- 不创建浏览器、不读取普通浏览器/profile/凭据、不绕过Work浏览器设置；不读取HTTP响应正文/头/Location，不登录，不选择书或写入业务。
- 独立检查仅审固定新代码/旧Job字节及差量、脱敏、依赖绑定、单次预算和固定归档释放，零网络。此次读到HTTP状态只证明该API代理路径有响应，不等于原浏览器问题已根治或登录/书籍/业务通过。

本轮结束后依据首个结果更新路线；无法确认时保留结果并停止，不在此任务扩展无界故障矩阵。

## Explicit coordinator engineering-limit revision

Candidate 6966509b consumed one startup and failed before Job construction, Popen, GO or GET. Python -I excludes the script directory; the sibling owned_job import failed. Preserve startup-failure evidence and cleanup_proven=false. The static review missed launcher compatibility. No original candidate retry.

Under existing user continue-and-connect authority, the coordinator explicitly revises its own one-candidate engineering limit: one additional local-import-only candidate and startup, cumulative two candidates/starts, still at most one GET across both. This is not a separate user approval or restoration of old A10 budgets. Load only the hash-bound sibling by absolute file spec; keep isolation, TLS, request, classifier, Job and timeout policy unchanged. One zero-network import check before freeze, independent fixed delta/archive review before startup. Preserve old code and markers in a separate directory. If this fails, seal and stop; no third candidate.
