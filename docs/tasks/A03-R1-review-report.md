# A03-R1 等价内部替代独立验收

2026-10-18（Asia/Shanghai）。结论：**REWORK，整包未闭合；M 五例、L1 及下述依赖拒绝检查有限 ACCEPTED。** 本次在固定 raw Git 副本中独立复现了五个 M 起点、10 次 dispatch，并在自己的 M2 状态上复验 L1，未新增 dispatch。没有发现这些实测路径中的产品语义缺陷；这不证明尚未运行的 L/G/F 余量成立。A03 整体、I01 释放和主目录集成由调度决定。

## 固定对象、范围和采用

| 项目 | 确切身份 |
| --- | --- |
| 正式派发 workflow | `07708f34`，`A03-R1-review-dispatch-2026-10-18.md` |
| 原实施授权 workflow | `0476257d34e39cc8cc4a2a0b4b99c26dbe85c0e6` |
| 固定起点 | `d5f777590e72eb070af0497afdb144d60c61b95d` |
| 产品候选 | `6097a06de937fee8876feccedf46920510850b83` |
| 最终交付／本次执行视图 | `54e86adfaf144093a688b62fe0dad5190ceb2fa6` |
| L 驱动首次／纠正冻结 | `d0438c998c9e161ae7d919e2ac83ce9075a56751`／`456740b4360c408efdc3165e6e98b136770613ab` |
| 作者报告 raw SHA256 | `f0a8f282194b9a3b8ea84ce2eeaa3472be99c1c1119e0579b24574f2a3d76f6c` |
| 作者 manifest raw SHA256 | `be1e8da1c7a7da02b82ddd3e2803bb8fa44e3b1048ccdf8c114a459f5d768f16` |
| 独立目录 | `D:/1800-worktrees/a03-r1-review-54e86adf` |

以 `git -c core.longpaths=true` 和 `cat-file --batch` 导出 raw blobs；独立本地仓库 HEAD 绑定最终交付，不在作者目录或主目录运行产品。候选至最终的 `src/` 差异为零，六个后续提交仅一个产品 src 树。1300 个作者清单成员、35118730 bytes 全部重新核对，无长度或摘要差异；1316 个改动路径均在批准范围。旧证据、公共合同、根依赖、delivery、quality 等只读范围无改动。36 项 implementation/schema pins 均与实际 raw 执行字节相符，API/oracle/schema 语义未改。详见 [静态核对](../evidence/A03/R1/review/static-audit.json) 和 [副本索引](../evidence/A03/R1/review/snapshot-index.json)。

T1 只沿用 `ed90664ab15afd1938725441e2bc86db7884f784` 的 capture 与 L1/U1–U5 原有限接受；capture SHA256 仍为 `3e07d56f409d8203c42f252f7a2900e902e31f56e1ff5fc7475335d33d0b042b`。T2 只沿用 `699f748a124162b3118e3996c03757725daac363` 的 C12/H1 及 workflow `94c376914db82942ceb0246f338e5caa574cfb42` 归档接受。通过 workflow `07708f34` 的调度接受/原复核文档核对这些边界；没有把它们改标为当前共享校验组合整套实测通过。

## 内部替代审查

`_validated_value` 已实际接入 `_issue_context`、私有 runtime `_validate` 和公开 `validate_native_bundle`。它按 registry 实例内的规范 root、实际 selection/pins、完整规范输入摘要索引最多 16 项纯计算结果；命中后使用新的 ResourceReader 重读全部 manifest bytes 并检查路径/摘要。manifest 合并 StaticPackage 和 recovery closure 实际读取的资源；输入或每 consumer 声明变化转入完整校验。单次 closure 的资源扫描仍区分 media type、book、scope、实际 consumer；每个 consumer 的声明独立核对，混合图边与环检查保留。NativeSchemas 复用同次读取的文档，未以 caller 自报验证、skip 或全局 PASS 代替依赖检查。

缓存不包含 owner、generation、fence、head、pending、hold、PRE proof、permit 或目标观察。独立逐方法 AST 比较确认 `_lease`、intent/permit/授权、`_guard_target_effect`、`NativeRegistry._current/_dispatch`、`_pre_lease` 和未尝试入口与起点一致；hold、recovery、publisher、持久目标和 reconciler 字节也一致。实际链仍为：intent 本地事务提交 → permit 消费/实时账本门 → 目标独立事务内 fence、完整 target hash/version 和相关前置条件检查 → 新读回 → runtime 结果提交。M3 的旧 POST_HOLD proof 拒绝和 L1 当前全书 pending 阻断提供本轮动态差量。没有用长事务或缓存结果替代这些资格边界，也没有合并 runtime 与 target 的事务。

独立预检复跑 8 项既有合同控制和 3 项复用控制，全部通过；包括缺 nested ref、第二 consumer 缺声明、错书/scope、成功后改资源/实现、同 size/mtime 换 bytes、不同 root/registry 和伪 context。另作 5 个独立负控：暖缓存后改递归叶资源、第二 consumer 去声明、OBSERVED EvidenceRecord、native schema bytes 和 `_json.py` helper bytes，分别命中 `RESOURCE_HASH`、`UNDECLARED_REFERENCE`、`SYNTHETIC_ONLY`、`NATIVE_SCHEMA_PIN`、`NATIVE_IMPLEMENTATION_PIN`。全部零 DB/目标/dispatch；原字节均恢复，详见 [独立负控](../evidence/A03/R1/review/runs/dependency-controls/results.json)。

`_validate_native_for_registry` 的旧 docstring 仍声称 “One fresh complete validation”，与现在条件复用的实现不符。这是已知文字欠项；本次未改产品或重绑 pins。

## M/L1 独立实测与证据边界

沿用固定驱动和输入，每例只执行一次。子阶段 180 秒、每例父进程 240 秒；批次记录器 1250 秒仅容纳五个独立父预算，不延长任何单例。读回 2 秒、entry 8 秒、gate 5 秒、lease 10 秒/续期 2 秒、PRE/currentness 和核对次数均未调整。环境为既有 Windows CPython 3.9.13；未安装依赖。

| 场景 | dispatch／实际变更 | execute wall／CPU 秒 | finish wall／CPU 秒 | 完整校验／入口 | 独立结果 |
| --- | --- | --- | --- | --- | --- |
| M1 | 3／3 | 26.141／23.188 | 1.844／1.828 | 25／257 | 三动作 APPLIED；3 intents/permits；3题6框；独立报告一次；新进程重开拒绝旧计划 `REPLAY_FORBIDDEN`。 |
| M2-sufficient | 2／2 | 11.719／10.234 | 6.625／4.563 | 20／185 | A APPLIED、B UNKNOWN、C NOT_APPLIED/NOT_ATTEMPTED；C 无 intent/permit/dispatch；三次实际只读后 COMMITTED，正式 receipt，仍暂停。 |
| M2-insufficient | 2／2 | 12.187／10.813 | 3.828／2.438 | 17／178 | C RESERVED、无 fact/intent；两读后 ABORTED；重开同 entry 拒绝；只有 progress，无完整 receipt/Batch。 |
| M3-new-plan | 2／1 | 6.687／5.453 | 52.141／43.109 | 38／290 | 首次 not_applied 调用后 UNKNOWN → 新进程 ABSENT；候选只清 hold，最终再读/CAS；旧 proof 失效；新 INITIAL/PRE/TARGET/plan 后成功继续。 |
| M3-final-drift | 1／0 | 7.281／6.188 | 15.657／12.234 | 24／164 | 最终再漂移报 TARGET_CHANGED；hold 留存，候选无新 dispatch。 |

五例合计 5 个 fresh native 起点、10 次调用、8 次实际目标变更；`effects` 表包含 not_applied 调用，不能把 10 当作新增题数。批次 wall 为 147.844 秒。1074 次入口中完整计算 124 次、复用 950 次，与作者同一有限输入的计数一致；这证明重复完整计算减少，未建立同环境成对基准、吞吐或任意规模性能结论。M3 finish 超过旧45秒不构成业务失败，原内部守卫仍按真实时钟执行。

**L1：有限通过。** 使用自己的 M2-sufficient 终态，原字节消费最终交付内两份既有 legacy 历史输入，未再生成 legacy 业务。新进程调用冻结 `deltas.py::ledger`，一次 `reconcile(max_attempts=1)` 得 MATCH；pending `1→2→3→2`，两个 LEGACY_UNRECORDED 历史仍保留，局部 native 包不能绕过当前全书扫描，新的 INITIAL 被 `BOOK_WRITE_PAUSED` 拒绝。目标调用记录仍为2；新 POST/Batch 来自另一次实际观察，报告读计数一次，原 UNKNOWN artifact/ref 和 intent 的原 receipt 绑定保持。此处 frame_structure=FAIL、整书仍 HOLD，不将它写成整书恢复成功或内容通过。

作者六组终态的12份 raw capture 库已在隔离副本中以 `mode=ro&immutable=1` 重新查询，均与 SQL.json 相符；独立运行42阶段/84份库同样重新查询，事件 hash/head 链、动作事实、目标效果、释放状态与 capture 相符。SQL 前后字节不变。没有打开作者原库、旧 A03/T3 pending 库或用最终库补造中间状态；逐库 capture 不声称跨库原子。作者51条完成记录和独立44条完成记录逐项核对；native 观察器的记录没有 `waited` 字段，其 wait/reap 依据是固定源文件中的真实 `wait()` 后退出/poll 记录，未补造字段。自有登记 PID 最终无活动项，keepers 已 stop/join，owner/PID为空、lease=0、RELEASED；pending/hold 没有为释放而清除。见 [作者原件复核](../evidence/A03/R1/review/retained-audit.json)、[独立审计](../evidence/A03/R1/review/independent-audit.json) 和 [释放核对](../evidence/A03/R1/review/release-audit.json)。

## 失败、冻结计数和剩余有界清单

**已确认的产品语义缺陷：本次选择的实测范围内未发现。** 这不豁免下面的缺证。

作者 preflight-01 把实际 `RuntimeFailure(NATIVE_CONTEXT_ROOT_FOREIGN)` 误写为期望 ContractError，属于测试断言错误，尚未建立 DB/目标；原失败和当时4份 source 差异保留。它不是一个已经执行 M 的冻结业务候选。

L 首次冻结 `d0438c...` 的 legacy 驱动把最后的 CheckReport 当 receipt；实际已调用一次 in-memory MockSession 后 AttributeError，完整执行结果未写出，不能追补成已留存成功历史。`456740...` 唯一纠正先保存 bundle、再按 kind 选择 receipt，随后两个 legacy 调用和 L1 成功。纠正轮 L2/B 在登记前 `RESOURCE_HASH`：raw PGM 为3579 bytes、SHA256 `1f82898615c67c676c532b17a8bd8e801c73eb6e7e2ba5a7f685bf1c3582cc7a`；失败输入3615 bytes、SHA256 `71e9910267fb626ad4498ef0787d98c06bcd14fa0226ef798a071dbdb31561b0`。仅 CRLF→LF 即逐字节等于 raw 输入，调用栈止于 setup 内 `_validate`。因此 B 未 register/claim/建 target/dispatch；这证明错误输入被拒，不能判另书隔离通过或失败。本轮没有为复现此已知错误再跑业务。

**计数结论：** 产品候选只有一个已执行的 src 版本；L 有两次冻结驱动包和两轮实际尝试，第二轮是针对第一轮的唯一纠正。作者“纠正额度已用”有 L 包事实依据，不能据此声称两个不同产品实现候选均已执行。原任务“本包最多两次冻结业务候选”也没有规定“只有改 src 才计数”；不能利用同一 src 或换名恢复业务额度。本次不判定存在可自动使用的新名额，不自行续派第三次 L 包，由调度根据完整冻结/尝试记录一次裁定。实际消耗另列：作者 native M=5起点/10 dispatch；legacy=首次失败1次＋纠正2次；L1复用 M2、reconcile一次/零 dispatch；B=0。独立 M=5/10、L1复用自己的 M2/零 dispatch，二者不混为作者第二候选或冲销作者消耗。

| 余量 | 分类与具体最小边界 |
| --- | --- |
| L2 输入接缝 | **驱动/输入问题。** `examples/a03/R1/deltas.py::setup` 使用 checkout fixture，须在后续获派范围采用与冻结 raw-view 一致的输入；本次未修。修正后仍须原 L2：同账本 A.pending=2/B.pending=0、B 单书/合法多书两种只读表示、B 一次 native 执行及 A 不变。不能将 B 的表示数算多个业务通过。 |
| L3 | **未运行。** 原有限新 UNKNOWN 族：旧项 ABSENT 后真正新计划产生新 UNKNOWN，旧 resolution/报告不可解新未决；原最多两动作/两dispatch/首intent一次reconcile，不重放已成功 M。 |
| L4 | **未运行。** 只在实际产物上作分叉、循环、错原 receipt 三差量，最多6次门调用，无新业务起点。 |
| G1 | **部分证据，运行差量缺少验证。** 引用/consumer/bytes/pins/root/registry 及 M3 旧 proof 有本轮检查；其余 plan/action/question/run/漏登记、graph/snapshot/policy/授权/能力及缺前置按原 coverage key 去重，只补确实受影响的门。结构层早拒绝不算运行门通过，20/40仍是上界。 |
| G2 | **部分作者证据＋静态支持，余量缺证。** 错 ledger/store、缺/坏 DB 的实际拒绝记录已核对；原初始化 before_completion 仅历史有限继承。SQL事务/文件写失败、未知runtime/target/交换格式及目录绑定尚未完整验证；只在自有负控副本内按原≤11边界补必要差量，不批准迁移或追补旧缺件。 |
| G3 | **角色/中断缺证。** native-as-readonly 拒绝、C01 archive无native资格和L1 legacy保停有材料；1.1角色/原转换中断等未闭合。保留 LEGACY_INITIAL_ONLY、fresh-native-only、NOT_IMPLEMENTED_BLOCKED，不要求新增 COMMITTED 格式或 DB迁移。 |
| G4 | **有限支持。** 作者六槽均到 SYNTHETIC_ONLY，独立新增 EvidenceRecord/递归依赖控制；receipt PLATFORM_OBSERVED 只到 SHAPE_oneOf，明确 REJECTED_AT_STRUCTURE，未证明后层准入。无需采集真实来源或解决S01。 |
| G5 | **有限值层支持，余量未运行。** M/L1 正式报告仍PENDING/NOT_SUBMITTED；VERIFIED为结构拒绝，改total_expected为DENOMINATOR_CHANGED；三分母组合只有纯 diagnostic。旧报告复用、多头不同snapshot值层尚缺，不为分母新增dispatch。 |
| G6 | **实际预算缺证。** max_attempts=0/4拒绝已留存；同intent同call最多三读、耗尽后新进程重开不补读未运行。M2无intent entry三读不能代替它；沿用原≤1起点/≤1dispatch、有效恢复≤2、实际读≤3上界，先到deadline如实停止。 |
| F | **材料可复用，整体收口未完成。** M1正常、M3真正新规划、L1 UNKNOWN历史报告已有当前版本独立材料；按上述限制及T1/T2确切范围继承，仍须完成原余量/采用和运/核/查/导出证据收口，不能直接释放I01，也不因此强制再造三个业务起点。 |

## 原 V01–V10 / R01–R18 逐项结论

“独立有限通过”只对应本表列出的场景；“历史继承”只保留已接受的旧版本边界；“作者证据”表示本次核对原件/源码，没有冒称本次亲自执行该项。未另开全交错矩阵。

| ID | 当前可支持的有限范围、继承与缺口 |
| --- | --- |
| V01 | **独立有限通过 M1。** 三动作、跨进程重开/去重、真实目标/回执闭合；仅固定native synthetic输入。 |
| V02 | **历史六类单动作切点继承** E04/E07/E09，当前相关守卫/事务调用链静态相同；M2/L1是新进程消费差量，未冒称六点当前重跑或所有交错通过。 |
| V03 | **独立有限通过** M3充分ABSENT、新规划与L1 MATCH；T1 U1–U5只保留原异常读回接受，共享校验变更后未整套重演。 |
| V04 | **独立有限通过 M2两支。** C无intent/permit/dispatch；充分可receipt、不足仅progress，未提前解锁。 |
| V05 | **L1独立有限通过；L2未证明。** 同书跨run/scope真实库扫描保停；B输入失败不能证明另书/合法多书隔离。 |
| V06 | **旧owner两例历史继承；M3旧proof拒绝独立通过。** L3新UNKNOWN未运行；field reset始终排除。 |
| V07 | **依赖/声明负控及M3漂移有限通过。** T2 C12历史接受保留；L4和其余G1运行门未闭合。 |
| V08 | **作者错身份/缺坏DB拒绝＋旧初始化有限继承。** G2文件/SQL/未知格式和G3转换中断仍缺。 |
| V09 | **L1 legacy保停独立通过；G4作者六槽拒绝、receipt结构拒绝。** 版本/转换余量未闭合，S01单列。 |
| V10 | **M/L1正式状态独立通过；G5纯诊断作者证据。** G6 intent同call三读/重开未验证。 |
| R01 | **固定范围/raw pins/清单和自有资源有限通过。** 首次legacy完整结果未保存、准备命令首错保留；不改历史限制。 |
| R02 | **8+3控制及5独立负控通过。** 公共和runtime入口均采用依赖重查；其余G1运行资格不据此概括通过。 |
| R03 | **E04/E07/E09六类单动作历史继承。** 本轮未增崩溃交错；新UNKNOWN终局/报告由M/L1提供差量，旧F2/F3缺件不追补。 |
| R04 | **独立有限通过。** 新PID、两真实库、独立持久目标和原件相符；intent→dispatch事件/目标记录顺序成立，源码保留独立事务。 |
| R05 | **独立MATCH/ABSENT/不足分支通过。** 核对零新增效果；异常五类仍限T1原接受，不伪称当前全部实测。 |
| R06 | **L1原UNKNOWN→解决→新POST/Batch独立通过。** 原artifact和intent.receipt不改；L3新UNKNOWN优先及L4链负控未运行。 |
| R07 | **L1独立有限通过。** 局部native包不含历史两scope仍全书暂停；未另构caller空账本输入，不做field reset。 |
| R08 | **声明/资源/root/registry负控独立通过；作者库身份拒绝支持。** 其余action/question/run/漏登记运行门仍缺。 |
| R09 | **旧C1/C2历史有限继承＋当前守卫静态核对。** 未新增竞争效果例，不宣称约束任意外部写者。 |
| R10 | **同书两历史包独立通过。** L2登记前失败，另书/合法多书及邻例运行未证明；A02 R1原失败保留。 |
| R11 | **M2两支独立有限通过。** 调用事实与效果分开；完整receipt/progress界限及前序正常变化正确。 |
| R12 | **M3新INITIAL/PRE/TARGET/plan与L1全书pending门独立通过。** 旧proof拒绝；G1只换ID/缺前置负控未全验。 |
| R13 | **M3候选/clear/CAS/新INITIAL及最终漂移独立通过。** 其余graph/policy/授权/能力版本差量未全验。 |
| R14 | **作者缺坏库/身份拒绝＋E06旧初始化有限继承。** SQL/未知格式/转换中断等未完整覆盖，不清暂停。 |
| R15 | **L1两个legacy无intent未解除独立通过。** native-as-readonly作者拒绝支持；G3四角色/转换中断未闭合，旧原件不重封。 |
| R16 | **G4六槽作者证据及EvidenceRecord独立负控。** 第七槽仅结构拒绝；S01、平台、B资格未取得。 |
| R17 | **M1/M3/L1正式报告/历史链独立有限通过。** PENDING/NOT_SUBMITTED；VERIFIED仅结构拒绝，旧报告/多头值层未跑。 |
| R18 | **M2 entry持久读限独立通过；G5诊断作者证据。** intent同call读限/耗尽重开尚缺，不混借预算。 |

## 命令、归档和释放

所有调用均 create-only，实际 argv/cwd/PID/退出和 raw streams 在 [processes](../evidence/A03/R1/review/processes/)。本轮关键实际入口如下，已存在的输出不可原地重跑：

```powershell
python -X utf8 -B D:/1800/docs/evidence/A03/R1/review/prepare.py
python -X utf8 -B D:/1800/docs/evidence/A03/R1/review/invoke.py --label preflight --timeout 150 -- python -X utf8 -B examples/a03/R1/run.py --mode preflight --candidate 54e86adfaf144093a688b62fe0dad5190ceb2fa6 --output D:/1800-worktrees/a03-r1-review-54e86adf/docs/evidence/A03/R1/review/preflight
python -X utf8 -B D:/1800/docs/evidence/A03/R1/review/invoke.py --label independent-M --timeout 1250 -- python -X utf8 -B examples/a03/T3-closure/run.py --batch --candidate 54e86adfaf144093a688b62fe0dad5190ceb2fa6 --output D:/1800-worktrees/a03-r1-review-54e86adf/docs/evidence/A03/R1/review/business
python -X utf8 -B D:/1800/docs/evidence/A03/R1/review/invoke.py --label independent-L1 --timeout 180 --pythonpath D:/1800-worktrees/a03-r1-review-54e86adf/docs/evidence/A03/R1/review/business/runtime-view/src -- python -X utf8 -B D:/1800/docs/evidence/A03/R1/review/l1_reproduce.py
```

M 的5条保留证据断言另通过；static/retained/dependency/finish/release 审计命令以各 `request.json` 为准。真实 annotation 导入位置/摘要和重建 raw-view 索引已核对，均属于固定视图；可重建视图本身不重复封存。新的 raw输入、双库阶段原件、正式产物、调用流与自有释放保存于 [runs](../evidence/A03/R1/review/runs/)，SHA256/长度索引见 [manifest.json](../evidence/A03/R1/review/manifest.json)，排除项明确登记。原作者及旧证据按确切提交引用，没有重新封存旧全集。

准备器首次将 `git checkout --detach` 与 path 参数并用而退出128；当时仅新建空clone、零产品导入/业务。原失败见 `prepare-first-failure.json`，纠正为验证空clone后直接设置其自身HEAD并导出raw blobs，没有改产品/驱动或消耗业务起点。静态只读Git辅助调用未逐条留存子PID；其命令/固定对象和外层进程退出保留，不把它们计入上述业务完成记录。

本次没有写产品、主Git索引、提交或调度JSON，没有作者/旧A03/T3/B联系、平台/browser/profile/凭据、网络、OCR/模型、推送、书级提交或A05题22操作。所有验收子进程已完成，原pending/hold保留；不自行接受A03整体、释放I01、安排返修或开始下一候选。
