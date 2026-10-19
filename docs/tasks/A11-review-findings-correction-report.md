# A11 R01/R02 有限差量交付：REVIEW

2026-10-20（Asia/Shanghai）。按固定调度任务 `73ded167:docs/tasks/A11-review-findings-correction.md` 执行。原作者基线 `c580ca63ada9e452fd5ee71e5272cf0d047d4574`，独立发现基线 `1522d1b612ba35f441a046706e46eabf97fe4a8d`。实际分支 `codex/a11-review-delta`，目录 `D:/1800-worktrees/a11-live-pilot`；原 `codex/a11-live-pilot-core` 分支及全部旧成功/失败证据保留，未合入主线其他变更。

本轮唯一冻结运行产品及驱动：**`8ff44619b955983cc84041525c7b9176d45660f2`**。其后只新增实际证据和本报告，产品/驱动/测试/fixture 不再修改或补跑。最终证据提交由交付消息给出。

## 范围与额度

主调度依据用户持续推进指令修订原工程上限，作者总候选上限明确变为3；不是声称用户另回了额度批准。本轮仅第三候选、一次六项差量。原作者两次17项suite（第一失败、第二成功）和原独立17/17结果保持，本轮均未重跑。新增差量成功后额度已耗尽，没有第四候选。

只修改 `quality/live_pilot.py`、`runtime/live_pilot/runner.py`、`runtime/live_pilot/journal.py` 和允许更新的runbook。新增一个差量测试文件、`review_delta` fixture目录、本报告与新证据目录。源代码修改不涉及合同/schema、pins、依赖、其他源码、主调度JSON或旧fake。

原作者基线共30,411路径，其中30,407条保护路径 mode/type/blob 原样；仅上述4条允许路径修改，无删除。初次切分支时 Git sparse checkout 隐去了部分原A11文件，已从固定c580ca63 raw blob 恢复缺失文件；未覆盖现有差异，未改主线工作区。

## 两项实际修正

R01：`ordinary_choice` 与六角色仍是必要条件，但新增 `check_single_choice`。来源 SourceBundle.history 必须引用确切、已审阅的分类JSON资源；公共C01校验路径及摘要，新检查对实际读取bytes再次核SHA256。分类绑定书、内部题ID、六框事实摘要、六段文本摘要；本题 approval.choice_qualification 同时绑定相同资源引用和分类。仅明确 `SINGLE_CHOICE` 可继续；未知或多选拒绝。选项标签必须按A/B/C/D显式给出，答案全文恰为其中单个标签，BC等多答案拒绝；题干明确多选也保守拒绝。资源和批准共同绑定，不用未绑定的布尔自报替代来源。真实事实注册表仍缺，生产入口仍BLOCKED。

R02：`reconcile_readonly` 返回原apply_release、本次reconcile_release、当前release、status及不可重发处置。close抛异常或返回released=false均保留为失败，返回HOLD；返回false的原原因/会话字段不丢失。标准report同时显示apply与reconcile释放，当前释放未证明即HOLD，列出失败事件；较早apply成功不会覆盖后续对账失败。原UNKNOWN结果、后继NOT_RUN、发送占用与一次对账限制不改写；正常对账释放也保持resend_allowed=false、write_disposition=HOLD。

## 唯一实际六项差量

冻结前仅6个Python文件AST语法检查、fixture模型解析/重封、静态raw范围检查，0 suite/runtime。固定 [六项清单](../evidence/A11/review-delta-execution/case-catalog.json)、[11成员fixture摘要](../evidence/A11/review-delta-execution/fixture-manifest.json) 和 [冻结预检](../evidence/A11/review-delta-execution/freeze-preflight.json) 已随产品固定。

| 项 | 实际结果与命中层 |
|---|---|
| D01 | PASS。source+approval明确单选的两个合成输入获准；六框、文本、坐标与原fixture完全相同。0plan/intent/send。 |
| D02 | PASS。BC输入的C01、摘要、全文批准均有效；实际命中 `quality.check_single_choice / SINGLE_ANSWER_LABEL_REQUIRED`。 |
| D03 | PASS。明确MULTIPLE_CHOICE且答案仅B，C01和批准均有效；实际命中 `quality.check_single_choice / SINGLE_CHOICE_REQUIRED`。 |
| D04 | PASS。归档副本readonly对账MATCH后close抛OSError；返回/report均HOLD、本次release=false、原apply release=true。 |
| D05 | PASS。独立归档副本close返回false；返回/report均HOLD并保留原false原因与会话字段。 |
| D06 | PASS。独立归档副本正常只读释放如实显示true；原UNKNOWN/NOT_RUN保留，resend_allowed=false。 |

实际命令：

```powershell
$env:GIT_NO_LAZY_FETCH = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONDONTWRITEBYTECODE = '1'
python docs/evidence/A11/review-delta-execution/run-delta.py docs/evidence/A11/review-delta-execution/attempt-1
```

实际6/6 PASS，0 failure/error；worker执行UTC `2026-10-19T16:17:15.022931+00:00` 至 `16:17:18.941419+00:00`，外层180秒未触发。驱动fail-fast、保留每项进度与NOT_RUN机制；没有额外案例或第二次运行。[结果](../evidence/A11/review-delta-execution/attempt-1/result.json)、[日志](../evidence/A11/review-delta-execution/attempt-1/suite.log)。

第4–6项固定来源：`c580ca63:docs/evidence/A11/execution/attempt-2/runtime/test_T6_response_frame_and_read_failure/http_only`。来源含15个Git raw成员，[来源清单](../evidence/A11/review-delta-execution/archive-source-manifest.json) 固定commit/path/blob/SHA/字节数。每项独立创建raw副本，复制后检查原bytes；仅调用一次reconcile_readonly。没有运行apply、旧成功题或旧suite制造起点，也没有导入旧fake的send实现。

三副本原15成员均逐bytes保持，包括原UNKNOWN RESULT、NOT_RUN批次、发送占用和假backend；各自只新增RECONCILE_CLAIM、RECONCILE_RELEASE、RECONCILIATION三个事件及对应锚点。归档fake原发送计数为1，本轮新增send为0；三个对账各读取一次。每项copy-manifest及result.json保存起点、标准report、返回值、真实命中层和delta。旧源文件及旧证据未修改。

## 自有资源与未证明范围

唯一suite worker PID64084，由supervisor PID63976保留原Popen对象并等待退出。退出码0，原communicate/wait已完成，stdout/stderr句柄均关闭，外层未超时且没有终止进程。[创建](../evidence/A11/review-delta-execution/attempt-1/process-created.json)、[释放](../evidence/A11/review-delta-execution/attempt-1/process-release.json)、[PID只读复核](../evidence/A11/review-delta-execution/owned-process-readback.json)记录当前该worker无匹配活进程。三个journal作用域均结束，测试留证`book_gate_released=true`。关闭异常/false均为新增合成故障transport返回，不代表活浏览器或真实会话。

本轮0新plan/intent/apply/send，0平台/网络/浏览器/profile/SQLite/B消息/推送；无依赖安装、旧业务重放或主线集成。SourceBundle分类资源的REVIEWED在新增fixture中明确是合成测试标签，不能提升为真实人工审核或平台事实。

本六项只证明R01/R02有限差量，不宣称重跑后的全回归或平台合格。新增代码中未知分类拒绝、显式多选题干拒绝及未完成对账claim报告为静态实现；未在本轮追加第7项等反例。旧报告列出的真实wire/事实注册表、intent代码身份外部清单绑定及真实C01 ExecutionReceipt未闭合接口保持。本交付状态 **REVIEW**，独立验收待调度固定版本后进行；真实入口仍BLOCKED，最终NOT_SUBMITTED。
