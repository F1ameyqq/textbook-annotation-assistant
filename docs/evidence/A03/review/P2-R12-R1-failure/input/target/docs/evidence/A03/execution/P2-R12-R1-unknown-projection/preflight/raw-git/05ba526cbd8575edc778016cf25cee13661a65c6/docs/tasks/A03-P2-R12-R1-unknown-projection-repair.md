# A03 P2-R12-R1：UNKNOWN 投影修复及原五例验证

2026-10-18（Asia/Shanghai）。原执行对话 `01a145aa-2fea-7942-97f9-ad260acf4e30` 续接，原独立验收对话等待冻结交付。A03 整体仍为 REWORK，I01 未释放。保留用户当前 model/thinking，不委派。

## 已核实的返工原因与本轮决定

唯一 base 为 `394fe51f5ed14c5ed312073a20faac0f5cbb9990`，产品内容与 `cc5966dc58c62017a27266c40ca0cedc5c68485c` 相同。R12 在准备阶段停止，U1–U5 全部未运行。此前四个 crash cut 的有限通过保留。

[独立静态复核](A03-P2-R12-prerequisite-review-report.md)（SHA-256 `33c224427aa86bce6d4966aa8eafd7fae51e5bf2823c09a56745d1fc6cdaff95`）与[调度独立核对](../evidence/coordinator/heartbeat-20261018-0845/r12-static-corroboration.json)共同确认：`RuntimeStore.commit_action_result` 调用投影；当所有动作已有 fact、存在 UNKNOWN、尚无相应 receipt 时，继承的投影生成旧式 POST_APPLY。`NativeRuntimeStore._append` 的 native 校验要求不同字段，存在缺 6 项、多 4 项的字面冲突。调度核对164项manifest、109份raw Git来源、7个登记子进程退出，并独立按类限定AST计算字段差异。实际异常码和事务副作用尚未动态观察。

调度结论仅为 `STATIC_BLOCKER_CONFIRMED`，不是功能 ACCEPTED。现授权一次有界实现修复：native 投影保留真实 UNKNOWN、receipt 和 progress；正式报告仍由独立观察驱动的发布入口负责。此范围符合既有 native 合同，不改变公共字段或 B 的确认状态。

## 基线、目录与可改范围

- 工作目录：`C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800`；分支 `codex/a03-runtime-recovery`。不合并移动的调度分支；workflow 以派发消息的确切提交为准。
- 派发键：`A03:execution:P2-R12-R1-unknown-projection:394fe51f5ed14c5ed312073a20faac0f5cbb9990`。
- 产品仅允许改 `src/annotation/runtime/storage/__init__.py`、`src/annotation/runtime/storage/native.py`。
- 调度作为公共 pin 整合负责人，本轮明确指定原执行者同步候选中的 `src/annotation/contracts/a03_native/data/profile.json` 对应这两个实现摘要，以及 `data/adoption.json` 的 `profile_sha256`。其他字段、schema pins、其他 implementation pins 必须不变。此授权仅是候选修复，实际主目录集成仍由调度验收后完成。
- 新增测试仅 `tests/test_a03_p2_r12_r1_unknown_projection.py`，新样例/驱动仅 `examples/a03/P2-R12-R1-unknown-projection/`，新证据仅 `docs/evidence/A03/execution/P2-R12-R1-unknown-projection/`，报告为 `docs/tasks/A03-P2-R12-R1-unknown-projection-report.md`。
- 旧测试、R12首次阻断包及全部历史证据保持原字节；schema、API、oracle、producer、verifier、native_quality 发布模块、依赖及调度 state 均只读。若发现修复必须超出这4个既有文件，提交确切缺口后停止，不顺手扩展。

## 修复要求

在投影内部提取窄的受保护报告策略/钩子，默认保持 legacy 旧行为，native 覆盖为不在投影内生成诊断 POST。函数命名和小范围实现细节由执行者选择；不要复制整个投影方法制造双份状态机。

必须保留原 fact/intent/permit/attempt、UNKNOWN 结果、未决暂停、receipt 的 unresolved issue 绑定、progress 及事件/Resource历史。只取消 native 对旧式诊断 POST 的隐式构造，不能删除 UNKNOWN issue、伪造新观察、把 UNKNOWN 改成功、清 pending/hold、吞验证异常或放宽校验。完整 receipt/progress 仍须正常通过 native 闭包校验。

`publish_native_quality` 及其独立新鲜观察、action/fact/intent/resolution 绑定和 durable report-read 限额保持原代码。投影不得消耗报告读回次数，也不得自动生成 POST/Batch；显式发布的既有职责保留。本轮不额外运行显式发布场景，以源码差异和不变摘要确认其未改；不得将这种静态确认写成新动态发布验收。

## 一次有界验证

先完成实现与必要驱动的静态准备，核对真实API、UTF-8、compile、输入闭包、pin摘要和原任务预期；提交代码/驱动/输入形成确切候选代码版本，再启动功能。不得边跑边改代码或预期；功能首错、超时或运行证据缺失即停后续组、保留现场、交 REWORK，不自行二次修复重跑。

顺序为一个受影响的 legacy 对照 L1，再原 U1→U5，各一次。总计最多6个功能场景，不跑旧全套、旧成功组、N7 或 field reset。L1 为本次基类改动所需的唯一新增兼容性对照：使用全新固定单动作 synthetic legacy 输入及正常持久化/执行流程形成真正 UNKNOWN fact，证明旧分支仍产生原合法诊断 POST/receipt/progress、保留暂停和不可重放。不得靠直接塞数据库/伪造 fact、AST裁剪执行或仅测试钩子返回值代替。若原 legacy 入口无法构建这个有界对照，报告实际前置限制，不能调用多场景旧套件填补。

U1–U5 完全继承[原 R12 任务](A03-P2-R12-inconclusive-readback-validation.md)的固定输入语言、公开故障接缝、建立/释放/跨进程恢复顺序及验收准则；原准备阶段停止意味着这些是首次功能运行。本任务只放开上述产品修复和新目录，不改变五例业务标准：

| 场景 | 正式 UNKNOWN 的首次建立 | 唯一恢复读回 |
| --- | --- | --- |
| U1 | partial效果，正常完整执行读回 | 正常完整读回，必须仍为未决冲突，不补写缺片 |
| U2 | applied效果，unavailable执行读回 | duplicate，须有实际重复身份证据，不能用空表降级冒充 |
| U3 | 同U2，各自全新目录 | contradictory |
| U4 | 同U2，各自全新目录 | truncated |
| U5 | 同U2，各自全新目录 | unavailable，保留真实null/不可用记录 |

每例一次dispatch；原owner/keeper正常停止且有退出/释放证明后，另一个独立进程只做一次 `max_attempts=1` reconcile。每例正式 UNKNOWN 建立必须产生合法 receipt/progress，投影前后没有伪造POST/Batch，`native_report_reads` 不被隐式消费；重开后保持原记录。恢复期间目标新增效果为0，UNKNOWN/暂停/待核对义务保留；动作、读回、Resource和事件精确绑定及内容/完整性符合原标准。不能把非预期异常仅因“最终仍暂停”记为通过。

父watchdog每例90秒、业务子进程45秒，既有观察2秒、屏障5秒、lease10秒不变。实际启动前登记源码/输入摘要、argv/cwd、时限和分支预期；保留所有自有Popen的start/completion、真实原始stdout/stderr和导入路径。首次失败后只允许收集现场与正常释放，不追加功能试探或扩大预算。

按原任务在现场保存每例建立前、UNKNOWN建立后/释放后、reconcile前、reconcile后的 runtime/target 二进制原件和capture记录；字节相同可明确指向同一原件。L1保留建立前后所需原件。逐库复制说明writer状态，不宣称跨库原子快照；只读SQL核对用自有immutable副本，不修改原始库。正式引用JSON/Resource和历史链齐全，不用最终库追构中间证据。归档后最多一次新元数据静态纠正，保留首错，不调产品；再次归档失败交REWORK。

## 交付及验收边界

交付 clean exact commit，区分候选代码提交与最终证据提交；给出4个既有文件diff、pin变更表、可搬运复现命令、L1/U1–U5实际或未运行状态、所有现场原件、manifest和自有进程释放证明。manifest覆盖4个改动文件及全部新交付与报告，仅排除自身；历史大包以提交/摘要引用，不复制全集。

执行者交 REVIEW。调度核对冻结产物后向原独立验收对话派发同一固定候选、L1和五例各一次的复验。通过仅关闭本处投影缺陷、有限legacy对照及原V03/R05五项，不能外推其他A03验收条目、本地集成、B版本映射或I01完成。

零平台/浏览器/profile/凭据、网络、安装、OCR、付费模型、B联系、推送、A05题22或书级送交。field reset 维持 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`，不运行、变体、委派或建议重测。
