# A15 唯一 live 固定结果正式独立核证

结论：`ACCEPTED_FAILURE_ARCHIVE_AND_EVIDENCED_OWNED_RELEASE_ONLY`。只接受本次固定失败归档、实际有界范围与已证自有释放；认证、LOGIN_REQUIRED、书籍、保存及根因均未证明。本对话只读核证完成后停止 REVIEW，0 新 suite/live，A15 live 1/1 已耗尽、剩余 0。

正式独立对话 `01a157fe-5cc9-7d91-8bbe-73b376cbe2a5`；调度 `01a15768-1e2d-7781-b29f-1f7376270216`。固定作者 final `49e5ab4e804e0f35b665a61bd63343184eda0fdb`；产品 `bef0204541eedd86e1fab849e8002a83f432cd7b` 未变；候选清单 `78382e0b484ad46ab497217683fa3022440a1f570589f538c3d355670d552652`。本次仅读隔离输入及调度指定固定预检，未读作者活动目录、实际 local 输出、profile 或进程。

## 固定 raw 与授权

交付清单 SHA256 `bcbfd3d043276c3cf580c1b1ba7b903d25e052e8ece8142416a06d2d6a458c51` 匹配。73 个成员及清单本身共 74 raw 与 final Git blob 一致；前一 final `7432122b9fd5602785ebfb2b3f24e407fdf76eda` 的 31,259 个旧成员 mode/type/blob 保全，仅新增 27，全部在本轮 live 归档子树。22 个候选成员未改；原离线独立报告、差量和静态封存的 27 成员及清单仍原 bytes 保全。

激活 raw SHA256 `45d418b27b55f5b3230ec431fbbe74d5ce99064440f6d35005cd72876135d3b2` 匹配。独立按权威用户决定/任务核字段，而非采用作者结果作为准入标准：任务、workflow、用户决定、提案、候选、调度 ID、run_id、目标、专用 profile 非敏感指纹、新输出、证书例外及 1 context/1 导航/0 登录提交/0 业务额度均绑定；实际独立离线报告 SHA `a26530da782df64e29afce5f0749ec54e62f991926487fed70b28603c8fd94f9` 与此前本对话封存原件相同。

激活窗口为北京时间 2026-10-20 **15:16:59.690400 至 15:31:59.690400**；原始命令时间为 **15:23:34.7899566 至 15:23:41.9208206**，完整调用在窗口内，总 7.130864 秒。独立使用精确 100ns 整数解析原 UTC，包括 PowerShell 七位小数，没有修改、截断或重写原始时间；原 UTC、整数计算与命令/标记逐项核对见 `fixed-record-audit.json`。

## 真实结果及范围

固定命令为已批准 launcher 一次调用，退出码 2、stderr 0 bytes。记录一个 context 创建、一个 navigation intent、四个本轮绑定的独占阶段标记。profile 指纹由产品在激活后重核并匹配；唯一实际占用检查的固定记录为零匹配、退出码 0、无超时。独立未重新读取 profile 或执行占用检查。固定代码保全及记录相互支持本次范围；不外推为对所有机器进程或书籍状态的观察。

第一条 policy 拒绝为北京时间 **15:23:41.371345，ORIGIN_BLOCKED / GET / FETCH_REQUEST_STAGE**。终态为 `ERROR / NETWORK_GUARD_STOPPED`，observation_error 一致；guard_failure 为 null，不能将策略拒绝改述为另一个底层异常。关闭前和最终序列化时 terminal_stopped 均 true、pending_tasks 均 0，successors=`NOT_RUN`；没有将已停止 guard 的 DOM 状态记成成功。

8 条 audit 是事件，分类为 NAVIGATION×2、STATIC×2、ORIGIN_BLOCKED×1、STOPPED×3，记录的方法均 GET。两条 NAVIGATION 分别来自 FETCH_REQUEST_STAGE 和 CONTEXT_FIRST_REQUEST，与同一次导航的双守卫观察相符，不能计为第二次导航；也不能把 8 条事件计为 8 个唯一请求。所有记录的 redirect_hop 为 false，仅说明本归档所列事件。

冻结 audit 没有 URL、域名、resource type 或请求唯一 ID。因此被阻断的 URL/域名/资源类型、具体请求关联及根因均为 `UNKNOWN_NOT_RECORDED`；未补取 trace、访问站点、调整允许列表或重试。证书例外仅表示本次已批准 context 的运行配置，不证明服务端身份，也不证明此前证书缺陷已修复。

## 已证自有释放与时间边界

没有仅凭 RELEASED 文本或关句柄接受释放。独立逐项核对保留句柄的 before/after PID 与创建 FILETIME 相等，after 有 OS exit_observed、退出 FILETIME 及退出码；其生命周期均在本次调用原始时间内。

| 自有 Popen 角色 | PID | 退出码 | OS 生命周期（毫秒） |
| --- | --- | --- | --- |
| product | 10832 | 2 | 6464.3639 |
| worker | 79292 | 2 | 5997.8282 |
| occupancy | 76068 | 0 | 575.8190 |

三个对应句柄均记录关闭。两个自有 Job 均已分配、最终活动数 0 且关闭；最终清理前各有一个活动成员，固定源码该分支只终止各自 owned Job。归档没有这些剩余成员的个体身份，不猜测其角色，也不把 Job 为零扩大成全系统无浏览器进程。context.close 和 runtime.stop 均完成、无 release errors；最终 guard pending_tasks=0。

launcher 本地单调时钟报告 6531ms，产品监督 worker 报告 6031ms；各自的 90 秒总限/75 秒 worker 限与产品 85 秒截止无 exceeded 标记。本轮实际占用记录无 4 秒超时，观察记录导航限 45 秒，整个观察记录跨度 4.876916 秒。这里只接受本轮完成时间和固定源码使用各进程自身时基的事实，不把一次快速失败当作通用截止守卫或所有超时路径的验证；A14-TIMING-01 通用结论仍不接受。

launcher 自身没有外部保留 OS 身份，继续 `UNKNOWN`。命令的 native 退出码 2 不代替缺失的自身创建/退出身份。shell/报表进程身份未测量，A13 wrapper UNKNOWN 也未改写。

## 报表错误与保全

原报告 helper 因 Python 3.9 无法解析 PowerShell 七位小数 UTC 而退出 1；原 helper SHA `8fe0808eec6e223d5dea23cb1a468fdcaf34ed3f0f81a40577a025d223d3bf14`、错误事件和原命令时间都保全。静态比较新 helper 仅添加六位比较/完整下一微秒窗口检查及报表说明，未改变产品、启动代码或冻结现场；差异见 `report-helper-only.diff`。本次另用整数精度独立核原始时间，不执行任一 helper。固定记录中的 live 调用仍只有 1；此报表修正不是第二次 live，也不恢复额度。

10 个归档 live JSON 的摘要及 size 与 source-capture 清单一致，并与固定 Git blob 一致。独立未回读实际 `.local` 源；“作者复制前后源相等”仅保留为固定 capture 回执，不冒称本次刷新观察。输入和旧独立输出的末次保全见 `input-preservation.json`。

## 接受边界及停止状态

接受本轮失败及以上三项自有子进程身份/退出、两个 Job 计数、context/runtime 关闭的固定证据。AUTHENTICATED_VIEWER 和 LOGIN_REQUIRED 均未证明；完整书籍读取、首题保存及刷新重开读回未执行。固定产品只允许限定只读策略，登录提交和业务写入记录为 0，不扩张成平台业务通过。

本次独立仅运行自编标准库只读核档工具及 3 个固定 Git 读取命令，各 Git 命令先设 `GIT_NO_LAZY_FETCH=1` 并带 `-c core.longpaths=true`；无产品 import、suite、browser、network、native API、profile、实际进程/占用动作或其他聊天消息。分析解释器/Git 是同步准备进程，不声称整个准备过程零进程。静态报告、清单和释放均只新增在本目录，原预检封存未覆盖。

本对话停止 REVIEW。A15 live 1/1 耗尽，不补跑；首题保存读回仍 NOT_RUN，其他三例 HOLD、Q22 不重放，0 B 消息/书级送审送交。A16 准备与本次验收分开，本对话未处理或派发 A16。
