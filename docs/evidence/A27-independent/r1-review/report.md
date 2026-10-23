# A27 R1 独立复验及总范围有限结论

结论：`ACCEPTED_OFFLINE_ONLY`。接受新候选 `ebca4c71a70bdfb5fbccc023d00e0207ae532470` 在本任务内的有限离线实现；原 R1 profile 等价路径阻断解除。范围合并首轮已完成且代码未变的有限键序批处理、协作式有界关闭/CLI 退出、成功回执后的单次只读恢复证据链，以及本轮修正的 profile 目录身份门禁。新代码真实平台、真实 Edge 进程枚举和真实恢复仍为 `NOT_RUN`；本结论不授予 live 权限，不影响 A26 已完成交付。

只从根指定 R1 root-fixed-delivery 接收，index SHA256 为 `540efe4e335bbf18bbe891b96d3a9e3f244c0d6d40f54df2a09c7afc14766ae6`，原交付 manifest 为 `1aaa90ff70d6cdb788c174d3dbc683f90310e0e656defed341376335bbc57c50`。72 交付成员、34 Git raw 依赖及 index/receipt/manifest 共 109 份源件/独立副本一致；34 份源码逐原 blob 身份核验。相对首轮只有四条差异路径，其中产品代码只改 `tools/run_usense_postsave_readback.py`；其余是新 R1 测试、说明与状态文档。30 个先前依赖字节相同。原首轮 147 份源件/副本、正式报告、原 witness 及原失败均保全。

R1 现在由 `CommandLineToArgvW` 解析 Windows 引号和参数，再提取 user-data-dir，以目录 `st_dev/st_ino` 比较身份；解析缓冲区调用 LocalFree 释放。空/重复/相对/缺失或不可读取目录参数保守拒绝；显式 UNC、扩展 UNC 和相对形式在 stat 前拒绝。前后两次观察保留。实际恢复入口 execute、preflight、prepare_request、main 等七个既有函数 AST 原样保持；只修改 exclusive_profile，并新增两个解析/身份 helper。没有新增 sender、重试或 ledger 写入路径。

原阻断控制 I07 只替换候选源码定位，测试逻辑原样重跑：Windows samefile 仍证实规范路径与 `parent\.\profile` 是同一目录；首次观察现抛出 `RECOVERY_PROFILE_IN_USE`，configure/capture=0、输出未创建、spent=0。原失败 witness SHA256 `616fd5b65ed843a4446bd0651696281c9d766cccebccd5bb273f8eaf22fe5824` 亦按原字节核对，其原进程返回行和原合成目录在新 observer 下被精确拒绝。旧 witness 中的两次 matched0/configure+capture/旧成功状态没有改写。

本轮在独立冻结副本执行新增 8 项全部 PASS（0.612 秒），包括等价目录写法、带空格的引号参数、重复/未知参数、第一次/第二次门禁、不同目录、空 OS 查询和不可读命令行。另有 4 项独立控制通过：原 I07；精确原 witness 返回行；五个非本地/相对形式在 stat 前拒绝；同前缀但不同目录的真实恢复入口正常只读、两个观察均完成、完整 ledger 不变、零标准 marker、一次消费后重复分派被拒绝。这里的真实入口指执行产品函数，OS 查询及 capture 均为替身；Windows 参数解析与合成目录元数据读取实际运行，没有 Edge 或平台。

作者受影响 2/2 的原命令/退出码/原输出已核字节并读取，本独立未再重复。首轮新增 20 PASS、独立 I01–I06 共 6 PASS 及 51 份固定 A25 原件回放证据，依未变源码和本轮静态差量核证继续有效，未重跑旧 20/9/194。首轮 I07 FAIL 只作为旧版本历史保留，不能被新版本 PASS 覆盖。首轮独立辅助审计 ERROR、作者首轮四份失败、R1 的基线复现 FAIL 和一次引号夹具 FAIL 均按原输出保持；本 R1 独立没有新失败或辅助错误。

本 A27 总范围的可接受事实：正常批处理优先 strict，仅对新建 question/answer 直接 data 的精确三字段键序作有限回退，完整值/类型/数组/其他快照仍受保护；有限成功有独立 status，不创建标准 accepted marker。writer 保留原业务状态、关闭失败和 OS 释放的分层；15/5/15 秒协作式阶段限制及独立 writer CLI 不进入无限取消 join 已有离线证据。同步阻塞或底层线程仍需既有外层监管，框架失败不能由 OS 退出覆写。恢复仍必须核同一 intent/计划/精确回执/guard/holder 完整释放、新 reader 身份/时间/全部原始响应及完整比较，只分派 configure/capture，失败不重发。

历史边界保持：A25 第三题原 strict FAIL、第四题原 context/runtime false 和两个 TimeoutError不变，根因 UNKNOWN；第 3/4 题无标准 accepted marker，两个新证据类型均不能成为旧 revision 前驱。`revision.py`、writer、release、postsave、update 和 batch 业务代码本 R1 未变。五题既有保存/独立读回没有重做，也没有将旧账本失败升级为标准成功。新结果不会恢复旧额度。

固定机器结果、来源/原件清单、静态 AST 差量、每次测试命令/解释器摘要/退出码/原 stdout/stderr 及新合成 witness 已落本目录和独立私有目录，统一列入哈希清单；清单自身摘要单列。正式审阅完成并释放，无常驻浏览器/runtime/profile。未访问作者活动工作区、真实 profile/ledger 或真实进程列表，未更改根 state/AGENTS、作者产品、Git 或自动化，未向其他聊天发消息。1800-a 按任务保持 PAUSED，本独立未重新读取其实时配置。
