# A22 唯一实际轮固定失败与释放独立核证

结论：ACCEPTED_FIXED_FAILURE_AND_OWN_RELEASE_ONLY。仅接受本次固定失败归档与已证自有释放，不接受平台认证、profile 持久化、书源、书籍身份或首题保存读回。A22 live 已用 1、余 0，不重跑、不改旧 activation/output/标记。

独立对话 01a15cad-c63a-7062-8fe6-2fc4add9e9a5；本次核证派发 workflow817903b62df8adcc4a48009a70184a23e23dd253，任务 SHA256 a17e88ea456783072a6a97796507de6677a0c6db62cb051c1bada3b077f0c1fa。产品41fda0d1ff7f548e1bc8ec6b5b4d653109736532、pre-live final1acc8d00dfef5808561139a99ba6f028d7bfd7a1、实际 final3517982bd416ff77fdf596e80c502a75d780f2b9，产品 workflow68279e400143c5681338530db409060a39760c0a 保持。

仅静态读取 D:/1800-worktrees/a22-live-review 固定输入，以及根指定任务/输入清单。58 份输入逐份核大小、SHA256、Git blob SHA1，候选28依赖、实际28成员及两清单自身恰好闭合为58。候选 SHA256 264e7fd8120efc8dd8f95f6c66b28693104d82f47e3d68e3a91fd0c422b38141；实际交付清单 SHA256 7602eb7d04101047f161c3c392e1076e0b3600b8e5b21aacfc19b58232a7e006；根输入清单 SHA256 ecb2034e126b5b37e9d415979ed320f3587a6442b906f02a818c3242f34c08db。10 份 raw-copy 成员与其冻结清单相等。本次静态核记录17组通过，不是 suite 或产品运行。32045旧成员保全、29新增0改删、直接父链及五份 authority 与根原件相等是根已核事实，本独立不扫描 Git、原活动作者目录或 .local 补证。

包内 activation/authorization/原独立机器报告/派发任务原 bytes 的 hash 与 dispatch/prelaunch 一致，50 项原范围逐项同类型同值核对，候选亦一致。原 profile 指纹 b4620cd9fe064121a916062126321b7bba3862185d8919bf228f1399097a0d00；四个 claim 均绑定同一 A22 run/candidate/workflow/profile/activation。authorization 使用 A17 持续只读 TLS 许可，用户名密码配置读取、凭据传输及登录授权均 false，未借 A21 已耗许可。

窗口为 2026-10-21 04:47:40.208839—05:02:40.208839 UTC，900秒含释放。唯一固定 envelope 04:49:20.646327—04:49:40.826781 UTC，单调20172ms；其 argv/cwd 与固定派发相等，记录 launches1/retry0。原 capture_once 源码只作静态查看，未执行。launch intent、四标记、有限输出中没有第二次启动；这不是 OS 全历史证明。

原主 Document 记录 HTTP200、DCL，goto12046ms，VISIBLE_CONTAINER readiness47ms/DONE，随后 ERROR/PROTECTED_AUTHENTICATION_UNPROVEN。原结果 session_receipts/native_http_observations 均为空；permissions 仅有两层预留/ALLOW 事件，没有成功响应投影。组合准入和真实账户认证未证，不能据此认定注销、凭据无效或 profile 持久化失败。具体缺失原因 UNKNOWN；最终错误码没有分支级 trace，也不据此断言唯一失败分支。

导航两层各预留1；六固定业务 GET、viewer14/173 两图及映射、全部样题和登录动作均 NOT_RUN，书籍身份 false 表示未获证明。审计中无业务/注册原图预留，无写方法；用户名密码配置读0由冻结拒绝入口和序列化结果支持，不冒充 OS 文件访问审计。业务写入0，write_eligible/production_ready=false 保持。

13项是守卫事件，不是13个HTTP请求。permissions 两事件也不是两次HTTP成功；session 实际发送数/状态 UNKNOWN。version 两层各预留1，HTTP成功 UNKNOWN；CDN Script 一项预期拒绝及完成调用记载，不证明脚本必要性或 DNS/TCP/TLS 零活动。一个同源 Script 仅有已捕获元数据、hash/size/HTTP200，完整3,065,996字节 body及sidecar仅.local，本次没有读取、复制或打印。它不构成 schema、账户身份或书源接受。

| 持有身份对象 | PID | 前后创建 FILETIME 一致 | 已观察退出码 | 持有句柄 |
|---|---|---|---|---|
| product | 51224 | 134370317616692552 | 2 | 已关闭 |
| worker | 42792 | 134370317624701624 | 2 | 已关闭 |
| occupancy | 41356 | 134370317634722847 | 0 | 已关闭 |

前后 PID 和创建身份匹配，退出 FILETIME 均在固定窗口内。两 Job final active0/closed；context_closed/runtime_stopped=true、errors=[]；shutdown 前及序列化 pending0，无截止超限记录。仅据此有限接受这些对象释放。launcher 自身仅有 envelope child returncode2，没有持有其 OS 创建身份的前后比对，继续 UNKNOWN。

capture工具exit0与 launcher/product/worker 的 exit2 分开；前者只说明证据包装完成。launcher stdout 原135bytes 已核 SHA256 454bc8839e2b14c128e8ecc6bd81417a33c395dca90fdb9319abc363eff11168 及固定JSON字段；其中 errors=false 不把 product_exit_code2 改成观察成功。product stdout90bytes仅有计数/digest，原bytes缺失，不重构。worker stdout/stderr均计数0，outer stderr计数0/hash为空摘要。

墙钟/单调时差分别保留：envelope墙钟20180.454ms vs单调20172ms；launcher墙钟18872.548ms vs单调18969ms；worker墙钟17985.910ms vs单调17985ms。各层仍在窗口内；差值原因 UNKNOWN，不猜时钟调整、系统或产品根因。prelaunch可选文件缺失及capture父目录表达式在启动前纠正仅有作者转录，未提供独立原失败输出；不能升级为产品重试，也不要求为报告细节重跑。

本次0suite、产品import/run、launcher、浏览器、网络、profile、本机配置、native、占用及新连接；没有进程扫描、凭据访问、重试、清锁/标记或新live。静态helper已完成，无等待进程或持有资源。仅本次报告/机器结果/静态记录/清单/释放写入指定独立目录；原58输入复核不变。其他三例HOLD、Q22不重放、0B/外部联系人消息。A23必要离线准备并行不由本归档激活，本独立不检查活动A23工作。
