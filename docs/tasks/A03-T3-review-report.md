# A03-T3 第一阶段独立验收报告

2026-10-18（Asia/Shanghai）。**ACCEPTED，仅限原28项余量映射及历史结论边界。** 后续集成计划仍须下文一份合并修订清单和调度一次裁定，尚不是可直接执行的任务单。本结论不接受A03功能或产品，不集成，不释放I01，不代表B共同确认。

## 固定身份与审查范围

| 身份 | 确切版本 |
| --- | --- |
| T3交付target | `3fcdb73416142a0a85dfb951a7f839849871c549` |
| 产品基线P | `1330047dd29890dea0e433ff01b991f615bf78f4` |
| 原任务workflow W | `f7084b2e8f2e9a1fcf758f9cba56ec9c9fb1f304` |
| 本次验收交接workflow | `69ef1b3456c7c44c463c4f4fb43b6064b8cf4e09` |
| 原作者交接H | `6b61ac9d623e76cbe6311f64d012fd04e2e03c21` |

被验文件为target中的[余量矩阵](A03-T3-remaining-matrix.md)、[集成计划](A03-T3-integration-plan.md)及其execution索引；全部按raw Git读取。自有最小隔离导出位于 `D:/1800/.local/A03-T3-independent-review`，包含六份交付原件及必要固定源码，不是浮动工作树或历史全集。未执行作者audit脚本：它把ROOT/OUT固定到执行者工作树，会写执行者索引；本轮另用标准库静态脚本独立核对。

仅审查文档、源码和必要索引。产品导入、业务执行、SQLite连接均为0；没有把新T1/T2结果倒灌此冻结矩阵。后续仍须独立接受的T1/T2确切提交和调度组合target。

## 完整性与28项映射

独立结果见[身份与引用审计](../evidence/A03/T3/review/identity-and-reference-audit.json)、[逐项语义结论](../evidence/A03/T3/review/semantic-28-review.json)和[固定源码/决定摘录](../evidence/A03/T3/review/source-and-decision-anchors.json)。

- 相对P恰好6个允许新增文件，src/examples/tests差异为空；交付manifest raw SHA256为 `c5e801a381a04360ae223dd26ecf21fab9cd3db377985b7378ad0c8ebd998423`，5项成员长度/摘要全部一致。
- 70条引用的raw长度、SHA256、Git blob身份及所列行号均一致；44处关联manifest/release/index引用存在且摘要一致。本轮只核对这些必要索引，没有再次验证历史清单所有成员、SQL或历史业务。
- V01–V10和R01–R18共28个原编号均唯一映射，索引内原文行与W一致；每项子要求、已有有限证据和余量经人工语义核对，不能由28/28编号检查单独推出本结论。
- 作者结果、独立观察、调度接受、实际集成分开；E03只读codec的局部集成没有被放大为native集成。没有把旧REWORK、NOT_RUN或缺件改成通过。

矩阵正确保留了多动作/NOT_ATTEMPTED、跨scope/run当前账本、另书及合法多书包、真正新规划、版本/存储失败关闭、旧无intent UNKNOWN、真实来源拒绝、报告/分母/次数等原要求。没有漏掉必须关闭的整类原要求。S5的转换版本定性以及M3正向串接须按下文明确；它们不需要重造28项矩阵。

去重边界也正确：历史六类单动作切点、R10两例owner行为、R11四切点、固定MATCH/充分ABSENT、旧只读codec及静态消费者闭包按各自确切版本保留，不重新要求穷举交错或每个多动作重跑六切点。不同snapshot多头仍只在已选值层表达，不要求运行跨计划聚合。最新P改了共享归属/校验，历史接受不自动成为P通过；最终候选兼容需按实际consumer变化选择差量。

R11作者F2/F3、旧NOT_RETAINED和R12-R2 U2两阶段/journal缺失均不得追补。C/L1/U1仍为原作者结果；U2首错与后继未运行的分类保持，不把采集失败直接算作产品失败。field reset继续排除。

## 实现缺口与原依据

1. **未尝试入口属原要求的真实实现余量。** P的 `runtime/storage/__init__.py:1045–1048` 无条件关闭为 `EVENT_PREFIX_CONTRACT_GAP`；AST确认NativeRuntimeStore继承而未覆盖。V04/R11及P1-R2已接受的D04要求充分/不足ABSENT分开，不能拿R9 D2的MAY_HAVE_BEEN_ATTEMPTED替代。W的R1调度决定又明确独立持久三读、logical session与CAS方向，尚不等于当前产品已实现完整协议。
2. **当前单题语言不能覆盖原多动作要求。** P的 `quality/synthetic_precheck.py:50–85` 固定一图、一题、两片段；planner `:265–290` 每题生成动作。W的R8实施及R8-R4调度决定明确该语言有限，原V01/V04/R11不豁免，多动作须另有有限采用范围。三题/三页是可审的实现候选，不是原标准规定的唯一方案。
3. **新规划正支有原依据，现列串接尚有静态接缝。** R12要求ABSENT后新快照、检查和真正新计划；R13及R8-R3决定没有接受合格清hold/不同hold替换正支。P的 `native.py:415–432` 在record_native_plan调用普通 `_lease`，而 `storage/__init__.py:340–347` 在hold活动时拒绝；`holds.py:315–317` 的clear又要求候选计划已正式索引。清除后，`native.py:160–174,258–284` 的POST_HOLD证明仍核对活动的确切hold。因而计划所列“生成/登记候选→清hold→消费同PRE执行”不能当作现成可用链。这里只确认该列举串接的静态缺口，未运行反例，也未证明所有替代接口均不可达。
4. **COMMITTED完成点有静态决定，数据库接纳不能顺带开放。** W的R1决定把“转换接纳点”和“已知DB接纳”分别列项；R2仅接受CONVERSION-07值级规则。P的legacy converter `contracts/recovery.py:1273–1279` 仍是初始夹具/COMPLETED_NEW_FIXTURE；R8实施明确新库fresh-only、既有旧库接纳/旧连接迁移继续阻断，P的native runtime/target元数据也如此。可定位旧转换与选定完成点的差别，但不能据此把当前native数据库迁移、任何新COMMITTED profile实施都直接认定为已获授权的必修项。

CLI限制同样有源码依据：现有 `runtime/recovery/cli.py` 的init/open/replan为legacy路径；不能在native库上直接使用。单独有界样例驱动可以作为命令行交付候选，但须满足原运行、核对、查询和导出用途。

## 一份合并最小修订与待裁定清单

以下四项一次收敛，不逐helper开门；不要求本轮实施、重跑历史或先补新动态证据。

| 编号 | 最小修订 / 调度需固定的点 | 边界与关闭条件 |
| --- | --- | --- |
| C1 转换与采用 | 将矩阵S5、G2/G3的“旧夹具转换完成点差异”“新profile采用待定”“既有DB接纳仍阻断”分开。调度决定K需要哪一种合法全合成初始转换及COMMITTED版本/完成记录；不得把DB迁移作为隐含前提。 | 原V08/V09/R14/R15的显式转换/中断/旧字节/legacy UNKNOWN要求保留。旧converter正支若版本与语义未变可沿用E00；确实选择新完成点时仅新版本差量，不重跑旧转换全集，不解锁旧无intent UNKNOWN。 |
| C2 M包及新规划接缝 | 一次固定满足原多动作要求的最小合成语言、oracle/profile/API/prefix/session/pins与唯一整合者；三题和具体产品文件仍为提案。M3补上候选计划在hold下正式登记、清hold后PRE/计划资格交接及最终再读/CAS的明确受支持顺序，或如实列该单一阻断。 | 上述静态路径足以说明所列顺序有缺口，不必先派业务来“发现”同一接缝；也不据此预授权改holds.py或共享合同。可以在同一完整M包处理，不删普通hold/pending/fence守卫，不恢复旧尾。 |
| C3 L包输入与计数 | L1/L2为当前可恢复intent、导入历史分别标明格式/来源、scope/run、LEGACY_UNRECORDED分类及预期pending数；明确R10“同书多个历史包”的最小材料，不能只用一句“完整保留”代替输入。说明L2两种B包表示是否各有新target/起点，统一“3个起点”与“2次B dispatch”的计数单位。 | 导入legacy可支撑另一scope未决保持，但不能当成可恢复新intent或由版本改标造历史。不得重复提交同B旧动作来验证另一种包表示；在同一个有限L包内明确材料即可，不新增历史生成专项。 |
| C4 G/F执行合同与去重 | 将G的20差量/11存储/7来源槽位等数值标为待裁定的覆盖上限，逐项按“原子要求＋实际守卫层＋确切实现字节”去重；相同T1/T2已接受覆盖在未来K清单扣除。一次选择native驱动或局部CLI方案，给运行/核对/查询/导出的命令与输出约定；F的异常限定为本计划的目标检查/重新规划。 | 不自动批准所有路径和数量，不把结构层拒绝算作后层验证，不把G扩成原七包/全套。F仅正常、明确未生效后新规划、UNKNOWN恢复三条有界路径；相同字节产物可复用，确有consumer变化才跑必要差量。真实A01/B接入、内容修正/OCR及S01能力另列。 |

C1–C4是同一份后续派发前的修订/决定集合；矩阵的原28项映射可保留本次有限接受。调度提供经过这些点收敛的有限任务和确切K后，才进入执行/后续独立功能验收。T1/T2当前结果不在本报告作判断，也不据其后来变化改写此次冻结结论。

## 复现、工具首错与释放

独立静态脚本为[身份/引用审计](../evidence/A03/T3/review/scripts/review_static.py)、[语义依据采集](../evidence/A03/T3/review/scripts/review_semantics.py)。在本仓库可分别以 `python -X utf8 -B <脚本路径>` 复现；所有Git子进程显式带 `-c core.longpaths=true`。它们不运行产品/作者驱动、不导入sqlite3、不连接数据库；可重算的只是文档/字节/AST/引用结果，人工计划判断见本报告。

身份/引用脚本一次成功，119条同步Git调用完成；语义采集首版把converter摘录终行写到文件长度之外，静态AssertionError退出1。已保留[首版脚本与观察输出](../evidence/A03/T3/review/reviewer-tool-failure-01/observed-output.txt)，只把摘录收窄为1273–1279，一次静态重跑成功，15条Git调用完成。没有业务重跑或产品修改。首错是工具返回的合并输出转录，未伪称独立保存了当时PID和raw stdout/stderr。

本轮只写专属review报告/证据及自有隔离目录；未操作主目录Git索引/提交、产品、执行者工作树、公共任务单或协调JSON。所有已启动命令均同步结束，无自有业务进程、后台服务、owner、浏览器/profile或其他会话待释放；不是机器全局PID扫描。

保持 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`。无网络、平台、凭据、安装、模型、OCR、推送、书级提交、A05题22、B或旧A03联系、委派。A03仍REWORK，I01未释放。文件摘要与最终清单见[review manifest](../evidence/A03/T3/review/manifest.json)，排除清单自身。
