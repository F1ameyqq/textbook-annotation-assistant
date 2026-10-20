# A12 独立静态核查

只适用[新专用无头reuse-only观测](A12-headless-reuse-native-transport-probe.md)，不重跑A04/A10/A11，0平台/原profile/凭据访问。作者仅1冻结候选/1次N1-N3本地suite；独立不得复跑suite、另造浏览器矩阵或补做作者失败的后继。

准备阶段只读任务标准、既有权威源码和依赖接口；作者固定产品、raw清单、唯一结果及精确自有释放后，主调度另发确切commit和raw身份，再正式核查。准备不等于验收产品，不因工作目录出现文件而提前读取作者未冻结实现。

正式从固定raw隔离导出，核对：

1. 原路径保全、单候选/单suite、3例真实流量和时间顺序，首失败后NOT_RUN，不能把单元函数返回当终点0请求。
2. 原生浏览器路径及发送前逐跳origin/method守卫；不把route.continue_等价于redirect安全。WebSocket、worker/serviceworker和子页/弹出页不能成为未覆盖发送口；不能通过关闭浏览器前没等到事件冒充负例。
3. N1实际允许GET/同origin重定向，N2实际发起跳转且禁用终点0请求，N3脚本实际发起POST/WS且服务器0记录。对照固定驱动、服务器记录、CDP/请求事件审计和精确释放证明，不只信摘要。
4. live默认关闭、一次性标记失败也不重置、确切候选摘要/原profile绑定/占用检查、90秒硬界限及精确自有释放。若守卫或占用未知则拒绝；不读凭据、不登录、不改TLS、0业务，不按URL/HTTP200伪造认证。
5. 本任务使用正式开发接口实现新headless网络守卫，不能用于操控被URL策略拒绝的chrome-extension页或任何其他绕过。任何令牌/登录原件不得进入报告。

报告仅可为ACCEPTED_PREPARATION_FOR_ONE_REUSE_ONLY_OBSERVATION、REWORK、BLOCKED；不能宣称真实认证/书籍/内容/框保存通过。报告列确切产品/驱动/最终提交、raw核证、证据路径、已查/未查与风险、独立0运行和释放。主调度核证后才决定本轮新的唯一live启动；有缺口则停，不自动追加候选或suite。
