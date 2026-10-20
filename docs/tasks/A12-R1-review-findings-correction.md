# A12-R1：占用输出与守卫最终判定的有限纠正

2026-10-20。原 A12 正式独立验收 `01a15794-ad3e-7653-8f77-237fe06f8898` 已释放，固定报告为 REWORK。调度依据用户持续推进路线的授权，明确修订自己设定的工程上限，仅增加这两项可逆离线纠正；不声称用户另行批准过额度，不恢复旧候选、旧 suite 或旧 live 次数。原任务所述“不自动追加”由本次具体差量任务替代到以下确切范围，不能递归扩展。

## 固定依据

- 原产品 `7f3d42e31be29782f0e09e6c01cc8e277387747c`，原交付 `0c30b365ed18b006bcab32bed4acb60869ff9f92`。
- 独立报告：`docs/evidence/coordinator/a12-formal-review/report.json`，SHA256 `cf29e73425b17c3d88388d6c7af6b55ade0258c1016f46a7924c5eb0c2e33ae3`。
- 原 N1/N2/N3 实际流量与精确释放证据有限保留；原 22 文件、31,159 基线成员完整。原候选使用1、原浏览器 suite 使用1，剩余均0；live使用0但资格关闭。
- R01：Windows 文本 stdout 产生 CRLF，父进程二进制比较只接受 LF，导致零占用也被拒绝。
- R02：密码/受保护 DOM 的 await 期间可发生 guard stopped/failure，成功分支及序列化前未重新裁决；异常路径可能丢失原 guard error。

## 正式派发与路径

本阶段必须分别新建正式执行、正式独立验收对话，thinking=xhigh、model沿用；子代理仅辅助。创建前调度登记去重意图，创建后登记真实 threadId/host/cursor。验收初期只准备标准，待固定交付、raw清单和作者释放后收到调度续派才读取新候选。

执行目录由调度固定为 `D:/1800-worktrees/a12-review-delta`，独立分支 `codex/a12-review-delta`，基于原交付 `0c30b365ed18b006bcab32bed4acb60869ff9f92`；在派发记录另绑定本任务 workflow commit。旧目录/分支不改。正式对话初始 cwd 即使是 D:/1800，也必须显式切到指定目录。

唯一允许新增：

- `tools/headless_native_reuse_probe_r1.py`
- `docs/evidence/A12/review-delta/`
- `docs/tasks/A12-review-delta-author-report.md`

原产品和全部原证据必须原 bytes 保留，新产品以原冻结实现为来源，仅作 R01/R02 与必要的候选摘要、导入及证据路径接线。记录完整差异；原 allowlist、NativePolicy、发送前网络守卫、WS/子目标拦截、TLS、profile绑定、占用期限、一次性输出目录/标记、原生传输和精确Job释放语义不放宽。新产品仍共享原固定 live 输出/启动标记，不新开 live 额度或输出路径。原证据依赖按固定raw摘要复用，不能改旧清单。

## 必须修正

R01：建立一致的严格单记录输出协议。可使用二进制固定换行，或严格解析明确允许的 LF/CRLF。stderr、非零退出、非零/非法计数、多记录、额外字段或尾随内容必须拒绝。不得执行真实占用扫描来验证本项；用只输出合成计数的受控子进程验证实际 Windows 管道 framing。复用产品协议函数，不能在测试中重写其算法以自证。

R02：DOM异步读取后、最终结果序列化前均将真实 guard 终止状态及首次原错误作为决定性结果。任何已观察到的 guard stop/failure 都不能留下认证成功/正常LOGIN_REQUIRED退出；序列化 pre-shutdown 状态，区分业务守卫终止与仅为关闭而设置 stopped。关闭期间新出现的真实错误也要保留，不能用清理动作抹去原错误。保留 UNKNOWN/NOT_RUN、0重试和0登录语义。允许最小提取纯判定函数/注入测试边界，但生产路径必须调用相同实现，不能让fake绕过真正的判定逻辑。

## 冻结后唯一离线差量

作者新增最多1候选、1次以下固定8项差量；独立另最多1次同范围差量。原浏览器suite不重跑，浏览器/fixture服务器/平台/profile/凭据访问全部0。允许一轮受控本地协议子进程（每方最多1个，只输出合成0，无占用扫描），其余为纯内存/异步fake。先静态/语法准备，再冻结产品与驱动，第一次行为执行即消耗本方唯一差量；不得先偷偷跑目标用例。冻结后首意外失败固定，后继NOT_RUN，不改后重跑。

1. D1：实际 Windows binary PIPE 收到产品协议发出的合成零计数，被同一产品父协议接收；记录字节、退出码、准确子进程释放。
2. D2：固定拒绝集：非零count、负数、布尔count、额外字段、多记录、尾随垃圾、stderr、非零exit；全部拒绝。此为预先固定8个输入，不能现场扩矩阵。
3. D3：受保护路由、viewer可见、密码不可见、无guard错误，结果如实认证；shutdown-only stopped不误判真实失败。
4. D4：密码可见、无guard错误，结果LOGIN_REQUIRED，0登录动作。
5. D5：密码await期间触发stopped且failure=None，结果必须保守失败、保存stop证据、0认证/正常登录结论。
6. D6：viewer await期间触发带原始脱敏error的guard failure，保留首次error，结果失败。
7. D7：进入观察循环前已有guard failure，保留原error/NOT_RUN，不被通用NETWORK_GUARD_STOPPED覆盖丢失。
8. D8：读DOM完成到最终序列化之间（含关闭await）注入真实guard failure，最终不能成功；首次error及pre-shutdown/最终状态如实。必须通过生产最终化路径验证。

外层最多60秒，不运行旧suite、不启动浏览器、不触及原profile或真实占用。只清理受控自有子进程句柄；禁止批量kill或无关进程检查。无新依赖。已有有限网络guard证据只在相关实现原bytes/等价AST不变的范围沿用；未动态覆盖的worker/popup、强制deadline异常等仍列限制，不宣称全面回归。

## 交付

产品/驱动冻结commit、最终commit、raw成员清单及摘要、逐项实际结果、命令和期限、确切自有释放、原路径保全、旧新代码差异与范围映射。作者只报告 REVIEW/REWORK/BLOCKED，不自宣接受；固定后释放，不再改产品或补跑。调度核raw后向独立对话派发固定版本及隔离副本，独立自建有限输入核验这8项并封存。

作者候选累计上限明确为2（原1+本差量1），原浏览器suite仍1且耗尽，新增纯离线差量各方1；不是重置原计数。两方live上限0。任何进一步缺口固定交接，不能自行第三候选或再派重复差量。通过后也仅能由调度另行登记同一个尚未使用的最多1次reuse-only观测；此前还要核真实profile绑定、占用、单次标记和精确期限。其他三例HOLD、Q22不重放、0B消息、0业务写入；10月22日晚目标不重起算。
