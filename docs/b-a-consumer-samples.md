# B→A 离线消费者样例提案

更新时间：2026-10-17，Asia/Shanghai。负责人：B 侧。基线：`103d98da822ba4ec246057aa31b0d71ff6886cfd`，分支 `b-side/readonly-book-46007447`。合同 `contracts-v1.md` 仍是设计草案；本文及下列 B trial 都是 B proposal，不是 A 兼容通过、合同冻结或平台验收。

## 固定证据与复现

正常结构样例来自当前固定真实计划 [content-region-plan-v1.json](../tests/fixtures/book46007447/content-region-plan-v1.json)，计划 SHA-256 为 `c11b6233cf61d551d7864ce8ee3245bc36482204e6e41b280df20f9da7bf9438`，计划内部内容引用为 `content-revision-plan-185419c281c293a2e7f0806b` revision 3、hash `bde8b2b74da9f008faba58c70b321745e09144b4d82a37930c94ed98891a2df9`。其区域操作绑定真实固定裁片 `tests/fixtures/book46007447/recovery-assets/unit2-q16.png` 和原图 SHA `a231f0247cd0444cc34ed699c4cca99245d2ac6cfda5ef10a38ca3f8164510be`。计划内容可追溯实际来源和真实 B 产物；其中 Q16 三行是未核准 `MODEL_DRAFT`，并非正确转写金标准。

实际 14 阶段运行、G07/Check07 引用、范围、HOLD 与不完整状态记录在 [content-region evaluation](../evaluation/book-46007447-content-region.json) 及 [区域重建说明](b-content-region-46007447.md)。运行目录 `data/runs/46007447-content-region-pipeline-v1` 被忽略且含 SQLite/对象存储；当前自动区域导出中 graph 约 18 MB、application 约 20 MB。为避免手工裁剪破坏对象引用、hash 或丢失 provenance，本提案不提交裁切后的 G07/Check07 JSON，也不将 evaluation 摘要伪装成完整 stage wrapper。

检查固定计划和已有生产者回归：

```powershell
Get-FileHash tests/fixtures/book46007447/content-region-plan-v1.json -Algorithm SHA256
python -m unittest tests.test_content_region_pipeline_cli -v
```

第二条命令中的既有测试验证真实计划语义所在的 0.2/G07/Check07 链：产生 `b-graph-trial/0.7` 与 `b-check-trial/0.7`、Check07 引用当前 G07、决定为 HOLD；还验证 0.1 计划承载 0.2 区域操作时不发布 final outputs。测试运行时另含合成像素测试，不能把该测试数据说成真实业务样例。要查看当前真实输出，先用 evaluation 的 `pipeline_runs`/`final_outputs` 引用在本机 SQLite 对象目录定位并核对引用；不要从另一个 run 或旧 Check06 拼接。

## 消费样例与预期

| 样例 | 可追溯输入/变体 | A 消费者应验证的边界 | 提案预期 |
|---|---|---|---|
| 正常结构 | 固定真实计划经当前 0.2 区域链生成的 G07 与 Check07；以 evaluation 的真实运行回执和对象引用定位，不从摘要重造对象 | envelope/schema 明确为 B trial 0.7；从 `payload.result` 读取 stage 结果；检查最终 E/G07/Check07 互相引用及 book/scope；`content_fragments` 中三条 `REGION_DRAFT` 含有来源区域、多片段分配及 plain/LaTeX runs；`render_regions`/`content_fragment_ids` 与当前 typed 呈现一致；保留 `MODEL_DRAFT`、`UNVERIFIED`、`complete=false`、`business_acceptance=false` 和问题 | 结构层可解析/可呈现的候选；业务决策必须是 HOLD，不能提升为内容正确、READY 可提交或 G1 通过。该结果是 B 对消费者行为的建议，等待 A 实际运行并记录 |
| 歧义/缺片段 | 同一固定 Q16 真实来源：Q16 有旧 OCR 缺失/分母拆行、F5 无原 OCR 片段、F9 旧两遍一致但错误；评估记录该来源证据及 50 项独立来源风险。用真实 G07/Check07，不新造文本或篡改图谱来表示“业务真相” | 保留空旧 `source_fragment_ids` 也可能是有 `source_region` 的新 `REGION_DRAFT`；不得因此隐藏区域。逐项消费 Check07 的当前问题与草稿风险，检查其引用当前 G07；歧义、缺失或未核准证据不能由完整字段/高置信度/来源一致性消除 | 结构上可读取，同时保留 HOLD/未决项；消费者拒绝“可提交/内容 PASS”结论。缺片段不是缺失 JSON key 的同义词，A 应按 B trial 语义检查并报告是否支持 |
| 陈旧版本 / 未知版本 | 陈旧负例：现有测试把同一带区域计划改标 0.1 并验证 pipeline FAILED 且 `final_outputs=null`。未知版本：由 A 在隔离的测试副本把 schema_version 改成未注册值；不提交伪造业务对象 | 陈旧 E/G/Check 或对象引用不匹配时拒绝，不得借用旧检查；未知 schema/version 必须显式拒绝并返回可诊断错误，不按字段相似度猜测为 0.6/0.7；失败不能提供最终输出 | 拒绝，记录具体拒绝原因；B 侧既有回归只证明旧 0.1 操作新区域计划会失败，不声称它已覆盖 A 的未知版本策略。未知版本一例待 A 消费者实际实现/回执 |

这些情况共享固定书籍与来源事实，能够复现 B 的实际版本边界；负例是对固定真实输入做的消费者测试变换，不得把变换后对象称为真实 B 生产输出。未知版本值应由 A 的测试临时生成，避免约定一个看似正式的版本号。

## 接收状态与限制

状态：B 提案；A 未验证；公共合同未冻结；无 A 兼容通过声明。没有新建固定样例，因为完整 G07/Check07 仅存在于忽略的运行对象库，安全裁剪仍需要保持跨对象引用、stage wrapper 与内容 hash 一致；仓库中的计划、评估和说明提供 provenance，但不等同可独立导入的完整输出包。A 若要独立导入，需先取得同一 run 的完整当前对象闭包，或提供其固定消费者期望的包格式，再冻结最小导出包及摘要。

局限：当前固定计划是局部样书 Q16/Q9 的未核准草稿，非留出集、非人工标准；运行产物不随仓库提交。本文未改公共合同或 A 侧状态，未运行模型、网站操作或平台消费者；提交和远端版本以本 PR 与 B 状态为准。
