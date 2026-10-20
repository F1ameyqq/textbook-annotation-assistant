# A13 唯一专用无头复用观测：BLOCKED，待独立静态核证

执行对话：`01a157d2-caed-7162-8c48-06ad7117bd90`。固定产品 `d45ed25a` / 最终交付 `81fab23e`，53 输入在启动前后 raw bytes、SHA256、size 及 Git blob 身份一致，未修改产品或旧证据。

北京时间 2026-10-20 13:42:39 发起唯一启动；约 10.391 秒后停止。原专用 profile 仅由执行准备调用一次元数据绑定，实际占用仅冻结 worker 内一次四秒有界扫描，确认 0。随后创建一次专用无头 context 并发出一次 annotateUnified 导航；首次返回 `ERR_CERT_COMMON_NAME_INVALID`，观察结果 `ERROR`。认证及 LOGIN_REQUIRED 均未建立，HTTP 状态未记录，根因 UNKNOWN。严格 TLS 保持，无证书忽略、重试、重载或后续诊断。

两条 GET/NAVIGATION audit 分别来自 Fetch 与 context 守卫，是同一次导航的两层事件。最终 guard failure=null、pending_tasks=0。0 登录填写或提交、0 书籍/源/框接口、0 业务写入、0 旧 suite/driver、0 新候选、0 B 或其他对话消息。所有后继读取、首题保存、刷新重开及题框读回均 NOT_RUN。

占用子进程 PID75784、worker PID16076、外层持有的产品 Popen PID75280 均有保留句柄的同 PID/创建 FILETIME 与退出证据。占用子进程 exit0，worker 与产品 exit2。context/runtime 关闭，worker handle 与 Job 均关闭，Job 活动数最终为 0；外层 pipes/handle 已关闭，未超时。工具壳报告 exit1，原值单独保留，不覆盖确切产品退出码2；wrapper 自身 OS 退出身份未被该 wrapper 持有。

`live-records/` 为六个已检查脱敏产品 JSON 的原 bytes 副本，共享 `.local/stages/a12-native-reuse-live` 原件和标记保留，不改不删。原始异常/产品 stdout 文本不外传，仅保留摘要与长度。`raw-output-manifest.json` 包含53固定输入及全部新增输出成员，不自引用。

本轮 live 额度已用1、剩余0，失败不恢复旧额度。作者结论仅 BLOCKED 和释放交付，不自宣独立接受、认证通过或平台可用。完成封存后停止，由调度收取固定材料并交正式独立静态验收。其他三例 HOLD，Q22 不重放，书籍送审送交未运行。
