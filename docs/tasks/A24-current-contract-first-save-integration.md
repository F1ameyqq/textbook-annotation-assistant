# A24 current contract and first-question integration

用户要求加速、真实读取后尽快首题保存与读回，不再拆过多诊断轮。本阶段集中当前书源合同适配、真实sender/receipt和首题保存/刷新/独立重开读回；一对新的正式执行和独立对话贯穿同阶段必要修订与固定交付，不为每个字段另开Axx。当前派发仅离线实现与准备，0browser/network/profile/真实配置/native占用/产品launcher/live/write。用户已有持续同类只读TLS许可；后续具体只读候选预检及根绑定后直接激活，不重复泛问。现阶段绝无自行登录/写入/自激活权。

基线454c6ff4a89580e6209b4c45fd6bc74a5e603d83。作者唯一工作区D:/1800-worktrees/a24-first-save，branch codex/a24-first-save；不得写D:/1800根协调文件，不改任何旧证据。先读根AGENTS/coordination/development-plan/state及本任务，以最新要求优先于worktree内旧状态。新对话ID/产品workflow由根登记；候选冻结时必须用自己的实际ID和本任务workflow。A23实际正式验收在并行，接受前不激活本阶段，离线工作不等待其归档。

新事实：A23原permissions完成且viewer组合准入，主动profile0；book get_once已返回，外层BOOK_IDENTITY_REJECTED。book HTTP/response/body/安全shape未落盘，真实无目标与冲突/结构分支UNKNOWN，不得推定根因。旧A23唯一live已耗，不能重跑它或改其output/activation/标记。输入根a23-live-delivery和已固定final；当前前端静态辅助见根a23-book-contract-analysis（hash与字节offset已核）。不是正式实际响应合同证明。

优先交付可运行的当前合同读取修订，同时准备首题真实接线，避免保存所有代码完成才读取。复用现有current_readonly/auth/policy/gate/probe/launcher，必要修改decode.book_identity和有限事实投影；不新造业务执行系统或重写native/OS释放/时间守卫。正常必要纯内存fake开发和相关新测试允许，失败留存，不人为限制一候选/一次离线测试；不运行旧A03-A23 suite，不为历史NOT_RUN刷PASS。

书籍合同：固定当前AnnotateUnified链vyt→qze→n0选择data.records || data.books || data.list || []，page=1/pageSize=10，route.query.bookId→搜索id→find(String(row.id)===bookId)，选择row.id/title，后续file_id沿用此id。身份字段是id，不是file_id/book_id；不递归合并所有别名，不接受任意第一本。保留容器类型、匹配0/1/冲突、缺title/不符等显式失败。记录实际原HTTP/业务code、白名单container/列表项数量、目标匹配数量、分支原因以及仅目标id/title等允许字段，在解析前落有限安全证据；未知任意键或账号/原请求参数值/响应全文不得输出。其他已准业务GET也应在字段适配前留下足够的有限结构，避免再因丢失当前事实而多跑。未经证明不能标FULL/KNOWN_EMPTY。

当前前端还带username/role/status_list/team等查询上下文，A23只page/pageSize/id。不能仅凭失败猜加用户名/改角色/分页。离线先用同一已捕获Script明确当前viewer调用链，选择一个有确切依据且不扩大访问权限的具体请求计划：原GET保持，或当前官方UI的目标bookId路由和其实际上下文请求。若采用目标路由，只允许原站同路径确定bookId=46007447；若上下文参数必要，必须从当前官方页面已有会话上下文在页内绑定，禁止读用户名密码配置、猜admin/role、导出token或任意账号、额外profile诊断。源代码不能证明当前角色或书籍权限。只允许精确端点、有限键/参数类型和固定目标、原主框、无redirect；自动前端与主动读取共享同一业务预算，不得两次发送。冻结方案时明确到底哪一种，不可运行时自选替代路线。

本阶段新只读预算先预留至多1原context/1固定目标导航/900秒含释放；六业务GET（含书籍）各最多1，viewer14/173两来源注册原图各1、version≤1、共享排除16；session单VIEWER三原路径每条≤1/总3，唯一主动profile仅全无预留/在途/UNKNOWN时计总3，统一20秒。0用户名密码配置/登录/refresh/重发/业务写入/上传/OCR/样题/书级提交。身份通过立即同context全部书源读取及页映射，不停在诊断成功。具体新task/scope/run_id/executor/workflow/candidate/report/decision/activation/path必须自绑定并拒绝旧A23许可，原profile指纹b4620cd9fe064121a916062126321b7bba3862185d8919bf228f1399097a0d00。预留scope CURRENT_CONTRACT_AND_FIRST_SAVE_PREPARATION_READONLY，decision docs/approvals/A24-current-contract-user-decision.json，report docs/evidence/coordinator/a24-independent-closure/independent-result.json，activation .local/stages/a24-current-contract-activation.json，output .local/stages/a24-current-contract-live；当前全部不得创建。已有A17“一直批准”只读TLS可由根在预检后引用，不能扩大登录/写入或恢复旧轮数。

并行首题离线工作：依据.local/stages/coordinator/a23-first-save-consolidation/draft.md（SHA335a3ea88780bee6113c568bfc764f71110b310816c003aa6c43bca9abc44c28）与notes，集中替换src/annotation/delivery/live_pilot/usense.py真实observe/build/send/receipt占位、runner offline限定和quality真实新鲜来源比较、plan实际目录绑定；保留journal/书锁/immutable intent/claim/UNKNOWN不重发，不另造执行器。当前接口源码线索不是实时schema证据；没有当前事实的写分支保持禁用，可用fake实现编排但不得宣称live就绪。可以分先固定只读候选、后同阶段固定首题候选，不重新建正式聊天。

真实书源到达后，同阶段立即锁定书46007447第2节《一定是直角三角形吗》基础印刷1候选（四组三边1,2,3/2,3,4/3,4,5/4,5,6，历史C，Q/W/W/W/W/A），当前未录入/目录/全局序号、文字和bbox、源SHA/尺寸/页映射全部核实，未符合不能自动换题/沿用旧Q1。固定实际保存接口字段、完整写集、1次新题savePOST、必要裁片上传具体整数/对象及新鲜内容+6框get/refresh/reopen读回次数；不得把UI流程算1写或继承403重试。旧正文保全依完整聚合、权威旧记录摘要版本或服务端强制新增及完整写集的真实证据之一，全框/单题正文不能冒充。真实保存前须固定完整可审查新题/policy/版本/预算并由独立与根核证，根依据用户本次明确首题指令落实具体写入许可及activation；作者不能自行从只读切写。若有新增未授权边界，先把具体方案准备完整再交根处理，不先泛问或索要密码。

同阶段首题作者保存及刷新读回、正式独立新会话重开读回通过后，才推进其余最多4题（总5）。保存UNKNOWN停书只读对账不重发。不把所有旧记录真实正文未核称全量保全。其他3例HOLD，Q22自然全量保留但不导航/样题/重放，无B/外部联系人消息或推送，无书级送审送交。保留Edge/profile，禁批量kill/清锁/换profile/token注入/工具URL策略绕过。

每个固定交付给产品commit/final/完整Git raw候选依赖、相关新测试和失败、报告及精确释放。首个可运行只读修订优先交付，同时提交首题接线明确缺口，不将首题完整实现拖慢真实读取。根机械核后同独立在新raw隔离有限验收；报告细节但原件完整正确停止者列限制，不另造阻断。新实际运行必须绑定已接受具体新候选与新预算，不能称旧轮额度恢复，也不自动追加盲重试。
