# A03 P2-R8-R3 POST_HOLD 有界独立验收

2026-10-18（Asia/Shanghai）。**POST_HOLD 三处衔接修复及本报告列明的 local、N1–N5 子范围有限 ACCEPTED；整个 A03 仍为 REWORK，I01 不释放。**

从 exact target 导出的未改动产品与最终驱动，在全新双库、全新 run id 中按依赖独立执行 local→N1→N2→N3→N4→N5，各一次，六组均通过。N1 的正式 receipt/progress/POST/Batch 与 N2 两次真实 POST_HOLD 接纳、真实过期及保留门禁另以自有 immutable 数据库副本和原字节核对。没有只用作者通过数作结论。

**原 N7 保持 FAILED。** 已证实旧 target 入口实际拒绝 native 库；本次失败是新增驱动要求精确外层 `TARGET_STORE_VERSION_UNSUPPORTED`，而已有包装返回 `TARGET_STORE_CORRUPT`。现有书面合同没有规定这一外层 symbol，仓库内未找到依赖该精确 symbol 改变恢复/重试/迁移决定的调用方，故归为新增诊断断言过强，不预设必须修产品。包装造成的程序可见错误分类差异是真实行为，也不能据此宣称库损坏。N7 未达初始化中断分支、N6 均保持 NOT_RUN，本轮未重演 N7 或变体。

被审 target `d9ed692db9ab8e9277f8ffd09e040451e8b8f65f`，派发键 `A03:review:P2-R8-R3-post-hold:d9ed692db9ab8e9277f8ffd09e040451e8b8f65f`。未委派、未联系 B/执行者，未改用户 model/thinking、执行工作树、旧证据或调度 state，未自记 INTEGRATED。

## 固定输入与保全

| 输入 | 提交或 raw SHA256 |
| --- | --- |
| 审阅 workflow | `c728ce1587cb68a22a212cb48d71facf584ec426` |
| 审阅交接单 | `11beab27fb6782a108509a53ce0f68b606bda22b70e51f1b13d16b829a04cdd2` |
| base | `58d8a64734271d15654bb00b03d760f0f3eccd10` |
| 产品/驱动提交 | `13c8a766124ac45a91fa3edfa22de7df1e033c3e` |
| target | `d9ed692db9ab8e9277f8ffd09e040451e8b8f65f` |
| 执行 workflow | `b79b12fe6a82f9d88b6533b54aea016c4f67f60b` |
| 执行任务 | `8bb76c2cd713ec9af5386f3dcd547f443bbef42d6d4d19fc603ef0fcf5bd6a29` |
| 执行报告 | `472ad5c6bdd2068ee178a36566d4d321aa4af0d9fe9fb7216ca26019c8182099` |
| 执行 manifest | `a094d8a73d68273afd58afe0f6d4f4b7ffb4e1a0be3e5721dfef803cf181f91c` |
| 作者 process-release | `4d9b305aef3a5429005d496af68f36bf268d9ac4b68495c40e89b3e55c941dcf` |
| 原 N7 stderr | `0c5670e4e345ad9c55020d83851ea971c0dbc4a865899b425c15241847706fc5` |
| 调度交付前检 | `86b34c1c0cf0cee47744710b9ebab89cc6b65e9ee6136af5a2122de0ee77df7c` |

使用命令级 `git -c core.longpaths=true`、`ls-tree` 和二进制 `cat-file --batch`，核对 mode/type/blob、blob SHA1、长度和 raw SHA256，未经 checkout EOL 转换或合浮动主树。884 个 manifest 条目及自身、885 个变化路径和六项原输入 pins 全部吻合。base 的 30,285 个旧条目中 30,282 个不变，只有 native.py/profile/adoption 三个允许路径改变。

见 [交付字节索引](../evidence/A03/review/P2-R8-R3-post-hold/delivery-byte-index.json)、[678 项必要导出](../evidence/A03/review/P2-R8-R3-post-hold/input-index.json) 和 [一项原 N1–N7 标准补充输入](../evidence/A03/review/P2-R8-R3-post-hold/supplemental-input-index.json)。独立工作区含 68 个正常产品包文件、最终两个驱动、固定 R3 夹具、N5 所需的确切静态数据及仅作登记摘要的 inputs.json，共 121 个种子文件；没有复制作者成功库/validation 作为前序。

5,229 个旧 A03 审阅/报告文件以路径/长度/raw SHA256 的有序集合摘要保全，封存前再核对，见 [历史保全](../evidence/A03/review/P2-R8-R3-post-hold/historical-preservation.json)。旧 R7、R8、R8-R1、R8-R2 原件和失败均未改，没有复制历史全集。根工作区原 `mermaid-diagram.png` 保留。

## 三处修复与原门禁

独立阅读 [native.py](../evidence/A03/review/P2-R8-R3-post-hold/isolation/workspace/src/annotation/runtime/storage/native.py) 的 `_pre_lease`、`_post_hold_event` 与三个实际调用点：`begin_native_pre`、`NativeRegistry._current`、admit_pre 提交事务。三者均调用同一受限辅助，提交前再次核对当前性。

- `_pre_lease` 继续调用未改动的共享 `_lease`，保留 ACTIVE、PID/instance、owner/generation 校验。POST_HOLD 例外显式扫描全书 pending，有未解决义务即 BOOK_WRITE_PAUSED；它不是清 hold 或普通写入许可。
- 活跃 hold 必须来自不可变事件，target key、registration、source、scope、store、session 与当前登记一致。已登记运行还核对 exact hold_id、hold Resource 实体和已登记的 head；两个 head 都与实际事件 hash 对应。
- 运行观察/快照、输入原摘要、资源清单、五项实际比较和提交状态仍逐项核对；60 秒持久窗口、2 秒观察上限和读前计数未改。没有仅凭事务外检查接纳。
- INITIAL/普通写入保留原 hold/pending 禁令。投影、producer、合同四项守卫、Schema、版本/角色和根依赖未变。六份 schema、23 项 implementation pins 均核对原字节。

| 唯一旧产品变更 | target raw SHA256 |
| --- | --- |
| native.py | `c3e2f01ccbfb7b64c49a5272eb51ffbe2f6af8c8abb5a51c4c9c6965166b902a` |
| native profile | `023078c2a8bdfd1f3cc80eb6effdfc31010284464584218cbb77f3c4583c921a` |
| native adoption | `24d6529f2fcb9a386b0c52ab46f7551ee8c8701350351c88b241621fdec4477f` |

profile 只有 native implementation pin 改变，adoption 只有 profile SHA 改变；逐字段比较没有其他变化。详见 [静态核对及 diff](../evidence/A03/review/P2-R8-R3-post-hold/static-review.json)。

## 一轮独立运行及正式边界

工作区为 `D:/1800/docs/evidence/A03/review/P2-R8-R3-post-hold/isolation/workspace`，run id 为 **`review-r3-31803881c16a`**。validation 在首次启动前不存在。正常 Python import 的实际 module.__file__ 均在该工作区 src，driver 在该工作区 tests；没有导入执行树。每组前后 121 项种子 raw bytes 均与 target 一致。

实际 storage/native 导入路径为：

`D:/1800/docs/evidence/A03/review/P2-R8-R3-post-hold/isolation/workspace/src/annotation/runtime/storage/native.py`

最终主驱动 SHA256 为 `02acb22f395f380528130166ca8ae4637e3303c73f6496d9da4166b5050a1467`，local 驱动为 `2b183879068beb22eefb1922c7353d16117b35b9c725ae74b7eeee3e58d7a41f`，原字节未改。各组实际导入记录和 entry-source 快照分别保留；独立运行汇总见 [six-group summary](../evidence/A03/review/P2-R8-R3-post-hold/independent-run-summary.json)。

| 独立组 | 父 PID / exit | 实际范围 |
| --- | --- | --- |
| local | 21552 / 0 | 正常 API 产生真实 pending；无 hold 的 POST_HOLD、旧 generation、pending 精确拒绝，permit/effect=0。 |
| N1 | 7440 / 0 | 完整固定合成恢复链，效果子 PID 19840 exit87，真实效果屏障；正式 receipt/progress/POST/Batch。 |
| N2 | 11792 / 0 | 承接本轮 N1 库；两次 POST_HOLD 接纳、正常 owner/head 推进、真实过期和普通写入拒绝。 |
| N3 | 69920 / 0 | 五个原定语义控制，各只出现对应比较项 FAIL。 |
| N4 | 46172 / 0 | 缺少、序列化、他属 handle 与他属观察精确拒绝，两个控制库无 permit/effect。 |
| N5 | 61200 / 0 | 实际 1.1 JSON 读取、R7 静态 1.3 校验和七项 native authority 拒绝。 |

六组各一个固定 unittest 方法、各一次，无失败后重跑。N2 使用 120 秒父 watchdog，实耗 **68.25 秒**，没有改变产品窗口/观察预算或时钟。独立 N6/N7、最小测试变体及兼容全套均未运行。

作者冻结库和独立新库分别只对自有复制件建立标准库 `mode=ro&immutable=1`、query_only 连接，quick_check 均为 ok，读取前后及原导出摘要一致，临时副本已清理。没有连接作者原库，也没有在读回阶段调用 native API。

| N1 主场景冻结库 | runtime raw SHA256 | target raw SHA256 |
| --- | --- | --- |
| 作者原件 | `fc712e89f6468dfbb32523198fd8c39c1a21a27b93b22bf413b6d1ccb06b8e03` | `d65c27010afb010237cc3192c1b83e30245c94ea1335bb09607e4336b88c1f57` |
| 独立新库 | `33819382ea7bca7ed6b36940d3f841604168354ffda138440bc5b830ac0df5ef` | `19f1bf9d7dd4c8bfdbb2bfcc3d218bbb0b85196a8534931f936515f78dcfe86f` |

主场景独立 runtime 最终有 1 plan/action/intent/permit/resolution、3 PRE runs、1 report read、25 个正式 Artifact；target 有 1 effect、7 observations。作者/独立分别见 [作者数据库](../evidence/A03/review/P2-R8-R3-post-hold/author-database-review.json)、[独立数据库](../evidence/A03/review/P2-R8-R3-post-hold/independent-database-review.json)。local/N4 控制库另外独立核对，未用主场景结果代替，见 [独立控制库](../evidence/A03/review/P2-R8-R3-post-hold/independent-control-database-review.json)。

### N1 正式提交

从 SQL registrations、artifacts.ref/path、intent.receipt 和实际资源原件定位：PRE 为 ADMITTED，accepted_plan 绑定实际单动作 CREATE_FRAMES；唯一 permit 为 CONSUMED；效果恰好一次，子 exit87 的 marker/PID/放行与父独立计数一致。原 UNKNOWN 和 null 原回执保留，终局 head 为 RESOLVED_APPLIED、original_receipt_ref=null。

晚到 receipt 同时位于 SQL artifacts、当前登记包及 intent.receipt，完整四元组一致；两个正式 material progress 的 plan/action/intent/attempt 和尝试证据与同一个原 fact 一致，仍为 MAY_HAVE_BEEN_ATTEMPTED，没有改写为 ATTEMPTED。独立新 POST/Batch 均正式登记，报告快照/观察与终局观察不同，durable report read=1。frame_structure=PASS，但内容 PENDING、submission NOT_SUBMITTED、Batch CONTENT_PENDING。

独立关键 refs 均 revision=1：

| 产物 | artifact_id / content_hash |
| --- | --- |
| plan | `plan-r8-r3-n1` / `59061ebd398deb518d9d430f7e822d6d14a5b9a97465233ed9c191e6b51c7608` |
| receipt | `executionreceipt-b0b14fd7663949219d5a2d37ec6cfe6b` / `74a3aa037063008d7b47da853a4b9b5e8a7e2b6c3eea299386f4b841680420aa` |
| terminal head | `resolution-71fddc0de3424235897f19ac3796df20` / `5ac66bc0499e339459f6db4dfc83376769d24cc7b685dbf56cd2ba8f3741a961` |
| POST | `native-post-13595e7011a249258a703cec2c8ccc6a` / `32e0b97f2f34fc9b71e149b434429419c8abcc247471f77418a4128ae48c95f1` |
| Batch | `native-batch-72f2e983bb6e4cab9eefda3f37663c5a` / `493c082b952b4055a9d173e22faff22764223e2bd6ece19406740d6aa7e1aba6` |

作者原件与独立运行分别按同一组自己编写的纯读取规则核对，未调用作者归档检查器作为业务结论。详见 [作者正式绑定](../evidence/A03/review/P2-R8-R3-post-hold/author-boundary-review.json) 与 [独立正式绑定](../evidence/A03/review/P2-R8-R3-post-hold/independent-boundary-review.json)。

### N2 的两个真实接纳与门禁

独立 hold 为 `target-drift-hold-29845abd98f44e5492a869ce8aa92db8`，两次均绑定同一实际 hold Resource：

`assets/runtime/5673232817ea8c91e402e9f3831e00f1ceade26ab1a936ad99bf005f2b9d4e39.json`

Resource 实体、hash、不可变 hold 事件及 target/registration/source/scope/store/session 逐项相符。整个事件链的 event_hash/previous_hash 与最终 book head 核对一致。

| 独立接纳字段 | 第一次 | 正常 release/claim 后第二次 |
| --- | --- | --- |
| run_id | `native-pre-0faaee22fc8d465ca6faf97fd89aed8f` | `native-pre-49d4c6f56f4c4c75a2caa316a7163d36` |
| generation / read_sequence | 4 / 6 | 5 / 7 |
| registered head sequence | 19 | 22 |
| head hash | `20da4e63f166140bbb5f4c4abef694ef12829ab14e8594aa8ed623072739aab7` | `4d688615dcdd2fa54b552e611f8a832aa91b296978eb55d2fcd46f26fcc4f2fc` |
| PRE id | `pre-r8-r3-post-hold-1` | `pre-r8-r3-post-hold-2` |
| PRE hash | `997f7b84d67b595a75540ef2b485469e72d8efcb978e6cbd820b1c1a430dfe3e` | `5bf19c81d70f3b801cd512c0408dcdd70197a1758aa9e43273c6f634de17f879` |
| observation_id | `native-observation-1c6a72d0e553442ca2678700a12b7603` | `native-observation-d978c0b070a54e50ada9955b62c9fecf` |

两个 durable row 均 ADMITTED、reads=1、accepted_plan=null；PRE/run resource/context、输入清单、raw SHA、五检查、确切快照及 target observations 表中的实际观察相同。它们不产生新计划/permit/效果。最终 hold 未清，原 head/UNKNOWN 历史保留。

| 独立控制 | 实际 code |
| --- | --- |
| reopened registry 的旧 INITIAL 私有证明 | NATIVE_ADMITTED_RUN_REQUIRED |
| held book 上 INITIAL | TARGET_DRIFT_HOLD |
| held book 普通计划接纳 | TARGET_DRIFT_HOLD |
| 正常 owner/generation/head 推进后的旧 POST_HOLD | OWNER_GENERATION_STALE |
| 新 POST_HOLD 已接纳后的普通写入 | TARGET_DRIFT_HOLD |
| 当前 hold PRE 真实过期 | NATIVE_PRE_DEADLINE_EXCEEDED |

第二 run.created=`1792263339.405663`，驱动实际等待至 created+60.1，父完成时间也晚于 created+60；没有改时钟/SQL 或把 watchdog 当产品期限。保持 hold、permit=1、effect=1。旧 run 的动态控制同时推进了 owner/generation/head，拒绝先发生在 owner/generation；本报告不把它扩大成单独 stale-head 变体实测。

这只接受**同一个 hold 下两个 exact head 的读取接纳**，不证明不同 hold-id 替换或合格流程清 hold，也不授予恢复普通写入。见 [独立 POST_HOLD 绑定](../evidence/A03/review/P2-R8-R3-post-hold/independent-post-hold-review.json) 和 [作者同范围复核](../evidence/A03/review/P2-R8-R3-post-hold/author-post-hold-review.json)。

## N3–N5 的有限语义

N3 固定驱动在内存中修改输入；不能把仍未改写的磁盘 initial.json 冒充实际负例。审阅仅为这一已授权调用添加非修改型 sys.settrace，保存 NativeSchemas.check 实际完成时的五份输入和比较器实际输入/返回值，没有增调产品函数。两处 canonical SHA 相同，schema 返回成功，Artifact 摘要独立重算一致，实际 PGM 字节与输入资产 SHA 相同。

五个控制分别只得到 `source_integrity=FAIL`、`structure=FAIL`、`answer_matching=FAIL`、`coverage=FAIL`、`policy=FAIL`，其余四项均 PASS。这些是具体比较项结果，**不是抛出的异常码**。它们到达直接语义比较层，未调用负例 PRE 接纳，也没有 N3 数据库；不宣称已完成每项负例的端到端接纳拒绝。实际内存输入见 [N3 trace](../evidence/A03/review/P2-R8-R3-post-hold/N3-readonly-trace.json)。

N4 使用两个正常生成且 ADMITTED 的独立 registry/store 场景。缺失 handle、序列化 run_id、他属 handle 均为 `NATIVE_RUN_HANDLE_REQUIRED`；他属实际观察为 `NATIVE_PRE_OBSERVATION_FOREIGN`。独立 SQL 对两库确认 plan/intent/permit/effect 均为 0，registry/registration 身份不同；没有将早期无关错误算作观察负控。

N5 七项实际拒绝均为 `NATIVE_CONTEXT_REQUIRED`：包括未签发 context、R7 selection、已校验静态 1.3 对象、实际读取的 1.1 历史 JSON，以及旧 role 描述。1.1 只作 JSON 历史读取，1.3 经 R7 static validator；**未调用或接受 1.1 archive-validator、未执行显式转换**。不把普通 JSON/静态描述升级为 native authority。

local 的真实 pending=1、permit/effect=0 也由独立 SQL 核对。N3–N5 原件、精确结果、控制库身份及实际资源摘要见 [有限控制核对](../evidence/A03/review/P2-R8-R3-post-hold/negative-controls-review.json)。

## N7：原失败保留，诊断预期不等于产品门禁失败

原栈明确为：persistent.py:335 先 reject TARGET_STORE_VERSION_UNSUPPORTED；ContractError 继承 ValueError，被 :342 的广义 ValueError catch 再包装为 TARGET_STORE_CORRUPT；驱动 helper 随后对外层 code 的精确断言失败。该原 stderr 的 raw SHA 仍为表中 `0c5670...06fc5`，原 N7 exit1/FAILED 未改。

本次只读判断分别如下：

1. **实际拒绝：是。** 版本检查在 session 构造和身份接纳前抛错，正常 return 不可能到达；不是 native target 被旧入口采用。
2. **损坏/重置或弱接纳：没有这项证据。** 已到达路径在业务写语句前终止，事后库仍为 native application/user version 与 adoption、effect=1。open 本身使用 mode=rw，不能称作只读 API；本轮没有调用它，也没有 N7 专属调用前/后原 hash 对，所以不扩大为任意 I/O 不变性证明。
3. **外层精确 symbol 的既有合同：未发现。** 冻结 V08/R14 要求未知格式拒绝、错误可定位、历史保持，不指定这个外层名称。对 frozen src/tests/相关书面合同的搜索，仅 persistent.py 内部分支和新增 N7 断言引用这两个完整 symbol。内层 VERSION 原因仍在错误链中。
4. **调用方影响：诊断差异可观察，但未证实业务资格变化。** recovery CLI 会输出 issues[0].code，因此外层 CORRUPT 会传给读码/显示者；现有仓库未发现以这两个精确 symbol 选择自动重建、迁移或重试的分支。正常 native observer 走显式 native bridge。不能据此保证所有外部消费者无精确依赖，也不能把 CORRUPT 当实际数据损坏诊断。

据此，这次失败归为**新增驱动的精确诊断预期过强**；不依据它预定下一轮必须修改 persistent.py。是否明确新的外层错误码合同或修正驱动断言，由调度据此决定，本审阅未改任何一方。原 N7 已到达 native 严格 reopen、旧 runtime 拒绝和旧 target 拒绝；初始化中断分支仍 NOT_REACHED，N6 未运行。见 [N7 只读分类依据](../evidence/A03/review/P2-R8-R3-post-hold/N7-readonly-classification.json)。

## 原 P2 覆盖映射与最小剩余

已逐项对照冻结原任务 V01–V10 和独立标准 R01–R18，并审查作者 p2-coverage-map；完整 28 项原文行号、实际到达、限定和未覆盖记录见 [独立覆盖映射](../evidence/A03/review/P2-R8-R3-post-hold/p2-independent-coverage-review.json)。没有将 N1–N5 自动换算为整个 P2，通过范围概括如下：

| 原项 | 本轮范围及仍缺内容 |
| --- | --- |
| V01 / R04 | 固定单动作、双库/跨进程实际效果与正式完成；非一般多动作/重复提交保证。 |
| V02 / R03 | 一处效果提交后 exit87；其他 intent/dispatch/readback/receipt 崩溃点未覆盖。 |
| V03 / R05 | 新鲜 MATCH 只读对账；ABSENT、部分/矛盾/截断/失败读回未覆盖。 |
| V04 / R11 | 多动作未尝试尾段及充分/不足 ABSENT 未运行；字段重置专项保持固定禁行状态。 |
| V05 / R07 / R10 | 一个真实 pending 拒绝；native 多 scope/run、跨书完整账本场景未覆盖。 |
| V06 / R06 / R09 | 正常 owner/head 推进、旧 generation/proof 与真实 expiry；双 owner 竞争、新 UNKNOWN/分叉循环未覆盖。 |
| V07 / R02 / R08 / R12 / R13 | 固定比较/authority 控制、同 hold 两次接纳与普通写入拒绝；完整错身份/摘要/授权矩阵、qualified clear/不同 hold 替换与 ABSENT 后新计划流程未覆盖。 |
| V08 / R14 | native reopen/旧入口拒绝已达；N7 原精确断言 FAILED，初始化中断及其他损坏/I/O/迁移控制未覆盖。 |
| V09 / R15 / R16 | 实际历史 JSON、static 1.3 与 authority 拒绝；archive-validator/显式转换、真实/ORIGINAL/OBSERVED 否定矩阵及 S01 未覆盖。 |
| V10 / R17 / R18 | 固定非零分母、新正式 POST/Batch、PENDING/NOT_SUBMITTED；旧报告复用/VERIFIED 篡改、零/未知分母、跳过与 max-attempt 边界未覆盖。 |
| R01 | 本次 frozen 输入/范围/原件保全和独立运行成立，不代表集成或跨侧确认。 |

后续最小接口闭合应围绕已有标准而非新增无限矩阵：N6 的完整 UNKNOWN 历史下 creation-anchor 重算/正式依赖控制；N7 未到达的初始化中断 fail-closed 分支；先按合同定清该诊断断言口径。若纵向入口要恢复 held book 普通写入，还缺原 R13/N2 标准下的合格清 hold/不同 hold 替换证据；只读 PRE 接纳不能代替它。

原任务还要求正常与明确未生效等可移植演示；本轮效果后 MATCH 单动作链不替代这些既有要求。多动作/ABSENT、native 多 scope/多书、双 owner 竞争、其他崩溃点、archive/真实来源否定、旧报告/分母/次数等广覆盖仍按映射保留，未豁免。本报告不自行挑选豁免或制定 B 内部任务；S01 与双方映射确认继续是独立依赖，I01 不释放。

## 过程身份、失败与释放

作者 34 组已登记进程的 argv/cwd、输入/产品摘要、原输出、PID/退出/timeout/alive 已核对。C01 三个 exit1 为预期缺引用拒绝，N1 子 exit87 是预期效果后退出，N7 父 exit1 是真实断言失败。作者 N4 在 N7 失败前已启动、失败后才完成，由 started/end 时间证明，不是失败后重跑。

最终 C01 70、A02 52、R7 13 原日志均 OK，无 skip；只读取现有结果，未重跑全套。各组产品 source-index 同为 `e78f63e7d4f05f8e132cb24e61c4072bb897d49243e173376998fd397505c5ae`。

**产品相同不等于所有驱动全文相同。** 作者 N1/N2 实际主脚本快照 SHA 为 `501911ae33a741cf2d9cefc60995a12adb6b3ee4197d369629ff521847453659`，最终为 `02acb22f395f380528130166ca8ae4637e3303c73f6496d9da4166b5050a1467`。差异是当时尚未运行的 N4–N7 精确拒绝/输出收紧；已核对实际 N1/N2 方法、此前全部 helper/prefix 和 main 入口相同。本次六组独立运行使用最终驱动，不将两个原快照伪记为 byte-equal。详见 [作者过程核对](../evidence/A03/review/P2-R8-R3-post-hold/author-process-review.json)。

审阅元数据检查有三次首轮失败，均保留脚本快照、PID、raw stdout/stderr 与退出：脚本快照等同假设、workflow 文档路径路由、Windows 路径筛选。纠正后仅重新核对字节/已保存行，没有重跑任何产品组。另一个 PowerShell 只读诊断查询在解析阶段报错，仅保留工具转录，未取得 PID/分流原输出；[该限制](../evidence/A03/review/P2-R8-R3-post-hold/reviewer-query-preparation-failure.json) 单列，不伪造 raw 过程证明。

独立产品六组均首轮通过，无产品失败后重跑。N3 的审阅 trace 只保存同一次调用的实际输入/返回，不修改对象或多调用比较器。所有已登记自有检查及 10 个嵌套子进程已 wait/退出；释放只依据自有 Popen 与原完成记录，不进行当前 OS/profile 扫描，见 [自有释放](../evidence/A03/review/P2-R8-R3-post-hold/process-release.json)。

## 封存与边界

仅新增本报告和 R3 审阅目录；exact 输入、原输出、实际 import、SQL/Resource 绑定、N7 分类/覆盖映射及 [完整 SHA256 清单](../evidence/A03/review/P2-R8-R3-post-hold/sha256-manifest.json) 统一保留，只排除清单自身。[最终核对](../evidence/A03/review/P2-R8-R3-post-hold/final-verification.json) 复核源/种子未变、281 个独立运行产物、旧历史摘要、完整目录集合与进程记录，不再运行功能。

零网络、真实平台、浏览器、凭据/profile、OCR、模型/付费 API、安装、A05 题22重放、推送或 B 联系。字段重置专项始终 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`，不复跑、变形、委派或建议重测。原 R7/R8-R2 有限接受分别保留。最终是**POST_HOLD 与本轮 local/N1–N5 有限接受，N7 原失败保留、N6/初始化未达项保留，A03 整体 REWORK，I01 未释放。**
