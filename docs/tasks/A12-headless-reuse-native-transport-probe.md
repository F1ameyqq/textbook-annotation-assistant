# A12：专用无头 profile 复用的原生传输观测

2026-10-20。用户继续要求原无头路线及三天试用目标；现有扩展MCP已验证到日常Default登录页，但它不含原专用登录态。旧A10第一次失败发生在A04的 `route.fetch(max_redirects=0,max_retries=0)` API传输路径；本次原生Edge导航实际到达平台登录页。这是新路径证据，不是根因证明，也不恢复任何旧轮数。

## 唯一目标与权限

确认原专用无头profile能否通过原生浏览器网络读取受保护标注界面。仅一次新候选，先离线验证必要的网络守卫，固定交付和释放后独立静态审查；作者不得访问平台。主调度核证后最多启动一次新reuse-only观测，书籍选择、来源/题框读取、文字/框写入全部不在本任务中。

不运行旧A10/native/代理driver或 `usense_login.py` 的自动登录入口。不得填写/提交登录、复制Default状态、忽略证书、修改profile内容求通过、安装依赖或启动付费模型。最终首次异常或LOGIN_REQUIRED立即停止，无自动重试，无第二候选或第二live启动。其他三例HOLD、Q22不重放、0B消息。

## 允许新增路径与隔离

- `tools/headless_native_reuse_probe.py`
- `docs/evidence/A12/native-reuse-probe/`（固定清单、离线驱动、结果、报告、释放）
- `docs/tasks/A12-headless-reuse-probe-author-report.md`

作者使用独立分支/目录，从调度派发实际workflow commit读取以上任务规则。所有Git从第一条 `GIT_NO_LAZY_FETCH=1`、`-c core.longpaths=true`。不修改旧源码、合同、依赖、pins、调度JSON或旧证据。预检失败保留，不以reset/clean/stash求干净。

## 产品必须满足

1. import无副作用。CLI默认仅静态检查；live模式必须有确切候选摘要、一次性启动标记和固定输出目录；已存在标记（成功/失败皆同）拒绝再次live。先落盘intent，异常不删除标记。
2. live仅使用 `D:/1800/.local/browser-profiles/` 下原已有专用profile；可要求恰好一个目录并核固定非敏感指纹，不能读取登录JSON内容、cookie、storage、token或复制profile。读取profile元数据和浏览器正常复用存储由运行库负责。不得使用日常Default。先核现有实际占用，冲突停止，不杀他人进程、不删锁。
3. 无头持久化Edge，严格TLS、service workers关闭、无登录回退。只创建一个自有页面，最多一次导航意图 `https://www.usense.com/qieti/annotateUnified`，重试/重载为零。导航总限时不超过45秒，全轮硬上限不超过90秒；超时需要精确自有释放。不得让宽泛进程扫描支配/超出硬上限，不能批量kill。
4. 新传输使用浏览器原生网络，不使用 `route.fetch` / APIRequestContext。守卫必须在可能发送前拦截非GET/HEAD、非固定Usense及已审查静态资源origin的请求和WebSocket；顶层导航只允许固定平台origin，逐跳重定向也必须受控。固定allowlist来源须引用旧已审查源码，不能凭猜测扩域。不能仅把原 `route.fetch` 换成 `route.continue_` 并假定重定向会再拦截。
5. 可使用正式Playwright开发接口和Chromium Fetch请求阶段暂停实现网络守卫，但其用途只限全新增专用无头驱动的网络边界，不得用作操作被URL策略禁止的扩展页、读取认证值或绕过任何交互授权。若不能证明逐跳守卫，交付BLOCKED，不启动live。
6. 判断仅复用既有 `verify_viewer` 的受保护标记、实际平台路由和登录框是否可见；禁止把URL或HTTP200单独当认证成功。遇登录表单输出LOGIN_REQUIRED并停。输出为AUTHENTICATED_VIEWER_OBSERVED、LOGIN_REQUIRED、ERROR或UNKNOWN之一，保留原异常类别/期限和NOT_RUN后继，不泄露响应体、页内容、账号或profile绝对子目录。
7. 释放只针对本次context/worker的确切句柄与身份，保留创建/退出/close/错误和最终释放状态。无证明时为UNKNOWN，不销毁原profile。首个意外失败保留，后继NOT_RUN。

## 唯一离线验证

冻结前允许语法与纯静态检查。固定产品和驱动后仅一次本地suite、最多一个临时自有无头浏览器，使用临时空profile和本机HTTP fixture，无真实平台/原profile/登录配置/凭据。固定三例：

- N1：允许origin的GET与同origin重定向最终页能够读取。
- N2：允许入口302到另一不允许origin，终点服务器真实收到0请求；必须验证浏览器实际流量，不仅比较计划或guard函数返回。
- N3：页面实际发起POST及WebSocket尝试，终点记录0业务请求/握手；不得把没发起调用当负例通过。

套件首次意外失败即停，后继NOT_RUN，保留临时服务器自有退出及context释放。不改后重跑，不为覆盖率扩矩阵。若本机依赖/守卫不可满足，固定失败或BLOCKED交付；不能擅自另派运行额度。

## 固定交付和独立审查

作者提交产品commit、冻结驱动及raw成员清单/摘要、唯一suite实测、3例实际终点计数、原路径保全和精确自有资源释放；报告REVIEW，不自宣ACCEPTED。独立新agent仅从固定raw交付做静态核查及原始记录核证，不重跑suite/平台；主调度接受只限“可进行这一次reuse-only观测”的准备资格，不能称真实平台通过。

live启动前另记该候选摘要、真实profile非敏感绑定、当前占用、启动时间/硬期限和单次启动标记。本任务不产生具体题目写入授权。真实受保护界面若可用，才另固定书46007447的当前只读来源/目标范围。
