# A03 P2-R10 双进程 owner/fencing 独立验收

2026-10-18（Asia/Shanghai）。**结论：`ACCEPTED_OWNER_FENCING_TWO_CASES_ONLY`。** 在固定 target 的全新隔离树，C1、C2 各首轮一次通过，另用自有不可变数据库副本、正式Resource、事件链、屏障和进程时序独立核对。只接受原V06/R09的这两个子项；整个A03仍为REWORK，完整并发/崩溃矩阵、本地产品集成与I01均未放行。

## 固定输入与保全

| 输入 | 提交或 raw SHA256 |
| --- | --- |
| 唯一 target | `1c26b4a8eb378af33e57668472d2071e9ea6afff` |
| 直接父提交 / base | `bfd7fe896a7eee663ea8e0b6cf967548d8dd8f39` |
| 审阅 workflow | `2b6771285507fb18d4c6fcd5d6f4933003e94bd0` |
| 审阅交接单 | `e3008275528e4b90493339ca82326bbfd691f2313a640acf84b6ccfb3a87eff0` |
| 执行 workflow | `2d8357e040ee5c54494882bc175baf2579d07aed` |
| 执行任务 | `5314105f2b1c8b773c4ceda21ed82904ea210258ecbb2406ce6cd29490c1510a` |
| 执行报告 | `a718ddf8b3969dd8b44d81fb22f4ee86b30400c9d85f7226194a6136613e86d4` |
| 作者 manifest.json | `7372f10d785322d949a29ea4b28c730ea90411f05ddc2448a39f4e6d2b9bc9a7` |
| 作者 process-release.json | `b7d20a8254ba93b815b40066724a23c75a1206c0f826df90aa9838da4dc1fbd2` |
| 调度只读预检 | `5b060dcf021f7be17c949967fca4f58f831c011f87884cfcb04356c3f7d2b0d2` |

命令级`git -c core.longpaths=true`、raw cat-file/ls-tree及父提交查询核实：target直接父提交为base；261份新增raw blobs与260条manifest加自身相符，32,152个旧mode/type/blob条目全部原样；4份workflow原件及11项base引用逐项相符。只导出356项必要源/文档/本轮证据，不合并浮动调度分支或复制旧历史全集。见 [输入索引](../evidence/A03/review/P2-R10-owner-fencing/input-index.json)、[交付字节核对](../evidence/A03/review/P2-R10-owner-fencing/delivery-byte-index.json)。

8,509项旧A03审阅/报告文件共240,552,123字节原样保全，有序`[path,size,raw SHA256]`集合摘要为 `33c31250ee7faf13ffdc2dca521defba5f694a61997b6cf6516c62edaecab853`，封存前再次核对，见 [历史保全](../evidence/A03/review/P2-R10-owner-fencing/historical-preservation.json)。R9-R1四组有限接受、作者原borrow FAILED/D2 NOT_RUN及旧R3失败均不改、不重演。

## 独立源、驱动与一轮运行

workspace：`D:/1800/docs/evidence/A03/review/P2-R10-owner-fencing/isolation/workspace`；新run id：**`review-r10-5d608090db83`**。首次启动前没有validation或SQLite种子。76项raw种子仅含68个完整产品包文件、R10原驱动、R3正常setup helper、5个固定32×32单题两片段夹具文件及仅作登记摘要的inputs.json。作者数据库只在冻结输入中供只读比对，没有作为新案例起点。

驱动原字节SHA256=`da15d84be77fb9be7b718ff28721647a6b3c4052b32531cae45768394c798a82`；helper=`02acb22f395f380528130166ca8ae4637e3303c73f6496d9da4166b5050a1467`，均未修改。提前静态检查并冻结 [具体预期/期限](../evidence/A03/review/P2-R10-owner-fencing/driver-preregistration.json)、[源语义检查](../evidence/A03/review/P2-R10-owner-fencing/static-review.json)。6项schema、23项implementation pins与raw产品匹配；产品/schema/profile/adoption/pins/oracle/producer/verifier及依赖原样。

薄 [单次启动器](../evidence/A03/review/P2-R10-owner-fencing/scripts/run_group.py) 顺序执行确切驱动C1、C2，逐组exclusive登记argv/cwd、输入/源/脚本SHA、预期、PID及原stdout/stderr。正常import，不作AST/exec裁剪、产品monkeypatch、SQL写业务状态或PID/时钟/lease伪造；ast.parse只作静态语法检查。实际模块__file__/SHA来自上述隔离树，native.py实际位于该树`src/annotation/runtime/storage/native.py`，SHA=`c3e2f01ccbfb7b64c49a5272eb51ffbe2f6af8c8abb5a51c4c9c6965166b902a`。所有实际存在的worker imports和资格/ready导入记录保留，没有按预设计数补造文件；这不是安装验收。

| 独立组 | 父 PID / exit / 实耗 | 业务A / B PID及exit |
| --- | --- | --- |
| C1 | 66108 / 0 / 2.327秒 | 53684 / 0；41268 / 0 |
| C2 | 38208 / 0 / 5.530秒 | 38292 / 0；48816 / 0 |

父watchdog90秒、业务child从启动计45秒；产品BEFORE_CLAIM5秒、lease10秒、观察2秒保持。两组各一次，无功能首败、超时或重跑；worker对预期业务拒绝完成记录后正常exit0，不能把进程exit0误解为两方claim都成功。

## C1：两个真实存活进程的claim互斥

双方先正常open同一新注册书，各保存ready，均进入原FaultController的BEFORE_CLAIM屏障并写真实PID marker。父进程核对两份ready/marker与实际Popen PID、存活后，在`1792276919324871800 ns`共同放行；两方结果都晚于它。父进程在`1792276919403164700 ns`保存双方仍存活的竞争观察。

A（PID53684，instance/owner=`process-4f75a616a6c44acc9d742b40b53c5eb9`）成为唯一ACTIVE owner/generation1。B（PID41268，独立instance=`process-077c4b4f59014e2c8ef2e6536f2421a9`）具体收到RuntimeFailure/OWNER_BUSY，消息`lease expired AND previous process exited required`，实际trace到达claim busy-owner守卫，不是无关异常。

live runtime的owner/PID/process_id/generation与A一致，lease有效，target fence为A/1。OWNER_CLAIM_RESERVED和OWNER_ACTIVE各一次，effects=0。只有在两份结果及live观察保存后，父进程才发finish；A正常stop keeper/release。A/B实际退出分别为`1792276919504782900`、`1792276919506782500 ns`，均晚于live观察，排除了成功者先退出后的串行接管。

最终runtime RELEASED、owner/pid=null、lease0、generation1；target保留A/1最后合法fence。共有3个事件，无PRE、创建锚、计划接纳或业务效果。本项只证明claim互斥，不证明效果提交竞争或死进程回收。

## C2：真实换代后，存活旧A从run_plan被拒

A（PID38292、instance/owner=`process-8f694bfe398b489c93d5b95b5e9333c6`）在同一真实store内经正常PRE/admit/targetcheck/planner/record形成有效资格，generation1，尚未accept。独立核对正式四元组、SQL登记和Resource：

| 正式资格 | revision / content_hash或原SHA |
| --- | --- |
| ApplyPlan `plan-r10-C2` | 1 / `d87bd05ec23353ef3e9f42b0a939c54705f9ee1bb8a9080258db402eec22f439` |
| PRE `pre-r8-r3-C2` | 1 / `8067d6c5821187e486e13dd45428b43a31124409422d758363f7d9e8d856784e` |
| ADMITTED native run | `native-pre-3afab89105d044d68a43a13a515a989e` |
| creation anchor canonical bytes / SQL input_sha | `9ebc7c7bbf6b38af45f7899e90fcfc638a8fa16f57516a44dd74521526c6f3ff` |

SQL PRE为ADMITTED、accepted_plan=null，run Resource的五检查PASS及owner/generation/registry/store/session绑定一致。计划含真实单个CREATE_FRAMES并绑定该PRE/实际快照；创建输入canonical原件、资源清单及递归实体SHA均核对。**已记录计划Artifact不等于plans/actions接纳行存在**：两表以及intents/permits仍0，effect0。

资格在`1792276929602024800 ns`保存；父进程发release信号后，A正常stop原keeper/release并于`1792276929654378500 ns`记录完成，但进程和原store/claim保持存活。B（PID48816，instance/owner=`process-c72d9716e6474e2f9c4d380547a1e919`）正常open/claim后于`1792276930231239000 ns`记录ACTIVE/generation2，target fence同步B/2。

父进程确认双方仍活、B ACTIVE后才放行旧调用。A仅一次使用原pair进入run_plan，具体RuntimeFailure/OWNER_GENERATION_STALE、`current ACTIVE lease required`；trace为驱动→recovery:86→storage._lease:343，拒绝在计划接纳和新intent/permit/dispatch前发生。此处错误未被共享事务包装成别的码，不套用上轮事务包装预期。

拒绝前后plans/actions/intents/permits均0、effects0，artifacts/PRE/anchor/事件计数和target观察/效果计数不变，B的owner/generation/ACTIVE/PID/process_id及target fence保持。A移交后不renew/release/覆盖B。父进程于`1792276930400572400 ns`再保存双方存活观察，晚于旧调用拒绝、早于双方退出；其后才允许B正常stop/release。最后runtime RELEASED/generation2，target保留B/2 fence，共6个事件，分别为两代各claim-reserved/active/released。

这接受“实际正常换代后存活旧进程资格失效”；不分拆宣称所有单字段fencing负控、过期/死进程回收、pending清除或其他崩溃点通过。

## 冻结双库、正式绑定与过程

作者两例及独立两例共8份最终库，均从raw导出/独立产物复制到自有临时文件，以stdlib SQLite `mode=ro&immutable=1`、query_only读回；quick_check均ok，原件/副本读取前后SHA一致，副本已删。没有连接作者活动库或调用产品API做验收读回。

| 独立case | runtime raw SHA256 | target raw SHA256 |
| --- | --- | --- |
| C1 | `2926ac37f05cc08c7ce714968de8d6b146bce9129f077800d73e81144fb12a8b` | `749592262523310ffcea738c50b7b2524c79eba93aaf3bdbc6a005d837bae8a2` |
| C2 | `a9f21e6299edd64722dfd3490c6b8d9ae0c8fc81a0e76b083c26fa1413cb0e3f` | `dd633fef4bb0d182a24a60522acdc06f85acbd0e949a6b5b5754129370509eed` |

独立C1有4个正式Artifact、0次target观察；C2有8个Artifact、1个ADMITTED PRE/creation anchor、1次target观察。SQL refs/path、各Artifact实体/current bundle、全事件hash链及最终head闭合；递归Resource实体摘要相符。两例plans/actions/intents/permits及effects始终0，无receipt/resolution/POST/Batch，不把缺失产物填成保存成功。

live阶段SQL事务、两库及raw字节读取按顺序进行，**不宣称跨库原子快照**；并发/移交到达依据是实际屏障、Popen存活观察、租约/fence与完整时序。详见 [独立SQL/Resource/时序审查](../evidence/A03/review/P2-R10-owner-fencing/case-and-timeline-review.json)、[作者过程身份审查](../evidence/A03/review/P2-R10-owner-fencing/author-process-review.json)。作者8个原登记进程退出和实际源/导入记录仅只读核对；五个已知LF→CRLF文件逐项显式验证，其余作者源raw一致，本次独立产品源全部raw一致，不做宽泛归一化。

首次功能前有一次元数据helper生成错误：过宽的文本数字替换被摘要断言拦住，辅助文件尚未写入；后续解释器找不到runner，亦未运行产品。改为精确字段替换后才冻结/执行功能。仅有渲染摘录、无PID或分流raw，限制如实保留于 [准备首错](../evidence/A03/review/P2-R10-owner-fencing/preparation-tool-failure.json)。功能启动后未纠正/重跑任何驱动、产品或审阅检查。

全部实际存在的自有子进程已wait退出：6个登记检查/功能父进程、4个业务worker及1个实际观察child、6个Git子进程、1个封存包装；没有全系统PID/profile扫描。真实导入与退出文件按存在情况登记，不补造预设数量，见 [进程释放证明](../evidence/A03/review/P2-R10-owner-fencing/process-release.json)。110份独立运行产物、76项源/驱动、356项输入及本轮全部文件/报告均由 [SHA256清单](../evidence/A03/review/P2-R10-owner-fencing/sha256-manifest.json) 覆盖，仅排除清单自身；[最终核对](../evidence/A03/review/P2-R10-owner-fencing/final-verification.json) 在封存后再读body和完整目录集合。

仅新增本报告与R10 review目录。全程无旧四组/整套矩阵、子智能体、网络/平台/浏览器/profile/凭据、OCR/付费模型、安装、推送、B联系、A05题22或书级送交；保留用户model/thinking，不改调度state。字段重置始终 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`，不运行、变体、委派或建议重测。最终只交两个子项冻结结论，整个A03/I01不放行。
