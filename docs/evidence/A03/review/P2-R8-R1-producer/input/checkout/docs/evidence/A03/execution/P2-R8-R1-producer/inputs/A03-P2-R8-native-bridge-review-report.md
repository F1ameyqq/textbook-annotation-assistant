# A03 P2-R8 原生桥接冻结失败独立核验

结论：**REWORK**。被审 target 为 `fa6edeb7e9dd0c9502781747e5fce012931d9441`。已独立确证 N1 的 producer/schema 合同缺陷：`coverage_for` 返回二元组，producer 却将整个二元组作为对象字段 `coverage`，经原生封签的 JSON canonical 转换成为数组，无法匹配 PRE 的对象合同。第二次 N1 的真实父、子 stderr 均证明实际停在该层，未完成 PRE 封签或接纳。

本轮只核验冻结字节、静态源码/Schema、历史进程日志及 SQLite immutable 副本；**未重跑 N1，未运行 N2–N7、native API 或任何兼容测试**，没有修产品或启动目标效果。R7 原只读 codec 的既有 ACCEPTED 范围保留；R8 不能接受整个 A03，也不释放 I01。

## 冻结身份与范围

2026-10-17，继续原独立验收对话，未委派、未联系 B/执行者，保留用户 model/thinking。未修改执行工作树、调度 state 或旧证据；未提交、安装、联网或推送。

| 输入 | 确切提交或 raw SHA256 |
| --- | --- |
| 审阅 workflow | `267bce2b18b04c75d0737da06052db2b31ba01fa` |
| 审阅交接单 SHA256 | `4af279d3be77f3755afda92b7f5efafdbc2b331c039e51ab93c0cb0b97ed5a0d` |
| base | `8ad45dd07214ae406a3fab28d76a4b5abd6eef03` |
| 合同桥接提交 | `352b1475fff85a034b839a712ee499ba4c1ec5e6` |
| runtime/producer 候选提交 | `334577d922d224789191a8b4d7127513692ada95` |
| 最终 target | `fa6edeb7e9dd0c9502781747e5fce012931d9441` |
| 执行 workflow | `873d8151000430fc79e63b312ccd21978fc15f79` |
| 执行任务 SHA256 | `b7dbf94ff06d8ba272b1bd20bf61afbe09fa1dd99c501dcb70f865ab36737721` |
| 执行报告 SHA256 | `2d482c8c2b20985496cf0b07db65aaa68fccc3acfae6e363af0c3d34d6f0372d` |
| 执行 `manifest.json` SHA256 | `c9d195c5a97ef6293cece1627372ecf8f7404d4537bac9a9bda5e298841f0c7e` |
| 作者释放记录 SHA256 | `58f0b7cbfd9d747144f24df05c4852714ad40417575486b92c92cc11eea7a98b` |
| 作者 bounded-outcome SHA256 | `6c5c68c5510bcb5cd2d7fb68b4e8bbe2d36fc8a8f093191652245b0233d9e5a7` |
| 调度前检 SHA256 | `a416e8ac974ffbc9ca6f78ac22a44d54fe3c9d7d6c2d043bba68b8e59ec311b8` |

raw Git 核对使用命令级 `git -c core.longpaths=true`，未改全局设置。二进制 `cat-file --batch` 核对 blob SHA1、长度及 SHA256，独立核对 462 个 manifest 条目及 manifest 自身、89 个原输入 pins；未执行作者检查器代替审阅。上述三个交付提交的父子链依次回到 base。

[交付字节核对](../evidence/A03/review/P2-R8-native-bridge/delivery-byte-index.json) 确认：base 的 28,750 个 tree entries 中，28,738 个 mode/type/blob 不变，仅 12 个允许的共享旧路径修改；本轮共 463 个改动路径。pyproject 保留原内容，仅附加 a03_native 的 package-data，依赖与版本未改。R7 产品/数据、旧 Schema/profile/API、旧测试/样例/证据均不在这 12 个例外中，原字节保留。

隔离导出 296 个必要文件，见 [输入索引](../evidence/A03/review/P2-R8-native-bridge/input-index.json)。另按确切 raw Git 导出五个 recovery 快照和五个被新 profile 固定的既有 runtime 源文件，共 10 项 [补充输入](../evidence/A03/review/P2-R8-native-bridge/supplemental-input-index.json)，没有重写初始索引或把它们混记为作者新增 pins。未复制历史全集；未使用的重复 product-snapshot 仍由完整 463 项 raw 索引证明身份。

根工作区已有 3,877 个 A03 审阅/报告文件，以路径、长度、原 SHA256 的有序集合摘要保全并在封存时再次核对，见 [历史保全](../evidence/A03/review/P2-R8-native-bridge/historical-preservation.json)。旧 R7 报告与证据未改。未触碰根工作区已有的 `mermaid-diagram.png`。

## P1 缺陷：PRE coverage 字段收到二元组

最短定位如下，全部指向冻结导出源码：

- [synthetic_precheck.py](../evidence/A03/review/P2-R8-native-bridge/input/checkout/src/annotation/quality/synthetic_precheck.py) 第 121–130 行，尤其第 **122** 行：`'coverage': coverage_for(bundle, graph)`，然后交给 `make_artifact('CheckReport', ...)`。
- [targetcheck/__init__.py](../evidence/A03/review/P2-R8-native-bridge/input/checkout/src/annotation/quality/targetcheck/__init__.py) 第 92–109 行：构造 coverage 字典、计算 complete 布尔值，第 **109** 行明确 `return coverage, complete`。这是已有公共调用约定。
- [新 exchange Schema](../evidence/A03/review/P2-R8-native-bridge/input/checkout/src/annotation/contracts/a03_native/data/schemas/exchange.json) 的 `/$defs/AmendedCheckReport/properties/payload/oneOf/0` 为 PRE_APPLY；必需的 coverage 引用 `#/$defs/Coverage`，其 `type` 为 `object`。其他分支的 stage 是 TARGET/POST_APPLY，不能接纳 PRE_APPLY。
- [原生封签](../evidence/A03/review/P2-R8-native-bridge/input/checkout/src/annotation/contracts/a03_native/__init__.py) 的 `seal_native_artifact` 先 canonical JSON 再解析，二元组因此成为二元素数组；`NativeSchemas.check` 选择 AmendedCheckReport，并在计算有效 content_hash 前检查 shape。

因此，凡 producer 到达该行，coverage 均是 `[coverage_object, complete_bool]` 而不是对象。对本次固定 N1，PRE_APPLY 分支因 coverage 类型不符失败，其他 payload 分支因 stage 不符失败，最终汇总为 `$/payload: SHAPE_oneOf`。这是确定的调用方合同错误，不能通过放宽 Schema、修改公共 helper 返回约定或将质量 PASS 当作接纳绕过。

第二次 N1 父 PID **63432**、子 PID **23008** 均实际 exit **1**、无 timeout/alive，均未释放效果屏障。子调用链是：

`setup_pre → produce_a03_pre_run → make_artifact → seal_native_artifact → NativeSchemas.check → SHAPE_oneOf`

父测试原本要求效果后退出码 87，实际收到 1，因此父测试也明确失败。原始 [父 stderr](../evidence/A03/review/P2-R8-native-bridge/input/checkout/docs/evidence/A03/execution/P2-R8-native-bridge/runs/N1-local-fix/stderr.txt) 和 [静态核对结果](../evidence/A03/review/P2-R8-native-bridge/static-review.json) 相互印证；没有用早期无关异常冒充此项阻断，也未再次运行失败命令。

影响是 N1 在 PRE 封签前被阻断，尚无可接纳 PRE；TARGET、计划、intent、permit、UNKNOWN 恢复、晚到回执及 POST/Batch 均不能由该记录证明通过。没有证据支持“改这一行后整个 A03 即通过”。

## 首次失败和唯一局部修复的边界

第一次 N1 的子 stderr 确为 `$.artifacts[1].content_hash: HASH_MISMATCH`，调用停在初始 `store.bridge_for → _validate_value → recovery._legacy_projection → C01 validate_bundle`，早于书籍登记及目标观察。原始 [父 stderr](../evidence/A03/review/P2-R8-native-bridge/input/checkout/docs/evidence/A03/execution/P2-R8-native-bridge/runs/N1-initial/stderr.txt) 保留。

独立读取 fixture 确认原 EvidenceBundle 的 bbox 为整数；既有 C01 `models.py` 使用 `List[float]`。初始私有投影先按整数数据封签，再经 C01 类型规范化为浮点，导致规范化后的摘要与投影摘要不符。这一解释与实际 artifacts[1] 失败及源码顺序一致；审阅者未执行类型模型或重封签原输入。

两轮真实 product-source-index 的差异恰为三条：

| 路径 | 唯一修复前 raw SHA256 | 修复后 raw SHA256 |
| --- | --- | --- |
| `contracts/recovery.py` | `5e5586814b37ed447767e05e2a821ca82eab1b13ad8ea1505f182fbe5ba1c905` | `691e847171004c25b160458e675a6bb23a42426d83878d6a320f29714a9fb5ab` |
| 新 native profile | `0e6c18b4eb91f6080569b52f7aaf216190ec197a28aee8b0b62c5cfc5c643465` | `29e9d78190dd702fb944d99d74bd9c40426618b477ed16088422b9b89c45219b` |
| 新 native adoption | `d27f14976c3043ff11d4a436a6b00515dedacdb97ff190638810989d73034694` | `f0e793d635b5072b7955259f15cc7b389e99c02adbbae4bb98e21a966b1eb6b7` |

recovery 的实际 diff 只新增八行：在 `ctx.native` 为真时，先用 C01 ExchangeBundle 将这个私有业务投影规范化，再计算投影摘要；未删除其他行。profile/adoption 仅随实现身份更新。生产器、targetcheck、native schema 及 N1 驱动未在两次失败之间修复；producer raw SHA256 始终为 `ffdfc0f73d969c19b489aa9342dae6b73aa3f8d80df5382dba57ee07a25606b0`。

最终 recovery 与第二次运行快照相同。三组兼容测试的 recovery 快照与第一次 N1 相同。八行 diff 和三条完整来源差异已写入 static-review；当前六份 Schema 和 23 项 implementation pins 均独立核对吻合。修复推进过原 HASH_MISMATCH 后，第二次才暴露上述独立 coverage shape 阻断，不能将两次失败合并成一个已解决问题。

## 冻结 SQLite 与实际持久边界

只从冻结 raw Git 导出三个必要 SQLite 文件，复制到自有临时目录，以标准库 `sqlite3` 的 `mode=ro&immutable=1` URI 连接，并启用连接级 query_only。未对执行原库建立连接。每个副本读取前后及源导出文件的 SHA256 相同，quick_check 为 ok，临时目录已清理。SQL 和全部计数见 [独立数据库核对](../evidence/A03/review/P2-R8-native-bridge/database-review.json)。

| 冻结库 | raw SHA256 | 独立读取结果 |
| --- | --- | --- |
| bounded-01 runtime | `6f3f7ae5e9858deb59b266a7db9845fe71c52dbea2ff823e58a9b48da20b7935` | books/registrations/native_pre_runs/plans/intents/permits 全为 0；没有首轮成功前缀。 |
| bounded-02 runtime | `9315a5e83150d7ba5e824d23c3ba4cceede5594d8325b0253afeddcabecc96b5` | books=1、registrations=1、native_pre_runs=1；唯一 run 为 `OBSERVED`、reads=1、pre_ref=null、run_sha=null。plans/intents/permits=0，creation anchors/report reads/resolutions=0。 |
| bounded-02 target | `710c82c4ba2051572d53131169eb958680e840b328d787aeb8ef9a55c753aefd` | observations=1、effects=0；不存在计划目标效果。 |

两个 runtime 的 application_id 均为 1093678162，target 为 1093678164，三库 user_version 均为 4。这只核实冻结前缀身份和状态，不是 N7 严格重开/中断/旧库拒绝验收。

另直接读取实际 run resource，raw SHA256 为 `6845ce79b980ff45dd5d03fb1cf8d0625d03bc3e527aa728ca6c868577452d58`，不是只读取作者的 bounded-outcome 声明。该原件明确 `ACTUAL_CHECKS_COMPUTED` / `RUNTIME_RECHECK_REQUIRED`，INITIAL hold 三字段均 null，五项检查都记录 PASS；producer 实现摘要和五个链接 Resource 的实际字节/hash 一致。审阅者只核对已保存数据，未重新计算五项质量结果。

两个已持久 package 分别有 4、5 个 Artifact，种类仅 SourceBundle/EvidenceBundle/QuestionGraph/PlatformSnapshot；canonical Artifact hash 与 run 的实际输入摘要吻合，没有 PRE/TARGET/ApplyPlan/receipt/POST/Batch。详见 [实际产物边界](../evidence/A03/review/P2-R8-native-bridge/artifact-boundary-review.json)。结合 SQLite 的空接纳字段，五个 PASS 只能称为**已计算、未接纳**，没有当前写入资格或效果证明。

## 兼容性与 28 个历史进程的准确口径

[进程与兼容证据核对](../evidence/A03/review/P2-R8-native-bridge/process-and-compatibility-review.json) 逐一核对 28 个 preregistered/started/completed、argv/cwd、限时、PID、原 stdout/stderr；原记录自带日志摘要者逐项比对，其余 raw 日志由冻结 manifest 和独立摘要绑定。28 个记录均表示已 wait/退出且无 timeout/alive。此结论仅限冻结历史记录，未扫描当前系统、profile 或执行工作树。

三组原兼容测试各一轮的原 stderr 分别为 C01 70、A02 52、R7 13 项且以 OK 结束，无失败或 skip。它们的 product-source-index 相同，均为最终 native-only 投影修复**之前**的快照；因此只能证明那个修复前候选的对应旧入口回归，不能据此宣称最终候选的全部兼容性或 N1–N7 已通过。本轮未重跑兼容测试。

C01 下的三个 exit=1 均经原始 JSON stderr 和原测试源码对应确认：

| 子进程 | 实际拒绝 | 原测试用途 |
| --- | --- | --- |
| child-01 | `MISSING_REFERENCE`，`$.artifacts[4].payload.questions[0].fragment_ids[0]` | `invalid.json` 中主动设置 missing-fragment；原断言要求非零及 fragment_ids 定位。 |
| child-07 | `MISSING_REFERENCE`，`$.artifacts[5].payload.questions[0].directory_id` | 平台问题目录引用不存在；原断言要求非零、valid=false 和确切路径。 |
| child-08 | `MISSING_REFERENCE`，`$.artifacts[8].payload.actions[0].target.platform_question_id` | action 引用计划快照中不存在的平台问题；原断言要求同上。 |

所以它们是预期负控，不是真实兼容测试失败。相反，两次 N1 的父、子四个 exit=1 均违反 N1 的 87 退出码/效果屏障要求，是真实失败。不能只看父进程 exit=0、子进程 exit=1 或通过数作统一判断。

审阅自己的 `process-review-01` 曾因不同记录使用 `timeout` 与 `timed_out` 两种键名而 KeyError；保留原脚本快照、原输出和 exit=1。检查脚本随后显式识别两种已存在的记录格式，并要求实际字段存在，`process-review-02` 通过；未把缺失值默认为 false，没有重跑任何候选或作者命令。这是审阅记录器适配，未改产品或作者证据。

## 最小返工范围与必要后续证据

下一次明确冻结返工应以这个 producer 调用合同为最小范围，不在本次已用完唯一修复的交付上继续修改：

1. 在 `quality/synthetic_precheck.py` 调用处明确解包 `(coverage, complete)`，只把 coverage 对象放入 PRE payload；对 complete 的处理须与已有 coverage 比较、PASS/HOLD 语义一致，不能丢失完整性判定或借机增加写入资格。保留公共 `coverage_for` 返回约定和现有 Schema。
2. 随实际修改更新 producer implementation pin、新 profile 和 adoption 的确切身份；不改 R7/旧 Schema/profile/API，不通过放宽 oneOf/coverage 类型、重封签旧原件或写入成功 SQL 行使链路通过。
3. 新冻结材料须补齐针对该调用的对象形状、完整性/失败决策及真实 PRE 封签与 runtime 接纳证据，再按新任务的授权核验原 N1 后半段；必须实际证明目标效果恰好一次及完整恢复产物，不能用五项已计算 PASS、预期退出码或候选测试代码替代。最终候选的相关兼容证据也不能沿用为“修复后已运行”。

本次没有执行以上修复或后续验证。N1 的 PRE 接纳之后直至独立 POST/Batch 全部仍未到达；N2–N7 仍为 `NOT_RUN_AFTER_INDEPENDENT_BLOCKER`。冻结 tree 中只有 N1 的两次失败前缀，没有 N2–N7 成功目录、before-dispatch 或效果屏障产物。严格新库重开、INITIAL/POST_HOLD 生命周期、creation-input anchor、拒绝控制、单次 permit、UNKNOWN 只读恢复和迟到 receipt 均不得据本报告接受。

原 P2 V01–V10/R01–R18 未获豁免，I01 继续关闭，跨侧合同未共同确认。字段重置专项保持 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`，不复跑、变形、委派或建议重测。

## 封存

仅新增本报告和 R8 审阅目录。独立脚本、输入索引、原输出、自有 PID/限时/退出，以及唯一审阅脚本失败均保留。见 [审阅进程释放](../evidence/A03/review/P2-R8-native-bridge/process-release.json)、[最终核对](../evidence/A03/review/P2-R8-native-bridge/final-verification.json) 和 [完整新增 SHA256 清单](../evidence/A03/review/P2-R8-native-bridge/sha256-manifest.json)，清单只排除自身。封存完成后再次按完整目录集合逐字节核对清单，未运行产品测试。

本轮零网络、平台、浏览器、凭据/profile、OCR、模型、付费 API、安装或目标写入；未重放 A05 题22，未自记 INTEGRATED，未修改调度 state。最终结论仅为上述确切 target 的 **R8 REWORK**，R7 已接受范围单独保留。
