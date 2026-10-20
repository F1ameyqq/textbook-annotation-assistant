# A13：唯一一次专用无头登录态复用观测

2026-10-20。用户本轮明确要求：“查看 A12-R1 独立验收结果，通过后继续推进那一次专用无头登录态复用观测。新阶段分别新建执行和验收对话，不重跑旧任务、不恢复已耗额度，按首题真实保存和读回的路线持续推进。”

A12-R1 正式独立结论为 `ACCEPTED_PREPARATION_FOR_ONE_REUSE_ONLY_OBSERVATION`，D1-D8 8/8，562ms；调度核固定raw、资源释放和R01/R02有限结论后登记本任务。原A12/N1-N3、A12-R1作者及独立差量已耗尽，不再运行。这是原先尚未使用的一次live，不是新加一轮或重试。

## 固定执行物与唯一目录

- 产品/驱动：`d45ed25a98361002ddb28985c1d27687c4421a17`。
- 最终交付：`81fab23e3e7e9e32a36d3857a253afc69b5bd3e1`。
- 产品：`tools/headless_native_reuse_probe_r1.py`，SHA256 `3f1e4a425e18ed0e2a28893989f31677ba6b9b7f4b9c3da2800bc925443999c9`。
- 候选清单SHA256：`38eb3f836f14b44db77ce516f461bd4f3934df71807c1fac962560603a210920`。
- 独立清单SHA256：`59d23a1dbe6e20abe92e7abf0ac89ba13834d6c6d90a01bcfae073e6072b72e7`。
- 新执行隔离raw目录：`D:/1800-worktrees/a13-reuse-observation`；53固定输入完全只读。
- 执行者只新增该目录 `execution-output/` 的准备/发起/报告/清单，以及产品自身固定的 `D:/1800/.local/stages/a12-native-reuse-live/` 原始输出。不得写主线或旧执行/验收目录。

## 正式角色

分别新建正式执行与正式独立验收对话，xhigh、model沿用，先登记去重意图后创建并登记真实ID。执行者负责唯一发起与固定报告，验收者此时只准备标准；执行者固定并释放后由调度另派固定原始结果静态核证。独立0新平台观测、0登录/业务、0重放。

## 单次启动前检查与登记

执行者核上述53raw及候选/产品摘要，不能修改产品、冻结驱动、allowlist、TLS、标记/输出、期限或精确Job释放逻辑；不安装依赖、运行旧suite、重新访问MCP标签或旧driver。

1. 先确认原共享 `a12-native-reuse-live` 目录及 `execution-output/launch-intent.json` 均不存在；任何已有标记或输出都停止，不删除、更名、替换或换目录重试。
2. 允许从已接受的惰性模块调用 `candidate(expected)` 和 `profile_binding()` 各一次，只取得候选校验和原专用profile元数据指纹。不读取profile内部文件、登录JSON、cookie、storage、token；不输出子目录名。若唯一目录/指纹规则失败即固定BLOCKED。
3. 将确定的非敏感指纹、确切候选/产品/交付身份、UTC和本地时间、执行threadId、单次上限、固定目标与启动期限写入 `execution-output/launch-intent.json`（exclusive create），记录固定wrapper/命令摘要后才启动。profile实际占用由冻结产品内部唯一一次、4秒有界检查完成；这里不另做实际占用扫描。

## 唯一运行

从隔离目录使用已安装Python 3.9和Edge，固定产品仅一次 `--live --candidate-sha256 <上述值> --profile-fingerprint <刚固定值>`。不得调用旧 `usense_login.py`。唯一专用持久化无头context、唯一about:blank、最多一次导航 `https://www.usense.com/qieti/annotateUnified`；0重载/重试/登录填写提交/验证码尝试/业务写入/书籍选择或源框接口。

允许最小外层 `execution-output/launch_once.py` 仅记录和调用上述冻结命令：启动前冻结自身raw摘要，无行为预跑；保留Popen确切句柄/创建身份，捕获原返回码和脱敏输出摘要，不改产品或模拟返回。产品已有75秒worker限制及确切Job释放，外层88秒最多等待、最多2秒保留句柄清理，90秒边界；只可终止本次外层持有的产品进程句柄，原产品的Job关闭负责其自有后代，不能扫描/杀其他Edge、relay或清锁。超时/无法证明释放一律UNKNOWN并停止，不另启动清理浏览器或重跑。不能宣称操作系统永久阻塞下普遍硬保证。

预检、占用、网络或守卫首个意外失败即停，后继NOT_RUN；LOGIN_REQUIRED亦正常停在该事实，不回退登录。真实保护标记、路由、密码框与网络守卫状态共同满足才可记AUTHENTICATED_VIEWER_OBSERVED，不能只看URL/HTTP200。产品工作进程实际检查并落盘profile-binding/occupancy，只有占用证明0才可能导航。失败也消耗此次启动，保留共享标记，不恢复次数。

## 释放与固定交付

保留原始单次intent、worker claim、绑定/占用、observation或preflight-failure、worker-release及外层句柄释放。输出不得含账号/密码/token/profile子目录/原始响应体/全页内容；产品正常产生的脱敏JSON可按原bytes复制至 `execution-output/live-records/`，原件不改不删。异常原文如含敏感内容只留.local，入报告仅脱敏类别与摘要，记录未复制原因。

报告 `execution-output/report.json` / `report.md`、完整raw清单（包含53输入身份及输出成员，不自引用）、外层/内层确切创建与退出身份、成功/失败/UNKNOWN范围、已耗1/剩余0及后继NOT_RUN。作者只报告REVIEW或BLOCKED，完成即释放停止，不自宣独立通过。

验收只静态核上述唯一观测证据和资源释放；若受保护界面确已观测且独立核证通过，主调度再固定书46007447当前源/目标只读任务、具体新普通单选/执行政策/写入次数、首题真实保存与刷新重开内容和题框读回。当前任务本身不授权那一步。其他三例HOLD、Q22不重放、0B及外部联系人消息，无书级送审送交；10月22日晚目标保持。
