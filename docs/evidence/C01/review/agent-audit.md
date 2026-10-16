# C01 冻结合同专项审计

日期：2026-10-16（Asia/Shanghai）。建议主验收结论：**REWORK**，依据两项已复现的引用漏拒绝；本专项不代替主报告的完整范围验收。

被验交付 HEAD：`b8c4341d277d205dddfae22b26c245b646a1cea2`；实现提交：`4660e8e4120af1b8550c2e0ee3dd02593aa38aac`；基线：`30bc00cbaa3e40d78fd8d5cac98e81bd354763b2`。读取对象为 `D:\1800\.local\stages\C01-review\frozen\tree`，未修改执行树、导出树、协调状态或主报告。

## 来源、环境和证据

- `frozen/delivery-manifest.json` 的 82 个文件全部按字节 SHA-256 复核匹配，manifest.commit 与被验 HEAD 一致。
- Python 3.9.13，Pydantic 2.12.5；通过 `-B` 与 `sys.dont_write_bytecode` 禁止向源树写 bytecode。
- 独立自造包没有读取作者固定样例。所有输入和证据均明确 SYNTHETIC；创建实际 PGM、文本和 JSON 字节，验证原图头部、资源存在和 SHA-256。正式反例 `resources_verified=true`，不是跳过资源检查后的结果。
- 修改语义后通过公共 `seal_artifact` 重算所有受影响摘要与下游依赖引用。公开 `validate_bundle`、`assert_plan_ready` 和 CLI 均直接调用冻结树代码，未修改实现来制造结果。
- 主次证据：`agent-probes/results.json`、`agent-probes/stdout.jsonl`；UNKNOWN 澄清以更新后的 `agent-probes/shadow-followup/results.json` 和 `stdout.jsonl` 为准。

冻结源文件摘要：

| 文件 | SHA-256 |
|---|---|
| models.py | `592601b8049980c38e9fb837b7e47e90352409da5562b1b086a208904eb8e1ec` |
| validation.py | `779d61270e62ced51642727cc9ed5d94ab53dbcb14394633f227d5489f1f3908` |
| integrity.py | `378cc52d6b701011b6d074e5cbed35811bf3d927e5a3bbeb08f6acef04ee45a0` |
| docs/contracts-implementation-v1.md | `79ea14a5e22e4e48c19bce48beb48e098b340d48cb3bcf4cf247a7196842c142` |

导出仅含交付改动文件，未包含原始架构/任务文档，因此语义依据另读主目录现有文件并绑定摘要：`docs/contracts-v1.md`=`8fdc31e5b6671f4995ea95b3271b916d784c300336a9ee1420e79dfb3ccfcaae`，`docs/architecture.md`=`c2b5dce8b862d6d274d87ce75cbbb844d75b12e6c3e6885884984b0b5c321b5f`，`docs/tasks/C01-contracts-implementation.md`=`86b45bb6dd98d32c469033f37c3df64e91c2f03c1e420b99a2405ee6a2527e1e`。

## 阻断项 1：PlatformSnapshot 的题目可引用不存在的目录

分类：**ACCEPTED_INVALID / P2**。

最小包：[minimal-input.json](D:/1800/.local/stages/C01-review/agent-probes/snapshot-question-missing-directory/minimal-input.json)，仅 1 个 PlatformSnapshot 产物、1 份政策、1 条带真实本地资源的模拟证据。`payload.directories=["pd"]`，但 `payload.questions[0].directory_id="missing-directory"`。快照各摘要均正确。

实际结果：CLI 退出 0，`valid=true/resources_verified=true/artifacts=1`。同样语义放在完整自造链的 `input.json` 时，`validate_bundle` 和 `assert_plan_ready` 均放行。

位置：[validation.py:638](D:/1800/.local/stages/C01-review/frozen/tree/src/annotation/contracts/validation.py:638) 到 647；代码检查能力、题目和框 ID 唯一性及 frame→question，没有检查 question→directory。`models.py:280-283` 仅规定字符串结构。

合同依据：`docs/contracts-v1.md:33` 将已有目录/题目/框定义为快照对象；任务要求缺失实体引用可定位并拒绝（`docs/tasks/C01-contracts-implementation.md:16,28`）；实施说明声称全部引用由公共验证入口校验（冻结实现文档第 39、54 行）。这项属于合同引用完整性，不要求真实平台调用。

修复建议：检查 snapshot.directories 唯一性；每个 PlatformQuestion.directory_id 必须属于该快照平台目录集合，错误位置定位到 `.questions[i].directory_id`。平台目录命名空间应与 SourceBundle 内部目录保持区分，不要求两者字符串相同。

## 阻断项 2：动作可绑定快照中不存在的平台题目 ID

分类：**ACCEPTED_INVALID / P2**。

最小包：[minimal-input.json](D:/1800/.local/stages/C01-review/agent-probes/action-missing-platform-question/minimal-input.json)，7 个产物组成 Source→Evidence→Graph→Snapshot→两份 PASS→READY Plan。图谱 external_refs.platform_question_id 与快照均为 `pq`，动作却声明 `target.platform_question_id="missing-question"`。内部 question_id、target_id、scope、两份报告、版本和全部摘要均一致。

实际结果：CLI 退出 0，`valid=true/resources_verified=true/artifacts=7`；完整自造链 `validate_bundle` 和 `assert_plan_ready` 均放行，证明不是仅 CLI 结构层遗漏。

位置：[validation.py:497](D:/1800/.local/stages/C01-review/frozen/tree/src/annotation/contracts/validation.py:497) 到 509，只检查内部 question_id、来源实体归属及整体 target_id；没有核对非空 target.platform_question_id。

合同依据：Action.target 和绑定目标快照用于计划前置条件及目标状态检查（`docs/contracts-v1.md:108,114-122`）；任务要求缺失实体引用不能校验成可执行计划（任务第 19、28 行）。这是对当前计划声明引用的检查，不涉及 executor。

修复建议：非空 action.target.platform_question_id 必须存在于所绑定快照；已有声明内部↔平台关联时校验一致性。若操作面向尚不存在的新平台题目，应使用明确的未分配表示及操作前置条件，不能容许任意非空悬空 ID。

## 非阻断澄清：UNKNOWN 与历史/当前 BatchReport

主复核后撤回初轮 raw results 中 shadow UNKNOWN 的 `ACCEPTED_INVALID` 阻断标签。初轮记录保留原始输出便于审计；本节及 `shadow-followup/results.json` 的 `NONBLOCKING_CLARIFICATION` 是最终专项解释。

更新后用不同 plan_id/action_id 构造后续 UNKNOWN，避免把同一动作的两份回执误当合法重放证据：

| 场景 | 实际结果 | 判断 |
|---|---|---|
| 12:00 的不可变历史 READY 批次，另附 12:01 同书同 scope 的 UNKNOWN | validate/CLI 退出 0 | 历史产物可与后续事实共存，不能单凭此判为失败 |
| 历史 COMPLETED 批次，后续新动作 UNKNOWN | validate/CLI 退出 0 | 同上；不能追溯抹掉既有提交事实 |
| 12:02 新 revision=2 的批次显式将 UNKNOWN 回执列入 input_refs，主要 payload.receipt 仍指旧 APPLIED，仍 READY | validate/CLI 退出 0 | 当前汇总语义存在待明确之处；尚无 current_batch 标识/专门汇总验证上下文，列澄清而非第三个阻断项 |
| 在包含后续 UNKNOWN 的完整交换包对任意计划调用 assert_plan_ready | 拒绝，`BOOK_WRITE_PAUSED` | 书级写入门禁正确，没有证明可真实重放 |

证据：[shadow-followup/results.json](D:/1800/.local/stages/C01-review/agent-probes/shadow-followup/results.json) 及其各场景 `minimal-input.json`，包含各 13 个自造产物及实际资源。

定位：`validation.py:597-609` 的 Batch 检查只观察 payload.receipt；`validation.py:684-688` 的资格检查则遍历同书所有 UNKNOWN 回执。冻结实现文档第 88 行无条件表述“BatchReport 必须 NEEDS_RECONCILIATION”，第 54 行同时允许旧修订共存、不暗中取最大 revision；两句应明确历史快照与当前 runtime 汇总视图的适用边界。

建议：限定文档中 Batch 的暂停要求为引用该未决动作/承担当前汇总职责的报告；如需要校验当前汇总，明确输入完整性、当前报告身份和未知依赖处理规则，再由 runtime/后续任务提供当前日志与锁状态。不要为了让所有历史 Batch 一律失败而破坏不可变产物共存，也不要用修改措辞放开现有 assert_plan_ready 的 UNKNOWN 门禁。

## 几何解释待定项

`noninvertible-transform-original-box-already-bound` 被接受。该包已明确提供合法、尺寸/摘要正确绑定的原图 bbox，只将处理图变换 invertible 改为 false；无法据此证明现有原图框需要经不可靠回投才能得到。因此本项为 **INTERPRETATION_REQUIRED，非阻断**。C01 保存变换合同、不实现回投算法（冻结实现文档第 64 行）；只有生产者明确声明原框依赖无法准确回投时，才应要求异常路径，不能扩大为 A01 几何算法验收。

## 正向和拒绝对照

- 最小正常链公开资格检查通过，资源字节检查通过。
- 快照 frame 指向不存在的 platform question：拒绝，`MISSING_REFERENCE`。
- Plan 绑定新 graph revision，仍使用旧 graph 的两份检查：拒绝，`VERSION_CONFLICT`，且输入声明及摘要已正确更新。
- Patch 精确派生结果：接受；丢失声明 patch 变更：拒绝，`PATCH_DERIVATION`。
- 同书 UNKNOWN 的公开资格门：拒绝，`BOOK_WRITE_PAUSED`。

## 复现命令

在普通 PowerShell 中运行自造探测（只写指定审计目录）：

```powershell
python -B D:\1800\.local\stages\C01-review\agent-probes.py --tree D:\1800\.local\stages\C01-review\frozen\tree --output-dir D:\1800\.local\stages\C01-review\agent-probes --frozen-commit b8c4341d277d205dddfae22b26c245b646a1cea2 --manifest D:\1800\.local\stages\C01-review\frozen\delivery-manifest.json
```

当前脚本的 UNKNOWN 标签和不同 action/plan 构造已经过专项澄清修订，因此再次运行时这些条目应为 NONBLOCKING_CLARIFICATION；原始初轮输出仍保存在主目录，后续修订证据单独保存在 shadow-followup。若只复跑 UNKNOWN，不重复两项主引用检查：

```powershell
python -B D:\1800\.local\stages\C01-review\agent-probes.py --tree D:\1800\.local\stages\C01-review\frozen\tree --output-dir D:\1800\.local\stages\C01-review\agent-probes\shadow-followup --frozen-commit b8c4341d277d205dddfae22b26c245b646a1cea2 --manifest D:\1800\.local\stages\C01-review\frozen\delivery-manifest.json --only shadow-unknown-batch-ready shadow-unknown-batch-completed shadow-unknown-declared-current-summary shadow-unknown-eligibility-control
```

独立 CLI 最小复现，PYTHONPATH 仅用于本 PowerShell 进程：

```powershell
$env:PYTHONPATH = 'D:\1800\.local\stages\C01-review\frozen\tree\src'
python -B -m annotation.contracts validate D:\1800\.local\stages\C01-review\agent-probes\snapshot-question-missing-directory\minimal-input.json
python -B -m annotation.contracts validate D:\1800\.local\stages\C01-review\agent-probes\action-missing-platform-question\minimal-input.json
```

两条当前均错误退出 0；修复后应非零并定位具体悬空引用。各最小包目录保存对应 cli-stdout.txt/cli-stderr.txt；执行资格放行的证据保存在最初 results.json 与 stdout.jsonl。

本专项未运行平台浏览器、未读取凭据、未调用付费模型、未重放线上写入，未声称算法、真实保存、真实恢复或 B 接口采用通过。
