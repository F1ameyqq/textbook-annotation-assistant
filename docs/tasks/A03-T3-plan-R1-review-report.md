# A03-T3 plan-R1 C1–C4 独立复核

2026-10-18（Asia/Shanghai）。**ACCEPTED，仅接受本次C1–C4计划修订及受影响引用。** D-CONV、D-M已足够明确供调度一次裁定，仍是未采用、未实施的方案；本结论不代调度采用，不授权产品修改或M/L/G执行，不接受K组合、A03功能、I01或B确认。

## 固定身份与范围

| 身份 | 确切提交 |
| --- | --- |
| 被验target | `765aef597a93fe36060fce65e17b22fe1c3408b8` |
| 前版文档target | `3fcdb73416142a0a85dfb951a7f839849871c549` |
| 本次复核workflow | `0beba0d0c82376b119c46b1d35a137fde541113c` |
| 作者修订依据workflow | `b6e00eb3d0512b4ad838676d72c28e8036125301` |
| 产品静态基线P | `1330047dd29890dea0e433ff01b991f615bf78f4` |

只复核target中的两份T3文档与 `docs/evidence/A03/T3/execution/plan-R1/`，以及原C1–C4影响的必要固定引用。既有[28项映射有限接受](A03-T3-review-report.md)沿用，本轮只检查28行原字节保全，不重新展开或验收原28项业务。自有隔离目录为 `D:/1800/.local/A03-T3-independent-review/plan-R1`；旧review目录与报告只读。

## 静态准入与保全

独立结果见[差异/引用审计](../evidence/A03/T3/review-plan-R1/static-delta-audit.json)及[C1–C4逐项结论](../evidence/A03/T3/review-plan-R1/c1-c4-assessment.json)。

- 相对前版恰好两份文档修改、七份新证据；src/examples/tests差异为空。交付manifest raw SHA256为 `02b80200878ddf09a08c603dc2a2c45bef4917764d978fc0019d58655f8b7937`，8项成员的长度/摘要全部一致。
- 17处受影响引用的raw长度、SHA256及适用的Git blob/摘录行号均一致；T1工具只核对固定身份和接受范围，没有导入或运行。未重复旧70条引用与44处历史索引全量审计。
- 旧4个execution文件相对前版原字节不变，28行映射原字节不变；旧独立报告、旧review清单及其成员共14个文件保持此前封存摘要。
- 作者首轮静态摘录越界退出1保留；仅摘录终行150改为149，首版/纠正脚本差异确为一处。纠正后的29条Git调用均有完成/回收记录。首错为合并工具输出转录，没有补称当时PID或分流raw stdout/stderr。本轮未执行作者脚本，也没有要求重跑产品来修复文档。

## C1–C4判断

以下行号均指target的 `docs/tasks/A03-T3-integration-plan.md`，不是主目录浮动副本。

| 项目 | 结论与依据 |
| --- | --- |
| C1 转换/采用/迁移 | **满足**（17–27、155行及矩阵S5）。保留旧初始converter有限语义和同版本/consumer证据复用；新COMMITTED记录只作为D-CONV条件性提案，列出初始文件范围、manifest单向引用、完成前INCOMPLETE、重开不补提交及候选入口。native继续fresh-only，DB迁移未批准，也不把新converter作为M前置。转换中断、legacy UNKNOWN拒绝等未证项保留，未宣称R15闭合。 |
| C2 一个M包/完整持有流程 | **满足计划修订标准**（29–67、156行）。选定最多三题、一个native样例驱动；拟议record_hold_candidate仅索引清hold证据，不接纳actions或发permit。clear保留独立最终读、owner/generation、完整pending、hold/head/CAS/fence和期限；清除后旧POST_HOLD证明失效，重新真实INITIAL PRE/TARGET/plan，再走普通record/run守卫。未尝试入口单列持久entry、无intent三读含最终currentness、失败耗次/期限、全局前缀及所有受控dispatch/claim/takeover的session守卫。精确候选文件/API/闭包/schema/oracle/pins影响集中列出，仍须D-M一次采用，当前方法不存在、实现OPEN的事实没有被掩盖。 |
| C3 历史材料/隔离/数量 | **满足**（69–99行）。N-A为真实可恢复native UNKNOWN；H-A1/H-A2为同书不同scope/run的C01/A02原生UNKNOWN归档，导入后永久LEGACY_UNRECORDED；目标身份匹配，先建立native UNKNOWN再导入。明确pending为1→2→3→2，另一书B为0；两种B表示优先只读各一次，B native只执行一次。首选native起点≤3、legacy≤2、合计≤5，dispatch合计≤6；若另选两个B执行则另给fresh target/action和备选上限，未混入首选。既有公开history.generate及A02输入生产路径可定位，不通过改标历史或SQL补造；不新建历史专项。 |
| C4 去重/命令/F边界 | **满足**（101–159行）。G数字仅为覆盖上限，按原子要求、输入语义、真实consumer/守卫层及递归依赖的实际执行字节和pins选择INHERIT/RUN_DELTA/WAIT/结构层拒绝。一个native驱动明确run、reconcile、query、export的命令/输出，未回落到legacy CLI；query/export不暗中对账或消费报告预算。F仅正常、ABSENT后真正新规划、UNKNOWN恢复三条；同字节/入口证据可复用，F新增起点可为0，有实质consumer变化才作有限差量。未把T1异常读回冒充terminal H1，也没有预填T2接受。 |

C3的层级限制仍须保留：C01单书/多书表示只读通过，加上native B账本隔离，并不自动证明mixed-native执行消费。修订稿84行已经要求此消费映射未证时单列未证明，不能据计划通过给原R10或整个L包功能通过。

数量核对仅是计划上限：M≤5起点/11次dispatch；L首选≤5起点/6次dispatch、两次reconcile，两个B表示不是两个业务起点；F可复用或至多3个起点/6次dispatch。它们不是本轮执行授权、必须跑满的数量或已实测结果。

## 留给调度的采用与派发输入

**必要修订：无。** 不再要求作者为相同C1–C4另造一轮矩阵、先实现产品或新增业务反例。

- **D-CONV**：在K中注明LEGACY_INITIAL_ONLY，或选择条件性新初始文件COMMITTED格式/入口；两者均不开放既有DB迁移，未选新格式也不成为fresh-native M的隐含实现要求。
- **D-M**：一次固定候选只读登记角色/API、prefix/session封闭字段/事件及全部受控写入口覆盖、语言/oracle/schema/API/implementation pins、精确白名单和唯一整合者。当前设计可供裁定，不等于已采用或证明可执行；若限定模型仍不相容，沿计划保留这一个M接缝，不退化普通守卫。
- **K与去重清单**：T2接受/释放后由调度给确切组合版本和consumer影响/继承表，再选择有限M/L/G范围。T2新交REVIEW由另行独立验收处理，本轮不判断其结果；文档的历史“待交付”表述不构成返工理由。

上述是原派发要求保留的采用决定与执行入口，不是新增验收标准或新的helper审批轮次。原28项映射接受及其未证业务范围不变，真实A01/B、S01、OCR/内容、平台事项仍分列。

## 复现与释放

本轮自有[静态审计脚本](../evidence/A03/T3/review-plan-R1/scripts/audit_plan_r1_review.py)以 `python -X utf8 -B <脚本路径>` 运行一次成功；40条登记Git子进程均有PID、限时、退出与wait记录，全部显式 `-c core.longpaths=true`。这只复现差异/原字节/引用/计数核对，C1–C4语义判断见本报告。作者脚本只读检查，没有执行。

产品导入、业务运行、SQL/数据库连接均为0；没有浏览器/profile、网络、安装、模型、OCR、平台、推送、A05题22或书级提交；没有联系作者、旧A03、B或委派。field reset保持 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`。

本轮只写新review-plan-R1范围及自有新隔离目录，未操作主目录Git索引/提交、协调JSON、执行工作树或旧报告/证据。自有静态命令均已结束，无业务进程、owner、后台或其他会话待释放；不是机器全局PID扫描。A03仍REWORK，I01未释放。最终文件摘要见[本轮manifest](../evidence/A03/T3/review-plan-R1/manifest.json)，排除自身。
