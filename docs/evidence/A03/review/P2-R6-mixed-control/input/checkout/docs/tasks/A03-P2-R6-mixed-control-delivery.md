# A03 P2-R6 混合环控制头修正交付

状态：**REVIEW**。单一候选先行数据检查通过，随后一次不变 R5 完整入口在 MIXED_DAG 层拒绝为 MIXED_CYCLE，consumer_failures 为空。没有自行宣布验收接受；冻结后等待原独立验收。

- base：`323013c4f0dbae75368e56db60147a8057368d1f`；workflow：`77d3e123ab7247eae6f81f7acd669e3a69c934a0`。
- 工作树：`C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800`；分支：`codex/a03-runtime-recovery`。
- [任务原文](../evidence/A03/execution/P2-R6-mixed-control/inputs/workflow/docs/tasks/A03-P2-R6-mixed-control-rework.md) SHA256：`97211bd4dd86097ae2ed08c19f38f208c4a790432fe42875bb0d7901fff1f0cd`。保留用户当前思考设置，未改档、推断具体档位、委派或合浮动主树。

## 单一输入修正

[候选 case](../../examples/a03/P2-R6-mixed-control/case.json) 只来源于 base 的 R5 mixed-cycle repair-01；[case/index](../../examples/a03/P2-R6-mixed-control/case-index.json) 固定新候选。没有复制完整历史证据、旧保全清单或产品源码。

先行 [语义差异与数据检查](../evidence/A03/execution/P2-R6-mixed-control/precheck.json) 完整列出变更：第 8 条事件 initial_event_head.hash 从旧值 `87f8f86767e923c8fe7eb351c45eb57df3d6d4ebfdf855249fc7f5be025bbf84` 改为实际第 7 条摘要 `28ef8b468d67a04e9ba75fe3e41a45fb96f280deb95ddcef4cdc2097d6c195f9`。必要传递为事件 8—14 的 7 个 event_hash、事件 9—14 的 6 个 previous_hash、prefix expected_book_head.hash，共 15 处叶字段变化。

accepted_anchor 在第 5 条，保持不变。bundle 只有 `evidence[1].resource.sha256` 一处语义变化。16 个 Artifact 内容/hash、所有 ArtifactRef、return Resource、书籍/scope/版本/声明/旧历史均不变；没有删引用、删证据或重构控制。

| 候选文件 | SHA256 |
| --- | --- |
| bundle | `6a39c873de02dab04d3efd831cb1032b87ba8323c35bfd2a7a31f0b2e48dabd2` |
| prefix Resource | `d946006863bac1a8862ba2b3652f0b62e0914c36625541d463c342721e508e5f` |
| case | `2763198f4b68b9e636b00780cf5a28b8a89ac0dc117269c43fc6efc731bccab2` |

## 先行核对与一次完整入口

先行检查由新的标准库数据读取脚本独立完成，未导入 R5/R3/R2 checker 或产品。通过后才允许 entry 驱动读取落盘结果并导入不变 R5。检查覆盖 16 个 Artifact、18 个 Resource 原字节、普通 exact refs、两个 prefix 的所有事件/内部头/accepted/expected head、已有 basis 头、正式 EvidenceRecord 展开及 frame/外层各自声明和书籍/scope。58 份数据消费检查均无声明故障；该数字包含重复上下文和全局 frame 的数据核对，不冒充 58 个 runtime 真实消费者。

原 Source → 正式 EvidenceRecord → prefix Resource → 合法 frame → return Resource → 同一 Source 的五条环边先行验证保留；[实际入口结果](../evidence/A03/execution/P2-R6-mixed-control/entry-result.json) 又记录五边均存在于真实 Package 图。

| 实际观测 | 结果 |
| --- | --- |
| 不变 R5 完整入口调用 trace | 1 |
| 继承 R3 / R2 validate 调用 trace | 各 1 |
| R3 entry_calls | 0 → 1，增量 1 |
| 到达层 / 实际拒绝 | MIXED_DAG / MIXED_CYCLE |
| 错误路径 | A:760b541bec881e9d98abb75f38bc7e34a75d2ed047edbc8ac657091c70fdc320 |
| 真实消费者 / None-book 消费者 | 44 / 0 |
| consumer_failures | [] |
| 实际图节点 / 原环边保留 | 64 / 5 边均存在 |

R5 registration.py SHA256 仍为 `3f0281c5cfc9aeec99b11fa2de30ba40e9984a19dd0e651b747d99ebe29772ba`，load_static.py 仍为 `734b8760b58f7778f4bd32608b77fc87f95a31c027ce457408d5fbdcf8166098`；R2/R3、Schema、oracle pins 与加载语义全部不变。只读 trace 观察调用/到达行，没有修改返回、异常或模块判定。没有调用 helper 代替完整入口；没有执行 session/conversion/oracle comparison。

## 驱动启动失败留痕

`entry-01` 的 trace 条件中 `__code__` 后漏空格，Python 在解析整份文件时 SyntaxError 退出 1；模块顶层代码、Package 构造/导入/调用都未发生，invocation guard 和结果文件当时不存在。原注册脚本、SHA、stdout/stderr、PID/退出完整保留。只补空格，先由 `syntax-01` 做 AST 检查，见 [语法核对](../evidence/A03/execution/P2-R6-mixed-control/driver-syntax-check.json)，随后 `entry-02` 执行尚未发生的唯一完整入口并退出 0。候选和 checker 未变；这不是完整入口后的修包重试，也没有第二次 Package 调用。

该启动错误属于作者驱动错误，不隐藏为语义通过或改写退出。实际计数来自 trace 和继承类计数差；不是用脚本字面量次数代替测量。

## 保全、归档和复现

[46 项 raw Git 输入 pins](../evidence/A03/execution/P2-R6-mixed-control/raw-input-pins.json) 绑定必要 workflow 文档、唯一源 case/资源、R5/R3/R2 源码与 Schema、实际 fallback Resources；旧源码只读引用，无代码复制。输入在完整入口前逐项核对，所有输出限本任务三处新路径。

[旧路径先行指纹](../evidence/A03/execution/P2-R6-mixed-control/old-preservation-before.json) 和 [封存后指纹](../evidence/A03/execution/P2-R6-mixed-control/old-preservation-after.json) 以可复现长度前缀摘要流核对 28,318 个旧路径的工作区字节/symlink，并逐项比较 HEAD/index 的 mode/type/blob 与精确 base。未复制旧保全清单或创建历史文件全集副本。

[归档核对](../evidence/A03/execution/P2-R6-mixed-control/archive-verification.json)、[完整新增清单](../evidence/A03/execution/P2-R6-mixed-control/sha256-manifest.json)（仅排除自身）及 [自有同步进程释放](../evidence/A03/execution/P2-R6-mixed-control/process-release.json) 一并封存。运行均先登记脚本/输入 SHA、argv/cwd/限时并持久打开 stdout/stderr，再记 PID，结束记退出/超时/alive；失败不覆盖。最终提交 raw Git blob 与清单核对，工作树干净；确切 commit 在交付消息中提供，避免报告自引用。

只读复现命令供原独立验收使用，本轮封存阶段没有再次执行 Package：

```powershell
Set-Location C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800
python -X utf8 -B examples/a03/P2-R6-mixed-control/entry.py --readonly
# 只核对归档和旧文件，不导入 checker 或重复先行数据检查。
python -X utf8 -B docs/evidence/A03/execution/P2-R6-mixed-control/archive.py --check
```

R5 六项静态范围按既有 ACCEPTED_STATIC_LIMITED 保留，本轮未重跑。旧 36 矩阵、产品/SQLite/native/PRE ABI/planner、网络/浏览器/平台/profile/凭据/OCR/模型/付费 API/安装/推送/B 或验收者联系均未发生。A03 恢复功能及 I01 仍未接受。字段重置专项仍为 **NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION**，未复跑、变形、委派或建议再测。一次完整入口后冻结为 REVIEW，到此停止。
