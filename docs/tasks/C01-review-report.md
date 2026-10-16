# C01 独立验收报告

日期：2026-10-16（Asia/Shanghai）。结论：**REWORK**。A 侧内部合同实现尚不能验收通过；两处悬空平台引用在完整资源校验及执行资格检查后仍被放行。主调度负责复核、定向返修、集成和下游释放；本报告不修改调度状态，不替 B 确认接口。

## 被验版本与验收方法

- base_commit / workflow_commit：`30bc00cbaa3e40d78fd8d5cac98e81bd354763b2`。
- 交付 HEAD：`b8c4341d277d205dddfae22b26c245b646a1cea2`；实现与样例提交：`4660e8e4120af1b8550c2e0ee3dd02593aa38aac`。两者之间仅新增 `docs/tasks/C01-execution-report.md`。
- 分支：`codex/c01-contracts`；执行工作树：`C:\Users\ASUS\.codex\worktrees\c01-contracts\1800`。执行 turn completed 后才正式冻结；验收前后 HEAD 相同、工作树干净。
- 合同 `1.0.0-a-proposal`、交换 `c01-exchange-1`、样例 `c01-fixtures-1`。82 个交付文件均在任务允许范围，逐文件字节数与 SHA-256 见 [delivery-manifest.json](../evidence/C01/review/delivery-manifest.json)。
- 只读执行工作树，以 Git archive 导出上述 HEAD 到 `D:\1800\.local\stages\C01-review\frozen\tree`。安装、测试、资源复制与变异输入均在验收临时目录；没有修改实现来制造通过。
- 实际环境 Python **3.9.13**、Pydantic **2.12.5**、setuptools **82.0.0**；离线构建安装 annotation-contracts **0.1.0** 到验收目录，确认跨 cwd 导入的是该安装副本。见 [安装来源输出](../evidence/C01/review/checks/installed-provenance.stdout.txt)。

提交导出是验收权威。执行工作树有 11 个文本文件为 CRLF、Git blob 为 LF；仅统一 CRLF 后全部 82 文件字节一致，资源摘要无差异。工作树最终状态及两种文件摘要见 [最终核对](../evidence/C01/review/final-verification.json)，避免混用工作区字节与提交字节。

## 结果

原交付 unittest：**54/54 通过，无跳过**，复跑耗时 6.676 秒。独立补充检查最终 **80 项中 78 通过、2 项漏拒绝**。首次命令复现包含 16 项成功记录，随后新增两条引用闭合反例；这些检查有重叠，不累加为一个测试总数。见 [unittest 输出](../evidence/C01/review/checks/delivered-unittest.stderr.txt)、[精确命令及退出码](../evidence/C01/review/checks/commands.json)、[独立最终结果](../evidence/C01/review/independent-results.json)。

| 验收条款 | 结果及证据 |
|---|---|
| 九类公共类型、单一结构定义与 Schema | 通过。四组均含九类、12 个产物，Schema 与同一模型生成结果一致，无手写第二权威。 |
| normal / EXCEPTION / UNKNOWN 完整串联 | 通过。另有 choice-assumption；CLI 与公开消费者均精确匹配 expected，诊断 BLOCKED 不冒充可执行计划。 |
| 摘要、版本、kind、输入引用 | 已测负例通过；独立实现 canonical JSON 摘要、键顺序及无自指规则吻合。下面两项平台内部引用仍失败。 |
| 原图 asset / 尺寸 / 摘要、bbox | 通过。缺资产、尺寸/摘要不符、负数、零面积、倒序、越界、NaN/Infinity 均拒绝；右下边界等于原图宽高合法。 |
| 通用身份与平台映射分离 | 通过。重复印刷“1”在两个目录使用不同内部 ID；跨页、多框、共享材料保留。平台角色仅在映射及快照层。 |
| CheckReport 依据与两份 PASS | 通过。缺必需检查、失败项仍 PASS、证据悬空、覆盖造假、同一 PASS 充两份、图谱/政策版本冲突均拒绝。 |
| 当前目标及能力 | 通过已测项。明确的新快照使旧计划失效；UNKNOWN/缺证据/平台版本不符能力拒绝。同会话已验证方案不机械要求重启恢复。 |
| 平台目录与题目引用闭合 | **失败 F1**。快照题目可引用不存在的目录。 |
| 动作中的平台题目引用闭合 | **失败 F2**。动作可引用快照不存在的平台题目，执行资格仍通过。 |
| APPLIED / NOT_APPLIED / UNKNOWN | 主路径通过。缺读回、UNKNOWN 伪装 APPLIED、直接重放、普通重试、错误批次状态均拒绝；新计划 ID 不能绕过同书 UNKNOWN 资格门。 |
| submission / content / COMPLETED | 主路径通过。NOT_SUBMITTED、PENDING 内容、未通过框检查不能 COMPLETED；提交与内容分别保存。跨历史回执组合见下方澄清。 |
| Patch | 通过。精确基线正例、错 revision/hash、错实体/before、覆盖旧修订及对新基线误用旧 patch 均拒绝；交付回归亦覆盖派生修改丢失/夹带。 |
| 分母、异常/跳过与费用 | 通过。删减源范围分母被拒；异常组保留四题及 SKIPPED；未知账单不能用零代替。 |
| 相对路径、资源字节、跨目录消费 | 通过。危险路径拒绝，资源篡改被发现；四组复制至含空格目录，在其他 cwd 通过安装包消费和往返。交付的 Windows junction 反例复跑通过。 |
| 固定样例确定性 | 通过。从 Git 提交导出的 68 个样例/政策文件重生成后摘要均不变，包含样例 `.gitattributes`。 |
| 真实平台、OCR、算法、恢复、B 接受 | **未测且不属本次验收**。全部业务产物为 SYNTHETIC；没有浏览器、凭据、付费模型或线上写入。 |

## 必须修复 F1：快照题目所属目录不存在仍合法

最小变化：在 normal 包的 `artifacts[5].payload.questions` 增加：

```json
{"platform_question_id":"platform-question-review","directory_id":"platform-directory-not-present","platform_order":999}
```

该快照目录只有 `directory-a`、`directory-b`。全部产物摘要及依赖摘要已合法重算，正常资产原样保留。当前 `validate_bundle` / `load_bundle` / CLI 默认完整资源校验 / `assert_plan_ready` 全部放行。冻结源码 `src/annotation/contracts/validation.py:638` 仅核对重复题目/框及 frame→question，遗漏 question→directory。

完整可移植输入：[F1 input.json](../evidence/C01/review/counterexamples/snapshot_question_missing_directory/input.json)，同目录 `assets/` 齐全。实测 CLI 退出 0，stdout 为 `valid=true, resources_verified=true, artifacts=12`；资格返回 eligible。见 [完整实际结果](../evidence/C01/review/reference-failures.json)。

修复要求：快照目录 ID 集合与每个题目 `directory_id` 必须闭合，非法引用返回具体 JSON 字段位置。补充正常目录引用与悬空引用两种测试；如要支持未展开的外部目录，须显式表达其未决状态并阻断执行资格，不能将缺失引用当成已验证目标。

## 必须修复 F2：动作指定不存在的平台题目仍具执行资格

最小变化：normal 的首动作 `target.platform_question_id` 从 null 改为 `platform-question-not-present`；其绑定快照 `questions=[]`。全部摘要与下游依赖已合法重算，资源字节校验通过。当前公开校验及 `assert_plan_ready` 均接受。冻结源码 `src/annotation/contracts/validation.py:497` 核对内部 question/source ownership 及 target_id，没有核对非空 platform_question_id。

完整输入：[F2 input.json](../evidence/C01/review/counterexamples/action_missing_platform_question/input.json)。CLI 同样退出 0、报告资源已验证；资格仍为 eligible，见 [完整实际结果](../evidence/C01/review/reference-failures.json)。这会让消费者拿到看似满足两份 PASS、实则目标实体不存在的计划。

修复要求：动作中非空平台题目 ID 必须在计划绑定快照中存在，并核对它与内部目标及已有外部映射的关系；null 表达新题的合法流程应保留。补充存在目标、空目标新题、悬空目标与错误目标映射测试，不扩大为真实 executor 实现。

## 精确复现

以下使用交付提交的导出树。全部命令只读实现，例子读取公共 API；两条反例当前均输出 `bundle_valid=true, resources_verified=true, eligible=true`，属于预期拒绝没有发生：

```powershell
$c01Tree = 'D:\1800\.local\stages\C01-review\frozen\tree'
$c01Review = 'D:\1800\docs\evidence\C01\review'
python -B "$c01Review\scripts\check_counterexample.py" --tree $c01Tree --input "$c01Review\counterexamples\snapshot_question_missing_directory\input.json"
python -B "$c01Review\scripts\check_counterexample.py" --tree $c01Tree --input "$c01Review\counterexamples\action_missing_platform_question\input.json"
```

完整独立反例矩阵可以重新生成，output 必须选新目录（公开 writer 拒绝覆盖已有文件）：

```powershell
python -B 'D:\1800\docs\evidence\C01\review\scripts\run_independent_review.py' --tree 'D:\1800\.local\stages\C01-review\frozen\tree' --output 'D:\1800\.local\stages\C01-review\reproduce-new'
```

当前结果退出 1：`total=80, passed=78, failed=2`，失败仅 F1/F2 `ACCEPTED_INVALID`。其余语义变异重算摘要后测试，避免只被 stale hash 挡住；NaN/Infinity 验结构层。冻结导出可用 [freeze_delivery.py](../evidence/C01/review/scripts/freeze_delivery.py) 在对应干净交付 HEAD 重建；精确提交、所有交付文件摘要及 archive 摘要均在 delivery-manifest.json。

## 边界、澄清及收口

当前 W 独立/合并仍 UNRESOLVED；普通选择题正常例仅为 SYNTHETIC_ASSUMPTION，切为 PLATFORM 被拒。真实框保存来源说明与 OCR UNVERIFIED 分开。字段/能力新增、摘要的跨语言规则及 B 采用均为未共同确认提案。此次 A 内部复现不能表述为 B 已接受、平台保存成功、OCR 准确、自动恢复或产品验收。

专项复核另以不依赖作者固定样例的自造包复现 F1/F2：最小快照仅 1 产物、动作链 7 产物，资源字节检查与 CLI 均错误通过；详见 [专项审计](../evidence/C01/review/agent-audit.md) 和 [自造探测结果](../evidence/C01/review/agent-probes/results.json)。

crop_transform 的 invertible=false 并不单凭一个标志证明原图框不可靠；C01 没有几何回投算法，本次不以此制造阻断。历史 READY/COMPLETED 可以与后续 UNKNOWN 事实共存，不能据此追溯抹掉提交事实；同书写入资格仍正确返回 BOOK_WRITE_PAUSED。当前汇总报告显式依赖新 UNKNOWN、主要 receipt 仍引用旧 APPLIED 时的状态规则，列为**非阻断澄清**：实现说明应区分历史产物与当前 runtime 汇总职责。详见 [UNKNOWN 澄清证据](../evidence/C01/review/agent-probes/shadow-followup/results.json)，不计为第三个阻断项。

本次未切共享分支、未提交或推送文件、未修改执行实现、coordination 状态或他人改动。付费模型调用/费用 0；真实算法成本与人工效率未测。**未集成，不释放下游任务**；修复交付新的确切提交后，由主调度安排针对 F1/F2 的独立复验及相关回归。
