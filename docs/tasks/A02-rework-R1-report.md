# A02 R1 有界返修执行报告

日期：2026-10-16（Asia/Shanghai）。交付状态：**REVIEW**，等待原独立验收对话复验与主调度决定；未标 ACCEPTED、未集成、未推送、未释放 A03。

R1 修复了完整多书 ExchangeBundle 历史中的外书 UNKNOWN 误暂停当前书的问题。生产改动仅在 `MockSession.is_paused(book_id)` 加上回执自身 `book_id == book_id` 筛选。保留原书级 pending 判断、完整历史、UNKNOWN 和重放门；没有删除外书产物、拒绝合法混合包或放宽同书保护。

## 版本、范围和授权

| 项目 | 确切值 |
|---|---|
| 本轮任务 | A02 R1：跨书暂停隔离修复 |
| R1 基线 | `5c9285720c8628c5198bedeadfc9f6bc7826a914` |
| 原实现 / 原 base 与 workflow | `3fe492ce10bf93711ce57d305bc716f8b29345b7` / `39341c98d73c354d639f3beeb55429f55d0e9be5` |
| **R1 实现及被复现提交** | **`13ddf83083224ffafc17a4f57cf2c1a1a1ae02b2`** |
| 最终冻结交付提交 | 包含本报告及本轮证据的后续文档提交；完整 SHA 在本对话最终交付回执明确列出，生产/测试/复现代码与上行实现提交一致 |
| 分支 / 实现及 Git cwd | `codex/a02-planner-mock` / `C:\Users\ASUS\.codex\worktrees\a02-planner-mock\1800` |
| API / 交换 / 原样例 | `1.0.0-a-proposal` / `c01-exchange-1` / `c01-fixtures-1`、`a02-fixtures-1`；公共 API 和结构未改 |
| R1 样例 | `examples/a02/R1/scenarios.py` 在上述实现提交上派生的构造输入，全部 SYNTHETIC；内存执行 SIMULATED，诊断 NOT_EXECUTED |
| 本轮改动范围 | `src/annotation/delivery/mock/`、`tests/test_a02_r1.py`、`examples/a02/R1/`、`docs/evidence/A02/execution/R1/`、本报告 |

正式任务、独立验收、原最小反例、原观察和主调度复现均先只读，原字节复制到 [inputs/provenance.json](../evidence/A02/execution/R1/inputs/provenance.json) 所列新位置。未合并浮动主分支，未修改主目录调度文件或旧报告/证据。planner、targetcheck、contracts、公共政策、C01 样例、根依赖、父入口、source/geometry/runtime/B 模块均未修改。

## 修复前和修复后

修复前已重放冻结验收脚本；使用主目录 raw 导出副本的 10 个生产源码文件，并逐字核对 `5c928572` 的 Git blob。脚本退出 0 表示原缺陷断言成立：无本书 UNKNOWN / intent 的 NOT_EXECUTED 诊断后，本书 pause 错误变为 true；随后公共资格门通过的 READY / 3 动作被 BOOK_WRITE_PAUSED 拒绝，实际目标和日志不变。[修复前命令、身份与源码摘要](../evidence/A02/execution/R1/before/command-receipt.json)、[实际观察](../evidence/A02/execution/R1/before/counterexample/observations.json)。冻结验收脚本与原结果均未改写。

另把新增 R1 回归运行在同一旧生产源码上：`full_foreign_unknown_diagnostic_then_ready` 在两种书籍角色方向均失败，退出 1，定位 `FOREIGN_UNKNOWN_FALSELY_PAUSES_OTHER_BOOK`。[命令收据](../evidence/A02/execution/R1/before/r1-regression-command.json)、[失败 stdout/stderr](../evidence/A02/execution/R1/before/r1-regression.stderr.txt)。这证明新回归能够拒绝旧缺陷，而不是只运行一个不会触发该问题的成功输入。

修复后，两方向合法混合包的 NOT_EXECUTED 诊断均保留外书完整 UNKNOWN 链；当前书 pause 保持 false，随后 READY 三动作实际 APPLIED，独立目标读回为 3 题 / 9 框，动作日志、平台模拟 ID 和回执一致。完整历史包含诊断与执行两条，没有删除外书产物。[正向结果](../evidence/A02/execution/R1/after/matrix/mixed-diagnostic-forward-result.json)、[交换角色结果](../evidence/A02/execution/R1/after/matrix/mixed-diagnostic-swapped-result.json)、[最终独立目标/日志/历史](../evidence/A02/execution/R1/after/matrix/mixed-diagnostic-forward/final-state-log-history.json)。

| R1 任务回归组 | 作者离线结果与证据 |
|---|---|
| 多书包诊断 → READY，交换角色 | 两方向通过，NOT_EXECUTED 不误暂停，READY 实际 3 题 / 9 框；外书 UNKNOWN 原链仍在 |
| 同书换 action/run/question/scope、调用者省略历史 | 4 组候选均 BOOK_WRITE_PAUSED；目标、日志、完整历史逐字等值，未重复效果；[身份变更及三类旧计划](../evidence/A02/execution/R1/after/matrix/same-book-and-replay-result.json) |
| 另一书独立包及含外书 UNKNOWN 的混合包 | 两方向均可正常模拟；APPLIED、NOT_APPLIED、NOT_EXECUTED 历史均不产生误暂停；明确 ABSENT 后新检查/新计划成功 |
| 两书各有实际未决项 | 两方向分别保持本书暂停，调用者省略历史仍各自拒绝；每书实际 4 框和 UNKNOWN 保留；[双书未决](../evidence/A02/execution/R1/after/matrix/two-books-lost_response-forward-result.json) |
| 一书 APPLIED/NOT_APPLIED 不清另一书 UNKNOWN | 外书可继续自己的合法模拟，原未决书 pause 保持 true，原完整历史不变 |
| 同书仅有历史 UNKNOWN，无本会话 pending | NOT_EXECUTED 后 pause=true，0 intent；省略输入历史仍 BOOK_WRITE_PAUSED，证明筛选没有丢掉同书历史依据；[结果](../evidence/A02/execution/R1/after/matrix/same-book-history-only-result.json) |
| 三类旧计划不可重放、正常多动作、未派发 ABSENT | APPLIED/NOT_APPLIED 旧计划 REPLAY_FORBIDDEN；UNKNOWN 旧计划 BOOK_WRITE_PAUSED；明确未生效只派发首动作，其余独立读回 ABSENT；正常多动作仍 9 框 |

[16 场景总表](../evidence/A02/execution/R1/after/matrix/results.json) 含每项真实结果。所有多书交换包经公共资源/引用验证；构造器仅合并完全相同的注册表项，不过滤其他书的产物。每次采集的目标、动作日志、书级完整历史与响应/回执分别留档。

## 确切源码身份、环境与实际复现

实测 Python 3.9.13 / Pydantic 2.12.5，解释器 `C:\Users\ASUS\AppData\Local\Programs\Python\Python39\python.exe`。运行入口的 cwd 为上述任务工作树；正式测试/演示子进程 cwd 与导入路径固定到新 raw 源码导出 `docs/evidence/A02/execution/R1/source-13ddf830/`，没有使用别的 editable 源码。

Windows 现有 checkout 的部分 C01 Python 文件为 CRLF，因此本轮从指定实现提交 raw Git blob 导出 141 个必要代码/测试/资源文件，保持精确字节，不改全局 Git 设置。正式复现前后逐字验证其中 **19 个生产/测试/演示源码文件**，并记录实际四模块导入位置与摘要。[源码导出清单](../evidence/A02/execution/R1/source-13ddf830/source-export.json)、[正式身份绑定](../evidence/A02/execution/R1/after/source-binding.json)。

该导出目录没有 `.git`，其 `checkout_commit` 明确为 **null / unknown**；`declared_commit=13ddf830...` 来自外部明确指定并通过实际源码 Git blob 校验。新复现器确认 Git 顶层必须等于源码根才可报告 checkout 身份，绝不采用父仓库 HEAD。旧 `verify.py` 与旧清单元数据未改写，也未用于 R1 身份结论。

实际命令（均在任务工作树发起，实际 argv/cwd/退出码见 [顶层收据](../evidence/A02/execution/R1/top-level-commands.json) 及 [正式清单](../evidence/A02/execution/R1/after/manifest.json)）：

```powershell
python -B examples/a02/R1/export.py --repo "$PWD" `
  --commit 13ddf83083224ffafc17a4f57cf2c1a1a1ae02b2 `
  --output docs/evidence/A02/execution/R1/source-13ddf830
python -B docs/evidence/A02/execution/R1/source-13ddf830/examples/a02/R1/verify.py `
  --source-root docs/evidence/A02/execution/R1/source-13ddf830 `
  --source-commit 13ddf83083224ffafc17a4f57cf2c1a1a1ae02b2 `
  --identity-repo "$PWD" --output docs/evidence/A02/execution/R1/after
```

这些输出目录已存在，重跑须改为新目录。入口和参数说明见 [R1 README](../../examples/a02/R1/README.md)。最短工作树回归命令为：

```powershell
$env:PYTHONPATH = "$PWD\src"
python -B -m unittest discover -s tests -p 'test_a02*.py' -v
python -B -m unittest discover -s tests -p 'test_contracts*.py' -v
```

正式实际结果：

| 检查 | 退出码 | 实际观察 |
|---|---:|---|
| 原冻结最小反例 | 0 | 旧缺陷断言复现；这是失败证据 |
| 新 R1 定向回归 + 旧源码 | 1 | 两方向拒绝旧实现；这是预期失败证据 |
| A02 受影响套件 | 0 | **52 项通过**（原 44 + R1 新增 8）；[日志](../evidence/A02/execution/R1/after/a02-tests.stderr.txt) |
| C01 合同套件 | 0 | **70 项通过**；[日志](../evidence/A02/execution/R1/after/c01-tests.stderr.txt) |
| R1 真实内存场景 | 0 | **16 组通过**，完整输入、计划、回执、目标、日志、历史与错误保留 |
| 原有正常/故障演示 | 各 0 | **10 组通过**，最终交换包与资源重新加载；正常、选择假设、异常、ABSENT、丢响应/可读、矛盾、部分生效、读回失败、第二动作未知 |

R1 新测试首轮有一个作者构造器错误：复制了未引用的同名 `readback.json` 附带文件而产生资源冲突，尚未到达 mock。已改为复制输入中全部实际引用资源并校验字节一致；没有删减任何 EvidenceRecord 或 Artifact。该脚本错误已修正，正式 52/70 和矩阵均从冻结实现提交运行。

## 摘要、保留边界与交付状态

本轮完整证据与本报告 SHA256 统一列在 [sha256-manifest.json](../evidence/A02/execution/R1/sha256-manifest.json)，清单自身按约定不自引用。旧执行报告、旧证据和旧复现器保持原字节；交付检查覆盖允许路径、旧材料完整性、正式源码/证据摘要和全部新交换包资源重新读回。

N1 **保留**：EXCLUDED clue 没有明确的排除 region 关联字段，A02 仍可能保守拒绝未入题闭包的页眉 region；未按 bbox 相同猜排除规则，未放宽覆盖门。N2 **保留**：上游产物 SYNTHETIC 检查不是完整的 EvidenceRecord.mode 标签准入；故意把被引用证据改成 OBSERVED 的原边界未修。本轮新增样例与效果证据仍为 SYNTHETIC，未声称解决真实来源 S01、A01 的验收问题或 B 合同确认。

框保存、内容和提交继续区分：正常模拟框匹配后仍 `CONTENT_PENDING / PENDING / NOT_SUBMITTED`，没有 COMPLETED。全部 UPDATE、组合/父子、七选五与合并 W 仍是原有拒绝路径；没有扩大投影功能。

未实现、未执行或未验证：A03 持久 intent/跨进程书锁/重启恢复、正式 ReconciliationResult 和解暂停、真实平台/浏览器/凭据/OCR、B 算法准确率、最终内容正确性与人工最终提交。内存会话仍必须保持原实例，不能以新进程或删除 UNKNOWN 历史解锁。

平台动作、浏览器动作、凭据访问、OCR、模型调用及外部模型花费均为 **0**；真实运行成本未测。最终提交证据/报告后 worktree 干净并冻结，无待释放浏览器会话；只交回 REVIEW，等待原独立验收和主调度决定。
