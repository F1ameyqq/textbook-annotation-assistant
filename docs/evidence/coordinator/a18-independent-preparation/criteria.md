# A18 有限独立验收准备

当前状态 `WAITING_EXECUTION`。本轮仅准备标准、输入依赖及释放说明；未取得固定产品，不作产品接受、真实事实或资源释放的代验结论。正式执行与本验收对话分开，后续由调度向同一验收对话提供固定 raw 隔离输入。

## 身份及范围

- 基线：`5aec24575a0e1621f4f22680da3beba581e6cec2`。
- workflow：`bb163ba162f32857202b6a068e9fc050ed4ad9f4`。
- 正式执行：`01a15954-3ca1-76a3-a984-13229a985976`。
- 正式独立：`01a15954-997c-7af2-9645-a4e2c2b25e76`。
- scope：`CURRENT_BOOK_SOURCE_INVENTORY_CURRENT_FRONTEND_READONLY`。
- 执行任务 SHA256：`9f4f4f625ac5fda385c8f550d3ea6e55fbcb9f27f33c86bc5d5625abebaf87dd`。
- 验收任务 SHA256：`7bdf83cde0c346dfa25a7e4f7c70a6980e4ae60c2c8836dd40ad1ec27a0c90ba`。

## 固定输入到达后的有限检查

| 组 | 必须成立的事实与最小检查 |
|---|---|
| P0 固定输入 | 先核产品/final/candidate 的确切绑定、raw 字节清单、必要依赖闭包、改动白名单、旧证据保全和作者释放。仅使用调度指定的新隔离输入；缺少输入保持等待，不读活动作者目录。 |
| P1 拒绝与继续 | 未准入同源非 API GET XHR/Fetch 仍在发送前拒绝。有限继续须同时具备原主框、无重定向、严格规范化的原站 HTTPS、GET、XHR/Fetch，且原策略唯一拒绝原因为 PATH_BLOCKED；用最小正/负控制核实实际拒绝次数与发送为零。 |
| P2 硬停止优先 | API_BLOCKED、已知六 GET 的参数/书 ID 不符、样题、login/logout/signin/user_login 等受保护路径、其他方法/origin、导航/redirect、WS、身份缺失、歧义 URL 均不得降级继续。对变化的分类分支作有限负例，特别核硬停止先于 PATH_BLOCKED 排除。 |
| P3 精确版本读取 | 源码 hash/bytes offset/调用关系独立核实后，才接受原站原主框无重定向 Fetch/XHR 的精确 `/qieti/version.json` GET：唯一 query 键 t、值为数值时间戳、至多一次；不泛化 JSON/参数。重复仍拒绝并计共享预算；版本变化引起 reload 时第二主导航仍阻止。 |
| P4 共享预算 | CDN、同源 PATH_BLOCKED 排除、重复版本请求合计至多16事件；双层重复保守计两次；await 前记账。用混合事件到16/17及一个异步交错控制核预算共享、无单独额外额度，第17次仍拒绝且 fatal。 |
| P5 最终结清 | 拒绝异常、原应拒请求出现响应、晚到 fatal、context/native 回调未结清必须使最终 ERROR/UNKNOWN；检查最终 drain 与最终判定次序。保留具体原始原因；拒绝及 ERROR 正确且原件完整的细微顶层归因差异记录限制，不另造阻断。 |
| P6 端点与源码事实 | 脱敏诊断保留安全路径模板或不可逆路径 hash、可核已知路由、query 键名、方法/类型/层/拒绝原因；query 值、完整 URL、headers/cookie/token/profile 不输出，动态/疑似凭据段仅模板/hash。脚本只静态读取影响准入的片段；六固定 GET 如需参数修正，必须逐项有当前捕获源码依据，不顺手准入新 API。 |
| P7 A18 绑定与事实 | 新候选、scope/run_id/workflow/executor、决定引用、正式机器报告、activation 与输出路径闭合；旧 A17 对象拒绝。sample0、自动 schema=false、write_eligible/production_ready=false、原 R02 未修保持。认证/目录/库存/图/正文/schema 按实际证据标记；AVAILABLE/KNOWN_EMPTY/UNKNOWN 与 FULL/PARTIAL/UNKNOWN 分开。 |

检查采用必要的纯内存 fake transport 新差量和有限控制。未改源码可在原 bytes 同一性核实后明确引用旧有限证据；不重跑旧30/34/11及其他旧 suite，不刷历史 NOT_RUN，不准备无关大规模回归。出现改变接受结论的语义反例即保留首次失败与后续 NOT_RUN，报告 REWORK；不修改产品后重跑。

## 源码核验依赖与结论边界

唯一捕获 Script 的任务声明：SHA256 `d0a5ebce18bc92d7643662ecec2d078bb295214111e7cb32688f0b88e05bed41`，3065996字节。正式复核只读任务指定文件，先核 hash/长度，再核 mount→fEt→ED({initialize:true})→uEt、端点常量 offset3064125、fetch offset3064330、t=Date.now()、cache=no-store 及只读 JSON 关系。本准备未打开 Script，以上是待核依赖，不是独立已证事实。不执行、不重新请求、不复制入 Git，不读 source sidecar/profile。缺失或 hash 不符如实报告。

六业务 GET、viewer14/173 两原图各最多一次，额外精确版本 GET 至多一次；原 session/static 范围保持，共享排除16。总 HTTP 不以“8次”概括。普通单选内容、准确 bbox、未录入状态及正文/保存接线只按后续事实；不沿用旧核准或自动写入。

完整预检完成才可形成 `result=ACCEPTED_OFFLINE_ONLY`、`acceptance_basis=BOUNDED_READONLY_PREFLIGHT` 的正式机器报告，并绑定实际 candidate/workflow/executor/path；现在不填接受结果。TLS“一直批准”的持续许可已有记录，由调度单独绑定 A18 决定，不重复索取。独立预检不创建 activation、不启动 live。

后续唯一真实轮由调度固定至多1轮/1context/1主导航/900秒含释放；同一正式独立对话仅核执行者固定实际结果及精确自有释放，0重跑。认证、辅助发送总数、OS创建身份等无证据即 UNKNOWN；已证释放不外推为全部资源或真实平台成功。

本轮 0browser/network/profile/credentials/native/occupancy/login/business，0产品导入/运行/测试，0B消息。其他三例 HOLD，Q22不导航/样题/重放，无书级提交。准备完成即释放，不保持等待进程或占用。
