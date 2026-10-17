# A03 P2 独立复验报告

日期：2026-10-17（Asia/Shanghai）。结论：**REWORK**。本次续派要求为 `xhigh`；没有派发其他智能体或其他对话。

必需的无 intent 未尝试事实正向路径在冻结实现中仍直接失败关闭。独立建立真实已接受/永久预留、intent前退出的现场，专用入口实际返回 `EVENT_PREFIX_CONTRACT_GAP`（退出2），没有两次新读和事实提交。正常三动作、持久目标/报告及旧计划拒绝的有限对照通过，不能抵消这个功能缺口。**A03 功能不接受、不集成，I01 不释放。**

## 1. 输入、来源和本轮边界

| 项目 | 精确值 |
|---|---|
| 正式复验 workflow | `2ef3bfda20476dff3bdd23912d5bf2d1e3eb5ce1` |
| 被验交付 | `c30526958e313141bf64152627591b0907b04aa8` |
| 被验最终实现 | `fa645ac8fd70688f3293edc5cfb1077fc7bd9daa` |
| 产品 base / 已接受 P1 最终版 | `940a5de33a24b1a3a9ded6e69ade1dd0609ed83a` |
| P1 设计提交 | `a250a76dc0b3f13b9dee3bcd2c3d7414032b9768` |
| 原 P2 workflow / A02 依赖 | `6b77c436742cf2826083b109d8ed86b85539cba6` / `ec1b4defbfa3ec0f181d291106fb53313983e493` |
| 执行报告 SHA256 | `acde484108252c1437d25b96123d5eb8c22cba6f23aac34c53420700bfab27d7` |
| 作者清单 SHA256 | `d305dd02378811d99d49e882ede04a72ff27ec0697b9c09a6e94057aa8a8e703` |
| 接受 API SHA256 | `e2b0865fc1a25206181f3094155b059a6d34eb851afc750e813f0c2e89960f85` |

从workflow原Git读取 [正式handoff](../evidence/A03/review/P2/input/documents/2ef3bfda20476dff3bdd23912d5bf2d1e3eb5ce1/docs/tasks/A03-P2-review-handoff.md) 与 [调度预检](../evidence/A03/review/P2/input/documents/2ef3bfda20476dff3bdd23912d5bf2d1e3eb5ce1/docs/evidence/coordinator/heartbeat-20261017-0516/A03-delivery-preflight.json)，读取冻结 [执行报告](../evidence/A03/review/P2/input/documents/c30526958e313141bf64152627591b0907b04aa8/docs/tasks/A03-execution-report.md)。执行完成/释放及工作树clean是已交付门的来源；本次功能输入一律来自确切Git，不借作者活动环境或后续主分支。

[交付字节索引](../evidence/A03/review/P2/delivery-byte-index.json) 独立复算作者清单17429项的raw Git blob/长度/SHA256，未复制其228MB历史树。[隔离输入索引](../evidence/A03/review/P2/input-index.json)只导出73份必要源码、合成normal输入、P2助手和文档；隔离源码与fa645ac原blob一致。基线9710个Git文件仅4个批准既有源码变更（contracts公共入口和3个A02接缝）；七份实现Schema逐字节等于接受R2 pins。没有把旧profile的重复版本字符串当作包选择依据。

隔离目录为 `D:/1800/docs/evidence/A03/review/P2/input/checkout/`，新运行库和目标均在本轮 `cases/`。真实导入见 [environment.json](../evidence/A03/review/P2/environment.json)：Python3.9.13、SQLite3.37.2、Pydantic2.12.5，九个相关模块均来自该隔离src；没有安装依赖。`PYTHONPATH`固定该src，`-B`及PYTHONDONTWRITEBYTECODE=1。没有改产品源码/合同/依赖/调度state。

## 2. 独立实测和最小阻断

### A03-P2-UNATTEMPTED-01：必需正向入口仍未实现

冻结 [storage源码](../evidence/A03/review/P2/input/checkout/src/annotation/runtime/storage/__init__.py)第1015–1018行为无条件 `fail(EVENT_PREFIX_CONTRACT_GAP, ..., 2)`。不是对某个不合法输入的选择性拒绝；该入口尚未执行当前账本/前缀验证、两新读、比较或原子fact/event/index提交。

独立案例 [no-intent-absence结果](../evidence/A03/review/P2/cases/no-intent-absence/independent-result.json) 使用原始normal全合成输入的显式新转换，通过公开CLI初始化、当前真实快照和两阶段规划。真实子进程在BEFORE_INTENT_COMMIT退出90；新stdlib-only进程以SQLite `mode=ro`检查目标和完整账本。观察到原子接受事件seq3（前两条为OWNER_CLAIM_RESERVED/OWNER_ACTIVE），三动作永久预留，无intent、permit、fact或目标效果。选择第一动作，无未知前序相关性问题；当前CLI取得ACTIVE owner并将原计划标INTERRUPTED后调用专用入口。

| 独立观察 | 实际值 |
|---|---|
| 专用调用 | [05-dedicated-readonly](../evidence/A03/review/P2/cases/no-intent-absence/commands/05-dedicated-readonly/completion.json)：退出2，EVENT_PREFIX_CONTRACT_GAP |
| 独立目标效果 | 调用前0，调用后0；questions/frames/业务映射投影摘要相同 |
| 目标观察序列 | 前2，后2；专用入口实际新读0 |
| 未尝试事实事件 | 0；各action.fact仍null，没有补造intent/义务/permit |
| 账本 | [前查询](../evidence/A03/review/P2/cases/no-intent-absence/commands/04-independent-before/stdout.log) / [后查询](../evidence/A03/review/P2/cases/no-intent-absence/commands/06-independent-after/stdout.log)保留所有表和完整事件 |

这确认了所需专用正向路径不可用；不把“安全保持拒绝”计为功能完成。没有另外重跑APPLIED/UNKNOWN/C混合或截断场景；其作者失败与本次更小阻断分开，均不能获得V04/R11通过。

### 正常路径有限对照

[normal-control](../evidence/A03/review/P2/cases/normal-control/independent-result.json) 的公开run退出0（14.844s）；worker退出后新进程直接只读目标，实际3次mutated效果，完整receipt及Batch持久存在。再次提交旧计划退出2/REPLAY_FORBIDDEN，目标效果仍3，业务投影摘要不变。正常Batch的total_expected=3、state=CONTENT_PENDING、content_check_status=PENDING、submission_status=NOT_SUBMITTED；没有把框效果升级为内容完成或人工提交。

这是一个独立正常对照，不是V01–V10/R01–R18整套通过。本轮没有复跑作者完整unittest，也没有复跑效果后失响应或普通ABSENT演示。冻结作者完整轮属于12ecced版本27/30、退出1；fa645ac的normal/effect-crash/absent-replan三条针对性结果是另一版本，不能相加成最终全套通过。

## 3. 报告、hold、迁移和失败原件的独立判断

[静态定位及逻辑见证](../evidence/A03/review/P2/static-findings.json) 区分代码约束、逻辑推导和未运行的真实组合。

| 项目 | 本轮判断及限制 |
|---|---|
| A03-P2-REPORT-02（R17） | contracts/recovery.py 856–860要求单个POST的receipt等于每个头的original_receipt_ref、单snapshot等于每个头的observed_snapshot_ref。无原receipt的头(null)与后来完整receipt不能满足前者；两个不同snapshot的头不能同时满足后者。quality.py 175–181确有返回REPORT_CONTRACT_GAP的分支。本轮没有构造整个合法运行组合并调用该分支，不能称已实测，也不据代码存在就宣称诊断及暂停行为通过。正常Batch仅证明可表示分支。原历史不可修改以求通过 |
| A03-P2-HOLD-03（R13） | holds.py要求新实际snapshot、新post-hold PRE/TARGET/候选计划，并在最终事务前重新读取及CAS；这些是可定位防护。合法新PRE的来源/公开接纳、新PRE正向清hold、清除前再次目标变化均NOT_RUN。缺CLI PRE生产者不授权伪造PRE，也不能把旧PRE拒绝当作正向解除完成；不要求越界实现B模块 |
| A03-P2-MIGRATION-04（R14/R15） | D02/D03允许未知DB版本失败关闭，要求旧归档与显式新合成转换；不额外要求自动迁移任意未知数据库。正常初始合成转换已运行，但转换失败/中断保留、新旧原字节及迁移映射异常路径未独立实测。convert_synthetic_fixture有INCOMPLETE标记及范围缺页枚举拒绝，源码防护不替代中断证据；“未知DB拒绝”不能直接充当全部迁移要求通过 |
| A03-P2-EVIDENCE-05（R01/R14） | 冻结质量index明确first-quality-failure动态原件NOT_RETAINED，hold汇总明确两次原始总体stdout/stderr缺失。当前清单对现存文件的字节完整性不能补回这些原件。原件缺失为保全条件未满足；不重建冒充原件，不用后来通过重写过去失败。后续新的有界运行须完整保留，历史限制是否可被接受由调度明确决定 |

未知/零分母、异常/跳过/未入图谱的归档诊断不等于运行准入和完整Batch资格；本轮也未补跑这些项。S01真实来源完整性、Pillow依赖、B共同确认、真实平台/OCR/模型质量成本继续未解决。

## 4. V01–V10、R01–R18逐项结论

以下是本次独立复验状态，不能拿作者历史数量补足NOT_RUN。原文及来源逐项保存在 [review-matrix.json](../evidence/A03/review/P2/review-matrix.json)。PARTIAL仅表示表内有限证据，不是该标准接受。

| 编号 | 本次状态 | 实际证据或未运行范围 |
|---|---|---|
| V01 | PARTIAL_RUNTIME | 独立normal三动作/完整receipt与Batch、重开SQL和旧计划拒绝通过本场景；不是全部V01回归接受 |
| V02 | PARTIAL_RUNTIME | 真实BEFORE_INTENT_COMMIT进程退出90，独立目标0/无intent；其他五窗口及效果后崩溃未在本轮重跑 |
| V03 | NOT_RUN | 普通intent MATCH/ABSENT及部分/重复/矛盾/截断等本轮未测，作者历史分开引用 |
| V04 | FAIL | 最小合法无intent正向入口实际EVENT_PREFIX_CONTRACT_GAP/退出2/新读0/fact0；混合A/B/C完整场景未另跑 |
| V05 | NOT_RUN | 未独立运行同书跨scope/run及另书隔离 |
| V06 | NOT_RUN | 未跑两进程竞争/旧代次/新UNKNOWN；字段重置专项受既有审查拒绝，明确NOT_EXECUTED |
| V07 | PARTIAL_STATIC | 正常旧计划重放拒绝；引用和版本负例、新PRE/hold正向解除及二次变化未运行 |
| V08 | NOT_RUN | 未运行损坏/目录替换/迁移中断；只读确认未知格式拒绝及显式转换边界 |
| V09 | PARTIAL_RUNTIME | 正常旧合成输入显式转换已运行且原输入摘要不变；旧UNKNOWN和真实/OBSERVED拒绝未独立复跑 |
| V10 | PARTIAL_RUNTIME | 正常Batch total_expected=3、CONTENT_PENDING/PENDING/NOT_SUBMITTED；其他范围、次数和期限未测 |
| R01 | PARTIAL_FAIL | 17429 raw Git清单/73导出/七pins/导入环境和范围核对；早期失败原件缺失不符合完整保全条件 |
| R02 | PARTIAL_STATIC | 七Schema同R2原字节、正常公开入口；递归闭包负例未另跑，静态防护不算功能通过 |
| R03 | PARTIAL_RUNTIME | 只有intent前真实进程退出；其余断点未运行，不以作者日志替代 |
| R04 | PARTIAL_RUNTIME | 两个实际不同SQLite文件及新只读进程查询；正常3效果持久，未测效果后无receipt窗口 |
| R05 | NOT_RUN | 未独立运行四类比较及不充分读回；专用入口提前拒绝，未发生两读 |
| R06 | PARTIAL_STATIC | 报告链约束只读分析；未构造运行时分叉/终局后继/新UNKNOWN |
| R07 | NOT_RUN | 保留本场景完整账本查询，但没有跨scope构造，不足证明全书扫描 |
| R08 | PARTIAL_RUNTIME | 正常旧计划REPLAY_FORBIDDEN且业务效果不变；其他身份/旧owner/换库未测 |
| R09 | NOT_RUN | 没有竞争屏障或受控夺权实验；普通claim不等于并发验证 |
| R10 | NOT_RUN | 未独立复跑合法多书包及A02 R1跨书邻例 |
| R11 | FAIL | 专用未尝试事务为无条件stub；不可能据本交付形成所需两新读/ABSENT事实 |
| R12 | PARTIAL_RUNTIME | 正常旧计划重复拒绝；ABSENT后真正新快照/检查/规划继续路径未独立运行 |
| R13 | NOT_RUN | hold代码要求新PRE与最终再读/CAS；合法正向解除及第二变化无独立实际证据 |
| R14 | PARTIAL_STATIC | 转换INCOMPLETE和格式拒绝代码可定位，迁移/事务失败未测；旧缺失原件保持缺失 |
| R15 | PARTIAL_RUNTIME | 正常显式新合成转换通过；旧无intent UNKNOWN保全/转换失败及中断未独立跑 |
| R16 | PARTIAL_STATIC | 本轮仅全合成；来源深层拒绝仅读实现，真实来源和S01未通过 |
| R17 | PARTIAL_FAIL | 正常实际报告存在；两个恢复组合的单POST约束矛盾可定位，REPORT_CONTRACT_GAP运行分支未实际构造 |
| R18 | PARTIAL_RUNTIME | 正常总量3和内容/提交状态已读；未知/零题/异常跳过和3次/期限未独立复跑 |

## 5. 必须先明确的有界补充与再交付

不修改或批准合同。本次只提出可审阅的最小差异，后续仍由主调度定范围、唯一写入者实现并冻结：

1. 前缀：保全旧七Schema/API/profile原字节，在 `src/annotation/contracts/schemas/` 新增独立P2 runtime前缀Schema/profile，并由 `prefix_validation.py`、`recovery.py` 显式选型。候选format可为 `a03-runtime-event-prefix-1`。从真实PLAN_ACCEPTED全局序号及真实前驱到当前书头，保留期间owner/control/其他计划/reconciliation/import等事件，封闭逐类payload和identity；未调用判断仍绑定永久预约和完整当前账本/CAS。不得改号、删控制事件、投影后冒称完整前缀，或用布尔complete取得权力。具体事件全集/payload须再批准，本文不补实现。
2. 报告：在 `src/annotation/contracts/` 的新显式版本及 `runtime/recovery/quality.py` 明确“原receipt可缺、后来完整receipt”的事实关联，以及每action的独立snapshot/recovery头如何被一个完整报告消费。不能改旧resolution的original_receipt_ref、合并伪造观察或删头。若保留为不支持，须调度明确缩窄原要求，不能执行者自行豁免R17。
3. hold与迁移：提供合法新PRE生产/接纳的具体入口和输入来源、正向解除及第二变化的有界证据；明确批准版本支持哪些归档/显式转换及中断恢复，而不是擅自自动迁移未知DB。上述方法不能使用被拒字段重置专项。
4. 证据：保留本轮失败及原缺失声明；提交新的冻结实现/报告/清单/释放记录，逐项说明仍未运行，合同补充批准另可定位。不得把新通过记成旧失败原件已恢复。

这些是退回调度的提案/缺证条件，不向执行者/B发送消息，不安排其排期。本轮在明确阻断处结束，不为计数重复完整矩阵；正式再验须新续派。

## 6. 复现、工具失败保全与释放

本轮实际命令：`python -X utf8 -B docs/evidence/A03/review/P2/scripts/freeze.py`（字节导出）；`run_review.py`（正常对照后因review驱动释放检查退出1）；`finish_minimal.py`（原现场继续并冻结失败，wrapper退出0）。wrapper的0表示成功记录阻断，不是专用功能通过；实际专用CLI退出2。每条真实argv/cwd/PID/PYTHONPATH/超时/退出码及原始stdout/stderr在case的commands目录。

原驱动在stdlib SQL只读进程退出0后，立即看到Job活动计数1并断言失败，未进入专用调用。保留 [首版驱动](../evidence/A03/review/P2/scripts/run_review.attempt-01.py)、[工具失败](../evidence/A03/review/P2/review-run-failure.json) 和首次 [释放记录](../evidence/A03/review/P2/process-release.json)。随后 [owned_process.py](../evidence/A03/review/P2/scripts/owned_process.py)增加最多2s的后代释放等待，仅在原现场追加未执行的专用调用和后查询，没有重建状态或擦除失败。即时计数1原记录没有改为0。各命令属于自己的Windows Job Object，设置kill-on-close；首版退出也关闭该Job，后续命令最终活动计数为0。此处是取证驱动修正，不记为产品缺陷，也不推断未证实的计数时序根因。

```powershell
# 只读核验本轮完整归档，不运行产品、DB或被拒动作
python -B D:/1800/docs/evidence/A03/review/P2/scripts/verify_archive.py

# 如后续明确授权重新复现，须新case-id；本命令本轮未再跑
# 会新增独立合成状态，不能复用旧case；失败时脚本退出1
python -B D:/1800/docs/evidence/A03/review/P2/scripts/reproduce_minimal.py --case-id new-independent-absence-01
```

新复现会向新case目录写证据，应另作新轮归档，不将其写入已签清单后仍冒称原清单完全一致。新脚本复用本次实际使用的有界公开CLI流程及独立SQL取证；该便捷入口本身没有在本轮额外执行。

13个直接测试/取证/环境子进程均结束；Job后代按逐命令账户记录和关闭回收机制处理，未做全系统进程扫描、未终止其他进程。[第二阶段释放](../evidence/A03/review/P2/process-release-run02.json) 和 [环境释放](../evidence/A03/review/P2/process-release-environment.json) 保留真实记录。本轮两套runtime/target为独立SQLite文件；有限normal模拟目标实际3个业务效果，阻断案例0个，全部SYNTHETIC/SIMULATED。没有真实业务或线上效果。

## 7. 保全、清单和明确未执行项

旧审查/准备文件1524项的长度/SHA在开始记录并于结束核对，原P1/P1-R1失败、P1-R2设计接受及P2准备不改。所有本轮输入、脚本、案例库/不可变文件、完整账本/目标查询、原始日志、工具失败和报告列入 [统一清单](../evidence/A03/review/P2/sha256-manifest.json)，仅排除清单自身；Git忽略项明确列入，不把归档字节核验当功能接受。终检见 [final-verification.json](../evidence/A03/review/P2/final-verification.json)。

被测系统浏览器、网络、平台、凭据/profile、OCR、业务模型/收费API、真实书籍和书级提交均0；真实质量/成本未测。未运行浮动源码、未重放A05题22、未改产品/state/根配置、未提交/合并/集成/推送、未联系执行者/B/其他chat、未创建轮询或自动化。仅写本报告和本轮P2证据目录，审查自己的新合成现场独立保留。

作者 `authorization-review-block.json` 的字段重置专项已被自动安全审查以潜在网络安全风险拒绝，本轮严格保持 **NOT_EXECUTED**：未复跑、改写、变形重做或另派。只读确认最终源码成功验证后移除原生对象身份登记，并运行正常控制流程；这不证明该专项对抗行为已通过，也不把未执行专项升级成已证实双效果。本轮没有请求绕过该拒绝。

结论为 **REWORK**；本轮到此结束，等待主调度处理补充合同、缺证条件及下一次冻结续派。I01不释放。
