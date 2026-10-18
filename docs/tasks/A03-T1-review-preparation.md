# A03-T1 独立验收准备

2026-10-18（Asia/Shanghai）。状态：**WAITING_FOR_FROZEN_T1_DELIVERY**。本轮仅阅读约定和冻结旧失败、核对必要摘要并编写本文；业务调用、SQLite 查询、夹具和六场景复验全部 **NOT_RUN**，不作 ACCEPTED/REWORK/BLOCKED 新结论。A03 整体仍 REWORK，I01 未释放。

## 固定依据与启动条件

- workflow：`f7084b2e8f2e9a1fcf758f9cba56ec9c9fb1f304`；已用 `git -c core.longpaths=true show <commit>:<path>` 阅读其中的[拆分约定](A03-redispatch-2026-10-18.md)、[T1任务单](A03-T1-capture-and-inconclusive.md)、[原R12五例](A03-P2-R12-inconclusive-readback-validation.md)、[R12-R2任务](A03-P2-R12-R2-issue-ownership-repair.md)及[原验收交接](A03-original-reviewer-handoff-2026-10-18.md)。新拆分规则优先，不唤醒旧对话。
- 共同产品基线：`1330047dd29890dea0e433ff01b991f615bf78f4`；原最终交接：`6b61ac9d623e76cbe6311f64d012fd04e2e03c21`。已从最终交接读取执行交接、R12-R2报告及下列必要证据；不合并浮动主分支。
- 已读主目录 `AGENTS.md`、`docs/architecture.md`、`docs/contracts-v1.md`、`docs/coordination.md`、`docs/development-plan.md`；历史状态按各自确切版本理解。
- **尚未收到本轮 T1 的确切代码/证据 target、完整 manifest 及自有进程/keeper/owner 释放证明。** 三者由调度交齐后，才建立独立副本、核对冻结范围并正式复验；不审浮动 T1 代码、不轮询作者。

## 冻结旧失败与不可补齐项

R12-R1 的 UNKNOWN fact/目标部分效果已提交，但正式 receipt 因问题归属 `MISSING_REFERENCE` 未形成；不能把仍暂停当合法 UNKNOWN 建立。R12-R2 中 C12项、L1、U1 仅作者检查通过，原验收者未复核 R12-R2。

旧 U2 的 `commit_action_result` 已返回；`unknown-established` 与随后的 `first-failure` 均在旧 `support.py:88` 因 `active SQLite sidecar at raw capture` 断言失败。未观察到产品异常栈，不能直接归为产品失败；两阶段 capture/双库原件及瞬时 journal 原字节、摘要未保存，不能用释放后库重建。U2 duplicate 恢复、U3–U5、H1 均 NOT_RUN。旧20份阶段库及 R11 作者 F2/F3 中间原件缺口保持；不重开、续跑或补造历史。

本轮静态核对旧提交 raw Git 字节，以下四项与交接摘要一致；报告、失败摘要、释放证明及 U2 stderr 也与旧 manifest 对应成员一致。仅核对必要成员，未重验649项全集或查询数据库。

| 旧文件（均属于上述最终交接提交） | SHA256 |
| --- | --- |
| `docs/tasks/A03-P2-R12-R2-issue-ownership-report.md` | `538017a11e11a21f214104668a796b8fcb0c629ff3b55391a3924819f5dc882a` |
| `docs/evidence/A03/execution/P2-R12-R2-issue-ownership/manifest.json` | `8432178da68c8c9823874a0e0a18eb1244d7f7acd5b49bb980b34541c3b68833` |
| 同目录 `failure-summary.json` | `17255916b291e79686e7caf7088e1b39eaf367330f1979e9b49a7555d0979e19` |
| 同目录 `sealing/process-release-proof.json` | `d5da9b5c5450db36358ff3837c519b2e972a8d085bff2fcf909761762637cb12` |

释放文件记载30个自有 Popen 已回收且均 alive=false；这只是冻结记录核对，不是当前PID扫描，也不替代 T1 自己的释放证明。

## 正式复验的有界范围（本轮未执行）

先检查无业务效果的最小 SQLite 夹具及可供 T2 导入的取证 API：所有自有写者和保活线程须有可解释的同步确认、事务结束/连接关闭及生命周期证据，不能靠 sleep、删除 journal/WAL/SHM 或在活动写入时 immutable 查询通过。逐库静止原字节复制须可核对源/副本摘要；其他复制技术明确其证据含义，业务阶段仍保留静止原件，不宣称跨库原子快照。核对产品、src/pins/schema 和旧驱动/证据未改，没有复制 runtime 规则、改预期或放宽时限。

| 场景 | 固定建立与恢复 | 核对重点 |
| --- | --- | --- |
| L1 | 唯一 legacy 单动作 partial/完整读回对照 | 原合法诊断 POST/HOLD、UNKNOWN receipt/progress、暂停及不可重放保留 |
| U1 | native partial/完整读回建立 UNKNOWN；新进程完整读回对账 | 不判 MATCH/ABSENT，不补片，保留合法未决/暂停及原历史 |
| U2 | 正常 applied + unavailable 建立 UNKNOWN；新进程 duplicate 对账 | 真实重复身份读回，不使目标造重复或解除暂停 |
| U3 | 同 U2 建立；contradictory 对账 | 矛盾证据保持未决/暂停 |
| U4 | 同 U2 建立；truncated 对账 | 原始读回与完整性标记相符，保持未决/暂停 |
| U5 | 同 U2 建立；unavailable 对账 | 保留实际不可用记录，不补造 snapshot 或已解决结果 |

各用新目录、新数据库和固定输入，不复用作者数据库；每场景一次 dispatch，U1–U5 正常释放后由新进程恰好一次 `reconcile(max_attempts=1)`。恢复新增效果为0，调用/消费事实及原 receipt/progress/history 保留；native 场景 `native_report_reads=0`，不发布 POST/Batch。业务子进程45秒、父90秒，观察2秒、屏障5秒、lease10秒保持。合法未决结果须符合冻结前登记的实际 API/错误语义，不能以最终仍暂停掩盖异常。

核对建立前、UNKNOWN建立后、释放后、恢复前后适用阶段的 runtime/target 原件、capture、真实正式产物/Resource/事件、效果和精确身份绑定；同字节可显式共用原件引用，不能省略逻辑阶段。SQL仅查询自有 immutable 副本。真实 argv/cwd/导入/执行字节摘要、raw流、exit/timeout/wait及owner释放全部留存，区分 raw Git 与 checkout 字节。

首错保留并停止后继；仅本任务新增驱动错误允许一次有界修正及失败场景/未运行后继复验，形成新候选和新目录，第二次失败即停止交付。产品语义缺陷交精确反例给调度，不自行修产品。不跑 C、H1、R9–R11或原全矩阵。

## 写入与结束边界

本轮仅新增本文，由调度保存；不操作主目录 Git 索引/提交或 `coordination-state.json`，不写执行者 worktree。后续自有隔离副本及运行输出仅在 `D:/1800/.local/A03-T1-independent-review`，必要证据/报告只写 `docs/evidence/A03/T1/review/` 和 `docs/tasks/A03-T1-review-report.md`。全部 Git（含子进程）显式 `-c core.longpaths=true`，Python 使用 `-X utf8`。

全部离线；不使用网络、平台、browser/profile/凭据、安装、模型/OCR、推送、书级提交或A05题22，不联系B或旧A03对话，不委派。field reset 保持 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`。收到固定交付前在此结束等待；未来全部满足时仅建议 T1 有限 ACCEPTED，工具经调度接受后才供 T2 消费，不外推整体A03、I01、集成或B确认。
