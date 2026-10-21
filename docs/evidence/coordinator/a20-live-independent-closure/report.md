# A20 唯一真实轮固定失败及有限释放独立核证

结论：**ACCEPTED_FIXED_FAILURE_AND_OWN_RELEASE_ONLY**。只接受固定失败归档及原始收据已证的自有释放；不接受认证、书籍/书源、映射或首题保存读回通过。原唯一 live 已耗 1、余 0，禁止重试、延期、清标记或重开原 activation/output；既有产品离线预检结论不扩展为真实平台通过。

本独立 `01a159ab-01ba-7093-89a6-69e7ce572c38`，派发 workflow `90406699ad083a98efc0bd5a1c0eb94fb199c42f`。产品 `28203196b4f2dae27b1de4213b27da9a41ae3139`，离线 final `b41e88d7756fde9d7f1b348ce5a300d1104e765b`，中间证据提交 `28dc921c84bb4a6f043472337f3df9128c3b4d3f`，本次 final `f45fa86789b8f154d03e8c4807412a2161d678f6`。候选 SHA `91db377e44b5b864208cc27a078d25266b3375bba2fdee18b9c648f37b572a7b`，产品 workflow `52be34a72c43a7331976aba4b286138b9183856b`。

只读取 `D:/1800-worktrees/a20-live-review` 的 56 固定 raw；先核后解释并在封存前再核全部 SHA256、长度、Git blob 和清单声明 mode/type。作者 55 成员清单加自身与输入集合闭合，27 候选依赖及父包原 bytes 保持。全树 31853 旧成员保全、28 新增/0改删是调度固定机械核证的引用范围；本隔离独立复核范围是所给 56 raw，不冒充重新核全树或访问原作者目录。

## 授权与一次执行绑定

本轮直接决定记录用户原答复“批准本轮一次登录及读取”，明确包含本轮登录、凭据在 context TLS 例外中发送的授权。candidate、decision、activation、原独立报告完整 39 项 scope 的值与类型逐项匹配；原 profile 指纹、run_id、executor、产品 workflow、输出/activation/决定/报告路径及预算均对应。决定/activation/原独立报告的 raw SHA 与派发记录一致；五份 authority 原件的复制 hash/长度均与固定来源捕获记录匹配。原提案/answer-record 仅作为本次决定与派发中的匹配 hash 引用，未超出 56 raw 另行读取。

批准窗口为 UTC 2026-10-21 01:33:24.446405—01:48:24.446405，恰好 900 秒。固定 launch intent/argv 和四个一次性标记相互绑定，记录一次外层启动、一个 context、一个登录页导航意图及双层各一次导航预留；没有第二个 viewer 导航意图。此为所给固定意图/收据的核证，不声称新增过全局 OS 启动追踪。

| 时间层 | UTC 起止 | 原记录耗时 |
|---|---|---|
| 外部证据捕获 | 01:34:25.405895—01:34:36.111973 | 10703ms |
| launcher 收据 | 01:34:26.050828—01:34:35.972390 | 9984ms |
| worker 收据 | 01:34:26.767695—01:34:35.926159 | 9156ms |
| context 观察 | 01:34:28.905627—01:34:35.883475 | 未单列单调耗时 |

各层 UTC 起止均在批准窗口内，记录的 deadline_exceeded 均为 false。时间层、UTC端点算术与各自产生的耗时字段分别保留；细小差值及跨层差值原因 UNKNOWN，不将其精确归因。静态核证记录另列端点算术供核对，没有重跑或补测计时。

## 固定失败与零后继

原始 `raw/current-state.json` 顶层和 guard 首错一致为 ERROR / Stop / API_BLOCKED。UTC 01:34:35.501292，首个非预期致命 BLOCK 记录为同源 HTTPS `www.usense.com:443`、GET、Image、FETCH_REQUEST_STAGE，redirect_hop=false；path SHA `7f8d9b088e7dea613880ef32040bf2c15bda25cb7a672a7ae05a37137bac2eba`。具体路径、用途、产生原因和根因均 UNKNOWN；不猜验证码、logo 或其他用途，亦未做 hash 字典、源码诊断或额外请求。

登录页有 native/context 两条 NAVIGATION/ALLOW 记录，固定已知 `/qieti/login` 的 path hash 匹配；没有把审计的 Document 字段冒充独立保存的 frame ID 比较。`login_navigation=FAILED`，`login_fill/login_submit=NOT_RUN`，提交意图 false，双层 POST 预留和实际 POST 均 0，登录 HTTP/响应为空。固定控制流中第 798 行的导航 await 未完成，配置 reader 在第 808 行之后，支持本轮配置未读、未填写/点击/提交的有限结论；这不是新 OS 文件访问审计。作者包装器未读凭据亦仅为固定声明。

六业务 GET、viewer14/173 两原图、两映射、样题及业务写入/上传/OCR/书级提交全部未进入，相应后继维持 NOT_RUN，sources 为空，protected_viewer_authenticated=false。真实认证、当前书身份、目录、题框、源图和映射未证明；body/schema UNKNOWN、write_eligible=false、首题保存/读回 NOT_RUN。

此前一次 CDN Script 被预期拒绝，排除事件及已完成拒绝调用各 1，仍未获发送许可。11 条审计为守卫事件，不能当 11 请求；辅助实际发送总数 UNKNOWN。version native 预留 1、context 0，后者记录 STOPPED；预留不等于实际发送或 HTTP 成功。viewer 专属 `navigation_diagnostics=NOT_STARTED` 与登录页已启动不矛盾，不能由它推断整轮未启动。登录主 Document HTTP 状态/DCL 没有落盘，均 UNKNOWN。静态 Script HTTP200/原 SHA 元数据只证明该素材记录，不证明登录主响应或认证；本独立未读 `.local` Script/sidecar 实物。

## 已证自有释放与退出层

| 持有句柄收据 | PID | before/after created_filetime | exit | 句柄关闭 |
|---|---|---|---|---|
| product | 33872 | 134370200660575953 | 2 | true |
| worker | 39416 | 134370200667701250 | 2 | true |
| occupancy | 37684 | 134370200677639436 | 0 | true |

三份 raw 的 PID/创建身份 before/after 均一致，exit_observed=true，退出时间有效；作者释放投影与原收据一致。两个 Job 最终 active=0、closed=true、assigned=true，原 before-final-cleanup active=1 值均保留。context_close/runtime_stop 成功、errors=[]、state=RELEASED；最终 pending_tasks=0、pending_callbacks=0，terminal_stopped=true。API_BLOCKED 首错在 shutdown 前及序列化时保持，没有被晚到 STOPPED 改写。

只接受上述固定持有句柄及自有 context/runtime/Job 收据。没有新增 OS/native/占用/进程扫描，也没有证明 launcher 自身 OS 创建/退出身份；该项仍 UNKNOWN，不由包装器完成推断。外层 launcher/product/worker exit 均 2；作者汇总记录的证据捕获工具包装器 exit0仅表示捕获完成，原工具 transcript 不在 56 raw 内，不能认作产品通过。outer stdout 135 bytes 仅有安全 JSON 投影与 SHA，原 bytes 未提供，不能独立重算它的 hash；另有 launcher 收据的内部 stdout90bytes/hash，各层分别保留。stderr0不代表整个产品成功。

## 保留原失败与审查边界

普通 checkout CRLF/LF 与 Git raw 误比较导致首次清单生成失败，中间 `28dc921c` 缺清单后又封存补齐；失败记录明确是作者转录而非原始完整工具 stderr，原工具输出未提供。固定最终 raw 清单已核通过，但不回写第一次失败/中间提交，不称为产品重跑。原件完整且实际正确拒绝并 ERROR 的这些限制不要求修产品或恢复额度。

本独立只做 JSON/hash/AST 静态比对，记录的 110 项是证据比较，**不是 suite 或产品测试**。0 产品 import/run、0新旧suite、0 launcher/browser/network/profile/真实凭据/native/占用、0新连接/登录/业务写入、0 decision/activation/live；不读原作者或 `.local` 实物，不重做旧预检、不刷旧 NOT_RUN。仅新增本目录审查材料，全部原输入末尾再次保全核对。明确释放见 release.json，无等待进程或持有平台资源。其他三例 HOLD，Q22 不导航/样题/重放，0 B 消息，无书级送交。本阶段旧额度保持耗尽，不开启后继。
