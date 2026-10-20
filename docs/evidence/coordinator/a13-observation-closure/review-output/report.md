# A13 独立静态验收：仅接受固定失败归档与自有资源释放

结论：`ACCEPTED_FAILURE_ARCHIVE_AND_EXACT_OWNED_RELEASE_ONLY`。观测仍为 `BLOCKED`，根因 `UNKNOWN`；本报告不释放平台或业务后继。

独立对话 `01a157d3-48d4-70e0-8b77-b3bb6d00fcea`；执行对话 `01a157d2-caed-7162-8c48-06ad7117bd90`。固定产品 `d45ed25a98361002ddb28985c1d27687c4421a17`，最终交付 `81fab23e3e7e9e32a36d3857a253afc69b5bd3e1`。执行清单 SHA256 `58477a26586e43dd726c52124603e435c9cd0bf659f96e6756715aeaa24743dd`。

隔离输入恰为83文件：53原始固定输入、29执行输出及其清单。大小和SHA256全匹配，无缺失、额外、reparse或symlink文件；53输入的Git blob OID独立重算一致。候选21、交付30、继承22成员匹配。此前R1的8/8、562ms及清单身份仅在固定已接受报告/回执范围继承；30个R1独立输出不在本包，未重新核对或重跑。

准备脚本只进行一次候选检查和一次profile元数据绑定；指纹跨intent、共享marker和worker一致。占用仅由冻结worker发起一次。占用子进程PID75784在05:42:41.415218 UTC退出0，记录匹配数0及句柄关闭，之后才进入context/观测代码。验收未读取profile或重扫占用。

严格TLS和原方法/路径/WS/相关target守卫保持。唯一goto在北京时间2026-10-20 13:42:44产生Fetch与context两层GET audit，属于同一次导航。首次错误为 `ERR_CERT_COMMON_NAME_INVALID`，HTTP状态未记录，认证和LOGIN_REQUIRED均未建立。最终guard failure=null、pending_tasks=0、shutdown_started=true、stopped=true、terminal_stopped=false；登录、书籍源/目标读取、首题保存、刷新重开及内容/题框读回全部NOT_RUN。

产品PID75280及worker PID16076有同PID/创建FILETIME的保留句柄退出2证据，占用PID75784退出0。产品pipes/handle和worker handle关闭；固定源码支持worker管道关闭，Job活动数1到0后关闭，context/runtime关闭无错误。外层记录10391ms、worker监督记录9672ms且未超时；这些计时与OS进程寿命不同，不构成永久OS阻塞下的普遍硬保证。

wrapper PID31208仅有创建身份，确切OS退出身份为UNKNOWN。工具壳exit1与保留句柄产品exit2分别保留；源码预期wrapper返回2不能替代实测退出证明。接受范围只覆盖上述自有句柄、Job和context/runtime，不宣称整个壳或会话所有进程均退出。

六个live JSON固定副本与清单一致；共享.local原件相等及marker保留依据调度固定核证，本验收未读原件。封装失败事件和原seal源码保全，最终seal只新增UTF-8声明；未重现封装失败或执行封装脚本。原产品stdout文本被扣留，仅有长度和摘要。

验收只进行文件、JSON、AST和摘要静态工作：0产品导入或运行、0wrapper/旧suite、0浏览器/平台/占用/进程查询、0profile凭据读取、0登录/业务/外部消息，83输入不改。报告生成曾在functions.exec编排层语法拒绝，发生在任何嵌套工具调用或写文件之前；仅修正报告生成代码。

只新增report.json、report.md、raw-output-manifest.json。live已耗1、剩余0；旧额度不恢复。其他三例HOLD，Q22不重放，0B消息。验收已释放停止，无补测、重试、修补或业务后继授权。
