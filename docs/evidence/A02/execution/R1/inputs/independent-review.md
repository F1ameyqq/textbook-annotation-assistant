# A02 正式独立验收报告

日期：2026-10-16（Asia/Shanghai）。结论：**REWORK**。

被验冻结交付为 **`5c9285720c8628c5198bedeadfc9f6bc7826a914`**，实现提交为 `3fe492ce10bf93711ce57d305bc716f8b29345b7`，base/workflow 均为 `39341c98d73c354d639f3beeb55429f55d0e9be5`。本结论仅针对 A02 的离线计划、目标检查及当前内存模拟会话。发现一项确定的跨书隔离错误，须修复后复验；未集成，不能据此释放 A03。

## R1：其他书的 UNKNOWN 污染当前书暂停状态（P2，必须修复）

位置：冻结提交 `src/annotation/delivery/mock/__init__.py:47–50`，`MockSession.is_paused(book_id)`。

会话按书保存历史，但历史元素是包含全部产物的完整 ExchangeBundle。`is_paused` 遍历其中所有 ExecutionReceipt，没有筛选回执自身的 `book_id`。合法包中另一书的 UNKNOWN 因此会被当成本书的未决写入。

独立反例将 C01 的 `synthetic-book` UNKNOWN 链和 A02 的 `other-book` 输入合并，全部精确引用和资源通过公共验证。`other-book` 先消费无动作 BLOCKED 诊断计划，得到 NOT_EXECUTED 空结果回执。该书没有 UNKNOWN、没有 intent、目标未变，但 `is_paused('other-book')` 从 false 变为 true。随后重新独立计算出的 READY / 3 动作计划通过公共资格门并注册目标，仍在 mock 入口被 BOOK_WRITE_PAUSED 拒绝。

实际观察：

```text
initial_pause=false
diagnostic_execution_mode=NOT_EXECUTED
diagnostic_results=[]
own_unknown_receipts=[]
pause_after_diagnostic=true
fresh_readiness=READY
fresh_action_count=3
fresh_public_gate_passed=true
fresh_error=BOOK_WRITE_PAUSED
target_unchanged=true
action_log_empty=true
```

证据：[观察与错误](../evidence/A02/review/formal/counterexamples/crossbook/observations.json)、[合法诊断输入](../evidence/A02/review/formal/counterexamples/crossbook/blocked-input.json)、[诊断回执](../evidence/A02/review/formal/counterexamples/crossbook/blocked-receipt.json)、[后续 READY 计划](../evidence/A02/review/formal/counterexamples/crossbook/fresh-ready-planned.json)。目标、日志和完整历史的三个时点文件保存在同目录。

最短复现（输出目录须不存在）：

```powershell
# cwd: D:\1800；脚本自行固定导入冻结副本 src
python -B docs/evidence/A02/review/formal/probe_crossbook.py `
  --output D:/1800/.local/stages/A02-review/crossbook-reproduce-new
```

退出 0 表示上述缺陷断言成功复现，不表示验收通过。修复应让暂停依据只来自同书 pending/UNKNOWN，保留完整历史，不能通过删除其他书历史规避。复验至少保留“同书换 action/run/question/scope 仍阻断”“另一书单独包正常”“包含另一书 UNKNOWN 的合法多书包仍可独立模拟”三组证据。这是当前会话的隔离错误，不是 A03 跨进程恢复缺口。

## 冻结与复现证据

已通过 raw Git blob 导出确切提交到 `D:/1800/.local/stages/A02-review/frozen-5c928572`，避免 checkout/archive 换行转换。导出及测试后分别核对全部 **1,116 个文件**，无摘要差异；base、实现及已接受 C01 来源均为交付祖先。基线至交付 **386 个改动路径**均在执行任务允许范围内。冻结执行报告 SHA256 为 `d8c0cfc961a0ac7a1d78a4ca8cfa235bb26a20ee1c3af5c0bbedc6ab492eddda`。原准备报告及其四项清单文件字节保持不变。

环境：Windows / PowerShell；Python 3.9.13，Pydantic 2.12.5。实际 Python 为 `C:/Users/ASUS/AppData/Local/Programs/Python/Python39/python.exe`；contracts、planner、mock、targetcheck 均导入上述冻结副本，未使用其他 editable 源码。测试临时目录位于授权 `.local/stages/A02-review/`。

| 实际命令（主目录运行，wrapper 内固定 cwd/导入路径） | 退出码 | 结果 |
|---|---:|---|
| `python docs/evidence/A02/review/formal/export_frozen.py` | 0 | 1,116 个 Git blob 校验、祖先及范围检查 |
| `python docs/evidence/A02/review/formal/run_commands.py` | 0 | 作者完整复现器、环境探针和异目录 CLI 校验 |
| 冻结副本 `python examples/a02/verify.py --output <新目录>` | 0 | 44 项 A02、70 项 C01、10 组演示通过 |
| `python docs/evidence/A02/review/formal/independent_review.py` | 1 | 60 项符合预期；1 项验收脚本输入构造错误，见下文 |
| `python -B docs/evidence/A02/review/formal/independent_review.py --supplement` | 0 | 9 项符合预期，含修正后的政策版本反例 |
| `python -B docs/evidence/A02/review/formal/supplement_final.py` | 0 | 明确 ABSENT 后重新检查/规划可执行；另一书独立包可执行 |
| `python -B docs/evidence/A02/review/formal/probe_crossbook.py` | 0 | R1 确定缺陷复现 |
| `python -B docs/evidence/A02/review/formal/probe_coverage_labels.py` | 0 | 两项附加边界观察，仅计算计划 |
| `python -B docs/evidence/A02/review/formal/consolidate.py` | 0 | 冻结源码复核、67 场景覆盖及命令收据汇总 |

实际命令、退出码和环境详见 [命令收据](../evidence/A02/review/formal/independent-command-receipts.json)、[作者复现收据](../evidence/A02/review/formal/commands.json)。作者复现 stdout/stderr 与完整输出均在 `formal/reproduction/`；各独立案例保留输入、计划、错误、目标、日志和回执。

验收脚本首轮的 `stale-policy` 使用浅复制，误改原政策的 source_notes 列表，先触发 HASH_MISMATCH，没有到达计划版本门。原失败证据保留；验收者只修正自己的脚本为深复制，单独复测得到 VERSION_CONFLICT。该脚本错误不计为 A02 缺陷。累计 72 次独立案例运行中，**71 次符合预期，1 次为上述已更正的验收脚本错误**；R1 另由专属反例确认。

作者 `verify.py` 在无 `.git` 的导出目录执行 `git rev-parse HEAD`，会读到并行维护的主目录版本。因此本次 `reproduction/manifest.json` 的 `code_commit` 不作为被验身份。所有实际导入文件由 [Git blob 导出清单](../evidence/A02/review/formal/frozen-export.json)与[测试后完整性记录](../evidence/A02/review/formal/source-integrity.json)绑定冻结提交；该元数据限制单独记于 [reproduction-bindings.json](../evidence/A02/review/formal/reproduction-bindings.json)，未改写原始输出。

## 原任务十条验收结果

| 条款 | 结果 | 独立证据与观察 |
|---|---|---|
| 1 确切版本、作者命令及 C01 检查 | 通过 | 冻结导出、固定模块导入；44/70 项及 10 演示复现 |
| 2 三模块真实计算与边界 | 通过 | 阅读完整实现、AST 导入检查；更改几何、重复题号及答案候选后实际生成并执行 3 题 / 9 框；不依赖 expected.json |
| 3 新题/已有映射及非法引用 | 通过 | 空目标、非空目标 null 新题、已有 ID/题序、不同目录命名空间、同题序不同真实 ID；缺目录、错序、空串、动作错映射及 null 绕过均拒绝 |
| 4 两 PASS、图谱/政策/目标/授权/能力双门 | 通过 | 缺报告/错阶段/非 PASS、旧修订、伪 TARGET、错书/目标/范围/操作/目录、能力 UNKNOWN/UNSUPPORTED/错版本；计划或执行按实际拒绝层关闭，无写入 |
| 5 身份/来源闭包及相关前置事实 | 通过 | 两章重复印刷号、跨页/共享片段、未选答案不混入；手算 4+3+2 框和顺序；正常前序变化通过；外部修改第二题事实后保留第一动作并阻断后续 |
| 6 效果/故障与独立读回 | 通过 | APPLIED/MATCH、NOT_APPLIED/ABSENT、丢响应但可读 APPLIED、丢读回/矛盾/部分生效 UNKNOWN；实际状态和日志分开核对 |
| 7 UNKNOWN 同书阻断、另一书独立及旧计划不可重播 | **失败（R1）** | 同书换 action/run/question/scope、省略调用历史仍阻断；三类旧计划不重播，ABSENT 后新检查/计划成功；另一书独立包通过，但合法多书包历史污染触发误暂停 |
| 8 分母、内容及提交状态 | 通过 | 独立 4 项清单含异常/跳过/未入图谱；框成功仍 CONTENT_PENDING/PENDING/NOT_SUBMITTED；未知题仍 UNKNOWN/NEEDS_RECONCILIATION |
| 9 UPDATE 与 A03 边界 | 通过（拒绝路径） | A02 对全部差量明确 UPDATE_UNSUPPORTED，无降级新建；不宣称持久恢复/正式解暂停；写后证据异常保留 pending，同书关闭 |
| 10 公共 API、精确依赖与模拟标记 | 通过（有边界说明） | 全部交付样例及正常独立包使用公共校验；来源/回执精确引用；C01 已保证与 A02 新保证分开；标签边界见 N2 |

[67 场景逐项索引](../evidence/A02/review/formal/matrix-results.json)保留每行状态和证据。F01/F02/U11 为版本、范围及边界静态复核；U05 因 R1 失败。没有用多个检查者的一致意见替代实际读回。

多动作未派发项的 NOT_APPLIED 已独立核对：模拟器对每项另采 before/readback，读回 OK，相关题未绑定且预期框 ABSENT，日志明确 `dispatched=false`。第一动作明确未生效时仅一项 intent；第一动作 UNKNOWN 时仍保留其实际 4 框和未决历史，后续 ABSENT 不会解锁原 UNKNOWN。第二动作丢响应得到 APPLIED/UNKNOWN/NOT_APPLIED 和 7 个实际框。额外注入首动作写后证据落盘失败，得到实际 4 框、pending 暂停和再次执行拒绝。

## 附加边界观察（不另计必须修缺陷）

**N1：有依据的排除项仍可能被保守拒绝。** 合法 PRE_APPLY PASS 输入增加同原图同 bbox 的页眉 region 与 EXCLUDED clue，A02 `coverage_for` 会将未入题闭包的页眉 region 计为 unassigned，TARGET 为 EXCEPTION，计划 BLOCKED。C01 规定 EXCLUDED clue 的 region_ids 为空，现版本没有明确的排除区域关联字段；仅 bbox 相同不应由验收者擅自制定自动排除规则。记录此兼容性限制，后续需明确来源/覆盖政策及支持范围，本轮不要求放宽完整性门。证据：[excluded-header/actual.json](../evidence/A02/review/formal/counterexamples/coverage-labels/excluded-header/actual.json)。

**N2：SYNTHETIC admission 检查没有覆盖证据注册表。** 将实际引用的 proof-target EvidenceRecord.mode 故意改为 OBSERVED，四类上游产物仍 SYNTHETIC；公共合同允许该方向依赖，A02 仍计算 PASS/READY。该反例仅规划，未执行；本次交付样例及实际模拟效果证据均为 SYNTHETIC，因此不将其等同于发生真实平台调用或伪造平台资格。不能将 A02 的 SYNTHETIC_ONLY 声明理解成完整的证据注册标签准入保证；如后续需要该保证，应明确拒绝策略并补测。证据：[observed-evidence-label/actual.json](../evidence/A02/review/formal/counterexamples/coverage-labels/observed-evidence-label/actual.json)。

## 限制、未验证层与交回主调度

C01 提供结构、引用/摘要、原图绑定、两阶段资格及回执/批次状态组合校验；A02 增加实际目标条件计算、支持范围内的动作投影、真实内存变更、读回效果比较及当前会话暂停。公共结构通过不能证明业务效果，合成 PRE_APPLY 仍为合同桩。

未执行或未验证：真实平台/浏览器/登录、OCR、B 识别组题质量、算法准确率、真实运行成本、最终内容正确性、最终提交、跨进程锁/持久事务/重启恢复、正式 ReconciliationResult 和 UNKNOWN 解除。全部 UPDATE、组合/父子/七选五/合并 W 仍是显式拒绝路径，没有验收其执行功能。空平台快照可用，不代表零题范围获得支持。

本次合成来源模拟结果不能解决 A01 的 REWORK 或 S01 公共真实来源完整性门禁；不授权真实 A01 SourceBundle 自动资格，不表示 B 已确认共同合同。

本轮平台动作、浏览器动作、凭据访问、外部模型调用与外部模型费用均为 0。只写本正式报告、`docs/evidence/A02/review/formal/`及授权临时目录；原准备材料保持不变，未修作者实现、合同或主调度状态，未联系其他 Codex 对话、管理 B、推送或集成。完整正式证据及本报告摘要统一登记于 [sha256-manifest.json](../evidence/A02/review/formal/sha256-manifest.json)。

交回主调度：以 R1 安排有界返修并冻结新提交后复验。主调度独立决定复现、接受、集成及 A03 依赖释放；本轮正式结论维持 **REWORK**。
