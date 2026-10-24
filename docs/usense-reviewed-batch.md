# 经审校批次：离线准备与逐题续跑

本地格式 `b-usense-reviewed-batch-*/0.1` 属 B 侧实现，不修改公共合同。入口仍限定书籍 46007447；现在支持同书其他课时的已有题文本更新，不支持通用换书、建删框或拆题。Q7 insertion/finalize 保持原专用入口。

旧 `--orders` 调用已拒绝。原印刷题号、导出连续序号都不是稳定身份。每项必须明确 `printed_number`、`variant`、当前 `native_order`、目录 `node_id` 和 `question_info.id`（`info_id`）；由现有 updater 再核目录遍历序、原生 order、父目录、全框、单题框和 info。不会猜测原题17对应当前18，也不会因为目录标签相似而迁移题目。

## 三个命令

```powershell
python tools/run_usense_reviewed_batch.py prepare --manifest PRIVATE/manifest.json --sha256 MANIFEST_FILE_SHA256 --ledger-root PRIVATE/usense-existing-ledger --out PRIVATE/new-preparation
python tools/run_usense_reviewed_batch.py status --plan PRIVATE/new-preparation/batch-plan.json --sha256 PLAN_FILE_SHA256 --execution-root PRIVATE/new-execution
python tools/run_usense_reviewed_batch.py run --plan PRIVATE/new-preparation/batch-plan.json --sha256 PLAN_FILE_SHA256 --execution-root PRIVATE/new-execution --profile PRIVATE/browser --authorization-reference CURRENT_AUTHORIZATION
```

`PRIVATE/...` 是说明用占位路径；实际清单引用全部使用绝对路径。入口按脚本所在仓库加载，无需安装项目，也不接受另一个 `--repo` 覆盖。可选 `--dependency-dir` 仅向子进程提供已有依赖；可选 `--tls-approval-reference` 传递现有运行时的明确证书批准。两个离线命令只用 Python 标准库，不导入 Playwright、不启动浏览器。`prepare` 就是 dry-run，不创建配置或发送意图。`run` 才调用原有配置、writer 和独立 capture 子进程，不重写网络传输。

所有输入校验通过后才独占创建准备输出。准备文件绑定清单、原始 capture 字节、候选、来源、审校文件、前序证据和整个运行包的摘要。代码变化须重新准备，已有配置也须按原运行时规则重新冻结。

## 私有清单

以下是形状示例，所有 ID、题号及路径都为合成占位，不能直接用于平台。各 `sha256` 是相应文件原始字节的 SHA256；候选沿用 updater 的 `target`、`approved_changes` 格式，来源和审校引用必须实际存在。

```json
{
  "schema": "b-usense-reviewed-batch-manifest/0.1",
  "book_id": "46007447",
  "source_lesson": "synthetic-lesson2",
  "lesson_directory_id": "synthetic-confirmed-lesson-node",
  "scope_review": {"path": "C:/private/scope.json", "sha256": "FILE_SHA256"},
  "captures": [{"path": "C:/private/current-reader/capture-summary.json", "sha256": "FILE_SHA256"}],
  "items": [{
    "item_id": "printed17-main",
    "printed_number": "17",
    "variant": "main",
    "native_order": 18,
    "node_id": "synthetic-stable-question-node",
    "info_id": "synthetic-stable-info-id",
    "candidate": {"path": "C:/private/candidate.json", "sha256": "FILE_SHA256"},
    "pages": [12, 173],
    "previous_acceptance": null
  }]
}
```

`scope.json` 必须包含 `schema: b-usense-batch-scope-review/0.1`、相同的 `book_id/source_lesson/lesson_directory_id`、`directory_membership: CONFIRMED`，以及与清单顺序相同的 `mapping` 数组。每项 mapping 恰含 `item_id/printed_number/variant/native_order/node_id/info_id`。这条来源审校记录要求操作者明确确认来源课时与实际目录的对应，不能用目录标签或同号题替代；`CONFLICT` 或缺记录直接拒绝。

`captures` 引用现有采集器的 `UsenseNativeCapture/v1` 原始摘要，可有多批。各摘要必须成功、零写入且释放完成，原始响应字节/长度/状态/双层请求次数可核；公共目录/全框/来源等重叠响应必须逐字节相同。每项必须覆盖完整九项题目/全局响应（directory、frames、annotations、info、五区），加 source 和所列来源页；页数沿用现有端点上限。框所在页必须列入。捕获时间不能在未来，最旧响应最多15分钟。准备和剩余题续跑都会检查此窗口，无法用新清单给旧响应刷新日期。

相同 item_id、node_id、info_id、原生序号或原印刷号/变式组合不允许重复；当前已采集 info ID 之间也不能冲突。不同课时的同号题应分开批次并经来源审校。

## 逐题状态与断点

`status` 从原始证据重新计算状态，不信任一个手写 summary 的 ACCEPTED 字符串。`next_item_id` 仅在整批无阻断且剩余基线未过期时给出。`status` 本身的平台请求数为零，不代表此前 writer 没有写入。

|状态|含义与可继续条件|
|---|---|
|READY|尚未 dispatch、没有不明旧 intent、来源与当前基线完整，可以显式 run|
|NO_CHANGE_OFFLINE|审校文本与本地基线同值；无需发送，不宣称已新读回平台|
|ACCEPTED|完整旧 writer/reader 进程、原始收据/字节、配置、网络 guard、ledger 和读回经现有 `verify_previous_acceptance` 再核，可跳过|
|BLOCKED_NO_RETRY|未知发送、缺证据、中断目录、身份/摘要变化、过期基线等；整批禁止继续|

执行根绑定唯一 batch 摘要，且有独占运行锁。每题在任何子进程之前写独占 `dispatch.json`；子进程超时、输出异常或未知回执均保留该标记，第二次运行会阻断，不因为没看见收据而再发。即使失败发生在配置阶段，也采用这个保守策略。未消解的运行锁不能自动清除。该锁与 writer 原有 profile/稳定身份 ledger 检查共同使用。

每题独立运行 writer，成功并退出后才运行新配置的 capture。原 updater 比较目标完整状态及来源页，原 predecessor verifier 再核时间顺序、不同 PID/上下文、原始响应与收据、发送次数、网络事件和 ledger，全部通过后才选下一题。已验收题只跳过，不调用 writer。手写 acceptance、UNKNOWN 原回执、缺 accepted marker 或其他未知修订分支都不能作为续跑依据。

显式修改已验收题时，清单的 `previous_acceptance` 必须 SHA 绑定原 `acceptance.json`。准备阶段直接复用完整前序 verifier，当前基线必须精确等于旧读回；新 intent 沿用现有 revision key，不清旧 ledger。已重排的旧前序目标不匹配时拒绝，不自行迁移历史。

基线在中断期间过期时，只能由平台独占操作者重新采集并审查剩余范围、准备新的剩余批次。新批次不得包含未消解 intent 的题。此工具不提供 UNKNOWN 消解、自动补发或把历史 UNKNOWN 改成 ACCEPTED 的功能。

## 下一课时真实输入边界

固定 `ee463c8` 的完成记录说明：第2课时原印刷17—21目前为原生18—22，仍存在目录归属冲突。这只是已完成第一课时后的历史映射，不能直接生成本次 live 计划。启动下一课时至少还需：15分钟内的当前采集、来源课时/目录冲突的明确处置及 scope 审校、逐题稳定节点和 info ID 映射、逐区来源审校候选及当前专用 profile 的真实 ledger。此离线工作线没有操作平台、登录态或业务导出，没有重放第一课时17题。

## 离线验证

```powershell
$env:PYTHONPATH='src'
python -B -m unittest discover -s tests -p test_usense_reviewed_batch.py -v
python -B -m unittest discover -s tests -p 'test_usense_live*.py' -v
python -B -m unittest discover -s tests/usense_live -p 'test_*.py' -v
```

测试用合成内容覆盖重排、身份歧义、来源/目录冲突、缺响应、原字节变动、过期、未知旧 ledger、显式修订、断点拒绝重发、完整前序正例和任意 cwd 的实际 CLI。测试不构成真实下一课时平台或业务验收。
