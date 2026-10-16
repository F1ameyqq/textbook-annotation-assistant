# A05 主调度收口

2026-10-16，结论：**ACCEPTED，仅限书 46007447 新增题 22 的 Q/A 框保存与关闭重开恢复试验**。

主调度读取执行对话与独立验收对话的 completed 状态，核对执行提交 `a56ce0e23ee613cd81c09f7f21392ffc2ff17d60`、[独立验收报告](A05-review-report.md) 和双方会话释放证明。重新运行执行证据检查 34 项、独立证据检查 33 项，均通过；没有重开浏览器、重放写入或触发 OCR。

- 从 21 题 / 66 框变为 22 题 / 68 框，新题只有预期 Q/A 两框。
- 原 66 框的已导出字段与原目录保留，书仍为标注中；历史 OCR 内容没有完整写前快照，不能扩大保留证明。
- 只证明已保存结果的重开恢复；未保存草稿恢复、UNKNOWN 恢复、批量稳定性尚未验证。
- `content_check_status=PENDING`、`submission_status=NOT_SUBMITTED`，不宣称完整 OCR、自动识别或 B 算法已验收。
- 执行与验收专用浏览器均已关闭，无未决写入。新增题 22 不得重复执行。

复现：`python tools/a05_verify_evidence.py --output docs/evidence/A05/coordinator/execution-checks.json`；`python docs/evidence/A05/review/verify_independent_evidence.py`。证据分别见 [执行检查](../evidence/A05/coordinator/execution-checks.json)、[独立检查](../evidence/A05/review/independent-checks.json)。

归档时发现 Git 默认换行转换会改变证据原字节，故对证据、已签摘要报告和 A05 校验脚本保留原换行，不改现有 manifest。已核对基线 6 份、执行 43 份、独立验收 51 份文件摘要全部匹配；集成包含相应 `.gitattributes` 规则，并继续检查实际多余行尾空格。

当前仅完成 A05 的验收收口和证据归档。按原路线下一阶段为 C01 合同实现与固定样例；A05 不解除 C01/A01/A02/A03/A04 的模块验收要求。集成提交另在调度状态中记录，本地提交不表示已推送或 B 已收到。
