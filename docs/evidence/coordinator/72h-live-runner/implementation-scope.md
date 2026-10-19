# 三天限定普通单选 live runner：全新增实施任务单草案

2026-10-19；静态基线 `404199fbbd7ef97b5837ba3d0555e91e5175e1cd`。本文件只定义工程接线边界，不构成真实题清单、写入次数、平台共同政策或上线放行。候选上限 5 题，实际清单及次数尚未固定；Q22 不重放，其他复杂三例继续 HOLD。A03/A04/A07–A09 旧额度不恢复。

阶段结论：**可立即实施全新增离线内核和阻断式平台接口；当前真实执行仍 BLOCKED**。主调度最新消息：A10 唯一只读轮已在首次导航发生 NAVIGATION/TRANSPORT 失败，未登录提交，0 业务写入，作者报自有资源释放，固定交付仍待收。此消息是调度状态输入，不是本子任务独立验收；不得制造当前来源、登录、坐标或 VERIFIED 能力。下一次平台诊断/取证由调度另定具体新范围，本草案不续跑 A10。

## 1. 已核实的最小复用面

以下固定文件均从上述提交的 Git blob 静态读取；A05 私有脚本仅读取守卫源码并核摘要，未运行、未读 profile/凭据。

| 依据 | 能复用的事实 / 限制 |
|---|---|
| `docs/delivery-72h-plan-2026-10-19.md` | 有限真实试用目标、逐题计划/回执、全书顺序、UNKNOWN 停止、独立读回；文内旧“待连接许可”由最新纠正覆盖。Q4 最新离线采用消息亦不升级为平台政策。 |
| `src/annotation/contracts/validation.py:443–565,700–731`、`models.py:267–311,581–591` | 已有 PLATFORM → PLATFORM_OBSERVED；READY 必须双 PASS、当前快照、同 policy/hash、JOINT_CONFIRMED applicability、OBSERVED 依赖/证据、同平台版本的 VERIFIED frame_readback 及 session 能力。C01 验结构/引用，不能代替事实采集或共同采用证明。 |
| `src/annotation/quality/targetcheck/__init__.py:112–130` | `projection_frames` 是纯投影：根据实际图谱/选定答案/原图区域/政策生成角色和顺序，可复用。不能复用该模块 `make_artifact` 的 SYNTHETIC 封装、`analyze_target` 的模拟准入。 |
| `src/annotation/delivery/planner/__init__.py:17–44,61–130` | `frame_facts`、`compare_action_effect` 可作框级比较辅助；`action_facts` 的 next_order 是目录局部 max，不能当真实全书追加依据；比较器不核文本，不验证旧目录/全书旧题保全。ABSENT 结论必须再受新全书基线检查约束。 |
| 同文件 `create_plan` | 固定输出 SIMULATED，按目录局部追加；新建 `create_live_plan`，不改旧函数/模拟守卫。 |
| `src/annotation/delivery/mock/persistent.py:107–178` | `BookEffectGate` 为宿主机跨进程字节锁，可单独复用；固定同书同路径，5 秒内失败关闭。它不证明远端排他，不能排除其他机器或平台人工写入。 |
| `src/annotation/runtime/storage/common.py:canonical/digest/exclusive_bytes` | 可复用规范化摘要、独占创建和 flush/fsync；同内容文件已存在不等于再次获得发送许可。不可复用 RuntimeStore 的 SIMULATED intent/receipt 或 SYNTHETIC evidence 工厂作真实实现。 |
| `docs/tasks/A05-execution-report.md`、`A05-review-report.md`、`docs/evidence/A05/execution/commit-preflight.json`、`commit-receipt.json` | 2026-10-16 历史实测一次新增题级保存：`POST /qieti/api/annotate_pic/commit_unified_submit`；新题上下文 question_order=null、is_new_question_insertion=true、全书 insert_after_order=21、两新框、删除列表空、ocr_submissions=[]；业务回执 code=0 / success / inserted / question_order=22 / append_at_global_end=true，刷新及关闭重开持久化。只证明该 Q/A 填空样例，不证明 W、批量、文本录入、当前接口或 UNKNOWN 恢复。 |
| `.local/stages/A05/session.py:25–52` | SHA-256 `bba7998f8279fd3403420765cccee53a2ecaba73a23b864fb945059e7b99c9d7` 与固定 code-version 一致。其 commit_sent 是进程内一次标记，旧常量锁定 21→22 两框；只作行为参考，禁止调用或改写旧队列/脚本。 |

历史 GET 可定位全量框 `get_manual_annotations_unified/46007447`、单题框 `get_manual_annotations_unified_by_order_in_level/46007447/{order}`、题型 `get_question_info/46007447/{order}`。目录、书状态、原图及 OCR 查询亦有历史业务回执；本草案不猜测未读取的接口字段，不把 GET 路径存在当当前可访问。

## 2. 唯一支持范围与授权/输入

首版只接收普通单选 ordinary_choice，恰好 1 stem、4 个有明确顺序的 option、1 个已选定 answer，恰好六框 `Q/W/W/W/W/A`；全部具有独立原图区域。任何 shared_material、explanation、组合/子题、七选五、图片选项、多区域拼接、未解决答案关系或框数差异均拒绝，不自动转题型/合框。首版是否支持公式由明确文本编码 profile 决定；不支持编码应在发送前拒绝。

每题必需：稳定内部 question_id；来源/图谱/检查包确切 ref 和 hash；原图文件摘要、尺寸、resource 身份与 viewer/source/save-page 显式映射；每框原图坐标/角色/类型/顺序；核准的题干、四选项和答案文本/关系；显式末级目录映射；单题内容核准与本轮真实 CREATE 授权。授权 manifest 包含书 46007447、1–5 个固定 question_id+输入摘要、有序清单、每题最多一次发送、全批次数上限、起止窗口、禁止 Q22/旧平台映射、policy ref、证据 refs、允许操作。清单缺失/空、超过 5 或摘要变化均阻断 apply。

支持普通选项的语义从权威规则导出，独立断言 option→W；即使旧 Q/Q/Q/Q/Q/A 政策与计划及伪读回互相一致也必须拒绝。已有 Q1/Q4 离线业务核准、5970f15a / 2455fa4 技术采用和 A05 BOUNDED_A05_OBSERVED 都不能代替本轮 JOINT_CONFIRMED 平台执行政策。完整 B G/Check 尚未取得就保持输入阻断，不从 stage 小包自行拼造“B 完整通过”。

## 3. 全新增文件白名单（建议实施派发）

| 新文件 | 单一责任 |
|---|---|
| `src/annotation/quality/live_pilot.py` | `check_input`、`check_target`、`check_observed_content`、`check_preservation`；纯规则/比较；输出具体证据绑定，缺证据 HOLD/FAIL。 |
| `src/annotation/delivery/live_pilot/__init__.py` | 显式导出，不在 import 时创建浏览器/目录/锁。 |
| `src/annotation/delivery/live_pilot/plan.py` | 本轮 manifest/transport DTO、全书顺序 facts、单题 PLATFORM 计划构造与重算校验；使用 C01 seal/validate/assert_plan_ready。 |
| `src/annotation/delivery/live_pilot/usense.py` | 显式注入既有登录会话的窄适配器：只读观察、受限载荷构造/校验、单次发送、业务回执解析、刷新/重开、关闭；文本 wire profile 未证明时 fail closed。 |
| `src/annotation/runtime/live_pilot/__init__.py` | 无副作用导出。 |
| `src/annotation/runtime/live_pilot/__main__.py` | `inspect-input` / `prepare` / `apply` / `reconcile-readonly` / `report`；默认本地检查。apply 必须显式且完成全部准入，不能靠 --force/--assume-verified 解锁。 |
| `src/annotation/runtime/live_pilot/journal.py` | 固定书级锁、不可覆盖 intent/发送权/读回/回执文件、重启禁止重发、账本完整性与 batch NOT_RUN。只实现本轮一次 CREATE 状态机。 |
| `src/annotation/runtime/live_pilot/runner.py` | 逐题串行编排；首失败停；分离框保存、内容和独立验收状态；finally 关闭/释放并落盘。题型规则留 quality。 |
| `tests/test_live_pilot_admission.py` | 授权、C01、角色、全书顺序和来源负例。 |
| `tests/test_live_pilot_journal.py` | 跨进程排他、一次发送、故障点/重启、UNKNOWN、NOT_RUN。 |
| `tests/test_live_pilot_readback.py` | 业务回执/真实读回适配、文本/旧状态保全与关闭。 |
| `tests/fixtures/live_pilot/fixture-catalog.json` | 仅新增小型脱敏 fixture 引用与摘要；模拟样例清楚标记，无凭据或“真实通过”假证据。其他 fixture 文件只允许该清单预声明的新路径。 |
| `docs/live-pilot-runbook.md` | 已有运行环境检查、固定入口、输入/授权模板、停止/只读对账/人工接管、实际结果边界。 |

禁止修改任何既有 src、合同/schema/policy、依赖、pyproject、主调度 JSON、旧脚本/证据/pins。使用已有 Python 3.9+、Pydantic/Pillow 和当前已有浏览器依赖；依赖不存在即报告缺项，不安装。模块入口为 `python -m annotation.runtime.live_pilot`，通过现有安装或显式 src 路径使用，无需改根 scripts。新增产品在独立分支/工作目录，固定基线导出旧 raw manifest；本草案本身仅写当前两个 .local 文件。

## 4. 可立即并行的离线接口

这些是实施工作包划分，不是本子任务自行派发。A：纯 input/TARGET/plan；B：journal/runner+假 transport；C：usense codec/readback+历史脱敏 fixture；D：独立验收设计。只在既定 owner 管理的独立新增路径工作；共享 DTO 由 plan.py owner 固定。

1. `check_input(bundle, approval, source_bytes, policy_adoption_proof) -> Admission`：验证原始字节/图像尺寸及范围、六角色、文本、答案和核准闭包；不读浏览器。保留原 B HOLD 与新 A 授权分开引用。
2. `observe_current(session) -> Observation`：必须返回当前书/完整目录与全量框、平台题身份/全书顺序、涉及原图 mapping、题型/内容读取能力与实际源响应 refs、采集时刻、session 身份/平台版本、完整性。不能由 plan.expected_after 生成 observation。
3. `check_target(admission, observation, journal_status) -> CheckReport`：本题确为未录入；全书顺序无歧义；旧题/目录基线完整；无未解决 UNKNOWN；同书排他/专用会话实际有效；当前原图与批准摘要一致；真实共同 policy 与 frame_readback/session 证据齐备。每项 PASS 必须从事实运算，禁止直接导入手填 PASS。
4. `create_live_plan(...) -> 单题 ApplyPlan`：只一个 CREATE_FRAMES action；根据完整全书题列表算 global_max+1、固定 insert_after_order；保存前再 GET 对照 current snapshot/hash、全书最大序号/目录 hash 和旧框 hash，变化停止且不悄悄重算续跑。C01 中 expected_before 附全书 facts，但不把目录局部 action_facts 当唯一判据。
5. `build_commit(plan, approved_text, uploaded_crop_refs, wire_profile) -> payload`：产生新 rect_id、Q/W/W/W/W/A 对应 six frames；每个 upload 与原图裁片 hash 绑定，类型、页映射、zone order 独立核验。线上上传也是外部动作，必须纳入新真实单题授权与 intent/不可重发审计，不能因 A05 network.json 不含 OSS 上传便遗漏。未知上传/commit 立即停。
6. `send_once(intent, payload) -> RawBusinessReceipt`：必须先持久化绑定 code/input/approval/policy/plan/baseline/payload hash 的 intent，再独占创建持久发送占用标记并 fsync，最后一次平台调用；任何 retry/重定向重发/旧队列禁止。网络返回不推导 APPLIED；HTTP 200/toast 不充分。
7. `read_back(question_identity) -> Observation` 与 `compare_saved(...)`：从独立 GET、刷新、关闭后新会话重开获取；依据平台返回 ID 建 mapping。六框原图、角色、类型、数量、顺序、题型/内容逐项对批准输入比较。A02 比较函数只作为框比较辅助；fragment_id/region_id 从批准 identity 与实际 rect 数据匹配，严禁填 expected projection 冒充 actual projection。
8. `reconcile_readonly(intent) -> MATCH/ABSENT/CONFLICT/INDETERMINATE`：一个获准只读 GET 对账机会，不能发送。MATCH 也只新增 reconciliation，不改旧 UNKNOWN 回执、不自动启动后继；ABSENT 不能恢复发送权；需要调度决定新计划/新额度。读取失败或证据缺失仍 UNKNOWN。

默认使用 SAME_SESSION_HANDOFF 仅在真实当前证据支持时；PERSISTENT 需另有 persistent_draft 当前证据。A05 已保存内容可重开不等于未保存草稿可跨重启。只读预检不能凭空证明保存能力；旧 A05 可作历史支持，新版本适用性需要明确证据，证据不足就 HOLD。

关闭重开的真实 session_id 应更新，保留 predecessor-session/释放/新会话证据链；不能伪造相同 session_id 来通过 A02 recovery comparator 的同会话检查。跨会话验收由新比较层验证同平台/书/题身份及原图绑定。浮点 bbox 如需误差容限必须来自明确冻结的坐标规则与实测依据；不默认照搬 A05 的小于 0.001px 历史误差，也不能自动四舍五入抹平真实错位。

## 5. 一次发送状态机与原状态保护

批次清单先建立 N 个 NOT_RUN。逐题新计划→基线读回→PREPARED→INTENT_DURABLE→SEND_CLAIMED→一次发送→业务回执落盘→独立 GET→刷新→关闭/重开读回→框结果/文本结果。只有本题所有要求满足才可进入下一题。业务失败、结构/内容不符、保存未知或关闭释放不能证明时停止，后继保持 NOT_RUN，不制造 ExecutionReceipt 成功结果；每题单一 plan 避免 C01 每 action 结果覆盖要求与后继未执行混淆。

日志是每个事件一个不可覆盖文件，含 sequence、previous_hash、对象 refs 和本轮 owner；损坏/缺文件/冲突不能重建成“从未发送”。同一 canonical 平台+书键共用固定宿主机锁路径，不能用 run_id、可选 output_dir 或另一个 profile 绕过；还需调度独占与实际 profile 占用检查，冲突停止，不杀他人进程/删锁。挂起 intent 或 SEND_CLAIMED 跨重启均禁止自动重发，未知实际效果需对账。明确只读 report 可重读落盘数据，不产生新平台动作。

每次后读必须证明：旧 rect_id 集合及所有业务字段原样；旧题型/已存在文本（若读取得到）逐字段原样；完整旧目录名称/层级/同级顺序原样，仅当前题节点追加；全书题序无移动；书仍未送审/送交。若历史文本/题型快照不完整，不能宣称其完整保全。对于新事务中 ocr_delete_zones 等前端默认字段，只有确认被严格限制在新题且无旧 ID/旧题上下文时可放行；不能照搬 A05 默认列表扩大删除范围。成功和异常路径都关闭本次 context、核对自有 PID/profile 占用、落 session-release；release=true 与业务 UNKNOWN 可同时存在，释放不是解决保存不确定性。

## 6. 文本保存目前缺什么，离线可做什么

确定事实：A05 两框 `content_type=text` 只是框的内容类别；`ocr_submissions=[]`，Q/A OCR 查询“未找到标注结果”。仓库现有 src/tools 未找到已验证的非空文本提交实现。因此不能交付“六框保存”后把 CONTENT_PENDING 改 VERIFIED。

尚缺：当前前端对普通单选的 W/choice 角色与 zone 索引映射；非空文本/公式/选项/答案的实际载荷字段和编码；题型字段实际值；上传裁片路径的生成与签名流程；业务保存回执是否包含文本持久化结果；独立内容查询的 endpoint/schema、文本规范化规则及选项对应；是否同一 commit 原子保存六框和文字；若需单独内容接口，其次数/失败处置必须在新授权中明确。不能由字段名 ocr_submissions 猜造非空 schema。

离线可立即交付：ApprovedText / ObservedText DTO、严格文本比对（仅明确可证明的空白/换行规范化，数学、正负号、上下标、选项顺序不可容错吞掉）、未知 wire profile 拒绝、固定旧 A05 decoder 与 fixture、transport mock 和故障矩阵。可静态阅读已有已归档且脱敏的前端代码来整理候选 codec；候选值标 NOT_PLATFORM_VERIFIED，缺 live source 及响应闭包时真实发送仍关闭。新实际页面/源码取证需等调度新范围；A10 当前失败不能提供上述事实，更不能靠手填 capability 弥补。

## 7. 最少必要测试矩阵（全部新离线范围，零平台）

| 组 | 正常与必须反例 |
|---|---|
| T1 输入与权威 | 一个有效六框输入；摘要/尺寸/原图映射/授权 question_id 各一处变更拒绝；Q22、已有平台映射、空清单、6 题拒绝。 |
| T2 角色语义 | 正确 Q/W/W/W/W/A；格式良好但陈旧 Q/Q/Q/Q/Q/A，连同计划和模拟读回一致仍拒绝；shared/explanation/七选/子题/五选拒绝。 |
| T3 C01 与能力 | joint applicability +确切采用 refs 结构链；仅 Q1/Q4 离线采用、SYNTHETIC 改标签、无证据 VERIFIED、旧平台版本、当前 snapshot 变更、frame/session 缺失全部拒绝。模拟 fixture 的 PASS 不生成真实准入证明。 |
| T4 全书追加与保全 | 两目录 local_max≠global_max，必须 global+1；重复/歧义题序、目录漂移、已保存同题、旧框/文本/目录任一改动停止。 |
| T5 一次发送/重启 | intent 前失败 0 send；intent 后/发送占用后/实际效果后/回执落盘前各崩溃；新进程同一题不能再次发送；并发两个进程最多一个占用成功；同内容已存在文件不重新授权。 |
| T6 UNKNOWN 与批次 | response 丢失、只返回 HTTP 200、部分六框、GET 超时/截断/冲突；本题 UNKNOWN，后继 NOT_RUN；只读对账 MATCH/ABSENT/冲突均 0 resend；不修改旧 UNKNOWN。 |
| T7 内容与读回 | business success+实际六框+文本匹配；文本缺失/PENDING、错字/符号/答案/选项顺序、只替换为 expected projection 必须失败；刷新/重开实际新 read_sequence/来源 refs 与旧 plan copy 区分。 |
| T8 释放与禁止动作 | 成功/失败/关闭异常各路径；释放不能证明即 HOLD；未授权 OCR/送审/送交/旧题写入/删除/其他书/未知上传一律阻断；锁/profile 冲突不杀进程。 |

仅运行上述新 tests 及相关 C01/纯投影导入检查；不复跑旧业务 CLI/旧成功矩阵/平台测试。测试执行次数与候选额度由新派发单固定，不从旧任务借用。

## 8. 冻结与独立标准

作者先冻结确切产品 commit、基线、全新增白名单、raw SHA-256 清单、脱敏 fixture+expected 规则出处、测试命令/结果、未验证接口和准入缺口。旧 tracked 路径 raw bytes 保全；不能为干净工作区覆盖主线大量 M。作者标 REVIEW，不自行 ACCEPTED。

独立离线验收从固定 raw blob 隔离导出，核旧 bytes/新路径、逐项新负例（至少 stale Q role、目录局部 max、把计划伪装读回、SEND_CLAIMED 重启、伪 VERIFIED）。只能接受“新有限离线实现/拒绝行为”，不能宣布平台资格或 B 共同政策。独立者不与平台执行共用活动 profile。

真实放行另需：A10 固定失败/释放证据审查完成；后续新范围取得当前可达/身份/原图/坐标/会话事实；本轮确切 1–5 题与每题次数已核准；完整输入/内容审批与平台共同 policy；文本 wire/readback 能力证据。首题新真实闭环必须同时有保存业务回执、刷新/重开独立读回、实际文字正确与旧状态保全，才允许消耗清单中后继题额度。失败固定现场并停止，不修后同轮再跑。最后交付逐题成功/失败/UNKNOWN/NOT_RUN、独立结果、session-release 及人工接管说明；NOT_SUBMITTED 始终保留，最终提交人工负责。

本子任务执行：仅静态读取固定 Git blob、核 A05 session.py 摘要、写本目录两份文件；未访问平台/网络/profile/凭据，未运行业务或测试，未改 src、主调度 JSON、主线既存文件，未派发或发 B 消息。
