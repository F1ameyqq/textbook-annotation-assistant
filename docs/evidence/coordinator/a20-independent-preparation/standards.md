# A20 独立预检准备标准

状态：`PREPARATION_COMPLETE_WAITING_FIXED_DELIVERY`，验收为 `WAITING_EXECUTION`；以下全部为后续检查标准，当前未检查产品、未运行测试，不能据此接受候选或平台。

独立聊天 `01a159ab-01ba-7093-89a6-69e7ce572c38`；作者 `01a159aa-42b4-7103-bfaa-9767969d9b8e`；基线 `38e86a1c153eb0ad68ebd22d4403602ffaa6852b`；workflow `52be34a72c43a7331976aba4b286138b9183856b`。任务以根 A20 执行/独立任务及登记 JSON 为准，输入 hash 见 dependencies-release.json。

| 检查组 | 固定交付后的有限检查和通过事实 |
|---|---|
| P01 输入和依赖 | 调度提供确切产品/final commit、候选 SHA、全量 raw/清单、相关新测试原结果/失败、报告及作者释放。先核原 bytes、差量白名单、运行依赖闭包（含父包初始化文件），再读产品。只用新隔离，不读作者活动目录、不修产品。历史证明仅在相关源码原 bytes 同一且适用范围不变时引用，明确未重跑。 |
| P02 官方来源 | 从获准固定 Script 原件静态核实登录函数、JSON 编码和两键 username/password、成功条件、401 分支/两处登录跳转、刷新 POST 和重发行为，给精确位置/hash。任务中的静态线索不是本独立已核结论；来源不足须明确缺口，不猜接口、不作网络探针。原 Script/sidecar 不复制入 Git，不执行。 |
| P03 决定门禁 | A20 自己的 scope/run_id/executor/workflow/candidate/独立报告/直接决定/activation/一次额度和路径须相互绑定。缺失、错阶段、旧 A17/A19 决定或不含“至多一次登录提交及 TLS 例外中发送凭据”的直接决定均不能 live。先固定候选和有限预检，具体决定由根最后落实；本独立不创建决定或激活。 |
| P04 context 和导航 | 1 个原专用 context，900 秒包含释放。最多 2 次 Document 主导航，按序仅 https://www.usense.com/qieti/login 与 https://www.usense.com/qieti/annotateUnified 各一次。校验原站 HTTPS、原主框身份、无 redirect；其他目标/子框冒充/第二次相同导航/reload/不明身份拒绝并停止。SPA router.push 若无 Document 不虚增 HTTP 导航。 |
| P05 凭据边界 | 真实配置仅获本阶段批准 live 时运行中读取 D:/1800/.local/usense-login.json；不能从新 worktree 读同名配置。离线只用 fake credentials；原 profile 运行中派生指纹须为 b4620cd9fe064121a916062126321b7bba3862185d8919bf228f1399097a0d00。填写前后再核原站/原框/确切官方表单。0 新 profile/日常 Edge 替换/token 注入/跨 profile 状态借用。 |
| P06 单次真实提交 | 点击前不可逆记录提交意图；仅原固定 UI 操作产生、关联原 frame 的同源 POST /qieti/api/user_login/login，精确 username/password 两键。native 与 context 双层各预留一次实际 POST，但合计至多一次真实发送。检查先后回调/重复点击/第二次 POST/表单或字段变更均不能产生额外发送；异常/超时/错误口令/验证码/MFA/UNKNOWN 不重试。 |
| P07 请求约束 | 刷新 API、原请求自动重发和重复登录在发送前拒绝；不放开域级 POST/API。必要 session 请求必须逐一固定方法/路径/身份/上限。保留六固定业务 GET、viewer14/173 原图各一次、version 静态 GET 至多一次、共享排除 16；CDN 仍拒绝。0 样题/正文保存/题框写入/上传/OCR/书级提交；新来源和未知 API 停止。 |
| P08 认证与同轮读取 | 登录 URL/HTTP200/POST200/router.push 均不足以证明认证。明确受保护 viewer、当前书 46007447 身份及允许读取证据；已登录分支须凭当前明确认证标志跳过凭据提交。身份成立后同 context 直接完成六 GET、两原图及 viewer14/173 映射；不再拆新读取轮。未认证或未知则后继 NOT_RUN。当前 sample0、schema UNKNOWN、R02 未修、写入资格 false。 |
| P09 保密与事实 | fake username/password/token/cookie/header/body 哨兵检查所有输出面：命令行/聊天/日志/异常/报告/截图均无敏感值；DEBUG/PWDEBUG 不得继承暴露。被动响应证据仅安全枚举/有限字段、HTTP 状态及来源关联；不输出自由 detail/message/响应对象。保留实际首错、最终 guard、late fatal、回调结清，预期拒绝及时停止，禁止为诊断追加请求。 |
| P10 释放与结论 | 正常/拒绝/超时均按现有内核验证精确自有进程身份、Job/context/runtime 释放；不终止借用进程，不把 UNKNOWN 写成已证。检查剩余预算不能恢复旧额度。原件完整且正确停止的轻微顶层报告差异可列限制；凭据保密、重复提交、不误写、不越界、有界停止或事实缺口须阻断。通过也仅 ACCEPTED_OFFLINE_ONLY，实际认证/书籍/首题仍未证明。 |

后续只做必要的新 A20 纯内存/fake transport 控制；具体入口、数量和命令在新固定隔离派发后确定，本准备文件不启动或预先承诺 suite。旧 A19 18/3 及 A18/A17/A16 等 suite 不重跑，历史 NOT_RUN 不刷 PASS。保留真实失败；不为报告美化扩大测试。

其他三例 HOLD，Q22 不导航/样题/重放，0 B 消息，无书级送交，2026-10-22 晚截止保持。本轮准备完成即释放，无等待进程；恢复条件和实际零运行记录见 dependencies-release.json。
