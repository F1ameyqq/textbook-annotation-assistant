# A03 P2-R8-R4 剩余范围独立验收

2026-10-18（Asia/Shanghai）。**N6 的完整 UNKNOWN 历史下创建输入重算、一个正式 PRE 依赖缺失控制，以及 N7 的一个 runtime 初始化中断分支有限 ACCEPTED。新 N1 必要前序首轮通过并核对正式边界。A03 整体仍为 REWORK，I01 未释放。**

本轮仅运行 exact target 的 N1→N6→N7 初始化，各一次，无产品失败或重跑。原 R3 N7 的 FAILED 和“新增精确外层诊断断言过强”分类永久保留；本轮初始化分支通过不把原失败改为 PASS。未调用原失败的旧 target 入口或变体，未改 persistent.py。原 R3 local/N1–N5 有限接受只静态引用，不重复其他组或兼容套件。

## 固定输入与保全

派发键 `A03:review:P2-R8-R4-remaining:435aaee2d140e82d3237ce8902d594a1aee70aad`。不委派、不联系执行者/B，保留用户当前 model/thinking，不修改根调度 state、执行工作树或旧证据。

| 输入 | 提交或 raw SHA256 |
| --- | --- |
| 审阅 workflow | `74b4fbc9c2778a516cb9f7cadd7e3b3ca5faa639` |
| 审阅交接单 | `b239748cdd5b875b8870f4fa1fdaa679314a46dacf5e2003a17bfe938a7f09bb` |
| base / 未变产品 | `d9ed692db9ab8e9277f8ffd09e040451e8b8f65f` |
| 唯一 target | `435aaee2d140e82d3237ce8902d594a1aee70aad` |
| 执行 workflow | `cb9c8f76e9eae40a8fda042c196705d7258b5107` |
| 执行任务 | `5a93ea9012ad8d9d2f69e622235051cbf1ced23922e1e6fc021c4443657e184b` |
| 执行报告 | `eaba2a007216999ca70e506609a50a049e89b48b86b4c39af0e51dfa50e9e324` |
| 执行 manifest.json | `337ba0aa1ce0fd8a70032a6b2580797752f0e4ea5b0216b56913dae2ebd91f4c` |
| 作者 process-release.json | `31f77b464ff08fbca8c79b4fec0e1e6500a07f9773056f541e96d03318bab6b7` |
| 调度只读交付前检 | `a9dae4fafe827c654531c9fde046dcd2f5e974383ad634132e3d1bef6cc3a2b5` |
| R3 独立报告 | `a39afab68c15837122a34fb0f75dca7cae339dd2ba1be13dde007971b99b9a17` |
| 原 R3 N7 stderr | `0c5670e4e345ad9c55020d83851ea971c0dbc4a865899b425c15241847706fc5` |

以命令级 `git -c core.longpaths=true`、`ls-tree` 和二进制 `cat-file --batch` 核对 mode/type/blob、blob SHA1、长度与 raw SHA256。314 个清单条目加清单自身共315个新增文件全部相符；base 全部31,167个旧 tree 条目原样，无旧路径例外。六份 workflow 文档与作者保存原件逐字节相同。没有用 checkout 字节替代 raw Git 保全证据。

导出409项必要源/夹具、权威文档和本轮作者证据，见 [输入索引](../evidence/A03/review/P2-R8-R4-remaining/input-index.json) 与 [完整交付字节核对](../evidence/A03/review/P2-R8-R4-remaining/delivery-byte-index.json)。新隔离树只放68个产品包文件、确切 R4/R3 驱动、5个固定 R3 夹具文件和仅作驱动登记摘要的 inputs.json，共76个种子；没有复制作者 validation 或数据库作为起点。

此前6,368项 A03 审阅/报告文件，合计144,516,343字节，按有序 `[path,size,raw SHA256]` 集合摘要保全，未复制历史全集。摘要 `75f7fc0667aa094fd59cd8fa8ff2a9cb4638e46df0921b8dc370f4cc41da9adb`，封存前再核对，见 [历史保全](../evidence/A03/review/P2-R8-R4-remaining/historical-preservation.json)。开始时根 state 已有未提交修改、mermaid-diagram.png 已存在，本审阅只新增获准的 R4 报告和证据目录，未处理这些他属状态。

## 确切驱动、导入和一轮运行

独立 workspace：

`D:/1800/docs/evidence/A03/review/P2-R8-R4-remaining/isolation/workspace`

新 run id：**`review-r4-2bd4a13ab0fe`**。validation 在首次启动前不存在，也没有任何 SQLite 种子。实际新产物位于该 workspace 的 `docs/evidence/A03/execution/P2-R8-R4-remaining/validation/review-r4-2bd4a13ab0fe/`，共116个文件；全部76个种子在各组前后及封存前保持原字节。

| 源/驱动 | raw SHA256 |
| --- | --- |
| R4 主驱动 | `27d1969548011b044c21b77a121c53b5bef90d4aa0b19aef95f65b8d692f9a3d` |
| 原 R3 主驱动 | `02acb22f395f380528130166ca8ae4637e3303c73f6496d9da4166b5050a1467` |
| native.py | `c3e2f01ccbfb7b64c49a5272eb51ffbe2f6af8c8abb5a51c4c9c6965166b902a` |
| native profile | `023078c2a8bdfd1f3cc80eb6effdfc31010284464584218cbb77f3c4583c921a` |
| native adoption | `24d6529f2fcb9a386b0c52ab46f7551ee8c8701350351c88b241621fdec4477f` |

68项产品来自未改的 target raw blobs，六项 schema pins 和23项 implementation pins 均核对。产品 native 实际导入位置为上述 workspace 的 `src/annotation/runtime/storage/native.py`；所有实际 annotation 模块和两个测试模块的 __file__/SHA 均逐项绑定隔离树 raw bytes，见 [N1 导入](../evidence/A03/review/P2-R8-R4-remaining/imports-N1.json)、[N6 导入](../evidence/A03/review/P2-R8-R4-remaining/imports-N6.json)、[N7 导入](../evidence/A03/review/P2-R8-R4-remaining/imports-N7.json)。没有导入作者工作树。

审阅者 [入口](../evidence/A03/review/P2-R8-R4-remaining/scripts/group_entry.py) 正常 import 原驱动并选择一个 unittest 方法，仅把测试模块的输出根指向新 run 目录，保存初始/实际路由。没有修改产品、驱动原字节、业务输入、时钟/期限，没有 AST/exec 裁剪导入或产品 monkeypatch。静态 ast.parse 仅用于语法检查。Python为现有 Windows CPython3.9；这不是安装验收。

| 独立组 | 父 PID / exit | 父实耗 | 到达范围 |
| --- | --- | --- | --- |
| N1 | 66412 / 0 | 24.938秒 | 调用完整原 N1 方法；实际效果 child 57664 在提交屏障后 exit87。 |
| N6 | 34716 / 0 | 3.485秒 | 一次正常历史 verifier、一次内部真实计划重算、一个明确 PRE 证据缺失拒绝。 |
| N7 初始化 | 43976 / 0 | 0.719秒 | 一次 before_completion 钩子异常；随后一次正常 open 拒绝。 |

三组各一个 unittest、各一轮，无 skip/timeout/alive；父 watchdog均60秒，子进程沿用原限定（效果 child45秒、观察子进程2秒）。[汇总](../evidence/A03/review/P2-R8-R4-remaining/independent-run-summary.json) 不代替以下 SQL/Resource 绑定复核。

固定合成模板沿用 `plan-r8-r3-n1`、book/ledger/store 等逻辑标签；不能因此称这些标签全部是新 UUID。新的路径/双库从空目录建立，实际 PRE run、观察、intent、receipt、resolution 身份重新产生，完整计划四元组因新内容而不同于作者和旧 R3。没有从旧库接续。

## N1 必要前序的正式边界

作者冻结库只从 raw 导出读取；独立库只从新 run 读取。审阅者将各自双库复制到自有临时副本，以标准库 SQLite `mode=ro&immutable=1`、query_only读取；quick_check均ok，原件/副本读前后摘要相同，副本已移除。未连接作者原库或调用其产品 API。

| 双库 | runtime raw SHA256 | target raw SHA256 |
| --- | --- | --- |
| 作者冻结原件 | `46e9bb060b4b06ce1c5c76b81e29ee42df187fbc457fb90f90e2af7324c01199` | `97016773ba0265a0625c54a38c06c9b0ceeade4368f55e9f25db046005d82126` |
| 独立新库 | `928323d783c8dae33397c6dcb91a4f5ad811b8244a3925c3f2c80b46cb18b8f1` | `ac0bd6ad8b19e05ea5d220fe3656a9cbc5623be1fb52da7845e90e605dc1a091` |

runtime最终20个正式 artifacts、各1个 PRE run/creation anchor/plan/action/intent/permit/resolution/report read；target为4次实际观察、效果恰好1。PRE为ADMITTED、accepted_plan绑定真实计划，permit为CONSUMED；单动作CREATE_FRAMES的plan/action/digest/intent与实际效果一致。child真实提交后屏障、父效果计数和release/exit87记录相符。

原 UNKNOWN 及 null 原回执保留；终局 RESOLVED_APPLIED 的 original_receipt_ref仍null。晚到 receipt 四元组在 SQL artifacts、current bundle、intent.receipt 三处相同，指向原恢复 fact。两个正式 material progress 的 plan/action/intent/attempt四项及尝试证据与该 fact 一致，保留 MAY_HAVE_BEEN_ATTEMPTED，没有改写尝试事实。新 POST/Batch 正式登记，报告观察/快照与终局观察不同，durable report read=1；frame_structure=PASS，内容PENDING、NOT_SUBMITTED，Batch为CONTENT_PENDING。

独立 refs 均 revision=1：

| 产物 | artifact_id / content_hash |
| --- | --- |
| plan | `plan-r8-r3-n1` / `0193a996b84a717e2ebe1343ed6fa52ca768c14ca30e0b285df5feddc20daed2` |
| receipt | `executionreceipt-3458fd9db7c24885a55d0a957bbad8ca` / `463948868923f7eece7c595137a28a9307624d808ef8a199dce747995939d2b8` |
| terminal head | `resolution-9438d0cdfd654fc59415be3352245929` / `b235800aed2177f4dccd22007af12668be9b9b826017956edb55bcdb69507a60` |
| POST | `native-post-8dbd2d7749e8436299bff781666f9245` / `771dc47c60511ebd20486eed14a8b02d0ba9d4ca9c04aa4dd5132fe78040e008` |
| Batch | `native-batch-42b5b39bce7e440ab096815f6e057ade` / `78e5347c0a7479e6d2223569c0a8b81df462799fc4bb7a16a1edaa4a0c44edc0` |

见 [作者正式边界](../evidence/A03/review/P2-R8-R4-remaining/author-boundary-review.json)、[独立正式边界](../evidence/A03/review/P2-R8-R4-remaining/independent-boundary-review.json) 及其各自 database-review.json。N1副本核对在独立N6前完成；N6后以原字节再比对其不变性，没有补发写入。

## N6：完整历史、实际重算和一个正式依赖控制

传给 verifier 的 current bundle 包含全部20项正式 artifacts：原 UNKNOWN、晚到receipt、resolution及新POST/Batch都保留。已与当前登记 bundle 和全部 SQL artifacts refs 交叉核对，不是作者从历史中过滤后的成功输入。

产品既有 native verifier 在该完整历史上下文中，从 SQL 登记的 creation anchor 读取当时7项创建输入，验证原字节/资源清单/config，正常调用 create_plan 重建原计划。创建时输入与后来的完整历史分别保存；使用登记创建输入是产品既有逻辑，不是驱动删除后代、重封签或降级。

| 摘要口径 | 作者 | 独立新运行 |
| --- | --- | --- |
| anchor canonical bytes / SQL input_sha / objects原件 | `3d9b5f62304ed6c01e33c6dd7867a4775892106927937210afc6f6b861bacc9a` | `28c396774fc750b1b90dab7af4c4626a7b1b947f390e120215db8cfd666f568d` |
| 完整原计划及实际重算计划 canonical JSON | `ff6805e33e3b3f02239cfe00d426f7b660c2ff1414b9d46f487dcb21238d503f` | `056ef925a3a3a424145f538302f97467127a4e971d49d4f73724cd83f7d200c2` |

以上完整JSON摘要与 plan四元组中的 content_hash 是不同口径，未混用。实际 return 捕获只有一个 generated plan，完整JSON/四元组/全部action均与原计划相同；只有一个resource_manifest返回，等于SQL清单。审阅者另从anchor递归遍历实际Resource，6项集合相同，每项实体长度/SHA与保存读回相符。

已静态检查 exact 驱动的 sys.setprofile：只在当前正常验证调用中观察 create_plan 和 resource_manifest 的真实 return，不替换参数/返回，不二次调用planner，finally恢复None。独立运行确实执行该原方法并保存实际return；本审阅的后续只读核对不调用planner。

负控删除的准确消费者为 PRE `pre-r8-r3-N1`（revision1，hash=`c31996762d6ed6fd0a312eb0e7d32c2af4ab44b67e638b10fd009982c15b9f43`）的 checks[0] / source_integrity / evidence_refs[0]，EvidenceRecord：

`native-pre-proof-ec12016d5e5b2d856357b8b298262adcc6aae85e`

其正式Resource为 `assets/native-pre/ec12016d5e5b2d856357b8b298262adcc6aae85e54c164f392d8c11218f4fe54.json`，SHA即文件名。独立逐字段比较证明缺失副本只移除这一record，其他输入、anchor和资源实体未改。

正常 historical context入口在闭包层抛 `StaticCodecError/EVIDENCE_ID_MISSING`，实际定位：

`pre-r8-r3-N1/checks/0/evidence_refs[native-pre-proof-ec12016d5e5b2d856357b8b298262adcc6aae85e]`

原异常/traceback保留，未把早期无关拒绝或任意外层symbol要求计为通过。它证明**一个正式PRE依赖缺失被定位拒绝**，不证明全部Resource损坏矩阵或负例计划接纳流程。

N6正例与负控前后，runtime/target raw SHA均与N1副本读取值相同，permit=1、effect=1，新增均0；原anchor再次读回相同。详见 [作者N6独立读回](../evidence/A03/review/P2-R8-R4-remaining/author-N6-review.json)、[本轮新N6读回](../evidence/A03/review/P2-R8-R4-remaining/independent-N6-review.json)。

## N7：一个 runtime 初始化钩子的有限拒绝

在首次不存在的 `cases/N7-before-completion/`，正常 init_native_state 通过既有 before_completion钩子恰好调用一次stop，原 ControlledStop对象被原样传播。钩子位于建表后、INSERT meta和anchor正式落盘前；没有直接SQL改字段。

保留的runtime已建表，meta为空，native_creation_anchors/plans/intents/permits均0，无initialization=COMPLETE，anchor.json不存在。随后正常open_native_state一次，以STATE_DIRECTORY_IDENTITY_MISMATCH拒绝，错误链为缺失anchor的FileNotFoundError。没有恢复初始化或再试到成功。

审阅者又对自有immutable/query_only副本核对表、空meta及quick_check；原件/副本/open前后raw SHA均为 `dd19ba8a492195879043099bb964c4a086aa6bc8077193c139fe2bfad5aecf0d`。作者和独立运行的这个空中间库字节相同，不据此推断复用了目录；首次不存在的路径、种子无库及实际正常调用另有登记。target目录/数据库未创建，effects记NOT_CREATED，不把未创建的表伪记0行查询。

这是**同进程受控异常下一个runtime正式完成前钩子的fail-closed证明**，不是进程崩溃或目标库所有初始化点证明。迁移仍NOT_IMPLEMENTED_BLOCKED。见 [作者初始化复核](../evidence/A03/review/P2-R8-R4-remaining/author-N7-initialization-review.json)、[独立初始化复核](../evidence/A03/review/P2-R8-R4-remaining/independent-N7-initialization-review.json)。

## 覆盖与未释放边界

已逐项保留原V01–V10、R01–R18的28项原文及原R3状态，单独标记本轮新增范围、当前剩余和N1–N7分项，见 [独立覆盖映射](../evidence/A03/review/P2-R8-R4-remaining/p2-independent-coverage-review.json)。作者映射仅作输入，未用它替代独立结论。

| 原范围 | 本轮结论 |
| --- | --- |
| N1 | 新必要前序和正式单动作恢复边界通过，不增加一般性覆盖。 |
| N2–N5 | 原R3有限接受和限制保持，未重跑。 |
| N6 | 完整历史中的真实anchor重算及一个正式PRE依赖缺失控制有限接受。 |
| N7 | runtime初始化钩子分支有限接受；原R3失败/诊断分类及其已达旧入口边界静态保留。 |
| V07/R02 | 新增上述重算/依赖证据；完整错身份/action/digest/资源/policy/capability/authorization矩阵仍未覆盖。 |
| V08/R14 | 新增一个runtime完成前控制；其他初始化、损坏、替换、I/O、迁移仍未覆盖。 |
| 其他V/R | 原已达子范围与原剩余逐项保留，不以本轮三组通过豁免。 |

多动作及明确未生效演示、混合尾段/充分与不足ABSENT、native多scope/run/多书、双owner竞争、其他崩溃点、qualified clear/不同hold-id替换、archive-validator/显式转换、真实/ORIGINAL/OBSERVED/S01否定矩阵、旧报告/VERIFIED篡改、分母/跳过/max-attempt边界均未在本轮扩测。B确认和S01仍为独立依赖，不代为派单或验收。**A03整体REWORK，I01未释放，不自记INTEGRATED。**

## 过程身份、失败记录与封存

作者8项实际父子进程的preregistration/argv/cwd、源与脚本快照、PID、原输出、exit/timeout/alive均只读核对。效果child60488为预期exit87，其余0，三组原日志各一个test且OK。三个作者产品索引相同，实际模块/驱动路径及摘要另逐项核对，见 [作者过程审查](../evidence/A03/review/P2-R8-R4-remaining/author-process-review.json)。

这里明确区分 raw Git 与执行checkout表示：产品包共68个文件，作者索引按.py/.json只选65个；其中60个与raw Git逐字节相同，另外五个旧文件仅为确切LF→CRLF：`annotation/__init__.py`、`contracts/__main__.py`、`contracts/cli.py`、`contracts/integrity.py`、`contracts/models.py`。五项转换后的长度/SHA与作者启动索引及实际导入摘要吻合，具体raw/actual摘要逐项保存；没有对其他文件作宽泛归一化。native/profile/adoption及23项implementation pins仍为原字节，本次独立导入全部使用target raw字节。

审阅辅助过程有两次元数据断言失败：首次误把作者索引当作68项；第二次忽略上述五个已有EOL表示。两次脚本快照、PID、raw stdout/stderr、exit1均保留，修正后只重查元数据/字节，未重跑产品。另一次静态查询误用了planner.py路径，真实实现为planner/__init__.py；仅有渲染工具转录，无PID/分流原输出，不伪造完整过程记录，见 [只读查询限制](../evidence/A03/review/P2-R8-R4-remaining/reviewer-query-preparation-failure.json)。

独立产品三组均首轮通过；14项已登记自有产品/检查进程（含最终字节核对）及4个嵌套子进程已wait/退出。释放依据自有Popen及已登记完成记录，无OS/profile全局扫描，见 [自有释放证明](../evidence/A03/review/P2-R8-R4-remaining/process-release.json)。

复现命令和实际argv、输入/源摘要、限时、运行前后路由均保存在各runs目录及 [单次启动脚本](../evidence/A03/review/P2-R8-R4-remaining/scripts/run_group.py)。这些exclusive输出已存在，记录用于在新目录审阅，不在本轮原路径再运行。

[最终核对](../evidence/A03/review/P2-R8-R4-remaining/final-verification.json) 与 [完整SHA256清单](../evidence/A03/review/P2-R8-R4-remaining/sha256-manifest.json) 覆盖本轮全部文件和本报告，仅排除清单自身；保存两次辅助失败、原R3失败输入、实际导入、新产物及绑定核对。清单落盘后再读取每项原字节与完整目录集合核对，不再运行功能。

零网络、平台、浏览器、凭据/profile、OCR、模型或付费API、安装、A05题22重放、书级送交、推送和B联系。字段重置专项始终 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`，不复跑、变形、委派或建议重测。最终仅接受本报告明确的R4子范围，保留全部既有未覆盖标准和发布边界。
