# A03 P2-R6：只修混合环控制的内部头引用

2026-10-17。继续原执行对话 `01a145aa-2fea-7942-97f9-ad260acf4e30`，保留用户当前思考设置，不改 thinking/model、不委派或新建任务。工作树 `C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800`，分支 `codex/a03-runtime-recovery`，唯一 base `323013c4f0dbae75368e56db60147a8057368d1f`。调度消息给出本任务及 R5 归档的精确 workflow；按 raw Git 读取，不合浮动主树。

## 唯一缺口与固定输入

先读 [R5 调度决定](A03-P2-R5-registration-context-coordinator-decision.md)、[R5 独立报告](A03-P2-R5-registration-context-review-report.md)和[调度复核](../evidence/coordinator/heartbeat-20261017-1059/A03-R5-review-check.json)。独立报告 SHA256 `f4831a2f8274f3cad718b440b0bd647ccd726ba997dafb5e0089028d2fb5ab5f`，审阅清单 SHA256 `bff7b99b110f8c104317357460a41b05de72ec73f997d3c6c7dd19f65e60f496`。六项静态检查已有限接受，不重新打开或复跑。

唯一输入为 base 中 `examples/a03/P2-R5-registration-context/cases/artifact-resource-frame-mixed-cycle/repair-01/`，通过同版 repair-case-index 及 case 文件定位资源。bundle SHA256 `f2f5e5a032271d7890165d49e4c336dbcb5f628bbf18e372e0d7148a54535d67`；resources/0.json prefix SHA256 `4d153e82f0a75d233bb77bb7028a2a3dc2bdbcd4f22bda6514a15d0be4450de0`。

第 8 条 READONLY_ABSENCE_STARTED 的 initial_event_head 仍带旧第 7 条 hash `87f8f86767e923c8fe7eb351c45eb57df3d6d4ebfdf855249fc7f5be025bbf84`；实际前驱是 `28ef8b468d67a04e9ba75fe3e41a45fb96f280deb95ddcef4cdc2097d6c195f9`。现在的 MIXED_CYCLE 拒绝不能证明控制是单一故障。本轮修输入，不据此更改实现。

## 范围和先行检查

只新增 `examples/a03/P2-R6-mixed-control/`、`docs/evidence/A03/execution/P2-R6-mixed-control/`、`docs/tasks/A03-P2-R6-mixed-control-delivery.md`。旧文件 mode/type/blob 及失败证据不变；不复制完整历史证据、旧保全清单或产品代码。最小必要输入可引用冻结原件并按 raw Git 逐项绑定。

在新目录制作一个修正候选，修正该内部头及因此必须更新的后续 event_hash/previous_hash、prefix accepted/expected head、Resource SHA、Artifact 内容摘要、exact refs 与 case/index pins。逐项解释传递修改；不得改书籍/scope、删除 UNKNOWN/登记历史、删引用、删证据或重构控制。保留原来的 Source → 正式 EvidenceRecord → prefix Resource → 合法 frame → return Resource → 同一 Source 混合环及合法声明。

在任何 Package 调用前，以数据读取独立核对并落盘：全部 event 摘要/前驱链、所有 initial_event_head 与实际前驱、accepted_anchor/expected_book_head 与对应事件、Artifact hash、Resource 原字节 SHA、普通四元组引用及 frame/外层各自声明一致。列出相对于 repair-01 的全部语义变化，证明只有该头修正和必然传递变化，混合环仍闭合。先行检查发现本任务以外的新语义矛盾时立即停止，不能先运行期待错误码再解释输入。

## 一次完整入口与停止条件

保持 base 中 R5 `registration.py` SHA256 `3f0281c5cfc9aeec99b11fa2de30ba40e9984a19dd0e651b747d99ebe29772ba`、`load_static.py` SHA256 `734b8760b58f7778f4bd32608b77fc87f95a31c027ce457408d5fbdcf8166098` 及其 R2/R3/schema/oracle pins 全部不变。允许新建只读驱动传入这一个候选；不能改 Package、基类、Schema、加载语义或预期判定。

先行数据检查通过后，只调用一次完整 `registration.Package.validate`。记录实际继承入口调用次数、MIXED_DAG 到达层、拒绝路径、real consumers 与 consumer_failures；预期 MIXED_CYCLE 且声明/输入检查没有无关残余。不以 helper 通过或同码替代真实入口。不要执行其余六例、旧 36 矩阵、session/conversion 或字段重置专项。一次入口后冻结，不再自行修复/重跑或增加变体；未闭合则如实交付 REWORK 并列出最短原因，由调度决定是否接受此控制证明或转入单独产品任务。

## 交付

交付确切提交、简短报告、单候选变更证明与先行核对结果、只读复现命令、最小输入 raw Git 索引、全部新文件清单（仅排除清单自身）、旧路径保全证明。运行前保存脚本/输入 SHA、argv/cwd、限时与 stdout/stderr；启动后记录 PID，完成记录退出/超时/alive。冻结后自有运行全部结束、工作树干净，交由原独立验收对话复验这一候选，执行者不能自行宣称验收通过。

产品/SQLite/native/planner、网络/浏览器/平台/profile/凭据/OCR/模型/付费 API、依赖安装、推送和联系 B/验收者均不在范围；I01 不释放。字段重置专项保持 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`，禁止复跑、变形、委派或建议重测。本轮不扩大到三项产品 ABI 决策或重新审查 R4 接口盘点。
