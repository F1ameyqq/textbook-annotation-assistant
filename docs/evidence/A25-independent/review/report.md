# A25 首份冻结交付：正式有限独立结论

代码结论：`ACCEPTED_OFFLINE_ONLY`。唯一实际只读轮结论：`ACCEPTED_FIXED_FAILURE_AND_OWN_RELEASE_ONLY`。五题当前来源、候选、审校、保存计划、真实保存、独立持久化读回和导出全部 `NOT_RUN`；本报告不激活任何新 live。

验收对话 `01a166e8-3f23-7192-a560-4724adca74b1`（登记 `gpt-6.1-sol / xhigh`）；协调者 `01a166c5-f93f-76e3-baf4-a3545ccddebd`；执行者 `01a166e7-cfd7-7da2-a76e-bcb612b9646b`。继续原 A25 标准，不另开诊断阶段。

## 冻结范围和原字节

基线 `ee463c800bef1ec5010ee5950662b9726d474e42`，产品 `b551dceadb052efad2e7e47216ec62896213ee40`，最终交付 `b74e9865d0e77bab304f0e91fb0c5e839ae56079`。交付 raw 清单 SHA256 `558dddbdf859374095cd9b1d56c889bc0e88e5d9c3cef3544513f401a2b9438c`。

独立从确切 Git blob 导出并核验 27 份源码：大小、SHA256、Git blob ID、作者冻结 bytes 及最终提交 bytes 全部一致。另复制并核对 3 份外部输入、47 份冻结私有原件和 3 份最终报告。原件隔离于 `D:/1800/.local/stages/a25-independent-20261023/review-initial-20261023/`；未读作者活动工作树。完整输入和 64 条 Git 只读命令及原 stdout/stderr 见 `intake.json`。每条 Git 均设置 `GIT_NO_LAZY_FETCH=1`、`-c core.longpaths=true`，未 fetch/add/commit/push。

基线到最终提交的 diff 无删除；已有文件只改批入口和 `docs/status/a.md`，其他修改均为本轮新增文件。writer、update、revision、capture、core/TLS 及其余旧包实现未改。产品到最终提交只新增报告/原输出/清单。没有改变旧第一课时成功、旧 UNKNOWN 或历史 evidence。

## 有限代码检查

以下命令使用原字节无 `.git` 导出、独立工作目录、Python 3.9，以及验收侧 socket/非 Python 进程/实际 capture/login/writer 子命令限制器。所有输入均为合成数据与新建临时 profile 目录；没有真实浏览器、网络、profile、OCR 或模型操作。命令完整 argv、时间、exit、stdout/stderr 原 bytes 及 SHA256 见 `test-commands.json`、`resumed-test-commands.json`、`controls-v2-process.json`。

| 执行 | 原始结果 | 解释及后继 |
| --- | --- | --- |
| 最终新增 `test_a25_batch.py -f` | 16 项中 15 PASS，1 ERROR；exit1；21.177s | 最后一项便携子进程被验收 guard 误挡；后续独立控制未运行 |
| 仅 `PortableEntryA25Tests -f` | 1/1 PASS；exit0；1.300s | 只修验收 guard 的 Windows 审计参数解析；未重跑前 15 项 |
| 独立控制初版 | 第一项 FAIL；exit1；1.042s；其余 7 项 NOT_RUN | 验收夹具给三个 actor 相同值，产品正确拒绝 `CURRENT_ACTORS_REQUIRED` |
| 独立控制 v2 | 8/8 PASS；exit0；20.095s | 只将夹具 actor 改为三个不同的合成值；原控制文件及失败原输出保留 |

因此最终新增文件的 16 个不同测试均取得通过证据，另有 8 个独立控制通过。没有把两次验收工具/夹具错误抹除，也不把 26 次执行称作 26 个独立通过。第一处限制器修正保留原 `sitecustomize.py`，新版单独保存在 `guard-windows-argv/`；第二处夹具修正保留 `controls.py`，新版为 `controls-v2.py`。未修改产品、计划、pins、expected 值或现有 ledger 来使测试通过。

实际独立控制补充验证了：

- 真实便携 configure 从其他 cwd、存在同名冲突包时成功，使用五题/两来源页，创建配置但不创建 runtime/claim；不靠 mock import。
- 候选与目标同时改成错误实际父目录仍拒绝；只更新 candidate 内的 source 摘要不能绕过清单的审校摘要绑定。
- no-op 为 0 发送，但仍逐题走新 reader，不创建已发送 accepted marker。
- 读回内容不符、reader 与 writer 同 PID、writer 释放未证均停止，并阻止后继或 accepted 标记。
- 第一个目标成功后，后继稳定身份出现新 UNKNOWN，已成功结果保留，后续 writer 不启动，不清 ledger、不重发。

作者原件也按原范围核对：初版新增 14/14、第二版 15/15、受影响 11/11、最终差量 3/3；这些有重叠且属于不同作者修订，不相加当作最终独立覆盖量。旧 194 项、旧第一课时和 OCR 没有重跑。作者末次 AST 子进程 exit0 和其后外层哈希脚本 AssertionError 分别保留；缺失的外层 traceback 原 bytes 未补造。

## 原标准逐项结论

| 标准 | 此次已验证层 | 未证明层 |
| --- | --- | --- |
| I01 | 固定 bytes、diff 范围、输入隔离 PASS | 作者活动目录未读取 |
| I02 | 真实子进程 help/configure、同名包干扰、其他 cwd PASS | 实际浏览器未启动 |
| I03/I04 | 合成重排、稳定 ID、info/实际父目录、旧题序拒绝 PASS | 当前五个真实 stable ID、当前 18—22 映射未取得 |
| I05 | 候选/来源/审校/清单摘要闭包和变更拒绝 PASS | 真实来源页、正文/答案/图形审校 NOT_RUN |
| I06/I07 | 第五题缺件在首 child 前拒绝、重复 node/info/order 拒绝 PASS | 真实整批候选尚不存在 |
| I08 | 未决稳定身份 intent、前序引用摘要、pending ledger 变更拒绝 PASS | 深层已接受前序成功链本次未新增重跑；revision 实现与 B 基线字节相同 |
| I09/I10 | 生成后计划变更拒绝、一次发送/UNKNOWN 停止、no-op PASS | 真实发送未运行；底层 writer 未改 |
| I11/I12 | writer 后 reader 的串行消费、PID/时间比较、读回失败/释放失败/后继 NOT_RUN PASS | 真实写后新进程持久化读回未运行 |
| I13 | 原生完整比较器、目录/全框/未修改区保全路径保持，合成比较 PASS | 原 17 题真实内容保全及五题真实导出 NOT_RUN，不能以数量相等代替 |
| I14 | 本轮固定失败/精确自有释放有限接受 | 当前来源、根因、认证及新 live 准入均未证明 |

未发现本轮包入口/批清单新增实现需要阻挡离线接受的代码问题。该结论仅适用于上述有限代码边界，不能替代本轮实源候选和具体保存计划的验收。

## 唯一只读实际及释放

配置 SHA256 `8e25a3b8bbd5ae0e54441dd32733bf12a5aa45d4ba1517d8982342f18b8b6c75`，包实现 SHA256 `31f268add44773ec35b939644d5fefff98a646a4e6d7687164f2c2ff8e200cc8`。独立重算包摘要与配置、launch 记录一致；私有预算启动前从 0 记为 1，launch 为 attempt1/spent1/remaining0、retry=false、写入授权 0。配置含 41 条 GET 规则、static disabled，窗口不超 900 秒；本轮实际在窗口内。

2026-10-23 12:07:04—12:07:05（Asia/Shanghai），持有 Python 进程 exit2，stdout 原 bytes 与 `capture-summary.json` 相等；stderr 原 bytes 为 0。摘要为 `CAPTURE_FAILED_NO_RETRY / SSLEOFError / CAPTURE_ERROR`，`captures={}`、save_attempts=0，网络审计原件 `[]`。完整异常文本和 traceback 未保留，根因继续 `UNKNOWN`；没有当前证书内容、服务端或代理/DNS 原因结论。

原摘要 `release:null` 保持原样。单独 `release.json` 的配置摘要正确，记录 context_closed/runtime_stopped=true、pending_callbacks=0、errors=[]、context_runtime_release_confirmed=true；它不能被改写成摘要原来已有 release。静态调用顺序是在启动 Playwright runtime 前执行精确证书 TLS 前置函数；该前置失败对应此次没有创建 runtime/context，单独 release 在这条路径是未创建资源的收口，不宣称关闭过一个实际浏览器。

外层固定 Windows Job 记录显示进程恢复前已入 Job，持有 Python PID 24672、conhost PID 50132 的 creation FILETIME、镜像和句柄；两者已 signaled，Job 活动进程 0，进程/线程/Job 句柄关闭、errors=[]。profile 前后观察的匹配 Edge 与锁名均为空。这里只接受所持两个身份和 Job 的释放；不把未观察的瞬时进程或外层监督者自身作为已持有并关闭的身份。

执行前固定包与最终包内 Python/capture 入口全部字节相同；唯有未被此次 capture 消费的批工具在 live 结束后改动，与作者报告相符。独立静态核证脚本 exit0，结果见 `actual-review.json`；没有重放 TLS、浏览器或请求。

## 阻挡继续取源和写入的具体缺口

1. 当前只读轮已耗尽，旧配置/claim/output/launch 不可重开。下一次实际取源须由协调者在同一 A25 中绑定新的明确轮次、配置、预算和执行边界；本报告不恢复旧预算，也不推定 SSLEOFError 已修复。
2. 本轮业务响应为 0，五个真实 node/info ID、实际父目录、完整当前原生基线、来源页 12/173 原图及对应审校材料都缺失。B 旧报告或合成测试不能填补这些当前材料；没有它们不能冻结真实五题清单。
3. 写入前还须提交本轮实源绑定的候选、完整来源/审校哈希、现有 ledger 与必要前序修订原件，以及具体五题计划供同一独立对话继续审核。原 17 题保全需要明确比较对象；当前无真实写后保全或导出证据。
4. 本轮记录未证明新的平台/认证状态。只读 TLS 许可不代替具体写入条件；不能新登录、读凭据配置、切 profile、清锁、扩 origin、迁移目录或书级送审来填补缺口。原未知保存分支也不能通过换清单或输出目录重发。

这些是当前执行依赖与证据缺口，没有把网络未知原因包装成代码修复结论。真实保存、独立读回和导出必须继续保持 `NOT_RUN`，直到新的实际证据和具体计划被接续。

## 交付和权限边界

新增报告、脚本、清单在本 review 子目录；原准备交付保持原字节。`result.json` 给出机器状态，`review-files.sha256` 固定公开交付。私有 raw 和独立运行输出索引见 `review-raw-manifest.json`。独立工作未改作者、根 JSON/AGENTS、旧原件、现有 profile 或根共享暂存区，未向其他对话/B 发消息，未创建子智能体/聊天。由协调者选择收录本固定报告。
