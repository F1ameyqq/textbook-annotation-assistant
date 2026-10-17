# A04 R3 原始Git字节补证

target `6c8137a4fadddc01a47906d564ab3460277c8958`；workflow `9317efcdb734b081075c56f6557838d591959e8f`。**补证PASS；限定OFFLINE_R3=ACCEPTED；A04_OVERALL=BLOCKED。**

[补充报告](../../../../tasks/A04-coordinate-R3-raw-bytes-review-report.md) · [结论](review-verdict.json) · [收口](closure-checks.json) · [新清单](sha256-manifest.json) · [自身释放](self-release.json)

旧报告的“全量原Git字节”来源描述错误。原tar及355项准确绑定此前archive表示，全部原字节保留。本次212项由cat-file直接提取；59项仅CRLF/LF不同，不能以归一比较替代原字节证明。

| 文件/目录 | 内容 |
|---|---|
| [archive-vs-cat-file.json](archive-vs-cat-file.json) | 59项差异，55 Python＋1 .gitattributes＋3 PGM；旧新摘要/大小分别记录 |
| [cat-file-export-command.json](cat-file-export-command.json) | 真实cat-file argv、212个commit:path查询、二进制协议和object SHA1复核 |
| `inputs/raw product with spaces/` | 真正运行的212个原始blob文件；没有使用archive/checkout转换 |
| [运行前](runtime-inputs-before.json) / [运行后](runtime-inputs-after.json) | object ID、Git SHA256、原大小、运行目录SHA256/大小，212项全部精确匹配 |
| `inputs/replay-scripts/` | 原样复制的精确反例、70项/26项检查及guard/进程helper；[摘要绑定](replayed-scripts.json) |
| [临时bootstrap](runtime-harness-bootstrap.json) | 原guard副本，单列的reviewer harness，不冒充目标文件 |
| `inputs/workflow/` | 固定补充任务、规则、主调度首次失败与直接blob复现证据 |
| `jobs/` | 每条命令实际argv/cwd、原始stdout/stderr、退出码、PID和创建时间 |
| [exact-replay/result.json](exact-replay/result.json) | 原hash的精确反例：wrapper0、产品2、无最终包 |
| [regression-result.json](regression-result.json) | 原样70项相关回归通过，不是旧archive成绩复用 |
| [independent-cases/results.json](independent-cases/results.json) | 原样26项独立检查通过；所有输出在新目录 |
| [separate-run-comparison.json](separate-run-comparison.json) | 旧archive运行与新cat-file运行明确分开，不双计 |
| [实际导入](actual-imports.json) | 实际parser/gate/loader路径及文件摘要与原blob对应；现有环境，无依赖变化 |
| [PGM绑定](pgm-resource-bindings.json) | 三张原始PGM的Git、运行、发布、搬运摘要相同；与旧archive字节不同但解码像素相同 |
| [旧保全前](old-preservation-before.json) / [后](old-preservation-after.json) | 355项＋原清单自身356份记录不变，包括旧tar、报告、脚本和失败 |

`scripts/run_supplement.py`是新路径控制器，因为旧控制器硬编码原stage/output；它没有修改原检查脚本、断言或期望值。一次运行包含规定的精确/70/26，以及任务要求的三张原始PGM公开发布与搬运绑定观察。生成目录均要求不存在，避免覆盖证据；精确重放可按补充报告使用新的`--output`。

本轮不扩展更早整套测试、格式或配置压力范围；R01～R06、S01继续BLOCKED。无浏览器/网络/平台/profile/凭据/模型/书籍动作，不改旧材料、产品、依赖或state，不提交/推送/集成，不联系其他任务/B。主调度收到冻结补充后决定有限接受和集成。
