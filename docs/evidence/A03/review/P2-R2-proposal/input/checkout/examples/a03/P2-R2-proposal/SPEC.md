# A03 P2-R2 静态候选规范

状态：STATIC / UNIMPLEMENTED / REVIEW。只约束 A 侧离线合成提案；没有公共合同采用、B 确认、产品实现或原生接纳权威。调度 workflow `d834bf531f95abac7ed30b89b3ca55105fa6f491`；执行 base `7fdbde8f16569fd3bc399013115e13269d5d33fa`。

## V：唯一版本和入口

唯一候选是 `candidate-final/`，profile=`a03-p2-r2-static-2-PROPOSAL`，exchange=`a03-exchange-3-proposal`，新 Artifact=`1.3.0-a03-static-proposal`。选择必须匹配 [profile](candidate-final/profile.json) 全部六 Schema pins、API、oracle 和静态 oracle verifier 原字节 SHA。根下 `candidate/` 是已失败时间样例的原件，不是候选别名；旧 R1 candidate-v2 完全不改。

[check.py](check.py) 的 `Package.validate()` 是两种完整包共同经过的唯一结构/消费者入口，不存在只调用 prefix_check 绕过外层的正例。Schema 和语义 registry 都支持相同 12 种 Artifact。1.1 节点仅作不可变只读输入；本轮新 receipt 可以引用既有已接受计划的只读身份作恢复依据，但不能因此 dispatch、恢复旧尾、升级旧节点或使用旧 PRE stub 获得新执行资格。1.2 R1 是另外的历史候选，不能混入这个 selector。未知版本拒绝。

Schema 解释器是明确有限的 stdlib 子集：未知关键词拒绝，支持本候选全部关键词，不代表通用 JSON Schema 标准认证。规范的字段约束由 Schema 和本规范的跨字段规则共同组成；结构通过不等于 native eligible。

## S：typed frame、逐消费者和统一混合 DAG

外层 Artifact 递归消费其 payload 及嵌套 Resource；每个普通 ArtifactRef 必须 exact 四元组可解、被该消费者自己的 input_refs 声明、同 book/scope。Resource 路径不得逃逸，raw SHA 必须匹配；额外声明也参与身份、scope 和 DAG 检查，不能成为后门。

唯一例外位置是**经 Resource 字节绑定、精确 profile/format 和封闭 Schema 验证的 prefix.frames**。只在这个位置停止把 frame 内引用归到外层；header 普通 refs 仍归外层。每个 frame 自己递归消费 event 和其所有嵌套 Resource，自己声明 input_refs，使用自己的推导 scope。任意其他位置的 frame_version，包括普通 Resource 中伪装的 frame，都拒绝。

frame scope 从 exact indexed plan 推导。严格历史 TARGET_DRIFT_HOLD 中具备登记元组 `(registration_id, source_ref, snapshot_ref, scope_id)` 时，planless scope 从 exact Source/Snapshot 的相同 scope 推导并校验登记元组；原生层还必须与实际 registration 行等值，不能靠 caller JSON 证明登记。其余无 scope 依据的 planless 控制事件必须 null，不能凭帧自己填 scope。当前最小正包用两个 exact plan；登记元组分支未提供独立正包，不能计为该分支已证明。

全图节点包含 Artifact、每份 `(path,raw SHA)` Resource 和每个 typed frame；一个统一 DFS 检查混合环。它在 Artifact content_hash 最终检查前进行，所以故意制造的混合环可以精确报 MIXED_CYCLE，而非仅被旧 hash 掩盖；该负值不声称能构造加密摘要自洽的环。消费者声明/scope 规则随后逐一执行；不凭“全书可信”豁免普通引用。

[scope-session.json](candidate-final/scope-session.json) 是同书 original-a/original-b 两 scope、不同计划的完整 15 Artifact 包。两个 PLAN_ACCEPTED 的 evidence 都有两层 Resource，最深处引用本 frame 的 Source。外层 receipt 的 fact→basis→prefix 不再要求它声明或消费另一 scope 的 frame 引用。该包通过完整入口。正例只是静态值，legacy PRE/TARGET 是明确 stub，不能称原生合法历史或新 PRE 资格。

前缀来自全书 genesis，保留真实序号、前驱、全部 control/其他计划行，subject accepted anchor 与前驱从原链核对；不重编号、不投影、不设 complete 布尔。新封闭事件变体之外，Schema 原样嵌入 R1 的 39 个旧 event-body 变体，保留其字段和版本；不删旧 owner/control 来适配。完整原生 DB/index/head 等值仍未执行。

## T：session、三读、期限和唯一事实

`a03-unattempted-basis-3` 的 binding/gate_binding、所有 STARTED/READ 事件、prepare、observation 必须绑定相同 ledger/session/entry/parent-call/owner/generation/registration/store/target-session/target-key/plan/scope/action/digest/fence。任何一项不同拒绝。fence_token 字符串只是静态诊断值；未来必须验证真实私有 fence/handle，不把它或 in_final_gate 布尔当锁。

H0 必须等于本 session 的唯一 STARTED 紧前事件 `(sequence,hash)`，并等于 STARTED.payload.initial_event_head。完整 hash 链、subject PLAN_ACCEPTED/永久预留及每个计划的 action/digest 绑定必须正确。H0 到 Hfinal 的窗口只有该 session 的七条许可事件：STARTED，然后三次 READ_STARTED/READ_FINISHED；窗口内其他 control、其他登记/owner/session 或第四次读拒绝。Hfinal 同时等于 prefix.expected_book_head 和 basis.expected_event_head。

计数在真实读之前持久提交：三次实际读，前两次 EVIDENCE，第三次 CURRENTNESS 且在最终短 gate 内。序号/used_count 为1/2/3，独立 observation ID/read_sequence/time 严格绑定；完整相关 ABSENT、相同目标 hash/version，prepare 来自第一读并保留 exact expected_before。该正值三个读时间均位于对应 started/finished 之间。

每读≤2s、entry≤8s、parent≤60s、busy≤1s、gate≤5s；lease10s、续期2s；retries=0。每步由 native parent/entry 的最早绝对 deadline 截短，不能层层重新开始计时。静态值同时核对 event/observation 时间及入口 deadline 上限，不能证明真实墙钟/锁已符合。parent/entry 持久预算由可信入口建立；同 call/entry 重开或接管不重置，读崩溃也耗次，无 intent 使用独立计数，不占/伪造 intent 额度，不自动换 call 循环。

fact 永久唯一键为 SHA256(canonical `{target_key,plan_ref,action_id,action_digest}`)，独立于 owner/generation/call/session；同 action 的新调用不能产生第二份不同事实。同一不可变 fact 可有多个 receipt 消费者，不把重复引用误算为重复事实。fact 的序号为 Hfinal+1、前驱为 Hfinal.hash，receipt/result/plan/prepare/readback/basis/无 intent/NOT_ATTEMPTED 必须一致。先持久写资源，最终事务 CAS 同时提交 fact index 和事件；UNKNOWN 提交先核实际状态，不自动重提。当前静态检查有重复 fact 拒绝，但没运行 DB 唯一索引或事务。

逻辑 session 必须有真实持久记录；所有受控写入口共同执行，包括 claim/takeover、plan 接纳/启动、intent、permit issue/consume、目标 effect、hold clear、profile 接纳和转换注册。中间允许释放 OS gate；第三次读在最终短 gate 内，此后只有本地校验/CAS，不能隐藏第四次业务读。owner 死亡、lease 失效、deadline 到期立即暂停；遗留 session 明记 ABORTED 与已耗次数，不以重新调用重置。相关 UNKNOWN/hold、其他 scope pending 保留；他书独立。

**覆盖所有写入口及已打开连接的排他是未来实现的前提，本轮不声称已证明。** 无法证实任一受控入口或 predecessor 影响不能排除时，阻断事实/效果，不能退化成 caller 布尔。

## A：已知 DB 的持久接纳门

这是规范性候选，不是实际 SQL 或 DB 文件。本轮没有查询/打开数据库。

选定已知 `a03-runtime-db-1`、原 application_id/user_version1、原四键 meta 完整匹配后才可开始。显式事务保留原 version/ledger_id/target_store_id/state_dir，新增四键：`profile_id`、`profile_pins_sha256`（完整 profile raw SHA）、`adoption_nonce`、`adoption_state=ADOPTED`。同一事务追加唯一 RUNTIME_PROFILE_ADOPTED，绑定 prior head、profile/pins、nonce、owner/generation、原 meta 摘要和排他/旧 writer 退出证据。meta 不回指 adoption-event hash，避免自引用。新 open 要求精确键集与该唯一事件一致；旧四键严格比较会拒绝新 meta。这只是基线源码静态推断，未运行旧 writer。

顺序：先建立 ledger 维护排他、覆盖全部相关 book/target gate，核对所有旧 writer/已打开连接退出并阻断其重启；再将目标 fence 置 PREPARED/禁止效果；随后提交 runtime meta+event；最后核对该事务已持久并将目标 fence 置 ACTIVE，绑定同 nonce/profile/pins/generation。新入口仅在 runtime meta/event 与 ACTIVE target fence 全部等值时运行。原行/hash 不改；未知格式/多余键/不一致一律拒绝。

崩溃在目标 PREPARED、runtime 未提交，或 runtime 已提交、目标未 ACTIVE：均 ADOPTION_INCOMPLETE/只读诊断，不产生效果、不自动换格式或补写。两份存储不能假装一个原子事务；显式修复须另派。没有完整旧 writer 退出与禁止重启的可核对条件时，**接纳整体 BLOCKED**；额外 meta 只能防后续旧 open，不能撤销已有连接。本轮未证明覆盖、排他、fence 或崩溃恢复。

## P：INITIAL、POST_HOLD 和待审 oracle

新初始包包括完整 Source/Evidence/Graph/Snapshot 和新 PRE；12类 registry 由同一候选列表驱动，Source 不再结构允许而语义 unregistered。新 PRE synthetic_run_ref 与 verification_context 必须一致。INITIAL 的 hold_id/head/ref 全为 null；POST_HOLD 三项都必须存在，并与 hold Resource 的 id/head/scope 一致，观察严格晚于 hold，snapshot/time/Source/Graph 绑定一致。两个静态上下文都保持 NOT_EXECUTED、五项 UNAVAILABLE、没有 native run。新 PRE=HOLD，不能复制旧 stub 改 ID/time。

[oracle.json](oracle.json) 是待独立审阅的固定声明：新手写32×32 P2 PGM，白底两个黑矩形，单题、stem/answer 各一、固定答案关系及映射。Graph 构造代码不读取 oracle 的 expected 字段；oracle 不存 graph hash 来代替比较。它由执行者分别编写，尚未被独立认可，不能自称独立权威。exact 原始输入为 `candidate-final/original/page-a.pgm` 和 `original/new-authored-initial-a.json`，摘要在 profile/转换清单/最终交付索引。

[oracle_verifier.py](oracle_verifier.py) 草案分别比较：原像素/尺寸/raw SHA/页清单；question/fragment/region 数量与几何/角色/引用；明确选中的 answer 关系；每页/每题/每区域和 clue 分母；exact 固定 policy role_mapping/option_grouping/question_type。它只适用该固定 singleton fixture，不是 B 算法或一般题库验证器。五项 STATIC_MATCH 以及逐项破坏得到的 STATIC_MISMATCH，只说明静态比较工作，不生成 native PASS/run 或 oracle 批准。

未来生产仍需获批 exact oracle/verifier digest、真实新读取与五检查、私有 registry/run 身份和输入字节校验。POST_HOLD 后续新 TARGET/plan、最终三读中的真实 currentness/CAS、正向清 hold 和第二次变化均未执行。

## C：完整静态转换和 COMMITTED 唯一接纳点

转换原件是**本轮新写的已知1.1初始 fixture**，不是旧失败现场的恢复：`original/new-authored-initial-a.json` 含七个完整 Source/Evidence/Graph/Snapshot/PRE/TARGET/Plan。没有 receipt/intent/UNKNOWN。前四项转换到新 namespace/scope/version；原件原字节保留。旧 PRE/TARGET/plan 仅归档，映射 new_ref=null 并有原因。新 INITIAL PRE 单列 new_derived，依据新 Source/Graph/Snapshot/run/oracle，不能伪造与旧 PRE 等价。

[mapping](candidate-final/conversion/mapping.json) 给出完整双向 ID/revision/hash 对应：全部旧节点恰好一次处置，全部新节点恰好来自映射或显式 new_derived。所有旧 Resource 的 old/new path/raw SHA 完整列出；原图/文本原样复制，嵌套 JSON refs 与显式 scope 字段递归重写。checker 独立按映射重建预期 payload 与 JSON Resource，逐项相等，旧派生对象不能混入等价映射。原件和目标摘要闭合。

CREATED→COPYING→VALIDATING 是追加 Resource 链。completion manifest 在准备完成后写入，精确绑定 source/mapping/target 及目标全部 Resource 原字节集合。manifest **不引用 COMMITTED**。唯一静态文件接纳点是 terminal COMMITTED：引用已存在 manifest 的 raw SHA 和上一状态。rename 后未 COMMITTED 的分支明确 INCOMPLETE；CREATED/COPYING/VALIDATING/FAILED/INCOMPLETE 全部拒绝接纳，即使完成 manifest 已存在。重开只读诊断，不自动补提交；重做必须新 id/新目录。

样例 COMMITTED 是作者构造的完整静态协议值，不是转换器运行收据。native_execution_eligible=false，PRE=HOLD，无 registry/run。真实转换及每个故障点/重开行为均 NOT_EXECUTED，未知 DB 不接纳、不自动迁移。

## R：R17 的最短场景与明确残余

本轮新1.1初始 fixture 的 source manifest、Graph 都只有 question-a、一个目录、两个可投影区域，snapshot 无题/框。冻结未改 A02 planner 的255–287行在真实 PRE/TARGET=PASS、配置/能力/当前 snapshot 检查通过后，每个 Graph question 产生一个 CREATE_FRAMES，因此**条件成立时动作数为1**；action_id 按279–280行 plan_id/question/graph/snapshot 摘要计算。本轮手写的原格式计划仅作此静态投影说明，没有执行 planner，也没剪裁旧三动作计划。

未来最短原生证据：获批 INITIAL 实际生产/接纳→新 TARGET→未改 planner 的一动作计划→真实 intent 后 UNKNOWN 且尚无原 receipt→只读恢复终局 head(original_receipt=null)→同 intent/fact 晚到完整单 action receipt→独立报告读→新 POST/Batch；保留 UNKNOWN，旧头不改，PENDING/NOT_SUBMITTED，不重放旧尾。

**这条完整路径当前 BLOCKED：** 冻结 planner 的 observation bridge 在308–309行明确拒绝非1.1计划，而本候选新初始/新 PRE 是1.3，旧版又只读。新版本如何给未改 planner 供输入、并让其输出在新 profile 下合法消费，尚无批准的 projection/adapter 协议。不能把本轮手写计划、旧 stub 或版本 reseal 当作可达性证明。调度需选择另行明确版本投影/接纳合同，或另批 A02 bridge 兼容范围；未选择前不启动原生 R17。此处只证明单题循环数量，不证明整体运行可达。

R1 多头/不同 snapshot 的表达包保持原字节、继续只作值层模型；当前首 UNKNOWN 即停，不能伪造同计划多头历史、跨计划/scope 聚合或续旧尾。分层不豁免原 R17，也没有新的功能通过结论。

## E：原件、过程记录和未来证据

历史 NOT_RETAINED 按调度决定作为不可修复限制保留，不改成通过、不重建。所有新静态运行启动前预登记 argv/cwd/脚本SHA/限时，stdout/stderr 先建持久文件再启动子进程，finally 保存原始退出/PID/alive。后续 runner 同时保存 entry/helper 源码快照。首 check-01 的脚本只登记 SHA、未保存当时源码快照；其失败候选、原始两流和退出均保留，不能声称那份源码原件齐备。没有重建冒充原件。

真实功能阶段仍需新的持久 target/storage 前后证据、真实 reads/receipts、并发/崩溃/UNKNOWN 核对、进程树 containment 及业务读回。本轮仅结束自己的同步静态子进程，无后台任务、native session 或全系统扫描。字段重置专项保持 NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION，不能列入后续测试。
