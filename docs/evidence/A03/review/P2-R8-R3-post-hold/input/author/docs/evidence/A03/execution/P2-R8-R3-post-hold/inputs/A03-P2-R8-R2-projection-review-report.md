# A03 P2-R8-R2 投影修复及 N1 有界独立验收

2026-10-18（Asia/Shanghai）。**已确认的尝试分类投影缺口关闭；固定合成单动作 N1 完整恢复链有限 ACCEPTED。N2 未通过，整个 R8/A03 仍为 REWORK，I01 不释放。**

本轮先核对冻结源码、作者原件与必要 immutable 数据库副本，再从 exact target 导出产品、固定输入及未改动 N1 驱动，在全新 run id 和全新双库上独立运行 **一次** `R8R2NativeBridgeTests.test_N1`，随后以自己编写的标准库只读查询核对正式登记和绑定。该唯一独立测试通过，效果恰好一次，正式 receipt/progress 与独立 POST/Batch 均已落库。N2 只读定位，未重跑；未执行 N3–N7、最小检查或兼容全套。

被审 target 为 `58d8a64734271d15654bb00b03d760f0f3eccd10`，派发键 `A03:review:P2-R8-R2-projection:58d8a64734271d15654bb00b03d760f0f3eccd10`。本报告没有修产品、放宽合同、复用作者成功库或把作者通过直接记为独立通过。原 R7 接受范围及 R8/R8-R1 原失败字节保留；不自行登记 INTEGRATED。

## 确切输入与保全

| 输入 | 提交或 raw SHA256 |
| --- | --- |
| 审阅 workflow | `1f2030b813cbbfc77cc12cab36db453972af26b9` |
| 审阅交接单 | `e66037d79d96b263d5b50b4ab4d3cb101592bfeabe81551ab535f031bcc09507` |
| base | `a0c40886f3076f84c46377e03fc2206d2fdc5585` |
| 产品/辅助源码提交 | `002c26795822fe8518117793f59598b3eceab02e` |
| target | `58d8a64734271d15654bb00b03d760f0f3eccd10` |
| 执行 workflow | `016e048669e5af1f193e71968d03bf3000cf16d1` |
| 执行任务 | `c76ef2a47fa9bbfecb83b05e02cfe56a6599c68600786d2a86eb9547c35fb3e0` |
| 执行报告 | `8fd88d3f19de8a853f8649412ecbef9cae4c453c689b2540413d206db0178421` |
| 执行 manifest | `5b5a3cc998c05fbe4ac3d044bac8bfd1b468b24d7b3e71adb7b78a7db397684c` |
| 作者 process-release | `6119e12e0b7b35c09c60b89eb32aa4445c4806c6fd73b365adb1394910425875` |
| 作者 bounded-outcome | `e20b2567885408ea6edbc37ea51952cfdcccb5ca3ab44036e782ed3b10212bfe` |
| 作者 database-readback | `b5564cad9c89fcbf2c158989505a61f6a7fbd543984164c93d8f7ca942db34f5` |
| 调度交付前检 | `0abd9fd491ca3d538da16bb9b881c999df5fb21a6dcc3b6378c90ca207de572d` |

使用命令级 `git -c core.longpaths=true`，通过 `ls-tree` 与二进制 `cat-file --batch` 核对 mode/type/blob、blob SHA1、长度及 raw SHA256，未改变全局 Git 设置或合浮动主树。见 [交付字节索引](../evidence/A03/review/P2-R8-R2-projection/delivery-byte-index.json) 和 [exact 输入索引](../evidence/A03/review/P2-R8-R2-projection/input-index.json)。581 个 manifest 条目及自身、582 个变化路径、六项原输入 pins 全部吻合；base 29,706 个条目中，29,703 个原样保留，只改变三个允许的旧产品路径。

共导出 407 个必要输入文件。其中独立工作区只有 68 个正常产品包文件、固定驱动、固定夹具和仅用于驱动登记摘要的 inputs.json，共 **75 个种子文件**；没有复制作者 validation、成功数据库或成功产物作为运行前缀。其余必要作者证据单独隔离保存，未使用的重复快照只核对 raw 索引，不复制历史全集。

根工作区 4,645 个旧 A03 审阅/报告文件按有序路径、长度、原 SHA256 集合摘要保全，封存时再次核对，见 [历史保全](../evidence/A03/review/P2-R8-R2-projection/historical-preservation.json)。原 `mermaid-diagram.png` 保留。未改执行工作树、旧报告、旧证据或调度 state。

## 投影修复的独立静态判断

新增私有 `_progress_attempt`，位置为冻结 [storage/__init__.py](../evidence/A03/review/P2-R8-R2-projection/isolation/workspace/src/annotation/runtime/storage/__init__.py) 第 747–758 行；实际调用在第 811–818 行。

有 fact 时，它先核对完整 plan_ref、action_id、action_digest、外层 intent_ref，以及 result 内的 action_id/intent_ref；拒绝错绑后，从原 fact.result 取 attempt_fact，并 deepcopy 原 attempt_evidence_refs。`_project_plan_locked` 实际读取该行的 Resource 原件并使用返回值，没有根据 APPLIED 效果结论改写历史尝试分类。无 fact 时保留旧 NOT_ATTEMPTED / MAY_HAVE_BEEN_ATTEMPTED / ATTEMPTED 分支与空证据。

独立逐字段比较 profile/adoption，确认只更新受影响的 storage implementation pin 和 profile SHA。当前六份 Schema、23 项 implementation pins 均与实际源字节吻合；合同四项守卫、Schema、native commit_reconciliation、producer、版本/角色语义、根依赖及旧原件未改。

| 唯一三个旧产品变更 | target raw SHA256 |
| --- | --- |
| storage 实现 | `93cb82da040346cfba95a312f3615b8bfc5c47edee01ba69584ac338882cfa3a` |
| native profile | `46dba6f9c33d84daa8149a77afbe86952fc08ff835ed180828d7ab307cdd9d47` |
| native adoption | `a1c8b6e1f85a603b107163d618985b127c9157050b1977f4fd626f7021eec760` |

冻结最小检查原记录涵盖 material fact 保留 MAY_HAVE_BEEN_ATTEMPTED、尝试证据副本、无 fact 的 pending/reserved 旧分支、外属 intent 拒绝。它没有 SQL 接纳/效果，只作局部来源分支证据，本轮未重跑。代码 diff、pins、原最小记录、N1 驱动静审和 N2 确定性位置见 [静态核对](../evidence/A03/review/P2-R8-R2-projection/static-review.json)。

## 作者 N1 正式原件核验

没有仅采用作者 N1-result 的布尔结论。以 SQL registrations.bundle_path/package_root、artifacts.ref/path、intent.receipt 和实际 Resource 原字节定位，分别核对 current bundle、完整四元组及 canonical hash。两库从冻结 blob 复制到自有临时目录，以 `mode=ro&immutable=1`、连接级 query_only 查询，quick_check 为 ok，读前后及源导出摘要相同，临时副本已清理。未连接执行者原库。

| 作者冻结库 | raw SHA256 |
| --- | --- |
| runtime | `0f32ca20b0a2cf9b7a66c434994c845e921d5a5701d20ea6265a3ca95b4915ea` |
| target | `9ee1fb878a0b65bed21b893ff242072d8d0775671518d9dae4810070cce4b25e` |

作者 N1 父 PID **57904** exit 0；效果子 PID **13392** exit 87，barrier_released=true。屏障源代码在实际效果提交后由父进程独立查询 effects=1 再放行，冻结 target 仍为 1。

独立读取作者原件确认 PRE ADMITTED、计划单动作 CREATE_FRAMES、唯一 permit CONSUMED、原 UNKNOWN 保留、RESOLVED_APPLIED 终局 head 的 original_receipt_ref=null。正式 receipt `executionreceipt-376adae14660420cac6f962a2a08eef6` / hash `59e66571edc2f2392ea2bb5118c466f871ecd2e04ed6bb9d6bd024e7ec0c6238` 同时存在于 SQL artifacts、当前登记包和 intent.receipt，完整引用相同。

两个正式 material progress 均与同一 fact 的 plan/action/intent/attempt 四项一致，attempt_fact=MAY_HAVE_BEEN_ATTEMPTED，尝试证据与原 fact 完全相同；正式 receipt.results 聚合原 fact.result，没有将普通文件存在视为提交。新 POST/Batch 和报告快照也已正式登记，native_report_reads=1；frame_structure=PASS、content_check_status=PENDING、submission_status=NOT_SUBMITTED。

见 [作者独立 SQL 核对](../evidence/A03/review/P2-R8-R2-projection/author-database-review.json) 与 [作者直接产物绑定](../evidence/A03/review/P2-R8-R2-projection/author-boundary-review.json)。作者库后来被 N2 的受控目录变更加入 hold，current artifacts=21；这个后续 hold 不撤销历史 N1 的正式登记，也不赋予当前继续写入资格。

## 唯一一次独立完整 N1

独立工作区为：

`D:/1800/docs/evidence/A03/review/P2-R8-R2-projection/isolation/workspace`

run id 为 **`review-n1-0c7cf9db3e2c`**。启动前整个 validation 根不存在，未复制成功库；75 项种子文件逐字节核对。子进程 PYTHONPATH 仅指向该工作区的 src。审阅入口正常 import 固定驱动，只装载 `R8R2NativeBridgeTests.test_N1`；驱动原 bytes 未改，SHA256 为 `6f956a134ce2d0f2075bb23ccb52d0ef0443bfd692d556e486d9f8339051dfff`。

实际 `annotation.runtime.storage.__file__`：

`D:/1800/docs/evidence/A03/review/P2-R8-R2-projection/isolation/workspace/src/annotation/runtime/storage/__init__.py`

annotation、storage/native、contracts/recovery、producer 及驱动的真实导入路径和 raw SHA256 均核对为本次导出，见 [实际导入](../evidence/A03/review/P2-R8-R2-projection/independent-imports.json)。没有从执行工作树 import。源包 68 个文件与全部种子在运行后仍与冻结 raw bytes 相同，见 [种子保全](../evidence/A03/review/P2-R8-R2-projection/independent-input-preservation.json)。

测试父 PID **18032** exit **0**，原 unittest stderr 为 **Ran 1 test in 24.582s / OK**；效果子 PID **33740** exit **87**、barrier_released=true、无 timeout/alive。marker 的 PID 与效果子相同。另三个实际观察子进程均 exit 0，四个嵌套子进程均已 wait/退出。见 [父原始结果](../evidence/A03/review/P2-R8-R2-projection/runs/independent-n1-01/completion.json)、[测试原输出](../evidence/A03/review/P2-R8-R2-projection/runs/independent-n1-01/stderr.log) 和 [自有嵌套释放](../evidence/A03/review/P2-R8-R2-projection/independent-nested-release.json)。

随后未调用 native API，用自己编写的标准库查询另取自有 immutable 副本，重新核对正式登记与实际资源：

| 独立新库 | raw SHA256 | 读取结果 |
| --- | --- | --- |
| runtime | `7c97fee3eb4b47cdc191e8461f53c082aadf33b8f129039a1522dc9e1efe48f2` | plans/actions/intents/permits/resolutions/PRE/creation_anchor/report_read 各 1，artifacts=20，计划 FINISHED。 |
| target | `455ccbf685d387cfa3c2ca8906f9ef427d053ef8523803ba6c19a895937b3d1d` | effects=1，observations=4。 |

读取前后 raw SHA 一致，副本已清理，未对新源库再建立 SQL 连接。该独立运行没有 N2 的目录变更或 hold，只有 N1 case。详见 [独立数据库核对](../evidence/A03/review/P2-R8-R2-projection/independent-database-review.json) 和 [独立正式绑定核对](../evidence/A03/review/P2-R8-R2-projection/independent-boundary-review.json)。

独立原件的关键 ref 均 revision=1：

| 产物 | artifact_id / content_hash |
| --- | --- |
| plan | `plan-r8-r2-n1` / `51c22f305025a1726163a55a06237a92c1180ccf08fea1ae35d54a7c2ded3052` |
| 正式 receipt | `executionreceipt-bfdd3842e9af4c3ba60d221a3095d272` / `875d5662708ccdfeb61ab0094268ce5d03ed3820093f722d0fe7b891ebe4e5ec` |
| terminal head | `resolution-23340bee38c045c98102069d410ad711` / `87a7233106348146ac3b0192e70d2ff6b6bf1cf6ba6eae61f34a06c4f505a4d0` |
| POST | `native-post-cbc0f28bd20f475982cdeee18174a002` / `3bad96189b40442f6a9806708653e249dafe1b5ab6ec9ed568750499f34c4e0b` |
| Batch | `native-batch-4e57280a56354851a761c963b64c0189` / `d0f53d9400a474e1e8e5d128ca7e40ed9a1532bef4a9074a2fc41ab8ebd3651e` |

这些 ref、当前包摘要和数据库字节均与作者运行不同，来自本次新库和新资源。独立核对接受的是以下实际边界：

| N1 项目 | 独立结果 |
| --- | --- |
| PRE、TARGET、真实单动作计划 | PRE durable ADMITTED，接受计划绑定实际 plan；一个 CREATE_FRAMES。 |
| permit、目标效果、子崩溃 | 唯一 permit CONSUMED，效果恰好 1，真实屏障与 exit87。 |
| 原 UNKNOWN/原回执缺失 | 原 UNKNOWN progress `executionprogress-db4e831863a54c1cbb5193bbaaefa815` 原样保留，其 receipt_ref=null。 |
| 终局只读 head | RESOLVED_APPLIED，original_receipt_ref=null。 |
| 晚到正式 receipt | SQL artifacts、当前登记包、intent.receipt 的完整四元组一致；results/action_fact_refs 聚合实际不可变 fact。 |
| 两个正式 material progress | `executionprogress-d53277d4edf74e57977c93fd26c530ff` 和 `executionprogress-76d06b99045b49708c333afe401105af`；plan_ref、action_id、intent_ref、attempt_fact 四项逐一相同，尝试证据与原 fact 相同。 |
| 未改写尝试事实 | 两个 progress 均保留 MAY_HAVE_BEEN_ATTEMPTED；material fact raw SHA 为 `cf262a9c0b820a6e839f3068b1d96644e1ffdf2312aafe11a31eea87ef9acc2b`。 |
| 独立新 POST/Batch | 正式登记、receipt/head/action/fact 绑定正确，报告快照和观察 Resource 与终局对账观察不同，durable report read=1。frame_structure=PASS，内容仍 PENDING、NOT_SUBMITTED，Batch 为 CONTENT_PENDING。 |
| 无重发 | 独立最后查询 effects 仍为 1，没有因 UNKNOWN 重复执行目标效果。 |

因此，本次可确认固定合成 N1 完整链的有限功能结果，而非只有文件系统候选或作者自报成功。历史 UNKNOWN 没有删除；创建锚点原字节核对，但 UNKNOWN 历史下 N6 重算未在本轮执行。

## N2 的首次阻断与最小接口缺口

N2 没有复跑。原 driver 在正常受控合成目录变更后调用 detect_target_drift，作者冻结 SQL books.hold 与 TARGET_DRIFT_HOLD 事件的 hold_id 均为：

`target-drift-hold-347994b72519469fa107efe6d613fa22`

原 N2 父 PID **54044** exit 1，stderr 为真实 ERROR，调用栈：

`test_N2 → begin_native_pre(kind='POST_HOLD') → _lease → TARGET_DRIFT_HOLD`

独立静态定位与原栈一致：

- [native.py](../evidence/A03/review/P2-R8-R2-projection/isolation/workspace/src/annotation/runtime/storage/native.py) 第 **318** 行先调用 `_lease(connection, book, owner, generation)`，没有传 pending_ok；第 319–320 行才区分 INITIAL/POST_HOLD。
- [storage/__init__.py](../evidence/A03/review/P2-R8-R2-projection/isolation/workspace/src/annotation/runtime/storage/__init__.py) 的 `_lease` 默认 `pending_ok=False`，第 **346–347** 行在非空 hold 时拒绝。原栈的异常文本恰为上述真实 hold id。
- 作者冻结库只有一个旧 INITIAL ADMITTED run，**POST_HOLD run=0**，未进行新 POST_HOLD 观察、五检查、接纳或 hold 清除。books 最终为 RELEASED、owner=null、generation=4，是 N2 finally 的释放后状态；不能把该最终状态冒充失败瞬间的 owner 状态。

原 driver 中旧 INITIAL 拒绝断言位于失败 POST_HOLD 调用之前，已执行到其后；但它使用 `assertRaises(Exception)`，捕获的确切异常 code 未单独原始记录。因此只确认该旧证明被拒绝的固定断言，不能编造其具体拒绝码或宣布整个 POST_HOLD 生命周期通过。

最小修复接口在 `begin_native_pre` 的 **POST_HOLD PRE 启动与 lease/hold 读取衔接**：后续明确任务须为这种受控只读 PRE 启动取得合法的当前 owner/generation 和 exact hold 上下文，并保留 INITIAL、普通写入和当前资格路径的 hold/pending 守卫。不能把 `_lease` 全局默认改成宽松、清除 hold、沿用旧 INITIAL 或绕过登记/来源/目标/观察/预算检查来取得写入资格。

本轮未修改 `_lease` 或 begin_native_pre，未创建 POST_HOLD run，未继续 N2/N3–N7。新的持久 hold 不构成继续写入授权；剩余接口修复与 N2 标准须由下一份有界任务另行明确。

## 兼容、释放与封存辅助错误的限制

[作者过程核对](../evidence/A03/review/P2-R8-R2-projection/author-process-review.json) 核对 **26 组已登记** preregistered/started/completed、argv/cwd、脚本/产品快照、PID、原 stdout/stderr 和退出；记录均无 timeout/alive。N1 子 exit87、N1 父 exit0、N2 父 exit1 与其用途分别相符；C01 三个 exit1 为 valid=false/MISSING_REFERENCE 的预期 CLI 拒绝。

minimal、N1、N2、C01、A02、R7 的 product-source-index 相同，SHA256 `aa3bd32f82c27d5916052676f66de2ec9528921341da5f3f1c6ea683b477a124`，关键产品快照与本次最终 target 相同。最终候选 C01 **70**、A02 **52**、R7 **13** 项的原 stderr 均 OK，无 skip；本轮未重跑这些套件。

另一次封存辅助生成命令的 PowerShell 引号传递 SyntaxError **不具备上述完整 PID/raw 过程证据**：只有工具 chunk `1f2eb8`、exit1 和明确标注的转录摘录，PID 为 null，独立 raw stdout/stderr 未提供。原 JSON 说明它未创建目标文件、未运行产品，随后由单独预登记 prepare_sealer 完成辅助准备；审阅没有重建或伪补原日志。26 组已登记进程核对不能写成这个未提供 PID 的辅助命令也有完整原始进程证明。这一限制与 N1/N2 产品结果分别保留。

本审阅自有 N1 父与四个嵌套子进程均保留原始登记/输出/退出并 wait；所有只读检查另有独立记录。释放依据限自有 Popen wait 和已保存完成记录，不进行当前 OS/profile 扫描。见 [自有进程释放](../evidence/A03/review/P2-R8-R2-projection/process-release.json)。

## 最终范围

投影修复及固定合成 N1 完整链有限接受，不等于整个 A03、POST_HOLD 或真实平台恢复接受。N2 未通过，N3–N7 保持 NOT_RUN_AFTER_NEW_INDEPENDENT_PRODUCT_BLOCKER，原 P2 V01–V10/R01–R18 未豁免；B 跨侧合同未共同确认，I01 不释放。

字段重置专项始终 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`。本轮没有专项或变体、委派或重测建议，未联系 B/执行者；零网络、浏览器、真实平台、凭据/profile、OCR、模型/付费 API、安装、A05 题22重放或推送。

仅新增本报告和 R2 审阅目录。记录 exact inputs、自有运行原输出及实际导入、正式绑定/数据库读取证据、进程释放和 [完整 SHA256 清单](../evidence/A03/review/P2-R8-R2-projection/sha256-manifest.json)，只排除清单自身；[最终核对](../evidence/A03/review/P2-R8-R2-projection/final-verification.json) 在封存时复核输入/历史保全与目录集合。无产品修复、无重复 N1、无调度 state 或用户 model/thinking 变更。最终结论：**N1 有限 ACCEPTED，N2 阻断，R8/A03 整体 REWORK，I01 未释放。**
