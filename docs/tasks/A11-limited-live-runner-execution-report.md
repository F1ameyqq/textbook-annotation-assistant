# A11 执行交付：REVIEW

2026-10-19。作者独立分支 `codex/a11-live-pilot-core`，工作目录 `D:/1800-worktrees/a11-live-pilot`。固定调度工作流/父基线 `87f55ff636e463053f0b3c3ec97b0692511a06d0`，任务指定产品背景 `404199fbbd7ef97b5837ba3d0555e91e5175e1cd`。本报告不声明接受、集成、发布、平台资格或 B 采用。

最终运行产品为第二最终候选 **`ea5b62fd593041c29c00831ddb0eb453b0230307`**。此后只新增报告与原始执行证据，产品/测试/fixture 不再修改，不再运行验证。最终证据提交由本次交付消息给出，不能自引用自身提交号。

## 实际实现

- 新增 quality 输入/目标/保全/严格内容检查，公共 C01 验证源文件字节、原图尺寸和引用闭包；独立从权威普通选项规则核六框 Q/W/W/W/W/A，陈旧 Q 选项即使合法重封也拒绝。
- 每题一个 C01 ApplyPlan 和运行结果；使用完整全书最大题序追加，固定保存前完整基线；先算单题计划，再取新 prewrite 核对全书状态。局部 max=2、全书 max=9 的新 fixture 计划从10开始。
- journal 使用固定书级宿主机锁，事件/锚点/intent/claim 独占创建和 fsync。持久 intent 在发送占用之前；同内容文件不会恢复许可。已有批次或 intent/claim 的重启不重发；首失败或 UNKNOWN 后继 NOT_RUN。
- transport 协议明确；测试 fake 将命令转换为磁盘后端矩形/文本，读回再独立从磁盘解码，不返回计划 expected_after。get/refresh/reopen 分别留证，重开要求新 session 及前 session 释放链；旧框、题序、目录和文字保全。
- `inspect-input / prepare / apply / reconcile-readonly / report` 五个本地 CLI 入口。真实 apply/reconcile 明确 BLOCKED；无 force/assume 开关。真实 UsenseTransport 未实现/未验证的文本、上传和读回能力全部关闭，构造/import 不创建浏览器或连接。

运行方式及输入字段见 [runbook](../live-pilot-runbook.md)。真实清单最多5题的准入代码已具备；当前正例只证明本次两个新合成题，未使用真实Q1/Q4/Q22或任何旧成功场景。

## 固定候选和实际 suite

冻结前只做 AST 语法、静态差异及 fixture model seal，没有提前运行 suite 或旧业务。固定 [case 清单](../evidence/A11/execution/suite-catalog.json) 为17个 test method，各方法内的有限变体和预期已预先写入清单；[fixture 清单](../evidence/A11/execution/fixture-manifest.json) 为6成员，所有数据标记 `A11_SYNTHETIC_OFFLINE_ONLY`。

| 候选 | 固定提交 | 唯一实际结果 |
|---|---|---|
| 1 | `f5e3d63e6e31a87eb2b45789dbebadf89b4ac81e` | 6 PASS，第7 ERROR=`CHECK_SUBJECT`，10 NOT_RUN。fail-fast 后停止。 |
| 2 | `ea5b62fd593041c29c00831ddb0eb453b0230307` | 同一17项 17 PASS，25.121秒，0 failures / 0 errors。 |

唯一产品纠正是 TARGET CheckReport.subject 从 graph ref 改为 snapshot ref，遵守既有 C01，而非放宽 C01。详见 [纠正范围](../evidence/A11/execution/candidate-2-correction.md)。首失败证据和提交保留；两次累计2尝试/1成功，作者额度耗尽。没有第三候选、成功后补跑或旧额度复用。

实际命令（第二次）为：

```powershell
$env:GIT_NO_LAZY_FETCH = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONDONTWRITEBYTECODE = '1'
python docs/evidence/A11/execution/run-suite.py docs/evidence/A11/execution/attempt-2
```

驱动只加载清单中三个新文件，fail-fast，未运行项写 NOT_RUN。冻结产品目录和 `src` 的 raw 字节为实际执行字节。实际结果：[第一次](../evidence/A11/execution/attempt-1/result.json)、[第二次](../evidence/A11/execution/attempt-2/result.json)、[第二次日志](../evidence/A11/execution/attempt-2/suite.log)。独立验收不得把作者 PASS 当独立通过。

T5 五个崩溃点产生自有子进程退出73；新进程全部被 BOOK_ALREADY_STARTED 拒绝，发送计数分别0/0/0/1/1。双进程同书竞争只有一个 claim，0 send。重封旧Q策略、目录局部max、计划来源伪读回、缺证据/旧版本能力、HTTP200、响应丢失、部分框、GET失败、文字/符号/答案/选项顺序、旧状态篡改、释放异常和禁止操作均按固定范围检查。

第二 suite 共有26个保留的假后端目录、22次假发送调用；这些是固定故障案例的合成副作用，**真实平台发送0次**。正常两题分别追加10/11，六次 get/refresh/reopen 读回。对账 MATCH/ABSENT/CONFLICT 保留原 UNKNOWN 结果，均0 resend，不恢复后继。

## 原字节与释放

固定父基线29,968条旧路径的 mode/type/blob 全保留；只新增白名单路径，未 stage 或提交旧源码、根依赖、pins、A05脚本、主调度JSON或旧证据。独立目录中的旧源码已 raw 导出用于运行；由于仓库换行属性，部分 Git worktree 状态可显示 M，但逐文件读取与固定 Git blob 完全相同，不为清洁状态改写主线或旧材料。

[首冻结清单](../evidence/A11/execution/candidate-1-manifest.json)、[第二冻结清单](../evidence/A11/execution/candidate-2-manifest.json)、[完整基线成员](../evidence/A11/execution/baseline-raw-members.json) 和最终 delivery raw 清单供独立隔离导出。运行产品及fixture文件必须取 Git blob 原bytes，避免 checkout CRLF/LF 改变摘要。

12个跨进程 worker 的 PID 创建/退出已保留，退出结果为预期73/2，均已退出；[只读PID复核](../evidence/A11/execution/owned-process-readback.json) 当前匹配活进程为空。5个 CLI subprocess.run 均已返回，退出码在 suite 检查，stdout保留；其PID未单独记载。没有终止别人的进程、删除旧锁、创建浏览器/profile或访问凭据。崩溃案例磁盘 fake_session_closed=false 是刻意保留的合成故障记录，不是活浏览器。完整释放与假发送计数见 [release summary](../evidence/A11/execution/release-and-runtime-summary.json)。

## 未闭合接口和诚实边界

1. 真实源/目标/执行政策及新业务清单未取得；生产 check_input 在真实事实注册表缺失处阻断。当前不会产生生产 READY。
2. Usense 文本/公式wire、W/choice字段、上传签名/裁片绑定、当前业务回执和内容GET/刷新/重开codec均未接通。历史A05 decoder仅给 CONTENT_PENDING，不能证明文字保存。
3. 当前一次发送只证明使用同宿主固定锁与账本协议的受控进程；不是平台 exactly-once，也不证明另一机器、人工或远端排他。生产接口仍关闭。
4. intent 内记录 `code_version=a11-offline-core-1`，确切运行commit/原bytes由外部冻结清单绑定；intent本身尚未内嵌运行Git commit或源码SHA。该边界不能被称为 intent 已自证确切代码身份。
5. C01公共校验用于输入和每题ApplyPlan。运行结果为A11自有不可覆盖日志记录，尚未输出真实 C01 PLATFORM_OBSERVED ExecutionReceipt；真实收口接口仍待明确取证后接入。
6. 文本只做严格比较，未引入宽松规范化、公式编码或真实内容真值。离线 origin/session/source_ref 是受控假后端证据，不能当真实平台来源鉴别。

本轮0平台/网络/浏览器/profile/模型/依赖安装/B脚本/SQLite/业务写入/推送/B消息/送审/送交。旧任务和Q1/Q4成功额度未恢复。作者状态 **REVIEW**；独立待调度另派，真实试用仍 BLOCKED，最终 `NOT_SUBMITTED`。
