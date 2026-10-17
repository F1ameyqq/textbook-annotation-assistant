# A03 P2 离线执行交付

状态：REVIEW（未满足 P2 全部交付条件，存在下列阻断与未闭合项）。这是执行者的作者检查报告；没有独立验收通过、集成或 I01 释放结论。

## 权限、版本与环境

本轮使用原工作目录 `C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800`、分支 `codex/a03-runtime-recovery`。执行 base=`940a5de33a24b1a3a9ded6e69ade1dd0609ed83a`，workflow=`6b77c436742cf2826083b109d8ed86b85539cba6`，A02 依赖仍为 `ec1b4defbfa3ec0f181d291106fb53313983e493`。workflow 派发、P1 接受、原任务和独立标准的原 Git 字节保存在 [inputs](../evidence/A03/execution/P2/inputs/)，[workflow 核对](../evidence/A03/execution/P2/workflow-input-verification.json) 逐一比较原 blob。

采用 D01–D08、P1-R1 API/逐消费者闭包和 R2 profile；冻结 API SHA256=`e2b0865fc1a25206181f3094155b059a6d34eb851afc750e813f0c2e89960f85`。七份旧 R2 Schema 原字节不改，以局部 `.gitattributes` 防止归一化破坏已冻结摘要。

合同提交为 `afea07bbc592366af6789e2e07dae1bfa47cfef1`、原字节修复 `b12f0eeee2a028a708c2e82a550bdd1029c8fa34`、历史视图及新资格修复 `d2a9d37900228b590f1c1a527fbdb38a591076d9`。runtime/接缝/测试实现提交为 `d95e8003088161ca1f927232c443ec09827cd545`，完整过程轮源码为 `12ecced6f0a81f8c48a7d0f5635c7a5d42955104`。最后防护修复及最终实现提交为 `fa645ac8fd70688f3293edc5cfb1077fc7bd9daa`，仅在 storage 中增加6行：进度写入持书闸，成功验证授权后销毁原生身份。[完整过程轮源码](../evidence/A03/execution/P2/frozen-source-inputs.json) 与 [最终源码](../evidence/A03/execution/P2/frozen-source-inputs-final.json) 分别绑定31个实际 Python 文件及原始 Git blob 字节；后续交付提交只归档文档和证据。

实际运行使用已有 Python 3.9.13、SQLite 3.37.2、Pydantic 2.12.5；未安装包。每轮环境/真实导入位置由命令记录和最终审计保留。只改获准 contracts、runtime storage/recovery、reconciler、三个 A02 接缝、persistent.py、新 A03 测试/演示/P2证据及本报告。根依赖/属性/政策、父入口、调度文件、source/geometry、其他 A 任务和 B 均未改。主目录只作为不可变输入来源。

## 实现与明确阻断

运行库与目标库为两个 SQLite 文件，事务独立。新初始化与打开已有状态分离；anchor、目录、ledger/store、DB/application/user version、不可变文件索引及事件链不符均失败关闭。接受事务一次预留全计划动作；实际效果须经过真实当前 PreparedAction 验证、持久 intent、许可发放、单次消费、DISPATCH_STARTED 和目标 fence，再独立读回并提交事实。

当前 observer 按原生对象身份、不可变摘要和独立目标观察验证准备能力，序列化值不能重建派发资格。书级 gate 是实际当前线程持有的受控同机锁；owner lease10秒、每2秒续租，接管须前 owner 进程已退出且租约到期。当前账本扫描全部同书 run/scope，旧无 intent UNKNOWN 为 LEGACY_UNRECORDED，不能通过归档/转换解除。

reconcile 只读独立目标，不调用 dispatch。每 intent/call 最多3次、单读2秒、intent8秒、整调用60秒；attempt 先登记，失败资源保留，同 call_id 重启不重置次数或期限，按最早 monotonic 截止退出。SQLite busy1秒、gate/屏障5秒。只回收自己创建的读取进程和续租线程；不终止其他服务。

正常完整事实生成不可变 receipt，新 POST_APPLY/BatchReport 通过精确当前解决链头计算有效状态；原 UNKNOWN 和旧报告不改。部分计划仅输出完整动作 progress。框一致不会验证最终内容或人工提交，仍为 PENDING/NOT_SUBMITTED。

以下项没有降级为通过：

1. **未尝试事实仍阻断**：R2 前缀 Schema 固定从1开始、zero genesis、同计划九类事件、design_only=true，不能表示当前真实书全局 journal 中 owner/control/其他计划和 reconciliation 事件。实际 PLAN_ACCEPTED 在领取后为3。专用入口返回 EVENT_PREFIX_CONTRACT_GAP，没有重编号、删事件或伪造 intent。独立 P2 profile 的最小补充提案及静态见证见 [实现说明](../a03-runtime-recovery.md) 和 [prefix-contract-gap](../evidence/A03/execution/P2/prefix-contract-gap/)。尚未取得补充批准；V04 两个功能场景保持失败。
2. **报告可表示性**：原结果没有 receipt 而随后才补完整 receipt、或多恢复头绑定不同 snapshot 时，冻结 POST 单一精确引用约束无法表示。输出 REPORT_CONTRACT_GAP 诊断；不修改旧解决结果、不伪造新 POST/Batch、不解除书级暂停。
3. **漂移 hold 的正向解除未测**：终局后的新漂移追加 TARGET_DRIFT_HOLD，效果许可阻断；清除入口要求真正新快照、新 PRE/TARGET/候选计划和当前事务 CAS。现有 CLI 没有新 PRE 生产者，保留旧 PRE，因此只能验证拒绝路径。没有通过改 ID/时间复制 PRE 冒充实际新检查。合法外部新 PRE 的正向清除、清除前第二次变化未证明；当前 hold 实现固定单 registration，多 registration 明确拒绝 REGISTRATION_BINDING_MISMATCH。
4. **未入图谱/未知分母的运行准入有限制**：旧 exceptions 样例缺未入图谱题的独立页枚举，转换被 CONVERSION_INPUT_UNSUPPORTED 拒绝。原字节归档诊断保留范围、EXCEPTION/SKIPPED 和未知/零分母；这不等于该输入已获得运行或 Batch 资格。
5. **早期失败的部分原件缺失**：质量首轮测试框架 TemporaryDirectory 自动清理动态 normal/partial 数据；早期 hold 两个 Temp 场景也未找到总体 unittest stdout/stderr，只保留现存子进程原件及可恢复工具记录。保留可恢复日志和其余原件，明确缺失，未重建冒充。此项不符合完整失败现场保全目标，需在验收中保留为证据限制。[质量归档索引](../evidence/A03/execution/P2/quality-agent-development/index.json) 和 [hold 汇总](../evidence/A03/execution/P2/hold-agent-development/hold-check-summary.json) 区分原件、副本及来源路径；SQLite副本仅作取证，不冒充可换目录打开的原状态。

## 作者实测与复现

以下全部为 SYNTHETIC/SIMULATED。每轮新目录，保留原失败；旧 P1/C01/A02 样例和既有执行/验收失败字节未改。完整源码冻结后的结果另列；早期检查不冒充冻结版本的独立验收。

在该工作目录运行：

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -B examples/a03/P2/run.py --scenario normal --output <全新目录1>
python -B examples/a03/P2/run.py --scenario effect-crash --output <全新目录2>
python -B examples/a03/P2/run.py --scenario absent --output <全新目录3>
$env:A03_TEST_EVIDENCE_ROOT = '<全新过程证据目录>'
python -B -m unittest tests.test_a03_process -v
```

独立目标 probe、每个请求/argv/cwd/PID、stdout/stderr、退出码、实际效果日志、不可变产物和 process-release.json 均在各场景目录。故障 marker 只证明控制流到达；实际效果数来自新进程直接打开目标库。owner 竞争用双方到达屏障，busy 用独立进程真正持有排他事务。Windows Git 长路径仅对命令使用 `git -c core.longpaths=true`，未改全局设置。

早期检查：contracts-check-04 为164项通过；runtime-authority-check-agent-01 为9项通过/27子进程释放，agent-02 为2项通过/6子进程释放；quality-check-01 为7项通过。首次功能 functional-01 有29场景21通过8失败；functional-02 有30场景23通过7失败。这些目录完整保留。functional-02 的4个失败是旧计划拒绝错误码顺序与新 freshness 门不一致，另1个为重复身份读回错误投影为合法快照，另2个为前缀阻断；后续修复和冻结复跑不改写它们。

固定 `12ecced` 的 functional-03 实际执行15个 unittest 方法、30场景：27通过、3失败，退出1，545.719秒。失败为 V04 两个前缀阻断，以及 V03 新计划过程中 project_plan 写事务与续租争抢导致的真实 SQLite busy；后者保留2个已完成效果并退出，没有重发。该版本完整权限专项另跑11/11通过、退出0，证据实际目录为 runtime-authority-check-cb072a8603b1，见 [索引](../evidence/A03/execution/P2/authority-check-final-01/result-index.json)。

最终 `fa645ac` 针对性复跑三条：normal 退出0/30.859秒，effect-crash 退出0/21.250秒，absent-replan 退出0/61.704秒。最后数值是包含多个独立命令的整场景时间，不是单次60秒恢复调用。各场景实际回执、独立效果计数、新快照及不可变原历史由其 scenario-result/command/target probe 保留。完整上一轮仍为27/30，不能把这三条新版本结果拼成新的整轮28/30或全套通过；最终提交没有再全套重跑。统一结果索引见 [check-summary-final](../evidence/A03/execution/P2/check-summary-final.json)。

早期普通 smoke 依次记录 SQL 占位、旧初始快照、方法缩进、证据ID、未尝试状态、A02历史闭包及配置版本读取错误；修复后的新目录独立保存。AFTER_RECEIPT_COMMIT 曾错误放在单步 progress 后；旧场景不计真实 receipt 边界，已修到完整 receipt/index/intent.receipt 持久提交后，并独立核对原始索引和摘要。CONFLICT 作为比较分类保留实际读回/原因；ActionResult 的 UNKNOWN 按冻结格式写 INDETERMINATE，不放宽 Schema。

hold-check-01 为3项中2通过/1失败（旧20秒外层超时），hold-check-02 为2通过/1错误（测试把 string directory 当dict），hold-check-03 仅补跑该项1/1通过，不拼接成单轮3/3。03实际新计划执行39.594秒，终局后合法APPLIED不误hold，追加合法新目录的业务漂移建立hold且效果仍3；02保留旧PRE、错hold、旧观察/代次与跨scope未决拒绝。早期 g4879 夹具 target key 不同的失败不计跨scope通过，修正后的真实 key 另有原件。[重复身份 focused](../evidence/A03/execution/P2/duplicate-check-02/command.json) 退出0；此前同类失败完整保留。

外层进程驱动默认65秒用于包住内部恢复调用60秒及回收；不是放宽单读2秒、intent8秒、恢复60秒、闸/屏障5秒。内部期限断言继续检查实际 elapsed、失败资源、尝试持久额度与同call重启；未知/损坏状态不通过增加时间来解锁。纯合同恢复链的质量投影使用新合成 fixture，并非实际runtime恢复报告正例；其动态 helper 清理后仅有日志/可复现源码，不宣称原动态字节完整留存。两个 REPORT_CONTRACT_GAP 组合目前是静态分支与合同可表示性推导，尚无实际输出场景。

最后复核提出 native authorization 的 caller-visible used 字段可被复原的问题。专项字段重置复现被自动安全审查以可能的网络安全风险拒绝，未执行且未重试，未声称取得复现结果。已采用保守防护，在成功验证时立即从私有原生身份登记删除该对象，正常/崩溃/新计划回归通过；该特定对抗用例仍未实测。[审查记录](../evidence/A03/execution/P2/authorization-review-block.json) 区分未执行脚本与实际测试。原有持久单次permit仍独立阻止重复派发；不把验证器风险说成已证实双效果。

## V01–V10 逐项状态

下表为作者分项结果，提交适用范围以各原命令为准，不能合并成同一版本的全套通过。

| 条件 | 实际结果 | 证据及限制 |
|---|---|---|
| V01 | 通过 | functional-03 normal；最终 normal-final-01 再通过，多动作、重开、旧动作拒绝 |
| V02 | 通过已测窗口 | functional-03 六个真实退出窗口及完整receipt索引；最终 effect-crash-final-01 再通过，恢复无效果重发 |
| V03 | 修复后针对性通过 | 完整03的 ABSENT重规划写锁失败原样保留；最终 absent-replan-final-01 通过，其余部分/重复/截断/矛盾/失败读回在03保持暂停 |
| V04 | 失败/合同阻断 | sufficient 与 truncated 均 EVENT_PREFIX_CONTRACT_GAP，没有专用完整未尝试ABSENT功能 |
| V05 | 已测通过 | functional-03 当前库同书跨scope两未决只解一项、另书legacy UNKNOWN不暂停 |
| V06 | 已测通过/有限制 | functional-03 双进程屏障和旧代次；权限专项11通过。字段重置专项被审查拒绝，不能计通过 |
| V07 | 部分通过 | 公共引用/版本/全合成门及 hold 检测/拒绝有证据；正向hold清除与第二次漂移清除未测 |
| V08 | 部分通过 | DB/资源损坏缺失、未知meta/application/user版本、换目录、真实busy通过；无schema迁移实现/迁移中断验证 |
| V09 | 已测通过/边界保留 | 原档案、显式合成转换、无intent UNKNOWN及深层ORIGINAL/OBSERVED拒绝；真实S01不因此通过 |
| V10 | 部分通过 | functional-03 实际2秒读超时、3次、同call重启限额、max4拒绝通过；质量7项含unknown/zero/异常跳过归档诊断，未入图谱运行准入和报告组合未闭合 |

## R01–R18 作者覆盖及未闭合层

| 标准 | 作者验证与限制 |
|---|---|
| R01 | 白名单、基线9710文件、导入及七Schema原字节审计；早期质量动态失败原件缺失保留限制 |
| R02 | 严格合同/递归资源声明/身份/摘要，加真实 runtime native capability 拒绝；局部 JSON 不证明全书完整 |
| R03 | 六个真实独立进程退出窗口；真实 receipt 以新修正场景及 SQLite 索引为准 |
| R04 | runtime/target 独立库及新进程目标 probe；不宣称断电耐久 |
| R05 | MATCH/ABSENT/部分/矛盾/截断/重复/失败读回；非充分证据保持暂停 |
| R06 | 唯一链头/历史前缀/叉环/终局后继/旧报告及新资格合同反例；未覆盖所有可能交错 |
| R07 | 当前库同书跨scope legacy 与本地 intent 两未决，只解一项不清另一项 |
| R08 | 旧代次/伪上下文/重放/换空库/原生对象复制及任意 binding 拒绝 |
| R09 | 实际两进程屏障 owner fencing、伪held拒绝、2秒真实续租；限受控同机目标 |
| R10 | 另书 legacy UNKNOWN 不暂停本书，旧 A02 R1 隔离回归保留 |
| R11 | 混合 APPLIED/UNKNOWN/NOT_ATTEMPTED progress；完整未尝试 ABSENT 受前缀合同阻断 |
| R12 | ABSENT 后旧计划拒绝；实际新观察/TARGET/新计划再执行；只换ID旧快照合同拒绝 |
| R13 | 漂移检测、旧PRE/错hold/旧观察/旧代次/跨scope未决拒绝；正向解除未实测 |
| R14 | DB/资源缺失损坏、未知metadata/application/user version、换目录及真实busy；无迁移实现/迁移中断正例 |
| R15 | 新旧归档/显式合成转换；旧无intent UNKNOWN 不能补intent解除 |
| R16 | ORIGINAL/OBSERVED 深层准入拒绝；S01真实完整性保持未解决 |
| R17 | 正常实际receipt报告与合成合同链投影；原UNKNOWN/旧报告保留断言。无receipt后补及多snapshot仅静态诊断分支，未实测 |
| R18 | PENDING/NOT_SUBMITTED、异常/跳过/未入图谱与unknown/zero归档分母诊断、3次与期限；不把归档当运行 |

## 清单、释放与权限边界

统一 [manifest](../evidence/A03/execution/P2/manifest.json) 覆盖本次实际必要输入、失败、日志、DB/资源、演示、矩阵、报告及原始开发证据；只排除清单自身和可再生字节码，嵌套输入manifest仍包含，源代码由确切 Git 提交绑定。被忽略的 *.log 显式入交付，原件缺失不以清单包装为齐备。最终审计核对基线、白名单、真实导入、七Schema和自有进程释放，不清理他人服务。释放脚本前两次遇CIM七位小数及Z时区与Python3.9解析差异，未产生结果，错误摘录保留并修复解析后再查，不计运行时失败。

[最终释放记录](../evidence/A03/execution/P2/process-release-final.json) 核对1028份进程completion、144份释放记录，记录中的active/remaining均0；当前匹配工作目录或记录生命周期内后代的Python进程为0，没有发送终止信号。早期控制器被强制终止时，不能事后把未记录读取子进程称为已join；本次另查当前存活后代为0，保留这一证据边界。

[最终审计](../evidence/A03/execution/P2/audit-final.json) 对9710个基线文件逐字节核对，只有4个获准既有源码文件变化，未发现越界改动；旧样例/报告/失败文件不变。七份Schema均等于冻结R2原字节。真实imports均来自本worktree；Python/SQLite/Pydantic版本与上述一致。[审计命令](../evidence/A03/execution/P2/final-audit-command/command.json) 退出0。

复核命令为 `python -B docs/evidence/A03/execution/P2/audit_delivery.py verify` 和 `python -B docs/evidence/A03/execution/P2/verify_git_blobs.py`；第二条比较原始Git blob，不依赖checkout换行过滤。源码/文档差异检查仅命令级采用 `git -c core.longpaths=true -c core.whitespace=trailing-space,space-before-tab,cr-at-eol diff --check <base> HEAD -- src tests examples docs/a03-runtime-recovery.md docs/tasks/A03-execution-report.md`，保留已冻结CRLF Schema，不格式化原字节取证日志、不修改全局配置。清单自身不自签，最终交付提交由回复给出。

本轮被测系统网络/浏览器/平台/OCR/模型/收费API调用均0；没有访问凭据或 profile、没有 A05题22重放、没有真实书籍或书级提交、没有推送/合并/向B发消息。2026-10-17 主调度有界原对话续接保持原范围；最终停在 REVIEW，等待主调度决定补充合同和后续独立验收，不修改其调度状态。
