# 固定公开入口单次传输诊断

2026-10-19。用户要求按三天路线持续推进，已明确一直允许连接平台。此项为新的最小只读故障定位，沿用连接许可；旧A10唯一平台前检已经失败收口，不恢复其轮数，不重放原driver，不增加业务写入。

## 固定输入与观察边界

- 旧失败归档 `7dbe786da0d6ff86eef8ca9c05bccdc2d5583204`。静态诊断指出旧session同一try覆盖fetch/fulfill，现有TRANSPORT分类不足以判定根因。
- 固定公开入口 `https://www.usense.com/qieti/annotateUnified`，来自既有Git登录辅助源码的VIEWER_URL常量。无query/fragment；不得换端点、跟随重定向或登录。
- 使用现有Playwright的一个无状态APIRequestContext，至多一次GET。TLS校验开启，max_redirects=0、max_retries=0、fail_on_status_code=false，单请求30秒，整个诊断及自有资源收口60秒。启动/绑定/环境能力不满足即停止，未发请求也不自动重启。
- 不使用浏览器、profile、storage_state、http_credentials或本地登录配置；不读取代理设置、凭据、token、cookie、环境值，不改变TLS/系统代理或安装依赖。API实现可能接收响应，但不得调用读取、保存或散列响应body/headers/Location的方法。
- 结果只允许固定阶段、异常类型、明确白名单错误码或UNKNOWN、HTTP状态、时间/计数、精确自有进程与释放状态。不得输出自由文本异常、堆栈、URL/IP/头/正文/证书主体。捕获异常原字符串只可在内存匹配固定码/固定证书短语后丢弃。
- 首个状态或异常即停止；零第二请求、fallback或修改后重跑。该诊断不能证明原浏览器导航、登录、书籍状态或业务通过。
- worker使用固定最小环境及 `NODE_TLS_REJECT_UNAUTHORIZED=1`，不读取或复制父进程环境，不携带NODE_OPTIONS/DEBUG/代理/凭据变量；这是该新自有进程的配置，不改全局。与旧ambient transport不完全等价须随结果说明，不能把新错误直接归因为旧A10相同根因。依赖在此环境不能启动则0 GET失败并停止，不回退。

## 交付与执行

复用诊断agent `/root/a10_local_guard_diagnosis`，先在独立工作目录新增 `docs/evidence/A10/public-transport/` 下短脚本及输入/原字节清单、任务报告，不改旧产品或归档。先静态检查并冻结Git候选，0网络交回；主调度核对后再给一次具体执行信号。自有进程须能限时收口，Windows子进程可用仅归属自己的Job/原句柄，未知权限或身份停止，不操作其他进程。不要为此重做通用运行时。

执行后保留启动标记、请求次数、首错或HTTP状态、自有清理、固定报告/raw清单，封存交付并释放。独立只审固定源码及归档，0新网络。作者、独立均不重跑旧A10/A07/A08/A09等成功或失败场景。

## 下一依赖

明确错误码后制定针对性修复；未知则如实记录具体剩余信息缺口。此次不预授权TLS忽略、代理修改或第二次请求。A11离线录入内核并行推进；其他三例HOLD，Q22和书级送审不触碰。
