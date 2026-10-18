# A03 P2-R12 准备阶段阻断独立静态复核

2026-10-18（Asia/Shanghai）。结论：**阻断证据确认**。确认的是固定源码中的 native UNKNOWN fact 投影与 POST_APPLY schema 不兼容，以及准备期停止记录的来源和边界。**U1–U5 未执行、R12 功能未验收；whole A03 仍为 REWORK，I01 未放行。** 本轮没有产品导入/调用、SQL 连接、修复、合同采纳或调度登记。

## 固定身份与交付核对

- 目标：`394fe51f5ed14c5ed312073a20faac0f5cbb9990`；直接父提交及产品基线：`cc5966dc58c62017a27266c40ca0cedc5c68485c`。
- 本轮 workflow：`7bc96e3aa378fb7b5b0a4b5cdd49fb721777ac84`；交接单 raw SHA256：`b55a77279059871377e59aa1d7eafd6adba7492fba9d3b598f493e1ea5d14db3`。
- 原 R12 workflow：`7593f880ebec191ed55e03b2d3893d68b00ab0ca`；原任务 raw SHA256：`15c4f65a698a86ffeb0bbde8a6c97465905bcb0fb5f9bfc1856aec522161f1df`。

独立按 raw Git 核对：32993 个基线 mode/type/blob 条目全部不变，目标仅新增39个文件；manifest覆盖38项加自身。4份workflow原文与对应归档副本相同，10份产品源码输入与base raw blob及其声明摘要相同。新输入索引共109份必要导出，只包含本轮交付、来源原文和用于来源/pin核对的产品源码；没有复制数万份历史产物。[字节核对](../evidence/A03/review/P2-R12-prerequisite/delivery-byte-review.json)和[输入索引](../evidence/A03/review/P2-R12-prerequisite/input-index.json)保留每份出处、raw Git blob、SHA256、长度及实际导出路径。

| 冻结目标中的依据 | 已核对的 raw SHA256 |
|---|---|
| 原执行报告 | `cfb51c43f718349aa2c8d99fbb9bc3e145eb6b891e4d9507065648af9bd4fc04` |
| execution manifest | `b3f0483de0b007341a750963f3d71db92b8b9efec124c26b8394935bd6325f75` |
| 原进程释放记录 | `5318caeb0a97f014ee2c038b349316d41be12430e9ff29ca441f0a5679013b1f` |
| storage/__init__.py | `93cb82da040346cfba95a312f3615b8bfc5c47edee01ba69584ac338882cfa3a` |
| storage/native.py | `c3e2f01ccbfb7b64c49a5272eb51ffbe2f6af8c8abb5a51c4c9c6965166b902a` |
| native exchange schema | `8417b84787ec3ff95966129e7bf14e388c0b66018f4828d3c438fd2e1134a1af` |

原静态进程的脚本快照与目标测试入口、登记摘要一致，输入索引和产品source index摘要相符。原登记进程PID54248，历史wait/completion记录为exit0、timeout=false、alive=false；这不是本轮扫描当前PID。入口AST导入仅含argparse、ast、hashlib、json、pathlib、sys；结合冻结源码和输出，准备期停止的声明与交付一致。[原静态记录复核](../evidence/A03/review/P2-R12-prerequisite/author-static-record-review.json)没有将静态exit0当作五例功能成功。产品source index中既有5个LF→CRLF表示差异逐项显式核对，未把checkout摘要冒充raw blob摘要。

公共schema、profile/adoption、全部6项schema pins及23项implementation pins均未变且摘要一致；历史证据和共享协调文件未改。

## 按类限定的调用与校验链

下表行号均来自target与base完全相同的raw源码。复核以类体中的方法AST为入口，未采用模块级同名包装函数替代。[独立调用链证据](../evidence/A03/review/P2-R12-prerequisite/class-scoped-chain.json)保留完整函数源码、行号、源码摘要及构造语句的祖先条件。

| 真实入口/分派 | 路径与行号 | 静态事实 |
|---|---|---|
| `RuntimeStore.commit_action_result` | `src/annotation/runtime/storage/__init__.py:693–740` | 正常比较结果构造fact并更新action/intent/plan及事件；事务块之后在:737调用`self.project_plan`。UNKNOWN对应PENDING intent、不可重放和MAY_HAVE_BEEN_ATTEMPTED。 |
| `RuntimeStore.project_plan` | 同文件:742–744 | 持有effect gate后调用`self._project_plan_locked`。 |
| `RuntimeStore._project_plan_locked` | 同文件:760–826 | :770要求所有动作已有fact；:773从fact筛UNKNOWN；:786要求没有匹配receipt；:790要求issues非空；随后:793–800构造旧式POST_APPLY，:801调用`self._append`。 |
| `RuntimeStore._new_artifact` | 同文件:493–500 | 从plan复制schema_version等信封字段，payload仅经plain包裹，没有把旧诊断字段转换为native报告。 |
| `NativeRuntimeStore(RuntimeStore)` | `src/annotation/runtime/storage/native.py:219` | 未重写上述commit/project/_project_plan_locked/_new_artifact，也未重写_validate/transaction，实际继承对应RuntimeStore方法。 |
| `NativeRuntimeStore._append` | 同文件:291–298 | 将待追加产物合入包，:297先调用`self._validate`，再调用父类_append。 |
| `RuntimeStore._validate`及native bridge | storage:109–111；native.py:235–236、56–59 | `_validate`参数中的`self.bridge_for`先经NativeRegistry.context调用native `_issue_context`。不能忽略参数求值期间已经发生的native校验。 |
| native校验 | `contracts/a03_native/__init__.py:111–118、134–156、169–175` | `_issue_context`和`validate_native_bundle`进入`_validate_value`；`StaticPackage.validate`（`_closure.py:253–299`）先进行exchange schema校验。 |
| 通用入口的native分流 | `contracts/recovery.py:915–919`；native `NativeSchemas.check:160–166` | native exchange明确转入native验证；schema使用Amended定义，没有旧POST报告的回退分支。 |

此路径不要求调用显式`publish_quality`。所以原R12任务“不调用POST/Batch报告发布”的限制，不能避开投影内部的旧式POST构造。native校验在bridge/context及追加前验证中均有入口；本轮不推断哪个校验或其他前提会在真实运行中首先抛错。

## 字面payload与schema冲突

Schema路径：`src/annotation/contracts/a03_native/data/schemas/exchange.json`；JSON pointer：`/$defs/AmendedCheckReport/properties/payload/oneOf/2`。该分支stage为POST_APPLY，`additionalProperties=false`；根artifacts union选择AmendedCheckReport，没有兼容旧诊断形状的分支。

| 比较方向 | 独立从AST/JSON计算的字段 |
|---|---|
| 缺少6个native必需字段 | `action_bindings`、`content_check_status`、`frame_structure`、`report_observation`、`report_snapshot_ref`、`submission_status` |
| 多出4个被禁止的旧字段 | `checks`、`coverage`、`reason`、`snapshot` |

旧构造实际12个顶层payload字段为stage、subject、graph、policy、snapshot、receipt、coverage、checks、issues、decision、reason、recovery_refs。以上集合差异由本轮类限定AST重新提取并与schema计算，和作者声称的6/4相符；不是直接采纳作者preflight的通过字段。

native `_reports`（`contracts/a03_native/__init__.py:211–271`）还消费独立report_snapshot_ref、report_observation和逐动作action_bindings，核对fact、intent、resolution head和实际比较。因此改版本标签、填空字段或放宽schema也不能解决所需证据语义。

该冲突适用于“已有实际UNKNOWN action fact、尚无对应receipt”的投影分支。R11 F2/F3在切点尚无fact，投影UNKNOWN时未进入所有fact齐备的receipt/旧POST分支；F4已有APPLIED fact而issues为空。原四个crash cut的有限证据没有覆盖本分支，本次静态发现也不自动撤销其既有有限结论。

## 与U1–U5的关系及未观察边界

公开接缝、`PersistentMockSession.dispatch_action`（persistent.py:637–687）和模块级`apply_synthetic_action`（:219–245）显示partial会移除最后一个投影片段。`compare_action_effect`（planner/__init__.py:61–130）在非OK读回时返回INDETERMINATE/UNKNOWN；在完整且绑定成立的部分效果既不MATCH也不满足零框且状态不变的ABSENT时，返回CONFLICT/UNKNOWN。这是满足前提时的源码路径推导，未创建或观测实际部分效果。

原U1要求先以partial建立正式UNKNOWN；U2–U5要求先产生一次applied效果、以unavailable执行读回建立正式UNKNOWN，再分别恢复duplicate/contradictory/truncated/unavailable。因此五例共享本次被识别的正常UNKNOWN建立前提，准备期停止有源码依据；不能据此认定它是唯一尚存问题。

| 项目 | 冻结事实/本轮边界 |
|---|---|
| U1 | NOT_EXECUTED_STATIC_PREREQUISITE_CONFLICT |
| U2–U5 | NOT_EXECUTED_AFTER_PREPARATION_STOP |
| init/register/PRE/dispatch/UNKNOWN建立/reconcile | 原静态入口未执行；本轮产品导入/调用为0 |
| runtime/target数据库及四阶段capture | 冻结交付中未创建；本轮未创建、未连接、未重建 |
| 效果数、paused/pending、真实异常码及事务副作用 | NOT_OBSERVED，不是“观察到0” |
| 正式plan/intent/receipt/resolution/attempt、新观察和Resource | 本轮无动态运行产物，不补造引用 |

`RuntimeStore.transaction`（storage:154–167）源码区分sqlite3.Error与其他异常，并含commit/rollback路径；commit_action_result的fact事务与随后projection事务在源码上有先后边界。**本轮没有实际异常、提交/回滚或跨库/文件副作用证据，不能把源码结构写成已观察的持久化结果，也不能指定真实外层错误码。**

## 最小修复建议与需另行验证的范围

建议调度另发一个实现范围明确的任务，优先分离native投影与正式报告发布，而不是给旧payload补造报告观察：

1. 在`RuntimeStore._project_plan_locked`附近将旧UNKNOWN诊断POST构造提取为受保护的报告策略/钩子，默认分支保持legacy原行为；由`NativeRuntimeStore`覆盖native策略，使native投影专注原UNKNOWN fact、正式receipt和ExecutionProgress，不在缺少独立报告读回时伪造POST。建议主要实现文件仅为`src/annotation/runtime/storage/__init__.py`和`src/annotation/runtime/storage/native.py`。这是建议，未实现或采纳；仍须验证完整native闭包，而不是假定跳过旧构造就足够。
2. 保留现有`runtime/recovery/native_quality.py:12–85`的正式发布责任：在明确调用时正常取得受控、独立、新鲜的报告观察，绑定report snapshot、action/fact/intent/resolution，再产生typed POST/Batch。该文件本轮只作参考，建议不为规避投影错误而扩大修改。不能借投影隐式消耗native_report_reads或绕过原发布限额。
3. 两个建议实现文件均在23项implementation pins中。若后续确实改动，必须同步由责任人整合native `data/profile.json`中对应摘要，并更新`data/adoption.json`绑定的profile_sha256。当前schema、公共信封/API、oracle/producer/verifier和根依赖无需为这个建议预先变更。本轮没有更新任何pin或文件。

原fact、intent、消费permit、attempt_fact、原UNKNOWN及事件/Resource历史必须保留；receipt/progress精确绑定仍须完整验证。不能将UNKNOWN改成APPLIED/NOT_APPLIED，删除pending/paused/history，伪造report_observation，吞掉验证异常或更改期望来获得资格。legacy默认行为及其命名空间/原报告合同应保持兼容，不能把native策略应用到旧分支。

后续实现应证明：正常UNKNOWN建立能完成正式receipt/progress且保持真实未决和不可重放；报告发布前无伪造POST/Batch或隐式报告观察；明确发布时仍要求合法独立报告证据；legacy输出兼容；新的固定提交和pins可完整验证。随后才能按另行授权继续原U1→U5，检查实际异常、事务/双库副作用、身份/完整性/null字段、暂停与不重发，并保全原要求的现场原件。本轮不执行、不委派这些验证，也不自动启动新阶段。

上述投影/发布职责分离可作为既有native字段及独立报告语义的实现修复，不要求本轮改变共享合同。若要让“投影中的诊断HOLD”本身成为无独立观察的正式POST、增加新的诊断产物/可选字段、改变报告调用次数或接口必需行为，则已超出这个最小范围，需明确合同及消费者选择并交调度协调；不能由本次静态复核代替双方确认。B版本映射仍未共同确认。

## 本轮执行及交付

本轮只运行一轮新静态复核。新源码先严格UTF-8解码及compile检查，再运行；仅导入标准库，未执行AST裁剪代码或作者脚本。实际静态子进程PID67384退出0、无超时；6个只读Git子进程均登记argv/cwd/source/input/时限、真实原始流及wait/退出，所有Git使用`-c core.longpaths=true`。原PID54248的退出是历史证据，本轮没有当前PID扫描。[源码预检](../evidence/A03/review/P2-R12-prerequisite/source-preflight.json)、[进程释放证明](../evidence/A03/review/P2-R12-prerequisite/process-release.json)与[新manifest](../evidence/A03/review/P2-R12-prerequisite/sha256-manifest.json)保留实际依据；新manifest覆盖本报告及全部本轮文件，仅排除自身。

未改产品、schema/pins、作者目录、旧证据、共享协调文档或state；未运行U1–U5、历史功能或整套测试；没有线上/profile/凭据/网络/安装/付费模型/推送/B联系/A05题22/书级送交。用户model/thinking保持原设置，无委派。字段重置始终为`NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`，不运行、变体、委派或建议重测。

本报告只交付**阻断证据确认和最小修复范围建议**；R12功能与A03整体未验收，产品本地集成、I01及B兼容性确认均未放行。由调度独立核实后决定下一有界任务。
