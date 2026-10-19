# A10 首次平台只读前检：执行失败收口

2026-10-19。结果：`FAILED_STOPPED_BEFORE_PLATFORM`。这是一次已消耗启动标记的前检尝试，首个实际占用检查失败；平台访问轮数为 0。未修后重跑、未再次启动。本报告交付独立审查，不自称验收通过或真实写入就绪。

## 固定输入与范围

- 工作流：`6dcea351b4be4608d4d2a185a4721b4daf6ba286`。
- [任务单](A10-platform-readiness-preflight.md)、[明确授权](../approvals/A10-platform-readonly-approval.json)：仅书 `46007447`，最多一轮、首次平台操作起 15 分钟，首个意外失败后停止。
- 唯一执行者：`/root/a10_platform_preflight`；启动前核对调度 JSON 的执行者和 profile 预约者一致。调度者与审查者没有被要求并行访问平台。
- 冻结工具来源：A04 `6c8137a4fadddc01a47906d564ab3460277c8958`；31 个 `src` 文件由 `git cat-file blob` 原字节导出至本地忽略目录 `.local/stages/a10-preflight/frozen/`，不修改旧工作树、src、pins、依赖或旧证据。它们只是本次前检依赖，不代表整个 A04 已通过或集成。
- [窄驱动](../evidence/A10/execution/preflight.py)复用原有 `HeadlessSession`、`ProfileLease` 和业务 GET/来源观察函数；既有登录辅助程序原字节与工作流 Git blob 一致。新文件只在本任务证据目录和本地 stage。
- 现有固定请求守卫支持 viewer14、15、173。本轮选取这三页；viewer10 标为未选择，未扩大或修改守卫。未运行旧正常业务、旧 CLI 或任何旧验收矩阵。
- TLS 校验保持开启；配置 `ignore_https_errors=False`。凭据由原登录辅助代码负责，但本轮在其调用前停止，未读取凭据、填写或提交登录。

## 离线准备与实际时序

[静态准备](../evidence/A10/execution/static-preparation.json)记录语法解析和离线依赖导入通过，0 浏览器、0 平台操作。Python 3.9.13、Playwright 1.58.0、Pillow 11.3.0、Pydantic 2.12.5；没有安装依赖。

[输入原字节清单](../evidence/A10/execution/input-raw-manifest.json)在启动前冻结：31 个 A04 原始源文件、工作流输入、当前登录辅助程序、驱动和已导入运行库的路径、版本/来源及 SHA-256。驱动 SHA-256 为 `7b0fdb26990a9d05d67bda40d72c4fa6516d5aa1a07b73bd89d9d405a9581456`；输入清单 SHA-256 为 `9b1879b2a32eee8b8bbab9389bf10fc3a92355af1fdc5df1506a1fc607df4805`。

| 事件 | UTC 时间 / 结果 |
|---|---|
| 排他性启动标记创建 | `2026-10-19T13:24:40.228037+00:00` |
| 首个占用检查失败并停止 | `2026-10-19T13:25:01.575754+00:00` |
| 首次平台操作 | 未发生；`live_started_at=null` |
| 平台结束时间 | 不适用；`live_ended_at=null` |
| 平台计时 / 轮数 | 0 秒 / 0 轮 |
| 前检启动标记 / 自动重试 | 1 / 0 |
| 收口进程观察 | `2026-10-19T13:26:05.6867936+00:00` |

[启动标记](../evidence/A10/execution/run-once-marker.json)以新建模式落盘；同一路径不会被覆盖。此失败后不得自行删除标记、补驱动并再启动。历史 A04/A07/A08/A09 的额度没有恢复。

## 逐项结果

| 步骤 | 结果 | 实际证据 |
|---|---|---|
| 独立 profile 进程/锁检查 | FAIL | 既有 `ProfileLease._snapshot()` 调用进程检查时返回 `PROCESS_CHECK_FAILED`，stage=`process_check`；未得到可用的占用/锁快照 |
| 必要登录与受保护界面确认 | NOT_RUN | 未创建浏览器、未调用会话进入入口、未读取凭据 |
| 目标书籍确认 | NOT_RUN | 无当前书籍数据 |
| 当前目录 | NOT_RUN | 无当前目录读回 |
| 当前题框 | NOT_RUN | 无当前题框读回；不引用历史 22 题/68 框作为现状 |
| 来源元数据 | NOT_RUN | 未读取 |
| viewer14 身份/原图/可见几何 | NOT_RUN | 未导航或下载 |
| viewer15 身份/原图/可见几何 | NOT_RUN | 未导航或下载 |
| viewer173 身份/原图/可见几何 | NOT_RUN | 未导航或下载 |
| viewer10 | NOT_SELECTED | 不在本次固定工具支持的三页集合内 |

[结果 JSON](../evidence/A10/execution/result.json)保留首个失败和所有后继 `NOT_RUN`。底层只返回固定脱敏错误，无法据此区分 CIM 超时、进程信息读取失败或其他本地检查异常；未重复运行该检查作诊断，也未连接网站测试 TLS。当前阻断是本地占用可观测性未得到证明，不能归因为平台登录、网络或证书失败。

## 审计与释放

[网络审计](../evidence/A10/execution/network-audit.json)为空数组。实际业务写入、画框、编辑、删除、OCR、保存、书级提交、Q22 重放、模型调用均为 0；未运行 B 脚本或访问其 SQLite，未安装依赖、推送或向外发送消息。没有原始 URL、请求体、凭据、cookie、token 或 profile 内容进入证据。

[会话收口](../evidence/A10/execution/session-release.json)显示未获得 context 和 profile 租约：`auth_mode=UNCONFIRMED`、`context_closed=false`、`lease.acquired=false`。这里的 `context_closed=false` 表示从未创建 context；`close_returned_success=true` 仅表示空资源收口调用返回成功，不证明 profile 空闲。

监督进程也在 CIM 元数据收集处失败，工具返回固定提示 `A10_LOCAL_PREPARATION_OR_SUPERVISOR_FAILED_NO_RAW_DETAILS`；因此 `worker-created.json`、`worker-ended.json` 与精确自有 PID/创建时间记录缺失。这是交付证据缺口，不补造 PID、不把它记为完整释放链通过。

停止后的[进程观察](../evidence/A10/execution/post-stop-process-observation.json)使用 `Get-Process` 的名称/创建时间读取，未读命令行或 profile：当时 Python/Pythonw 进程总数为 0，创建时间不可读数量为 0。本轮未创建浏览器或租约，没有终止任何进程、清理锁或触碰其他会话。该观察支持执行 Python 已结束；它不替代失败的 profile 排他性检查，也不声称 profile 当前空闲。

## 复现边界与交付

历史实际命令为 `python -B docs/evidence/A10/execution/preflight.py prepare`，冻结后执行一次 `python -B docs/evidence/A10/execution/preflight.py run`。两者均已执行；这不是新的重跑授权。审查只读取固定交付、重算 SHA 或解析源码，不启动 `run`/`worker`，不登录或读 profile。

[交付校验](../evidence/A10/execution/delivery-verification.json)记录冻结输入保持和脱敏证据结构检查；[输出原字节清单](../evidence/A10/execution/output-raw-manifest.json)覆盖本报告及本次证据。只提交新增 A10 文件；既有主线存在的未提交修改未恢复、清理或加入本次提交。

结论保持为首次本地前置检查失败，真实平台状态尚未观察。独立审查可审查本轮失败边界和现有释放证据，不能据此宣布 A04、真实几何或平台写入就绪。是否纠正本地可观测性并给予新的明确有界尝试，由调度依据此固定失败交付另行处理。
