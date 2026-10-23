# A27 固定候选独立验收

结论：`REWORK`。候选 `23591811be71f9598c07c09b6a25a2a5fb066db0` 的新恢复入口存在一项阻断问题，不能接受其当前 profile 独占门禁。有限键序接入、异步关闭退出以及其他已运行控制的结果分别保留；不把整项产品记为离线接受，不影响 A25 既有五题结论或 A26 交付。

**R1 / P1：等价 profile 路径绕过占用检查并进入恢复 reader。** 固定文件 `product/tools/run_usense_postsave_readback.py` 第 111–113 行只将命令行替换分隔符并 casefold，然后做完整 profile 字符串子串检查。反例进程参数是 `--user-data-dir="<parent>\.\<profile>"`，由 `str(profile.parent) + '\\.\\' + profile.name` 构造。Windows `Path(alias).samefile(profile)` 已在合成目录上证实它与规范 profile 路径是同一目录，但规范路径不是该命令行的连续子串。

独立 I07 通过 `execute` 的真实恢复入口、真实 `exclusive_profile` 检查和合成 OS 查询返回复现：两次占用观察均输出 `matching_profile_processes=0`，随后分派 `['configure','capture']`，最终状态为 `READBACK_MATCHED_AFTER_OS_RELEASE`。预期是在首次观察时拒绝，两个命令都不分派。原成功回执、意图和 holder 链在夹具中均完整，因此失败点确为独占检查而非缺少其他前提。没有启动 Edge、读取真实 profile/ledger、查询真实进程或请求平台；子进程派发采用合成替身，恢复 POST 为 0。完整 witness 和合成输入留在独立私有目录，并列入 `control-artifacts.json`。

最小返工范围：按 Windows 命令行参数语义识别 user-data-dir，核等价路径/目录身份；对于无法可靠解析或解析到确切目录的占用情况保守拒绝。保留前后两次观察，不以简单字符串包含判断宣布独占。新增一个实际恢复入口控制：`parent\profile` 与 `parent\.\profile` 必须在 configure 前被视为同目录；同时保留不相同目录的正常放行。不要因此启动真实 profile、扩展当前平台范围、重发 POST 或修补历史 ledger。修改后由根送新的精确冻结增量，复核该门禁及必要受影响路径。

接收与身份：只从根指定 `root-fixed-delivery/root-index.json` 接收。其摘要 `2300a16282a81e9eeab0da1518a5a9415cabc08e454572543194973c982ea0cf` 与根 receipt 一致；原 delivery manifest 为 `0c3df2aef1c79edf019829008e3b417adc40c560affe5202fe7aa0418d0395ab`。112 份交付成员、32 份产品依赖以及 index/receipt/原 manifest 共 147 份源件/独立副本原字节一致；32 份源码按 `blob <bytes> NUL <raw>` 复算 Git blob ID。提交与基线映射由根固定入口和 dependency manifest 提供，本独立未访问作者活动工作区或使用 checkout 换行归一化替代原字节。九个差异路径与固定 patch/根 receipt 相符。结束时再次核全部 147 份及原 preparation 文件不变。

正常批处理调用路径已核：`run_usense_reviewed_batch.execute` 第 147 行调用 `compare_batch_readback`；新比较器先走原 strict，失败时仅接纳 question/answer 新建直接 data 的规定三字段键序，复用完整严格比较。新 status 为 `ACCEPTED_CREATED_ZONE_ORDER`，第 171 行跳过标准 accepted marker；`revision.py` 原 strict 前驱校验保持。作者新增集中的实际 batch 替身控制证明两个目标串行继续，而有限键序目标没有标准 marker。独立 I01 穷举六种直接字段排列，只有原序和已证服务端序通过；另外六种值/类型/缺键/未知键/数组/未涉及对象变更均拒绝，输入摘要不变。

关闭调用路径已核：writer 清理前保留业务状态并解除 POST arming/封锁 policy；`close_framework` 保持 15/5/15 秒阶段上限，用 deadline 观察和一次取消，不等待抗取消协程无限 join。`run_usense_live --writer` → `writer.main` → `run_owned_writer` 的实际 CLI 分派已用合成 body/真实 cleanup 验证：抗取消 close 后返回 exit 2，context=false/runtime=true，OS 释放仍明确要求外层 holder。原 CLI stderr 的 pending task 销毁消息完整保留，未写成干净退出或 OS 释放证明。同步阻塞/底层线程仍依赖既有外层监管；未证明真实关闭问题的根因，原 UNKNOWN 保持。

恢复链其他已核范围：原固定 q4 回执/intent/send/双层 guard/完整 before/holder 身份与时间、新 reader 原始响应和完整比较均被新验证器读取；缺少正确回执、错误意图或未释放 holder 在创建资源前拒绝。第二次观察发现 profile 占用时，只完成 configure，reader NOT_RUN，spent 保留且无 marker。新 recovery sidecar 被未修改的 revision 前驱入口拒绝，原意图字节保持。R1 说明这些条件不能弥补当前占用观察的漏洞。

验证记录：

|类别|实际结果|
|---|---|
|候选新增测试|独立冻结副本执行 20/20 PASS，2.996 秒；未运行旧 194|
|作者受影响检查|原始 9/9 输出已核字节并读取，本独立未重复运行|
|独立 I01–I06|6 个不同控制 PASS，包括 51 份固定 A25 原件回放、实际 CLI 派发、前资源拒绝与 revision 拒绝|
|独立 I07|1 FAIL：等价 profile 路径使实际恢复入口继续 configure/capture；首个产品反例后停止，后续产品验证 NOT_RUN|
|独立辅助脚本原错误|1 ERROR 保留：首次 I03 在产品子进程启动前被辅助审计钩子误拦截；I04–I07 在该原运行均 NOT_RUN|
|辅助修正范围|原脚本原字节保留，新 v2 只显式传 `executable=sys.executable`；仅执行 I03–I07，未重跑已通过 I01/I02|
|作者历史失败|四份原失败及修正链保留，未转换为 PASS|
|新代码真实平台/浏览器/OS枚举|NOT_RUN；没有新 live 授权或旧预算恢复|

固定回放继承了 q3 原 strict=false/有限=true，以及 q4 原 framework=false/后来完整读回匹配；不是新保存或新回读。第 3/4 题原失败、ledger 和前驱资格未改写。机器结果、命令 argv/cwd/解释器摘要/退出码、原 stdout/stderr、原件和自身哈希见同目录文件及 `review-files.sha256`。清单自身摘要另列 `review-files.sha256.self`。

本次审阅完成并释放；保留合成证据以供根复核，没有常驻 runtime/browser/profile 资源。未修改根 state/AGENTS、作者产品、真实 ledger 或自动化，未提交 Git、未发其他聊天消息。1800-a 按任务维持 PAUSED，未重新读取其实时配置。
