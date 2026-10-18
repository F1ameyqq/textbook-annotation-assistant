# A03-P2-R12：准备阶段阻断的独立静态复核

状态：待原独立验收对话复核。任务仅确认冻结交付、源码冲突及最小修复边界；R12 的 U1–U5 尚未执行，A03 整体保持 REWORK，I01 未放行。

## 固定身份与输入

- 执行对话：`01a145aa-2fea-7942-97f9-ad260acf4e30`。
- 独立验收对话：`01a145aa-8d59-7c70-8d81-731712103a9a`。复用现有对话，省略 model、thinking，保留用户设置。
- 冻结目标：`394fe51f5ed14c5ed312073a20faac0f5cbb9990`。
- 产品及历史证据基线：`cc5966dc58c62017a27266c40ca0cedc5c68485c`。
- 原 R12 工作流：`7593f880ebec191ed55e03b2d3893d68b00ab0ca`；[原任务](A03-P2-R12-inconclusive-readback-validation.md) SHA-256 为 `15c4f65a698a86ffeb0bbde8a6c97465905bcb0fb5f9bfc1856aec522161f1df`。
- 派发键：`A03:review:P2-R12-prerequisite:394fe51f5ed14c5ed312073a20faac0f5cbb9990`。

下表文件均以冻结目标的 raw Git blob 为准，不能以移动中的工作目录替代：

| 文件 | SHA-256 |
| --- | --- |
| `docs/tasks/A03-P2-R12-inconclusive-readback-report.md` | `cfb51c43f718349aa2c8d99fbb9bc3e145eb6b891e4d9507065648af9bd4fc04` |
| `docs/evidence/A03/execution/P2-R12-inconclusive-readback/manifest.json` | `b3f0483de0b007341a750963f3d71db92b8b9efec124c26b8394935bd6325f75` |
| `docs/evidence/A03/execution/P2-R12-inconclusive-readback/process-release.json` | `5318caeb0a97f014ee2c038b349316d41be12430e9ff29ca441f0a5679013b1f` |

同时读目标中的 `preflight/static-prerequisite-conflict.json`、`preflight/source-chain-supplement.json`、`inputs.json`、`bounded-outcome.json` 及静态子进程记录。以上相对路径均属于该执行证据目录。

调度已做一次[冻结交付核对](../evidence/coordinator/heartbeat-20261018-0830/r12-delivery-preflight.json)，SHA-256 为 `dec3a853ec091bab3cebf0231a360bb31d7b21f5d7bcb641223bc3c422e4dd31`：32993 个基线树项未变，39 个新增文件 raw bytes 核对通过，manifest 覆盖 38 个成员加自身；4 个工作流输入、10 个产品源码输入及 1 个已退出静态子进程记录匹配。此结果仅是交付预检，不是独立验收或功能通过。

## 本轮要回答的四件事

1. 冻结报告、manifest、源码输入、静态脚本快照及退出记录是否相互一致；是否确实保持产品、公共 schema、版本 pin 和历史证据未变。核查树项和新增文件即可，不复制数万条历史产物。必须区分“历史记录证明该子进程已退出”和“当前进程扫描”。
2. 独立按类限定的方法检查调用链：`RuntimeStore.commit_action_result` → `project_plan` / `_project_plan_locked` → `_new_artifact` / `_append`，以及 `NativeRuntimeStore` 继承、重写和校验路径。确认 UNKNOWN action fact 是否导致自动构建旧格式 POST_APPLY，是否在 native 校验中遇到下述不一致；确认其与原 U1–U5 正常建立 UNKNOWN 的前置步骤相关。记录准确函数和行号、字面字段及 schema 路径，不把同名其他函数误当实际入口。
3. 报告是否诚实区分静态发现与动态事实：U1–U5、runtime 初始化、PRE 注册、dispatch、UNKNOWN 建立和 reconcile 均未运行；没有创建 runtime/target 数据库。`NOT_OBSERVED` 不得改写成已观测到零副作用；不能推断实际异常码、事务提交/回滚效果或唯一剩余故障。
4. 若冲突成立，列出一个可执行的最小修复范围及后续验证要求，说明 native 投影与正式报告发布各自责任、legacy 兼容边界、UNKNOWN fact/receipt/progress/pending/history 的保留要求。判断是否涉及既有合同语义变化；有无法由现有合同决定的选项就明确列出，不代替跨侧确认。本轮只给证据和建议，不实现、不采纳修复方案。

待核对的作者结论（不是预设验收答案）：

- `src/annotation/runtime/storage/__init__.py` 的 UNKNOWN 投影分支生成旧式 POST_APPLY payload。
- native schema `src/annotation/contracts/a03_native/data/schemas/exchange.json` 的 `/$defs/AmendedCheckReport/properties/payload/oneOf/2` 要求不同字段，并禁止额外字段。
- 缺少 6 项：`action_bindings`、`content_check_status`、`frame_structure`、`report_observation`、`report_snapshot_ref`、`submission_status`。
- 多出 4 项：`checks`、`coverage`、`reason`、`snapshot`。
- 既有 R11 四个 crash cut 的有限通过不自动覆盖这条 UNKNOWN fact 投影分支，也不因本次静态发现自动撤销。

不得用伪造 `report_observation`、把 UNKNOWN 改成成功、删除 pending/history、放宽 schema、静默吞错或更改测试期望绕过冲突。修复范围应首先检视 native 投影职责；需要更多文件或合同变更时说明理由和边界。

## 执行边界与交付

这是一次有界静态复核，可用 Python 标准库解析 Git bytes、AST 和 JSON；不导入/调用产品，不连接 SQL，不运行 init/PRE/dispatch/project/reconcile，不启动 U1–U5，不重跑历史功能或整个测试集。不要运行作者 seal 或准备脚本以刷新其冻结产物。所有 Git 调用设置 `-c core.longpaths=true`，文件使用显式 UTF-8；新静态脚本先做编译检查。

只新增 `docs/evidence/A03/review/P2-R12-prerequisite/` 和 `docs/tasks/A03-P2-R12-prerequisite-review-report.md`，不修改共享协调文件、产品或旧证据。选取必要源码和证明文件即可，旧证据以确切提交和摘要引用。静态子进程若需要，登记命令、时间界限、退出和自有进程释放；不得借本轮重启任何功能进程。保留第一次失败，无法完成则如实交付未完成项，不自行开启新一轮修复/复验。

报告给出冻结目标、原始输入出处、每项核对的结论、冲突是否成立及其适用范围、最小修复建议和仍未运行的原始场景；附新文件 manifest 和必要进程释放记录。允许结论为“阻断证据确认”或“证据需要补正”，不能把本轮写成 R12 功能 ACCEPTED。执行者不得自行宣布整体验收通过。交给调度核实后才决定下一个有界任务。

本轮没有平台操作、登录/profile、网络、安装、付费模型、推送或 B 侧派发。field reset 维持 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`，不通过变体、委托或建议重测绕过。

完成后的依赖：调度核对独立静态结论 → 必要时向原执行者派发确切修复范围 → 固定新提交后继续原 U1–U5 功能执行及独立验收。它们完成仍不能替代原 A03 其余未覆盖验收项、范围明确的本地集成或 B 包兼容性确认。
