# A03 P2-R8：冻结失败交付的有界独立核验

2026-10-17。继续原独立验收对话 `01a145aa-8d59-7c70-8d81-731712103a9a`，保留用户手动设置，消息省略 thinking/model。不委派、不修产品、不修改执行工作树、旧证据或调度 state。

## 冻结输入与交接边界

| 项目 | 固定值 |
| --- | --- |
| base | `8ad45dd07214ae406a3fab28d76a4b5abd6eef03` |
| target | `fa6edeb7e9dd0c9502781747e5fce012931d9441` |
| 合同桥接提交 | `352b1475fff85a034b839a712ee499ba4c1ec5e6` |
| runtime/producer 候选提交 | `334577d922d224789191a8b4d7127513692ada95` |
| 执行 workflow | `873d8151000430fc79e63b312ccd21978fc15f79` |
| 执行任务 | `docs/tasks/A03-P2-R8-native-bridge-implementation.md` |
| 执行任务 SHA256 | `b7dbf94ff06d8ba272b1bd20bf61afbe09fa1dd99c501dcb70f865ab36737721` |
| 执行报告 | `docs/tasks/A03-P2-R8-native-bridge-delivery.md` |
| 执行报告 SHA256 | `2d482c8c2b20985496cf0b07db65aaa68fccc3acfae6e363af0c3d34d6f0372d` |
| 执行清单 | `docs/evidence/A03/execution/P2-R8-native-bridge/manifest.json` |
| 执行清单 SHA256 | `c9d195c5a97ef6293cece1627372ecf8f7404d4537bac9a9bda5e298841f0c7e` |
| 释放记录 SHA256 | `58f0b7cbfd9d747144f24df05c4852714ad40417575486b92c92cc11eea7a98b` |
| bounded-outcome SHA256 | `6c5c68c5510bcb5cd2d7fb68b4e8bbe2d36fc8a8f093191652245b0233d9e5a7` |

执行工作树 `C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800` 已清洁冻结，执行对话 completed。审阅 workflow 和本单 SHA256 由调度消息给出。只按确切 Git blob 读取，沿用原独立隔离方式，不合浮动分支。运行 Git 时使用命令级 `-c core.longpaths=true`，不改变全局设置。

[调度前检](../evidence/coordinator/heartbeat-20261017-1510/A03-R8-delivery-preflight.json)核对了 462 个清单条目与清单自身、89 项输入 pins、28,750 个旧 tree entries 中 28,738 个未变条目、12 个允许修改的旧路径，以及 28 个已登记进程的 preregistration/started/completed/原始日志。pyproject 仅附加 native package-data。前检不导入候选、不运行功能、未扫描系统或 profile；进程释放结论限历史记录。清单实际名称为 `manifest.json`。

作者明确交付 **REVIEW，N1 未闭合**：唯一局部修复后，PRE producer 把 `coverage_for` 返回的 `(coverage, complete)` 整体交给要求对象的 coverage 字段，停在 `CheckReport.payload: SHAPE_oneOf`。N2–N7 未运行，目标效果为 0。不能把源码候选、已计算 PASS 或旧兼容测试当作链路通过。此次核验以确认真实阻断、影响和下一次最小修复边界为目的，禁止顺手扩张成全套新验收。

## 本轮核验项目

1. **原字节、范围和冻结。** 独立核对报告/manifest/release/输入索引及对应 raw Git，检查允许路径和 R7/旧 schema/profile/API 保全。不要只调用调度或作者的检查脚本作为结论。可以保存小型独立核对索引，避免复制历史全集和重复巨型快照。
2. **确定性失败定位。** 对照 target 的 `quality/synthetic_precheck.py:121-130`、`quality/targetcheck/__init__.py:92-109`、新 PRE schema 和实际第二次 N1 父/子 stderr，独立判断二元值是否违背字段合同、真实失败是否到达该层。静态源码加已封存实际日志能确证时，不重跑 N1、不创建新的 native 库或目标效果。若缺少必要证据，明确指出缺口，不能补造后续成功。
3. **实际边界。** 独立检查两个 N1 运行的脚本/产品快照及版本差异，确认第一次 HASH_MISMATCH 与唯一修复、第二次独立 SHAPE 阻断的区分。仅从冻结 raw blobs 提取最少 SQLite 文件到独立临时目录，用只读 immutable 连接核对记录数与状态，记录副本读取前后 SHA；禁止对执行原库打开可写连接。核对第二次 plans/intents/permits/effects 为 0、run 为 OBSERVED 且 pre_ref/run_sha 为 null，不能将已计算五项 PASS 当作实际接纳。检查 N2–N7 的 NOT_RUN 与无成功后段产物一致；不执行这些组。
4. **兼容与释放证据的准确口径。** 核对三组兼容性一轮记录及实际产品快照，说明均早于最终 native-only 投影修复；它们不证明最终候选全部通过。C01 的若干嵌套子进程 exit=1，需从原始命令/日志/调用用途区分预期拒绝探针和真实测试失败，不能只按父进程 exit=0 或“70”数字下结论，也不要为此重跑全部兼容性测试。复核自己需要的运行记录、28 个进程最终状态和原始 stdout/stderr，释放结论不扩大成当前全系统扫描。
5. **修复建议必须有界。** 若确认缺陷，输出 REWORK，给出具体调用/返回值约定、最小修改路径和必须补齐的针对性验证；明确本轮尚未到达的 N1 后半段及 N2–N7 仍未验收。不能提前认定改一行后整个 A03 能通过。原 P2 V01–V10/R01–R18 仍未豁免，I01 不释放。若发现另一个会直接阻止同一前缀的确定性问题，可静态记录；不得发散新增矩阵、候选或尝试修复。

只做上述一次有界核验。必要的独立字节/静态/只读数据库脚本保存精确输入摘要、argv/cwd、限时、原始输出、PID 与退出状态；不导入或运行旧 examples/AST/exec 候选驱动，不重复作者失败命令，不运行 native API、N1 全链、N2–N7、旧 36 矩阵或旧 P2 全矩阵。允许普通 Python 标准库进行只读证据核对。

## 输出与后续

只新增 `docs/evidence/A03/review/P2-R8-native-bridge/` 与 `docs/tasks/A03-P2-R8-native-bridge-review-report.md`。报告记录被审 target、确切缺陷、已核实与未运行项目、最小修复范围；完整新增文件 SHA 清单排除自身，所有自有进程退出后交付。不得自行改执行代码、验收 state、记录 INTEGRATED 或释放 I01。旧 R7 ACCEPTED 与本轮 R8 的结论分别保留。

禁止网络、浏览器、真实平台、凭据/profile、OCR、模型、付费 API、安装、push、B/执行者消息。A05 题22不得重放。字段重置专项保持 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`，不复跑、变形、委派或建议重测。A03 用户手动思考设置继续保留。
