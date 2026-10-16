# C01 R1 独立复验报告

日期：2026-10-16（Asia/Shanghai）。结论：**ACCEPTED（A 内部离线合同实现与固定样例）**。首轮 F1/F2 已在原始未改输入上正确拒绝；R1 未发现剩余阻断项。此结论供主调度复核，不自行集成或释放下游，不表示 B 已确认接口或真实平台/算法/恢复通过。

## 精确版本与范围

- 被验交付 HEAD：`4e42668ab28eda37a37285285d2f6c595d3bba12`；修复代码：`cb684f90a2cd7bd7064ce1f30b7d024a49389132`。
- R1 基线：`b8c4341d277d205dddfae22b26c245b646a1cea2`；原 base_commit / workflow_commit：`30bc00cbaa3e40d78fd8d5cac98e81bd354763b2`。
- 执行工作树：`C:\Users\ASUS\.codex\worktrees\c01-contracts\1800`，分支 `codex/c01-contracts`。在执行 completed、HEAD/clean 核对后，以 Git archive 导出到 `D:\1800\.local\stages\C01-review-R1\tree`；所有测试写入新的 R1 临时目录。
- R1 相比首轮仅 4 文件：`validation.py`、实现说明、`tests/test_contracts_platform_refs.py`、R1 执行报告；代码提交到交付 HEAD 之间仅新增执行报告。公共模型、依赖、固定样例及原 54 项测试未改。
- 84 个完整交付文件及其字节数/SHA-256、4 文件差异和 archive SHA-256 见 [delivery-manifest.json](../evidence/C01/review-R1/delivery-manifest.json)。原报告与旧正式证据 **161 文件原样保护**，核对见 [final-verification.json](../evidence/C01/review-R1/final-verification.json)。

实际环境 Python **3.9.13**、Pydantic **2.12.5**、setuptools **82.0.0**。离线构建安装 annotation-contracts **0.1.0** 到 R1 目录，在另一个 cwd 确认导入的是该安装副本，见 [安装来源](../evidence/C01/review-R1/checks/installed-provenance.stdout.txt)。合同仍为 `1.0.0-a-proposal`，交换 `c01-exchange-1`，固定样例 `c01-fixtures-1`。

## 原始失败输入复验

两份原始输入未复制改写后再测试，直接读取首轮正式 evidence；摘要与返修任务单完全一致：

| 输入 | 原始文件 SHA-256 |
|---|---|
| F1 snapshot_question_missing_directory | `91315dde2e4cdefdb0069301047c0e02f35123ca84439c1030ca19a968710101` |
| F2 action_missing_platform_question | `d0bc9967abae687a450975d25043183563f3226676c6c003b46e4ec96e55366d` |

默认完整资源校验 CLI 均退出 **1**；`validate_bundle`、默认 `load_bundle`、`assert_plan_ready` 共 **6/6** 检查也均拒绝，code 均为 `MISSING_REFERENCE`：

- F1：`$.artifacts[5].payload.questions[0].directory_id`。
- F2：`$.artifacts[8].payload.actions[0].target.platform_question_id`。

拒绝来自对应悬空引用，未被坏摘要或其他无关约束遮蔽。原始反例资源未改，CLI 未使用 `--structure-only`。详见 [公开 API 结果](../evidence/C01/review-R1/original-api-results.json)、[F1 CLI stderr](../evidence/C01/review-R1/checks/original-cli-snapshot_question_missing_directory.stderr.txt)、[F2 CLI stderr](../evidence/C01/review-R1/checks/original-cli-action_missing_platform_question.stderr.txt)。首轮错误放行的报告和输出保留在原位置，没有改写成通过。

## 实际检查结果

| 检查 | 结果 |
|---|---|
| 冻结提交交付测试 | **70/70 通过，无跳过**；原 54 项及 R1 新增 16 项，9.586 秒。 |
| 原独立 80 项矩阵 | **80/80 通过**；未改矩阵预期，F1/F2 由漏拒绝转为正确拒绝。 |
| 独立自造 R1 映射场景 | **22/22 符合预期**：12 合法、10 非法；公开校验、资格 API、CLI 分别检查。 |
| 原始 F1/F2 | 2 个 CLI 及 6 个 API 检查全部按字段拒绝，输入摘要不变。 |
| normal / exception / unknown / choice-assumption | **4/4 EXACT_MATCH**；完整复制资源至含空格目录，在其他 cwd 用安装包消费、写新目录再读回。 |
| 两份 PASS、UNKNOWN、完成状态、摘要、几何、路径、patch | 相关原测试和 80 项矩阵均通过；同书 UNKNOWN 资格仍关闭，目标快照变化仍使旧计划失效。 |
| 范围与文档 | R1 仅约定 4 文件，未改公共类型或样例；Git diff check 和本地链接检查通过。 |
| 真实平台、OCR、识别/组题、自动恢复、B 采用 | **未测，不属本轮合同复验**。 |

这些集合有重叠，不相加为单一测试总数。[交付测试输出](../evidence/C01/review-R1/checks/delivered-unittest.stderr.txt)、[原矩阵逐项结果](../evidence/C01/review-R1/original-matrix-results.json)、[实际命令/退出码](../evidence/C01/review-R1/checks/commands.json)与[独立专项结果](../evidence/C01/review-R1/agent-r1/results.json)保存完整证据。

## 新规则与合法边界

独立专项未读取作者固定样例构造输入；每个场景均自造完整闭合产物及实际 PGM/文本/JSON 资源，重新封签摘要和依赖，启用资源字节校验。详见 [专项审计](../evidence/C01/review-R1/agent-r1-audit.md)，逐场景 input、资源和 stdout/stderr 在其同级 `agent-r1/`。

- **正确接受**：存在目标且映射一致；已知一致题序、未知题序 null；空/非空快照中的新题 null；多个新题 null 并存；内部目录与平台目录不同。
- **正确拒绝**：悬空快照目录、重复目录 ID、悬空动作平台 ID、悬空图谱映射、指向另一已存在目标、非空目标但缺显式映射、已有映射改用 null、已知题序冲突、空字符串冒充未分配目标。
- **没有新增一对一投影假设**：无父子关系的多个内部题、组合父子、不同内部目录题均可共享同一显式平台 ID；同目录及不同平台目录的重复题序均通过。代码只核对明确 ID 的引用与已记录题序，没有要求映射值或题序唯一。

源码复核与独立场景一致：F1 检查同一快照目录集合；F2 核对动作非空平台 ID 存在且等于内部题已声明映射。两个字段均 null 的新题路径保留。非空动作而内部映射 null 时返回 `PLATFORM_MAPPING_REQUIRED`，要求先记录映射并重查；实现说明将此保守规则标为 A 内部提案，没有称为双方已共同确认。内部和平台目录没有映射字段，代码没有直接比较它们的 ID。

## 可复现命令

精确命令、cwd、退出码与 stdout/stderr 都在 commands.json。下面使用冻结导出，当前 PowerShell 进程指定公共包路径：

```powershell
$c01R1Tree = 'D:\1800\.local\stages\C01-review-R1\tree'
$env:PYTHONPATH = "$c01R1Tree\src"
$env:PYTHONDONTWRITEBYTECODE = '1'
python -B -m unittest discover -s "$c01R1Tree\tests" -p 'test_contracts*.py' -v
python -B 'D:\1800\docs\evidence\C01\review-R1\scripts\verify_originals.py' --tree $c01R1Tree
```

原始 CLI 反例两条命令均应退出 1 并显示上面的精确字段：

```powershell
python -B -m annotation.contracts validate 'D:\1800\docs\evidence\C01\review\counterexamples\snapshot_question_missing_directory\input.json'
python -B -m annotation.contracts validate 'D:\1800\docs\evidence\C01\review\counterexamples\action_missing_platform_question\input.json'
```

复跑原矩阵及独立 R1 专项须选择新的 output，保留既有证据：

```powershell
python -B 'D:\1800\docs\evidence\C01\review-R1\scripts\run_independent_review.py' --tree $c01R1Tree --output 'D:\1800\.local\stages\C01-review-R1\reproduce-matrix-new'
python -B 'D:\1800\docs\evidence\C01\review-R1\scripts\agent-r1-probes.py' --tree $c01R1Tree --output-dir 'D:\1800\.local\stages\C01-review-R1\reproduce-agent-new' --frozen-commit 4e42668ab28eda37a37285285d2f6c595d3bba12 --manifest 'D:\1800\docs\evidence\C01\review-R1\delivery-manifest.json'
```

两条退出 0，分别得到 `80/80` 和 `22/22`。交付各文件摘要、独立场景证据摘要及正式证据目录摘要可用于复核被验版本和原始输入。

## 限制与交接

本次接受范围是 A 内部离线合同及固定样例；显式映射的业务真实性、快照实时性和真实目标检查仍由后续平台适配/quality 验证。共享映射正例只说明合同未误加限制，不证明平台实际支持相应投影。W 独立/合并、B 接口确认、跨语言数字规范及首轮记录的当前/历史批次汇总澄清仍保持未决，R1 未冒充解决。

执行工作树最终 HEAD 不变且干净；原报告与旧 evidence 161 文件逐字节保持不变。未改实现、协调状态或他人文件；未启动浏览器、读取凭据、重放线上写入或调用付费模型，调用/费用为 0。**尚未集成，不自行释放 A01/A02/A04**；主调度复核并完成集成检查后决定下游安排。
