# A02 执行交付报告

日期：2026-10-16（Asia/Shanghai）。执行状态：**REVIEW**，待独立对话复核及主调度验收；执行者不标 ACCEPTED、不释放 A03、不集成或推送。

固定 QuestionGraph 已经通过独立计算的 TARGET 检查生成 ApplyPlan，真正改变内存模拟目标，再根据独立读回生成 ExecutionReceipt。正常样例实际新增 3 个模拟题 / 9 个模拟框，保持 `CONTENT_PENDING / PENDING / NOT_SUBMITTED`。保存后响应和读回丢失样例实际新增 1 题 / 4 框，但回执保持 UNKNOWN / PAUSE_RECONCILE，后续动作没有派发。

## 版本与授权

| 字段 | 本次值 |
|---|---|
| 任务 | A02：计划、目标检查与模拟执行 |
| base_commit | `39341c98d73c354d639f3beeb55429f55d0e9be5` |
| workflow_commit | `39341c98d73c354d639f3beeb55429f55d0e9be5` |
| 确切代码提交 / 被正式复现 HEAD | `3fe492ce10bf93711ce57d305bc716f8b29345b7` |
| 交付 HEAD | 包含本报告和最终证据的后续文档提交；完整 SHA 在本对话最终交付回执列明，代码与上行提交一致 |
| 工作分支 | `codex/a02-planner-mock` |
| 实现与 Git 工作目录 | `C:\Users\ASUS\.codex\worktrees\a02-planner-mock\1800` |
| 合同 / 交换文件 / C01 样例 | `1.0.0-a-proposal` / `c01-exchange-1` / `c01-fixtures-1` |
| A02 实现 / 输入样例 | `a02-1` / `a02-fixtures-1` |
| 数据与运行性质 | 所有业务输入、资产和证据 SYNTHETIC；READY 计划及执行 SIMULATED；BLOCKED 诊断回执 NOT_EXECUTED |
| 线上 / 模型 | 浏览器、网络平台、OCR、最终提交、模型调用和模型花费均为 0 |

严格使用正式派发的独立工作树。未修改主工作区、contracts、C01 样例、公共政策、根依赖、父入口、source、geometry、runtime 或 B 模块；未重放 A05 题 22，未使用真实测试书授权执行平台动作。未创建新任务、未向其他对话发送消息。

## 改动与公共入口

- [targetcheck](../../src/annotation/quality/targetcheck/__init__.py)：纯计算当前快照、授权书/目标/范围、显式目录映射、平台能力及适用版本、政策和独立覆盖清单，产生逐项 TARGET 报告与具体 issue。
- [planner](../../src/annotation/delivery/planner/__init__.py)：复算 TARGET 与配置绑定；仅两阶段 PASS 才生成 READY；按内部身份、片段归属、共享材料和选定答案生成有序 CREATE_FRAMES。计划相关事实的 before/after 与每目录新题顺序明确保留。
- [mock](../../src/annotation/delivery/mock/__init__.py)：持有可单独读取的真实内存目标，追加 intent/response/readback/receipt 日志；比较读回决定结果；按书保留完整未决回执与 pending 暂停依据。
- [作者回归](../../tests/test_a02.py)、[固定输入](../../tests/fixtures/a02/normal/input.json)、[演示及 API 说明](../../examples/a02/README.md)、[证据复现器](../../examples/a02/verify.py)。

运行模块只从 `annotation.contracts` 公共 API 导入类型/封签/引用/校验，不复制合同类型，不导入合同私有实现。算法桩仅存在于明确标注的样例输入；没有调用 B 的 recognition/assembly/precheck。

`SimulationConfig` 为 A02 本地模拟配置，书/目标/范围、允许操作、会话模式、内部到平台目录映射整体摘要绑定 producer.config_version。它不扩展 C01 字段。新题目录不能按同名猜测；已映射题同时核对平台 ID、实际目录、已知题序。执行前使用会话自行读取的当前快照，并重新生成计划逐项核对，拒绝重新封签的动作/事实篡改。

C01 原有保证与本次新增保证分开：C01 负责结构、引用/摘要、角色/坐标、两阶段资格、回执状态组合和批次约束；A02 实际计算 TARGET 条件、投影动作、改变目标、采集读回、比较效果，以及在调用方省略日志时仍由会话保留同书暂停。PRE_APPLY 的 PASS 仍只是 SYNTHETIC 合同桩，没有算法质量证明。

## 环境与复现

实测 Windows / PowerShell，`C:\Users\ASUS\AppData\Local\Programs\Python\Python39\python.exe`，Python 3.9.13，Pydantic 2.12.5，无新依赖。正式环境记录见 [environment.stdout.txt](../evidence/A02/execution/final/environment.stdout.txt)。初始 Python editable 安装指向另一 C01 工作树，所有正式子进程均显式指定本工作树 `src`；环境记录确认实际导入本树。

在交付 checkout 根目录执行，输出路径必须不存在；下面路径可换成新的本地临时目录：

```powershell
$env:PYTHONPATH = "$PWD\src"
python -m unittest discover -s tests -p 'test_a02*.py' -v
python -m unittest discover -s tests -p 'test_contracts*.py' -v
python examples/a02/run.py --output "$env:TEMP/a02-review-normal-new"
python examples/a02/run.py --output "$env:TEMP/a02-review-absent-new" --fault not_applied
python examples/a02/run.py --output "$env:TEMP/a02-review-unknown-new" --fault lost_response
python examples/a02/run.py --output "$env:TEMP/a02-review-conflict-new" --fault contradictory
python examples/a02/run.py --output "$env:TEMP/a02-review-second-new" --fault lost_response --fault-index 1
python examples/a02/run.py --input tests/fixtures/a02/choice/input.json --output "$env:TEMP/a02-review-choice-new"
python examples/a02/run.py --input tests/fixtures/a02/exceptions/input.json --output "$env:TEMP/a02-review-exceptions-new"
python -m annotation.contracts validate "$env:TEMP/a02-review-normal-new/final.json"
```

正式证据命令（已在上述代码提交上执行，退出 0）：

```powershell
python examples/a02/verify.py --output docs/evidence/A02/execution/final
```

该目录现已存在，复现时改为新的目录。复现器独立设置 PYTHONPATH，记录命令、退出码、stdout/stderr、代码文件 SHA256 和完整证据文件 SHA256；[manifest.json](../evidence/A02/execution/final/manifest.json) 是最终证据索引。实际结果：**44 项 A02 回归通过、70 项 C01 合同回归通过、10 个演示退出 0**。作者结果不是独立验收结论。

每个演示目录包含完整输入及相对资产、computed TARGET/ApplyPlan 的 `planned.json`、带动作结果的 `executed.json`、含演示批次的 `final.json`、独立 `target-state.json`、`action-log.json`、完整 `receipt-history.json` 和 `summary.json`。最终交换包在新位置通过 `load_bundle` 重新读取并校验全部资源字节。源输入不含 ApplyPlan 或 ExecutionReceipt；代码不读取 C01 的 expected.json，也不使用复制的 C01 占位 readback/proof-after 文件生成回执，效果证据来自本次模拟状态。

首次开发正常运行保存在 [execution/normal](../evidence/A02/execution/normal/summary.json)，先于最终代码冻结；仅保留历史，不用作正式交付复现依据。正式证据全部在 `execution/final/`。

## 故障实测

| 输入 / 故障 | 实际动作结果 | 目标题 / 框 | 处置及批次 |
|---|---|---|---|
| [正常](../evidence/A02/execution/final/cases/normal/summary.json) | APPLIED ×3 | 3 / 9 | POSTCHECK；CONTENT_PENDING；NOT_SUBMITTED |
| [独立 W 假设](../evidence/A02/execution/final/cases/choice/summary.json) | APPLIED ×3 | 3 / 11 | 只在 SYNTHETIC_ONLY / SIMULATED 生效 |
| [异常 / 跳过 / 未入图谱](../evidence/A02/execution/final/cases/exceptions/summary.json) | 无动作；NOT_EXECUTED | 0 / 0 | BLOCKED；4 题分母；NEEDS_REVIEW |
| [明确未生效](../evidence/A02/execution/final/cases/not-applied/summary.json) | NOT_APPLIED ×3 | 0 / 0 | 仅首动作派发；其余不派发并读回 ABSENT；RECHECK_TARGET；旧计划不可重放 |
| [保存后丢响应 / 读回](../evidence/A02/execution/final/cases/lost-response/summary.json) | UNKNOWN, NOT_APPLIED, NOT_APPLIED | 1 / 4 | PAUSE_RECONCILE；同书暂停；NEEDS_RECONCILIATION |
| [丢响应但可独立读回](../evidence/A02/execution/final/cases/response-lost-readable/summary.json) | APPLIED ×3 | 3 / 9 | TIMEOUT 响应不决定结果；完整读回支持 MATCH |
| [矛盾读回](../evidence/A02/execution/final/cases/contradictory/summary.json) | UNKNOWN, NOT_APPLIED, NOT_APPLIED | 1 / 4 | 两次读回视图矛盾，保持暂停 |
| [部分生效](../evidence/A02/execution/final/cases/partial/summary.json) | UNKNOWN, NOT_APPLIED, NOT_APPLIED | 1 / 3 | 不满足 MATCH 或 ABSENT，保持暂停 |
| [读回失败](../evidence/A02/execution/final/cases/readback-failure/summary.json) | UNKNOWN, NOT_APPLIED, NOT_APPLIED | 1 / 4 | 保存响应 OK 仍不能确认效果 |
| [第二动作丢响应](../evidence/A02/execution/final/cases/lost-second/summary.json) | APPLIED, UNKNOWN, NOT_APPLIED | 2 / 7 | 第一动作预期变更被接受，第二动作未知后停止 |

三种结果均 `replay_allowed=false`。APPLIED 同时保存实际模拟平台题/框 ID、MATCH 证据和读回资源；NOT_APPLIED 有相关目标未变且无预期框的明确 ABSENT；UNKNOWN 为 INDETERMINATE / RECONCILE 并产生 SAVE_UNKNOWN issue，完整回执 PAUSE_RECONCILE。读回失败时额外读取真实模拟目标供独立核对，不能因此偷偷把原 UNKNOWN 改为 APPLIED。

## 任务条款执行结果

以下“通过”仅表示作者本地离线观察到预期结果。日志见 [A02 stderr](../evidence/A02/execution/final/a02-tests.stderr.txt) 及 [C01 stderr](../evidence/A02/execution/final/c01-tests.stderr.txt)。

| 条款 | 作者验证 | 依据 / 限制 |
|---|---|---|
| 1 自包含交换包、公共封签与写出、精确引用 | 通过 | load/validate/seal/write 公共入口；跨目录复制及最终资源重新读回 |
| 2 TARGET 真实判断 | 通过 | 不复制输入 TARGET；授权、映射、能力及版本、政策、覆盖分别计算并给 issue |
| 3 planner 纯计算、quality 不写、mock 变更 | 通过 | 输入序列化前后不变；只有 MockSession 修改目标；无浏览器/网络导入 |
| 4 两阶段 PASS / 精确图谱政策快照授权门 | 通过 | missing/wrong-stage/stale graph-policy/forged TARGET/changed authorization 反例关闭门 |
| 5 普通选择题假设及未支持投影 | 通过（有界） | 独立 W 仅人工 SYNTHETIC 假设；组合、父子、七选五、合 W 显式异常 |
| 6 计划及执行显式当前快照资格门 | 通过 | 计划后外部版本变化使执行失败，intent 和目标不变；执行不接受调用方假装当前 |
| 7 来源闭包及内部身份 | 通过 | 两目录同印刷 1；跨页原图、共享材料、所选答案；动作 ID 不取题号/题序/bbox |
| 8 相关事实与依赖顺序 | 通过 | CREATE 每题一动作；序列依赖；同目录 next_order 接受前序预期变化 |
| 9 空 / 非空目标新题 null | 通过 | 非空既有目标不按重复印刷号或顺序猜归属 |
| 10 已有题映射与目录命名空间 | 通过 | 合法显式 ID/实际题序/目录映射；缺失、错序、空串、null/错动作映射拒绝 |
| 11 UPDATE 基线与能力 | 通过（拒绝路径） | C01 校验旧回执/先前图谱/APPLIED/frame_update；A02 全部差量明确 UPDATE_UNSUPPORTED，不降级 CREATE |
| 12 真实模拟状态、追加日志、响应和读回分离 | 通过 | target-state/action-log/history 独立导出；回执根据实际读回计算，无预制 expected 回执 |
| 13 正常 / 未生效 / 保存后丢响应等 | 通过 | 10 组演示及独立实际目标；部分生效/矛盾/不可读保持 UNKNOWN |
| 14 三类证据和处置 | 通过 | MATCH+ID / ABSENT / INDETERMINATE；后者 PAUSE_RECONCILE |
| 15 全部不可重放、重查重规划、同书暂停 | 通过 | 旧计划再次执行 REPLAY_FORBIDDEN；NOT_APPLIED 可重查后新计划，非自动重发 |
| 16 完整 UNKNOWN 与换 ID/运行/题/范围 | 通过（同会话） | 调用方删减历史仍 BOOK_WRITE_PAUSED；回执副本不能清历史；另一书独立运行 |
| 17 内存边界及缺失解决合同 | 通过（边界声明） | 无解除 API、无 ReconciliationResult、无历史删除；跨进程恢复未实现 |
| 18 独立范围分母 | 通过 | 4 题包含 EXCEPTION / SKIPPED / 未入图谱项；不是只遍历可执行或成功题 |
| 19 保存 / 内容 / 提交区分 | 通过 | 框匹配可 PASS，内容仍 PENDING；提交 NOT_SUBMITTED；无 COMPLETED |
| 20 SYNTHETIC / SIMULATED / NOT_EXECUTED | 通过 | 公共模型和演示输出保持标记，无真实平台或算法验收声明 |

## 未执行、接口缺口与后续限制

未执行且未宣称通过：真实平台、OCR、算法准确率/漏错率、实际模型或人工效率/成本、B 侧合同确认、跨进程持久化、重启恢复、正式未知结果解除、最终提交。作者自测不代替独立验收；A03 仍须主调度决定是否释放。

模拟投影仅支持自由作答、明确独立 W 假设、每题 CREATE_FRAMES、尚无框的明确已有题。组合题及父子/共享平台题 ID 的语义投影、七选五、合并 W、已有框重建和全部 UPDATE 仍未实现，明确阻断。本次不需要共享代码变更。

**供 A03/主调度的最小接口缺口说明**：C01 只有 UNKNOWN receipt 与暂停资格门，没有可校验的 ReconciliationResult 或明确解决未决事项的产物。A02 不向共享合同添加私有字段。A03 应由指定负责人提出带精确原计划/回执/新观察快照与证据的 `RESOLVED_APPLIED / RESOLVED_NOT_APPLIED / STILL_UNKNOWN` 合同及持久 intent、书锁、恢复顺序；旧 UNKNOWN 必须保留，未有合法解决证据前不能恢复写入。该条仅为接口需求，未实施公共合同变更或跨侧确认。

`MockSession` 是单进程串行模拟会话，没有跨进程锁或持久事务；新进程/新实例会失去内存历史保护。证据落盘或后续验证在写后异常时，本会话 pending 保持暂停，但无法保证崩溃重启保护。同书另 scope 的实际执行接入与 source 版本迁移也需后续 runtime 设计；本次只证明跨 scope 不能绕过同书 UNKNOWN。

状态读回和日志/历史 API 返回防御性副本；这不是对任意 Python 私有属性篡改的安全边界。源码文件 SHA 是本次执行时字节记录，不替代 Git 提交身份；在自动 CRLF 转换的 checkout 应以确切提交及重新运行结果评估。

模型调用/已知模型费用为 0；真实运行成本未测。最终 worktree 在证据/报告提交后保持干净并冻结，等待独立对话和主调度复核。
