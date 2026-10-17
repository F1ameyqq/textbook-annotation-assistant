# A03 P2-R2 静态修订交付：REVIEW

2026-10-17，Asia/Shanghai，按本次明确的 `xhigh` 边界继续原执行工作树；未派发子智能体。本轮是一次有界静态修订，**没有产品实现、公共合同采用、exact oracle/pins 批准、B 确认或功能验收结论**。I01 不释放。提案确切提交在最终交付消息给出。

- base：`7fdbde8f16569fd3bc399013115e13269d5d33fa`
- workflow：`d834bf531f95abac7ed30b89b3ca55105fa6f491`
- 工作树：`C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800`，分支 `codex/a03-runtime-recovery`
- 只新增本报告、`examples/a03/P2-R2-proposal/`、`docs/evidence/A03/execution/P2-R2-proposal/`；不合浮动主树。

独立 R1 结论 REWORK 和调度决定原字节见 [输入索引](../evidence/A03/execution/P2-R2-proposal/input-index.json)。本轮只导出15份必要文本/诊断/Schema/规划源码，不复制309份历史档案；309是调度已核验的历史记录。架构/公共合同在本次 workflow 与执行 base 间无差异；采用冻结 AGENTS/coordination 与本次任务边界。旧 candidate-v2、旧检查器、所有旧报告/失败证据均不变。

## 唯一候选与 exact pins

规范见 [SPEC](../../examples/a03/P2-R2-proposal/SPEC.md)。唯一候选为 [candidate-final/profile.json](../../examples/a03/P2-R2-proposal/candidate-final/profile.json)：

| 项目 | 固定值 |
| --- | --- |
| profile | `a03-p2-r2-static-2-PROPOSAL` |
| profile raw SHA256 | `f7385ba20090b5df8aa062c417e3d5c66a889a30f464facff994d9929b94f9ea` |
| exchange / 新 Artifact | `a03-exchange-3-proposal` / `1.3.0-a03-static-proposal` |
| 完整 pins | profile 中六份 Schema 的精确集合，另含 API/oracle/verifier SHA 及历史 prefix 来源 pin；缺失/额外/错误均拒绝 |
| API SHA256 | `b5210ab175ccfd3f1f8f6baf0da07a3757dac732decf3bfa3de0b65354b0eba8` |
| oracle SHA256 | `659a715bd293026e28ec50f6bccbe1cecdf6511d168afc9f98d9ab05f6e8efb9` |
| 静态 oracle verifier SHA256 | `6667659ccc71cf1c0769d2ca7c684021140046a71a2ca73e40699aa354afac2d` |

`candidate/` 是首轮时间负值的保留原件；旧 R1 candidate-v2 是另一份历史提案。两者均不能作为本轮 selector 别名或混选 pins。1.1 仅作不可变只读输入；新1.3类型在结构与语义 registry 中覆盖一致。静态代码能解析不授予 native 资格。

## 三个缺口的本轮结果

| 缺口 | 新的完整值与入口 | 实际静态证据 |
| --- | --- | --- |
| SCOPE-01 | [双 scope 全包](../../examples/a03/P2-R2-proposal/candidate-final/scope-session.json)，同书 original-a/original-b、不同计划、两层 Resource；新 receipt→fact→basis→prefix 是实际外层路径 | `Package.validate()` 统一验证整个15 Artifact包；typed frames 接管各自递归声明/推导 scope，header/非frame仍同 scope；Artifact/Resource/frame 使用同一 DAG。错误 scope、漏声明、他书、伪frame、混合环均按指定层拒绝 |
| SESSION-02 | [basis](../../examples/a03/P2-R2-proposal/candidate-final/session/basis.json)、prefix、fact、完整 receipt | gate/session 与所有 owner/fence/登记/target/call/entry 字段一致；H0 为 STARTED 紧前头，窗口只允许本session三读记账，Hfinal/唯一fact/CAS前驱绑定；读序列、其他登记、窗口控制事件、超长entry及不同fact重复永久键拒绝。同一fact有多个消费者允许 |
| CONVERSION-07 | [新初始完整包](../../examples/a03/P2-R2-proposal/candidate-final/converted-initial.json)、[映射](../../examples/a03/P2-R2-proposal/candidate-final/conversion/mapping.json)、[状态分支](../../examples/a03/P2-R2-proposal/candidate-final/conversion/case.json) | 新 Source/Evidence/Graph/Snapshot/PRE 经同一全包入口；四个旧初始节点映射、三个旧派生PRE/TARGET/plan归档、新INITIAL PRE另列来源；新旧payload/嵌套JSON/资源摘要与完整分母闭合。COMMITTED独立引用manifest，不反向自引用；rename后未COMMITTED等五类状态拒绝接纳 |

两个已归档 session 诊断原件完整保留。本轮把它们**各自损坏的字段**投影到新的完整 basis 后，分别报 SESSION_BINDING 与 H0_CHAIN；不是把旧值直接送新 Schema 靠版本差异拒绝。旧新Source诊断通过新的完整1.3初始包覆盖，不再出现 unregistered new kind。参见 [静态结果](../evidence/A03/execution/P2-R2-proposal/static-results.json) 及其中精确 raw-input SHA、错误路径和 [负值复现差量](../evidence/A03/execution/P2-R2-proposal/negative-values/archived-initial-head-not-in-canonical-prefix.json)。

这些结果关闭的是本轮列举的静态消费者/字段自洽缺口，不证明真实完整账本、锁、读取、计数持久化、原生 fact index/CAS 或转换器已工作。普通 Resource不获通用scope豁免。登记元组推导分支在规范中封闭为旧严格hold元组与exact Source/Snapshot；本轮没有该分支独立正包，未将其记作已验证。

## 调度决定到规范、样例和未来证据

| 决定编号 | 规范位置 | 本轮样例/检查 | 后续功能证据（均NOT_EXECUTED） |
| --- | --- | --- | --- |
| VERSION | SPEC V | 精确profile/六pins/API；12类registry；旧节点只读 | 新旧入口与实际接纳/拒绝 |
| SCOPE-01 | SPEC S | 同书两scope全包、嵌套Resource、typed边界与混合DAG | 原生全书/registration/index等值；登记分支正包仍缺 |
| SESSION-02 | SPEC T | archived两反例、H0→Hfinal、三读/绑定/唯一fact | 真正锁/fence/reads/CAS/UNKNOWN核对与原子性 |
| BUDGET-03 | SPEC T | 3实际读、2/8/60/1/5秒、lease10/续期2、read前计数、绝对期限约束 | 真实计数/崩溃耗次/重开不重置/续租与超时 |
| ADOPTION-04 | SPEC A | 明确原四meta+四新键、adoption事务/nonce/事件、跨存储失败状态、旧连接退出前提 | 所有旧writer退出/重启阻断、旧open拒绝、target fence与崩溃；无法覆盖则接纳BLOCKED |
| R17-05 | SPEC R | 新单题输入、未改planner255–287行的一动作条件推导；原多头仅值层 | 整体可达性因1.1 observation bridge vs1.3新输入而BLOCKED，需另裁版本桥接；未作原生通过 |
| PRE-06 | SPEC P | INITIAL无hold、POST_HOLD exact hold/new observation；五项固定oracle比较及逐项反例 | exact oracle/实现独立批准、实际五检查/私有run接纳、新TARGET/plan/hold正向和第二变化 |
| CONVERSION-07 | SPEC C | 完整目标/双向映射/原件、COMMITTED唯一点、各不完整状态拒绝 | 真转换、六故障点/只读重开/新id重做 |
| RETENTION | SPEC E | 本轮预登记/持久原始流/失败finally/退出与仅自有进程释放 | 业务进程树containment与存储/target原件保全；历史NOT_RETAINED不恢复 |

## oracle、R17和接纳限制

原始新固定PGM的 SHA256=`9fc6a5f04ac863f5edb9e145b90b440aa5a5745326e4b44e1b83b61e784ef890`；新写的已知1.1初始原件 SHA256=`5f4ab079d6b5eef146db4ad013aad29b42e5fe2d2edf330340113f03645558f1`。它们是本轮静态输入，不是历史失败恢复件。oracle是单题/两矩形的固定作者声明，尚未独立批准；Graph生成器不读取其expected字段。verifier逐项比较像素/尺寸/来源摘要、结构/几何、答案关系、覆盖分母和policy，未以graph hash相等或producer输出自证。

五项 STATIC_MATCH 和五个对应 STATIC_MISMATCH 只属于静态层；INITIAL/POST_HOLD run 都仍 NOT_EXECUTED/UNAVAILABLE，新PRE=HOLD、无native registry/run。完整静态 COMMITTED 也不等于真实转换运行或执行资格。没有实现 B、OCR、一般新算法或自动迁移框架。

R17只证明在真实PRE/TARGET和所有当前检查满足时，未改planner会对一个Graph question产生一个动作。现有 observation bridge 的308–309行只接受1.1计划；新初始/新PRE为1.3，旧版只读。**合法版本投影/adapter及新profile消费未改planner输出的合同仍未裁定，完整原生路径BLOCKED。** 不使用手写计划、旧stub、剪裁旧三动作计划、续旧尾或跨计划/scope聚合替代。多头保留为旧R1值模型，不代表原生多头历史。请调度在此残余处另作范围决定，不自动追加本轮实现或无限修订。

DB接纳选定meta+event和目标fence分阶段门，但从未打开DB。额外meta只能让后续旧open失败，不能撤销旧已打开连接；无法确认全部旧writer退出并阻断重启、或任一受控写入口未覆盖，接纳继续BLOCKED。不能把静态fence字符串/布尔或持久记录计划当作排他已实现。

## 实际命令、失败和冻结

在本工作树复核当前静态值：

```powershell
python -X utf8 -B examples/a03/P2-R2-proposal/check.py
python -X utf8 -B docs/evidence/A03/execution/P2-R2-proposal/verify.py --check
```

正式持久运行使用 `runner.py <新run-id> check`；不得覆盖原run。生成器默认要求目录尚不存在，冻结后不重生成。完整原始命令/cwd/SHA/PID/流/退出见 [check-05](../evidence/A03/execution/P2-R2-proposal/runs/check-05/exit.json)。最终静态结果36条：7项STATIC_ACCEPTED、23项预期静态拒绝、1组含五项STATIC_MATCH、5项逐检查STATIC_MISMATCH；不是36项功能通过。

check-01 原件因观察时间晚于 READ_FINISHED 报 READ_TIME、退出1；`candidate/` 及原stdout/stderr/exit保留。author-02另立 candidate-final 修正时间，check-02至05逐次保留记录。首批wrapper已预登记脚本SHA、持久流及退出，但尚未保存当时entry源码快照；不重建冒充原件。后续wrapper已在启动前保存entry/helper源码快照，当前失败原始日志齐备；这个早期源码快照限制如实保留。历史P2 NOT_RETAINED按调度决定继续作为不可修复限制，不改成通过。

本轮产品运行、DB查询/原生session、网络/浏览器/平台/profile/凭据/OCR/模型调用、安装、推送、调度state改动、联系B/验收者均0。既有被拒字段重置保持 **NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION**，没有复跑/变形/委派，也不列后续测试。

[范围与旧原件核对](../evidence/A03/execution/P2-R2-proposal/delivery-verification.json)、[自有进程释放](../evidence/A03/execution/P2-R2-proposal/process-release.json)、[统一清单](../evidence/A03/execution/P2-R2-proposal/sha256-manifest.json) 在退出后冻结；清单覆盖本轮所有实际文件并仅排除自身。旧Git原件逐字节核对、提交原字节复核和干净工作树以最后工具回执为准。

消费者影响仅为候选：contracts新版本选择/递归消费者/Schema与conversion；runtime storage/common/holds的持久session/meta/CAS/guard；recovery observation/lease/cli/quality；固定synthetic PRE verifier。未修改上述产品文件、根依赖或共享入口。Exchange/跨scope/Receipt/POST/Batch仍需公共接口双方确认，本轮不替B作确认。

**冻结后停止在REVIEW**：本轮静态值自洽结果交独立审阅；R17版本桥接、登记分支正包和全部原生证据仍按上表保留，不能据作者检查自行记为接受或释放I01。
