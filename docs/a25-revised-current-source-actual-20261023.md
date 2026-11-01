# A25 修订版唯一当前源实际轮：固定失败与自有释放

本次为同一 A25、原执行及独立对话，在传输增量正式/根接受后由根明确激活的新轮。固定产品 `afc9d761294203e7cfb8086a82f1a7fdd8724372`、launch 版本 `fef3638d5793347a2b70f21108f6c03ee7856bbc`，authority ID `9a6bed2d-3025-4dec-b719-6c7762476134`。本页是实际结果作者交付，尚待本次实际结果的有限独立验收。

范围依题号更正分别记录：第二课时印刷 1—5、历史全局 17—21、拟 native 18—22；书46007447，viewer12/173，目录/全框/source及五题各7项，共40 JSON GET上限。原 profile、明确本地 HTTP proxy、原 leaf/SPKI、1探测/1context/1inert导航/900秒上限，0save/login/新origin/图像下载/OCR。

## 启动与原始失败

调度已预建空 configs/evidence/runs。最初两条准备 helper 因独占 mkdir 遇已存在目录而 exit1，尚未调用配置程序或启动实际轮。该首错已保留观察记录；原 helper stdout/stderr 未分别落盘，不冒充原 bytes。核实空目录后使用预建目录，所有新文件均独占创建；没有另开阶段或消费实际额度。

唯一实际 configure 成功，config SHA256 `e7db1b2469bc9fbb843f5e9b255f2282dc05f934853ce17d1646a361b05bf5d5`，implementation `5ddfe19c4cb0f2b98555c927a1d205f1165ab23ecac981896627445e29f3c2c8`。UTC窗口05:11:36.586767—05:26:36.586767，实际进程于2026-10-23 13:12:13—13:12:14（Asia/Shanghai）执行。启动前冻结 authority 原件、单次 launch、配置绑定及独占证据，原子记新轮 spent1/remaining0，再恢复已入 Windows Job 的子进程。

本轮返回 exit2 / `CAPTURE_FAILED_NO_RETRY`。原65-byte CONNECT请求及39-byte HTTP200响应均留存；探测随后在 `TLS_HANDSHAKE` 的 Python `ssl.py:do_handshake()` 抛出 `FileNotFoundError: [Errno 2] No such file or directory`。异常没有给出缺失文件名。TLS未返回leaf，未进入证书相等判断；具体网络/SSL/文件系统原因均 UNKNOWN，不能把异常类型当作已定位的文件缺失根因。

新 capture-error traceback 为1563 bytes、SHA256 `a28771d35996b3258453f59ceb979e65d1dd257fc27339886145d1a0686efcaf`；另保留 TLS probe/startup 原错误、阶段JSON及完整异常文本。stderr原件0 bytes，stdout原件1285 bytes。网络审计原件为 `[]`，业务响应0，浏览器context/runtime均未创建。

## 释放与后继

capture摘要已包含实际独立release：context/runtime释放true，created/started false，回调0，errors空。外层持有Python PID52748和conhost PID20684的creation FILETIME、镜像及句柄；均已signaled，Job活动进程0，process/thread/Job及两身份句柄均关闭。前后原profile匹配Edge进程及锁名均为0。此证据限本次持有身份与Job，不扩大为未观察进程证明。

首次实际异常后停止，未重试、换路、登录、改绑定实现或读profile内容。原初始EOF轮仍1/0，本次修订轮也1/0；未恢复剩余额度。历史原件、两个先前冻结包及其输入保持。

五题当前node/info/实际父目录和稳定ledger key均未取得；当前来源关系、候选审校、一次保存计划、账本初始化、保存、独立读回及导出全部逐项NOT_RUN。两张已准备的历史图仍为历史来源，不用它们补造当前身份/来源。本次条件“成功并释放后继续候选”未满足，不能提前初始化空账本或保存。

固定checkpoint为私有 `transport-revision/next-live/checkpoint-fixed-failure.json`，SHA256 `1b1a98a1a4ac1fa90e74d9dc79aec521531cda461106affe7424d8340e4ab22b`；已在执行对话评论报告供根及时收取。完整新授权/配置/launch、过程原件、持有进程释放和固定输入见本次raw清单。没有新增产品测试或产品修改，没有推送或联系其他对话；sole1800-a保持PAUSED，等待根按固定结果继续调度。

固定失败小包随后独占创建，`fixed-failure/manifest.json` SHA256为 `c8d748c684d239104c1ca48d360d7c8962a269774c76fe323cf48937c3abfdcf`，绑定34个原件和3个直接调用源码。原栈/运行库记录确认Python3.9.13、OpenSSL1.1.1n；`ssl.py`和`_ssl.pyd`原件也在小包。静态核对只发现TLS前已成功完成的两个原件文件open（请求/响应头），随后wrap_socket仅传socket及server_hostname，没有给它传文件路径。没有确证的本地缺失路径可修，未补建猜测文件、放宽TLS或修改异常名。

根随后允许只查本次目标的现有本机代理日志。本地监听元数据显示查询时127.0.0.1:7897由verge-mihomo.exe持有；这份晚于实际轮的观察不证明过去PID归属。仅检索13:11—13:13（Asia/Shanghai）/05:11—05:13 UTC和www.usense.com:443，从对应日期/覆盖时段日志中得到一条13:12:14的python.exe目标记录：`match GeoIP(cn) using DIRECT`。该行原bytes292、SHA256 `ffa8b8e0aac6a428fa1e868c856213b99c752ed3988f2c0cd655da0ee2b86604`。它与执行时间相容，但不含PID，实际probe没有记录本地端口，故时间关联不当作socket身份绑定。日志未给出TLS断链原因；只能证明该匹配记录选择DIRECT，不能证明代理已修复直连路径或证明远端中断根因。只提取/保留目标窗口匹配行，未复制整份日志或提取其他站点记录；未读取订阅/控制秘密，未新增网络或改规则/服务。
