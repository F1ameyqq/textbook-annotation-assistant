# C01 有界返修 R1 执行报告

日期：2026-10-16（Asia/Shanghai）。状态：**REVIEW**，等待原独立验收对话复验。此次为执行侧修复交付，不代替独立验收、不作 ACCEPTED 结论。

## 版本与改动范围

- 工作树：`C:\Users\ASUS\.codex\worktrees\c01-contracts\1800`；分支 `codex/c01-contracts`。
- 返修基线：`b8c4341d277d205dddfae22b26c245b646a1cea2`。
- 原 base_commit / workflow_commit：`30bc00cbaa3e40d78fd8d5cac98e81bd354763b2`。本轮沿用原调度规则及主工作区的 R1 附加任务单。
- 精确修复代码提交：`cb684f90a2cd7bd7064ce1f30b7d024a49389132`。仅改 `src/annotation/contracts/validation.py`、`docs/contracts-implementation-v1.md`，新增 `tests/test_contracts_platform_refs.py`；3 文件，266 行新增。
- 本报告单独以随后文档提交归档，最终回执给出交付 HEAD；该提交只增加本报告，不改上述被验代码。
- 合同版本仍为 `1.0.0-a-proposal`，交换版本 `c01-exchange-1`，样例版本 `c01-fixtures-1`。没有新增字段、修改公共类型或依赖；原固定样例、原 54 项测试及旧执行报告均未修改。

任务依据仅只读读取 `D:\1800\docs\tasks\C01-rework-R1.md`、`D:\1800\docs\tasks\C01-review-report.md` 及其证据。主工作区反例、验收报告、调度状态均未修改；没有切换或写入 `D:\1800` 主分支。

## 修复规则

1. **F1 快照内部闭合**：平台题目的 `directory_id` 必须存在于同一快照的 `directories`，错误精确指向标量字段；快照目录集合同时拒绝重复 ID。
2. **F2 动作目标闭合**：非 null `target.platform_question_id` 必须存在于计划绑定快照，并等于其内部目标题的 `external_refs.platform_question_id`；不允许用动作 null 绕过已有平台映射。
3. 当前计划图谱的非 null 平台题目映射也须存在于其快照；已有非 null `platform_order` 必须匹配该平台 ID 对应的题序。不会使用印刷题号或题序推断身份。
4. 新题的“图谱平台映射 null＋动作平台目标 null”继续合法，快照可以为空，也可以包含其他题目。非 null 动作指向存在平台题但内部映射为 null 时，当前字段无法核实归属，本轮提案要求先显式填写既有 `external_refs` 并重查，返回 `PLATFORM_MAPPING_REQUIRED`，不猜默认对应。

上述第 4 点的保守资格规则已补入[实现说明](../contracts-implementation-v1.md)，保持 A 内部提案，未表述为双方已共同确认。内部目录与平台目录没有跨命名空间映射字段，不比较它们的 ID。组合父子投影仍未决，本轮不擅定一对一映射或全局唯一题序；父子共享明确平台映射的合同正例继续通过，不代表已验证真实平台分组能力。

## 原始反例前后结果

两份原始完整反例均在返修前、指定基线上先复现：公开检查脚本输出 `bundle_valid=true, resources_verified=true, eligible=true`，退出 0，确认首轮漏拒绝。随后在**修复提交 cb684f90a2cd7bd7064ce1f30b7d024a49389132** 再运行原始文件，未复制改写反例：

| 反例 | 修复前 | 修复后 CLI / 公开检查脚本 | 修复后 code 与精确 path |
|---|---|---|---|
| F1 snapshot_question_missing_directory | 错误放行，eligible=true | 均退出 1，valid/eligible=false | `MISSING_REFERENCE`，`$.artifacts[5].payload.questions[0].directory_id` |
| F2 action_missing_platform_question | 错误放行，eligible=true | 均退出 1，valid/eligible=false | `MISSING_REFERENCE`，`$.artifacts[8].payload.actions[0].target.platform_question_id` |

公开 `load_bundle` 和 `validate_bundle(..., asset_root=原反例目录)` 也分别拒绝相同字段。默认 CLI 启用完整资源校验，没有使用 `--structure-only`。两个输入修改前后的 SHA-256 保持：

```text
F1 91315dde2e4cdefdb0069301047c0e02f35123ca84439c1030ca19a968710101
F2 d0bc9967abae687a450975d25043183563f3226676c6c003b46e4ec96e55366d
```

## 复现命令与实际结果

实际环境：Python **3.9.13**、Pydantic **2.12.5**，原 editable 安装导入路径确认为本工作树 `src\annotation\contracts\__init__.py`。没有重装依赖或更改全局设置。

```powershell
Set-Location 'C:\Users\ASUS\.codex\worktrees\c01-contracts\1800'
python -B -m unittest discover -s tests -p 'test_contracts_platform_refs.py' -v
python -B -m unittest discover -s tests -p 'test_contracts*.py' -v
```

新增 16 项定向测试通过；最后全量复跑为原 54 项加新增 16 项：

```text
----------------------------------------------------------------------
Ran 70 tests in 9.636s

OK
exit=0; skipped=0
```

新增测试对合法输入重新封签全部依赖，并同步旧/新图谱的外部映射，保证 patch 派生仍合法；错误不会被旧摘要或 patch 差异抢先遮蔽。负例精确断言 `ContractError.issues` 的 code 和 path，且再次通过 `assert_plan_ready` 验证资格 API 不放行。

- 正例：快照题目引用存在目录；动作指向已有题且显式映射一致；已知题序一致/未知题序 null；新题 null 目标在空/非空快照中均通过；内部目录与平台目录不同仍合法；父子共享显式平台映射不被新增一对一规则误拦。
- 负例：F1/F2 等价变异；动作指向另一存在题；无内部映射却指定已有目标；已有映射改用 null；图谱映射悬空；已知题序冲突；空字符串不充当新题 null。完整复制资源后的默认 loader/CLI 也验证 F1/F2 拒绝，未依赖主工作区的绝对路径作为提交测试前提。

原始两份反例的独立复现（以下四条命令各自**预期退出 1**）：

```powershell
python -B -m annotation.contracts validate D:\1800\docs\evidence\C01\review\counterexamples\snapshot_question_missing_directory\input.json
python -B -m annotation.contracts validate D:\1800\docs\evidence\C01\review\counterexamples\action_missing_platform_question\input.json
python -B D:\1800\docs\evidence\C01\review\scripts\check_counterexample.py --tree C:\Users\ASUS\.codex\worktrees\c01-contracts\1800 --input D:\1800\docs\evidence\C01\review\counterexamples\snapshot_question_missing_directory\input.json
python -B D:\1800\docs\evidence\C01\review\scripts\check_counterexample.py --tree C:\Users\ASUS\.codex\worktrees\c01-contracts\1800 --input D:\1800\docs\evidence\C01\review\counterexamples\action_missing_platform_question\input.json
```

四组跨目录消费：分别复制 normal/exception/unknown/choice-assumption 完整目录到系统临时路径（含空格），移除子进程 PYTHONPATH，在另一 cwd 使用已安装公共包运行 `consume.py --roundtrip`，再对写出目录运行消费者；**4/4 EXACT_MATCH**。批次状态仍分别是 READY_FOR_SUBMISSION、NEEDS_REVIEW、NEEDS_RECONCILIATION、READY_FOR_SUBMISSION，UNKNOWN 保留原资格拦截。`git diff --check` 通过；本轮未重生成或修改旧样例。

## 未解决项与交接

F1/F2 及本轮关联字段的执行侧负例均观察到预期拒绝，没有已知剩余 R1 阻塞。首轮独立验收的 80 项结果保持原始记录，未改成“已通过”；原独立验收对话将在新交付版本复验，主调度再决定验收与集成。

原合同中的 W 政策、B 采用、组合父子实际平台投影、跨目录映射及其他未共同确认项仍未决；此轮没有新增字段解决这些业务语义。检查只核对给定快照与显式映射的闭合/一致性，不能证明快照是实时平台状态或显式映射在业务上真实正确，真实目标检查仍由后续适配器和 quality 负责。

此次完全离线：未启动浏览器/profile、未读取凭据、无模型调用/费用、未重放 A05 或题 22、未进行平台写入/提交。没有执行器、A03 恢复、OCR 或 B 算法验收；未推送、未集成、未管理 B、未向其他对话发消息。交付后工作树保持干净，冻结代码版本，状态回 REVIEW，等待定向复验。
