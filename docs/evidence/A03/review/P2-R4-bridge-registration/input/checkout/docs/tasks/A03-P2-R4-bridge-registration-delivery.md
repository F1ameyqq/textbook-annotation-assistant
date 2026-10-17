# A03 P2-R4 桥接接口与登记准备交付

状态：**REVIEW_WITH_MINIMAL_RESIDUAL**，由原独立验收对话评审；执行者未记 ACCEPTED。正包被固定总入口拒绝，目标元组负控被同一路径遮蔽，本轮按停止条件冻结。R3 原有 ACCEPTED_STATIC_LIMITED 不扩大为本轮正包或恢复功能通过。

- 原工作目录：`C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800`；分支 `codex/a03-runtime-recovery`。
- base：`87606b73e0754fa670491d9fb958a416c26bfe88`；workflow：`ef1d2f4a20971b416afae500889aa5c090dfe89b`。
- [固定任务原文](../evidence/A03/execution/P2-R4-bridge-registration/inputs/documents/A03-P2-R4-bridge-registration-preparation.md)，SHA256 `fdef54715b78fcf48bcdb65a4cea3aea0e479ebf3cf1251d2455be91b8399dc5`；未合浮动主树。
- 保留用户当前思考设置，未推断档位、改档或委派。字段重置专项仍为 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`。

## 交付物

[接口表](../../examples/a03/P2-R4-bridge-registration/bridge-interface-proposal.json) SHA256 为 `b57d0af5d72a03c4b16e6eeedc267bda50f1dfcf022728b1f107f5b158a22207`；[简短说明及输入输出形状](../../examples/a03/P2-R4-bridge-registration/README.md) 补充 19 个现有入口及 1 个尚不存在的私有 PRE 接纳边界。机器表固定每个源码 blob/SHA、签名/函数摘要、版本选择、exact refs、拒绝条件、后续文件/函数及未执行的完整单题调用链。

[raw Git 输入索引](../evidence/A03/execution/P2-R4-bridge-registration/input-index.json) 固定 6 份 workflow 文档、12 个仅作文本/AST 的产品源文件和 15 个复用静态输入；[资源输入 pins](../evidence/A03/execution/P2-R4-bridge-registration/resource-input-pins.json) 固定 5 份复制资源。[函数与类型清单](../evidence/A03/execution/P2-R4-bridge-registration/function-inventory.json) 没有产品 import。既有 profile/schema/API/R3 原件及 pins 均保留。

四份完整最小包（每包 10 artifacts、6 事件）分别为 [正包](../../examples/a03/P2-R4-bridge-registration/cases/registration-positive/case.json)、[Source 负控](../../examples/a03/P2-R4-bridge-registration/cases/source-binding-negative/case.json)、[Snapshot 负控](../../examples/a03/P2-R4-bridge-registration/cases/snapshot-binding-negative/case.json)、[target 负控](../../examples/a03/P2-R4-bridge-registration/cases/target-tuple-negative/case.json)。每份 case 索引包含 bundle/Resource 原始 SHA、逻辑路径、语义修改与预期层级；资源与事件摘要均重算。固定 schema、profile、API、原始 fixture 按输入索引从 base 只读复用，不拷贝或重生成大候选。

## 实际检查与残余

仅在 `prepare-01` 调用固定 R3 `closure.Package.validate` **4 次**，未重跑旧 36 矩阵。完整 [实际结果](../evidence/A03/execution/P2-R4-bridge-registration/four-package-results.json)、[路由证明](../evidence/A03/execution/P2-R4-bridge-registration/fixed-entry-routing.json)、[一次范围内诊断](../evidence/A03/execution/P2-R4-bridge-registration/minimal-residual-assessment.json) 保留。

| case | 预期 | 实际/错误位置 | 解释 |
| --- | --- | --- | --- |
| registration-positive | STATIC_ACCEPTED | FRAME_REGISTRATION_BINDING，r4-static/registration-positive/prefix.json | 未通过 |
| source-binding-negative | 登记绑定拒绝 | FRAME_REGISTRATION_BINDING，r4-static/source-binding-negative/prefix.json | Source A 与 Snapshot/scope B 不一致，实际消费者层拒绝 |
| snapshot-binding-negative | 登记绑定拒绝 | FRAME_REGISTRATION_BINDING，r4-static/snapshot-binding-negative/prefix.json | Snapshot A 与 Source/scope B 不一致，实际消费者层拒绝 |
| target-tuple-negative | 登记 target 元组拒绝 | FRAME_REGISTRATION_BINDING，r4-static/target-tuple-negative/prefix.json | 目标不一致存在，但被全局上下文失败遮蔽，不能认定控制有效 |

`matched` 只表示错误码匹配，不能当成全部三个负控语义均已证明。继承固定 R2 `check.py:70` 的登记谓词在正包实际消费者中成立；`:87` 全局 EvidenceRecord 扫描传 book=None，重入 typed prefix 后在同谓词失败。诊断 JSON 给出每包实际输入及两上下文谓词值；这不是额外 Package 运行。固定 R3 加载器仅重定向 `base.EVID` 的输出赋值，Package 类 AST 前后相同，类摘要 `df0133704f9cb876a1d530d629a8a65a1f5ff45bf86129a4d68612e66f8085e4`。

局部选择（均未实施）：将全局无上下文的 EvidenceRecord 字节/图检查与实际消费者绑定检查分开，保留真实 book/scope、frame 声明及混合 DAG；不能简单遇 None 就豁免。若调度选择限制 Resource 放置，须先确认正式直接消费字段和另一个有限包，不能本轮换路径追绿。解除正包阻断后需独立判断 Snapshot.target_id 与 canonical 登记 target 的校验；当前未复现一个被接受的 target 反例。

## 运行留痕与文件审计

每个登记子进程先写 argv/cwd、脚本原件/SHA、超时和 stdout/stderr 文件，随后记录 PID，结束记录退出码/alive。见 [runs](../evidence/A03/execution/P2-R4-bridge-registration/runs/freeze-01/registration.json)。`freeze-01` 退出 0；`prepare-01` 因正包残余退出 1；`assess-01` 因把继承谓词误查在 R3 文件而 AssertionError 退出 1，原脚本/错误保留；仅修正诊断的源码定位后 `assess-02` 退出 0，未再调用 Package。其间一次未封装的文件读取因 assessment 尚不存在而 FileNotFoundError，只保留在工具轨迹，未重造为原始文件证据。

[交付文件审计](../evidence/A03/execution/P2-R4-bridge-registration/delivery-verification.json) 只检查输入/文件摘要、四包保存完整性、接口源签名和链接，不执行产品或重新校验案例。[自有进程释放](../evidence/A03/execution/P2-R4-bridge-registration/process-release.json) 记录自有同步子进程均退出；[新增文件清单](../evidence/A03/execution/P2-R4-bridge-registration/sha256-manifest.json) 覆盖三个授权新增范围内所有文件，仅排除清单自身。封存前核对 28,002 个旧跟踪文件的工作区字节不变，并核对暂存 raw Git blob 与清单；最终提交 SHA 随交付消息提供，避免文件自引用。

`verify-01` 完成前置摘要检查后，在检查尚待本次成功审计才生成的 `delivery-verification.json` 自链接时退出 1；原日志保留。仅补充这个封存前待生成链接的白名单后执行 `verify-02`，不改变包或 Package 语义。最终只读 `--check` 要求所有链接实际存在，没有该豁免。

最短只读复现（文件/留痕审计，不重跑四包）：

```powershell
Set-Location C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800
python -X utf8 -B docs/evidence/A03/execution/P2-R4-bridge-registration/verify.py --check
```

`prepare.py` 和 runner 的 prepare 模式是已完成的一次性生产入口，不是本轮授权再次执行的复现命令；`xb` 防止覆盖历史。接口、包与诊断脚本可只读检查。

## 限制与停止

产品/planner 未运行或改动，DB 未打开/查询，native session、浏览器、平台、profile、凭据、OCR、模型、付费 API、依赖安装、推送、B/验收者联系均未发生。旧 1.1 仅作方案中的历史读取；当前 1.3、R2 profile、oracle 和新 PRE 接纳 API 未采用。没有原生单动作计划生成/UNKNOWN/恢复/晚到 receipt/POST 链的运行证明。I01、native、oracle、公共合同及 B 采用仍关闭。本轮交 REVIEW 后停止，不自行修 checker、追加案例或重测。
