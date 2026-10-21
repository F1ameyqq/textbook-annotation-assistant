# A24 正式独立验收准备

状态：PREPARATION_COMPLETE_RELEASED / WAITING_EXECUTION。本文件是标准，不是产品验收、真实就绪或激活。

固定任务基线：454c6ff4a89580e6209b4c45fd6bc74a5e603d83；workflow：c3026c05d1603038328ceca6918452d3ec4504b7。
执行对话：01a15cf8-0c63-70d3-b374-ce85e6f29fd7（来自本次派发）；独立确切 ID 以根登记为准，不能由文件夹名推定。
只在本准备目录写材料；不读 D:/1800-worktrees/a24-first-save 的目录、文件或输出。当前无固定作者交付，所有产品运行、测试及真实动作均 NOT_RUN。

## 固定交付入口

根给作者明确释放后的新 raw 隔离路径、产品/final 提交、完整候选依赖及输入清单 SHA，再开始有限正式验收。先核 raw Git bytes、改动范围、旧成员保全和身份绑定，后解释结果；checkout CRLF 与 raw LF 分开。

作者可先交付只读候选和首题接线缺口表，后在同阶段交付首题候选。首题未接通不阻断安全可运行的只读候选；只读接受不把首题分支标为已准写。沿用本对正式对话，不为字段或普通报告差异拆新阶段。

## 只读候选的有限预检

| 项 | 必须可核的事实 |
| --- | --- |
| canonical 合同 | 仅按 data.records || data.books || data.list || [] 的前端优先序；保持 JavaScript 真值语义（空数组仍被选中），不递归拼别名。选定容器非数组显式拒绝。以 String(row.id) 精确匹配 46007447，恰好一个目标且 title 有效一致；0/重复/冲突/缺标题均显式停止，不选第一本、不把 file_id/book_id 当列表身份。 |
| 当前请求计划 | 固定时只选一种：原 GET，或原站同路径 bookId=46007447 的官方目标路由。给同一已捕获 Script 的 hash、精确调用链和参数依据，不运行时切换补救。username/role/status_list/team 等只可从官方页内既有上下文绑定；不猜账号角色，不读凭据配置，不导出账号值/token，不加 profile 诊断。静态源码不证明当前权限。 |
| 解析前事实 | 原 HTTP/有限业务 code、白名单容器类型/项数、目标匹配数、明确分支及仅目标 id/title 等允许字段，须在身份/字段适配可能抛错前持久化。其余已准业务响应也留下有限结构。不能输出未知键、响应全文或身份/原请求参数值。实际缺失继续 UNKNOWN，不称 FULL/KNOWN_EMPTY。 |
| 同一请求账 | 自动前端、在途响应和主动 GET 共用预算；预留/在途/UNKNOWN 都不得另发同一业务请求。来源身份、HTTP、phase 和是否真实发送可核，审计事件不冒充发送数。身份通过立即完成同 context 全部已准书源与页映射。 |
| 权限绑定 | 当前 task/scope/run_id/executor/workflow/candidate/report/decision/activation/path 完整且类型精确，自绑定并拒绝 A23 等旧材料。完整 scope 由本候选实际 schema 枚举，不能仅核关键子集或强制沿用历史条目数。 |
| 有界守卫 | 首个异常/UNKNOWN 停止，后继 NOT_RUN；不重试、延期、清标记、换输出或恢复旧额度。只复核有改动的守卫关联，保留原主框、无 redirect、回调结清与释放边界；不重写 native/OS/时间框架。 |

预留预算仅供未来根绑定：1 原 context / 1 固定目标导航 / 900 秒含释放；六业务 GET 各至多1，viewer14/173 注册原图各1，version≤1，共享排除16。session 单 VIEWER 三原路径各≤1/总3，统一20秒；主动 profile 仅全无预留/在途/UNKNOWN 时一次并计总3。原 profile 指纹 b4620cd9fe064121a916062126321b7bba3862185d8919bf228f1399097a0d00。

0 凭据配置读取/填写/登录、refresh、重发、业务写入、上传、OCR、样题、书级提交。原图 origin 与端点沿已准闭集，不增加来源。

未来只读绑定路径：decision `docs/approvals/A24-current-contract-user-decision.json`；report `docs/evidence/coordinator/a24-independent-closure/independent-result.json`；activation `.local/stages/a24-current-contract-activation.json`；output `.local/stages/a24-current-contract-live`；scope `CURRENT_CONTRACT_AND_FIRST_SAVE_PREPARATION_READONLY`。本次不创建上述文件。根在 A23 实际收口及本候选有限预检后引用 A17 持续同类只读 TLS 许可，不重复泛问，不扩大登录/写入。

最小相关新控制按变更选择：canonical 优先序/空数组/错误容器/目标在非首位/无匹配/重复冲突/缺标题；失败前安全 shape 和敏感值不外泄；官方上下文与固定计划拒绝猜值/替代路线；自动与主动重复及在途/UNKNOWN 拒绝；旧 A23/错绑定/额外写方法拒绝。作者相关新测试只作输入，独立作必要少量反例；不跑旧 A03–A23 suite，不为历史 NOT_RUN 刷 PASS。可定位原件且已正确拒绝/停止的报告细节列限制，不单独阻断实测。

## 同阶段首题准写门槛

当前源目标到达后固定书46007447第2节《一定是直角三角形吗》基础印刷1：四组 1,2,3 / 2,3,4 / 3,4,5 / 4,5,6；历史 C 只是待核线索。必须核当前未录入、合法末级目录和全局题序、逐字题干/选项顺序/答案关系、源 SHA/尺寸/viewer-resource-save 页映射及六框 Q/W/W/W/W/A 的类型/顺序/bbox。不能自动换题、沿旧 Q1 许可或从离线标签生成 PLATFORM 事实。

真实 observe/build/send/receipt、runner、plan、quality 应接入现有 journal、书锁、immutable intent 和 claim。baseline→新鲜 prewrite→intent/claim 持久化→恰好一次 save POST→真实 receipt→get→实际 refresh→作者释放→独立新 session reopen，按阶段证明。服务端新身份/题序缺失或歧义即 UNKNOWN，不能客户端 fallback；不清 claim、不重发。

冻结前一次填齐：当前 wire 字段/类型/完整写集及空值语义，精确 payload/hash/policy/版本，六新框且0旧框 upsert/删除和旧正文删除；上传 U 为固定整数（U=0也须合法路径证据），若 U>0 列签名及每对象来源/方法/hash/字节/次数，0签名刷新/403重试。全部 GET 按 phase/URL/参数/次数展开整数；T、Z、P 或“按需”未定不激活。自动 UI 请求计入同 phase，不重复主动发。

旧目录/题/题序/框/绑定/正文保全必须有一种当前真实证据：完整聚合正文前后比较；覆盖旧集合的权威逐记录摘要/版本；或服务端强制唯一新增事务及可独立核对完整写集。全框库存、单题正文、计数、is_new/空删除数组不能替代。缺能力时记具体缺口，保留已做实现，不启动泛化诊断。

只读候选预留不包含首题写入。完整可审查当前新题/policy/计划/整数预算固定并独立及根核证后，由根落实已有用户首题指令适用的具体许可和 activation；作者/独立均不可自行从只读切写。独立重开预算单列，确认作者释放和不同真实 session 后才只读重开。

## 实际结果与释放

分别报告：当前 viewer 准入、认证依据及限制、书籍身份、完整源目标、保存 HTTP/业务 receipt、正文/六框 get、实际 refresh、正式独立 reopen、旧记录保全、NOT_SUBMITTED、自有资源释放。跨 phase 必须有新服务器响应，payload 回显/缓存不是读回。

首题成功须作者与独立均核同一服务端新题身份、逐字内容、六框角色/顺序/类型/几何和旧集合不变。保存 UNKNOWN 停书保留原件，后续只读对账另核授权，不由 MATCH/ABSENT 自动清 UNKNOWN 或重发。释放只接受保留身份的自有资源证据；launcher OS 身份等未证明项仍列限制，不从关闭句柄推断进程退出。

首题全链通过才另固定其余最多4题（累计5）；本准备无额外题权限。其他三例 HOLD，Q22 只自然保全不导航/样题/重放，0 B/外部联系人消息、推送和书级送审送交。保持 Edge/profile，不批量 kill/清锁/换 profile/token 注入/绕过工具策略。

结论层级固定为：准备完成→只读有限预检→实际只读结果→首题候选核证→真实保存及作者刷新→正式独立重开。只接受各自已证范围。所有旧失败、UNKNOWN、历史 NOT_RUN 和耗尽预算保持。
